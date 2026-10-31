#!/usr/bin/env python3
"""Verification tests for the Hub-reference missing-pair diagnostic (read-only).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Independently recompute Table IV and check the ledger, the aggregation and the
evidence behind each primary cause; confirm that the original inputs are unchanged.

Usage:
    python3 -B test_missing_pairs.py [--results-dir DIR] [-v]
DIR defaults to the directory above this script.
"""
import argparse
import csv
import hashlib
import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dot_graph  # noqa: E402
import diagnose_missing_pairs as dmp  # noqa: E402

RESULTS = HERE.parent
CTX = {}


def setUpModule():
    nodes, mm, _ = dot_graph.load(dmp.INPUTS["graph_dot"])
    CTX["nodes"], CTX["mm"] = nodes, mm
    CTX["pairs"] = {(s, t) for s, _, t in mm}
    with open(dmp.A / "edges/csv/01_model_model_edges.csv", newline="", encoding="utf-8") as fh:
        CTX["csv_triples"] = {(r["source"].split("::", 1)[1], r["edge_type"], r["target"].split("::", 1)[1])
                              for r in csv.DictReader(fh)}
    queried = {l.strip() for l in open(dmp.INPUTS["completed"], encoding="utf-8") if l.strip()}
    ref = {}
    with open(dmp.INPUTS["reference"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["Source"] in queried:
                ref[(r["Source"], r["Target"])] = dmp.NORM.get(r["Edge_type"], r["Edge_type"])
    CTX["queried"], CTX["ref"] = queried, ref
    with open(RESULTS / "missing_pairs.csv", newline="", encoding="utf-8") as fh:
        CTX["rows"] = list(csv.DictReader(fh))
    with open(RESULTS / "root_causes.csv", newline="", encoding="utf-8") as fh:
        CTX["agg"] = list(csv.DictReader(fh))


class TableIV(unittest.TestCase):
    def test_dot_equals_family01_csv(self):
        self.assertEqual(CTX["mm"], CTX["csv_triples"])
        self.assertEqual(len(CTX["mm"]), 966035)

    def test_reference_recovered_missing_totals(self):
        ref, q, pairs = CTX["ref"], CTX["queried"], CTX["pairs"]
        rec = [p for p in ref if p in pairs and p[0] in q]
        self.assertEqual(len(ref), 15689)
        self.assertEqual(len(rec), 14668)
        self.assertEqual(len(ref) - len(rec), 1021)

    def test_per_adaptation_matches_published(self):
        ref, pairs = CTX["ref"], CTX["pairs"]
        for lab, (n, k, m) in dmp.TABLE_IV.items():
            sel = [p for p, l in ref.items() if l == lab]
            self.assertEqual(len(sel), n, lab)
            self.assertEqual(sum(p in pairs for p in sel), k, lab)
            self.assertEqual(sum(p not in pairs for p in sel), m, lab)


class Ledger(unittest.TestCase):
    def test_one_row_per_distinct_missing_pair(self):
        rows = CTX["rows"]
        keys = [(r["reference_upstream"], r["reference_derivative"]) for r in rows]
        self.assertEqual(len(rows), 1021)
        self.assertEqual(len(set(keys)), 1021)
        self.assertEqual(len({r["pair_id"] for r in rows}), 1021)

    def test_rows_are_exactly_the_unrecovered_reference_pairs(self):
        expected = {p for p in CTX["ref"] if p not in CTX["pairs"]}
        got = {(r["reference_upstream"], r["reference_derivative"]) for r in CTX["rows"]}
        self.assertEqual(got, expected)
        for r in CTX["rows"]:
            self.assertEqual(r["exact_edge_in_graph"], "False")
            self.assertEqual(r["alternative_label_edge_in_graph"], "False")

    def test_adaptation_labels(self):
        for r in CTX["rows"]:
            lab = CTX["ref"][(r["reference_upstream"], r["reference_derivative"])]
            self.assertEqual(r["reference_adaptation"], dmp.ADAPTATION_NAME[lab])
        c = Counter(r["reference_adaptation"] for r in CTX["rows"])
        self.assertEqual(c, Counter({dmp.ADAPTATION_NAME[k]: v[2] for k, v in dmp.TABLE_IV.items()}))

    def test_every_row_has_cause_confidence_and_evidence(self):
        allowed = {c for c, _ in dmp.CAUSES}
        for r in CTX["rows"]:
            self.assertIn(r["primary_root_cause"], allowed)
            self.assertIn(r["confidence"], {"confirmed", "probable", "unresolved"})
            self.assertTrue(r["evidence_sources"].strip(), r["pair_id"])


class CauseEvidence(unittest.TestCase):
    """Re-check each primary cause against the DOT, independently of the diagnostic's own flags."""

    def test_endpoint_causes(self):
        nodes = CTX["nodes"]
        for r in CTX["rows"]:
            s, t, c = r["reference_upstream"], r["reference_derivative"], r["primary_root_cause"]
            if c.startswith("C1_"):
                self.assertTrue(s not in nodes and t not in nodes)
            elif c.startswith("C2_"):
                self.assertTrue(s in nodes and t not in nodes)
            elif c.startswith("C3_"):
                self.assertTrue(s not in nodes and t in nodes)
            else:
                self.assertTrue(s in nodes and t in nodes, r["pair_id"])

    def test_case_mismatch_edges_exist_case_insensitively(self):
        lc = defaultdict(set)
        for s, t in CTX["pairs"]:
            lc[(s.lower(), t.lower())].add((s, t))
        for r in CTX["rows"]:
            if r["primary_root_cause"].startswith("C5_"):
                hits = lc[(r["reference_upstream"].lower(), r["reference_derivative"].lower())]
                names = r["derivative_card_declared_parents"].lower().split(";")
                self.assertTrue(hits or r["reference_upstream"].lower() in names, r["pair_id"])

    def test_alias_edges_exist_in_dot_under_noninventory_id(self):
        inv = dmp.read_ids(dmp.INPUTS["crawl_inventory_2026Aug28"])
        for r in CTX["rows"]:
            if r["primary_root_cause"].startswith("C6_"):
                ids = r["alias_parent_ids"].split(";")
                self.assertTrue(any((p, r["reference_derivative"]) in CTX["pairs"] for p in ids), r["pair_id"])
                self.assertTrue(all(p not in inv for p in ids), r["pair_id"])
                self.assertNotIn(r["reference_upstream"], ids)

    def test_derivative_card_never_names_upstream_exactly(self):
        # If an archived card named the upstream exactly, the extractor would have emitted the edge.
        for r in CTX["rows"]:
            self.assertNotEqual(r["derivative_card_names_upstream"], "exact", r["pair_id"])

    def test_no_reverse_edges_and_no_pipeline_exclusion(self):
        for r in CTX["rows"]:
            self.assertEqual(r["reverse_edge_in_graph"], "False")
            self.assertEqual(r["pipeline_stage_outputs_with_pair"], "none")


class Aggregation(unittest.TestCase):
    def test_root_causes_sum(self):
        agg = {r["root_cause"]: r for r in CTX["agg"]}
        cols = ["Fine-tune", "Adapter", "Quantized", "Merge"]
        body = [r for k, r in agg.items() if k != "TOTAL"]
        self.assertEqual(sum(int(r["Total"]) for r in body), 1021)
        for col, (lab, v) in zip(cols, [(k, dmp.TABLE_IV[k]) for k in dmp.ADAPTATION_ORDER]):
            self.assertEqual(sum(int(r[col]) for r in body), v[2], col)
            self.assertEqual(int(agg["TOTAL"][col]), v[2], col)
        for r in body:
            self.assertEqual(sum(int(r[c]) for c in cols), int(r["Total"]))
            self.assertEqual(sum(int(r[c]) for c in ("confirmed", "probable", "unresolved")), int(r["Total"]))
        ledger = Counter(r["primary_root_cause"] for r in CTX["rows"])
        for k, r in agg.items():
            if k != "TOTAL":
                self.assertEqual(int(r["Total"]), ledger[k], k)


class OriginalsUnchanged(unittest.TestCase):
    def test_input_checksums_unchanged(self):
        before = RESULTS / "logs/input_sha256_before.txt"
        if not before.exists():
            self.skipTest("no pre-run checksum record")
        for line in before.read_text().splitlines():
            digest, path = line.split(None, 1)
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 24), b""):
                    h.update(chunk)
            self.assertEqual(h.hexdigest(), digest, path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    a, rest = ap.parse_known_args()
    RESULTS = a.results_dir
    unittest.main(argv=[sys.argv[0]] + rest)
