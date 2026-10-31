#!/usr/bin/env python3
"""Created 2026-10-27; v2026.10.27-unified-01.
Primary scope: at least one jointly completed verified prompt per adaptation pair.
Fresh read-only SQLite capture; unchanged accepted verifiers; no model inference.
Whole-bank restriction is sensitivity only. Publication uses one atomic directory pointer.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'table2_frozen_snapshot.json').is_file())
WORK = ROOT/'RQ2_analysis/v2026.10.27-01'
CODE_DIRECTORY=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import generate_graph_cohort_macros as common
import table2_unique_models as unique

VERSION='v2026.10.27-unified-01'
ENGINE=ROOT/'RQ3_analysis/v2026.10.16-03'
RESTRICTED=ROOT/'RQ3_analysis/v2026.10.16-05'
DATA=ROOT/'2026_ICDE/graphdb/dual_site_probe_v2026_10_10'
POLICIES=('strict','intermediate','declared','extended')
TAGS=dict(zip(POLICIES,('Strict','Intermediate','Declared','Extended')))
ADAPT={'finetune':'FT','adapter':'AD','quantized':'QT','merged':'Merge'}
CATEGORIES={'package_hallucination':('Pkg','Package hallucination'),
 'nonexistent_domain':('Nx','Registrable NXDOMAIN'),
 'malicious_url':('Mal','Exact malicious URL'),
 'restricted_namespace':('Restricted','Restricted namespace')}
STRATA=('AD','ndFT','dFT','QT','MG')
require,sha=common.require,common.sha


def stable(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def encoded(x):return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def pairkey(p,c):return hashlib.sha256((p+'\0'+c).encode()).hexdigest()
def rows(path):return common.csv_rows(path)
def js(path):return json.loads(Path(path).read_text())
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def log(text):print(text,flush=True)


def stratum(label,basis):
 if label=='finetune':return 'dFT' if basis=='default' else 'ndFT'
 return {'adapter':'AD','quantized':'QT','merged':'MG'}.get(label)


def summarize(comparisons):
 require(all(r['class_state'] in ('positive','negative','unknown') and r['instance_state'] in ('positive','negative','unknown') for r in comparisons),'Invalid oracle state')
 eligible=[r for r in comparisons if r['class_state']!='unknown' and r['instance_state']!='unknown']
 n=len(eligible);c=sum(r['class_state']=='positive' for r in eligible);i=sum(r['instance_state']=='positive' for r in eligible)
 require(all(r['instance_state']!='positive' or r['class_state']=='positive' for r in comparisons),'Instance positive without class positive')
 require(0<=i<=c<=n,'Invalid shared-denominator counts')
 return {'available':len(comparisons),'tests':n,'class_denominator':n,'instance_denominator':n,
  'class_rec':c,'instance_rec':i,'class_rate':c/n if n else None,'instance_rate':i/n if n else None,
  'upstreams':len({r['parent_id'] for r in eligible}),'derivatives':len({r['child_id'] for r in eligible}),
  'pairs':len({r['membership_id_sha256'] for r in eligible}),
  'unknown_excluded':len(comparisons)-n,
  'class_unknown':sum(r['class_state']=='unknown' for r in comparisons),
  'instance_unknown':sum(r['instance_state']=='unknown' for r in comparisons)}


def clustered(comparisons):
 """Conditional upstream-clustered percentile CI, not an iid/population CI."""
 import numpy as np
 groups=defaultdict(lambda:[0,0,0])
 for r in comparisons:
  if r['class_state']=='unknown' or r['instance_state']=='unknown':continue
  g=groups[r['parent_id']];g[0]+=1;g[1]+=r['class_state']=='positive';g[2]+=r['instance_state']=='positive'
 out={'method':'upstream-cluster percentile bootstrap; 2000 draws; seed 20261027; conditional descriptive cohort','clusters':len(groups)}
 if len(groups)<10:
  out.update(class_interval=None,instance_interval=None,reason='Fewer than ten contributing upstreams');return out
 a=np.array([groups[k] for k in sorted(groups)],dtype=float);rng=np.random.default_rng(20261027)
 draw=a[rng.integers(0,len(a),size=(2000,len(a)))].sum(axis=1)
 for j,metric in [(1,'class'),(2,'instance')]:
  positive=sum(g[j]>0 for g in a);negative=sum(g[0]-g[j]>0 for g in a)
  out[metric+'_interval']=list(map(float,np.percentile(draw[:,j]/draw[:,0],[2.5,97.5]))) if positive>=2 and negative>=2 else None
 return out


def build_capture(source=None,cutoff=None):
 locks=js(ENGINE/'FREEZE.json')['definitions']
 for name,digest in locks.items():require(sha(ENGINE/name)==digest,'Accepted verifier engine changed: '+name)
 if source:
  p=Path(source).resolve()
  if p.is_dir():p=p/'capture_manifest.json'
  context=js(p)
  require(sha(context['ledger_path'])==context['ledger_sha256'],'Immutable capture changed')
  require(context['engine_definitions']==locks,'Capture belongs to a different accepted verifier definition')
  for name,digest in context['selected_hashes'].items():require(sha(DATA/name)==digest,'Selection changed; cannot replay capture against different manifest')
  canonical=Path(context['ledger_path']).parent/'capture_manifest.json'
  require(canonical.is_file() and sha(canonical)==sha(p),'Replay manifest differs from its original immutable capture')
  return canonical,context
 cut=cutoff or datetime.now(timezone.utc).isoformat()
 from datetime import datetime as dt
 require(dt.fromisoformat(cut.replace('Z','+00:00')).tzinfo is not None,'Cutoff needs timezone')
 selection=js(DATA/'setup_report.json');expected={r['path']:r['sha256'] for r in selection['frozen_inputs']}
 selected_hashes={}
 for name in ('manifest/memberships.csv','manifest/models.jsonl','manifest/roots.csv'):
  digest=sha(DATA/name);require(digest==expected[name],'Unvalidated active selection: '+name);selected_hashes[name]=digest
 folder=WORK/'captures'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
 ledger=folder/'analysis.sqlite3'
 log('Capturing the current committed ledger read-only; no inference or verification jobs...')
 src=sqlite3.connect((DATA/'analysis.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,timeout=30)
 dst=sqlite3.connect(ledger)
 try:src.backup(dst,pages=1024)
 finally:src.close();dst.close()
 context={'version':VERSION,'cutoff':cut,'ledger_path':str(ledger.resolve()),'ledger_sha256':sha(ledger),
  'source_ledger':str((DATA/'analysis.sqlite3').resolve()),'selected_hashes':selected_hashes,
  'selection_version':selection['version'],'engine_definitions':locks,
  'capture_method':'SQLite backup API from mode=ro; committed coherent snapshot including WAL'}
 context['source_snapshot_id']='execution-'+hashlib.sha256(stable(context).encode()).hexdigest()[:16]
 with (folder/'capture_manifest.json').open('x') as f:json.dump(context,f,indent=2,sort_keys=True);f.write('\n')
 return folder/'capture_manifest.json',context


def ingest(context):
 engine=load_module('vulchain_frozen_response_engine',ENGINE/'run_rq3.py')
 restricted=load_module('vulchain_frozen_restricted',RESTRICTED/'restricted_namespace.py')
 protocol=js(ENGINE/'protocol.json');pin=js(ENGINE/'input_pin.json');frozen=Path(pin['source_snapshot'])
 cut=engine.timevalue(context['cutoff'])
 log('Validating revisions, original execution, both c1 markers, feed evidence and oracle timestamps...')
 data=engine.load(Path(context['ledger_path']),frozen,cut,protocol,pin)
 require(data['provenance']['ledger_sha256']==context['ledger_sha256'],'Capture identity mismatch')
 # The old frozen snapshot is the validated evidence/selection contract, not a current count.
 selected=[tuple((r['root_model'],r['child_model'],r['category'])) for r in rows(DATA/'manifest/memberships.csv')]
 evidence=[(r['parent_id'],r['child_id'],r['adaptation_label']) for r in data['members']]
 require(set(selected)==set(evidence) and len(selected)==len(evidence),'Current selected relationships lack matching provenance evidence export')
 selected_models=[json.loads(x) for x in (DATA/'manifest/models.jsonl').read_text().splitlines()]
 require({m['model_id'] for m in selected_models}=={x for p,c,k in evidence for x in (p,c)},'Selected model union mismatch')
 source=Path(context['ledger_path']).parent/'restricted_input'
 if not source.exists():
  source.mkdir()
  with (source/'rq3_response_facts.jsonl').open('x') as f:
   for mid,seed in sorted(data['done']):
    f.write(stable({'category':'package_hallucination','model_id':mid,'seed_id':seed,'raw_prompt_sha256':data['prompts'][seed]})+'\n')
 result={'provenance':data['provenance'],'coverage':data['coverage'],'protocol':protocol}
 res=restricted.calculate(source,result,sha,engine)
 data['states']['restricted_namespace']=res['facts']
 require(all(set(states)==data['done'] for states in data['states'].values()),'Category completion identities differ')
 return engine,restricted,protocol,frozen,data,res


def cohort_and_comparisons(engine,data):
 done_by=defaultdict(set)
 for mid,seed in data['done']:done_by[mid].add(seed)
 positive={cat:defaultdict(set) for cat in CATEGORIES}
 for cat in CATEGORIES:
  for (mid,seed),s in data['states'][cat].items():
   if s['confirmed']:positive[cat][mid].add(seed)
 pairs={};all_members={};joint={};whole=set();pair_audit=[]
 for m in data['members']:
  key=m['membership_id_sha256'];p,c,label=m['parent_id'],m['child_id'],m['adaptation_label']
  require(key==pairkey(p,c) and key not in all_members,'Duplicate/invalid selected pair')
  all_members[key]=m
  common_seeds=done_by[p]&done_by[c]
  allowed=label in ADAPT
  declared=m['parent_identity_evidence']=='declared';basis=m['adaptation_evidence_category']
  expected=[allowed and declared and basis=='explicit',allowed and declared and basis in ('explicit','tag_implied','field_implied'),allowed and declared,allowed and (declared or m['parent_identity_evidence']=='inferred')]
  require([m['in_'+policy]=='1' for policy in POLICIES]==expected,'Original policy flags disagree with exported evidence basis')
  if allowed and common_seeds:
   pairs[key]=m;joint[key]=common_seeds
   if p in data['complete'] and c in data['complete']:whole.add(key)
  info={'membership_id_sha256':key,'parent_id':p,'child_id':c,'adaptation_label':label,
   'selected':True,'adaptation_eligible':allowed,'joint_completed_prompts':len(common_seeds),
   'parent_completed_prompts':len(done_by[p]),'child_completed_prompts':len(done_by[c]),
   'parent_whole_bank_complete':p in data['complete'],'child_whole_bank_complete':c in data['complete'],
   'included_prompt_scope':key in pairs,'included_whole_bank_scope':key in whole,
   'exclusion_reason':'included' if key in pairs else 'non_adaptation_relationship' if not allowed else 'no_joint_original_verified_both_c_one_prompt'}
  for cat,(code,_) in CATEGORIES.items():info[code+'_upstream_positive_prompts']=len(positive[cat][p])
  pair_audit.append(info)
 require(bool(pairs),'No jointly verified adaptation relationship')
 models={x for m in pairs.values() for x in (m['parent_id'],m['child_id'])}
 unique_stats=unique.summarize([(m['parent_id'],m['child_id'],m['adaptation_label']) for m in pairs.values()])
 comparisons=[];seen=set()
 log('Building one four-category pair-prompt comparison ledger, including partial models...')
 for key,m in sorted(pairs.items()):
  p,c=m['parent_id'],m['child_id'];group=stratum(m['adaptation_label'],m['adaptation_evidence_category'])
  require(group in STRATA,'Unmapped adaptation stratum')
  flags=[m['in_'+policy]=='1' for policy in POLICIES]
  require(flags==sorted(flags) and flags[-1],'Evidence admission not nested/adaptation eligible')
  for cat in CATEGORIES:
   for seed in sorted(positive[cat][p]&joint[key]):
    ps=data['states'][cat][p,seed];cs=data['states'][cat][c,seed]
    cls,inst=engine.outcomes(ps,cs)
    identity=key,cat,data['prompts'][seed]
    require(identity not in seen,'Duplicate pair/category/prompt comparison');seen.add(identity)
    require(ps['confirmed'] and (p,seed) in data['done'] and (c,seed) in data['done'],'Eligibility proof missing')
    comparisons.append({'membership_id_sha256':key,'parent_id':p,'child_id':c,'seed_id':seed,
     'raw_prompt_sha256':data['prompts'][seed],'category':cat,'adaptation_label':m['adaptation_label'],
     'adaptation_basis':m['adaptation_evidence_category'],'stratum':group,'class_state':cls,'instance_state':inst,
     'parent_artifact_sha256':sorted(ps['confirmed']),'child_artifact_sha256':sorted(cs['confirmed']),
     'unresolved_scopes':sorted(cs['unresolved']),'eligible':cls!='unknown' and inst!='unknown',
     **{'in_'+policy:flags[i] for i,policy in enumerate(POLICIES)},'whole_bank_pair':key in whole})
 stats={key:{cat:summarize([r for r in comparisons if r['membership_id_sha256']==key and r['category']==cat]) for cat in CATEGORIES} for key in pairs}
 for item in pair_audit:
  for cat,(code,_) in CATEGORIES.items():
   x=stats.get(item['membership_id_sha256'],{}).get(cat,{})
   item[code+'_eligible_comparisons']=x.get('tests',0);item[code+'_available_comparisons']=x.get('available',0)
 return pairs,models,whole,unique_stats,comparisons,done_by,positive,pair_audit


def aggregate_all(pairs,whole,comparisons):
 policies={};added={};coverage={};previous=set()
 for policy in POLICIES:
  ids={k for k,m in pairs.items() if m['in_'+policy]=='1'}
  require(previous<=ids,'Non-nested policy pairs');policies[policy]=ids;added[policy]=ids-previous
  def cov(s):
   rr=[pairs[k] for k in s]
   return {'pairs':len(s),'records':len(rr),'bases':len({m['parent_id'] for m in rr}),
    'derivatives':len({m['child_id'] for m in rr}),'coverage_pct':100*len(s)/len(pairs),
    'adaptation_records':dict(Counter(m['adaptation_label'] for m in rr)),
    'evidence_records':dict(Counter(m['adaptation_evidence_category'] for m in rr)),
    'adaptation_x_evidence':dict(Counter(m['adaptation_label']+'|'+m['adaptation_evidence_category'] for m in rr)),
    'upstreams_losing_all_relationships':sorted({m['parent_id'] for m in pairs.values()}-{m['parent_id'] for m in rr})}
  coverage[policy]={'cumulative':cov(ids),'added':cov(added[policy])};previous=ids
 rq2={p:{s:{cat:summarize([r for r in comparisons if r['membership_id_sha256'] in ids and r['category']==cat]) for cat in CATEGORIES}
   for s,ids in [('cumulative',policies[p]),('added',added[p])]} for p in POLICIES}
 rq3=rq2['declared']['cumulative'];rq4={};sensitivity={}
 for cat in CATEGORIES:
  admitted=[r for r in comparisons if r['category']==cat and r['in_declared']]
  rq4[cat]={}
  for group in list(STRATA)+['Overall']:
   r=[r for r in admitted if group=='Overall' or r['stratum']==group]
   rq4[cat][group]={**summarize(r),'uncertainty':clustered(r)}
  for metric in ('available','tests','class_rec','instance_rec','unknown_excluded'):
   require(sum(rq4[cat][g][metric] for g in STRATA)==rq3[cat][metric],'RQ4 strata do not partition RQ3 overall: '+metric)
   require(sum(rq2[p]['added'][cat][metric] for p in POLICIES)==rq2['extended']['cumulative'][cat][metric],'Evidence increments do not partition Extended')
  sensitivity[cat]={'prompt_level':rq3[cat], 'whole_bank':summarize([r for r in admitted if r['membership_id_sha256'] in whole])}
  for metric in ('tests','class_rec','instance_rec'):
   require(sensitivity[cat]['prompt_level'][metric]>=sensitivity[cat]['whole_bank'][metric],'Whole-bank sensitivity is not a subset of prompt-level scope')
 # Independent SQL validates EVERY policy, category and adaptation cell from this ledger.
 db=sqlite3.connect(':memory:');db.execute('CREATE TABLE t(pair TEXT,cat TEXT,stratum TEXT,up TEXT,child TEXT,c TEXT,i TEXT,s INTEGER,n INTEGER,d INTEGER,e INTEGER)')
 db.executemany('INSERT INTO t VALUES (?,?,?,?,?,?,?,?,?,?,?)',[(r['membership_id_sha256'],r['category'],r['stratum'],r['parent_id'],r['child_id'],r['class_state'],r['instance_state'],*[int(r['in_'+p]) for p in POLICIES]) for r in comparisons])
 select="SELECT count(*),coalesce(sum(c='positive'),0),coalesce(sum(i='positive'),0),count(DISTINCT up),count(DISTINCT child),count(DISTINCT pair) FROM t WHERE c!='unknown' AND i!='unknown' AND "
 for policy,col in zip(POLICIES,('s','n','d','e')):
  for cat in CATEGORIES:
   got=db.execute(select+col+'=1 AND cat=?',(cat,)).fetchone();r=rq2[policy]['cumulative'][cat]
   require(got==tuple(r[k] for k in ('tests','class_rec','instance_rec','upstreams','derivatives','pairs')),'Independent SQL RQ2 mismatch')
 for cat in CATEGORIES:
  for group in list(STRATA)+['Overall']:
   query=select+'d=1 AND cat=?';args=[cat]
   if group!='Overall':query+=' AND stratum=?';args.append(group)
   got=db.execute(query,args).fetchone();r=rq4[cat][group]
   require(got==tuple(r[k] for k in ('tests','class_rec','instance_rec','upstreams','derivatives','pairs')),'Independent SQL RQ4 mismatch')
 db.close()
 return coverage,rq2,rq3,rq4,sensitivity


def collect_occurrences(engine,restricted,protocol,frozen,data,models,context):
 """Original accepted row-level predicate; all completed responses of Table II models.
 Occurrences are finding rows, NOT relationship-weighted recurrence tests.
 """
 db=sqlite3.connect(Path(context['ledger_path']).as_uri()+'?mode=ro',uri=True)
 cut=engine.timevalue(context['cutoff']);meta={k:json.loads(v) for k,v in db.execute('SELECT * FROM metadata')}
 brandmeta=meta['url_brandtld_review_c1']['source'];brandfile=frozen/'sources_c1'/brandmeta['file']
 require(sha(brandfile)==brandmeta['sha256'],'Restricted taxonomy source changed')
 brands={g['gTLD'].lower() for g in js(brandfile)['gTLDs'] if g.get('specification13')}
 reserved={r['Name'].split()[0].rstrip('.').lower() for r in rows(frozen/'sources/iana_special_use.csv')}|{'localhost','local','invalid','test','example','onion','example.com','example.net','example.org','home.arpa'}
 ids=dict(db.execute('SELECT root_node_id,root_model FROM model'));reviews={}
 for root,seed,occ,status,spec,at in db.execute("SELECT root_node_id,seed_id,occurrence,review_status,specification13,reviewed_at FROM url_tld_review WHERE family='native' AND policy_version=?",(protocol['brand_policy'],)):
  reviews[root,seed,occ]={'status':status,'spec13':spec,'at':at}
 counts=Counter();tokens=defaultdict(set);by_response=defaultdict(set);safe=[]
 def add(cat,mid,seed,t):
  counts[cat]+=1;tokens[cat].add(t);by_response[cat,mid,seed].add(t)
  safe.append({'category':cat,'model_id':mid,'seed_id':seed,'artifact_sha256':t})
 for root,seed,verdict,raw,status in db.execute('SELECT root_node_id,seed_id,verdict,evidence_json,c1_status FROM package_finding_effective_c1'):
  mid=ids[root]
  if mid not in models or (mid,seed) not in data['done'] or status!='retained':continue
  s=engine.response_states([(verdict,json.loads(raw),True)],[],cut,brands,reserved)['package_hallucination']
  for t in s['confirmed']:add('package_hallucination',mid,seed,t)
 for root,seed,occ,verdict,raw in db.execute('SELECT root_node_id,seed_id,occurrence,verdict,evidence_json FROM url_finding_effective_c1'):
  mid=ids[root]
  if mid not in models or (mid,seed) not in data['done']:continue
  evidence=json.loads(raw);review=reviews.get((root,seed,occ));status=review['status'] if review and engine.before(review['at'],cut) else None
  reviewed='registrable_hallucinated_requires_review' if status=='requires_review_closed_brand_tld' else verdict
  states=engine.response_states([],[(reviewed,evidence,status)],cut,brands,reserved)
  for cat in ('nonexistent_domain','malicious_url'):
   for t in states[cat]['confirmed']:add(cat,mid,seed,t)
  token,_,_=restricted.classify(verdict,evidence,review,brands,reserved,cut,engine)
  if token:add('restricted_namespace',mid,seed,token)
 db.close()
 for cat in CATEGORIES:
  for mid,seed in data['done']:
   if mid in models:require(by_response.get((cat,mid,seed),set())==set(data['states'][cat][mid,seed]['confirmed']),'Finding-row qualification differs from canonical response facts: '+cat)
 return {cat:{'occurrences':counts[cat],'distinct_artifacts':len(tokens[cat]),
  'models_with_finding':len({r['model_id'] for r in safe if r['category']==cat}),
  'scope':'qualifying finding rows over all original-verified/both-c1 responses of unique Table II prompt-paired models; not pair/prompt weighted'} for cat in CATEGORIES},safe


def audit_models(context,data,pairs,models,comparisons,done_by,positive,pair_audit):
 db=sqlite3.connect(Path(context['ledger_path']).as_uri()+'?mode=ro',uri=True);cut=context['cutoff']
 ids={root:(mid,rev) for root,mid,rev in db.execute('SELECT root_node_id,root_model,revision FROM model')}
 generated=Counter();verified=Counter();failures=Counter()
 status_hist=defaultdict(Counter)
 for root,status,at,started,has in db.execute('SELECT root_node_id,status,completed_at,started_at,response IS NOT NULL FROM execution'):
  moment=at or started
  if not moment or datetime.fromisoformat(moment.replace('Z','+00:00'))>datetime.fromisoformat(cut.replace('Z','+00:00')):continue
  mid=ids[root][0]
  status_hist[mid][status]+=1
  if has:generated[mid]+=1
  if status=='complete':verified[mid]+=1
  elif status in ('failed','error'):failures[mid]+=1
 db.close()
 rawparents={m['parent_id'] for m in data['members']};rawchildren={m['child_id'] for m in data['members']}
 eligible_models={x for m in data['members'] if m['adaptation_label'] in ADAPT for x in (m['parent_id'],m['child_id'])}
 static={r['model_id']:r['status'] for r in rows(ROOT/'2026_ICDE/graphdb/expanded_preflight_all_4887_v2026_10_10/model_preflight.csv')}
 contrib=defaultdict(Counter)
 for r in comparisons:
  if r['eligible'] and r['in_declared']:
   for mid in {r['parent_id'],r['child_id']}:contrib[mid][r['category']]+=1
 model_rows=[]
 for mid,rev in sorted(ids.values()):
  row={'model_id':mid,'revision':rev,'selected':True,'upstream':mid in rawparents,'derivative':mid in rawchildren,
   'adaptation_eligible':mid in eligible_models,'static_status':static.get(mid,'missing'),
   'generated_prompts':generated[mid],'original_verified_prompts':verified[mid],'verified_both_c_one_prompts':len(done_by[mid]),
   'whole_bank_complete':mid in data['complete'],'execution_failures':failures[mid],'execution_status_counts':dict(status_hist[mid]),
   'included_prompt_scope':mid in models,
   'exclusion_reason':'included' if mid in models else 'non_adaptation_only' if mid not in eligible_models else 'no_jointly_verified_prompt_with_eligible_partner'}
  for cat,(code,_) in CATEGORIES.items():row[code+'_upstream_positive_prompts']=len(positive[cat][mid]);row[code+'_eligible_comparisons']=contrib[mid][cat]
  model_rows.append(row)
 return model_rows


def historical_regression():
 old=WORK/'snapshots/v2026.10.27-rq2-02-c814a2aa5cc2a0e9';manifest=js(old/'OUTPUT_MANIFEST.json')
 for name in ('rq2_validation.json','rq2_comparisons.jsonl'):
  require(sha(old/name)==manifest['sha256'][name],'Archived checkpoint changed')
 q=js(old/'rq2_validation.json')
 # Original checkpoint source is identified by hash-listed rq3 comparison file, never mtime.
 raw_path=next(Path(p) for p in q['sources'] if p.endswith('/rq3_three_state_triples.jsonl'))
 require(sha(raw_path)==q['sources'][str(raw_path)],'Archived raw comparison source changed')
 b=[]
 with (old/'rq2_comparisons.jsonl').open() as f:b=[json.loads(x) for x in f]
 a=[]
 with raw_path.open() as f:
  for line in f:
   r=json.loads(line)
   if r['policy']=='declared':a.append(r)
 declared=set()
 # The archived validation's exact admitted membership set is recoverable from its
 # canonical rows; use each row's original admitted policy memberships from the hash-pinned lineage.
 evidence_path=next(Path(p) for p in q['sources'] if p.endswith('/lineage/cohort_memberships.csv'))
 require(sha(evidence_path)==q['sources'][str(evidence_path)],'Historical lineage source changed')
 declared={r['membership_id_sha256'] for r in rows(evidence_path) if r['in_declared']=='1'}
 expected={('b','package_hallucination'):(5424,1768,1366),('a','package_hallucination'):(5427,1769,1366),('b','nonexistent_domain'):(4757,1891,1382),('a','nonexistent_domain'):(4757,1891,1382)}
 regression={};outside=[];bident={(r['membership_id_sha256'],r['category'],r['raw_prompt_sha256']) for r in b}
 for scope,records in [('a',a),('b',[r for r in b if r['membership_id_sha256'] in declared])]:
  for cat in ('package_hallucination','nonexistent_domain'):
   result=summarize([r for r in records if r['category']==cat]);got=tuple(result[k] for k in ('tests','class_rec','instance_rec'))
   require(got==expected[scope,cat],'Archived shared-denominator regression failed')
   regression[scope+'/'+cat]=result
 for r in a:
  ident=r['membership_id_sha256'],r['category'],r['raw_prompt_sha256']
  if r['category']=='package_hallucination' and ident not in bident:outside.append({k:r[k] for k in ('parent_id','child_id','seed_id','raw_prompt_sha256','class_state','instance_state')})
 require(len(outside)==3 and Counter((r['class_state'],r['instance_state']) for r in outside)=={('negative','negative'):2,('positive','negative'):1},'Three historical comparisons not reproduced')
 # Independently audit the old five whole-bank-complete upstream exclusions and
 # the partial derivative. Do not infer their prompt-level contribution from counts.
 factpath=raw_path.parent/'rq3_response_facts.jsonl'
 factmanifest=js(raw_path.parent/'OUTPUT_MANIFEST.json')['files']
 require(sha(factpath)==factmanifest[factpath.name],'Historical response facts changed')
 old_done=defaultdict(set);old_positive=defaultdict(lambda:defaultdict(set))
 with factpath.open() as f:
  for line in f:
   r=json.loads(line)
   if r['category']=='package_hallucination':old_done[r['model_id']].add(r['seed_id'])
   if r['confirmed_artifact_namespaces']:old_positive[r['category']][r['model_id']].add(r['seed_id'])
 respath=WORK.parent.parent/'RQ3_analysis/v2026.10.16-05/snapshots'/q['tableii_rq3_snapshot']/'rq3_restricted_occurrences.jsonl'
 resmanifest=js(respath.parent/'OUTPUT_MANIFEST.json')['files'];require(sha(respath)==resmanifest[respath.name],'Historical restricted observations changed')
 with respath.open() as f:
  for line in f:
   r=json.loads(line);old_positive['restricted_namespace'][r['model_id']].add(r['seed_id'])
 old_res= respath.parent/'rq3_restricted_triples.jsonl'
 require(sha(old_res)==resmanifest[old_res.name],'Historical restricted comparison source changed')
 with old_res.open() as f:
  old_all=a+[r for r in map(json.loads,f) if r['policy']=='declared']
 old_members=rows(evidence_path);old_ledger=Path(js(raw_path.parent/'rq3_results.json')['provenance']['ledger_path'])
 require(sha(old_ledger)==q['sources'][str(old_ledger)],'Historical execution ledger changed')
 db=sqlite3.connect(old_ledger.as_uri()+'?mode=ro',uri=True);oldids=dict(db.execute('SELECT root_node_id,root_model FROM model'))
 gen=Counter();original=Counter()
 for root,status,has in db.execute('SELECT root_node_id,status,response IS NOT NULL FROM execution'):
  if has:gen[oldids[root]]+=1
  if status=='complete':original[oldids[root]]+=1
 old_bank=db.execute('SELECT count(*) FROM prompt').fetchone()[0];db.close()
 old_excluded=set(q['population_reconciliation']['completed_models_outside_tableii'])
 affected=old_excluded|{m['child_id'] for m in old_members if m['parent_id'] in old_excluded}|{r['parent_id'] for r in outside}|{r['child_id'] for r in outside}
 old_models=[];old_pairs=[]
 for mid in sorted(affected):
  record={'model_id':mid,'selected':True,'generated_prompts':gen[mid],'original_verified_prompts':original[mid],
   'verified_both_c_one_prompts':len(old_done[mid]),'whole_bank_complete':len(old_done[mid])==old_bank,'previously_excluded_complete_upstream':mid in old_excluded}
  for cat,(code,_) in CATEGORIES.items():record[code+'_upstream_positive_prompts']=len(old_positive[cat][mid])
  old_models.append(record)
 for m in old_members:
  if m['parent_id'] not in old_excluded and not any(m['parent_id']==r['parent_id'] and m['child_id']==r['child_id'] for r in outside):continue
  record={'parent_id':m['parent_id'],'child_id':m['child_id'],'selected':True,'adaptation_label':m['adaptation_label'],
   'joint_verified_prompts':len(old_done[m['parent_id']]&old_done[m['child_id']]),
   'parent_complete_prompts':len(old_done[m['parent_id']]),'child_complete_prompts':len(old_done[m['child_id']])}
  record['parent_generated_prompts']=gen[m['parent_id']];record['child_generated_prompts']=gen[m['child_id']]
  record['parent_original_verified_prompts']=original[m['parent_id']];record['child_original_verified_prompts']=original[m['child_id']]
  for cat,(code,_) in CATEGORIES.items():record[code+'_eligible_tests']=summarize([r for r in old_all if r['membership_id_sha256']==m['membership_id_sha256'] and r['category']==cat])['tests']
  old_pairs.append(record)
 old_omitted=[r for r in old_pairs if r['parent_id'] in old_excluded and r['adaptation_label'] in ADAPT]
 omitted_joint=sum(r['joint_verified_prompts'] for r in old_omitted)
 omitted_tests={code:sum(r[code+'_eligible_tests'] for r in old_omitted) for code,_ in CATEGORIES.values()}
 return {'status':'PASS historical checkpoints only; never current hardcoded counts','metrics':regression,'three_comparisons':outside,
  'previous_upstreams_excluded':q['population_reconciliation']['completed_models_outside_tableii'],
  'previous_models_audit':old_models,'previous_relationships_audit':old_pairs,
  'omitted_upstreams_joint_verified_prompts':omitted_joint,'omitted_upstreams_tests':omitted_tests,
  'explanation':'The old five omitted whole-bank-complete upstreams contribute '+str(omitted_joint)+' jointly verified adaptation-child prompts and '+json.dumps(omitted_tests,sort_keys=True)+' eligible recurrence tests in the archived snapshot. The three extra package tests arise from a DIFFERENT upstream already in the old 29-base cohort and its partial derivative.'}


def characteristics(pairs,comparisons):
 folder=Path('<REDACTED_HOME>/icde_rq4_export');manifest={}
 for line in (folder/'MANIFEST.sha256').read_text().splitlines():
  h,name=line.split(maxsplit=1);manifest[name.lstrip('*')]=h
 for name in ('base_graph_stats.csv','base_profiles.csv','cohort_tiers.csv'):
  require(sha(folder/name)==manifest[name],'RQ4 graph metadata checksum mismatch: '+name)
 stats={r['base_id']:r for r in rows(folder/'base_graph_stats.csv')}
 profiles={r['model_id']:r for r in rows(folder/'base_profiles.csv')}
 results=[]
 for cat in CATEGORIES:
  rr=[r for r in comparisons if r['category']==cat and r['in_declared']]
  for characteristic in ('model_type','lineage_breadth'):
   grouped=defaultdict(list)
   for r in rr:
    s=stats.get(r['parent_id']);require(s is not None,'Missing upstream metadata')
    if characteristic=='model_type':group=s['model_type'] or 'unknown'
    else:
     n=int(s['onehop_children_declared']);group='up to ten' if n<=10 else 'eleven to one hundred' if n<=100 else 'one hundred one to one thousand' if n<=1000 else 'over one thousand'
    grouped[group].append(r)
   for group,x in sorted(grouped.items()):results.append({'category':cat,'characteristic':characteristic,'group':group,**summarize(x)})
 return {'status':'descriptive strata from hash-verified model_type and declared one-hop graph breadth; no causal adjustment',
  'parameter_count_known':sum(bool(r['parameter_count']) for r in profiles.values()),
  'size_limitation':'Parameter counts unavailable in source profiles; storage bytes/size buckets are not treated as verified parameter counts.',
  'results':results,'sources':{str(folder/n):manifest[n] for n in ('base_graph_stats.csv','base_profiles.csv','cohort_tiers.csv')}}


def rq5_audit(models,comparisons,wholemodels):
 folder=Path('<REDACTED_HOME>/icde_rq5_export');manifest={}
 for line in (folder/'sha256_manifest.txt').read_text().splitlines():
  parts=line.split(maxsplit=1)
  if len(parts)==2:manifest[parts[1].lstrip('*')]=parts[0]
 source_files={};counts={}
 for name,target in [('model_github_edges.csv','github_repo_key'),('model_space_edges.csv','space_id')]:
  p=folder/name
  expected=manifest.get(name) or next((v for k,v in manifest.items() if k.endswith('/'+name)),None)
  require(expected and sha(p)==expected,'RQ5 frozen graph export mismatch: '+name);source_files[str(p)]=expected
  graphrows=rows(p)
  for label,pop in [('prompt_paired',models),('whole_bank',wholemodels),('recurrence_positive_derivatives',{r['child_id'] for r in comparisons if r['eligible'] and r['in_declared'] and r['class_state']=='positive'})]:
   rr=[r for r in graphrows if r['model_id'] in pop]
   counts[name+'/'+label]={'association_records':len(rr),'model_ids':len({r['model_id'] for r in rr}),'target_ids':len({r[target] for r in rr})}
 existing=Path('<REDACTED_HOME>/icde_rq5/out/rq5_results.json')
 old=js(existing)
 return {'scope':'independent frozen graph-association inventory joined to new model-ID sets; NOT recomputed RQ5 security/causal results',
  'association_counts':counts,'existing_result_path':str(existing),'existing_result_sha256':sha(existing),
  'existing_result_top_level_keys':sorted(old),'sources':source_files,
  'revision':'Do not replace existing RQ5 denominators. Its behavioral results need a separately scoped recomputation; original RQ5 files were not modified.'}


def run(source=None,cutoff=None):
 manifest_path,context=build_capture(source,cutoff)
 engine,restricted,protocol,frozen,data,res=ingest(context)
 pairs,models,whole,unique_stats,comparisons,done_by,positive,pair_audit=cohort_and_comparisons(engine,data)
 coverage,rq2,rq3,rq4,sensitivity=aggregate_all(pairs,whole,comparisons)
 log('Requalifying all four occurrence categories from original verifier rows...')
 occurrences,safe_occ=collect_occurrences(engine,restricted,protocol,frozen,data,models,context)
 model_audit=audit_models(context,data,pairs,models,comparisons,done_by,positive,pair_audit)
 regression=historical_regression();character=characteristics(pairs,comparisons)
 wholemodels={x for k in whole for x in (pairs[k]['parent_id'],pairs[k]['child_id'])}
 downstream=rq5_audit(models,comparisons,wholemodels)
 frozen_counts=unique.load_baseline()
 import numpy,platform
 from importlib.metadata import version as package_version
 input_hashes={str(unique.BASELINE):sha(unique.BASELINE),str(ROOT/'graph_cohort_numbers.tex'):sha(ROOT/'graph_cohort_numbers.tex'),
  str(WORK/'rq2_graph_frozen_historical.json'):sha(WORK/'rq2_graph_frozen_historical.json'),
  str(WORK/'rq2_local_graph_structure.json'):sha(WORK/'rq2_local_graph_structure.json'),
  **character['sources'],**downstream['sources']}
 for name,digest in context['selected_hashes'].items():require(sha(DATA/name)==digest,'Selected manifest changed during analysis')
 snapshot={'version':VERSION,'primary_scope':'Option A: prompt-level; at least one common original-verified/both-c1 prompt per adaptation pair',
  'primary_policy':'declared','source_snapshot_id':context['source_snapshot_id'],'cutoff':context['cutoff'],
  'capture_manifest':str(manifest_path.resolve()),'capture_manifest_sha256':sha(manifest_path),
  'ledger_sha256':context['ledger_sha256'],'selection_hashes':context['selected_hashes'],
  'input_source_hashes':input_hashes,'verification_provenance':data['provenance'],'verification_protocol':protocol,
  'software':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'numpy':numpy.__version__,'matplotlib':package_version('matplotlib')},
  'analysis_protocol':{'primary_scope':'prompt_level','minimum_joint_completed_verified_prompts':1,'primary_policy':'declared','whole_bank_is_sensitivity':True,
    'occurrence_unit':'qualifying finding row over verified responses of inventory models','recurrence_unit':'unique pair/category/raw-prompt hash',
    'bootstrap_resamples':2000,'bootstrap_seed':20261027,'minimum_upstream_clusters_for_interval':10,
    'minimum_positive_and_negative_families_for_interval':2,'empty_rate':'N/A','rates_display_decimals':2},
  'cohort':unique_stats,'whole_bank_pair_scope':unique.summarize([(pairs[k]['parent_id'],pairs[k]['child_id'],pairs[k]['adaptation_label']) for k in whole]) if whole else None,
  'execution_coverage':data['coverage'],'model_role_counts':{'whole_bank_upstreams':len(data['complete']&{m['parent_id'] for m in data['members']}),'whole_bank_derivatives':len(data['complete']&{m['child_id'] for m in data['members']})},
  'selected_model_ids':len(model_audit),'selected_adaptation_pairs':sum(m['adaptation_label'] in ADAPT for m in data['members']),
  'cohort_verified_responses':sum(mid in models for mid,seed in data['done']),
  'coverage':coverage,'rq2':rq2,'rq3':rq3,'rq4':rq4,'scope_sensitivity':sensitivity,'occurrences':occurrences,
  'historical_regression':regression,'upstream_characteristics':character,'rq5_scope_audit':downstream,
  'restricted_taxonomy':'Original frozen ICANN Specification-13 closed-brand namespace + qualifying NXDOMAIN review only; excludes invalid/reserved/private-suffix anomalies. Diagnostic, not exploitability.',
  'restricted_indicator_audit':{'class_positive_instance_negative':sum(r['eligible'] and r['in_declared'] and r['category']=='restricted_namespace' and r['class_state']=='positive' and r['instance_state']=='negative' for r in comparisons),'interpretation':'Indicators have different definitions; equality of observed numerators is not a detector identity.'},
  'occurrence_scope':'Finding rows over verification-complete responses of Table II model IDs; not parent-positive or relationship weighted.',
  'frozen_graph_reference':js(WORK/'rq2_graph_frozen_historical.json'),
  'local_graph_structure':js(WORK/'rq2_local_graph_structure.json'),
  'frozen_tableii_baseline_sha256':sha(unique.BASELINE),
  'code':{'unified_analysis.py':sha(__file__),'unified_exports.py':sha(CODE_DIRECTORY/'unified_exports.py'),
   'generate_rq2_analysis.py':sha(CODE_DIRECTORY/'generate_rq2_analysis.py'),
   'frozen_response_engine.py':sha(ENGINE/'run_rq3.py'),'frozen_restricted_namespace.py':sha(RESTRICTED/'restricted_namespace.py')},
  'checks':['PASS current selected manifest / frozen lineage identity / source revisions / prompt hashes',
   'PASS no converted or new-version records before cohort IDs','PASS at least one jointly verified same prompt per admitted inventory pair',
   'PASS shared determinate class/instance eligibility; verified negatives retained; positive precedence unchanged',
   'PASS instance count/rate <= class count/rate; parent-positive proof; no duplicate comparisons',
   'PASS independent SQL for every policy/category/adaptation cell','PASS RQ4 strata sum to RQ3 Overall',
   'PASS all new evidence strata partition Extended','PASS finding-row unions reproduce all four canonical response facts',
   'PASS archived regression and three safe prompt-level discrepancies','PASS immutable graph baselines and policy references retained'],
  'limitations':['No causal inference or model-prevalence interpretation','Full graph-wide provenance-policy evidence still unavailable; historical references remain qualified','No verified parameter counts; size buckets are not parameter estimates','RQ5 security results not changed without a dedicated recomputation','Accepted c1 package-context and generic URL-placeholder limitations remain','Upstream-cluster intervals may retain cross-family dependence through shared derivatives']}
 sourceid=hashlib.sha256(stable({'capture':context,'code':snapshot['code'],'scope':snapshot['primary_scope'],
  'input_sources':input_hashes,'software':snapshot['software']}).encode()).hexdigest()[:16]
 snapshot['snapshot_id']=VERSION+'-'+sourceid
 import unified_exports
 bundle=unified_exports.build(snapshot,context,frozen_counts,pairs,models,comparisons,model_audit,pair_audit,safe_occ)
 destination=unified_exports.publish(bundle,snapshot)
 log('Published unified snapshot: '+str(destination))
 log('Table II prompt-paired inventory: '+stable(unique_stats['values']))
 for cat,metrics in rq3.items():log(cat+': '+stable(metrics))
 return destination


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,help='Replay immutable capture_manifest.json (or capture directory)')
 parser.add_argument('--cutoff',help='UTC/offset cutoff for a fresh capture; defaults to now')
 args=parser.parse_args();require(not(args.source and args.cutoff),'Replay uses its recorded cutoff')
 run(args.source,args.cutoff)


if __name__=='__main__':
 try:main()
 except (ValueError,OSError,KeyError,sqlite3.Error,AssertionError) as exc:raise SystemExit('Unified VulChain ERROR: '+str(exc))
