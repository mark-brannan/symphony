#!/usr/bin/env python3
"""
Single source of truth for "which files carry sops-encrypted secrets".

`.sops.yaml` is the only place that list is written down. Everything else
that needs it -- the pre-commit guard, the CI encryption verifier,
`.gitattributes` -- asks this script instead of keeping its own copy.
That's deliberate: the four hand-maintained copies this replaces had
already drifted apart (CI was checking 3 of 10 files).

Two kinds of rule live in `.sops.yaml`, told apart by `encrypted_regex`:

  in-place  -- has `encrypted_regex`. The file stays legible on disk and in
               git; only the named leaf fields become ENC[...]. Read
               directly by SignalK/Grafana, so it must be plaintext locally
               and is handled by the clean/smudge filter.
  whole     -- no `encrypted_regex`. Entire file is ciphertext at rest,
               only ever opened via `sops`. (secrets/*.sops.yaml)

Usage:
    sops_paths.py list           # in-place file paths, one per line
    sops_paths.py list --whole   # whole-file glob patterns
    sops_paths.py check          # verify .sops.yaml and .gitattributes agree
"""
import argparse
import glob
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOPS_CONFIG = os.path.join(REPO, ".sops.yaml")
GITATTRIBUTES = os.path.join(REPO, ".gitattributes")

# A path_regex we can turn back into a literal path: only escaped dots and
# an optional anchor. Anything fancier (character classes, .*, alternation)
# is a real pattern and can't be expanded to one filename.
LITERAL_SAFE = re.compile(r"^[\w\-./]+$")


def load_rules():
    with open(SOPS_CONFIG) as f:
        config = yaml.safe_load(f)
    return config.get("creation_rules", []) or []


def regex_to_path(path_regex):
    """Turn `signalk/security\\.json$` into `signalk/security.json`.

    Returns None if the regex isn't a plain literal path.
    """
    literal = path_regex.rstrip("$").replace("\\.", ".")
    return literal if LITERAL_SAFE.match(literal) else None


def inplace_paths():
    """Literal file paths for every in-place (partial-encryption) rule."""
    paths = []
    for rule in load_rules():
        if "encrypted_regex" not in rule:
            continue
        path = regex_to_path(rule.get("path_regex", ""))
        if path is None:
            print(
                f"warning: in-place rule '{rule.get('path_regex')}' is a pattern, "
                "not a literal path -- skipping. Point it at one file.",
                file=sys.stderr,
            )
            continue
        paths.append(path)
    return paths


def whole_file_patterns():
    """path_regex of every whole-file rule, as-is (these really are patterns)."""
    return [
        rule["path_regex"]
        for rule in load_rules()
        if "encrypted_regex" not in rule and "path_regex" in rule
    ]


def whole_file_paths():
    """Files on disk matching the whole-file rules."""
    found = []
    for pattern in whole_file_patterns():
        compiled = re.compile(pattern)
        for path in glob.glob(os.path.join(REPO, "**", "*"), recursive=True):
            rel = os.path.relpath(path, REPO)
            if os.path.isfile(path) and compiled.search(rel):
                found.append(rel)
    return sorted(set(found))


def gitattributes_paths():
    """Files .gitattributes routes through the sops clean/smudge filter."""
    if not os.path.exists(GITATTRIBUTES):
        return []
    paths = []
    with open(GITATTRIBUTES) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "filter=sops" not in line:
                continue
            paths.append(line.split()[0])
    return paths


def check():
    """Every in-place file must also be wired to the filter, and vice versa.

    A file in .sops.yaml but not .gitattributes never gets encrypted on
    commit -- the dangerous direction. The reverse is a filter pointed at a
    file sops has no rule for, which fails the commit confusingly.
    """
    in_sops = set(inplace_paths())
    in_attrs = set(gitattributes_paths())
    failures = []

    for path in sorted(in_sops - in_attrs):
        failures.append(
            f"{path}: has a .sops.yaml in-place rule but no '{path} filter=sops' "
            "line in .gitattributes -- it would commit as PLAINTEXT."
        )
    for path in sorted(in_attrs - in_sops):
        failures.append(
            f"{path}: routed through the sops filter in .gitattributes but has "
            "no in-place rule in .sops.yaml -- commits will fail."
        )

    # A configured file that doesn't exist yet is a warning, not a failure.
    # It's the normal state between "we decided this plugin's token will be
    # encrypted" and "the plugin is actually installed" -- and a file that
    # does not exist cannot leak. Reported every run so it doesn't become
    # permanent furniture.
    missing = [p for p in sorted(in_sops & in_attrs) if not os.path.exists(os.path.join(REPO, p))]
    for path in missing:
        print(
            f"note: {path} is configured for encryption but does not exist on disk "
            "-- the plugin isn't installed yet, or this is a stale rule.",
            file=sys.stderr,
        )

    if failures:
        print(f"sops config is inconsistent ({len(failures)} problem(s)):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        print(
            "\nFix by re-running scripts/add_inplace_secret.sh for the file, "
            "or removing the stale rule from .sops.yaml and .gitattributes.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(in_sops)} in-place file(s) consistent across .sops.yaml and .gitattributes.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    list_cmd = sub.add_parser("list", help="print configured secret-bearing paths")
    list_cmd.add_argument("--whole", action="store_true", help="whole-file rules instead of in-place")
    sub.add_parser("check", help="verify .sops.yaml and .gitattributes agree")

    args = parser.parse_args()
    if args.command == "check":
        return check()
    for path in (whole_file_paths() if args.whole else inplace_paths()):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
