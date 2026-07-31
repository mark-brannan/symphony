#!/usr/bin/env python3
"""
Syntax validation for every tracked JSON/YAML file in the repo. Doesn't
need the age key or sops -- the sops-tracked files (security.json, the two
plugin configs, secrets/symphony.sops.yaml) are still syntactically valid
JSON/YAML as committed; only their secret leaf values are opaque ENC[...]
strings, which parse fine as plain strings. Meant to run in CI (no secrets
available there) as well as locally.
"""
import json
import subprocess
import sys

import yaml

TRACKED_JSON = subprocess.run(
    ["git", "ls-files", "*.json"], capture_output=True, text=True, check=True
).stdout.splitlines()
TRACKED_YAML = subprocess.run(
    ["git", "ls-files", "*.yaml", "*.yml"], capture_output=True, text=True, check=True
).stdout.splitlines()

failures = []

for path in TRACKED_JSON:
    try:
        with open(path) as f:
            json.load(f)
    except Exception as e:
        failures.append(f"{path}: {e}")

for path in TRACKED_YAML:
    try:
        with open(path) as f:
            list(yaml.safe_load_all(f))
    except Exception as e:
        failures.append(f"{path}: {e}")

if failures:
    print(f"{len(failures)} file(s) failed to parse:")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)

print(f"OK: {len(TRACKED_JSON)} JSON file(s), {len(TRACKED_YAML)} YAML file(s) parse cleanly.")
