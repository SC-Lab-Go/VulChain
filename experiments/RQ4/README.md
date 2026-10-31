# RQ4: Adaptation types and failure persistence

**Objective.** Compare same-prompt recurrence across adaptation categories.

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: recurrence by adaptation category | `tab:rq4-adaptation-split` | `rq4_table_01.py` | PASS (80/80) |

| Code | Inputs | Calc. reproduced | Values verified | Public | Restricted |
|---|---|---|---|---|---|
| yes | yes (restricted; hash-checked) | yes, from comparison records | 80/80 | no | yes (`data/rq_snapshot/`) |

**How it is computed.**

- Strata come from `stratum()`. A fine-tune with a default-assigned label is
  dFT; any other fine-tune is ndFT.
- The table rows come from `rq4_rows()` and `rq4_table_vii_macros()`.
- These functions are copied verbatim from `production/…/unified_analysis.py`
  and `production/…/unified_exports.py`.
- The production run also checks every stratum cell with an independent SQL
  recount (`aggregate_all()`).

**Setup.** Declared comparisons are split by recorded adaptation stratum:

| Stratum | Meaning |
|---|---|
| AD | adapter |
| ndFT | fine-tune with explicit evidence |
| dFT | default-assigned fine-tune |
| QT | quantized |
| MG | merge |

The table pools ndFT and dFT as "Finetune". For each category it reports:

- **Bases:** distinct parents with an eligible test;
- **Derivatives:** distinct children with a class-level recurrence;
- **Tests;**
- class-level and instance-level recurrence (count and rate).

The strata partition the RQ3 Declared totals exactly.

```bash
python experiments/RQ4/rq4_table_01.py
```

**Expected results.** The Overall rows equal RQ3:

| Category | Class-level | Instance-level |
|---|---:|---:|
| Package hallucination | 31.91% | 23.75% |
| NXDOMAIN | 39.98% | 26.49% |

**Limitations.**
- Adaptation labels are recorded, not verified. RQ1 shows that
  quantization is often recorded as fine-tune.
- Quantized and merge strata are small in this snapshot.
