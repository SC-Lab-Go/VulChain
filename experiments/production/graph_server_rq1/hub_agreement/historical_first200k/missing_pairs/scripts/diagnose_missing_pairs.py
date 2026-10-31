#!/usr/bin/env python3
"""Diagnose Hub model-tree reference pairs not recovered by HuggingGraph v3 (read-only).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Reproduce Table IV (tab:hub_agreement) from HuggingGraph_v3.dot and assign one
evidence-backed primary root cause to every unrecovered reference pair.

Usage:
    python3 -B diagnose_missing_pairs.py --out-dir <new directory>

Every input is opened read-only. The output directory must not exist yet. No network access.

Matching rule (identical to rq1_audit_2026Oct15/scripts/eval_hf_tree_recall.py):
  reference = (Source, Target) rows of graph_model_model_first_200k.csv whose Source is in
  the completed-source list; Hub relation 'merge' is renamed 'merged'.
  graph     = Model->Model edges of HuggingGraph_v3.dot (both endpoints model::), with the
  model:: prefix removed and DOT escaping undone.
  recovered = the exact, case-sensitive (Source, Target) pair is a graph edge whose source
  was queried, with any edge label.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dot_graph  # noqa: E402

W = Path("<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working")
M = W / "2026_Fall_Extension/models"
X = W / "2026_Fall_Extension/extension_updated_code"
A = X / "hugginggraph_v3_2026oct02_reproducibility"

INPUTS = {
    "graph_dot": A / "graph/HuggingGraph_v3.dot",
    "reference": M / "graph_model_model_first_200k.csv",
    "completed": M / "graph_model_model_first_200k.csv.completed.txt",
    "crawl_errors": M / "graph_model_model_first_200k.csv.errors.csv",
    "crawler": M / "graph_model_model_master.py",
    "crawl_inventory_2026Aug28": A / "raw/models/all_huggingface_models_2026Aug28.csv",
    "card_metadata_2026Sep01": A / "raw/models/all_model_readme_metadata_2026Aug28.jsonl",
    "readmes_full_2026Sep25": A / "raw/models/all_model_readmes_full_2026Sep25.jsonl",
    "lineage_declared": A / "evidence/top_level/model_lineage_edges.csv",
    "lineage_inferred": A / "evidence/top_level/model_lineage_edges_inferred.csv",
    "lineage_merged": A / "evidence/top_level/model_lineage_edges_merged.csv",
    "derived_without_parent": A / "evidence/top_level/derived_models_without_identifiable_parent.jsonl",
    "lineage_extractor": A / "source/model_lineage_edges.py",
    "classifier": A / "source/count_model_types.py",
    "inventory_2025Aug14": W / "project_script/all_huggingface_models_Aug14.csv",
    "inventory_2025Jun29": W / "other_supportings/all_huggingface_models.csv",
    "model_tree_2025": A / "evidence/top_level/model_tree_models.csv",
    "published_confusion": X / "rq1_audit_2026Oct15/hf_tree_random1k/smoke_test_first200k/label_confusion.csv",
    "published_metrics": X / "rq1_audit_2026Oct15/hf_tree_random1k/smoke_test_first200k/metrics.json",
}
EXPECTED_DOT_SHA256 = "348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b"
TABLE_IV = {  # adaptation: (reference pairs, recovered, missing), as published
    "finetune": (3466, 3209, 257), "adapter": (1350, 1280, 70),
    "quantized": (9284, 8800, 484), "merged": (1589, 1379, 210),
}
TABLE_IV_TOTAL = (15689, 14668, 1021)
ADAPTATION_NAME = {"finetune": "Fine-tune", "adapter": "Adapter", "quantized": "Quantized", "merged": "Merge"}
ADAPTATION_ORDER = ["finetune", "adapter", "quantized", "merged"]
NORM = {"merge": "merged"}

# Primary root causes, in decision order (the first that applies is assigned).
CAUSES = [
    ("C1_both_endpoints_absent_from_graph", "Both endpoints absent from graph"),
    ("C2_derivative_absent_from_graph", "Derivative endpoint absent from graph (not in crawled model population)"),
    ("C3_upstream_absent_from_graph", "Upstream endpoint absent from graph"),
    ("C4_derivative_card_not_crawled", "Derivative in graph only as a referenced ID; its own card was never crawled"),
    ("C5_identifier_case_mismatch", "Identifier mismatch: case only"),
    ("C6_upstream_alias_noninventory_id", "Identifier mismatch: derivative card names a different, non-inventory upstream ID (repository rename/alias)"),
    ("C7_card_changed_after_snapshot", "Reference/snapshot temporal mismatch: card names upstream only in later (2026-09-25) README"),
    ("C8_unsupported_by_archived_card", "Hub relation not supported by archived card (card names other in-inventory parent(s) or none)"),
]
CAUSE_LABEL = dict(CAUSES)
OUTPUTS = ("missing_pairs.csv", "root_causes.csv", "summary.json", "input_manifest.json", "run.log")

csv.field_size_limit(1 << 30)
ALT_FIELDS = ("Base Model", "Base model", "Base_model", "base model", "base-model", "base_models",
              "derived_from", "finetuned_from", "parent_model", "original_model", "real_base_model",
              "base_model_original", "base_model_sources", "base\\_model", "basemodel", "source_model",
              "duplicated_from", "teacher_model")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def load_classifier():
    spec = importlib.util.spec_from_file_location("count_model_types", INPUTS["classifier"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def strs(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.extend(y for y in x.values() if isinstance(y, str))
        return out
    return []


def card_parents(md, cmt):
    """Parent strings named on an archived card: base_model, base_model tags, explicit parent fields."""
    found = []
    for p in cmt.normalize_base_models(md.get("base_model")):
        found.append((p, "base_model"))
    tags = md.get("tags")
    tags = [tags] if isinstance(tags, str) else (tags if isinstance(tags, list) else [])
    for t in tags:
        if isinstance(t, str) and t.strip().lower().startswith(("base_model:", "base-model:")):
            payload = t.strip().split(":", 1)[1]
            rel, sep, par = payload.partition(":")
            known = sep and cmt.RELATION_ALIASES.get(cmt.normalize_text(rel))
            found.append(((par if known else payload).strip(), "tag"))
    for f in ALT_FIELDS:
        if f in md:
            for v in strs(md[f]):
                found.append((v.strip(), "field:" + f))
    seen, out = set(), []
    for v, src in found:
        if v and (v, src) not in seen:
            seen.add((v, src))
            out.append((v, src))
    return out


def frontmatter(text):
    if not isinstance(text, str) or not text.lstrip().startswith("---"):
        return None
    body = text.lstrip()[3:]
    end = body.find("\n---")
    return body[:end] if end >= 0 else None


def read_ids(path):
    with open(path, encoding="utf-8") as fh:
        fh.readline()
        return {l.strip() for l in fh if l.strip()}


def stream_jsonl_by_id(path, wanted, key_prefix):
    """Yield parsed records whose modelId is in wanted; the ID is sliced from the raw line first."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            i = line.find(key_prefix)
            if i < 0:
                continue
            j = i + len(key_prefix)
            mid = line[j:line.find('"', j)]
            if mid in wanted:
                yield mid, json.loads(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--skip-checksums", action="store_true", help="skip sha256 of the large inputs (faster)")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUTS:
        if (a.out_dir / name).exists():
            raise SystemExit("refusing to overwrite existing output %s" % (a.out_dir / name))
    log = []

    def note(msg):
        log.append(msg)
        print(msg, flush=True)

    cmt = load_classifier()
    manifest = {}
    for k, p in INPUTS.items():
        st = p.stat()
        manifest[k] = {"path": str(p), "bytes": st.st_size, "mtime_epoch": int(st.st_mtime),
                       "sha256": None if a.skip_checksums else sha256(p)}
    if not a.skip_checksums and manifest["graph_dot"]["sha256"] != EXPECTED_DOT_SHA256:
        raise SystemExit("HuggingGraph_v3.dot sha256 differs from the released v3 graph")
    note("inputs recorded: %d" % len(manifest))

    # Graph.
    nodes, mm, dstats = dot_graph.load(INPUTS["graph_dot"])
    note("dot: %s" % json.dumps(dict(dstats)))
    assert dstats.get("unparsed_edge_lines", 0) == 0
    pair_labels = defaultdict(set)
    parents_of = defaultdict(set)
    lc_pairs = defaultdict(set)  # lower-cased pair -> original-case graph pairs
    for s, e, t in mm:
        pair_labels[(s, t)].add(e)
        parents_of[t].add((s, e))
        lc_pairs[(s.lower(), t.lower())].add((s, t))

    # Reference.
    queried = {l.strip() for l in open(INPUTS["completed"], encoding="utf-8") if l.strip()}
    ref = {}
    ref_rows = 0
    with open(INPUTS["reference"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ref_rows += 1
            if r["Source"] in queried:
                ref.setdefault((r["Source"], r["Target"]), set()).add(NORM.get(r["Edge_type"], r["Edge_type"]))
    assert all(len(v) == 1 for v in ref.values()), "a reference pair carries several Hub relations"
    with open(INPUTS["crawl_errors"], encoding="utf-8") as fh:
        crawl_error_rows = sum(1 for _ in fh) - 1

    graph_q = {p for p in pair_labels if p[0] in queried}
    missing = sorted((p for p in ref if p not in graph_q),
                     key=lambda p: (ADAPTATION_ORDER.index(next(iter(ref[p]))), p[0], p[1]))
    recovered = [p for p in ref if p in graph_q]

    table = {}
    for lab in ADAPTATION_ORDER:
        n = sum(1 for p, v in ref.items() if lab in v)
        k = sum(1 for p in recovered if lab in ref[p])
        table[lab] = (n, k, n - k)
    total = (len(ref), len(recovered), len(missing))
    exact_label = sum(1 for p in recovered if ref[p] & pair_labels[p])
    table_check = {
        "table_iv_recomputed": {ADAPTATION_NAME[k]: list(v) for k, v in table.items()} | {"Total": list(total)},
        "table_iv_published": {ADAPTATION_NAME[k]: list(v) for k, v in TABLE_IV.items()} | {"Total": list(TABLE_IV_TOTAL)},
        "matches_published": table == TABLE_IV and total == TABLE_IV_TOTAL,
        "reference_rows": ref_rows, "queried_sources": len(queried),
        "sources_with_ge1_reference_pair": len({s for s, _ in ref}),
        "crawl_error_rows": crawl_error_rows,
        "label_exact_pairs": exact_label,
        "graph_mm_edges": len(mm), "graph_model_nodes": len(nodes),
        "graph_pairs_from_queried_sources": len(graph_q),
        "graph_pairs_from_queried_sources_absent_from_reference": len(graph_q - set(ref)),
        "matching": "exact case-sensitive owner/name strings; model:: prefix removed; Hub 'merge'=='merged'; any graph label counts",
    }
    with open(INPUTS["published_metrics"], encoding="utf-8") as fh:
        pub = json.load(fh)
    table_check["published_metrics_pair_recall_k"] = pub["pair_recall"]["k"]
    table_check["published_metrics_exact_label_k"] = pub["exact_label_recall"]["k"]
    pub_conf = {}
    with open(INPUTS["published_confusion"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["released_label"] == "MISSING":
                pub_conf[r["reference_label"]] = int(r["count"])
    table_check["published_confusion_missing"] = pub_conf
    table_check["published_confusion_matches"] = pub_conf == {k: v[2] for k, v in table.items()}
    note("table IV: %s" % json.dumps(table_check["table_iv_recomputed"]))
    note("matches published: %s" % table_check["matches_published"])

    # Archived evidence for endpoints.
    inv = read_ids(INPUTS["crawl_inventory_2026Aug28"])
    inv25 = read_ids(INPUTS["inventory_2025Aug14"]) | read_ids(INPUTS["inventory_2025Jun29"])
    srcs = {s for s, _ in missing}
    tgts = {t for _, t in missing}
    meta = dict(stream_jsonl_by_id(INPUTS["card_metadata_2026Sep01"], srcs | tgts, '"modelId": "'))
    sep25 = {}
    for mid, rec in stream_jsonl_by_id(INPUTS["readmes_full_2026Sep25"], srcs | tgts, '"modelId":"'):
        sep25[mid] = {"status": rec.get("status"), "retrieved_at_utc": rec.get("retrieved_at_utc"),
                      "readme": rec.get("readme") or ""}
    stage = defaultdict(set)
    for key in ("lineage_declared", "lineage_inferred", "lineage_merged"):
        with open(INPUTS[key], newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["target"] in tgts:
                    stage[(r["source"], r["target"])].add(key)
    dwp = {mid: rec.get("_audit", {}) for mid, rec in
           stream_jsonl_by_id(INPUTS["derived_without_parent"], tgts, '"modelId": "')}
    tree25 = defaultdict(set)
    with open(INPUTS["model_tree_2025"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["Target"] in tgts:
                tree25[(r["Source"], r["Target"])].add(r["Edge_type"])
    kids = defaultdict(set)
    for s, e, t in mm:
        if s in srcs:
            kids[s].add(t)

    rows = []
    for idx, (s, t) in enumerate(missing, 1):
        lab = next(iter(ref[(s, t)]))
        r = {"pair_id": "HMP%04d" % idx, "reference_upstream": s, "reference_derivative": t,
             "reference_adaptation": ADAPTATION_NAME[lab], "hub_relation": "merge" if lab == "merged" else lab}
        s_in, t_in = s in nodes, t in nodes
        r["upstream_in_graph"] = s_in
        r["derivative_in_graph"] = t_in
        r["upstream_in_crawl_inventory"] = s in inv
        r["derivative_in_crawl_inventory"] = t in inv
        r["exact_edge_in_graph"] = (s, t) in pair_labels
        ci = sorted(f"{p}->{c}[{'+'.join(sorted(pair_labels[(p, c)]))}]" for p, c in lc_pairs.get((s.lower(), t.lower()), set()))
        r["canonicalized_edge_in_graph"] = bool(ci)
        r["canonicalized_edge_detail"] = ";".join(ci)
        r["reverse_edge_in_graph"] = (t, s) in pair_labels
        r["alternative_label_edge_in_graph"] = bool(pair_labels.get((s, t)))
        r["pipeline_stage_outputs_with_pair"] = "+".join(sorted(stage.get((s, t), []))) or "none"
        md_rec = meta.get(t)
        r["derivative_card_status_2026Sep01"] = md_rec.get("status") if md_rec else "not_in_crawl"
        md = md_rec.get("readme_metadata") if md_rec and isinstance(md_rec.get("readme_metadata"), dict) else {}
        cps = card_parents(md, cmt)
        r["derivative_card_declared_parents"] = ";".join(sorted({v for v, _ in cps}))
        r["derivative_card_relation_field"] = str(md.get("base_model_relation", md.get("base_model_relationship", "")) or "")
        names = "exact" if any(v == s for v, _ in cps) else ("case_insensitive" if any(v.lower() == s.lower() for v, _ in cps) else "no")
        r["derivative_card_names_upstream"] = names
        r["derivative_graph_parents"] = ";".join(sorted(f"{p}[{e}]" for p, e in parents_of.get(t, set())))
        up = meta.get(s)
        r["upstream_card_status_2026Sep01"] = up.get("status") if up else "not_in_crawl"
        # Alias candidates: declared parents not in the crawl inventory, not a case variant of the upstream.
        so, _, sn = s.partition("/")
        sdoc = (sep25.get(s, {}).get("readme", "") + "\n" +
                json.dumps(up.get("readme_metadata") if up else None)).lower()
        alias = []
        for v in sorted({v for v, _ in cps}):
            if v in inv or v.lower() == s.lower():
                continue
            po, _, pn = v.partition("/")
            alias.append({"id": v, "edge_in_graph": (v, t) in pair_labels,
                          "same_owner": po.lower() == so.lower(),
                          "same_repo_name_other_owner": po.lower() != so.lower() and pn.lower() == sn.lower(),
                          "old_id_in_2025_inventory": v in inv25,
                          "upstream_in_2025_inventory": s in inv25,
                          "upstream_card_mentions_old_id": v.lower() in sdoc,
                          "upstream_card_mentions_distinct_old_name": bool(pn) and pn.lower() != sn.lower() and pn.lower() in sdoc})
        r["alias_parent_ids"] = ";".join(x["id"] for x in alias)
        r["alias_edge_in_graph"] = any(x["edge_in_graph"] for x in alias)
        # Strong: ownership transfer keeping the repository name, or the upstream's own archived
        # card naming the exact old ID. Moderate: same-owner rename, a distinct old name in the
        # upstream card, or old ID present in 2025 while the upstream was not.
        strong, moderate = [], []
        for key in ("same_repo_name_other_owner", "upstream_card_mentions_old_id"):
            if any(x[key] for x in alias):
                strong.append(key)
        for key in ("same_owner", "upstream_card_mentions_distinct_old_name"):
            if any(x[key] for x in alias):
                moderate.append(key)
        if any(x["old_id_in_2025_inventory"] and not x["upstream_in_2025_inventory"] for x in alias):
            moderate.append("old_id_in_2025_inventory_upstream_not")
        corr = strong + moderate
        r["alias_corroboration"] = ";".join(corr)
        r["alias_corroboration_strength"] = "strong" if strong else ("moderate" if moderate else ("none" if alias else "n/a"))
        s25 = sep25.get(t)
        if s25:
            fm = frontmatter(s25["readme"]) or ""
            r["derivative_readme_2026Sep25_status"] = s25["status"]
            r["derivative_readme_2026Sep25_names_upstream"] = ("frontmatter" if s.lower() in fm.lower() else
                                                               ("body_only" if s.lower() in s25["readme"].lower() else "no"))
        else:
            r["derivative_readme_2026Sep25_status"] = "not_in_corpus"
            r["derivative_readme_2026Sep25_names_upstream"] = "n/a"
        r["pair_in_2025_model_tree"] = "+".join(sorted(tree25.get((s, t), []))) or "no"
        sib = sorted(k for k in kids.get(s, ()) if (s, k) not in ref and k.split("/", 1)[0].lower() == t.split("/", 1)[0].lower())
        r["same_owner_graph_children_of_upstream_not_in_reference"] = ";".join(sib[:5])
        r["derivative_flagged_derived_without_parent"] = bool(dwp.get(t))

        # Primary cause, secondary factors, confidence.
        sec = []
        src_ev = []
        if not s_in and not t_in:
            cause, conf = "C1_both_endpoints_absent_from_graph", "confirmed"
            src_ev.append("graph_dot:no model:: node for either endpoint")
        elif not t_in:
            cause, conf = "C2_derivative_absent_from_graph", "confirmed"
            src_ev.append("graph_dot:no model::%s node" % t)
        elif not s_in:
            cause, conf = "C3_upstream_absent_from_graph", "confirmed"
            src_ev.append("graph_dot:no model::%s node" % s)
        elif t not in inv:
            cause, conf = "C4_derivative_card_not_crawled", "confirmed"
            src_ev.append("graph_dot:derivative present only as edge endpoint")
        elif names == "case_insensitive" or r["canonicalized_edge_in_graph"]:
            cause, conf = "C5_identifier_case_mismatch", "confirmed"
            src_ev.append("graph_dot:case-insensitive edge %s" % r["canonicalized_edge_detail"])
        elif alias and r["alias_edge_in_graph"]:
            cause = "C6_upstream_alias_noninventory_id"
            conf = {"strong": "confirmed", "moderate": "probable"}.get(r["alias_corroboration_strength"], "unresolved")
            src_ev.append("graph_dot:edge %s->%s" % (next(x["id"] for x in alias if x["edge_in_graph"]), t))
        elif r["derivative_readme_2026Sep25_names_upstream"] == "frontmatter":
            cause, conf = "C7_card_changed_after_snapshot", "probable"
            src_ev.append("readmes_full_2026Sep25:%s front matter names upstream" % t)
        else:
            cause, conf = "C8_unsupported_by_archived_card", "unresolved"
        if cause in ("C1_both_endpoints_absent_from_graph", "C2_derivative_absent_from_graph", "C4_derivative_card_not_crawled"):
            if t not in inv:
                sec.append("derivative_not_in_2026Aug28_crawl_inventory")
                src_ev.append("crawl_inventory_2026Aug28:%s absent" % t)
            if sib:
                sec.append("same_owner_graph_child_of_upstream_outside_reference(possible_derivative_rename)")
        if cause == "C3_upstream_absent_from_graph" or cause == "C1_both_endpoints_absent_from_graph":
            sec.append("upstream_in_crawl_inventory_but_no_graph_edges" if s in inv else "upstream_not_in_crawl_inventory")
            src_ev.append("card_metadata_2026Sep01:%s status=%s" % (s, r["upstream_card_status_2026Sep01"]))
        if t_in and t in inv:
            src_ev.append("card_metadata_2026Sep01:%s status=%s parents=[%s]" % (t, r["derivative_card_status_2026Sep01"], r["derivative_card_declared_parents"]))
        if alias and cause != "C6_upstream_alias_noninventory_id":
            sec.append("card_names_noninventory_parent:" + r["alias_parent_ids"].replace(";", "|"))
        if alias:
            sec.extend("alias_" + c for c in corr)
            if "upstream_card_mentions_old_id" in corr or "upstream_card_mentions_distinct_old_name" in corr:
                src_ev.append("readmes_full_2026Sep25|card_metadata_2026Sep01:%s card text mentions old ID/name" % s)
            if "old_id_in_2025_inventory_upstream_not" in corr:
                src_ev.append("inventory_2025:old ID listed, upstream not")
        if cause not in ("C7_card_changed_after_snapshot",) and r["derivative_readme_2026Sep25_names_upstream"] == "frontmatter" and cause != "C5_identifier_case_mismatch":
            sec.append("derivative_2026Sep25_frontmatter_names_upstream")
        if r["derivative_readme_2026Sep25_status"] in ("restricted", "error", "no_readme"):
            sec.append("derivative_readme_2026Sep25_" + r["derivative_readme_2026Sep25_status"])
        if r["derivative_card_status_2026Sep01"] == "no_metadata":
            sec.append("derivative_card_had_no_metadata_2026Sep01")
        if r["derivative_flagged_derived_without_parent"]:
            sec.append("derivative_listed_in_derived_models_without_identifiable_parent")
        if r["pair_in_2025_model_tree"] != "no":
            sec.append("pair_in_2025_model_tree_crawl")
        r["primary_root_cause"] = cause
        r["primary_root_cause_label"] = CAUSE_LABEL[cause]
        r["secondary_factors"] = ";".join(sec)
        r["evidence_sources"] = " | ".join(src_ev)
        r["confidence"] = conf
        r["available_provenance_evidence"] = ",".join(x for x in (
            "graph_dot", "crawl_inventory" if t in inv else "",
            "card_metadata_2026Sep01" if md_rec else "",
            "readme_2026Sep25" if s25 else "",
            "pipeline_stage_outputs" if stage.get((s, t)) else "") if x)
        notes = []
        if cause == "C6_upstream_alias_noninventory_id":
            notes.append("graph keeps the lineage under the card's ID %s, absent from the 2026-08-28 inventory; the Hub lists the child under %s" % (r["alias_parent_ids"], s))
        if cause in ("C2_derivative_absent_from_graph", "C1_both_endpoints_absent_from_graph"):
            notes.append("why the derivative is absent from the crawl (created after 2026-08-28, renamed, or not listed) is not recorded locally")
        if cause == "C8_unsupported_by_archived_card":
            notes.append("archived card (2026-09-01) names [%s]; no archived record links the child to %s" % (r["derivative_card_declared_parents"] or "nothing", s))
        r["diagnostic_notes"] = "; ".join(notes)
        rows.append(r)

    cols = list(rows[0].keys())
    with open(a.out_dir / "missing_pairs.csv", "x", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    agg = Counter((r["primary_root_cause"], r["reference_adaptation"]) for r in rows)
    conf_by_cause = Counter((r["primary_root_cause"], r["confidence"]) for r in rows)
    with open(a.out_dir / "root_causes.csv", "x", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["root_cause", "label", "Fine-tune", "Adapter", "Quantized", "Merge", "Total", "Percentage",
                    "confirmed", "probable", "unresolved"])
        for c, label in CAUSES:
            vals = [agg[(c, ADAPTATION_NAME[k])] for k in ADAPTATION_ORDER]
            tot = sum(vals)
            w.writerow([c, label] + vals + [tot, "%.1f" % (100 * tot / len(rows))] +
                       [conf_by_cause[(c, x)] for x in ("confirmed", "probable", "unresolved")])
        vals = [table[k][2] for k in ADAPTATION_ORDER]
        w.writerow(["TOTAL", "All unrecovered pairs"] + vals + [len(rows), "100.0"] +
                   [sum(conf_by_cause[(c, x)] for c, _ in CAUSES) for x in ("confirmed", "probable", "unresolved")])

    # Summary statistics used in the report.
    def pct(n):
        return round(100 * n / len(rows), 1)
    cnt = Counter(r["primary_root_cause"] for r in rows)
    summary = {
        "table_check": table_check,
        "missing_rows": len(rows), "distinct_pairs": len({(r["reference_upstream"], r["reference_derivative"]) for r in rows}),
        "cause_counts": {c: cnt[c] for c, _ in CAUSES},
        "confidence_counts": dict(Counter(r["confidence"] for r in rows)),
        "absent_endpoint_pairs": cnt["C1_both_endpoints_absent_from_graph"] + cnt["C2_derivative_absent_from_graph"] + cnt["C3_upstream_absent_from_graph"],
        "both_endpoints_present_pairs": sum(1 for r in rows if r["upstream_in_graph"] and r["derivative_in_graph"]),
        "identifier_normalization_pairs": cnt["C5_identifier_case_mismatch"] + cnt["C6_upstream_alias_noninventory_id"],
        "pipeline_exclusion_pairs": sum(1 for r in rows if r["pipeline_stage_outputs_with_pair"] != "none"),
        "card_names_upstream_exact": sum(1 for r in rows if r["derivative_card_names_upstream"] == "exact"),
        "reverse_edges": sum(1 for r in rows if r["reverse_edge_in_graph"]),
        "case_insensitive_edges": sum(1 for r in rows if r["canonicalized_edge_in_graph"]),
        "alternative_label_edges": sum(1 for r in rows if r["alternative_label_edge_in_graph"]),
        "unresolved_pairs": cnt["C8_unsupported_by_archived_card"],
        "alias_pairs_by_corroboration": dict(Counter(r["alias_corroboration"] or "none" for r in rows if r["primary_root_cause"] == "C6_upstream_alias_noninventory_id")),
        "alias_distinct_old_ids": len({x for r in rows if r["primary_root_cause"] == "C6_upstream_alias_noninventory_id" for x in r["alias_parent_ids"].split(";")}),
        "alias_distinct_upstreams": len({r["reference_upstream"] for r in rows if r["primary_root_cause"] == "C6_upstream_alias_noninventory_id"}),
        "missing_by_upstream_top15": Counter(r["reference_upstream"] for r in rows).most_common(15),
        "missing_by_upstream_owner_top10": Counter(r["reference_upstream"].split("/")[0] for r in rows).most_common(10),
        "missing_by_derivative_owner_top10": Counter(r["reference_derivative"].split("/")[0] for r in rows).most_common(10),
        "distinct_upstreams_with_missing": len({r["reference_upstream"] for r in rows}),
        "secondary_factor_counts": dict(Counter(f.split(":")[0] for r in rows for f in r["secondary_factors"].split(";") if f)),
        "percentages": {c: pct(cnt[c]) for c, _ in CAUSES},
    }
    # Sensitivity only (does not change any published metric): recall if C5/C6 pairs were matched.
    adj = len(recovered) + summary["identifier_normalization_pairs"]
    summary["sensitivity_recall_if_alias_and_case_resolved"] = {"k": adj, "n": len(ref), "p": round(adj / len(ref), 4)}
    adj_c = len(recovered) + cnt["C5_identifier_case_mismatch"] + sum(1 for r in rows if r["primary_root_cause"] == "C6_upstream_alias_noninventory_id" and r["confidence"] == "confirmed")
    summary["sensitivity_recall_if_confirmed_alias_and_case_resolved"] = {"k": adj_c, "n": len(ref), "p": round(adj_c / len(ref), 4)}
    # Graph-wide context: Model->Model sources that are not crawl-inventory models.
    srcs_all = {s for s, _, _ in mm}
    stale = srcs_all - inv
    summary["graph_mm_sources_not_in_crawl_inventory"] = len(stale)
    summary["graph_mm_edges_with_source_not_in_crawl_inventory"] = sum(1 for s, _, _ in mm if s not in inv)
    inv_lc = {x.lower() for x in inv}
    summary["graph_mm_sources_not_in_inventory_that_look_like_local_paths"] = sum(1 for s in stale if "\\" in s or ":" in s or s.count("/") > 1)
    summary["graph_mm_sources_not_in_inventory_unnamespaced"] = sum(1 for s in stale if "/" not in s)
    summary["graph_mm_edges_with_unnamespaced_noninventory_source"] = sum(1 for s, _, _ in mm if s in stale and "/" not in s)
    summary["graph_mm_sources_not_in_inventory_case_variant_of_inventory_id"] = sum(1 for s in stale if s.lower() in inv_lc)
    summary["graph_mm_edges_with_case_variant_source"] = sum(1 for s, _, _ in mm if s in stale and s.lower() in inv_lc)
    for name, text in (("summary.json", json.dumps(summary, indent=1)), ("input_manifest.json", json.dumps(manifest, indent=1))):
        with open(a.out_dir / name, "x", encoding="utf-8") as fh:
            fh.write(text + "\n")
    note(json.dumps({k: summary[k] for k in ("cause_counts", "confidence_counts", "absent_endpoint_pairs",
                                               "both_endpoints_present_pairs", "identifier_normalization_pairs",
                                               "pipeline_exclusion_pairs")}, indent=1))
    with open(a.out_dir / "run.log", "x", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
