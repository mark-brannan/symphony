# HALOS swap prep — execution checkpoint, 2026-09-02

Session `symphony-pr-33-review-601c06-0a` (Fable), working PR #33 and the bench
card `symphony-halos` (192.168.0.193) overnight on Mark's instruction. Updated
as work lands. Facts are measured unless marked otherwise.

## Bench card state (halos)

Done tonight, in order:

- AvNav, OpenCPN: stopped and disabled (staydown). InfluxDB app apt-removed.
  Homarr `docker stop`ped for the build (bench only; comes back on a
  core-containers restart, re-stop it).
- SignalK restart loop root-caused: HALOS's container healthcheck allows
  60 s + 3×30 s for startup; a cold start with this plugin set takes 3–4 min
  on the bench, so autoheal restarted a server that was still booting.
  Fix: systemd drop-in `marine-signalk-server-container.service.d/symphony.conf`
  adds `-f /etc/container-apps/marine-signalk-server-container/symphony.override.yml`
  (start_period 900 s, timeout 30 s, probe 127.0.0.1). Package compose file
  untouched. Healthy since 06:51Z.
- `/dev/i2c-1`: `i2c-dev` persisted in `/etc/modules-load.d/`.
- Tailnet node renamed `symphony-halos` (B2d).
- telegraf + chrony installed from the InfluxData repo (B4a); telegraf runs the
  repo config as `pi` via symlink + drop-in; `systemd-timesyncd` removed by chrony.
- `host/install.sh` from PR #34's branch run to completion: watchdog conf,
  heartbeat + ble-check timers enabled and active, chrony conf. The
  `claude-resident` user unit step fails on this card (no such unit); harmless.
- `/etc/boat-heartbeat.json` points at a **second** healthchecks.io check,
  `SignalK Symphony (halos card)`, same Pushover channel, so the bench card's
  pings cannot mask a boat outage. `ping ok` confirmed.
- WiFi (B2a/B2b): boat profiles `Symphony` and `Symphony_5G` installed from
  the boat's keyfiles; HALOS's `Halos-AP` hotspot renamed to SSID `SignalK`
  with the boat's key. All three keyfiles are backed up in sops
  (`nm_*_nmconnection`, main e2c34b2).
- ntfy (B4c): up on :8090 from the repo compose, health 200.
- zram: `systemd-zram-generator`, 1 GB zstd at priority 100 — bench aid so the
  2 GB box can run the full stack for a soak without SD-card swap thrash.
- Hostname `signalk`, `hostname -d` = boat domain (B2c). HALOS's canonical
  name is the *first* entry of `/etc/halos/hostnames.conf`, so the order is
  now `${fqdn}`, `${hostname}.local`, `${domain}` (the plan's literal
  `symphony.<boat-domain>` line was wrong: `boat_domain` in sops *is* the
  apex, so `${domain}` covers it). Result: `HALOS_DOMAIN=signalk.symphony.dark-star-llc.com`,
  device cert SANs `signalk.local`, `signalk.symphony.dark-star-llc.com`,
  `symphony.dark-star-llc.com` (07:27Z). SignalK restarted for the new
  `extra_hosts` entry.

- B5a Traefik router `/etc/halos/traefik-dynamic.d/symphony-signalk-host.yml`
  installed 07:33Z (priority 50 on `websecure`, `host.docker.internal:3000`).
  Measured with `--resolve` against 127.0.0.1: `/` → 302 to `/admin/`
  (SignalK's own redirect, so SignalK serves the root), `/ca` → 302 `/ca/`,
  `/ca/` → 200 CA download, `/sso` → 404, `/sso/` → 200 whose first bytes
  mention `signalk` — **confirm that body is Authelia** (`grep -c -i authelia`)
  before trusting SSO; if it is SignalK, the `!PathPrefix` exclusion is not
  winning and the file should be deleted.
- 07:35Z: Mark's Opus session is wiring i2c on the bench box; hands off it
  from here.

## Boat card (symphony-pi) — touched read-only except:

- `systemctl reset-failed grafana-server unattended-upgrades` (06:45Z): the
  heartbeat had been pinging `/fail` on those two dead units and the
  healthchecks.io check showed *down*. Up since.
- Router: DHCP reservation `cerbo` 5c:c5:63:0a:df:52 → 192.168.8.107 added.

## Verified tonight

- `scripts/dns_cutover.sh set` works both ways from home; public resolvers
  followed within 30 s each way (07:14Z). Record is back on `symphony-pi`.
- Baseline `scripts/halos_swap_check.sh symphony-pi` at 07:16Z: signalk, lan
  (eth0 + can0 UP), ble (1 of 5 sensors publishing), heartbeat, ntfy, bme680
  ok. Pre-existing on the boat, not swap-caused: Victron MQTT to the Cerbo in
  SYN-SENT since 2026-09-01 21:06Z (Cerbo answers on no port); position comes
  from `signalk-fixed-position`, not N2K (N2K itself is live: water
  temperature fresh); QuestDB `signalk_position` last written 2026-08-20
  (`signalk` table is live).

- Boat QuestDB is overloaded: `questdb` container at 164 % CPU, even the
  metadata queries `tables()` / `wal_tables()` time out at 30 s, and the boat's
  load average is 11.8 with 13 logged-in users (07:23Z). Pre-existing. The
  swap check's `questdb` line needs a query that is cheap on the boat too, or
  the runbook says the baseline may time out there.

## Not yet done

- Reboot soak with all units, preflight run to green (script untested
  against halos as a whole; its `front` and `plugins` lines are new), PR #33
  slimmed and rebased, plan + runbook updated with real output, swap-day
  dispatch prompt, pypilot (B4d) decision.
- Swap check re-run on the boat at 07:34Z after the fixes: every line ok
  except `victron` (Cerbo) and `questdb` (boat QuestDB does not answer in
  30 s) — both pre-existing, both now explained in the line itself.

## Session pr33-comments-merge-33902c (Fable), from 10:00Z

- PR #33 review threads all answered and resolved; #35 (i2c `group_add`)
  merged into the PR branch by Mark at 10:16Z.
- Step 1: `signalk-server` `(healthy)` after the 07:40Z reboot. Step 2:
  `/sso/` confirmed Authelia; router file stays.
- First end-to-end `halos_preflight.sh` run. Script side: ssh to a renamed
  tailnet node needs the host key accepted, so both scripts now pass
  `StrictHostKeyChecking=accept-new`. Card side, fixed on the card:
  `systemd-networkd-wait-online` enabled at 03:18 today by a session (not
  stock), failing every boot → disabled; InfluxDB unit left behind by
  `remove` → package purged; `reset-failed`; heartbeat back to `ping ok`.
  Plugin diffs were three image-only packages, now allow-listed (plan).
- The `signalk` preflight line now also checks gid 988 in the container's
  node process via `/proc` (`pi` cannot run docker on HALOS).
- Soak (B6) with zram (`/dev/zram0` is 1.8 GB, not 1 GB): QuestDB and
  Grafana started 10:17Z; five minutes in, 310–345 MB available, ~1.15 GB
  of zram in use, load back to 1.1 from a 6.4 startup peak.
- Rebooted 10:22Z with QuestDB and Grafana enabled: SignalK answered after
  194 s, no failed units, every preflight line `ok` at 10:26Z (401 MB
  available, 1118 MB of zram in use). Homarr re-stopped. That block is now
  the runbook's. `/dev/zram0` reports 1.8 GB.
