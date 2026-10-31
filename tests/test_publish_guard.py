"""Deadline-guard tests for automatic GitHub publication.

Created: 2026-10-30
Version: v2026.10.30-03
Purpose: Prove the 2026-11-11T22:00:00Z cutoff with an injected clock and
         throwaway local Git repositories. No network, no GitHub, and the
         system clock is never changed.

Command: python -m unittest tests.test_publish_guard -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import github_publish_guard as guard  # noqa: E402
import publish_github as pub  # noqa: E402

CUTOFF = datetime(2026, 11, 11, 22, 0, 0, tzinfo=timezone.utc)
NEEDS_RESULTS = unittest.skipUnless((REPO / "results" / "latest" / "RESULTS_MANIFEST.json").is_file(),
                                    "needs a validated local results/latest (live results pipeline)")
BEFORE = CUTOFF - timedelta(hours=2)


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Guard(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.state)

    def test_1_before_cutoff_allowed(self):
        guard.check("push", BEFORE, self.state)
        guard.check("push", CUTOFF - timedelta(microseconds=1), self.state)

    def test_2_exactly_at_cutoff_blocked(self):
        with self.assertRaises(guard.PublishingFrozen):
            guard.check("push", CUTOFF, self.state)

    def test_3_after_cutoff_blocked_and_status_text(self):
        with self.assertRaises(guard.PublishingFrozen) as ctx:
            guard.check("push", CUTOFF + timedelta(days=30), self.state)
        self.assertIn("GITHUB PUBLISHING FROZEN — DEADLINE REACHED", str(ctx.exception))

    def test_cutoff_is_utc_regardless_of_host_timezone(self):
        self.assertEqual(guard.HARD_CUTOFF_UTC.isoformat(), "2026-11-11T22:00:00+00:00")
        cst = timezone(timedelta(hours=-6))
        self.assertEqual(datetime(2026, 11, 11, 16, 0, tzinfo=cst), guard.HARD_CUTOFF_UTC)
        with mock.patch.dict(os.environ, {"TZ": "Asia/Tokyo"}):
            with self.assertRaises(guard.PublishingFrozen):
                guard.check("push", datetime(2026, 11, 12, 7, 0, tzinfo=timezone(timedelta(hours=9))), self.state)

    def test_7_schedules_cannot_bypass(self):
        # Configuration or environment cannot extend the cutoff ...
        with mock.patch.dict(os.environ, {"GITHUB_PUBLISH_CUTOFF_UTC": "2030-01-01T00:00:00Z"}):
            self.assertEqual(guard.effective_cutoff(), CUTOFF)
        # ... but can tighten it.
        with mock.patch.dict(os.environ, {"GITHUB_PUBLISH_CUTOFF_UTC": "2026-11-10T00:00:00Z"}):
            self.assertLess(guard.effective_cutoff(), CUTOFF)
        # Once frozen, a clock that moves backwards does not reopen publishing.
        self.assertTrue(guard.is_frozen(CUTOFF + timedelta(minutes=1), self.state))
        self.assertTrue(guard.is_frozen(BEFORE, self.state))
        # The command line offers no clock override.
        self.assertNotIn("argparse", (REPO / "scripts" / "github_publish_guard.py").read_text())

    def test_clock_rollback_before_freeze_is_ignored(self):
        guard.observed_now(CUTOFF + timedelta(seconds=5), self.state)
        with self.assertRaises(guard.PublishingFrozen):
            guard.check("push", BEFORE, self.state)


class Publication(unittest.TestCase):
    """End-to-end publication against a local bare repository standing in for GitHub."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "state"
        self.remote = self.tmp / "remote.git"
        self.clone = self.tmp / "clone"
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        sh("git", "clone", "-q", str(self.remote), str(self.clone))
        sh("git", "-C", str(self.clone), "config", "user.name", "Fixture")
        sh("git", "-C", str(self.clone), "config", "user.email", "fixture@example.invalid")
        sh("git", "-C", str(self.clone), "commit", "-q", "--allow-empty", "-m", "init")
        sh("git", "-C", str(self.clone), "push", "-q", "origin", "main")
        approved = self.tmp / "approved.txt"
        approved.write_text("README.md\n")
        self.settings = {"enabled": True, "clone_dir": str(self.clone), "remote": "origin", "branch": "main",
                         "approved_files": str(approved), "results_dir": "results", "min_window_minutes": 15}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def remote_head(self):
        return sh("git", "--git-dir", str(self.remote), "rev-parse", "main")

    @NEEDS_RESULTS
    def test_publishes_before_cutoff(self):
        status, commit = pub.publish(self.settings, clock=lambda: BEFORE, state_dir=self.state)
        self.assertEqual(status, "PUBLISHED")
        self.assertEqual(self.remote_head(), commit)
        message = sh("git", "--git-dir", str(self.remote), "log", "-1", "--format=%B")
        self.assertNotIn("Co-Authored-By", message)
        self.assertNotIn("Claude", message)
        self.assertTrue((self.state / "PUBLICATION_STATE.json").is_file())

    @NEEDS_RESULTS
    def test_6_unfinished_publication_not_completed_after_cutoff(self):
        times = iter([BEFORE, BEFORE, BEFORE, BEFORE, CUTOFF + timedelta(seconds=1)] + [CUTOFF + timedelta(minutes=5)] * 10)
        head = self.remote_head()
        status, detail = pub.publish(self.settings, clock=lambda: next(times), state_dir=self.state)
        self.assertEqual(status, "FROZEN")
        self.assertEqual(detail, guard.FROZEN_STATUS)
        self.assertEqual(self.remote_head(), head)

    def test_short_window_does_not_start(self):
        head = self.remote_head()
        status, _ = pub.publish(self.settings, clock=lambda: CUTOFF - timedelta(minutes=5), state_dir=self.state)
        self.assertEqual(status, "FROZEN")
        self.assertEqual(self.remote_head(), head)

    @NEEDS_RESULTS
    def test_8_and_10_no_retry_after_cutoff_and_last_version_kept(self):
        status, published = pub.publish(self.settings, clock=lambda: BEFORE, state_dir=self.state)
        self.assertEqual(status, "PUBLISHED")
        (self.clone / "README.md").write_text("local change that must never be pushed automatically\n")
        for minutes in (0, 1, 60, 60 * 24 * 365):
            status, _ = pub.publish(self.settings, clock=lambda: CUTOFF + timedelta(minutes=minutes), state_dir=self.state)
            self.assertEqual(status, "FROZEN")
        self.assertEqual(self.remote_head(), published)
        pending = json.loads((self.state / "PENDING_UNPUBLISHED.json").read_text())
        self.assertEqual(pending["pending_files"], ["README.md"])


class LocalResearchIndependence(unittest.TestCase):
    def test_9_research_code_never_imports_the_publisher(self):
        for path in list((REPO / "experiments").rglob("*.py")) + [REPO / "scripts" / "refresh_results.py",
                                                                  REPO / "scripts" / "validate_results.py",
                                                                  REPO / "scripts" / "freeze_submission.py"]:
            if path.is_file():
                text = path.read_text()
                self.assertNotIn("publish_github", text, path)
                self.assertNotIn("github_publish_guard", text, path)

    @unittest.skipUnless((REPO / "configs" / "pipeline.local.json").is_file(), "needs local pipeline configuration")
    def test_4_and_5_refresh_and_sync_wrapper_succeed_after_cutoff(self):
        state_home = Path(tempfile.mkdtemp())
        try:
            marker = state_home / "vulchain_publish" / "FROZEN"
            marker.parent.mkdir(parents=True)
            marker.write_text("test fixture: deadline already reached\n")
            env = dict(os.environ, XDG_STATE_HOME=str(state_home))
            result = subprocess.run(["bash", str(REPO / "scripts" / "vulchain_refresh_and_publish.sh")],
                                    capture_output=True, text=True, env=env, timeout=1800)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(guard.FROZEN_STATUS, result.stdout)
            self.assertIn("Latest validated snapshot", result.stdout)
            check = subprocess.run([sys.executable, "-B", str(REPO / "scripts" / "validate_results.py")],
                                   capture_output=True, text=True, env=env, timeout=1800)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        finally:
            shutil.rmtree(state_home)


if __name__ == "__main__":
    unittest.main()
