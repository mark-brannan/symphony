#!/usr/bin/env python3
"""The bash and python mode helpers must not drift apart.

scripts/secretguard.sh and scripts/secretguard.py implement the same
spec twice, in two languages, because guards exist in both. Drift is
invisible until a contributor gets blocked by one guard and waved through by
another on the same clone -- which reads as a broken repo, not a bug in a
helper. So: run both, assert byte-identical answers.

Stdlib unittest, no dependency. Runs in well under a second.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(REPO, "scripts", "secretguard.sh")
PY = os.path.join(REPO, "scripts", "secretguard.py")
MODE_FILE = os.path.join(REPO, ".secretguard-mode")

# Fields exercised by the message-shape test. Deliberately includes two
# `file` entries: repeating that one is the only supported repetition.
MSG_FIELDS = [
    ("problem", "the clean filter did not run"),
    ("file", "signalk/security.json"),
    ("file", "host/boat-heartbeat.json"),
    ("needs", "an age key"),
    ("blocked_by", "pre-commit hook sops-secret-guard"),
    ("fix", "bash scripts/setup-git-filters.sh"),
    ("if_stuck", "git restore --staged <file>"),
    ("see", "RUNBOOK.md, When a hook blocks your commit"),
]


def _env(**overrides):
    env = dict(os.environ)
    for name in (
        "SECRETGUARD_MODE",
        "_secretguard_mode",
        "_secretguard_mode_reason",
        "CI",
        "GITHUB_ACTIONS",
    ):
        env.pop(name, None)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


# start_new_session detaches the controlling terminal, so the helpers'
# "write to /dev/tty when stderr is captured" path can't open one and falls
# back to stderr -- which is what these tests read. Without it the suite
# passes on a headless runner and fails in a developer's terminal.
def _sub(argv, env):
    return subprocess.run(
        argv, cwd=REPO, env=env, capture_output=True, text=True, check=True,
        start_new_session=True,
    )


def _run(argv, env):
    return _sub(argv, env).stdout


def bash_mode(env):
    out = _run(
        ["bash", "-c", ". %s; secretguard_mode; secretguard_mode_reason" % SH], env
    )
    return out.splitlines()


def py_mode(env):
    return [
        _run([sys.executable, PY, "mode"], env).strip(),
        _run([sys.executable, PY, "reason"], env).strip(),
    ]


class ModeParity(unittest.TestCase):
    def assertAgree(self, env, expected_mode=None):
        b, p = bash_mode(env), py_mode(env)
        self.assertEqual(b, p, "bash and python disagree: %r vs %r" % (b, p))
        if expected_mode is not None:
            self.assertEqual(b[0], expected_mode)
        return b

    def test_env_var_forces_strict(self):
        for word in ("strict", "STRICT", " strict "):
            with self.subTest(word=word):
                self.assertAgree(_env(SECRETGUARD_MODE=word), "strict")

    def test_env_var_forces_contributor(self):
        for word in ("contributor", "Contributor"):
            with self.subTest(word=word):
                self.assertAgree(_env(SECRETGUARD_MODE=word), "contributor")

    def test_boolean_words_are_not_a_second_vocabulary(self):
        # SECRETGUARD_MODE names a mode, so it takes a mode word. `=0` and
        # `=1` would be a second vocabulary for the same knob, and `0`
        # meaning "contributor" is exactly the kind of guess a guard should
        # not make about a secret-handling setting. Both twins ignore them
        # and fall through, identically.
        for word in ("1", "0", "true", "false", "on", "off", "maybe"):
            with self.subTest(word=word):
                self.assertAgree(_env(SECRETGUARD_MODE=word))

    def test_ci_is_always_strict(self):
        # CI has no age key and no configured filters, so auto-detection
        # would call it a contributor and wave through exactly the gaps CI
        # exists to catch.
        for name in ("CI", "GITHUB_ACTIONS"):
            with self.subTest(var=name):
                self.assertAgree(_env(**{name: "true"}), "strict")

    def test_ci_beats_an_explicit_override(self):
        # "CI is always strict" is advertised in the README, the RUNBOOK and
        # every guard message, so it has to hold against a SECRETGUARD_MODE
        # that some workflow step sets for an unrelated reason. CI resolves
        # first, in both twins.
        env = _env(CI="true", SECRETGUARD_MODE="contributor")
        self.assertAgree(env, "strict")

    def test_internal_cache_cannot_be_set_from_the_environment(self):
        # The resolved mode is cached in a process-local, `_secretguard_mode`
        # in bash and `_resolved` in python. Neither is an input. The shell
        # twin used to seed its cache from the environment, which made it a
        # second undocumented override that python ignored -- shell guards
        # strict, python guards contributor, inside one `pre-commit run`.
        #
        # Pinned against a contributor baseline rather than checked for
        # parity alone: with no baseline this test would also pass if both
        # twins honored the injected value, and would pass on a maintainer
        # clone where auto-detection resolves strict on its own.
        baseline = self.assertAgree(
            _env(SECRETGUARD_MODE="contributor"), "contributor"
        )
        env = _env(SECRETGUARD_MODE="contributor")
        env["_secretguard_mode"] = "strict"
        env["_secretguard_mode_reason"] = "should be ignored"
        self.assertEqual(bash_mode(env), baseline)
        self.assertEqual(py_mode(env), baseline)

    def test_auto_detect_agrees(self):
        self.assertAgree(_env())

    def test_auto_detect_without_key_is_contributor(self):
        # An unset SOPS_AGE_KEY_FILE and a HOME with no key: whatever the
        # filters say, no key means contributor.
        env = _env(HOME=os.path.join(REPO, "intermediate_files", "no-such-home"))
        env.pop("SOPS_AGE_KEY_FILE", None)
        self.assertAgree(env, "contributor")

    def test_mode_file(self):
        if os.path.exists(MODE_FILE):
            self.skipTest(".secretguard-mode already exists; not clobbering it")
        for word in ("strict", "contributor"):
            with self.subTest(word=word):
                with open(MODE_FILE, "w", encoding="utf-8") as fh:
                    fh.write("# set by test\n%s\n" % word)
                try:
                    self.assertAgree(_env(), word)
                finally:
                    os.unlink(MODE_FILE)


# (label, text, is a real sops document?). The negatives are the point:
# every one of them contains the word "sops" and none of them is encrypted.
SOPS_FIXTURES = [
    ("json real", '{\n  "a": "ENC[x]",\n  "sops": {\n    "mac": "ENC[y]",\n'
                  '    "version": "3.13.3"\n  }\n}', True),
    ("yaml real", "a: ENC[x]\nsops:\n    mac: ENC[y]\n    version: 3.13.3\n",
     True),
    ("json decoy value", '{"note": "sops", "password": "hunter2"}', False),
    ("yaml decoy value", "note: sops\npassword: hunter2\n", False),
    ("json key without metadata", '{"sops": {"note": "not really"}}', False),
    ("yaml key without metadata", "sops:\n    note: not really\n", False),
    ("yaml decoy key not top level", "outer:\n  sops:\n    mac: x\n"
                                     "    version: 1\n", False),
    ("plaintext", '{"password": "hunter2"}', False),
    ("empty", "", False),
]


class SopsDetectionParity(unittest.TestCase):
    """One policy for "is this encrypted", applied by guards in both languages.

    A file that reads as encrypted to the pre-commit guard and plaintext to
    the pre-push one (or the reverse) is worse than either answer alone: the
    commit sails through and the push blocks, or the reverse, and neither
    message explains why the other disagreed.
    """

    def _bash(self, text):
        done = subprocess.run(
            ["bash", "-c",
             ". %s; secretguard_is_sops_encrypted" % SH],
            cwd=REPO, env=_env(), input=text, capture_output=True, text=True,
            start_new_session=True,
        )
        return done.returncode == 0

    def _py(self, text):
        code = (
            "import sys; sys.path.insert(0, %r); import secretguard as m; "
            "sys.exit(0 if m.is_sops_encrypted(sys.stdin.read()) else 1)"
            % os.path.join(REPO, "scripts")
        )
        done = subprocess.run(
            [sys.executable, "-c", code], cwd=REPO, env=_env(), input=text,
            capture_output=True, text=True, start_new_session=True,
        )
        return done.returncode == 0

    def test_fixtures(self):
        for label, text, expected in SOPS_FIXTURES:
            with self.subTest(case=label):
                self.assertEqual(self._py(text), expected, "python")
                self.assertEqual(self._bash(text), expected, "bash")

    def test_the_repo_own_encrypted_files_are_recognized(self):
        # The fixtures are hand-written; these are what sops actually emits.
        import glob

        real = sorted(glob.glob(os.path.join(REPO, "secrets", "*.sops.yaml")))
        self.assertTrue(real, "no encrypted files to check")
        for path in real:
            with self.subTest(path=os.path.basename(path)):
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertTrue(self._py(text))
                self.assertTrue(self._bash(text))


class Destination(unittest.TestCase):
    def test_redirected_stderr_is_appended_not_truncated(self):
        """`> /dev/stderr` reopens the redirect target with O_TRUNC.

        A hook run as `pre-commit run 2>>build.log` would have its message
        destroy everything already in that log. Duplicating FD 2 doesn't.
        """
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
            fh.write("EXISTING LOG LINE\n")
            log = fh.name
        try:
            subprocess.run(
                ["bash", "-c",
                 "exec 2>>%s; . %s; secretguard_msg note t problem=p" % (log, SH)],
                cwd=REPO, env=_env(), check=True, start_new_session=True,
                capture_output=True, text=True,
            )
            with open(log, encoding="utf-8") as fh:
                body = fh.read()
        finally:
            os.unlink(log)
        self.assertIn("EXISTING LOG LINE", body)
        self.assertIn("secretguard note: t", body)

    def test_an_in_process_redirect_of_stderr_captures_the_message(self):
        """A deliberate redirect outranks /dev/tty.

        _dest() prefers a controlling terminal when stderr is not one, so
        that a passing-but-degraded guard still reaches a human through
        pre-commit's capture. Applied blindly that also defeats
        contextlib.redirect_stderr: the message goes to the terminal, the
        caller collects nothing, and any assertion on the text fails --
        but only on a machine that HAS a terminal, so CI stayed green while
        a developer's commit was blocked by a phantom failure with the guard
        blocks dumped into unrelated hook output. Pin the precedence.
        """
        import contextlib
        import io

        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import secretguard

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            secretguard.block("t", problem="p", file="some/file.md")
        self.assertIn("some/file.md", buf.getvalue())
        self.assertIn("secretguard BLOCKED: t", buf.getvalue())

    def test_comments_only_mode_file_does_not_abort_a_set_e_caller(self):
        """pipefail + a grep that matches nothing killed the sourcing script."""
        mode_file = MODE_FILE
        if os.path.exists(mode_file):
            self.skipTest(".secretguard-mode already exists; not clobbering it")
        with open(mode_file, "w", encoding="utf-8") as fh:
            fh.write("# only a comment\n\n")
        try:
            done = subprocess.run(
                ["bash", "-c",
                 "set -euo pipefail; . %s; secretguard_mode" % SH],
                cwd=REPO, env=_env(), capture_output=True, text=True,
                start_new_session=True,
            )
        finally:
            os.unlink(mode_file)
        self.assertEqual(done.returncode, 0, done.stderr)
        # A comments-only file yields no mode, so the mode comes from
        # auto-detection -- which legitimately differs per machine (strict
        # where an age key and the filters are present, contributor where
        # they are not). Pinning "contributor" here made this test fail on
        # exactly the machines the strict path exists for. What this test is
        # actually about is the returncode above; all this needs to add is
        # that a real mode still came out.
        self.assertIn(done.stdout.strip(), ("strict", "contributor"), done.stderr)


class FindSops(unittest.TestCase):
    """find_sops is what stands between a working sops and a failed checkout.

    Every case here builds its own fake sops, so the result never depends on
    whether the host running the tests happens to have the real one.
    """

    def setUp(self):
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import secretguard

        self.secretguard = secretguard
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

        # Restore whatever the suite was run with, whichever way we exit.
        self.addCleanup(os.environ.__setitem__, "PATH", os.environ["PATH"])
        self.addCleanup(
            setattr, secretguard, "_SOPS_DIRS", secretguard._SOPS_DIRS
        )

    def _fake_sops(self, name="sops", executable=True):
        directory = tempfile.mkdtemp(dir=self.tmp)
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o755 if executable else 0o644)
        return directory, path

    def test_path_wins_over_the_fallback_dirs(self):
        """A sops the caller can already reach is the one we should run."""
        on_path, expected = self._fake_sops()
        fallback, _ = self._fake_sops()
        os.environ["PATH"] = on_path
        self.secretguard._SOPS_DIRS = (fallback,)
        self.assertEqual(self.secretguard.find_sops(), expected)

    def test_falls_back_when_path_does_not_have_it(self):
        """The whole point: PATH misses, sops is installed, we still find it."""
        fallback, expected = self._fake_sops()
        os.environ["PATH"] = ""
        self.secretguard._SOPS_DIRS = (fallback,)
        self.assertEqual(self.secretguard.find_sops(), expected)

    def test_non_executable_candidate_is_not_sops(self):
        """A readable file named sops is not something we can run."""
        fallback, _ = self._fake_sops(executable=False)
        os.environ["PATH"] = ""
        self.secretguard._SOPS_DIRS = (fallback,)
        self.assertEqual(self.secretguard.find_sops(), "")

    def test_directory_named_sops_is_not_sops(self):
        """isfile, not exists -- a directory would pass a bare exists check."""
        fallback = tempfile.mkdtemp(dir=self.tmp)
        os.mkdir(os.path.join(fallback, "sops"))
        os.environ["PATH"] = ""
        self.secretguard._SOPS_DIRS = (fallback,)
        self.assertEqual(self.secretguard.find_sops(), "")

    def test_nothing_anywhere_is_empty_not_a_guess(self):
        """Callers treat "" as 'blocked'; it must never be a bare "sops"."""
        os.environ["PATH"] = ""
        self.secretguard._SOPS_DIRS = (os.path.join(self.tmp, "nonexistent"),)
        self.assertEqual(self.secretguard.find_sops(), "")

    def test_first_matching_dir_wins(self):
        """Order in _SOPS_DIRS is a preference, so it has to be honoured."""
        first, expected = self._fake_sops()
        second, _ = self._fake_sops()
        os.environ["PATH"] = ""
        self.secretguard._SOPS_DIRS = (first, second)
        self.assertEqual(self.secretguard.find_sops(), expected)

    def test_locations_message_lists_every_dir_searched(self):
        """The `needs:` line must not send anyone somewhere we don't look."""
        message = self.secretguard.sops_locations()
        self.assertIn("PATH", message)
        for directory in self.secretguard._SOPS_DIRS:
            self.assertIn(directory, message)


class CanDecryptParity(unittest.TestCase):
    """mode() and can_decrypt() are different questions, in both languages.

    Strict answers "how rigorously to enforce"; can_decrypt answers "does
    this machine hold a runnable sops and an age key". CI is strict while
    holding neither, by design, so a twin that conflates them blocks a
    keyless runner on a capability it is never going to have. Every case
    builds its own fake sops and key, pins CI=true so mode resolves strict
    everywhere, and asserts the twins give the same yes/no.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # A controlled PATH still has to let the child find bash itself --
        # replacing PATH wholesale made the bash twin unrunnable, which
        # reads as a parity failure and is actually a broken test harness.
        self.toolbox = tempfile.mkdtemp(dir=self.tmp)
        os.symlink(shutil.which("bash"), os.path.join(self.toolbox, "bash"))

    def _path(self, *dirs):
        return os.pathsep.join(list(dirs) + [self.toolbox])

    def _fake_sops_dir(self):
        directory = tempfile.mkdtemp(dir=self.tmp)
        path = os.path.join(directory, "sops")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o755)
        return directory

    def _fake_key(self):
        path = os.path.join(self.tmp, "keys.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# stands in for an age key; existence is the test\n")
        return path

    # Both twins get their fallback-directory list emptied, the same way
    # FindSops monkeypatches the python one -- otherwise a real sops in
    # /usr/bin would decide these cases on exactly the machines the strict
    # path exists for.
    def _bash(self, env):
        done = subprocess.run(
            ["bash", "-c",
             ". %s; _secretguard_sops_dirs() { :; }; "
             "secretguard_can_decrypt" % SH],
            cwd=REPO, env=env, capture_output=True, text=True,
            start_new_session=True,
        )
        return done.returncode == 0

    def _py(self, env):
        code = (
            "import sys; sys.path.insert(0, %r); import secretguard as m; "
            "m._SOPS_DIRS = (); sys.exit(0 if m.can_decrypt() else 1)"
            % os.path.join(REPO, "scripts")
        )
        done = subprocess.run(
            [sys.executable, "-c", code], cwd=REPO, env=env,
            capture_output=True, text=True, start_new_session=True,
        )
        return done.returncode == 0

    def assertBothSay(self, env, expected):
        self.assertEqual(self._py(env), expected, "python")
        self.assertEqual(self._bash(env), expected, "bash")

    def test_sops_and_key_present_is_yes_even_in_strict(self):
        env = _env(CI="true", PATH=self._path(self._fake_sops_dir()),
                   SOPS_AGE_KEY_FILE=self._fake_key())
        self.assertBothSay(env, True)

    def test_no_key_is_no_even_though_ci_is_strict(self):
        # The defect this predicate exists to fix: CI resolves strict and
        # holds no key, and "strict" must not be read as "keys exist here".
        env = _env(CI="true", PATH=self._path(self._fake_sops_dir()),
                   SOPS_AGE_KEY_FILE=None)
        env["HOME"] = os.path.join(REPO, "intermediate_files", "no-such-home")
        self.assertBothSay(env, False)

    def test_no_sops_is_no_whatever_the_key_says(self):
        env = _env(CI="true", PATH=self._path(), SOPS_AGE_KEY_FILE=self._fake_key())
        self.assertBothSay(env, False)

    def test_find_sops_resolves_the_same_path_in_both_languages(self):
        directory = self._fake_sops_dir()
        env = _env(PATH=self._path(directory))
        from_bash = _run(
            ["bash", "-c", ". %s; secretguard_find_sops" % SH], env
        ).strip()
        code = (
            "import sys; sys.path.insert(0, %r); import secretguard as m; "
            "print(m.find_sops())" % os.path.join(REPO, "scripts")
        )
        from_py = _run([sys.executable, "-c", code], env).strip()
        self.assertEqual(from_bash, from_py)
        self.assertEqual(from_bash, os.path.join(directory, "sops"))

    def test_locations_text_is_byte_identical(self):
        # The bash text is hand-written and the python one is generated from
        # _SOPS_DIRS, so this equality is what keeps the two search lists
        # from drifting apart.
        env = _env()
        from_bash = _run(
            ["bash", "-c", ". %s; secretguard_sops_locations" % SH], env
        ).strip()
        code = (
            "import sys; sys.path.insert(0, %r); import secretguard as m; "
            "print(m.sops_locations())" % os.path.join(REPO, "scripts")
        )
        from_py = _run([sys.executable, "-c", code], env).strip()
        self.assertEqual(from_bash, from_py)


class MessageParity(unittest.TestCase):
    def test_same_message_shape(self):
        env = _env(SECRETGUARD_MODE="strict")
        args = " ".join("'%s=%s'" % kv for kv in MSG_FIELDS)
        from_bash = subprocess.run(
            ["bash", "-c", ". %s; secretguard_msg BLOCKED 'a title' %s" % (SH, args)],
            cwd=REPO, env=env, capture_output=True, text=True, check=True,
            start_new_session=True,
        ).stderr

        sys.path.insert(0, os.path.join(REPO, "scripts"))
        code = (
            "import sys; sys.path.insert(0, %r); import secretguard as m; "
            "print(m.format('BLOCKED', 'a title', problem=%r, file=%r, "
            "needs=%r, blocked_by=%r, fix=%r, if_stuck=%r, see=%r))"
            % (
                os.path.join(REPO, "scripts"),
                MSG_FIELDS[0][1],
                [MSG_FIELDS[1][1], MSG_FIELDS[2][1]],
                MSG_FIELDS[3][1],
                MSG_FIELDS[4][1],
                MSG_FIELDS[5][1],
                MSG_FIELDS[6][1],
                MSG_FIELDS[7][1],
            )
        )
        from_py = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO, env=env, capture_output=True, text=True, check=True,
            start_new_session=True,
        ).stdout

        self.assertEqual(from_bash, from_py)
        self.assertIn("mode:       strict", from_bash)

    def test_mode_line_is_always_present(self):
        # The whole point of auto-detection being acceptable: it is never
        # silent. No message may omit which mode produced it.
        env = _env()
        out = subprocess.run(
            ["bash", "-c", ". %s; secretguard_msg note 'x' problem=y" % SH],
            cwd=REPO, env=env, capture_output=True, text=True, check=True,
            start_new_session=True,
        ).stderr
        self.assertIn("  mode:       ", out)


if __name__ == "__main__":
    unittest.main()
