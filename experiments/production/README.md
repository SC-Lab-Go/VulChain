<!--
Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Explain the production analysis code that generated the RQ2-RQ5 values.
-->

# Production analysis code (RQ2–RQ5 and the evaluated cohort)

This folder holds the code that produced the manuscript's RQ2–RQ5 numbers on
the Security Server. It covers every step from the measurement ledger to the
macro files: verification, eligibility, matching, recurrence outcomes,
denominators, the bootstrap, and table generation. Each file keeps the same
relative path it has in the production repository, so its internal imports
and path references still read the same.

The entry points in `experiments/RQ2` … `experiments/RQ5` recompute the tables
from the exported comparison records (`data/rq_snapshot/`). They use
`experiments/vulchain_rq.py`, whose calculation sections are verbatim copies
of `unified_analysis.py` and `unified_exports.py` from this folder.
`tests/test_production_sources.py` checks that, definition by definition.

The RQ1 code from the Graph Server is in a subfolder, `graph_server_rq1/`.
It has its own manifest; see the
[section below](#rq1-graph-server-code-graph_server_rq1).

## Pipeline

```text
ledger (analysis.sqlite3; restricted: raw prompts and responses)
  │  2026_ICDE/package_probe_validation.py   PyPI/npm extraction and registry check
  │  2026_ICDE/url_probe_validation.py       URL extraction, URLhaus/PhishTank exact match,
  │                                          public-suffix registrable domain, DNS NXDOMAIN
  │  dual_site_probe_v2026_10_10/*_c1.py     versioned extraction corrections (c1) and the
  │                                          closed-brand TLD review; define the *_effective_c1 views
  ▼
RQ3_analysis/v2026.10.16-03/run_rq3.py       load(): both-c1 completion, cutoff, frozen inputs
                                             response_states(): verified artifacts per response
                                             outcomes(): class/instance positive, negative, unknown
  ▼
RQ2_analysis/v2026.10.27-01/unified_analysis.py
                                             build_capture(): read-only SQLite backup at a cutoff
                                             cohort_and_comparisons(): pair eligibility, same-prompt
                                               matching, one record per pair × category × prompt
                                             summarize(): shared-denominator rates
                                             clustered(): base-clustered percentile bootstrap
                                             aggregate_all(): policy, stratum and category cells,
                                               checked by an independent SQL recount
  ▼
RQ2_analysis/v2026.10.27-01/unified_exports.py
                                             build(): RQ2–RQ5 macros and tables; rq5_compute():
                                             Space/GitHub associations, shared artifacts
  ▼
canonical_comparisons.jsonl, qualified_occurrences.jsonl, …  (data/rq_snapshot/, artifacts as hashes)
  ▼
experiments/RQ2 … RQ5 entry points (public code; restricted input)
```

## Where each calculation is

| Calculation | File | Function or field |
|---|---|---|
| Package finding: registry `404`/absent, checked before cutoff, PyPI or npm | `run_rq3.py` | `response_states()` (package branch) |
| Registry lookup itself | `2026_ICDE/package_probe_validation.py` | `PackageVerifier.validate()`, `fetch_registry()` |
| NXDOMAIN finding: registrable domain, public suffix, DNS, closed-brand review | `run_rq3.py`; `url_probe_validation.py` | `response_states()` (URL branch); `Verifier.validate()`, `Verifier.dns()` |
| Exact malicious URL (URLhaus, PhishTank, 2026-10-08 feeds) | `url_probe_validation.py`; `run_rq3.py` | `Verifier.validate()`; `load()` re-checks feed matches |
| Exclusions: context, reserved names, special-use IPs, closed-brand TLDs | `run_rq3.py` | `host_exclusion()` |
| Completion: original verification plus both c1 markers before the cutoff | `run_rq3.py` | `load()` (`done`) |
| Class- and instance-level outcome | `run_rq3.py` | `outcomes()`; independent check `sql_verify()` |
| Pair eligibility and policy flags (Strict ⊂ Intermediate ⊂ Declared ⊂ Extended) | `unified_analysis.py` | `cohort_and_comparisons()` |
| Same-prompt matching (parent's verified-positive prompts, jointly completed) | `unified_analysis.py` | `cohort_and_comparisons()` |
| Denominator (both outcomes determinate) and rates | `unified_analysis.py` | `summarize()` |
| 95% base-clustered bootstrap (2,000 draws, seed 20261027) | `unified_analysis.py` | `clustered()` |
| Adaptation strata (AD, ndFT, dFT, QT, MG) | `unified_analysis.py` | `stratum()` |
| Restricted-namespace diagnostic | `RQ3_analysis/v2026.10.16-05/restricted_namespace.py` | `classify()`, `calculate()` |
| Table II unique-model counting | `table2_unique_models.py` | `summarize()` |
| RQ2–RQ5 macros and tables | `unified_exports.py` | `build()`, `rq4_table_vii_macros()`, `rq5_compute()`, `rq5_macros()` |
| Frozen definitions in prose | `RQ3_analysis/v2026.10.16-03/protocol.json` | `class_rule`, `instance_rule`, `denominators`, … |

## Files

`SOURCE_MANIFEST.json` lists every file with its role, the SHA-256 of the
original on the production server, and the SHA-256 of the published copy.

| Path | Status |
|---|---|
| `RQ2_analysis/v2026.10.27-01/unified_analysis.py` | redacted (3 path literals) |
| `RQ2_analysis/v2026.10.27-01/unified_exports.py` | redacted (3 path literals) |
| `RQ3_analysis/v2026.10.16-03/run_rq3.py` | redacted (1 hostname) |
| `RQ3_analysis/v2026.10.16-03/protocol.json`, `input_pin.json`, `FREEZE.json` | redacted (path literals) |
| `RQ3_analysis/v2026.10.16-03/inputs/agent.py` | redacted (hostname, account name) |
| `RQ3_analysis/v2026.10.16-03/inputs/paper.py`, `agent_protocol.json` | verbatim |
| `RQ3_analysis/v2026.10.16-05/restricted_namespace.py` | verbatim |
| `generate_graph_cohort_macros.py`, `table2_unique_models.py` | verbatim |
| `2026_ICDE/package_probe_validation.py`, `url_probe_validation.py` | verbatim |
| `2026_ICDE/dual_site_probe_v2026_10_10/common.py`, `package_extraction_c1.py`, `url_extraction_c1.py` | verbatim |
| `2026_ICDE/dual_site_probe_v2026_10_10/reclassify_packages_c1.py`, `reclassify_urls_c1.py`, `brand_tld_review_c1.py` | redacted (scratch path) |

Added for publication (new code, not production):

- `verify_sources.py` checks the manifest.
- `offline_verifiers.py` gates live registry and DNS queries.

### Publication redactions

Four kinds of machine-specific literal were replaced by placeholders:

- `<REDACTED_SECURITY_SERVER_HOST>`: a server hostname;
- `<REDACTED_HOME>`: an account home directory;
- `<REDACTED_TACC_SCRATCH>`: a scratch directory;
- `<REDACTED_USER>`: an account name.

Nothing else changed. No definition, constant, threshold, or control flow is
different. The authors keep the replaced values privately. With them,

```bash
python experiments/production/verify_sources.py --private-values <values.json> --originals <production repository root>
```

restores every file and checks it against the original SHA-256 and the
original bytes. This was run on 2026-10-30: 20/20 files matched. Without the
private values, the command checks the published hashes only.

Because of the redactions, the in-code integrity checks on the published copies will fail:

- `FREEZE.json` records hashes of the unredacted `run_rq3.py`, `protocol.json`, and `input_pin.json`;
- `unified_analysis.py` verifies those hashes before it runs.

That is intended. These modules run only next to the restricted ledger, on the production server.

## Running

These modules are published so the computation can be read and audited.
They do not run against public data:

- `unified_analysis.py` and `run_rq3.py` need the restricted ledger and frozen inputs.
- `run_rq3.py` also refuses to run on any host other than the Security Server.

The public reproduction path is the entry points in `experiments/`.

The verifiers can be exercised offline:

```python
import sqlite3, sys
sys.path.insert(0, "experiments/production")
import offline_verifiers

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE registry_evidence(ecosystem TEXT, name TEXT, evidence_json TEXT)")
verifier = offline_verifiers.package_verifier(db)          # cached evidence only
verifier = offline_verifiers.package_verifier(db, fetch=f)  # injected lookup, e.g. a recorded fixture
```

### External services

| Service | Used by | When |
|---|---|---|
| `pypi.org` JSON API, `registry.npmjs.org` | `PackageVerifier.fetch_registry()` | only for a name not in `registry_evidence` |
| DNS (A/AAAA) via the system resolver | `Verifier.dns()` | only for a host not in `dns_evidence` |
| URLhaus, PhishTank | `load_feeds()` | reads local dated feed files; no download |
| Public Suffix List | `Verifier.__init__()` | reads a local pinned `public_suffix_list.dat`; no download |

Importing any module here makes no network request (tested). Through
`offline_verifiers.py`, a live query needs either `allow_network=True` or
`VULCHAIN_ALLOW_NETWORK=1`. If neither is set, an uncached lookup raises
`NetworkDisabled`. Calling the frozen classes directly, without
`offline_verifiers.py`, uses their original behavior and queries uncached
names live.

Dependencies:

- The package verifier and `run_rq3.py` need only the standard library.
- `unified_analysis.py` needs `numpy`, and `unified_exports.py` needs `matplotlib` for its figures.
- The URL verifier needs `requirements-verifiers.txt`.

### Publication-safety review (2026-10-30)

All 20 modules were read in full and scanned before publication. The review
found:

- **Credentials:** none. No tokens, keys, passwords, or authorization headers.
  The package verifier sends only a `User-Agent`.
- **Restricted findings:** none. The code contains no model IDs, prompts,
  responses, verified package names, domains, or URLs. The only literals of
  that kind are reserved names (`example.com`, `localhost`, …) and the synthetic
  examples in the c1 docstrings.
- **Machine-specific information:** a hostname, two home and scratch paths,
  and an account name. They are replaced by the four placeholders above.
- **Network behavior:**
  - Importing a module makes no request. This is tested with sockets blocked.
  - The offline wrapper (`offline_verifiers.py`) needs explicit permission for
    any live query.
  - The underlying frozen verifiers are unchanged and can still query PyPI,
    npm, and DNS when called directly.
  - The offline tests use injected lookups and in-memory caches; they never
    contact an external service.
  - The results refresh (`scripts/refresh_results.py`) and the GitHub publisher
    import none of these modules, so routine refreshes never run live
    verification.

The verification definitions were not changed to make publication safe.

### Not included

These stay with the authors (see `LIVE_RESULTS_PIPELINE.md`):

- the ledger;
- prompts and responses;
- feed snapshots;
- the frozen input snapshot;
- model-level findings.

The GPU generation workers (`worker.py`, `strict_worker.py`) and scheduler
scripts are also not included. They produce responses and do not affect how
the recorded responses are scored.

## RQ1 Graph Server code (`graph_server_rq1/`)

<!-- Added 2026-10-30, v2026.10.30-04 -->

These files come from the Graph Server transfer package
`v2026.10.30-transfer-01`. That package has 189 files and passed
`SHA256SUMS` verification on arrival. Only files marked `PUBLIC` or
`PUBLIC-DATA` in its `metadata/TRANSFER_MANIFEST.csv` were imported, keeping
their package paths: 80 files in all. 48 are verbatim. 32 contain the Graph
Server's home directory, its hostname, or the account name; those literals are
replaced by placeholders, and nothing else is changed.

`graph_server_rq1/SOURCE_MANIFEST.json` records, for each file:

- its Graph Server source path;
- its role;
- its original and published SHA-256.

To check the files:

```bash
python experiments/production/verify_sources.py --root experiments/production/graph_server_rq1
python experiments/production/verify_sources.py --root experiments/production/graph_server_rq1 \
    --private-values <values.json> --originals <transfer package root>   # authors only; 80/80 on 2026-10-30
```

| Path | What it is | Used by |
|---|---|---|
| `figure_rq1/source/rq1_scaling_figure.py` | The original plotting script, v2026.10.15-01 | `rq1_figure_01.py`, which runs it unchanged |
| `figure_rq1/benchmark/scripts/` | The original benchmark: input sampler, builder, driver, summarizers | `rq1_figure_01.py` (`elapsed`, `metric`, `stat`, `parse_total`; builder with `--rebuild-dot`) |
| `figure_rq1/benchmark/reference_builder/` | The release builder that the benchmark imports for schema, checks and serialization | `--rebuild-dot` |
| `figure_rq1/benchmark/results-local-20261015-scaling-03/` | The complete measurement record of the published run: per-run `/usr/bin/time -v`, stdout and stderr, plus input manifest and summaries. Host load snapshots and the hardware listing are excluded. | `rq1_figure_01.py` |
| `figure_rq1/output/rq1_scaling_figure_cropped.{pdf,png}` | The archived figure. The PDF is byte-identical to the manuscript's | reference |
| `figure_rq1/audit/` | Evidence that the benchmark assembled `HuggingGraph_v3.dot` (348d92cd…), not `VulChain.dot` | documentation |
| `hub_agreement/historical_first200k/acquisition/` | Hub model-tree crawler (`graph_model_model_master.py`, which reads the Hub token at run time only) and the delta-inventory builder | documentation |
| `hub_agreement/historical_first200k/reference/` | The 15,689 reference pairs, the 200,000 completed sources, and the empty error file. Public Hub metadata. | `rq1_table_02.py` |
| `hub_agreement/historical_first200k/evaluator/` | `eval_hf_tree_recall.py` (exact-ID matching, label confusion) and `sampling_summary.json` (source of 111,816) | `rq1_table_02.py`, which runs it unchanged |
| `hub_agreement/historical_first200k/published_output/` | The archived evaluator output | compared byte for byte or value for value |
| `hub_agreement/historical_first200k/selection_audit/` | `audit_selection.py` (Wilson, cluster-robust and bootstrap intervals; selection trace), its tests, outputs and reports | `rq1_table_02.py`, which executes its per-adaptation statements |
| `hub_agreement/historical_first200k/missing_pairs/` | The 1,021 unrecovered pairs with root causes (C6 = 812 rename/transfer aliases), plus the diagnostic code | reference |
| `hub_agreement/historical_first200k/table/icde_table_iv_revised.tex` | Revised table template. VERSION 2 has a Fine-tune upper bound of 94.9 that should be 94.8. | reference |

**Not imported.** These stay in the transfer package or on the Graph Server:

- **`RESTRICTED-RAW`:** the 2026-08-28 and CIKM model inventories, the delta
  inventory, and the 1.3 GB model-card metadata.
- **`RESTRICTED-INTERNAL`:** host load snapshots (they list other users'
  processes), the hardware listing, the crawl log, and the transfer harness's
  run log and results.
- **The 17 released edge CSVs:** identical to the graph release, and read
  through `--release-dir`.
- **`model_lineage_edges_merged.csv`:** 100 MB. It is an optional evaluator
  input that adds only an informational breakdown.
- **Benchmark run DOTs:** 5.3 GB and regenerable.
- **The 2027 probability-sample experiment:** still running, and not a source
  of any table value.

Several scripts hard-code Graph Server paths, which now read as `<REDACTED_HOME>/…`:

- `audit_selection.py`;
- `diagnose_missing_pairs.py`;
- `run_scaling_local.sh`.

The entry points never rely on those paths. `rq1_table_02.py` sets the audit's
`INPUTS` to the public files before it executes the audit statements.

**Safety review (2026-10-30).**

- **Credentials:** none. The crawler obtains the Hub token at run time with
  `huggingface_hub.get_token()`.
- **Security findings:** none.
- **Machine-specific literals:** none remain after redaction (tested).
- **Token-shaped strings:** 8 lines of `graph_model_model_first_200k.csv.completed.txt`
  are public Hub repository names shaped like access tokens (`owner/hf_…`).
  They are third-party IDs that are already in the released graph. Whether to
  keep redistributing them is a release-policy decision.
