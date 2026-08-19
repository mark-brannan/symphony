#!/usr/bin/env python3
"""Python twin of scripts/symphony_mode.sh -- same mode, same message shape.

Guards in this repo exist in both languages (lint_repo_hygiene.py and
hostvars_filter.py in python, the pre-commit shell guards in bash), and a
contributor should not be able to tell which one stopped them. Both
implementations resolve mode by the rules documented in the shell file and
format messages identically; scripts/test_symphony_mode.py asserts they
still agree.

Deliberately stdlib-only. It is on the path a clone takes when pyyaml is
what's missing, so it cannot import yaml.

Usage as a library:

    import symphony_mode
    if symphony_mode.require("...", problem=..., fix=...):
        return 1          # strict: the guard should fail
                          # contributor: warning already printed, carry on

Usage from the shell (for scripts and for debugging):

    python3 scripts/symphony_mode.py mode
    python3 scripts/symphony_mode.py reason
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODE_FILE = os.path.join(REPO, ".symphony-mode")

STRICT_WORDS = {"1", "true", "yes", "on", "strict"}
CONTRIBUTOR_WORDS = {"0", "false", "no", "off", "contributor"}

# Fixed print order. Anything not here is a caller bug, not a new field.
FIELD_LABELS = (
    ("problem", "problem:   "),
    ("file", "file:      "),
    ("needs", "needs:     "),
    ("blocked_by", "blocked by:"),
    ("fix", "fix:       "),
    ("see", "see:       "),
)

_resolved = None


def _git_config(name):
    try:
        out = subprocess.run(
            ["git", "config", "--get", name],
            cwd=REPO, capture_output=True, text=True,
        )
    except OSError:
        return ""
    return out.stdout.strip()


def _have_age_key():
    env = os.environ.get("SOPS_AGE_KEY_FILE")
    if env and os.path.isfile(env):
        return True
    return os.path.isfile(
        os.path.join(os.path.expanduser("~"), ".config", "sops", "age", "keys.txt")
    )


def have_age_key():
    """Public: callers outside this module ask this, not the private form."""
    return _have_age_key()


def _filters_configured():
    return bool(_git_config("filter.sops.clean")) and bool(
        _git_config("filter.hostvars.clean")
    )


def _read_mode_file():
    try:
        with open(MODE_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                return line.split()[0].lower()
    except OSError:
        pass
    return ""


def resolve():
    """(mode, reason). Cached: mode cannot change mid-process."""
    global _resolved
    if _resolved is not None:
        return _resolved

    raw = os.environ.get("SYMPHONY_STRICT", "")
    lowered = raw.strip().lower()
    if lowered in STRICT_WORDS:
        _resolved = ("strict", "SYMPHONY_STRICT=%s" % raw)
        return _resolved
    if lowered in CONTRIBUTOR_WORDS:
        _resolved = ("contributor", "SYMPHONY_STRICT=%s" % raw)
        return _resolved
    if lowered:
        sys.stderr.write(
            "symphony: ignoring unrecognized SYMPHONY_STRICT=%s\n" % raw
        )

    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        _resolved = ("strict", "CI")
        return _resolved

    word = _read_mode_file()
    if word in ("strict", "contributor"):
        _resolved = (word, ".symphony-mode says %s" % word)
        return _resolved
    if word:
        sys.stderr.write(
            "symphony: ignoring unrecognized .symphony-mode value %s\n" % word
        )

    key, filters = _have_age_key(), _filters_configured()
    if key and filters:
        _resolved = (
            "strict",
            "auto-detected: age key available, git filters configured",
        )
    else:
        missing = []
        if not key:
            missing.append("no age key")
        if not filters:
            missing.append("git filters not configured")
        _resolved = ("contributor", "auto-detected: " + ", ".join(missing))
    return _resolved


def mode():
    return resolve()[0]


def reason():
    return resolve()[1]


def format(level, title, **fields):  # noqa: A001 -- mirrors symphony_msg
    """The one message shape. `file` may be a str or a list of str."""
    current, why = resolve()
    lines = ["", "symphony %s: %s" % (level, title)]
    for key, label in FIELD_LABELS:
        value = fields.pop(key, None)
        if not value:
            continue
        for item in value if isinstance(value, (list, tuple)) else [value]:
            lines.append("  %s %s" % (label, item))
    for unknown in fields:
        sys.stderr.write("symphony_mode.format: unknown field %s\n" % unknown)
    lines.append("  mode:       %s (%s)" % (current, why))
    return "\n".join(lines)


def _dest():
    """Where a guard message goes -- see the same helper in the shell twin.

    pre-commit captures stderr and shows it only when a hook FAILS, so a
    degraded-but-passing guard's `mode:` line would never reach anyone. If
    stderr isn't a terminal but one is attached, write straight to it. One
    destination, never both.
    """
    try:
        if sys.stderr.isatty():
            return sys.stderr
        return open("/dev/tty", "w", encoding="utf-8")
    except OSError:
        return sys.stderr


def _write(text):
    out = _dest()
    try:
        out.write(text)
        out.flush()
    finally:
        if out is not sys.stderr:
            out.close()


def emit(level, title, **fields):
    _write(format(level, title, **fields) + "\n")


def require(title, **fields):
    """A capability this guard wants.

    Returns True in strict mode (caller should fail) after printing a
    BLOCKED message; returns False in contributor mode after printing a
    warning, so the commit proceeds and CI stays the enforcement boundary.
    """
    if mode() == "strict":
        emit("BLOCKED", title, **fields)
        return True
    emit("warning", title, **fields)
    return False


def block(title, **fields):
    """Not negotiable in any mode. Always returns True (caller must fail)."""
    emit("BLOCKED", title, **fields)
    return True


def note(title, **fields):
    emit("note", title, **fields)
    return False


def line(text):
    """One-line note, for code that runs once per file.

    The git clean/smudge filters are invoked per covered file -- thirteen
    times on a checkout -- so the full block below would bury a clone in
    output. Still names the mode: nothing here is allowed to be silent
    about which mode produced it.
    """
    _write("symphony note [%s]: %s\n" % (mode(), text))


def require_pyyaml(hook):
    """Shared by every entry point that parses YAML.

    pyyaml is not in the stdlib, so `import yaml` at the top of a guard
    turns "this laptop has no pyyaml" into a traceback that fails a commit
    for a reason unrelated to the commit. Returns True if the caller should
    fail (strict, or CI), False if it should skip its check and let the
    commit through.
    """
    try:
        import yaml  # noqa: F401
    except ImportError:
        return require(
            "a check needs pyyaml and this clone hasn't got it",
            problem="this check parses YAML, and python3 cannot import yaml",
            needs="the pyyaml package for this python3",
            blocked_by=hook,
            fix="pip install pyyaml",
            see="bash scripts/check_clone_setup.sh",
        )
    return None


def main(argv):
    if len(argv) == 2 and argv[1] == "mode":
        print(mode())
        return 0
    if len(argv) == 2 and argv[1] == "reason":
        print(reason())
        return 0
    sys.stderr.write("usage: symphony_mode.py {mode|reason}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
