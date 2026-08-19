#!/usr/bin/env python3
"""
Git clean/smudge filter for plugin-config values that legitimately differ
per machine. The first case is signalk-ntfy's server URL: the dev docker
stack reaches ntfy over the compose network as `http://ntfy:80`, the boat
Pi's native SignalK reaches its own ntfy container as
`http://localhost:8090`. One tracked file cannot hold both, and whichever
machine committed last used to win.

Git stores a placeholder:      "url": "{{ ntfy_url }}"
The working tree holds this machine's value, read from hostvars.local.yaml
(gitignored, one per machine; template in hostvars.local.yaml.example).
smudge expands the placeholder on checkout, clean contracts the value back
on commit -- so SignalK reads and rewrites the file exactly as it always
did, and the machine-specific value never reaches git.

Same architecture as the pseudonymize layer inside scripts/sops_filter.py
-- a reversible textual substitution on quoted JSON string values -- but
keyed on a per-machine file instead of an encrypted shared map, and with no
sops step: these values are not secrets, they just are not shared.

Only whole values substitute ("{{ name }}" must be the entire JSON string,
and clean matches the quoted value byte-for-byte). Nothing is ever rewritten
inside a longer string, which is what keeps the reverse direction exact:
a value like `http://ntfy:80` can't be clobbered where it happens to appear
as a fragment of some other setting.

Which files and which variables: .hostvars.yaml (tracked).
Which values: hostvars.local.yaml (gitignored).

Usage:
    hostvars_filter.py clean  <repo-relative-path>   # working tree -> git
    hostvars_filter.py smudge <repo-relative-path>   # git -> working tree
    hostvars_filter.py refresh   # re-expand covered files after editing
                                 # hostvars.local.yaml, preserving all other
                                 # local edits (unlike `git checkout --`)
    hostvars_filter.py check     # committed/staged form still holds every
                                 # declared placeholder (pre-commit + CI)
    hostvars_filter.py paths     # covered files, for setup-git-filters.sh
"""
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # handled per-subcommand in main()
    yaml = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import secretguard  # noqa: E402  -- needs the sys.path line above
CONFIG = os.path.join(REPO, ".hostvars.yaml")
LOCAL = os.path.join(REPO, "hostvars.local.yaml")
LOCAL_EXAMPLE = "hostvars.local.yaml.example"

# `{{ name }}` as the ENTIRE quoted JSON string, nothing else. Matches the
# jinja2 syntax render.py already uses, so a later Ansible migration reads
# these files as the templates they effectively are.
TOKEN_RE = re.compile(r'"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}"')


class LocalUnavailable(Exception):
    """hostvars.local.yaml is missing or unusable."""


def warn(message):
    sys.stderr.write(f"hostvars: {message}\n")


def token(name):
    return '"{{ ' + name + ' }}"'


def load_config():
    """{repo-relative path: [variable names]} from the tracked config."""
    with open(CONFIG) as f:
        config = yaml.safe_load(f) or {}
    return {path: names or [] for path, names in (config.get("paths") or {}).items()}


def load_local():
    """{name: value} from this machine's hostvars.local.yaml.

    Raises LocalUnavailable rather than returning empty defaults: an empty
    map during smudge would silently leave placeholders in a file SignalK is
    about to read as live configuration.

    Duplicate values are rejected because clean maps value -> name; two
    names sharing a value would make that reversal ambiguous.
    """
    if not os.path.exists(LOCAL):
        raise LocalUnavailable(
            f"no {os.path.relpath(LOCAL, REPO)} on this machine -- copy "
            f"{LOCAL_EXAMPLE} to it and set this machine's values"
        )
    with open(LOCAL) as f:
        values = yaml.safe_load(f) or {}
    if not isinstance(values, dict):
        raise LocalUnavailable(f"{os.path.relpath(LOCAL, REPO)} is not a key: value map")
    for name, value in values.items():
        if not isinstance(value, str) or not value:
            raise LocalUnavailable(
                f"{os.path.relpath(LOCAL, REPO)}: '{name}' must be a non-empty "
                f"string (quote values YAML would otherwise retype)"
            )
    seen = {}
    for name, value in values.items():
        if value in seen:
            raise LocalUnavailable(
                f"{os.path.relpath(LOCAL, REPO)}: '{name}' and '{seen[value]}' "
                f"hold the same value, so clean can't tell which placeholder "
                f"to restore -- give them distinct values"
            )
        seen[value] = name
    return values


def expand(text, names, values):
    """Git form -> working-tree form. Returns (text, unresolved names).

    Placeholders whose name isn't declared for this file, or has no local
    value, stay as-is -- smudge must never fail, because that breaks
    `git checkout` itself.
    """
    unresolved = []

    def convert(match):
        name = match.group(1)
        if name not in names:
            return match.group(0)
        if name not in values:
            unresolved.append(name)
            return match.group(0)
        return json.dumps(values[name])

    return TOKEN_RE.sub(convert, text), unresolved


def contract(text, names, values):
    """Working-tree form -> git form. Returns (text, names left unplaced).

    A name comes back in the second element when its placeholder is absent
    from the result -- either the file never had it, or the value on disk no
    longer matches hostvars.local.yaml (e.g. the URL was edited in SignalK's
    admin UI). Committing then carries the literal value into git; callers
    warn, and the `check` gate blocks it at commit/CI time.
    """
    for name in names:
        if name in values:
            text = text.replace(json.dumps(values[name]), token(name))
    unplaced = [name for name in names if token(name) not in text]
    return text, unplaced


def head_blob(path):
    """Whatever HEAD has for `path`, or None. Companion to index_blob."""
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"], capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def index_blob(path):
    """Git's current copy of `path` (the index), or None if untracked."""
    result = subprocess.run(
        ["git", "show", f":{path}"], capture_output=True, text=True, cwd=REPO
    )
    return result.stdout if result.returncode == 0 else None


def clean(path, text):
    names = load_config().get(path)
    if not names:
        return text
    try:
        values = load_local()
    except LocalUnavailable as error:
        warn(f"WARNING - {error}")
        warn(
            f"WARNING - machine-local values in {path} cannot be mapped back "
            "to placeholders and would be committed literally."
        )
        return text
    result, unplaced = contract(text, names, values)
    for name in unplaced:
        warn(
            f"WARNING - {path} contains neither '{{{{ {name} }}}}' nor this "
            f"machine's value for it. If the value changed on disk, update "
            f"hostvars.local.yaml, run scripts/hostvars_filter.py refresh, "
            f"then re-stage with: git add --renormalize {path}"
        )
    return result


def smudge(path, text):
    names = load_config().get(path)
    if not names:
        return text
    try:
        values = load_local()
    except LocalUnavailable as error:
        warn(f"WARNING - {error}")
        warn(
            f"WARNING - placeholders in {path} stay unexpanded. SignalK would "
            "read them as literal values; fix hostvars.local.yaml and re-run "
            "scripts/setup-git-filters.sh before starting it."
        )
        return text
    result, unresolved = expand(text, names, values)
    for name in unresolved:
        warn(
            f"WARNING - {path} references '{{{{ {name} }}}}' but "
            "hostvars.local.yaml has no value for it -- left unexpanded."
        )
    return result


def blob_pattern(blob, names):
    """Regex matching any working-tree expansion of git's copy of a file.

    Each declared placeholder in the blob becomes a wildcard for one quoted
    JSON string; everything else must match byte-for-byte. Used by refresh
    to recognize a file whose only difference from git is the expanded
    values -- in which case the blob itself IS the contracted form, even
    when the values on disk came from an older hostvars.local.yaml.
    """
    pattern = ""
    pos = 0
    for match in TOKEN_RE.finditer(blob):
        if match.group(1) not in names:
            continue
        pattern += re.escape(blob[pos:match.start()]) + r'"(?:[^"\\]|\\.)*"'
        pos = match.end()
    return pattern + re.escape(blob[pos:])


def refresh():
    """Rewrite covered files in place from the current hostvars.local.yaml.

    contract-then-expand, so a value edited in the local file lands on disk
    without discarding any other local change in the file (which is what a
    bare `git checkout --` would do). The usual case -- the on-disk value
    came from an OLDER hostvars.local.yaml and matches nothing in the
    current one -- is recovered positionally from git's copy of the file,
    provided nothing else in the file differs from git.
    """
    values = load_local()  # let LocalUnavailable escape -- refresh needs it
    for path, names in load_config().items():
        full = os.path.join(REPO, path)
        if not os.path.exists(full):
            continue
        with open(full) as f:
            text = f.read()
        contracted, unplaced = contract(text, names, values)
        if unplaced:
            blob = index_blob(path)
            if blob is not None and re.fullmatch(blob_pattern(blob, names), text):
                contracted, unplaced = blob, []
        for name in unplaced:
            warn(
                f"{path}: can't place '{{{{ {name} }}}}' -- its on-disk value "
                "matches nothing in hostvars.local.yaml AND the file carries "
                "other uncommitted changes. Commit those first, then re-run."
            )
        result, _ = expand(contracted, names, values)
        if result != text:
            with open(full, "w") as f:
                f.write(result)
            print(f"refreshed {path}")
        else:
            print(f"unchanged {path}")
    return 0


def check():
    """Assert git's copy of every covered file still holds its placeholders.

    Reads the index (`git show :path`), not the working tree -- the working
    tree is *supposed* to hold the machine-local values. Run by pre-commit
    and CI; a failure means a literal value got past the clean filter,
    usually a clone that never ran scripts/setup-git-filters.sh.
    """
    failures = []
    for path, names in load_config().items():
        blob = index_blob(path)
        if blob is None:
            continue  # not tracked (yet) -- nothing to leak
        for name in names:
            if token(name) not in blob:
                failures.append(
                    f"{path}: git's copy is missing the '{{{{ {name} }}}}' "
                    f"placeholder -- a machine-local value is being committed "
                    f"literally. If the value on disk changed (e.g. via the "
                    f"admin UI), set it in hostvars.local.yaml and run "
                    f"scripts/hostvars_filter.py refresh; if this clone never "
                    f"ran scripts/setup-git-filters.sh, run that. Either way, "
                    f"re-stage with: git add --renormalize {path}"
                )
    if failures:
        print(f"hostvars check failed ({len(failures)} problem(s)):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"OK: {len(load_config())} hostvars file(s) hold their placeholders in git.")
    return 0


def main():
    args = sys.argv[1:]

    # pyyaml is not in the stdlib, and each subcommand has a different
    # right answer when it is missing.
    #
    # `check` degrades: it runs on every commit via an always_run hook, so
    # an ImportError here blocked a clone with no pyyaml from committing
    # anything at all, a markdown typo fix included.
    #
    # `smudge` degrades too, and for the same reason scripts/sops_filter.py
    # does: leaving the {{ placeholders }} in the working tree is exactly
    # the documented fresh-clone state, and erroring would break
    # `git clone` and `git checkout` on a machine that was never going to
    # run SignalK.
    #
    # `clean` does NOT degrade, and the asymmetry is the point. Direction
    # decides it. Smudging wrong leaves a placeholder in a file on your
    # disk -- visible, local, fixable. Cleaning wrong writes one machine's
    # literal value into the shared repo, which is the whole failure this
    # filter exists to prevent. It passes content through only when that is
    # provably a no-op: byte-identical to what git already has.
    if yaml is None:
        if args == ["check"]:
            gate = secretguard.require_pyyaml(
                "pre-commit hook 'hostvars-placeholders' "
                "(scripts/hostvars_filter.py check)"
            )
            return 1 if gate else 0

        if args[:1] == ["smudge"] and len(args) == 2:
            secretguard.line(
                f"{args[1]} checked out with its {{{{ placeholders }}}} intact "
                f"-- no pyyaml to expand them. Details: bash "
                f"scripts/check_clone_setup.sh"
            )
            sys.stdout.write(sys.stdin.read())
            return 0

        if args[:1] == ["clean"] and len(args) == 2:
            path, raw = args[1], sys.stdin.read()
            if raw in (index_blob(path), head_blob(path)):
                sys.stdout.write(raw)
                return 0
            secretguard.block(
                "a per-machine value cannot be contracted back to a placeholder",
                problem="this file changed and there is no pyyaml to read "
                        ".hostvars.yaml, so this machine's literal value "
                        "would be committed in place of the placeholder and "
                        "every other machine would inherit it",
                file=path,
                needs="the pyyaml package for this python3",
                blocked_by="the hostvars clean filter (scripts/hostvars_filter.py)",
                fix="pip install pyyaml",
                if_stuck=f"git restore --staged {path} to leave it out of this "
                         f"commit -- the rest goes through",
                see="RUNBOOK.md, Per-machine config values",
            )
            return 1

        secretguard.block(
            "the hostvars filter cannot run: pyyaml is missing",
            problem="refresh and paths both read .hostvars.yaml and cannot "
                    "parse it",
            needs="the pyyaml package for this python3",
            blocked_by="scripts/hostvars_filter.py",
            fix="pip install pyyaml",
            see="bash scripts/check_clone_setup.sh",
        )
        return 1

    if args[:1] in (["clean"], ["smudge"]) and len(args) == 2:
        handler = clean if args[0] == "clean" else smudge
        sys.stdout.write(handler(args[1], sys.stdin.read()))
        return 0
    if args == ["refresh"]:
        try:
            return refresh()
        except LocalUnavailable as error:
            warn(f"{error}")
            return 1
    if args == ["check"]:
        return check()
    if args == ["paths"]:
        for path in load_config():
            print(path)
        return 0
    print(
        "usage: hostvars_filter.py clean|smudge <repo-relative-path>\n"
        "       hostvars_filter.py refresh|check|paths",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
