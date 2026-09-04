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
SECTION_PROSE_MAX = 120

# Net prose words (added minus removed) one commit may add across all
# checked files.
COMMIT_PROSE_DELTA_MAX = 40

# A commit that touches a runbook may also touch only these. Anything else
# -- code, scripts, compose, ansible, host, secrets -- goes in its own
# commit, so a runbook edit can be reviewed and rejected on its own.
RUNBOOK_COMMIT_ALLOWED = ("RUNBOOK.md", "runbooks/", "README.md", "CLAUDE.md", "reference/")

# Section whose body is a generated navigation index, not prose.
EXEMPT_SECTIONS = ("Where things are",)

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’./_-]*")


def is_checked(path):
    p = str(path)
    return p == "RUNBOOK.md" or (p.startswith("runbooks/") and p.endswith(".md"))


def _prose_lines(text):
    """Yield (section_title, line) for every prose-bearing line."""
    section = "(preamble)"
    in_fence = False
    fence_marker = None
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence, fence_marker = True, m.group(1)
            elif line.strip().startswith(fence_marker):
                in_fence, fence_marker = False, None
            continue
        if in_fence:
            continue
        h = HEADING_RE.match(line)
        if h:
            if len(h.group(1)) == 2:
                section = h.group(2)
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):  # table row
            continue
        if set(stripped) <= set("|-: "):  # table rule
            continue
        yield section, line


def count_prose_words(text):
    """Total prose words in a document."""
    return sum(
        len(WORD_RE.findall(line))
        for section, line in _prose_lines(text)
        if section not in EXEMPT_SECTIONS
    )


def section_word_counts(text):
    """{section title: prose words}, in document order, index excluded."""
    counts = {}
    for section, line in _prose_lines(text):
        if section in EXEMPT_SECTIONS:
            continue
        counts[section] = counts.get(section, 0) + len(WORD_RE.findall(line))
    return counts


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
    r = _git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
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
        for title, count in section_word_counts(text).items():
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
        base = argv[argv.index("--base") + 1]

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
