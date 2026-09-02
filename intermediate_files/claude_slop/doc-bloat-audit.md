# Doc bloat & audience-drift audit — maintenance/ and reference/

2026-08-19. Read-only analysis; no files edited. RUNBOOK.md is the standard and
out of scope. Proposals are (a) delete, (b) trim to factual line(s), (c) move,
(d) keep with reasoning. Nothing below is applied until Mark says so.

Authorship note: `git blame` was checked where prose looked hand-written. The
"Amended 2026-08016…" QuestDB paragraph in monitoring_decisions.md is Mark's
own checkpoint commit (68e4e04) and is not flagged as drift — at most it could
be folded into the containerization decision it fed, at his option.

---

## maintenance/log.md (812 lines)

Stated convention: short factual dated entries, no specs/part numbers, "when
did a major system change happen." Roughly 500 of 812 lines are the
2026-08-11…08-19 SignalK entries, and most of those are session wrap-ups, not
log entries.

### 1. Fisheries Supply itemizations (2024-08-01 through 2026-07-08, ~20 entries)
> "Purchased parts/supplies at Fisheries Supply totaling $139.10: Trident
> Marine Hose & Propane — Trident Sanitation Hose, White 1-1/2", 50 ft. Box
> (x10) …"

Violates the file's own "not a place for technical specs/part numbers" rule —
these are SKU-level line items. The date/vendor/total is legitimate log
material; the itemization is a purchase record.
**Proposal (b)+(c):** trim each to one line (`Purchased parts at Fisheries
Supply, $139.10 — sanitation hose project`), move line-item detail to a
purchases file (`reference/purchases.csv` or per-system files when populated).
`intermediate_files/fisheries-line-items.csv` already holds the source data.
Owner call — if he wants the itemization greppable in the log, keep as-is;
it's factual, just mis-filed.

### 2. The 2026-08-12/13 mega-entries (~250 lines)
These are session narratives. Representative tells:

> "Started reconciling the boat's SignalK install against the repo's, and the
> first useful result was that the framing was wrong."
> "The census also killed a tempting mistake: attributing data-model paths to
> the plugin id that published them says almost nothing…"
> "Evaluated the two voyage-logging plugins, and corrected a claim this
> session had been repeating."

That is internal reasoning and self-correction narrative — scratch notes from
a session, written for the next session. The same entries also carry specs and
prices the convention bans from the log (saillogger "USD $7.99/month", watchdog
sysfs verification detail, npm version splits), and most bullets end "written
up in RUNBOOK / reference/X" — then restate the content anyway.
**Proposal (b):** trim each day to short factual bullets of what changed on
the boat ("Rebuilt the SignalK plugin tree; 0 plugins now fail on missing
modules", "Disabled signalk-noaa-weather after it drove watchdog resets",
"Connected SignalK to the NMEA 2000 bus"). The reasoning already lives in
reference/ and RUNBOOK; delete the duplication. Estimated result: those two
days shrink from ~250 lines to ~30.

Also structural: two undated bullet blocks float after the 2026-08-13 heading
(the N2K-connection block and the healthcheck-removal block) with no date of
their own — **(b)** date them or fold them under the right heading.

### 3. 2026-08-19 repo-meta entries (~65 lines)
> "Resolved the 'Git hygiene doc redesign' item parked under Blocked. The
> destructive-command bans in CLAUDE.md § Git hygiene were written against
> the failure mode of…" (35 lines)
> "Wrap-up sweep after the git-hygiene redesign above… (owner: 'push to
> fucking main')…" (25 lines)
> "Verified the anti-polling hook enforces in a Claude Code cloud session…"
> "Applied the session-cost settings parked under Blocked…"

These log Claude's own process management (CLAUDE.md redesign, PR #9, hook
verification, settings changes) in the ship's log, at essay length, quoting
chat messages. A human reading the log to learn when a major system changed
gets nothing from them. The git history and CLAUDE.md itself already record
the substance.
**Proposal (b):** one line each ("Git hygiene rules redesigned around
per-session worktrees; PR #9 closed as reconciled"), or **(a)** delete the
hook/settings bullets outright — commits record them. Whether repo-meta work
belongs in the ship's log at all is a convention decision worth making
explicitly (see mechanism section).

### 4. Working notes addressed to future sessions
> "Note for whoever owns the watchdog: it stays vulnerable to this. Any future
> `npm install` in `~/.signalk` deletes it again…"

Written *for* Claude. It's a real risk, but it's an open item, not a log fact.
**Proposal (c):** move to priorities.md (it is in fact already tracked there
via the watchdog item) and delete here.

### 5. What's fine
The 2024–2026 physical-work entries (2024-08 approximate block, haul-out,
stern gland, the 2026-08-19 fuel filter/GFCI/deck-cap bullets) are the model
the whole file should follow. Keep. The 2026-08-14/15 entries are middling —
verbose but mostly factual; trim opportunistically, lower priority.

---

## maintenance/priorities.md (609 lines)

Stated convention: kanban; finished items move to log and get removed; backlog
position = priority. The SignalK/IoT section has become a set of essays.

### 1. Finished items still present
Violates "finished items don't stay here":
- "Heartbeat fails-silent escalation… **done and deployed 2026-08-14**… live-tested 2026-08-14" — everything in the item is done except an untested soft-warn band.
- "Host-metrics collectors: keep two, delete two — decided 2026-08-14, done 2026-08-14." Entirely done.
- "~~Census the dev container's SignalK install.~~ Done 2026-08-14…" (18 lines of findings under a struck-through title).
- ntfy work inside "Phone and audible delivery": "done 2026-08-14, both places… installed and delivering in both places 2026-08-15."

**Proposal (a)/(b):** delete the done items (log.md already records them);
where a residue is genuinely open (soft-warn untested; phone subscription),
keep only that residue as the item.

### 2. Items that are session findings, not tasks
- "Watch SignalK's memory" — 20 lines of RSS sawtooth analysis ending "the
  trend is recoverable rather than needing to be re-measured by hand." There
  is no action. **Proposal (a)**, or (b) to one line ("Check Telegraf's
  procstat trend for signalk-server RSS growth") if the watch is wanted.
- "~~Fork signalk-fixed-position~~ … Considered and rejected 2026-08-13,
  keeping the note because the write rate is real and will get re-discovered."
  A rejected idea kept as a 15-line essay. **Proposal (b):** two lines —
  rejected, why, pointer to log. (The stated reason to keep it is legitimate;
  it doesn't need the full measurement narrative twice — log.md has it too.)
- "Retire signalk-healthcheck's host section" — 30 lines, half of which is
  "Correcting this entry, which previously said…" self-correction narrative,
  and the action is marked **done 2026-08-14**. Only the "restore config to
  git needs sops rewiring" step is open. **Proposal (b):** keep that step,
  delete the history.
- "Decide what the boat computer boots from" + its two follow-on paragraphs —
  ~50 lines including a full SSD-vs-SD argument and the HALPI2 pitch, much of
  it duplicated in compute_hardware.md. **Proposal (b):** trim to the
  decision ask + "reasoning in reference/compute_hardware.md" pointer, after
  confirming that reasoning lives there (most does).

### 3. Claude-facing policy living in the backlog
These are instructions to sessions, not priorities:
- "**Do not touch the `captain` credentials**… the offer itself is the thing
  he asked to stop." Real, load-bearing, and enforced by a lint script — but
  it's a standing rule. **Proposal (c):** move to CLAUDE.md (Security posture
  or a "standing holds" bullet), leave a one-line pointer at most.
- "**Dev-container plugin configs are a workbench, not state…**" and
  "Evaluate the parked plugins… **a parked plugin is not drift**" and
  "Answering the census's question 2… cannot be done from the container" —
  three items, ~60 lines, that exist to stop future sessions from
  misreading the dev container. The *rule* is worth keeping; the evidence
  dumps (per-plugin verdicts, enumeration-artifact analysis) are session
  findings. **Proposal (b)+(c):** move the two rules (workbench; parked ≠
  drift) into CLAUDE.md in two lines each; trim the plugin-by-plugin state to
  the genuinely open questions (open-meteo fine → delete; questdb misconfig →
  one line; untraced marinetraffic anomaly → one line).

### 4. Blocked section
Fit for purpose by its own charter, but the Grafana-dashboards item closes
with coaching prose ("The honest first step is neither — it is to open both
side by side…"). **Proposal (b):** keep; trim each entry toward: question,
who answers it, pointer.

### 5. Keep as-is
- Mark's own lists at the top ("physical tasks", "nits (gross!)") — his prose,
  his file section; not touched. The overlap with Evernote is already declared
  acceptable in the header.
- The physical Backlog sections — terse, well-formed.
- Items like fail2ban, DS3231, read-only root, major-version upgrades: long
  but each is a real decision with reasoning a human needs. Trim only where a
  reference doc already carries the argument.

---

## reference/specs.md — clean. Complies with its own rules (no hedging, precise
field names, flat list). Keep.

## reference/vendors-parts.md — a bare heading. Fine (a gap beats padding).
Candidate destination if the log's purchase itemizations move.

## reference/security_posture.md — keep. It's addressed to Claude on purpose;
that's its charter per CLAUDE.md, and it's tight.

## reference/host_provisioning.md — keep. Decision + plan + boundaries, no
hedging, right altitude. This and specs.md are what reference/ should look like.

## reference/legacy_openplotter_stack.md — keep, minor notes. Explicitly
time-scoped ("will stop being true at cutover"), measured, and the Traps
section earns its length. No changes proposed.

## reference/signalk_paths.md — keep. Owner-facing, measured, the naming
observations are exactly the "why" material the file rules ask for.

## reference/compute_hardware.md

Mostly good. Three flags:

1. > "Worth keeping, because the failure was invisible for a long time and the
   > shape of it will recur."
   A doc arguing for its own existence is a session tell. **(b):** delete the
   sentence; the section stands on its content.
2. > "Orderable. The 8 GB / 512 GB SSD configuration was $614.35 and added to
   > cart without issue on 2026-08-13." and the shop-notice paragraph
   ("Don't read it as the machine being unavailable").
   Point-in-time shopping status in a reference doc; the price and stock claim
   rot within weeks and are stated as if durable. **(b):** "HALPI2 target
   config: 8 GB / 512 GB SSD (~$614 as of 2026-08-13)"; delete the cart and
   stock-notice sentences. (Duplicated a third time in priorities.md's HALPI2
   paragraph.)
3. The Hal OS section is flagged stale by containerization_strategy.md itself.
   **(b):** either update it from that file's verified findings or replace the
   section with a pointer — two docs describing HALOS at different freshness
   is the redundancy the repo rules warn about.

## reference/software_stack.md

Good spine; three drift spots:

1. "### The mount can go stale and strand the container" (~30 lines) — a
   single WSL/Docker-Desktop incident from 2026-08-12, on the dev box, ending
   with a bulleted "*Unverified, and worth correcting if you learn otherwise*"
   list. The section itself concedes "it cannot be hit" on the boat. This is
   incident forensics for a dev machine parked in the boat's reference doc,
   with speculation explicitly present (the file's own rule: verify or leave
   out). **Proposal (a)** delete, or (c) move to a dev-notes file if the WSL
   trap is worth keeping anywhere.
2. The `grafanaPort` paragraph: "*Unverified, and worth correcting if you
   learn otherwise:* the fix has never been run…" — honest, but it's a hedge
   block where the file rules say flag in conversation or leave out. **(b):**
   one line: "Untested fix: changing `grafanaPort`. Nobody has run it."
3. SSO section, document-history narrative: "…an earlier version of this
   document cited it as proof that no email-based hook existed." The doc
   narrating its own past errors is session residue. **(b):** state the
   current fact (extractUserInfo is dead code; the live path is the callback)
   without the historiography. Same for "Neither of the two routes considered
   on 2026-08-11 is what shipped" — the decision rationale is worth one
   sentence, not the timeline.

## reference/monitoring_posture.md — keep, one flag. It's a measured snapshot
("21 notifications were live when measured") that has already partially rotted
(healthcheck reconfigured since; zones added). The header dates it, which
saves it. **(b) optional:** re-title the perishable numbers as "as measured
2026-08-14" is already done — no change strictly needed; consider dropping the
"21 notifications" inventory, which is the most perishable part.

## reference/monitoring_decisions.md

The decision table and per-role verdicts are real reference. The drift is that
the doc has become a chronological accretion instead of a statement of current
truth — Role 4 especially:

> "**The prior finding was wrong, and the correction changes the plan.**…"
> "**Corrected same day, from the watchdog session reading its source**…"
> "First written as: disable all three. Amended 2026-08-14…"
> "**Verified 2026-08-15 — the watchdog hypothesis holds, and v1 exists.**"
> "**Deployed and verified on `symphony-pi`, 2026-08-15.**" (17 lines that
> duplicate log.md's 2026-08-15 entry almost clause for clause)

A reader must replay four layers of amendment to learn what's decided.
**Proposal (b):** rewrite each role to state the current decision once, with a
short "history" line where the reversal itself matters (the data-age-watchdog
blind spot genuinely does). Delete the deployment narrative — that's log.md's
job and it's already there. The "Considered and rejected" list: keep, that's
proper decision-record content. The research-trail detail in Role 1
(StatusGator event counts, FAQ quotes) — **(b)** trim to the verdict plus one
supporting fact each; the [verified] tags can stay on what remains.

Mark's own QuestDB paragraph (68e4e04): keep as-is or fold into
containerization_strategy.md at his option — not flagged.

## reference/containerization_strategy.md

Commissioned decision record with Mark in the loop; most of it earns its
place. Three flags:

1. > "Research caveat: hatlabs.fi, docs.halos.fi, questdb.com and
   > docs.influxdata.com were unreachable from the research session's proxy…"
   Session apparatus — which proxy a session used is scratch. **(b):** keep
   only "GitHub-sourced claims are solid; blog-post claims are snippet-level"
   if the caveat is wanted at all.
2. "## Boat-side investigation checklist" (~90 lines) — step-by-step
   commands with pass/fail gates. That is RUNBOOK material by the repo's own
   split (actions → RUNBOOK, why → reference). It's also one-shot rather than
   repeatable, which is why it likely landed here. **Proposal (c) or (d):**
   either move to RUNBOOK as a dated one-time procedure, or keep here but
   accept it's a plan that gets deleted once executed — decide which,
   explicitly. Also: "Findings from these steps belong back in this file…" is
   an instruction to future Claude sessions inside an owner doc; move that
   sentence to the priorities item that tracks Track B.
3. The [verified]/[unverified] tag scheme: **keep** — it's the repo's
   verify-before-asserting rule made visible, and it's the one hedging pattern
   that pays its way.

## reference/signalk_plugin_watchdog.md and reference/watchdog_writeup_draft.md

The watchdog story is told three times: the design brief here, Role 4 of
monitoring_decisions.md, and the draft post. The brief has been amended in
place ("Settled 2026-08-15…") so it now describes a plugin that exists while
titled as one that doesn't.

- **signalk_plugin_watchdog.md — (b)+(c):** the durable content is the failure
  description, the "test the failure path" lesson, and the two stopgap bugs.
  Fold the settled-crux update into a rewritten header ("this plugin now
  exists at plugins/signalk-plugin-watchdog; this file records why") and cut
  the superseded Sketch section, or move the whole thing to the plugin's own
  directory as its design doc.
- **watchdog_writeup_draft.md — (c):** it's a draft community post, not
  reference about the boat. Move to `plugins/signalk-plugin-watchdog/` (or a
  drafts/ area) if publishing is still intended; **(a)** delete if it isn't —
  the facts all live elsewhere. reference/ shouldn't hold outbound-content
  drafts.

## reference/node_red_signalk_use_cases.md (441 lines)

The clearest case of a session deliverable filed as durable reference. List 3
opens by disclaiming itself:

> "**This is a first, rough pass, not a thorough comparison.** Everything
> below is [recall]… Treat every tag below as a starting point to verify, not
> a verdict."

— 200 lines of unverified tags in a directory whose rule is "no speculation;
a gap is better than a confident guess." List 2's ranking self-describes as
double-counted. The two actionable findings it produced (derived true heading;
barometric-drop zone) were already copied into priorities.md, which is the
right place for them.
**Proposal (b), owner call:** keep List 1 (the idea inventory — genuinely
reusable) and the Excluded list (what Symphony already covers — verified-ish);
delete List 2; collapse List 3 to the handful of confirmed items (owner-
confirmed n/a's like no-generator/no-Starlink are worth keeping as facts).
If Mark commissioned this as-is and wants the full survey, (d) keep — but
then it should drop the [recall] tags by being verified, or live outside
reference/.

---

## Structural drift — where the checkpoint content came from

Pattern, not accident: four forces each pushed session state into these files.

1. **Session wrap-ups needed a home and log.md was the only dated file.** The
   continuity rule ("write where we are before ending") is right, but its
   output — narrative, self-corrections, verification detail — is scratch,
   and it landed in the ship's log because nothing else was designated. The
   08-12/08-13 log entries are wrap-ups verbatim.
2. **priorities.md became the inter-session message bus.** The Blocked section
   legitimized parking session questions there; the pattern then leaked into
   Backlog as "done" annotations, correction narratives, and rules-for-other-
   sessions (workbench, parked-plugin, captain-freeze). Tasks and messages are
   different things sharing one file.
3. **reference/ absorbed one-shot research deliverables.** The use-case
   survey, the writeup draft, the boat-side checklist — each was a session's
   output that needed to persist, and reference/ was the persistent place.
   None of them is "architecture and why-notes for a human to read later."
4. **Decision docs accreted instead of being restated.** Corrections were
   appended ("first written as… amended… corrected same day") because
   appending is safer for a session than rewriting — but the reader pays for
   it every time.

## Proposed mechanism to keep it from recurring

Recommendation first: **create a designated scratch home and add a per-file
admission test to CLAUDE.md; back the log rule with the existing lint hook.**
Specifically:

1. **`maintenance/journal/` for session wrap-ups.** Tracked (so any session,
   local or cloud, can read it — unlike Artifacts or the local memory dir),
   one dated file per session/topic, explicitly non-authoritative and
   deletable. New rule: log.md gets at most ~3 lines per event; anything
   longer is a journal entry the log line may point to. This gives the
   continuity rule a destination that isn't the ship's log. (The untracked
   strays in the working tree right now — runbook_formatting_analysis.md,
   before_after_examples.md, results.json — show sessions already improvising
   exactly this; naming the place ends the improvisation.)
2. **A three-line "admission test" at the top of each file's CLAUDE.md
   section**, phrased as what a *reader* uses it for, e.g.:
   - log.md: "A human skimming for 'when did X change.' One event = 1–3 lines,
     past tense, no reasoning, no prices/specs. If you're explaining *why*,
     it goes in reference/ or the journal."
   - priorities.md: "Open work only. An item = the ask + owner + one pointer,
     ≤5 lines. Done → delete (log gets the line). Rules for sessions →
     CLAUDE.md. Evidence → journal or reference."
   - reference/: "Current truth a human reads later. State conclusions, not
     the path to them; corrections rewrite the text, never append to it.
     Dated snapshots and unverified surveys don't come in."
3. **Move the Claude-facing standing rules out of priorities.md into
   CLAUDE.md** (captain-credentials freeze, dev-container workbench rule,
   parked-plugin rule) so the backlog stops doing double duty as policy.
4. **Enforcement for the one rule that keeps failing:** extend
   `scripts/lint_repo_hygiene.py` (already wired for the captain-credential
   guard) with a soft check on log.md — warn when a single bullet in a new
   entry exceeds ~5 lines. Per the standing orders, what *must* happen
   belongs in a hook, not prose; this is the only rule here with a cheap
   mechanical test. The reference/ and priorities rules stay prose — they
   need judgment.

Not proposed: Artifacts (not readable back by other sessions, per the brief);
a new template regime for reference/ (the good files — specs, security
posture, host provisioning — got good without one).

## Rough size impact if all proposals land

log.md ~812 → ~350 lines; priorities.md ~609 → ~400; node_red survey ~441 →
~200; monitoring_decisions ~369 → ~220; watchdog files consolidated to one;
software_stack/compute_hardware trims are small but remove the staleness
traps. Numbers are estimates from the flagged spans, not measurements.
