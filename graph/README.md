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
