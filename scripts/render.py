#!/usr/bin/env python3
"""
Layer-1 render step: decrypts secrets/symphony.sops.yaml and renders the
.j2 templates listed in TEMPLATES below to their target paths.

Deliberately shaped like a list of ansible.builtin.template tasks (src,
dest, vars all coming from one decrypted fact source) so that migrating to
a real Ansible role later is a mechanical transcription, not a rewrite.

The other secret-bearing files (signalk/security.json,
signalk/plugin-config-data/signalk-to-influxdb2.json,
signalk/plugin-config-data/signalk-dsc.json) are NOT handled here --
they're restored automatically by the sops git smudge filter on
`git checkout` (see scripts/setup-git-filters.sh). Grafana users are
handled separately by scripts/provision_grafana_users.sh, since Grafana
OSS has no file-based provisioning for them at all. This script only
covers the .env layer that docker-compose substitutes at container-start
time.
"""
import os
import stat
import subprocess
import sys

import yaml
from jinja2 import Template

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_FILE = os.path.join(REPO_ROOT, "secrets", "symphony.sops.yaml")

TEMPLATES = [
    # (src relative to repo root, dest relative to repo root)
    (".env.j2", ".env"),
    ("dex/config.yaml.j2", "dex/config.yaml"),
]


def load_secrets():
    result = subprocess.run(
        ["sops", "--decrypt", SECRETS_FILE], capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.stderr.write(
            "\nCouldn't decrypt secrets/symphony.sops.yaml -- do you have an "
            "age private key at ~/.config/sops/age/keys.txt (or "
            "$SOPS_AGE_KEY_FILE) that's in the recipient list in .sops.yaml?\n"
        )
        sys.exit(result.returncode)
    return yaml.safe_load(result.stdout)


def render(src_name, dest_name, variables):
    src = os.path.join(REPO_ROOT, src_name)
    dest = os.path.join(REPO_ROOT, dest_name)
    with open(src) as f:
        template = Template(f.read())
    rendered = template.render(**variables)
    with open(dest, "w") as f:
        f.write(rendered)
    os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)  # 600 -- it holds secrets
    print(f"rendered {dest_name} from {src_name}")


def main():
    variables = load_secrets()
    for src_name, dest_name in TEMPLATES:
        render(src_name, dest_name, variables)


if __name__ == "__main__":
    main()
