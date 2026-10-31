"""Shared calculation library for the VulChain RQ2-RQ5 reproduction scripts.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Recompute the manuscript's RQ2-RQ5 values from the published, frozen
         analysis snapshot without the raw response ledger.

Every definition in the "Copied verbatim" sections below is the exact text of
the production analysis code that generated the manuscript macros (snapshot
v2026.10.27-unified-01-b9e3e4d60181fa58). It was extracted mechanically with
the Python ast module; it is not a re-implementation. The source files and
line ranges are listed above each section. Only the "Adapter" section is new:
it provides the names the copied code expects (the production module aliases
`a` and `common`), typed loaders for the published CSV/JSONL inputs, and
manuscript comparison helpers.
"""

import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


# ============================================================================
# Adapter (new code)
# ============================================================================

def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


# Paths read by the copied rq5_graph(); set by load_rq5_graph().
RQ5_EXPORT = None
RQ5_LINEAGE = None


# ============================================================================
# Copied verbatim from unified_analysis.py
# SHA-256 4b3f7b2d3a3fb5bddf49a17496c0fe52fce6c2789843aea776214be8bc63823a
# Lines: 32-32, 33-33, 34-34, 35-38, 39-39, 53-55, 58-70, 73-88
# ============================================================================

POLICIES=('strict','intermediate','declared','extended')

TAGS=dict(zip(POLICIES,('Strict','Intermediate','Declared','Extended')))

ADAPT={'finetune':'FT','adapter':'AD','quantized':'QT','merged':'Merge'}

CATEGORIES={'package_hallucination':('Pkg','Package hallucination'),
 'nonexistent_domain':('Nx','Registrable NXDOMAIN'),
 'malicious_url':('Mal','Exact malicious URL'),
 'restricted_namespace':('Restricted','Restricted namespace')}

STRATA=('AD','ndFT','dFT','QT','MG')

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


# Adapter (new code): the production exports module refers to the analysis
# module as `a`; provide the same names before the exports code runs.
a = SimpleNamespace(require=require, sha=sha, rows=csv_rows, summarize=summarize,
                    clustered=clustered, POLICIES=POLICIES, TAGS=TAGS,
                    CATEGORIES=CATEGORIES, STRATA=STRATA)

# ============================================================================
# Copied verbatim from unified_exports.py
# SHA-256 35eff65a28cb9ebb1dc0edb0126c0b7f61cac6be0a7f531c45d5b38530cbde38
# Lines: 61-61, 62-65, 69-80, 83-84, 85-85, 86-86, 89-98, 101-117, 120-121, 122-122, 125-128, 131-144, 306-306, 307-307, 308-308, 309-309, 312-332, 335-345, 348-360, 363-367, 370-386, 389-422
# ============================================================================

def rate(value):return 'N/A' if value is None else f'{100*value:.2f}'

# v2026.10.28-format-01: trim only after existing two-decimal formatting.
def percentage(text):
 text=str(text).replace(r'\%','')
 return text.rstrip('0').rstrip('.') if '.' in text else text

class Macros:
 def __init__(self,comment):self.values={};self.comment=comment
 def put(self,name,value):
  a.require(re.fullmatch('[A-Za-z]+',name) and name not in self.values,'Invalid/duplicate macro: '+name)
  text=str(value)
  if ((name.startswith(('rqTwo','RQThree','rqThree','RQFour')) and name.endswith(('Rate','Coverage')))
      or name.startswith(('rqthreePsi','rqthreeSigma','rqfourRate')) or (name.startswith('rqfive') and 'Pct' in name)):text=percentage(text)
  self.values[name]=text
 def group(self,prefix,r):
  for key,name in [('tests','Tests'),('class_rec','ClassRec'),('instance_rec','InstanceRec'),('upstreams','Upstreams'),('derivatives','Derivs'),('pairs','Pairs'),('unknown_excluded','UnknownExcluded'),('available','Available')]:self.put(prefix+name,r[key])
  self.put(prefix+'ClassRate',rate(r['class_rate']));self.put(prefix+'InstanceRate',rate(r['instance_rate']))
 def text(self):return ('% '+self.comment+'\n'+''.join('\\newcommand{\\'+k+'}{'+v+'}\n' for k,v in self.values.items())).encode()

# Manuscript (single-column Table VII) names: legacy category/stratum spellings of the same cells.
LEGACY_CATS={'package_hallucination':'Pkg','nonexistent_domain':'Nx','restricted_namespace':'Res','malicious_url':'Mal'}

LEGACY_STRATA={'AD':'Adapter','ndFT':'FTEvid','dFT':'FTDef','QT':'Quantized','MG':'Merged','Overall':'All'}

BASE_CATS=('package_hallucination','nonexistent_domain');BASE_STRATA=('AD','ndFT','dFT','MG','Overall')

def rq4_legacy_aliases(m4,rq4):
 """K = recurrences, N = that level's denominator, Rate = that level's rate, Bases = distinct
 upstreams with an eligible comparison; every value is a field of the validated RQ4 cell."""
 for cat,legacy in LEGACY_CATS.items():
  for group,name in LEGACY_STRATA.items():
   r=rq4[cat][group]
   for metric,level in (('class','Class'),('instance','Instance')):
    m4.put('rqfourK'+legacy+level+name,r[metric+'_rec']);m4.put('rqfourN'+legacy+level+name,r[metric+'_denominator'])
    m4.put('rqfourRate'+legacy+level+name,rate(r[metric+'_rate']))
   if cat in BASE_CATS and group in BASE_STRATA:m4.put('rqfourBases'+legacy+name,r['upstreams'])

def rq3_compatibility_aliases(m3,s):
 """Two manuscript naming conventions backed by the validated canonical cells.
 Scalar aliases remain valid inside icdecount/numexpr. C/I test aliases share N
 only because the active estimator validates equal category-specific denominators."""
 for cat,(code,_) in a.CATEGORIES.items():
  legacy='Res' if code=='Restricted' else code;r=s['rq3'][cat];oc=s['occurrences'][cat]
  canonical={'Occ':oc['occurrences'],'Distinct':oc['distinct_artifacts'],'Tests':r['tests'],
   'ClassRec':r['class_rec'],'ClassRate':rate(r['class_rate']),
   'InstanceRec':r['instance_rec'],'InstanceRate':rate(r['instance_rate'])}
  for suffix,value in canonical.items():m3.put('rqThree'+code+suffix,value)
  m3.put('rqthreeOcc'+legacy,canonical['Occ']);m3.put('rqthreeDistinct'+legacy,canonical['Distinct'])
  for policy in a.POLICIES:
   tag={'strict':'Strict','intermediate':'Inter','declared':'Decl','extended':'Ext'}[policy]
   cell=s['rq2'][policy]['cumulative'][cat]
   m3.put('rqthreePosC'+legacy+tag,cell['class_rec']);m3.put('rqthreePosI'+legacy+tag,cell['instance_rec'])
   m3.put('rqthreePsiTable'+legacy+tag,rate(cell['class_rate']))
   m3.put('rqthreeSigmaTable'+legacy+tag,rate(cell['instance_rate']))

# Revised two-column Table VII: Finetune pools ndFT and dFT; every model count is a set over ledger IDs.
TABLE_CATS=('package_hallucination','nonexistent_domain','restricted_namespace')

TABLE_GROUPS={'Adapter':('AD',),'Finetune':('ndFT','dFT'),'Quantized':('QT',),'Merged':('MG',),'All':a.STRATA}

def rq4_rows(comparisons,cat,strata):
 """Eligible (jointly determinate) Declared comparisons of one category in the given strata."""
 return [r for r in comparisons if r['category']==cat and r['in_declared'] and r['stratum'] in strata
         and r['class_state']!='unknown' and r['instance_state']!='unknown']

def rq4_table_vii_macros(m4,comparisons):
 """Bases = distinct parent_id with an eligible comparison; Affected = distinct child_id with an eligible
 class-level recurrence; Finetune K/N/Rate from the pooled ndFT+dFT rows. Existing names are not re-emitted."""
 for cat in TABLE_CATS:
  legacy=LEGACY_CATS[cat]
  for name,strata in TABLE_GROUPS.items():
   rows=rq4_rows(comparisons,cat,strata)
   if 'rqfourBases'+legacy+name not in m4.values:m4.put('rqfourBases'+legacy+name,len({r['parent_id'] for r in rows}))
   m4.put('rqfourAffected'+legacy+name,len({r['child_id'] for r in rows if r['class_state']=='positive'}))
   if name=='Finetune':
    r=a.summarize(rows)
    for metric,level in (('class','Class'),('instance','Instance')):
     m4.put('rqfourK'+legacy+level+name,r[metric+'_rec']);m4.put('rqfourN'+legacy+level+name,r[metric+'_denominator'])
     m4.put('rqfourRate'+legacy+level+name,rate(r[metric+'_rate']))

RQ5_GRAPH_FILES=('cohort_models.csv','cohort_lineage.csv','model_space_edges.csv','model_github_edges.csv','space_github_edges.csv','graph_manifest.json')

RQ5_CATS={'package_hallucination':'Pkg','nonexistent_domain':'Nx','malicious_url':'Mal','restricted_namespace':'Res'}

RQ5_VERIFIED=('package_hallucination','nonexistent_domain','malicious_url')

ROLE_TEXT={'upstream_base':'an upstream base','derivative':'a derivative',None:'N/A'}

def rq5_graph():
 """Frozen graph export and full-graph lineage, each hash-checked against the export manifest (fail closed)."""
 manifest={}
 for line in (RQ5_EXPORT/'sha256_manifest.txt').read_text().splitlines():
  parts=line.split(maxsplit=1)
  if len(parts)==2:manifest[parts[1].strip().lstrip('*')]=parts[0]
 sources={}
 for name in RQ5_GRAPH_FILES:
  p=RQ5_EXPORT/name;a.require(manifest.get(name) and a.sha(p)==manifest[name],'RQ5 graph export mismatch: '+name);sources[str(p)]=manifest[name]
 pin=next((v for k,v in manifest.items() if k.endswith('/edges/csv/01_model_model_edges.csv')),None)
 a.require(pin and a.sha(RQ5_LINEAGE)==pin,'RQ5 full-graph lineage mismatch');sources[str(RQ5_LINEAGE)]=pin
 g={'role':{r['model_id']:r['cohort_role'] for r in a.rows(RQ5_EXPORT/'cohort_models.csv')},'ms':defaultdict(set),'mg':defaultdict(set),'sg':defaultdict(set),
    'memberships':[(r['parent_model_id'],r['child_model_id'],r['recorded_adaptation_label'],r['excluded_label']=='1') for r in a.rows(RQ5_EXPORT/'cohort_lineage.csv')]}
 for r in a.rows(RQ5_EXPORT/'model_space_edges.csv'):g['ms'][r['model_id']].add(r['space_id'])
 for r in a.rows(RQ5_EXPORT/'model_github_edges.csv'):g['mg'][r['model_id']].add(r['github_repo_key'])
 for r in a.rows(RQ5_EXPORT/'space_github_edges.csv'):g['sg'][r['space_id']].add(r['github_repo_key'])
 with RQ5_LINEAGE.open(newline='') as f:g['edges']=[(r['source'].removeprefix('model::'),r['target'].removeprefix('model::')) for r in csv.DictReader(f)]
 gm=json.loads((RQ5_EXPORT/'graph_manifest.json').read_text());space=re.search(r'(\d{4})([A-Z][a-z]{2})(\d{2})',gm['graph_snapshot']['acquisition_context']['space_card_metadata'])
 g['meta']={'export_version':gm['export_version'],'snapshot_id':gm['graph_snapshot']['id'],'snapshot_date':gm['graph_snapshot']['analysis_snapshot_date'],
  'space_metadata_date':datetime.strptime(''.join(space.groups()),'%Y%b%d').strftime('%Y-%m-%d')}
 return g,sources

def lineage_components(edges):
 """Undirected connected components over every recorded model-model lineage edge (all edge types)."""
 parent={}
 def find(x):
  parent.setdefault(x,x)
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for u,v in edges:
  ru,rv=find(u),find(v)
  if ru!=rv:parent[ru]=rv
 return find

def rq5_reach(models,g):
 """Legacy rq5_reach.reach: recorded associations of a model set (graph-frame members only)."""
 ms,sg,mg,role=g['ms'],g['sg'],g['mg'],g['role'];inside={m for m in models if m in role}
 spaces=set().union(*(ms.get(m,set()) for m in inside)) if inside else set();direct=set().union(*(mg.get(m,set()) for m in inside)) if inside else set()
 via=set().union(*(sg.get(x,set()) for x in spaces)) if spaces else set()
 has_s={m for m in inside if ms.get(m)};has_g={m for m in inside if mg.get(m)};has_sg={m for m in inside if any(sg.get(x) for x in ms.get(m,()))}
 return dict(models=len(models),models_outside_graph_cohort=len(models)-len(inside),bases=sum(role[m]=='upstream_base' for m in inside),
  derivatives=sum(role[m]=='derivative' for m in inside),models_with_space=len(has_s),bases_with_space=sum(role[m]=='upstream_base' for m in has_s),
  derivatives_with_space=sum(role[m]=='derivative' for m in has_s),spaces=len(spaces),model_space_edges=sum(len(ms.get(m,())) for m in inside),
  spaces_with_github=sum(1 for x in spaces if sg.get(x)),repos_via_space=len(via),models_with_space_github_path=len(has_sg),models_with_direct_github=len(has_g),
  repos_direct=len(direct),repos_union=len(via|direct),repos_both=len(via&direct),
  model_space_github_paths=sum(len(sg.get(x,())) for m in inside for x in ms.get(m,())),model_github_paths=sum(len(mg.get(m,())) for m in inside),
  models_with_any_association=len(has_s|has_g),space_set=spaces,repo_set=via|direct)

def rq5_families(models,g,parents):
 """Legacy families(): a base is its own family; a derivative belongs to every frame parent."""
 out=set()
 for m in models:out|={m} if g['role'].get(m)=='upstream_base' else parents.get(m,set())
 return len(out)

def rq5_shared(emitters,g,top,component):
 """Legacy shared_reach over exact canonical artifacts with >= 2 distinct emitters, plus the recorded-lineage
 statistic: beyond_lineage = at least one emitter pair lies in different undirected lineage components
 (no recorded lineage path in either direction); all_unlinked = every emitter in a different component."""
 ms,sg=g['ms'],g['sg'];rows=[]
 for tok in sorted(emitters):
  em=emitters[tok]
  if len(em)<2:continue
  spaces=set().union(*(ms.get(m,set()) for m in em));repos=set().union(*(sg.get(x,set()) for x in spaces)) if spaces else set()
  comps=[component(m) for m in em]
  rows.append(dict(emitters=len(em),spaces=len(spaces),repos=len(repos),reaches_space=bool(spaces),by_top=top in em,
   reaches_space_excl_top=any(ms.get(m) for m in em if m!=top),beyond_lineage=len(set(comps))>=2,all_unlinked=len(set(comps))==len(comps)))
 med=lambda k:statistics.median([r[k] for r in rows]) if rows else None;mx=lambda k:max(r[k] for r in rows) if rows else None
 return dict(artifacts=len(emitters),shared=len(rows),emit_min=min((r['emitters'] for r in rows),default=None),emit_median=med('emitters'),emit_max=mx('emitters'),
  spaces_median=med('spaces'),spaces_max=mx('spaces'),reaching_space=sum(r['reaches_space'] for r in rows),reaching_repo=sum(r['repos']>0 for r in rows),
  by_top=sum(r['by_top'] for r in rows),reaching_space_excl_top=sum(r['reaches_space_excl_top'] for r in rows),
  beyond_lineage=sum(r['beyond_lineage'] for r in rows),all_unlinked=sum(r['all_unlinked'] for r in rows))

def rq5_compute(g,models,pairs,comparisons,occurrences,model_audit):
 frame_rows=[m for m in g['memberships'] if not m[3]];excluded_rows=[m for m in g['memberships'] if m[3]]
 frame={x for p,c,_,_ in frame_rows for x in (p,c)};sens=set(g['role'])
 parents=defaultdict(set)
 for p,c,_,_ in frame_rows:parents[c].add(p)
 component=lineage_components(g['edges']);evaluated=set(models);evpairs={(m['parent_id'],m['child_id']) for m in pairs.values()}
 out={'frame':rq5_reach(frame,g),'frame_pairs':len(frame_rows),'frame_set':frame,'frame_pair_set':{(p,c) for p,c,_,_ in frame_rows},
  'sens':rq5_reach(sens,g),'sens_pairs':len(g['memberships']),'excluded_models':sorted(sens-frame),'excluded_memberships':sorted((p,c,l) for p,c,l,_ in excluded_rows),
  'eval':rq5_reach(evaluated,g),'eval_pairs':len(evpairs),'eval_set':evaluated,'eval_pair_set':evpairs,'parents':parents,
  'sens_set':sens,'frame_rows':frame_rows,'graph_ms_models':set(g['ms']),'graph_mg_models':set(g['mg']),'meta':g['meta'],'lineage_edges':len(g['edges'])}
 out['excluded_detail']=[{'model_id':m,'role':g['role'][m],'spaces':len(g['ms'].get(m,())),'spaces_unique_to_model':len(g['ms'].get(m,set())-out['frame']['space_set']),
  'github_direct':len(g['mg'].get(m,()))} for m in out['excluded_models']]
 tested={r['model_id'] for r in model_audit if r['verified_both_c_one_prompts']>0}
 out['tested']=dict(rq5_reach(tested,g),complete=sum(1 for r in model_audit if r['model_id'] in tested and r['whole_bank_complete']),set=tested)
 emit={c:defaultdict(set) for c in RQ5_CATS}
 for o in occurrences:emit[o['category']][o['artifact_sha256']].add(o['model_id'])
 positive={c:{m for e in emit[c].values() for m in e} for c in RQ5_CATS};mplus=set().union(*(positive[c] for c in RQ5_VERIFIED))
 deg=sorted(((len(g['ms'].get(m,())),m) for m in mplus if m in g['role']),key=lambda x:(-x[0],x[1]))
 top=deg[0][1] if deg and deg[0][0] else None;total=sum(d for d,_ in deg)
 out['positive']=dict(rq5_reach(mplus,g),set=mplus,per_category={c:len(positive[c]) for c in RQ5_CATS},families=rq5_families(mplus,g,parents),
  top=top,top_role=g['role'].get(top) if top else None,top_degree=deg[0][0] if top else None,top3_edges=sum(d for d,_ in deg[:3]),total_edges=total,
  excl_top=rq5_reach(mplus-{top},g) if top else None,excl_top_families=rq5_families(mplus-{top},g,parents) if top else None)
 out['behavior']={}
 for cat,C in RQ5_CATS.items():
  el=[r for r in comparisons if r['category']==cat and r['in_declared'] and r['eligible']]
  elig={r['child_id'] for r in el};cls={r['child_id'] for r in el if r['class_state']=='positive'};inst={r['child_id'] for r in el if r['instance_state']=='positive'}
  tokens=defaultdict(set)
  for r in el:
   if r['instance_state']=='positive':
    for h in set(r['parent_artifact_sha256'])&set(r['child_artifact_sha256']):tokens[h]|={r['parent_id'],r['child_id']}
  out['behavior'][cat]=dict(comparisons=len(el),eligible=elig,class_recurrent=cls,instance_recurrent=inst,instance_reach=rq5_reach(inst,g),
   instance_families=rq5_families(inst,g,parents),shared=rq5_shared(emit[cat],g,top,component),shared_recurrence=rq5_shared(tokens,g,top,component),
   emitters=set().union(*emit[cat].values()) if emit[cat] else set())
 return out


# ============================================================================
# Adapter (new code): namespace aliases, loaders, and manuscript comparison
# ============================================================================

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO / "data" / "rq_snapshot"
DEFAULT_EXPECTED = REPO / "data" / "manuscript_macros"


def snapshot_files(snapshot_dir):
    """Hash-check every published snapshot input against its manifest (fail closed)."""
    snapshot_dir = Path(snapshot_dir)
    manifest = json.loads((snapshot_dir / "INPUT_MANIFEST.json").read_text())
    for name, digest in manifest["files"].items():
        require(sha(snapshot_dir / name) == digest, "Snapshot input changed: " + name)
    return manifest


def load_comparisons(snapshot_dir):
    with (Path(snapshot_dir) / "canonical_comparisons.jsonl").open() as handle:
        return [json.loads(line) for line in handle]


def load_occurrences(snapshot_dir):
    with (Path(snapshot_dir) / "qualified_occurrences.jsonl").open() as handle:
        return [json.loads(line) for line in handle]


def load_pairs(snapshot_dir):
    return {r["membership_id_sha256"]: r for r in csv_rows(Path(snapshot_dir) / "evaluated_relationships.csv")}


def load_models(snapshot_dir):
    return {r["model_id"] for r in csv_rows(Path(snapshot_dir) / "evaluated_model_manifest.csv")}


def load_model_audit(snapshot_dir):
    """model_status_audit.csv with the two fields rq5_compute reads restored to int/bool."""
    rows = csv_rows(Path(snapshot_dir) / "model_status_audit.csv")
    for r in rows:
        r["verified_both_c_one_prompts"] = int(r["verified_both_c_one_prompts"])
        r["whole_bank_complete"] = r["whole_bank_complete"] == "True"
    return rows


def load_rq5_graph(export_dir, lineage_csv):
    global RQ5_EXPORT, RQ5_LINEAGE
    RQ5_EXPORT, RQ5_LINEAGE = Path(export_dir), Path(lineage_csv)
    return rq5_graph()


def occurrence_counts(occurrences):
    """Occurrence rows and distinct canonical artifacts per category (RQ3 Occ./Dist.)."""
    rows = Counter(o["category"] for o in occurrences)
    distinct = defaultdict(set)
    for o in occurrences:
        distinct[o["category"]].add(o["artifact_sha256"])
    return {c: {"occurrences": rows[c], "distinct_artifacts": len(distinct[c])} for c in CATEGORIES}


def manuscript_macros(expected_dir, *names):
    values = {}
    for name in names:
        text = (Path(expected_dir) / name).read_text()
        values.update(re.findall(r"\\newcommand\{\\(\w+)\}\{([^\n]*)\}", text))
    return values


def compare(computed, expected, names):
    """Return (rows, ok). Each row: name, recomputed, manuscript, status."""
    rows, ok = [], True
    for name in names:
        got = str(computed.get(name))
        want = expected.get(name)
        status = "MATCH" if want is not None and got == want else "MISMATCH"
        ok &= status == "MATCH"
        rows.append((name, got, want, status))
    return rows, ok


def write_report(path, title, rows, ok, notes=()):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"Result: {'VERIFIED' if ok else 'MISMATCH'}", ""]
    lines += [f"- {n}" for n in notes]
    lines += ["", "| Macro | Recomputed | Manuscript | Status |", "|---|---|---|---|"]
    lines += [f"| {n} | {g} | {w} | {s} |" for n, g, w, s in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"{title}: {'VERIFIED' if ok else 'MISMATCH'} "
          f"({sum(r[3] == 'MATCH' for r in rows)}/{len(rows)} values match) -> {path}")
    return 0 if ok else 1
