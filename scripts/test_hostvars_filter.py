#!/usr/bin/env python3
"""Unit tests for the pure substitution core of hostvars_filter.py.

Same rationale as test_pseudonymize.py: this code rewrites files SignalK
reads as live configuration, and both failure directions are silent -- a
missed expansion hands SignalK a `{{ placeholder }}` as a URL, a missed
contraction commits one machine's value over the other's. Stdlib unittest,
no repo state touched: expand/contract take their maps as arguments.
"""
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


if __name__ == "__main__":
    unittest.main()
