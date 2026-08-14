#!/usr/bin/env python3
"""Repo-only lint rules. Safe to run anywhere, including CI.

Each rule here exists because its absence already cost real time on this
boat. They are deliberately generic: none of them know anything about
Symphony's layout beyond which files to read.

Host-state rules -- compiled artifacts, installed-file drift, port
ownership -- live in scripts/lint_host_state.py instead, because they need the
machine and would fail in CI for the wrong reason.

Usage:  python3 scripts/lint_repo_hygiene.py [--warn-only]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))

failures: list[str] = []
warnings: list[str] = []


def fail(rule: str, msg: str) -> None:
    failures.append(f"{rule}: {msg}")


def warn(rule: str, msg: str) -> None:
    warnings.append(f"{rule}: {msg}")


def rule_declared_filters_are_configured() -> None:
    """A .gitattributes filter that git doesn't have configured is a trap.

    The declared transform silently does not happen: content the repo says
    is encrypted-on-commit goes in as plaintext, and nothing says so. This
    is not a sops rule -- it applies identically to git-lfs, git-crypt, or
    any clean/smudge pair.

    Found unconfigured on the boat Pi on 2026-08-14, in a public repo.

    Skipped in CI, which legitimately has no filters: CI never commits, and
    a fresh checkout is expected to lack them.
    """
    ga = ROOT / ".gitattributes"
    if CI or not ga.exists():
        return
    declared = set()
    for line in ga.read_text(encoding="utf-8").splitlines():
        for m in re.finditer(r"(?:^|\s)filter=(\S+)", line):
            declared.add(m.group(1))
    for name in sorted(declared):
        clean = subprocess.run(
            ["git", "config", "--get", f"filter.{name}.clean"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip()
        if not clean:
            fail(
                "unconfigured-filter",
                f".gitattributes declares filter={name} but "
                f"filter.{name}.clean is not set in git config. Files it "
                f"covers would commit UNTRANSFORMED. Fix: "
                f"bash scripts/setup-git-filters.sh",
            )


# Deliberately NOT here: "config file for a plugin that isn't installed".
#
# It looks like a repo rule and isn't. SignalK names a config file after the
# plugin's id, which is not derivable from the package name -- charts.json
# comes from @signalk/charts-plugin, venus.json from signalk-venus-plugin,
# open-meteo.json from @signalk/open-meteo-provider. A first cut of this rule
# guessed the mapping by stripping prefixes and suffixes and reported 14 false
# positives out of 16. A linter that cries wolf gets skipped, which costs more
# than never having written it.
#
# The check is worth having, so it lives in scripts/lint_host_state.py, which can ask
# the running server which plugin ids actually exist instead of inferring them.


# Keys whose value being large or unbounded means "a lot of alarms".
_SCOPE_KEYS = ("states", "regions", "areas", "zones", "countries")


def rule_audible_alarms_are_scoped() -> None:
    """Sound + unbounded scope is how a notification storm starts.

    signalk-noaa-weather was set to notificationStates "WA" -- every NWS
    alert for an entire US state, polled every 60s, each playing a sound.
    On 2026-08-13 that starved the Pi until the hardware watchdog reset it,
    twice. The plugin was working exactly as configured.
    """
    cfg_dir = ROOT / "signalk" / "plugin-config-data"
    if not cfg_dir.is_dir():
        return
    for cfg in sorted(cfg_dir.glob("*.json")):
        try:
            doc = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        conf = doc.get("configuration")
        if not isinstance(conf, dict):
            continue
        sound = any(
            k.lower().endswith("sound") and v is True
            for k, v in conf.items()
            if isinstance(v, bool)
        )
        if not sound:
            continue
        scoped = [
            f"{k}={v!r}"
            for k, v in conf.items()
            if any(s in k.lower() for s in _SCOPE_KEYS)
            and isinstance(v, (str, list))
            and v
        ]
        if scoped:
            warn(
                "unscoped-audible-alarm",
                f"{cfg.relative_to(ROOT)} plays sound over a broad scope "
                f"({', '.join(scoped)}). Confirm this cannot raise many "
                f"simultaneous notifications; each one may spawn a player.",
            )


def main() -> int:
    warn_only = "--warn-only" in sys.argv
    for rule in (
        rule_declared_filters_are_configured,
        rule_audible_alarms_are_scoped,
    ):
        rule()

    for w in warnings:
        print(f"  warn  {w}")
    for f in failures:
        print(f"  FAIL  {f}")

    if failures and not warn_only:
        print(f"\n{len(failures)} problem(s). See scripts/lint_repo_hygiene.py "
              f"for why each rule exists.")
        return 1
    if not failures and not warnings:
        print("repo hygiene: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
