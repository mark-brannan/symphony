#!/usr/bin/env python3
"""Unit tests for scripts/pseudonymize.py.

Run: python3 scripts/test_pseudonymize.py
"""
import json
import os
import re
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pseudonymize as p

SALT = b"test-salt-not-the-real-one"
OTHER_SALT = b"a-different-salt"

# A realistic mixed user block: a GitHub login (handle, no address in
# username), a Google login (address in both fields), and a guest. Tab
# indentation on purpose -- it is what SignalK writes, and preserving it is
# the reason substitution is textual.
USERS = [
    {
        "username": "mark-brannan",
        "type": "admin",
        "oidc": {"sub": "CggxNTgxMTY1MBIGZ2l0aHVi", "email": "markbrannan@gmail.com"},
    },
    {
        "username": "markbrannan@gmail.com",
        "type": "admin",
        "oidc": {"sub": "ChUxMTQ5NjEx", "email": "markbrannan@gmail.com"},
    },
    {
        "username": "paranoid-friend@yahoo.com",
        "type": "readonly",
        "oidc": {"sub": "ChUyMjg4", "email": "paranoid-friend@yahoo.com"},
    },
]
USERS_JSON = json.dumps(USERS, indent="\t")


class TestDerive(unittest.TestCase):
    def test_stable_across_calls(self):
        self.assertEqual(p.derive("a@b.com", SALT), p.derive("a@b.com", SALT))

    def test_distinct_addresses_get_distinct_tokens(self):
        self.assertNotEqual(p.derive("a@b.com", SALT), p.derive("c@b.com", SALT))

    def test_salt_changes_the_token(self):
        self.assertNotEqual(p.derive("a@b.com", SALT), p.derive("a@b.com", OTHER_SALT))

    def test_case_and_whitespace_normalized(self):
        self.assertEqual(p.derive("  A@B.CoM ", SALT), p.derive("a@b.com", SALT))

    def test_domain_preserved(self):
        self.assertTrue(p.derive("someone@yahoo.com", SALT).endswith("@yahoo.com"))

    def test_missing_salt_refuses(self):
        for empty in (None, "", b""):
            with self.assertRaises(ValueError):
                p.derive("a@b.com", empty)

    def test_token_local_part_is_a_valid_address(self):
        """`:` is not RFC 5322 atext -- a token must survive email validation.

        This is the whole reason the prefix is `pid.` and not `pid:`.
        """
        atext = re.compile(r"^[A-Za-z0-9!#$%&'*+\-/=?^_`{|}~.]+$")
        local = p.derive("someone@yahoo.com", SALT).rsplit("@", 1)[0]
        self.assertRegex(local, atext)

    def test_carries_the_do_not_mail_guard(self):
        self.assertIn("+invalid@", p.derive("someone@yahoo.com", SALT))


class TestPseudonymize(unittest.TestCase):
    def setUp(self):
        self.mapping = {}

    def convert(self, text=None):
        out, added = p.pseudonymize(text or USERS_JSON, SALT, self.mapping)
        return out, added, json.loads(out)

    def test_non_email_values_untouched(self):
        _, _, users = self.convert()
        self.assertEqual(users[0]["username"], "mark-brannan")
        self.assertEqual(users[0]["type"], "admin")

    def test_sub_untouched(self):
        _, _, users = self.convert()
        for original, result in zip(USERS, users):
            self.assertEqual(result["oidc"]["sub"], original["oidc"]["sub"])

    def test_addresses_replaced_wherever_they_sit(self):
        _, _, users = self.convert()
        self.assertTrue(p.is_token(users[1]["username"]))
        self.assertTrue(p.is_token(users[1]["oidc"]["email"]))
        self.assertTrue(p.is_token(users[2]["username"]))

    def test_same_address_gets_one_token_everywhere(self):
        _, _, users = self.convert()
        self.assertEqual(users[0]["oidc"]["email"], users[1]["username"])
        self.assertEqual(users[1]["username"], users[1]["oidc"]["email"])

    def test_formatting_preserved_outside_the_addresses(self):
        """Everything but the addresses must survive byte-for-byte.

        A structural round-trip through json.dumps would reformat the whole
        file and make every commit a whole-file diff.
        """
        out, _, _ = self.convert()
        strip = lambda t: p.QUOTED_EMAIL_RE.sub('""', p.QUOTED_TOKEN_RE.sub('""', t))
        self.assertEqual(strip(out), strip(USERS_JSON))

    def test_reports_newly_added_addresses(self):
        _, added, _ = self.convert()
        self.assertEqual(
            sorted(set(added)), ["markbrannan@gmail.com", "paranoid-friend@yahoo.com"]
        )

    def test_known_addresses_are_not_reported_again(self):
        self.convert()
        _, added, _ = self.convert()
        self.assertEqual(added, [])

    def test_map_holds_token_to_address(self):
        self.convert()
        token = p.derive("paranoid-friend@yahoo.com", SALT)
        self.assertEqual(self.mapping[token], "paranoid-friend@yahoo.com")

    def test_idempotent(self):
        once, _, _ = self.convert()
        twice, added, _ = self.convert(once)
        self.assertEqual(once, twice)
        self.assertEqual(added, [])

    def test_collision_raises_rather_than_overwriting(self):
        token = p.derive("first@example.com", SALT)
        self.mapping[token] = "somebody-else@example.com"
        with self.assertRaises(p.CollisionError):
            p.pseudonymize('{"e": "first@example.com"}', SALT, self.mapping)


class TestDepseudonymize(unittest.TestCase):
    def test_round_trip_is_byte_identical(self):
        mapping = {}
        out, _ = p.pseudonymize(USERS_JSON, SALT, mapping)
        back, unresolved = p.depseudonymize(out, mapping)
        self.assertEqual(back, USERS_JSON)
        self.assertEqual(unresolved, [])

    def test_missing_map_leaves_tokens_and_reports_them(self):
        mapping = {}
        out, _ = p.pseudonymize(USERS_JSON, SALT, mapping)
        back, unresolved = p.depseudonymize(out, {})
        self.assertEqual(back, out)
        self.assertTrue(unresolved)
        self.assertTrue(all(p.is_token(t) for t in unresolved))

    def test_partial_map_resolves_what_it_can(self):
        mapping = {}
        out, _ = p.pseudonymize(USERS_JSON, SALT, mapping)
        token = p.derive("paranoid-friend@yahoo.com", SALT)
        back, _ = p.depseudonymize(out, {token: mapping[token]})
        users = json.loads(back)
        self.assertEqual(users[2]["username"], "paranoid-friend@yahoo.com")
        self.assertTrue(p.is_token(users[1]["username"]))


class TestMask(unittest.TestCase):
    def test_keeps_ends_and_domain(self):
        self.assertEqual(p.mask("paranoid-friend@yahoo.com"), "p*****d@yahoo.com")

    def test_hides_local_part_length(self):
        short = p.mask("abc@x.com")
        long = p.mask("a-considerably-longer-one@x.com")
        self.assertEqual(len(short), len(long))

    def test_short_local_part_reveals_nothing(self):
        self.assertEqual(p.mask("jd@navy.mil"), "******@navy.mil")

    def test_never_contains_the_full_local_part(self):
        self.assertNotIn("paranoid-friend", p.mask("paranoid-friend@yahoo.com"))


class TestStore(unittest.TestCase):
    def test_real_store_decrypts_and_has_a_salt(self):
        # The only test here that touches the real encrypted store, so the
        # only one that needs sops and a key. On a clone that has neither
        # it used to error on import of the sops binary and fail the whole
        # secret-tooling-tests hook -- i.e. block a contributor's commit
        # over a capability they are not expected to have. Strict mode
        # still runs it: a machine that holds secrets must be able to open
        # them.
        import secretguard

        if secretguard.mode() != "strict" and (
            not shutil.which("sops") or not secretguard.have_age_key()
        ):
            self.skipTest(
                "no sops on PATH or no age key, and this clone is in "
                "contributor mode"
            )
        try:
            salt, mapping = p.load_store()
        except p.StoreUnavailable as error:
            # "I could not check this" and "I checked and it is wrong" are
            # different results. Reporting the first as the second trains
            # people to ignore the suite.
            if secretguard.mode() == "strict":
                raise
            self.skipTest(f"the store is not openable here ({error})")
        self.assertTrue(salt)
        self.assertIsInstance(mapping, dict)


class TestConfig(unittest.TestCase):
    def test_covered_paths_are_also_wired_to_the_filter(self):
        """A covered file that isn't `filter=sops` would commit in cleartext."""
        attributes = os.path.join(p.REPO, ".gitattributes")
        with open(attributes) as f:
            filtered = {
                line.split()[0]
                for line in f
                if line.strip() and "filter=sops" in line
            }
        for path in p.load_paths():
            self.assertIn(path, filtered, f"{path} is covered but not filter=sops")


if __name__ == "__main__":
    unittest.main(verbosity=2)
