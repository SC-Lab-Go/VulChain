# RQ3: Failure persistence across derivatives

**Objective.** Measure how often an externally verified failure of a base
model recurs in its one-hop derivatives under the same prompt.

| Artifact | Label | Entry point | Status |
|---|---|---|---|
| Table: same-prompt recurrence under Declared | `tab:rq3` | `rq3_table_01.py` | PASS (24/24) |
| Table: lineage vs. matched non-lineage models | `tab:rq3nlc` | none | PENDING |

| Label | Code | Inputs | Calc. reproduced | Values verified | Public | Restricted |
|---|---|---|---|---|---|---|
| `tab:rq3` | yes | yes (restricted; hash-checked) | yes, from comparison records | 24/24 | no | yes |
| `tab:rq3nlc` | no | no | no | no | no | yes (expected) |

**How `tab:rq3` is computed.** Each comparison's class and instance outcome
comes from `run_rq3.py`:

- **class positive:** the derivative has any verified artifact of the category;
- **instance positive:** the derivative's verified artifacts share an
  identity with the base's;
- **unknown:** an unresolved candidate could change the outcome;
- **excluded:** unknown outcomes leave the shared denominator.

The rates come from `summarize()`, a verbatim production rule.

Occurrence and distinct-artifact counts come from `occurrence_counts()`. That
function is adapter code in `vulchain_rq.py`. It counts rows and distinct
artifact hashes in `qualified_occurrences.jsonl`, which the production
`collect_occurrences()` wrote.

See [../production/README.md](../production/README.md).

## `tab:rq3`

For each category the table reports:

- occurrence rows and distinct canonical artifacts over verified responses;
- eligible tests;
- class-level and instance-level recurrence (count and rate);
- reproduction: instance recurrences as a share of class recurrences,
  computed in LaTeX.

```bash
python experiments/RQ3/rq3_table_01.py
```

**Inputs.** `canonical_comparisons.jsonl` and `qualified_occurrences.jsonl`.
Occurrence artifacts are SHA-256 hashes, not raw strings.

**Expected results.**

| Category | Tests | Class-level | Instance-level |
|---|---:|---:|---:|
| Package hallucination | 13,934 | 31.91% | 23.75% |
| NXDOMAIN | 9,661 | 39.98% | 26.49% |

Restricted namespace is reported as a diagnostic only.

## `tab:rq3nlc`: PENDING

The table compares lineage recurrence with matched non-lineage models, using
95% base-clustered bootstrap intervals. Its values are typed directly into
`experiments.tex`; no macro file or generating script was found on this
server. The graph-side control matching exists (`control_assignment.csv`,
`control_candidates.csv`, seed 20261016). The control-model responses and the
comparison code were not found.

The test counts also disagree with `tab:rq3`:

| Category | `tab:rq3nlc` | `tab:rq3` |
|---|---|---|
| Package | 10,420 tests, 31.97% | 13,934 tests, 31.91% |
| NXDOMAIN | 7,156 tests, 38.74% | 9,661 tests, 39.98% |

The control table may use a matched subset or an earlier snapshot. This must
be resolved before the table is published as reproducible. See
`reproducibility/TRANSFER_CHECKLIST.md`.

No reproduction script exists, and none will be written from the manuscript
values. `rq3_table_02.py` will be added only after the authoritative matched-control
implementation and its comparison records are transferred. It must reproduce
all of the following:

- the actual control matching;
- the comparison denominators (10,420 and 7,156 tests);
- the lineage and non-lineage rates and Δ;
- the 95% base-clustered bootstrap intervals.

Do not use any of the following as substitutes:

- the historical `RQ3_analysis/v2026.10.16-01` control code;
- its 174 proposed `matched_controls.csv`;
- the simulated `synthetic_malicious_refresh` files.

## Limitations

- Rates are comparison-weighted and descriptive.
- Recurrence is not evidence of causal inheritance.
- Values come from the 2026-10-30 snapshot.
