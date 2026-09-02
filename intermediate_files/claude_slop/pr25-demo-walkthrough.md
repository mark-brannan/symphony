# PR #25 demo: walking Mark through the QuestDB dashboards

Mark asked for a live walkthrough of the ported dashboards rather than a
diff read or screenshots. This file is the setup half so the session doing
the walking spends its time on the dashboards, not on plumbing.

## Stand it up

Run it isolated, not through `scripts/dev_stack.sh`. The dev box already has
a long-running `docker compose` stack from this repo (signalk on :3000,
influxdb on :8086, ntfy on :8090, and a `grafana` container that has been
crash-looping for days). `dev_stack.sh up` acts on that same compose project
and would disturb it.

```bash
cd <a worktree of the PR #25 branch>
docker build -t symphony-grafana-demo ./grafana
docker network create symphony-demo-net

docker run -d --name questdb-demo --network symphony-demo-net \
  -p 127.0.0.1:9500:9000 \
  -e QDB_CAIRO_WRITER_DATA_APPEND_PAGE_SIZE=256k \
  -e QDB_CAIRO_WRITER_DATA_INDEX_VALUE_APPEND_PAGE_SIZE=256k \
  questdb/questdb:latest

python3 scripts/seed_dev_questdb.py --url http://localhost:9500

docker run -d --name grafana-demo --network symphony-demo-net \
  -p 127.0.0.1:3100:3000 \
  -e GF_SECURITY_ADMIN_USER=admin -e GF_SECURITY_ADMIN_PASSWORD=devadmin \
  -e GF_PLUGINS_PREINSTALL=questdb-questdb-datasource \
  -e QUESTDB_HOST=questdb-demo -e QUESTDB_PORT=8812 \
  -e QUESTDB_USER=admin -e QUESTDB_PASSWORD=quest \
  -e INFLUX_URL=http://127.0.0.1:8086 -e INFLUX_TOKEN=unused \
  -e INFLUX_ORG=symphony -e INFLUX_BUCKET=signalk \
  -e SIGNALK_HOST=127.0.0.1:3000 -e SIGNALK_TOKEN=unused \
  -e GF_AUTH_GENERIC_OAUTH_ENABLED=false \
  -e GF_SERVER_ROOT_URL=http://localhost:3100 \
  symphony-grafana-demo
```

Grafana needs about 30 s and an uplink for the plugin preinstall. Then:

```bash
python3 scripts/verify_dashboards_live.py \
  --grafana http://localhost:3100 --user admin --password devadmin
```

Expected tail: `196 panel queries: 196 returned data, 0 empty, 0 errored`
(measured 2026-09-01). Anything less means the seed or the datasource is
wrong, not the dashboards — fix that before walking Mark through anything.

Tear down with `docker rm -f questdb-demo grafana-demo && docker network rm
symphony-demo-net`. Nothing here touches the pre-existing stack.

## What to walk him through

<http://localhost:3100>, admin / devadmin. Six dashboards in the Marine
folder. Suggested order, and the question each one is actually asking:

1. **Navstation** — the one he'd have open at anchor. Does the top row read
   like a boat, and are the units right (knots, degrees, °F, hPa)?
2. **Electricity** — the largest, and the one tied to real hardware
   (`PACKS_PARALLELED` in `build_dashboards.py` is still `False`, so 5C90 is
   labelled House and 0146 Spare).
3. **System health** — the Telegraf side, and where this session's two panel
   fixes landed: *Disk used* is now pinned to `path = '/'` and *Network
   throughput (eth0)* to one interface.
4. **Navigation**, **Weather**, **Life support** — quicker passes.

## Known before he asks

- **`Vessel state` and `Tendency` on Navstation read "No data"**, and so do
  the other string-valued stat panels. Their queries return a row — the live
  check counts them as passing — but a Grafana `stat` panel with
  `reduceOptions.fields: ""` reduces numeric fields only, so a string-only
  frame renders as No data. **This predates the port**: the panel JSON for
  these is byte-identical on `origin/main`, where the query was Flux. Not a
  PR #25 regression, and not fixed in PR #25. It is a one-line change in
  `build_dashboards.py` if he wants it — set `fields` to `/.*/` for
  text-mode stats — but that is its own commit.
- **The seed is a sine wave**, so every trace looks like a sine wave. Shape,
  units and scale are the point; the data is not.
- **`environment.outside.pressure.trend.severity` has no explicit range** and
  gets seeded 0..100. The seeder says so on stdout.

## Taking his feedback

He said he wants questions and comments taken down and answered, so:

- Anything he wants changed in a dashboard is a change to
  `scripts/build_dashboards.py`, then `python3 scripts/build_dashboards.py`,
  then `python3 scripts/test_dashboards.py`. Never edit the JSON, and never
  edit a panel in the Grafana UI and export it back — the JSON is build
  output and the test asserts it regenerates identically.
- Small fixes he approves in the moment: commit to the PR #25 branch as he
  approves them, one commit each, and re-run the seed + live check so the
  next dashboard he looks at already has them.
- Anything bigger, or anything he wants to think about: a card in
  `intermediate_files/claude_slop/kanban.md`, written at the moment he says
  it, with enough detail to act on without him.
- A wrap-up ends with zero unmeasured decisions: every question raised
  either executed in-session or put to him as an explicit prompt before the
  turn ends.
