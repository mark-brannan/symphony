# Secrets

Adding, removing, and the long rotations. The short ones and an exposure are
in [RUNBOOK.md](../RUNBOOK.md#rotating-a-secret).

## Adding a secret

**A standalone value** (API key, token, password) goes in the store:

```bash
sops secrets/symphony.sops.yaml          # add the `name: value` line, save
git add secrets/symphony.sops.yaml
git commit -m "Store <name>" -- secrets/symphony.sops.yaml
```

*Verify:* `sops --decrypt --extract '["<name>"]' secrets/symphony.sops.yaml`
prints the value and `git show :secrets/symphony.sops.yaml | grep <name>` shows
`ENC[`. `File has not changed, exiting.` means the edit didn't save.

To make something read it: add the key to `.env.example` and `.env.j2`, run
`python3 scripts/render.py`, restart the reader.

**A field inside a config file SignalK or Grafana owns** is encrypted in place:

```bash
scripts/add_inplace_secret.sh signalk/plugin-config-data/<plugin>.json token
git commit -m "Encrypt <plugin>.json's token"
```

Never point it at `secrets/*.sops.yaml`. If one of those fails `git add` with
sops complaining about *"a top-level entry called 'sops'"*, delete its
`filter=sops` line from `.gitattributes` and its `path_regex` block from
`.sops.yaml`, then:

```bash
git check-attr filter -- secrets/symphony.sops.yaml   # want: unspecified
python3 scripts/sops_paths.py check
git add secrets/symphony.sops.yaml
```

## Removing a secret

1. Delete its `path_regex` block from `.sops.yaml`.
2. Delete its `filter=sops` line from `.gitattributes`.
3. `python3 scripts/sops_paths.py check`
4. If the file is going away: `git rm --cached <file>` and add it to `.gitignore`.

If the value was ever live in a public commit, rotate it.

## Rotating an InfluxDB token

Tokens show once at creation, so: mint, migrate, verify, then revoke.

```bash
cd ~/symphony
TOK=$(sops --decrypt --extract '["influxdb_captain_token"]' secrets/symphony.sops.yaml)
ORG=$(curl -s -H "Authorization: Token $TOK" http://localhost:8086/api/v2/orgs \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["orgs"][0]["id"])')
curl -s -o /dev/null -w "auth check: %{http_code}\n" -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
```

`200` to continue. Find the authorization to replace:

```bash
curl -s -H "Authorization: Token $TOK" "http://localhost:8086/api/v2/authorizations?orgID=$ORG" \
  | python3 -c '
import json,sys
for a in json.load(sys.stdin)["authorizations"]:
    print(a["id"], repr(a.get("description","")), "perms=%d" % len(a["permissions"]))
'
OLD_ID=<paste the id>
```

Mint the replacement with the same permissions. Don't echo `$NEW`; scrollback persists.

```bash
curl -s -H "Authorization: Token $TOK" "http://localhost:8086/api/v2/authorizations/$OLD_ID" > /tmp/oldauth.json
python3 -c '
import json
a=json.load(open("/tmp/oldauth.json"))
json.dump({"orgID":a["orgID"],"userID":a["userID"],
           "description":a.get("description","")+" (rotated)",
           "permissions":a["permissions"]}, open("/tmp/newauth-req.json","w"))
'
curl -s -X POST -H "Authorization: Token $TOK" -H "Content-Type: application/json" \
     -d @/tmp/newauth-req.json http://localhost:8086/api/v2/authorizations > /tmp/newauth.json
NEW=$(python3 -c 'import json;print(json.load(open("/tmp/newauth.json"))["token"])')
```

Update every consumer. The plugin token is nested at
`configuration.influxes[].token`; the buffering plugin's file is
`signalk-to-influxdb-v2-buffer.json`.

```bash
grep -rl -- "$TOK" ~/.signalk/plugin-config-data/ /etc/telegraf/ 2>/dev/null
grep -c -- "$TOK" ~/symphony/.env
for f in $(grep -rl -- "$TOK" ~/.signalk/plugin-config-data/); do
  OLD="$TOK" NEW="$NEW" python3 -c '
import os,io,sys
p=sys.argv[1]; s=io.open(p,encoding="utf-8").read()
io.open(p,"w",encoding="utf-8").write(s.replace(os.environ["OLD"],os.environ["NEW"]))
print("updated", p)
' "$f"
done
sops --set "[\"influxdb_captain_token\"] \"$NEW\"" secrets/symphony.sops.yaml
python3 scripts/render.py
```

Restart consumers and prove writes land before revoking:

```bash
sudo systemctl restart signalk telegraf                      # boat
# docker compose up -d --force-recreate signalk telegraf     # containerized
curl -s -H "Authorization: Token $NEW" -H "Content-Type: application/vnd.flux" -H "Accept: application/csv" \
     -XPOST "http://localhost:8086/api/v2/query?org=symphony" \
     -d 'from(bucket:"symphony")|>range(start:-2m)|>limit(n:3)' | head -3
```

Rows means the new token carries traffic. No rows: stop and fix; the old one still works. Then revoke:

```bash
curl -s -o /dev/null -w "delete: %{http_code}\n" -X DELETE -H "Authorization: Token $NEW" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID"
curl -s -o /dev/null -w "old token now: %{http_code}  (401 = revoked)\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
shred -u /tmp/oldauth.json /tmp/newauth.json /tmp/newauth-req.json
```

Expect `204` then `401`. Record it in `ROTATION.md`. If nothing authenticates,
the InfluxDB UI at `:8086` with the `captain` login is what's left.

## Rotating the age key

Annually, and immediately on suspected exposure. Keep two recipients, stored
apart. Commit after each phase.

```bash
scripts/rotate_age_key.sh status
scripts/rotate_age_key.sh add --generate           # phase 1: new key joins
#   back up the new key; install it on every host
scripts/rotate_age_key.sh verify <new-public-key>  # gate: the new key alone opens everything
scripts/rotate_age_key.sh retire <old-public-key>  # phase 2
```

Don't skip `verify`: a plain `sops --decrypt` passes while the old key is
still in your keyring. On failure it names the files.

A host missed before phase 2 fails to decrypt afterward: copy a current key
there and re-run `scripts/setup-git-filters.sh`. If the old key was
*compromised*, rotate the secrets themselves too.

Check an escrow key yearly and after any move, without putting it in the
keyring:

```bash
install -m 600 /dev/null /tmp/check.key            # paste the key in
age-keygen -y /tmp/check.key                       # must print the public key from .sops.yaml
SOPS_AGE_KEY_FILE=/tmp/check.key scripts/rotate_age_key.sh verify <public-key>
shred -u /tmp/check.key
```

Expect `decrypts all N file(s)` for an escrow key; fewer means it is scoped.

## Email pseudonyms in security.json

Addresses in `signalk/security.json` become `pid.*` tokens in git and are
restored on checkout.

```bash
python3 scripts/pseudonymize.py resolve pid.rj232vx
git log -S 'pid.rj232vx' -- signalk/security.json       # when someone had access
```

When someone new logs in, the commit prints `pseudonymize: the map changed`;
stage `secrets/pseudonyms.sops.yaml` in that same commit.

If checkout warns `cannot decrypt secrets/pseudonyms.sops.yaml`, don't start
SignalK against the file. Get an age identity working, then
`git checkout -- signalk/security.json`.

## Router config backup

The router holds the DNS override that makes the hostnames resolve aboard.
Refresh after any router change, from anywhere on the tailnet:

```bash
ssh pi@symphony-pi 'ssh root@192.168.8.1 "uci export"' > /tmp/uci.txt
test -s /tmp/uci.txt && grep -q '^package' /tmp/uci.txt && echo export ok
python3 -c "import yaml; yaml.safe_dump({'uci_export': open('/tmp/uci.txt').read()}, open('secrets/router-config.sops.yaml','w'), default_style='|')"
sops --encrypt --in-place secrets/router-config.sops.yaml
rm /tmp/uci.txt
```

Stop if `export ok` doesn't print; an empty export overwrites the backup.

*Verify:* `sops --decrypt --extract '["uci_export"]' secrets/router-config.sops.yaml | head -3`, then commit.

Restore: `sops --decrypt secrets/router-config.sops.yaml`, feed `uci_export`
through `uci import` on the router, then `reload_config`. This restores WiFi
and WAN too.
