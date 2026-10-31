<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: evidence-backed diagnosis of the 1,021 Hub model-tree reference pairs that HuggingGraph v3 / VulChain does not recover (ICDE 2027 RQ1, Table IV tab:hub_agreement) -->

# Unrecovered Hub model-tree reference pairs: diagnostic report

**Scope.** This is a read-only diagnosis. No graph was rebuilt, no Hub API request was made, and no existing file was modified (§10). The graph used throughout is the released `HuggingGraph_v3.dot` (sha256 `348d92cd…`). Every copy with that name on the host is byte-identical: the archive copy, `HuggingGraph_v3_release/`, `mxr_project_06_ICDE/2026_ICDE/`, and the RQ1 rebuild and benchmark copies. The only differing DOT files are an older `.bak` from 2026-09-30 and `HuggingGraph_v3_candidate_build*.dot` (`25d669bd…`). The candidate is an "analytical view" that only replaces family 02 (Dataset→Model), so it is not a newer v3 release.

**Paths.** `$W` = `<REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working`; `$A` = `$W/2026_Fall_Extension/extension_updated_code/hugginggraph_v3_2026oct02_reproducibility`; `$M` = `$W/2026_Fall_Extension/models`. Input checksums are in `input_manifest.json`. Every claim below is computed by `scripts/diagnose_missing_pairs.py`, unless it is marked as a separate check.

## 1. Source artifacts

| Role | Artifact | Notes |
|---|---|---|
| Frozen graph (RQ1) | `$A/graph/HuggingGraph_v3.dot`, 2026-10-02, sha `348d92cd…` | 7,775,872 edges. 966,035 Model→Model edges (both endpoints `model::`), 1,888,591 model nodes. The DOT has no standalone node statements, so a model is a node only if it has at least one edge. After DOT unescaping, the Model→Model edge set equals `$A/edges/csv/01_model_model_edges.csv` exactly (6 rows differ only in `\\` escaping of Windows-path parent IDs). |
| Hub reference | `$M/graph_model_model_first_200k.csv` (sha `fa045591…`) and `.completed.txt` | Crawler `$M/graph_model_model_master.py`, v2026.08.31-01. Ran 2026-08-31 17:14 → 2026-09-06 07:11 UTC. For each of the first 200,000 rows of `delta_model-2026-Aug28.csv`, it queried `filter=base_model:{finetune,quantized,adapter,merge}:<id>` with full pagination. The error file holds only a header. HTTP 429 responses are retried without limit, so the many rate-limit pauses in the log did not truncate results. 5,222 sources have ≥1 pair. |
| Model inventory | `$A/raw/models/all_huggingface_models_2026Aug28.csv` | 3,029,377 IDs. This is the crawled model population. |
| Card metadata (extractor input) | `$A/raw/models/all_model_readme_metadata_2026Aug28.jsonl`, retrieved 2026-09-01 17:02–17:50 UTC | 1,911,017 `ok`, 1,110,353 `no_metadata` and 8,007 `not_returned_by_models_api`, which covers every inventory ID. |
| Later full cards | `$A/raw/models/all_model_readmes_full_2026Sep25.jsonl` | Used only as later corroborating evidence. |
| Lineage extraction | `$A/source/model_lineage_edges.py` (sha `7e984d91…`); `$A/evidence/top_level/model_lineage_edges{,_inferred,_merged}.csv` | Family 01 = merged = declared (943,861) ∪ inferred (22,174). Declared parents are taken verbatim from `base_model` and related fields. Only `strip()` is applied: no case folding and no inventory resolution for `base_model`. |
| Table IV generator | `$W/2026_Fall_Extension/extension_updated_code/rq1_audit_2026Oct15/scripts/eval_hf_tree_recall.py` → `hf_tree_random1k/smoke_test_first200k/{metrics.json,label_confusion.csv}` | `label_confusion.csv` (sha `9b5b889e…`) supplies the per-adaptation missing counts. |
| Historical context only | 2025 inventories (`$W/project_script/all_huggingface_models_Aug14.csv`, `$W/other_supportings/all_huggingface_models.csv`); `$A/evidence/top_level/model_tree_models.csv` | `model_tree_models.csv` is a 2025 derivative (identical to `helping_Emma/model_tree_models.csv`). It is not an independent reference, and it contains none of the 1,021 pairs. |

**Not found locally.** No manuscript `.tex` containing `tab:hub_agreement` exists under `$W` or `mxr_project_06_ICDE`. The published table values were therefore taken from the task statement and checked against `label_confusion.csv` and `metrics.json`.

## 2. Table IV reproduction

The same rule as the evaluator was applied, using the DOT as the graph:
- **Reference pairs:** the reference `(Source, Target)` pairs whose `Source` completed all four queries.
- **Label mapping:** the Hub's `merge` label is mapped to `merged`.
- **Recovered:** the exact, case-sensitive `owner/name` pair is a DOT Model→Model edge from a queried source, with any label.

| Adaptation | Reference pairs | Recovered | Missing | Missing rate |
|---|---:|---:|---:|---:|
| Fine-tune | 3,466 | 3,209 | 257 | 7.4% |
| Adapter | 1,350 | 1,280 | 70 | 5.2% |
| Quantized | 9,284 | 8,800 | 484 | 5.2% |
| Merge | 1,589 | 1,379 | 210 | 13.2% |
| **Total** | **15,689** | **14,668** | **1,021** | **6.5%** |

- **No discrepancy:** all 15 values equal the published table, `metrics.json` (`pair_recall.k` = 14,668) and the `MISSING` column of `label_confusion.csv`.
- **Identifier form:** only exact identifiers are used. No canonicalization or alias resolution is applied on either side, and canonicalized variants are reported here only as diagnostics.
- **Labels:** every reference pair carries exactly one Hub relation. Label-exact pairs = 7,336, as published. 1,399 graph pairs from queried sources are absent from the reference; these are not false positives.

## 3. Per-pair checks (all 1,021)

| Check (task §3) | Result | Evidence |
|---|---|---|
| Upstream is a graph node | 1,009 yes · 12 no | DOT model nodes |
| Derivative is a graph node | 833 yes · 188 no | DOT model nodes |
| Both present, edge missing | 823 | DOT |
| Edge present under case folding | 3 | DOT, case-insensitive pair |
| Edge present reversed | **0** | DOT |
| Edge present with another adaptation label | **0** (by construction: recovery ignores labels) | DOT |
| Edge present under a different upstream ID (alias/rename) | 812 primary; also the secondary factor of 10 C3 pairs and 1 C5 pair | DOT edge `P→derivative`, where P is the ID named on the derivative's card |
| Derivative card unavailable | 195 derivatives are not in the 2026-08-28 crawl inventory, so no card was collected. All 826 crawled derivatives have `status = ok` card metadata. | inventory; card metadata |
| Extracted, then dropped by filtering, dedup or assembly | **0**. No missing pair appears in the declared, inferred or merged lineage outputs. No crawled derivative card names the reference upstream exactly, so there was nothing to drop. | `model_lineage_edges{,_inferred,_merged}.csv` |
| Deleted, gated or private repository | Not shown to be causal. 19 derivatives were `restricted` (gated) on 2026-09-25, but all 19 had readable card metadata on 2026-09-01 and are classified C6. | `readmes_full_2026Sep25` |
| Hub relation unsupported by archived evidence | 0 under C8. 13 C6 pairs have no local corroboration (§5). | |
| Date inconsistency | Inventory 2026-08-28 < card metadata 2026-09-01 ≤ reference crawl 2026-08-31→09-06 < full cards 2026-09-25 < DOT 2026-10-02. One pair is consistent with a card edit after the metadata snapshot (C7). | file timestamps; `retrieved_at_utc` |

## 4. Root-cause classification (mutually exclusive)

**Decision order:**
1. Endpoint presence in the DOT: C1–C3.
2. A derivative that is a graph node only through other edges and was never crawled: C4.
3. The card's declared parent compared with the reference upstream: C5 (case only), then C6 (a different ID that is not in the inventory and whose edge is in the graph).
4. Later card evidence: C7.
5. Otherwise: C8.

**Confidence levels:**
- *Confirmed:* the stated fact is directly established by archived records.
- *Probable:* supported by indirect evidence.
- *Unresolved:* the mechanism is not supported locally.

| Root cause | Fine-tune | Adapter | Quantized | Merge | Total | % | Confirmed / probable / unresolved |
|---|---:|---:|---:|---:|---:|---:|---|
| C6 Identifier mismatch: the card names a different, non-inventory upstream ID (rename/transfer) | 207 | 46 | 387 | 172 | **812** | **79.5** | 637 / 162 / 13 |
| C2 Derivative absent from graph (not in crawled population) | 47 | 19 | 87 | 33 | **186** | **18.2** | 186 / 0 / 0 |
| C3 Upstream absent from graph | 1 | 4 | 5 | 0 | 10 | 1.0 | 10 / 0 / 0 |
| C4 Derivative is a graph node only as a referenced ID; its card was never crawled | 1 | 0 | 1 | 5 | 7 | 0.7 | 7 / 0 / 0 |
| C5 Identifier mismatch, case only | 0 | 0 | 3 | 0 | 3 | 0.3 | 3 / 0 / 0 |
| C1 Both endpoints absent from graph | 1 | 1 | 0 | 0 | 2 | 0.2 | 2 / 0 / 0 |
| C7 Temporal: the card names the upstream only in the later (09-25) README | 0 | 0 | 1 | 0 | 1 | 0.1 | 0 / 1 / 0 |
| C8 Unsupported by archived card | 0 | 0 | 0 | 0 | 0 | 0.0 | — |
| **Total** | **257** | **70** | **484** | **210** | **1,021** | **100** | 845 / 163 / 13 |

### C6: rename or transfer of the upstream repository (812)

**Mechanism.**
- In every C6 pair, the derivative's archived card (2026-09-01) declares a parent ID P that:
  - is not the reference upstream S, even ignoring case;
  - is **absent from the 2026-08-28 inventory**;
  - and P→derivative **is** an edge in the DOT.
- All 929 such P→derivative edges are `declared_parent` edges from the card's `base_model` field.
- The extractor keeps the ID as written, while the Hub lists the child under the current name S.
- The lineage relation is therefore present in VulChain, but keyed to a stale identifier.

**Confidence grading** (secondary factors in the ledger):
- *Confirmed* (637), at least one strong signal:
  - same repository name under a different owner, i.e. an ownership transfer, e.g. `LLM360/K2-V2` vs `IFM/K2-V2`, `AIDC-AI/Marco-o1` vs `ATH-MaaS/Marco-o1`;
  - or the upstream's own archived card or README names P exactly.
- *Probable* (162), moderate signals only:
  - same owner, e.g. `CYFRAGOVPL/PLLuM-12B-nc-instruct` vs `…-2412`;
  - a distinct old repository name appearing in the upstream's card;
  - or P listed in a 2025 inventory while S was not.
- *Unresolved* (13): no local corroboration, e.g. `WhiteRabbitNeo/WhiteRabbitNeo-V3-7B` vs `DeepHat/DeepHat-V1-7B`, or `Meddies/lfm25_merged` vs `HoangHa/pii_sft`. These pairs are still C6 by the archived facts (the card names P, P is not in the inventory, the edge exists under P). However, the archive cannot show that P and S are the same repository.

**Additional support.**
- For 29 C6 pairs, the derivative's 2026-09-25 README front matter names S, meaning the card was later updated to the new name.
- What is *not* available locally is a Hub redirect record. The rename/transfer explanation is therefore graded by the corroboration above rather than confirmed by redirect data.

### C2, C1 and C4: derivative never crawled (195 in total)

- None of these 195 derivatives is in the 2026-08-28 inventory, so the pipeline had no card to read.
- 188 of them are not graph nodes at all (C2, C1). Seven are nodes only because another card names them, e.g. `Cyclone-Labs/Solar-Dawn-31B` (C4).
- *Why* they are missing from the crawl cannot be established locally. Creation after 2026-08-28, a rename, or omission from the listing are all possible, and the archive holds no creation dates. The absence is therefore confirmed, but its cause is not.

### C3: upstream with no graph edges (10)

- The upstream is in the inventory, but its own card had `no_metadata` and no crawled card names it, so it has no edges.
- In all 10 pairs, the derivative card names a non-inventory alias, e.g. `tplr/TEMPLAR-I` for `1Covenant/TEMPLAR-I`, or `sunhaonlp/…` for `Alibaba-NLP/…`. These alias edges are in the DOT. This is the same mechanism as C6, recorded as a secondary factor (6 with strong corroboration).

### C5 and C7

- **C5:** for example, the card names `crownelius/…` while the Hub and inventory use `Crownelius/…`. The edge exists case-insensitively.
- **C7:** `HuggingFaceTB/SmolLM3-3B` → `AbteeXAILab/lumynax-infused-smollm3-3b-gguf`. The card metadata from 2026-09-01 declares no parent (it is listed in `derived_models_without_identifiable_parent`), but the 2026-09-25 front matter names SmolLM3-3B.

## 5. Aggregate statements

| Statement | Pairs | % of 1,021 |
|---|---:|---:|
| An endpoint absent from the graph (C1+C2+C3) | 198 | 19.4 |
| Both endpoints present, edge missing (C4–C7) | 823 | 80.6 |
| Attributable to identifier normalization or alias resolution (C5+C6) | 815 | 79.8 |
| — of which confirmed (C5 + confirmed C6) | 640 | 62.7 |
| Confirmed pipeline exclusions | 0 | 0.0 |
| Derivative card never collected (C1+C2+C4) | 195 | 19.1 |
| Unresolved: no archived support for the mechanism (C6-unresolved) | 13 | 1.3 |
| Primary cause unsupported by any archived evidence (C8) | 0 | 0.0 |

**Differences across adaptations.**
- **Merge has the highest missing rate** (13.2% vs 5.2–7.4%), and 82% of its misses are C6 (172/210).
- **Adapter has the largest share of uncrawled derivatives** (19+1 of 70 = 28.6%, C1+C2).
- Fine-tune (80.5% C6) and Quantized (80.0% C6) follow the overall pattern.

**Concentration.**
- The 1,021 misses involve 403 distinct upstreams; 231 of them contribute a single pair.
- Two owners account for 248 pairs (24.3%), all but one of them C6: `ATH-MaaS` (133; `ATH-MaaS/Marco-o1` alone has 59) and `DS-Archive` (115). These names suggest archive or transfer accounts, which is consistent with repositories moved from their original owners.
- The 15 most frequent upstreams account for 276 pairs (27.0%).
- Among uncrawled derivatives, no owner exceeds 15 pairs (largest: `mradermacher`).

**Labels on the alias edges.**
- For reference-quantized C6 pairs, the graph labels the P→child edge `finetune` in 285 of 387 cases.
- This mirrors the quantized→finetune default seen on recovered pairs. The missing pairs do not hide a different labeling behavior.

## 6. Implications for RQ1

1. **93.5% pair recovery.**
   - The figure is recall against the sampled Hub model-tree reference: the trees of 5,222 of the first 200,000 queried models. That sample is a prefix of the delta list, not a random sample.
   - It is not overall lineage recall.
   - Most of the shortfall (79.8%) is a naming failure: the lineage evidence is in the graph under a stale identifier.
   - Sensitivity only, with no published metric changed: if the 3 case mismatches and the 637 confirmed aliases were resolved, recovery would be 15,308/15,689 = 97.6%. Including all C6 pairs it would be 15,483/15,689 = 98.7%.
2. **Adaptation-label agreement.** This is computed on the 14,668 recovered pairs, so it is unaffected. Exact-label recall (7,336/15,689) counts the 1,021 misses in its denominator.
3. **Quantization-label disagreement.** Unchanged in direction: alias edges show the same default-finetune labeling.
4. **Default-assigned fine-tune.** 514 of the 929 alias edges carry the `base_model_present_default_finetune` basis. This matches the known weakness rather than adding a new one.
5. **Evidence-qualified lineage.** All alias edges are `declared_parent`. Missingness is not caused by evidence filtering.
6. **966,035 Model-to-Model edges.** The count is correct (DOT = family-01 CSV), but the same identifier issue affects the graph more broadly:
   - 121,771 edges (12.6%), from 18,195 distinct parent IDs, name a parent that is not in the crawled inventory;
   - 37,071 of those edges come from 1,034 case variants of inventory IDs;
   - 38,972 come from 1,355 un-namespaced legacy IDs, e.g. `bert-base-uncased`;
   - 290 parent IDs look like local paths.

   Node-level statistics, such as roots or descendants per model, may split one model across several identifiers. This report does not quantify that effect.

## 7. Evidence limitations

- No Hub redirect, rename or creation-date records are archived, so renames can only be graded through corroboration.
- Why the 195 derivatives are absent from the crawl is unknown.
- No live API check was made, by design.
- The published manuscript source was not found locally.

## 8. Recommended changes (not applied; each needs separate approval)

1. **Manuscript.** Use `rq1_paper_text.tex` (explanation, limitation, caption).
2. **Pipeline (future build, not RQ1).** Resolve declared parent IDs against the inventory, case-insensitively and through Hub redirects or `api/models/<id>` canonical names, recording both the raw and the canonical ID.
3. **Evaluator (sensitivity only).** Optionally report alias-resolved recall alongside the exact-match figure.

## 9. Verification

See `logs/test_results.txt` and `logs/input_unchanged_check.txt`.

## 10. Files

All outputs are new files in this directory. No existing file was modified or regenerated.
