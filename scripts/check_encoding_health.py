#!/usr/bin/env python3
"""Is anything on this box still going to mangle non-ASCII text?

Written after a script truncated maintenance/priorities.md on 2026-08-14. The
file was fine; the environment was not. `LANG=en_US` names a locale with no
codeset, so glibc falls back to ISO-8859-1, and Python inherits that as its
default for file I/O. Opening a UTF-8 document without an explicit encoding
reads it as latin-1 and writes latin-1 back -- which is how a degree sign or an
em dash becomes mojibake in a committed file, silently.

Three layers have to hold, and this checks all three:

  1. The files are actually UTF-8, and carry no mojibake already.
  2. The host has a UTF-8 locale generated AND selected.
  3. Running processes have picked it up -- the slow part, because a service
     keeps its environment until it restarts.

Layer 3 is why this script exists rather than a one-time fix. Changing
/etc/default/locale changes nothing for anything already running, so the fix
lands gradually and you want to watch it converge instead of assuming it did.

    python3 scripts/check_encoding_health.py            # everything
    python3 scripts/check_encoding_health.py --repo     # layer 1, all tracked files (CI)
    python3 scripts/check_encoding_health.py --staged   # layer 1, this commit only

Exit status is non-zero only for layer 1 failures -- real mojibake or a file
that isn't valid UTF-8. Host findings are reported, not enforced: this script
runs in CI too, where the locale is not the boat's problem to solve.

WHAT IS NOT ENOUGH, and why the layers are separate
---------------------------------------------------
Setting LANG alone is the fix people reach for and it is incomplete here:

  - en_US.UTF-8 must be *generated* (locale-gen) before it can be *selected*.
    Selecting an ungenerated locale silently falls back to C/POSIX.
  - LC_ALL overrides every other category. If it is set to a non-UTF-8 value,
    LANG is irrelevant. It should generally not be set system-wide at all.
  - systemd services do not read /etc/default/locale the way a login shell
    does, so a service can keep a stale locale across the change.
  - Node.js is UTF-8 internally regardless of locale, so SignalK is not at
    risk from this. Python is, which on this boat means OpenPlotter and the
    scripts in this directory.

The belt-and-braces answer for Python specifically is PYTHONUTF8=1 (PEP 540),
which forces UTF-8 regardless of what the locale says. Cheaper and safer than
relying on every caller to pass encoding= correctly.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# This script prints the mojibake markers it searches for, and one of them
# contains a euro sign. On the box this was written for, stdout is ISO-8859-1,
# so printing them raised UnicodeEncodeError and took the pre-commit hook down
# with it -- the checker defeated by the exact fault it exists to catch.
#
# Force UTF-8 on our own streams rather than trusting the environment. This is
# the same belt-and-braces the docstring recommends for everything else, and a
# tool that audits encoding has no business being the thing that gets it wrong.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent

# Byte sequences that mean UTF-8 text was already read as latin-1 and rewritten.
# Each is the latin-1 rendering of a common UTF-8 lead byte pair -- an accented
# letter, a curly quote, a degree sign. Finding one is evidence of past damage,
# not a risk of future damage.
#
# Written as escapes on purpose. Spelled literally, this file would contain the
# very sequences it searches for and would flag itself on every run. The
# alternative -- excluding this file from the scan -- is worse, because it would
# also hide real damage here.
MOJIBAKE_MARKERS = (
    "\u00c3",                          # lead byte of most latin-1-mangled accents
    "\u00e2\u20ac",                    # mangled curly punctuation
    "\u00c2\u00b0",                    # mangled degree sign
    "\u00e2\u20ac\u2122",              # mangled right single quote
    "\u00e2\u20ac\u009c",              # mangled left double quote
    "\ufeff",                          # byte-order mark: not damage, never wanted
)

UTF8_LOCALES = ("utf-8", "utf8")

# A document that EXPLAINS mojibake has to be able to show what it looks
# like. Without an opt-out the checker flags the explanation as damage --
# which it did, to reference/precommit_guards.md, on the first CI run after
# that file was written.
#
# Deliberately a whole-file downgrade to a warning rather than a silent
# exemption, and deliberately NOT extended to invalid UTF-8: an example can
# be mojibake on purpose, but no file is un-decodable on purpose. The
# marker has to be typed out, so it cannot be reached by accident, and the
# file still reports what it found -- you lose the block, not the visibility.
ALLOW_MARKER = "encoding-health: allow-mojibake"


def staged_paths():
    """Repo-relative paths in this commit, or None if git can't say.

    None means "scope unknown"; callers fall back to every tracked file, so
    a broken git invocation can never silently disable the check.
    """
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return {line for line in r.stdout.splitlines() if line}


def tracked_text_files(only=None):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    for name in out.split("\0"):
        if not name:
            continue
        if only is not None and name not in only:
            continue
        p = ROOT / name
        if not p.is_file():
            continue
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        if _is_binary(raw):
            continue
        yield p


# Control bytes that never appear in prose. Tab, newline and carriage return
# are the only ones that legitimately do.
_TEXT_CONTROL = {0x09, 0x0A, 0x0D}


def _is_binary(raw: bytes) -> bool:
    """Distinguish a data file from prose without maintaining a path list.

    A NUL byte is the classic test and it is not sufficient here: the repo
    carries bluetoothctl session captures that are hex dumps plus ANSI escape
    sequences plus raw device bytes, with no NUL anywhere. They are not
    mis-encoded text and flagging them as such is noise -- the kind that
    teaches you to skip the check.

    Anything carrying control characters beyond tab/newline/return is treated
    as data. A path allowlist would go stale the first time someone adds a
    capture in a new directory; this does not.
    """
    if b"\0" in raw[:8192]:
        return True
    sample = raw[:8192]
    return any(b < 0x20 and b not in _TEXT_CONTROL for b in sample)


def check_repo(only=None):
    """Layer 1: the files themselves.

    `only` limits the scan to the paths this commit stages. Unscoped, one
    file damaged by an old latin-1 round-trip blocks every commit in the
    repo forever, by someone who did not cause it and may not know how to
    fix it. CI runs the unscoped form, which is where whole-repo truth
    belongs.
    """
    bad_encoding, mojibake, allowed = [], [], []
    for p in tracked_text_files(only):
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            bad_encoding.append((p.relative_to(ROOT), str(e)[:60]))
            continue
        hits = [m for m in MOJIBAKE_MARKERS if m in text]
        if hits:
            target = allowed if ALLOW_MARKER in text else mojibake
            target.append((p.relative_to(ROOT), hits))

    scope = "staged files" if only is not None else "tracked files"
    print(f"layer 1 -- {scope}")
    for path, hits in allowed:
        print(f"   allowed: {path} contains mojibake {hits} and declares "
              f"'{ALLOW_MARKER}' -- treated as deliberate examples")
    if not bad_encoding and not mojibake:
        print(f"   ok: every scanned text file is valid UTF-8, no mojibake markers")
        return 0

    print("\nencoding-health: BLOCKED", file=sys.stderr)
    for path, err in bad_encoding:
        _report(path, f"not valid UTF-8 ({err})")
    for path, hits in mojibake:
        _report(path, f"contains mojibake markers {hits} -- UTF-8 text that "
                      f"was read as latin-1 and written back, mangling a "
                      f"character",
                extra=f"  deliberate example? Put this exact text somewhere in "
                      f"the file and it becomes a warning instead:\n"
                      f"           {ALLOW_MARKER}")
    return len(bad_encoding) + len(mojibake)


def _report(path, what, extra=None):
    """One finding, with a fix and an exit that needs nothing."""
    print(
        f"\n  file:  {path}\n"
        f"  what:  {what}\n"
        f"  fix:   rewrite it as UTF-8, then re-stage:\n"
        f"           python3 scripts/check_encoding_health.py --fix {path}\n"
        f"           git add {path}\n"
        f"  didn't cause it, or the fix looks wrong? Drop the file from this\n"
        f"         commit and the rest goes through:\n"
        f"           git restore --staged {path}\n"
        f"         Another session staged it? Leave it alone and use:\n"
        f"           SKIP=encoding-health git commit ...\n"
        f"  last resort, bypasses ALL hooks:  git commit --no-verify"
        + (f"\n{extra}" if extra else ""),
        file=sys.stderr,
    )


# Characters that a mojibake run can be built from: the latin-1 range plus
# the cp1252 punctuation that shows up when UTF-8 is misread through a
# Windows codepage (the em dash / curly quote cases). cp1252 is a superset
# of latin-1 over these, so encoding a run with it covers both origins.
_CP1252_EXTRAS = "\u20ac\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160" \
                 "\u2039\u0152\u017d\u2018\u2019\u201c\u201d\u2022\u2013\u2014" \
                 "\u02dc\u2122\u0161\u203a\u0153\u017e\u0178"
_MOJIBAKE_RUN = re.compile("[\u0080-\u00ff" + _CP1252_EXTRAS + "]+")


def repair_mojibake(text):
    """Undo a latin-1/cp1252 misread, run by run. Returns (text, n_repaired).

    Per-run, not whole-file, and that distinction is the whole point: a
    document can contain both real mojibake AND legitimate non-ASCII (an em
    dash, a degree sign in a spec). Re-encoding the entire file fails on the
    legitimate characters and repairs nothing -- which is exactly what the
    first cut of this function did, on the first real file it met.

    A run is only rewritten when it decodes cleanly as UTF-8, so text that
    merely contains an accented word is left untouched.
    """
    repaired = 0

    def convert(match):
        nonlocal repaired
        run = match.group(0)
        try:
            candidate = run.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return run
        repaired += 1
        return candidate

    return _MOJIBAKE_RUN.sub(convert, text), repaired


def fix_file(rel):
    """Re-encode one file to UTF-8, undoing a latin-1 round-trip.

    Element 4 of the message contract has to be a command that exists. It
    did not before: the check named the damage and left the reader to work
    out the repair by hand.
    """
    p = (ROOT / rel).resolve()
    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Not UTF-8 at all: decode as latin-1 (never fails) and re-encode.
        p.write_bytes(raw.decode("latin-1").encode("utf-8"))
        print(f"rewrote {rel} as UTF-8 (was latin-1)")
        return 0

    if not any(m in text for m in MOJIBAKE_MARKERS):
        print(f"{rel} is already clean UTF-8; nothing to fix", file=sys.stderr)
        return 1

    result, count = repair_mojibake(text.replace("\ufeff", ""))
    leftover = [m for m in MOJIBAKE_MARKERS if m in result]
    if leftover:
        print(
            f"{rel}: repaired {count} run(s), but markers {leftover} remain -- "
            f"this is not a plain encoding round-trip and guessing further "
            f"would risk corrupting real text. Inspect it, or restore the file "
            f"from a known-good commit:\n"
            f"  git log --oneline -- {rel}\n"
            f"  git checkout <good-sha> -- {rel}",
            file=sys.stderr,
        )
        return 1
    p.write_text(result, encoding="utf-8")
    print(f"repaired {count} damaged run(s) in {rel}")
    return 0


def _generated_locales():
    out = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def check_host():
    """Layer 2: is a UTF-8 locale generated and selected?"""
    print("\nlayer 2 -- host locale")
    generated = _generated_locales()
    utf8_available = [l for l in generated
                      if any(u in l.lower() for u in UTF8_LOCALES)]
    print(f"   generated UTF-8 locales: {utf8_available or 'NONE'}")
    if not utf8_available:
        print("   FINDING no UTF-8 locale is generated. Selecting one would "
              "silently fall back to C/POSIX. Run locale-gen first.")

    conf = Path("/etc/default/locale")
    if conf.is_file():
        for line in conf.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith(("LANG=", "LC_ALL=", "LANGUAGE=")):
                is_utf8 = any(u in line.lower() for u in UTF8_LOCALES)
                flag = "ok " if is_utf8 else "not UTF-8"
                print(f"   {conf}: {line}   [{flag}]")
                if line.startswith("LC_ALL=") :
                    print("   FINDING LC_ALL is set system-wide. It overrides every "
                          "other category, so LANG cannot fix anything while it "
                          "disagrees. Prefer unsetting it entirely.")

    py = sys.getfilesystemencoding()
    print(f"   this python's filesystem encoding: {py}"
          + ("" if any(u in py.lower() for u in UTF8_LOCALES)
             else "   <-- non-UTF-8, this is the trap"))
    if os.environ.get("PYTHONUTF8") == "1":
        print("   PYTHONUTF8=1 is set, which forces UTF-8 regardless of locale")


def check_processes():
    """Layer 3: how far has the change actually propagated?

    Reads each process's own environment rather than the system default,
    because that is the thing that decides behaviour. Counts down to zero as
    services restart, which is the progression worth watching.
    """
    print("\nlayer 3 -- running processes")
    stale, total, unreadable = [], 0, 0
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            env = (pid_dir / "environ").read_bytes().decode("utf-8", "replace")
        except (OSError, PermissionError):
            unreadable += 1
            continue
        entries = dict(e.split("=", 1) for e in env.split("\0") if "=" in e)
        locale_vars = {k: v for k, v in entries.items()
                       if k in ("LANG", "LC_ALL", "LC_CTYPE")}
        if not locale_vars:
            continue
        total += 1
        if not any(any(u in v.lower() for u in UTF8_LOCALES)
                   for v in locale_vars.values()):
            try:
                comm = (pid_dir / "comm").read_text().strip()
            except OSError:
                comm = "?"
            stale.append((pid_dir.name, comm, locale_vars.get("LANG", "")))

    print(f"   processes declaring a locale: {total}"
          + (f"   (+{unreadable} unreadable without root)" if unreadable else ""))
    print(f"   still on a non-UTF-8 locale: {len(stale)}")
    for pid, comm, lang in sorted(stale, key=lambda r: r[1])[:20]:
        print(f"      {pid:>8}  {comm:<24} LANG={lang}")
    if len(stale) > 20:
        print(f"      ... and {len(stale) - 20} more")
    if stale:
        print("   These keep their environment until they restart. Expect this "
              "count to fall, not to drop to zero at once.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="store_true",
                    help="all tracked files; skip host and process checks (CI)")
    ap.add_argument("--staged", action="store_true",
                    help="only files this commit stages (pre-commit)")
    ap.add_argument("--fix", metavar="PATH",
                    help="rewrite one file as UTF-8, repairing a latin-1 round-trip")
    args = ap.parse_args()

    if args.fix:
        return fix_file(args.fix)

    only = staged_paths() if args.staged else None
    if args.staged and only is not None and not only:
        print("layer 1 -- staged files\n   ok: this commit stages no text file.")
        return 0
    failures = check_repo(only)
    if not (args.repo or args.staged):
        check_host()
        check_processes()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
