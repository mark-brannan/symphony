#!/usr/bin/env python3
"""Tests for the staged-scoping and the repair path of check_encoding_health.

The repair tests exist because the first cut of fix_file re-encoded the
whole file, which fails the moment a document holds both real mojibake and
a legitimate em dash -- i.e. on almost every real file in this repo. The
check named a fix command that did not work, which is worse than naming
none.
"""
# Fixtures are written as escapes, never literally. Spelled out, this file
# would contain the very byte sequences check_encoding_health searches for
# and would flag itself on every CI run -- which is exactly what happened on
# the first version of it. Same reasoning as MOJIBAKE_MARKERS in the script
# under test.
import io
import contextlib
import tempfile
import unittest
from pathlib import Path

import check_encoding_health as eh


def mangle(s):
    """What a UTF-8 string looks like after a latin-1 round-trip."""
    return s.encode("utf-8").decode("cp1252")


class RepairTest(unittest.TestCase):
    def test_repairs_a_mangled_accent(self):
        text, n = eh.repair_mojibake(mangle("a café line"))
        self.assertEqual(text, "a café line")
        self.assertEqual(n, 1)

    def test_repairs_a_mangled_em_dash(self):
        text, _ = eh.repair_mojibake(mangle("rope — 12 mm"))
        self.assertEqual(text, "rope — 12 mm")

    def test_leaves_legitimate_non_ascii_alone(self):
        clean = "12° true — heading"
        text, n = eh.repair_mojibake(clean)
        self.assertEqual(text, clean)
        self.assertEqual(n, 0)

    def test_repairs_damage_beside_legitimate_non_ascii(self):
        """The case that broke the first implementation."""
        mixed = "heading 12° — and " + mangle("a café")
        text, n = eh.repair_mojibake(mixed)
        self.assertEqual(text, "heading 12° — and a café")
        self.assertEqual(n, 1)

    def test_repair_is_idempotent(self):
        once, _ = eh.repair_mojibake(mangle("café"))
        twice, n = eh.repair_mojibake(once)
        self.assertEqual(once, twice)
        self.assertEqual(n, 0)


class FixFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = eh.ROOT
        eh.ROOT = Path(self.dir.name)

    def tearDown(self):
        eh.ROOT = self.root
        self.dir.cleanup()

    def write(self, name, data):
        p = Path(self.dir.name) / name
        p.write_bytes(data)
        return p

    def _quiet(self, fn):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn()
        return rc, out.getvalue() + err.getvalue()

    def test_fixes_a_non_utf8_file(self):
        p = self.write("a.md", "12° true\n".encode("latin-1"))
        rc, _ = self._quiet(lambda: eh.fix_file("a.md"))
        self.assertEqual(rc, 0)
        self.assertEqual(p.read_text(encoding="utf-8"), "12° true\n")

    def test_fixes_mojibake_next_to_real_non_ascii(self):
        p = self.write("b.md", ("12° — " + mangle("café") + "\n")
                       .encode("utf-8"))
        rc, _ = self._quiet(lambda: eh.fix_file("b.md"))
        self.assertEqual(rc, 0)
        self.assertEqual(p.read_text(encoding="utf-8"), "12° — café\n")

    def test_strips_a_byte_order_mark(self):
        p = self.write("c.md", "\ufeffhello\n".encode("utf-8"))
        rc, _ = self._quiet(lambda: eh.fix_file("c.md"))
        self.assertEqual(rc, 0)
        self.assertEqual(p.read_text(encoding="utf-8"), "hello\n")

    def test_clean_file_is_reported_not_rewritten(self):
        p = self.write("d.md", "plain ascii\n".encode("utf-8"))
        before = p.read_bytes()
        rc, msg = self._quiet(lambda: eh.fix_file("d.md"))
        self.assertEqual(rc, 1)
        self.assertIn("nothing to fix", msg)
        self.assertEqual(p.read_bytes(), before)

    def test_unrepairable_damage_is_refused_with_a_way_out(self):
        """Never guess. Say so, and name a command that recovers the file."""
        p = self.write("e.md", "\u00c3 alone\n".encode("utf-8"))
        before = p.read_bytes()
        rc, msg = self._quiet(lambda: eh.fix_file("e.md"))
        self.assertEqual(rc, 1)
        self.assertIn("git checkout", msg)
        self.assertEqual(p.read_bytes(), before, "must not corrupt what it can't fix")


class MessageContractTest(unittest.TestCase):
    def test_blocking_message_names_hook_file_fix_and_exit(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            eh._report("some/file.md", "not valid UTF-8")
        text = err.getvalue()
        for element in ("some/file.md", "--fix", "git restore --staged",
                        "SKIP=encoding-health", "--no-verify"):
            self.assertIn(element, text)


if __name__ == "__main__":
    unittest.main()
