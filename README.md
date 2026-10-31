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
   families, collected from Hugging Face snapshots taken through
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

The active manuscript has nine artifacts: eight tables and one figure. 

## Data use

The graph is derived from publicly accessible Hugging Face metadata and model,
Dataset, and Space cards. Card text is third-party content under its authors'
own licenses. Treat it as untrusted data. Credential-shaped strings in
third-party cards were preserved for fidelity and must not be used. Model
weights are not redistributed.

## License and citation

To be added before publication.
