#!/usr/bin/env python3
"""Python twin of scripts/secretguard.sh -- same mode, same message shape.

Guards in this repo exist in both languages (lint_repo_hygiene.py and
sops_filter.py in python, the pre-commit shell guards in bash), and a
contributor should not be able to tell which one stopped them. Both
implementations resolve mode by the rules documented in the shell file and
format messages identically; scripts/test_secretguard.py asserts they
still agree.

The invariant every caller is composing against
-----------------------------------------------

    Enforcement may soften a guard about your ENVIRONMENT.
    It may never soften a guard about the CONTENT of your commit.

Environment is a fact about this clone -- no age key, filters unwired,
pyyaml missing. Strict blocks on it, contributor warns, and a contributor
can still commit a typo fix in a markdown file. Content is what is in the
index right now: a plaintext secret staged for a public repo is the same
incident whoever commits it, so it blocks in every mode.

Which is why `require()` and `block()` are separate calls rather than one
with a severity argument. A guard about content calls `block`; only a guard
about capability calls `require`. Where both axes apply -- as in
lint_repo_hygiene's unconfigured-filter rule -- they compose as

    blocking = <this commit stages a covered path> or <mode is strict>

Read it as the pass condition and the ambiguity goes away: it passes only
when nothing covered is staged AND enforcement is not strict. Both axes
have to clear it, and neither can wave the other through. (Saying "an AND"
next to an `or` has already misled one reader; the boolean is an OR of the
two blocking triggers, which is the same thing as an AND of the two pass
conditions.)

Written down here because two sessions derived this independently and very
nearly composed it the other way, which would have let contributor mode
wave a staged plaintext secret through.

Deliberately stdlib-only. It is on the path a clone takes when pyyaml is
what's missing, so it cannot import yaml.

Usage as a library:

    import secretguard
    if secretguard.require("...", problem=..., fix=...):
        return 1          # strict: the guard should fail
                          # contributor: warning already printed, carry on

Usage from the shell (for scripts and for debugging):

    python3 scripts/secretguard.py mode
    python3 scripts/secretguard.py reason
"""
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODE_FILE = os.path.join(REPO, ".secretguard-mode")

MODES = ("strict", "contributor")

# Fixed print order. Anything not here is a caller bug, not a new field.
FIELD_LABELS = (
    ("problem", "problem:   "),
    ("file", "file:      "),
    ("needs", "needs:     "),
    ("blocked_by", "blocked by:"),
    ("fix", "fix:       "),
    ("if_stuck", "if stuck:  "),
    ("see", "see:       "),
)

# --- is this file actually a sops document? ---------------------------------
#
# Every guard that decides "this covered file is safe to commit" answers it
# by looking at the file, not by decrypting it -- decryption needs a key the
# contributor path does not have. The cheap version of that test is "does
# the text contain the word sops", and the cheap version is wrong: a
# plaintext `{"note": "sops", "password": "hunter2"}` passes it and every
# guard downstream then treats a live credential as encrypted. That is a
# false negative on the one class of check whose whole job is to have no
# false negatives.
#
# So: require the shape of sops' own metadata block, not the string. sops
# writes a `sops` key whose value is a mapping carrying at least `mac` and
# `version`, in both output forms. A file that carries all three by accident
# is not a shape anyone types by hand.
#
# The bash twin (secretguard_is_sops_encrypted) applies the same rule with
# grep, and the parity test runs both over a shared fixture list.
_SOPS_JSON_KEY = re.compile(r'"sops"\s*:\s*\{')
_SOPS_JSON_MAC = re.compile(r'"mac"\s*:')
_SOPS_JSON_VERSION = re.compile(r'"version"\s*:')
_SOPS_YAML_KEY = re.compile(r"^sops:\s*$", re.M)
_SOPS_YAML_MAC = re.compile(r"^\s+mac:", re.M)
_SOPS_YAML_VERSION = re.compile(r"^\s+version:", re.M)


def is_sops_encrypted(text):
    """True only for text carrying a real sops metadata block."""
    if _SOPS_JSON_KEY.search(text):
        return bool(_SOPS_JSON_MAC.search(text)) and bool(
            _SOPS_JSON_VERSION.search(text)
        )
    if _SOPS_YAML_KEY.search(text):
        return bool(_SOPS_YAML_MAC.search(text)) and bool(
            _SOPS_YAML_VERSION.search(text)
        )
    return False


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


# git runs filters from whatever spawned git, and that is often not a login
# shell -- an IDE, a GUI client, an agent harness. Those inherit a bare PATH
# without ~/.local/bin, so `which("sops")` misses on a machine that has sops
# installed and working. In strict mode a missing sops is fatal, and a fatal
# smudge takes the whole checkout down with it, so resolving by PATH alone
# turns "your shell config differs" into "git worktree add fails".
# Kept unexpanded: this doubles as the text of the `needs:` line, where
# "~/.local/bin" is what a reader recognises, and expanding at lookup time
# means a changed HOME is honoured rather than frozen at import.
_SOPS_DIRS = (
    "~/.local/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    "/bin",
)


def find_sops():
    """Absolute path to a runnable sops, or "" if there isn't one."""
    found = shutil.which("sops")
    if found:
        return found
    for directory in _SOPS_DIRS:
        candidate = os.path.join(os.path.expanduser(directory), "sops")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return ""


def sops_locations():
    """Everywhere find_sops looks, phrased for a `needs:` line.

    One source for the text so a diagnostic cannot tell you to put sops
    somewhere the resolver does not actually look, or omit somewhere it does.
    """
    return "sops on PATH or in " + ", ".join(_SOPS_DIRS)


def can_decrypt():
    """This machine can open the encrypted store: runnable sops AND an age key.

    Deliberately a separate question from mode(). Strict answers "how
    rigorously to enforce"; it does not answer "does this machine hold
    keys" -- CI is strict unconditionally while carrying no key at all, by
    design. Code that needs to actually decrypt asks this; code deciding
    block-vs-warn asks mode(). Reading `mode() == "strict"` as "keys exist
    here" is the conflation that made test_pseudonymize demand a key from a
    keyless runner. The shell twin is secretguard_can_decrypt.
    """
    return bool(find_sops()) and _have_age_key()


def _filters_configured():
    return bool(_git_config("filter.sops.clean"))


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

    # CI first, and unconditionally: "CI is always strict" only holds if
    # nothing downstream can downgrade it, including an explicit override a
    # workflow sets for an unrelated reason. The shell twin resolves in the
    # same order.
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        _resolved = ("strict", "CI")
        return _resolved

    raw = os.environ.get("SECRETGUARD_MODE", "")
    word = raw.strip().lower()
    if word in MODES:
        _resolved = (word, "SECRETGUARD_MODE=%s" % word)
        return _resolved
    if word:
        sys.stderr.write(
            "secretguard: ignoring SECRETGUARD_MODE=%s "
            "(expected strict or contributor)\n" % raw
        )

    word = _read_mode_file()
    if word in MODES:
        _resolved = (word, ".secretguard-mode says %s" % word)
        return _resolved
    if word:
        sys.stderr.write(
            "secretguard: ignoring .secretguard-mode value %s "
            "(expected strict or contributor)\n" % word
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


def format(level, title, **fields):  # noqa: A001 -- mirrors secretguard_msg
    """The one message shape. `file` may be a str or a list of str."""
    current, why = resolve()
    lines = ["", "secretguard %s: %s" % (level, title)]
    for key, label in FIELD_LABELS:
        value = fields.pop(key, None)
        if not value:
            continue
        for item in value if isinstance(value, (list, tuple)) else [value]:
            lines.append("  %s %s" % (label, item))
    for unknown in fields:
        sys.stderr.write("secretguard.format: unknown field %s\n" % unknown)
    lines.append("  mode:       %s (%s)" % (current, why))
    return "\n".join(lines)


def _dest():
    """Where a guard message goes -- see the same helper in the shell twin.

    pre-commit captures stderr and shows it only when a hook FAILS, so a
    degraded-but-passing guard's `mode:` line would never reach anyone. If
    stderr isn't a terminal but one is attached, write straight to it. One
    destination, never both.
    """
    # An in-process redirect of sys.stderr (contextlib.redirect_stderr, a
    # test harness, a caller collecting output) is a deliberate instruction
    # about where this text goes. Honour it before considering /dev/tty:
    # otherwise the message escapes the capture, lands on whatever terminal
    # happens to be attached, and the caller sees nothing. That is not
    # hypothetical -- it made this module's own tests pass on a machine with
    # no controlling terminal (CI) and fail on a developer's laptop, with the
    # guard blocks printed into an unrelated commit's hook output.
    if sys.stderr is not sys.__stderr__:
        return sys.stderr
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
    _write("secretguard note [%s]: %s\n" % (mode(), text))


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
    sys.stderr.write("usage: secretguard.py {mode|reason}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
