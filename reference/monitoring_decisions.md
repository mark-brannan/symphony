# Monitoring: who owns which job

Decision record, researched 2026-08-14. Companion to
[monitoring_posture.md](monitoring_posture.md) (the measured map) and
[signalk_plugin_watchdog.md](signalk_plugin_watchdog.md) (the build proposal).
Four roles, one owner each. Every load-bearing claim is tagged **[verified]**
(fetched, read, or measured during this research — source named) or
**[recall]** (plausible, not checked).

## The decisions

| Role | Owner | Add | Retire | Cost to switch |
|---|---|---|---|---|
| 1. Off-boat liveness & host health | **healthchecks.io hosted + `boat-heartbeat`** — keep | extend `/fail` conditions; endpoint-down escalation; weekly report email | nothing | shell edits, no new accounts |
| 2. Onboard vessel alarming | **SignalK notification bus** (zones, hoekens-anchor-alarm, mob-notifier) — keep | Pushover relay (internet path); self-hosted ntfy + `signalk-ntfy` (LAN path); speaker **[hardware]** | nothing | two plugin installs, one small server, one speaker |
| 3. History & forensics | **Telegraf → InfluxDB → Grafana** — keep, forensics-only | soft warning tier in the heartbeat; warn zones on `signalk-rpi-monitor` paths | `signalk-rpi-uptime` (boat), `signalk-rpi-stats` (dev) | plugin disable + zone config, reversible |
| 4. Staleness | **off-boat freshness check** — age *and existence* of critical paths → a second healthchecks.io check | nothing else: `signalk-data-age-watchdog` demoted to optional (blind to never-published; core subsumes it, PR #2689) | bespoke watchdog plugin optional; `signalk-ble-check` stays | one script, an afternoon |

Nothing above waits on the VPS. No recommendation needs hardware the boat
doesn't have, except where flagged under Siren Marine.

Roles 1 and the off-boat half of 4 collapse into the heartbeat + healthchecks.io.
Role 2 and the onboard half of 4 collapse into the notification bus. Role 3
stays its own stack and must stay alarm-free — see below.

## Role 1 — off-boat liveness and host health

**Keep healthchecks.io, hosted. Don't self-host it. Don't switch providers.**

### The reliability record (open question 1)

- It is open source, BSD 3-clause, self-hostable: Django, PostgreSQL, a web
  server, and two background daemons. **[verified — github.com/healthchecks/healthchecks README]**
- They do not offer SLAs, in their own words: "We do not offer to sign SLAs"
  and "The ops team consists of a single person, so multi-hour or even
  multi-day outages are possible." Infrastructure is load-balanced app servers
  and a PostgreSQL hot standby with **manual** failover, daily encrypted
  backups to S3. **[verified — healthchecks.io/faq]**
- No uptime percentage is published anywhere I could find — not on
  status.healthchecks.io, not in the docs. **[verified — both fetched]**
- Third-party record: StatusGator has tracked it since Sep 2022 — 236
  status-page events in ~4 years; in the last 60 days, 7 incidents from 4
  minutes to 6h38m, all "warn" (degraded) rather than outright down.
  **[verified — statusgator.com/services/healthchecksio]** That's a count of
  status-page flips, not measured downtime, so it overstates severity.

Verdict: on paper this is worse than a contractual three nines — a one-man
shop that admits multi-day outages are possible. In practice the record is
brief degradations, and the boat's own uplink misses more pings than the
provider ever will. The gap the FAQ admits to is not worth a migration; it is
worth *detection*, which is question 2.

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
that were never configured; the sole configured zone aboard is air quality.

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
doesn't go quietly blank — that check is the entire switching cost.

Vessel history: the boat necessarily runs the InfluxDB path today — the
QuestDB pair needs Docker, which the boat doesn't have. **[verified —
software_stack.md]** Whether `signalk-to-influxdb2` is actually enabled on
the boat wasn't checkable from here (this checkout's plugin configs are the
dev container's); worth a one-minute look next time aboard. Choosing between
the InfluxDB and QuestDB paths is a rebuild-machine decision; nothing about
it needs deciding now. PostgSail, SailLogger, NoForeignLand are cruising-log
services, not forensics — untouched.

## Role 4 — alarming when data stops

**The prior finding was wrong, and the correction changes the plan.** Both
source docs state no registry plugin covers staleness. A full sweep of all
559 packages carrying the `signalk-node-server-plugin` keyword found
**`signalk-data-age-watchdog`**: monitors the age of configured paths,
publishes `<path>.dataAge`, and raises
`notifications.<path>.dataAge.dataStale` past a threshold. v1.0.4, published
2025-06-24, MIT, zero dependencies, single author (Oskari Vuori), no linked
repo. **[verified — npm metadata and README]** The earlier text-searches
missed it; the keyword sweep is the reliable query.

**Corrected same day, from the watchdog session reading its source
[verified — the 82-line index.js from the npm tarball, plus server source]:**
it does *not* cover the failure that motivated the design brief. It calls
`app.getSelfPath(path)` and silently skips any path with no timestamp — so a
plugin that dies at load and never publishes (the bt-sensors incident:
`electrical.batteries.*` never enters the tree at all) raises nothing. It
detects went-quiet-*after*-publishing only. Also source-confirmed: one
global threshold for every path, a hardcoded 1-second poll, and it publishes
a `<path>.dataAge` delta every second per monitored path — noise that
signalk-to-influxdb2 would faithfully write to the SD card.

**Also material: the server core is getting this.** signalk-server master
has a merged, unreleased staleness enforcer (PR #2689, merged 2026-07-11,
missed v2.30.0): it learns per-path cadence and flags `timedOut` per
path+source. Same blind spot — it walks the delta cache, so never-published
paths are equally invisible. The durable rule: **every path-level approach
misses mute-from-startup.** Only per-plugin delta counts
(`app.providerStatistics` in core today — zero means never published) or an
external expectation list can catch it.

**So the ranking flips: the freshness check is the load-bearing piece.** A
small sibling timer queries SignalK's REST API on localhost and pings a
second healthchecks.io check — `/fail` on stale timestamps, **absent
paths**, or no answer at all. One script covers went-quiet, never-published,
and wedged-server alike, and it is the "rebuild the staleness watch in the
heartbeat's orbit" direction software_stack.md already records. Kept
separate from `boat-heartbeat` itself, which is deliberately too dumb to
parse JSON and should stay that way.

`signalk-data-age-watchdog` drops to optional: its remaining niche is a
sensor going quiet mid-passage ringing the speaker with no uplink, and the
next server release subsumes that slice with learned cadences and no extra
plugin. If it is installed anyway, keep its `.dataAge` paths out of
signalk-to-influxdb2.

**What this demotes:** the bespoke watchdog plugin
(signalk_plugin_watchdog.md) drops from necessary to optional. Its remaining
unique value is auto-learning cadences and per-plugin restart — and
`app.providerStatistics` is the right hook for its never-published
detection. Detection of the motivating case lands in the freshness check;
build the plugin only if restart automation proves worth the effort. `signalk-ble-check` stays meanwhile — it is the only *recovery*
mechanism aboard, and detection without recovery still means a dead battery
feed until someone acts. That pairing (watchdog detects broadly, ble-check
recovers narrowly) is redundancy with a purpose, not waste.

`signalk-dead-mans-switch` also exists in the registry but is a crew-liveness
escalation (push a button or alarms escalate) — different problem.
**[verified — registry description]**

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
