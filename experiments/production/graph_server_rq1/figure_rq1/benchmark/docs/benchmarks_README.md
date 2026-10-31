# Offline construction benchmark plan

Created: 2026-10-15  
Version: v2026.10.15-01  
Status: **local-server execution authorized; Slurm not required**

The authorized local-server runner is:

```bash
cd <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working
bash ICDE2027_RQ1_graph_quality_v2026_10_15/benchmarks/run_offline_benchmarks_local.sh
```

It creates a new timestamped, persistent `benchmarks/results-local-*`
directory and refuses to reuse an existing destination. The stages are
CPU/RAM/I/O-bound; the installed GPUs are recorded for hardware provenance but
are not used by the archived Python programs.

The Slurm runner below is retained as an alternative only; it is not used for
the authorized local-server run.

Submit only after permission, from the scheduler submission host:

```bash
cd <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working
sbatch ICDE2027_RQ1_graph_quality_v2026_10_15/benchmarks/run_offline_benchmarks.slurm
```

Alternatively obtain an interactive allocation with at least 8 CPUs, 64 GiB
RAM, eight hours, and 50 GiB allocation-local scratch, then execute the body of
the script. The guard intentionally refuses execution without `SLURM_JOB_ID`
and `SLURM_TMPDIR`.

Run that command only on a Slurm login host where the absolute project/archive
paths exist. Before approval/submission, verify `sacctmgr show assoc user=$USER`
and `sinfo -p defq`; the current inspection host has no Slurm client. Also
confirm that `SLURM_TMPDIR` is created with at least 50 GiB free, because the
job refuses to fall back to login-node or home-directory scratch.

The four stages are: model-lineage extraction; validated Dataset→Model
extraction; Dataset→Dataset metadata/README extraction including SQLite
staging; and final DOT assembly from all 17 archived edge files. Every command
uses only archived local inputs. `prepare_hugginggraph_v3_edges.py` is excluded
because it contains `HfApi().space_info(...)` calls and therefore is not a
valid offline benchmark.

For each stage `/usr/bin/time -v` records elapsed time, user/system CPU, CPU
percentage, and peak RSS. The script also records input/output bytes, hashes
the assembled DOT, and captures allocation, CPU, memory, filesystem, kernel,
and Python details without dumping environment variables. The final summarizer
writes `performance_summary.csv` and JSON with input/output records and bytes,
effective scanned-record/s and emitted-record/s, per-output SHA-256 hashes,
CPU time, peak RSS, and wall time. Do not use prior login-node reruns as the
paper benchmark.

Required immutable inputs occupy approximately 17 GiB (`raw/`) plus 1.6 GiB
(`edges/`); the archived DOT is approximately 974 MiB. The allocation needs
additional space for extraction outputs, SQLite state, and the new DOT.
