# Tests

```bash
python -m unittest discover -s tests -v
```

| Test | What it checks |
|---|---|
| `GraphConstruction` | All 18 embedded pipeline scripts match their recorded SHA-256, and the stages start. The `prepare` stage is skipped when `huggingface_hub` is not installed. |
| `Catalog` | The 17 families are numbered 1–17, their edges sum to 7,666,919 (the edges of `VulChain.dot`), and every family has a sample file. |
| `CalculationRules` | Shared-denominator recurrence (unknown outcomes excluded), percentage display, and distinct-ID counting. |
| `Snapshot` | Snapshot inputs match `INPUT_MANIFEST.json`, and the comparison records carry hashes, not raw artifacts. |

Full numerical regression against the manuscript is done by
`reproducibility/verify_results.py`.

## Production-source tests (`test_production_sources.py`)

These run offline on synthetic evidence. They use no ledger, prompt,
response, or finding, and they make no registry or DNS query.

| Test | What it checks |
|---|---|
| `Manifest` | All 20 modules in `experiments/production/` match `SOURCE_MANIFEST.json`. Only the documented placeholders appear, and no machine paths. Every definition in the "Copied verbatim" sections of `experiments/vulchain_rq.py` appears verbatim in the production files. |
| `NoNetworkOnImport` | Importing the verifiers, the c1 extraction, `offline_verifiers`, and `run_rq3` opens no socket. |
| `OutcomeRules` | `run_rq3.outcomes()` returns the documented class and instance outcome for each case: identical artifact, different artifact, unresolved candidate, and no candidate. |
| `VerifiedFindingRules` | `run_rq3.response_states()` handles each case as documented: a registry 404 before or after the cutoff, NXDOMAIN with and without review, and the private-suffix exclusion. |
| `PackageVerifier` | An uncached lookup is refused without explicit permission. An injected lookup is cached. A warning context is excluded before any lookup. |
| `C1Extraction` | The c1 correction drops words from shell comments that the frozen extractor kept. |
| `URLVerifier` | The c1 Markdown-link split. Skipped unless `requirements-verifiers.txt` is installed. |

The original-source check, `verify_sources.py --private-values`, restores
the redacted files and compares them with their original SHA-256. It needs the
authors' private redaction values. It is therefore not part of this
suite.

## RQ1 Graph Server tests (`test_rq1_graph_server.py`)

| Test | What it checks |
|---|---|
| `Sources.test_manifest_hashes` | All 80 files in `experiments/production/graph_server_rq1/` match their `SOURCE_MANIFEST.json`. |
| `Sources.test_no_machine_literals_restricted_files_or_in_progress_experiment` | Only `PUBLIC` and `PUBLIC-DATA` files are imported. There are no host load snapshots, hardware listing or crawl log, no Graph Server paths or hostname, and no file from the in-progress probability-sample experiment. |
| `Reproduction.test_fig_rq1_values_from_raw_measurements` | `rq1_figure_01.py` recomputes every plotted value from the raw run records and verifies it. |
| `Reproduction.test_hub_agreement_from_original_evaluator_and_audit` | `rq1_table_02.py` reproduces all 34 cells with the original evaluator and audit statements. It is skipped unless the graph release is configured, through `VULCHAIN_RELEASE_DIR` or `configs/pipeline.local.json`. |

## Publication deadline tests (`test_publish_guard.py`)

These use an injected clock and throwaway local Git repositories. They make no
network calls, touch no GitHub repository, and never change the system clock.

| Requirement | Test |
|---|---|
| 1. Before the cutoff, publishing is allowed | `test_1_before_cutoff_allowed`, `test_publishes_before_cutoff` |
| 2. Exactly at the cutoff, it is blocked | `test_2_exactly_at_cutoff_blocked` |
| 3. After the cutoff, it is blocked | `test_3_after_cutoff_blocked_and_status_text` |
| 4–5. Sync and refresh still work after the cutoff | `test_4_and_5_refresh_and_sync_wrapper_succeed_after_cutoff` |
| 6. An unfinished publication is not completed | `test_6_unfinished_publication_not_completed_after_cutoff`, `test_short_window_does_not_start` |
| 7. Scheduled runs cannot bypass the deadline | `test_7_schedules_cannot_bypass`, `test_clock_rollback_before_freeze_is_ignored` |
| 8 and 10. No retries; the last published version is kept | `test_8_and_10_no_retry_after_cutoff_and_last_version_kept` |
| 9. Research code does not depend on publishing | `test_9_research_code_never_imports_the_publisher` |
| The cutoff is in UTC on any host | `test_cutoff_is_utc_regardless_of_host_timezone` |
