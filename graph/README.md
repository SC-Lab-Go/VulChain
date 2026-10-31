# VulChain graph

`VulChain.dot` is the VulChain graph reported in the manuscript
(Table `tab:master_table`).

| Property | Value |
|---|---|
| File | `VulChain.dot` (Graphviz DOT, UTF-8) |
| Size | 1,006,495,786 bytes (959.9 MiB) |
| SHA-256 | `25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97` |
| Nodes / edges | 3,117,399 / 7,666,919 |
| Entity types / relationship families | 8 / 17 |

| Entity type | Nodes |
|---|---:|
| Model | 1,885,384 |
| Space | 712,728 |
| Dataset | 414,723 |
| GitHub repository | 96,678 |
| License | 4,888 |
| Library | 2,148 |
| Task | 839 |
| Agent framework | 11 |

## How it relates to HuggingGraph v3

`VulChain.dot` is derived from the October 2, 2026 HuggingGraph v3 release
(release `v2026.10.02-07`). Sixteen relationship families are identical to
the release. Relationship 2 (Dataset→Model) keeps only the 253,111 training-data
declarations that resolve to exactly one Dataset in the crawled inventory,
instead of all 362,064 declared references.

| | HuggingGraph v3 release | `VulChain.dot` |
|---|---:|---:|
| Edges | 7,775,872 | 7,666,919 |
| Nodes | 3,137,207 | 3,117,399 |
| Dataset→Model edges | 362,064 | 253,111 |
| Model nodes | 1,888,591 | 1,885,384 |
| Dataset nodes | 431,324 | 414,723 |

The unfiltered release (`HuggingGraph_v3.dot`, SHA-256 `348d92cd…`) is not
distributed here. It is preserved unchanged, with its benchmark records, for
historical reproducibility.

### Which results depend on the difference

| Result | Families used | Affected? |
|---|---|---|
| `tab:master_table` | all 17 | Reports `VulChain.dot` (PASS 44/44) |
| `tab:hub_agreement` | 1 (Model→Model) | No: family 1 is identical |
| `fig:rq1` (assembly scaling) | all 17 | Measured on `HuggingGraph_v3.dot` (7,775,872 edges), not on `VulChain.dot` |
| RQ2–RQ4 | 1 (lineage) | No: family 1 is identical |
| RQ5 | 1, 10, 12, 14 | No: these families are identical |

No experimental result was recomputed or changed when `VulChain.dot` became
the publication graph.

The DOT header reads `digraph HuggingGraph {`, because it is written by the
production assembler. Renaming it would change the checksum.

## Download and verify

The file is larger than GitHub's 100 MiB per-file limit, so it is distributed
as an asset of this repository's GitHub Release
[`v2026.10.30`](https://github.com/SC-Lab-Go/VulChain/releases/tag/v2026.10.30).
Download it into this directory, then run:

```bash
curl -L -o graph/VulChain.dot https://github.com/SC-Lab-Go/VulChain/releases/download/v2026.10.30/VulChain.dot
(cd graph && sha256sum -c VulChain.dot.sha256)   # 25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97
python reproducibility/verify_graph.py graph/VulChain.dot
```

`verify_graph.py` checks the checksum, the node and edge totals, each entity
type, and each of the 17 relationship families.

## Rebuild it

The inputs are in the graph's reproducibility archive (release
`v2026.10.02-07`, two `.tar.zst` parts plus `RELEASE_ASSETS.sha256`):

```bash
(cd <download dir> && sha256sum -c RELEASE_ASSETS.sha256)
cat <download dir>/hugginggraph_v3_2026oct02_reproducibility.tar.zst.part-* | zstd -dc | tar -xf -
python graph_construction/build_analytical_view.py \
    --release-dir hugginggraph_v3_2026oct02_reproducibility --output VulChain.dot
sha256sum VulChain.dot   # 25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97
```

The builder runs the production assembly code (`build_hugginggraph_v3.build`)
and the production type-prefixing code (`prepare_hugginggraph_v3_edges.copy_core`).
Both are embedded in `vulchain_graph.py`; only the expected totals differ.

Two builds on 2026-10-30 were byte-identical. Their SHA-256 also matches the
prefix `25d669bd` that the Graph Server's 2026-10-28 audit recorded for this
analytical graph, which it built separately.

The RQ1 and RQ5 entry points read the per-family edge files from the same
extracted archive.

## Format

Each edge is one line:

```dot
"model::Qwen/Qwen3.8-27B" -> "model::unsloth/Qwen3.8-27B-GGUF" [label="finetune", edge_type="finetune"];
```

- Node IDs carry a type prefix: `model::`, `dataset::`, `space::`,
  `library::`, `license::`, `task::`, `agent::`. GitHub repositories are
  normalized URLs: `https://github.com/owner/repo`.
- `edge_type` is the canonical relationship. `label` repeats it, except for
  merges (`label="merge"`, `edge_type="merged"`).
- Lineage edges point from the upstream artifact to the downstream artifact.
  Attribute edges point from the artifact to the attribute.
- The file contains edges only. Every node is an endpoint of at least one edge.

## Loading

NetworkX and pydot need a lot of memory for the full graph. Stream the file
instead:

```bash
python relationships/examples/show_relationship.py graph/VulChain.dot --family 12 --limit 5
```
