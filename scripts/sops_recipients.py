#!/usr/bin/env python3
"""
Who can decrypt what, and the only safe way to change it.

`.sops.yaml` gives every creation rule the same key list through one YAML
anchor (`recipients:`). A rule can instead spell out its own list, which is
how a key gets access to ONE file rather than all of them -- the pseudonym
map is the case that forced it, since a key that resolves an email pseudonym
must not also open the boat's live credentials.

That second kind is why this module exists. `scripts/rotate_age_key.sh` used
to edit only the anchor. A rotation would then leave an explicit list still
holding the retired key -- the file would keep committing, keep looking
encrypted, and be readable only by the key you had just deleted. Every
recipient edit goes through here now.

An explicit list is maintained as (every global recipient) + (that rule's
extras). `add` writes the key into the anchor AND into every explicit list;
`remove` takes it out of both. Nothing marks a key as an extra -- extras are
simply what a list holds that the anchor doesn't -- so the two can't drift
apart into disagreeing opinions about which is which.

Edits are line-based, not a YAML round-trip: the comments and the anchor
itself are load-bearing here, and PyYAML would silently drop both.

Usage:
    sops_recipients.py list [--all]     # global recipients (--all: every key)
    sops_recipients.py show             # global + per-rule extras, annotated
    sops_recipients.py add <age-pubkey>
    sops_recipients.py remove <age-pubkey>
    sops_recipients.py files-for <age-pubkey>   # "kind<TAB>path" per line
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sops_paths  # noqa: E402  (sibling module, path fixed up above)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOPS_CONFIG = os.path.join(REPO, ".sops.yaml")

GLOBAL = "recipients"

KEY_RE = re.compile(r"^(\s+)- (age1[0-9a-z]{58})\s*$")
ALIAS_RE = re.compile(r"^\s+- age:\s*\*(\w+)\s*$")
LIST_RE = re.compile(r"^\s+- age:\s*$")
RULE_RE = re.compile(r"^\s+- path_regex:\s*(.+?)\s*$")

PUBKEY_RE = re.compile(r"^age1[0-9a-z]{58}$")


class ConfigError(Exception):
    pass


class Block:
    """One list of age recipients in the file, and where its lines are."""

    def __init__(self, label, alias=None):
        self.label = label          # GLOBAL, or the rule's path_regex
        self.alias = alias          # anchor name if this rule reuses one
        self.keys = []
        self.lines = []             # line numbers holding those keys
        self.indent = "  "

    @property
    def explicit(self):
        return self.alias is None


def read(path=SOPS_CONFIG):
    with open(path) as f:
        return f.readlines()


def parse(lines):
    """Recipient blocks in file order: the anchor first, then one per rule."""
    blocks = []
    current = None
    label = None

    for i, line in enumerate(lines):
        if line.startswith(f"{GLOBAL}:"):
            current = Block(GLOBAL)
            blocks.append(current)
            continue
        if line.startswith("creation_rules:"):
            current = None
            continue

        rule = RULE_RE.match(line)
        if rule:
            label = rule.group(1).strip().strip("'\"")
            current = None
            continue

        alias = ALIAS_RE.match(line)
        if alias:
            blocks.append(Block(label, alias=alias.group(1)))
            current = None
            continue

        if LIST_RE.match(line):
            current = Block(label)
            blocks.append(current)
            continue

        key = KEY_RE.match(line)
        if key and current is not None:
            current.indent = key.group(1)
            current.keys.append(key.group(2))
            current.lines.append(i)
            continue

        # Comments and blank lines sit inside a block; anything else ends it.
        if current is not None and line.strip() and not line.lstrip().startswith("#"):
            current = None

    return blocks


def global_keys(blocks):
    for block in blocks:
        if block.label == GLOBAL:
            return block.keys
    raise ConfigError(f"no top-level `{GLOBAL}:` block in .sops.yaml")


def rule_blocks(blocks):
    return [b for b in blocks if b.label != GLOBAL]


def effective_keys(block, blocks):
    """What this rule's key list actually resolves to."""
    return block.keys if block.explicit else global_keys(blocks)


def all_keys(blocks):
    seen = []
    for block in blocks:
        for key in block.keys:
            if key not in seen:
                seen.append(key)
    return seen


def extras(blocks):
    """Per-rule keys that aren't global recipients, by rule."""
    shared = set(global_keys(blocks))
    found = {}
    for block in rule_blocks(blocks):
        if not block.explicit:
            continue
        odd = [k for k in block.keys if k not in shared]
        if odd:
            found[block.label] = odd
    return found


# ------------------------------------------------------------------ edits ---
def add_key(lines, key):
    """Insert `key` into the anchor and into every explicit rule list.

    Returns the number of lists changed. Inserting bottom-up keeps the line
    numbers from the parse valid while we mutate the list.
    """
    blocks = parse(lines)
    targets = [b for b in blocks if b.explicit and key not in b.keys]
    for block in targets:
        if not block.lines:
            raise ConfigError(f"recipient list for '{block.label}' is empty -- fix it by hand")
    for block in sorted(targets, key=lambda b: b.lines[-1], reverse=True):
        lines.insert(block.lines[-1] + 1, f"{block.indent}- {key}\n")
    return len(targets)


def remove_key(lines, key):
    """Drop `key` from every list. Refuses to leave a list with no keys."""
    blocks = parse(lines)
    holders = [b for b in blocks if b.explicit and key in b.keys]
    if not holders:
        raise ConfigError(f"{key} is not a recipient anywhere in .sops.yaml")

    emptied = [b.label for b in holders if len(b.keys) == 1]
    if emptied:
        raise ConfigError(
            "refusing to remove the only recipient of: " + ", ".join(emptied)
            + " -- those files would become permanently unreadable. Add another key first."
        )

    doomed = {i for b in holders for i, k in zip(b.lines, b.keys) if k == key}
    lines[:] = [line for i, line in enumerate(lines) if i not in doomed]
    return len(holders)


def write(lines, path=SOPS_CONFIG):
    with open(path, "w") as f:
        f.writelines(lines)


# ------------------------------------------------------------- key -> files --
def keys_for_path(path, blocks):
    """Recipients of `path`, honouring sops' first-rule-wins matching."""
    for block in rule_blocks(blocks):
        if block.label and re.search(block.label, path):
            return effective_keys(block, blocks)
    return []


def files_for_key(key, blocks):
    """Every configured file this key can decrypt, as (kind, path)."""
    found = []
    for path in sops_paths.whole_file_paths():
        if key in keys_for_path(path, blocks):
            found.append(("whole", path))
    for path in sops_paths.inplace_paths():
        if key in keys_for_path(path, blocks):
            found.append(("inplace", path))
    return found


# ------------------------------------------------------------------- CLI -----
def cmd_show(blocks):
    print("Global recipients (shared by every rule via the `recipients` anchor):")
    for key in global_keys(blocks):
        print(f"  {key}")

    odd = extras(blocks)
    if not odd:
        print("\nNo per-rule keys. Every rule uses the anchor.")
        return 0
    print("\nPer-rule keys (these files, and no others):")
    for label, keys in odd.items():
        print(f"  {label}")
        for key in keys:
            print(f"    {key}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="print global recipients")
    listing.add_argument("--all", action="store_true", help="every key anywhere in the file")
    sub.add_parser("show", help="global recipients and per-rule extras")
    for name in ("add", "files-for"):
        sub.add_parser(name).add_argument("key")
    removal = sub.add_parser("remove")
    removal.add_argument("key")
    removal.add_argument(
        "-n", "--dry-run", action="store_true",
        help="report whether the removal is safe, change nothing",
    )

    args = parser.parse_args()
    lines = read()
    blocks = parse(lines)

    if args.command == "list":
        for key in (all_keys(blocks) if args.all else global_keys(blocks)):
            print(key)
        return 0

    if args.command == "show":
        return cmd_show(blocks)

    if not PUBKEY_RE.match(args.key):
        print(f"error: '{args.key}' is not an age public key", file=sys.stderr)
        return 1

    if args.command == "files-for":
        for kind, path in files_for_key(args.key, blocks):
            print(f"{kind}\t{path}")
        return 0

    try:
        if args.command == "add":
            changed = add_key(lines, args.key)
        else:
            changed = remove_key(lines, args.key)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "dry_run", False):
        print(f"would remove {args.key} from {changed} recipient list(s) -- nothing written")
        return 0

    write(lines)
    verb = "added to" if args.command == "add" else "removed from"
    print(f"{args.key} {verb} {changed} recipient list(s) in .sops.yaml")
    if args.command == "remove":
        print("Check for a comment above the removed key that no longer applies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
