# RUNBOOK.md Formatting — Before & After Examples

## Example 1: Table of Contents Reformatting

### BEFORE (lines 16-52, current state)
```markdown
## Where things are

**Getting in:** [Remote SSH access](#remote-ssh-access) ·
[Reaching the boat over Tailscale](#reaching-the-boat-over-tailscale) ·
[The resident Claude session on the boat Pi](#the-resident-claude-session-on-the-boat-pi)

**Building and maintaining the host:** [Bringing up a host](#bringing-up-a-host) ·
[Installing host files](#installing-host-files) ·
[Turning on the off-boat heartbeat](#turning-on-the-off-boat-heartbeat) ·
[Don't autostart a browser on the boat Pi](#dont-autostart-a-browser-on-the-boat-pi) ·
[Upgrading the scanners](#upgrading-the-scanners)

**Secrets and encryption:** [Adding a secret](#adding-a-secret) ·
[Rotating a secret](#rotating-a-secret) · ...
```

**Issues:**
- Lines break awkwardly in editor/web view
- Dots (·) create visual clutter
- Hard to scan at a glance

### AFTER (proposed)
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

**Secrets and encryption**
- [Adding a secret](#adding-a-secret)
- [Rotating a secret](#rotating-a-secret)
- [Rotating the age key](#rotating-the-age-key)
- [Removing a secret](#removing-a-secret)
- [Email pseudonyms in security.json](#email-pseudonyms-in-securityjson)
- [Per-machine config values](#per-machine-config-values)
- [Router config backup](#router-config-backup)
- [Scanning for leaks by hand](#scanning-for-leaks-by-hand)

**Identity and access**
- [SSO login (GitHub / Google)](#sso-login-github--google)

**Running SignalK**
- [Stopping SignalK on the boat Pi](#stopping-signalk-on-the-boat-pi)
- [SignalK's NMEA 2000 input](#signalks-nmea-2000-input)
- [Setting up a BLE sensor](#setting-up-a-ble-sensor-in-bt-sensors-plugin-sk)

**When something's broken**
- [Hostnames stop resolving](#when-the-boats-hostnames-stop-resolving)
- [A plugin isn't in the config UI](#when-a-plugin-isnt-in-the-config-ui)
- [SignalK errors about missing packages](#when-signalk-errors-about-missing-packages-on-the-boat-pi)
- [BLE sensors silent after a reboot](#ble-sensors-go-silent-after-a-reboot)
- [A BLE sensor connects but delivers nothing](#a-ble-sensor-connects-but-never-delivers-data)
- [A plugin fork keeps reverting](#a-local-plugin-fork-keeps-reverting-to-the-registry-build)
- [A hook blocks your commit](#when-a-hook-blocks-your-commit)
- [Never use OpenPlotter's "Reinstall"](#never-use-openplotters-reinstall-for-signal-k)

**Incidents & recovery**
- [A secret was committed in plaintext](#a-secret-was-committed-in-plaintext)
- [Recovering a lost age key](#recovering-a-lost-age-key)
```

**Improvements:**
✅ Scannable bullet list format  
✅ Logical grouping is obvious  
✅ Consistent indentation  
✅ No line wrapping issues  

---

## Example 2: Adding Visual Separators Between Sections

### BEFORE (lines 652-670, current state)
```markdown
## Rotating a secret

**Layer 1:**

```bash
sops secrets/symphony.sops.yaml          # edit the value, save
python3 scripts/render.py
docker compose up -d --force-recreate <service>
```

`GF_SECURITY_ADMIN_PASSWORD` is the exception — it only takes effect on a
*fresh* `grafana-data` volume. On an existing one, also run:

```bash
docker exec grafana grafana cli admin reset-admin-password '<value>'
curl -u admin:<value> http://localhost:3001/api/org      # expect 200
```

**In-place:** change it through the SignalK admin UI, then:

```bash
git add <file>
git commit
```

The clean filter re-encrypts on the way in. If the same secret is also
mirrored in `secrets/symphony.sops.yaml` (like `influx_token`, which Grafana
needs as an env var — a second consumption path besides SignalK reading it
off disk), update both.

**Grafana / InfluxDB users:** edit the password in
```

**Issue:** Three completely different procedures (Layer 1, In-place, Grafana) run together without visual breaks.

### AFTER (proposed)
```markdown
## Rotating a secret

### Layer 1: stored values

```bash
sops secrets/symphony.sops.yaml          # edit the value, save
python3 scripts/render.py
docker compose up -d --force-recreate <service>
```

`GF_SECURITY_ADMIN_PASSWORD` is the exception — it only takes effect on a
*fresh* `grafana-data` volume. On an existing one, also run:

```bash
docker exec grafana grafana cli admin reset-admin-password '<value>'
curl -u admin:<value> http://localhost:3001/api/org      # expect 200
```

---

### In-place: plugin config files

Change it through the SignalK admin UI, then:

```bash
git add <file>
git commit
```

The clean filter re-encrypts on the way in. If the same secret is also
mirrored in `secrets/symphony.sops.yaml` (like `influx_token`, which Grafana
needs as an env var — a second consumption path besides SignalK reading it
off disk), update both.

---

### Grafana / InfluxDB users: passwords and roles

Edit the password in `secrets/symphony.sops.yaml`, then re-run the matching
provisioner — both converge password + role on every run, safe to re-run any time:
```

**Improvements:**
✅ Each procedure is visually distinct  
✅ Horizontal rules mark section transitions  
✅ Subheadings clarify what each procedure does  
✅ Easier to skim/find the right procedure  

---

## Example 3: Converting Warnings to Callout Blocks

### BEFORE (lines 483-484, current state)
```markdown
If that diff shows the URL in the clear, **stop**: the sops filter isn't
wired in this checkout. Run `bash scripts/setup-git-filters.sh` and
re-stage. This is not hypothetical — it was found unconfigured here on
2026-08-13, which is the state in which a secret gets committed in public.
```

**Issue:** Warning is just bold text, easily missed while reading.

### AFTER (proposed)
```markdown
> ⚠️ **Warning:** If the diff shows the URL in the clear, the sops filter isn't
> wired in this checkout. Run `bash scripts/setup-git-filters.sh` and re-stage
> the file immediately. **This is not hypothetical** — it was found unconfigured
> on 2026-08-13, which is the state in which a secret gets committed publicly.
```

---

### BEFORE (line 1988, current state)
```markdown
Never run `npm install` over a broken tree. npm treats a half-written package
directory as installed and skips it, so a second run repairs nothing. Move the
tree aside first:
```

**Issue:** "Never" advice is inline text, not visually emphasized.

### AFTER (proposed)
```markdown
> 🔴 **Critical:** Never run `npm install` over a broken tree. npm treats
> half-written package directories as installed and skips them, so a second
> run repairs nothing. Always move the tree aside first:
```

---

### BEFORE (lines 1590-1597, current state)
```markdown
### A fallback that has become the primary looks exactly like success

`signalk-fixed-position` (Position Keeper) stores the last known fix and
re-emits it once GPS has been quiet for its `interval`. That is wanted
behaviour — position-dependent plugins keep working through a GPS dropout.
The trap is that it looks identical to a working GPS: for a long time it was
the *only* position source on this boat, emitting a stored dock coordinate
about two metres from the truth, and nothing appeared broken.

So don't read "there is a position" as "the GPS works." Read `$source`.
```

**Issue:** The key insight (read $source, not just presence) is buried in the last paragraph.

### AFTER (proposed)
```markdown
### When a fallback has become the primary

`signalk-fixed-position` (Position Keeper) stores the last known fix and
re-emits it once GPS has been quiet for its `interval`. That is wanted
behaviour — position-dependent plugins keep working through a GPS dropout.

> 📌 **Gotcha:** This looks identical to a working GPS. The boat once emitted a
> stored dock coordinate two metres from truth, and nothing appeared broken
> because the position was there. **Don't read "position exists" as "GPS works" —
> always check the `$source` field to confirm the real GPS is active.**
```

**Improvements:**
✅ Key warning stands out visually  
✅ Shorter, punchier wording  
✅ Action is clear: "check $source"  
✅ Historic example backs up the warning  

---

## Example 4: Heading Standardization

### BEFORE (inconsistent depth and length)
```markdown
## Bringing up a host

### Phase 1 — Host and tooling

The host needs Docker (with compose v2)...

### Phase 2 — Key material

Get the age **private** key...

### Phase 3 — Repo and configuration

```bash
git clone ...
```

### Phase 4 — Services

```bash
docker compose up -d
```

### First-ever boot

If no `security.json` has ever existed...

### What `provision_influxdb.sh` does

It can mint credentials...
```

**Issue:** Subsections under a procedure (Phases 1-4) should be h4, not h3, to show hierarchy. "First-ever boot" and "What ... does" are at same level as phases, but are actually detail subsections.

### AFTER (proposed)
```markdown
## Bringing up a host

Four phases, in this order: tooling, key material, repo, services. Each ends
with a check — run it, because a failure in an early phase tends to surface
two phases later as something that looks unrelated.

#### Phase 1 — Host and tooling

The host needs Docker (with compose v2)...

#### Phase 2 — Key material

Get the age **private** key...

#### Phase 3 — Repo and configuration

```bash
git clone ...
```

#### Phase 4 — Services

```bash
docker compose up -d
```

### Special cases

#### First-ever boot

If no `security.json` has ever existed...

#### What `provision_influxdb.sh` does

It can mint credentials...
```

**Improvements:**
✅ h4 shows Phases are sub-steps of the overall procedure  
✅ "Special cases" grouping clarifies that "First-ever boot" and explanation sections aren't sequential phases  
✅ Readers can understand structure without reading every word  

---

## Summary of Changes by Type

| Type | Example | Benefit |
|------|---------|---------|
| **TOC Formatting** | Bullet list instead of dots | Better scannability, no line wrapping |
| **Visual Breaks** | `---` between procedures | Clear section boundaries |
| **Callout Blocks** | `> 🔴 **Critical:**` blockquotes | Warnings can't be missed |
| **Heading Depth** | h4 for sub-subsections | Visual hierarchy shows structure |
| **Heading Length** | Shorten long titles | Faster scanning |

