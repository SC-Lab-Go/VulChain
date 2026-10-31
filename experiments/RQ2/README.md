# RQ2: Impact of provenance evidence on security analysis

**Objective.** Measure how the evidence-admission policy changes which
base–derivative comparisons are analyzed, and how that changes the observed
recurrence. Prompts, responses, and verification evidence are held fixed.

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: evidence admission and recurrence | `tab:rqtworecurrence` | `rq2_table_01.py` | PASS (56/56) |

| Code | Inputs | Calc. reproduced | Values verified | Public | Restricted |
|---|---|---|---|---|---|
| yes | yes (restricted; hash-checked) | yes, from comparison records | 56/56 (and 661/661 production macros) | no | yes (`data/rq_snapshot/`) |

**How it is computed.**

- `rq2_table_01.py` applies the four cumulative policy flags and the newly
  admitted strata. It checks that the policies are nested.
- `summarize()` computes each cell with a shared denominator: a comparison is
  eligible when both its class and instance outcomes are determinate.
- `summarize()` is copied verbatim from
  `production/RQ2_analysis/v2026.10.27-01/unified_analysis.py`.
- The comparison records come from the same module's `cohort_and_comparisons()`.
- The outcome per record comes from `production/RQ3_analysis/v2026.10.16-03/run_rq3.py`
  (`outcomes()`).

See [../production/README.md](../production/README.md).

**Setup.** The four nested policies (Strict ⊂ Intermediate ⊂ Declared ⊂
Extended) are applied to the evaluated cohort. For each policy and category
(package hallucination, NXDOMAIN) the table reports:

- **Base:** distinct upstream models with an eligible comparison;
- **Tests:** eligible comparisons;
- **Class(%):** class-level recurrence rate;
- **Inst.(%):** instance-level recurrence rate.

"Newly added" rows contain only the comparisons a policy admits beyond the
previous one.

```bash
python experiments/RQ2/rq2_table_01.py
```

**Input.** `data/rq_snapshot/canonical_comparisons.jsonl`: 24,150
comparison records with per-policy admission flags.

**Expected results.** Package hallucination:

| Policy | Tests | Class-level recurrence |
|---|---:|---:|
| Strict | 5,437 | 38.55% |
| Declared | 13,934 | 31.91% |

The full table is in `outputs/RQ2/rq2_table_01_macros.tex` after running.

**Limitations.**
- Differences between policies reflect which comparisons are admitted. They
  are not a causal effect.
- Strict rests on few base models.
- Values come from the 2026-10-30 snapshot of an ongoing evaluation.
