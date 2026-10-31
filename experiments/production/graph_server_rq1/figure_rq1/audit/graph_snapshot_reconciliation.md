<!-- Created: 2026-10-30 · Version: v2026.10.30-02 · Purpose: reconcile the released HuggingGraph_v3.dot with the manuscript's evidence-qualified analytical graph -->

# Full DOT vs analytical graph: reconciliation

**Result.**
- **Edges:** the analytical graph is the released graph minus **108,953 Dataset→Model `trained_on` edges**. Nothing is added or changed in any other family.
- **Nodes:** the 19,808 missing nodes (16,601 datasets and 3,207 models) are exactly the nodes whose **every** incident edge was among the removed ones. The builder writes nodes only as edge endpoints, so these nodes vanish with their edges.
- **Lineage:** Model→Model lineage (966,035 edges) is identical in both graphs, so RQ1 lineage results do not depend on which graph is used.

Machine output: `v02/graph_reconciliation.json`, produced by `scripts/reconcile_graphs.py` (read-only; 1 min 54 s).

## 1. Artifacts

| Role | File | sha256 | Counts |
|---|---|---|---|
| Released graph (authoritative, immutable) | `hugginggraph_v3_2026oct02_reproducibility/graph/HuggingGraph_v3.dot` | `348d92cd…` | 7,775,872 edges · 3,137,207 nodes |
| Release builder | `…/source/build_hugginggraph_v3.py` | `a5c96d10…` | 17 families in fixed order |
| Analytical graph (two identical builds) | `rq1_audit_2026Oct15/release_candidate/HuggingGraph_v3_candidate_build{1,2}.dot` | identical sha (`candidate_builds_identical = true`) | 7,666,919 edges · 3,117,399 nodes |
| Analytical builder | `release_candidate/build_hugginggraph_v3_candidate.py` | — | Diff vs release builder: only the expected constants (family-02 count 362,064→253,111; model 1,888,591→1,885,384; dataset 431,324→414,723; totals). Header says "logic unchanged. NOT the official release." |

## 2. Transformation, verified

| Check | Result |
|---|---|
| Families with byte-identical edge CSVs (release vs candidate) | **16 of 17** |
| Family 02 (Dataset→Model): release rows → candidate rows | 362,064 → 253,111. Candidate ⊆ release; **108,953 removed, 0 added**. All removed edges are `trained_on`. |
| Candidate family 02 = `evidence/top_level/dataset_model_edges_validated.csv` | **Yes, as a set** (253,111 = 253,111). The validated file stores bare IDs; the candidate adds `dataset::`/`model::` prefixes, so their sha256 differ. |
| DOT edge diff (release − candidate) | 108,953 edges, all `dataset->model`. Candidate − release: 0. Duplicate edge lines in either DOT: 0. |
| Nodes only in release | **19,808** = 16,601 `dataset::` + 3,207 `model::` |
| Nodes only in candidate | 0 |
| Every release-only node is an endpoint of a removed edge | **true** |
| Release-only model nodes with any Model→Model edge | **0** |
| Endpoints of removed edges that survive in the candidate | 83,716. They keep other edges. |

**Why the edges were removed** (prior audit, `cohort_graph_audit.md` §6; not re-derived here): the dataset string named on the model card does not resolve to exactly one dataset in the enumerated inventory. The prior audit gives these classes:
- ambiguous bare name: 55,115;
- owner/repo absent: 39,749;
- bare name absent: 13,558;
- malformed or placeholder: 531.

Examples of removed dataset nodes include `dataset::-`, `dataset::.`, `dataset::0420_train.jsonl` and `dataset::01_load_data_set`. The prior audit notes a minor class-boundary inconsistency with `RQ1_EVIDENCE_REPORT.md` (55,115 / 39,750 / 13,566 / 522; same total).

**Node removal is not a separate isolated-node filter.** It was checked in the implementation: the release and candidate builders emit no standalone node statements. A node exists only if some edge mentions it, so the 19,808 nodes disappear exactly when their last edge is removed. The reconciliation verifies this set equality directly.

## 3. Which graph each manuscript number refers to

| Manuscript item | Graph | Note |
|---|---|---|
| Table I-style totals 3,117,399 nodes / 7,666,919 edges / 1,885,384 model nodes | analytical (evidence-qualified) | Not the released DOT |
| Model→Model edges 966,035, Table IV graph counts | both (identical) | Family 01 unchanged |
| Figure 7 scalability (53.34 s, ≈146K edges/s) | **released DOT** | See `figure7_throughput_audit.md` |
| Released artifact | released DOT (`348d92cd…`) | The analytical DOT is a release candidate, not published |

**Recommended wording.** The manuscript should name the released graph (7,775,872 edges) and state that analyses use an evidence-qualified view that drops 108,953 Dataset→Model edges whose dataset name does not resolve to a unique inventory dataset. `graph_manuscript_corrections.tex` §B in `ICDE2027_graph_cohort_audit_v2026_10_28/` already contains such wording, and `icde_rq1_revised.tex` §F aligns with it.

No original artifact was modified. The checksums of all 49 v02 inputs, including both DOTs, all edge CSVs and the builders, are in `logs/v02_input_sha256_before.txt`.
