#!/usr/bin/env python3
"""Keep the runbook from growing back, one defensible addition at a time.

RUNBOOK.md reached ~3500 lines of prose without a single bad commit: every
paragraph was reasonable on its own. A whole-file ceiling only punishes
whoever adds the last straw, so this measures each straw instead -- a budget
per `##` section, and a cap on how much prose one commit may add net of what
it removes. Cutting as much as you add always passes.

Both rules count PROSE words only: words outside fenced code blocks, and not
in headings, blank lines, table rows, or the "Where things are" index.
Commands, output and the index are free; explanation is what costs.

Usage:  python3 scripts/lint_runbook_prose.py [--all] [--warn-only] [--base REF]

  --all        report every over-budget section regardless of staging (CI)
  --warn-only  print findings, exit 0
  --base REF   diff the staged files against REF instead of HEAD
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files this lint governs.
CHECKED_GLOBS = ("RUNBOOK.md", "runbooks/*.md")

# Prose words allowed in one `##` section.
SECTION_PROSE_MAX = 140

# Net prose words (added minus removed) one commit may add across all
# checked files.
COMMIT_PROSE_DELTA_MAX = 40

# A commit that touches a runbook may also touch only these. Anything else
# -- code, scripts, compose, ansible, host, secrets -- goes in its own
# commit, so a runbook edit can be reviewed and rejected on its own.
RUNBOOK_COMMIT_ALLOWED = ("RUNBOOK.md", "runbooks/", "README.md", "CLAUDE.md", "reference/")

# Section whose body is a generated navigation index, not prose.
EXEMPT_SECTIONS = ("Where things are",)

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’./_-]*")


def is_checked(path):
    p = str(path)
    return p == "RUNBOOK.md" or (p.startswith("runbooks/") and p.endswith(".md"))


def _is_table_delimiter(stripped):
    """A '---|---' style delimiter row, with or without a leading pipe."""
    return "|" in stripped and "-" in stripped and set(stripped) <= set("|-: ")


def _prose_lines(text):
    """Yield (section_id, section_title, line) for every prose-bearing line.

    section_id increments on each `##` heading, so two sections that happen
    to share a title (e.g. two `## Backup`) stay distinct rather than
    merging into one combined count.
    """
    section_id = 0
    section_title = "(preamble)"
    in_fence = False
    fence_char = None
    fence_len = 0
    in_table = False
    pending = None  # a line held back in case it's a table header, not prose

    def flush():
        nonlocal pending
        if pending is not None:
            item, pending = pending, None
            return item
        return None

    for line in text.splitlines():
        if in_fence:
            s = line.strip()
            if s and set(s) == {fence_char} and len(s) >= fence_len:
                in_fence = False
            # A `#` comment inside a shell fence is prose wearing a costume;
            # count it, or budgets get met by moving sentences into fences.
            elif re.match(r"^\s*#", line) and not line.lstrip().startswith("#!"):
                item = flush()
                if item:
                    yield item
                yield section_id, section_title, line
            continue
        m = FENCE_RE.match(line)
        if m:
            item = flush()
            if item:
                yield item
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            in_fence = True
            in_table = False
            continue
        h = HEADING_RE.match(line)
        if h:
            item = flush()
            if item:
                yield item
            in_table = False
            if len(h.group(1)) == 2:
                section_id += 1
                section_title = h.group(2)
            continue
        stripped = line.strip()
        if not stripped:
            item = flush()
            if item:
                yield item
            in_table = False
            continue
        if _is_table_delimiter(stripped):
            pending = None  # the line just before this was a header, not prose
            in_table = True
            continue
        if in_table:
            if "|" in stripped:  # a table body row, piped or not
                continue
            in_table = False
        if stripped.startswith("|"):  # a piped row with no delimiter above
            continue
        item = flush()
        if item:
            yield item
        pending = (section_id, section_title, line)
    item = flush()
    if item:
        yield item


CODE_SPAN_RE = re.compile(r"`[^`]*`")


def _words(line):
    """Prose words on a line; inline `code spans` are commands, not prose."""
    return len(WORD_RE.findall(CODE_SPAN_RE.sub(" ", line)))


def count_prose_words(text):
    """Total prose words in a document."""
    return sum(
        _words(line)
        for _, section, line in _prose_lines(text)
        if section not in EXEMPT_SECTIONS
    )


def section_word_counts(text):
    """[(section title, prose words)], in document order, index excluded.

    A list, not a dict: two sections that share a title (e.g. two separate
    `## Backup`) must stay separate entries rather than merge their counts.
    """
    order = []
    counts = {}
    for section_id, title, line in _prose_lines(text):
        if title in EXEMPT_SECTIONS:
            continue
        if section_id not in counts:
            counts[section_id] = [title, 0]
            order.append(section_id)
        counts[section_id][1] += _words(line)
    return [tuple(counts[sid]) for sid in order]


def _git(args):
    return subprocess.run(
        ["git"] + args, cwd=ROOT, capture_output=True, text=True
    )


def git_show(ref, path):
    """File content at ref (use ':' for the index), or None if absent."""
    spec = f":{path}" if ref == ":" else f"{ref}:{path}"
    r = _git(["show", spec])
    return r.stdout if r.returncode == 0 else None


def staged_paths():
    r = _git(["diff", "--cached", "--no-renames", "--name-only", "--diff-filter=ACMRD"])
    return [p for p in r.stdout.splitlines() if p.strip()]


def tracked_checked_files():
    files = []
    for pattern in CHECKED_GLOBS:
        files.extend(sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern)))
    return [f for f in files if is_checked(f)]


def check_sections(paths, read):
    findings = []
    for path in paths:
        text = read(path)
        if text is None:
            continue
        for title, count in section_word_counts(text):
            if count > SECTION_PROSE_MAX:
                findings.append(
                    f"{path}: section '{title}' has {count} prose words "
                    f"(max {SECTION_PROSE_MAX})"
                )
    return findings


def check_delta(paths, base):
    added = 0
    removed = 0
    for path in paths:
        before = git_show(base, path)
        after = git_show(":", path)
        before_n = count_prose_words(before) if before is not None else 0
        after_n = count_prose_words(after) if after is not None else 0
        if after_n > before_n:
            added += after_n - before_n
        else:
            removed += before_n - after_n
    delta = added - removed
    if delta > COMMIT_PROSE_DELTA_MAX:
        return delta, [
            f"commit adds {delta} net prose words to the runbooks "
            f"(max {COMMIT_PROSE_DELTA_MAX}); cut as much as you add"
        ]
    return delta, []


def check_runbook_only(staged):
    if not any(is_checked(p) for p in staged):
        return []
    strays = [
        p
        for p in staged
        if not is_checked(p) and not any(p == a or p.startswith(a) for a in RUNBOOK_COMMIT_ALLOWED)
    ]
    if not strays:
        return []
    return [
        "runbook edits land in their own commit so they can be reviewed and "
        "rejected on their own; also staged: " + ", ".join(sorted(strays))
    ]


def main(argv):
    check_all = "--all" in argv
    warn_only = "--warn-only" in argv
    base = "HEAD"
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print("runbook-prose: --base requires REF", file=sys.stderr)
            return 2
        base = argv[i + 1]

    findings = []
    if check_all:
        paths = tracked_checked_files()
        findings += check_sections(paths, lambda p: (ROOT / p).read_text(encoding="utf-8"))
        summary = f"checked {len(paths)} runbook file(s)"
    else:
        staged = staged_paths()
        checked = [p for p in staged if is_checked(p)]
        if not checked:
            return 0
        findings += check_runbook_only(staged)
        findings += check_sections(checked, lambda p: git_show(":", p))
        delta, delta_findings = check_delta(checked, base)
        findings += delta_findings
        summary = f"checked {len(checked)} staged runbook file(s), net prose delta {delta:+d}"

    for f in findings:
        print(f"runbook-prose: {f}")
    if findings:
        print(f"runbook-prose: {len(findings)} finding(s); {summary}")
        return 0 if warn_only else 1
    print(f"runbook-prose: OK -- {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
