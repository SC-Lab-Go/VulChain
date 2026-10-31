#!/usr/bin/env bash
# Created: 2026-10-15; version v2026.10.15-01
set -euo pipefail
umask 077
if [ "${RQ1_SCALING_APPROVED:-}" != "YES" ]; then
  echo "REFUSING: set RQ1_SCALING_APPROVED=YES only after explicit approval and load preflight." >&2
  exit 2
fi
unset HF_TOKEN HUGGING_FACE_HUB_TOKEN
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORK=<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working
ARCH="$WORK/2026_Fall_Extension/extension_updated_code/hugginggraph_v3_2026oct02_reproducibility"
EXP="$WORK/ICDE2027_RQ1_graph_quality_v2026_10_15"
RUN_ID="${1:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULT="$EXP/benchmarks/scalability/results-$RUN_ID"
if [ -e "$RESULT" ]; then echo "REFUSING existing result: $RESULT" >&2; exit 2; fi
mkdir -p "$RESULT/runs"
{
 date -u +%FT%TZ; hostname; uname -a; python3 --version; lscpu; free -h; df -hT "$EXP" "$ARCH"
 nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
} > "$RESULT/hardware.txt"
python3 "$EXP/scripts/prepare_scaling_inputs.py" --source "$ARCH/edges/csv" --output "$RESULT/inputs" > "$RESULT/input-preparation.stdout"
sha256sum "$ARCH/source/build_hugginggraph_v3.py" "$EXP/scripts/build_hugginggraph_scaling.py" > "$RESULT/builder.sha256"

capture_load() {
  local output="$1"
  { date -u +%FT%TZ; cat /proc/loadavg; free -h; ps -eo user,comm,%cpu,%mem,etime --sort=-%cpu | sed -n '1,25p'; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true; } > "$output"
}
run_one() {
  local size="$1" rep="$2"
  local stem="$RESULT/runs/pct-$(printf '%03d' "$size")-run-$rep"
  capture_load "$stem.load-before.txt"
  /usr/bin/time -v -o "$stem.time" python3 "$EXP/scripts/build_hugginggraph_scaling.py" \
    --reference-builder "$ARCH/source/build_hugginggraph_v3.py" \
    --edge-dir "$RESULT/inputs/pct-$(printf '%03d' "$size")" --output "$stem.dot" \
    > "$stem.stdout" 2> "$stem.stderr"
  capture_load "$stem.load-after.txt"
}

# Balanced order reduces systematic warm-cache/time-order confounding.
run_one 25 1; run_one 50 1; run_one 100 1
run_one 50 2; run_one 100 2; run_one 25 2
run_one 100 3; run_one 25 3; run_one 50 3
python3 "$EXP/scripts/summarize_scaling_benchmarks.py" --result "$RESULT"
date -u +%FT%TZ > "$RESULT/COMPLETE"
echo "Completed: $RESULT"
