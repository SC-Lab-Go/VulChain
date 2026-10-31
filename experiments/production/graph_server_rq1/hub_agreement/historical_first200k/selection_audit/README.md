<!--
Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Read-only audit of how the 200,000 queried / 5,222 nonempty Hub model-tree sources behind
         ICDE 2027 Table IV (15,689 reference pairs, 14,668 recovered) were selected, and how far the
         93.5% recovery generalizes. Companion to ../hub_reference_missing_pairs_2027/ (not modified).
-->

# Hub-reference selection audit (ICDE 2027, RQ1 / Table IV)

## Findings

1. **5,222 is not the number of models queried.** The crawl queried **200,000** models, all of which succeeded with 0 failures. **5,222** of them had at least one Hub derivative, and **194,778** had none.
2. **Selection rule.** The queried models are the first 200,000 rows of `delta_model-2026-Aug28.csv`. That file holds the 1,324,194 inventory IDs (inventory of 2026-08-28) that are absent from the 2025-06-29 (CIKM) inventory, sorted in Python code-point order. The selection is a deterministic convenience prefix. It is not random, not stratified, and not based on popularity or lineage. No inclusion probabilities exist. No artifact records why the cutoff is 200,000; the crawl took 134 h under rate limiting.
3. **Coverage gaps.**
   - The prefix contains no lowercase-initial owner and no model from the 2025 baseline.
   - Baseline-era models are the parents of 72.1% of VulChain Model→Model edges.
   - Within the prefix, recovery ranges from 83.1% to 98.5% across owner groups.
4. **Table IV reproduces exactly** from unchanged inputs: 15,689 / 14,668 / 1,021 and every per-category row.
5. **Uncertainty.** The Wilson interval [93.1, 93.9] is a correct binomial interval for this pair set. Clustering pairs by upstream gives a design effect of about 10, and the cluster-bootstrap interval is [92.2, 94.6].
6. **Recommendation:** keep the reference set, with methodological limitations stated (see `statistical_assessment.md` and the final summary).

## Files

| File | Content |
|---|---|
| `selection_trace.md` | Reconstructed selection procedure and answers to the ten selection questions |
| `selection_flow.csv` | Counts and exclusions from the inventory to recovered pairs |
| `representativeness_report.md` | Queried models vs eligible, excluded and graph populations; link with the missing-pairs package |
| `reference_pair_validation.md` | Pair definition, deduplication, endpoint / edge / label layers, Table IV reproduction |
| `statistical_assessment.md` | Generalizability, clustered intervals, heterogeneity and sensitivity diagnostics |
| `icde_paper_text.tex` | Overleaf-ready methodology, RQ1 clarification and threats-to-validity text |
| `scripts/audit_selection.py` | The audit (Python 3.10 standard library only; offline; read-only) |
| `outputs/selection_audit.json` | All computed values (`sort_keys`; deterministic) |
| `outputs/per_source_recovery.csv` | One row per reference source (5,222) |
| `outputs/selection_flow.csv` | Script-generated copy of the flow table |
| `tests/test_selection_audit.py` | Reproducibility and consistency tests |
| `logs/` | Input checksums before and after, run stdout, test results. `logs/run1_pre_determinism_fix_outputs/` holds a first run made before set-ordering fixes; its values are identical and it is kept for traceability only. |

`selection_flow.csv` at the package root is a copy of `outputs/selection_flow.csv`.

## Methodology

- **Inputs.** All 20 input paths and their sha256 checksums are listed in `outputs/selection_audit.json` → `inputs` and in `logs/input_sha256_before.txt`. They comprise the inventories and delta builder, the crawler and its command notes, the reference CSV with its sidecars and log, the released family-01 edges, the merged lineage evidence, the card metadata, the evaluator and its published outputs, the prepared random-1k plan, and the missing-pairs ledger and summary.
- **Frame.** The script recomputes `sorted(inventory − baseline)` and confirms it equals the delta file. It then checks that the 200,000-row prefix equals the set of completed queries.
- **Reference and Table IV.** The script applies the evaluator's rules: keep sources that completed all four queries, map `merge` → `merged`, and count a pair as recovered on an exact case-sensitive ID pair with any label.
- **Representativeness.** It compares the prefix, the unqueried delta, the baseline-era models, the 5,222 sources and the graph parents on these dimensions:
  - owner-initial class;
  - released out-degree;
  - card status, `pipeline_tag` and `library_name`;
  - released label mix and evidence mix.
- **Statistics.** The pooled Wilson interval is computed alongside:
  - cluster-robust (linearization) intervals for the ratio estimator, clustered by upstream and by owner;
  - cluster bootstraps (2,000 replicates; seeds 20261030 and 20261031);
  - per-source distributions and stratified descriptive recovery.
- **Not done.** No live Hub API requests, no graph or edge regeneration, no changes to Table IV or to any RQ1–RQ5 result or macro.

## Reproduction

```bash
cd <REDACTED_HOME>/Graph_Lab/research_projects/mxr_project_01_debug/working/validation/hub_reference_selection_audit_2027
# 1. Re-run the audit into a NEW directory (about 50 s; the script refuses a non-empty --out-dir)
/usr/bin/python3 -B scripts/audit_selection.py --out-dir "$(mktemp -d)/audit"
# 2. Run the tests against the stored outputs (about 1 min)
/usr/bin/python3 -B tests/test_selection_audit.py -v
# 3. Optionally also require a byte-identical re-run
SELECTION_AUDIT_RERUN=1 /usr/bin/python3 -B tests/test_selection_audit.py -v
# 4. Confirm inputs are unchanged
sha256sum -c logs/input_sha256_before.txt
```

## Change record

```
2026-10-30 v2026.10.30-01
- Created this directory and all files in it (new files only).
- No existing file was modified, moved or deleted. No backup was needed because nothing existing was edited.
- Behavior, defaults, dependencies and existing documentation: unchanged.
```
