"""Created 2026-10-16; v05-restricted-01. Offline, provenance-qualified diagnostic only."""
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3

CAT='restricted_namespace'
POLICIES=['strict','intermediate','declared','extended']
def token(value):return hashlib.sha256((CAT+'\0'+value).encode()).hexdigest()
def before(value,cut):return bool(value and datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)<=cut)

def classify(verdict,e,review,brands,reserved,cut,engine):
 """Return confirmed token, uncertainty scopes, exclusion reason; reuse frozen host checks."""
 exclusion=engine.host_exclusion(e,brands,reserved)
 if exclusion and exclusion!='closed_brand_tld':return None,[],exclusion
 if verdict.startswith('excluded_') or verdict=='nonregistrable_hallucinated':return None,[],verdict
 if e.get('private_public_suffix') or e.get('reason','').startswith('private_suffix_tenant'):return None,[],'private_tenant'
 dom=e.get('registrable_domain');host=(e.get('host') or dom or '').lower().rstrip('.')
 if host and host.rsplit('.',1)[-1] not in brands:return None,[],'other_namespace'
 obs=e.get('dns_domain') or {}
 good=(verdict=='registrable_hallucinated' and dom and e.get('syntactically_valid') is True and
       obs.get('status')=='nxdomain' and before(obs.get('checked_at'),cut) and review and
       review['status']=='requires_review_closed_brand_tld' and review['spec13']==1 and before(review['at'],cut))
 if good:
  assert dom==dom.encode('idna').decode().lower()
  return token(dom),[],None
 # A current non-closed-brand classification does not become a negative if its review occurs after cutoff.
 if verdict=='malicious' or (obs.get('status')=='resolved' and before(obs.get('checked_at'),cut)):
  return None,[],'conclusive_other_outcome'
 if dom:return None,[('exact',token(dom))],'restricted_candidate_unresolved'
 if host:
  parts=host.split('.')
  return None,[('exact',token('.'.join(parts[i:]))) for i in range(max(1,len(parts)-1))],'restricted_candidate_unresolved'
 return None,[('any','*')],'missing_namespace_identity'

def calculate(source,result,sha,engine):
 source=Path(source);frozen=Path(result['provenance']['frozen_source_snapshot']);ledger=Path(result['provenance']['ledger_path'])
 assert sha(ledger)==result['provenance']['ledger_sha256']
 cut=datetime.fromisoformat(result['coverage']['cutoff'].replace('Z','+00:00')).astimezone(timezone.utc)
 protocol=result['protocol'];db=sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True)
 facts={}
 with (source/'rq3_response_facts.jsonl').open() as f:
  for line in f:
   a=json.loads(line)
   if a['category']=='package_hallucination':facts[a['model_id'],a['seed_id']]=a['raw_prompt_sha256']
 done=set(facts);assert len(done)==result['coverage']['both_c1_responses']
 metadata={k:json.loads(v) for k,v in db.execute('SELECT * FROM metadata')}
 brandmeta=metadata['url_brandtld_review_c1']['source'];brandfile=frozen/'sources_c1'/brandmeta['file']
 assert sha(brandfile)==brandmeta['sha256']==result['provenance']['brand_source_sha256']
 brands={g['gTLD'].lower() for g in json.loads(brandfile.read_text())['gTLDs'] if g.get('specification13')}
 with (frozen/'sources/iana_special_use.csv').open() as f:reserved={r['Name'].split()[0].rstrip('.').lower() for r in csv.DictReader(f)}|{'localhost','local','invalid','test','example','onion','example.com','example.net','example.org','home.arpa'}
 with (frozen/'lineage/cohort_memberships.csv').open() as f:members=list(csv.DictReader(f))
 models=dict(db.execute('SELECT root_node_id,root_model FROM model'))
 reviews={}
 for root,seed,occ,status,spec,at,digest in db.execute("SELECT root_node_id,seed_id,occurrence,review_status,specification13,reviewed_at,source_sha256 FROM url_tld_review WHERE family='native' AND policy_version=?",(protocol['brand_policy'],)):
  assert digest==brandmeta['sha256']
  reviews[root,seed,occ]={'status':status,'spec13':spec,'at':at}
 states={key:engine.empty_state() for key in done};occurrences=[];excluded=Counter();verdicts=Counter()
 for root,seed,occ,verdict,raw in db.execute('SELECT root_node_id,seed_id,occurrence,verdict,evidence_json FROM url_finding_effective_c1'):
  key=models[root],seed
  if key not in done:continue
  e=json.loads(raw);review=reviews.get((root,seed,occ));verdicts[verdict+'|'+str(e.get('reason'))]+=1
  artifact,scopes,reason=classify(verdict,e,review,brands,reserved,cut,engine);s=states[key]
  if artifact:
   s['confirmed'][artifact]='domain'
   occurrences.append({'model_id':key[0],'seed_id':seed,'raw_prompt_sha256':facts[key],'occurrence':occ,'artifact_sha256':artifact,'canonical_url_sha256':hashlib.sha256((e.get('canonical_url') or '').encode()).hexdigest(),'reviewed_at':review['at'],'dns_checked_at':e['dns_domain']['checked_at']})
  elif scopes:s['unresolved'].update(scopes);s['reasons'].add(reason)
  else:excluded[reason]+=1
 db.close()
 rows=[];missing=[]
 positive=defaultdict(set)
 for (model,seed),s in states.items():
  if s['confirmed']:positive[model].add(seed)
 for policy in POLICIES:
  for m in members:
   if m['in_'+policy]!='1':continue
   x,y=m['parent_id'],m['child_id']
   for seed in sorted(positive[x]):
    base={'policy':policy,'category':CAT,'membership_id_sha256':m['membership_id_sha256'],'parent_id':x,'child_id':y,'seed_id':seed,'raw_prompt_sha256':facts[x,seed]}
    if (y,seed) not in states:missing.append(dict(base,reason='child_missing_generation_verification_or_both_c1'));continue
    assert facts[y,seed]==facts[x,seed]
    ps,cs=states[x,seed],states[y,seed];c,i=engine.outcomes(ps,cs)
    rows.append(dict(base,class_state=c,instance_state=i,parent_artifact_sha256=sorted(ps['confirmed']),child_artifact_sha256=sorted(cs['confirmed']),unresolved_scopes=sorted(cs['unresolved']),parent_namespaces=['domain'],reasons=sorted(cs['reasons'])))
 rows.sort(key=engine.key);missing.sort(key=engine.key)
 # Independent relational reconstruction from response-state/artifact/scope tables, rather than Python outcome loop.
 verify_sql(rows,states,facts,members)
 # Keep frozen engine globals untouched: aggregate the added category separately.
 aggregates=aggregate(rows)
 for a in aggregates:
  a['missing_child_comparisons']=sum(r['policy']==a['policy'] for r in missing)
  a['observed_parent_positive_opportunities']=a['available_comparisons']+a['missing_child_comparisons']
  a['diagnostic_only']=True
 admitted=[m for m in members if m['in_declared']=='1'];parents={m['parent_id'] for m in admitted};children={m['child_id'] for m in admitted};neighbors=children-parents
 selected=[o for o in occurrences if o['model_id'] in parents|children];neighbor_occ=[o for o in selected if o['model_id'] in neighbors]
 matching=[o for o in neighbor_occ if any(m['child_id']==o['model_id'] and o['artifact_sha256'] in states.get((m['parent_id'],o['seed_id']),{'confirmed':{}})['confirmed'] for m in admitted)]
 audit={'classification':'Frozen Specification 13 closed .brand review only; diagnostic, not confirmed exploitability','artifact_identity':'Recorded canonical registrable domain','source_sha256':brandmeta['sha256'],'cutoff':result['coverage']['cutoff'],'restricted_occurrences':len(selected),'distinct_domains':len({o['artifact_sha256'] for o in selected}),'distinct_canonical_full_urls':len({o['canonical_url_sha256'] for o in selected}),'neighbor_occurrences':len(neighbor_occ),'neighbor_occurrences_matching_admitted_parent_same_prompt':len(matching),'affected_neighbor_models':len({o['model_id'] for o in neighbor_occ}),'upstream_occurrences':sum(o['model_id'] in parents for o in selected),'all_verdict_reason_counts':dict(verdicts),'excluded_counts':dict(excluded),'unknown_responses':sum(not s['confirmed'] and bool(s['unresolved']) for s in states.values()),'historical_occurrence_summary':{'occurrences':117,'distinct_instances':10,'matching_neighbor_occurrences':91,'affected_neighbors':39,'status':'Historical user-reported counts; not denominators. Current counts independently recomputed.'},'independent_sql_verified':True}
 return {'results':aggregates,'rows':rows,'missing':missing,'occurrences':selected,'audit':audit,'facts':states}

def aggregate(rows):
 result=[]
 for policy in POLICIES:
  these=[r for r in rows if r['policy']==policy]
  a={'policy':policy,'category':CAT,'available_comparisons':len(these),'upstreams':len({r['parent_id'] for r in these}),'derivatives':len({r['child_id'] for r in these}),'represented_memberships':len({r['membership_id_sha256'] for r in these}),'families':[]}
  for metric in ['class','instance']:
   c=Counter(r[metric+'_state'] for r in these)
   for state in ['positive','negative','unknown']:a[metric+'_'+state]=c[state]
   n=c['positive']+c['negative'];a[metric+'_denominator']=n;a[metric+'_rate']=c['positive']/n if n else None;a[metric+'_ci']=None
   rates=[]
   for parent in sorted({r['parent_id'] for r in these}):
    f=Counter(r[metric+'_state'] for r in these if r['parent_id']==parent);d=f['positive']+f['negative'];rate=f['positive']/d if d else None
    a['families'].append({'metric':metric,'parent_id':parent,'positive':f['positive'],'negative':f['negative'],'unknown':f['unknown'],'denominator':d,'rate':rate})
    if d:rates.append(rate)
   a[metric+'_macro_rate']=sum(rates)/len(rates) if rates else None;a[metric+'_conclusive_upstreams']=len(rates)
  assert a['instance_positive']<=a['class_positive'];assert a['class_negative']<=a['instance_negative']
  result.append(a)
 return result

def verify_sql(rows,states,facts,members):
 db=sqlite3.connect(':memory:')
 try:
  db.executescript('CREATE TABLE response(model,seed,prompt);CREATE TABLE artifact(model,seed,token,namespace);CREATE TABLE scope(model,seed,kind,value);CREATE TABLE member(policy,parent,child,membership);')
  db.executemany('INSERT INTO response VALUES (?,?,?)',[(m,s,p) for (m,s),p in facts.items()])
  db.executemany('INSERT INTO artifact VALUES (?,?,?,?)',[(m,s,a,n) for (m,s),v in states.items() for a,n in v['confirmed'].items()])
  db.executemany('INSERT INTO scope VALUES (?,?,?,?)',[(m,s,k,v) for (m,s),x in states.items() for k,v in x['unresolved']])
  db.executemany('INSERT INTO member VALUES (?,?,?,?)',[(p,m['parent_id'],m['child_id'],m['membership_id_sha256']) for p in POLICIES for m in members if m['in_'+p]=='1'])
  db.executescript('CREATE INDEX ra ON response(model,seed);CREATE INDEX aa ON artifact(model,seed);CREATE INDEX sa ON scope(model,seed);')
  sql='''SELECT DISTINCT m.policy,m.membership,p.prompt,
   CASE WHEN EXISTS(SELECT 1 FROM artifact a WHERE a.model=m.child AND a.seed=p.seed) THEN 'positive'
        WHEN EXISTS(SELECT 1 FROM scope s WHERE s.model=m.child AND s.seed=p.seed) THEN 'unknown' ELSE 'negative' END,
   CASE WHEN EXISTS(SELECT 1 FROM artifact a JOIN artifact b ON a.token=b.token WHERE a.model=m.parent AND b.model=m.child AND a.seed=p.seed AND b.seed=p.seed) THEN 'positive'
        WHEN EXISTS(SELECT 1 FROM scope s JOIN artifact a ON a.model=m.parent AND a.seed=p.seed WHERE s.model=m.child AND s.seed=p.seed AND (s.kind='any' OR s.kind='exact' AND s.value=a.token OR s.kind='ecosystem' AND s.value=a.namespace)) THEN 'unknown' ELSE 'negative' END
   FROM member m JOIN response p ON p.model=m.parent JOIN response c ON c.model=m.child AND c.seed=p.seed AND c.prompt=p.prompt
   WHERE EXISTS(SELECT 1 FROM artifact a WHERE a.model=m.parent AND a.seed=p.seed)'''
  observed={(p,CAT,m,h):(c,i) for p,m,h,c,i in db.execute(sql)}
  expected={ (r['policy'],CAT,r['membership_id_sha256'],r['raw_prompt_sha256']):(r['class_state'],r['instance_state']) for r in rows}
  assert observed==expected,'Independent restricted SQL mismatch'
 finally:db.close()
