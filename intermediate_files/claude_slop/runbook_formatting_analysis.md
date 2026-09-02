# RUNBOOK.md Formatting & Readability Analysis

## Current State Summary
- **Total length**: ~2286 lines
- **Table of contents**: Lines 16-52 (informal bullet-link navigation)
- **Main sections**: ~40+ major headings (h2/h3 mix)
- **Visual breaks**: Minimal (no rules between major sections)
- **Callouts/emphasis**: Mostly bold text, no dedicated callout blocks

---

## 1. TABLE OF CONTENTS ISSUES

### Current State (lines 16-52)
```markdown
## Where things are

**Getting in:** [Remote SSH access](#remote-ssh-access) · ...
**Building and maintaining the host:** [Bringing up a host](#bringing-up-a-host) · ...
```

### Problems Identified
1. **No numbered TOC** — informal navigation only
2. **Long lines** — bullet points wrap awkwardly
3. **No hierarchy** — all groups are visually equal despite different importance
4. **Sections not self-linking** — "Where things are" isn't referenced elsewhere
5. **No visual separation** between topic groups (only uses **bold** labels)

### Targeted Improvement
Add:
- Numbered sections (optional but helpful)
- Visual separators (blank line) between groups
- Consistent bullet depth
- Optional: expand headings to show structure levels

```markdown
## Navigation

**Getting in**
- [Remote SSH access](#remote-ssh-access)
- [Reaching the boat over Tailscale](#reaching-the-boat-over-tailscale)
- [The resident Claude session on the boat Pi](#the-resident-claude-session-on-the-boat-pi)

**Building and maintaining the host**
- [Bringing up a host](#bringing-up-a-host)
- [Installing host files](#installing-host-files)
- [Turning on the off-boat heartbeat](#turning-on-the-off-boat-heartbeat)
- [Don't autostart a browser on the boat Pi](#dont-autostart-a-browser-on-the-boat-pi)
- [Upgrading the scanners](#upgrading-the-scanners)

...
```

---

## 2. HEADING HIERARCHY ISSUES

### Current Pattern
- Mix of h2 (`##`) and h3 (`###`) without clear rules
- Long descriptive headings (sometimes 10+ words)
- "When X" pattern repetitive but clear for troubleshooting sections
- No h1 (reserved for document title)

### Examples of Inconsistency
```
### Phase 1 — Host and tooling          # short, OK
### SSH users and the periodic check    # descriptive
### A page hangs but the host is reachable — MTU    # long
### When every stored token is dead     # problem-statement
### Re-testing the login flow without real providers  # long descriptor
```

### Issues
1. **Inconsistent depth**: subsections vary between h3, h4 conceptually but all use h3
2. **Length variance**: some 2-3 words, some 15+ (reading/scanning harder)
3. **Parallel structure missing**: "When X" is good for problems, but mixed with other patterns

### Targeted Improvements
1. **Reserve h3 for immediate subsections only** — add h4 for sub-subsections
2. **Standardize problem headings** — use "When X happens" consistently in troubleshooting
3. **Consider shortening** some headings with descriptive text moved to lead sentence
   
**Example Refactor**:
```markdown
## Rotating a secret

**Layer 1: updating a stored value**

### ...

## Troubleshooting

### When a secret was committed in plaintext
### When every stored token is dead
### When the boat's hostnames stop resolving
```

---

## 3. VISUAL BREAKS & WHITESPACE

### Current Usage
- No horizontal rules (`---`) between major sections
- Single blank lines between paragraphs (correct)
- Dense text blocks (10-15 lines) without breaks
- Code blocks provide some visual relief

### Issues
1. **Long sections feel monotonous** — lines 552-648 (96 lines on "Adding a secret" with minimal breaks)
2. **Subsection transitions unclear** — no visual marker when moving to new topic
3. **Important "gotchas" buried in prose** — hard to spot while scanning

### Targeted Improvements
Add horizontal rules (---) or visual breaks:

**Before:**
```
### Phase 2 — Key material
Get the age **private** key onto the host out-of-band...
```bash
mkdir -p ~/.config/sops/age
```
*Verify:* `sops --decrypt...
```

### Phase 3 — Repo and configuration
```bash
git clone https://github.com/mark-brannan/symphony.git
```
```

**After:**
```
### Phase 2 — Key material
Get the age **private** key onto the host out-of-band...

```bash
mkdir -p ~/.config/sops/age
```

*Verify:* `sops --decrypt...

---

### Phase 3 — Repo and configuration
```bash
git clone https://github.com/mark-brannan/symphony.git
```
```

---

## 4. WARNINGS, NOTES, AND CALLOUTS

### Current State
- **Bold** for emphasis (`**Layer 1:**`, `**Prevent this.**`)
- Occasional inline warnings (e.g., "**stop**:")
- No dedicated callout blocks (> blockquotes, color boxes, etc.)

### Identified Callout Candidates

**Critical warnings that need highlighting:**
1. Line 261: "If it doesn't, stop — nothing downstream will work"
2. Line 285: "Filters can't be wired before this point"
3. Line 483-484: "If that diff shows the URL in the clear, **stop**"
4. Line 530: "Chromium started from autostart... wedges the v3d driver"
5. Line 1042-1044: "If SignalK was already running during setup, restart it"
6. Line 1988: "Never run npm install over a broken tree"
7. Line 2100-2101: "Confirm no install is in flight first"

**Procedure gotchas:**
1. Line 353-356: "If it minted a new `influx_token`..."
2. Line 445-446: "Don't call `shutdown` from cron directly"
3. Line 625: "Never point `add_inplace_secret.sh` at `secrets/*.sops.yaml`"
4. Line 1072-1075: "Until the two agree, committing the file is blocked"

**Important notes about trade-offs:**
1. Line 393-395: "But check rather than assume it"
2. Line 797: "Record it in `ROTATION.md`"
3. Line 1590-1597: "A fallback that has become the primary looks exactly like success"

### Best Practice: Markdown Callout Syntax
Use blockquotes with emoji/keywords (GitHub-rendered nicely):

```markdown
> ⚠️ **Warning:** If the URL is exposed in plaintext, the clean filter isn't wired correctly. Stop and re-run `bash scripts/setup-git-filters.sh` before continuing.

> 🔴 **Critical:** Never run `npm install` over a broken tree — npm treats half-written package directories as installed and won't repair them.

> 💡 **Tip:** Record completed rotations in `ROTATION.md` to track credential lifecycle.

> 📌 **Note:** The fallback position looks identical to a working GPS. Read `$source` to confirm.
```

---

## SUMMARY: Targeted Improvements

| Area | Impact | Effort | Priority |
|------|--------|--------|----------|
| Reformat TOC with spacing/groups | Medium | Low | High |
| Add visual breaks (---) between major sections | Medium | Low | High |
| Convert 8-10 critical warnings → callout blocks | High | Low | High |
| Standardize h3/h4 heading depth | Low | Medium | Medium |
| Shorten 5-6 longest headings | Low | Low | Medium |
| Add 3-4 "procedure gotcha" callouts | Medium | Low | Medium |

---

## SUGGESTED FOLLOW-UP SESSION

**Scope:** Apply targeted formatting improvements while preserving all content
- Reformat TOC for better scanning
- Add horizontal rule separators after major section closes
- Convert identified warnings to blockquote callouts (8-10 spots)
- Standardize heading levels (h3 → h4 for deeper nesting)
- Minor heading text adjustments (1-2 words shortened)

**Model:** Sonnet 5 (handles structured text editing well, good balance)
**Effort level:** Medium (not complex, but needs precision to avoid breaking Markdown)
**Time estimate:** 30-45 minutes

**Exact prompt template:**
```
Review /home/user/symphony/RUNBOOK.md for formatting improvements:
1. Reformat "Where things are" TOC with visual spacing between topic groups
2. Add horizontal rules (---) to visually separate major sections
3. Convert these warning passages to blockquote callouts with ⚠️/🔴/💡 emoji:
   - Line 261 (verify failure)
   - Line 483-484 (sops filter not wired)
   - Line 1988 (npm install on broken tree)
   - [7 more specific line ranges]
4. Standardize heading hierarchy (reserve h4 for deep nesting)
5. Apply changes, verify Markdown syntax, commit to claude/runbook-formatting

Show me each change before/after so we can review and iterate.
```
