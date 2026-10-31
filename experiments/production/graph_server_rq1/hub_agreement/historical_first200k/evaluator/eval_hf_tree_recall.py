#!/usr/bin/env python3
"""Evaluate released Model->Model lineage against an HF model-tree reference.

Created: 2026-10-15 (rq1_audit_2026Oct15). Offline; reads CSVs only.

Reference: CSV with Source,Edge_type,Target from graph_model_model_master.py
(HF Hub filters base_model:{finetune,adapter,quantized,merge}:<source>), plus the
list of sources whose four queries completed (<output>.completed.txt).
Released: family-01 CSV (source,edge_type,target with model:: prefixes).
Scope: only released edges whose source was queried are compared.

Metrics (each with a Wilson 95% score interval):
  pair_recall          |ref pairs found as released pairs| / |ref pairs|
  exact_label_recall   |ref (s,label,t) found as released triple| / |ref triples|
  label_agreement_on_matched_pairs   exact matches / matched ref pairs
Also: label confusion matrix (reference label x released label set or MISSING),
and the count of released pairs from queried sources absent from the reference
(NOT a false-positive rate: the HF index only covers indexed base_model tags).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

NORM = {"merge": "merged"}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> dict:
    if n == 0:
        return {"k": k, "n": n, "p": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"k": k, "n": n, "p": p, "lo": max(0.0, centre - half), "hi": min(1.0, centre + half)}


def untyped(x: str) -> str:
    return x.split("::", 1)[1] if x.startswith("model::") else x


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--completed", type=Path, required=True)
    ap.add_argument("--released", type=Path, required=True)
    ap.add_argument("--evidence", type=Path, help="model_lineage_edges_merged.csv (optional breakdown)")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=False)

    queried = {l.strip() for l in a.completed.open(encoding="utf-8") if l.strip()}
    ref_triples = set()
    with a.reference.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["Source"] in queried:
                ref_triples.add((r["Source"], NORM.get(r["Edge_type"], r["Edge_type"]), r["Target"]))
    rel_triples = set()
    with a.released.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            s = untyped(r["source"])
            if s in queried:
                rel_triples.add((s, r["edge_type"], untyped(r["target"])))

    ref_labels, rel_labels = defaultdict(set), defaultdict(set)
    for s, e, t in ref_triples:
        ref_labels[(s, t)].add(e)
    for s, e, t in rel_triples:
        rel_labels[(s, t)].add(e)
    matched = set(ref_labels) & set(rel_labels)
    exact = ref_triples & rel_triples

    confusion = Counter()
    for (s, e, t) in ref_triples:
        got = rel_labels.get((s, t))
        confusion[(e, "+".join(sorted(got)) if got else "MISSING")] += 1

    out = dict(
        queried_sources=len(queried),
        reference_triples=len(ref_triples), reference_pairs=len(ref_labels),
        released_triples_from_queried=len(rel_triples), released_pairs_from_queried=len(rel_labels),
        pair_recall=wilson(len(matched), len(ref_labels)),
        exact_label_recall=wilson(len(exact), len(ref_triples)),
        label_agreement_on_matched_pairs=wilson(
            sum(1 for p in matched if ref_labels[p] & rel_labels[p]), len(matched)),
        released_pairs_absent_from_reference=len(set(rel_labels) - set(ref_labels)),
        reference_label_counts=dict(Counter(e for _, e, _ in ref_triples)),
    )
    if a.evidence:
        ev = {}
        with a.evidence.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["source"] in queried:
                    ev[(r["source"], r["target"])] = r["evidence"]
        out["matched_pairs_by_evidence"] = dict(Counter(ev.get(p, "unknown") for p in matched))
    (a.out_dir / "metrics.json").write_text(json.dumps(out, indent=1))
    with (a.out_dir / "label_confusion.csv").open("x", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["reference_label", "released_label", "count"])
        for (r, g), n in sorted(confusion.items()):
            w.writerow([r, g, n])
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
