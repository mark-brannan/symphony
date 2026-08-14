# Rotating an InfluxDB token

Draft for RUNBOOK.md, written 2026-08-14 from an actual rotation of
`influxdb_captain_token`. Every command here was run on the boat Pi.
Fold it into RUNBOOK and delete this file, or link to it.

**The existing RUNBOOK block is wrong**, not merely awkward. It authenticates
with `influxdb_operator_token`, which returns 401 on this box — verified. The
documented path cannot work as written, on either platform.

## Baremetal or container?

Everything InfluxDB-side is plain HTTP against `:8086` and is **identical**
either way. Listing authorizations, minting, revoking — no Docker involved.

Only the ends differ, so this is one procedure with a fork at step 5:

| | baremetal (the Pi today) | container |
|---|---|---|
| restart consumers | `sudo systemctl restart signalk telegraf` | `docker compose up -d --force-recreate <service>` |
| plugin configs | `~/.signalk/plugin-config-data/` | mounted volume |
| Grafana admin reset | n/a | `docker exec grafana grafana cli ...` |

## Before you start

A token's value is shown **once**, at creation. There is no "reset in place".
So the order below is mint, migrate, verify, *then* revoke — the old token
keeps working until the new one is proven, and nothing loses data mid-rotation.

## 1. Get a working credential and the org id

Nothing here is hand-substituted; every value comes off the box.

```bash
TOK=$(python3 -c "import json;print(json.load(open('$HOME/.signalk/plugin-config-data/signalk-to-influxdb2.json'))['configuration']['influxes'][0]['token'])")
ORG=$(curl -s -H "Authorization: Token $TOK" http://localhost:8086/api/v2/orgs \
      | python3 -c "import json,sys;print(json.load(sys.stdin)['orgs'][0]['id'])")
curl -s -o /dev/null -w "auth check: %{http_code}\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
```

Expect `200`. If you get `401`, that token is dead too — find one that isn't
before going further, and see "When every stored token is dead" below.

## 2. Find the authorization you are replacing

```bash
curl -s -H "Authorization: Token $TOK" \
     "http://localhost:8086/api/v2/authorizations?orgID=$ORG" \
  | python3 -c "
import json,sys
for a in json.load(sys.stdin)['authorizations']:
    print(a['id'], repr(a.get('description','')), 'perms=%d' % len(a['permissions']))
"
OLD_ID=<paste the id from above>
```

This is the one value you must choose by hand, because only you know which
authorization you mean.

## 3. Mint the replacement with the same permissions

```bash
curl -s -H "Authorization: Token $TOK" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID" > /tmp/oldauth.json

python3 -c "
import json
a=json.load(open('/tmp/oldauth.json'))
json.dump({'orgID':a['orgID'],'userID':a['userID'],
           'description':a.get('description','')+' (rotated)',
           'permissions':a['permissions']}, open('/tmp/newauth-req.json','w'))
"

curl -s -X POST -H "Authorization: Token $TOK" -H "Content-Type: application/json" \
     -d @/tmp/newauth-req.json http://localhost:8086/api/v2/authorizations \
  > /tmp/newauth.json

NEW=$(python3 -c "import json;print(json.load(open('/tmp/newauth.json'))['token'])")
```

Don't echo `$NEW`. Anything printed to a terminal ends up in scrollback, and
in a Claude session it ends up in a transcript — which is what caused this
rotation in the first place.

## 4. Update every consumer

**Find them rather than trusting a list**, because the list grows:

```bash
grep -rl -- "$TOK" ~/.signalk/plugin-config-data/ /etc/telegraf/ 2>/dev/null
grep -c -- "$TOK" ~/symphony/.env
```

As of 2026-08-14 that was four places, and two are easy to miss:

- `~/.signalk/plugin-config-data/signalk-barograph.json`
- `~/.signalk/plugin-config-data/signalk-to-influxdb2.json` — the token is
  nested at `configuration.influxes[].token`, **not** a top-level `token`
- `~/.signalk/plugin-config-data/signalk-to-influxdb-v2-buffer.json` — the
  file is `-buffer`, not `-buffering`, though the plugin is named `-buffering`
- `secrets/symphony.sops.yaml`, key `influxdb_captain_token`

```bash
for f in $(grep -rl -- "$TOK" ~/.signalk/plugin-config-data/); do
  OLD="$TOK" NEW="$NEW" python3 -c "
import os,io,sys
p=sys.argv[1]; s=io.open(p,encoding='utf-8').read()
io.open(p,'w',encoding='utf-8').write(s.replace(os.environ['OLD'],os.environ['NEW']))
print('updated', p)
" "$f"
done

cd ~/symphony
sops --set "[\"influxdb_captain_token\"] \"$NEW\"" secrets/symphony.sops.yaml
python3 scripts/render.py
```

## 5. Restart consumers, then verify writes

```bash
sudo systemctl restart signalk telegraf      # baremetal
# docker compose up -d --force-recreate signalk telegraf   # container
```

Verify data is still landing **before** revoking anything:

```bash
curl -s -H "Authorization: Token $NEW" -H "Content-Type: application/vnd.flux" \
     -H "Accept: application/csv" -XPOST \
     "http://localhost:8086/api/v2/query?org=symphony" \
     -d 'from(bucket:"symphony")|>range(start:-2m)|>limit(n:3)' | head -3
```

Rows means writes are flowing on the new credential. No rows means stop and
fix it — the old token still works, so nothing is lost yet.

## 6. Revoke, and prove it is dead

```bash
curl -s -o /dev/null -w "delete: %{http_code}\n" -X DELETE \
     -H "Authorization: Token $NEW" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID"

curl -s -o /dev/null -w "old token now: %{http_code}  (401 = revoked)\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations

shred -u /tmp/oldauth.json /tmp/newauth.json /tmp/newauth-req.json
```

Expect `204` then `401`. Record it in `ROTATION.md`.

## When every stored token is dead

As of 2026-08-14 the sops `influxdb_operator_token` and `influxdb_signalk_token`
both return 401, and the repo's tracked copy of
`signalk/plugin-config-data/signalk-to-influxdb2.json` was carrying a *third*,
also-dead token — distinct from both the boat's live value and the sops one.
Following the old procedure would have propagated a 401 credential.

If nothing you have authenticates, the remaining routes are the InfluxDB UI at
`:8086` with the `captain` login, or `scripts/provision_influxdb.sh` on a fresh
volume. Neither has been exercised from a fully-locked-out state, so don't
write them up as if they had been.

## What this does not fix

One all-access token doing four jobs. Least privilege wants a scoped
write-only token per consumer — see the InfluxDB reconciliation item in
`maintenance/priorities.md`.
