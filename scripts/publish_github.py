#!/usr/bin/env python3
"""Guarded, automatic GitHub publication of approved VulChain files.

Created: 2026-10-30
Version: v2026.10.30-03
Purpose: Copy approved repository files into a local clone of the public
         repository, then commit and push them - but only while
         github_publish_guard allows it (before 2026-11-11T22:00:00Z).

Safety rules:
- Disabled unless configs/github_publish.json has "enabled": true and names
  the clone, remote, branch and approved-file list.
- Checks the deadline guard at start and immediately before git add, commit,
  tag and push. The push runs with a timeout that ends before the cutoff.
- Starts only if at least min_window_minutes remain, so a publication either
  completes before the cutoff or does not happen.
- Publishes only when results/latest passed validation; never a partial snapshot.
- Uses the clone's existing Git identity; refuses if none is configured.
  Never adds AI co-author trailers. Tags only if "tag_approved" is true.
- No retry loop. After the cutoff it prints the frozen status, records pending
  local changes, and exits 0 so research workflows continue.

Command: python scripts/publish_github.py [--dry-run]
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import github_publish_guard as guard  # noqa: E402

REPO = guard.REPO
GRAPH_SHA256 = "25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97"


def git(clone, *args, timeout=None):
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True,
                          timeout=timeout, check=True).stdout.strip()


def load_settings(path):
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def record(state_dir, name, data):
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    (Path(state_dir) / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def statuses():
    path = REPO / "REPRODUCIBILITY_MATRIX.csv"
    if not path.is_file():
        return {}
    import csv
    with path.open(newline="") as handle:
        return {r["latex_label"]: r["status"] for r in csv.DictReader(handle)}


def pending_changes(settings):
    approved = [l.strip() for l in (REPO / settings["approved_files"]).read_text().splitlines()
                if l.strip() and not l.startswith("#")]
    clone = Path(settings["clone_dir"])
    changed = [p for p in approved if not (clone / p).is_file() or (REPO / p).read_bytes() != (clone / p).read_bytes()]
    return approved, changed


def publish(settings, dry_run=False, clock=lambda: None, state_dir=guard.DEFAULT_STATE_DIR, runner=git):
    """Return (status, detail). `clock`/`runner` are injectable for tests only (clock() -> UTC datetime or None)."""
    approved, changed = pending_changes(settings)
    try:
        guard.check("start publication", clock(), state_dir)
        remaining = guard.remaining_seconds(clock(), state_dir)
        if remaining < 60 * settings.get("min_window_minutes", 15):
            raise guard.PublishingFrozen(f"{guard.FROZEN_STATUS} (window too short: {remaining:.0f}s left)")
        latest = json.loads((REPO / settings.get("results_dir", "results") / "latest" / "RESULTS_MANIFEST.json").read_text())
        if not latest.get("validation_passed"):
            return "SKIPPED", "results/latest did not pass validation"
        if not changed:
            return "UP TO DATE", "no approved file differs from the published clone"
        clone = Path(settings["clone_dir"])
        if not runner(clone, "config", "user.email") or not runner(clone, "config", "user.name"):
            return "BLOCKED", "Git identity is not configured in the clone"
        if dry_run:
            return "DRY RUN", f"{len(changed)} approved file(s) would be published"
        for rel in changed:
            (clone / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, clone / rel)
        guard.check("git add", clock(), state_dir)
        runner(clone, "add", "--", *changed)
        guard.check("git commit", clock(), state_dir)
        message = (f"Update VulChain results ({latest['snapshot_id']})\n\n"
                   f"Snapshot cutoff: {latest['cutoff_utc']}\nGraph SHA-256: {GRAPH_SHA256}\n")
        runner(clone, "commit", "-m", message)
        commit = runner(clone, "rev-parse", "HEAD")
        if settings.get("tag_approved") and settings.get("tag"):
            guard.check("git tag", clock(), state_dir)
            runner(clone, "tag", settings["tag"])
        guard.check("git push", clock(), state_dir)
        budget = guard.remaining_seconds(clock(), state_dir) - 30
        if budget <= 0:
            raise guard.PublishingFrozen(f"{guard.FROZEN_STATUS} (no time left to push)")
        refs = [settings["branch"]] + ([settings["tag"]] if settings.get("tag_approved") and settings.get("tag") else [])
        runner(clone, "push", "--atomic", settings["remote"], *refs, timeout=budget)
        record(state_dir, "PUBLICATION_STATE.json", {
            "repository_url": runner(clone, "remote", "get-url", settings["remote"]),
            "final_published_commit": commit, "last_successful_push_utc": datetime.now(timezone.utc).isoformat(),
            "graph_sha256": GRAPH_SHA256, "latest_validated_snapshot": latest["snapshot_id"],
            "artifact_statuses": statuses(), "files_published": changed})
        return "PUBLISHED", commit
    except guard.PublishingFrozen as exc:
        record(state_dir, "PENDING_UNPUBLISHED.json", {
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "reason": str(exc),
            "pending_files": changed})
        return "FROZEN", guard.FROZEN_STATUS
    except subprocess.TimeoutExpired:
        return "ABORTED", "push did not finish before the cutoff; not retried"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--settings", type=Path, default=REPO / "configs" / "github_publish.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = load_settings(args.settings)
    if guard.is_frozen():
        print(guard.FROZEN_STATUS)
        return 0
    if not settings or not settings.get("enabled"):
        print("GITHUB PUBLISHING NOT ENABLED (configs/github_publish.json); nothing done")
        return 0
    status, detail = publish(settings, dry_run=args.dry_run)
    print(f"{status}: {detail}")
    return 1 if status in ("BLOCKED", "ABORTED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
