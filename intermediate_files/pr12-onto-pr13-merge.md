# Rebasing #12 onto #13 — trial run, already done

> **Naming caveat, 2026-08-19.** Mark rejected `SYMPHONY_MODE` /
> `SYMPHONY_STRICT` on #13: "mode" collides with vessel operating mode and
> SignalK's own usage, and the boat's name has no business in a mechanism
> that isn't boat-specific. #13 is renaming as this was written. Wherever
> this file says *the enforcement switch*, read whatever #13 landed —
> the concept is what matters, not the spelling. The proposal I put to
> them was `SECRETS_ENFORCEMENT=strict|warn-only`, one variable instead
> of two. **Nothing in #12's shipped code references the old names**, so
> the rename costs this branch only the wording below.

Result of actually rebasing `claude/precommit-global-state-design-2ujiib`
onto `claude/bold-wozniak-alvlcl` rather than predicting it. Recorded so
whoever does the real rebase after #13 lands does not re-derive any of it.

`pr12-onto-pr13-merge.patch` held the resolved versions of the three files
that needed judgment. It was deleted once the real rebase landed: a tracked
copy of source diverges from the source the moment the source changes, and
it had already gone stale (it predated `gitattributes_filters()` and
`filter_is_configured()`, and carried a test asserting on wording that the
live suite no longer has). The live scripts are authoritative; this file
keeps the reasoning, which does not rot the same way.

## Conflict surface: four, all resolved, none hard

| file | resolution |
|---|---|
| `scripts/lint_repo_hygiene.py` | **the only real one** — both PRs rewrote `rule_declared_filters_are_configured`. Merged as AND (below). |
| `scripts/precommit_secret_guard.sh` | **skip my commit entirely** — it was messages-only and #13 rewrote the same messages through the shared message formatter. Superseded. |
| `.pre-commit-config.yaml` | take #13's `run_secret_tooling_tests.sh` runner; append my two suites to it; union the `files:` patterns. |
| `scripts/test_pseudonymize.py` | both fixed the same sops-skip. Keep #13's strict-mode gate (strict still runs it) **and** my `StoreUnavailable` skip — sops installed but no age key is a real case #13 misses. In strict, re-raise instead of skipping. |

Also: git auto-merges my `die()` in `sops_filter.py` back in. **Delete it** —
PR #13's `can_encrypt()` gate runs earlier and covers more -- take its file whole.

## The rule, merged

Two axes. MODE = who is committing. SCOPE = what is in the commit.
Composed as AND:

    hits     = staged paths covered by this unconfigured filter
    blocking = bool(hits) or <enforcement is strict>

So a staged covered path blocks in **every** mode, contributor included —
that is content, and content is never softened by mode. An unconfigured
filter with nothing covered staged is environment: strict blocks,
contributor warns, and a contributor can still commit a typo fix.

Taking either axis alone loses something real: mode alone lets a
contributor stage a plaintext secret with only a warning here; scope alone
stops strict mode complaining about a clone that is not wired up.

## The only thing #12 needs from #13's naming

Something callable that answers strict-vs-not. The merged rule is

    blocking = bool(hits) or enforcement_is_strict()

Any spelling works. The AND is the load-bearing part: mode/enforcement may
soften a guard about your ENVIRONMENT, never one about the CONTENT of your
commit.

## Found in the trial, worth keeping

- The staged-block message had lost the `SKIP=` / `--no-verify` exits in my
  merge — restored. A blocked person always gets three ways out.
- Two of my tests asserted on message *wording* (`"unconfigured-filter" in w`)
  and broke the moment the formatter changed. Rewritten to assert behaviour.
  They were change-detectors; that is on me.

## Verified on the merged tree

All six suites pass. In a clone with no sops, no age key, no filters:

- contributor staging a doc edit -> all guards pass, commit goes through
- contributor staging a sops-covered file -> BLOCKED, correctly, in
  contributor mode

CI must gain `hostvars_filter.py check --all` — once scoping lands, the
existing unscoped `check` passes vacuously in CI, because nothing is staged
there. Same for `lint_repo_hygiene.py --all` and
`check_encoding_health.py --repo`.

## Done for real, 2026-08-19, after #13 merged

The trial above held. What it did not predict:

- **A fifth conflict**, in `scripts/hostvars_filter.py` — #13's later review
  round added `head_blob()` at the same place this branch added
  `staged_paths()`. Purely additive; kept both.
- **#13 had already landed `staged_paths()` and `gitattributes_filters()`**
  in `lint_repo_hygiene.py`, so this branch's copies of both were dropped
  rather than merged. The rule itself merged as the notes said: AND, via
  `blocking = bool(hits) or secretguard.mode() == "strict"`.
- **#13's version of the rule matched staged paths by exact membership**
  (`p in set(declared[name])`) where this branch used fnmatch.
  `.gitattributes` entries are globs, so exact membership silently missed
  any pattern-declared path. Took fnmatch.
- **The scoping tests passed vacuously on any clone that has the filters
  wired** — the rule returns early there, so every assertion held while
  testing nothing. `filter_is_configured()` is now a seam the tests pin.
  This is the same failure mode as the `check --all` one, one level in.
- The two wording assertions were rewritten to assert severity and the
  presence of message fields, not phrasing.

`validate.yml` needed no change — `check --all` came through the auto-merge
intact. Confirmed the failure it prevents: `check` without `--all` in CI
prints "this commit stages no hostvars-covered file" and exits 0.

Verified in a throwaway keyless clone (no sops, no age key, no filters,
mode auto-detects contributor):

- doc edit → all four guards pass, commit lands;
- `signalk/plugin-config-data/venus.json` staged → BLOCKED in contributor
  mode, full message, and the named `git restore --staged` exit clears it;
- latin-1 file staged → BLOCKED, and the `--fix` the message names works;
- all six suites pass, `bash -n` clean over every script.

One note-vs-reality difference worth recording: the notes say "take #13's
`sops_filter.py` whole," which also drops this branch's one-line addition to
the pseudonym-map warning (`git add secrets/pseudonyms.sops.yaml`). Followed
the notes; the warning itself predates both PRs and still fires.
