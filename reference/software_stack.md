# Software stack

How Symphony's onboard software is put together and why. Reference, not
procedure — for what to *do*, see [RUNBOOK.md](../RUNBOOK.md).

## Containers

Containers come from two places.

**Compose services**, in `docker-compose.yml` and the `compose-*.yml` files
it includes:

| Service | Image | Port | Persistent state |
|---|---|---|---|
| `signalk-server` | `signalk/signalk-server:latest` | 3001→3000, 80 | `./signalk` (bind mount, **in git**) |
| `influxdb` | `influxdb:2.7` | 8086 | `influxdb-data`, `influxdb-config` volumes |
| `grafana` | `grafana/grafana:latest` | 3000 | `grafana-data` volume, `./grafana/provisioning` |

**Plugin-managed containers**, launched by SignalK plugins through the
`signalk-container` plugin and named `sk-*`. These are in no compose file —
SignalK starts them itself:

| Container | Launched by | Notes |
|---|---|---|
| `sk-signalk-questdb` | `signalk-questdb` | time-series store |
| `sk-signalk-grafana` | `signalk-grafana` | its own Grafana, auto-provisioned against QuestDB |

`docker compose ps` shows only the first group. `docker ps -a` shows both.

Node-RED runs inside SignalK (the `@signalk/signalk-node-red` plugin), with
its flows under `signalk/red/`.

SignalK's whole state directory is a bind mount that's tracked in git. That
is why the in-place encryption scheme exists: SignalK reads and rewrites
these files while running, so they have to be plaintext on disk and
ciphertext in git.

Outbound integrations that need credentials: PostgSail
(`api.openplotter.cloud`), OpenWeather, Windy, and InfluxDB. Each token is
encrypted in the relevant `signalk/plugin-config-data/*.json`.

## Two paths to the same job

There are two parallel data paths, and which one is live has changed over
time. Check before assuming:

- SignalK → InfluxDB (`signalk-to-influxdb2`) → compose `grafana`
- SignalK → QuestDB (`signalk-questdb`) → `sk-signalk-grafana`

Credentials for both are tracked and encrypted, so the secrets tooling
doesn't decide between them. Three traps on the QuestDB path, all of which
fail quietly:

**Network names get a project prefix.** Both plugins default to
`networkName: symphony-net`, but compose actually creates
`symphony_symphony-net`. Finding no bare `symphony-net`, `signalk-container`
creates one, and the plugin containers end up on a bridge SignalK isn't on —
`getent hosts sk-signalk-questdb` from inside `signalk-server` won't resolve.
Point the plugins at `symphony_symphony-net`, or declare `symphony-net`
external and have compose join it.

**`questdbHost` defaults to `127.0.0.1`,** which inside the `signalk-server`
container means that container, not the host. It's ignored while
`managedContainer` is true, and starts mattering the moment you set it false.

**Both Grafanas want host port 3001.** SignalK publishes on 3001 and
`signalk-grafana` defaults to `grafanaPort: 3001`, so the plugin-managed one
dies with `Bind for 0.0.0.0:3001 failed: port is already allocated` and sits
in `Created`.

To run QuestDB from your own compose file instead, set
`managedContainer: false` and point `questdbHost` at the service name. The
plugin then behaves as a client and `signalk-container` isn't involved.
`signalk-grafana` has no equivalent switch — it always runs its own.

## The Docker socket

`compose-signalk.yml` mounts `/var/run/docker.sock` into `signalk-server`
and adds the host's `docker` group. This is what lets `signalk-container`
start containers on behalf of other plugins — `signalk-questdb`,
`signalk-grafana`, `signalk-chart-locker` and `signalk-doctor` all delegate
their container lifecycle to it.

This has nothing to do with SignalK reaching InfluxDB or Grafana. Those are
ordinary HTTP calls over the container network. The socket is only about
*launching and managing* containers.

Docker API access is equivalent to root on the host: anything that can reach
the socket can start a container that mounts the host filesystem. That socket
is reachable from inside `signalk-server` — confirmed by querying `/version`
through it from within the container. So any SignalK plugin, or anything that
compromises one, can take the host.

While those plugins are enabled, plugin installation is the security boundary.
Know what you're installing, and consider turning off `backgroundUpdateChecks`
in the `signalk-container` config so new plugin code doesn't arrive
unattended.

The mount can go entirely if nothing needs managed containers: run QuestDB
from compose (`managedContainer: false`), drop `signalk-grafana`, and remove
the `docker.sock` volume and `group_add` from `compose-signalk.yml`.

A socket proxy is the usual middle path, but it buys little here —
`signalk-container` has to create containers to do its job, and container
creation is itself the escalation.

## How secrets are stored

Two encryption mechanisms, one age key, one store of truth
(`secrets/symphony.sops.yaml`):

- **Layer 1** — `docker-compose` `env_file: .env`. `.env` is gitignored,
  rendered by `scripts/render.py` from `secrets/symphony.sops.yaml`.
  `.env.example` documents every key.
- **In-place** — plugin config files that SignalK/Grafana read directly off
  disk (and rewrite at runtime) are tracked in git *as themselves*. A git
  clean/smudge filter (`scripts/sops_filter.py`, wired by `.gitattributes` +
  `scripts/setup-git-filters.sh`) encrypts just the secret leaf fields on
  commit and decrypts them back on checkout. The working copy on disk is
  always plaintext — SignalK reads and rewrites it exactly as it would
  otherwise. Only what git stores is encrypted.
- **API-provisioned** — Grafana users and all of InfluxDB. These have no file
  to encrypt; their state lives inside the containers and is created over
  HTTP by `scripts/provision_grafana_users.sh` and
  `scripts/provision_influxdb.sh`.

`.sops.yaml` is the single source of truth for which files carry secrets. The
pre-commit guard and the CI verifier read it at runtime via
`scripts/sops_paths.py`. Don't hardcode that list anywhere else; duplicate
copies drift, and the copy that drifts is usually the one doing the checking.

## How the safety net is layered

The layers are not equally trustworthy:

| Layer | What it catches | Can it be bypassed? |
|---|---|---|
| sops clean filter | encrypts configured fields automatically on commit | only if the clone never ran `setup-git-filters.sh` |
| pre-commit hooks | unencrypted secrets, cleartext credentials, forbidden files | **yes** — `--no-verify`, or never installing them |
| GitHub Actions | all of the above, plus full-history and live-credential scans | **no** — runs on every push |

CI is the enforcement boundary; the hooks are fast feedback, not a guarantee.
That is why `.github/workflows/validate.yml` re-runs the same checks rather
than trusting that a hook already ran.
