#!/usr/bin/env python3
"""
Git clean/smudge filter for files that must exist as plaintext on disk
(read directly by SignalK / Grafana) but should only ever be stored in git
with their secret fields encrypted.

Uses sops's partial in-place encryption (encrypted_regex in .sops.yaml) so
most of the file stays legible in `git show` / GitHub; only the leaf values
matching the configured key names (secretKey, password, token, ...) are
ciphertext.

Wired up via .gitattributes (`filter=sops`) + `scripts/setup-git-filters.sh`
(git filter commands live in .git/config, which isn't versioned, so every
clone must run the setup script once).

Usage:
    sops_filter.py clean  <repo-relative-path>   # working tree -> git object
    sops_filter.py smudge <repo-relative-path>   # git object -> working tree

age/sops encryption is not deterministic: re-encrypting identical plaintext
produces different ciphertext bytes. Since git's dirty-check compares the
clean filter's output against the blob already in the index, a naive
"always re-encrypt" clean step would make these files show as permanently
modified. To avoid that, `clean` first decrypts whatever is already staged
and only emits new ciphertext if the plaintext actually changed.
"""
import json
import os
import subprocess
import sys

import yaml

import pseudonymize

SOPS = "sops"


def warn(message):
    sys.stderr.write(f"{message}\n")


def to_git_form(path, text):
    """Working-tree text -> the form that belongs in git.

    Runs BEFORE encryption on the clean side. Ordering is not negotiable:
    sops's MAC covers the file, so any substitution has to happen while the
    document is still plaintext, and the reverse has to happen after
    decryption on the way out.
    """
    if path not in pseudonymize.load_paths():
        return text

    salt, mapping = pseudonymize.load_store()
    result, added = pseudonymize.pseudonymize(text, salt, mapping)
    if added:
        pseudonymize.save_store(salt, mapping)
        for address in added:
            warn(
                f"pseudonymize: new address {pseudonymize.mask(address)} -> "
                f"{pseudonymize.derive(address, salt)}"
            )
        warn(
            "pseudonymize: the map changed -- stage secrets/pseudonyms.sops.yaml "
            "in this commit, or the token will not resolve in a fresh clone."
        )
    return result


def to_worktree_form(path, text):
    """Git text -> the form SignalK reads. Runs AFTER decryption on smudge."""
    if path not in pseudonymize.load_paths():
        return text

    try:
        _, mapping = pseudonymize.load_store()
    except pseudonymize.StoreUnavailable as error:
        # Deliberately not fatal: failing here breaks `git checkout` itself.
        # Loud instead, because the silent version is genuinely bad -- the
        # tokens stay in the file, SignalK reads them as if they were real
        # addresses, and rewrites them back as the user's identity.
        warn(f"pseudonymize: WARNING - {error}")
        warn(
            "pseudonymize: WARNING - email addresses in "
            f"{path} will stay as tokens. Do NOT start SignalK against this "
            "file; it will treat them as real addresses and write them back."
        )
        return text

    result, unresolved = pseudonymize.depseudonymize(text, mapping)
    if unresolved:
        warn(
            f"pseudonymize: WARNING - {len(unresolved)} token(s) in {path} are not "
            f"in the map and stay unresolved: {', '.join(sorted(set(unresolved)))}"
        )
    return result


def is_yaml(path):
    return path.endswith((".yaml", ".yml"))


def parse(text, path):
    return yaml.safe_load(text) if is_yaml(path) else json.loads(text)


def run_sops(args, input_text):
    result = subprocess.run(
        [SOPS, *args], input=input_text, capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    return result.stdout


# sops re-serializes the document it is given, so IT decides the file's
# indentation, not whatever was on disk. Its default (`--indent 0`) means
# tabs -- which is where the tabs in security.json actually come from, on
# both the git side and the working-tree side. Setting it here is the only
# place that can win: normalizing the text before handing it to sops is
# pointless, because sops re-indents it right back.
INDENT = ["--indent", "2"]


def sops_encrypt(path, plaintext):
    return run_sops(
        ["--encrypt", *INDENT, "--filename-override", path, "/dev/stdin"], plaintext
    )


def sops_decrypt(path, ciphertext):
    return run_sops(
        ["--decrypt", *INDENT, "--filename-override", path, "/dev/stdin"], ciphertext
    )


def index_blob(path):
    """Whatever's currently staged for `path`, or None if there's no such entry."""
    result = subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def clean(path):
    # Pseudonymize FIRST, then treat the result as the plaintext for every
    # step below. The unchanged-comparison further down decrypts the staged
    # blob, which is already in git form -- comparing it against the raw
    # working tree would never match, so every commit would rewrite the blob
    # and these files would look permanently modified.
    new_plaintext = to_git_form(path, sys.stdin.read())
    old_ciphertext = index_blob(path)

    # SOPS_FILTER_REKEY forces fresh encryption even when the plaintext is
    # unchanged. Required for age key rotation: the reuse path below emits
    # the *existing* ciphertext byte-for-byte, which is still encrypted to
    # the old recipient only. Without this escape hatch, changing the
    # recipient list in .sops.yaml and re-staging appears to succeed while
    # silently leaving every in-place file readable by the old key alone --
    # and unreadable by the new one. See scripts/rotate_age_key.sh.
    if os.environ.get("SOPS_FILTER_REKEY") == "1":
        sys.stdout.write(sops_encrypt(path, new_plaintext))
        return

    already_encrypted = old_ciphertext is not None and (
        '"sops"' in old_ciphertext or "sops:" in old_ciphertext
    )
    if already_encrypted:
        try:
            old_plaintext = sops_decrypt(path, old_ciphertext)
            if parse(old_plaintext, path) == parse(new_plaintext, path):
                sys.stdout.write(old_ciphertext)
                return
        except SystemExit:
            pass  # old blob didn't decrypt cleanly (e.g. rule changed) -> fall through

    sys.stdout.write(sops_encrypt(path, new_plaintext))


def smudge(path):
    ciphertext = sys.stdin.read()
    sys.stdout.write(to_worktree_form(path, sops_decrypt(path, ciphertext)))


if __name__ == "__main__":
    mode, target = sys.argv[1], sys.argv[2]
    {"clean": clean, "smudge": smudge}[mode](target)
