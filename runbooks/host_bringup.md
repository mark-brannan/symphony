# Bringing up a host

A new or rebuilt host, in order; run each check before the next phase.

## 1. Tooling

Docker with compose v2, your user in `docker`, and:

```bash
sudo apt install pre-commit     # or: brew install pre-commit
```

`sops` and `age`: release binaries, onto `PATH`.

*Verify:* `docker compose version && sops --version && age --version && pre-commit --version`

## 2. Key material

Get the age private key onto the host out of band, never through the repo.

```bash
mkdir -p ~/.config/sops/age
cp <key file> ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

*Verify:* `sops --decrypt secrets/symphony.sops.yaml | head -1` prints readable YAML. If not, stop here.

## 3. Repo

```bash
git clone https://github.com/mark-brannan/symphony.git
cd symphony
bash scripts/setup-git-filters.sh
python3 scripts/render.py
```

*Verify:* `bash scripts/verify_encrypted.sh` passes and `grep -c ENC .env` prints 0.

## 4. Services

```bash
docker compose up -d                              # plain
docker compose --profile tls up -d --build        # fully containerized host with SSO
bash scripts/provision_grafana_users.sh
bash scripts/provision_influxdb.sh
```

On the boat, skip the `--profile tls` line ([sso.md](sso.md)). If
`provision_influxdb.sh` minted `influx_token`, re-render and recreate grafana;
if it minted `influxdb_signalk_token`, put it in
`signalk/plugin-config-data/signalk-to-influxdb2.json` and restart SignalK.

*Verify:* `bash scripts/test_integration.sh`

First-ever boot with no `security.json`: let SignalK's setup wizard create it,
then `git add signalk/security.json` once.

## Onto the tailnet

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=<name>
```

*Verify:* `tailscale status` on another device lists it.

## Provisioning a HALOS card with Ansible

From a laptop on the tailnet, with `sops`, the age key, and ssh to `pi@symphony-halos`:

```bash
sudo apt install ansible
ansible-galaxy collection list community.sops community.general
ssh pi@symphony-halos 'cd /home/pi/symphony && bash scripts/setup-git-filters.sh'   # once per card
(cd ansible && ansible-playbook site.yml)
```

Variants: `--check --diff` (no changes), `--tags verify` (audit only),
`-e symphony_allow_reboot=false` (card carrying live data; reboot it yourself
after), `-e symphony_repo_version=<branch>`.

*Verify:* run it a second time and get `changed=0 failed=0`, then
`scripts/halos_preflight.sh` reads `ok` on every line.

## Host files

```bash
cd ~/symphony && git pull
sudo host/install.sh
```

Idempotent; re-run after any change under `host/`. It refuses on anything that
isn't a boat card; `SYMPHONY_INSTALL_FORCE=1` overrides only for a real card
failing a check. *Verify* the watchdog per
[RUNBOOK.md](../RUNBOOK.md#deploying-a-change-to-the-boat).

It drops chrony's config whether or not chrony is installed. If `chronyc` is
missing:

```bash
sudo apt install chrony
sudo host/install.sh
chronyc tracking && chronyc sources     # a reference named, one `^*` peer
```

`nightly-reboot` installs with its cron line commented out. Re-enabling it
means keeping its guard: a reboot landing on an `npm install` in `~/.signalk`
truncates the plugin tree beyond npm's repair.

## QuestDB

The mmap limit is a kernel setting on the host; the container cannot raise it
itself.

```bash
if [ "$(cat /proc/sys/vm/max_map_count)" -lt 1048576 ]; then
  echo 'vm.max_map_count=1048576' | sudo tee /etc/sysctl.d/99-questdb.conf
  sudo sysctl --system
fi
test "$(cat /proc/sys/vm/max_map_count)" -ge 1048576 && echo ok
docker compose -f docker-compose.yml up -d questdb
curl -fsS --max-time 5 --retry 30 --retry-delay 2 --retry-connrefused \
  -G --data-urlencode 'query=SELECT 1;' http://127.0.0.1:9000/exec      # answers = ready
docker inspect questdb --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^QDB_CAIRO_' | sort
```

All five must be present with these values, or the container preallocates
16 MB per column file and fills the SD card:

```
QDB_CAIRO_COMMIT_MODE=sync
QDB_CAIRO_O3_COLUMN_MEMORY_SIZE=256k
QDB_CAIRO_WAL_WRITER_DATA_APPEND_PAGE_SIZE=128k
QDB_CAIRO_WRITER_DATA_APPEND_PAGE_SIZE=256k
QDB_CAIRO_WRITER_DATA_INDEX_VALUE_APPEND_PAGE_SIZE=256k
```

Missing or different: `docker compose -f docker-compose.yml up -d --force-recreate questdb` and re-check. Then the writers:

```bash
sudo systemctl restart telegraf
until curl -sf -G --data-urlencode 'query=SELECT 1 FROM cpu LIMIT 1' http://127.0.0.1:9000/exec | grep -q '"count":1'; do sleep 5; done
scripts/questdb_table_hygiene.sh              # TTL + dedup; read its output for unrecognised tables
sudo du -sm "$(docker inspect questdb --format '{{range .Mounts}}{{if eq .Destination "/var/lib/questdb"}}{{.Source}}{{end}}{{end}}')"
```

*Verify:* the `du` reads tens of MB, not GB. Re-run the hygiene script after
adding a Telegraf input or recreating a table.

## The off-boat heartbeat

`boat-heartbeat.timer` pings a healthchecks.io check every five minutes, using
the sops-encrypted URL in `host/boat-heartbeat.json` that `host/install.sh`
places at `/etc/boat-heartbeat.json`. To set it up or change it: create a check
(period 5 min, grace 20 min or more), edit the `url` field, then:

```bash
git diff --cached host/boat-heartbeat.json   # must show ENC[...], not the URL
sudo host/install.sh
sudo systemctl start boat-heartbeat.service
journalctl -t boat-heartbeat -n 5            # expect: ping ok
systemctl list-timers boat-heartbeat.timer   # NEXT about five minutes out
```

If the diff shows the URL in clear, stop: run `bash scripts/setup-git-filters.sh`
and re-stage. To turn pings off, delete `/etc/boat-heartbeat.json`; leave the
timer alone.
