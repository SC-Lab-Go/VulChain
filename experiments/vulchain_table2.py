"""Table II ID-set counting used by tab:model_corpus.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Count distinct base and derivative model IDs per adaptation label.

The definitions below are copied verbatim (Python ast extraction) from the
production table2_unique_models.py; only require() is new.
"""

import hashlib
import itertools
import json
from collections import Counter, defaultdict
from types import SimpleNamespace

# Copied verbatim from generate_graph_cohort_macros.py lines 32-33
# (SHA-256 bafcb42ebd992eb364cddb9cbf6def0bfa5436fa33b1c9d839af9598e683e599).
CATS = dict(finetune='FT', adapter='AD', quantized='QT', merged='Merge',
            converted='Conv', new_version='NewVer')


# Copied verbatim from generate_graph_cohort_macros.py lines 69-71.
def records_digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows), separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


graph = SimpleNamespace(CATS=CATS, records_digest=records_digest)


def require(condition, message):
    if not condition:
        raise ValueError(message)


# Copied verbatim from table2_unique_models.py
# SHA-256 de91f6547cc6d44fc23f492f8854b81e1af08f40d0b88b8cd7e0095df2425c92
# Lines: 17-17, 21-24, 27-57

LABELS = {'finetune': 'FT', 'adapter': 'AD', 'quantized': 'QT', 'merged': 'Merge'}

def eligible(rows):
    rows = [tuple(r) for r in rows]
    require(all(r[2] in graph.CATS for r in rows), 'Unknown source adaptation label')
    return [r for r in rows if r[2] in LABELS]

def summarize(rows):
    """Filter first, then build ID sets. Duplicate records never inflate models."""
    rows = eligible(rows)
    require(bool(rows), 'No eligible adaptation relationships')
    require(all(p and c and p == p.strip() and c == c.strip() and p != c for p, c, _ in rows), 'Invalid exact ID')
    bases = {p for p, c, k in rows}
    cats = {name: {c for p, c, k in rows if k == label} for label, name in LABELS.items()}
    derivs = set().union(*cats.values())
    models = bases | derivs
    values = {name: len(ids) for name, ids in cats.items()}
    values.update(Bases=len(bases), UniqueDerivs=len(derivs), UniqueModels=len(models),
                  Overlap=len(bases & derivs), Pairs=len(set(rows)))
    pair_labels, child_labels, child_parents = defaultdict(set), defaultdict(set), defaultdict(set)
    for p, c, k in rows:
        pair_labels[p, c].add(k)
        child_labels[c].add(k)
        child_parents[c].add(p)
    overlaps = {a + '/' + b: sorted(cats[a] & cats[b]) for a, b in itertools.combinations(cats, 2)}
    require(values['UniqueModels'] >= max(values['Bases'], values['UniqueDerivs']), 'Union bounds failed')
    require(values['UniqueModels'] == len(bases | set().union(*cats.values())), 'ID-set union failed')
    return {'values': values, 'input_eligible_records': len(rows),
            'duplicate_exact_records': len(rows) - len(set(rows)),
            'distinct_parent_child_pairs': len(pair_labels),
            'multiple_label_pairs': [{'parent_id': p, 'child_id': c, 'labels': sorted(labels)}
                                     for (p, c), labels in sorted(pair_labels.items()) if len(labels) > 1],
            'multiple_label_derivatives': {c: sorted(labels) for c, labels in sorted(child_labels.items()) if len(labels) > 1},
            'multiple_parent_derivatives': {c: sorted(ps) for c, ps in sorted(child_parents.items()) if len(ps) > 1},
            'category_overlap_ids': overlaps, 'upstream_derivative_overlap_ids': sorted(bases & derivs),
            'displayed_sets_mutually_exclusive': not (bases & derivs) and not any(overlaps.values()),
            'category_record_counts': dict(Counter(LABELS[k] for _, _, k in rows)),
            'records_sha256': graph.records_digest(sorted(set(rows)))}
