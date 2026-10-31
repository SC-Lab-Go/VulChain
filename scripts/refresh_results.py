#!/usr/bin/env python3
"""Refresh RQ2-RQ5 results from the latest validated analysis snapshot.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Discover the newest analysis snapshot that the production pipeline
         has captured, validated and published; stage checksummed copies of
         its inputs; recompute every table macro with the repository's entry
         points; run numerical, denominator, population and consistency
         checks; and publish results/versions/<snapshot>/ plus an atomic
         results/latest pointer only if every check passes.

A failed or interrupted refresh never changes results/latest. Failed runs
are kept under results/failed/ for diagnosis. Re-running is safe: an
already-published snapshot is reported as up to date.

Command: python scripts/refresh_results.py [--config configs/pipeline.local.json]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import vulchain_results as R  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", type=Path, default=R.REPO / "configs" / "pipeline.local.json")
    parser.add_argument("--dry-run", action="store_true", help="validate but do not publish")
    args = parser.parse_args()

    cfg = R.load_config(args.config)
    results = cfg["results_dir"]
    results.mkdir(parents=True, exist_ok=True)
    lock = R.acquire_lock(results)
    try:
        for moved in R.recover_stale_staging(results):
            print(f"Recovered interrupted staging directory -> {moved}")
        snapshot_dir, info = R.discover(cfg["snapshot_root"])
        sid = info["snapshot_id"]
        print(f"Latest validated snapshot: {sid} (cutoff {info['cutoff_utc']})")
        if (results / "versions" / sid).exists() and not args.dry_run:
            print("Already published; results/latest is up to date.")
            return 0

        staging = results / f".staging-{sid}-{os.getpid()}"
        staging.mkdir()
        inputs = R.stage_inputs(snapshot_dir, info, cfg, staging)
        values, comparisons = R.compute(inputs, cfg["release_dir"] / "edges" / "csv" / "01_model_model_edges.csv")
        checks = R.run_checks(values, comparisons, inputs)
        passed = all(ok for _, ok, _ in checks)
        outputs = R.write_outputs(staging, values)
        previous = R.read_latest(results)
        record = dict(info, created_at_utc=R.now(), validation_passed=passed,
                      counts=R.summary_counts(values, comparisons, inputs),
                      checks=[{"check": c, "passed": ok, "detail": d} for c, ok, d in checks],
                      input_manifest_sha256=R.v.sha(inputs / "INPUT_MANIFEST.json"),
                      output_sha256=outputs, code_sha256=R.code_versions(),
                      previous_version=previous["snapshot_id"] if previous else None,
                      values={k: dict(m.values) for k, m in values.items()})
        (staging / "CHANGES.md").write_text(R.change_report(previous, record, values, R.REPO / "data" / "manuscript_macros"))
        R.write_json(staging / "RESULTS_MANIFEST.json", record)
        for c, ok, d in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {c}{'  (' + d + ')' if d else ''}")

        if not passed or args.dry_run:
            dest = results / "failed" / f"{sid}-{record['created_at_utc'].replace(':', '')}"
            dest.parent.mkdir(exist_ok=True)
            os.rename(staging, dest)
            print(("Dry run" if passed else "Validation FAILED") + f"; results/latest unchanged. Run kept at {dest}")
            return 0 if passed else 1
        target = R.publish(staging, results, sid)
        print(f"Published {target}; results/latest -> versions/{sid}")
        print(f"Change report: {target / 'CHANGES.md'}")
        return 0
    except R.PipelineError as exc:
        print(f"REFRESH ABORTED: {exc}. results/latest unchanged.", file=sys.stderr)
        for d in results.glob(f".staging-*-{os.getpid()}"):
            dest = results / "failed" / (d.name.lstrip(".") + "-aborted")
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(d), dest)
        return 2
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
