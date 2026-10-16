#!/usr/bin/env python3
"""discord_notify: embed rendering, message identity on the issue, failure modes. Stdlib unittest, no network."""
import argparse
import io
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from discord_notify import lead_paragraph, notify, render, with_marker  # noqa: E402

HOOK = "https://discord.com/api/webhooks/123/abc-DEF_9"
NOW = datetime(2026, 10, 3, 15, 30, tzinfo=timezone.utc)
REPO = "mark-brannan/symphony"
URL = f"https://github.com/{REPO}/issues/42"


def R(event, text="", since="2026-10-01T12:00:00+00:00"):
    return render(event, "symphony-pi", 42, since, text, "777", REPO, NOW)


class Render(unittest.TestCase):
    def test_opened(self):
        self.assertEqual(R("opened"), {
            "embeds": [{"color": 0xE74C3C, "title": "Symphony heartbeat down · symphony-pi",
                        "fields": [{"name": "Down since", "value": "2026-10-01T12:00:00+00:00", "inline": True},
                                   {"name": "Issue", "value": f"[#42]({URL})", "inline": True}],
                        "footer": {"text": "issue #42 · run 777"}}],
            "allowed_mentions": {"parse": []}})

    def test_verdict(self):
        self.assertEqual(R("verdict", "Host is dark.")["embeds"][0], {
            "color": 0xE67E22, "title": "Symphony heartbeat down · symphony-pi", "description": "Host is dark.",
            "url": URL, "footer": {"text": "issue #42 · rule-based first pass"}})

    def test_agent(self):
        self.assertEqual(R("agent", "🤖 Likely uplink.\n\nMore.")["embeds"][0], {
            "color": 0xF1C40F, "title": "Symphony heartbeat down · symphony-pi", "url": URL,
            "description": f"Likely uplink.\n\n[full write-up on the issue →]({URL})",
            "footer": {"text": "claude-sonnet-5-5 · agent triage"}})

    def test_recovered(self):
        self.assertEqual(R("recovered")["embeds"][0], {
            "color": 0x2ECC71, "title": "Recovered · symphony-pi", "description": "down 2d 3h 30m",
            "url": URL, "footer": {"text": "issue #42 closed"}})

    def test_recovered_unparseable_since(self):
        self.assertEqual(R("recovered", since="unknown")["embeds"][0]["description"], "down unknown")

    def test_no_content_key_and_no_mentions(self):
        for ev in ("opened", "verdict", "agent", "recovered"):
            p = R(ev, "@everyone hi")
            self.assertNotIn("content", p)
            self.assertEqual(p["allowed_mentions"], {"parse": []})


class Lead(unittest.TestCase):
    def test_strips_robot_and_stops_at_blank_line(self):
        self.assertEqual(lead_paragraph("🤖 One\ntwo\n\nthree"), "One\ntwo")

    def test_caps_at_600_with_ellipsis(self):
        out = lead_paragraph("x" * 900)
        self.assertEqual(len(out), 600)
        self.assertTrue(out.endswith("…"))

    def test_exactly_600_untouched(self):
        self.assertEqual(lead_paragraph("y" * 600), "y" * 600)


class Marker(unittest.TestCase):
    def test_appends_and_keeps_hc_marker(self):
        out = with_marker("<!-- hc:pi -->\nbody\n", "555")
        self.assertEqual(out, "<!-- hc:pi -->\nbody\n<!-- discord:555 -->\n")

    def test_replaces_stale_discord_marker_only(self):
        out = with_marker("<!-- hc:pi -->\n<!-- discord:1 -->\n", "2")
        self.assertEqual(out, "<!-- hc:pi -->\n<!-- discord:2 -->\n")


class Resp:
    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps(self.data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Fake:
    """Fake urlopen: replies come from a list of dicts or HTTP codes; every request is recorded."""
    def __init__(self, *replies):
        self.replies, self.reqs = list(replies), []

    def __call__(self, req, timeout=None):
        self.reqs.append((req.get_method(), req.full_url, json.loads(req.data)))
        r = self.replies.pop(0)
        if isinstance(r, int):
            raise urllib.error.HTTPError(req.full_url, r, "x", {}, io.BytesIO())
        return Resp(r)


def run(env, fake, body):
    args = argparse.Namespace(event="verdict", issue=42, host="symphony-pi", since="", text="v", run_id="1")
    saved = []
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = notify(args, dict(env, GITHUB_REPOSITORY=REPO), fake, lambda: body, saved.append, NOW)
    return rc, saved, buf.getvalue()


class Notify(unittest.TestCase):
    ENV = {"SYMPHONY_DISCORD_ALARMING_WEBHOOK": HOOK}

    def test_first_post_records_marker(self):
        fake = Fake({"id": "999"})
        rc, saved, _ = run(self.ENV, fake, "<!-- hc:pi -->\nb")
        self.assertEqual(rc, 0)
        self.assertEqual([(m, u) for m, u, _ in fake.reqs], [("POST", HOOK + "?wait=true")])
        self.assertEqual(saved, ["<!-- hc:pi -->\nb\n<!-- discord:999 -->\n"])

    def test_trailing_newline_in_secret_is_stripped(self):
        fake = Fake({"id": "999"})
        rc, _, _ = run({"SYMPHONY_DISCORD_ALARMING_WEBHOOK": HOOK + "\n"}, fake, "b")
        self.assertEqual(rc, 0)
        self.assertEqual([(m, u) for m, u, _ in fake.reqs], [("POST", HOOK + "?wait=true")])

    def test_later_event_patches_known_message(self):
        fake = Fake({})
        rc, saved, _ = run(self.ENV, fake, "b\n<!-- discord:999 -->\n")
        self.assertEqual([(m, u) for m, u, _ in fake.reqs], [("PATCH", HOOK + "/messages/999")])
        self.assertEqual(saved, [])

    def test_404_falls_back_to_post_and_rerecords(self):
        fake = Fake(404, {"id": "1000"})
        rc, saved, _ = run(self.ENV, fake, "b\n<!-- discord:999 -->\n")
        self.assertEqual([m for m, _, _ in fake.reqs], ["PATCH", "POST"])
        self.assertEqual(saved, ["b\n<!-- discord:1000 -->\n"])

    def test_no_secret_is_a_noop(self):
        fake = Fake()
        rc, saved, out = run({}, fake, "b")
        self.assertEqual((rc, fake.reqs, saved), (0, [], []))
        self.assertIn("not set", out)

    def test_bad_url_refused(self):
        for bad in ("http://discord.com/api/webhooks/1/a", "https://evil.example/api/webhooks/1/a",
                    "https://discord.com/api/webhooks/1/a?x=1", "https://discord.com.evil.io/api/webhooks/1/a"):
            fake = Fake()
            rc, _, out = run({"SYMPHONY_DISCORD_ALARMING_WEBHOOK": bad}, fake, "b")
            self.assertEqual((rc, fake.reqs), (0, []))
            self.assertNotIn(bad, out)

    def test_rejection_names_shape_not_secret(self):
        fake = Fake()
        bad = "https://example.org/hooks/123/" + "T" * 40 + "?x=1"
        rc, _, out = run({"SYMPHONY_DISCORD_ALARMING_WEBHOOK": bad}, fake, "b")
        self.assertIn("host=other", out)
        self.assertNotIn("example", out)
        self.assertIn("extras=query", out)
        self.assertNotIn("T" * 10, out)

    def test_common_paste_variants_accepted(self):
        for variant in ('"%s"' % HOOK, HOOK + "/", HOOK.replace("discord.com", "discordapp.com"),
                        HOOK.replace("https://discord.com/api", "https://ptb.discord.com/api/v10")):
            fake = Fake({"id": "9"})
            run({"SYMPHONY_DISCORD_ALARMING_WEBHOOK": variant}, fake, "b")
            self.assertEqual(len(fake.reqs), 1, variant)

    def test_http_error_warns_without_url_and_exits_zero(self):
        fake = Fake(500)
        rc, saved, out = run(self.ENV, fake, "b")
        self.assertEqual((rc, saved), (0, []))
        self.assertIn("::warning::", out)
        self.assertNotIn("abc-DEF", out)


if __name__ == "__main__":
    unittest.main()
