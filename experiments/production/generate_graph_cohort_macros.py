#!/usr/bin/env python3
"""Created: 2026-10-27. Version: v2026.10.27-01.
Purpose: verify Table II snapshots and atomically regenerate independent macros.
New file; no predecessor or backup. Standard library only; no inference/imports.
Final validation additions: 2026-10-27 v2026.10.27-01;
backup generate_graph_cohort_macros.py.bak.20261027-121540.

Daily: python3 -B generate_graph_cohort_macros.py
Initial freeze: --freeze --reason TEXT
Replacement: --freeze --replace-frozen --expected-frozen-sha256 SHA --reason TEXT
The active selection is common.py's dual-site DATA manifest, never result ledgers.
--selection-dir allows an explicitly designated successor with setup_report hashes.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
GRAPH = HERE / '2026_ICDE/graphdb'
FROZEN = HERE / 'table2_frozen_snapshot.json'
VERSION = 'v2026.10.27-01'
CATS = dict(finetune='FT', adapter='AD', quantized='QT', merged='Merge',
            converted='Conv', new_version='NewVer')
HIST = {'OneHop': [11047, 8202, 3658, 402, 75, 105, 23489],
        'Ready': [3811, 3761, 188, 278, 13, 81, 8132],
        'Cohort': [3047, 3514, 115, 133, 4, 8, 6821]}
QUERY = '''SELECT b.model_id,m.model_id,c.category FROM category_membership c
 JOIN model b ON b.node_key=c.root_key JOIN model m ON m.node_key=c.node_key
 WHERE c.is_direct=1'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def csv_rows(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))


def provenance(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path)}


def records_digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows), separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def count(rows):
    require(bool(rows), 'Essential population is empty')
    require(len(rows) == len(set(rows)), 'Duplicate parent-child-relation records')
    for p, c, label in rows:
        require(p and c and p == p.strip() and c == c.strip(), 'Invalid exact model ID')
        require(p != c, 'Self relationship')
        require(label in CATS, 'Unknown adaptation label: ' + label)
    parents = {r[0] for r in rows}
    children = {r[1] for r in rows}
    cats = Counter(r[2] for r in rows)
    result = {suffix: cats[label] for label, suffix in CATS.items()}
    result.update(Bases=len(parents), Pairs=len(rows), UniqueDerivs=len(children),
                  Overlap=len(parents & children), Models=len(parents | children),
                  distinct_parent_child_pairs=len({r[:2] for r in rows}),
                  extra_relation_labels=len(rows) - len({r[:2] for r in rows}),
                  records_sha256=records_digest(rows))
    require(sum(result[k] for k in CATS.values()) == result['Pairs'], 'Category total mismatch')
    require(result['Models'] == result['Bases'] + result['UniqueDerivs'] - result['Overlap'],
            'Model union mismatch')
    return result


def publish(path, content):
    """Verified, exclusive dated backup; same-directory fsync and atomic replace."""
    path = Path(path)
    data = content.encode()
    if path.exists():
        if path.read_bytes() == data:
            return
        stamp = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y%m%d-%H%M%S')
        backup = Path(str(path) + '.bak.' + stamp)
        with path.open('rb') as src, backup.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        require(backup.exists() and sha(backup) == sha(path), 'Backup verification failed')
    fd, pending = tempfile.mkstemp(prefix=path.name + '.pending.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(pending, path)
    finally:
        if os.path.exists(pending):
            os.unlink(pending)


def frozen_inputs():
    database = GRAPH / 'text_generation_root_descendant_counts.sqlite3'
    preflight = GRAPH / 'expanded_preflight_all_4887_v2026_10_10'
    paths = [database, GRAPH / 'text_generation_root_descendant_counts.csv',
             GRAPH / 'text_generation_root_descendant_counts_summary.json',
             preflight / 'model_preflight.csv', preflight / 'root_descendant_counts.csv',
             preflight / 'summary.json', GRAPH / 'count_text_root_descendants.py',
             GRAPH / 'expanded_preflight_v2026_10_10.py', HERE / 'source/model_lineage_edges.py',
             HERE / 'source/count_model_types.py',
             HERE / '2026_ICDE/lineage_probe_v2026_10_10/prepare.py',
             HERE / '2026_ICDE/dual_site_probe_v2026_10_10/prepare.py']
    return paths


def reconstruct():
    database, _, summary_path, preflight_path, root_counts_path, ready_summary_path, *_ = frozen_inputs()
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        require(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Graph SQLite integrity')
        require(not db.execute('PRAGMA foreign_key_check').fetchall(), 'Graph foreign keys')
        rows = [tuple(r) for r in db.execute(QUERY)]
        roots = {r[0] for r in db.execute('SELECT m.model_id FROM root r JOIN model m ON r.root_key=m.node_key')}
        metadata = {k: json.loads(v) for k, v in db.execute('SELECT * FROM metadata')}
    statuses = csv_rows(preflight_path)
    require(len(statuses) == len({r['model_id'] for r in statuses}), 'Duplicate preflight IDs')
    status = {r['model_id']: r['status'] for r in statuses}
    expected = roots | {r[1] for r in rows}
    require(set(status) == expected, 'Preflight model population differs from graph population')
    require(set(status.values()) <= {'ready', 'blocked'}, 'Preflight incomplete/unknown status')
    summary = read_json(ready_summary_path)
    require(summary['run_state'] == 'complete' and not summary['worker_failures'], 'Preflight not complete')
    ready = [r for r in rows if status[r[1]] == 'ready']
    one, filtered = count(rows), count(ready)
    require(set(ready) <= set(rows), 'Ready not subset of one-hop records')
    graph_summary = read_json(summary_path)
    require(len(roots) == graph_summary['roots'], 'Root inventory disagrees with summary')
    require(one['Bases'] == graph_summary['roots_with_text_direct_children'], 'Contributing root summary mismatch')
    # Independently cross-check every published per-root category count.
    table = csv_rows(root_counts_path)
    require(len(table) == len(roots) and {r['base_model'] for r in table} == roots,
            'Ready per-root inventory mismatch')
    all_by_root, ready_by_root = defaultdict(Counter), defaultdict(Counter)
    for p, c, label in rows:
        all_by_root[p][label] += 1
    for p, c, label in ready:
        ready_by_root[p][label] += 1
    columns = dict(finetune='FT', adapter='AD', quantized='QT', merged='Merge',
                   converted='Converted', new_version='New_version')
    for r in table:
        for label, col in columns.items():
            require(int(r[col]) == ready_by_root[r['base_model']][label], 'Per-root readiness mismatch')
            require(int(r[col + '_total']) == all_by_root[r['base_model']][label], 'Per-root graph mismatch')
    return rows, ready, {'OneHop': one, 'Ready': filtered}, roots, metadata, summary, status


def freeze(args):
    require(args.reason and args.reason.strip(), '--freeze requires a recorded --reason')
    previous = None
    if FROZEN.exists():
        require(args.replace_frozen, 'Frozen file exists; separate --replace-frozen operation required')
        require(args.expected_frozen_sha256 == sha(FROZEN), 'Explicit prior frozen SHA-256 required')
        previous = read_json(FROZEN)
    rows, ready, counts, roots, metadata, summary, status = reconstruct()
    value = {'schema_version': 1, 'change_id': VERSION,
             'snapshot_id': metadata['version'] + '+' + summary['version'] + '-' + records_digest(rows)[:12],
             'created_at': datetime.now(timezone.utc).isoformat(), 'reason': args.reason,
             'source_metadata': metadata, 'readiness_summary': summary,
             'TextGenLineageRoots': len(roots), 'counts': counts,
             'sources': [provenance(p) for p in frozen_inputs()],
             'definitions': {
                 'identity': 'Exact case-sensitive (upstream ID, derivative ID, adaptation label); no alias folding.',
                 'total': 'Sum six adaptation categories; Base excluded. Multi-label pairs retain each distinct relation.',
                 'OneHop': 'Recorded text-generation/text2text-generation roots and direct eligible children; root excluded.',
                 'Ready': 'One-hop records whose child has status ready in the completed static snapshot; parent readiness not required.',
                 'FT': 'Preserve graph finetune labels, including default fallback, tag-implied and inferred labels; not proof of explicit fine-tuning.',
                 'ambiguous': 'Keep source classifications; never relabel from names or security results. Unknown labels fail.',
                 'roots': 'All eligible root inventory, including roots with no direct children; differs from OneHopBases.'},
             'ready_parent_statuses': dict(Counter(status[p] for p in {r[0] for r in ready})),
             'replacement_history': ([] if previous is None else previous.get('replacement_history', []) +
                 [{'previous_sha256': sha(FROZEN), 'previous_snapshot_id': previous['snapshot_id'],
                   'reason': args.reason}])}
    publish(FROZEN, json.dumps(value, indent=2, sort_keys=True) + '\n')
    print('Frozen snapshot written:', FROZEN, value['snapshot_id'])


def selection(folder, ready, status):
    report_path = folder / 'setup_report.json'
    report_sha = sha(report_path)
    report = read_json(report_path)
    require(bool(report.get('version')), 'Selection version missing')
    entries = report['frozen_inputs']
    require(len(entries) == len({r['path'] for r in entries}), 'Duplicate selection checksum entries')
    expected = {r['path']: r['sha256'] for r in entries}
    paths = [report_path]
    for rel in ('manifest/memberships.csv', 'manifest/models.jsonl', 'manifest/roots.csv'):
        require(rel in expected and sha(folder / rel) == expected[rel], 'Unvalidated selected source: ' + rel)
        paths.append(folder / rel)
    source = csv_rows(folder / 'manifest/memberships.csv')
    require(all(r['hop'] == '1' for r in source), 'Selected non-one-hop record')
    rows = [(r['root_model'], r['child_model'], r['category']) for r in source]
    counts = count(rows)
    require(set(rows) <= set(ready), 'Selected records absent from frozen static-ready population')
    models = [json.loads(line) for line in (folder / 'manifest/models.jsonl').read_text().splitlines()]
    require(len(models) == len({m['model_id'] for m in models}), 'Duplicate selected model ID')
    require({m['model_id'] for m in models} == {x for p, c, _ in rows for x in (p, c)}, 'Selected model union differs from manifest')
    require(all(status.get(m['model_id']) == 'ready' for m in models),
            'Selected model was not ready in the frozen preflight')
    roots = csv_rows(folder / 'manifest/roots.csv')
    require(len(roots) == len({r['base_model'] for r in roots}), 'Duplicate selected upstream')
    require({r['base_model'] for r in roots} == {r[0] for r in rows}, 'Selected root inventory differs')
    # Recompute the documented process: every ready direct relation of selected roots.
    require(set(rows) == {r for r in ready if r[0] in {x['base_model'] for x in roots}},
            'Selection does not retain all frozen ready relations of selected roots')
    if 'memberships' in report:
        require(counts['Pairs'] == report['memberships'], 'Selected report membership count mismatch')
    if 'models' in report:
        require(counts['Models'] == report['models'], 'Selected report model count mismatch')
    # Reject concurrent edits between verification, parsing and publication.
    sources = [provenance(p) for p in paths]
    require(sha(report_path) == report_sha, 'Selection setup report changed during read')
    for rel in expected.keys() & {'manifest/memberships.csv', 'manifest/models.jsonl', 'manifest/roots.csv'}:
        require(sha(folder / rel) == expected[rel], 'Selection changed during read')
    return counts, report['version'], sources


def macros(frozen, selected, selected_version, sources):
    lines = ['% Created: 2026-10-27; change ' + VERSION + '; generated Table II counts.',
             '% Frozen snapshot: ' + frozen['snapshot_id'],
             '% Selected snapshot: ' + selected_version,
             '% Selected memberships SHA256: ' + next(r['sha256'] for r in sources if r['path'].endswith('/memberships.csv')),
             '% Totals count labeled relationships; Base is never added to Pairs.']
    for prefix, counts in list(frozen['counts'].items()) + [('Cohort', selected)]:
        for suffix in ['Bases'] + list(CATS.values()):
            lines.append('\\newcommand{\\' + prefix + suffix + '}{' + str(counts[suffix]) + '}')
        expr = '+'.join('\\' + prefix + s for s in CATS.values())
        lines.append('\\newcommand{\\' + prefix + 'Pairs}{\\number\\numexpr' + expr + '\\relax}')
        if prefix == 'Cohort':
            for suffix in ('UniqueDerivs', 'Overlap'):
                lines.append('\\newcommand{\\Cohort' + suffix + '}{' + str(counts[suffix]) + '}')
            lines.append('\\newcommand{\\CohortModels}{\\number\\numexpr\\CohortBases+\\CohortUniqueDerivs-\\CohortOverlap\\relax}')
    lines.append('\\newcommand{\\TextGenLineageRoots}{' + str(frozen['TextGenLineageRoots']) + '}')
    return '\n'.join(lines) + '\n'


def generate(args):
    frozen_sha = sha(FROZEN)
    frozen = read_json(FROZEN)
    for entry in frozen['sources']:
        require(sha(entry['path']) == entry['sha256'], 'Frozen source changed: ' + entry['path'])
    rows, ready, counts, roots, _, _, status = reconstruct()
    require(counts == frozen['counts'] and len(roots) == frozen['TextGenLineageRoots'], 'Frozen counts do not match original records')
    selected, selected_version, sources = selection(args.selection_dir.resolve(), ready, status)
    counts['Cohort'] = selected
    lines = ['Table II verified counts', 'Change: ' + VERSION,
             'Frozen snapshot: ' + frozen['snapshot_id'], 'Selected snapshot: ' + selected_version,
             'OneHop source: ' + str(frozen_inputs()[0]),
             'Ready source: ' + str(frozen_inputs()[3]),
             'Selected source: ' + str(args.selection_dir.resolve() / 'manifest/memberships.csv'),
             'Stage | Base | FT | AD | QT | Merge | Conv. | New_Ver. | Total']
    for prefix, c in counts.items():
        lines.append(prefix + ' | ' + ' | '.join(str(c[k]) for k in ['Bases'] + list(CATS.values()) + ['Pairs']))
    lines += ['Selected unique derivatives: ' + str(selected['UniqueDerivs']),
              'Selected overlap: ' + str(selected['Overlap']), 'Selected model union: ' + str(selected['Models']),
              'Eligible text-generation lineage roots: ' + str(len(roots)),
              'Historical differences (verified minus historical):']
    for stage, historical in HIST.items():
        lines.append(stage + ': ' + ', '.join(k + '=' + str(counts[stage][k] - h)
                     for k, h in zip(list(CATS.values()) + ['Pairs'], historical)))
    lines += ['Cohort Bases=0; UniqueDerivs=0; Models=0 (all historical deltas).',
              'OneHop Base and Ready Base were unknown historically; now calculated directly.',
              'PASS: source checksums; SQLite integrity/foreign keys; exact IDs; duplicate triple rejection;',
              'PASS: per-root category reconstruction; Ready subset OneHop; selected subset Ready;',
              'PASS: all ready relations of selected roots retained; selected model/root inventories and frozen readiness;',
              'PASS: category sums exclude Base; unique model union includes overlap subtraction.',
              'Distinct unlabelled parent-child pairs: OneHop=' + str(counts['OneHop']['distinct_parent_child_pairs']) +
              ', Ready=' + str(counts['Ready']['distinct_parent_child_pairs']) + ', Cohort=' + str(selected['distinct_parent_child_pairs']),
              'Extra relation labels: ' + ', '.join(k + '=' + str(counts[k]['extra_relation_labels']) for k in counts),
              'Readiness is child-only; contributing parent statuses: ' + json.dumps(frozen['ready_parent_statuses'], sort_keys=True),
              'FT preserves default fallback labels; this is not explicit fine-tuning evidence.',
              'LaTeX compilation: not performed by this generator. Available compiler: ' +
              str(next((shutil.which(n) for n in ('pdflatex', 'lualatex', 'xelatex', 'tectonic') if shutil.which(n)), None)) +
              '; actual formatter file present: ' + str((HERE / 'table2_icdecount.tex').is_file()),
              'RQ3/RQ4/RQ5 macros and experimental results are not read as selection inputs or modified.']
    audit = {'created': '2026-10-27', 'change_id': VERSION, 'purpose': 'Table II generation provenance',
             'frozen_snapshot_sha256': frozen_sha, 'frozen_snapshot_id': frozen['snapshot_id'],
             'selection_version': selected_version, 'selected_sources': sources,
             'generator': provenance(__file__), 'counts': counts, 'validation': lines}
    # Validate everything before replacing any output; frozen file is never written here.
    require(sha(FROZEN) == frozen_sha, 'Frozen snapshot changed concurrently')
    for s in frozen['sources'] + sources:
        require(sha(s['path']) == s['sha256'], 'Input changed during validation: ' + s['path'])
    publish(HERE / 'graph_cohort_numbers.tex', macros(frozen, selected, selected_version, sources))
    publish(HERE / 'table2_validation.json', json.dumps(audit, indent=2, sort_keys=True) + '\n')
    publish(HERE / 'table2_validation.txt', '\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main():
    # v2026.10.27-04: unique-ID stages; preserve all selected Cohort macro meanings.
    # Backup: generate_graph_cohort_macros.py.bak.20261027-132236.
    import table2_unique_models as unique
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection-dir', type=Path, default=GRAPH / 'dual_site_probe_v2026_10_10')
    p.add_argument('--freeze', action='store_true')
    p.add_argument('--replace-frozen', action='store_true')
    p.add_argument('--expected-frozen-sha256')
    p.add_argument('--reason')
    args = p.parse_args()
    require(args.freeze or not (args.replace_frozen or args.expected_frozen_sha256 or args.reason),
            'Replacement options require separate --freeze operation')
    if args.freeze:
        require(not args.replace_frozen and not args.expected_frozen_sha256,
                'Original and new baselines are immutable; use a new version ID')
        unique.freeze(args.reason)
    else:
        unique.generate_graph(args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, sqlite3.Error, json.JSONDecodeError) as exc:
        sys.exit('Table II ERROR: ' + str(exc))
