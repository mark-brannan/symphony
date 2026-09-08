#!/usr/bin/env bash
# The unit tests for the scripts that rewrite secret-bearing content, the
# check that the two mode helpers still agree, and the guard-scoping suites.
#
# Wrapped rather than inlined in .pre-commit-config.yaml so the pyyaml
# dependency can degrade: these tests import yaml, so on a clone
# without it every one of these tests errors on import and the hook fails a
# commit for a reason that has nothing to do with the commit. Strict mode
# still treats that as an error -- a machine that holds secrets must be able
# to run the tests that guard them.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/secretguard.sh disable=SC1091
. "$(pwd)/scripts/secretguard.sh"

if ! command -v python3 >/dev/null 2>&1; then
	secretguard_require "secret-tooling tests did not run: no python3" \
		problem="the pseudonymize/recipients tests were skipped" \
		needs="python3 on PATH" \
		blocked_by="pre-commit hook 'secret-tooling-tests' (scripts/run_secret_tooling_tests.sh)" \
		fix="install python3 (see RUNBOOK.md, Bringing up a host, step 1 Tooling)" \
		see="bash scripts/check_clone_setup.sh" || exit 1
	exit 0
fi

# These two need nothing but the stdlib, so they run before the pyyaml gate
# below rather than being skipped along with the suites that do need it.
python3 scripts/test_repo_hygiene.py -q
python3 scripts/test_encoding_health.py -q

if ! python3 -c 'import yaml' >/dev/null 2>&1; then
	secretguard_require "secret-tooling tests did not run: pyyaml is missing" \
		problem="the sops path helpers import yaml, so every one of these tests errors on import" \
		needs="the pyyaml package for this python3" \
		blocked_by="pre-commit hook 'secret-tooling-tests' (scripts/run_secret_tooling_tests.sh)" \
		fix="pip install pyyaml" \
		see="bash scripts/check_clone_setup.sh" || exit 1
	exit 0
fi

python3 scripts/test_pseudonymize.py -q
python3 scripts/test_sops_recipients.py -q
python3 scripts/test_secretguard.py -q
