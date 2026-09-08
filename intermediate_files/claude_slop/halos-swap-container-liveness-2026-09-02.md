# Container liveness, and what the swap has to carry — 2026-09-02

Prep for the HALOS card swap ([plan](halos-swap-plan.md),
[dispatch](dispatch-halos-swap-day.md)). The boat card's `dex`, `questdb`
and `ntfy` now have healthchecks and an `autoheal` container; this is what
that means for the card that replaces them.

## The two cards do the same job by different routes

| | boat card (`openplotter`) | HALOS card |
|---|---|---|
| autoheal | `compose-autoheal.yml`, this repo | HALOS core, `halos-core-containers` |
| scope | opt-in: `autoheal: "true"` per service | `AUTOHEAL_CONTAINER_LABEL=all` |
| stop timeout | 30 s | 10 s |
| curl timeout | 60 s | 30 s (stock) |

Both work. They diverge because HALOS owns its whole host and this repo's
compose stack shares a daemon with hand-run containers.

## What to check on swap day

- **`ntfy` is the one service that crosses.** `reference/system_map.md` has
  it running from `compose-ntfy.yml` on both cards. Its healthcheck rides
  along in the file, and HALOS's `all`-mode autoheal covers it without
  needing the label. No gap, but it means ntfy is watched by a watchdog with
  a 10 s stop timeout rather than 30 s. Harmless for ntfy, which stops
  cleanly.
- **Don't start this repo's `autoheal` on the HALOS card.** HALOS already
  runs one. Two would both act on the same unhealthy container and race on
  the restart. If `compose-autoheal.yml` is ever brought up there, give the
  HALOS one the job and leave ours down.
- **`docker ps` health is now in the preflight** — done 2026-09-03. Both
  `scripts/halos_swap_check.sh` and `halos_preflight.sh` FAIL if any
  container isn't reporting `(healthy)`.

## The risk this introduces, named

`dispatch-halos-swap-day.md` § Known before the day says: *"The boat card's
QuestDB may not answer in 30 s; that is the baseline, not the new card."*

That is now a liveness input, not just a preflight caveat. QuestDB's probe
is `curl --max-time 15` against `/exec?query=select 1`. If the boat card's
QuestDB is genuinely that slow under load, the probe fails, and three
consecutive failures 30 s apart restart it.

Two reasons that is tolerable rather than a bug, but both are judgements
worth revisiting if it fires:

- It needs ~90 s of sustained failure, not one slow query. A single slow
  answer costs nothing.
- A QuestDB that cannot answer `select 1` in 15 seconds, three times
  running, is not healthy in any sense the rest of the stack cares about.
  Restarting it is what a session did by hand on 2026-09-02.

Measured after that session's cleanup: 51 ms. Every probe since has passed.
If autoheal starts restarting QuestDB on the boat, raise `timeout` and
`--max-time` together before assuming a fault — and read
`docker logs autoheal` first, which now records every restart truthfully.

## Verified, and the one leg that isn't

Tested on the boat 2026-09-02, twice, by SIGSTOP on the container's PID 1 —
a process that spins and never exits, which is what `restart: unless-stopped`
cannot see and what QuestDB did for eleven hours:

- unhealthy after three failed probes, restarted by autoheal, healthy again
  132 s and 142 s from the freeze;
- QuestDB's probe checked on its own: `curl` exits 28 after 15 s while
  frozen, 0 again after SIGCONT.

**Not tested: a full host reboot.** Every container reached `healthy` with a
zero failing streak on recreate and no `start_period` is near its measured
cold start (dex 4 s, ntfy 2 s, questdb 17 s), so flapping is unlikely — but
a cold boot with SignalK's plugins and everything else contending is a
different load than a recreate on a quiet box. Check `docker ps` after the
next reboot, whichever card is in the boat.
