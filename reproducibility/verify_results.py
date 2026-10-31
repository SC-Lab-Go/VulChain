#!/usr/bin/env python3
"""Run every table/figure reproduction entry point and summarize the results.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: One command that re-runs all manuscript reproductions and prints a
         status per artifact. Entry points whose inputs are not in this
         repository are reported as PENDING rather than skipped silently.

Command: python reproducibility/verify_results.py --release-dir <extracted release archive>
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXP = REPO / "experiments"

# (artifact label, script, needs --release-dir, extra args)
ENTRY_POINTS = [
    ("tab:model_corpus", "setup/setup_table_01.py", False, []),
    ("tab:master_table (analytical)", "RQ1/rq1_table_01.py", True, ["--view", "analytical"]),
    ("tab:master_table (HuggingGraph v3 check)", "RQ1/rq1_table_01.py", True, ["--view", "released"]),
    ("tab:hub_agreement", "RQ1/rq1_table_02.py", True, []),
    ("fig:rq1", "RQ1/rq1_figure_01.py", False, []),
    ("tab:rqtworecurrence", "RQ2/rq2_table_01.py", False, []),
    ("tab:rq3", "RQ3/rq3_table_01.py", False, []),
    ("tab:rq4-adaptation-split", "RQ4/rq4_table_01.py", False, []),
    ("tab:rq5", "RQ5/rq5_table_01.py", "lineage", []),
]
NOT_REPRODUCIBLE_HERE = [
    ("tab:rq3nlc", "PENDING", "values are typed in the manuscript; generating code and control responses not located"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release-dir", type=Path, required=True,
                        help="extracted hugginggraph_v3_2026oct02_reproducibility directory")
    args = parser.parse_args()

    failures = 0
    for label, script, needs, extra in ENTRY_POINTS:
        cmd = [sys.executable, "-B", str(EXP / script), *extra]
        if needs is True:
            cmd += ["--release-dir", str(args.release_dir)]
        elif needs == "lineage":
            cmd += ["--lineage-csv", str(args.release_dir / "edges" / "csv" / "01_model_model_edges.csv")]
        result = subprocess.run(cmd, capture_output=True, text=True)
        status = "PASS" if result.returncode == 0 else "FAIL"
        failures += result.returncode != 0
        print(f"{status:24} {label:36} {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()[-300:]}")
    for label, status, reason in NOT_REPRODUCIBLE_HERE:
        print(f"{status:24} {label:36} {reason}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
