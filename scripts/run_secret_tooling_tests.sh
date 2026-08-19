#!/usr/bin/env bash
# The unit tests for the scripts that rewrite secret-bearing content, plus
# the check that the two mode helpers still agree.
#
# Wrapped rather than inlined in .pre-commit-config.yaml so the pyyaml
# dependency can degrade: hostvars_filter.py imports yaml, so on a clone
# without it every one of these tests errors on import and the hook fails a
# commit for a reason that has nothing to do with the commit. Strict mode
# still treats that as an error -- a machine that holds secrets must be able
# to run the tests that guard them.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/symphony_mode.sh disable=SC1091
. "$(pwd)/scripts/symphony_mode.sh"

if ! command -v python3 >/dev/null 2>&1; then
	symphony_require "secret-tooling tests did not run: no python3" \
		problem="the pseudonymize/recipients/hostvars tests were skipped" \
		needs="python3 on PATH" \
		blocked_by="pre-commit hook 'secret-tooling-tests' (scripts/run_secret_tooling_tests.sh)" \
		fix="install python3 (see RUNBOOK.md, Bringing up a host -- Phase 1)" \
		see="bash scripts/check_clone_setup.sh" || exit 1
	exit 0
fi

if ! python3 -c 'import yaml' >/dev/null 2>&1; then
	symphony_require "secret-tooling tests did not run: pyyaml is missing" \
		problem="hostvars_filter.py and the sops path helpers import yaml, so every one of these tests errors on import" \
		needs="the pyyaml package for this python3" \
		blocked_by="pre-commit hook 'secret-tooling-tests' (scripts/run_secret_tooling_tests.sh)" \
		fix="pip install pyyaml" \
		see="bash scripts/check_clone_setup.sh" || exit 1
	exit 0
fi

python3 scripts/test_pseudonymize.py -q
python3 scripts/test_sops_recipients.py -q
python3 scripts/test_hostvars_filter.py -q
python3 scripts/test_symphony_mode.py -q
