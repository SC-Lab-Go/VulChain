<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: reconstructed selection procedure for the Hub model-tree reference behind ICDE 2027 Table IV -->

# Selection trace: how the Hub model-tree reference was selected

**Main correction.** The 5,222 figure is **not** the number of Hub models queried. The crawl queried **200,000** models. **5,222** of them returned at least one derivative, and **194,778** returned an empty model tree. A manuscript row that reads "Hub models queried: 5,222" is therefore mislabeled.

**Paths.**
- `$W` = `<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working`
- `$M` = `$W/2026_Fall_Extension/models`
- `$A` = `$W/2026_Fall_Extension/extension_updated_code/hugginggraph_v3_2026oct02_reproducibility`

All counts come from `outputs/selection_audit.json` (key `frame` unless another key is given). The tests in `tests/` recompute them from the raw inputs.

## 1. Producing scripts and artifacts

| Step | Script / artifact | Evidence |
|---|---|---|
| Hub model inventory, 2026-08-28 | `$M/all_models_names.py` → `all_huggingface_models_2026Aug28.csv` (3,029,377 IDs) | Byte-identical to `$A/raw/models/…` (same sha256 `20528f73…`) |
| 2025 baseline inventory | `$M/all_huggingface_models_CIKM.csv` (1,823,093 IDs) | Byte-identical to `$W/other_supportings/all_huggingface_models.csv`, mtime 2025-06-29 (sha `bfcefb7f…`) |
| Candidate list ("delta") | `$M/delta_models.py` → `delta_model-2026-Aug28.csv` | Code: `new_model_ids = sorted(current_ids - baseline_ids)`. This is Python code-point order, so uppercase sorts before lowercase. |
| Model-tree crawl | `$M/graph_model_model_master.py` v2026.08.31-01 | For each source, four Hub API filters: `base_model:{finetune,quantized,adapter,merge}:<source>`, with every pagination link followed |
| Crawl command | `$M/model_pipeline.md` | `--input delta_model-2026-Aug28.csv --output graph_model_model_first_200k.csv --start 0 --end 200000 --workers 4 --request-interval 0.5` |
| Crawl outputs | `graph_model_model_first_200k.csv` (15,689 rows), `.completed.txt` (200,000 lines), `.errors.csv` (header only), `.nohup.log` | |
| Evaluator | `…/rq1_audit_2026Oct15/scripts/eval_hf_tree_recall.py` → `hf_tree_random1k/smoke_test_first200k/{metrics.json,label_confusion.csv}` | These are the Table IV numbers. |

## 2. Answers to the selection questions

| # | Question | Verified answer |
|---|---|---|
| 1 | Which script generated the queried list? | `delta_models.py` built the candidate list. `graph_model_model_master.py` queried rows 0–199,999 of it (`--start 0 --end 200000`). No separate list of 5,222 models was ever produced: 5,222 is the count of queried sources that appear in the output CSV. |
| 2 | Original candidate population | 1,324,194 IDs: every model in the 2026-08-28 inventory whose ID was **absent** from the 2025-06-29 (CIKM) inventory. The script output equals `sorted(inventory − baseline)` exactly (`delta_equals_inventory_minus_baseline = true`). The other 1,705,183 inventory models were never candidates. |
| 3 | How were candidates selected? | A deterministic **prefix**: the first 200,000 rows of the code-point-sorted delta. Selected IDs run from `0-0-WasAlreadyTaken/mobilenet_multilabel` to `John6666/jedpoint-il-v7-vae-sdxl`. The first excluded ID is `John6666/jedpoint-real-v8-vae-sdxl`. |
| 4 | Random / stratified / popularity / lineage / convenience? | **Convenience (deterministic alphabetical prefix).** No seed, sampling code, strata, weights or inclusion probabilities exist for this crawl. The output directory name `smoke_test_first200k` and the earlier audits (`model_tree_agreement.md` line 19; `cohort_graph_audit.md` line 75) also describe it as "a prefix, not a random sample". |
| 5 | Selected because they had known derivatives? | **No.** Selection used only the ID's sort position. Graph lineage was not consulted: 97.0% of queried models have no released child. The 5,222 count is an **outcome** of querying (nonempty model tree), not a selection criterion. |
| 6 | Filters on type, task, architecture, popularity, accessibility? | Only two: (a) the ID is absent from the 2025 baseline, which selects for models created or renamed after 2025-06-29; (b) the ID falls in the code-point prefix. No task, architecture, popularity or access filter exists in either script. |
| 7 | Limited by API availability, rate limits, time or storage? | Rate limiting is **recorded**: the log shows 4,851 "Rate limited" pauses and 133 h 56 min for 200,000 models (about 2.41 s per model). **No artifact states why 200,000 was chosen.** The default `--end` is 2,000, and 200,000 was passed explicitly. Throughput suggests querying the full delta would have taken about 37 days. That is an inference, not a documented rationale. |
| 8 | 5,222 selected up front, or a remainder after failures? | Neither. 200,000 were selected and all 200,000 succeeded. 5,222 is the subset with at least one derivative. |
| 9 | Attempted / succeeded / failed / empty | Attempted 200,000 sources (≥ 800,000 relation-filter requests; pagination requests are not logged). Succeeded 200,000. Failed 0. Empty 194,778. Nonempty 5,222. |
| 10 | Same period as the graph snapshot? | Close but not identical. The inventory dates from 2026-08-28. The reference crawl ran 2026-08-31 17:14 → 2026-09-06 07:11 UTC. Card metadata was retrieved 2026-09-01. The DOT graph dates from 2026-10-02. The reference therefore postdates the inventory by 3–9 days; 195 reference derivatives are absent from the inventory (see the missing-pairs package). |

## 3. Selection flow (`selection_flow.csv`)

| Selection stage | Models / pairs | Excluded | Exclusion reason |
|---|---:|---:|---|
| Crawled Hub model inventory (2026-08-28) | 3,029,377 | — | — |
| *Context: VulChain model nodes (paper)* | *1,885,384* | — | Not the sampling frame. The frame came from the inventory, not from graph nodes. The DOT used for Table IV has 1,888,591 model nodes; the paper uses the evidence-qualified count (see `ICDE2027_graph_cohort_audit_v2026_10_28`). |
| Eligible for model-tree queries (delta) | 1,324,194 | 1,705,183 | ID already present in the 2025-06-29 (CIKM) inventory |
| Selected for querying | 200,000 | 1,124,194 | Row ≥ 200,000 of the code-point-sorted delta (includes **all** lowercase-initial owners) |
| Queries attempted (sources) | 200,000 | 0 | — (4 relation filters each) |
| Successful queries | 200,000 | 0 | — |
| Nonempty model-tree responses | 5,222 | 194,778 | Hub listed no derivative under any relation |
| **Final population producing reference pairs** | **5,222** | — | This is the 5,222 in the manuscript |
| Reference pairs | 15,689 | — | 15,073 distinct derivatives |
| Recovered pairs | 14,668 | 1,021 | Not found as an exact-ID VulChain edge |

Population terms are kept distinct:
- **Query count:** 200,000 sources, ≥ 800,000 relation-filter requests.
- **Unique queried IDs:** 200,000.
- **Successful responses:** 200,000.
- **Models producing reference pairs:** 5,222.

## 4. What the selection implies

- **Every** queried source was new to the Hub, or renamed, after 2025-06-29.
- **None** of the 1,705,183 models already present in the 2025 crawl was queried. These baseline-era models are the parents of 72.1% of VulChain Model→Model edges (696,897 of 966,035).
- **None** of the 100 VulChain models with the most children was queried. Of these, 75 are baseline-era (e.g., `black-forest-labs/FLUX.1-dev`, `Qwen/Qwen1.5-0.5B`, `google/gemma-2b`, `meta-llama/Llama-3.1-8B-Instruct`), 16 are absent from the inventory, and 9 are in the unqueried part of the delta.
- **No** queried source has a lowercase-initial owner (0 of 200,000), while 64.6% of inventory models and 77.0% of the unqueried delta do. Owners such as `meta-llama`, `google`, `mistralai`, `unsloth` and `bartowski` are therefore unrepresented as upstreams.
- Derivatives are **not** restricted: 59.6% of the 15,073 reference derivatives have lowercase-initial owners, and 9,997 lie in the unqueried part of the delta.
- One frame side effect links to the missing-pair analysis. A repository **renamed** after 2025-06-29 enters the delta under its new name, because the new ID is absent from the baseline. In 432 of the 812 rename/alias misses (C6), the old ID named on the derivative card is present in the 2025 baseline. See `representativeness_report.md` §5.

No files outside this directory were modified.
