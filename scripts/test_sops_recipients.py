#!/usr/bin/env python3
"""Tests for scripts/sops_recipients.py.

The failure this guards against is silent and unrecoverable: a rotation that
edits the shared anchor but not an explicit per-rule list leaves that rule
holding only the retired key. Nothing errors, the file still commits, and it
becomes unreadable the moment the old private key is deleted. So the tests
below care mostly about which lists an edit reaches, and about refusing edits
that would strand a file.

Run:  python3 scripts/test_sops_recipients.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sops_recipients as sr  # noqa: E402

A = "age1" + "a" * 58
B = "age1" + "b" * 58
C = "age1" + "c" * 58
NEW = "age1" + "n" * 58

SAMPLE = f"""# a comment at the top
recipients: &recipients
  # working key
  - {A}

  # escrow key
  - {B}

creation_rules:
  - path_regex: secrets/only-mine\\.sops\\.yaml$
    key_groups:
      - age:
          # mirrors the anchor above
          - {A}
          - {B}
          # extra: this file and no other
          - {C}

  - path_regex: secrets/.*\\.sops\\.ya?ml$
    key_groups:
      - age: *recipients

  - path_regex: signalk/security\\.json$
    encrypted_regex: '^(secretKey|password)$'
    key_groups:
      - age: *recipients
"""


def lines_of(text=SAMPLE):
    return text.splitlines(keepends=True)


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.blocks = sr.parse(lines_of())

    def test_finds_the_anchor_and_one_block_per_rule(self):
        self.assertEqual(
            [b.label for b in self.blocks],
            [
                sr.GLOBAL,
                "secrets/only-mine\\.sops\\.yaml$",
                "secrets/.*\\.sops\\.ya?ml$",
                "signalk/security\\.json$",
            ],
        )

    def test_global_keys(self):
        self.assertEqual(sr.global_keys(self.blocks), [A, B])

    def test_alias_rules_hold_no_keys_of_their_own(self):
        aliased = [b for b in self.blocks if not b.explicit]
        self.assertEqual(len(aliased), 2)
        self.assertTrue(all(b.keys == [] for b in aliased))

    def test_comments_inside_a_list_do_not_end_it(self):
        explicit = self.blocks[1]
        self.assertEqual(explicit.keys, [A, B, C])

    def test_alias_rules_resolve_to_the_global_list(self):
        aliased = self.blocks[2]
        self.assertEqual(sr.effective_keys(aliased, self.blocks), [A, B])

    def test_extras_are_whatever_the_anchor_does_not_have(self):
        self.assertEqual(sr.extras(self.blocks), {"secrets/only-mine\\.sops\\.yaml$": [C]})


class AddTest(unittest.TestCase):
    def test_reaches_the_anchor_and_every_explicit_list(self):
        lines = lines_of()
        self.assertEqual(sr.add_key(lines, NEW), 2)
        blocks = sr.parse(lines)
        self.assertIn(NEW, sr.global_keys(blocks))
        self.assertIn(NEW, blocks[1].keys)

    def test_is_idempotent(self):
        lines = lines_of()
        sr.add_key(lines, NEW)
        after_first = list(lines)
        self.assertEqual(sr.add_key(lines, NEW), 0)
        self.assertEqual(lines, after_first)

    def test_preserves_comments_and_the_anchor(self):
        lines = lines_of()
        sr.add_key(lines, NEW)
        text = "".join(lines)
        self.assertIn("recipients: &recipients", text)
        self.assertIn("- age: *recipients", text)
        self.assertIn("# extra: this file and no other", text)

    def test_new_key_lands_at_the_indent_of_the_list_it_joins(self):
        lines = lines_of()
        sr.add_key(lines, NEW)
        added = [line for line in lines if NEW in line]
        self.assertEqual(added, [f"  - {NEW}\n", f"          - {NEW}\n"])


class RemoveTest(unittest.TestCase):
    def test_reaches_every_list_holding_the_key(self):
        lines = lines_of()
        self.assertEqual(sr.remove_key(lines, A), 2)
        blocks = sr.parse(lines)
        self.assertEqual(sr.global_keys(blocks), [B])
        self.assertEqual(blocks[1].keys, [B, C])

    def test_removing_a_per_rule_key_leaves_the_anchor_alone(self):
        lines = lines_of()
        self.assertEqual(sr.remove_key(lines, C), 1)
        blocks = sr.parse(lines)
        self.assertEqual(sr.global_keys(blocks), [A, B])
        self.assertEqual(blocks[1].keys, [A, B])

    def test_refuses_to_strand_a_file(self):
        lines = lines_of()
        sr.remove_key(lines, A)
        sr.remove_key(lines, C)
        # B is now the only recipient of the explicit rule.
        with self.assertRaises(sr.ConfigError) as caught:
            sr.remove_key(lines, B)
        self.assertIn("only-mine", str(caught.exception))

    def test_a_refused_removal_changes_nothing(self):
        lines = lines_of()
        sr.remove_key(lines, A)
        sr.remove_key(lines, C)
        before = list(lines)
        with self.assertRaises(sr.ConfigError):
            sr.remove_key(lines, B)
        self.assertEqual(lines, before)

    def test_unknown_key_is_an_error_not_a_silent_no_op(self):
        with self.assertRaises(sr.ConfigError):
            sr.remove_key(lines_of(), NEW)

    def test_add_then_remove_round_trips(self):
        original = lines_of()
        lines = list(original)
        sr.add_key(lines, NEW)
        sr.remove_key(lines, NEW)
        self.assertEqual(lines, original)


class MatchingTest(unittest.TestCase):
    def setUp(self):
        self.blocks = sr.parse(lines_of())

    def test_first_matching_rule_wins(self):
        # Both secrets/ rules match this path; the narrower one is first, so
        # its extra key applies and the anchor-only rule does not.
        self.assertEqual(
            sr.keys_for_path("secrets/only-mine.sops.yaml", self.blocks), [A, B, C]
        )

    def test_other_files_fall_through_to_the_anchor(self):
        self.assertEqual(sr.keys_for_path("secrets/symphony.sops.yaml", self.blocks), [A, B])
        self.assertEqual(sr.keys_for_path("signalk/security.json", self.blocks), [A, B])

    def test_unconfigured_path_has_no_recipients(self):
        self.assertEqual(sr.keys_for_path("README.md", self.blocks), [])


class RealConfigTest(unittest.TestCase):
    """The checked-in .sops.yaml must stay parseable by all of the above."""

    def setUp(self):
        self.blocks = sr.parse(sr.read())

    def test_parses_and_has_recipients(self):
        self.assertTrue(sr.global_keys(self.blocks))

    def test_every_rule_has_a_recipient_list(self):
        for block in sr.rule_blocks(self.blocks):
            self.assertTrue(
                sr.effective_keys(block, self.blocks),
                f"rule {block.label} resolves to no recipients",
            )

    def test_every_configured_file_is_readable_by_some_key(self):
        import sops_paths

        for path in sops_paths.whole_file_paths() + sops_paths.inplace_paths():
            self.assertTrue(
                sr.keys_for_path(path, self.blocks),
                f"{path} is configured for encryption but matches no rule with keys",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
