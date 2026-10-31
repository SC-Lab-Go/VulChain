# RQ5: Heterogeneous context and downstream exposure

**Objective.** Use the graph's Space and GitHub relationships to describe
where models with verified findings are associated downstream.

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: heterogeneous associations and findings | `tab:rq5` | `rq5_table_01.py` | PASS (35/35) |

| Code | Inputs | Calc. reproduced | Values verified | Public | Restricted |
|---|---|---|---|---|---|
| yes | yes (snapshot restricted; graph export and release edges public) | yes | 35/35 | no | yes (`data/rq_snapshot/`) |

**How it is computed.**

- The calculation runs through `rq5_graph()`, `lineage_components()`,
  `rq5_reach()`, `rq5_shared()`, and `rq5_compute()`.
- These are copied verbatim from
  `production/RQ2_analysis/v2026.10.27-01/unified_exports.py`.
- `table_macros()` in `rq5_table_01.py` is the `tab:rq5` subset of the
  production `rq5_macros()`.

## What the table reports

- **Associations of the evaluated cohort:**
  - one-hop base–adaptation relationships;
  - models linked to Spaces, and the Spaces linked to them;
  - models with Space or GitHub references;
  - distinct GitHub repositories linked to them.
- **Per finding category:**
  - derivatives with eligible tests;
  - instance-recurrent derivatives, and how many of those have a Space link;
  - shared canonical artifacts (emitted by ≥2 models), with emitters per
    artifact (median and maximum) and the number that have a Space-linked
    emitter.
- **Concentration:**
  - models with verified findings;
  - their Model→Space edges;
  - the share of those edges held by the single most-linked model;
  - distinct linked Spaces, with and without that model.

```bash
python experiments/RQ5/rq5_table_01.py \
    --lineage-csv <release>/edges/csv/01_model_model_edges.csv
```

**Inputs.**
- The snapshot files in `data/rq_snapshot/`.
- The RQ5 graph export in `data/rq_snapshot/rq5_graph_export/`. This is a
  cohort subgraph of the October 2 release, with provenance references to its
  release rows.
- The released Model→Model edge file, checked by SHA-256. It is used for
  lineage components.

**Expected results.**

| Value | Expected |
|---|---:|
| Evaluated pairs | 437 |
| Most-linked model's share of Model→Space edges | 25.77% |
| Maximum emitters of one hallucinated package | 184 |

**Limitations.**
- Space and GitHub links are recorded associations, not verified deployments.
- Exposure counts describe potential reach, not exploitation.
