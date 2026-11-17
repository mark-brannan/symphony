# Signal K plugin test rig

A design for a full Signal K install that a pull request of any plugin can
be run against. Design, not procedure: nothing here is built yet. Open
questions at the end are the owner's to answer and stay open until a line
in a decisions file closes them.

## What the rig gives a plugin PR

A plugin is never alone on Symphony. It loads next to roughly a hundred
others, reads paths they publish, writes paths they consume, and shares
one event loop, one data model and one set of notifications. A scratch
server with one plugin and an empty config proves the plugin starts. It
cannot show that the PR breaks another plugin, or works only because
nothing else is loaded. The rig has to give a PR:

- **The real neighbourhood.** Every plugin and webapp Symphony installs, at
  the versions Symphony installs, with Symphony's own configuration for
  each, and Symphony's server settings.
- **The PR in place of the released plugin.** The branch's build replaces
  the published package of the same name. Nothing else changes, so any
  difference is the PR's.
- **Data moving through it.** A stream of realistic NMEA 2000 traffic
  entering the way it does aboard, so plugins that only act on data act.
- **A verdict a person can read.** For every plugin, whether it started,
  whether it is publishing, and whether either changed compared with the
  same rig running the released version.
- **Nothing leaking out.** No page to a phone, no post to a cloud service
  under the boat's name, no secret read, no write to the dev box's state
  or the boat's.
- **No harm to the box it runs on.** It leaves the long-lived dev stack,
  its container names, its ports and its files alone, and leaves nothing
  behind when torn down.
- **Any plugin, any PR.** Naming a repo and a PR number is enough. Nothing
  in the rig is written for one plugin.

## Why not the earlier shape

A first attempt gave each PR a worktree of the plugin, a throwaway config
directory holding only that plugin, and its own port. It was reverted as
the wrong shape: it is the scratch single-plugin server above, made
repeatable. Its useful half, a plugin's own webapp dev loop, lives in that
plugin's repo. `plugins/signalk-plugin-watchdog/test/run-test.sh` is the
same shape on purpose, and stays right for what it does: a unit-level
check of one plugin against fixtures. The rig complements it.

## Design

```
 symphony @ ref                     plugin repo @ PR head
 signalk/ (config of record)        (npm pack in a builder)
        |                                   |
        v                                   v
 +-------------------- rig image --------------------+
 | signal k server, same image line as the dev stack |
 | layer 1: node_modules from signalk/package.json   |  cached by package.json hash
 | layer 2: PR tarball installed over its entry      |  rebuilt per PR head
 | layer 3: seed tree = signalk/ minus secrets,      |
 |          plus the rig overlay                     |
 +---------------------------------------------------+
        |  first start copies seed tree into
        v
 named volume  (the rig's ~/.signalk; disposable)
        |
 compose project signalk-rig-<plugin>-<pr>
   rig-vcan   own network namespace, own can0, replay feeds it
   rig-signalk   joins rig-vcan's namespace
   port published on 127.0.0.1 only, from a band clear of the dev stack
```

### Configuration comes from git, not from a running server

The baseline is the `signalk/` tree at a symphony ref, `main` by default:
`settings.json`, `package.json`, `plugin-config-data/`, `applicationData/`
and the rest. That tree is what the repo says Symphony runs. The dev box's
live `./signalk` is not the baseline: Signal K rewrites it while running,
and the dev stack owns it.

The tree is read from git objects, so every field `.sops.yaml` names is
ciphertext there. The seed step blanks those fields, using the same
`scripts/sops_paths.py` the guards use, rather than decrypting them. The
rig never holds a secret, and needs no age key.

### Everything is baked into the image; state lives in a volume

Following the pattern `compose-grafana.yml` adopted after the root-owned
stub incident (CLAUDE.md, worktree section), the rig has no host bind
mounts. The plugin set, the PR's build and the seed tree are layers of an
image. On first start the seed tree is copied into a named volume that is
the rig's state directory, so Signal K can write to it freely, the admin UI
can save config, and nothing written there flows back to git. Because no
path is relative to a checkout, the rig runs the same from a worktree as
from the main checkout, and the compose-up guard has no reason to stop it.

The plugin set is the slow, heavy layer (native modules, the
`allowScripts` list). It is keyed by the hash of `signalk/package.json`,
so it rebuilds when Symphony's plugin set changes and not when a PR does.
Only the PR layer rebuilds per PR head.

Signal K keys plugin config by plugin id, not package name
(`@signalk/charts-plugin` reads `charts.json`). The PR layer reads the id
from the built package, so the PR inherits Symphony's existing config for
that plugin, and starts enabled with an empty config when Symphony has
none.

### The rig overlay

`dev/plugin-config-overrides/` already holds dev-only values for plugins
that cannot run the same in two places. The rig needs the same idea, wider:
every plugin whose product is an outward effect (a push, an upload, a
report to a cloud service) is either disabled or pointed at a sink inside
the rig. The overlay is a directory of replacement config files, structured
like the originals so a diff shows only the rig delta, applied by copy into
the seed tree at build time. Copying rather than mounting keeps the admin
UI's save path working, unlike the dev overrides' single-file mounts.

The overlay is one list, shared with the dev overrides where a plugin is in
both, so the two cannot drift on which plugins are dangerous to run off the
boat.

### Isolation from the dev stack

- Its own compose project name per rig, so `docker compose down` on one rig
  touches only that rig.
- Its own container names. `compose-signalk.yml` pins `signalk-server` and
  `signalk-vcan`, and `compose-ntfy.yml` pins `ntfy`; the rig sets its own
  instead of inheriting them, or it collides with the dev stack.
- Its own network namespace and `can0`, built the way the `vcan` sidecar in
  `compose-signalk.yml` builds them, so `settings.json`'s `n2k-can0`
  provider works unchanged.
- No other symphony services by default. Plugins that need InfluxDB,
  QuestDB or ntfy see them absent, and the verdict says so, rather than the
  rig reaching the dev stack's instances.
- No Docker socket by default (open question 2). Plugins that run their
  containers through `signalk-container` then fail to start their
  container, and the verdict shows them as such.
- Port published on loopback only.

### Data

A replay container writes a recorded `candump` log onto the rig's `can0`
in a loop, so data enters through the same canboatjs provider it does
aboard. Which recording is open question 3.

### The verdict

The rig runs twice on the same seed: once with the released package, once
with the PR. After a settle period each run takes a census of every plugin:
started or not, its last status or error line, and whether it publishes,
read from the server's plugin API and by `scripts/signalk_plugin_census.py`
(which already knows that a webapp or an exporter publishing nothing is
correct). The report is the diff; an illustrative run, numbers invented:

```
signalk-rig  signalk-noaa-space-weather PR #318 (a1b2c3d) vs 0.30.7
symphony main @ 9f8e7d6   plugins 104   replay boat-sample   settle 120s

plugin                        released        PR              change
signalk-noaa-space-weather    started  pub    started  pub    -
signalk-derived-data          started  pub    started  pub    -
signalk-rules                 started  pub    error           NEW ERROR
  "Cannot read properties of undefined (reading 'kp')"
signalk-questdb               no docker       no docker       -
... 100 unchanged

1 plugin changed. Admin UI (PR run, kept until teardown): http://127.0.0.1:3410/
```

The PR run stays up after the report so a person can open the admin UI and
the webapps against it; teardown removes the project, its containers and
its volume.

### Entry point

One command, given a plugin repo and a PR number (or a local path), that
builds, runs both passes, prints the report and leaves the PR run up; and
a teardown. It lives in symphony beside the compose files it reads.

## Builds on

- `docker-compose.yml`, `compose-signalk.yml`: the service shape the rig
  copies, including the `vcan` namespace owner.
- `compose-grafana.yml`, `grafana/Dockerfile`: the bake-into-image pattern.
- `compose-dev.yml`, `dev/plugin-config-overrides/README.md`: the override
  idea the overlay generalizes.
- `signalk/`: the config of record; `.gitignore` for what in it is runtime
  data rather than config.
- `.sops.yaml`, `scripts/sops_paths.py`: which fields are secret.
- `scripts/signalk_plugin_census.py`: per-plugin evidence of activity.
- `plugins/signalk-plugin-watchdog/test/run-test.sh`: the single-plugin
  check the rig complements.
- [software_stack.md](software_stack.md), "The Docker socket": what the
  socket grants.

## Open questions

1. **Where does it run?** The dev box only, a spare HaLOS-class box, or a
   plugin repo's CI. CI changes the cost question: the plugin-set layer is
   a large build, and the run draws on the account's concurrent-job cap.
2. **Docker socket in the rig.** Off, the plugins that launch containers
   through `signalk-container` cannot be tested. On, the code under review
   has root on the host that runs the rig.
3. **Which recording feeds the replay.** A capture from the boat is the
   most realistic and carries her positions and track; a synthetic or
   public sample carries neither and exercises less.
4. **The overlay's list.** Which outward plugins are disabled, and which
   point at a sink inside the rig (a rig-local ntfy, for one).
5. **The baseline.** The repo's `signalk/` at `main`, or a snapshot of what
   the boat actually runs. They drift; the census script exists because
   they do.
6. **Server version.** The dev stack's `latest`, or pinned to the boat's
   version so a pass means the same thing aboard.
7. **What a verdict is for.** Advisory to the PR's author and reviewer, or
   a required check in plugin repos.
