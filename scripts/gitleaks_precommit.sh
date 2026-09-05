#!/usr/bin/env bash
# gitleaks over the staged diff, from a pinned image, degrading gracefully
# when there is no Docker daemon to run it in.
#
# This replaces the upstream `gitleaks-docker` pre-commit hook, which is a
# `language: docker_image` hook and therefore hard-fails the commit the
# moment `docker` can't be reached -- Docker Desktop not started, WSL2
# integration off for the distro, or no Docker at all. That turned "I don't
# run containers on this laptop" into "I cannot commit a typo fix".
#
# The invocation is upstream's, verbatim
# (gitleaks/.pre-commit-hooks.yaml at v8.30.1), with --config added to match
# what CI passes. Pinning an exact image rather than using whatever
# `gitleaks` is on PATH is deliberate: a stale distro build is a different
# (and differently-spelled) scanner than the one CI runs.
#
# Upgrading: this is now the pin `pre-commit autoupdate` used to move. Bump
# GITLEAKS_VERSION here AND the image tag in .github/workflows/secret-scan.yml
# together, so laptop and CI keep agreeing on which scanner cleared a commit.
#
# CI is unaffected by any of this: the gitleaks job in validate.yml runs the
# same image over full history on a runner that always has Docker, and is
# the enforcement boundary regardless of what a laptop can run.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/secretguard.sh disable=SC1091
. "$(pwd)/scripts/secretguard.sh"

GITLEAKS_VERSION="v8.30.1"
IMAGE="zricethezav/gitleaks:${GITLEAKS_VERSION}"

if ! command -v docker >/dev/null 2>&1; then
	secretguard_require "gitleaks did not run: no docker on PATH" \
		problem="the staged diff was not scanned for credential-shaped strings on this machine" \
		needs="docker, to run the pinned $IMAGE" \
		blocked_by="pre-commit hook 'gitleaks' (scripts/gitleaks_precommit.sh)" \
		fix="install Docker, or accept the gap: CI runs the same scanner over full history and cannot be bypassed" \
		see="RUNBOOK.md, A hook blocks your commit" || exit 1
	exit 0
fi

if ! docker info >/dev/null 2>&1; then
	secretguard_require "gitleaks did not run: docker daemon not reachable" \
		problem="docker is installed but not running, so the staged diff was not scanned on this machine" \
		needs="a running Docker daemon" \
		blocked_by="pre-commit hook 'gitleaks' (scripts/gitleaks_precommit.sh)" \
		fix="start Docker Desktop / dockerd (WSL2: enable integration for this distro), or commit and let CI scan" \
		see="RUNBOOK.md, A hook blocks your commit" || exit 1
	exit 0
fi

config_args=()
if [ -f .gitleaks.toml ]; then
	config_args=(--config "$PWD/.gitleaks.toml")
fi

# --redact is non-negotiable: without it gitleaks prints the secret it found
# into the terminal, turning a near-miss into a real exposure.
exec docker run --rm -v "$PWD:$PWD" -w "$PWD" "$IMAGE" \
	git --pre-commit --redact --staged --verbose "${config_args[@]}"
