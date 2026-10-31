#!/usr/bin/env bash
# Created: 2026-10-30  Version: v2026.10.30-01
# Purpose: Check the interpreter and the optional graph-construction dependencies.
set -u

python=${PYTHON:-python3}
"$python" - <<'EOF'
import importlib.util
import sys

ok = sys.version_info >= (3, 10)
print(f"{'PASS' if ok else 'FAIL'}  Python {sys.version.split()[0]} (>= 3.10 required)")
print("PASS  experiments/ and reproducibility/ use the standard library only")
for module, needed_by in [("huggingface_hub", "graph_construction prepare (Space reconciliation)"),
                          ("yaml", "graph_construction README attribute stages"),
                          ("pandas", "graph_construction (pinned in requirements.txt)")]:
    found = importlib.util.find_spec(module) is not None
    print(f"{'PASS' if found else 'MISSING'}  {module:16} needed by {needed_by}")
sys.exit(0 if ok else 1)
EOF
command -v zstd >/dev/null && echo "PASS  zstd (to extract the graph release archive)" \
                           || echo "MISSING  zstd (to extract the graph release archive)"
