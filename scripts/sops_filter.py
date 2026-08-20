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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import secretguard  # noqa: E402  -- needs the sys.path line above

# Both optional at import time so this file can still run its no-key
# pass-through paths on a clone that has neither. Anything that actually
# needs them checks first and fails loudly, never silently.
try:
    import yaml
except ImportError:
    yaml = None

try:
    import pseudonymize
except ImportError:
    pseudonymize = None

# Absolute path when we can find one, bare name otherwise so the failure
# text still names what is missing. Resolved once: PATH cannot change
# mid-process, and a filter runs per file.
_SOPS_PATH = secretguard.find_sops()
SOPS = _SOPS_PATH or "sops"


def looks_encrypted(text):
    """What a sops document looks like from the outside, without parsing it.

    One policy, shared with the pre-commit and pre-push guards, so a file
    cannot read as encrypted to one of them and plaintext to another.
    """
    return secretguard.is_sops_encrypted(text)


def can_encrypt():
    """Everything the encrypt path needs, in one question."""
    missing = []
    if not _SOPS_PATH:
        missing.append(secretguard.sops_locations())
    if not secretguard.have_age_key():
        missing.append("an age key (~/.config/sops/age/keys.txt, or SOPS_AGE_KEY_FILE)")
    if yaml is None or pseudonymize is None:
        missing.append("the pyyaml package for this python3")
    return missing


def blob(ref, path):
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


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
    raw = sys.stdin.read()

    # A fresh clone with no key checks these files out as ciphertext -- that
    # is the documented, expected state, and it is what the working tree
    # holds until setup-git-filters.sh decrypts them. Staging anything else
    # in the repo then makes git run this filter over them, and every
    # encrypt path below needs sops and a key. That turned "no sops on this
    # laptop" into "git commit dies on a traceback", for a README edit.
    #
    # So: if the working-tree copy is still exactly the ciphertext git
    # already has, hand it straight back. Byte-identical to the blob, needs
    # nothing installed, and cannot leak -- it is the encrypted form.
    if looks_encrypted(raw):
        if raw in (index_blob(path), blob("HEAD", path)):
            sys.stdout.write(raw)
            return
        secretguard.block(
            "a sops-encrypted file was edited without being decrypted first",
            problem="this file is still ciphertext in the working tree but no "
                    "longer matches what git has, so it cannot be passed "
                    "through and cannot be re-encrypted -- committing it "
                    "would store a document whose MAC no longer verifies",
            file=path,
            needs=", ".join(can_encrypt()) or "the sops clean filter to run",
            blocked_by="the sops clean filter (scripts/sops_filter.py)",
            fix=f"git checkout -- {path} to discard the edit, or provision a "
                f"key and run: bash scripts/setup-git-filters.sh",
            see="RUNBOOK.md, When a hook blocks your commit",
        )
        sys.exit(1)

    missing = can_encrypt()
    if missing:
        secretguard.block(
            "a secret-bearing file cannot be encrypted on this machine",
            problem="this file is plaintext and git is about to store it. "
                    "Refusing, because storing it as-is would put the secret "
                    "in the clear in a public repo",
            file=path,
            needs=", ".join(missing),
            blocked_by="the sops clean filter (scripts/sops_filter.py)",
            fix="bash scripts/setup-git-filters.sh (after installing what "
                "'needs' lists), or unstage the file",
            see="RUNBOOK.md, When a hook blocks your commit",
        )
        sys.exit(1)

    # Pseudonymize FIRST, then treat the result as the plaintext for every
    # step below. The unchanged-comparison further down decrypts the staged
    # blob, which is already in git form -- comparing it against the raw
    # working tree would never match, so every commit would rewrite the blob
    # and these files would look permanently modified.
    new_plaintext = to_git_form(path, raw)
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

    already_encrypted = old_ciphertext is not None and looks_encrypted(
        old_ciphertext
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

    # Contributor: check the file out as ciphertext rather than failing.
    # That is exactly the state a fresh clone is in before
    # setup-git-filters.sh runs, it is what RUNBOOK.md already describes,
    # and the alternative is `git clone` erroring out on a machine that was
    # never going to read these files anyway.
    #
    # Strict: fail. A machine that holds secrets is a machine something
    # READS them -- SignalK and Grafana parse these files directly. Handing
    # them ENC[...] blobs where they expect configuration is a silent
    # runtime failure on the boat, where a checkout that errors is a loud
    # one. Degrading here would trade a visible problem for an invisible
    # one, which is the opposite of the trade this mode switch exists for.
    missing = can_encrypt()
    if missing:
        if secretguard.mode() == "strict":
            secretguard.block(
                "cannot decrypt a file this machine is expected to read",
                problem="checking it out as ciphertext would leave SignalK or "
                        "Grafana parsing ENC[...] blobs as configuration -- a "
                        "silent failure, where this is a loud one",
                file=path,
                needs=", ".join(missing),
                blocked_by="the sops smudge filter (scripts/sops_filter.py)",
                fix="restore what 'needs' lists, then: bash scripts/setup-git-filters.sh",
                see="bash scripts/check_clone_setup.sh",
            )
            sys.exit(1)
        secretguard.line(
            f"{path} checked out as ciphertext -- missing {missing[0]}. "
            f"Details: bash scripts/check_clone_setup.sh"
        )
        sys.stdout.write(ciphertext)
        return

    sys.stdout.write(to_worktree_form(path, sops_decrypt(path, ciphertext)))


if __name__ == "__main__":
    mode, target = sys.argv[1], sys.argv[2]
    {"clean": clean, "smudge": smudge}[mode](target)
