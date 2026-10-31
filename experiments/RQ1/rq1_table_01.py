#!/usr/bin/env python3
"""Reproduce Table tab:master_table (RQ1).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: "VulChain statistics (October 2, 2026)" - unique edges and endpoint
         nodes for the 17 relationship families, and the union node count by
         entity type.

The manuscript reports the inventory-resolved analytical view (default,
--view analytical): the released per-family edge files with relationship 2
(Dataset->Model) replaced by evidence/top_level/dataset_model_edges_validated.csv,
which keeps only training-data declarations that resolve to exactly one
Dataset in the crawled inventory. This view is graph/VulChain.dot.
--view released reproduces the counts of the full October 2 HuggingGraph v3
release (HuggingGraph_v3.dot) from the same code.

Inputs:  <release>/edges/csv/01..17_*.csv
         <release>/evidence/top_level/dataset_model_edges_validated.csv (analytical view)
Output:  outputs/RQ1/rq1_table_01_<view>.csv, outputs/RQ1/rq1_table_01_<view>_verification.md
Command: python experiments/RQ1/rq1_table_01.py --release-dir <extracted release archive>
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

FAMILIES = (
    ("Model -> Model", "01_model_model_edges.csv", "model", "model"),
    ("Dataset -> Model", "02_model_dataset_edges.csv", "dataset", "model"),
    ("Dataset -> Dataset", "03_dataset_dataset_edges.csv", "dataset", "dataset"),
    ("Model -> Library", "04_model_library_edges.csv", "model", "library"),
    ("Dataset -> Library", "05_dataset_library_edges.csv", "dataset", "library"),
    ("Model -> License", "06_model_license_edges.csv", "model", "license"),
    ("Dataset -> License", "07_dataset_license_edges.csv", "dataset", "license"),
    ("Model -> Task", "08_model_task_edges.csv", "model", "task"),
    ("Dataset -> Task", "09_dataset_task_edges.csv", "dataset", "task"),
    ("Model -> GitHub", "10_model_github_edges.csv", "model", "github"),
    ("Dataset -> GitHub", "11_dataset_github_edges.csv", "dataset", "github"),
    ("Model -> Space", "12_model_space_edges.csv", "model", "space"),
    ("Dataset -> Space", "13_dataset_space_edges.csv", "dataset", "space"),
    ("Space -> GitHub", "14_space_github_edges.csv", "space", "github"),
    ("Space -> License", "15_space_license_edges.csv", "space", "license"),
    ("Space -> Task", "16_space_task_edges.csv", "space", "task"),
    ("Space -> Agent", "17_space_agent_edges.csv", "space", "agent"),
)
NODE_TYPES = ("model", "dataset", "space", "github", "library", "license", "task", "agent")

# Values printed in the manuscript (experiments.tex, \label{tab:master_table}).
MANUSCRIPT_ANALYTICAL = {
    "Model -> Model": (966035, 978868), "Dataset -> Model": (253111, 194462),
    "Dataset -> Dataset": (12541, 15172), "Model -> Space": (941121, 487287),
    "Dataset -> Space": (83061, 85762), "Model -> GitHub": (962855, 729920),
    "Dataset -> GitHub": (188888, 196768), "Space -> GitHub": (113755, 90895),
    "Model -> Library": (1311386, 1214466), "Dataset -> Library": (16864, 16467),
    "Model -> License": (1090845, 1092560), "Dataset -> License": (331317, 332328),
    "Space -> License": (420369, 420557), "Model -> Task": (577077, 541491),
    "Dataset -> Task": (317412, 211454), "Space -> Task": (43223, 42229),
    "Space -> Agent": (37059, 37016),
    "nodes": {"model": 1885384, "dataset": 414723, "space": 712728, "github": 96678,
              "library": 2148, "license": 4888, "task": 839, "agent": 11},
    "total_edges": 7666919, "total_nodes": 3117399,
}
# Full October 2 HuggingGraph v3 release (build_hugginggraph_v3.py constants; SUBGRAPH_COUNTS.csv).
RELEASED = dict(MANUSCRIPT_ANALYTICAL, **{
    "Dataset -> Model": (362064, 287539),
    "nodes": {"model": 1888591, "dataset": 431324, "space": 712728, "github": 96678,
              "library": 2148, "license": 4888, "task": 839, "agent": 11},
    "total_edges": 7775872, "total_nodes": 3137207,
})


def typed(value, kind):
    """As prepare_hugginggraph_v3_edges.typed(); GitHub targets are already URLs."""
    if kind == "github":
        return value
    prefix = f"{kind}::"
    return value if value.startswith(prefix) else prefix + value


def family_stats(path, source_type, target_type, union):
    edges, nodes = set(), set()
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            s, t = typed(row["source"], source_type), typed(row["target"], target_type)
            edges.add((s, row["edge_type"], t))
            nodes.update((s, t))
            union[source_type].add(s)
            union[target_type].add(t)
    return len(edges), len(nodes)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release-dir", type=Path, required=True,
                        help="extracted hugginggraph_v3_2026oct02_reproducibility directory")
    parser.add_argument("--view", choices=("analytical", "released"), default="analytical")
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ1")
    args = parser.parse_args()

    expected = MANUSCRIPT_ANALYTICAL if args.view == "analytical" else RELEASED
    union = {k: set() for k in NODE_TYPES}
    rows, cmp_rows, ok = [], [], True
    for name, filename, st, tt in FAMILIES:
        path = args.release_dir / "edges" / "csv" / filename
        if args.view == "analytical" and filename.startswith("02_"):
            path = args.release_dir / "evidence" / "top_level" / "dataset_model_edges_validated.csv"
        e, n = family_stats(path, st, tt, union)
        rows.append((name, e, n))
        for label, got, want in ((name + " edges", e, expected[name][0]), (name + " nodes", n, expected[name][1])):
            ok &= got == want
            cmp_rows.append((label, f"{got:,}", f"{want:,}", "MATCH" if got == want else "MISMATCH"))
    for kind in NODE_TYPES:
        got, want = len(union[kind]), expected["nodes"][kind]
        ok &= got == want
        cmp_rows.append((f"union {kind} nodes", f"{got:,}", f"{want:,}", "MATCH" if got == want else "MISMATCH"))
    totals = (("total edges", sum(e for _, e, _ in rows), expected["total_edges"]),
              ("total nodes", sum(len(s) for s in union.values()), expected["total_nodes"]))
    for label, got, want in totals:
        ok &= got == want
        cmp_rows.append((label, f"{got:,}", f"{want:,}", "MATCH" if got == want else "MISMATCH"))

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / f"rq1_table_01_{args.view}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relationship", "edges", "nodes"])
        writer.writerows(rows)
        writer.writerows([(f"union:{k}", "", len(union[k])) for k in NODE_TYPES])
    return v.write_report(args.out / f"rq1_table_01_{args.view}_verification.md",
                          f"RQ1 Table tab:master_table ({args.view} view)", cmp_rows, ok,
                          ["Expected values are transcribed from experiments.tex (analytical) or "
                           "build_hugginggraph_v3.py (released); they are compared, never emitted."])


if __name__ == "__main__":
    raise SystemExit(main())
