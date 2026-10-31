"""Parse HuggingGraph_v3.dot into model nodes and Model->Model edges (read-only).

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: DOT reader for the Hub-reference missing-pair diagnostic. Opens the DOT
read-only; IDs are DOT-unescaped and returned without the model:: prefix.
"""
import re
from collections import Counter

EDGE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)" -> "((?:[^"\\]|\\.)*)" \[(.*)\];\s*$')
ATTR = re.compile(r'edge_type="((?:[^"\\]|\\.)*)"')
UNESCAPE = re.compile(r'\\(.)')


def unescape(x):
    """Undo DOT string escaping (backslash-escaped characters)."""
    return UNESCAPE.sub(r"\1", x) if "\\" in x else x


def load(path):
    """Return (model_nodes, mm_edges, stats). Model IDs are returned without the model:: prefix."""
    nodes = set()
    mm = set()
    stats = Counter()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if "->" not in line:
                stats["non_edge_lines"] += 1
                continue
            m = EDGE.match(line)
            if not m:
                stats["unparsed_edge_lines"] += 1
                continue
            s, t, attrs = m.groups()
            s, t = unescape(s), unescape(t)
            a = ATTR.search(attrs)
            e = unescape(a.group(1)) if a else None
            stats["edges"] += 1
            sm, tm = s.startswith("model::"), t.startswith("model::")
            if sm:
                nodes.add(s[7:])
            if tm:
                nodes.add(t[7:])
            if sm and tm:
                mm.add((s[7:], e, t[7:]))
                stats["mm_edge_lines"] += 1
                stats["mm_type:" + str(e)] += 1
    stats["model_nodes"] = len(nodes)
    stats["mm_edges_distinct"] = len(mm)
    return nodes, mm, stats
