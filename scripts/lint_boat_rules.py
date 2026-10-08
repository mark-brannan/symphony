#!/usr/bin/env python3
"""Symphony-only repo lint rules. Safe to run anywhere, including CI.

The generic rules (declared filters configured, plaintext secrets
protectable) moved to the shared hook repo, mark-brannan/pre-commit-hooks,
as the `repo-hygiene` hook. What is left knows this repo's layout: SignalK
plugin configs and the frozen captain credentials under secrets/. Each rule
carries its incident in its docstring.

Host-state rules -- compiled artifacts, installed-file drift, port
ownership -- live in scripts/lint_host_state.py instead, because they need the
machine and would fail in CI for the wrong reason.

Scope: by default each rule looks only at what THIS commit stages. `--all`
checks everything and is what CI runs.

Usage:  python3 scripts/lint_boat_rules.py [--all] [--warn-only]

HYGIENE_COMMIT_RANGE=<base>..<head> makes rule_frozen_secrets_untouched diff
that range instead of the index -- CI's index is empty after checkout, so
without this it would pass vacuously regardless of what a push changed.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CI = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))

failures: list[str] = []
warnings: list[str] = []

SCOPE_ALL = False


def in_scope() -> set[str] | None:
    """What this run is allowed to look at: staged paths, or None for all.

    None means "everything is in scope" and is deliberately what both the
    --all flag and a failed `git diff` produce -- a broken git invocation
    must never silently narrow a guard to nothing.
    """
    return None if SCOPE_ALL else staged_paths()


def staged_paths() -> set[str] | None:
    """Repo-relative paths this commit stages, or None if git can't say.

    None means "scope unknown", and every caller then behaves as if
    everything is in scope. A broken git invocation must never be the thing
    that quietly switches a guard off.
    """
    result = subprocess.run(
        # -z, not --name-only alone: git quotes any path outside plain
        # ASCII (core.quotePath defaults on), so `caf\u00e9.md` came back as
        # a quoted display string and never matched a covered path. A guard
        # that silently drops a file from its own scope fails open, which is
        # the one direction these must not fail.
        #
        # --diff-filter=d: a staged deletion puts no content into git, so
        # it is never a finding -- and naming a deleted file in a "fix it
        # like this" message is just wrong.
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=d"],
        # Explicit UTF-8, not the locale's guess: git emits paths as UTF-8
        # bytes, and under LC_ALL=C with PEP 538 coercion off, text=True
        # decodes as ASCII and raises UnicodeDecodeError on `caf\u00e9.md`.
        # That crashed the guard with a traceback -- the exact failure this
        # whole change exists to stop. surrogateescape so a path that is
        # not valid UTF-8 either round-trips instead of exploding.
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape",
    )
    if result.returncode != 0:
        return None
    return {name for name in result.stdout.split("\0") if name}


def staged_blob(path: str) -> str | None:
    """Git's recorded text for `path`, or None if it can't be read.

    None means "fall back to the working tree" -- for an unstaged or
    untracked file there is nothing in the index to judge.
    """
    r = subprocess.run(
        ["git", "show", f":{path}"], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="surrogateescape",
    )
    return r.stdout if r.returncode == 0 else None


def fail(rule: str, msg: str) -> None:
    failures.append(f"{rule}: {msg}")


def warn(rule: str, msg: str) -> None:
    warnings.append(f"{rule}: {msg}")


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
    scope = in_scope()
    for cfg in sorted(cfg_dir.glob("*.json")):
        rel = str(cfg.relative_to(ROOT))
        if scope is not None and rel not in scope:
            continue  # warn about configs THIS commit touches, not all of them
        # Scoped runs read the INDEX, unscoped runs read disk -- the same
        # split as check_encoding_health, and for the same reason: if this
        # is a statement about your commit, it has to be about the bytes
        # your commit records, not whatever the working tree holds after
        # `git add -p`. Left inconsistent, the scope came from the index
        # and the content from disk.
        #
        # Safe for sops-covered configs: .sops.yaml's encrypted_regex
        # covers secret-shaped keys only (secretKey/password/token/...),
        # so the boolean flags this rule reads are cleartext in the index
        # too. If that regex ever widens to cover them, this rule would
        # stop seeing them -- silently, since an ENC[...] string is not
        # `is True`. Then it should move back to disk, deliberately.
        raw = staged_blob(rel) if scope is not None else None
        if raw is None:
            try:
                raw = cfg.read_text(encoding="utf-8")
            except OSError:
                continue
        try:
            doc = json.loads(raw)
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


# sops keys the owner has frozen. Not a general "secrets are sensitive" rule --
# these specific values are staged for a hardening pass he is doing himself, on
# his own schedule, and a session changing them ahead of that is unwanted work
# on a credential he still needs to be able to predict.
FROZEN_SECRET_KEYS = ("signalk_captain_password", "influxdb_captain_password")


def rule_frozen_secrets_untouched() -> None:
    """Some credentials are deliberately not ours to improve.

    The owner froze the captain credentials pending his own hardening work and
    asked, explicitly, that sessions stop offering to fix them. An offer is
    cheap to make and costs him the same judgement every time it recurs.

    This is a gate rather than a note because the note already existed. It lived
    in maintenance/priorities.md, phrased as a task, and read as an invitation to
    every session that opened the file -- which is exactly what prose does. His
    own standing orders say it: anything that must happen belongs in a hook, not
    in a document.

    Passes when there's no change to those keys; fails on a diff that
    touches one. Override needs a human deciding to, which is the point.

    Local pre-commit runs read the index (`git diff --cached`), since that's
    the diff about to be committed. CI has nothing staged after checkout, so
    that read is vacuously empty there -- this rule used to pass on every CI
    run regardless of what a push actually changed. HYGIENE_COMMIT_RANGE
    (set by the workflow, e.g. "<before>..<sha>") switches it to diffing
    that range instead, so CI checks the commits a push or PR actually
    introduces. An unusable range (shallow history, first push on a branch)
    warns and skips rather than failing the whole job over a range this
    rule can't evaluate.
    """
    commit_range = os.environ.get("HYGIENE_COMMIT_RANGE", "").strip()
    if commit_range:
        diff = subprocess.run(
            ["git", "diff", commit_range, "-U0", "--", "secrets/"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape",
        )
        if diff.returncode != 0:
            warn("frozen-secret-range",
                 f"couldn't diff {commit_range} ({diff.stderr.strip() or 'git error'}); "
                 f"frozen-secret check skipped for this run.")
            return
        staged = diff.stdout
    else:
        staged = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--", "secrets/"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape",
        ).stdout
    if not staged:
        return
    for line in staged.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        for key in FROZEN_SECRET_KEYS:
            if key in line:
                fail(
                    "frozen-secret",
                    f"this commit changes {key}, which the owner froze until "
                    f"his own hardening pass. Don't rotate, split, or "
                    f"strengthen it, and don't offer to. See the captain "
                    f"credentials item in maintenance/priorities.md.",
                )
                return


def main() -> int:
    global SCOPE_ALL
    warn_only = "--warn-only" in sys.argv
    SCOPE_ALL = "--all" in sys.argv
    for rule in (
        rule_audible_alarms_are_scoped,
        rule_frozen_secrets_untouched,
    ):
        rule()

    # Rules that use secretguard already produce a formatted block; the
    # short ones are one-liners and get the compact prefix.
    for w in warnings:
        print(w if "\n" in w else f"  warn  {w}")
    for f in failures:
        print(f if "\n" in f else f"  FAIL  {f}")

    if failures and not warn_only:
        scope_note = ("across the whole repo" if SCOPE_ALL
                      else "in what this commit stages")
        print(f"\nboat-rules: BLOCKED on {len(failures)} problem(s) "
              f"{scope_note}.")
        print("Each fix above includes a way out if you can't run it. Failing "
              "that, `git commit --no-verify` bypasses all hooks.")
        return 1
    if not failures and not warnings:
        print("boat rules: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
