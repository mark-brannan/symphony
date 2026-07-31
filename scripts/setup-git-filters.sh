#!/usr/bin/env bash
# Run once per clone/checkout. `.gitattributes` names the `sops` filter but
# git filter *commands* live in .git/config, which git deliberately doesn't
# version (arbitrary commands from a repo you cloned would be a code-exec
# vector) -- so every clone has to wire this up for itself.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if ! command -v sops >/dev/null 2>&1; then
  echo "sops not found on PATH -- install it first (see RUNBOOK.md)" >&2
  exit 1
fi
if ! command -v age >/dev/null 2>&1; then
  echo "age not found on PATH -- install it first (see RUNBOOK.md)" >&2
  exit 1
fi
if [ ! -f "$HOME/.config/sops/age/keys.txt" ] && [ -z "${SOPS_AGE_KEY_FILE:-}" ]; then
  echo "warning: no age key found at ~/.config/sops/age/keys.txt and SOPS_AGE_KEY_FILE is unset." >&2
  echo "  security.json / users.yaml / plugin tokens will smudge as ciphertext until you provision one." >&2
fi

git config filter.sops.clean  "python3 $(pwd)/scripts/sops_filter.py clean %f"
git config filter.sops.smudge "python3 $(pwd)/scripts/sops_filter.py smudge %f"
git config filter.sops.required true

git config core.hooksPath .githooks

echo "git filters + hooks configured."
