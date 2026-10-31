#!/usr/bin/env python3
"""Reproduce Table tab:rq4-adaptation-split (RQ4).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "Same-prompt failure recurrence by adaptation category under
         Declared" - Bases / Derivatives / Tests / Class / Instance for
         Adapter, Finetune (ndFT+dFT pooled), Quantized, Merge and Overall,
         for package hallucination and registrable NXDOMAIN.

Inputs:  data/rq_snapshot/canonical_comparisons.jsonl
Expected: data/manuscript_macros/rq4_numbers_codex.tex
Output:  outputs/RQ4/rq4_table_01_macros.tex, outputs/RQ4/rq4_table_01_verification.md
Command: python experiments/RQ4/rq4_table_01.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

GROUPS = ("Adapter", "Finetune", "Quantized", "Merged", "All")


def compute(comparisons):
    """RQ4 cells as in aggregate_all(), then the manuscript's legacy and Table VII names."""
    rq4 = {}
    for cat in v.CATEGORIES:
        admitted = [r for r in comparisons if r["category"] == cat and r["in_declared"]]
        rq4[cat] = {g: v.summarize([r for r in admitted if g == "Overall" or r["stratum"] == g])
                    for g in list(v.STRATA) + ["Overall"]}
    m = v.Macros("rq4_table_01")
    v.rq4_legacy_aliases(m, rq4)
    v.rq4_table_vii_macros(m, comparisons)
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--snapshot", type=Path, default=v.DEFAULT_SNAPSHOT)
    parser.add_argument("--expected", type=Path, default=v.DEFAULT_EXPECTED)
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ4")
    args = parser.parse_args()

    v.snapshot_files(args.snapshot)
    m = compute(v.load_comparisons(args.snapshot))
    names = []
    for code in ("Pkg", "Nx"):
        for g in GROUPS:
            names += [f"rqfourBases{code}{g}", f"rqfourAffected{code}{g}"]
            for level in ("Class", "Instance"):
                names += [f"rqfourK{code}{level}{g}", f"rqfourN{code}{level}{g}", f"rqfourRate{code}{level}{g}"]
    expected = v.manuscript_macros(args.expected, "rq4_numbers_codex.tex")
    rows, ok = v.compare(m.values, expected, names)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq4_table_01_macros.tex").write_bytes(m.text())
    return v.write_report(args.out / "rq4_table_01_verification.md",
                          "RQ4 Table tab:rq4-adaptation-split", rows, ok,
                          ["Derivatives column = rqfourAffected (derivatives with a class-level recurrence)."])


if __name__ == "__main__":
    raise SystemExit(main())
