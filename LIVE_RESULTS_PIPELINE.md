# Live results pipeline

The RQ2–RQ5 evaluation keeps running until submission. This pipeline turns
each new validated analysis snapshot into a reproducible, checksummed, and
validated set of results. It never touches the live measurement database.

## Where the data comes from

```text
live ledger (LAB / HPC / TACC experiments; never read here)
   │  production analysis pipeline: SQLite backup API at a fixed cutoff,
   │  own validation, immutable snapshot, atomic LATEST.json pointer
   ▼
RQ2_analysis/<version>/snapshots/<snapshot_id>/  +  LATEST.json
   │  scripts/refresh_results.py
   ▼
results/.staging-<id>-<pid>/  ── checks fail ──▶ results/failed/<id>-<time>/
   │  all checks pass
   ▼
results/versions/<snapshot_id>/   (read-only)   ◀── results/latest (atomic symlink)
   │  scripts/freeze_submission.py
   ▼
freezes/<label>/                  (read-only)
```

## Commands

Copy `configs/pipeline.example.json` to `configs/pipeline.local.json` and set
these paths:

- the production snapshot root;
- the RQ5 graph export;
- the extracted graph release;
- the graph file.

| Task | Command |
|---|---|
| Refresh results | `python scripts/refresh_results.py` |
| Check without publishing | `python scripts/refresh_results.py --dry-run` |
| Re-validate the latest version | `python scripts/validate_results.py` |
| Re-validate a given version | `python scripts/validate_results.py --version <snapshot_id>` |
| Reproduce one artifact | `python experiments/RQ3/rq3_table_01.py` (see `REPRODUCIBILITY_MATRIX.csv`) |
| Reproduce all artifacts vs. the manuscript | `python reproducibility/verify_results.py --release-dir <release>` |
| Freeze the submission | `python scripts/freeze_submission.py --label submission-2026-11-06` |
| Refresh, then publish through the guard | `bash scripts/vulchain_refresh_and_publish.sh` |
| Run the tests | `python -m unittest discover -s tests -v` |

## What a refresh does

1. **Discover.** Read `LATEST.json`, which the production pipeline writes only
   after its own validation. Accept the snapshot only if:
   - every file matches its `OUTPUT_MANIFEST.json`;
   - `rq4_publication_validation.json` and `rq5_publication_validation.json` say PASS;
   - every check recorded in `rq2_validation.json` is PASS.
2. **Stage.** Copy the five comparison-level inputs, the production macros, and
   the RQ5 graph export into a private staging directory. Each copy is
   hash-checked against its source manifest, and the pass writes
   `INPUT_MANIFEST.json`. If `LATEST.json` moves during staging, the refresh
   aborts.
3. **Recompute.** Run the same entry-point code used for the manuscript
   (`experiments/`) on the staged copies.
4. **Validate.** The refresh publishes only if all of these hold:
   - every recomputed value equals the snapshot's own production macro (an
     independent re-computation);
   - policy nesting holds;
   - there are no duplicate comparisons;
   - RQ4 strata partition the RQ3 tests;
   - RQ2 Declared equals RQ3;
   - the newly admitted strata partition Extended;
   - instance ≤ class ≤ tests in every cell;
   - EvalPairs and EvalUniqueModels equal the evaluated relationship and model counts;
   - every evaluated model is in the planned cohort;
   - every comparison belongs to an evaluated relationship.
5. **Record.** `RESULTS_MANIFEST.json` stores:
   - model and relationship counts;
   - comparisons and Declared tests;
   - cutoff and refresh timestamps;
   - input, output, and code hashes;
   - every check result.

   `CHANGES.md` lists what changed since the previous validated version, and
   every macro that differs from the manuscript.
6. **Publish atomically.** The staging directory is renamed to
   `results/versions/<id>/` and made read-only. Then `results/latest` is
   repointed with a single `os.replace`. A reader therefore always sees either
   the old version or the complete new one.

Definitions are never changed: experimental definitions, matching,
detectors, eligibility, and estimators all come from the production code. The
pipeline reports the cohort that has actually been evaluated (as of
2026-10-30: 45 bases and 482 models of the planned 176 bases and 6,963 models).
It never reports the planned cohort as evaluated.

## Interrupted or failed refreshes

- **A refresh fails a check.** The run is moved to `results/failed/` and
  `results/latest` keeps the previous validated version.
- **A refresh is interrupted** (crash, kill, or reboot). The half-written
  `results/.staging-*` directory is never linked from `latest`. The next run
  moves it to `results/failed/…-interrupted`; it is never deleted.
- **Two refreshes overlap.** A lock file (`results/.refresh.lock`) stops the
  second one. A lock left by a dead process is cleared automatically.
- **Resuming.** Run `python scripts/refresh_results.py` again. If the latest
  snapshot was already published, the run is a no-op.

## Public and restricted reproducibility

| Reproducible from public data | Requires restricted research data |
|---|---|
| Graph verification and assembly; `tab:master_table`; `tab:hub_agreement`; `fig:rq1`; all tests | The Sel. cohort row of `tab:model_corpus`, and `tab:rqtworecurrence`, `tab:rq3`, `tab:rq4-adaptation-split`, `tab:rq5` (comparison-level records name models next to verified findings) |

- `results/`, `freezes/`, and `configs/*.local.json` are gitignored.
- Aggregate macro files (`outputs/*_macros.tex`) contain only counts and rates.
  They can be shared after disclosure review.
- To reproduce with the full data privately: obtain `data/rq_snapshot/` under
  controlled access, check it against `data/rq_snapshot/INPUT_MANIFEST.json`,
  then run the commands above.

## GitHub publication deadline

Automatic GitHub publication stops permanently at
**2026-11-11T22:00:00Z** (November 11, 2026, 4:00 PM America/Chicago).
Research does not stop.

**The guard.** `scripts/github_publish_guard.py` is the only deadline check.
- The cutoff is a constant in its code. `GITHUB_PUBLISH_CUTOFF_UTC` (in
  `configs/github_publish.json` or the environment) can move it earlier, never
  later.
- All comparisons are in UTC.
- The guard remembers the latest time it has seen, so a clock moved backwards
  cannot reopen publishing.
- At the cutoff it writes a permanent `FROZEN` marker in
  `~/.local/state/vulchain_publish/`.
- Its command-line interface has no clock override.

**The publisher.** `scripts/publish_github.py` is the only GitHub-writing path.
- It checks the guard at start and again immediately before `git add`,
  `commit`, `tag`, and `push`.
- It starts only if at least 15 minutes remain.
- The push runs with a timeout that ends before the cutoff.
- It publishes only a validated `results/latest`.
- It never adds AI co-author trailers.
- It tags only when `tag_approved` is true.
- It has no retry loop.

**After the cutoff.** The publisher prints
`GITHUB PUBLISHING FROZEN — DEADLINE REACHED`, writes the pending local
changes to `PENDING_UNPUBLISHED.json`, and exits 0.
`scripts/vulchain_refresh_and_publish.sh` always runs the local refresh first.
Its exit status reflects the refresh only, so `daily_sync.sh` or any scheduler
calling it keeps working.

**Record of the last publication.** `PUBLICATION_STATE.json` records:
- repository URL;
- final commit;
- last push time;
- graph SHA-256;
- artifact statuses;
- latest validated snapshot.

**Status: publication is not enabled.** `configs/github_publish.json` has
`"enabled": false` and `configs/github_approved_files.txt` is empty. These
are still missing:
- an approved target repository and local clone;
- a configured Git identity;
- an approved file list.

No scheduler is installed.
