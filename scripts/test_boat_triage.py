#!/usr/bin/env python3
"""boat_triage.sh --classify: each diagnostics log gets the verdict its first matching rule names. Stdlib unittest."""
import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boat_triage.sh")

HEALTHY = """## tailscale status
100.64.0.7  symphony-pi  pi@  linux  -
## tailscale ping
pong from symphony-pi (100.64.0.7) via DERP(nyc) in 80ms
## on host
 12:00:01 up 3 days,  2:10,  0 users,  load average: 0.40, 0.35, 0.30
  UNIT LOAD ACTIVE SUB DESCRIPTION
0 loaded units listed.
               total        used        free      shared  buff/cache   available
Mem:            1906         900         300          20         700        1006
Swap:            511          10         501
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p2   29G   12G   16G  43% /
timer: active
service: active
healthchecks.io HTTP 200
"""


def classify(log):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(log)
    try:
        return subprocess.run(["bash", SCRIPT, "--classify", f.name], capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(f.name)


class Classify(unittest.TestCase):
    def test_healthy_says_outage_may_have_cleared(self):
        self.assertIn("may already have cleared", classify(HEALTHY))

    def test_no_answer_on_tailnet(self):
        log = "## tailscale ping\nno reply\n## on host\nssh failed: exit 255\n"
        self.assertIn("does not answer on the tailnet", classify(log))

    def test_ping_without_ssh_blames_sshd(self):
        log = "## tailscale ping\npong from symphony-pi\n## on host\nssh failed: exit 124\n"
        self.assertIn("ssh fails", classify(log))

    def test_uplink_down(self):
        self.assertIn("cannot reach healthchecks.io", classify(HEALTHY.replace("HTTP 200", "HTTP 000")))

    def test_server_error_counts_as_uplink(self):
        self.assertIn("cannot reach healthchecks.io", classify(HEALTHY.replace("HTTP 200", "HTTP 503")))

    def test_redirect_is_not_an_outage(self):
        self.assertIn("may already have cleared", classify(HEALTHY.replace("HTTP 200", "HTTP 301")))

    def test_heartbeat_timer_inactive(self):
        self.assertIn("heartbeat timer/service is not running", classify(HEALTHY.replace("timer: active", "timer: inactive")))

    def test_heartbeat_service_failed(self):
        self.assertIn("heartbeat timer/service is not running", classify(HEALTHY.replace("service: active", "service: failed")))

    def test_low_memory(self):
        self.assertIn("under 400 MB", classify(HEALTHY.replace("700        1006", "700         350")))

    def test_other_failed_units(self):
        self.assertIn("other units have failed", classify(HEALTHY.replace("0 loaded units", "2 loaded units")))

    def test_ssh_failure_outranks_everything_else(self):
        log = HEALTHY.replace("timer: active", "timer: failed") + "ssh failed: exit 255\n"
        self.assertIn("ssh fails", classify(log))


if __name__ == "__main__":
    unittest.main()
