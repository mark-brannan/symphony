#!/usr/bin/env python3
"""Repo-only lint rules. Safe to run anywhere, including CI.

Each rule here exists because its absence already cost real time on this
boat. They are deliberately generic: none of them know anything about
Symphony's layout beyond which files to read.

Host-state rules -- compiled artifacts, installed-file drift, port
ownership -- live in scripts/lint_host_state.py instead, because they need the
machine and would fail in CI for the wrong reason.

Scope: by default each rule looks only at what THIS commit stages, because
a hook that blocks on repo-wide state punishes whoever commits next rather
than whoever caused it. `--all` checks everything and is what CI runs.

Usage:  python3 scripts/lint_repo_hygiene.py [--all] [--warn-only]
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import secretguard  # noqa: E402  -- needs the sys.path line above

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


def _fnmatch_any(path: str, patterns) -> bool:
    """.gitattributes patterns are globs, and a bare `*.sops.yaml` is
    matched against the basename as git does, not just the full path."""
    from fnmatch import fnmatch
    return any(fnmatch(path, pat) or fnmatch(os.path.basename(path), pat)
               for pat in patterns)


def staged_paths() -> set[str] | None:
    """Repo-relative paths this commit stages, or None if git can't say.

    None means "scope unknown", and every caller then behaves as if
    everything is in scope. A broken git invocation must never be the thing
    that quietly switches a guard off.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return {line for line in result.stdout.splitlines() if line}


def gitattributes_filters() -> dict[str, list[str]]:
    """{filter name: [paths it covers]}, straight out of .gitattributes.

    Read here rather than from .sops.yaml so these rules keep working with
    no pyyaml -- which is exactly the clone they most need to work on.
    """
    ga = ROOT / ".gitattributes"
    declared: dict[str, list[str]] = {}
    if not ga.exists():
        return declared
    for line in ga.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for match in re.finditer(r"(?:^|\s)filter=(\S+)", line):
            declared.setdefault(match.group(1), []).append(line.split()[0])
    return declared


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
    if CI or not (ROOT / ".gitattributes").exists():
        return

    declared = gitattributes_filters()
    scope = in_scope()
    for name in sorted(declared):
        clean = subprocess.run(
            ["git", "config", "--get", f"filter.{name}.clean"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip()
        if clean:
            continue

        # Two axes, composed as AND -- this is the one place PR #12's and
        # #13's reworks of this rule could have cancelled each other out.
        #
        #   MODE  says who is committing        (contributor / strict)
        #   SCOPE says what is in this commit   (does it stage a covered path)
        #
        # The invariant, agreed across both:
        #   enforcement may soften a guard about your ENVIRONMENT;
        #   it may never soften one about the CONTENT of your commit.
        #
        # So a staged covered path BLOCKS in every mode, contributor
        # included -- that is the 2026-08-14 incident (plaintext secrets into
        # a public repo) and it is content. An unconfigured filter with
        # nothing covered staged is environment: strict blocks, contributor
        # warns, and a contributor can still commit a markdown typo fix.
        #
        # Taking either axis alone loses something real: mode alone lets a
        # contributor stage a plaintext secret with only a warning here;
        # scope alone stops strict mode complaining about a clone that isn't
        # wired up yet.
        #
        # scope is None means "everything" -- --all, or a git call that
        # failed. Both must widen the rule, never narrow it to nothing.
        hits = sorted(declared[name]) if scope is None else sorted(
            p for p in scope if _fnmatch_any(p, declared[name])
        )
        blocking = bool(hits) or secretguard.mode() == "strict"

        if hits:
            first = hits[0]
            message = secretguard.format(
                "BLOCKED",
                "this commit stages a file whose git filter isn't configured",
                problem=f".gitattributes routes it through filter={name}, but "
                        f"filter.{name}.clean is unset in this clone, so it "
                        f"would be committed UNTRANSFORMED -- for filter=sops, "
                        f"that means in plaintext",
                file=hits,
                needs=f"filter.{name}.clean in this clone's .git/config",
                blocked_by="pre-commit hook 'repo-hygiene' "
                           "(scripts/lint_repo_hygiene.py)",
                fix="bash scripts/setup-git-filters.sh, then: "
                    f"git add --renormalize {first}",
                if_stuck="no sops or age key here, or you didn't stage it? Take "
                         "it out of this commit and everything else goes "
                         f"through: git restore --staged {first} -- or commit "
                         "only your own paths: git commit -m ... -- <your "
                         "paths>. Last resort: SKIP=repo-hygiene git commit ...",
                see="README.md, Setup -- or bash scripts/check_clone_setup.sh",
            )
        else:
            message = secretguard.format(
                "BLOCKED" if blocking else "warning",
                "a declared git filter is not configured in this clone",
                problem=f".gitattributes declares filter={name} and "
                        f"filter.{name}.clean is unset. Nothing in this commit "
                        f"is covered by it, so nothing is at risk right now",
                needs=f"filter.{name}.clean in this clone's .git/config",
                blocked_by="pre-commit hook 'repo-hygiene' "
                           "(scripts/lint_repo_hygiene.py)",
                fix="bash scripts/setup-git-filters.sh, before you commit a "
                    "covered file",
                if_stuck="SKIP=repo-hygiene git commit ...   (last resort: "
                         "git commit --no-verify)",
                see="README.md, Setup -- or bash scripts/check_clone_setup.sh",
            )
        (failures if blocking else warnings).append(message)


def rule_plaintext_secrets_are_protectable() -> None:
    """Secrets sitting in the clear on a machine that cannot re-encrypt them.

    Every other check here fires when you touch something. This one is about
    a standing condition, and it is the one that fails late otherwise: a
    machine that HAD a key and lost it -- sops uninstalled, keys.txt gone,
    SOPS_AGE_KEY_FILE unset in a new shell -- has real secrets decrypted on
    disk and no way to put them back. Nothing says so until someone happens
    to stage one of those files, which may be days later and may be a
    `git add .`.

    So: check the state, not the operation, and say it on the first commit.

    Cannot false-positive on a keyless contributor clone, which is the case
    it must not annoy -- there the covered files are still ciphertext, so
    there is nothing in the clear to protect. It takes both halves.
    """
    if CI:
        return  # a fresh checkout is ciphertext by definition
    covered = gitattributes_filters().get("sops", [])
    if not covered:
        return

    missing = []
    if shutil.which("sops") is None:
        missing.append("sops on PATH")
    if not secretguard.have_age_key():
        missing.append("an age key (~/.config/sops/age/keys.txt, or SOPS_AGE_KEY_FILE)")
    if not missing:
        return

    exposed = []
    for rel in covered:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Both output forms, and the metadata shape rather than the word --
        # see secretguard.is_sops_encrypted. Getting this wrong is bad in
        # both directions: too loose and a plaintext file mentioning sops
        # reads as encrypted, too tight and an encrypted YAML file reads as
        # plaintext and blocks every commit.
        if not secretguard.is_sops_encrypted(text):
            exposed.append(rel)
    if not exposed:
        return

    failures.append(secretguard.format(
        "BLOCKED",
        "decrypted secrets are on disk and this machine cannot re-encrypt them",
        problem="these files hold real credentials in the clear right now, and "
                "nothing here can put them back. Any commit is one `git add .` "
                "away from publishing them, so this blocks every commit rather "
                "than waiting for the one that stages them",
        file=exposed,
        needs=", ".join(missing),
        blocked_by="pre-commit hook 'repo-hygiene' (scripts/lint_repo_hygiene.py)",
        fix="restore what 'needs' lists, then: bash scripts/setup-git-filters.sh",
        if_stuck="if the plaintext is stale rather than live, delete those files "
                 "and `git checkout --` them to get the encrypted form back. To "
                 "commit anyway: SKIP=repo-hygiene git commit ... (CI's gitleaks "
                 "and trufflehog passes still run on a PR)",
        see="bash scripts/check_clone_setup.sh",
    ))


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
        if scope is not None and str(cfg.relative_to(ROOT)) not in scope:
            continue  # warn about configs THIS commit touches, not all of them
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

    Passes when the working tree is clean of changes to those keys; fails on a
    staged diff that touches one. Override needs a human deciding to, which is
    the point.
    """
    staged = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--", "secrets/"],
        cwd=ROOT, capture_output=True, text=True,
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
        rule_declared_filters_are_configured,
        rule_plaintext_secrets_are_protectable,
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
        print(f"\nrepo-hygiene: BLOCKED on {len(failures)} problem(s) "
              f"{scope_note}.")
        print("Each fix above includes a way out if you can't run it. Failing "
              "that, `git commit --no-verify` bypasses all hooks.")
        return 1
    if not failures and not warnings:
        print("repo hygiene: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
