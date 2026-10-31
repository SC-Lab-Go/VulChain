"""Tests for the RQ1 Graph Server code (fig:rq1, tab:hub_agreement).

Created: 2026-10-30
Version: v2026.10.30-04
Purpose: Check the transferred RQ1 sources against their manifest, that no
         machine-specific literal or in-progress experiment is published, and
         that both RQ1 entry points reproduce the manuscript. The Hub test needs
         the graph release; set VULCHAIN_RELEASE_DIR, or configs/pipeline.local.json
         "release_dir", otherwise it is skipped.

Command: python -m unittest discover -s tests -v
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "experiments" / "production" / "graph_server_rq1"


def release_dir():
    value = os.environ.get("VULCHAIN_RELEASE_DIR")
    local = REPO / "configs" / "pipeline.local.json"
    if not value and local.is_file():
        value = json.loads(local.read_text()).get("release_dir")
    path = Path(value) if value else None
    return path if path and (path / "edges" / "csv" / "01_model_model_edges.csv").is_file() else None


def run(*args):
    return subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True)


COMPLETED = PKG / "hub_agreement" / "historical_first200k" / "reference" / "graph_model_model_first_200k.csv.completed.txt"


class Sources(unittest.TestCase):
    @unittest.skipUnless(COMPLETED.is_file(), "Release asset graph_model_model_first_200k.csv.completed.txt not downloaded (README: Download)")
    def test_manifest_hashes(self):
        result = run(REPO / "experiments" / "production" / "verify_sources.py", "--root", PKG)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        n = len(json.loads((PKG / "SOURCE_MANIFEST.json").read_text())["files"])
        self.assertIn(f"{n}/{n} files verified", result.stdout)

    def test_no_machine_literals_restricted_files_or_in_progress_experiment(self):
        manifest = json.loads((PKG / "SOURCE_MANIFEST.json").read_text())
        self.assertTrue(all(f["eligibility"] in ("PUBLIC", "PUBLIC-DATA") for f in manifest["files"]))
        for path in PKG.rglob("*"):
            self.assertNotIn("probability_sample", str(path))
            self.assertNotRegex(path.name, r"load-(before|after)|hardware\.txt|nohup\.log")
            if path.is_file() and path.suffix not in (".pdf", ".png"):
                self.assertIsNone(re.search(r"/home/[A-Za-z]|cse-\d", path.read_text()), path)


class Reproduction(unittest.TestCase):
    def test_fig_rq1_values_from_raw_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(REPO / "experiments" / "RQ1" / "rq1_figure_01.py", "--out", tmp)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFIED", result.stdout)

    @unittest.skipUnless(release_dir(), "graph release not configured (VULCHAIN_RELEASE_DIR)")
    def test_hub_agreement_from_original_evaluator_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(REPO / "experiments" / "RQ1" / "rq1_table_02.py", "--release-dir", release_dir(), "--out", tmp)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("34/34", result.stdout)


if __name__ == "__main__":
    unittest.main()
