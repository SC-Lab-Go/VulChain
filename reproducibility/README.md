# Reproducibility tools

| File | Purpose |
|---|---|
| `verify_environment.sh` | Checks the Python version and the optional construction dependencies |
| `verify_graph.py` | Verifies a downloaded `VulChain.dot`: SHA-256, totals, entity types, and the 17 relationship families |
| `verify_results.py` | Runs every table/figure entry point and prints one status line per artifact |
| `TRANSFER_CHECKLIST.md` | Inputs still on other servers, and the artifacts that depend on them |

Typical order:

```bash
bash reproducibility/verify_environment.sh
python reproducibility/verify_graph.py graph/VulChain.dot
python reproducibility/verify_results.py --release-dir <extracted release>
python -m unittest discover -s tests -v
```
