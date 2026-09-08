# Dev-only plugin config overrides

`signalk/plugin-config-data/` is what we intend to push to the boat. A few
plugins can't hold the same values in both places — the relay that pages a
real phone is the one left. Rather
than let dev values creep into the repo, each of those gets a replacement
file here, bind-mounted read-only over the repo's copy in
`docker-compose.override.yml`.

Compose loads that override file automatically, no `-f` flag. The boat runs
SignalK natively rather than in Docker, so nothing here reaches it.

## What's pinned, and why

| File | Dev value | Reason |
|---|---|---|
| `signalk-pushover-notification-relay.json` | `api_user`/`api_key` blank, `enabled: true` | The relay's dedupe state is in memory, so every container restart re-sends every non-normal notification, and the dev container restarts constantly. With blank credentials the plugin still runs, but Pushover rejects each request with 400 and nothing reaches the phone (`index.js` builds the request from `config.api_key` with no guard; the response is logged at debug level only). Only the secret differs from the boat's file. |

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
block the commit if you do.
