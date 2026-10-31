#!/usr/bin/env python3
"""Reproducibility and consistency tests for the Hub-reference selection audit (read-only).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Independently recompute the selection frame, the reference set and Table IV from the
original inputs; check that the stored outputs and the prose deliverables agree with them; and
confirm that every input file is unchanged since the audit ran.

Usage:
    python3 -B tests/test_selection_audit.py [-v]
Set SELECTION_AUDIT_RERUN=1 to also re-run the audit into a fresh temporary directory and
require byte-identical outputs (about one minute).
"""
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG / "scripts"))
import audit_selection as au  # noqa: E402  (paths and constants only)

OUT = PKG / "outputs"
CTX = {}


def ids(path, col):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [v for v in ((r.get(col) or "").strip() for r in csv.DictReader(fh)) if v]


def setUpModule():
    CTX["R"] = json.loads((OUT / "selection_audit.json").read_text())
    CTX["inv"] = set(ids(au.INPUTS["inventory_2026Aug28"], "modelId"))
    CTX["base"] = set(ids(au.INPUTS["baseline_CIKM"], "model_id"))
    CTX["delta"] = ids(au.INPUTS["delta_2026Aug28"], "modelId")
    CTX["done"] = [l.strip() for l in open(au.INPUTS["completed"], encoding="utf-8") if l.strip()]
    with open(au.INPUTS["reference"], newline="", encoding="utf-8") as fh:
        CTX["ref_rows"] = [(r["Source"], r["Edge_type"], r["Target"]) for r in csv.DictReader(fh)]
    pairs = set()
    with open(au.INPUTS["family01"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            pairs.add((r["source"].removeprefix("model::"), r["target"].removeprefix("model::")))
    CTX["rel_pairs"] = pairs
    with open(OUT / "per_source_recovery.csv", newline="", encoding="utf-8") as fh:
        CTX["per_src"] = list(csv.DictReader(fh))
    with open(OUT / "selection_flow.csv", newline="", encoding="utf-8") as fh:
        CTX["flow"] = {r["stage_id"]: r for r in csv.DictReader(fh)}


class OriginalsUnchanged(unittest.TestCase):
    def test_input_checksums_unchanged(self):
        before = {}
        for line in (PKG / "logs/input_sha256_before.txt").read_text().splitlines():
            h, p = line.split(None, 1)
            before[p.strip()] = h
        self.assertEqual(len(before), len(au.INPUTS))
        for p in au.INPUTS.values():
            h = hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).stat().st_size < 2**31 else None
            if h is None:  # large file: stream
                d = hashlib.sha256()
                with open(p, "rb") as fh:
                    for c in iter(lambda: fh.read(1 << 22), b""):
                        d.update(c)
                h = d.hexdigest()
            self.assertEqual(h, before[str(p)], p)
            self.assertEqual(h, CTX["R"]["inputs"][next(k for k, v in au.INPUTS.items() if v == p)]["sha256"])


class SelectionFrame(unittest.TestCase):
    def test_delta_is_sorted_inventory_minus_baseline(self):
        self.assertEqual(CTX["delta"], sorted(CTX["inv"] - CTX["base"]))
        self.assertEqual(len(CTX["delta"]), 1_324_194)
        self.assertEqual(len(CTX["inv"]), 3_029_377)

    def test_queried_is_exactly_the_200k_prefix(self):
        done = CTX["done"]
        self.assertEqual(len(done), 200_000)
        self.assertEqual(len(set(done)), 200_000)
        self.assertEqual(set(done), set(CTX["delta"][:200_000]))

    def test_no_failures_recorded(self):
        with open(au.INPUTS["crawl_errors"], newline="", encoding="utf-8") as fh:
            self.assertEqual(len(list(csv.reader(fh))), 1)  # header only
        log = Path(au.INPUTS["crawl_log"]).read_text(errors="replace")
        self.assertIn("Done: 200000 completed, 0 failed, 0 already completed", log)

    def test_prefix_has_no_lowercase_owner_and_no_baseline_model(self):
        q = set(CTX["done"])
        self.assertFalse(any("a" <= x[0] <= "z" for x in q))
        self.assertFalse(q & CTX["base"])
        self.assertTrue(max(q) < CTX["delta"][200_000])


class ReferenceSet(unittest.TestCase):
    def test_reference_definitions(self):
        rows, q = CTX["ref_rows"], set(CTX["done"])
        self.assertEqual(len(rows), 15_689)
        self.assertEqual(len(set(rows)), 15_689)
        self.assertTrue(all(s in q for s, _, _ in rows))
        labels = defaultdict(set)
        for s, e, t in rows:
            labels[(s, t)].add(e)
        self.assertEqual(len(labels), 15_689)
        self.assertEqual(sum(len(v) > 1 for v in labels.values()), 0)
        self.assertEqual(len({s for s, _, _ in rows}), 5_222)

    def test_table_iv_recomputed_independently(self):
        norm = {"merge": "merged"}
        cat = {"finetune": "Fine-tune", "adapter": "Adapter", "quantized": "Quantized", "merged": "Merge"}
        got = defaultdict(lambda: [0, 0])
        for s, e, t in CTX["ref_rows"]:
            c = cat[norm.get(e, e)]
            for key in (c, "Total"):
                got[key][0] += 1
                got[key][1] += (s, t) in CTX["rel_pairs"]
        for k, (n, rec, miss) in au.PUBLISHED_TABLE_IV.items():
            self.assertEqual((got[k][0], got[k][1], got[k][0] - got[k][1]), (n, rec, miss), k)

    def test_missing_pairs_match_existing_ledger(self):
        with open(au.INPUTS["missing_pairs_ledger"], newline="", encoding="utf-8") as fh:
            ledger = {(r["reference_upstream"], r["reference_derivative"]) for r in csv.DictReader(fh)}
        missing = {(s, t) for s, _, t in CTX["ref_rows"] if (s, t) not in CTX["rel_pairs"]}
        self.assertEqual(ledger, missing)


class StoredOutputs(unittest.TestCase):
    def test_flow_chain(self):
        f = {k: int(v["count"]) for k, v in CTX["flow"].items()}
        x = {k: int(v["excluded_from_previous"] or 0) for k, v in CTX["flow"].items()}
        self.assertEqual(f["S0"] - x["S1"], f["S1"])
        self.assertEqual(f["S1"] - x["S2"], f["S2"])
        self.assertEqual(f["S2"], f["S3"])
        self.assertEqual(f["S3"] - x["S4"], f["S4"])
        self.assertEqual(f["S4"] - x["S5"], f["S5"])
        self.assertEqual((f["S5"], f["S6"], f["S7"]), (5_222, 15_689, 14_668))
        self.assertEqual(f["S6"] - x["S7"], f["S7"])

    def test_per_source_table(self):
        ps = CTX["per_src"]
        self.assertEqual(len(ps), 5_222)
        self.assertEqual(sum(int(r["reference_pairs"]) for r in ps), 15_689)
        self.assertEqual(sum(int(r["recovered"]) for r in ps), 14_668)
        self.assertTrue(all(r["owner_bucket"] in {"0-9", "A-C", "D-F", "G-I", "J"} for r in ps))

    def test_clustered_interval_from_per_source_table(self):
        cl = [(int(r["recovered"]), int(r["reference_pairs"])) for r in CTX["per_src"]]
        K, N, n = sum(k for k, _ in cl), sum(m for _, m in cl), len(cl)
        p = K / N
        se = math.sqrt(n / (n - 1) * sum((k - p * m) ** 2 for k, m in cl)) / N
        sc = CTX["R"]["statistics"]["source_clustered"]
        self.assertAlmostEqual(se, sc["se"], places=12)
        self.assertGreater(sc["design_effect"], 1.0)
        w = CTX["R"]["statistics"]["pooled_wilson"]
        pub = json.loads(Path(au.INPUTS["published_metrics"]).read_text())["pair_recall"]
        for key in ("k", "n", "lo", "hi"):
            self.assertAlmostEqual(w[key], pub[key], places=12)
        bs = CTX["R"]["statistics"]["source_cluster_bootstrap"]
        self.assertLess(bs["lo"], w["lo"])
        self.assertGreater(bs["hi"], w["hi"])


class ProseConsistency(unittest.TestCase):
    def test_documents_cite_verified_numbers(self):
        need = {"selection_trace.md": ["200,000", "1,324,194", "5,222", "194,778", "John6666/jedpoint-real-v8-vae-sdxl"],
                "reference_pair_validation.md": ["15,689", "14,668", "7,336", "15,073"],
                "statistical_assessment.md": ["93.1", "93.9", "92.2", "94.6"],
                "representativeness_report.md": ["72.1", "0 of 200,000"]}
        for name, tokens in need.items():
            text = (PKG / name).read_text()
            for t in tokens:
                self.assertIn(t, text, f"{name} lacks {t}")

    def test_paper_text_does_not_claim_random_sampling(self):
        tex = (PKG / "icde_paper_text.tex").read_text()
        body = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))
        low = body.lower()
        self.assertNotRegex(low, r"randomly|uniformly|representative sample|stratified")
        for m in re.finditer(r"random", low):  # only negated uses ("non-random", "not a random")
            self.assertRegex(low[max(0, m.start() - 6):m.start()], r"(non-|not a )$")
        for t in ("200{,}000", "5{,}222", "15{,}689", "14{,}668"):
            self.assertIn(t, body)


@unittest.skipUnless(os.environ.get("SELECTION_AUDIT_RERUN") == "1", "set SELECTION_AUDIT_RERUN=1")
class Rerun(unittest.TestCase):
    def test_rerun_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", str(PKG / "scripts/audit_selection.py"), "--out-dir", d],
                           check=True, stdout=subprocess.DEVNULL)
            for name in ("selection_audit.json", "per_source_recovery.csv", "selection_flow.csv"):
                self.assertEqual(Path(d, name).read_bytes(), (OUT / name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
