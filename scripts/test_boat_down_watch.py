#!/usr/bin/env python3
"""boat_down_watch.plan: one issue per outage, closed on recovery. Stdlib unittest."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boat_down_watch import marker, plan  # noqa: E402

PI = {"name": "SignalK Symphony", "unique_key": "pi", "status": "down", "last_ping": "t"}
HALOS = {"name": "SignalK Symphony (halos card)", "unique_key": "halos", "status": "up", "last_ping": "t"}


def issue(n, key):
    return {"number": n, "body": f"{marker(key)}\nbody"}


class Plan(unittest.TestCase):
    def test_down_without_issue_opens_one(self):
        self.assertEqual(plan([PI, HALOS], []), ([PI], []))

    def test_down_with_open_issue_does_nothing(self):
        self.assertEqual(plan([PI], [issue(7, "pi")]), ([], []))

    def test_recovered_closes_its_issue(self):
        self.assertEqual(plan([HALOS], [issue(9, "halos")]), ([], [(9, HALOS)]))

    def test_paused_counts_as_recovered(self):
        paused = dict(PI, status="paused")
        self.assertEqual(plan([paused], [issue(7, "pi")]), ([], [(7, paused)]))

    def test_unknown_check_is_ignored(self):
        other = dict(PI, name="something else", unique_key="x")
        self.assertEqual(plan([other], []), ([], []))


if __name__ == "__main__":
    unittest.main()
