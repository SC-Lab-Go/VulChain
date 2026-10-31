<!-- Created: 2026-10-30 · Version: v2026.10.30-02 · Purpose: verify which graph Figure 7 benchmarked and the throughput denominator -->

# Figure 7 throughput audit

**Verdict.** Figure 7 benchmarked the **released full graph**:
- 7,775,872 edges and 3,137,207 nodes;
- output sha `348d92cd…` in all three full-size runs;
- the throughput denominator matches that graph.

The reported 53.34 s and ≈146K edges/s are correct for that graph. **No throughput change is needed.** The only correction is to name the benchmarked graph explicitly, because the manuscript's headline totals are those of the analytical view (7,666,919 edges).

## Evidence (`ICDE2027_RQ1_graph_quality_v2026_10_15/benchmarks/scalability/results-local-20261015-scaling-03/`, marked `COMPLETE`)

| Question | Finding | Source |
|---|---|---|
| 1. Which graph was processed? | The released graph. The 100% inputs are the 17 released per-family CSVs, **byte-identical to `hugginggraph_v3…/edges/csv`** (17/17 sha256 match, re-verified today); 7,775,872 records, 663,327,124 bytes. | `inputs/SCALING_INPUT_MANIFEST.json`; re-hash |
| Output | All three 100% outputs are 1,020,652,753 bytes with sha `348d92cd…`, the same as `HuggingGraph_v3.dot`. Re-hashed from disk today (`runs/pct-100-run-{1,2,3}.dot`). `scaling_summary.json`: `matches_official_release: true`, `output_nodes: 3137207`. | re-hash; summary |
| 2. What does the runtime include? | `/usr/bin/time -v` around one Python process (`scripts/build_hugginggraph_scaling.py`). That process starts the interpreter, imports the release builder (schema, family order, type checks, DOT serialization), reads and validates all 17 CSVs, writes the DOT, and counts nodes. **Not included:** Hub/API acquisition, README download, per-family relationship extraction (timed separately: lineage 40.83 s, D→M 25.43 s, D→D 199.33 s), graph-database loading or queries, model inference. | `run_scaling_local.sh` :33–35; wrapper source; `cohort_graph_audit.md` §6 |
| Wall times (100%) | 54.36 / 53.21 / 52.45 s → mean **53.34 s** (SD 0.96) | `scaling_performance.csv` |
| Peak RSS | 468,160 / 468,492 / 468,152 KiB → **0.447 GiB** | same |
| 3. Does the denominator match? | **Yes.** Mean of per-run rates = 145,811 edges/s (SD 2,620). Edges ÷ mean wall = 7,775,872 / 53.34 = 145,779 edges/s. Both round to ≈146K. With the analytical count the rate would be 7,666,919 / 53.34 = 143,737 (≈144K), which is **wrong**, because that graph was not processed. | arithmetic |
| 4. Released vs reported graph | Released: full DOT (`348d92cd…`). Manuscript totals: analytical view (3,117,399 / 7,666,919). Figure 7: released DOT. | `graph_snapshot_reconciliation.md` |
| 5. "Full-size runs reproduce the released graph" | **Accurate**: byte-identical output in 3/3 runs. | re-hash |
| Do not mix | The separate analytical-candidate build (`release_candidate/build1.time`: 53.12 s, 7,666,919 edges) and the single DOT run in `results-local-20261015-rq1-01` (51.87 s, 149,911 edges/s) are **not** Figure 7 measurements. | logs |

## Correction (if the text does not already say so)

```latex
Figure~\ref{fig:scalability} times offline assembly of the \emph{released} graph (7{,}775{,}872 edges, 3{,}137{,}207 nodes) from its archived per-family edge files: three full-size runs take $53.34 \pm 0.96$\,s with 0.447\,GiB peak memory on one CPU process (about 146K edges/s), and each output is byte-identical to the released graph. Timings exclude Hub data acquisition, relationship extraction, graph-database loading, and querying. The analyses use an evidence-qualified view that omits 108{,}953 Dataset-to-Model edges, leaving 7{,}666{,}919 edges.
```

Throughput was not changed. The logs establish the original denominator as correct.
