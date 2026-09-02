# Host files for a HALOS card

HALOS owns its unit and compose files under `/var/lib/container-apps/` and
overwrites them on `apt upgrade`, so Symphony's changes live in override files
that HALOS never touches. `host/install.sh` does not install these yet; place
them by hand (paths below), then `systemctl daemon-reload` and restart the
SignalK unit.

| File | Installs to | Why |
|---|---|---|
| `signalk-healthcheck-override.yml` | `/etc/container-apps/marine-signalk-server-container/symphony.override.yml` | Stock HALOS healthcheck: 60 s start period, then 3 probes 30 s apart (150 s in all). This plugin set cold-starts in 3–4 min on a Pi 4, so autoheal restarted it every ~3 min. 15 min start window, 30 s probe timeout, probe by 127.0.0.1. |
| `signalk-unit-override.conf` | `/etc/systemd/system/marine-signalk-server-container.service.d/symphony.conf` | Adds the override file to HALOS's `docker compose` command line. |
| `traefik-symphony-signalk-host.yml` | `/etc/halos/traefik-dynamic.d/` | Serves SignalK at the root of `signalk.<boat-domain>` instead of Homarr; `/sso` and `/ca` stay with Authelia and the CA download. Traefik reloads it on write. |
