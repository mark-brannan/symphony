#!/usr/bin/env bash
# Scans the full git history for credentials that are actually LIVE.
#
# trufflehog differs from gitleaks in one important way: it doesn't just
# pattern-match, it calls the provider's API to check whether a candidate
# credential still works. So a finding here is never a false alarm and is
# always urgent -- the secret is real, valid, and in a public repo.
#
# Why this wrapper exists: trufflehog has no --redact flag and prints raw
# secret values on stdout. This repo's GitHub Actions logs are public, so
# piping its output straight into CI would turn a near-miss into a second
# exposure. We take JSON and print only detector/file/commit -- never the
# value.
#
# Run locally any time:  scripts/scan_verified_secrets.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TRUFFLEHOG_VERSION="3.97.0"
REPORT="$(mktemp)"
trap 'rm -f "$REPORT"' EXIT

echo "Scanning full history for verified-live secrets (trufflehog ${TRUFFLEHOG_VERSION})..."

# --fail is deliberately NOT passed: we want the JSON regardless, and this
# script decides the exit status after redacting.
docker run --rm -v "$PWD:/repo" "trufflesecurity/trufflehog:${TRUFFLEHOG_VERSION}" \
  git file:///repo --results=verified --json --no-update >"$REPORT" 2>/dev/null || true

python3 - "$REPORT" <<'PY'
import json
import sys

findings = []
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("DetectorName"):
            findings.append(record)

if not findings:
    print("OK: no live credentials found in git history.")
    sys.exit(0)

print(f"\n{'=' * 70}")
print(f"{len(findings)} VERIFIED LIVE CREDENTIAL(S) IN GIT HISTORY")
print(f"{'=' * 70}\n")

for record in findings:
    meta = record.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
    # Deliberately never printing record["Raw"] / ["Redacted"] -- the point
    # of this wrapper is that the value stays out of public CI logs.
    print(f"  detector : {record.get('DetectorName')}")
    print(f"  file     : {meta.get('file', '?')}")
    print(f"  commit   : {str(meta.get('commit', '?'))[:12]}")
    print(f"  date     : {meta.get('timestamp', '?')}")
    print()

print("These credentials are LIVE and PUBLIC. In priority order:")
print("  1. Rotate them at the provider NOW. Revocation is the only fix that")
print("     matters -- rewriting git history does not un-publish a secret.")
print("  2. Then see RUNBOOK.md -> 'A secret was committed in plaintext'.")
sys.exit(1)
PY
