<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: definitions, deduplication and matching checks for the 15,689 Hub-reference pairs (ICDE 2027 Table IV) -->

# Reference-pair validation

Source: `outputs/selection_audit.json`, keys `reference`, `table_iv` and `endpoint_edge_label`. The tests (`tests/test_selection_audit.py::ReferenceSet`) recompute these values directly from the CSVs, without using the audit script's logic.

## 1. What a reference pair is

A reference pair is a row `(Source, Edge_type, Target)` of `graph_model_model_first_200k.csv`:
- `Source` is a queried model.
- `Target` is a Hub model returned by `filter=base_model:<Edge_type>:<Source>`, where `Edge_type` ∈ {finetune, quantized, adapter, merge}.
- The crawler drops `Target == Source` and deduplicates rows across restarts.
- The evaluator maps the Hub's `merge` label to `merged` and keeps only rows whose `Source` completed all four queries.

| Check | Result |
|---|---|
| Raw rows | 15,689 |
| Distinct raw rows | 15,689 (no duplicate rows) |
| Rows whose source did not complete all 4 queries | 0 |
| Distinct triples (after `merge` → `merged`) | 15,689 |
| **Distinct (parent, derivative) pairs** | **15,689** |
| Pairs listed under more than one Hub relation | **0**. Each pair has exactly one category, so the four Table IV rows partition the pairs. |
| Self-loops | 0 |
| IDs with leading/trailing whitespace | 0 |
| Distinct upstreams (sources) | 5,222. All are among the 200,000 queried. |
| Distinct derivatives | 15,073. 401 derivatives have two or more reference parents (e.g., merges). |
| Pairs whose derivative is itself a queried model | 4,571 |
| Pairs whose derivative is also one of the 5,222 sources | 575 |
| Pairs whose derivative lies **outside** the 200,000 queried set | 11,118. Allowed by design: only upstreams were selected. |
| Hub label counts | finetune 3,466 · quantized 9,284 · adapter 1,350 · merge 1,589 |

**Answers.**
- **Unique pairs or category records?** 15,689 is both: the counts coincide because no pair has two labels.
- **Duplicates removed?** Yes. The crawler deduplicates; the raw file has no duplicate rows and no multi-label pairs.
- **Can a pair appear in several categories?** Possible in principle, but it never occurs here.
- **Pairs involving models outside the queried set?** Yes, on the derivative side: 11,118 pairs. Upstreams are always queried models.
- **Grouped by the Hub's labels?** Yes. Table IV rows use the Hub relation, not VulChain's label.

## 2. Matching, evaluated in three separate layers

| Layer | Rule | Result over 15,689 pairs |
|---|---|---|
| **Endpoint presence (inventory)** | ID ∈ 2026-08-28 inventory | Upstream: 15,689 present. Derivative: 15,494 present, 195 absent. |
| **Endpoint presence (M→M edge set)** | ID appears as an endpoint of any released Model→Model edge | Upstream: 15,512 present, 177 absent (no released lineage edge at all). Derivative: 15,494 present, 195 absent. DOT node presence (any edge family) is in `../hub_reference_missing_pairs_2027/` (upstream 12 absent, derivative 188 absent, among the missing pairs). |
| **Lineage-edge presence** | Exact, case-sensitive `(owner/name, owner/name)` pair present as a released Model→Model edge after removing the `model::` prefix, **with any label** | **14,668 recovered**, 1,021 not recovered. 826 of the 1,021 have both endpoints in the inventory. |
| **Label agreement** | Hub label ∈ released labels for that pair | 7,336 label-exact. That is 46.8% of reference pairs and 50.0% of recovered pairs. |

Recovery uses exact identifiers and is independent of adaptation labels (`eval_hf_tree_recall.py` :74). Label agreement is computed separately (:75). None of the following is applied: case folding, alias resolution or reversal. 0 unrecovered pairs exist reversed.

## 3. Table IV reproduction (source data unchanged)

| Adaptation | Reference | Recovered | Missing | Published | Match |
|---|---:|---:|---:|---|---|
| Fine-tune | 3,466 | 3,209 | 257 | 3,466 / 3,209 / 257 | ✓ |
| Adapter | 1,350 | 1,280 | 70 | 1,350 / 1,280 / 70 | ✓ |
| Quantized | 9,284 | 8,800 | 484 | 9,284 / 8,800 / 484 | ✓ |
| Merge | 1,589 | 1,379 | 210 | 1,589 / 1,379 / 210 | ✓ |
| **Total** | **15,689** | **14,668** | **1,021** | 15,689 / 14,668 / 1,021 | ✓ |

**Cross-checks.**
- `metrics.json`: `queried_sources` = 200,000, `reference_pairs` = 15,689, `pair_recall.k` = 14,668, Wilson [0.93096, 0.93868]. All values are reproduced exactly.
- The released family-01 CSV (966,035 triples, 965,960 distinct pairs, 111,816 distinct parents) gives 16,067 released pairs from queried sources. Of those, 1,399 are absent from the reference. They are not false positives: the Hub index covers only indexed `base_model` tags.

**Discrepancies found:** none in Table IV. The one manuscript discrepancy is the label "Hub models queried = 5,222". The value 5,222 counts queried models **with at least one Hub derivative**. The number queried is 200,000.

## 4. Independence of the reference

The reference is the Hub's `base_model:<relation>:<model>` index, as the crawler's filter string shows. VulChain's recovered edges come almost entirely from the card's declared parent (`declared_parent` = 14,660 of 14,668 recovered pairs). Both sides therefore read the same card metadata field. Table IV measures how faithfully VulChain reproduces the Hub's own reading of declared base models. It does not measure agreement with an independent lineage ground truth.

No files outside this directory were modified.
