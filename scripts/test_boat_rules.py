#!/usr/bin/env python3
"""Tests for the Symphony-only lint rules in scripts/lint_boat_rules.py.

The generic repo-hygiene rules and their tests moved to
mark-brannan/pre-commit-hooks.

Run: python3 scripts/test_boat_rules.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lint_boat_rules as lint  # noqa: E402


class RuleTestCase(unittest.TestCase):
    """Saves and restores every module seam a test here patches."""

    def setUp(self):
        self._saved = (lint.staged_paths, lint.staged_blob,
                       lint.SCOPE_ALL, lint.CI)
        lint.failures.clear()
        lint.warnings.clear()
        lint.SCOPE_ALL = False
        lint.CI = False

    def tearDown(self):
        (lint.staged_paths, lint.staged_blob,
         lint.SCOPE_ALL, lint.CI) = self._saved
        lint.failures.clear()
        lint.warnings.clear()


class AudibleAlarmScopeTest(RuleTestCase):
    """The staged-vs-working-tree split, for the rule that had no tests.

    Same shape as test_encoding_health's StagedScopeReadsTheIndexTest: a
    scoped run is a statement about what the commit records, so it has to
    read the index. Reading scope from the index and content from disk --
    which this rule did until d2aae17 -- warns about bytes the commit does
    not contain after `git add -p`, and misses ones it does.
    """

    CONFIG = "signalk/plugin-config-data/noisy.json"

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "signalk" / "plugin-config-data").mkdir(parents=True)
        self._root, lint.ROOT = lint.ROOT, root
        self.addCleanup(lambda: setattr(lint, "ROOT", self._root))

    def write(self, sound, on_disk=True):
        """A config that trips the rule only when sound is True."""
        doc = {"configuration": {"notificationSound": sound,
                                 "notificationStates": "WA"}}
        text = json.dumps(doc)
        if on_disk:
            (lint.ROOT / self.CONFIG).write_text(text, encoding="utf-8")
        return text

    def run_rule(self, staged, index_text):
        lint.staged_paths = lambda: staged
        lint.staged_blob = lambda path: index_text
        lint.rule_audible_alarms_are_scoped()
        return lint.failures, lint.warnings

    def test_scoped_run_judges_the_index_not_the_working_tree(self):
        """The bug: staged copy is quiet, working tree is loud."""
        self.write(sound=True)                       # working tree: loud
        _, warns = self.run_rule({self.CONFIG}, self.write(False, on_disk=False))
        self.assertEqual(warns, [],
                         "warned about content this commit does not record")

    def test_scoped_run_still_catches_a_real_one(self):
        """And the converse, so the fix can't be 'never warn'."""
        self.write(sound=False)                      # working tree: quiet
        _, warns = self.run_rule({self.CONFIG}, self.write(True, on_disk=False))
        self.assertTrue(warns, "must warn on what the commit actually records")

    def test_unrelated_commit_is_silent(self):
        self.write(sound=True)
        _, warns = self.run_rule({"maintenance/log.md"}, None)
        self.assertEqual(warns, [])

    def test_all_mode_reads_the_working_tree(self):
        """CI's --all is about the files on disk, so it must not use the index."""
        lint.SCOPE_ALL = True
        self.write(sound=True)
        lint.staged_blob = lambda path: self.fail("--all must not read the index")
        lint.rule_audible_alarms_are_scoped()
        self.assertTrue(lint.warnings)


class FrozenSecretsStillBlockTest(unittest.TestCase):
    """This rule was already correctly scoped; make sure nothing broke it."""

    def setUp(self):
        self._range = os.environ.pop("HYGIENE_COMMIT_RANGE", None)
        lint.failures.clear()
        lint.warnings.clear()

    def tearDown(self):
        if self._range is not None:
            os.environ["HYGIENE_COMMIT_RANGE"] = self._range
        else:
            os.environ.pop("HYGIENE_COMMIT_RANGE", None)

    def test_rule_is_still_registered(self):
        import inspect
        self.assertIn("rule_frozen_secrets_untouched",
                      inspect.getsource(lint.main))

    def test_unusable_range_warns_instead_of_crashing_or_passing_silent(self):
        """CI's whole reason for this env var is a range that can't diff --
        a shallow clone, a first push. That must be visible, not a crash and
        not the same silence the bug this fixes already produced."""
        os.environ["HYGIENE_COMMIT_RANGE"] = "not-a-real-range..also-not-one"
        lint.rule_frozen_secrets_untouched()
        self.assertEqual(lint.failures, [])
        self.assertTrue(any("frozen-secret-range" in w for w in lint.warnings))


if __name__ == "__main__":
    unittest.main()
