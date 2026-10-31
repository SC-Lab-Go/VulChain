#!/usr/bin/env python3
"""Reproduce Table tab:rqtworecurrence (RQ2).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "Impact of lineage-evidence admission on same-prompt security-failure
         recurrence" - Base / Tests / Class(%) / Inst.(%) for package
         hallucination and NXDOMAIN under the four cumulative evidence
         policies (Strict, Intermediate, Declared, Extended) and the three
         newly admitted strata.

Inputs:  data/rq_snapshot/canonical_comparisons.jsonl
Expected: data/manuscript_macros/rq2_numbers_codex.tex
Output:  outputs/RQ2/rq2_table_01_macros.tex, outputs/RQ2/rq2_table_01_verification.md
Command: python experiments/RQ2/rq2_table_01.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

TABLE_CODES = ("Pkg", "Nx")
TABLE_FIELDS = ("Upstreams", "Tests", "ClassRate", "InstanceRate")


def compute(comparisons):
    """RQ2 cells as in aggregate_all(): cumulative policy sets and their newly admitted strata."""
    m = v.Macros("rq2_table_01")
    previous = set()
    for policy in v.POLICIES:
        current = {r["membership_id_sha256"] for r in comparisons if r["in_" + policy]}
        v.require(previous <= current, "Non-nested policy pairs")
        for scope, ids in (("", current), ("Added", current - previous)):
            for cat, (code, _) in v.CATEGORIES.items():
                rows = [r for r in comparisons if r["membership_id_sha256"] in ids and r["category"] == cat]
                m.group("rqTwo" + v.TAGS[policy] + scope + code, v.summarize(rows))
        previous = current
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--snapshot", type=Path, default=v.DEFAULT_SNAPSHOT)
    parser.add_argument("--expected", type=Path, default=v.DEFAULT_EXPECTED)
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ2")
    args = parser.parse_args()

    v.snapshot_files(args.snapshot)
    m = compute(v.load_comparisons(args.snapshot))
    names = [f"rqTwo{v.TAGS[p]}{s}{c}{f}" for p in v.POLICIES for s in ("", "Added")
             for c in TABLE_CODES for f in TABLE_FIELDS if not (p == "strict" and s == "Added")]
    expected = v.manuscript_macros(args.expected, "rq2_numbers_codex.tex")
    rows, ok = v.compare(m.values, expected, names)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq2_table_01_macros.tex").write_bytes(m.text())
    return v.write_report(args.out / "rq2_table_01_verification.md",
                          "RQ2 Table tab:rqtworecurrence", rows, ok,
                          ["Strict has no 'newly added' row in the manuscript; its Added cells are not compared."])


if __name__ == "__main__":
    raise SystemExit(main())
