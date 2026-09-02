# Handoff prompt — install the HALOS i2c fix and confirm the watchdog

**Model: Sonnet 5. Effort: low.** Two mechanical changes with one-line tests.
No design decisions. The analysis is done; this is execution.

---

Two things are outstanding on the HALOS bench card (`ssh pi@192.168.0.193`,
tailnet name `symphony-halos`) before it swaps into the boat Pi.

Full evidence for both:
`intermediate_files/claude_slop/halos-b3-findings-2026-09-02.md`.
The card for the first is in `intermediate_files/claude_slop/kanban.md`.

`sudo` on that box needs a password:

    sops -d --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml \
      | ssh pi@192.168.0.193 'sudo -S -p "" <cmd>'

Never pipe the password and file content through the same stdin — write the
file as `pi` first, then `sudo cp` it into place as a separate command.

## Task 1 — the SignalK container cannot open `/dev/i2c-1`

Measured 2026-09-02: the container runs as non-root `node`; the host `i2c`
group is gid 988 and `/dev/i2c-1` is `crw-rw---- root:988`, but `group_add`
grants only 960 and 4. The image has *its own* `i2c` group at gid 990, so `id`
inside the container reads as correct and grants nothing, and `privileged:
true` does not help a non-root user. Confirm the defect first:

    docker exec signalk-server python3 -c "open('/dev/i2c-1')"
    # expected before the fix: PermissionError: [Errno 13] Permission denied

This is a **regression the swap would introduce**, not an untested gap — the
boat's current card reports `bme680 ok` today. It fails silently: `i2c-reader`
logs only "devices config is missing", and an empty BME680 tree is
indistinguishable from the normal ~10 min post-restart burn-in.

**The fix.** Write this to
`/etc/container-apps/marine-signalk-server-container/symphony.override.yml`.
It is the existing file with `group_add` added; everything else is verbatim
and must stay that way — the healthcheck block is another session's fix for a
restart loop, do not alter it.

    # Symphony's override for HALOS's marine-signalk-server-container compose file.
    # HALOS gives SignalK 60 s to answer its healthcheck; a 120-plugin config takes
    # longer, and autoheal restarts the container before it finishes starting.
    #
    # group_add: the host's i2c group is gid 988. The image has its own i2c group at
    # gid 990, so `id` inside the container looks correct while /dev/i2c-1 (root:988)
    # stays unreadable; privileged:true does not help because signalk runs as non-root
    # `node`. 4 (adm) and 960 are HALOS's own grants, repeated here because compose
    # list-merge semantics are not worth betting on.
    services:
      signalk-server:
        group_add: ["4", "960", "988"]
        healthcheck:
          test: ["CMD-SHELL", "curl -sf http://127.0.0.1:3000/signalk || exit 1"]
          interval: 30s
          timeout: 30s
          start_period: 900s
          retries: 3

Before writing it, `cat` the file that is there and confirm the healthcheck
block still matches the one above. If it has changed, keep the version on the
box and add only the `group_add` line — do not overwrite their work.

Then:

    sudo systemctl restart marine-signalk-server-container.service
    docker exec signalk-server python3 -c "open('/dev/i2c-1')"   # silence = pass

**Also apply the same `group_add` line to `host/halos/` on PR #33** — that
copy is the source of truth and the box would otherwise drift back. If PR #33
has already merged, the file is on `main`.

If Mark has a BME680 wired to the bench card by then, that is the only chance
to test the i2c path against real hardware before the swap: `i2cdetect -y 1`
on the host, the same from inside the container, then confirm the BME680
plugin publishes deltas under `environment.inside.*`. Allow ~10 min of
burn-in before calling it a failure.

## Task 2 — confirm `plugin-watchdog` is actually running

Installed, enabled, and its config (`plugin-watchdog.json`, id
`plugin-watchdog` — *not* the package name) is the live one. What is unproven
is that it ticks. It could not be tested because nothing stayed up long
enough.

The test needs **600 s of unbroken SignalK uptime** — `graceSeconds` is 600,
and every restart resets the clock. The restart in task 1 starts that window,
so do task 1 first and then leave the unit alone.

    # note the start time
    docker inspect signalk-server --format '{{.State.StartedAt}}'
    # 11+ minutes later:
    docker logs signalk-server 2>&1 | grep 'ALERT: plugin'

Expected: `ALERT: plugin bt-sensors-plugin-sk enabled but has published no
deltas since startup (grace 600s exceeded)` — there are no BT sensors in range
at home, so the watchdog *should* alarm. **That line appearing is the pass.**
Its absence after 11 minutes of unbroken uptime means the watchdog is not
running, which is a real finding worth chasing.

Confirm uptime was genuinely unbroken before concluding anything —
`.State.StartedAt` must be unchanged from the value you noted.

Do not use `statusMessage` from `/skServer/plugins` as evidence either way:
only 2 of 63 enabled plugins populate it on this server version, and both
carry `''`. An empty status does not mean a plugin failed to start.

## House rules that bite on this box

- **Memory.** 1844 MB, and it cannot run SignalK plus the databases. Keep
  `opencpn`, `avnav`, `homarr`, `questdb`, `grafana` stopped. A stop does not
  survive a reboot — if the box has rebooted, re-stop them (`docker stop
  homarr`, not the systemd unit, which would also stop Traefik and Authelia).
  Check `free -m` first; under ~400 MB available with swap active is real
  pressure.
- **No reboot or power-cycle** without agreement from any other session
  working the card. Stopping units is always fine.
- Long operations go under `systemd-run --unit=<name> --collect`; never
  `docker exec` a long npm operation, the unit tears its own container down.
- Commit with an explicit pathspec. Land on `main` unless PR #33 is still
  open and the `host/halos/` change belongs on its branch.

## Done looks like

`docker exec signalk-server python3 -c "open('/dev/i2c-1')"` exits silently;
the `group_add` line is in both the box and `host/halos/`; the watchdog's
ALERT line is either observed (and recorded) or its absence is recorded as an
open finding; `halos-b3-findings-2026-09-02.md` updated with what you measured
and the kanban card deleted if it is closed.
