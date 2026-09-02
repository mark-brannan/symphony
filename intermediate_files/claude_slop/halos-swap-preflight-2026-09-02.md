# HALOS card — pre-swap state and preflight, morning of 2026-09-02

Read this before swapping cards. Evidence for every claim is in
[halos-b3-findings-2026-09-02.md](halos-b3-findings-2026-09-02.md).

## DO THIS FIRST: power-cycle the staging Pi

`halos-pi4` (192.168.0.193) wedged itself at ~06:2x UTC and was still wedged
45 minutes later. Ports 22/80/443/3000 accept TCP; nothing completes a
request. It is thrashing on swap and cannot be reached to stop it.

**Pull its power and bring it back up.** It has been swapping hard for hours;
sustained swap onto an SD card is the one thing here that can actually damage
the media. This is the only action that needs hands, and it should happen
before anything else.

Cause is understood and is not a HALOS fault — see "Is the card OK?" below.

## What state the card is in

Done and verified before the box wedged:

- B3a — boat `.signalk` state copied (settings, security.json with 3 users,
  ~105 plugin configs, Node-RED flows, baseDeltas, priorities).
- B3b — both local forks in `local-plugins/`: `bt-sensors-plugin-sk`
  1.3.8-beta11 (with the PR #189 D-Bus fixes) and `signalk-plugin-watchdog`.
- B3c — `package.json` repointed to the two `file:` entries; three plugins
  disabled; `venus.json` MQTT host -> 192.168.8.107.
- `node_modules` wiped and cleanly reinstalled: 2773 packages, exit 0. The
  earlier interrupted installs had left a corrupt tree; this is the good one.
- Native modules built against the right ABI: `i2c-bus`, `epoll`, `sqlite3`,
  `serialport`, `lzma-native`.
- Plugins failing to start went **from 6 to 1**.
- `signalk-notification-player` disabled; its mpg321 log spam is now zero.

## Known loose ends, none blocking

1. **A stray inert file:** `plugin-config-data/signalk-plugin-watchdog.json`.
   The plugin's real id is `plugin-watchdog` (`index.js:22`), so the live
   config is the pre-existing `plugin-watchdog.json`. Delete the stray:
   `rm /var/lib/container-apps/marine-signalk-server-container/data/data/plugin-config-data/signalk-plugin-watchdog.json`
   I could not remove it before the box wedged.
2. **`signalk-instrument-light-plugin` still fails** — needs `serialport`
   bindings that will not build for node 24. It has **no config file at all**,
   i.e. was never configured. Recommend leaving it.
3. **The watchdog plugin's actual running state is unconfirmed** on the card.

## Is the card OK? Yes — the failure was the staging rig, not HALOS

Measured:

- SignalK with this plugin set = **~1246 MB RSS** (measured on the boat,
  9h28m uptime, `NRestarts=0`).
- HALOS container stack + OS = **~1000 MB**.
- Total ~2250 MB.

| host | RAM | fits? |
|---|---|---|
| `halos-pi4` staging rig | 1844 MB | **no** — thrashes, as observed |
| `symphony-pi` boat (the target) | 3796 MB | yes, ~1.5 GB headroom |

Same board (Pi 4B Rev 1.5), and the boat boots from SD (`mmcblk0`), so the
card swap is exactly the right mechanism. **The staging box was never able to
run this load; that says nothing about the boat.**

Corollary, stated plainly: the card's *filesystem* can be built and checked at
home, but HALOS *under load* cannot be rehearsed on this hardware at all. The
swap is the test.

## What to watch for after the swap

1. **Does SignalK stay up?** On the staging box it restarted every ~3 min
   because the container healthcheck (`curl -sf localhost:3000/signalk`, 10 s
   timeout) *succeeded but overran its timeout* — a 13.2 s API response was
   measured — so `autoheal` restarted a healthy server. Expected to disappear
   on 4 GB. **If it persists on the boat, that is the finding**, and the fix
   is the healthcheck timeout, not the server. Do not pre-emptively edit the
   compose file: it is package-managed and not a conffile, so an `apt upgrade`
   silently reverts it.
2. **`can0`.** It cannot exist at home — the PiCAN-M HAT is on the boat. The
   `n2k-can0` provider will error until the card is in the boat Pi, and
   `/dev/i2c-1` was also absent at home. First real test of B1a/B1c.
3. **QuestDB's memory.** B1b enables the memory cgroup, which activates
   QuestDB's previously-inert `mem_limit: 768m`. HALOS documents this as the
   intended behaviour and measured it *better* (43 MB RSS vs 312 MB heap), but
   it has never been observed on this card. Watch QuestDB specifically.
4. **SignalK is uncapped** — no `mem_limit` in its compose — so it will not be
   OOM-killed at 1246 MB. Confirmed from HALOS's own compose.

## Rollback

The boat's current 32 GB card is the rollback and holds the only copies of
`~/influx-export` (1.4 GB) and `~/keep-before-purge/grafana.db`. Keep it.

## Two decisions waiting on you (not swap blockers)

- **Both anchor-alarm plugins are installed on the boat but disabled** — no
  config entry, and neither sets `signalk-plugin-enabled-by-default` (verified
  against signalk-server source, not assumed). No anchor activity in two days
  of logs; zero anchor zones in `baseDeltas.json`. The card copies this state
  faithfully, so the trial reproduces the gap.
- **`signalk-mob-notifier` and `signalk-dsc` are enabled in the repo and
  entirely absent from the boat.**
