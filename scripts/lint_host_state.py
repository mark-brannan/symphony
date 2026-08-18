#!/usr/bin/env python3
"""Host-state lint rules. Run this ON the boat computer, not in CI.

Everything here needs the machine: compiled artifacts, installed files,
which units are enabled, which devices exist. CI has none of that, so
these rules would fail there for the wrong reason and get muted.

Repo-only rules live in scripts/lint_repo_hygiene.py.

Usage:  python3 scripts/lint_host_state.py
Exit:   0 clean or warnings only, 1 if something is actually wrong.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNALK = Path(os.environ.get("SIGNALK_NODE_CONFIG_DIR", Path.home() / ".signalk"))

failures: list[str] = []
warnings: list[str] = []


def fail(rule: str, msg: str) -> None:
    failures.append(f"{rule}: {msg}")


def warn(rule: str, msg: str) -> None:
    warnings.append(f"{rule}: {msg}")


def sh(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def rule_native_modules_are_built() -> None:
    """A package with binding.gyp and no .node never compiled.

    This is the cheapest possible read on a broken plugin tree. On
    2026-08-13 there were zero .node files across 1155 packages -- every
    native build had aborted on a missing @mapbox/node-pre-gyp -- and 29
    plugins were failing to start. Nobody was looking at the artifacts.

    It also catches the narrower case that survives a clean rebuild:
    better-sqlite3@7.6.2 cannot compile against Node 22 at all.
    """
    nm = SIGNALK / "node_modules"
    if not nm.is_dir():
        return
    gyp = [p.parent for p in nm.glob("*/binding.gyp")] + \
          [p.parent for p in nm.glob("@*/*/binding.gyp")]
    if not gyp:
        return
    unbuilt = [d for d in gyp if not any(d.rglob("*.node"))]
    total_built = sum(1 for _ in nm.rglob("*.node"))
    if total_built == 0 and gyp:
        fail("native-tree-unbuilt",
             f"{len(gyp)} package(s) declare binding.gyp and there is not a "
             f"single compiled .node under {nm}. The native toolchain is "
             f"broken, not one package. Check @mapbox/node-pre-gyp exists.")
        return
    for d in sorted(unbuilt):
        warn("native-module-unbuilt",
             f"{d.relative_to(nm)} has binding.gyp but no compiled .node -- "
             f"any plugin depending on it will fail to start")


def _install_specs() -> list[tuple[Path, Path]]:
    """Parse the INSTALL array out of host/install.sh (src:dest:mode:o:g)."""
    sh_file = ROOT / "host" / "install.sh"
    if not sh_file.exists():
        return []
    body = sh_file.read_text(encoding="utf-8")
    m = re.search(r"^INSTALL=\((.*?)^\)", body, re.S | re.M)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip().strip('"')
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            out.append((ROOT / "host" / parts[0], Path(parts[1])))
    return out


def rule_installed_files_match_repo() -> None:
    """Drift between host/ and what is installed is a silent revert.

    host/systemd-watchdog.conf said RuntimeWatchdogSec=15 while the host ran
    30: the next `sudo host/install.sh` would have quietly put the watchdog
    back to 15s. The installer is idempotent, which is exactly what makes
    the drift dangerous -- it wins without saying anything.
    """
    for src, dest in _install_specs():
        if not src.exists() or not dest.exists():
            continue
        try:
            a = src.read_bytes()
            b = dest.read_bytes()
        except PermissionError:
            warn("install-drift-unreadable", f"cannot read {dest} (try sudo)")
            continue
        if a != b:
            fail("install-drift",
                 f"{dest} differs from {src.relative_to(ROOT)}. "
                 f"`sudo host/install.sh` would overwrite the host copy.")


def _compose_published_ports() -> dict[int, str]:
    """Host ports published by compose files, mapped to service name."""
    ports: dict[int, str] = {}
    for f in sorted(ROOT.glob("compose*.y*ml")) + sorted(ROOT.glob("docker-compose.y*ml")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        service = None
        for line in text.splitlines():
            sm = re.match(r"^  (\w[\w.-]*):\s*$", line)
            if sm:
                service = sm.group(1)
            pm = re.search(r'^\s*-\s*"?(?:[\d.]+:)?(\d+):\d+"?\s*$', line)
            if pm and service:
                ports[int(pm.group(1))] = service
    return ports


def rule_no_enabled_unit_shadows_a_container() -> None:
    """A native unit and a container cannot both own a port at boot.

    Containerising dex left the native dex.service still `enabled`; on the
    next reboot it would have raced the container for 5556 and one of them
    would have failed, intermittently and after a reboot -- the worst time
    to find out.
    """
    ports = _compose_published_ports()
    if not ports:
        return
    # A port declared in a compose file is not a conflict on its own -- most
    # of these services have not been migrated yet. The conflict is real only
    # once a container for that service actually exists, because then both
    # things start at boot. Checking `docker ps -a` rather than the compose
    # file is the difference between this rule finding the dex race and it
    # reporting every unmigrated service forever.
    existing = set(sh("docker", "ps", "-a", "--format", "{{.Names}}").split())
    if not existing:
        return
    for port, service in sorted(ports.items()):
        if service not in existing:
            continue
        if sh("systemctl", "is-enabled", service) == "enabled":
            fail("unit-shadows-container",
                 f"systemd unit '{service}' is enabled and container "
                 f"'{service}' exists, both claiming host port {port}. They "
                 f"will race at boot. Disable the unit if the container owns it.")


def rule_configs_reference_things_that_exist() -> None:
    """Config naming an absent device or plugin is a claim that isn't true.

    gpsd was configured for /dev/ttyOP_gps, which does not exist, and that
    single stale line supported a written conclusion that the boat had no
    GNSS at all -- while a GPS sat publishing on NMEA 2000.
    """
    gpsd = Path("/etc/default/gpsd")
    if gpsd.exists():
        for line in gpsd.read_text(encoding="utf-8").splitlines():
            m = re.match(r'\s*DEVICES="([^"]*)"', line)
            if m and m.group(1).strip():
                for dev in m.group(1).split():
                    if not Path(dev).exists():
                        fail("absent-device",
                             f"/etc/default/gpsd names {dev}, which does not "
                             f"exist. gpsd will publish nothing.")

    # Plugin ids come from the running server, not guessed from package names.
    cfg_dir = SIGNALK / "plugin-config-data"
    if not cfg_dir.is_dir():
        return
    try:
        with urllib.request.urlopen(
            "http://localhost:3000/skServer/plugins", timeout=10
        ) as r:
            live = {p.get("id") for p in json.load(r)}
    except Exception:
        warn("plugin-list-unavailable",
             "could not read /skServer/plugins; skipped the orphan-config "
             "check (server down, or it needs auth)")
        return
    for cfg in sorted(cfg_dir.glob("*.json")):
        if cfg.stem in live:
            continue
        try:
            enabled = json.loads(cfg.read_text(encoding="utf-8")).get("enabled")
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        if enabled:
            fail("orphan-plugin-config",
                 f"{cfg.name} is enabled but '{cfg.stem}' is not a plugin this "
                 f"server has. Nothing is acting on it.")


def rule_no_unexpanded_placeholders() -> None:
    """SignalK reads a '{{ ntfy_url }}' left in live config as the literal URL.

    A hostvars-covered file holds a placeholder on disk only when a checkout
    ran without the filter wired or without hostvars.local.yaml -- and the
    plugin doesn't fail until its next restart, which can be days after the
    pull that caused it. Catch it while the cause is still recent.
    """
    cfg_dir = SIGNALK / "plugin-config-data"
    if not cfg_dir.is_dir():
        return
    for cfg in sorted(cfg_dir.glob("*.json")):
        try:
            text = cfg.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name in re.findall(r'"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}"', text):
            fail("unexpanded-placeholder",
                 f"{cfg.name} holds '{{{{ {name} }}}}' as a live value. SignalK "
                 f"will read it literally at the plugin's next start. Set the "
                 f"value in hostvars.local.yaml, run scripts/hostvars_filter.py "
                 f"refresh, and restart signalk.")


def main() -> int:
    for rule in (
        rule_native_modules_are_built,
        rule_installed_files_match_repo,
        rule_no_enabled_unit_shadows_a_container,
        rule_configs_reference_things_that_exist,
        rule_no_unexpanded_placeholders,
    ):
        try:
            rule()
        except Exception as e:  # a broken check must not mask a broken boat
            warn("check-crashed", f"{rule.__name__}: {e!r}")

    for w in warnings:
        print(f"  warn  {w}")
    for f in failures:
        print(f"  FAIL  {f}")
    if not failures and not warnings:
        print("host state: ok")
    elif not failures:
        print(f"\n{len(warnings)} warning(s), nothing fatal.")
    else:
        print(f"\n{len(failures)} problem(s), {len(warnings)} warning(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
