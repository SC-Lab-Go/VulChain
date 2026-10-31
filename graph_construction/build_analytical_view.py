#!/usr/bin/env python3
"""Build VulChain.dot, the evidence-qualified analytical view of the October 2 graph.

Created: 2026-10-30
Version: v2026.10.30-04
Purpose: Produce the graph reported in the manuscript (tab:master_table):
         7,666,919 edges and 3,117,399 nodes over 8 entity types and 17
         relationship families.

VulChain.dot equals the October 2, 2026 HuggingGraph v3 release except for
relationship 2 (Dataset -> Model). There it keeps only training-data
declarations that resolve to exactly one Dataset in the crawled inventory
(evidence/top_level/dataset_model_edges_validated.csv, 253,111 edges) instead
of all 362,064 declared references.

Only production code is used, taken from the embedded scripts in
vulchain_graph.py:
- prepare_hugginggraph_v3_edges.copy_core() type-prefixes the validated file;
- build_hugginggraph_v3.build() validates every edge and writes the DOT.
The only change is build()'s expected counts, set to the analytical totals.
The other 16 relationship files are the released ones, unchanged.

Command: python graph_construction/build_analytical_view.py --release-dir <extracted release> --output VulChain.dot
"""

import argparse
import ast
import csv
import importlib
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vulchain_graph as bundle  # noqa: E402

DATASET_MODEL_EDGES = 253_111
EXPECTED_EDGES = 7_666_919
EXPECTED_TOTAL_NODES = 3_117_399
NODE_CHANGES = {"model": 1_885_384, "dataset": 414_723}


def production_copy_core():
    """copy_core() and its helpers, extracted verbatim from the embedded prepare script.

    The prepare module itself is not imported because it imports huggingface_hub,
    which only its network-dependent Space reconciliation step needs.
    """
    source = bundle.SOURCES["prepare_hugginggraph_v3_edges"]
    tree = ast.parse(source)
    wanted = {"FIELDS", "typed", "open_writer", "copy_core"}
    nodes = [n for n in tree.body
             if (isinstance(n, ast.FunctionDef) and n.name in wanted)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in wanted for t in n.targets))]
    namespace = {"csv": csv, "Path": Path}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "prepare_hugginggraph_v3_edges.py", "exec"), namespace)
    return namespace["copy_core"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release-dir", type=Path, required=True,
                        help="extracted hugginggraph_v3_2026oct02_reproducibility directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    bundle._install(HERE)
    builder = importlib.import_module("build_hugginggraph_v3")
    builder.SUBGRAPHS = tuple((name, f, s, t, DATASET_MODEL_EDGES if name == "model-dataset" else n)
                              for name, f, s, t, n in builder.SUBGRAPHS)
    builder.EXPECTED_NODES = dict(builder.EXPECTED_NODES, **NODE_CHANGES)
    builder.EXPECTED_EDGES = EXPECTED_EDGES
    builder.EXPECTED_TOTAL_NODES = EXPECTED_TOTAL_NODES

    release_edges = args.release_dir / "edges" / "csv"
    with tempfile.TemporaryDirectory(prefix="vulchain-edges-") as tmp:
        edge_dir = Path(tmp)
        for _name, filename, *_ in builder.SUBGRAPHS:
            if filename != "02_model_dataset_edges.csv":
                (edge_dir / filename).symlink_to(release_edges / filename)
        count = production_copy_core()(args.release_dir / "evidence" / "top_level" / "dataset_model_edges_validated.csv",
                                       edge_dir / "02_model_dataset_edges.csv", "dataset", "model")
        if count != DATASET_MODEL_EDGES:
            raise SystemExit(f"Validated Dataset->Model file has {count:,} rows, expected {DATASET_MODEL_EDGES:,}")
        counters, nodes = builder.build(edge_dir, args.output)

    print("VulChain analytical view")
    for name, *_ in builder.SUBGRAPHS:
        print(f"  {name:22} {counters[name]:12,}")
    print(f"  {'edges':22} {counters['edges']:12,}")
    for kind, values in nodes.items():
        print(f"  {kind + ' nodes':22} {len(values):12,}")
    print(f"  {'nodes':22} {sum(map(len, nodes.values())):12,}")
    print(f"DOT: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
