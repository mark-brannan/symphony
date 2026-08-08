#!/usr/bin/env bash
# Rotate the age master key.
#
# Rotation happens in two phases with a verification step between them, so
# there is never a moment where a host can't decrypt:
#
#   phase 1   add     -- new key becomes a second recipient. BOTH keys work.
#   (verify)  verify  -- prove the new key alone can decrypt everything.
#   phase 2   retire  -- old key stops being a recipient. Only the new works.
#
# Run phase 1, deploy the new key to every host, THEN run phase 2. Doing
# both at once will lock out any host you haven't updated yet.
#
# WHY THIS SCRIPT EXISTS: the in-place files (SignalK plugin configs) cannot
# be re-keyed with `sops updatekeys` -- on disk they are plaintext, and only
# git holds the ciphertext. They are re-keyed by forcing the clean filter to
# re-encrypt, which needs SOPS_FILTER_REKEY=1. Without that flag the filter
# reuses the existing ciphertext byte-for-byte, so rotation LOOKS like it
# worked while leaving every one of those files decryptable only by the old
# key. Doing this by hand is how you lose your secrets.
#
# Usage:
#   scripts/rotate_age_key.sh status
#   scripts/rotate_age_key.sh add [--generate | <new-age-public-key>]
#   scripts/rotate_age_key.sh verify <age-public-key>
#   scripts/rotate_age_key.sh retire <old-age-public-key>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

KEYS_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
SOPS_CONFIG=".sops.yaml"

die() { echo "error: $*" >&2; exit 1; }

configured_recipients() {
  python3 -c "
import yaml, sys
with open('$SOPS_CONFIG') as f:
    doc = yaml.safe_load(f)
for r in doc.get('recipients', []):
    print(r)
"
}

# Every file that needs re-keying, by kind.
whole_files() { python3 scripts/sops_paths.py list --whole; }
inplace_files() {
  while IFS= read -r p; do
    [ -n "$p" ] && [ -f "$p" ] && echo "$p"
  done < <(python3 scripts/sops_paths.py list)
}

# ---------------------------------------------------------------- status ---
cmd_status() {
  echo "Recipients configured in $SOPS_CONFIG:"
  configured_recipients | sed 's/^/  /'
  echo
  echo "Recipients actually present in committed ciphertext:"
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    count=$(git show "HEAD:$path" 2>/dev/null | grep -c 'recipient:' || true)
    printf '  %-64s %s recipient(s)\n' "$path" "${count:-0}"
  done < <(whole_files)

  while IFS= read -r path; do
    [ -n "$path" ] || continue
    count=$(git show "HEAD:$path" 2>/dev/null | python3 -c "
import json, sys
try:
    print(len(json.load(sys.stdin)['sops']['age']))
except Exception:
    print(0)
" 2>/dev/null || echo 0)
    printf '  %-64s %s recipient(s)\n' "$path" "$count"
  done < <(inplace_files)

  echo
  if [ -f "$KEYS_FILE" ]; then
    local n
    n="$(grep -c '^AGE-SECRET-KEY-' "$KEYS_FILE" || true)"
    echo "Private keys held locally in $KEYS_FILE: ${n:-0}"
    while IFS= read -r pub; do
      if configured_recipients | grep -qx "$pub"; then
        echo "  $pub  (current recipient)"
      else
        echo "  $pub  (NOT a recipient -- retired, or belongs elsewhere)"
      fi
    done < <(grep -oP '(?<=public key: )age1\w+' "$KEYS_FILE" 2>/dev/null || true)
  else
    echo "Private keys held locally: none -- $KEYS_FILE does not exist"
  fi
}

# ------------------------------------------------------------------- add ---
rekey_everything() {
  echo "Re-encrypting whole-file stores..."
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    sops updatekeys --yes "$path"
    git add "$path"
    echo "  re-keyed: $path"
  done < <(whole_files)

  echo "Re-encrypting in-place files (forcing the clean filter)..."
  local files=()
  while IFS= read -r path; do
    files+=("$path")
  done < <(inplace_files)

  if [ "${#files[@]}" -gt 0 ]; then
    # touch so git re-runs the filter even though content is unchanged
    touch -- "${files[@]}"
    SOPS_FILTER_REKEY=1 git add --renormalize -- "${files[@]}"
    for f in "${files[@]}"; do echo "  re-keyed: $f"; done
  fi
}

cmd_add() {
  local newkey="${1:?usage: $0 add [--generate | <new-age-public-key>]}"

  if [ "$newkey" = "--generate" ]; then
    local tmpdir tmpkey
    # age-keygen refuses to overwrite an existing file, so hand it a path
    # inside a fresh directory rather than a pre-created mktemp file.
    tmpdir="$(mktemp -d)"
    chmod 700 "$tmpdir"
    tmpkey="$tmpdir/new.key"
    age-keygen -o "$tmpkey" 2>/dev/null
    newkey="$(grep -oP '(?<=public key: )age1\w+' "$tmpkey")"
    mkdir -p "$(dirname "$KEYS_FILE")"
    touch "$KEYS_FILE"; chmod 600 "$KEYS_FILE"
    {
      echo ""
      echo "# added by rotate_age_key.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      cat "$tmpkey"
    } >>"$KEYS_FILE"
    shred -u "$tmpkey" 2>/dev/null || rm -f "$tmpkey"
    rmdir "$tmpdir" 2>/dev/null || rm -rf "$tmpdir"
    echo "generated new key, appended private half to $KEYS_FILE"
    echo
    echo "  ####################################################################"
    echo "  #  BACK UP $KEYS_FILE NOW."
    echo "  #  Put it in a password manager or an offline copy before you go on."
    echo "  #  If this file is lost, every encrypted value in the repo is gone."
    echo "  ####################################################################"
    echo
  fi

  [[ "$newkey" =~ ^age1[0-9a-z]{58}$ ]] || die "'$newkey' is not a valid age public key"

  if configured_recipients | grep -qx "$newkey"; then
    echo "already a recipient: $newkey"
  else
    python3 - "$newkey" <<'PY'
import re, sys
key = sys.argv[1]
with open(".sops.yaml") as f:
    lines = f.readlines()
# Insert after the last recipient entry in the `recipients:` block, which
# ends where `creation_rules:` begins.
end = next(i for i, l in enumerate(lines) if l.startswith("creation_rules:"))
last = max(i for i in range(end) if re.match(r"^\s+- age1", lines[i]))
lines.insert(last + 1, f"  - {key}\n")
with open(".sops.yaml", "w") as f:
    f.writelines(lines)
PY
    echo "added recipient to $SOPS_CONFIG: $newkey"
  fi

  rekey_everything
  git add "$SOPS_CONFIG"

  echo
  echo "Phase 1 complete. Both keys can now decrypt. Next:"
  echo "  1. git commit"
  echo "  2. Copy the new private key to every other host that needs it."
  echo "  3. scripts/rotate_age_key.sh verify $newkey"
  echo "  4. scripts/rotate_age_key.sh retire <old-public-key>"
}

# ---------------------------------------------------------------- verify ---
# Proves the given key can decrypt everything ON ITS OWN. This is the gate
# before retiring the old key -- skip it and you can lock yourself out
# permanently.
#
# CRITICAL: SOPS_AGE_KEY_FILE does NOT restrict sops to that one file. sops
# aggregates identities from SOPS_AGE_KEY, SOPS_AGE_KEY_FILE *and* the
# default keyring at $XDG_CONFIG_HOME/sops/age/keys.txt (falling back to
# $HOME/.config/...). Verifying with only SOPS_AGE_KEY_FILE set therefore
# passes whenever the OLD key is still in the default keyring -- which it
# always is, at exactly the moment you're deciding whether it's safe to
# delete. That false pass is how you lose every secret in the repo.
#
# So we also point HOME and XDG_CONFIG_HOME at an empty directory and clear
# SOPS_AGE_KEY, leaving the candidate key as the only identity sops can find.
cmd_verify() {
  local pubkey="${1:?usage: $0 verify <age-public-key>}"
  local privkey solo
  privkey="$(python3 - "$KEYS_FILE" "$pubkey" <<'PY'
import sys
path, want = sys.argv[1], sys.argv[2]
lines = open(path).read().splitlines()
for i, line in enumerate(lines):
    if want in line:
        for candidate in lines[i:]:
            if candidate.startswith("AGE-SECRET-KEY-"):
                print(candidate)
                sys.exit(0)
sys.exit(1)
PY
)" || die "no private key for $pubkey found in $KEYS_FILE"

  local sandbox
  sandbox="$(mktemp -d)"
  chmod 700 "$sandbox"
  solo="$sandbox/solo.key"
  printf '%s\n' "$privkey" >"$solo"
  chmod 600 "$solo"
  mkdir -p "$sandbox/empty"

  # Everything sops could read an identity from, neutralised except $solo.
  sops_solo() {
    env -u SOPS_AGE_KEY \
        HOME="$sandbox/empty" \
        XDG_CONFIG_HOME="$sandbox/empty" \
        SOPS_AGE_KEY_FILE="$solo" \
        sops "$@"
  }

  # Prove the isolation itself works before trusting any result from it: a
  # throwaway key must NOT be able to decrypt. If this passes, the sandbox
  # is leaking identities and every check below is meaningless.
  local canary="$sandbox/canary.key"
  age-keygen -o "$canary" 2>/dev/null
  local probe
  probe="$(whole_files | head -1)"
  if [ -n "$probe" ]; then
    if env -u SOPS_AGE_KEY HOME="$sandbox/empty" XDG_CONFIG_HOME="$sandbox/empty" \
         SOPS_AGE_KEY_FILE="$canary" sops --decrypt "$probe" >/dev/null 2>&1; then
      rm -rf "$sandbox"
      die "key isolation is not working -- an unrelated key decrypted $probe. Refusing to report a result."
    fi
  fi

  local fail=0 checked=0
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    if sops_solo --decrypt "$path" >/dev/null 2>&1; then
      checked=$((checked + 1))
    else
      echo "  CANNOT DECRYPT: $path" >&2
      fail=1
    fi
  done < <(whole_files)

  while IFS= read -r path; do
    [ -n "$path" ] || continue
    git show ":$path" >"$sandbox/blob" 2>/dev/null || { echo "  NOT STAGED: $path" >&2; fail=1; continue; }
    if sops_solo --decrypt --filename-override "$path" "$sandbox/blob" >/dev/null 2>&1; then
      checked=$((checked + 1))
    else
      echo "  CANNOT DECRYPT (staged): $path" >&2
      fail=1
    fi
  done < <(inplace_files)

  rm -rf "$sandbox"

  if [ "$fail" -ne 0 ]; then
    echo >&2
    die "$pubkey CANNOT decrypt everything. Do NOT retire the old key."
  fi
  echo "OK: $pubkey alone decrypts all $checked secret-bearing file(s)."
  echo "Safe to retire the old key once every host has this one."
}

# ---------------------------------------------------------------- retire ---
cmd_retire() {
  local oldkey="${1:?usage: $0 retire <old-age-public-key>}"

  configured_recipients | grep -qx "$oldkey" || die "$oldkey is not currently a recipient"
  local remaining
  remaining="$(configured_recipients | grep -vx "$oldkey" || true)"
  [ -n "$remaining" ] || die "refusing to retire the only recipient -- add a new key first"

  echo "Retiring: $oldkey"
  echo "Remaining recipient(s):"
  while IFS= read -r r; do
    [ -n "$r" ] && echo "  $r"
  done <<<"$remaining"
  echo
  echo "Every host must already hold a remaining key. Verify first:"
  echo "  scripts/rotate_age_key.sh verify <remaining-key>"
  read -r -p "Proceed? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || die "aborted"

  python3 - "$oldkey" <<'PY'
import sys
key = sys.argv[1]
with open(".sops.yaml") as f:
    lines = f.readlines()
lines = [l for l in lines if key not in l]
with open(".sops.yaml", "w") as f:
    f.writelines(lines)
PY
  echo "removed recipient from $SOPS_CONFIG"

  rekey_everything
  git add "$SOPS_CONFIG"

  echo
  echo "Phase 2 complete. Only the remaining key(s) can decrypt what is now staged."
  echo
  echo "  git commit"
  echo
  echo "IMPORTANT: git HISTORY still contains ciphertext encrypted to the old"
  echo "key. Rotation protects future commits, not past ones. If the old key"
  echo "was COMPROMISED, rotate the underlying secrets too -- see"
  echo "RUNBOOK.md -> 'A secret was committed in plaintext'."
  echo
  echo "Once every host is confirmed working, delete the old private key from"
  echo "$KEYS_FILE and from your backups."
}

case "${1:-}" in
  status) shift; cmd_status "$@" ;;
  add)    shift; cmd_add "$@" ;;
  verify) shift; cmd_verify "$@" ;;
  retire) shift; cmd_retire "$@" ;;
  *) sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
