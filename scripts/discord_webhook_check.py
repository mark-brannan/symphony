#!/usr/bin/env python3
"""Validate the alarms webhook and preview the outage message without running triage.

Usage: SYMPHONY_DISCORD_ALARMING_WEBHOOK=... scripts/discord_webhook_check.py [--preview | --post-sample [--keep]]
  (default)      shape check, then a read-only GET that names the webhook and channel
  --preview      print the four rendered payloads; needs no webhook
  --post-sample  post one TEST message, edit it through all four events, then delete it (--keep leaves it)
"""
import argparse
import json
import os
import sys
import urllib.error
from datetime import datetime, timedelta, timezone

import discord_notify as dn

HOST = "symphony-test"
SINCE = "2026-01-01T00:00:00Z"
AGENT_TEXT = "🤖 **Triage: sample write-up**\n\nThis is a sample first paragraph from the agent.\n\nSecond paragraph, not shown."


def payloads(now):
    texts = {"opened": "", "verdict": "Sample verdict: host is up and the heartbeat path looks healthy.",
             "agent": AGENT_TEXT, "recovered": ""}
    return {e: dn.render(e, HOST, 0, SINCE, texts[e], "sample", "mark-brannan/symphony", now) for e in dn.COLORS}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--preview", action="store_true")
    p.add_argument("--post-sample", action="store_true")
    p.add_argument("--keep", action="store_true")
    args = p.parse_args(argv)
    now = datetime.now(timezone.utc)
    if args.preview:
        for event, payload in payloads(now - timedelta(hours=2, minutes=5)).items():
            print(f"--- {event}\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
        return 0
    raw = os.environ.get("SYMPHONY_DISCORD_ALARMING_WEBHOOK", "")
    hook = raw.strip().strip("\"'").rstrip("/")
    if not hook:
        print("SYMPHONY_DISCORD_ALARMING_WEBHOOK is not set in this shell")
        return 1
    if not dn.WEBHOOK_RE.fullmatch(hook):
        print(f"shape: BAD ({dn.webhook_shape(hook)}); length {len(raw)}, stripped length {len(hook)}")
        return 1
    print("shape: ok")
    try:
        info = dn.send("GET", hook, None, dn.urllib.request.urlopen)
        print(f"discord: webhook '{info.get('name')}' -> channel {info.get('channel_id')}, guild {info.get('guild_id')}")
        if not args.post_sample:
            return 0
        sent = payloads(now - timedelta(hours=2, minutes=5))
        mid = dn.send("POST", f"{hook}?wait=true", sent["opened"], dn.urllib.request.urlopen)["id"]
        print(f"posted {mid}; editing through verdict, agent, recovered")
        for event in ("verdict", "agent", "recovered"):
            dn.send("PATCH", f"{hook}/messages/{mid}", sent[event], dn.urllib.request.urlopen)
        if not args.keep:
            dn.send("DELETE", f"{hook}/messages/{mid}", None, dn.urllib.request.urlopen)
            print("deleted the sample message")
    except urllib.error.HTTPError as e:
        print(f"discord: HTTP {e.code}" + (" (webhook deleted or token wrong)" if e.code in (401, 404) else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
