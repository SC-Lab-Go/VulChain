# Controlled DOT-assembly scaling preflight

Created: 2026-10-15  
Version: v2026.10.15-01  
Status: prepared, syntax-checked, **not executed**.

The immutable 17 archived edge CSVs contain 7,775,872 edges and approximately
0.618 GiB. `prepare_scaling_inputs.py` constructs exact-count deterministic
systematic 25% and 50% subsets independently inside every family; 100% uses
read-only symlinks. This preserves all 17 families and their proportions up to
unavoidable integer rounding. Subset preparation is outside timed assembly.

The prior 100% assembly took 51.87 s, used 0.447 GiB peak RSS, and emitted a
0.951 GiB DOT. Nine proposed outputs should require approximately 5.0 GiB,
plus less than 0.5 GiB of sampled inputs and logs. Reserve at least 10 GiB free,
4 CPU cores, 16 GiB RAM, and 30 minutes. The release builder has fixed
full-release cardinality assertions, so the suite uses
`scripts/build_hugginggraph_scaling.py`. That derived program imports the
release builder's family order, schema, endpoint-type validation, and DOT
serialization while omitting only fixed size assertions. Every size uses the
same derived builder, and the 100% DOT must match the release SHA-256. The
builder is single-process and has no GPU path; GPUs are recorded but not used.

Each size has three independent process executions in balanced order. Every
run records `/usr/bin/time -v`, input/output bytes, edge throughput, output
SHA-256, hardware, and before/after load snapshots. Outputs go only to a new
`benchmarks/scalability/results-*` directory. The script refuses an existing
destination and contains no deletion, archive write, API, or network command.
It also refuses to start without the explicit approval flag.

Immediately before execution, confirm sufficient disk and absence of material
CPU/I/O contention:

```bash
hostname
free -h
df -h <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working
ps -eo user,comm,%cpu,%mem,etime --sort=-%cpu | head -20
nvidia-smi
```

After explicit approval, the exact command is:

```bash
cd <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working
RQ1_SCALING_APPROVED=YES bash \
  ICDE2027_RQ1_graph_quality_v2026_10_15/benchmarks/run_scaling_local.sh \
  local-20261015-scaling-01
```

Do not infer linear scaling until `scaling_performance.csv` contains all nine
successful runs and the variance and residuals have been examined.
