#!/usr/bin/env python3
"""
Stable, short pseudonyms for email addresses in config files.

Anyone who logs into the boat via OIDC has their identity written into
`signalk/security.json` by SignalK itself. GitHub logins arrive as a handle
(`mark-brannan`) and stay legible on purpose -- knowing who had access is a
feature. Google logins have no handle, so SignalK falls back to the email
address, which lands in BOTH `username` and `oidc.email`. That address is a
live mailbox, and publishing a guest's mailbox is not the same thing as
recording that they were aboard.

This module replaces email-shaped values with a short deterministic token:

    paranoid-friend@yahoo.com  ->  pid.t8tym9m+invalid@yahoo.com

and keeps a `token -> address` map so the substitution can be undone.

Why this and not sops
---------------------
The values here are not secrets, they are identifiers, and identifiers have
to stay *comparable*. A sops ENC[...] blob is ~200 characters, re-randomizes
on every write, and cannot be matched against anything. A token is short,
stable forever, and greppable, so `git log -S 'pid.t8tym9m'` still answers
"when did this person first get access, and when did it go away."

Value-shaped, not key-shaped
----------------------------
`.sops.yaml` selects what to encrypt by *key name* (`encrypted_regex`).
That approach cannot work here. The address lands in `username` for Google
logins, and no key-name rule matches that `username` without also matching
`mark-brannan`. So the rule here matches on the *value*: any string that
parses as an email address, in a covered file, whatever field holds it.

That self-selects exactly right, with no per-user configuration:

    mark-brannan               -> untouched, still legible
    markbrannan@gmail.com      -> tokenized
    paranoid-friend@yahoo.com  -> tokenized in both fields, same token

Out of scope, deliberately: `oidc.sub`, `oidc.name`, and non-email
usernames. `sub` is left alone because it is self-regulating today -- the
GitHub subject decodes to a public profile we are content to expose, and the
Google subject has no public resolver. Both are Dex connector properties,
not guarantees; see reference/software_stack.md before adding a connector.

The salt is secret and load-bearing
-----------------------------------
A 7-character hash of a `@gmail.com` address falls to a dictionary attack in
seconds if the salt is known or absent. The salt is what makes the token a
pseudonym rather than an encoding, so there is no default and no fallback:
callers must supply one, and a missing salt is an error rather than a quiet
downgrade to a guessable token.
"""
import hashlib
import os
import re
import subprocess
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO, ".pseudonyms.yaml")
STORE = os.path.join(REPO, "secrets", "pseudonyms.sops.yaml")

# The store is rewritten from scratch whenever the filter learns a new
# address, so its comments cannot live in the file -- they would be lost on
# the first write. They live here instead, and this is their only copy.
STORE_HEADER = """\
# Salt and token -> address map for scripts/pseudonymize.py.
#
# GENERATED. The clean filter rewrites this file whenever it meets an
# address it has not seen; edits to anything but the values will be lost.
# Open it with:  sops secrets/pseudonyms.sops.yaml
#
# The salt is load-bearing and secret. A 7-character hash of a @gmail.com
# address falls to a dictionary attack in seconds if the salt is known or
# absent, so the salt is what makes a token a pseudonym rather than an
# encoding. Changing it invalidates every token already committed -- there
# is no reason to rotate it on a schedule, and good reason not to.
#
# The map keys (tokens) stay legible in the encrypted file on purpose: they
# are the published half. Only the addresses become ciphertext.
"""

# Crockford base32: no I, L, O or U, so a token read aloud or copied out of a
# terminal cannot be transcribed into a different one.
ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
TOKEN_CHARS = 7

# `+invalid` is not decoration. These tokens are meant to be published, and
# the guard tells a stranger reading the file not to try mailing it without
# needing a legend. `.` rather than `:` after the prefix because `:` is not
# valid in an RFC 5322 local part -- `pid:x@gmail.com` fails address
# validation, which would defeat the reason the domain is preserved at all.
PREFIX = "pid."
GUARD = "+invalid"

# Substitution is textual, not structural, and that is deliberate. SignalK
# writes security.json with tab indentation and its own key ordering;
# round-tripping it through json.loads/json.dumps would reformat the entire
# file and turn every commit into a whole-file diff. Matching quoted JSON
# string values in the raw text preserves the file byte-for-byte apart from
# the addresses themselves.
#
# Deliberately loose. It over-matches slightly (any `x@y.tld` shape), which
# is the safe direction: a false positive pseudonymizes something harmless,
# a false negative publishes a mailbox.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
QUOTED_EMAIL_RE = re.compile(r'"([^"@\s]+@[^"@\s]+\.[A-Za-z]{2,})"')

TOKEN_RE = re.compile(
    r"^" + re.escape(PREFIX) + f"[{ALPHABET}]{{{TOKEN_CHARS}}}" + re.escape(GUARD) + r"@"
)
QUOTED_TOKEN_RE = re.compile(
    r'"(' + re.escape(PREFIX) + f"[{ALPHABET}]{{{TOKEN_CHARS}}}"
    + re.escape(GUARD) + r'@[^"@\s]+)"'
)


class CollisionError(Exception):
    """Two different addresses derived the same token."""


class StoreUnavailable(Exception):
    """The salt/map store could not be decrypted."""


def load_store():
    """Decrypt the store. Returns `(salt, {token: address})`.

    Raises StoreUnavailable rather than returning empty defaults. An empty
    salt would silently produce guessable tokens, and an empty map during
    smudge would silently leave tokens in the working tree for SignalK to
    write back as if they were real addresses.
    """
    result = subprocess.run(
        ["sops", "--decrypt", STORE], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise StoreUnavailable(
            f"cannot decrypt {os.path.relpath(STORE, REPO)}: "
            f"{result.stderr.strip() or 'no age identity available'}"
        )
    doc = yaml.safe_load(result.stdout) or {}
    salt = doc.get("salt")
    if not salt:
        raise StoreUnavailable(f"{os.path.relpath(STORE, REPO)} has no salt")
    return salt, doc.get("map") or {}


def save_store(salt, mapping):
    """Re-encrypt the store with an updated map.

    Plaintext is piped straight into sops and never lands on disk -- an
    interrupted write must not be able to leave the addresses in the clear.
    """
    body = yaml.safe_dump(
        {"salt": salt, "map": dict(sorted(mapping.items()))},
        default_flow_style=False,
        sort_keys=False,
    )
    result = subprocess.run(
        ["sops", "--encrypt", "--filename-override", STORE, "/dev/stdin"],
        input=STORE_HEADER + body,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise StoreUnavailable(f"cannot re-encrypt the store: {result.stderr.strip()}")
    with open(STORE, "w") as f:
        f.write(result.stdout)


def load_paths():
    """Repo-relative paths whose email-shaped values get pseudonymized."""
    with open(CONFIG) as f:
        config = yaml.safe_load(f) or {}
    return config.get("paths", []) or []


def is_token(value):
    """True if `value` is already one of our tokens.

    Load-bearing for idempotence: a token is itself email-shaped, so without
    this check a second pass would happily pseudonymize the pseudonym.
    """
    return isinstance(value, str) and bool(TOKEN_RE.match(value))


def derive(email, salt):
    """`paranoid-friend@yahoo.com` -> `pid.t8tym9m+invalid@yahoo.com`.

    Keyed blake2b, not a bare digest: the salt is a MAC key, so knowing the
    algorithm without the key buys nothing.
    """
    if not salt:
        raise ValueError("refusing to derive a token without a salt")
    if isinstance(salt, str):
        salt = salt.encode()
    # Normalize once and derive BOTH halves from the result. Taking the
    # domain off the raw input instead would give `A@B.CoM` and `a@b.com`
    # the same hash but different token strings, and the map is keyed on the
    # whole token -- so one address would occupy two entries and stop
    # round-tripping.
    address = email.strip().lower()
    digest = hashlib.blake2b(address.encode(), key=salt, digest_size=16)
    value = int.from_bytes(digest.digest()[:5], "big")
    chars = ""
    for _ in range(TOKEN_CHARS):
        chars = ALPHABET[value & 31] + chars
        value >>= 5
    domain = address.rsplit("@", 1)[1]
    return f"{PREFIX}{chars}{GUARD}@{domain}"


def mask(email):
    """`paranoid-friend@yahoo.com` -> `p*****d@yahoo.com`, for log lines.

    Fixed width rather than true length: the length of a local part, given
    the domain, meaningfully narrows a guess. First and last character is
    enough to recognize someone you were expecting, which is all the warning
    needs to do -- the token beside it is the durable handle.
    """
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{'*' * 6}@{domain}"
    return f"{local[0]}{'*' * 5}{local[-1]}@{domain}"


def pseudonymize(text, salt, mapping):
    """Replace email-shaped JSON string values in `text` with tokens.

    `mapping` is `{token: address}` and is mutated in place: SignalK writes
    security.json itself, so a new address turning up mid-commit is the
    normal case, not an error. Returns the rewritten text and the addresses
    newly added, so the caller can warn about them.
    """
    reverse = {address: token for token, address in mapping.items()}
    added = []

    def convert(match):
        value = match.group(1)
        if is_token(value):
            return match.group(0)
        address = value.strip().lower()
        if address in reverse:
            return f'"{reverse[address]}"'
        token = derive(address, salt)
        if mapping.get(token, address) != address:
            raise CollisionError(
                f"token {token} already maps to a different address, cannot also "
                f"map to {mask(address)} -- this should be impossible; do not "
                "resolve it by overwriting the map."
            )
        mapping[token] = address
        reverse[address] = token
        added.append(address)
        return f'"{token}"'

    return QUOTED_EMAIL_RE.sub(convert, text), added


def depseudonymize(text, mapping):
    """Replace tokens in `text` with the addresses they stand for.

    Returns the rewritten text and any tokens that were not in the map.
    Unresolved tokens are left as-is rather than raising: that is exactly
    what a clone without the map looks like, and it needs to be reported
    clearly rather than as a stack trace in the middle of a checkout.
    """
    unresolved = []

    def convert(match):
        token = match.group(1)
        if token not in mapping:
            unresolved.append(token)
            return match.group(0)
        return f'"{mapping[token]}"'

    return QUOTED_TOKEN_RE.sub(convert, text), unresolved


def main():
    """Small CLI. `paths` feeds the pre-commit guard; `resolve` is for you.

    Resolving a token needs the store, so it needs an age identity -- which
    is the point: the token is publishable, the address behind it is not.
    """
    args = sys.argv[1:]
    if args[:1] == ["paths"]:
        for path in load_paths():
            print(path)
        return 0
    if args[:1] == ["resolve"] and len(args) == 2:
        _, mapping = load_store()
        token = args[1]
        # Accept either the full token or just the `pid.xxxxxxx` part, which
        # is what someone reading a diff or a log line is likely to copy.
        for key, address in mapping.items():
            if token in (key, key.split(GUARD)[0]):
                print(address)
                return 0
        print(f"no such token: {token}", file=sys.stderr)
        return 1
    print(
        "usage: pseudonymize.py paths\n"
        "       pseudonymize.py resolve <token>",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
