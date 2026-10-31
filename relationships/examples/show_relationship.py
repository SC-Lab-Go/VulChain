#!/usr/bin/env python3
"""Print the first edges of one relationship family from VulChain.dot.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Small, streaming example of how each relationship family is stored
         in the DOT graph. Uses the standard library only and never loads the
         whole graph into memory.

Examples:
    python relationships/examples/show_relationship.py graph/VulChain.dot --family 1
    python relationships/examples/show_relationship.py graph/VulChain.dot --family 17 --limit 3
"""

import argparse
import csv
import json
import re
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "relationship_catalog.csv"
EDGE = re.compile(r'^\s*("(?:[^"\\]|\\.)*")\s*->\s*("(?:[^"\\]|\\.)*")\s*\[.*edge_type=("(?:[^"\\]|\\.)*")')


def node_type(node):
    return "github" if node.startswith("https://github.com/") else node.split("::", 1)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dot", type=Path)
    parser.add_argument("--family", type=int, required=True, help="relationship number 1-17")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    with CATALOG.open(newline="") as handle:
        family = next(r for r in csv.DictReader(handle) if int(r["number"]) == args.family)
    edge_types = {t.strip() for t in family["edge_type"].split(";")}
    print(f"{family['number']}. {family['relationship']}: {family['source_entity']} -> "
          f"{family['target_entity']} ({', '.join(sorted(edge_types))})")
    shown = 0
    with args.dot.open(encoding="utf-8") as handle:
        for line in handle:
            m = EDGE.match(line)
            if not m:
                continue
            source, target, edge_type = (json.loads(x) for x in m.groups())
            if (edge_type in edge_types and node_type(source) == family["source_entity"]
                    and node_type(target) == family["target_entity"]):
                print(f"  {source} -[{edge_type}]-> {target}")
                shown += 1
                if shown >= args.limit:
                    break


if __name__ == "__main__":
    main()
