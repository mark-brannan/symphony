# Swapping the HALOS card onto the boat

Puts the HALOS card into the boat Pi; the boat card comes home as the
rollback. The Pi is powered from the NMEA 2000 bus: "power off" means
unplugging its Micro-C.

Both check scripts print one `ok`/`FAIL` line per function. A line that
FAILs on the boat card before the swap and on the HALOS card after it is a
boat problem, not a card problem; the baseline exists to tell them apart.

## Before leaving home

```bash
scripts/halos_preflight.sh
```

Every line must be `ok`. The `services` line needs QuestDB and Grafana up on
the bench Pi; on the 2 GB bench, stop them again afterward
(`sudo systemctl stop marine-questdb-container marine-grafana-container`).

## Sync the SignalK config

A `state` FAIL in the preflight means the boat's SignalK config has moved
since the card was loaded. Sync, then re-run the preflight. **Keep every
exclude**; the last five are the card's own settings, and SignalK re-enables
plugins live when they are overwritten, with no error.

```bash
ssh pi@symphony-halos 'D=/var/lib/container-apps/marine-signalk-server-container/data/data
rsync -av --exclude node_modules --exclude package.json --exclude appstore-cache \
  --exclude "skserver-raw_*" --exclude "*.bak*" --exclude "*.deb" --exclude signalk-server \
  --exclude "ssl-*.pem" --exclude "*.sqlite*" \
  --exclude "plugin-config-data/signalk-container.json" \
  --exclude "plugin-config-data/signalk-to-influxdb2.json" \
  --exclude "plugin-config-data/signalk-to-influxdb-v2-buffer.json" \
  --exclude "plugin-config-data/signalk-notification-player.json" \
  --exclude "plugin-config-data/venus.json" \
  pi@symphony-pi:.signalk/ "$D"/'
ssh pi@symphony-halos 'sudo systemctl restart marine-signalk-server-container'
```

If `state` names a plugin version or `package.json`, the boat installed a
plugin since the copy: copy the boat's `package.json` across, re-pin the two
`file:local-plugins/` entries, and rebuild (about 19 minutes; restarts
SignalK itself):

```bash
ssh pi@symphony-halos 'cd /home/pi/symphony && sudo scripts/halos_signalk_npm.sh'
ssh pi@symphony-halos 'journalctl -u halos-npm -f'      # follow or re-follow the build
```

Abort with `sudo systemctl stop halos-npm`, never `systemctl kill` (that
leaves SignalK down).

## Exercise the DNS cutover from home

So a dead token is found at home, not at the boat:

```bash
scripts/dns_cutover.sh set symphony-halos -y
dig +short symphony.dark-star-llc.com @1.1.1.1    # the halos tailnet IP
scripts/dns_cutover.sh set symphony-pi -y
dig +short symphony.dark-star-llc.com @1.1.1.1    # back to the boat card
```

## At the boat

1. Baseline the boat card and keep the output:

   ```bash
   scripts/halos_swap_check.sh symphony-pi
   ```

   `victron` and `questdb` FAILs are boat-side (Cerbo not answering on
   8883, QuestDB too loaded to answer in 30 s) and carry over.

2. Shut down; unplug the Micro-C when the green LED stops:

   ```bash
   ssh pi@symphony-pi 'sudo shutdown -h now'
   ```

3. Swap the cards. Pocket the boat card; it is the only copy of the
   QuestDB history and `~/influx-export`.

4. Reconnect the Micro-C. Wait five minutes (SignalK cold-starts in 3–4).

5. Check every function over Tailscale:

   ```bash
   scripts/halos_swap_check.sh
   ```

   Same lines as the baseline, `up=` small, `front` on `:4430`. `ble` and
   `bme680` can take ten minutes; rerun. Don't move DNS until every line
   that was `ok` in the baseline is `ok` here. A `bme680` FAIL that survives:

   ```bash
   # silence is a pass; PermissionError means the group_add override in
   # host/halos/signalk-healthcheck-override.yml is missing: install it per
   # host/halos/README.md and restart the unit
   ssh -t pi@symphony-halos "sudo docker exec signalk-server python3 -c \"open('/dev/i2c-1')\""
   ```

## Cut over and check from a phone

6. Cut public DNS over:

   ```bash
   scripts/dns_cutover.sh set symphony-halos
   ```

   Within about 35 minutes healthchecks.io reports `SignalK Symphony` late;
   that is the boat card no longer pinging. Pause that check or accept the
   one notification. The HALOS card pings `SignalK Symphony (halos card)`.

7. Phone on the boat WiFi: install the certificate from
   `https://signalk.symphony.dark-star-llc.com/ca/`, then open
   `https://signalk.symphony.dark-star-llc.com/`. Admin UI, no certificate
   warning, `SignalK` in the WiFi list.

## Rolling back

Unplug the Micro-C, swap the boat card in, plug in, wait three minutes:

```bash
scripts/halos_swap_check.sh symphony-pi
scripts/dns_cutover.sh set symphony-pi
```

The `(halos card)` check goes late instead. Nothing on the boat card is
changed by the trial.
