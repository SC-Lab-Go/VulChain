#!/usr/bin/env python3
"""Central deadline guard for every automatic GitHub-writing operation.

Created: 2026-10-30
Version: v2026.10.30-03
Purpose: Allow automatic GitHub publication only before the hard cutoff
         2026-11-11T22:00:00Z (November 11, 2026, 4:00 PM America/Chicago).

Rules:
- The cutoff is a constant in this file. GITHUB_PUBLISH_CUTOFF_UTC (environment
  or configs/github_publish.json) can only move it EARLIER, never later.
- All comparisons use UTC; the host time zone is irrelevant.
- The guard keeps the latest UTC time it has observed and never trusts a clock
  that moves backwards.
- Once the cutoff is observed, a permanent FROZEN marker is written; no code
  path removes it.
- Callers check before starting and immediately before every remote operation,
  and bound in-flight operations with remaining_seconds().
- Only GitHub publication is gated. Local research workflows never call this.

A test clock can be injected only through the Python API (now=...); the
command-line interface has no clock override.

Command: python scripts/github_publish_guard.py status
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HARD_CUTOFF_UTC = datetime(2026, 11, 11, 22, 0, 0, tzinfo=timezone.utc)
FROZEN_STATUS = "GITHUB PUBLISHING FROZEN — DEADLINE REACHED"
REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "configs" / "github_publish.json"
DEFAULT_STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "vulchain_publish"


class PublishingFrozen(Exception):
    """Raised when a GitHub-writing operation is attempted at or after the cutoff."""


def _parse(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Cutoff must include a UTC offset: {value!r}")
    return dt.astimezone(timezone.utc)


def effective_cutoff():
    """Hard cutoff, tightened (never extended) by configuration or environment."""
    candidates = [HARD_CUTOFF_UTC]
    if CONFIG.is_file():
        value = json.loads(CONFIG.read_text()).get("GITHUB_PUBLISH_CUTOFF_UTC")
        if value:
            candidates.append(_parse(value))
    if os.environ.get("GITHUB_PUBLISH_CUTOFF_UTC"):
        candidates.append(_parse(os.environ["GITHUB_PUBLISH_CUTOFF_UTC"]))
    return min(candidates)


def _state(state_dir):
    path = Path(state_dir) / "guard_state.json"
    return path, (json.loads(path.read_text()) if path.is_file() else {})


def observed_now(now=None, state_dir=DEFAULT_STATE_DIR):
    """UTC now, never earlier than any time previously observed by the guard."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    path, state = _state(state_dir)
    seen = _parse(state["last_seen_utc"]) if state.get("last_seen_utc") else current
    current = max(current, seen)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_seen_utc"] = current.isoformat()
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    os.replace(tmp, path)
    return current


def is_frozen(now=None, state_dir=DEFAULT_STATE_DIR):
    marker = Path(state_dir) / "FROZEN"
    if marker.exists():
        return True
    current = observed_now(now, state_dir)
    if current >= effective_cutoff():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{FROZEN_STATUS}\nobserved_at_utc={current.isoformat()}\n"
                          f"cutoff_utc={effective_cutoff().isoformat()}\n")
        return True
    return False


def check(operation, now=None, state_dir=DEFAULT_STATE_DIR):
    """Raise PublishingFrozen unless `operation` may run now. Call before every GitHub write."""
    if is_frozen(now, state_dir):
        raise PublishingFrozen(f"{FROZEN_STATUS} (blocked: {operation})")


def remaining_seconds(now=None, state_dir=DEFAULT_STATE_DIR):
    if is_frozen(now, state_dir):
        return 0.0
    return (effective_cutoff() - observed_now(now, state_dir)).total_seconds()


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    if command not in ("status", "check"):
        print("usage: github_publish_guard.py [status|check]", file=sys.stderr)
        return 2
    frozen = is_frozen()
    print(f"cutoff_utc={effective_cutoff().isoformat()}")
    print(f"state_dir={DEFAULT_STATE_DIR}")
    if frozen:
        print(FROZEN_STATUS)
        return 0 if command == "status" else 3
    print(f"GITHUB PUBLISHING ALLOWED — {remaining_seconds() / 3600:.1f} h remaining")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
