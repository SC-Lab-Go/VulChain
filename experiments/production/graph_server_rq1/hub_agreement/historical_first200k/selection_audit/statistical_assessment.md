<!-- Created: 2026-10-30 · Version: v2026.10.30-01 · Purpose: generalizability and uncertainty assessment for the 93.5% Hub-reference pair recovery (new sensitivity diagnostics; Table IV unchanged) -->

# Statistical assessment of 14,668 / 15,689 = 93.5%

All values come from `outputs/selection_audit.json` → `statistics`, and per-source rows are in `outputs/per_source_recovery.csv`. The published Table IV and its Wilson intervals are **not altered**. Everything below is an additional diagnostic.

## 1. What the estimate is

| Question | Answer |
|---|---|
| Unweighted rate over the collected reference set? | **Yes.** It is the pooled ratio Σ recovered / Σ reference pairs, with every pair weighted equally. |
| Collected through probability sampling? | **No.** The sources are a deterministic code-point prefix of the delta (`selection_trace.md`). |
| Inclusion probabilities recorded? | **No.** For a Hub-wide target, inclusion is 1 for prefix IDs and 0 for the rest, including all lowercase-initial owners and all baseline-era models. Design-based weighting is therefore impossible. |
| Do highly connected models contribute disproportionately? | **Moderately.** Pairs per source: median 2, 90th percentile 5, max 312. The top source holds 2.0% of pairs, the top 10 hold 7.2%, and the top 50 hold 17.6%. 2,506 sources contribute exactly one pair. |
| Does recovery vary across groups? | **Yes** (§3). |
| Could selection over- or under-estimate Hub-wide recovery? | **Either direction is possible; the size is not evaluable.** See §4. |
| Are the Wilson intervals appropriate? | **As a binomial interval over this fixed pair set, they are computed correctly.** They are not an uncertainty statement about a Hub-wide quantity, and they understate sampling variability because pairs cluster within upstreams (§2). |

## 2. Clustering

Pairs that share an upstream are not independent: 4,819 sources recover all of their pairs, 185 recover none, and 218 are partial. The Wilson interval treats the 15,689 pairs as independent Bernoulli draws.

| Interval for 93.49% | 95% interval | Half-width | Design effect | Effective n |
|---|---|---:|---:|---:|
| Wilson, pairs independent (published) | [93.10, 93.87] (shown as [93.1, 93.9]) | 0.39 pp | 1 | 15,689 |
| Cluster-robust, by queried upstream (5,222 clusters) | [92.27, 94.71] | 1.22 pp | 10.0 | ≈ 1,569 |
| Cluster bootstrap by upstream (2,000 reps, seed 20261030) | [92.18, 94.59] (shown as [92.2, 94.6]) | ≈ 1.2 pp | — | — |
| Cluster-robust, by upstream **owner** (1,827 clusters) | [90.83, 96.16] | 2.67 pp | 47.7 | ≈ 329 |
| Cluster bootstrap by owner (2,000 reps, seed 20261031) | [90.56, 95.82] | ≈ 2.6 pp | — | — |

Per adaptation category, with clustering by upstream:

| Category | Recovery | Wilson 95% | Clustered 95% | Design effect |
|---|---:|---|---|---:|
| Fine-tune | 92.6% | [91.7, 93.4] | [90.3, 94.9] | 6.7 |
| Adapter | 94.8% | [93.5, 95.9] | [92.5, 97.1] | 3.8 |
| Quantized | 94.8% | [94.3, 95.2] | [93.8, 95.8] | 4.6 |
| Merge | 86.8% | [85.0, 88.4] | [80.8, 92.7] | 12.8 |

Even read narrowly, as uncertainty over "upstreams like these", the interval is about 3× wider than published, or about 7× wider under owner clustering. The point estimate is unaffected.

## 3. Heterogeneity and sensitivity (descriptive)

| Diagnostic | Value |
|---|---|
| Unweighted mean of per-source recovery (each upstream counts once) | 94.9% (median 100%) |
| Excluding the 1 / 10 / 50 largest sources | 93.4% / 93.4% / 93.4%. Not driven by a few giant families. |
| Sources accounting for 50% of the 1,021 misses | 60 of 5,222. 403 sources have any miss. |
| By owner bucket | 0–9 83.1% · A–C 93.1% · D–F 92.7% · G–I 94.5% · J 98.5% |
| By pairs per source | 1: 95.1% · 2–4: 95.1% · 5–9: 90.2% · 10–49: 91.9% · 50+: 95.2% |
| Upstream with no released child (179 sources, 377 pairs) | 0.0% |
| Excluding those upstreams (as a graph-conditioned sample would) | 95.8% (14,668 / 15,312) |
| Excluding 96 upstreams whose C6 misses cite an old ID present in the 2025 baseline | 96.2% (14,505 / 15,084) |
| Source `pipeline_tag` | text-generation 92.3% · image-text-to-text 93.7% · text-to-image 56.7% (29 sources) · none 94.3% |

## 4. Can 93.5% be generalized?

**Not to the Hub or to all VulChain lineage.** Recovery is measured only for upstreams that meet three conditions:
- they are new or renamed since 2025-06-29;
- their owner IDs sort before `John6666/jedpoint-real-v8-vae-sdxl` in code-point order;
- they have at least one Hub-indexed derivative.

The excluded upstreams originate 98.3% of VulChain's M→M pairs. They include every top-100 parent and all lowercase-initial owners.

Recovery varies by 15 percentage points across owner groups inside the sample. No covariate is observed for the excluded groups that would support reweighting.

Two mechanisms pull in opposite directions:
- **Possible overestimation elsewhere:** the excluded upstreams include hub-scale bases with tens of thousands of children (e.g., `black-forest-labs/FLUX.1-dev`, 43,436 released children). If their Hub trees contain more derivatives outside the crawled inventory, or more alias references, recovery would be lower there. This was not measured.
- **Possible underestimation:** the delta frame enriches for recently renamed upstreams, which drive 79.5% of misses. Older, baseline-era bases may have fewer stale-ID derivatives. This was not measured either.

Neither direction is verified. **No population-level recovery claim is supported.** The supported claim is recall against this reference set of 15,689 Hub-listed pairs from 5,222 upstreams.

## 5. Recommendation on intervals

- Keep the published Wilson intervals in Table IV unchanged, but describe them as binomial intervals over the reference pairs.
- Optionally add the upstream-clustered interval [92.2, 94.6] in the text or a footnote as a sensitivity analysis.
- Do not present either interval as a Hub-wide confidence interval.

No files outside this directory were modified.
