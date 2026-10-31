# Graph construction

`vulchain_graph.py` contains the complete October 2, 2026 construction
pipeline for all 17 relationship families in one file. Each stage is one of
the 18 original pipeline scripts, embedded verbatim, and runs exactly as the
standalone script would. The file records each script's SHA-256 and checks it
before any stage runs.

```bash
python graph_construction/vulchain_graph.py list      # stages and the relationships they produce
python graph_construction/vulchain_graph.py verify    # embedded-source checksums
python graph_construction/vulchain_graph.py extract --to original_scripts   # write the 18 scripts out
python graph_construction/vulchain_graph.py <stage> --help
```

## Where the 17 relationship definitions are

| What | Where |
|---|---|
| Extraction code for each family | the embedded stage listed below; `vulchain_graph.py list` maps stages to families |
| One-row definition per family: metadata source, normalization, evidence requirement, deduplication, DOT form, validation, released edge file, counts | [`../relationships/relationship_catalog.csv`](../relationships/relationship_catalog.csv) |
| Five sample rows per family | [`../relationships/examples/`](../relationships/examples/) |

The canonical graph is `graph/VulChain.dot` (SHA-256 `25d669bd…`, analytical
view). The unfiltered `HuggingGraph_v3.dot` (SHA-256 `348d92cd…`) is kept
unchanged outside this repository.

This folder covers graph construction only. The RQ2–RQ5 security analysis is
in [`../experiments/production/`](../experiments/production/README.md).

## Workflow and execution order

| Step | Stage | Relationship(s) | Reads | Writes |
|---:|---|---|---|---|
| 0 | acquisition (separate, see below) | — | Hugging Face API | metadata snapshots, README crawls |
| 1 | `model-lineage` (uses `model-types`) | 1 | model metadata (`models_with_metadata.jsonl`, `models_without_metadata.jsonl`), model-ID universe | declared and inferred lineage edges |
| 2 | `dataset-model` | 2 | model metadata, Dataset inventory | `trained_on` edges, validated variant |
| 3 | `dataset-dataset-baseline`, then `dataset-dataset` | 3 | Dataset metadata, full Dataset READMEs | candidate-union edges and evidence |
| 4 | `model-library`, `model-license-task-github` | 4, 6, 8 | model metadata | attribute edges |
| 5 | `model-readme-attributes` (uses `model-dataset-attributes`) | 4, 6, 8 | full model READMEs (YAML front matter) | merged attribute edges |
| 6 | `dataset-attributes` | 5, 7, 9 | full Dataset READMEs (2026-09-28) | attribute edges |
| 7 | `model-github`, `dataset-github`, `space-github` | 10, 11, 14 | full README crawls | GitHub edges (SQLite state) |
| 8 | `space-edges` | 12, 13 | Space API metadata and cards (2026-09-24) | `used_by_space` edges |
| 9 | `space-attributes` | 15, 16, 17 | Space cards | license, task, agent edges |
| 10 | `audit-datasets` | 3, 5, 7, 9, 11 | Dataset outputs | coverage and consistency audit |
| 11 | `prepare` | 1–17 | stage outputs | 17 numbered, type-prefixed, count-checked edge files |
| 12 | `assemble` | 1–17 | the 17 edge files | `HuggingGraph_v3.dot` (unfiltered release) |
| 13 | `build_analytical_view.py` | 1–17 | the release edge files + validated Dataset→Model file | `VulChain.dot` |

`prepare` re-queries the Hugging Face API for Spaces missing from the
relationship snapshot. It requires network access and `huggingface_hub`. It
checks that exactly the three recorded Spaces are unavailable.

Several stages use script-relative default paths, because the original
scripts lived beside their data. `--workdir DIR` makes `DIR` stand in for that
directory.

## Verified: both graphs rebuild byte for byte

`VulChain.dot` (the graph in the manuscript):

```bash
python graph_construction/build_analytical_view.py \
    --release-dir <release> --output VulChain.dot
sha256sum VulChain.dot   # 25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97
```

`build_analytical_view.py` type-prefixes the validated Dataset→Model file with
the production `copy_core()`. It then runs the production `build()`, with the
expected totals set to 7,666,919 edges and 3,117,399 nodes. On 2026-10-30, two
builds were byte-identical and matched the hash prefix recorded by the Graph
Server audit.

The unfiltered HuggingGraph v3 release (not distributed here):

```bash
python graph_construction/vulchain_graph.py assemble \
    --edge-dir <release>/edges/csv --output HuggingGraph_v3.dot
sha256sum HuggingGraph_v3.dot   # 348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b
```

This was also verified byte-identical on 2026-10-30. `assemble` validates each
family's edge count, each entity type's node count, and the totals. It refuses
to overwrite an existing output.

The other stages were not re-executed for this package: their inputs are the
raw Hugging Face metadata and README crawls (tens of GB). They are the archived
production code, unchanged.

## Acquisition

The download scripts (models, datasets, Spaces, metadata, and README crawls)
are not embedded. They are in the graph's reproducibility archive under
`source/acquisition/`, and in `source/acquisition/` of the public HuggingGraph
repository. Their outputs depend on the Hub at crawl time, so re-running them
gives a different snapshot, not the October 2 graph.

## Resources

Offline stages are single-process and CPU-bound. On a dual AMD EPYC 9334 host
(network acquisition excluded):

| Stage | Wall time |
|---|---:|
| Model lineage | 40.83 s |
| Dataset→Model | 25.43 s |
| Dataset→Dataset | 199.33 s |
| DOT assembly (unfiltered release) | 51.87 s, 0.447 GiB peak RSS |

These are recorded single runs, not the assembly-scaling benchmark of
`fig:rq1`. Do not mix the two sets of numbers.
