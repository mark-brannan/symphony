# Dev-only plugin config overrides

`signalk/plugin-config-data/` is what we intend to push to the boat. A few
plugins can't hold the same values in both places — the relay that pages a
real phone, a provider watch for hardware the dev box doesn't have. Rather
than let dev values creep into the repo, each of those gets a replacement
file here, bind-mounted read-only over the repo's copy in
`docker-compose.override.yml`.

Compose loads that override file automatically, no `-f` flag. The boat runs
SignalK natively rather than in Docker, so nothing here reaches it.

## What's pinned, and why

| File | Dev value | Reason |
|---|---|---|
| `signalk-pushover-notification-relay.json` | `enabled: false` | The relay's dedupe state is in memory. Every container restart re-sent every non-normal notification to the phone, and the dev container restarts constantly. |
| `signalk-healthcheck.json` | `providers.n2k-can0.enabled: false` | Watches a CAN provider the dev box has no hardware for, so its delta rate is permanently 0 and it sits in `alarm` forever. |

## The trap: you can't save these from the dev admin UI

SignalK writes plugin config by writing `<file>.tmp` and renaming it over the
target (`atomicWriteFileSync`, `src/atomicWrite.ts`). A rename onto a
single-file bind mount fails, so saving one of these plugins in the dev
admin UI errors out instead of writing.

That's the intended behavior — these are pinned. To change one, edit the file
here and recreate the container:

```bash
docker compose up -d signalk
```

To change what goes to the *boat*, edit `signalk/plugin-config-data/` directly.

## Adding a plugin to this list

Copy the repo's version of the config here, change only what dev needs, and
add a mount line to `docker-compose.override.yml`. Keep the two files
structurally identical otherwise, so a diff shows just the dev delta — with
one exception: strip credential fields rather than copying them, both because
these files aren't sops-covered and because the pre-commit secret guard will
block the commit if you do. `signalk-healthcheck.json` drops its `mail` block
for that reason; email is disabled in dev either way.

`signalk-ntfy.json` is handled by the `hostvars` filter instead of a pin
(RUNBOOK.md § Per-machine config values): the plugin is live in both
environments and its non-URL settings should stay editable from either, so
a read-only pin is the wrong shape — only the server URL differs per
machine.
