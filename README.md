# S/V Symphony
A 1985 Hans Christian 38T; heavy displacement, cutter rigged, blue-water cruiser.
Seattle, WA is her home.

<img src="images/symphony.jpg" alt="Symphony at anchor" width="640">

## SV Symphony IoT setup
For setting up SV Symphony's devices and computer systems.

Inspired by [meri-imperiumi/curiosity](https://github.com/meri-imperiumi/curiosity)

## Setup

Two paths. Which one you want depends on whether you need the boat's secrets.

**Contributing** — no secrets, no key, nothing to provision.

```bash
git clone https://github.com/mark-brannan/symphony.git && cd symphony
bash scripts/check_clone_setup.sh   # what this clone has wired, and what to do about what it doesn't
bash scripts/dev_stack.sh up        # InfluxDB + Grafana locally, throwaway credentials
```

Commits work without `sops`, `age` or a key. The secret-bearing files stay
ciphertext on disk; you don't need to read them. `.github/workflows/validate.yml`
is the enforcement boundary — it needs no secrets and runs on every push and
pull request, so local hooks are fast feedback rather than the gate.

**Maintaining** — the boat's hosts, or anything that touches a secret.

```bash
bash scripts/setup-git-filters.sh   # git filters, pre-commit hooks, decrypt in place
```

Wants `sops`, `age`, `python3` and an age key. RUNBOOK.md § *Bringing up a host*
covers installing them and provisioning the key. Safe to re-run at any time.

Either way, if a hook blocks a commit: `bash scripts/check_clone_setup.sh` first,
then RUNBOOK.md § *A hook blocks your commit*.

## Symphony — Maintenance & Improvement Tracking
Working log of deferred maintenance, in-progress
work, and planned improvements.

### Structure
- `priorities.md` — current triage: In Progress / Blocked / Backlog / Someday-Maybe. Physical boat work is tracked in Evernote instead; this file is authoritative only for the SignalK / IoT section.
- `log.md` — chronological ship's-log record, oldest entry first, real append (tail-friendly)
- `systems/` — one file per system, empty for now; populate as it makes sense
- `reference/specs.md` — vessel identity, registration, and physical particulars
- `reference/vendors-parts.md` — vendor contacts and parts sourcing

## Links
- [Sailboatdata — Hans Christian 38T](https://sailboatdata.com/sailboat/hans-christian-38t/)
- [Good Old Boat — Hans Christian 38T](https://goodoldboat.com/saildata/boat/hans-christian-38t/)
- [AIS — MarineTraffic](https://www.marinetraffic.com/en/ais/details/ships/shipid:9545721/mmsi:368391180/vessel:SYMPHONY)
- [AIS — VesselFinder](https://www.vesselfinder.com/vessels/details/368391180)
- [Facebook - Hans Christian Sailboats](https://www.facebook.com/hanschristiansailboats/)
