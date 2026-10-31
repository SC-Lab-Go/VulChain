# Relationship families

VulChain has 17 relationship families over 8 entity types.
[`relationship_catalog.csv`](relationship_catalog.csv) has one row per family
with these fields:

- relationship name and `edge_type`;
- source and target entity types, and direction;
- metadata source;
- extraction and normalization logic;
- evidence requirement;
- deduplication rule;
- DOT representation;
- validation checks;
- the `vulchain_graph.py` stage that produces it;
- the released edge file;
- observed edge and node counts.

The catalog was written from the pipeline scripts' own documentation and the
build constants. Its edge counts are checked against the graph by
`reproducibility/verify_graph.py`.

## Examples

`examples/NN_<family>_sample.csv` holds the first five rows of each released
edge file. They are real, public Hugging Face identifiers in the
`source,edge_type,target` schema.

To see how a family appears in the graph itself:

```bash
python relationships/examples/show_relationship.py graph/VulChain.dot --family 1
```

## Notes on semantics

- **Direction.** Lineage edges point upstream → downstream. `new_version` is
  older → newer. `trained_on` points Dataset → Model.
- **Model → Model labels.** Labels are recorded or inferred, not verified.
  Of 710,010 `finetune` edges, 633,779 are default-assigned: a parent is
  declared but no adaptation type is given. Only 54,876 of the 943,861
  declared edges carry explicit relation evidence. RQ1 compares these labels
  with the Hub model-tree index.
- **Dataset → Dataset** stores a candidate union under one type,
  `dataset_relationship_candidate`. Evidence-specific types remain in the
  construction outputs.
- **Space and GitHub edges** record associations and references. They are not
  verified deployments or executable dependencies.
