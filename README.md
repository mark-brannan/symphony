# S/V Symphony
A 1985 Hans Christian 38T; heavy displacement, cutter rigged, blue-water cruiser.
Seattle, WA is her home.

<img src="images/symphony.jpg" alt="Symphony at anchor" width="640">

This repo holds two things: her maintenance records, and the source for the
SignalK/IoT stack that runs aboard — Ansible, compose files, host config, and
the reference docs for both.

## Setup

Two paths. Which one you want depends on whether you need the boat's secrets.

**Contributing** — no secrets, no key, nothing to provision.

```bash
git clone https://github.com/mark-brannan/symphony.git && cd symphony
bash scripts/check_clone_setup.sh   # what this clone has wired, and what to do about what it doesn't
bash scripts/dev_stack.sh up        # QuestDB + InfluxDB + Grafana locally, throwaway credentials
```

Commits work without `sops`, `age` or a key. The secret-bearing files stay
ciphertext on disk; you don't need to read them. `.github/workflows/validate.yml`
and `secret-scan.yml` need no secrets and run on every push and pull request, so
local hooks are fast feedback rather than the gate. Their eight jobs are
required checks on `main`, which also takes changes only through a squashed
pull request, so a red run blocks the merge.

**Maintaining** — the boat's hosts, or anything that touches a secret.

```bash
bash scripts/setup-git-filters.sh   # git filters, pre-commit hooks, decrypt in place
```

Wants `sops`, `age`, `python3` and an age key. RUNBOOK.md § *Bringing up a host*
covers installing them and provisioning the key. Safe to re-run at any time.

Either way, if a hook blocks a commit: `bash scripts/check_clone_setup.sh` first,
then RUNBOOK.md § *A hook blocks your commit*.

## Where to look

**The stack aboard**
- [reference/system_map.md](reference/system_map.md) — what runs where: machines, host configurations, services, one row each. Start here.
- [reference/software_stack.md](reference/software_stack.md) — how it is put together, and why.
- [RUNBOOK.md](RUNBOOK.md) — what to do when something breaks or needs deploying. Procedures only.
- [reference/](reference/) — the rest of the design record: compute hardware, monitoring posture, security posture, SignalK paths, plugin behavior.

**The source it is built from**
- `ansible/`, `host/` — how a host gets provisioned, and which files land on it.
- `docker-compose.yml` and the `compose-*.yml` files it includes — the compose services, mapped in `reference/software_stack.md`.
- `scripts/` — clone setup, the local dev stack, secret handling, repo guards.
- [CLAUDE.md](CLAUDE.md) — the conventions this repo is maintained under.

**The boat herself**
- [maintenance/log.md](maintenance/log.md) — ship's log of work done, oldest entry first.
- [maintenance/priorities.md](maintenance/priorities.md) — what is still open: In Progress / Backlog / Someday-Maybe. Physical jobs live in Evernote; this file is authoritative only for its SignalK / IoT section.
- [systems/](systems/) — one file per boat system, added as each gets written up.
- [reference/specs.md](reference/specs.md) — vessel identity, registration, and physical particulars.
- [reference/vendors-parts.md](reference/vendors-parts.md) — vendor contacts and parts sourcing.

## Links
- [Sailboatdata — Hans Christian 38T](https://sailboatdata.com/sailboat/hans-christian-38t/)
- [Good Old Boat — Hans Christian 38T](https://goodoldboat.com/saildata/boat/hans-christian-38t/)
- [AIS — MarineTraffic](https://www.marinetraffic.com/en/ais/details/ships/shipid:9545721/mmsi:368391180/vessel:SYMPHONY)
- [AIS — VesselFinder](https://www.vesselfinder.com/vessels/details/368391180)
- [Facebook - Hans Christian Sailboats](https://www.facebook.com/hanschristiansailboats/)
- Inspired by [meri-imperiumi/curiosity](https://github.com/meri-imperiumi/curiosity)
