# Swapping the HALOS card onto the boat

Puts the HALOS card into the boat Pi; the boat card comes home as the
rollback. The Pi is powered from the NMEA 2000 bus: "power off" means
unplugging its Micro-C.

`scripts/halos_preflight.sh` and `scripts/halos_swap_check.sh` each print
one `ok`/`FAIL` line per check. A line that FAILs on the boat card before
the swap and on the HALOS card after it is a boat problem, not a card
problem; the baseline exists to tell them apart.

## Before leaving home

```bash
scripts/halos_card_prepare.sh          # card already on the tailnet
scripts/halos_card_prepare.sh <lan-ip> # virgin card, wired Ethernet on the bench Pi
```

Runs every layer and ends with the preflight. Every preflight line must read
`ok`; the script is safe to re-run after fixing anything.

## Sync the SignalK config

`halos_card_prepare.sh` already relays the boat's SignalK config onto the
card, so this section is only for a `state` FAIL found later, after the boat's
config has moved on from what the card has. Sync, then re-run the preflight.
The card's own settings (which plugins stay disabled, `venus.json`) are
excluded by `scripts/halos_disabled_plugins.sh`, the same list the preflight
checks against, so the two can't drift apart; SignalK re-enables plugins live
when their config is overwritten, with no error.

```bash
scripts/halos_config_sync.sh
```

If `state` names a plugin version or `package.json`, the boat installed a
plugin since the copy: copy the boat's `package.json` across, re-pin the two
`file:local-plugins/` entries, and rebuild (about 19 minutes; restarts
SignalK itself):

```bash
ssh pi@symphony-halos 'cd /home/pi/symphony && sudo scripts/halos_signalk_npm.sh'
```

It follows the build's journal itself. If the ssh drops, the build carries
on; reconnect with `ssh pi@symphony-halos 'journalctl -u halos-npm -f'`.

Abort with `sudo systemctl stop halos-npm`, never `systemctl kill` (that
leaves SignalK down).

## Exercise the DNS cutover from home

So a dead token is found at home, not at the boat:

```bash
scripts/dns_cutover.sh set symphony-halos -y
dig +short symphony.dark-star-llc.com @1.1.1.1    # the halos tailnet IP, within the 300 s TTL
scripts/dns_cutover.sh set symphony-pi -y
dig +short symphony.dark-star-llc.com @1.1.1.1    # back to the boat card
```

A `dig` that still shows the old address is the resolver's cache; wait out
the TTL and run it again.

## At the boat

1. Baseline the boat card; keep the output:

   ```bash
   scripts/halos_swap_check.sh symphony-pi
   ```

   `victron` and `questdb` FAILs are boat-side and carry over.

2. Silence the boat card's alarm, shut down, and unplug the Micro-C when
   the green LED stops:

   ```bash
   scripts/monitoring_snooze.sh pause pi
   ssh pi@symphony-pi 'sudo shutdown -h now'
   ```

3. Swap the cards; pocket the boat card, the only copy of the QuestDB
   history and `~/influx-export`.

4. Reconnect; wait five minutes for SignalK's cold start.

5. Check over Tailscale:

   ```bash
   scripts/halos_swap_check.sh
   ```

   Same lines as the baseline, `up=` small, `front` on `:4430`. `ble` and
   `bme680` can take ten minutes; rerun. Move DNS only when every baseline
   `ok` is `ok` here. A `bme680` FAIL that survives:

   ```bash
   ssh -t pi@symphony-halos "sudo docker exec signalk-server python3 -c \"open('/dev/i2c-1')\""
   ```

   Silence passes. `PermissionError`: install the override per
   `host/halos/README.md`, restart the unit.

6. Cut public DNS over:

   ```bash
   scripts/dns_cutover.sh set symphony-halos
   ```

   The boat card's check stays paused; the HALOS card pings its own.

7. Phone on the boat WiFi: install the certificate from
   `https://signalk.symphony.dark-star-llc.com/ca/`, open the site: admin
   UI, no certificate warning, and the `SignalK` hotspot in the phone's
   WiFi list.

## Rolling back

Unplug the Micro-C, swap the boat card in, plug in, wait three minutes:

```bash
scripts/halos_swap_check.sh symphony-pi
scripts/dns_cutover.sh set symphony-pi
```

The `halos` check goes late instead, and the boat card's first ping
un-pauses its own. Nothing on the boat card is changed by the trial.
