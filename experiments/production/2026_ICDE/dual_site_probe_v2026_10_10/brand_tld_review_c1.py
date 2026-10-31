"""Created: 2026-10-11
Version: url-brandtld-review-v2026.10.11-c1 (change ID v2026.10.11-claude-09)
Purpose: review overlay for URL findings whose c1 verdict is registrable_hallucinated (registrable domain
NXDOMAIN). NXDOMAIN alone does not establish public registrability; when the TLD is an ICANN
Specification 13 ("closed .brand") gTLD, the finding is marked 'requires_review_closed_brand_tld'.
Source: frozen ICANN gTLD report DATA/sources_c1/icann_gtlds_v2_<date>.json (+ .meta.json with sha256),
selected by HG_BRAND_TLD_SOURCE or the newest file. Spec 9 (closed generic) TLDs are not covered.
Adds only (originals and c1 rows unchanged):
  url_tld_review(policy_version, family, root_node_id, seed_id, occurrence, registrable_domain, tld,
                 specification13, terminated_or_removed, review_status, source_sha256, reviewed_at)
  views url_finding_reviewed_c1 / artifact_url_finding_reviewed_c1 with column reviewed_verdict:
     'registrable_hallucinated_requires_review' (closed brand TLD) | original c1 verdict otherwise
Incremental; holds DATA/locks/analysis.lock; ledger backed up to HG_LEDGER_BACKUP_DIR first. Compute node only.
"""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
from common import DATA, digest

POLICY = 'url-brandtld-review-v2026.10.11-c1'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS url_tld_review(policy_version TEXT,family TEXT,root_node_id TEXT,seed_id TEXT,occurrence INTEGER,registrable_domain TEXT,
  tld TEXT,specification13 INTEGER,terminated_or_removed INTEGER,review_status TEXT,source_sha256 TEXT,reviewed_at TEXT,
  PRIMARY KEY(policy_version,family,root_node_id,seed_id,occurrence));
'''
VIEW = '''
CREATE VIEW IF NOT EXISTS {name} AS SELECT f.*, r.tld AS tld, r.specification13 AS specification13, r.review_status AS review_status,
  CASE WHEN r.review_status='requires_review_closed_brand_tld' THEN 'registrable_hallucinated_requires_review' ELSE f.verdict END AS reviewed_verdict
  FROM {base} f LEFT JOIN url_tld_review r ON r.policy_version='url-brandtld-review-v2026.10.11-c1' AND r.family='{family}'
   AND r.root_node_id=f.root_node_id AND r.seed_id=f.seed_id AND r.occurrence=f.occurrence;
'''
FAMILIES = {'native': ('url_finding_effective_c1', 'url_finding_reviewed_c1'), 'artifact': ('artifact_url_finding_effective_c1', 'artifact_url_finding_reviewed_c1')}

def source():
    folder = DATA/'sources_c1'
    path = Path(os.environ['HG_BRAND_TLD_SOURCE']) if os.environ.get('HG_BRAND_TLD_SOURCE') else sorted(folder.glob('icann_gtlds_v2_*[0-9].json'))[-1]
    meta = json.loads(path.with_name(path.stem+'.meta.json').read_text())
    if digest(path) != meta['sha256']: raise RuntimeError('Brand TLD source checksum mismatch')
    brands = {}
    for g in json.loads(path.read_text())['gTLDs']:
        if g.get('specification13'):
            brands[g['gTLD'].lower()] = bool(g.get('contractTerminated')) or bool(g.get('removalDate'))
    return brands, meta

def backup(path):
    folder = Path(os.environ.get('HG_LEDGER_BACKUP_DIR', '<REDACTED_TACC_SCRATCH>/hg_dual_ledger_backups_v2026_10_10')); folder.mkdir(parents=True, exist_ok=True)
    target = folder/(path.name+'.bak.'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.pre-brandtld')
    with path.open('rb') as s, target.open('xb') as d: shutil.copyfileobj(s, d)
    if digest(path) != digest(target): raise RuntimeError('Backup mismatch')
    return target

def main():
    brands, meta = source(); path = DATA/'analysis.sqlite3'; stats = {}
    with (DATA/'locks/analysis.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX); target = backup(path)
        db = sqlite3.connect(path.resolve().as_uri(), uri=True, timeout=120)
        try:
            db.executescript(SCHEMA)
            names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            t = datetime.now(timezone.utc).isoformat()
            with db:
                for family, (base, view) in FAMILIES.items():
                    if base not in names: continue
                    db.executescript(VIEW.format(name=view, base=base, family=family))
                    st = stats.setdefault(family, {'new_rows': 0, 'closed_brand': 0})
                    for root, seed, occ, ev in db.execute(f'''SELECT f.root_node_id,f.seed_id,f.occurrence,f.evidence_json FROM {base} f
                        WHERE f.verdict='registrable_hallucinated' AND NOT EXISTS (SELECT 1 FROM url_tld_review r WHERE r.policy_version=? AND r.family=?
                        AND r.root_node_id=f.root_node_id AND r.seed_id=f.seed_id AND r.occurrence=f.occurrence)''', (POLICY, family)).fetchall():
                        dom = (json.loads(ev).get('registrable_domain') or '').lower(); tld = dom.rsplit('.', 1)[-1] if dom else ''
                        brand = tld in brands
                        status = 'requires_review_closed_brand_tld' if brand else 'nxdomain_availability_not_confirmed'
                        db.execute('INSERT INTO url_tld_review VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                                   (POLICY, family, root, seed, occ, dom, tld, int(brand), int(brands.get(tld, False)), status, meta['sha256'], t))
                        st['new_rows'] += 1; st['closed_brand'] += int(brand)
                db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('url_brandtld_review_c1', json.dumps({'policy_version': POLICY, 'source': meta, 'last_run': t,
                    'rule': 'registrable_hallucinated under an ICANN Specification 13 gTLD -> requires_review_closed_brand_tld; others remain availability_not_confirmed'})))
            print(json.dumps({'policy': POLICY, 'stats': stats, 'source_sha256': meta['sha256'], 'ledger_backup': str(target)}))
        finally: db.close()

if __name__ == '__main__': main()
