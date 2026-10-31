#!/usr/bin/env python3
"""Reproduce Table tab:rq3 (RQ3).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "Same-prompt recurrence under Declared" - occurrences, distinct
         artifacts, tests, class-level and instance-level recurrence for
         package hallucination, NXDOMAIN, restricted namespace and exact
         malicious URL.

Inputs:  data/rq_snapshot/canonical_comparisons.jsonl,
         data/rq_snapshot/qualified_occurrences.jsonl
Expected: data/manuscript_macros/rq3_numbers_codex.tex
Output:  outputs/RQ3/rq3_table_01_macros.tex, outputs/RQ3/rq3_table_01_verification.md
Command: python experiments/RQ3/rq3_table_01.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

FIELDS = ("Occ", "Distinct", "Tests", "ClassRec", "ClassRate", "InstanceRec", "InstanceRate")


def compute(comparisons, occurrences):
    rq2 = {}
    for policy in v.POLICIES:
        rq2[policy] = {"cumulative": {cat: v.summarize([r for r in comparisons
                                                         if r["category"] == cat and r["in_" + policy]])
                                      for cat in v.CATEGORIES}}
    state = {"rq2": rq2, "rq3": rq2["declared"]["cumulative"],
             "occurrences": v.occurrence_counts(occurrences)}
    m = v.Macros("rq3_table_01")
    v.rq3_compatibility_aliases(m, state)
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--snapshot", type=Path, default=v.DEFAULT_SNAPSHOT)
    parser.add_argument("--expected", type=Path, default=v.DEFAULT_EXPECTED)
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ3")
    args = parser.parse_args()

    v.snapshot_files(args.snapshot)
    m = compute(v.load_comparisons(args.snapshot), v.load_occurrences(args.snapshot))
    names = [f"rqThree{code}{f}" for code in ("Pkg", "Nx", "Restricted") for f in FIELDS]
    names += ["rqThreeMalOcc", "rqThreeMalDistinct", "rqThreeMalTests"]
    expected = v.manuscript_macros(args.expected, "rq3_numbers_codex.tex")
    rows, ok = v.compare(m.values, expected, names)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq3_table_01_macros.tex").write_bytes(m.text())
    return v.write_report(args.out / "rq3_table_01_verification.md", "RQ3 Table tab:rq3", rows, ok,
                          ["The Reprod. column is computed in LaTeX as 100*InstanceRec/ClassRec."])


if __name__ == "__main__":
    raise SystemExit(main())
