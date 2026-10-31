"""Created: 2026-10-11
Version: url-extract-v2026.10.11-c1 (change ID v2026.10.11-claude-08)
Purpose: reclassify saved, verified responses under url_extraction_c1 without GPU reruns. Original
url_finding / artifact_url_finding rows and raw responses are never modified. Adds only:
  url_reclassification(policy_version, family, root_node_id, seed_id, occurrence, raw_url, start_offset, end_offset,
                       context, frozen_occurrence, changed, verdict, evidence_json, reclassified_at)
  url_reclassification_execution(policy_version, family, root_node_id, seed_id, reclassified_at)
  views url_finding_effective_c1 (family native) and artifact_url_finding_effective_c1 (family artifact)
  metadata key 'url_reclassification_c1'
Unchanged occurrences reuse the original verdict/evidence; split Markdown parts are revalidated with the
frozen Verifier.validate (frozen context exclusions, feeds, Tranco, PSL, cached/live DNS evidence).
Incremental; holds DATA/locks/analysis.lock; ledger backed up to HG_LEDGER_BACKUP_DIR first. Compute node only.
Change history: 2026-10-11 open ledger with uri=True (read-only feed ATTACH failed); backup reclassify_urls_c1.py.bak.20261011-140552.
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
from url_extraction_c1 import POLICY, classify

FAMILIES = {'native': ('execution', 'url_finding'), 'artifact': ('artifact_execution', 'artifact_url_finding')}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS url_reclassification(policy_version TEXT,family TEXT,root_node_id TEXT,seed_id TEXT,occurrence INTEGER,raw_url TEXT,
  start_offset INTEGER,end_offset INTEGER,context TEXT,frozen_occurrence INTEGER,changed INTEGER,verdict TEXT,evidence_json TEXT,reclassified_at TEXT,
  PRIMARY KEY(policy_version,family,root_node_id,seed_id,occurrence));
CREATE TABLE IF NOT EXISTS url_reclassification_execution(policy_version TEXT,family TEXT,root_node_id TEXT,seed_id TEXT,reclassified_at TEXT,
  PRIMARY KEY(policy_version,family,root_node_id,seed_id));
CREATE VIEW IF NOT EXISTS url_finding_effective_c1 AS SELECT root_node_id,seed_id,occurrence,raw_url,start_offset,end_offset,context,verdict,evidence_json,
  frozen_occurrence,changed FROM url_reclassification WHERE policy_version='url-extract-v2026.10.11-c1' AND family='native';
CREATE VIEW IF NOT EXISTS artifact_url_finding_effective_c1 AS SELECT root_node_id,seed_id,occurrence,raw_url,start_offset,end_offset,context,verdict,evidence_json,
  frozen_occurrence,changed FROM url_reclassification WHERE policy_version='url-extract-v2026.10.11-c1' AND family='artifact';
'''
METHOD = {'policy_version': POLICY, 'module': 'dual_site_probe_v2026_10_10/url_extraction_c1.py',
  'change': "Markdown links: candidates containing '](' are split into link-text and destination parts (offsets preserved, frozen trimming and +/-160 context)",
  'validation': 'frozen url_probe_validation.Verifier.validate (context exclusions, URLhaus/PhishTank exact match, Tranco, PSL, DNS) unchanged',
  'unchanged': 'frozen extractor/verifier; original url_finding rows; raw responses'}

def backup(path):
    folder = Path(os.environ.get('HG_LEDGER_BACKUP_DIR', '<REDACTED_TACC_SCRATCH>/hg_dual_ledger_backups_v2026_10_10')); folder.mkdir(parents=True, exist_ok=True)
    target = folder/(path.name+'.bak.'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.pre-url-c1')
    with path.open('rb') as s, target.open('xb') as d: shutil.copyfileobj(s, d)
    if digest(path) != digest(target): raise RuntimeError('Backup mismatch')
    return target

def main():
    from url_probe_validation import Verifier
    path = DATA/'analysis.sqlite3'
    with (DATA/'locks/analysis.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX); target = backup(path)
        db = sqlite3.connect(path.resolve().as_uri(), uri=True, timeout=120)  # uri=True needed for read-only ATTACH by URI
        try:
            db.executescript(SCHEMA)
            db.execute('ATTACH DATABASE ? AS ref', ((DATA/'sources/reference.sqlite3').resolve().as_uri()+'?mode=ro',))
            db.execute('CREATE TEMP VIEW threat_indicator AS SELECT * FROM ref.threat_indicator')
            db.execute('CREATE TEMP VIEW tranco_domain AS SELECT * FROM ref.tranco_domain')
            verifier = Verifier(db, DATA/'sources'); stats = {}
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for family, (ex_table, f_table) in FAMILIES.items():
                if ex_table not in tables or f_table not in tables: continue
                pending = db.execute(f'''SELECT e.root_node_id,e.seed_id,e.response FROM {ex_table} e WHERE e.status='complete' AND e.response IS NOT NULL
                    AND NOT EXISTS (SELECT 1 FROM url_reclassification_execution x WHERE x.policy_version=? AND x.family=? AND x.root_node_id=e.root_node_id AND x.seed_id=e.seed_id)''',
                    (POLICY, family)).fetchall()
                st = stats.setdefault(family, {'executions': 0, 'occurrences': 0, 'changed_occurrences': 0, 'frozen_mismatch': 0})
                for root, seed, response in pending:
                    t = datetime.now(timezone.utc).isoformat()
                    original = {r[0]: r[1:] for r in db.execute(f'SELECT occurrence,raw_url,start_offset,end_offset,verdict,evidence_json FROM {f_table} WHERE root_node_id=? AND seed_id=?', (root, seed))}
                    with db:
                        for n, (fi, raw, s, e, ctx, changed) in enumerate(classify(response)):
                            o = original.get(fi)
                            if not changed and o and tuple(o[:3]) == (raw, s, e): verdict, ev = o[3], o[4]
                            else:
                                if not changed: st['frozen_mismatch'] += 1
                                v = verifier.validate(raw, ctx); v['url_policy_version'] = POLICY; verdict, ev = v['verdict'], json.dumps(v)
                            db.execute('INSERT INTO url_reclassification VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                       (POLICY, family, root, seed, n, raw, s, e, ctx, fi, int(changed), verdict, ev, t))
                            st['occurrences'] += 1; st['changed_occurrences'] += int(changed)
                        db.execute('INSERT INTO url_reclassification_execution VALUES (?,?,?,?,?)', (POLICY, family, root, seed, t))
                    st['executions'] += 1
            with db: db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('url_reclassification_c1', json.dumps(dict(METHOD, last_run=datetime.now(timezone.utc).isoformat()))))
            print(json.dumps({'policy': POLICY, 'stats': stats, 'ledger_backup': str(target)}))
        finally: db.close()

if __name__ == '__main__': main()
