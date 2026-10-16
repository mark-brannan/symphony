#!/usr/bin/env python3
"""Turn a healthchecks.io outage into an open issue that stays open until recovery.

The check service alerts once, on the flip; this keeps the outage in front of
every session (an open `boat-down` issue) until the check is up again, and
names the issues it opened so the workflow can send an agent to triage them.

Env: HC_API_KEY (read-only key is enough), GH_TOKEN, GITHUB_REPOSITORY.
Writes `triage=<json list>` to $GITHUB_OUTPUT when set.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

API = "https://healthchecks.io/api/v3"
LABEL = "boat-down"


def host_of(check):
    """The tailnet host is a `symphony-*` tag on the check, so a card swap is a retag, not a code change."""
    return next((t for t in (check.get("tags") or "").split() if t.startswith("symphony-")), None)


def marker(key):
    return f"<!-- hc:{key} -->"


def plan(checks, open_issues):
    """Pure decision: which checks need an issue opened, which issues closed."""
    by_key = {}
    for issue in open_issues:
        for c in checks:
            if marker(c["unique_key"]) in issue["body"]:
                by_key[c["unique_key"]] = issue["number"]
    to_open, to_close = [], []
    for c in checks:
        if host_of(c) is None:
            continue
        issue = by_key.get(c["unique_key"])
        if c["status"] == "down" and issue is None:
            to_open.append(c)
        elif c["status"] != "down" and issue is not None:
            to_close.append((issue, c))
    return to_open, to_close


def hc(path):
    req = urllib.request.Request(API + path, headers={"X-Api-Key": os.environ["HC_API_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def down_since(check):
    flips = sorted(hc(f"/checks/{check['unique_key']}/flips/")["flips"], key=lambda f: f["timestamp"])
    downs = [f["timestamp"] for f in flips if not f["up"]]
    return downs[-1] if downs else check["last_ping"] or "unknown"


def notify(event, issue, host, since=""):
    """Best-effort Discord update; the notifier never raises, and a failure to launch it must not fail the watch."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord_notify.py")
    try:
        subprocess.run([sys.executable, script, event, "--issue", str(issue), "--host", host, "--since", since],
                       check=False, timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"::warning::discord notifier did not run: {type(e).__name__}")


def since_of(body):
    m = re.search(r"down since: (\S+)", body)
    return m.group(1) if m else ""


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    checks = hc("/checks/")["checks"]
    issues = json.loads(gh("issue", "list", "-R", repo, "--label", LABEL, "--state", "open",
                           "--json", "number,body", "--limit", "100"))
    to_open, to_close = plan(checks, issues)
    triage = []
    try:
        for c in to_open:
            host = host_of(c)
            since = down_since(c)
            body = (f"{marker(c['unique_key'])}\n"
                    f"healthchecks.io check **{c['name']}** is down.\n\n"
                    f"- host: `{host}`\n- down since: {since}\n- last ping: {c['last_ping']}\n\n"
                    "Closes itself when the check is up again.")
            url = gh("issue", "create", "-R", repo, "--label", LABEL,
                     "--title", f"{host} down since {since[:10]}", "--body", body).strip()
            triage.append({"issue": int(url.rsplit("/", 1)[1]), "host": host, "since": since})
            print(f"opened {url}")
            notify("opened", triage[-1]["issue"], host, since)
        bodies = {i["number"]: i["body"] for i in issues}
        for number, c in to_close:
            gh("issue", "close", str(number), "-R", repo, "--comment",
               f"Check is `{c['status']}` again (last ping {c['last_ping']}).")
            print(f"closed #{number} ({c['status']})")
            notify("recovered", number, host_of(c), since_of(bodies.get(number, "")))
    finally:
        # An issue opened before a later failure must still reach triage; the next run treats it as known.
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"triage={json.dumps(triage)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
