#!/usr/bin/env python3
"""Benchmark-only DOT builder retaining structural checks but not release sizes.

Created: 2026-10-15
Version: v2026.10.15-01

The reference release builder is imported for its schema, family order, type
checks, and DOT serialization. Only its fixed October 2 cardinality assertions
are omitted so controlled subsets can be assembled.
"""
from __future__ import annotations
import argparse, csv, importlib.util
from collections import Counter
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--reference-builder",type=Path,required=True)
    ap.add_argument("--edge-dir",type=Path,required=True); ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    spec=importlib.util.spec_from_file_location("release_builder",args.reference_builder)
    ref=importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
    edge_dir=args.edge_dir.expanduser().resolve(); output=args.output.expanduser().resolve()
    if output.exists(): raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    counters=Counter(); nodes={kind:set() for kind in ref.EXPECTED_NODES}
    with output.open("x",encoding="utf-8") as dot_file:
        dot_file.write('digraph HuggingGraph {\n  graph [rankdir="LR"];\n  node [shape="box"];\n')
        for name,filename,source_type,target_type,_expected_edges in ref.SUBGRAPHS:
            path=edge_dir/filename
            if not path.is_file(): raise FileNotFoundError(path)
            with path.open(newline="",encoding="utf-8") as input_file:
                reader=csv.DictReader(input_file)
                if reader.fieldnames != ref.FIELDS: raise ValueError(f"Unexpected schema in {path}: {reader.fieldnames}")
                for line_number,row in enumerate(reader,start=2):
                    source,target,edge_type=row["source"],row["target"],row["edge_type"]
                    context=f"{filename}:{line_number}"
                    ref.validate_node(source,source_type,context);ref.validate_node(target,target_type,context)
                    label="merge" if edge_type == "merged" else edge_type
                    dot_file.write(f"  {ref.dot_string(source)} -> {ref.dot_string(target)} [label={ref.dot_string(label)}, edge_type={ref.dot_string(edge_type)}];\n")
                    nodes[source_type].add(source);nodes[target_type].add(target)
                    counters[name]+=1;counters["edges"]+=1
        dot_file.write("}\n")
    print("HuggingGraph controlled assembly")
    for name,*_ in ref.SUBGRAPHS: print(f"{name:24} {counters[name]:12,}")
    print(f"{'Total edges':24} {counters['edges']:12,}")
    for kind in ref.EXPECTED_NODES: print(f"{kind + ' nodes':24} {len(nodes[kind]):12,}")
    print(f"{'Total nodes':24} {sum(map(len,nodes.values())):12,}")
    print(f"DOT: {output}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
