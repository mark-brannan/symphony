# Monitoring: who owns which job

Decision record, researched 2026-08-14. Companion to
[monitoring_posture.md](monitoring_posture.md) (the measured map) and
[signalk_plugin_watchdog.md](signalk_plugin_watchdog.md) (why the plugin exists).
Four roles, one owner each. Every load-bearing claim is tagged **[verified]**
(fetched, read, or measured during this research — source named) or
**[recall]** (plausible, not checked).

## The decisions

| Role | Owner | Add | Retire | Cost to switch |
|---|---|---|---|---|
| 1. Off-boat liveness & host health | **healthchecks.io hosted + `boat-heartbeat`** — keep | extend `/fail` conditions; endpoint-down escalation; weekly report email | nothing | shell edits, no new accounts |
| 2. Onboard vessel alarming | **SignalK notification bus** (zones, hoekens-anchor-alarm, mob-notifier) — keep | Pushover relay (internet path); self-hosted ntfy + `signalk-ntfy` (LAN path); speaker **[hardware]** | nothing | two plugin installs, one small server, one speaker |
| 3. History & forensics | **Telegraf → InfluxDB → Grafana** — keep, forensics-only but need to make decision on questdb in  longer term | soft warning tier in the heartbeat; warn zones on `signalk-rpi-monitor` paths | `signalk-rpi-uptime` (boat), `signalk-rpi-stats` (dev) | plugin disable + zone config, reversible |
| 4. Staleness | **off-boat freshness check** — age *and existence* of critical paths → a second healthchecks.io check | nothing else: `signalk-data-age-watchdog` demoted to optional (blind to never-published; core subsumes it, PR #2689) | bespoke watchdog plugin optional; `signalk-ble-check` stays | one script, an afternoon |

Nothing above waits on the VPS. No recommendation needs hardware the boat
doesn't have, except where flagged under Siren Marine.

Roles 1 and the off-boat half of 4 collapse into the heartbeat + healthchecks.io.
Role 2 and the onboard half of 4 collapse into the notification bus. Role 3
stays its own stack and must stay alarm-free — see below.

## Role 1 — off-boat liveness and host health

**Keep healthchecks.io, hosted. Don't self-host it. Don't switch providers.**

### The reliability record (open question 1)

healthchecks.io offers no SLA and publishes no uptime figure; the FAQ is
candid that "the ops team consists of a single person, so multi-hour or even
multi-day outages are possible." **[verified — healthchecks.io/faq;
status.healthchecks.io and the docs both fetched, no uptime figure anywhere]**
The third-party record is better than that reads: StatusGator's last 60 days
show 7 incidents, 4 minutes to 6h38m, all degradation rather than down
**[verified — statusgator.com/services/healthchecksio]**.

Verdict: on paper worse than a contractual three nines; in practice brief
degradations, and the boat's own uplink misses more pings than the provider
ever will. Not worth a migration — worth *detection*, which is question 2.

### Fails-silent (open question 2)

No hosted dead-man's-switch service I surveyed — Cronitor, Dead Man's Snitch,
Better Stack, healthchecks.io — advertises an unsolicited "still receiving
you" signal. **[search-level check, not exhaustive]** The confirmation has to
be assembled, and healthchecks.io gives three usable parts:

1. **Every ping is acknowledged synchronously.** The heartbeat's `curl -f`
   only succeeds on a 2xx, and the script already logs
   "ping failed (offline or endpoint down)" — the boat knows, it just tells
   nobody but syslog. **[verified — host/boat-heartbeat:106-115]** The fix:
   when pings fail repeatedly *and* the uplink is otherwise up (a probe to any
   unrelated host succeeds), POST directly to the Pushover API — a different
   company's infrastructure — saying "unmonitored." ~15 lines of shell in the
   existing script. This converts fails-silent into fails-noisy without
   changing provider. The remaining hole — provider down *and* uplink down at
   once — no service can fill, because nothing can leave the boat.
2. **Periodic email reports.** Daily, weekly, or monthly summary of every
   check's status and downtime stats. **[verified — healthchecks.io docs,
   Configuring Notifications]** Turn on weekly: an arriving report is positive
   proof the account, checks, and email channel all work; a missing Monday
   report is itself a tell. Zero cost, zero infrastructure.
3. **Public status badges.** Per-check JSON at an unauthenticated
   hard-to-guess URL. **[verified — healthchecks.io/docs/badges]** Anything
   independent can poll it — the future VPS, a free external monitor, a phone
   widget. Noted for later; not worth a new account today.

Plus status.healthchecks.io supports subscriptions for their own incidents.
**[verified — page fetched]**

### Self-hosting verdict

**No.** A single unredundant VPS running Django + PostgreSQL + SMTP would
replace their load-balanced app tier and hot-standby database with something
strictly worse, and the monitoring would then itself need monitoring — the
regress the dead-man's-switch design exists to avoid. The DMS shape is right:
alarms must originate somewhere the Pi's death can't reach, argued in the
heartbeat's own header comment and unchallenged by anything found here. Push
alerting *from* the boat dies with the boat or its uplink, every time.

### While in the script

The posture doc's finding stands: nine vitals travel in the ping body, two can
trip `/fail`. **[verified — read the script]** A failed `signalk.service` unit
should page, not sit in a ping body nobody opens. Adding failed-units (and
arguably sustained throttling) to the `/fail` conditions is the highest-value
change in this whole document, and it's a few lines.

## Role 2 — onboard alarming for vessel events

**Keep the SignalK notification bus and everything hanging off it.** This is
the one place the ecosystem is genuinely best-of-breed for a boat: zones are
server core, and the attached plugins are alive —
hoekens-anchor-alarm v2.13.0 published 2026-08-14 (today),
signalk-notification-player v2.7.0 from 2026-07. **[verified — npm registry]**
Nothing surveyed replaces this bus; everything else would have to feed it
anyway.

The weak joint is delivery, and owner facts from 2026-08-14 demote it further
than first written here. `signalk-push-notifications` relays through Amazon
SNS to the WilhelmSK app **[verified — README]**, which is iOS-only; Mark's
phone is Android, and WilhelmSK lives on an iPad that is only occasionally
aboard. Meanwhile nothing is wired to the Pi's audio output, so
notification-player plays to a jack with no speaker **[owner-stated]**. The
bus raises alarms fine; in practice, both delivery ends are missing and
vessel alarms currently ring nowhere.

So the Pushover relay is not redundancy — it is the primary path to build.
Pushover is already tested end to end and lives on Mark's Android phone.
Candidates, ranked:

1. **signalk-pushover-notification-relay** — general notifications→Pushover
   relay, exactly the right shape. v1.0.0, published 2022, untouched since.
   **[verified — npm]** Old, but small, and the Pushover API is stable
   **[recall]**. First choice; audit the config behavior on install.
2. **Node-RED flow** — the engine already runs aboard with zero flows;
   subscribing to `notifications.*` and POSTing to Pushover is a small flow
   and no new plugin. Fallback if 1 is broken.
3. **signalk-ntfy** — actively maintained (2026-07) **[verified — npm]**. No
   as an internet path — channel coverage is settled — but adopted 2026-08-14
   for what Pushover can't do: pointed at a self-hosted ntfy server on the
   Pi, it reaches the Android over boat WiFi with the internet down. Owner's
   call: that *and* a speaker, deliberately redundant for the
   dragging-anchor-at-night case.

WilhelmSK/SNS stays enabled as a freebie for the iPad when it's aboard.
Whether an Android-native SignalK alarm app exists is an open question,
parked in priorities.md rather than guessed at here.

Noted in passing: `signalk-pushover-plugin` is anchor-specific but can push
"everything is okay" at an interval **[verified — README]** — positive
confirmation for anchor watch, if that's ever wanted. Audible alarming aboard
needs hardware that isn't there: a speaker on the Pi's audio out, or a piezo
on GPIO — the beeper plugin is already installed, disabled. That purchase and
wiring decision is physical boat work **[hardware]**.

## Role 3 — history and forensics

**Keep Telegraf → InfluxDB → Grafana, and keep it forensics-only.** Grafana
alerting and InfluxDB checks were considered and rejected on architecture, not
quality: both services are this project's designated memory-pressure release
valve, stopped without asking when the Pi is squeezed — which is precisely
when a host alarm would need to fire. An alarm path that policy turns off
under load is not an alarm path. Alarming belongs to Roles 1 and 2.

**Delete the duplicate collectors.** Host metrics are collected three times
(posture doc, confirmed). Telegraf is the intended source, has the history,
and its `telegraf-rpi-health` exec input latches under-voltage and throttling
since boot **[verified — read the script]** — better power forensics than
`signalk-rpi-monitor` offers. The rpi plugins' only alarm value was zones
that were never configured; the one zone ever configured aboard — air
quality — was attached to a path no sensor has ever published
(`environment.inside.airquality` is absent from the vessel tree on both
boxes, checked live 2026-08-15), so no zone aboard has ever been live.

First written as: disable all three. Amended 2026-08-14 after the owner asked
for an early-warning tier on host metrics: `signalk-rpi-monitor` stays,
because it is the one thing that can put host metrics on the notification
bus — configure warn-band zones on its paths (thresholds derived from its
own utilisation formula, per the posture doc) and host warnings ride the
same onboard delivery as vessel alarms. That gives it a real job, which it
didn't have before, so the Telegraf overlap now earns its place. A soft
warning tier also goes into the heartbeat: pre-alarm thresholds send a
low-priority Pushover message directly — quiet buzz, never `/fail`.
`signalk-rpi-uptime` (boat) and `signalk-rpi-stats` (dev) still go. Before
disabling, grep KIP and any dashboards for those plugins' paths so a widget
doesn't go quietly blank — that check is the entire switching cost. Amended 2026-08016 after
Mark did an independent investigation of QuestDB vs InfluxDB; questdb looks better
on almost every dimension, and in particular, seems better for resource constrained systems.
The only strong argument for influxdb is that is has historic integration preference
among signalk users and therefore more plugins and perhaps support, but it also
looks like the tide is turning and experienced users growing to prefer questdb.
Given the rough shape of the DB on the boat today, we are not locked into either one
and should use whatever shows more long term promise.

Vessel history: the boat necessarily runs the InfluxDB path today — the
QuestDB pair needs Docker.  Choosing between
the InfluxDB and QuestDB paths is a rebuild-machine decision; nothing about
it needs deciding now. PostgSail, SailLogger, NoForeignLand are cruising-log
services, not forensics — untouched.

## Role 4 — alarming when data stops

**The off-boat freshness check is the load-bearing piece.** A small sibling
timer to `boat-heartbeat` queries SignalK's REST API on localhost and pings a
second healthchecks.io check — `/fail` on stale timestamps, **absent paths**,
or no answer at all. One script covers went-quiet, never-published, and
wedged-server alike. It stays separate from `boat-heartbeat` itself, which is
deliberately too dumb to parse JSON and should stay that way.

**Every path-level approach misses mute-from-startup.** This is the durable
rule behind the ranking, and it cost a reversal to learn: a plugin that dies
at load and never publishes (the bt-sensors incident —
`electrical.batteries.*` never enters the tree at all) is invisible to
anything that walks paths or the delta cache. Only per-plugin delta counts
(`app.providerStatistics`) or an external expectation list can catch it.

- `signalk-data-age-watchdog` (v1.0.4, MIT, zero deps) — **optional.** It
  monitors path age and raises `notifications.<path>.dataAge.dataStale`, but
  calls `app.getSelfPath(path)` and silently skips any path with no
  timestamp, so it detects went-quiet-*after*-publishing only. Also one
  global threshold for every path, a hardcoded 1-second poll, and a
  `<path>.dataAge` delta every second per monitored path — noise
  signalk-to-influxdb2 would faithfully write to the SD card. If installed
  anyway, keep its `.dataAge` paths out of influxdb. **[verified — the
  82-line index.js from the npm tarball]**
- **Server core covers the same slice, opt-in.** The staleness enforcer
  (PR #2689, merged 2026-07-11) shipped in v2.31.0: `enforceDataTimeouts` in
  settings, default off. It learns per-path cadence and flags `timedOut` per
  path+source, and has the identical blind spot. **[verified —
  signalk-server git tags; src/index.ts gates on `=== true`]**
- `signalk-ble-check` **stays** — it is the only *recovery* mechanism aboard,
  and detection without recovery still means a dead battery feed until
  someone acts.
- `signalk-dead-mans-switch` is a crew-liveness escalation, a different
  problem. **[verified — registry description]**

### The bespoke watchdog plugin

**Build-but-don't-publish.** v1 notify-only is built, tested, and running on
`symphony-pi` at `plugins/signalk-plugin-watchdog`: learned-producer
expectations persisted across boots plus an `expectPlugins` list, alarming on
`notifications.pluginWatchdog.<id>` over the Role 2 bus. It earns an optional
slot as the only mechanism catching mute-from-startup *onboard with no
uplink*; the original bar — restart automation — remains unmet, so detection
stays with the freshness check.

What the source says about the two hooks it stands on **[verified against
signalk-server master @ b9802a72 and a live v2.31.0 instance]**:

- `providerStatistics` is real and reliable: incremented as the first
  statement of `handleMessage`, before all `$source` rewriting, keyed by the
  registered plugin id whatever id or label the plugin supplies; rates
  recomputed every 5 s. A never-published plugin shows as an *absent key*,
  since entries are created lazily on the first delta. But it reaches plugins
  by accident, not contract — absent from the server-api types and all docs,
  shared only because the server copies its state into each plugin's `app`.
- Enumerating *enabled plugins* has no plugin-visible API. `app.getPluginsList`
  exists internally, but interfaces receive a Proxy over a key-snapshot taken
  before it is assigned, so plugins see `undefined` — on 2.31.0 and master
  alike. Fallback: read `plugin-config-data/*.json`, the same on-disk truth
  the server reads.
- Restart is admin-only. The sole external path is `POST /plugins/:id/config`,
  hard-gated to admin auth (`/config` is a reserved path plugins cannot
  re-permission); `stopPlugin` is module-private and there is no
  `restartPlugin`.

Publishing to npm waits on two upstream PRs — official `providerStatistics`
access and a supported `restartPlugin` — since today it stands on an
undocumented accident. It also stays vulnerable to `~/.signalk`'s
`package-lock=false` `npm install` behavior, which prunes any plugin with no
`package.json` dependency entry.

## Considered and rejected

- **Netdata** — agent sized at 100–200 MB by their own docs, 200–500 MB
  reported in practice on Pis **[verified — netdata sizing docs and community
  threads via search]**. Rent in the watched resource, and its cloud
  reachability alerts would fire on every routine uplink drop. No.
- **Zabbix** — server + database stack needs a permanent home (the unbuilt
  VPS) and its model assumes reachable agents; an intermittent uplink reads
  as flapping. Footprint figures **[recall]**. No.
- **Prometheus + Alertmanager** — pull model; scraping a boat that is
  normally unreachable makes absent-data alerts the steady state, which is
  the noise the constraints forbid. Needs the VPS besides. No.
- **Uptime Kuma** — good product; push monitors are a proper dead-man's
  switch, ~80–200 MB self-hosted **[verified — docs/reviews via search]**.
  But it is self-host-only, so as primary it inherits the whole self-hosting
  regress. Possible future role: polling the healthchecks badge from the VPS
  as the independent watcher. Not now.
- **ntfy / Gotify / Apprise** — channel plumbing; channel coverage is
  settled. Written here first as a full no, on the grounds that the audible
  path covered the offline-aboard case — then the speaker turned out not to
  exist. Reversed 2026-08-14 for ntfy alone, self-hosted on the Pi as the
  LAN-only delivery path (see Role 2). Gotify and Apprise stay out.
- **Siren Marine (Siren 3 Pro)** — $749.99 device; $22/mo, $150/yr seasonal,
  or $225/yr plans; own LTE-M cellular and own sensor inputs. **[verified —
  sirenmarine.com and retailers via search]** The only candidate that still
  alarms when the Pi *and* its uplink are both dead, because it shares
  nothing with them. That's a different threat tier — bilge, fire, theft with
  total electronics loss — and needs hardware not owned plus its own wiring
  **[hardware]**. Internal backup battery and offshore LTE-M coverage limits
  **[recall — check before any purchase]**. Not recommended now; revisit if
  unattended risk tolerance changes.
- **Self-hosted healthchecks** — see Role 1. No.

## Corrections and confirmations to the source docs

- monitoring_posture.md's registry claim ("no plugin covers plugin-level
  staleness", via the watchdog brief) is **overturned** for path-level
  staleness by signalk-data-age-watchdog; plugin-level supervision with
  restart remains genuinely uncovered.
- signalk-healthcheck was **not** removed on 2026-08-14, as this doc first
  said — that claim came from a same-day software_stack.md edit, and a boat
  check later that day (recorded in priorities.md) found it still installed
  and enabled, only reconfigured. The posture doc's description of it stands.
  Retiring its host section and keeping its provider watch is settled in
  priorities.md; its provider-staleness capability is folded into Role 4
  above either way.
- Everything else in the posture doc survived challenge: the three-stack map,
  zones firing only on arriving values (not re-verified in source, no
  contradiction found), and the dead-man's-switch rationale, which this
  research reinforces rather than weakens.
