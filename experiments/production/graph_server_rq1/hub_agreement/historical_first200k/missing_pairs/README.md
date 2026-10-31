<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: reproducibility guide for the ICDE 2027 RQ1 Hub-reference missing-pair diagnostic -->

# Hub model-tree reference: unrecovered-pair diagnostic

This directory explains why VulChain recovers **14,668 of 15,689 (93.5%)** Hub model-tree reference pairs, and what happened to the other **1,021**. It reproduces Table IV (`tab:hub_agreement`) exactly from the released `HuggingGraph_v3.dot`.

It is a read-only analysis:
- every input is only read;
- no graph was rebuilt;
- no Hub API request was made;
- no GPU was used;
- no existing file was changed.

Start with `diagnostic_report.md`.

## Contents

| File | What it is |
|---|---|
| `diagnostic_report.md` | The evidence-backed investigation: artifacts, Table IV check, per-pair checks, classification, RQ1 implications, limitations. |
| `missing_pairs.csv` | Ledger with one row per unrecovered reference pair (1,021 rows; columns below). |
| `root_causes.csv` | The ledger aggregated by primary root cause × adaptation, with confidence counts. |
| `summary.json` | Table IV recomputation, cause and confidence counts, concentration, sensitivity figures, graph-wide identifier counts. |
| `rq1_paper_text.tex` | LaTeX text: RQ1 explanation (A), threats-to-validity sentence (B), Table IV caption (C). |
| `input_manifest.json` | Path, size, mtime and sha256 of all 19 inputs, as recorded by the run. |
| `run.log` | Diagnostic log. |
| `reproduce.sh` | Read-only reproduction: reruns into a new directory, compares outputs, runs the tests. |
| `scripts/diagnose_missing_pairs.py` | The diagnostic (Python 3.10, standard library only). |
| `scripts/dot_graph.py` | DOT reader (Model→Model edges, model nodes, DOT unescaping). |
| `scripts/test_missing_pairs.py` | 14 verification tests. |
| `logs/` | Input checksums before and after the run, the unchanged-input check, test output, diagnostic stdout. |

## Source snapshot

| Item | Value |
|---|---|
| Graph | `2026_Fall_Extension/extension_updated_code/hugginggraph_v3_2026oct02_reproducibility/graph/HuggingGraph_v3.dot`. HuggingGraph v3, built 2026-10-02, 1,020,652,753 bytes, sha256 `348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b`. This matches the archive `MANIFEST.sha256`, and every other copy named `HuggingGraph_v3.dot` on the host is identical. |
| Model→Model edges | 966,035, equal to `edges/csv/01_model_model_edges.csv` after DOT unescaping. |
| Hub reference | `2026_Fall_Extension/models/graph_model_model_first_200k.csv` (sha256 `fa0455915bdb6034…`), with its `.completed.txt` (200,000 sources). Crawled 2026-08-31 → 2026-09-06 UTC by `graph_model_model_master.py` v2026.08.31-01. |
| Model inventory | `raw/models/all_huggingface_models_2026Aug28.csv` (3,029,377 IDs). |
| Card metadata | `raw/models/all_model_readme_metadata_2026Aug28.jsonl`, retrieved 2026-09-01. |
| Later cards | `raw/models/all_model_readmes_full_2026Sep25.jsonl`. |
| Published Table IV source | `rq1_audit_2026Oct15/hf_tree_random1k/smoke_test_first200k/{metrics.json,label_confusion.csv}`. |

All paths above are relative to `<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working`, except `raw/…` and `edges/…`, which are relative to the v3 archive `hugginggraph_v3_2026oct02_reproducibility/`. Full paths and hashes are in `input_manifest.json`.

## Matching and classification

**Recovery rule.** This is the published evaluator's rule (`rq1_audit_2026Oct15/scripts/eval_hf_tree_recall.py`):
- a reference pair is `(Source, Target)`, where `Source` completed all four Hub queries;
- it is recovered when the exact, case-sensitive `owner/name` pair is a DOT Model→Model edge, with any label;
- the Hub relation `merge` corresponds to the graph label `merged`.

**Primary root cause.** Each pair gets the first cause that applies:

| Code | Meaning |
|---|---|
| C1 | Both endpoints absent from the graph |
| C2 | Derivative absent from the graph |
| C3 | Upstream absent from the graph |
| C4 | Derivative is a graph node only as a referenced ID; its card was never crawled |
| C5 | Identifier differs only in case |
| C6 | The derivative card names a different upstream ID that is not in the inventory, and the edge exists in the graph under that ID (rename or transfer) |
| C7 | The card names the upstream only in the later (2026-09-25) README |
| C8 | Unsupported by the archived card |

**Confidence.** Each pair also gets a confidence level:
- **confirmed:** directly established by archived records;
- **probable:** indirect support;
- **unresolved:** the mechanism has no local support.

For C6, the confidence depends on how strongly the alias is corroborated (see `diagnostic_report.md` §4).

### `missing_pairs.csv` columns

| Column group | Columns |
|---|---|
| Pair identity | `pair_id`, `reference_upstream`, `reference_derivative`, `reference_adaptation`, `hub_relation` |
| Endpoint presence | `upstream_in_graph`, `derivative_in_graph`, `upstream_in_crawl_inventory`, `derivative_in_crawl_inventory` |
| Edge presence | `exact_edge_in_graph`, `canonicalized_edge_in_graph` (case-insensitive) with `canonicalized_edge_detail`, `reverse_edge_in_graph`, `alternative_label_edge_in_graph` |
| Pipeline and card evidence | `pipeline_stage_outputs_with_pair`, `derivative_card_status_2026Sep01`, `derivative_card_declared_parents`, `derivative_card_relation_field`, `derivative_card_names_upstream`, `derivative_graph_parents`, `upstream_card_status_2026Sep01` |
| Alias evidence | `alias_parent_ids`, `alias_edge_in_graph`, `alias_corroboration`, `alias_corroboration_strength` |
| Later and historical evidence | `derivative_readme_2026Sep25_status`, `derivative_readme_2026Sep25_names_upstream`, `pair_in_2025_model_tree`, `same_owner_graph_children_of_upstream_not_in_reference`, `derivative_flagged_derived_without_parent` |
| Classification | `primary_root_cause`, `primary_root_cause_label`, `secondary_factors`, `evidence_sources`, `confidence`, `available_provenance_evidence`, `diagnostic_notes` |

## Results

| Root cause | Fine-tune | Adapter | Quantized | Merge | Total | % |
|---|---:|---:|---:|---:|---:|---:|
| C6 Identifier mismatch: card names a non-inventory upstream ID (rename/transfer) | 207 | 46 | 387 | 172 | 812 | 79.5 |
| C2 Derivative absent from graph (never crawled) | 47 | 19 | 87 | 33 | 186 | 18.2 |
| C3 Upstream absent from graph | 1 | 4 | 5 | 0 | 10 | 1.0 |
| C4 Derivative card never crawled (node only as reference) | 1 | 0 | 1 | 5 | 7 | 0.7 |
| C5 Identifier mismatch, case only | 0 | 0 | 3 | 0 | 3 | 0.3 |
| C1 Both endpoints absent from graph | 1 | 1 | 0 | 0 | 2 | 0.2 |
| C7 Card changed after metadata snapshot | 0 | 0 | 1 | 0 | 1 | 0.1 |
| C8 Unsupported by archived card | 0 | 0 | 0 | 0 | 0 | 0.0 |
| **Total** | **257** | **70** | **484** | **210** | **1,021** | **100** |

Confidence across all pairs: 845 confirmed, 163 probable, 13 unresolved.

## Reproduce

```bash
cd <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working/validation/hub_reference_missing_pairs_2027
./reproduce.sh            # or: ./reproduce.sh /path/to/new/empty/dir
```

**What it does:**
- reruns the diagnostic into a new directory (it refuses to write inside this one);
- `cmp`s the regenerated `missing_pairs.csv` and `root_causes.csv` against the stored copies;
- runs the 14 tests.

**Requirements:**
- `/usr/bin/python3` 3.10 (override with `PYTHON=`); standard library only;
- measured on 2026-10-30: 2 min 9 s wall time and 3.0 GB peak RSS for the full `reproduce.sh` (`logs/reproduce_run.txt`).

**Individual steps:**
- Diagnostic only: `python3 -B scripts/diagnose_missing_pairs.py --out-dir <new dir> [--skip-checksums]`. The script refuses to overwrite existing outputs and stops if the DOT sha256 is not `348d92cd…`.
- Tests only: `python3 -B scripts/test_missing_pairs.py -v`.

## Verification (2026-10-30)

| Check | Result |
|---|---|
| Reference, recovered and unrecovered counts | 15,689 / 14,668 / 1,021, equal to the published Table IV, `metrics.json` and `label_confusion.csv` |
| Per-adaptation missing counts | 257 / 70 / 484 / 210; ledger and aggregate sums agree |
| Ledger integrity | 1,021 distinct pairs; equals the set of unrecovered reference pairs; none recovered |
| Cause evidence | Every primary cause is re-checked against the DOT: endpoint absence; case-insensitive edge; alias edge under a non-inventory ID |
| Tests | 14/14 pass (`logs/test_results.txt`) |
| Inputs unchanged | 19 inputs: sha256, size and mtime identical before and after the run (`logs/input_sha256_{before,after}.txt`, `logs/input_unchanged_check.txt`) |
