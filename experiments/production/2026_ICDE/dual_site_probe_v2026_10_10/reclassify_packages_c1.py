"""Created: 2026-10-11
Version: pkg-extract-v2026.10.11-c1 (change ID v2026.10.11-claude-07)
Purpose: reclassify saved, already-verified responses in analysis.sqlite3 under package_extraction_c1
without GPU reruns and without modifying original package_finding rows (raw responses and original
findings preserved). Adds only:
  package_reclassification(policy_version, root_node_id, seed_id, occurrence, ..., status)
      status = 'retained' | 'excluded_shell_comment'
  package_reclassification_execution(policy_version, root_node_id, seed_id, reclassified_at)
  view package_finding_effective_c1 (original rows + c1 status; excluded rows are not findings under c1)
  metadata key 'package_reclassification_c1'
Incremental and idempotent: only complete executions not yet reclassified under this policy are scanned.
Holds DATA/locks/analysis.lock while writing; backs up the ledger to HG_LEDGER_BACKUP_DIR first.
Run on a compute node (the TACC supervisor runs it daily).
Change history:
2026-10-11 v2026.10.11-claude-08
- Also reclassifies artifact-labelled (GGUF/llama.cpp) results: artifact_execution/artifact_package_finding;
  adds view artifact_package_finding_effective_c1. Backup reclassify_packages_c1.py.bak.20261011-140242.
"""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from common import DATA, HERE, digest
sys.path.insert(0, str(HERE.parent))
from package_extraction_c1 import POLICY, classify

SCHEMA = '''
CREATE TABLE IF NOT EXISTS package_reclassification(policy_version TEXT,root_node_id TEXT,seed_id TEXT,occurrence INTEGER,
  raw_name TEXT,ecosystem TEXT,construct TEXT,start_offset INTEGER,original_verdict TEXT,status TEXT,reason TEXT,reclassified_at TEXT,
  PRIMARY KEY(policy_version,root_node_id,seed_id,occurrence));
CREATE TABLE IF NOT EXISTS package_reclassification_execution(policy_version TEXT,root_node_id TEXT,seed_id TEXT,reclassified_at TEXT,
  PRIMARY KEY(policy_version,root_node_id,seed_id));
CREATE VIEW IF NOT EXISTS package_finding_effective_c1 AS
  SELECT f.*, r.status AS c1_status FROM package_finding f
  LEFT JOIN package_reclassification r ON r.policy_version='pkg-extract-v2026.10.11-c1'
   AND r.root_node_id=f.root_node_id AND r.seed_id=f.seed_id AND r.occurrence=f.occurrence;
'''
ARTIFACT_VIEW = '''
CREATE VIEW IF NOT EXISTS artifact_package_finding_effective_c1 AS
  SELECT f.*, r.status AS c1_status FROM artifact_package_finding f
  LEFT JOIN package_reclassification r ON r.policy_version='pkg-extract-v2026.10.11-c1'
   AND r.root_node_id=f.root_node_id AND r.seed_id=f.seed_id AND r.occurrence=f.occurrence;
'''
FAMILIES = (('execution', 'package_finding'), ('artifact_execution', 'artifact_package_finding'))
METHOD = {'policy_version': POLICY, 'module': 'dual_site_probe_v2026_10_10/package_extraction_c1.py',
  'change': 'install-command candidates that start inside an unquoted trailing shell comment are excluded',
  'unchanged': 'frozen package_probe_validation.py; original package_finding rows; imports/dependency extraction; registry evidence',
  'reason': "shlex.split without comments=True turned comment words (e.g. 'for', 'scalability') into package candidates"}

def backup(path):
    folder = Path(os.environ.get('HG_LEDGER_BACKUP_DIR', '<REDACTED_TACC_SCRATCH>/hg_dual_ledger_backups_v2026_10_10'))
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/(path.name+'.bak.'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.pre-c1')
    with path.open('rb') as s, target.open('xb') as d: shutil.copyfileobj(s, d)
    if digest(path) != digest(target): raise RuntimeError('Backup mismatch')
    return target

def main():
    path = DATA/'analysis.sqlite3'
    if not path.exists(): raise RuntimeError('No analysis ledger')
    with (DATA/'locks/analysis.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = backup(path)
        db = sqlite3.connect(path, timeout=60)
        try:
            db.executescript(SCHEMA)
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'artifact_package_finding' in tables: db.executescript(ARTIFACT_VIEW)
            pending = []
            for ex_table, f_table in FAMILIES:
                if ex_table not in tables or f_table not in tables: continue
                pending += [(f_table,)+r for r in db.execute(f'''SELECT e.root_node_id,e.seed_id,e.response FROM {ex_table} e
                WHERE e.status='complete' AND e.response IS NOT NULL AND NOT EXISTS (SELECT 1 FROM package_reclassification_execution x
                WHERE x.policy_version=? AND x.root_node_id=e.root_node_id AND x.seed_id=e.seed_id)''', (POLICY,)).fetchall()]
            now = datetime.now(timezone.utc).isoformat(); rows = excluded = 0; mismatched = []
            with db:
                for f_table, root, seed, response in pending:
                    flags = {(c['start_offset'], c['ecosystem'], c['construct']): ex for c, ex in classify(response)}
                    for occ, verdict, ev in db.execute(f'SELECT occurrence,verdict,evidence_json FROM {f_table} WHERE root_node_id=? AND seed_id=?', (root, seed)).fetchall():
                        e = json.loads(ev); key = (e.get('start_offset'), e.get('ecosystem'), e.get('construct'))
                        if key not in flags: mismatched.append((root, seed, occ)); status = 'retained'; reason = 'no matching frozen candidate; kept'
                        elif flags[key]: status = 'excluded_shell_comment'; reason = 'candidate starts inside unquoted shell comment on install line'; excluded += 1
                        else: status = 'retained'; reason = ''
                        db.execute('INSERT INTO package_reclassification VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                            (POLICY, root, seed, occ, e.get('raw_name'), e.get('ecosystem'), e.get('construct'), e.get('start_offset'), verdict, status, reason, now))
                        rows += 1
                    db.execute('INSERT INTO package_reclassification_execution VALUES (?,?,?,?)', (POLICY, root, seed, now))
                db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('package_reclassification_c1', json.dumps(dict(METHOD, last_run=now))))
            print(json.dumps({'policy': POLICY, 'executions_scanned': len(pending), 'finding_rows': rows, 'excluded_shell_comment': excluded,
                              'unmatched_rows_kept': len(mismatched), 'ledger_backup': str(target)}))
        finally: db.close()

if __name__ == '__main__': main()
