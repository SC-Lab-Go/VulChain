# RQ1: AI supply-chain graph reconstruction quality

**Objective.** RQ1 measures three things:

- the graph's scale and composition;
- how reliable its lineage labels are against an external reference;
- the cost of offline construction.

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: VulChain statistics | `tab:master_table` | `rq1_table_01.py` | PASS (44/44) |
| Table: lineage edges and Hub model-tree agreement | `tab:hub_agreement` | `rq1_table_02.py` | PASS (34/34) |
| Figure: DOT assembly scaling | `fig:rq1` | `rq1_figure_01.py` | PASS (71/71; 72/72 with `--rebuild-dot`) |

| Label | Code | Inputs | Calc. reproduced | Values verified | Public | Restricted |
|---|---|---|---|---|---|---|
| `tab:master_table` | yes | yes (release archive) | yes | 44/44 per view | yes | no |
| `tab:hub_agreement` | yes (original evaluator and audit) | yes | yes | 34/34 | yes | no |
| `fig:rq1` | yes (original summarizer and plotting script) | yes (raw run records) | yes, except that timings are not re-measured | 71/71 | yes | no |

**Two graph versions.**

| Graph | Edges | SHA-256 | Used by |
|---|---:|---|---|
| `VulChain.dot` (canonical, analytical view) | 7,666,919 | `25d669bd…` | `tab:master_table` (default view) |
| `HuggingGraph_v3.dot` (full release) | 7,775,872 | `348d92cd…` | `fig:rq1` (all benchmark runs); `tab:master_table --view released` |

The Model→Model family (966,035 edges), which `tab:hub_agreement` evaluates,
is identical in both graphs.

**Inputs.**

- `--release-dir`: the extracted reproducibility archive of release
  `v2026.10.02-07`, verified against its `MANIFEST.sha256`.
- `tab:master_table` reads:
  - the 17 files `edges/csv/01..17_*.csv`;
  - for the analytical view, `evidence/top_level/dataset_model_edges_validated.csv`.
- `rq1_table_02.py` reads:
  - `edges/csv/01_model_model_edges.csv`;
  - the Hub reference pairs and completed-source list in
    `../production/graph_server_rq1/hub_agreement/historical_first200k/reference/`.
- `rq1_figure_01.py` reads the benchmark run in
  `../production/graph_server_rq1/figure_rq1/benchmark/results-local-20261015-scaling-03/`.

**Dependencies.** `rq1_table_01.py` and `rq1_table_02.py` use only the
standard library. `rq1_figure_01.py` needs `matplotlib` to draw the figure.
Without it, the script still verifies every value. The original figure was
drawn with matplotlib 3.10.0 and DejaVu Serif.

All transferred code is hash-checked against
`../production/graph_server_rq1/SOURCE_MANIFEST.json` before it runs.

## `tab:master_table`

The table gives edges and endpoint nodes for each of the 17 families, plus
union nodes by entity type, for the analytical view. The analytical view is
the release's edge files with family 2 replaced by
`dataset_model_edges_validated.csv`.

```bash
python experiments/RQ1/rq1_table_01.py --release-dir <release>                   # manuscript (analytical) view
python experiments/RQ1/rq1_table_01.py --release-dir <release> --view released   # unfiltered HuggingGraph v3 counts
```

**Expected results.**

- Analytical view: 7,666,919 edges and 3,117,399 nodes. Dataset→Model has 253,111 edges and 194,462 nodes.
- Released view (unfiltered HuggingGraph v3, not distributed here): 7,775,872 edges and 3,137,207 nodes.

The analytical view is exactly `graph/VulChain.dot`. Both views were verified
exactly.

## `tab:hub_agreement`

```bash
python experiments/RQ1/rq1_table_02.py --release-dir <release> [--evidence <model_lineage_edges_merged.csv>]
```

**Reference set.** This is the historical exact-ID reference:

- **Queried:** the Hub model-tree index, through the
  `base_model:{finetune,adapter,quantized,merge}:<id>` filters, for the first
  200,000 models of the 2026-08-28 delta inventory.
- **Crawl:** `acquisition/graph_model_model_master.py`, run 2026-08-31 to
  2026-09-06, with 0 failures.
- **Result:** 5,222 of the queried models have Hub derivatives, giving 15,689 pairs.

The reference is a deterministic prefix, not a random sample. A separate
evaluation on a 6,816-upstream probability sample is still running. It is not
in this repository and is not used here.

**How each column is computed.**

| Column | Computation | Original code |
|---|---|---|
| `# Edges` | `edge_type` counts in the released Model→Model file | — (counting) |
| `# Pairs`, `# Recovered` | A Hub pair is recovered if the exact, case-sensitive `owner/name` pair is a released Model→Model edge, with any label, and its upstream completed all four queries. Hub `merge` maps to `merged`. | `evaluator/eval_hf_tree_recall.py`, run unchanged. Its `label_confusion.csv` is byte-identical, and its `metrics.json` value-identical, to the archived output. |
| `Recall (%) [CI]` | Pooled 95% Wilson score interval per adaptation (z = 1.959964) | `selection_audit/scripts/audit_selection.py`, lines 232–233, 283–293, 322–325, 332–333 and 544–556, executed unchanged on the public inputs. The results equal the archived `selection_audit.json`. |
| `Match (%)` | Recovered pairs whose released label set contains the Hub label | Counted from the audit's `exact` set (adapter code), and cross-checked against the evaluator's confusion matrix |

The archived audit ran on Python 3.10. Python 3.12 sums floats with
compensated summation, so design effects and cluster-robust bounds can differ
in the last binary digits. The script compares integers exactly and floats to
a relative tolerance of 1e-12. No printed value is affected.

**Expected results.**

| Label | # Pairs | # Recovered | Recall (%) [Wilson CI] | Match |
|---|---:|---:|---|---:|
| Fine-tune | 3,466 | 3,209 | 92.6 [91.7, 93.4] | 3,088 (96.2) |
| Adapter | 1,350 | 1,280 | 94.8 [93.5, 95.9] | 1,055 (82.4) |
| Quantized | 9,284 | 8,800 | 94.8 [94.3, 95.2] | 1,814 (20.6) |
| Merge | 1,589 | 1,379 | 86.8 [85.0, 88.4] | 1,379 (100) |
| Total | 15,689 | 14,668 | 93.5 [93.1, 93.9] | 7,336 (50) |

The `# Edges` column has these values:

| Label | Edges |
|---|---:|
| finetune | 710,010 |
| adapter | 131,430 |
| quantized | 66,064 |
| merged | 53,498 |
| others (1,410 converted + 3,623 new_version) | 5,033 |
| **Total** | **966,035** |

**Fine-tune CI (94.9 vs. 94.8).** The manuscript prints the pooled Wilson
interval, [91.7, 93.4], and that value is correct.

The 94.9 appears only in the cluster-robust interval of the revised table file
`production/graph_server_rq1/hub_agreement/historical_first200k/table/icde_table_iv_revised.tex`
(VERSION 2). That file prints `92.6 [90.3, 94.9]`, but the computed upper
bound is 0.948481, so the row should read `92.6 [90.3, 94.8]`. The value was
hand-copied from `selection_audit/statistical_assessment.md`, line 35.

**Choosing intervals (author decision).** Reference pairs cluster within
upstream models, with design effects of 6.7 (Fine-tune), 3.8 (Adapter), 4.6
(Quantized) and 12.8 (Merge). The pooled Wilson intervals therefore understate
the uncertainty. If the table switches to cluster-robust intervals, the
correct rows are:

| Label | Cluster-robust 95% CI |
|---|---|
| Fine-tune | [90.3, 94.8] |
| Adapter | [92.5, 97.1] |
| Quantized | [93.8, 95.8] |
| Merge | [80.8, 92.7] |

`outputs/RQ1/rq1_table_02.csv` lists both kinds of interval.

**Caption.** "(111,816 upstream models)" is the number of distinct upstream
models in the released Model→Model file (graph side). It is not the Hub
reference scope: 200,000 queried models, 5,222 with Hub derivatives.

**Not included.** The audit's representativeness sections read the raw
2026-08-28 inventories, the model-card metadata and the crawl log. Those are
restricted raw Hub crawls, and they are not needed for any table cell. The
unrecovered-pair ledger (`missing_pairs/`, 1,021 pairs, 812 rename/transfer
aliases) is included for reference.

## `fig:rq1`

```bash
python experiments/RQ1/rq1_figure_01.py
python experiments/RQ1/rq1_figure_01.py --rebuild-dot --release-dir <release> --work <scratch>   # +55 s, writes 1 GB
```

The figure shows offline DOT assembly at 25%, 50% and 100% of the input, with
three sequential runs each. The run is `results-local-20261015-scaling-03`: a
single CPU process on an AMD EPYC 9334 host, completed 2026-10-15T23:20:50Z.
Runs `-01` and `-02` were failed attempts and are excluded.

**What is recomputed.**

1. **Raw records.** Wall time and peak RSS come from the nine
   `/usr/bin/time -v` records, parsed with the benchmark's own `elapsed()` and
   `metric()`. Throughput is input records divided by wall seconds. Totals come
   from the run stdout, through the original `parse_total()`.
2. **Mean and SD.** The mean and sample SD per input size come from the original `stat()`.
3. **Exact checks.** Steps 1 and 2 are checked exactly against the recorded
   `scaling_performance.csv` and `scaling_summary.csv`. After rounding, they
   are checked against the constants in the original plotting script.
4. **Drawing.** The figure is drawn by running `source/rq1_scaling_figure.py`
   unchanged.
5. **Manuscript text.** The figure values quoted in the manuscript text are
   compared.
6. **Graph identity (with `--rebuild-dot`).** The benchmark's own builder
   reassembles the 100% input. The result must hash to `348d92cd…`, the
   HuggingGraph v3 release. This passed on 2026-10-30.

The manuscript's `images/rq1_scaling_figure_cropped.pdf` is byte-identical to
the archived output, `figure_rq1/output/rq1_scaling_figure_cropped.pdf`.

| Input | Edges | Mean wall time | Peak RSS | Throughput |
|---:|---:|---:|---:|---:|
| 25% | 1,943,967 | 13.30 ± 0.16 s | 0.207 GiB | 146,213 ± 1,715 edges/s |
| 50% | 3,887,935 | 26.58 ± 0.23 s | 0.326 GiB | 146,280 ± 1,239 edges/s |
| 100% | 7,775,872 | 53.34 ± 0.96 s | 0.447 GiB | 145,811 ± 2,620 edges/s |

Timings are a hardware benchmark. They are reproduced from the records and
are not re-measured. To re-measure, use the original driver
(`figure_rq1/benchmark/scripts/run_scaling_local.sh`) on an idle host; the
results will differ by host.

**Manuscript notes.**

- The RQ1 text says throughput "remains stable near 144K edges/s". The recorded
  means are 145.8K–146.3K, and the mean of the 100% runs is 145,811 edges/s
  (about 146K).
- The caption calls the benchmarked graph the "released graph". Consider naming
  the HuggingGraph v3 release explicitly, now that VulChain refers to the
  analytical graph.

## Limitations

- Hub agreement is measured on a non-random prefix of the inventory. It is not
  a population-wide accuracy estimate.
- Network acquisition is excluded from all timings.
