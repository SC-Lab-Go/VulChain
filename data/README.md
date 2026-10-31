# Frozen experiment inputs

Everything here is read-only input to the entry points in `experiments/`.

## `rq_snapshot/`

These are the comparison-level outputs of the RQ2–RQ5 analysis snapshot
`v2026.10.27-unified-01-b9e3e4d60181fa58`, captured at 2026-10-30 20:08:45 UTC.
`INPUT_MANIFEST.json` lists each file's SHA-256. Every entry point checks those
hashes before it runs.

| File | Rows | Content |
|---|---:|---|
| `canonical_comparisons.jsonl` | 24,150 | One base–derivative–prompt–category comparison: policy flags, adaptation label and stratum, class/instance state, artifact hashes |
| `qualified_occurrences.jsonl` | 58,558 | Verified finding rows: model, prompt ID, category, artifact hash |
| `evaluated_relationships.csv` | 437 | Evaluated base–derivative pairs |
| `evaluated_model_manifest.csv` | 482 | Evaluated models and their execution status |
| `model_status_audit.csv` | 6,963 | All selected models: verified prompt counts and completion status |
| `rq5_graph_export/` | — | Cohort subgraph of the October 2 graph (lineage, Model→Space, Model→GitHub, Space→GitHub) with release row references |

These files contain no raw model responses and no generated package names,
domains, or URLs. Artifacts appear only as SHA-256 hashes. The raw measurement
ledger (about 4 GB of responses and findings) is not distributed.

## `table2_baseline/`

`table2_stage_records.csv` holds the one-hop and static-ready (parent, child,
label) records of the frozen Table II baseline v2026.10.27-04. It was derived
from `table2_frozen_snapshot.v2026.10.27-04.json`, whose SHA-256 is recorded
in `BASELINE_METADATA.json`. Machine-specific paths were dropped.

## `manuscript_macros/`

These are the LaTeX macro files the manuscript loads. They are the expected
values the entry points compare against; the entry points never copy them into
their outputs.
