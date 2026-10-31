# Experiments (RQ1–RQ5)

| RQ | Question |
|---|---|
| RQ1 | How effectively can VulChain reconstruct a heterogeneous AI supply-chain graph at scale? |
| RQ2 | How do provenance-evidence policies affect cohort coverage and observed security-failure recurrence? |
| RQ3 | How frequently do externally verified security failures of a base model persist in its one-hop derivatives? |
| RQ4 | How does security-failure persistence vary across adaptation categories? |
| RQ5 | How does heterogeneous supply-chain information reveal potential downstream security exposure? |

Each manuscript table and figure has one entry point (`setup/`, `RQ1/` …
`RQ5/`). Every entry point does four things:

1. checks its inputs against recorded SHA-256 values;
2. recomputes the values;
3. compares every printed cell with the manuscript's value;
4. writes `outputs/<RQ>/<name>_verification.md` and exits non-zero on any mismatch.

To run them all:

```bash
python reproducibility/verify_results.py --release-dir <extracted release>
```

## Shared code

- **`vulchain_rq.py`** holds the calculation rules used for RQ2–RQ5.
  Everything outside its "Adapter" sections is the exact text of the
  production analysis code that generated the manuscript values
  (`unified_analysis.py`, `unified_exports.py`, snapshot
  `v2026.10.27-unified-01-b9e3e4d60181fa58`). It was copied mechanically, and
  the file header lists source checksums and line ranges. The Adapter sections
  are new: they add input loaders, path parameters, and the comparison with the
  manuscript.
- **`vulchain_table2.py`** is the Table II ID-set counting, copied verbatim from
  `table2_unique_models.py`.
- **`production/`** holds the production modules those copies come from.
  It also holds the earlier steps those copies do not cover: external
  verification, the c1 extraction corrections, the per-response outcome
  engine (`run_rq3.py`), and the construction of the comparison records from
  the ledger. See [production/README.md](production/README.md).
  `tests/test_production_sources.py` checks that every copied definition
  appears verbatim in `production/`.

## Common definitions (RQ2–RQ5)

- **Cohort.** The evaluated inventory as of the capture cutoff
  (2026-10-30 20:08:45 UTC): 45 upstream (base) models and 437 one-hop
  derivatives (482 models), with fine-tune, adapter, quantized, and merge
  relationships. Converted and new-version relationships are excluded. A pair
  enters once at least one identical prompt has completed original
  verification and both c1 passes on both models.
- **Prompt bank.** 575 package-hallucination prompts and 457 URL prompts. Each
  is a verified failure-inducing prompt for at least one base model. A
  derivative of base *x* is assessed only on *x*'s own failure-inducing
  prompts.
- **Comparison (test).** One base–derivative–prompt triple for one finding
  category, where the base shows a verified failure. It is eligible when both
  the class-level and the instance-level outcomes are determinate. Class and
  instance rates share this single denominator.
- **Class-level recurrence.** The derivative shows a verified failure of the
  same category under the same prompt.
- **Instance-level recurrence.** The derivative emits the identical canonical
  artifact as the base (same package or same registrable domain).
- **Evidence policies** (nested):
  - **Strict:** explicit `base_model_relation`, indexed relation tag, or `finetuned_from`.
  - **Intermediate:** adds adaptation-tag heuristics and `derived_from`.
  - **Declared:** adds every declared parent, including default fine-tune labels.
  - **Extended:** adds inferred lineage.
  - RQ3–RQ5 use **Declared**.
- **Categories.** Package hallucination (PyPI and npm); registrable NXDOMAIN;
  restricted namespace (a diagnostic only); exact malicious URL (URLhaus and
  PhishTank).

## Inputs

| Input | Used by | Location |
|---|---|---|
| Comparison-level records, occurrences, cohort and model audit | Setup (Eval row), RQ2–RQ5 | `data/rq_snapshot/` |
| RQ5 graph export (cohort lineage, Model→Space, Model→GitHub, Space→GitHub) | RQ5 | `data/rq_snapshot/rq5_graph_export/` |
| Frozen Table II stage records | Setup | `data/table2_baseline/` |
| Released per-family edge files | RQ1, RQ5 | graph reproducibility archive (`--release-dir`) |
| Benchmark run records (`fig:rq1`); Hub reference pairs and completed-source list (`tab:hub_agreement`) | RQ1 | `production/graph_server_rq1/` |
| Manuscript macro values (expected results) | all | `data/manuscript_macros/` |

## Status

The six checks for each artifact are in `REPRODUCIBILITY_MATRIX.csv`. Its
columns:

- `source_code_available`
- `required_inputs_available`
- `original_calculations_reproduced`
- `manuscript_values_verified`
- `public_reproduction_possible`
- `restricted_input_required`

| Artifact | Status | Values verified |
|---|---|---|
| `tab:model_corpus` | PASS | 19/19 |
| `tab:master_table` | PASS | 44/44 (analytical), 44/44 (released) |
| `tab:hub_agreement` | PASS | 34/34 |
| `fig:rq1` | PASS | 71/71 (72/72 with `--rebuild-dot`) |
| `tab:rqtworecurrence` | PASS | 56/56 |
| `tab:rq3` | PASS | 24/24 |
| `tab:rq3nlc` | PENDING | — |
| `tab:rq4-adaptation-split` | PASS | 80/80 |
| `tab:rq5` | PASS | 35/35 |

The one PENDING artifact, `tab:rq3nlc`, has no entry point.
`RQ3/rq3_table_02.py` will be added only after the authoritative code and
records arrive, and it will run that code. The RQ1 entry points added on
2026-10-30 follow the same rule: they run the transferred Graph Server code in
`production/graph_server_rq1/`.

Details are in each RQ folder's README.
