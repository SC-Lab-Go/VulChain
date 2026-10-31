"""Unit and consistency tests for the VulChain repository.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Fast checks that need no large downloads: embedded pipeline sources,
         shared calculation rules, snapshot integrity, and catalog totals.

Command: python -m unittest discover -s tests -v
"""

import csv
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments"))
import vulchain_rq as v  # noqa: E402
import vulchain_table2 as t2  # noqa: E402


class GraphConstruction(unittest.TestCase):
    def test_embedded_sources_match_recorded_checksums(self):
        result = subprocess.run([sys.executable, "-B", str(REPO / "graph_construction" / "vulchain_graph.py"), "verify"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("\nOK") + result.stdout.startswith("OK"), 18)

    def test_stdlib_stages_expose_help(self):
        for stage in ("assemble", "dataset-model", "space-attributes"):
            result = subprocess.run([sys.executable, "-B", str(REPO / "graph_construction" / "vulchain_graph.py"),
                                     stage, "--help"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, stage + result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("huggingface_hub"), "huggingface_hub not installed (requirements.txt)")
    def test_prepare_stage_exposes_help(self):
        result = subprocess.run([sys.executable, "-B", str(REPO / "graph_construction" / "vulchain_graph.py"),
                                 "prepare", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class Catalog(unittest.TestCase):
    def test_seventeen_families_sum_to_vulchain_edges(self):
        with (REPO / "relationships" / "relationship_catalog.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([int(r["number"]) for r in rows], list(range(1, 18)))
        self.assertEqual(sum(int(r["edges"]) for r in rows), 7666919)

    def test_every_family_has_a_sample(self):
        self.assertEqual(len(list((REPO / "relationships" / "examples").glob("*_sample.csv"))), 17)


class CalculationRules(unittest.TestCase):
    def test_summarize_shared_denominator_excludes_unknown(self):
        rows = [dict(class_state=c, instance_state=i, parent_id="p", child_id="c", membership_id_sha256="m")
                for c, i in [("positive", "positive"), ("positive", "negative"), ("negative", "negative"),
                             ("unknown", "negative")]]
        s = v.summarize(rows)
        self.assertEqual((s["tests"], s["class_rec"], s["instance_rec"], s["unknown_excluded"]), (3, 2, 1, 1))

    def test_percentage_display_trims_trailing_zeros(self):
        self.assertEqual(v.percentage(v.rate(0.3)), "30")
        self.assertEqual(v.percentage(v.rate(0.297)), "29.7")

    def test_table2_counts_distinct_ids(self):
        rows = [("b", "x", "finetune"), ("b", "x", "finetune"), ("b", "y", "adapter"), ("b", "z", "converted")]
        values = t2.summarize(rows)["values"]
        self.assertEqual((values["Bases"], values["FT"], values["AD"], values["UniqueModels"]), (1, 1, 1, 3))


@unittest.skipUnless((REPO / "data" / "rq_snapshot" / "canonical_comparisons.jsonl").is_file(),
                     "restricted RQ2-RQ5 snapshot not present (held privately)")
class Snapshot(unittest.TestCase):
    def test_snapshot_inputs_match_manifest(self):
        manifest = v.snapshot_files(v.DEFAULT_SNAPSHOT)
        self.assertEqual(manifest["snapshot_id"], "v2026.10.27-unified-01-b9e3e4d60181fa58")

    def test_no_raw_artifact_strings_in_comparisons(self):
        first = v.load_comparisons(v.DEFAULT_SNAPSHOT)[0]
        self.assertNotIn("response", first)
        self.assertTrue(all(len(h) == 64 for h in first["parent_artifact_sha256"]))


if __name__ == "__main__":
    unittest.main()
