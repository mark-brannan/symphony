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
import subprocess
import sys
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
        self.assertIn("contributor", done.stdout)


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
