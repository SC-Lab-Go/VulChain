#!/usr/bin/env python3
"""Hub model-tree reference selection and representativeness audit (read-only).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Reconstruct how the Hub model-tree reference behind ICDE 2027 Table IV was
selected (200,000 queried sources -> 5,222 with derivatives -> 15,689 pairs), compare the
queried sources with the eligible and excluded model populations, and compute descriptive
and model-clustered sensitivity diagnostics for the 14,668 / 15,689 pair recovery.

All inputs are only read. No network access, no Hub API request, no GPU. Standard library only.
Outputs are written to --out-dir, which must be new or empty.

Usage:
    python3 -B audit_selection.py --out-dir DIR [--bootstrap 2000] [--seed 20261030]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path("<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working")
M = W / "2026_Fall_Extension/models"
E = W / "2026_Fall_Extension/extension_updated_code"
A = E / "hugginggraph_v3_2026oct02_reproducibility"
RQ1 = E / "rq1_audit_2026Oct15"
MP = W / "validation/hub_reference_missing_pairs_2027"

INPUTS = {
    "inventory_2026Aug28": A / "raw/models/all_huggingface_models_2026Aug28.csv",
    "baseline_CIKM": M / "all_huggingface_models_CIKM.csv",
    "delta_2026Aug28": M / "delta_model-2026-Aug28.csv",
    "delta_builder": M / "delta_models.py",
    "crawler": M / "graph_model_model_master.py",
    "pipeline_notes": M / "model_pipeline.md",
    "reference": M / "graph_model_model_first_200k.csv",
    "completed": M / "graph_model_model_first_200k.csv.completed.txt",
    "crawl_errors": M / "graph_model_model_first_200k.csv.errors.csv",
    "crawl_log": M / "graph_model_model_first_200k.nohup.log",
    "family01": A / "edges/csv/01_model_model_edges.csv",
    "lineage_merged": A / "evidence/top_level/model_lineage_edges_merged.csv",
    "card_metadata": A / "raw/models/all_model_readme_metadata_2026Aug28.jsonl",
    "evaluator": RQ1 / "scripts/eval_hf_tree_recall.py",
    "published_metrics": RQ1 / "hf_tree_random1k/smoke_test_first200k/metrics.json",
    "published_confusion": RQ1 / "hf_tree_random1k/smoke_test_first200k/label_confusion.csv",
    "random1k_sampling_summary": RQ1 / "hf_tree_random1k/sampling_summary.json",
    "random1k_run_script": RQ1 / "hf_tree_random1k/run_hf_tree_random1k.sh",
    "missing_pairs_ledger": MP / "missing_pairs.csv",
    "missing_pairs_summary": MP / "summary.json",
}

NORM = {"merge": "merged"}
CATEGORY = {"finetune": "Fine-tune", "adapter": "Adapter", "quantized": "Quantized", "merged": "Merge"}
PUBLISHED_TABLE_IV = {"Fine-tune": (3466, 3209, 257), "Adapter": (1350, 1280, 70),
                      "Quantized": (9284, 8800, 484), "Merge": (1589, 1379, 210),
                      "Total": (15689, 14668, 1021)}
SELECTED_ROWS = 200_000
Z = 1.959963984540054


# ----------------------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ids(path: Path, column: str) -> list[str]:
    """IDs as delta_models.py treats them: stripped, empty dropped (order kept)."""
    out = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            v = (r.get(column) or "").strip()
            if v:
                out.append(v)
    return out


def untyped(x: str) -> str:
    return x.split("::", 1)[1] if x.startswith("model::") else x


def first_char_class(model_id: str) -> str:
    c = model_id[:1]
    if c.isdigit():
        return "digit"
    if "A" <= c <= "Z":
        return "uppercase"
    if "a" <= c <= "z":
        return "lowercase"
    return "other"


def owner_bucket(model_id: str) -> str:
    """Owner-initial bucket inside the code-point prefix (digits, A-C, D-F, G-I, J, other)."""
    c = model_id[:1]
    if c.isdigit():
        return "0-9"
    for lo, hi in (("A", "C"), ("D", "F"), ("G", "I"), ("J", "J")):
        if lo <= c <= hi:
            return f"{lo}-{hi}" if lo != hi else lo
    if "K" <= c <= "Z":
        return "K-Z"
    if "a" <= c <= "z":
        return "a-z"
    return "other"


def wilson(k: int, n: int) -> dict:
    if n == 0:
        return {"k": k, "n": n, "p": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return {"k": k, "n": n, "p": p, "lo": max(0.0, centre - half), "hi": min(1.0, centre + half)}


def clustered_ratio(clusters: list[tuple[int, int]]) -> dict:
    """Ratio estimator sum(k)/sum(m) with a cluster-robust (linearization) SE.

    clusters: (k_i recovered, m_i reference pairs) per cluster. Also reports the design
    effect relative to the binomial variance and the implied effective number of pairs."""
    n = len(clusters)
    K = sum(k for k, _ in clusters)
    Mt = sum(m for _, m in clusters)
    p = K / Mt
    ss = sum((k - p * m) ** 2 for k, m in clusters)
    var = n / (n - 1) * ss / (Mt * Mt) if n > 1 else float("nan")
    se = math.sqrt(var)
    var_bin = p * (1 - p) / Mt
    deff = var / var_bin if var_bin > 0 else float("nan")
    return {"clusters": n, "k": K, "n": Mt, "p": p, "se": se,
            "lo": p - Z * se, "hi": p + Z * se,
            "binomial_se": math.sqrt(var_bin), "design_effect": deff,
            "effective_n": Mt / deff if deff and deff > 0 else None}


def cluster_bootstrap(clusters: list[tuple[int, int]], reps: int, seed: int) -> dict:
    rng = random.Random(seed)
    n = len(clusters)
    ks = [k for k, _ in clusters]
    ms = [m for _, m in clusters]
    est = []
    idx = range(n)
    for _ in range(reps):
        draw = rng.choices(idx, k=n)
        est.append(sum(ks[i] for i in draw) / sum(ms[i] for i in draw))
    est.sort()
    return {"reps": reps, "seed": seed, "clusters": n,
            "lo": est[int(0.025 * reps)], "hi": est[int(0.975 * reps) - 1],
            "sd": statistics.pstdev(est)}


def quantiles(values: list[float], qs=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)) -> dict:
    v = sorted(values)
    out = {}
    for q in qs:
        i = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
        out[f"q{int(q * 100):02d}"] = v[i]
    return out


def degree_bin(d: int) -> str:
    if d == 0:
        return "0"
    if d == 1:
        return "1"
    if d <= 4:
        return "2-4"
    if d <= 9:
        return "5-9"
    if d <= 49:
        return "10-49"
    return "50+"


DEG_BINS = ["0", "1", "2-4", "5-9", "10-49", "50+"]


def dist(counter: Counter, total: int, keys=None) -> dict:
    keys = keys if keys is not None else sorted(counter)
    return {k: {"n": counter.get(k, 0), "pct": round(100 * counter.get(k, 0) / total, 3) if total else None}
            for k in keys}


def tvd(c1: Counter, n1: int, c2: Counter, n2: int) -> float:
    keys = sorted(set(c1) | set(c2))
    return 0.5 * sum(abs(c1.get(k, 0) / n1 - c2.get(k, 0) / n2) for k in keys)


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261030)
    a = ap.parse_args()
    out_dir = a.out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        sys.exit(f"--out-dir {out_dir} is not empty")
    out_dir.mkdir(parents=True, exist_ok=True)

    R: dict = {"version": "v2026.10.30-01", "inputs": {}}
    for k, p in INPUTS.items():
        st = p.stat()
        R["inputs"][k] = {"path": str(p), "bytes": st.st_size, "mtime_epoch": int(st.st_mtime)}
    print("[1/9] inventories and delta", flush=True)

    # ---- 1. sampling frame -------------------------------------------------------------
    inv_list = read_ids(INPUTS["inventory_2026Aug28"], "modelId")
    base_list = read_ids(INPUTS["baseline_CIKM"], "model_id")
    delta_list = read_ids(INPUTS["delta_2026Aug28"], "modelId")
    inv, base = set(inv_list), set(base_list)
    delta_recomputed = sorted(inv - base)
    selected = delta_list[:SELECTED_ROWS]
    selected_set = set(selected)
    rest_set = set(delta_list[SELECTED_ROWS:])
    baseline_era = inv & base

    done_lines = [l.rstrip("\n") for l in INPUTS["completed"].open(encoding="utf-8")]
    queried = {l.strip() for l in done_lines if l.strip()}
    with INPUTS["crawl_errors"].open(newline="", encoding="utf-8") as fh:
        err_rows = list(csv.reader(fh))
    log_text = INPUTS["crawl_log"].read_text(encoding="utf-8", errors="replace")
    done_line = re.findall(r"Done: (\d+) completed, (\d+) failed, (\d+) already completed", log_text)
    tq = re.findall(r"Models: (\d+)model \[([0-9:]+),", log_text)

    frame = {
        "inventory_rows": len(inv_list), "inventory_unique": len(inv),
        "baseline_rows": len(base_list), "baseline_unique": len(base),
        "inventory_in_baseline": len(baseline_era),
        "baseline_not_in_inventory": len(base - inv),
        "delta_rows": len(delta_list), "delta_unique": len(set(delta_list)),
        "delta_equals_inventory_minus_baseline": delta_list == delta_recomputed,
        "delta_is_codepoint_sorted": delta_list == sorted(delta_list),
        "selected_rows": len(selected), "selected_unique": len(selected_set),
        "selected_first": selected[0], "selected_last": selected[-1],
        "first_excluded": delta_list[SELECTED_ROWS] if len(delta_list) > SELECTED_ROWS else None,
        "excluded_delta_rows": len(delta_list) - len(selected),
        "completed_lines": len(done_lines), "completed_unique": len(queried),
        "completed_equals_selected": queried == selected_set,
        "crawl_error_data_rows": max(0, len(err_rows) - 1),
        "crawl_log_done_line": [list(map(int, t)) for t in done_line],
        "crawl_log_rate_limit_messages": log_text.count("Rate limited by Hugging Face"),
        "crawl_log_final_progress": list(tq[-1]) if tq else None,
        "relation_filters_per_source": 4,
        "relation_filter_queries_minimum": 4 * len(queried),
    }
    R["frame"] = frame
    pop_of = {}  # model id -> population label within the inventory

    def population(mid: str) -> str:
        if mid in selected_set:
            return "queried_prefix_200k"
        if mid in rest_set:
            return "delta_not_queried"
        if mid in baseline_era:
            return "baseline_era"
        return "not_in_inventory"

    char_classes = {}
    for name, ids in (("queried_prefix_200k", selected_set), ("delta_not_queried", rest_set),
                      ("baseline_era", baseline_era), ("inventory_all", inv)):
        c = Counter(first_char_class(x) for x in ids)
        char_classes[name] = dist(c, len(ids), ["digit", "uppercase", "lowercase", "other"])
    R["first_char_class"] = char_classes
    R["queried_owner_bucket"] = dict(Counter(owner_bucket(x) for x in selected_set))

    # ---- 2. reference ------------------------------------------------------------------
    print("[2/9] reference", flush=True)
    raw_rows = []
    with INPUTS["reference"].open(newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        ref_header = rd.fieldnames
        for r in rd:
            raw_rows.append((r["Source"], r["Edge_type"], r["Target"]))
    triples = {(s, NORM.get(e, e), t) for s, e, t in raw_rows if s in queried}
    ref_labels = defaultdict(set)
    for s, e, t in sorted(triples):
        ref_labels[(s, t)].add(e)
    ref_label = {p: next(iter(v)) for p, v in ref_labels.items()}
    src_pairs = defaultdict(list)
    for (s, t) in ref_labels:
        src_pairs[s].append(t)
    targets = {t for _, t in ref_labels}
    ref_info = {
        "header": ref_header, "raw_rows": len(raw_rows), "raw_rows_distinct": len(set(raw_rows)),
        "raw_edge_type_counts": dict(Counter(e for _, e, _ in raw_rows)),
        "rows_source_not_completed": sum(1 for s, _, _ in raw_rows if s not in queried),
        "distinct_triples": len(triples), "distinct_pairs": len(ref_labels),
        "pairs_with_multiple_labels": sum(1 for v in ref_labels.values() if len(v) > 1),
        "self_loops": sum(1 for s, t in ref_labels if s == t),
        "ids_with_outer_whitespace": sum(1 for s, _, t in raw_rows if s != s.strip() or t != t.strip()),
        "sources_with_ge1_pair": len(src_pairs),
        "queried_sources_with_0_pairs": len(queried) - len(src_pairs),
        "distinct_derivatives": len(targets),
        "derivatives_with_multiple_reference_parents": sum(
            1 for c in Counter(t for _, t in ref_labels).values() if c > 1),
        "reference_pairs_whose_derivative_is_also_queried": sum(1 for _, t in ref_labels if t in queried),
        "reference_pairs_whose_derivative_is_also_a_reference_source": sum(1 for _, t in ref_labels if t in src_pairs),
        "derivative_population": dict(Counter(population(t) for t in targets)),
        "derivative_first_char_class": dict(Counter(first_char_class(t) for t in targets)),
        "pairs_per_source": quantiles([len(v) for v in src_pairs.values()]),
        "label_counts": dict(Counter(ref_label.values())),
    }
    R["reference"] = ref_info

    # ---- 3. released family 01 ---------------------------------------------------------
    print("[3/9] released Model->Model edges", flush=True)
    rel_labels = defaultdict(set)
    with INPUTS["family01"].open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rel_labels[(untyped(r["source"]), untyped(r["target"]))].add(r["edge_type"])
    out_deg = Counter(s for s, _ in rel_labels)
    in_deg = Counter(t for _, t in rel_labels)
    mm_endpoints = set(out_deg) | set(in_deg)
    released_triples = sum(len(v) for v in rel_labels.values())

    # ---- 4. Table IV reproduction ------------------------------------------------------
    recovered = {p for p in ref_labels if p in rel_labels}
    exact = {p for p in recovered if ref_labels[p] & rel_labels[p]}
    t4 = {}
    for lab, name in CATEGORY.items():
        ps = [p for p, l in ref_label.items() if l == lab]
        k = sum(1 for p in ps if p in recovered)
        t4[name] = (len(ps), k, len(ps) - k)
    t4["Total"] = (len(ref_labels), len(recovered), len(ref_labels) - len(recovered))
    pub = json.loads(INPUTS["published_metrics"].read_text())
    R["table_iv"] = {
        "recomputed": t4, "published": PUBLISHED_TABLE_IV,
        "matches_published": all(tuple(t4[k]) == v for k, v in PUBLISHED_TABLE_IV.items()),
        "label_exact_pairs": len(exact),
        "metrics_json_pair_recall_k": pub["pair_recall"]["k"],
        "metrics_json_reference_pairs": pub["reference_pairs"],
        "metrics_json_queried_sources": pub["queried_sources"],
        "wilson_recomputed": wilson(len(recovered), len(ref_labels)),
        "wilson_published": pub["pair_recall"],
        "released_mm_triples": released_triples, "released_mm_pairs": len(rel_labels),
        "released_distinct_sources": len(out_deg),
        "released_pairs_from_queried_sources": sum(1 for (s, _) in rel_labels if s in queried),
        "released_pairs_from_queried_absent_from_reference": sum(
            1 for p in rel_labels if p[0] in queried and p not in ref_labels),
    }
    # endpoint / edge / label evaluated separately
    ep = Counter()
    for p in ref_labels:
        s, t = p
        ep[("source_is_mm_endpoint", s in mm_endpoints)] += 1
        ep[("derivative_is_mm_endpoint", t in mm_endpoints)] += 1
        ep[("source_in_inventory", s in inv)] += 1
        ep[("derivative_in_inventory", t in inv)] += 1
        ep[("both_in_inventory_edge_missing", s in inv and t in inv and p not in recovered)] += 1
    R["endpoint_edge_label"] = {f"{k}={v}": n for (k, v), n in sorted(ep.items())}

    # ---- 5. graph coverage of the frame ------------------------------------------------
    print("[4/9] frame coverage of graph lineage", flush=True)
    pops = {"queried_prefix_200k": selected_set, "delta_not_queried": rest_set,
            "baseline_era": baseline_era}
    cov = {}
    for name, ids in pops.items():
        degs = [out_deg.get(x, 0) for x in ids]
        n = len(ids)
        cov[name] = {
            "models": n,
            "graph_parent_ge1": sum(1 for d in degs if d > 0),
            "graph_parent_ge1_pct": round(100 * sum(1 for d in degs if d > 0) / n, 3),
            "graph_child_pairs_total": sum(degs),
            "graph_child_pairs_mean": sum(degs) / n,
            "out_degree_bins": dist(Counter(degree_bin(d) for d in degs), n, DEG_BINS),
            "first_char_lowercase_pct": char_classes[name]["lowercase"]["pct"],
        }
    edge_src_pop = Counter(population(s) for s, _ in rel_labels)
    cov["graph_mm_pairs_by_source_population"] = dist(edge_src_pop, len(rel_labels),
                                                     ["queried_prefix_200k", "delta_not_queried",
                                                      "baseline_era", "not_in_inventory"])
    par_src_pop = Counter(population(s) for s in out_deg)
    cov["graph_parents_by_population"] = dist(par_src_pop, len(out_deg),
                                             ["queried_prefix_200k", "delta_not_queried",
                                              "baseline_era", "not_in_inventory"])
    top = out_deg.most_common(100)
    cov["top100_graph_parents_by_population"] = dict(Counter(population(s) for s, _ in top))
    cov["top20_graph_parents"] = [[s, d, population(s)] for s, d in top[:20]]
    # Hub-reference sources: their graph out-degree vs Hub derivative count
    cov["reference_sources_graph_parent_ge1"] = sum(1 for s in src_pairs if out_deg.get(s, 0) > 0)
    cov["queried_sources_graph_parent_ge1_without_reference_pairs"] = sum(
        1 for s in queried if out_deg.get(s, 0) > 0 and s not in src_pairs)
    R["coverage"] = cov

    # ---- 6. released label and evidence mix, queried vs all ----------------------------
    print("[5/9] label / evidence mix", flush=True)
    lab_all, lab_q = Counter(), Counter()
    for (s, _), labs in rel_labels.items():
        for l in labs:
            lab_all[l] += 1
            if s in queried:
                lab_q[l] += 1
    ev_all, ev_q, ev_pop = Counter(), Counter(), defaultdict(Counter)
    with INPUTS["lineage_merged"].open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ev = r["evidence"]
            ev_all[ev] += 1
            pop = population(r["source"])
            ev_pop[pop][ev] += 1
            if r["source"] in queried:
                ev_q[ev] += 1
    na, nq = sum(lab_all.values()), sum(lab_q.values())
    R["mix"] = {
        "released_label_all": dist(lab_all, na), "released_label_queried_sources": dist(lab_q, nq),
        "released_label_tvd": tvd(lab_all, na, lab_q, nq),
        "evidence_all": dist(ev_all, sum(ev_all.values())),
        "evidence_queried_sources": dist(ev_q, sum(ev_q.values())),
        "evidence_tvd": tvd(ev_all, sum(ev_all.values()), ev_q, sum(ev_q.values())),
        "evidence_by_source_population": {k: dist(v, sum(v.values())) for k, v in ev_pop.items()},
    }

    # ---- 7. card metadata (task, library, accessibility) ------------------------------
    print("[6/9] card metadata (streaming ~1.3 GB)", flush=True)
    status, ptag, lib = {}, {}, {}
    with INPUTS["card_metadata"].open(encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid = d.get("modelId")
            if not mid:
                continue
            status[mid] = d.get("status") or "unknown"
            md = d.get("readme_metadata") or {}
            if isinstance(md, dict):
                pt, lb = md.get("pipeline_tag"), md.get("library_name")
                ptag[mid] = pt if isinstance(pt, str) and pt else "none"
                lib[mid] = lb if isinstance(lb, str) and lb else "none"

    def profile(ids) -> dict:
        ids = sorted(ids)
        n = len(ids)
        st = Counter(status.get(x, "absent_from_card_file") for x in ids)
        pt = Counter(ptag.get(x, "none") for x in ids)
        lb = Counter(lib.get(x, "none") for x in ids)
        return {"n": n, "status": dist(st, n), "pipeline_tag_counter": pt, "library_counter": lb}

    groups = {
        "queried_prefix_200k": selected_set, "delta_not_queried": rest_set,
        "baseline_era": baseline_era, "reference_sources_5222": set(src_pairs),
        "graph_parents_in_inventory": {s for s in out_deg if s in inv},
    }
    prof = {k: profile(v) for k, v in groups.items()}
    top_tags = [t for t, _ in (prof["graph_parents_in_inventory"]["pipeline_tag_counter"]).most_common(12)]
    top_libs = [t for t, _ in (prof["graph_parents_in_inventory"]["library_counter"]).most_common(10)]
    card = {}
    for k, p in prof.items():
        pt, lb, n = p["pipeline_tag_counter"], p["library_counter"], p["n"]
        card[k] = {"n": n, "status": p["status"],
                   "pipeline_tag_top": dist(pt, n, top_tags),
                   "pipeline_tag_other_pct": round(100 * (n - sum(pt.get(t, 0) for t in top_tags)) / n, 3),
                   "library_top": dist(lb, n, top_libs),
                   "library_other_pct": round(100 * (n - sum(lb.get(t, 0) for t in top_libs)) / n, 3)}
    pairs_to_compare = [("queried_prefix_200k", "delta_not_queried"),
                        ("queried_prefix_200k", "baseline_era"),
                        ("reference_sources_5222", "graph_parents_in_inventory")]
    card["tvd"] = {}
    for x, y in pairs_to_compare:
        px, py = prof[x], prof[y]
        card["tvd"][f"{x}_vs_{y}"] = {
            "pipeline_tag": round(tvd(px["pipeline_tag_counter"], px["n"], py["pipeline_tag_counter"], py["n"]), 4),
            "library": round(tvd(px["library_counter"], px["n"], py["library_counter"], py["n"]), 4)}
    R["card_profile"] = card

    # ---- 8. per-source recovery and strata ---------------------------------------------
    print("[7/9] per-source recovery, clustering, strata", flush=True)
    per_src = []
    for s, ts in src_pairs.items():
        k = sum(1 for t in ts if (s, t) in recovered)
        per_src.append((s, k, len(ts)))
    per_src.sort(key=lambda x: (-x[2], x[0]))
    clusters = [(k, m) for _, k, m in per_src]
    rates = [k / m for _, k, m in per_src]
    owner_cl = defaultdict(lambda: [0, 0])
    for s, k, m in per_src:
        o = s.split("/", 1)[0]
        owner_cl[o][0] += k
        owner_cl[o][1] += m
    owner_clusters = [tuple(v) for v in owner_cl.values()]
    total_pairs = len(ref_labels)
    stats = {
        "pooled_wilson": wilson(len(recovered), total_pairs),
        "source_clustered": clustered_ratio(clusters),
        "source_cluster_bootstrap": cluster_bootstrap(clusters, a.bootstrap, a.seed),
        "owner_clustered": clustered_ratio(owner_clusters),
        "owner_cluster_bootstrap": cluster_bootstrap(owner_clusters, a.bootstrap, a.seed + 1),
        "per_source_rate_mean_unweighted": statistics.fmean(rates),
        "per_source_rate_quantiles": quantiles(rates),
        "sources_full_recovery": sum(1 for r in rates if r == 1.0),
        "sources_zero_recovery": sum(1 for r in rates if r == 0.0),
        "sources_partial_recovery": sum(1 for r in rates if 0 < r < 1),
        "owners": len(owner_clusters),
    }
    for top_n in (1, 10, 50):
        sub = per_src[:top_n]
        stats[f"top{top_n}_sources_share_of_pairs"] = sum(m for _, _, m in sub) / total_pairs
        stats[f"top{top_n}_sources_share_of_missing"] = sum(m - k for _, k, m in sub) / (total_pairs - len(recovered))
        rest = per_src[top_n:]
        stats[f"recovery_excluding_top{top_n}_sources"] = wilson(sum(k for _, k, _ in rest), sum(m for _, _, m in rest))
    miss_sorted = sorted(per_src, key=lambda x: -(x[2] - x[1]))
    stats["sources_accounting_for_50pct_missing"] = next(
        i + 1 for i in range(len(miss_sorted))
        if sum(m - k for _, k, m in miss_sorted[: i + 1]) >= 0.5 * (total_pairs - len(recovered)))
    stats["sources_with_any_missing"] = sum(1 for _, k, m in per_src if k < m)
    stats["largest_sources"] = [[s, k, m] for s, k, m in per_src[:10]]

    def stratum(keyf) -> dict:
        g = defaultdict(list)
        for s, k, m in per_src:
            g[keyf(s, m)].append((k, m))
        out = {}
        for key, cl in sorted(g.items(), key=lambda kv: str(kv[0])):
            K, N = sum(k for k, _ in cl), sum(m for _, m in cl)
            c = clustered_ratio(cl) if len(cl) > 1 else None
            out[str(key)] = {"sources": len(cl), "pairs": N, "recovered": K, "p": K / N,
                             "clustered_lo": c["lo"] if c else None, "clustered_hi": c["hi"] if c else None}
        return out

    strata = {
        "owner_bucket": stratum(lambda s, m: owner_bucket(s)),
        "pairs_per_source_bin": stratum(lambda s, m: degree_bin(m)),
        "source_graph_out_degree_bin": stratum(lambda s, m: degree_bin(out_deg.get(s, 0))),
        "source_pipeline_tag": stratum(lambda s, m: ptag.get(s, "none") if ptag.get(s, "none") in top_tags[:8] else "other/none"),
        "source_card_status": stratum(lambda s, m: status.get(s, "absent_from_card_file")),
    }
    # category stratum (pairs, clustered within source by category)
    cat_cl = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (s, t), l in ref_label.items():
        cat_cl[l][s][1] += 1
        cat_cl[l][s][0] += (s, t) in recovered
    strata["adaptation_category"] = {}
    for l, d in cat_cl.items():
        cl = [tuple(v) for v in d.values()]
        c = clustered_ratio(cl)
        w = wilson(c["k"], c["n"])
        strata["adaptation_category"][CATEGORY[l]] = {
            "sources": len(cl), "pairs": c["n"], "recovered": c["k"], "p": c["p"],
            "wilson_lo": w["lo"], "wilson_hi": w["hi"], "clustered_lo": c["lo"], "clustered_hi": c["hi"],
            "design_effect": c["design_effect"]}
    # derivative-side stratum (pair level)
    der = defaultdict(lambda: [0, 0])
    for (s, t) in ref_labels:
        key = first_char_class(t)
        der[key][1] += 1
        der[key][0] += (s, t) in recovered
    strata["derivative_first_char_class_pair_level"] = {
        k: {"pairs": v[1], "recovered": v[0], "p": v[0] / v[1]} for k, v in sorted(der.items())}
    stats["strata"] = strata
    R["statistics"] = stats

    # ---- 9. link to the missing-pair diagnostic ----------------------------------------
    print("[8/9] missing-pair cross-check", flush=True)
    with INPUTS["missing_pairs_ledger"].open(newline="", encoding="utf-8") as fh:
        mrows = list(csv.DictReader(fh))
    miss_set = {(r["reference_upstream"], r["reference_derivative"]) for r in mrows}
    expected_missing = set(ref_labels) - recovered
    c6 = [r for r in mrows if r["primary_root_cause"].startswith("C6")]
    alias_in_base = 0
    upstreams_c6 = set()
    for r in c6:
        aliases = [x for x in r["alias_parent_ids"].split(";") if x]
        upstreams_c6.add(r["reference_upstream"])
        if any(x in base for x in aliases):
            alias_in_base += 1
    renamed_sources = {r["reference_upstream"] for r in c6
                       if any(x in base for x in r["alias_parent_ids"].split(";") if x)}
    rest_cl = [(k, m) for s, k, m in per_src if s not in renamed_sources]
    link = {
        "ledger_rows": len(mrows), "ledger_equals_recomputed_missing": miss_set == expected_missing,
        "cause_by_owner_bucket": {}, "c6_pairs": len(c6),
        "c6_pairs_alias_in_CIKM_baseline": alias_in_base,
        "c6_distinct_upstreams": len(upstreams_c6),
        "reference_sources_with_baseline_alias_evidence": len(renamed_sources),
        "pairs_from_those_sources": sum(m for s, _, m in per_src if s in renamed_sources),
        "recovery_excluding_sources_with_baseline_alias": wilson(sum(k for k, _ in rest_cl), sum(m for _, m in rest_cl)),
    }
    cb = defaultdict(Counter)
    for r in mrows:
        cb[owner_bucket(r["reference_upstream"])][r["primary_root_cause"].split("_", 1)[0]] += 1
    link["cause_by_owner_bucket"] = {k: dict(v) for k, v in sorted(cb.items())}
    R["missing_pair_link"] = link

    # ---- write -------------------------------------------------------------------------
    print("[9/9] write outputs", flush=True)
    for k, p in INPUTS.items():
        R["inputs"][k]["sha256"] = sha256(p)
    (out_dir / "selection_audit.json").write_text(json.dumps(R, indent=1, default=list, sort_keys=True) + "\n")
    with (out_dir / "per_source_recovery.csv").open("x", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "reference_pairs", "recovered", "missing", "recovery",
                    "graph_out_degree", "owner_bucket", "pipeline_tag", "card_status"])
        for s, k, m in per_src:
            w.writerow([s, m, k, m - k, f"{k / m:.6f}", out_deg.get(s, 0), owner_bucket(s),
                        ptag.get(s, "none"), status.get(s, "absent_from_card_file")])
    f = frame
    flow = [
        ("S0", "Crawled Hub model inventory (2026-08-28)", f["inventory_unique"], "",
         "all_huggingface_models_2026Aug28.csv; unique stripped IDs"),
        ("S0b", "Context: VulChain model nodes (paper, evidence-qualified graph)", 1885384, "",
         "Not the sampling frame; the frame was drawn from the inventory, not from graph nodes"),
        ("S1", "Eligible: inventory IDs absent from the CIKM 2025 baseline (delta)", f["delta_unique"],
         f["inventory_in_baseline"], "Excluded: ID present in all_huggingface_models_CIKM.csv (delta_models.py)"),
        ("S2", "Selected: first 200,000 rows of the code-point-sorted delta", f["selected_unique"],
         f["excluded_delta_rows"], f"Excluded: rows >= 200,000 (IDs >= {f['first_excluded']!r}); crawl run with --start 0 --end 200000"),
        ("S3", "Queries attempted (sources; 4 relation filters each)", len(queried), 0,
         f"{f['relation_filter_queries_minimum']} relation-filter queries minimum; pagination requests not logged"),
        ("S4", "Successful queries (all 4 relations completed)", len(queried), f["crawl_error_data_rows"],
         "errors.csv holds a header only; log 'Done: 200000 completed, 0 failed'"),
        ("S5", "Nonempty model-tree responses (>=1 derivative)", ref_info["sources_with_ge1_pair"],
         ref_info["queried_sources_with_0_pairs"], "Excluded: Hub returned no derivative for any relation"),
        ("S6", "Reference parent-derivative pairs", ref_info["distinct_pairs"], 0,
         f"{ref_info['distinct_derivatives']} distinct derivatives"),
        ("S7", "Reference pairs recovered (exact IDs, any label)", len(recovered),
         len(ref_labels) - len(recovered), "Unrecovered pairs: see hub_reference_missing_pairs_2027"),
    ]
    with (out_dir / "selection_flow.csv").open("x", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["stage_id", "selection_stage", "count", "excluded_from_previous", "exclusion_reason_or_note"])
        w.writerows(flow)
    print(json.dumps({"table_iv_matches": R["table_iv"]["matches_published"],
                      "selected_equals_completed": frame["completed_equals_selected"],
                      "sources_with_pairs": ref_info["sources_with_ge1_pair"],
                      "source_clustered": stats["source_clustered"],
                      "owner_clustered": stats["owner_clustered"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
