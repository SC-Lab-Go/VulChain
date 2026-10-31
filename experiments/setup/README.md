# Experimental setup: model cohort

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: text-generation one-hop derivatives across identification, readiness and selection | `tab:model_corpus` | `setup_table_01.py` | PASS (19/19) |

The table has three rows. Each counts distinct model IDs per adaptation label
plus the actual base ∪ derivative union.

| Row | Source |
|---|---|
| 1-hop der. | One-hop fine-tune, adapter, quantized, and merge children of text-generation lineage roots in the October 2 graph. 3,106 of the 4,887 roots have at least one such child. |
| Static-ready | The subset passing static inference-readiness checks. |
| Sel. cohort | The evaluated cohort as of the 2026-10-30 snapshot: 45 bases, 482 models. |

The first two rows come from the frozen Table II baseline (v2026.10.27-04),
shipped as `data/table2_baseline/table2_stage_records.csv`.

```bash
python experiments/setup/setup_table_01.py
```

**Notes from the Graph Server audit (2026-10-28).**

- **Static-ready "Base" (782)** counts upstream models with at least one ready
  child. Only 682 of these bases are themselves ready.
- **Static-ready total (8,745)** is the union count. 8,645 of those models are
  actually ready.
- **The static-ready stage is not purely from the October 2 snapshot.** It
  adds a 2026-10-10 live-metadata preflight.

The counts are verified. These notes concern how the rows are described.
