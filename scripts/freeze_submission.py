#!/usr/bin/env python3
"""Freeze a validated results version as the submission snapshot.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Record, immutably, everything needed to reproduce the submitted
         numbers: graph SHA-256, input snapshot hashes, evaluated model and
         relationship counts, RQ1-RQ5 output and macro hashes, code hashes,
         and the final reproduction status of every table and figure.
         The manuscript is never modified; differences from it are reported.

Command: python scripts/freeze_submission.py --label submission-2026-11-06 [--version <snapshot id>]
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vulchain_results as R  # noqa: E402
from validate_results import validate  # noqa: E402

RQ1_ENTRY_POINTS = (("tab:master_table", ["RQ1/rq1_table_01.py", "--view", "analytical"]),
                    ("tab:hub_agreement", ["RQ1/rq1_table_02.py"]),
                    ("fig:rq1", ["RQ1/rq1_figure_01.py"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--version", help="snapshot id (default: results/latest)")
    parser.add_argument("--config", type=Path, default=R.REPO / "configs" / "pipeline.local.json")
    args = parser.parse_args()

    cfg = R.load_config(args.config)
    results = cfg["results_dir"]
    version_dir = results / "versions" / args.version if args.version else (results / "latest").resolve()
    target = R.REPO / "freezes" / args.label
    if target.exists():
        print(f"Freeze {args.label} already exists; freezes are immutable.", file=sys.stderr)
        return 2

    record, checks, problems = validate(version_dir, cfg["release_dir"])
    if problems:
        print("Version is not valid; nothing frozen:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    graph_sha = R.v.sha(cfg["graph_dot"])
    if graph_sha != R.GRAPH_SHA256:
        print(f"Graph SHA-256 mismatch: {graph_sha}", file=sys.stderr)
        return 1

    rq1 = {}
    for label, cmd in RQ1_ENTRY_POINTS:
        run = subprocess.run([sys.executable, "-B", str(R.REPO / "experiments" / cmd[0]), *cmd[1:],
                              "--release-dir", str(cfg["release_dir"]), "--out", str(R.REPO / "outputs" / "RQ1")],
                             capture_output=True, text=True)
        rq1[label] = "PASS" if run.returncode == 0 else "FAIL"
    with (R.REPO / "REPRODUCIBILITY_MATRIX.csv").open(newline="") as handle:
        matrix = list(csv.DictReader(handle))

    target.mkdir(parents=True)
    shutil.copytree(version_dir / "outputs", target / "outputs")
    shutil.copy2(version_dir / "CHANGES.md", target / "CHANGES_AT_FREEZE.md")
    macros = {str(p.relative_to(R.REPO)): R.v.sha(p) for p in sorted((R.REPO / "data" / "manuscript_macros").glob("*.tex"))}
    try:
        commit = subprocess.run(["git", "-C", str(R.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    except OSError:
        commit = None
    freeze = {
        "label": args.label, "frozen_at_utc": R.now(), "graph_sha256": graph_sha,
        "results_version": record["snapshot_id"], "capture_cutoff_utc": record["cutoff_utc"],
        "input_manifest_sha256": record["input_manifest_sha256"],
        "input_files_sha256": json.loads((version_dir / "inputs" / "INPUT_MANIFEST.json").read_text())["files"],
        "counts": record["counts"], "output_sha256": record["output_sha256"],
        "manuscript_macro_sha256": macros, "code_sha256": R.code_versions(), "git_commit": commit,
        "validation": [{"check": c, "passed": ok} for c, ok, _ in checks],
        "rq1_entry_points": rq1,
        "artifact_status": {r["latex_label"]: r["status"] for r in matrix},
        "manuscript_modified": False,
    }
    R.write_json(target / "FREEZE_MANIFEST.json", freeze)
    for p in target.rglob("*"):
        if p.is_file():
            p.chmod(0o444)
    print(f"Frozen {record['snapshot_id']} as {target}")
    for label, status in freeze["artifact_status"].items():
        print(f"  {status:24} {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
