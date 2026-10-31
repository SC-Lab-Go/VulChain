#!/usr/bin/env python3
"""Created 2026-10-27; v2026.10.27-04. Unique-ID Table II accounting.
Explicit --freeze --reason TEXT creates a new immutable baseline, never replaces it.
Source relationships and the original frozen snapshot remain read-only.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import generate_graph_cohort_macros as graph

ROOT = Path(__file__).resolve().parent
VERSION = 'v2026.10.27-04'
BASELINE = ROOT / ('table2_frozen_snapshot.' + VERSION + '.json')
LABELS = {'finetune': 'FT', 'adapter': 'AD', 'quantized': 'QT', 'merged': 'Merge'}
require = graph.require


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


def freeze(reason):
    require(reason and reason.strip(), 'Explicit freeze reason required')
    require(not BASELINE.exists(), 'Immutable baseline exists; a replacement needs a NEW version ID')
    original = graph.read_json(graph.FROZEN)
    for source in original['sources']:
        require(graph.sha(source['path']) == source['sha256'], 'Original source changed: ' + source['path'])
    one, ready, old_counts, roots, metadata, summary, _ = graph.reconstruct()
    require(old_counts == original['counts'], 'Original baseline cannot be reproduced')
    one_filtered, ready_filtered = eligible(one), eligible(ready)
    require(set(ready_filtered) <= set(one_filtered), 'Ready not in one-hop adaptation population')
    stages = {'OneHop': summarize(one_filtered), 'Ready': summarize(ready_filtered)}
    contributing_roots = {r[0] for r in one_filtered}
    data = {'schema_version': 2, 'version': VERSION, 'snapshot_id': VERSION + '-unique-adaptation-models',
            'created_at': datetime.now(timezone.utc).isoformat(), 'reason': reason,
            'previous_snapshot': graph.provenance(graph.FROZEN),
            'previous_snapshot_id': original['snapshot_id'], 'previous_counts': original['counts'],
            'definition_change': 'Four adaptation labels only, filtered BEFORE parent/child ID sets. Categories count distinct children, Total counts actual upstream/derivative union. No relationship-count arithmetic for Total.',
            'label_mapping': LABELS, 'excluded_labels': ['converted', 'new_version'],
            'identity': 'Exact case-sensitive source model IDs; no alias normalization.',
            'FT_rule': 'Preserve recorded finetune including default, explicit, tag-implied and inferred labels; not proof of explicit fine-tuning.',
            'readiness_rule': 'Child status ready in original completed static snapshot; parent readiness not required.',
            'TextGenLineageRoots': len(roots), 'RootsWithEligibleAdaptations': len(contributing_roots),
            'RootsWithoutEligibleAdaptations': len(roots - contributing_roots),
            'stages': stages, 'counts': {k: s['values'] for k, s in stages.items()},
            'stage_records': {'OneHop': one_filtered, 'Ready': ready_filtered},
            'source_metadata': metadata, 'readiness_summary': summary, 'sources': original['sources'],
            'creator': graph.provenance(__file__)}
    # Exclusive creation: no code path overwrites either baseline.
    with BASELINE.open('x') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')
    print('Created immutable baseline:', BASELINE)
    print(json.dumps(data['counts'], indent=2))


def load_baseline():
    data = graph.read_json(BASELINE)
    require(data['version'] == VERSION and data['label_mapping'] == LABELS, 'Baseline definitions differ')
    require(graph.sha(data['previous_snapshot']['path']) == data['previous_snapshot']['sha256'], 'Original frozen baseline changed')
    for source in data['sources']:
        require(graph.sha(source['path']) == source['sha256'], 'Frozen source changed: ' + source['path'])
    for stage, rows in data['stage_records'].items():
        require(all(r[2] in LABELS for r in rows), 'Excluded relation in frozen adaptation stage')
        require(summarize(rows) == data['stages'][stage], 'Frozen ID-set validation failed: ' + stage)
    require(set(map(tuple, data['stage_records']['Ready'])) <= set(map(tuple, data['stage_records']['OneHop'])), 'Frozen nesting failed')
    return data


def generate_graph(args):
    baseline = load_baseline()
    original = graph.read_json(graph.FROZEN)
    one, ready, _, _, _, _, status = graph.reconstruct()
    require(graph.records_digest(eligible(one)) == graph.records_digest(baseline['stage_records']['OneHop']), 'Original one-hop differs')
    require(graph.records_digest(eligible(ready)) == graph.records_digest(baseline['stage_records']['Ready']), 'Original readiness differs')
    selected, selection_version, sources = graph.selection(args.selection_dir.resolve(), ready, status)
    legacy = graph.macros(original, selected, selection_version, sources)
    # All Cohort macros keep their existing selected-record semantics and names.
    selected_lines = [line for line in legacy.splitlines() if line.startswith('\\newcommand{\\Cohort') or line.startswith('\\newcommand{\\TextGen')]
    lines = ['% Created 2026-10-27; ' + VERSION + '; unique-model Table II.',
             '% Frozen baseline: ' + baseline['snapshot_id'],
             '% Categories are distinct derivative IDs; totals are actual ID-set unions.',
             '% Cohort macros below retain the original selected-cohort semantics.']
    for stage, values in baseline['counts'].items():
        for suffix in ['Bases'] + list(LABELS.values()) + ['UniqueDerivs', 'UniqueModels', 'Overlap', 'Pairs']:
            lines.append('\\newcommand{\\' + stage + suffix + '}{' + str(values[suffix]) + '}')
        lines.append('\\newcommand{\\' + stage + 'Total}{\\' + stage + 'UniqueModels}')
    for suffix in ('RootsWithEligibleAdaptations', 'RootsWithoutEligibleAdaptations'):
        lines.append('\\newcommand{\\TextGen' + suffix + '}{' + str(baseline[suffix]) + '}')
    lines += selected_lines
    graph.publish(ROOT / 'graph_cohort_numbers.tex', '\n'.join(lines) + '\n')
    audit = {'version': VERSION, 'baseline': graph.provenance(BASELINE), 'counts': baseline['counts'],
             'selection_version': selection_version, 'selected_sources': sources,
             'selected_counts_unchanged_semantics': selected, 'generator': graph.provenance(__file__)}
    graph.publish(ROOT / 'table2_validation.json', json.dumps(audit, indent=2, sort_keys=True) + '\n')
    text = ['Unique-model frozen Table II baseline: ' + baseline['snapshot_id']]
    text += [stage + ': ' + json.dumps(values, sort_keys=True) for stage, values in baseline['counts'].items()]
    graph.publish(ROOT / 'table2_validation.txt', '\n'.join(text) + '\n')
    print('\n'.join(text))


def write_audit(baseline, evaluation):
    """Current human-readable audit; old report versions survive dated backups.
    Addition backup: table2_unique_models.py.bak.20261027-132620.
    """
    stages = dict(baseline['stages'])
    stages['Evaluated'] = evaluation['unique_model_accounting']
    lines = ['# Table II unique-model audit', '', 'Created: 2026-10-27. Version: ' + VERSION + '.',
             'Supersedes earlier record-count Table II presentations; all source relationships and the original baseline remain intact.',
             '', 'Baseline: `' + str(BASELINE) + '`; SHA256 `' + graph.sha(BASELINE) + '`.',
             'Evaluated as of: ' + evaluation['as_of'] + '; snapshot `' + evaluation['rq3_snapshot_id'] + '`.',
             '', '| Stage | Base | FT | AD | QT | Merge | Unique derivatives | Total union | Relationships |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for stage, stats in stages.items():
        c = stats['values']
        lines.append('| ' + stage + ' | ' + ' | '.join(f'{c[k]:,}' for k in ['Bases', 'FT', 'AD', 'QT', 'Merge', 'UniqueDerivs', 'UniqueModels', 'Pairs']) + ' |')
    lines += ['', 'Original versus corrected displayed values (Base/FT/AD/QT/Merge/Total):', '']
    old = {'OneHop': [3212, 11047, 8202, 3658, 402, 26521], 'Ready': [855, 3811, 3761, 188, 278, 8893],
           'Evaluated': [34, 157, 72, 0, 9, 272]}
    for stage, previous in old.items():
        current = [stages[stage]['values'][k] for k in ['Bases', 'FT', 'AD', 'QT', 'Merge', 'UniqueModels']]
        lines.append('- ' + stage + ': ' + ', '.join(map(str, previous)) + ' -> ' + ', '.join(map(str, current)) +
                     '; deltas ' + ', '.join(str(b-a) for a, b in zip(previous, current)) + '.')
    lines += ['', 'Identity policy: exact case-sensitive model IDs. Mapping: finetune -> FT; adapter -> AD; quantized -> QT; merged -> Merge.',
              'Predicate applied before EVERY ID set: adaptation_label in {finetune, adapter, quantized, merged}. converted/new_version are excluded.',
              'FT keeps recorded default/explicit/tag-implied/inferred labels; no name-based relabeling or claim of explicit fine-tuning.',
              'OneHop uses direct category_membership records. Ready additionally requires child status ready in the original static snapshot; parent readiness is not required.',
              'Evaluated additionally requires BOTH endpoints fully completed under the existing RQ3 model revision, bank, original-verification and both-c1 criteria.',
              'Categories count distinct children per label; Total is the actual union of parents and children, stored as a plain integer. Source records are retained.',
              '', f"Eligible root inventory: {baseline['TextGenLineageRoots']:,}; contributing roots: {baseline['RootsWithEligibleAdaptations']:,}; roots without eligible adaptations: {baseline['RootsWithoutEligibleAdaptations']:,}.", '']
    for stage, stats in stages.items():
        lines += [stage + ' validation:',
                  '- Category intersections: ' + json.dumps({k: len(v) for k, v in stats['category_overlap_ids'].items()}, sort_keys=True) + '.',
                  '- Upstream/derivative overlap: ' + str(stats['values']['Overlap']) + '.',
                  '- Duplicate exact input rows: ' + str(stats['duplicate_exact_records']) + '; distinct parent-child pairs: ' + str(stats['distinct_parent_child_pairs']) + '.',
                  '- Multiple-label pairs: ' + str(len(stats['multiple_label_pairs'])) + '; multi-label children: ' + str(len(stats['multiple_label_derivatives'])) + '.',
                  '- Multiple-parent children: ' + str(len(stats['multiple_parent_derivatives'])) + '.',
                  '- Displayed ID sets mutually exclusive in this snapshot: ' + str(stats['displayed_sets_mutually_exclusive']) + '. This was verified, not assumed.', '']
    lines += [f"RQ3 reconciliation: {evaluation['full_rq3_completed_models']} fully evaluated models = {evaluation['full_rq3_completed_bases']} upstream-role + {evaluation['full_rq3_completed_derivatives']} derivative-role models; {evaluation['full_rq3_completed_responses']:,} completed responses.",
              'Table II excludes completed models with no eligible completed relationship: ' + json.dumps(evaluation['completed_models_outside_table2']) + '.',
              f"Its {evaluation['values']['UniqueModels']} model IDs account for {evaluation['values']['Responses']:,} completed responses. Existing RQ3 macros remain unchanged and retain the larger completion-population definition.",
              'Partial execution/verification models are excluded. The exact normalized RQ3 response identities and all available RQ3 count macros were cross-checked.',
              '', 'Sources and their checksums: new frozen JSON for graph/readiness; evaluated_cohort_validation.json for execution capture, prompt/revision checks, source snapshots and RQ3 manifests.',
              'All selected Cohort macros retain their existing full selected-relationship semantics. OneHop/Ready Pairs now explicitly describe eligible adaptation relationships, separate from unique counts.',
              'The original table2_frozen_snapshot.json is preserved. The new baseline is exclusively created and cannot be overwritten by the freeze command or daily generation.',
              '', 'Daily command (after normal RQ3 snapshot publication):', '', '```bash',
              'python3 -B ' + str(ROOT / 'generate_evaluated_cohort_macros.py'), '```',
              '', 'Graph/selected regeneration if needed: `python3 -B generate_graph_cohort_macros.py`. This reads the frozen baseline; it does not replace it.',
              'Upload the same filenames: graph_cohort_numbers.tex, evaluated_cohort_numbers.tex, graph_cohort_table.tex. Load graph counts before evaluated counts.',
              'Use the supplied siunitx icdecount formatter for comma grouping. No formatter is defined in either count file.',
              'TeX compilation remains unavailable on this server; standalone harnesses were updated. No new dependencies or experimental/manuscript/RQ files were modified.',
              '', 'Revised Model Cohort paragraph:', '',
              f"We identified \\icdecount{{\\OneHopUniqueDerivs}} unique text-generation derivatives through fine-tuning, adapter, quantization, or merge relationships from \\icdecount{{\\OneHopBases}} upstream models, yielding \\icdecount{{\\OneHopUniqueModels}} distinct models. Static readiness retained \\icdecount{{\\ReadyUniqueDerivs}} derivatives associated with \\icdecount{{\\ReadyBases}} upstreams (\\icdecount{{\\ReadyUniqueModels}} distinct models). As of \\EvalAsOf, \\icdecount{{\\EvalBases}} upstreams and \\icdecount{{\\EvalUniqueDerivs}} derivatives had both endpoints fully evaluated, yielding \\icdecount{{\\EvalUniqueModels}} distinct models in Table~\\ref{{tab:graph-cohort}}. Conversion and new-version relationships are excluded before forming these populations. Category columns count distinct derivative IDs and may overlap; totals use model-ID unions. The complete RQ3 execution population additionally contains five fully evaluated upstreams without an eligible completed child relationship, which are excluded from this table.", '']
    graph.publish(ROOT / 'table2_unique_model_audit.md', '\n'.join(lines))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--freeze', action='store_true', required=True)
    p.add_argument('--reason', required=True)
    args = p.parse_args()
    try:
        freeze(args.reason)
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit('Unique Table II ERROR: ' + str(exc))
