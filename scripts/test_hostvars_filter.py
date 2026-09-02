#!/usr/bin/env python3
"""Unit tests for the pure substitution core of hostvars_filter.py.

Same rationale as test_pseudonymize.py: this code rewrites files SignalK
reads as live configuration, and both failure directions are silent -- a
missed expansion hands SignalK a `{{ placeholder }}` as a URL, a missed
contraction commits one machine's value over the other's. Stdlib unittest,
no repo state touched: expand/contract take their maps as arguments.
"""
import contextlib
import io
import unittest

import hostvars_filter as hv

NAMES = ["ntfy_url"]
VALUES = {"ntfy_url": "http://ntfy:80"}

GIT_FORM = '{\n  "url": "{{ ntfy_url }}",\n  "topic": "symphony-alarms"\n}'
TREE_FORM = '{\n  "url": "http://ntfy:80",\n  "topic": "symphony-alarms"\n}'


class ExpandTest(unittest.TestCase):
    def test_expands_declared_placeholder(self):
        result, unresolved = hv.expand(GIT_FORM, NAMES, VALUES)
        self.assertEqual(result, TREE_FORM)
        self.assertEqual(unresolved, [])

    def test_tolerates_flexible_whitespace_in_placeholder(self):
        result, _ = hv.expand('"{{ntfy_url}}"', NAMES, VALUES)
        self.assertEqual(result, '"http://ntfy:80"')

    def test_missing_value_left_unexpanded_and_reported(self):
        result, unresolved = hv.expand(GIT_FORM, NAMES, {})
        self.assertEqual(result, GIT_FORM)
        self.assertEqual(unresolved, ["ntfy_url"])

    def test_undeclared_name_left_alone_silently(self):
        text = '"{{ some_other_var }}"'
        result, unresolved = hv.expand(text, NAMES, VALUES)
        self.assertEqual(result, text)
        self.assertEqual(unresolved, [])

    def test_placeholder_inside_longer_string_is_not_a_placeholder(self):
        text = '"prefix {{ ntfy_url }} suffix"'
        result, _ = hv.expand(text, NAMES, VALUES)
        self.assertEqual(result, text)


class ContractTest(unittest.TestCase):
    def test_contracts_value_back_to_placeholder(self):
        result, unplaced = hv.contract(TREE_FORM, NAMES, VALUES)
        self.assertEqual(result, GIT_FORM)
        self.assertEqual(unplaced, [])

    def test_value_inside_longer_string_untouched(self):
        text = '"see http://ntfy:80 for details"'
        result, unplaced = hv.contract(text, NAMES, VALUES)
        self.assertEqual(result, text)
        self.assertEqual(unplaced, ["ntfy_url"])

    def test_drifted_value_reported_and_committed_literally(self):
        drifted = TREE_FORM.replace("http://ntfy:80", "http://10.0.0.5:8090")
        result, unplaced = hv.contract(drifted, NAMES, VALUES)
        self.assertEqual(result, drifted)
        self.assertEqual(unplaced, ["ntfy_url"])

    def test_already_contracted_is_idempotent(self):
        result, unplaced = hv.contract(GIT_FORM, NAMES, VALUES)
        self.assertEqual(result, GIT_FORM)
        self.assertEqual(unplaced, [])


class BlobPatternTest(unittest.TestCase):
    """refresh's recovery path: recognizing a worktree file whose only
    difference from git's copy is the expanded values -- even values from an
    older hostvars.local.yaml that the current one no longer contains."""

    def test_matches_expansion_with_any_value(self):
        import re
        stale = TREE_FORM.replace("http://ntfy:80", "http://10.0.0.5:8090")
        self.assertTrue(re.fullmatch(hv.blob_pattern(GIT_FORM, NAMES), stale))

    def test_rejects_a_file_with_other_local_edits(self):
        import re
        edited = TREE_FORM.replace("symphony-alarms", "other-topic")
        self.assertFalse(re.fullmatch(hv.blob_pattern(GIT_FORM, NAMES), edited))

    def test_undeclared_placeholder_must_match_literally(self):
        import re
        blob = '{"a": "{{ other }}", "b": "{{ ntfy_url }}"}'
        kept = '{"a": "{{ other }}", "b": "http://x"}'
        expanded_other = '{"a": "http://y", "b": "http://x"}'
        self.assertTrue(re.fullmatch(hv.blob_pattern(blob, NAMES), kept))
        self.assertFalse(re.fullmatch(hv.blob_pattern(blob, NAMES), expanded_other))


class RoundTripTest(unittest.TestCase):
    def test_expand_then_contract_is_identity(self):
        expanded, _ = hv.expand(GIT_FORM, NAMES, VALUES)
        contracted, unplaced = hv.contract(expanded, NAMES, VALUES)
        self.assertEqual(contracted, GIT_FORM)
        self.assertEqual(unplaced, [])

    def test_contract_then_expand_is_identity(self):
        contracted, _ = hv.contract(TREE_FORM, NAMES, VALUES)
        expanded, unresolved = hv.expand(contracted, NAMES, VALUES)
        self.assertEqual(expanded, TREE_FORM)
        self.assertEqual(unresolved, [])




class StagedScopeTest(unittest.TestCase):
    """The guard must only block on files THIS commit stages.

    Regression for the dead end that made a one-line doc edit uncommittable
    for days: `check` asserted whole-repo state, failed on a covered file the
    committer never touched, and named a remedy (`refresh`) that needs a
    hostvars.local.yaml the committer did not have.
    """

    def setUp(self):
        self._config = hv.load_config
        self._blob = hv.index_blob
        self._staged = hv.staged_paths
        hv.load_config = lambda: {"covered.json": ["ntfy_url"]}
        hv.index_blob = lambda path: '{"url": "http://localhost:8090"}'  # literal

        # hv.check() writes a full BLOCKED banner to stderr, which is the
        # point of the guard and noise in a passing suite -- three banners
        # in a green run read as three failures. FailureMessageContractTest
        # keeps its own redirect because it asserts on what it captures.
        quiet = contextlib.redirect_stderr(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def tearDown(self):
        hv.load_config = self._config
        hv.index_blob = self._blob
        hv.staged_paths = self._staged

    def test_passes_when_commit_stages_nothing_covered(self):
        hv.staged_paths = lambda: {"maintenance/log.md"}
        self.assertEqual(hv.check(), 0)

    def test_blocks_when_commit_stages_the_covered_file(self):
        hv.staged_paths = lambda: {"maintenance/log.md", "covered.json"}
        self.assertEqual(hv.check(), 1)

    def test_all_mode_ignores_staging_for_ci(self):
        hv.staged_paths = lambda: {"maintenance/log.md"}
        self.assertEqual(hv.check(scope_all=True), 1)

    def test_unknown_scope_falls_back_to_checking_everything(self):
        """A broken `git diff` must not silently disable the guard."""
        hv.staged_paths = lambda: None
        self.assertEqual(hv.check(), 1)

    def test_passing_file_is_fine_when_staged(self):
        hv.index_blob = lambda path: '{"url": "{{ ntfy_url }}"}'
        hv.staged_paths = lambda: {"covered.json"}
        self.assertEqual(hv.check(), 0)


class FailureMessageContractTest(unittest.TestCase):
    """Every blocking message must name a file, a fix, and an exit that
    works for someone who lacks hostvars.local.yaml."""

    def test_message_carries_all_five_elements(self):
        import contextlib, io
        self._c, self._b, self._s = hv.load_config, hv.index_blob, hv.staged_paths
        hv.load_config = lambda: {"covered.json": ["ntfy_url"]}
        hv.index_blob = lambda path: '{"url": "http://localhost:8090"}'
        hv.staged_paths = lambda: {"covered.json"}
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                hv.check()
        finally:
            hv.load_config, hv.index_blob, hv.staged_paths = self._c, self._b, self._s
        text = err.getvalue()
        # Fields and data, never phrasing. Two earlier suites asserted on
        # wording and broke on changes that altered no behaviour; the shared
        # formatter's own parity test owns wording.
        for label in ("problem:", "file:", "needs:", "blocked by:",
                      "fix:", "if stuck:", "mode:"):
            self.assertIn(label, text, f"blocked message is missing {label}")
        self.assertIn("covered.json", text)  # names the file, not "a file"
        # The one substantive claim: an exit that needs no hostvars.local.yaml.
        self.assertIn("git restore --staged", text)


if __name__ == "__main__":
    unittest.main()
