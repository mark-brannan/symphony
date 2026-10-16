# Boat Pi, shift 1 as-built, 2026-10-15

## Disk
`df -h /` on symphony-pi: 29G, 21G used, 6.1G free, 78%. Under the 80% threshold, so nothing deleted. (Before = after = 78%.)

## signalk-to-influxdb2 uninstalled
Checked first: influxdb and grafana-server inactive, nothing listening on 8086, no npm running. `~/.signalk/package.json` already pointed watchdog at `file:../symphony/plugins/signalk-plugin-watchdog`, so the npm-tree quirk in kanban-detail.md no longer applies.

Snapshot: `/home/pi/signalk-snap-influx2-20261015/` (package.json, signalk-to-influxdb2.json).

Commands, on the boat:
```
cd ~/.signalk && npm uninstall signalk-to-influxdb2
rm plugin-config-data/signalk-to-influxdb2.json
sudo systemctl restart signalk
```
Result: npm exit clean, package gone from node_modules and package.json, watchdog intact. SignalK active, NRestarts=0, `GET /signalk` 200, zero HistoryAPI/influxdb2 journal lines in the 60 s after restart (24 in the hour before).

Repo: dropped the dependency from `signalk/package.json`. `signalk-to-influxdb-v2-buffering` is a separate plugin and was left alone.

Undo: `cd ~/.signalk && npm install signalk-to-influxdb2@^2.3.0`, copy the config back from the snapshot, restart signalk.

## Humidity-fix Node-RED flow: not deployed
The card says the procedure is in RUNBOOK; it was cut from there in c92e3e3 (flow JSON survives in commit ae7d73e). Node-RED is not active on the boat and `~/.node-red/flows*.json` does not exist, and the detail section says the flow is unverified against the live editor. Deploying needs installing and running Node-RED, which is a larger change than this card describes. Left for a human at the editor.

## pypilot
Container `pypilot` running, started 2026-10-16T01:16Z (up about 5 h at check). `pypilot-web` healthy.

Not done: removing the tracked `signalk/plugin-config-data/signalk-to-influxdb2.json` from the repo. The sops secret guard blocks a deletion in a worktree where the git filters are not set up; remove it from a checkout that has run `scripts/setup-git-filters.sh`.
