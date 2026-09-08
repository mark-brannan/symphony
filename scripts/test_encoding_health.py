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
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class AllowMarkerTest(unittest.TestCase):
    """The exemption a file can declare, and the one it cannot.

    ALLOW_MARKER downgrades a mojibake finding to a note, because
    reference/precommit_guards.md legitimately quotes mangled text as
    examples. It must NOT exempt a file that is invalid UTF-8: those are
    bad bytes, not a quoted example, and no declaration in a file makes
    the file decodable. Only the second case is easy to break -- moving
    the marker test earlier in check_repo would silently grant an
    exemption the design forbids, and nothing else here would notice.
    """

    def run_check(self, raw):
        """check_repo over exactly one in-memory fixture, stdout captured.

        The path is under ROOT but never written: check_repo takes its bytes
        from the generator, so nothing here touches the real checkout.
        """
        path = eh.ROOT / "fixture-not-on-disk.md"
        real = eh.tracked_text_files
        eh.tracked_text_files = lambda only=None: iter([(path, raw)])
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()):
                return eh.check_repo(), out.getvalue()
        finally:
            eh.tracked_text_files = real

    def test_declared_mojibake_does_not_block(self):
        damaged = mangle("caf\u00e9")
        raw = ("a " + damaged + " example\n" + eh.ALLOW_MARKER + "\n").encode("utf-8")
        rc, out = self.run_check(raw)
        self.assertEqual(rc, 0, "a declared example must not block")
        self.assertIn("allowed", out)

    def test_undeclared_mojibake_blocks(self):
        raw = ("a " + mangle("caf\u00e9") + " accident\n").encode("utf-8")
        rc, _ = self.run_check(raw)
        self.assertEqual(rc, 1)

    def test_declaring_the_marker_cannot_exempt_invalid_utf8(self):
        """Bad bytes are not a quoted example. No file may opt out of this."""
        raw = "caf\u00e9\n".encode("latin-1") + eh.ALLOW_MARKER.encode("utf-8")
        rc, _ = self.run_check(raw)
        self.assertEqual(rc, 1, "invalid UTF-8 must block even when declared")


class StagedScopeReadsTheIndexTest(unittest.TestCase):
    """Scoped runs must judge what git will record, not what is on disk.

    They differ after `git add -p`, or after staging a file and editing on.
    Reading the working tree gets it wrong in both directions: a commit
    whose recorded bytes are damaged can pass, and a commit that contains
    nothing wrong can be blocked.
    """

    def test_scoped_run_reads_the_staged_blob(self):
        """Both halves pinned: ls-files is stubbed too, so this cannot pass
        by yielding nothing at all -- which is exactly how the first version
        of this test passed while checking nothing."""
        seen = []

        class FakeLsFiles:
            stdout = "doc.md\0other.md\0"
            returncode = 0

        real_run, real_blob = eh.subprocess.run, eh.staged_blob
        eh.subprocess.run = lambda *a, **k: FakeLsFiles()
        eh.staged_blob = lambda name: seen.append(name) or b"from the index\n"
        try:
            files = list(eh.tracked_text_files(only={"doc.md"}))
        finally:
            eh.subprocess.run, eh.staged_blob = real_run, real_blob

        self.assertEqual(seen, ["doc.md"], "must read the staged blob, once")
        self.assertEqual([(p.name, raw) for p, raw in files],
                         [("doc.md", b"from the index\n")])

    def test_unscoped_run_reads_the_working_tree(self):
        """--repo is a statement about the files on disk, so it reads them."""
        real_run, real_blob = eh.subprocess.run, eh.staged_blob
        eh.staged_blob = lambda name: self.fail("--repo must not read the index")
        try:
            list(eh.tracked_text_files(only=None))
        finally:
            eh.subprocess.run, eh.staged_blob = real_run, real_blob


class CLocaleDoesNotBreakPathsTest(unittest.TestCase):
    """A C locale must not turn a non-ASCII path into a traceback.

    git emits paths as UTF-8 bytes. `text=True` alone decodes with whatever
    the locale says, and under LC_ALL=C with PEP 538 coercion disabled that
    is ASCII -- so `caf\u00e9.md` raised UnicodeDecodeError and took the hook
    down with it. Pinned by running a real subprocess under that exact
    environment, because the thing under test is how python and git agree
    on bytes, which no stub can tell us.
    """

    def test_staged_paths_survives_an_ascii_locale(self):
        name = "caf\u00e9.sops.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            run = lambda *c: subprocess.run(c, cwd=tmp, capture_output=True, env=CLEAN_ENV)
            run("git", "init", "-q", ".")
            run("git", "config", "user.email", "t@example.com")
            run("git", "config", "user.name", "t")
            (Path(tmp) / name).write_text("x\n", encoding="utf-8")
            run("git", "add", name)

            script = (
                "import sys; sys.path.insert(0, %r)\n"
                "import check_encoding_health as eh\n"
                "from pathlib import Path\n"
                "eh.ROOT = Path(%r)\n"
                "print(sorted(eh.staged_paths()))\n"
                % (str(Path(__file__).resolve().parent), tmp)
            )
            hostile = {
                **CLEAN_ENV,
                "LC_ALL": "C", "LANG": "C",
                "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0",
            }
            done = subprocess.run([sys.executable, "-c", script],
                                  capture_output=True, text=True, env=hostile)

        self.assertEqual(done.returncode, 0,
                         f"staged_paths died under a C locale:\n{done.stderr}")
        self.assertIn(name, done.stdout,
                      "the non-ASCII path must survive an ASCII locale")


# git exports GIT_DIR and GIT_INDEX_FILE into hook environments, so a test
# building its own temp repo drives the real one instead when run from a
# commit -- staging its fixture there and failing on the real index.
GIT_ENV = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY")
CLEAN_ENV = {k: v for k, v in os.environ.items() if k not in GIT_ENV}


class NonAsciiPathsStayInScopeTest(unittest.TestCase):
    """git quotes any path outside plain ASCII unless asked for -z.

    Without it `caf\u00e9.md` arrives as a quoted display string, matches no
    covered path, and drops out of the guard's scope silently -- the guard
    reports ok on a file it never looked at. Run against real git rather
    than a stub, because the thing being pinned is git's own behaviour.
    """

    def test_a_non_ascii_staged_path_is_returned_verbatim(self):
        name = "caf\u00e9-\u00e5\u00df.md"
        with tempfile.TemporaryDirectory() as tmp:
            run = lambda *c: subprocess.run(c, cwd=tmp, capture_output=True, env=CLEAN_ENV)
            run("git", "init", "-q", ".")
            run("git", "config", "user.email", "t@example.com")
            run("git", "config", "user.name", "t")
            (Path(tmp) / name).write_text("x\n", encoding="utf-8")
            run("git", "add", name)

            real_root = eh.ROOT
            eh.ROOT = Path(tmp)
            try:
                with mock.patch.dict(os.environ, CLEAN_ENV, clear=True):
                    staged = eh.staged_paths()
            finally:
                eh.ROOT = real_root

        self.assertEqual(staged, {name},
                         "a non-ASCII covered path must not fall out of scope")


class MessageContractTest(unittest.TestCase):
    def test_blocking_message_names_hook_file_fix_and_exit(self):
        # secretguard._dest() writes to /dev/tty instead of stderr whenever
        # sys.stderr isn't itself a terminal -- so a hook's message still
        # reaches the user even though pre-commit captured stdout/stderr
        # into pipes. That check re-fires here: redirect_stderr swaps in a
        # StringIO, which also isn't a tty, so an unpatched call escapes to
        # the real /dev/tty and `err` stays empty -- passing on a headless
        # runner and failing on a real terminal. test_secretguard.py hits
        # the same thing for its subprocess calls and works around it with
        # start_new_session; there's no subprocess here, so force stderr.
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(eh.secretguard, "_dest", lambda: sys.stderr):
            eh._report("some/file.md", "not valid UTF-8")
        text = err.getvalue()
        for element in ("some/file.md", "--fix", "git restore --staged",
                        "SKIP=encoding-health", "--no-verify"):
            self.assertIn(element, text)


if __name__ == "__main__":
    unittest.main()
