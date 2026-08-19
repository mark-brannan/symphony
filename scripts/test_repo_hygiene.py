#!/usr/bin/env python3
"""Tests for repo-hygiene's scoping.

The rule that matters both ways: an unconfigured filter must BLOCK when the
commit stages a file that filter covers (that is the 2026-08-14 incident --
plaintext secrets into a public repo) and must NOT block otherwise, because
the fix it names needs sops, age and the age key, which a contributor or a
fresh checkout does not have.
"""
import unittest

import lint_repo_hygiene as lint


class ScopingTest(unittest.TestCase):
    def setUp(self):
        lint.failures.clear()
        lint.warnings.clear()
        self._staged = lint.staged_paths
        self._all = lint.SCOPE_ALL
        lint.SCOPE_ALL = False
        self._ci = lint.CI
        lint.CI = False

    def tearDown(self):
        lint.staged_paths = self._staged
        lint.SCOPE_ALL = self._all
        lint.CI = self._ci
        lint.failures.clear()
        lint.warnings.clear()

    def run_rule(self, staged):
        lint.staged_paths = lambda: staged
        lint.rule_declared_filters_are_configured()
        return lint.failures, lint.warnings

    def test_unrelated_commit_warns_but_does_not_block(self):
        fails, warns = self.run_rule({"maintenance/log.md"})
        self.assertEqual(fails, [])
        self.assertTrue(any("unconfigured-filter" in w for w in warns))

    def test_staging_a_covered_file_blocks(self):
        fails, _ = self.run_rule({"signalk/plugin-config-data/venus.json"})
        self.assertTrue(any("UNTRANSFORMED" in f for f in fails))

    def test_block_message_offers_a_way_out(self):
        fails, _ = self.run_rule({"signalk/plugin-config-data/venus.json"})
        text = "\n".join(fails)
        self.assertIn("setup-git-filters.sh", text)      # the fix
        self.assertIn("git restore --staged", text)      # exit without the key
        self.assertIn("SKIP=repo-hygiene", text)         # another session's file

    def test_all_mode_blocks_regardless_of_staging(self):
        lint.SCOPE_ALL = True
        fails, _ = self.run_rule({"maintenance/log.md"})
        self.assertTrue(fails, "CI's --all must still enforce repo-wide")

    def test_unknown_scope_falls_back_to_blocking(self):
        """A broken `git diff` must not silently disable the rule."""
        fails, _ = self.run_rule(None)
        self.assertTrue(fails)

    def test_ci_skips_the_rule_entirely(self):
        lint.CI = True
        fails, warns = self.run_rule({"signalk/plugin-config-data/venus.json"})
        self.assertEqual((fails, warns), ([], []))


class FrozenSecretsStillBlockTest(unittest.TestCase):
    """This rule was already correctly scoped; make sure nothing broke it."""

    def test_rule_is_still_registered(self):
        import inspect
        src = inspect.getsource(lint.main)
        self.assertIn("rule_frozen_secrets_untouched", src)


if __name__ == "__main__":
    unittest.main()
