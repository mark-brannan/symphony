#!/usr/bin/env python3
"""Post or edit the single Discord message that tracks one boat-down outage.

The alarms channel is shared, so each outage gets one message, edited in place
as triage progresses. Its id lives on the GitHub issue as `<!-- discord:ID -->`.

Usage: discord_notify.py {opened,verdict,agent,recovered} --issue N --host H
         [--since ISO] [--text T | --body-file F] [--run-id R]
Env: SYMPHONY_DISCORD_ALARMING_WEBHOOK (absent: no-op), GH_TOKEN, GITHUB_REPOSITORY.
Never exits non-zero on Discord or gh failures: notification must not fail triage.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

WEBHOOK_RE = re.compile(r"^https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+$")
MARKER_RE = re.compile(r"<!-- discord:(\d+) -->")
UA = "DiscordBot (symphony-boat-triage, 1)"
COLORS = {"opened": 0xE74C3C, "verdict": 0xE67E22, "agent": 0xF1C40F, "recovered": 0x2ECC71}
MODEL = "claude-sonnet-5-5"


def lead_paragraph(text, cap=600):
    """First paragraph of the agent's write-up, minus the leading robot, capped with an ellipsis."""
    text = text.strip()
    if text.startswith("🤖"):
        text = text[1:].lstrip()
    para = re.split(r"\n\s*\n", text, maxsplit=1)[0].strip()
    return para if len(para) <= cap else para[: cap - 1].rstrip() + "…"


def duration(since, now):
    try:
        start = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "unknown"
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    mins = max(int((now - start).total_seconds() // 60), 0)
    days, rem = divmod(mins, 1440)
    hours, mins = divmod(rem, 60)
    return " ".join(p for p in (f"{days}d" if days else "", f"{hours}h" if hours else "", f"{mins}m" if mins or not (days or hours) else "") if p)


def render(event, host, issue, since, text, run_id, repo, now):
    """The webhook payload for one event: embed only, mentions disabled."""
    url = f"https://github.com/{repo}/issues/{issue}"
    embed = {"color": COLORS[event], "title": f"Symphony heartbeat down · {host}"}
    if event == "opened":
        embed["fields"] = [{"name": "Down since", "value": since or "unknown", "inline": True},
                           {"name": "Issue", "value": f"[#{issue}]({url})", "inline": True}]
        embed["footer"] = {"text": f"issue #{issue} · run {run_id}"}
    elif event == "verdict":
        embed["description"] = text
        embed["url"] = url
        embed["footer"] = {"text": f"issue #{issue} · rule-based first pass"}
    elif event == "agent":
        embed["description"] = f"{lead_paragraph(text)}\n\n[full write-up on the issue →]({url})"
        embed["url"] = url
        embed["footer"] = {"text": f"{MODEL} · agent triage"}
    else:
        embed["title"] = f"Recovered · {host}"
        embed["description"] = f"down {duration(since, now)}"
        embed["url"] = url
        embed["footer"] = {"text": f"issue #{issue} closed"}
    return {"embeds": [embed], "allowed_mentions": {"parse": []}}


def with_marker(body, message_id):
    marker = f"<!-- discord:{message_id} -->"
    if MARKER_RE.search(body):
        return MARKER_RE.sub(marker, body)
    return body.rstrip("\n") + f"\n{marker}\n"


def send(method, url, payload, urlopen):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method,
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    with urlopen(req, timeout=20) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def notify(args, env, urlopen, issue_body, set_issue_body, now):
    """Returns 0 always; problems print a ::warning:: (without the webhook URL)."""
    hook = env.get("SYMPHONY_DISCORD_ALARMING_WEBHOOK", "").strip()
    if not hook:
        print("discord: SYMPHONY_DISCORD_ALARMING_WEBHOOK not set; skipping")
        return 0
    if not WEBHOOK_RE.fullmatch(hook):
        print("::warning::discord: SYMPHONY_DISCORD_ALARMING_WEBHOOK is not a discord.com webhook URL; refusing")
        return 0
    payload = render(args.event, args.host, args.issue, args.since, args.text, args.run_id,
                     env.get("GITHUB_REPOSITORY", ""), now)
    try:
        body = issue_body()
        found = MARKER_RE.search(body)
        if found:
            try:
                send("PATCH", f"{hook}/messages/{found.group(1)}", payload, urlopen)
                print(f"discord: edited message for #{args.issue}")
                return 0
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                print("discord: message gone; posting a new one")
        message = send("POST", f"{hook}?wait=true", payload, urlopen)
        set_issue_body(with_marker(body, message["id"]))
        print(f"discord: posted message for #{args.issue}")
    except urllib.error.HTTPError as e:
        print(f"::warning::discord: HTTP {e.code} for event {args.event}")
    except Exception as e:  # network, gh, bad JSON: never fail the pipeline
        print(f"::warning::discord: {type(e).__name__} for event {args.event}")
    return 0


def _gh_io(issue, repo):
    def get():
        out = subprocess.run(["gh", "issue", "view", str(issue), "-R", repo, "--json", "body"],
                             check=True, capture_output=True, text=True).stdout
        return json.loads(out)["body"] or ""

    def put(body):
        subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}/issues/{issue}", "-f", f"body={body}"],
                       check=True, capture_output=True, text=True)
    return get, put


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("event", choices=sorted(COLORS))
    p.add_argument("--issue", type=int, required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--since", default="")
    p.add_argument("--text", default="")
    p.add_argument("--body-file")
    p.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = p.parse_args(argv)
    if args.body_file:
        try:
            with open(args.body_file, encoding="utf-8") as f:
                args.text = f.read()
        except OSError:
            print("::warning::discord: cannot read body file")
            return 0
    get, put = _gh_io(args.issue, os.environ.get("GITHUB_REPOSITORY", ""))
    return notify(args, os.environ, urllib.request.urlopen, get, put, datetime.now(timezone.utc))


if __name__ == "__main__":
    sys.exit(main())
