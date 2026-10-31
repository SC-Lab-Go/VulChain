<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: compare the 200,000 queried models (and the 5,222 producing reference pairs) with the eligible and excluded model populations -->

# Representativeness of the queried models

**Bottom line.** The queried population is a deterministic, non-probability prefix of models that are **new since the 2025 crawl**. Two exclusions are structural, not marginal:
- **0 of 200,000** queried models have a lowercase-initial owner.
- **0** of the 1,705,183 baseline-era models were queried, and those models originate **72.1%** of VulChain's Model→Model edges.

Inside the delta, the prefix resembles the unqueried remainder on task and library mix. It still cannot be weighted to the Hub, for two reasons:
- Recovery varies across owner groups inside the prefix (83.1%–98.5%).
- The excluded groups have zero coverage.

All numbers come from `outputs/selection_audit.json`. "Prefix" means the 200,000 queried models; "delta rest" means the 1,124,194 delta models not queried; "baseline-era" means the 1,705,183 inventory models that already existed in 2025.

## 1. Sampling frame used for comparison

The relevant eligible population is the **delta** (1,324,194), since only delta models could be selected. The table also shows the baseline-era models, which were never eligible, to show what a Hub-wide claim would leave out.

## 2. Owner-name composition (the selection variable itself)

| First character of model ID | Prefix (200,000) | Delta rest (1,124,194) | Baseline-era (1,705,183) | Inventory (3,029,377) |
|---|---:|---:|---:|---:|
| digit | 7.0% | 0.0% | 0.6% | 0.8% |
| uppercase | 93.0% | 23.0% | 35.3% | 34.5% |
| lowercase | **0.0%** | 77.0% | 64.1% | 64.6% |

Owner buckets within the prefix: 0–9 14,064 · A–C 81,428 · D–F 47,905 · G–I 41,284 · J 15,319.

## 3. Lineage degree (graph out-degree = distinct released children)

| | Prefix | Delta rest | Baseline-era |
|---|---:|---:|---:|
| Models with ≥ 1 released child | 5,982 (2.99%) | 29,345 (2.61%) | 58,294 (3.42%) |
| Mean released children per model | 0.080 | 0.117 | 0.409 |
| Models with ≥ 50 children | 18 (0.009%) | 262 (0.023%) | 1,053 (0.062%) |
| Share of VulChain M→M pairs whose parent is in this group | **1.66%** | 13.59% | **72.14%** (12.61% have a parent outside the inventory) |
| Top-100 VulChain parents in this group | **0** | 9 | 75 (16 outside the inventory) |

The prefix and the delta rest have similar rates of having any child, but the prefix has a thinner high-degree tail. The prefix contains no hub-scale upstream; its largest Hub family is `HuggingFaceTB/SmolLM3-3B` with 312 reference pairs. The heavily derived baseline-era base models are absent entirely.

## 4. Task, library and card availability (card metadata retrieved 2026-09-01)

`pipeline_tag` and `library_name` come from the card YAML. "none" means the field was absent.

| | Prefix | Delta rest | Baseline-era | 5,222 reference sources | 93,621 graph parents in inventory |
|---|---:|---:|---:|---:|---:|
| Card `status = ok` | 56.8% | 62.1% | 64.5% | 88.2% | 88.8% |
| `no_metadata` | 42.9% | 37.3% | 35.5% | 11.7% | 11.2% |
| `not_returned_by_models_api` | 0.35% | 0.61% | 0.03% | 0.11% | 0.04% |
| text-generation | 7.4% | 6.9% | 2.7% | **27.7%** | 16.3% |
| image-text-to-text | 1.4% | 1.3% | 0.2% | 7.2% | 3.1% |
| text-to-image | 1.4% | 1.4% | 1.9% | 0.6% | 0.8% |
| library = transformers | 18.2% | 20.1% | 17.1% | 45.1% | 39.9% |
| library = peft | 3.8% | 4.6% | 11.7% | 1.0% | 2.2% |

Total-variation distance (TVD):

| Comparison | pipeline_tag | library |
|---|---:|---:|
| Prefix vs delta rest | 0.017 | 0.059 |
| Prefix vs baseline-era | 0.097 | 0.101 |
| 5,222 reference sources vs graph parents in inventory | 0.173 | 0.064 |

**Reading.**
- Within the eligible delta, the alphabetical prefix differs little from the rest on task and library mix.
- Against baseline-era models it differs more, for example in PEFT adapters (3.8% vs 11.7%).
- The 5,222 sources that produced pairs are enriched for text-generation and image-text-to-text models compared with VulChain parents overall.

## 5. Released adaptation labels and provenance evidence

| Released label (pair–label rows) | All VulChain M→M | Edges from queried sources |
|---|---:|---:|
| finetune | 73.5% | 63.6% |
| adapter | 13.6% | 7.5% |
| quantized | 6.8% | 15.9% |
| merged | 5.5% | 10.7% |
| new_version / converted | 0.4% / 0.1% | 1.9% / 0.5% |

TVD = 0.159. The reference's Hub-label mix (59% quantized, 22% fine-tune, 10% merge, 9% adapter) therefore differs from the graph's.

| Lineage evidence (merged evidence file) | All edges | Queried sources | Delta rest | Baseline-era |
|---|---:|---:|---:|---:|
| `declared_parent` (explicit) | 97.7% | 92.9% | 94.6% | 98.0% |
| name heuristics (inferred) | 1.6% | 5.2% | 4.3% | 1.4% |
| `new_version_field` | 0.4% | 1.9% | 1.1% | 0.3% |

The queried sources carry more inferred and `new_version` edges than the graph as a whole. Of the 14,668 recovered pairs, 14,660 are `declared_parent` edges and 8 are `new_version_field` edges (`metrics.json`). The reference therefore evaluates almost only the explicit-declaration path.

## 6. Upstream versus derivative role

Only upstreams were selected. Derivatives are whatever the Hub returned:
- 15,073 distinct derivatives.
- 59.6% have lowercase-initial owners.
- 9,997 are in the delta rest, 4,346 in the prefix, 552 baseline-era, and 178 outside the inventory.

The derivative-side composition is therefore broad. Upstream-side coverage is the constraint.

## 7. Recovery heterogeneity inside the sample (descriptive, source-clustered 95% CI)

| Upstream owner bucket | Sources | Pairs | Recovered | Recovery | Clustered 95% CI |
|---|---:|---:|---:|---:|---|
| 0–9 | 167 | 379 | 315 | 83.1% | [74.5, 91.7] |
| A–C | 2,242 | 6,382 | 5,940 | 93.1% | [90.9, 95.2] |
| D–F | 1,495 | 4,452 | 4,128 | 92.7% | [90.5, 94.9] |
| G–I | 1,006 | 3,069 | 2,899 | 94.5% | [91.9, 97.1] |
| J (partial) | 312 | 1,407 | 1,386 | 98.5% | [97.6, 99.4] |
| K–Z, a–z | 0 | 0 | — | **not observed** | — |

Recovery depends on which owners are present, and the excluded buckets include most of the Hub's major upstream organizations. The 93.5% therefore cannot be transported to them by assumption.

Further strata (in `statistical_assessment.md` and `selection_audit.json` → `statistics.strata`):
- **Upstream with no released child:** 179 sources, 377 pairs, 0% recovered.
- **Merge:** 86.8%.
- **Source `pipeline_tag = text-to-image`:** 56.7% (29 sources).
- **Derivatives with uppercase-initial owners:** 90.4%; lowercase-initial: 95.7%.

## 8. Link with the missing-pair diagnostic (`../hub_reference_missing_pairs_2027/`)

That package was read only; nothing in it was changed or duplicated.
- **Ledger agreement:** its 1,021-row ledger equals the set of unrecovered pairs recomputed here.
- **Shared pattern:**
  - The delta frame is "IDs absent from the 2025 inventory", so any repository **renamed** after 2025-06-29 is eligible under its new name.
  - Renames are the dominant cause of unrecovered pairs: C6 accounts for 812 of 1,021.
  - In **432 of 812** C6 pairs, the old upstream ID named on the derivative card is in the 2025 baseline.
  - These pairs come from **96** of the 5,222 sources, which hold 605 pairs.
  - Excluding those 96 sources raises recovery to 96.2% (14,505 / 15,084). This is a descriptive sensitivity check, not a corrected estimate.
- **Direction of the effect:** the selection rule plausibly **enriches** the sample for recently renamed upstreams. Rename-driven recovery in baseline-era models was not measured, so the direction and size of the bias relative to the full Hub remain **not evaluable** from archived data.
- **Missing pairs by owner bucket:**
  - 0–9: 64 (C6 57)
  - A–C: 442 (C6 372)
  - D–F: 324 (C6 271)
  - G–I: 170 (C6 106)
  - J: 21 (C6 6)
- **Three separate questions:** why 200,000 / 5,222 models were queried (this package), why 1,021 pairs were not recovered (missing-pairs package), and why labels disagree (the 6,962 quantized→finetune cell; `model_tree_agreement.md` §4) are distinct issues. They overlap only through the rename pathway above.

## 9. Variables that could not be evaluated

| Variable | Status | Reason |
|---|---|---|
| Downloads / likes / popularity | **Not evaluable** | Inventory and card files hold no download or like counts for 2026-08-28. |
| Model size (parameters, bytes) | **Not evaluable** | Not archived. |
| Architecture / model family | **Not evaluable** (owner prefix and `pipeline_tag` only as proxies) | No `config.json` architecture field is archived. |
| Repository creation date | **Proxy only** | Baseline membership (present 2025-06-29 or not). Exact `createdAt` not archived. |
| Gated / private / deleted at query time | **Partly** | 0 query failures. Card status at 2026-09-01 shown in §4. Gating is visible only in the 2026-09-25 README crawl, so it is not snapshot-aligned. |
| Adaptation category of non-queried models | **Not evaluable** | The Hub relation is known only for queried sources. Released labels for all edges are shown in §5. |

No files outside this directory were modified.
