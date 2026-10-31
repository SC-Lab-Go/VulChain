#!/usr/bin/env python3
"""Reproduce Table tab:model_corpus (Experimental Setup).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "Text-generation one-hop derivative records across corpus
         identification, static readiness, and final cohort selection" -
         Base / Finetune / Adapter / Quantized / Merge / Total model IDs per stage.

Rows:
  1-hop der.    frozen Table II baseline (v2026.10.27-04), stage OneHop
  Static-ready  frozen Table II baseline, stage Ready
  Sel. cohort   evaluated relationships of the RQ2-RQ5 snapshot (\\Eval* macros)

Inputs:  data/table2_baseline/table2_stage_records.csv,
         data/rq_snapshot/evaluated_relationships.csv
Expected: data/manuscript_macros/{graph_cohort_numbers.tex, evaluated_cohort_numbers.tex}
Output:  outputs/setup/setup_table_01_verification.md
Command: python experiments/setup/setup_table_01.py
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402
import vulchain_table2 as t2  # noqa: E402

COLUMNS = ("Bases", "FT", "AD", "QT", "Merge", "UniqueModels")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baseline", type=Path, default=v.REPO / "data" / "table2_baseline")
    parser.add_argument("--snapshot", type=Path, default=v.DEFAULT_SNAPSHOT)
    parser.add_argument("--expected", type=Path, default=v.DEFAULT_EXPECTED)
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "setup")
    args = parser.parse_args()

    v.snapshot_files(args.snapshot)
    stages = {}
    with open(args.baseline / "table2_stage_records.csv", newline="") as handle:
        for r in csv.DictReader(handle):
            stages.setdefault(r["stage"], []).append((r["parent_id"], r["child_id"], r["adaptation_label"]))
    stages["Eval"] = [(r["parent_id"], r["child_id"], r["adaptation_label"])
                      for r in v.csv_rows(args.snapshot / "evaluated_relationships.csv")]
    computed = {}
    for stage, rows in stages.items():
        for key, value in t2.summarize(rows)["values"].items():
            computed[stage + key] = value
    computed["EvalTotal"] = computed["EvalUniqueModels"]

    expected = v.manuscript_macros(args.expected, "graph_cohort_numbers.tex", "evaluated_cohort_numbers.tex")
    names = [s + c for s in ("OneHop", "Ready", "Eval") for c in COLUMNS] + ["EvalTotal"]
    rows, ok = v.compare(computed, expected, names)
    return v.write_report(args.out / "setup_table_01_verification.md", "Setup Table tab:model_corpus", rows, ok,
                          ["1-hop and static-ready rows are typed in experiments.tex; they equal the OneHop*/Ready* macros compared here.",
                           "Sel. cohort is the evaluated cohort as of the 2026-10-30 snapshot (in-progress evaluation)."])


if __name__ == "__main__":
    raise SystemExit(main())
