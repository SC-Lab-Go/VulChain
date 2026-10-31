#!/usr/bin/env python3
"""Verify a downloaded VulChain.dot against the published checksum and counts.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Confirm the graph file is the published VulChain.dot (SHA-256) and that its
         node, edge, entity-type and per-relationship counts match
         relationships/relationship_catalog.csv. Streams the file; uses the
         standard library only.

Command: python reproducibility/verify_graph.py graph/VulChain.dot
"""

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHA256 = "25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97"
SIZE = 1006495786
NODES = {"model": 1885384, "dataset": 414723, "space": 712728, "github": 96678,
         "library": 2148, "license": 4888, "task": 839, "agent": 11}
EDGES, TOTAL_NODES, MODEL_MODEL = 7666919, 3117399, 966035
EDGE = re.compile(r'^\s*("(?:[^"\\]|\\.)*")\s*->\s*("(?:[^"\\]|\\.)*")\s*\[.*edge_type=("(?:[^"\\]|\\.)*")')


def node_type(node):
    return "github" if node.startswith("https://github.com/") else node.split("::", 1)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dot", type=Path)
    args = parser.parse_args()

    checks = []
    size = args.dot.stat().st_size
    checks.append(("file size", size, SIZE))
    digest = hashlib.sha256()
    with args.dot.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    checks.append(("sha256", digest.hexdigest(), SHA256))

    nodes = collections.defaultdict(set)
    family = collections.Counter()
    edges = 0
    with args.dot.open(encoding="utf-8") as handle:
        for line in handle:
            m = EDGE.match(line)
            if not m:
                continue
            s, t, et = (json.loads(x) for x in m.groups())
            st, tt = node_type(s), node_type(t)
            nodes[st].add(s)
            nodes[tt].add(t)
            family[(st, tt, et)] += 1
            edges += 1
    checks.append(("edges", edges, EDGES))
    checks.append(("nodes", sum(map(len, nodes.values())), TOTAL_NODES))
    checks.append(("model->model edges", sum(v for (a, b, _), v in family.items() if a == b == "model"), MODEL_MODEL))
    for kind, want in NODES.items():
        checks.append((f"{kind} nodes", len(nodes[kind]), want))
    with (REPO / "relationships" / "relationship_catalog.csv").open(newline="") as handle:
        for r in csv.DictReader(handle):
            types = {x.strip() for x in r["edge_type"].split(";")}
            got = sum(v for (a, b, et), v in family.items()
                      if a == r["source_entity"] and b == r["target_entity"] and et in types)
            checks.append((f"family {r['number']} {r['relationship']}", got, int(r["edges"])))

    failed = 0
    for name, got, want in checks:
        status = "PASS" if got == want else "FAIL"
        failed += status == "FAIL"
        print(f"{status}  {name}: {got:,}" if isinstance(got, int) else f"{status}  {name}: {got}")
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
