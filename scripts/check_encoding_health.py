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
    python3 scripts/check_encoding_health.py --repo     # layer 1 only (CI-safe)

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


def tracked_text_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    for name in out.split("\0"):
        if not name:
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


def check_repo():
    """Layer 1: the files themselves."""
    bad_encoding, mojibake = [], []
    for p in tracked_text_files():
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            bad_encoding.append((p.relative_to(ROOT), str(e)[:60]))
            continue
        hits = [m for m in MOJIBAKE_MARKERS if m in text]
        if hits:
            mojibake.append((p.relative_to(ROOT), hits))

    print("layer 1 -- tracked files")
    if not bad_encoding and not mojibake:
        print("   ok: every tracked text file is valid UTF-8, no mojibake markers")
    for path, err in bad_encoding:
        print(f"   FAIL not valid UTF-8: {path} ({err})")
    for path, hits in mojibake:
        print(f"   FAIL mojibake markers {hits} in {path}")
    return len(bad_encoding) + len(mojibake)


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
                    help="check tracked files only; skip host and process checks")
    args = ap.parse_args()

    failures = check_repo()
    if not args.repo:
        check_host()
        check_processes()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
