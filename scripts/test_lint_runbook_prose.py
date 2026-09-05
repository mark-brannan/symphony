#!/usr/bin/env python3
"""Tests for the runbook prose lint.

Four things it has to get right, all of which fail silently if wrong: prose
counting must ignore code fences and tables (else every command block reads
as bloat), a section over budget must fail, a commit that removes as much as
it adds must pass, and a runbook commit that also stages code must fail.

Run: python3 scripts/test_lint_runbook_prose.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lint_runbook_prose as lint  # noqa: E402


class ProseCountingTest(unittest.TestCase):
    def test_ignores_fences_headings_tables_blanks(self):
        text = (
            "# Title\n\n"
            "one two three\n\n"
            "```sh\n"
            "this whole fenced block is free of charge entirely\n"
            "```\n\n"
            "| col | col |\n"
            "| --- | --- |\n"
            "| a | b |\n"
        )
        self.assertEqual(lint.count_prose_words(text), 3)

    def test_shell_comments_inside_fences_count(self):
        text = "## A\n\n```bash\n#!/bin/sh\n# four words of prose\nrun --flag  # not counted\n```\n"
        self.assertEqual(lint.count_prose_words(text), 4)

    def test_inline_code_spans_are_free(self):
        self.assertEqual(lint.count_prose_words("## A\n\nrun `docker compose up -d` now\n"), 2)

    def test_index_section_is_exempt(self):
        text = "## Where things are\n\nlink one link two link three\n"
        self.assertEqual(lint.count_prose_words(text), 0)

    def test_words_attributed_to_enclosing_section(self):
        text = "## A\n\none two\n\n## B\n\nthree four five\n"
        self.assertEqual(lint.section_word_counts(text), [("A", 2), ("B", 3)])

    def test_repeated_section_titles_stay_separate(self):
        # Two distinct `## Backup` sections must not merge into one combined
        # count -- each may be under budget alone while the sum is over.
        text = "## Backup\n\none two\n\n## Backup\n\nthree four five\n"
        self.assertEqual(
            lint.section_word_counts(text), [("Backup", 2), ("Backup", 3)]
        )

    def test_four_backtick_fence_survives_a_nested_triple_backtick(self):
        text = "## A\n\n````\nsome prose with ``` inside a fence\n````\n\nafter\n"
        self.assertEqual(lint.count_prose_words(text), 1)

    def test_table_without_leading_pipes_is_free(self):
        text = "## A\n\nHeader | Header\n------ | ------\nvalue | value\n\nreal words here\n"
        self.assertEqual(lint.count_prose_words(text), 3)


class GitFixture(unittest.TestCase):
    """A throwaway repo, with lint.ROOT pointed at it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self._real_root = lint.ROOT
        lint.ROOT = self.root
        self.addCleanup(lambda: setattr(lint, "ROOT", self._real_root))
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *args):
        return subprocess.run(
            ["git"] + list(args), cwd=self.root, capture_output=True, text=True, check=True
        )

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


class SectionBudgetTest(GitFixture):
    def test_section_over_budget_fails(self):
        over = "## Big\n\n" + ("word " * (lint.SECTION_PROSE_MAX + 5)) + "\n"
        self.write("RUNBOOK.md", over)
        self.git("add", "RUNBOOK.md")
        findings = lint.check_sections(["RUNBOOK.md"], lambda p: lint.git_show(":", p))
        self.assertEqual(len(findings), 1)
        self.assertIn("Big", findings[0])

    def test_section_within_budget_passes(self):
        self.write("RUNBOOK.md", "## Small\n\nshort enough\n")
        self.git("add", "RUNBOOK.md")
        self.assertEqual(
            lint.check_sections(["RUNBOOK.md"], lambda p: lint.git_show(":", p)), []
        )


class DeltaTest(GitFixture):
    def test_new_file_counts_fully_as_added(self):
        self.write("RUNBOOK.md", "seed\n")
        self.git("add", "RUNBOOK.md")
        self.git("commit", "-qm", "seed", "--", "RUNBOOK.md")
        self.write("runbooks/new.md", "## S\n\n" + ("word " * 60) + "\n")
        self.git("add", "runbooks/new.md")
        delta, findings = lint.check_delta(["runbooks/new.md"], "HEAD")
        self.assertEqual(delta, 60)
        self.assertTrue(findings)

    def test_removal_credits_against_addition(self):
        self.write("RUNBOOK.md", "## A\n\n" + ("word " * 100) + "\n")
        self.git("add", "RUNBOOK.md")
        self.git("commit", "-qm", "seed", "--", "RUNBOOK.md")
        # Swap 100 words for 100 words: net zero, well inside the cap.
        self.write("RUNBOOK.md", "## A\n\n" + ("term " * 100) + "\n")
        self.git("add", "RUNBOOK.md")
        delta, findings = lint.check_delta(["RUNBOOK.md"], "HEAD")
        self.assertEqual(delta, 0)
        self.assertEqual(findings, [])


    def test_deleted_runbook_credits_its_words(self):
        self.write("RUNBOOK.md", "## A\n")
        self.write("runbooks/old.md", "## S\n\n" + ("word " * 100) + "\n")
        self.git("add", "RUNBOOK.md", "runbooks/old.md")
        self.git("commit", "-qm", "seed", "--", "RUNBOOK.md", "runbooks/old.md")
        self.git("rm", "-q", "runbooks/old.md")
        self.write("RUNBOOK.md", "## A\n\n" + ("word " * 120) + "\n")
        self.git("add", "RUNBOOK.md")
        delta, findings = lint.check_delta(lint.staged_paths(), "HEAD")
        self.assertEqual(delta, 20)
        self.assertEqual(findings, [])

    def test_pure_rename_is_net_zero(self):
        self.write("RUNBOOK.md", "seed\n")
        self.write("runbooks/a.md", "## S\n\n" + ("word " * 100) + "\n")
        self.git("add", "RUNBOOK.md", "runbooks/a.md")
        self.git("commit", "-qm", "seed", "--", "RUNBOOK.md", "runbooks/a.md")
        self.git("mv", "runbooks/a.md", "runbooks/b.md")
        delta, findings = lint.check_delta(lint.staged_paths(), "HEAD")
        self.assertEqual(delta, 0)
        self.assertEqual(findings, [])


class RunbookOnlyTest(unittest.TestCase):
    def test_code_alongside_runbook_fails(self):
        findings = lint.check_runbook_only(["RUNBOOK.md", "scripts/foo.py"])
        self.assertEqual(len(findings), 1)
        self.assertIn("scripts/foo.py", findings[0])

    def test_allowlisted_neighbours_pass(self):
        self.assertEqual(
            lint.check_runbook_only(
                ["RUNBOOK.md", "README.md", "CLAUDE.md", "reference/x.md", "runbooks/y.md"]
            ),
            [],
        )

    def test_no_runbook_staged_is_not_our_business(self):
        self.assertEqual(lint.check_runbook_only(["scripts/foo.py", "ansible/x.yml"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
