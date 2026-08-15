# signalk-plugin-watchdog

Raises a SignalK notification when an enabled plugin that should be
publishing deltas publishes none — either never since startup (the
bt-sensors D-Bus incident: plugin loads, its supply dies, absence is the
only symptom) or no longer (published this boot, then stopped).

Notify-only by design. It never restarts anything; notifications land on
`notifications.pluginWatchdog.<pluginId>` with state `alert`, so existing
alarm delivery (zones consumers, Pushover/ntfy relays, a speaker) picks
them up for free, and a recovery or a deliberate disable retracts the
alarm with state `normal`.

## How it detects

Reads `app.providerStatistics` — the per-plugin delta counter the server
increments at the top of `handleMessage`, *before* `$source` rewriting,
keyed by the real plugin id. This is the counter behind the admin
dashboard's rate column, so a plugin that publishes as `House Battery 1`
is still counted as `bt-sensors-plugin-sk`. A mute plugin shows up as an
absent key (entries are created lazily on the first delta), which this
plugin treats as a count of zero.

Only plugins there are grounds to expect deltas from are judged:

- plugins seen producing at least once, on any boot — persisted in
  `known-producers.json` in this plugin's data dir; or
- plugin ids listed in `expectPlugins` (watched from the first boot,
  before anything has been learned — put `bt-sensors-plugin-sk` here).

Everything else — webapps, pure consumers like a database writer — is
legitimately silent forever and never alarmed on. The first boot after
install therefore learns quietly; protection against mute-from-startup
begins on the next boot (or immediately, for `expectPlugins` entries).

## Config

- `checkIntervalSeconds` (30) — poll cadence.
- `graceSeconds` (300) — startup window in which "never published" cannot
  fire. Cover the slowest plugin's first publish; BLE first polls take
  minutes.
- `stallSeconds` (900) — alert when a watched plugin that has published
  this boot goes this long without a new delta. 0 disables. Keep it well
  above the slowest real cadence you have (a 60 s BMS poll needs several
  missed polls, not one).
- `expectPlugins` — always-watched plugin ids.
- `excludePlugins` — never-watched plugin ids.

## Caveats, honestly

- `providerStatistics` is not part of the documented plugin API. It
  reaches plugins by accident of how the server copies its state into
  each plugin's `app`. If a server release stops sharing it, this plugin
  sets a plugin error and does nothing rather than guess. Verified
  working against signalk-server 2.31.0.
- Enumerating *enabled* plugins from inside a plugin has no supported API
  either: `app.getPluginsList` exists internally but is invisible to
  plugins (interfaces receive a Proxy over a key-snapshot taken before it
  is assigned — verified against 2.31.0 and master). Fallback: this
  plugin reads `plugin-config-data/*.json`, the same on-disk truth the
  server reads. A leftover config file for an uninstalled plugin that was
  once seen producing would false-alarm; remove the stale file or add the
  id to `excludePlugins`.
- The counter counts `handleMessage` calls, incremented even for updates
  the server then discards as invalid — a plugin spamming broken deltas
  still looks alive. Acceptable: that failure mode is visible in the log,
  unlike silence.

## Test

`test/run-test.sh <dir with signalk-server installed>` runs a real
signalk-server against two fixtures: `mute-plugin` (starts cleanly, never
publishes) and `flaky-plugin` (publishes every 2 s unless a marker file
exists). It asserts the failure path positively — alert on
mute-from-startup via `expectPlugins`, alert on a learned producer that is
mute after a restart, no alert for the healthy plugin, and alarm clearance
on recovery.

```sh
mkdir /tmp/skdev && cd /tmp/skdev && npm install signalk-server
./test/run-test.sh /tmp/skdev
```

Not published to npm. Local to Symphony until the undocumented-API
question is settled upstream (official `providerStatistics` access and a
supported `restartPlugin` are the two core PRs worth proposing).
