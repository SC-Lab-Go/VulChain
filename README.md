# VulChain: Evidence-Aware Measurement of Security-Failure Persistence in LLM Supply Chains

This repository is the reproducibility package for the ICDE 2027 submission.
It contains:

- the VulChain heterogeneous supply-chain graph (`VulChain.dot`, a GitHub Release asset);
- the graph-construction pipeline for all 17 relationship families, in one file;
- one reproduction entry point per table and figure of the experiments (RQ1–RQ5);
- the production analysis code that computed the RQ2–RQ5 values, from the
  measurement ledger to the tables (`experiments/production/`);
- the frozen inputs those entry points read, with checksums.

## Why VulChain

LLMs on Hugging Face are reused through supply chains: an upstream model is
fine-tuned, adapter-tuned, quantized, or merged into thousands of derivatives,
which are in turn linked to datasets, applications (Spaces), and code
repositories. Security failures of an upstream model may recur in its
derivatives. Measuring that is hard because model-hub provenance is incomplete
and self-reported, and similar outputs alone do not establish a verified shared
failure.

VulChain combines three parts:

1. **Heterogeneous graph construction.** Eight entity types and 17 relationship
   families, collected from Hugging Face snapshots taken between August 28 and
   October 2, 2026.
2. **Provenance-qualified lineage selection.** Four nested evidence-admission
   policies (Strict ⊂ Intermediate ⊂ Declared ⊂ Extended).
3. **Same-prompt persistence measurement.** Package hallucinations and NXDOMAIN
   domains are checked against external sources (PyPI, npm, DNS, URLhaus,
   PhishTank). Recurrence is measured at two levels: the same failure class,
   and the identical artifact.

## The graph

`VulChain.dot` is the graph reported in the manuscript (Table `tab:master_table`):

| | `VulChain.dot` |
|---|---:|
| Edges | 7,666,919 |
| Nodes | 3,117,399 |
| Entity types / relationship families | 8 / 17 |
| Model→Model edges | 966,035 |
| Dataset→Model edges | 253,111 |
| SHA-256 | `25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97` |

It is built from the October 2, 2026 HuggingGraph v3 release with one
evidence filter, applied to relationship 2 (Dataset→Model). A training-data
declaration is kept only if it resolves to exactly one Dataset in the crawled
inventory. That drops 108,953 of the release's 362,064 declared references:

| Dropped references | Count |
|---|---:|
| Ambiguous bare names | 55,115 |
| Owner/repository IDs absent from the snapshot | 39,749 |
| Unmatched bare names | 13,558 |
| Malformed or placeholder strings, such as `-` | 531 |

Except for the malformed strings, the dropped references are unresolved, not
shown to be false.

The other 16 families are exactly the released ones. For reference, the
unfiltered HuggingGraph v3 release (`HuggingGraph_v3.dot`, 7,775,872 edges and
3,137,207 nodes) is not part of this repository. It remains available from its
own release, and `experiments/RQ1/rq1_table_01.py --view released` reproduces
its counts.

See [graph/README.md](graph/README.md) for download, verification and rebuilding.

**Entity types (8):** Model, Dataset, Space, GitHub repository, Library, License, Task, Agent framework.

**Relationship families (17):**

| # | Relationship | `edge_type` | Edges |
|---:|---|---|---:|
| 1 | Model → Model | finetune, adapter, quantized, merged, converted, new_version | 966,035 |
| 2 | Dataset → Model | trained_on (inventory-resolved) | 253,111 |
| 3 | Dataset → Dataset | dataset_relationship_candidate | 12,541 |
| 4 | Model → Library | uses_library | 1,311,386 |
| 5 | Dataset → Library | uses_library | 16,864 |
| 6 | Model → License | has_license | 1,090,845 |
| 7 | Dataset → License | has_license | 331,317 |
| 8 | Model → Task | performs_task | 577,077 |
| 9 | Dataset → Task | supports_task | 317,412 |
| 10 | Model → GitHub | links_to_github | 962,855 |
| 11 | Dataset → GitHub | links_to_github | 188,888 |
| 12 | Model → Space | used_by_space | 941,121 |
| 13 | Dataset → Space | used_by_space | 83,061 |
| 14 | Space → GitHub | links_to_github | 113,755 |
| 15 | Space → License | has_license | 420,369 |
| 16 | Space → Task | supports_task | 43,223 |
| 17 | Space → Agent framework | uses_agent_framework | 37,059 |

Each family's metadata source, extraction logic, evidence requirement, and
validation are in
[relationships/relationship_catalog.csv](relationships/relationship_catalog.csv).

## Repository layout

```text
graph/                 VulChain.dot (Release asset), checksum, loading notes
graph_construction/    vulchain_graph.py: the full construction pipeline in one file
relationships/         17-family catalog and a sample of each family
experiments/           one entry point per manuscript table/figure, plus shared code
  production/          production RQ2–RQ5 analysis code and verifiers (20 modules, source manifest)
    graph_server_rq1/  original RQ1 benchmark, figure, Hub evaluator and audit code + records (80 files)
data/                  frozen experiment inputs (with checksums) and the manuscript's macro values
reproducibility/       graph and result verifiers, transfer checklist
scripts/               live results pipeline (refresh, validate, freeze) and guarded GitHub publisher
configs/               configuration templates (local copies are gitignored)
tests/                 unit, consistency, production-source, and publication-deadline tests
REPRODUCIBILITY_MATRIX.csv   artifact → code → inputs → six reproduction checks → status
LIVE_RESULTS_PIPELINE.md     how results are refreshed, validated, frozen, and published
requirements-verifiers.txt   pins for the URL verifier (separate environment)
```

## Installation

Python 3.10 or later. The experiment entry points and verifiers use only the
standard library. The graph-construction stages need the pinned packages
(`huggingface_hub`, `PyYAML`, `pandas`, ...):

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt     # needed for graph_construction only
bash reproducibility/verify_environment.sh
```

Reading or testing the production analysis code needs a few more packages:

- `numpy`, for the bootstrap in `unified_analysis.py`;
- `matplotlib`, for figures in `unified_exports.py` and for drawing `fig:rq1`.
  Without it, `rq1_figure_01.py` still verifies every value, but draws nothing;
- `requirements-verifiers.txt`, for the URL verifier only. Install it in a
  separate environment, because its `idna` and `filelock` pins differ from
  `requirements.txt`.

Without those packages, the URL-verifier test is skipped.

Hardware: none of the reproduction steps needs a GPU.

- Verifying or re-assembling the graph needs about 1 GB of disk and under 1 GB of memory.
- The experiment entry points each run in seconds.
- Re-running the model inference behind RQ2–RQ5 needs GPU servers and is not
  part of this package; see the limitations below.

## Download

`VulChain.dot` (1.0 GB) and two Hub-ID input files are assets of the GitHub
Release [`v2026.10.30`](https://github.com/SC-Lab-Go/VulChain/releases/tag/v2026.10.30):

| Asset | Place at | SHA-256 |
|---|---|---|
| [`VulChain.dot`](https://github.com/SC-Lab-Go/VulChain/releases/download/v2026.10.30/VulChain.dot) | `graph/VulChain.dot` | `25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97` |
| [`graph_model_model_first_200k.csv.completed.txt`](https://github.com/SC-Lab-Go/VulChain/releases/download/v2026.10.30/graph_model_model_first_200k.csv.completed.txt) | `experiments/production/graph_server_rq1/hub_agreement/historical_first200k/reference/` | `de0df81d8d206de89f6685daf59fdf566fdb1a776323ceb3a8f4472c3e34da26` |
| [`table2_stage_records.csv`](https://github.com/SC-Lab-Go/VulChain/releases/download/v2026.10.30/table2_stage_records.csv) | `data/table2_baseline/` | `5789ad230dec925a4aae6e3eeffeb5ec979c955cc27bd7e90eddfe21952e9300` |

```bash
BASE=https://github.com/SC-Lab-Go/VulChain/releases/download/v2026.10.30
curl -L -o graph/VulChain.dot $BASE/VulChain.dot
curl -L -o experiments/production/graph_server_rq1/hub_agreement/historical_first200k/reference/graph_model_model_first_200k.csv.completed.txt $BASE/graph_model_model_first_200k.csv.completed.txt
curl -L -o data/table2_baseline/table2_stage_records.csv $BASE/table2_stage_records.csv
(cd graph && sha256sum -c VulChain.dot.sha256)
python reproducibility/verify_graph.py graph/VulChain.dot
```

The two input files are lists of public Hugging Face model IDs. They are
release assets rather than Git files because nine third-party repository names
in them have the shape of Hugging Face access tokens (`hf_` + 34 letters). The
files are unchanged; `experiments/production/graph_server_rq1/SOURCE_MANIFEST.json`
and `data/table2_baseline/BASELINE_METADATA.json` record their checksums.
`tab:hub_agreement` and the first two rows of `tab:model_corpus` need them.

## Reproducing the tables and figures

Download the release assets first (above); see also [graph/README.md](graph/README.md).
The RQ1 and RQ5 scripts read the per-family edge files from the extracted
release archive. Then run:

```bash
python reproducibility/verify_results.py --release-dir <extracted release>/hugginggraph_v3_2026oct02_reproducibility
```

Each entry point does three things:

- recomputes the values from its inputs;
- compares every printed cell with the manuscript's value;
- writes a verification report under `outputs/`.

The active manuscript has nine artifacts: eight tables and one figure. For
each one, the table below answers six questions, in this column order:

1. **Code:** is the source code available?
2. **Inputs:** are the required inputs available?
3. **Calc.:** were the original calculations reproduced?
4. **Verified:** were the manuscript values verified?
5. **Public:** is public reproduction possible?
6. **Restr.:** is restricted input required?

| Label | Entry point | Code | Inputs | Calc. | Verified | Public | Restr. | Status |
|---|---|---|---|---|---|---|---|---|
| `tab:model_corpus` | `experiments/setup/setup_table_01.py` | yes | yes | yes | 19/19 | rows 1–2 | Sel. cohort row | PASS |
| `tab:master_table` | `experiments/RQ1/rq1_table_01.py` | yes | yes | yes | 44/44 | yes | no | PASS |
| `tab:hub_agreement` | `experiments/RQ1/rq1_table_02.py` | yes | yes | yes | 34/34 | yes | no | PASS |
| `fig:rq1` | `experiments/RQ1/rq1_figure_01.py` | yes | yes | yes | 71/71 | yes (timings not re-measured) | no | PASS |
| `tab:rqtworecurrence` | `experiments/RQ2/rq2_table_01.py` | yes | yes (restricted) | yes | 56/56 | no | yes | PASS |
| `tab:rq3` | `experiments/RQ3/rq3_table_01.py` | yes | yes (restricted) | yes | 24/24 | no | yes | PASS |
| `tab:rq3nlc` | — | no | no | no | no | no | yes | PENDING |
| `tab:rq4-adaptation-split` | `experiments/RQ4/rq4_table_01.py` | yes | yes (restricted) | yes | 80/80 | no | yes | PASS |
| `tab:rq5` | `experiments/RQ5/rq5_table_01.py` | yes | yes (restricted) | yes | 35/35 | no | yes | PASS |

**What the statuses mean.**

- **PASS:** every printed value was recomputed from the inputs, using the original code, and matched exactly.
- **PENDING:** no reproduction code exists in this repository yet. No placeholder or hard-coded script stands in for it.

**Two graph versions in RQ1.** The canonical graph, `VulChain.dot`
(7,666,919 edges, SHA-256 `25d669bd…`), is what `tab:master_table` reports.
The assembly-scaling benchmark behind `fig:rq1` was measured on the full
HuggingGraph v3 release instead (`HuggingGraph_v3.dot`, 7,775,872 edges,
`348d92cd…`). The two graphs differ only in 108,953 unresolved Dataset→Model
references.

`tab:hub_agreement` compares family 1 (Model→Model) with the Hub. Family 1 is
identical in both graphs.

**How the RQ2–RQ5 "yes" is scoped.** For RQ2–RQ5, "Calc. reproduced" means the
table is recomputed from the exported comparison records, with the production
estimator code. The step before that, from the measurement ledger to the
comparison records, is published in `experiments/production/` but is not
re-executed here, because its ledger holds raw prompts and responses.

**Restricted data.** The comparison records (`data/rq_snapshot/`) name
individual models next to verified findings, so they are held back from public
release. See
[LIVE_RESULTS_PIPELINE.md](LIVE_RESULTS_PIPELINE.md#public-and-restricted-reproducibility).

The full matrix, with checksums, is in
[REPRODUCIBILITY_MATRIX.csv](REPRODUCIBILITY_MATRIX.csv).
[experiments/README.md](experiments/README.md) gives each RQ's setup, inputs,
definitions, and expected results.

## How each result was computed

The RQ1 figure and Hub-agreement values come from the original Graph Server
code in
[experiments/production/graph_server_rq1/](experiments/production/README.md#rq1-graph-server-code-graph_server_rq1).
It is hash-checked against its own `SOURCE_MANIFEST.json`.

| Artifact | Original code, and how the entry point uses it |
|---|---|
| `fig:rq1` | The nine raw `/usr/bin/time` records are parsed with the benchmark's own summarizer functions. The results are checked against the recorded summary and against the plotting script's constants, and the plotting script is run unchanged. Optionally, the benchmark builder reassembles the 100% input. |
| `tab:hub_agreement` | The original Hub evaluator (`eval_hf_tree_recall.py`) is run unchanged. The original per-adaptation statements of `audit_selection.py` (Wilson and cluster-robust intervals) are executed on the public reference pairs and the released Model→Model edges. |

The RQ2–RQ5 values come from the production analysis in
[experiments/production/](experiments/production/README.md):

| Step | Production code |
|---|---|
| External verification | `package_probe_validation.py` (PyPI/npm registry), `url_probe_validation.py` (URLhaus/PhishTank exact match, public suffix, DNS NXDOMAIN) |
| Versioned extraction corrections and closed-brand review | `dual_site_probe_v2026_10_10/*_c1.py` |
| Per-response verified artifacts; class- and instance-level outcomes | `run_rq3.py` (`response_states()`, `outcomes()`) |
| Cohort, eligibility, same-prompt matching, denominators, base-clustered bootstrap | `unified_analysis.py` (`cohort_and_comparisons()`, `summarize()`, `clustered()`) |
| RQ2–RQ5 macros and tables | `unified_exports.py` |

`SOURCE_MANIFEST.json` records the original SHA-256 of all 20 modules.

- 10 are verbatim.
- 10 differ only in four machine-specific literals: a hostname, a home
  directory, a scratch directory, and an account name.

`experiments/vulchain_rq.py`, which the entry points use, is a verbatim copy of
the production calculation code. `tests/test_production_sources.py` checks
that.

**Network safety.**

- `experiments/production/offline_verifiers.py` refuses live PyPI, npm, or DNS
  queries unless network access is explicitly allowed.
- The frozen verifiers it wraps are unchanged. Called directly, they still
  query any name or host that is not in their evidence cache.
- The tests and the results refresh never make live queries.

## Refreshing results while experiments continue

The RQ2–RQ5 evaluation is still running. To pick up its newest validated
snapshot:

```bash
python scripts/refresh_results.py      # stage, recompute, validate, publish results/latest atomically
python scripts/validate_results.py     # re-check the published version
python scripts/freeze_submission.py --label submission-2026-11-06
```

The refresh never reads the live database. A failed or interrupted refresh
leaves the previous validated results untouched. See
[LIVE_RESULTS_PIPELINE.md](LIVE_RESULTS_PIPELINE.md).

## Graph assembly vs. full acquisition

This repository reproduces graph assembly exactly.
`graph_construction/build_analytical_view.py` rebuilds `VulChain.dot` byte for
byte from the archived edge files of release `v2026.10.02-07`, plus the
validated Dataset→Model file from the same archive. The same assembler also
rebuilds the unfiltered HuggingGraph v3 release byte for byte.

It does not reproduce the Hugging Face acquisition: re-crawling the Hub
produces a new snapshot.

The assembly-scaling benchmark (`fig:rq1`) was measured on the unfiltered
release (7,775,872 edges), not on `VulChain.dot`. Its timings exclude network
acquisition. `experiments/RQ1/rq1_figure_01.py --rebuild-dot` reassembles that
100% input with the benchmark's own builder and checks that the result hashes
to `348d92cd…`. This passed on 2026-10-30.

## Input data and snapshots

| Input | Date |
|---|---|
| Hugging Face model metadata / inventory | 2026-08-28 |
| Space metadata and cards | 2026-09-24 |
| Full model README crawl | 2026-09-25 |
| Full Dataset README crawl | 2026-09-28 |
| Graph release (all 17 families) | 2026-10-02 (release `v2026.10.02-07`) |
| RQ2–RQ5 analysis snapshot | capture cutoff 2026-10-30 20:08:45 UTC (`v2026.10.27-unified-01-b9e3e4d60181fa58`) |
| External verification | URLhaus and PhishTank snapshots dated 2026-10-08 (`phishtank_online-valid_20261008-184915.csv`, `urlhaus_full_20261008-184915.zip`, hash-pinned in `run_rq3.py`). PyPI, npm, and DNS observations keep their own `checked_at` time; a finding counts only if that time precedes the capture cutoff. |

## Reproducibility limitations

- **RQ2–RQ5 use a dated snapshot of an ongoing evaluation.** The snapshot
  covers 45 upstream models and 437 one-hop derivatives (482 models). It is the
  state of the measurement ledger at the capture cutoff above. The scripts
  reproduce the manuscript exactly from that snapshot, but the values will
  change if the evaluation is extended.
- **Raw model responses are not included.** This covers generated package
  names, registrable domains, and URLs. They are security-sensitive, so RQ2–RQ5
  are recomputed from comparison-level records instead, with artifacts
  represented by hashes.
- **One table cannot be recomputed here.** The matched non-lineage control
  (`tab:rq3nlc`) is PENDING: its code and comparison records have not been
  located. See
  [reproducibility/TRANSFER_CHECKLIST.md](reproducibility/TRANSFER_CHECKLIST.md).
- **The Hub reference is a historical prefix, not a sample.** `tab:hub_agreement`
  uses the first 200,000 models of the 2026-08-28 delta inventory. A separate
  probability-sample evaluation of 6,816 upstream models is still running and
  is not part of this repository. Its results will not be mixed with this table.
- **Raw Hub crawls stay private.** These are not published:
  - the inventories and model-card metadata that `audit_selection.py` reads for
    its representativeness sections;
  - the crawl log;
  - host load snapshots.

  The table's columns need only the published reference pairs, the
  completed-source list, and the released edges.
- **Manuscript text to check (RQ1).** Four points, none of which changes a value:
  - The text says throughput is "near 144K edges/s". The recorded means are
    145.8K–146.3K, about 146K.
  - The caption's "111,816 upstream models" is the number of distinct upstream
    models in the released Model→Model file. The Hub reference covers 200,000
    queried models, 5,222 of which have Hub derivatives.
  - The table prints pooled Wilson intervals. Cluster-robust intervals, which
    treat each upstream model as a cluster, are wider.
  - The revised table file (`table/icde_table_iv_revised.tex`, VERSION 2)
    prints the Fine-tune cluster-robust upper bound as 94.9. It should be 94.8.
- **The production analysis code runs only with the restricted ledger.**
  `experiments/production/` is published so the computation can be read and
  audited. Its in-code integrity checks refer to the unredacted originals.
- **Feed date.** The manuscript (Experimental Setup) dates the URLhaus and
  PhishTank snapshots to October 2, 2026. The production engine uses the
  October 8 feed files, and its protocol records that correction.
- **Re-crawling Hugging Face will not give the same graph.** The Hub changes
  continuously. Stages that call the Hub API (acquisition, and Space
  reconciliation in `prepare`) depend on availability at run time. The
  offline stages are deterministic.
- **The scaling benchmark is hardware-dependent.** Its timings will differ on
  other hardware.

## Data use

The graph is derived from publicly accessible Hugging Face metadata and model,
Dataset, and Space cards. Card text is third-party content under its authors'
own licenses. Treat it as untrusted data. Credential-shaped strings in
third-party cards were preserved for fidelity and must not be used. Model
weights are not redistributed.

## License and citation

To be added before publication.
