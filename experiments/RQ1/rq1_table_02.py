#!/usr/bin/env python3
"""Reproduce Table tab:hub_agreement (RQ1).

Created: 2026-10-30
Version: v2026.10.30-04 (replaces v2026.10.30-01, which re-derived only the
         interval arithmetic from recorded counts; backup beside this file)
Purpose: "VulChain lineage edges and Hub model-tree agreement" - the '# Edges'
         column and the Hub-reference columns (# Pairs, # Recovered,
         Recall (%) [CI], Match (%)).

Reference set. This is the historical exact-ID reference: the Hub model-tree
index queried for the first 200,000 models of the 2026-08-28 delta inventory
(5,222 of them have Hub derivatives; 15,689 pairs). It is a deterministic
prefix, not a random sample. The 2027 probability-sample evaluation (6,816
upstreams) is a separate, unfinished experiment and is not used here.

How each column is computed (code in experiments/production/graph_server_rq1/,
each file hash-checked against its SOURCE_MANIFEST.json before use):
  # Edges        edge_type counts in the released Model->Model edge file.
  # Pairs, # Recovered, Total Match
                 the original evaluator, hub_agreement/historical_first200k/
                 evaluator/eval_hf_tree_recall.py, run unchanged; its
                 label_confusion.csv must be byte-identical and metrics.json
                 value-identical to the archived published output.
  Recall CI      per-adaptation 95% Wilson score intervals, as printed in the
                 manuscript, and the cluster-robust intervals, both computed by
                 executing the original statements of selection_audit/scripts/
                 audit_selection.py (lines listed in AUDIT_LINES) on the public
                 inputs. Their values must equal the archived selection_audit.json.
  Match (%)      recovered pairs whose released label set contains the Hub
                 label. Counted from the audit's own `exact` set (adapter code,
                 below) and cross-checked against the evaluator's confusion matrix.

Inputs:  --release-dir: edges/csv/01_model_model_edges.csv of release v2026.10.02-07
         experiments/production/graph_server_rq1/hub_agreement/historical_first200k/reference/
         --evidence (optional): model_lineage_edges_merged.csv, for the evaluator's
                    informational matched_pairs_by_evidence field
Output:  outputs/RQ1/rq1_table_02.csv, outputs/RQ1/rq1_table_02_verification.md
Command: python experiments/RQ1/rq1_table_02.py --release-dir <extracted release archive> [--evidence <csv>]
"""

import argparse
import csv
import filecmp
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

PKG = v.REPO / "experiments" / "production" / "graph_server_rq1"
HUB = "hub_agreement/historical_first200k"
EVALUATOR = f"{HUB}/evaluator/eval_hf_tree_recall.py"
AUDIT = f"{HUB}/selection_audit/scripts/audit_selection.py"
# Original audit_selection.py statements executed below (1-based, inclusive):
AUDIT_LINES = ((232, 233),   # queried sources (completed list)
               (283, 293),   # reference triples and pair labels
               (322, 325),   # released Model->Model pair labels
               (332, 333),   # recovered and exact-label pairs
               (544, 556))   # per-adaptation Wilson and cluster-robust intervals
ORDER = ("Fine-tune", "Adapter", "Quantized", "Merge")
HUB_LABEL = {"Fine-tune": "finetune", "Adapter": "adapter", "Quantized": "quantized", "Merge": "merged"}

# Values printed in the manuscript (experiments.tex, \label{tab:hub_agreement}); compared, never emitted.
EDGES = {"finetune": 710010, "adapter": 131430, "quantized": 66064, "merged": 53498,
         "others": 5033, "total": 966035}
MANUSCRIPT_HUB = {  # label: (# Pairs, # Recovered, "Recall (%) [CI]", match count, "Match (%)")
    "Fine-tune": (3466, 3209, "92.6 [91.7, 93.4]", 3088, "96.2"),
    "Adapter": (1350, 1280, "94.8 [93.5, 95.9]", 1055, "82.4"),
    "Quantized": (9284, 8800, "94.8 [94.3, 95.2]", 1814, "20.6"),
    "Merge": (1589, 1379, "86.8 [85.0, 88.4]", 1379, "100"),
    "Total": (15689, 14668, "93.5 [93.1, 93.9]", 7336, "50"),
}
CAPTION_UPSTREAMS = 111816  # caption: "(111,816 upstream models)"


def production_path(relpath):
    manifest = {f["path"]: f for f in json.loads((PKG / "SOURCE_MANIFEST.json").read_text())["files"]}
    path = PKG / relpath
    v.require(v.sha(path) == manifest[relpath]["published_sha256"], "Production source changed: " + relpath)
    return path


def pct(x):
    """Manuscript style: one decimal, trailing '.0' dropped (e.g. 100, 50)."""
    text = f"{100 * x:.1f}"
    return text[:-2] if text.endswith(".0") else text


def run_audit_statements(reference, completed, family01):
    """Execute the listed original audit_selection.py statements on the public inputs."""
    path = production_path(AUDIT)
    spec = importlib.util.spec_from_file_location("audit_selection", path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)  # defines helpers and constants only; main() is not run
    lines = path.read_text().splitlines(keepends=True)
    code = textwrap.dedent("".join("".join(lines[a - 1:b]) for a, b in AUDIT_LINES))
    ns = dict(vars(audit))
    ns.update(INPUTS={"completed": completed, "reference": reference, "family01": family01}, strata={})
    exec(compile(code, str(path), "exec"), ns)  # noqa: S102 - hash-checked original source
    return ns


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, help="model_lineage_edges_merged.csv (optional)")
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ1")
    args = parser.parse_args()

    family01 = args.release_dir / "edges" / "csv" / "01_model_model_edges.csv"
    reference = PKG / HUB / "reference" / "graph_model_model_first_200k.csv"
    completed = PKG / HUB / "reference" / "graph_model_model_first_200k.csv.completed.txt"
    for p in (reference, completed):
        production_path(str(p.relative_to(PKG)))
    published = PKG / HUB / "published_output"
    rows, ok, notes = [], True, []

    def check(name, got, want):
        nonlocal ok
        ok &= got == want
        fmt = lambda x: f"{x:,}" if isinstance(x, int) and not isinstance(x, bool) else str(x)  # noqa: E731
        rows.append((name, fmt(got), fmt(want), "MATCH" if got == want else "MISMATCH"))

    # '# Edges' column
    counts, sources = Counter(), set()
    with family01.open(newline="") as handle:
        for row in csv.DictReader(handle):
            counts[row["edge_type"]] += 1
            sources.add(row["source"])
    got = {k: counts[k] for k in ("finetune", "adapter", "quantized", "merged")}
    got["others"] = counts["converted"] + counts["new_version"]
    got["total"] = sum(counts.values())
    for k, want in EDGES.items():
        check(f"# Edges {k}", got[k], want)

    # original evaluator, unchanged
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "eval"
        cmd = [sys.executable, "-B", str(production_path(EVALUATOR)), "--reference", str(reference),
               "--completed", str(completed), "--released", str(family01), "--out-dir", str(out)]
        if args.evidence:
            cmd += ["--evidence", str(args.evidence)]
        run = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED="0"))
        v.require(run.returncode == 0, "Evaluator failed: " + run.stderr[-300:])
        check("evaluator label_confusion.csv byte-identical to published",
              filecmp.cmp(out / "label_confusion.csv", published / "label_confusion.csv", shallow=False), True)
        metrics = json.loads((out / "metrics.json").read_text())
        expected = json.loads((published / "metrics.json").read_text())
        if not args.evidence:
            expected.pop("matched_pairs_by_evidence")
            notes.append("Run without --evidence: metrics.json compared without the informational "
                         "matched_pairs_by_evidence field.")
        check("evaluator metrics.json value-identical to published", metrics == expected, True)
        confusion = list(csv.DictReader((out / "label_confusion.csv").open(newline="")))

    # original audit statements: per-adaptation counts and intervals
    ns = run_audit_statements(reference, completed, family01)
    strata = ns["strata"]["adaptation_category"]
    archived = json.loads((PKG / HUB / "selection_audit" / "outputs" / "selection_audit.json").read_text())
    # Integers must be equal; floats to 1e-12 relative. The archived run used Python 3.10;
    # Python >= 3.12 sums floats with compensated summation, which changes the last bits.
    stored = archived["statistics"]["strata"]["adaptation_category"]
    same = stored.keys() == strata.keys() and all(
        stored[c].keys() == strata[c].keys() and all(
            strata[c][f] == stored[c][f] if isinstance(stored[c][f], int)
            else abs(strata[c][f] - stored[c][f]) <= 1e-12 * abs(stored[c][f]) for f in stored[c])
        for c in stored)
    check("audit strata equal archived selection_audit.json", same, True)
    # adapter: label-match counts per adaptation from the audit's `exact` set
    match = Counter(ns["ref_label"][p] for p in ns["exact"])
    for name in ORDER:
        lab = HUB_LABEL[name]
        from_confusion = sum(int(r["count"]) for r in confusion
                             if r["reference_label"] == lab and lab in r["released_label"].split("+"))
        v.require(match[lab] == from_confusion, f"Label-match cross-check failed for {name}")

    table = []
    for name in ORDER + ("Total",):
        if name == "Total":
            n, k = len(ns["ref_labels"]), len(ns["recovered"])
            w = ns["wilson"](k, n)
            m = len(ns["exact"])
            lo, hi, clo, chi = w["lo"], w["hi"], None, None
        else:
            s = strata[name]
            n, k, m = s["pairs"], s["recovered"], match[HUB_LABEL[name]]
            lo, hi, clo, chi = s["wilson_lo"], s["wilson_hi"], s["clustered_lo"], s["clustered_hi"]
        recall = f"{100 * k / n:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]"
        pairs, rec, want_recall, want_m, want_mp = MANUSCRIPT_HUB[name]
        check(f"{name} # Pairs", n, pairs)
        check(f"{name} # Recovered", k, rec)
        check(f"{name} Recall (%) [Wilson 95% CI]", recall, want_recall)
        check(f"{name} Match count", m, want_m)
        check(f"{name} Match (%)", pct(m / k), want_mp)
        table.append([name, n, k, k / n, lo, hi, clo, chi, m, m / k])

    # caption and clustered-interval notes (informational, not counted)
    upstreams = len({ns["untyped"](s) for s in sources})
    with_derivatives = len({s for s, _ in ns["ref_labels"]})
    notes.append(f"Caption '({CAPTION_UPSTREAMS:,} upstream models)': the released Model->Model file has "
                 f"{upstreams:,} distinct upstream models ({'equal' if upstreams == CAPTION_UPSTREAMS else 'DIFFERENT'}). "
                 f"The Hub reference itself covers {len(ns['queried']):,} queried models, {with_derivatives:,} of them "
                 "with Hub derivatives.")
    ft = strata["Fine-tune"]
    notes.append("The manuscript prints pooled Wilson intervals (pairs treated as independent). Cluster-robust "
                 "intervals (upstream = cluster; design effects "
                 + ", ".join(f"{n} {strata[n]['design_effect']:.1f}" for n in ORDER)
                 + ") are wider, e.g. Fine-tune "
                 f"[{100 * ft['clustered_lo']:.1f}, {100 * ft['clustered_hi']:.1f}] "
                 f"(upper {ft['clustered_hi']:.6f}). The revised table file table/icde_table_iv_revised.tex (VERSION 2) "
                 "prints this upper bound as 94.9, a transcription error; the correct value is 94.8.")

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "rq1_table_02.csv").open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["label", "ref_pairs", "recovered", "recall", "wilson_lo", "wilson_hi",
                    "clustered_lo", "clustered_hi", "label_match", "label_match_rate"])
        w.writerows(table)
        w.writerows([[f"edges:{k}", got[k]] for k in EDGES])
    return v.write_report(args.out / "rq1_table_02_verification.md", "RQ1 Table tab:hub_agreement", rows, ok, notes)


if __name__ == "__main__":
    raise SystemExit(main())
