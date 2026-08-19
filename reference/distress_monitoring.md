# DSC / AIS distress monitoring

The distress-monitoring facet of Symphony's stack: receiving other vessels'
DSC calls and AIS survival beacons, alarming on them, and (eventually)
getting that alarm to a human. It is deliberately documented as its own
facet, separate from the host/vessel monitoring in
`monitoring_decisions.md`, so the pattern is liftable by other boats.

**The standing rule frames everything here: the radio's distress button is
never pressed to test anything** (`maintenance/priorities.md`). Every claim
below was verified by reading source or by synthetic injection with nothing
on the air — `RUNBOOK.md` → "Testing the DSC / AIS distress receive chain".

## Hardware aboard

- Handheld VHF with DSC and an emergency button.
- AIS Class B transceiver (receives other stations' traffic, including
  survival beacons).
- No MOB button, crew tags, or beacon hardware of our own.

## The receive chain

Three plugins, all receive-only:

- **`@sailingnaturali/signalk-dsc`** — parses DSC traffic from NMEA 0183
  (`DSC`/`DSE`, replacing the server's stock hook with a more tolerant
  parser) and NMEA 2000 (PGN 129808, which `n2k-signalk` doesn't map at
  all). Per received call it: appends to an on-disk JSONL log served at
  `/signalk/v2/api/resources/dsc-calls`; raises a **per-call** notification
  `notifications.received.<category>.dsc-<id>` (distress → `emergency`,
  urgency → `alarm`, safety → `warn`); emits the caller as a SaR target
  (`sar.urn:mrn:imo:mmsi:<caller>`) for distress, so chartplotters render a
  distress target; serves per-category GeoJSON marker layers at
  `/resources/dsc-call-markers`; optionally writes a GMDSS-style entry via
  signalk-logbook. Active distress alarms re-raise for up to an hour across
  server restarts.
- **`@sailingnaturali/signalk-ais-distress`** — watches the AIS position
  stream for survival-beacon MMSIs (970 SART, 972 MOB, 974 EPIRB) and does
  the same per-beacon treatment: `notifications.received.distress.ais-<id>`
  at `emergency`, `/resources/ais-distress`, marker layer, JSONL log.
- **`@meri-imperiumi/signalk-mob-notifier`** — independently consumes AIS
  MOB beacon (972) position reports and raises `notifications.mob` at
  `emergency`. Overlaps with signalk-ais-distress on the MOB class only;
  the overlap is deliberate redundancy, not a conflict.

Both sailingnaturali plugins share `signalk-distress-core` and are by the
same author, who corresponded with us 2026-08 after reading this repo.

## What is verified, and where

Validated 2026-08-19 on a faithful rebuild of the dev stack (same
`signalk/signalk-server:latest` image, 2.31.1, this repo's `signalk/`
config) in a cloud sandbox, by synthetic UDP injection:

- Parse → store → REST resources, for DSC distress and urgency calls and
  for SART/MOB AIS beacons. Parsed fields (MMSI, nature, position, UTC
  time) all correct against what the scripts sent.
- Per-call notifications at the right states; two concurrent calls hold two
  alarms.
- SaR context emission for distress callers; marker ResourceSets serving
  GeoJSON.
- `signalk-mob-notifier` raising `notifications.mob` at `emergency` off a
  synthetic 972 beacon.
- Restart re-announce: active alarms restored into the model after a server
  restart.
- Token-authed clearing (`clear-dsc-alarm.js` / `clear-ais-alarm.js`):
  alarms drop to `normal`, restart re-raise stops.

Not yet verified anywhere real: the boat (neither plugin is installed
there), the logbook integration (needs a token the sandbox didn't have),
and the ntfy hop below.

## The alarm-delivery gap

Found during that validation, reproduced at will, and it is the reason this
facet is not yet done:

**signalk-server 2.31.1 never delivers the first `values` delta of a
newly-created path to a wildcard subscriber that is already attached.** A
plugin subscribed to `notifications.*` receives the later `meta` delta for
the new path, and receives every subsequent delta on it — but the delta
that creates the path is lost. Six consecutive synthetic distress calls: 0
of 6 alarm deltas reached the subscriber; the follow-up clear deltas on the
same paths all arrived. The one delivery observed in testing happened only
when a meta delta preceded the values delta and so absorbed the path
creation.

Because the distress plugins raise **per-call unique paths** (by design —
concurrent calls must not overwrite each other), the lost first delta *is*
the alarm. Consequences, all observed directly:

- `signalk-ntfy` never fires for a distress alarm. Neither would the
  Pushover relay or a Node-RED flow subscribed to `notifications.*` — any
  wildcard subscriber has the same view.
- The restart re-announce recreates the paths, so re-announced alarms are
  equally invisible to delivery plugins.
- The REST model, chart markers, and SaR targets are all unaffected — the
  alarm exists; it just never reaches the delivery layer.
- One-shot fixed-path alarms lose their first raise the same way
  (`notifications.mob` was also undelivered in testing).

Mitigation paths, in preference order:

1. **Upstream fix in signalk-server** — the bug is in path-bus creation vs.
   wildcard-subscriber attachment; the repro in the RUNBOOK section is
   minimal and deterministic. Not yet reported as of 2026-08-19.
2. **Plugin-side workaround** — emitting meta (or registering the PUT
   handler) *before* the first values push makes the meta delta create the
   path, and the alarm then delivers. Evidenced directly: the single
   delivered alarm in testing had exactly that ordering. Suggested to the
   plugin author 2026-08.
3. **A delivery subscriber that doesn't use per-path wildcard buses** —
   `app.streambundle.getSelfBus()` with no path argument is a single bus
   attached once, so it sees every delta including path-creating ones.
   A small custom delivery plugin (or a patched signalk-ntfy) subscribing
   there and filtering `notifications.` prefixes client-side would be
   immune. Not built; only worth it if 1 and 2 both stall.

Until one of these lands, the honest status is: **distress calls are
received, logged, charted and alarmed aboard, but nothing pushes them to a
phone.** Verify alarms via REST, not by waiting for a buzz.

Separately noted: `signalk-ntfy` 0.0.7's `filterDuplicates` and
`minIntervalMinutes` config keys are unimplemented — they appear nowhere in
the plugin source — so our tracked config implies dedupe behavior that
doesn't exist.

## DSCWatch reporting

signalk-dsc reports every received DSC call to dscwatch.com (a crowdsourced
receiver network) **by default**, including the receiver's own position,
and queues undelivered reports on disk to send when connectivity returns.
The dev config has it enabled with MMSI 368391180 as the receiver key.
Whether the boat should report — and under the vessel MMSI or an anonymous
key — is an open owner decision, tracked in `maintenance/priorities.md`.
Non-negotiable either way: reporting must be off (or pointed at a mock)
while synthetic calls are being injected, or the fakes get reported as
heard traffic — including later, from the disk queue, after an offline
test.

## Status

- Dev container: `signalk-dsc` 0.10.0 installed, enabled, configured;
  `signalk-ais-distress` 0.5.0 installed, disabled. `signalk-mob-notifier`
  enabled.
- Boat: neither sailingnaturali plugin installed; `signalk-mob-notifier`
  installed. Whether the boat's SignalK version exhibits the same delivery
  bug is unverified — check before building on either answer.
- Install-and-validate on the boat is a tracked backlog item with its
  prerequisites (DSCWatch decision, delivery gap) listed there.

## The pattern, for other boats

What we'd tell another owner replicating this: install the pair, leave the
radio's button alone forever, and validate with the synthetic scripts from
the plugin repos (clone them — the npm tarballs omit `scripts/`). Test the
chain stage by stage against REST rather than trusting a single end signal,
and test your delivery layer *separately* with a fresh-path alarm — ours
looked configured and working, and had a 0% delivery rate for the alarms
that matter most. Decide the DSCWatch privacy question deliberately, and
disable it while testing. Redundant consumers (signalk-ais-distress and
mob-notifier both alarming on MOB beacons) are cheap and worth keeping.
