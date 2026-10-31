#!/usr/bin/env python3
"""Re-validate a published results version.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Check that a version under results/versions/ is intact and
         reproducible: every input and output matches its recorded SHA-256,
         recomputing from the stored inputs gives the stored values, and all
         consistency checks still pass.

Command: python scripts/validate_results.py [--version <snapshot id>] [--config configs/pipeline.local.json]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import vulchain_results as R  # noqa: E402


def validate(version_dir, release_dir):
    problems = []
    record = json.loads((version_dir / "RESULTS_MANIFEST.json").read_text())
    inputs = version_dir / "inputs"
    manifest = json.loads((inputs / "INPUT_MANIFEST.json").read_text())
    if R.v.sha(inputs / "INPUT_MANIFEST.json") != record["input_manifest_sha256"]:
        problems.append("INPUT_MANIFEST.json changed")
    problems += [f"input changed: {n}" for n, h in manifest["files"].items() if R.v.sha(inputs / n) != h]
    problems += [f"output changed: {n}" for n, h in record["output_sha256"].items() if R.v.sha(version_dir / n) != h]
    values, comparisons = R.compute(inputs, release_dir / "edges" / "csv" / "01_model_model_edges.csv")
    recomputed = {k: dict(m.values) for k, m in values.items()}
    diffs = R.diff_values(record["values"], recomputed)
    problems += [f"value differs on recomputation: {k} {a} -> {b}" for k, a, b in diffs[:20]]
    checks = R.run_checks(values, comparisons, inputs)
    problems += [f"check failed: {c} ({d})" for c, ok, d in checks if not ok]
    return record, checks, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", type=Path, default=R.REPO / "configs" / "pipeline.local.json")
    parser.add_argument("--version", help="snapshot id under results/versions (default: results/latest)")
    args = parser.parse_args()
    cfg = R.load_config(args.config)
    results = cfg["results_dir"]
    version_dir = results / "versions" / args.version if args.version else (results / "latest").resolve()
    if not (version_dir / "RESULTS_MANIFEST.json").is_file():
        print(f"No published version at {version_dir}", file=sys.stderr)
        return 2
    record, checks, problems = validate(version_dir, cfg["release_dir"])
    print(f"Version {record['snapshot_id']} (cutoff {record['cutoff_utc']})")
    for c, ok, d in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {c}")
    for p in problems:
        print(f"FAIL  {p}")
    print("VALID" if not problems else f"INVALID ({len(problems)} problem(s))")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
