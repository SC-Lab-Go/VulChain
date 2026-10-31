"""Offline tests for the production modules in experiments/production/.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Check that the published production sources match their manifest,
         that the shared calculation module is a verbatim copy of them, that
         importing them performs no network access, and that the frozen
         outcome and verifier rules behave as documented on synthetic
         evidence. No ledger, prompt, response, or finding is used, and no
         registry or DNS query is made.

Command: python -m unittest discover -s tests -v
"""

import ast
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRODUCTION = REPO / "experiments" / "production"
ICDE = PRODUCTION / "2026_ICDE"
ENGINE = PRODUCTION / "RQ3_analysis" / "v2026.10.16-03"
for path in (PRODUCTION, ICDE, ICDE / "dual_site_probe_v2026_10_10", ENGINE):
    sys.path.insert(0, str(path))
os.environ.pop("VULCHAIN_ALLOW_NETWORK", None)

import offline_verifiers  # noqa: E402
import package_extraction_c1  # noqa: E402
import package_probe_validation  # noqa: E402
import run_rq3  # noqa: E402

URL_DEPS = all(importlib.util.find_spec(m) for m in ("tldextract", "dns", "validators"))
CUT = run_rq3.timevalue("2026-10-16T00:00:00Z")


class Manifest(unittest.TestCase):
    def test_published_files_match_manifest(self):
        result = subprocess.run([sys.executable, "-B", str(PRODUCTION / "verify_sources.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("20/20 files verified", result.stdout)

    def test_only_documented_placeholders_and_no_machine_paths(self):
        manifest = json.loads((PRODUCTION / "SOURCE_MANIFEST.json").read_text())
        for entry in manifest["files"]:
            text = (PRODUCTION / entry["path"]).read_text()
            for placeholder in manifest["placeholders"]:
                expected = sum(r["occurrences"] for r in entry["redactions"] if r["placeholder"] == placeholder)
                self.assertEqual(text.count(placeholder), expected, (entry["path"], placeholder))
            self.assertIsNone(re.search(r"/home/[A-Za-z]|/scratch/\d", text), entry["path"])

    def test_shared_module_is_verbatim_production_code(self):
        source = (REPO / "experiments" / "vulchain_rq.py").read_text()
        origin = {"unified_analysis.py": "RQ2_analysis/v2026.10.27-01/unified_analysis.py",
                  "unified_exports.py": "RQ2_analysis/v2026.10.27-01/unified_exports.py"}
        headers = [(m.start(), m.group(1)) for m in
                   re.finditer(r"^# (?:Copied verbatim from (\S+)|Adapter)", source, re.M)]
        offsets = [0]
        for line in source.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        checked = 0
        for node in ast.parse(source).body:
            start = offsets[node.lineno - 1]
            section = [name for pos, name in headers if pos < start]
            if not section or section[-1] is None:
                continue
            segment = ast.get_source_segment(source, node)
            production = (PRODUCTION / origin[section[-1]]).read_text()
            self.assertIn(segment, production, f"{section[-1]}: {segment.splitlines()[0]}")
            checked += 1
        self.assertGreater(checked, 20)


class NoNetworkOnImport(unittest.TestCase):
    def test_imports_open_no_sockets(self):
        code = (
            "import socket, sys\n"
            "def refuse(*a, **k): raise AssertionError('network used on import')\n"
            "socket.socket.connect = refuse; socket.create_connection = refuse; socket.getaddrinfo = refuse\n"
            f"sys.path[:0] = {[str(PRODUCTION), str(ICDE), str(ICDE / 'dual_site_probe_v2026_10_10'), str(ENGINE)]!r}\n"
            "import offline_verifiers, package_probe_validation, package_extraction_c1, run_rq3\n"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                                env={k: v for k, v in os.environ.items() if k != "VULCHAIN_ALLOW_NETWORK"})
        self.assertEqual(result.returncode, 0, result.stderr)


class OutcomeRules(unittest.TestCase):
    """run_rq3.outcomes(): metric-specific positive precedence."""

    parent = dict(confirmed={"t1": "pypi"}, unresolved=set())

    def outcome(self, confirmed=(), unresolved=()):
        child = dict(confirmed={t: "pypi" for t in confirmed}, unresolved=set(unresolved))
        return run_rq3.outcomes(self.parent, child)

    def test_identical_artifact_is_class_and_instance_positive(self):
        self.assertEqual(self.outcome(confirmed=["t1"]), ("positive", "positive"))

    def test_different_artifact_is_class_positive_only(self):
        self.assertEqual(self.outcome(confirmed=["t2"]), ("positive", "negative"))

    def test_unresolved_candidate_that_could_match_parent_is_unknown(self):
        self.assertEqual(self.outcome(unresolved=[("exact", "t1")]), ("unknown", "unknown"))
        self.assertEqual(self.outcome(unresolved=[("ecosystem", "pypi")]), ("unknown", "unknown"))

    def test_unresolved_candidate_with_other_identity_keeps_instance_negative(self):
        self.assertEqual(self.outcome(unresolved=[("exact", "t3")]), ("unknown", "negative"))

    def test_no_candidate_is_negative(self):
        self.assertEqual(self.outcome(), ("negative", "negative"))


class VerifiedFindingRules(unittest.TestCase):
    """run_rq3.response_states(): what counts as an externally verified artifact."""

    def package(self, checked_at, status=404, state="absent"):
        evidence = dict(ecosystem="pypi", normalized_name="synthetic-test-package",
                        registry_observation=dict(state=state, http_status=status, checked_at=checked_at,
                                                  url="https://pypi.org/pypi/synthetic-test-package/json"))
        return run_rq3.response_states([("hallucinated_package", evidence, True)], [], CUT, set(), set())

    def test_registry_404_before_cutoff_is_confirmed(self):
        state = self.package("2026-10-01T00:00:00Z")["package_hallucination"]
        self.assertEqual(list(state["confirmed"].values()), ["pypi"])
        self.assertFalse(state["unresolved"])

    def test_registry_observation_after_cutoff_is_unresolved(self):
        state = self.package("2026-10-20T00:00:00Z")["package_hallucination"]
        self.assertFalse(state["confirmed"])
        self.assertEqual(state["unresolved"], {("exact", run_rq3.token("package_hallucination",
                                                                        "pypi:synthetic-test-package"))})

    def nx(self, reason="registrable_domain_NXDOMAIN", review="ok", status="nxdomain"):
        evidence = dict(host="www.synthetic-test.zz", registrable_domain="synthetic-test.zz",
                        syntactically_valid=True, private_public_suffix=False, reason=reason,
                        dns_domain=dict(status=status, checked_at="2026-10-01T00:00:00Z"))
        return run_rq3.response_states([], [("registrable_hallucinated", evidence, review)],
                                       CUT, set(), set())["nonexistent_domain"]

    def test_registrable_nxdomain_with_review_is_confirmed(self):
        self.assertEqual(self.nx()["confirmed"], {run_rq3.token("nonexistent_domain", "synthetic-test.zz"): "domain"})

    def test_private_suffix_tenant_is_ineligible_before_dns(self):
        state = self.nx(reason="private_suffix_tenant; not_a_registrar_domain")
        self.assertFalse(state["confirmed"])
        self.assertEqual(state["excluded"]["ineligible_nx_private_suffix_tenant"], 1)

    def test_missing_review_keeps_nxdomain_unresolved(self):
        state = self.nx(review=None)
        self.assertFalse(state["confirmed"])
        self.assertTrue(state["unresolved"])


class PackageVerifier(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE registry_evidence(ecosystem TEXT, name TEXT, evidence_json TEXT)")
        self.candidate = dict(raw_name="synthetic-test-package", ecosystem="pypi", construct="install",
                              start_offset=0, end_offset=22, context="pip install synthetic-test-package")

    def test_uncached_lookup_is_refused_without_explicit_permission(self):
        verifier = offline_verifiers.package_verifier(self.db)
        with self.assertRaises(offline_verifiers.NetworkDisabled):
            verifier.validate(self.candidate)

    def test_absent_registry_entry_is_hallucinated_and_cached(self):
        calls = []

        def fetch(ecosystem, name):
            calls.append((ecosystem, name))
            return dict(url="https://pypi.org/pypi/" + name + "/json", checked_at="2026-10-01T00:00:00Z",
                        state="absent", http_status=404)

        verifier = offline_verifiers.package_verifier(self.db, fetch=fetch)
        self.assertEqual(verifier.validate(self.candidate)["verdict"], "hallucinated_package")
        offline = offline_verifiers.package_verifier(self.db)
        self.assertEqual(offline.validate(self.candidate)["verdict"], "hallucinated_package")
        self.assertEqual(calls, [("pypi", "synthetic-test-package")])

    def test_warning_context_is_excluded_before_lookup(self):
        candidate = dict(self.candidate, context="never run pip install synthetic-test-package")
        verdict = offline_verifiers.package_verifier(self.db).validate(candidate)["verdict"]
        self.assertEqual(verdict, "excluded_context")


class C1Extraction(unittest.TestCase):
    def test_shell_comment_words_are_dropped_only_by_c1(self):
        text = "pip install synthetic-test-package  # for scalability\n"
        frozen = [c["raw_name"] for c in package_probe_validation.extract_packages(text)]
        corrected = [c["raw_name"] for c in package_extraction_c1.extract_packages(text)]
        self.assertIn("scalability", frozen)
        self.assertEqual(corrected, ["synthetic-test-package"])


@unittest.skipUnless(URL_DEPS, "tldextract, dnspython and validators not installed (requirements-verifiers.txt)")
class URLVerifier(unittest.TestCase):
    def test_markdown_link_is_split_by_c1(self):
        import url_extraction_c1
        text = "[https://a.synthetic-test.zz/x](https://b.synthetic-test.zz/y)"
        self.assertEqual([r for r, *_ in url_extraction_c1.extract_urls(text)],
                         ["https://a.synthetic-test.zz/x", "https://b.synthetic-test.zz/y"])


if __name__ == "__main__":
    unittest.main()
