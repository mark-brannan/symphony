# Agent decisions

Append-only. Each entry is a call an agent made in pencil: a default it took
under the one-way-door test, with its undo. Written by `agent-decision`; the
heading is the UTC stamp, so `agent_decisions.md#<stamp>` links one entry.

### 20261008t032150z
- HALPI2 bench rollback = release image Halos-Desktop-Marine-HALPI2-AP_2026-08-20.0.img.xz (the shipped image), not a file-level tar Undo: take a file-level tar of / with docker stopped before the real run ([#92](https://github.com/mark-brannan/symphony/pull/92))

### 20261016t035413z
- firmware imported into symphony firmware/halmet rather than a separate repo (the owner offered symphony; the plan records that SensESP repos under the organisation were a mistake) Undo: move the dir to its own repo ([#98](https://github.com/mark-brannan/symphony/pull/98))

### 20261016t045723z
- Boat-down triage raw diagnostics and the agent transcript go to the private claude_prompts_scratch repo under raw_logs/, linked from the public issue, instead of an age-encrypted 1-day artifact. Undo: Revert to the upload-artifact step of 59270367 and drop the scratch push. ([#99](https://github.com/mark-brannan/symphony/pull/99))

### 20261016t045725z
- A triage run whose diagnostics or agent log cannot be saved to the scratch repo fails the job visibly instead of passing green. Undo: Drop the exit 1 on the missing-log branches; the issue comment still shows what was saved. ([#99](https://github.com/mark-brannan/symphony/pull/99))

### 20261016t060101z
- A Discord notification that fails never fails the watch or the triage: the notifier always exits 0 and prints a warning. Undo: run the notifier with check=True and let a Discord or gh failure fail the step ([#112](https://github.com/mark-brannan/symphony/pull/112))

### 20261016t060106z
- One Discord message per outage, edited in place, embed only, mentions disabled; the shared channel sees four edits, not four posts. Undo: post a fresh message per event and drop the marker on the issue ([#112](https://github.com/mark-brannan/symphony/pull/112))

### 20261016t060109z
- The Discord message id is stored on the public GitHub issue body as an HTML comment marker; it identifies a message, not a credential. Undo: keep the id in the workflow run or a scratch-repo file instead ([#112](https://github.com/mark-brannan/symphony/pull/112))

### 20261117t212703z
- Moved all 44 tracked files (not just the 35 counted) to state/symphony/ in the state repo Hook now writes to state repo (SYMPHONY_STATE_DIR or ~/claude_prompts_scratch/state/symphony), silent if absent Dropped CLAUDE.md direct-to-main privilege for the old path Left dangling path mentions in reference docs and ansible comments Undo: revert the commit ([#79](https://github.com/mark-brannan/symphony/issues/79)) (no PR, branch claude/symphony-state-out)

### 20261117t212818z
- Test-rig design doc lives in reference/ (design rationale per CLAUDE.md), not docs/ Undo: move the file ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261117t212833z
- Test rig state is a named volume seeded from an image, no host bind mounts, following the grafana bake pattern Undo: edit the design doc ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261117t212846z
- Test rig overlay applied by copy into the seed tree, not single-file mounts, so admin-UI saves work Undo: edit the design doc ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261117t212854z
- Test rig blanks sops-named fields from git objects rather than decrypting; it holds no age key Undo: edit the design doc ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261117t212901z
- Test rig verdict is a two-pass per-plugin diff, released vs PR, on the same seed Undo: edit the design doc ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261117t212909z
- PR 162 Refs #63 rather than Closes: seven design-level questions remain the owner's Undo: edit PR body to Closes #63 ([#162](https://github.com/mark-brannan/symphony/pull/162))

### 20261118t043827z
- Alt not charging: alternator under 13.0 V for 30 s while RPM > 0 Undo: change 13.0f / 30 in the OLED alert loop ([#163](https://github.com/mark-brannan/symphony/pull/163))

### 20261118t043831z
- Err covers oil pressure, alternator and low memory; not reset or Signal K link Undo: edit err_alert in the OLED alert loop ([#163](https://github.com/mark-brannan/symphony/pull/163))

### 20261120t030309z
- lux rev 10: collar 36->48, bar notches open aft, tip 52x18, window 4 mm above joint, flat flange pocket, M3 inserts throughout ([#173](https://github.com/mark-brannan/symphony/pull/173))

### 20261120t231255z
- Always-on breaker stays and feeds the small fuses for Cerbo, bilge pumps and monitoring Inverter disconnect drawn as a second m-Series switch after the fuse Negative bar has one return stud per load, eight in all Undo: edit build() in house-bank-busbar-board.py and regenerate ([#174](https://github.com/mark-brannan/symphony/pull/174))

### 20261120t231406z
- IMU research README: bench experiments stay in symphony; driver trials and the board go to workshop when they start Undo: edit research/imu-mag/README.md ([#175](https://github.com/mark-brannan/symphony/pull/175))

### 20261120t232636z
- Battery leads enter at the top edge so the unswitched leads can leave the bottom Class T holder drawn 100 x 40 mm with the cable on the fuse studs, a guess until the part is named Undo: edit build() in house-bank-busbar-board.py and regenerate ([#174](https://github.com/mark-brannan/symphony/pull/174))

### 20261121t024917z
- Spare hole on the unswitched bar costs 1 in of board width Unswitched bar drawn passing under the master switch body; not checked against the part Positive board drawn 22 x 9.5 in, shorter than the 10 in before Undo: set SPARE = 0 and BOARD_W back 25.4 in house-bank-busbar-board.py ([#174](https://github.com/mark-brannan/symphony/pull/174))

### 20261121t025455z
- Breakers drawn on their sides, input right, lead leaving the left edge Inverter breaker drawn with its rating open, not 60 A Undo: swap breaker_side for breaker in house-bank-busbar-board.py ([#174](https://github.com/mark-brannan/symphony/pull/174))

### 20261121t050644z
- Drawing takes the shunt at the far end of the negative bar, of the C4b arrangements Undo: move the shunt back left and add a return strap from the far end (C4b second option) ([#174](https://github.com/mark-brannan/symphony/pull/174))

### 20261121t073959z
- chart-table cabinet sheet: a bold outline marks a box drawn to measured size chart-table cabinet sheet: the V/A meter gets its own legend colour, metering chart-table cabinet sheet: one measured lever terminal takes the first 54 mm of the dashed rail 2 placeholder, the rest stays TBD chart-table cabinet sheet: measured parts drawn centred on the rail's height Undo: revert e913986 ([#181](https://github.com/mark-brannan/symphony/pull/181))

### 20261122t101536z
- Homes for the 3D maps: research/nav-desk/ and research/shower-sump/; single-file fit-four-planner.html bundle left out as a duplicate Undo: move the folders in a follow-up PR ([#184](https://github.com/mark-brannan/symphony/pull/184))
