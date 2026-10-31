# Files needed from other servers

## Status (2026-10-30)

| Artifact | Status |
|---|---|
| `fig:rq1` | **Transferred and integrated.** PASS (71/71; 72/72 with `--rebuild-dot`) |
| `tab:hub_agreement` (Hub-reference columns) | **Transferred and integrated.** PASS (34/34) |
| `tab:rq3nlc` | **PENDING.** Source not located |

## Graph Server: received

The Graph Server transfer package `v2026.10.30-transfer-01` arrived on
2026-10-30 and passed `sha256sum -c SHA256SUMS` for all 189 files. Its
publication-safe files are in `experiments/production/graph_server_rq1/`; see
[the production README](../experiments/production/README.md#rq1-graph-server-code-graph_server_rq1).

The items requested from the Graph Server audit of 2026-10-28 arrived as follows:

| Needed for | File | Recorded prefix | Arrived |
|---|---|---|---|
| `fig:rq1` | `build_hugginggraph_scaling.py` | — | yes |
| `fig:rq1` | `scaling_performance.csv` | `cb2f1e6f` | yes, prefix matches |
| `fig:rq1` | `scaling_summary.json` | `a4ed517e` | yes, prefix matches |
| `fig:rq1` | plotting script (`rq1_scaling_figure.py`) | — | yes; its archived output is byte-identical to the manuscript's figure |
| `tab:hub_agreement` | `graph_model_model_first_200k.csv` | `fa045591` | yes, prefix matches |
| `tab:hub_agreement` | `graph_model_model_first_200k.csv.completed.txt` | `de0df81d` | yes, prefix matches |
| `tab:hub_agreement` | `graph_model_model_master.py` | — | yes |
| `tab:hub_agreement` | agreement code | — | yes: `eval_hf_tree_recall.py` and `audit_selection.py` |
| `tab:hub_agreement` | `model_tree_agreement.md`, `declared_provenance.csv`, `model_lineage_edges_instrumented.py` | `b424ef94` | not transferred, and not needed: the active table prints no default-fine-tune breakdown, and its columns come from the evaluator and audit code above |

The raw Hub crawls, host logs, and the in-progress probability-sample
experiment were deliberately not imported. They stay in the transfer package.

## Still missing: `tab:rq3nlc` (Security Server, LAB, or another host)

| Item | Detail |
|---|---|
| Control-model comparison records | Or the ledger they come from, with its cutoff and checksum |
| Code | Computes the matching, denominators, lineage and non-lineage rates, Δ, and the 95% base-clustered bootstrap intervals |
| Explanation of the test counts | Why they (package 10,420; NXDOMAIN 7,156) differ from `tab:rq3` (13,934; 9,661) |

The graph-side control assignment is already on the Security Server
(`control_assignment.csv`, seed 20261016).

The authors hold a read-only locator script that lists candidate files on a
given host. Nothing is copied until the authors confirm which files are the
generator and its inputs.

## Integration after arrival

Transferred code goes through the same procedure as the RQ1 files:

1. Verify the package checksums.
2. Import only publication-safe files, applying literal-only redactions.
3. Record the original and published SHA-256 in a `SOURCE_MANIFEST.json`, and
   check them with `verify_sources.py --root`.
4. Write `RQ3/rq3_table_02.py` to run the transferred computation.
5. Compare every printed value with the manuscript.

No PENDING artifact gets a placeholder script or hard-coded values.

Do not use any of these as substitutes:

- pilot results, such as the 692-model Hub pilot;
- the unfinished probability-sample evaluation;
- historical control code;
- simulated files.
