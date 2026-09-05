# HALOS swap day — 2026-09-05

State for the swap session. Boat phase starts at `runbooks/halos_swap.md`
§ At the boat.

## Pre-boat: done at home

- **§ Exercise the DNS cutover** — proved both directions, token good,
  DNS left on `symphony-pi`.
- **§ Sync the SignalK config** — not needed. Preflight `state` is `ok`:
  config files and installed plugin versions match the boat. No rebuild.
- **§ Before leaving home** (`scripts/halos_preflight.sh`) — 19 of 20 `ok`.

## The one accepted FAIL

```
FAIL  heartbeat  ping sent to /fail -- memory available 285 MB < 400
```

`MEM_ALARM_MB=400` in `/usr/local/sbin/boat-heartbeat` is calibrated for
the boat's 4 GB. The 2 GB bench peaks near 380 MB with SignalK, QuestDB
and Grafana resident, so the line cannot go green at home. The `mem`
check beside it (150 MB threshold) passes and says the same thing in its
own output.

**Mark accepted this as a bench artifact, 2026-09-05.** At the boat, a
`heartbeat` FAIL on `symphony-halos` is a carry-over, not a new failure —
treat it like the `victron` and `questdb` carry-overs the runbook already
names. Every *other* baseline `ok` must still be `ok` before DNS moves.

## Two earlier FAILs that were self-inflicted, not card defects

- `services` — QuestDB and Grafana are stopped by standing practice on
  the 2 GB bench. Started them; went green (`8 active`).
- `questdb` — SignalK's writer does not reconnect when the ILP endpoint
  disappears; the newest row was stamped the moment QuestDB stopped. A
  SignalK restart fixed it (row age 9971 s -> 4 s). Worth knowing: if
  QuestDB is ever bounced under a running SignalK, SignalK needs a
  restart too or it silently stops writing.

## Bench headroom lever

Homarr (~245 MB RSS, `unless-stopped`, inside `halos-core-containers`
alongside Traefik and Authelia) is the expendable one — the preflight
does not check it, and `docker ps` only lists running containers so the
`containers` health line stays green without it. Stop the container, not
the unit; the unit's Traefik is needed for the `front` check.

Bench was left restored: QuestDB and Grafana stopped, Homarr running.
