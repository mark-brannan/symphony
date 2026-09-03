# What we changed on HALOS, and who else might want it

Mark's question (2026-09-03): of the things we build, change or tweak on the
HALOS card, which belong in HALOS core, which are add-ons other casual or
power users would want, and which are only ours? Not to answer now — this is
the running list to answer it from later. One line per change, tagged with a
first guess: **core** / **add-on** / **ours**. Add a line the moment a change
is made; retag when we learn more. Upstream repo: `github.com/halos-org`.

| Change | Where it lives | First guess | Why |
|---|---|---|---|
| SignalK healthcheck: 15 min start window, 30 s probe timeout | `host/halos/signalk-healthcheck-override.yml` | core | Stock 60 s start / 10 s probe loses to any plugin-heavy install on a Pi 4; autoheal then restarts SignalK every ~3 min. Anyone with >20 plugins hits it. |
| `group_add` host `i2c` gid on the SignalK container | same file | core | Without it no i2c sensor plugin can open `/dev/i2c-1`; failure is silent. HALPI2 users with the Qwiic port hit it. |
| Override installed by systemd drop-in, not by editing the package compose | `host/halos/signalk-unit-override.conf` | add-on (pattern) | Survives `apt upgrade`. Worth documenting upstream as *the* way to customise an app. |
| `cgroup_enable=memory cgroup_memory=1` in cmdline | `ansible/roles/boot` | core | Without it every `mem_limit` in HALOS's own compose files is silently unenforced. Upstream may already set it on HALPI2 images; unknown for `-RPI`. |
| Disable `systemd-networkd-wait-online` | `host/halos/README.md`, `ansible/roles/can` | core | networkd manages only `can*`; wait-online times out 2 min every boot and leaves a failed unit. |
| `apt-get purge` (not remove) `marine-influxdb-container` | same | core (bug) | `remove` leaves a unit that starts and fails at boot. Package should clean up its unit on remove. |
| Persistent journal (`Storage=persistent`) | `host/journald-symphony.conf` | add-on | Pi OS ships `40-rpi-volatile-storage.conf`; a headless boat box that hangs is undiagnosable without it. Reasonable default for a marine distro; SD wear is the counter-argument. |
| Hardware watchdog `RuntimeWatchdogSec=30` | `host/systemd-watchdog.conf` | core | A hung box at anchor with nobody aboard needs it. Note it does not catch a swap livelock (bench, 2026-09-03). |
| Serve an app at `/` of a chosen hostname via Traefik dynamic file | `host/halos/traefik-symphony-signalk-host.yml` | add-on | Homarr at `/` is fine for a dashboard user; a SignalK-first user wants SignalK there. A `halos-app set-root signalk` would cover both. |
| Hotspot renamed to the boat's existing SSID/PSK via keyfile | `ansible/roles/network` | ours | Only relevant to a migration. |
| Boat heartbeat to healthchecks.io | `host/boat-heartbeat*` | add-on | Off-boat "is the boat alive" ping; generic enough to package. |
| Telegraf → QuestDB host metrics | `telegraf/`, `ansible/roles/monitoring` | add-on | HALOS has Grafana+QuestDB but nothing feeds host metrics into them. |
| pypilot as a container (IMU + web, no servo) | `pypilot/`, `compose-pypilot.yml` | add-on | Nothing for pypilot in HALOS today; the SWIG/RTIMULib build is the hard part others would rather not repeat. |
| BLE sensor plugin fork with D-Bus reconnect | `local-plugins/bt-sensors-plugin-sk` | neither | Belongs upstream in the plugin, not HALOS. |
| Local-plugin `file:` pins surviving app-store installs | RUNBOOK § plugin fork keeps reverting | core (docs) | Any user with a patched plugin hits the same silent revert. |
| npm native rebuild for Node 24 in a throwaway container | `halos-b3-findings-2026-09-02.md` | core (docs) | The image has no compiler; plugins with native deps fail silently. Either ship build tools or document the recipe. |
| zram swap on a 2 GB card | `ansible/roles/base` | add-on | Only matters for 2 GB boards. |
| Cerbo MQTT by IP because the container's `nsswitch` is `files dns` | `venus.json` | core (bug) | `.local` names never resolve inside HALOS app containers; anything mDNS-addressed breaks. |
