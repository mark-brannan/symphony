# Paste-ready prompt — Fable planning session (halos ↔ symphony sync)

Recommended model: **Fable 5.1**, effort **high**. This is far-reaching
architecture + a doc rewrite; it is not credential work. All sensitive bits
(SSH keys, WiFi PSK, tokens, the InfluxDB backup) are handled in a separate
lane — do not touch secrets or spray credentials.

---

You are planning how to get a spare Pi's HALOS SD card configured close
enough to the boat "symphony" that it can be swapped in this afternoon to
trial HALOS on real boat hardware. The old boat card comes home as the
rollback. A prior triage session already inventoried both boxes and split
out the sensitive credential work; build on its output, don't redo it.

## Read first (don't re-derive what these already settle)

- `intermediate_files/claude_slop/halos-sync-inventory-2026-09-01.md` — the
  fresh read-only boat snapshot. Start here.
- `reference/containerization_strategy.md` — the existing Track A / Track B
  plan and the four-quadrant framing. Your plan reconciles with this.
- `reference/compute_hardware.md`, `reference/software_stack.md`,
  `reference/monitoring_decisions.md`,
  `reference/legacy_openplotter_stack.md`, `RUNBOOK.md`.
- halos itself: `ssh pi@192.168.0.193` (key installed by the owner; WSL can't
  resolve `halos.local`, use the IP). Tailscale peer is `halos-pi4`.
- HALOS capabilities: the `halos-org` GitHub org; owner's merged PR is
  halos-org/halos#151.

Verify claims against the running systems and vendor docs. Do not infer
behavior from a config field name and write it up as fact.

## The plan shift you must reconcile

The docs describe trialing HALOS **at home** indefinitely (Track A), keeping
the boat's working card untouched until a decision gate. The owner now wants
to **accelerate**: swap the HALOS card onto the boat today and trial it on
real hardware. Consequences to design around:

- The boat's current stack goes offline for the trial; the old card is the
  instant rollback (swap back).
- `https://signalk.<boat-domain>` must keep pointing at the boat after the
  swap — design a small, scriptable cutover step, not a rework.
- Minimize Tailscale/Cloudflare churn: give HALOS a **new** tailnet node name
  (e.g. `symphony-halos`) rather than renaming `symphony-pi`. Both can
  coexist during the trial.

## Must-retain core functionality (owner's list)

1. **Bluetooth batteries** — `bt-sensors-plugin-sk` and friends.
2. **Monitoring** — Pushover, healthchecks.io, ntfy, the plugin watchdog.
   (Note: `signalk-healthcheck` is currently *disabled* on the boat — confirm
   how healthchecks.io is actually pinged before assuming the plugin is the
   path.)
3. **Victron data** — `signalk-venus-plugin`. Separately, a Cerbo GX runs its
   own Victron install visible in VRM cloud; it is undocumented here,
   independent of the Pi, and **must keep working untouched**. Do not plan
   changes to it.
4. **Network** — connect to the boat LAN with no extra steps (ethernet +
   Tailscale is the likely path; WiFi client + the `SignalK` AP hotspot are
   the boat's current setup).
5. **Drivers** — PiCAN-M: NMEA 2000 (`can0`), NMEA 0183 (`/dev/serial0`),
   I2C/Qwiic. Determine whether these are plug-and-play under HALOS or need
   config.

## Decisions to make (reasoned, don't descope out of convenience)

- **History DB: QuestDB, InfluxDB, or both?** The boat already runs a QuestDB
  container (up 11 days) and InfluxDB is `active/disabled` (mid-retirement).
  HALOS ships QuestDB natively. Weigh whether HALOS's ecosystem makes QuestDB
  the clear choice, whether InfluxDB is worth keeping, or whether to keep both
  trialing against each other. Recommend and justify.
- **SSO / TLS for the trial.** Symphony uses Dex + Caddy + Cloudflare on a
  real domain; HALOS uses Authelia + Traefik + a self-signed device CA. Pick
  the trial approach that keeps `signalk.<boat-domain>` reachable and the LAN
  easy, with the least rework. State what survives to a permanent choice.
- **Plugin container approach.** HALOS wraps apps as Docker/APT packages;
  some newer SignalK plugins (Dirk Wahrheit's, others) use dependent
  containers. Note where the two models clash and what that costs.

## Deliverables

1. **One reference doc that tells the whole story**, concise and organized so
   a contributor or the owner can read it once and understand the system.
   It must clearly separate **what actually works now (golden)** from **what
   is aspirational**, give the **purpose of each container**, and give the
   **purpose of each SSH connection string** (which host, which account,
   what for). Writing bar, measured hard: **ninth-grade reading level, simple
   sentences, highest useful-info-to-words ratio.** No exposition, no hedging,
   no "this may have changed" asides. Tables over prose. Obscure terms and
   artificially-shortened ambiguous sentences count against you as much as
   padding does. Site it per repo conventions (reference/ for explanation,
   RUNBOOK for actions-only; keep point-in-time status out).
2. **A symphony-vs-HALOS diff table** — what differs and whether it matters.
3. **An ordered build plan** to get the HALOS card ready before the swap,
   written so sub-agents/sessions can execute unblocked or find workarounds.
4. **A parallel work breakdown** — discrete items copy-pasteable to other
   sessions, with dependencies marked, so work can be divided.
5. **An at-the-boat swap checklist** the owner runs by hand: physical swap,
   the DNS/Tailscale cutover step, and a verification step per item (the
   command whose output proves it worked, not "it should work").

## Constraints

- No secrets in any output. Reference sensitive items abstractly: WiFi PSK
  lives in sops; the halos password is sops key `symphony_halos_pi_password`;
  write the boat domain as `<boat-domain>`. This repo is private, so Tailscale
  node names and hostnames are fine in tracked files; PSKs, passwords, and
  tokens are not.
- Follow the repo's git hygiene. This work spans several files and touches
  infra, so it very likely warrants a branch + draft PR, not direct-to-main
  commits — open the PR yourself as part of finishing, per the rules.
- The sensitive lane (handled separately, do not duplicate): halos SSH key
  install, WiFi creds → sops, and the **InfluxDB offline backup that must
  happen before any InfluxDB data is dropped** — flag it as a hard
  precondition in your plan but don't execute it here.

Ask any scope questions up front, then work unblocked.
