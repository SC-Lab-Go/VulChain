#!/usr/bin/env python3
"""Reproduce Table tab:rq5 (RQ5).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "Heterogeneous supply-chain associations and security findings in
         the evaluated cohort" - Space/GitHub associations of evaluated
         models, instance-recurrent derivatives, shared canonical artifacts,
         and concentration of Space links among models with findings.

Inputs:  data/rq_snapshot/{canonical_comparisons.jsonl, qualified_occurrences.jsonl,
         evaluated_relationships.csv, evaluated_model_manifest.csv, model_status_audit.csv},
         data/rq_snapshot/rq5_graph_export/*,
         01_model_model_edges.csv from the graph release (--lineage-csv)
Expected: data/manuscript_macros/rq5_numbers_codex.tex
Output:  outputs/RQ5/rq5_table_01_macros.tex, outputs/RQ5/rq5_table_01_verification.md
Command: python experiments/RQ5/rq5_table_01.py --lineage-csv <release>/edges/csv/01_model_model_edges.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

LINEAGE_SHA256 = "78284f0119e44392d019788ef2268686cd93a4d9f143dc5e1091a46b1563eb47"


def table_macros(r):
    """The tab:rq5 subset of the production rq5_macros() assignments (unified_exports.py)."""
    fmt = lambda x: 'N/A' if x is None else f'{int(x):,}'  # noqa: E731 - as in rq5_macros
    num = lambda x: 'N/A' if x is None else (str(int(x)) if float(x).is_integer() else str(x))  # noqa: E731
    pct = lambda n, d: 'N/A' if not d else f'{100*n/d:.2f}'  # noqa: E731
    m = v.Macros("rq5_table_01")
    p = r['positive']
    m.put('rqfiveTopEdgeSharePct', pct(p['top_degree'] or 0, p['total_edges']))
    m.put('rqfiveExclTopSpaces', fmt((p['excl_top'] or {}).get('spaces')))
    for cat, C in v.RQ5_CATS.items():
        b = r['behavior'][cat]
        ir = b['instance_reach']
        sh = b['shared']
        m.put('rqfiveShared' + C, fmt(sh['shared']))
        m.put('rqfiveSharedSpace' + C, fmt(sh['reaching_space']))
        m.put('rqfiveEligDerivs' + C, len(b['eligible']))
        m.put('rqfiveSharedEmitCell' + C, 'N/A' if sh['emit_median'] is None
              else num(sh['emit_median']) + ' (' + fmt(sh['emit_max']) + ')')
        m.put('rqfiveRecDerivsCell' + C, len(b['instance_recurrent']) if b['eligible'] else 'N/A')
        m.put('rqfiveRecDerivsSpaceCell' + C, ir['models_with_space'] if b['eligible'] else 'N/A')
    x = r['eval']
    for k, val in [('Pairs', r['eval_pairs']), ('SpaceModels', x['models_with_space']), ('Spaces', x['spaces']),
                   ('SpaceOrGitModels', x['models_with_any_association']), ('GitRepos', x['repos_union'])]:
        m.put('rqfiveEval' + k, val)
    for k, val in [('ConcModels', p['models']), ('ConcSpaceModels', p['models_with_space']),
                   ('ConcEdges', p['total_edges']), ('ConcSpaces', p['spaces'])]:
        m.put('rqfive' + k, val)
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--snapshot", type=Path, default=v.DEFAULT_SNAPSHOT)
    parser.add_argument("--expected", type=Path, default=v.DEFAULT_EXPECTED)
    parser.add_argument("--lineage-csv", type=Path, required=True,
                        help="edges/csv/01_model_model_edges.csv from the v2026.10.02-07 graph release")
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ5")
    args = parser.parse_args()

    v.snapshot_files(args.snapshot)
    v.require(v.sha(args.lineage_csv) == LINEAGE_SHA256, "Lineage CSV is not the released 01_model_model_edges.csv")
    g, _sources = v.load_rq5_graph(args.snapshot / "rq5_graph_export", args.lineage_csv)
    r = v.rq5_compute(g, v.load_models(args.snapshot), v.load_pairs(args.snapshot),
                      v.load_comparisons(args.snapshot), v.load_occurrences(args.snapshot),
                      v.load_model_audit(args.snapshot))
    m = table_macros(r)
    expected = v.manuscript_macros(args.expected, "rq5_numbers_codex.tex")
    rows, ok = v.compare(m.values, expected, list(m.values))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq5_table_01_macros.tex").write_bytes(m.text())
    return v.write_report(args.out / "rq5_table_01_verification.md", "RQ5 Table tab:rq5", rows, ok)


if __name__ == "__main__":
    raise SystemExit(main())
