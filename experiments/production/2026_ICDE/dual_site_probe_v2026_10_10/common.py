"""Created 2026-10-10; v2026.10.10-dual-01. Portable experiment helpers."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = Path(os.environ.get('HG_DUAL_DATA', str(HERE.parent / 'graphdb/dual_site_probe_v2026_10_10'))).resolve()
CACHE_ROOT = Path(os.environ.get('HG_CACHE_ROOT', str(DATA / 'weight_cache'))).resolve()
VERSION = 'v2026.10.10-dual-01'

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

def verify_inputs(full=False, selected=None):
    report = json.loads((DATA / 'setup_report.json').read_text())
    for item in report['frozen_inputs']:
        if not full and item['path'].startswith(('metadata/', 'plan/shard_')) and item['path'] != selected:
            continue
        if digest(DATA / item['path']) != item['sha256']:
            raise RuntimeError('Frozen input changed: ' + item['path'])
    for item in report['source_inputs']:
        if digest(REPO / item['path']) != item['sha256']:
            raise RuntimeError('Protocol source changed: ' + item['path'])
