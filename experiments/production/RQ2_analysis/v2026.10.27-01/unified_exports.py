"""Created 2026-10-27; v2026.10.27-unified-01. Validated publication bundle.
All scientific numbers come from unified_analysis. Atomic directory-pointer publication.
Original experimental, frozen verifier and legacy RQ export directories remain untouched.
"""
# Change history:
# 2026-10-28 v2026.10.28-rq3-macro-compat-01
# - Emit scalar-compatible rqThree and rqthree RQ3 aliases from canonical
#   shared-denominator metrics; scientific values and table structure unchanged.
# 2026-10-28 v2026.10.28-rq4-qt-01
# - Replace historical zero-QT assumptions with source-backed eligibility, ID,
#   numerator, rate and partition invariants. Table and macro contracts unchanged.
# 2026-10-28 v2026.10.28-rq4-compat-01
# - rq4_numbers_codex.tex also defines the manuscript's lowercase \rqfourK/N/Rate aliases and the
#   ten \rqfourBases{Pkg,Nx}{Adapter,FTEvid,FTDef,Merged,All} macros, read from the validated RQ4 cells.
# - RQ4 rates use the RQ2/RQ3 display rule (insignificant trailing zeros trimmed).
# - Ledger-level RQ4 publication validation (exact comparison identities) blocks publication on failure.
# - Previous version backed up as unified_exports.py.bak.20261028-112114.
# 2026-10-28 v2026.10.28-rq4-tablevii-01
# - Revised Table VII macros: rqfourBases/rqfourAffected for {Pkg,Nx,Res}x{Adapter,Finetune,Quantized,Merged,All}
#   and pooled Finetune (ndFT+dFT) K/N/Rate; model counts are set unions over canonical ledger IDs.
# - Validation: affected derivatives are class-recurrent tested derivatives; Finetune pooling; group partition.
# - Previous version backed up as unified_exports.py.bak.20261028-114355.
# 2026-10-28 v2026.10.28-rq5-unified-01
# - RQ5 from the same pinned capture: rq5_numbers_codex.tex (legacy \rqfive names regenerated where their meaning is
#   unchanged, plus Frame/Eval/Conc namespaces), macro-only Table VIII (tab:rq5), audit/discussion/validation reports.
# - Hash-pinned frozen graph inputs; separate graph-frame, evaluated, behavioral and concentration populations.
# - Previous version backed up as unified_exports.py.bak.20261028-125600.
# 2026-10-28 v2026.10.28-rq5-table-02
# - Table VIII: @{}lrrrr@{}, bold PkgH/NX/Mal/Res. header, six finding rows; rqfiveRecDerivsCell*/RecDerivsSpaceCell*
#   show N/A when no derivative is eligible (legacy rqfiveRecDerivs* counts unchanged); table-level validation.
# - validate_tex counts tabular columns outside brace groups (@{} specs).
# - Previous version backed up as unified_exports.py.bak.20261028-131400.
from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import statistics
import tempfile
from zoneinfo import ZoneInfo
import unified_analysis as a

ROOT,WORK=a.ROOT,a.WORK


def csvdata(records):
 if not records:return b''
 keys=list(dict.fromkeys(k for r in records for k in r));stream=io.StringIO(newline='')
 writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader()
 writer.writerows({k:(json.dumps(v,sort_keys=True) if isinstance(v,(dict,list,set,tuple)) else v) for k,v in r.items()} for r in records)
 return stream.getvalue().encode()


def count(name):return '\\icdecount{\\'+name+'}'
def rate(value):return 'N/A' if value is None else f'{100*value:.2f}'
# v2026.10.28-format-01: trim only after existing two-decimal formatting.
def percentage(text):
 text=str(text).replace(r'\%','')
 return text.rstrip('0').rstrip('.') if '.' in text else text
def stamp():return datetime.now(ZoneInfo('America/Chicago')).strftime('%Y%m%d-%H%M%S')


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


def comparison_id(r):return (r['membership_id_sha256'],r['category'],r['raw_prompt_sha256'])


def rq4_validation(s,pairs,comparisons,values):
 """Exact-identity RQ2/RQ3/RQ4 reconciliation. values: all generated macro values by name.
 Returns (report, failures); publication must not proceed when failures is non-empty."""
 checks=[];failures=[]
 def check(name,ok,detail):
  checks.append({'name':name,'result':'PASS' if ok else 'FAIL','detail':detail})
  if not ok:failures.append(name+': '+detail)
 ids=[comparison_id(r) for r in comparisons]
 check('ledger.comparison_identities_unique',len(ids)==len(set(ids)),f'{len(ids)} rows, {len(set(ids))} identities')
 check('ledger.every_stratum_mapped',all(r['stratum'] in a.STRATA for r in comparisons),'strata '+','.join(sorted({str(r['stratum']) for r in comparisons})))
 check('ledger.strata_match_recorded_adaptation',all(
  r['membership_id_sha256'] in pairs and
  pairs[r['membership_id_sha256']]['adaptation_label'] in a.ADAPT and
  a.stratum(pairs[r['membership_id_sha256']]['adaptation_label'],pairs[r['membership_id_sha256']]['adaptation_evidence_category'])==r['stratum'] and
  r.get('adaptation_label',pairs[r['membership_id_sha256']]['adaptation_label'])==pairs[r['membership_id_sha256']]['adaptation_label']
  for r in comparisons),'each comparison uses its recorded eligible adaptation label; no relabeling QT into FT/AD/MG')
 totals={};bases={};dft={}
 for cat,(code,_) in a.CATEGORIES.items():
  legacy=LEGACY_CATS[cat];rows=[r for r in comparisons if r['category']==cat]
  eligible=lambda r:r['class_state']!='unknown' and r['instance_state']!='unknown'
  rq3set={comparison_id(r) for r in rows if eligible(r) and pairs[r['membership_id_sha256']]['in_declared']=='1'}
  rq4rows=[r for r in rows if eligible(r) and r['in_declared']];rq4set={comparison_id(r) for r in rq4rows}
  check(cat+'.rq4_overall_identities_eq_rq3',rq4set==rq3set,f'{len(rq4set)} vs {len(rq3set)}; symmetric difference {len(rq4set^rq3set)}')
  ledger={'tests':len(rq4set),'class_rec':sum(r['class_state']=='positive' for r in rq4rows),'instance_rec':sum(r['instance_state']=='positive' for r in rq4rows)}
  for metric,ledger_value in ledger.items():
   got=[s['rq2']['declared']['cumulative'][cat][metric],s['rq3'][cat][metric],s['rq4'][cat]['Overall'][metric]]
   check(f'{cat}.{metric}.ledger_eq_rq2_rq3_rq4',got==[ledger_value]*3,f'ledger {ledger_value}; RQ2/RQ3/RQ4 {got}')
  for suffix in ('Tests','ClassRec','InstanceRec','ClassRate','InstanceRate','Upstreams'):
   got=[values.get('rqTwoDeclared'+code+suffix),values.get('RQThree'+code+suffix),values.get('RQFour'+code+'Overall'+suffix)]
   check(f'{cat}.macro_{suffix}_rq2_eq_rq3_eq_rq4',None not in got and len(set(got))==1,'rqTwoDeclared/RQThree/RQFour '+' / '.join(map(str,got)))
  strata={g:{comparison_id(r) for r in rq4rows if r['stratum']==g} for g in a.STRATA}
  union=set().union(*strata.values());overlap=sum(len(x) for x in strata.values())-len(union)
  check(cat+'.strata_partition_overall',union==rq4set and overlap==0,f'union {len(union)} of {len(rq4set)}; multiply counted {overlap}')
  avail={g:sum(1 for r in rows if r['in_declared'] and r['stratum']==g) for g in a.STRATA}
  check(cat+'.strata_partition_available',sum(avail.values())==s['rq4'][cat]['Overall']['available'],f'{sum(avail.values())} vs {s["rq4"][cat]["Overall"]["available"]}')
  totals[cat]={}
  for g in list(a.STRATA)+['Overall']:
   cell=s['rq4'][cat][g];chosen=[r for r in rq4rows if g=='Overall' or r['stratum']==g]
   upstreams=len({r['parent_id'] for r in chosen});name=LEGACY_STRATA[g]
   check(f'{cat}.{g}.shared_denominator',cell['class_denominator']==cell['instance_denominator']==cell['tests']==len(chosen),
         f"class {cell['class_denominator']}, instance {cell['instance_denominator']}, ledger {len(chosen)}")
   check(f'{cat}.{g}.legacy_aliases_eq_cell',[values.get('rqfourK'+legacy+'Class'+name),values.get('rqfourN'+legacy+'Class'+name),values.get('rqfourK'+legacy+'Instance'+name),values.get('rqfourN'+legacy+'Instance'+name),values.get('rqfourRate'+legacy+'Class'+name),values.get('rqfourRate'+legacy+'Instance'+name)]==
         [str(cell['class_rec']),str(cell['tests']),str(cell['instance_rec']),str(cell['tests']),values.get('RQFour'+code+g+'ClassRate'),values.get('RQFour'+code+g+'InstanceRate')],'K/N/Rate aliases vs RQFour'+code+g)
   check(f'{cat}.{g}.upstreams_from_ledger',upstreams==cell['upstreams'],f'ledger {upstreams} vs cell {cell["upstreams"]}')
   n=len(chosen);k=sum(r['class_state']=='positive' for r in chosen);ki=sum(r['instance_state']=='positive' for r in chosen)
   check(f'{cat}.{g}.recurrence_numerators_from_ledger',
         0<=ki<=k<=n and (cell['class_rec'],cell['instance_rec'])==(k,ki) and
         all(r['instance_state']!='positive' or r['class_state']=='positive' for r in chosen),f'ledger class {k}, instance {ki}, tests {n}')
   check(f'{cat}.{g}.model_and_pair_ids_from_ledger',
         (cell['derivatives'],cell['pairs'])==(len({r['child_id'] for r in chosen}),len({r['membership_id_sha256'] for r in chosen})),
         'distinct derivative and membership IDs; duplicate rows cannot inflate counts')
   expected_rates=[k/n if n else None,ki/n if n else None]
   check(f'{cat}.{g}.rates_from_ledger_or_nonestimable',
         [cell['class_rate'],cell['instance_rate']]==expected_rates and
         [values.get('rqfourRate'+legacy+level+name) for level in ('Class','Instance')]==[percentage(rate(x)) for x in expected_rates],
         f'tests {n}; expected class/instance rates {expected_rates}')
   totals[cat][g]={k:cell[k] for k in ('available','tests','class_rec','instance_rec','upstreams','derivatives','pairs')}
   if cat in BASE_CATS and g in BASE_STRATA:
    bases['rqfourBases'+legacy+name]=upstreams
    check(f'{cat}.{g}.rqfourBases{legacy}{name}',values.get('rqfourBases'+legacy+name)==str(upstreams),f'macro {values.get("rqfourBases"+legacy+name)} vs ledger {upstreams}')
  check(cat+'.QT.eligibility_controls_estimability',
        all((s['rq4'][cat]['QT'][metric+'_rate'] is None)==(len(strata['QT'])==0) for metric in ('class','instance')),
        f'{len(strata["QT"])} eligible QT comparisons; N/A exactly when the denominator is empty')
  if cat in BASE_CATS:
   check(cat+'.rqfourBases'+legacy+'All_eq_rqTwoDeclared'+code+'Upstreams',values.get('rqfourBases'+legacy+'All')==values.get('rqTwoDeclared'+code+'Upstreams'),
         f"{values.get('rqfourBases'+legacy+'All')} vs {values.get('rqTwoDeclared'+code+'Upstreams')}")
  # RQ4 dFT versus the comparisons newly admitted by Declared (RQ2 +Declared), by exact identity.
  dset={comparison_id(r) for r in rq4rows if r['stratum']=='dFT'}
  added=[r for r in rows if eligible(r) and r['in_declared'] and not r['in_intermediate']];aset={comparison_id(r) for r in added}
  check(cat+'.plus_declared_eq_rq2_added_tests',len(aset)==s['rq2']['declared']['added'][cat]['tests'],f"{len(aset)} vs {s['rq2']['declared']['added'][cat]['tests']}")
  both=[r for r in rq4rows if comparison_id(r) in dset&aset];union=dset|aset
  jaccard=len(dset&aset)/len(union) if union else None
  verdict='no comparisons' if not union else 'identical' if dset==aset else 'mostly overlapping (Jaccard >= 0.9)' if jaccard>=.9 else 'materially different (Jaccard < 0.9)'
  dpairs={k for k,m in pairs.items() if m['in_declared']=='1' and a.stratum(m['adaptation_label'],m['adaptation_evidence_category'])=='dFT'}
  apairs={k for k,m in pairs.items() if m['in_declared']=='1' and m['in_intermediate']!='1'}
  dft[cat]={'dFT':len(dset),'plus_declared':len(aset),'intersection':len(dset&aset),'dFT_only':len(dset-aset),'plus_declared_only':len(aset-dset),
   'jaccard':None if jaccard is None else round(jaccard,6),'overlap_class_rec':sum(r['class_state']=='positive' for r in both),
   'overlap_instance_rec':sum(r['instance_state']=='positive' for r in both),'verdict':verdict,
   'relationship_level':{'dFT_pairs':len(dpairs),'plus_declared_pairs':len(apairs),'intersection':len(dpairs&apairs)}}
 # Revised Table VII model counts, recomputed independently of the emitted macros.
 table={}
 for cat in TABLE_CATS:
  legacy,code=LEGACY_CATS[cat],a.CATEGORIES[cat][0];table[cat]={}
  for name,strata in TABLE_GROUPS.items():
   rows=rq4_rows(comparisons,cat,strata);ids={comparison_id(r) for r in rows}
   parents={r['parent_id'] for r in rows};tested={r['child_id'] for r in rows}
   affected={r['child_id'] for r in rows if r['class_state']=='positive'}
   cells=[s['rq4'][cat][g] for g in strata];g=name if name!='All' else 'Overall'
   k=sum(c['class_rec'] for c in cells);ki=sum(c['instance_rec'] for c in cells);n=sum(c['tests'] for c in cells)
   row={'bases':len(parents),'affected':len(affected),'tested_derivatives':len(tested),'tests':n,'class_rec':k,'instance_rec':ki,
        'class_rate':k/n if n else None,'instance_rate':ki/n if n else None}
   table[cat][name]=row
   check(f'{cat}.{name}.affected_are_class_recurrent_tested_derivatives',affected<=tested and all(any(r['child_id']==x and r['class_state']=='positive' for r in rows) for x in affected),
         f'affected {len(affected)} <= tested {len(tested)}')
   check(f'{cat}.{name}.rqfourAffected{legacy}{name}',values.get('rqfourAffected'+legacy+name)==str(len(affected)),f'macro {values.get("rqfourAffected"+legacy+name)} vs ledger {len(affected)}')
   check(f'{cat}.{name}.rqfourBases{legacy}{name}',values.get('rqfourBases'+legacy+name)==str(len(parents)),f'macro {values.get("rqfourBases"+legacy+name)} vs ledger {len(parents)}')
   check(f'{cat}.{name}.pooled_cells_eq_ledger',(n,k,ki)==(len(ids),sum(r['class_state']=='positive' for r in rows),sum(r['instance_state']=='positive' for r in rows)),
         f'cells {n}/{k}/{ki} vs ledger {len(ids)}')
   if name=='Finetune':
    check(cat+'.Finetune.K_N_eq_ndFT_plus_dFT',[values.get('rqfourK'+legacy+'ClassFinetune'),values.get('rqfourN'+legacy+'ClassFinetune'),values.get('rqfourK'+legacy+'InstanceFinetune'),values.get('rqfourN'+legacy+'InstanceFinetune')]==[str(k),str(n),str(ki),str(n)],
          f'pooled K {k}, Ki {ki}, N {n}')
    union=len({r['parent_id'] for r in rows});each=[len({r['parent_id'] for r in rq4_rows(comparisons,cat,(x,))}) for x in strata]
    check(cat+'.Finetune.bases_are_union_not_sum',max(each)<=union<=sum(each),f'union {union}; ndFT/dFT {each}')
    check(cat+'.Finetune.rates_from_pooled_rows',[values.get('rqfourRate'+legacy+'ClassFinetune'),values.get('rqfourRate'+legacy+'InstanceFinetune')]==
          [percentage(rate(k/n if n else None)),percentage(rate(ki/n if n else None))],'pooled rates')
   if name=='All':
    o=s['rq4'][cat]['Overall']
    check(cat+'.All.model_counts_are_distinct_ids',(len(parents),len(tested))==(o['upstreams'],o['derivatives']),f'bases {len(parents)}/{o["upstreams"]}, derivatives {len(tested)}/{o["derivatives"]}')
   if name=='Quantized':
    row.update(upstream_ids=sorted(parents),tested_derivative_ids=sorted(tested),class_recurrent_derivative_ids=sorted(affected),
               membership_ids=sorted({r['membership_id_sha256'] for r in rows}))
    check(cat+'.Quantized.source_backed_estimability',
          0<=ki<=k<=n and affected<=tested and
          [values.get('rqfourK'+legacy+level+'Quantized') for level in ('Class','Instance')]==[str(k),str(ki)] and
          [values.get('rqfourN'+legacy+level+'Quantized') for level in ('Class','Instance')]==[str(n),str(n)] and
          [values.get('rqfourRate'+legacy+level+'Quantized') for level in ('Class','Instance')]==
          [percentage(rate(k/n if n else None)),percentage(rate(ki/n if n else None))] and
          (bool(parents) and bool(tested) if n else not (parents or tested or affected)),
          f'bases {len(parents)}, tested derivatives {len(tested)}, affected {len(affected)}, tests {n}, class {k}, instance {ki}')
  groups=[g for g in TABLE_GROUPS if g!='All'];union=set().union(*({comparison_id(r) for r in rq4_rows(comparisons,cat,TABLE_GROUPS[g])} for g in groups))
  check(cat+'.table_groups_partition_rq3',sum(table[cat][g]['tests'] for g in groups)==len(union)==s['rq3'][cat]['tests'],f'{sum(table[cat][g]["tests"] for g in groups)} vs RQ3 {s["rq3"][cat]["tests"]}')
 return {'checks':checks,'adaptation_totals':totals,'contributing_bases':bases,'dft_vs_plus_declared':dft,'table_vii':table},failures


def rq4_validation_text(v):
 lines=['# RQ4 publication validation','',v['snapshot_id']+'; cutoff '+v['cutoff'],'Capture '+v['capture_manifest']+' (SHA256 '+v['capture_manifest_sha256']+'); ledger SHA256 '+v['ledger_sha256'],
  'Result: **'+v['status']+'** ('+str(sum(c['result']=='PASS' for c in v['checks']))+'/'+str(len(v['checks']))+' checks pass)','',
  '## Cohort','`'+json.dumps(v['cohort'],sort_keys=True)+'`','','## Numerical file hashes',*('- '+n+' '+h for n,h in sorted(v['file_sha256'].items())),'',
  '## Contributing upstreams (distinct parent_id with an eligible comparison; not additive across strata)','| Macro | Value |','|---|---:|',
  *('| \\'+n+' | '+str(x)+' |' for n,x in v['contributing_bases'].items()),'','## Adaptation totals (eligible tests, class/instance recurrences)',
  '| Category | Stratum | Available | Tests | Class rec. | Instance rec. | Upstreams |','|---|---|---:|---:|---:|---:|---:|']
 for cat,groups in v['adaptation_totals'].items():
  for g,r in groups.items():lines.append('| '+' | '.join(map(str,[cat,g,r['available'],r['tests'],r['class_rec'],r['instance_rec'],r['upstreams']]))+' |')
 lines += ['','## RQ4 dFT versus RQ2 +Declared (exact pair-category-prompt identities, eligible comparisons)',
  '| Category | dFT | +Declared | Intersection | dFT only | +Declared only | Jaccard | Overlap class rec. | Overlap instance rec. | Verdict |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
 for cat,r in v['dft_vs_plus_declared'].items():lines.append('| '+' | '.join(map(str,[cat,r['dFT'],r['plus_declared'],r['intersection'],r['dFT_only'],r['plus_declared_only'],r['jaccard'],r['overlap_class_rec'],r['overlap_instance_rec'],r['verdict']]))+' |')
 lines += ['','## Revised Table VII model counts (set unions over canonical IDs; Finetune = ndFT ∪ dFT)',
  '| Category | Group | Bases | Affected der. | Tested der. | Tests | Class rec. | Instance rec. |','|---|---|---:|---:|---:|---:|---:|---:|']
 for cat,groups in v['table_vii'].items():
  for g,r in groups.items():lines.append('| '+' | '.join(map(str,[cat,g,r['bases'],r['affected'],r['tested_derivatives'],r['tests'],r['class_rec'],r['instance_rec']]))+' |')
 lines += ['','## Percentage formatting regression','| Two-decimal value | Published |','|---|---|',*('| '+x+' | '+y+' |' for x,y in v['percentage_regression'].items()),'',
  '## Lowercase manuscript-compatibility macros ('+str(len(v['legacy_macros']))+')',' '.join('\\'+n for n in v['legacy_macros']),'',
  '## Checks',*('- '+c['result']+' '+c['name']+': '+c['detail'] for c in v['checks']),'','## Unresolved differences',*(v['unresolved'] or ['None.']),'',
  'TeX: '+v['tex_compilation']+'.']
 return '\n'.join(lines)+'\n'


# ---------------------------------------------------------------------------------------------
# RQ5. Four populations never share a denominator:
#   FRAME      adaptation-scoped graph frame: selected upstreams + adapter/finetune/quantized/merged children
#   SENSITIVITY the frame as exported (adds models reachable only through new_version/converted memberships)
#   EVALUATED  the RQ2-RQ4 behavioral cohort (endpoints of the admitted prompt-paired relationships)
#   POSITIVE   evaluated models with >= 1 verified Pkg/NX/Mal artifact (concentration); Res is diagnostic only
RQ5_EXPORT=Path('<REDACTED_HOME>/icde_rq5_export')
RQ5_LINEAGE=Path('<REDACTED_HOME>/icde_rq5/inputs/rq5_v05_lineage/transfer/edges/csv/01_model_model_edges.csv')
RQ5_LEGACY_INTERFACE=Path('<REDACTED_HOME>/icde_rq5/macro_interface.json')
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


def rq5_macros(m,r,s,sid):
 """Legacy \\rqfive names keep their legacy display (thousands separators, -- replaced by N/A as in RQ2-RQ4);
 new Frame/Eval/Conc/EligDerivs/SharedBeyondLineage names are plain integers for \\icdecount."""
 fmt=lambda v:'N/A' if v is None else f'{int(v):,}'
 num=lambda v:'N/A' if v is None else (str(int(v)) if float(v).is_integer() else str(v))
 pct=lambda n,d:'N/A' if not d else f'{100*n/d:.2f}'
 cut=s['cutoff'];meta=r['meta']
 for k,v in [('SnapshotDate',cut[:10]),('SnapshotCutoff',datetime.fromisoformat(cut).strftime('%Y-%m-%d %H:%M:%S UTC')),('SnapshotID',sid),
             ('MethodVersion',s['verification_protocol'].get('version')),('GraphExportVersion',meta['export_version']),
             ('GraphSnapshotID',meta['snapshot_id'].replace('_','\\_')),('GraphSnapshotDate',meta['snapshot_date']),('SpaceMetadataDate',meta['space_metadata_date'])]:m.put('rqfive'+k,v)
 # Sensitivity frame (as exported) under the legacy Cohort* names (their original population).
 x=r['sens']
 for k,v in [('CohortModels',x['models']),('CohortBases',x['bases']),('CohortDerivs',x['derivatives']),('CohortPairs',r['sens_pairs']),('CohortModelsSpace',x['models_with_space']),
             ('CohortModelsAnyAssoc',x['models_with_any_association']),('CohortSpaces',x['spaces']),('CohortModelSpaceEdges',x['model_space_edges']),('CohortRepos',x['repos_union'])]:m.put('rqfive'+k,fmt(v))
 m.put('rqfiveCohortModelsSpacePct',pct(x['models_with_space'],x['models']))
 # Executed (tested) models: both-c1 verified responses at the cutoff.
 t=r['tested'];m.put('rqfiveTestedModels',fmt(t['models']));m.put('rqfiveTestedBases',fmt(t['bases']));m.put('rqfiveTestedDerivs',fmt(t['derivatives']))
 m.put('rqfiveTestedComplete',fmt(t['complete']));m.put('rqfiveTestedPartial',fmt(t['models']-t['complete']));m.put('rqfiveTestedResponses',fmt(s['execution_coverage']['both_c1_responses']))
 m.put('rqfiveTestedOutsideCohort',fmt(t['models_outside_graph_cohort']));m.put('rqfiveTestedCoveragePct',pct(t['models'],x['models']))
 m.put('rqfiveTestedModelsSpace',fmt(t['models_with_space']));m.put('rqfiveTestedModelsAnyAssoc',fmt(t['models_with_any_association']))
 # Positive models (concentration population) under the legacy E1/E2/skew names.
 p=r['positive']
 m.put('rqfivePosModels',fmt(p['models']))
 for cat,C in RQ5_CATS.items():
  if cat in RQ5_VERIFIED:m.put('rqfivePosModels'+C,fmt(p['per_category'][cat]))
 for k,v in [('PosBases',p['bases']),('PosDerivs',p['derivatives']),('PosFamilies',p['families']),('PosModelsSpace',p['models_with_space']),('PosBasesSpace',p['bases_with_space']),
             ('PosDerivsSpace',p['derivatives_with_space']),('Spaces',p['spaces']),('ModelSpaceEdges',p['model_space_edges']),('SpacesGitHub',p['spaces_with_github']),
             ('ReposViaSpace',p['repos_via_space']),('ReposDirect',p['repos_direct']),('ReposUnion',p['repos_union']),('ReposBoth',p['repos_both']),
             ('PosModelsDirectGitHub',p['models_with_direct_github']),('PosModelsSpaceGitHubPath',p['models_with_space_github_path']),('PosModelsAnyAssoc',p['models_with_any_association']),
             ('PathsModelSpaceGitHub',p['model_space_github_paths']),('PathsModelGitHub',p['model_github_paths'])]:m.put('rqfive'+k,fmt(v))
 m.put('rqfivePosModelsSpacePct',pct(p['models_with_space'],p['models']));m.put('rqfivePosModelsAnyAssocPct',pct(p['models_with_any_association'],p['models']))
 paths=p['model_space_edges']+p['model_space_github_paths']+p['model_github_paths']
 for k,v in [('AblModelsAssocModelOnly',0),('AblModelsAssocSpace',p['models_with_space']),('AblModelsAssocGitHub',p['models_with_any_association']),
             ('AblGainModelsSpace',p['models_with_space']),('AblGainModelsGitHub',p['models_with_any_association']-p['models_with_space']),('AblPathsModelOnly',0),
             ('AblPathsSpace',p['model_space_edges']),('AblPathsGitHub',paths),('AblGainPathsGitHub',paths-p['model_space_edges']),('AblReposModelOnly',0),('AblReposSpace',0),
             ('AblReposGitHub',p['repos_union']),('AblSpacesModelOnly',0),('AblSpacesSpace',p['spaces']),('AblSpacesGitHub',p['spaces'])]:m.put('rqfive'+k,fmt(v))
 m.put('rqfiveTopRole',ROLE_TEXT[p['top_role']]);m.put('rqfiveTopEdges',fmt(p['top_degree']))
 m.put('rqfiveTopEdgeSharePct',pct(p['top_degree'] or 0,p['total_edges']));m.put('rqfiveTopThreeEdgeSharePct',pct(p['top3_edges'],p['total_edges']))
 e=p['excl_top'] or {}
 for k,v in [('ExclTopPosModels','models'),('ExclTopPosModelsSpace','models_with_space'),('ExclTopSpaces','spaces'),('ExclTopEdges','model_space_edges'),('ExclTopSpacesGitHub','spaces_with_github'),
             ('ExclTopReposViaSpace','repos_via_space'),('ExclTopReposDirect','repos_direct'),('ExclTopReposUnion','repos_union'),('ExclTopPosModelsAnyAssoc','models_with_any_association')]:m.put('rqfive'+k,fmt(e.get(v)))
 m.put('rqfiveExclTopFamilies',fmt(p['excl_top_families']))
 # Behavioral findings (Declared-eligible parent-child-prompt comparisons; derivative level).
 m.put('rqfiveRecPolicy','Declared')
 for cat,C in RQ5_CATS.items():
  b=r['behavior'][cat];ir=b['instance_reach'];sh=b['shared']
  m.put('rqfiveRecDerivs'+C,fmt(len(b['instance_recurrent'])));m.put('rqfiveRecEligibleDerivs'+C,fmt(len(b['eligible'])));m.put('rqfiveRecDerivsSpace'+C,fmt(ir['models_with_space']))
  m.put('rqfiveShared'+C,fmt(sh['shared']));m.put('rqfiveSharedSpace'+C,fmt(sh['reaching_space']));m.put('rqfiveSharedEmitMed'+C,num(sh['emit_median']));m.put('rqfiveSharedEmitMax'+C,fmt(sh['emit_max']))
  if C!='Mal':m.put('rqfiveEligDerivs'+C,len(b['eligible']))
  m.put('rqfiveSharedBeyondLineage'+C,sh['beyond_lineage']);m.put('rqfiveSharedEmitCell'+C,'N/A' if sh['emit_median'] is None else num(sh['emit_median'])+' ('+fmt(sh['emit_max'])+')')
  # Table VIII display cells: instance recurrence is not estimable (N/A) without an eligible derivative; 0 stays 0 otherwise.
  m.put('rqfiveRecDerivsCell'+C,len(b['instance_recurrent']) if b['eligible'] else 'N/A')
  m.put('rqfiveRecDerivsSpaceCell'+C,ir['models_with_space'] if b['eligible'] else 'N/A')
  if C in ('Pkg','Nx'):
   for k,v in [('RecClassDerivs',len(b['class_recurrent'])),('RecSpaces',ir['spaces']),('RecReposUnion',ir['repos_union']),('RecDerivsAnyAssoc',ir['models_with_any_association']),
               ('RecFamilies',b['instance_families']),('SharedRepo',sh['reaching_repo']),('SharedTop',sh['by_top']),('SharedSpaceExclTop',sh['reaching_space_excl_top']),
               ('SharedSpaceMax',sh['spaces_max']),('SharedRec',b['shared_recurrence']['shared'])]:m.put('rqfive'+k+C,fmt(v))
   m.put('rqfiveRecDerivsPct'+C,pct(len(b['instance_recurrent']),len(b['eligible'])));m.put('rqfiveSharedSpacePct'+C,pct(sh['reaching_space'],sh['shared']))
   m.put('rqfiveSharedSpaceMed'+C,num(sh['spaces_median']))
  if C!='Res':m.put('rqfiveArtifacts'+C,fmt(sh['artifacts']))
 m.put('rqfiveEligDerivsMal',len(r['behavior']['malicious_url']['eligible']))
 # New unambiguous namespaces for Table VIII.
 for pre,x,pairs_n in (('rqfiveFrame',r['frame'],r['frame_pairs']),('rqfiveEval',r['eval'],r['eval_pairs'])):
  for k,v in [('Models',x['models']),('Bases',x['bases']),('Derivs',x['derivatives']),('Pairs',pairs_n),('SpaceModels',x['models_with_space']),('Spaces',x['spaces']),
              ('ModelSpaceEdges',x['model_space_edges']),('SpaceOrGitModels',x['models_with_any_association']),('GitRepos',x['repos_union']),
              ('GitReposDirect',x['repos_direct']),('GitReposViaSpace',x['repos_via_space'])]:m.put(pre+k,v)
 m.put('rqfiveFrameExclModels',len(r['excluded_models']));m.put('rqfiveFrameExclPairs',len(r['excluded_memberships']))
 for k in ('SpaceModels','SpaceOrGitModels','GitRepos'):m.put('rqfive'+k,m.values['rqfiveEval'+k])    # requested evaluated-cohort names
 for k,v in [('ConcModels',p['models']),('ConcSpaceModels',p['models_with_space']),('ConcEdges',p['total_edges']),('ConcSpaces',p['spaces'])]:m.put('rqfive'+k,v)


def rq5_table():
 """Table VIII: every statistic is a macro of rq5_numbers_codex.tex; only labels and definitions are literal."""
 cells=lambda f:' & '.join(f(C) for C in ('Pkg','Nx','Mal','Res'))
 ic=lambda n:'\\icdecount{\\rqfive'+n+'}'
 assoc=[('Models','Models'),('\\quad upstream / derivative',None),('Adaptation pairs','Pairs'),('Models with a Space','SpaceModels'),('Distinct Spaces','Spaces'),
        ('Models with Space or GitHub','SpaceOrGitModels'),('GitHub repositories$^\\ddagger$','GitRepos')]
 lines=[r'\begin{table}[t]',r'\centering',
  r'\caption{RQ5: recorded heterogeneous associations and security findings. \emph{Graph frame}: adaptation-scoped text-generation models (selected upstreams and their one-hop adapter, fine-tune, quantized or merged derivatives); \emph{Evaluated}: the RQ2--RQ4 behavioral cohort. Findings use the evaluated cohort only: eligible derivatives have an upstream-positive comparison under \rqfiveRecPolicy{} lineage evidence; reproducing derivatives repeat the parent'+"'"+r's identical canonical artifact on the same prompt (instance level); shared artifacts are emitted by at least two evaluated models. Concentration: evaluated models with a verified finding and their Model$\to$Space edges. PkgH: package hallucination; NX: registrable NXDOMAIN; Mal: exact malicious URL; Res.$^\dagger$: restricted namespace (diagnostic). $^\ddagger$Direct Model$\to$GitHub or Model$\to$Space$\to$GitHub. 0: no qualifying observation; N/A: not estimable (no eligible comparison or no shared artifact). Recorded links do not establish deployment, artifact consumption, exploitation or causal inheritance.}',
  r'\label{tab:rq5}',r'\footnotesize',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular}{@{}lrrrr@{}}',r'\toprule',
  r'\textbf{Associations} & & & \textbf{Frame} & \textbf{Evaluated} \\',r'\midrule']
 for label,k in assoc:
  if k is None:lines.append(label+' & & & '+ic('FrameBases')+'/'+ic('FrameDerivs')+' & '+ic('EvalBases')+'/'+ic('EvalDerivs')+r' \\')
  else:lines.append(label+' & & & '+ic('Frame'+k)+' & '+ic('Eval'+k)+r' \\')
 lines += [r'\midrule',r'\textbf{Findings} & \textbf{PkgH} & \textbf{NX} & \textbf{Mal} & \textbf{Res.$^\dagger$} \\',r'\midrule',
  'Eligible derivatives & '+cells(lambda C:ic('EligDerivs'+C))+r' \\',
  'Reproducing derivatives & '+cells(lambda C:ic('RecDerivsCell'+C))+r' \\',
  r'\quad with a Space link & '+cells(lambda C:ic('RecDerivsSpaceCell'+C))+r' \\',
  'Shared artifacts & '+cells(lambda C:ic('Shared'+C))+r' \\',
  r'\quad emitters, med.\ (max) & '+cells(lambda C:'\\rqfiveSharedEmitCell'+C)+r' \\',
  r'\quad with a Space-linked emitter & '+cells(lambda C:ic('SharedSpace'+C))+r' \\',
  r'\midrule',r'\textbf{Concentration} & & & & \\',r'\midrule',
  'Positive models (with a Space) & & & & '+ic('ConcModels')+' ('+ic('ConcSpaceModels')+r') \\',
  r'Their Model$\to$Space edges & & & & '+ic('ConcEdges')+r' \\',
  r'Top model'+"'"+r's edge share & & & & \rqfiveTopEdgeSharePct\% \\',
  'Spaces (without top model) & & & & '+ic('ConcSpaces')+' ('+ic('ExclTopSpaces')+r') \\',
  r'\bottomrule',r'\end{tabular}',r'\end{table}']
 return ('\n'.join(lines)+'\n').encode()


def rq5_discussion():
 return (r'\paragraph{RQ5: heterogeneous supply-chain context}'+'\n'
  r'The graph frame of \icdecount{\rqfiveFrameModels} adaptation-scoped models (\icdecount{\rqfiveFrameBases} upstreams, \icdecount{\rqfiveFrameDerivs} derivatives, \icdecount{\rqfiveFramePairs} adaptation pairs) records \icdecount{\rqfiveFrameSpaceModels} models with a Space link to \icdecount{\rqfiveFrameSpaces} distinct Spaces and \icdecount{\rqfiveFrameGitRepos} GitHub repositories reached directly or through Spaces. '
  r'Of the \icdecount{\rqfiveEvalModels} evaluated models, \icdecount{\rqfiveEvalSpaceModels} link to \icdecount{\rqfiveEvalSpaces} Spaces and \icdecount{\rqfiveEvalSpaceOrGitModels} have a Space or GitHub link (\icdecount{\rqfiveEvalGitRepos} repositories, \icdecount{\rqfiveEvalGitReposDirect} of them directly referenced). '
  r'Behavioral results are reported only for the evaluated cohort: under \rqfiveRecPolicy{} evidence, \icdecount{\rqfiveRecDerivsPkg} of \icdecount{\rqfiveEligDerivsPkg} eligible derivatives reproduce an identical parent package artifact and \icdecount{\rqfiveRecDerivsNx} of \icdecount{\rqfiveEligDerivsNx} an identical NXDOMAIN artifact; only \icdecount{\rqfiveRecDerivsSpacePkg} and \icdecount{\rqfiveRecDerivsSpaceNx} of these derivatives have a recorded Space link. '
  r'Exact artifacts are also widely shared: \icdecount{\rqfiveSharedPkg} package and \icdecount{\rqfiveSharedNx} NXDOMAIN artifacts are emitted by at least two evaluated models (median \rqfiveSharedEmitMedPkg{} and \rqfiveSharedEmitMedNx{} emitters), \icdecount{\rqfiveSharedSpacePkg} and \icdecount{\rqfiveSharedSpaceNx} of them by at least one Space-linked model, and \icdecount{\rqfiveSharedBeyondLineagePkg} and \icdecount{\rqfiveSharedBeyondLineageNx} by models with no recorded lineage path between them. '
  r'Shared artifacts and recurrent derivatives use different counting units and must not be equated. Exact malicious-URL recurrence is not estimable because no eligible upstream-positive comparison exists; restricted-namespace observations remain diagnostic. '
  r'Space exposure among the \icdecount{\rqfiveConcModels} verified-positive evaluated models is concentrated: \rqfiveTopRole{} holds \rqfiveTopEdgeSharePct\% of their \icdecount{\rqfiveConcEdges} Model$\to$Space edges, and removing it reduces their linked Spaces from \icdecount{\rqfiveConcSpaces} to \icdecount{\rqfiveExclTopSpaces}.'+'\n\n'
  r'\noindent\textbf{Insight \#5.} Heterogeneous graph context adds information that model lineage alone does not provide: identical security-relevant artifacts recur along recorded adaptations, also appear beyond recorded lineage connectivity, and a small number of upstream models account for much of the recorded Space exposure. These are recorded associations; they indicate potential downstream exposure pathways, not deployment, artifact consumption, exploitation or causal inheritance.'+'\n').encode()


def rq5_table_checks(r,values,table,check):
 """Table VIII: macro-only, defined, frame/evaluated populations, four categories, N/A versus 0."""
 refs=set(re.findall(r'\\(rqfive[A-Za-z]+)',table))
 check('table.every_referenced_macro_defined',refs<=set(values),'undefined: '+','.join(sorted(refs-set(values))) if refs-set(values) else f'{len(refs)} macros')
 check('table.no_legacy_rq5_export_dependency','rq5_numbers_claude' not in table,'no reference to rq5_numbers_claude')
 check('table.associations_use_frame_not_sensitivity',not any(n.startswith('rqfiveCohort') for n in refs) and {'rqfiveFrameModels','rqfiveEvalModels'}<=refs
       and values['rqfiveFrameModels']==str(len(r['frame_set'])),f"frame {values['rqfiveFrameModels']}; no rqfiveCohort* in table")
 check('table.findings_use_evaluated_population',values['rqfiveEvalModels']==str(len(r['eval_set'])) and all(values['rqfiveEligDerivs'+C]==str(len(r['behavior'][c]['eligible'])) for c,C in RQ5_CATS.items()),
       f"evaluated {values['rqfiveEvalModels']}")
 check('table.four_categories_and_label',all(h in table for h in (r'\textbf{PkgH}',r'\textbf{NX}',r'\textbf{Mal}',r'\textbf{Res.$^\dagger$}')) and r'\label{tab:rq5}' in table
       and r'\begin{tabular}{@{}lrrrr@{}}' in table,'PkgH/NX/Mal/Res., tab:rq5, @{}lrrrr@{}')
 for c,C in RQ5_CATS.items():
  b=r['behavior'][c];sh=b['shared']
  want=(str(len(b['instance_recurrent'])),str(b['instance_reach']['models_with_space'])) if b['eligible'] else ('N/A','N/A')
  check(f'table.{C}.recurrence_cells_na_only_when_not_estimable',(values['rqfiveRecDerivsCell'+C],values['rqfiveRecDerivsSpaceCell'+C])==want,f'{want} with {len(b["eligible"])} eligible')
  check(f'table.{C}.shared_counts_are_observed_counts',(values['rqfiveShared'+C],values['rqfiveSharedSpace'+C])==(f"{sh['shared']:,}",f"{sh['reaching_space']:,}"),f"{sh['shared']} shared")
  check(f'table.{C}.emitter_cell_na_iff_no_shared',(values['rqfiveSharedEmitCell'+C]=='N/A')==(sh['shared']==0),values['rqfiveSharedEmitCell'+C])


def rq5_validation(r,s,values,table=None):
 checks=[];failures=[]
 def check(name,ok,detail):
  checks.append({'name':name,'result':'PASS' if ok else 'FAIL','detail':detail})
  if not ok:failures.append(name+': '+detail)
 fr,ev,se,ps=r['frame_set'],r['eval_set'],set(r['sens_set']),r['positive']['set']
 # Graph-association population (frame) versus behavioral population (evaluated): subset, never shared denominators.
 check('frame.excluded_memberships_are_new_version_or_converted',all(l in ('new_version','converted') for p,c,l in r['excluded_memberships']),
       f"{len(r['excluded_memberships'])} excluded memberships")
 check('frame.adaptation_pairs_have_adaptation_labels',all(l in ('adapter','finetune','quantized','merged') for p,c,l,x in r['frame_rows']),f"{r['frame_pairs']} frame pairs")
 check('frame.subset_of_sensitivity_frame',fr<=se and len(se-fr)==len(r['excluded_models']),f'{len(fr)} of {len(se)}; {len(r["excluded_models"])} excluded')
 check('frame.excluded_models_only_via_excluded_memberships',all(m not in fr for m in r['excluded_models']),'excluded models have no adaptation membership')
 check('frame.sensitivity_eq_capture_selection',len(se)==s['selected_model_ids'] and r['sens_pairs']-len(r['excluded_memberships'])==s['selected_adaptation_pairs'],
       f"{len(se)}/{s['selected_model_ids']} models; {r['sens_pairs']-len(r['excluded_memberships'])}/{s['selected_adaptation_pairs']} pairs")
 check('evaluated.subset_of_frame',ev<=fr and r['eval_pair_set']<=r['frame_pair_set'],f'{len(ev&fr)}/{len(ev)} models, {len(r["eval_pair_set"]&r["frame_pair_set"])}/{len(r["eval_pair_set"])} pairs')
 check('evaluated.eq_rq2_rq4_cohort',len(ev)==s['cohort']['values']['UniqueModels'] and r['eval_pairs']==s['cohort']['values']['Pairs'],f"{len(ev)} models, {r['eval_pairs']} pairs")
 for k in ('models_with_space','spaces','model_space_edges','models_with_any_association','repos_union','repos_direct','repos_via_space'):
  check(f'denominators.eval_{k}_le_frame',r['eval'][k]<=r['frame'][k]<=r['sens'][k],f"{r['eval'][k]} <= {r['frame'][k]} <= {r['sens'][k]}")
 check('denominators.eval_targets_subset_of_frame_targets',r['eval']['space_set']<=r['frame']['space_set'] and r['eval']['repo_set']<=r['frame']['repo_set'],'Spaces and repositories')
 check('denominators.git_repos_union_eq_direct_plus_via_minus_both',all(x['repos_union']==x['repos_direct']+x['repos_via_space']-x['repos_both'] for x in (r['frame'],r['eval'],r['sens'])),'union identity')
 for pre,x in (('rqfiveFrame',r['frame']),('rqfiveEval',r['eval'])):
  check(pre+'.macros_from_own_population',[values[pre+k] for k in ('Models','SpaceModels','Spaces','SpaceOrGitModels','GitRepos')]==[str(x[k]) for k in ('models','models_with_space','spaces','models_with_any_association','repos_union')],pre)
 check('joins.graph_ids_canonical',set(r['graph_ms_models'])<=se and set(r['graph_mg_models'])<=se,'Model->Space/GitHub model IDs are frame model IDs')
 # Behavioral population.
 for cat,C in RQ5_CATS.items():
  b=r['behavior'][cat];t=s['rq4'][cat]['Overall']
  check(f'{C}.eligible_derivs_eq_rq4_tested',len(b['eligible'])==t['derivatives'],f"{len(b['eligible'])} vs {t['derivatives']}")
  check(f'{C}.comparisons_eq_rq3',b['comparisons']==s['rq3'][cat]['tests'],f"{b['comparisons']} vs {s['rq3'][cat]['tests']}")
  check(f'{C}.instance_subset_class_subset_eligible_subset_evaluated',b['instance_recurrent']<=b['class_recurrent']<=b['eligible']<=ev,
        f"{len(b['instance_recurrent'])} <= {len(b['class_recurrent'])} <= {len(b['eligible'])}")
  check(f'{C}.emitters_are_evaluated_models',b['emitters']<=ev,f"{len(b['emitters']-ev)} outside")
  check(f'{C}.shared_two_plus_emitters',b['shared']['shared']==0 or b['shared']['emit_min']>=2,f"min {b['shared']['emit_min']}")
  check(f'{C}.shared_bounds',b['shared']['reaching_space']<=b['shared']['shared']<=b['shared']['artifacts'] and b['shared']['all_unlinked']<=b['shared']['beyond_lineage']<=b['shared']['shared'],'bounds')
  check(f'{C}.recurrence_artifacts_subset_shared',b['shared_recurrence']['shared']<=b['shared']['shared'],f"{b['shared_recurrence']['shared']} <= {b['shared']['shared']}")
  if cat=='malicious_url':check('Mal.nonestimable_without_eligible',len(b['eligible'])>0 or values['rqfiveSharedEmitCellMal']=='N/A' and values.get('rqfiveRecDerivsPctMal') is None,'no 0% reported')
 # Concentration population.
 p=r['positive']
 check('conc.positive_subset_evaluated',ps<=ev,f'{len(ps)} models')
 check('conc.restricted_namespace_excluded',ps=={m for c in RQ5_VERIFIED for m in r['behavior'][c]['emitters']},'M+ from Pkg/NX/Mal only')
 check('conc.denominator_is_positive_model_edges',p['total_edges']==p['model_space_edges'] and values['rqfiveConcEdges']==str(p['total_edges']),f"{p['total_edges']} edges")
 check('conc.top_in_positive_and_share_bounds',p['top'] in ps and 0<p['top_degree']<=p['total_edges'] and (p['excl_top'] or {}).get('spaces',0)<=p['spaces'],f"{p['top']} {p['top_degree']}")
 check('format.percentages_trimmed',all(not re.fullmatch(r'-?\d+\.(\d*0)',v) for n,v in values.items() if 'Pct' in n),'no insignificant trailing zeros')
 if table is not None:rq5_table_checks(r,values,table,check)
 return checks,failures


def rq5_inventory(values):
 """Legacy interface classification: regenerated (same meaning) or not regenerated (with the migration)."""
 legacy=json.loads(RQ5_LEGACY_INTERFACE.read_text())['names'];rows=[]
 for n in legacy:
  name='rqfive'+n
  if name in values:status,note='regenerated','same definition; current pinned sources'
  elif n.startswith('Lin'):status,note='historical','E2 lineage-connectivity/expanded-reach analysis of the legacy pipeline; not recomputed for the unified cohort. Remove or cite as historical (no current value).'
  elif n=='NonPosTestedModels':status,note='historical','would mix executed (both-c1) and evaluated populations; use rqfiveTestedModels and rqfiveConcModels separately.'
  else:status,note='historical','definition not reproduced by the unified export; remove from the manuscript.'
  rows.append({'macro':name,'status':status,'note':note,'value':values.get(name)})
 return rows,a.sha(RQ5_LEGACY_INTERFACE)


def rq5_audit_text(v):
 r=v['results'];lines=['# RQ5 unified audit','',v['snapshot_id']+'; cutoff '+v['cutoff'],'Capture '+v['capture_manifest']+' (SHA256 '+v['capture_manifest_sha256']+'); ledger SHA256 '+v['ledger_sha256'],
  'Graph export '+v['graph']['export_version']+' ('+v['graph']['snapshot_id']+'; Space metadata '+v['graph']['space_metadata_date']+'; independent of the response cutoff).',
  'Result: **'+v['status']+'** ('+str(sum(c['result']=='PASS' for c in v['checks']))+'/'+str(len(v['checks']))+' checks pass)','','## Populations (never share denominators)',
  '| Population | Rule | Models | Pairs |','|---|---|---:|---:|',
  '| Graph frame (primary) | selected upstreams + adapter/finetune/quantized/merged one-hop children | '+str(r['frame']['models'])+' | '+str(r['frame_pairs'])+' |',
  '| Sensitivity frame | as exported; also models reachable only via new_version/converted memberships | '+str(r['sens']['models'])+' | '+str(r['sens_pairs'])+' |',
  '| Evaluated | endpoints of admitted prompt-paired relationships (RQ2-RQ4) | '+str(r['eval']['models'])+' | '+str(r['eval_pairs'])+' |',
  '| Executed (tested) | models with both-c1 verified responses | '+str(r['tested']['models'])+' | - |',
  '| Verified-positive (concentration) | evaluated models with a verified Pkg/NX/Mal artifact | '+str(r['positive']['models'])+' | - |','',
  '## Graph-frame sensitivity (adaptation-scoped primary frame vs as-exported frame)','| Quantity | Primary | Sensitivity | Difference |','|---|---:|---:|---:|']
 for k in ('models','bases','derivatives','models_with_space','spaces','model_space_edges','models_with_any_association','repos_direct','repos_via_space','repos_union'):
  lines.append('| '+k+' | '+str(r['frame'][k])+' | '+str(r['sens'][k])+' | '+str(r['sens'][k]-r['frame'][k])+' |')
 lines += ['','Excluded memberships: '+'; '.join(f'{p} -> {c} ({l})' for p,c,l in r['excluded_memberships']),'','Models only reachable through them:',
  '| Model | Role | Spaces | Spaces not linked by any frame model | Direct GitHub |','|---|---|---:|---:|---:|',
  *('| '+d['model_id']+' | '+d['role']+' | '+str(d['spaces'])+' | '+str(d['spaces_unique_to_model'])+' | '+str(d['github_direct'])+' |' for d in r['excluded_detail']),
  '','The difference is material because a few of these converted/new-version models are themselves heavily used by Spaces: their Space links are not shared with any adaptation-scoped model, so excluding them removes those Spaces and Space-mediated repositories entirely. The as-exported frame remains a valid sensitivity population (legacy rqfiveCohort* macros).',
  '','## Behavioral findings (Declared-eligible parent-child-prompt comparisons; derivative and artifact levels)',
  '| | Pkg | NX | Mal | Res (diag.) |','|---|---:|---:|---:|---:|']
 B=r['behavior'];cats=list(RQ5_CATS)
 for label,f in [('Eligible comparisons',lambda b:b['comparisons']),('Eligible derivatives (= RQ4 tested)',lambda b:b['eligible']),('Class-recurrent derivatives',lambda b:b['class_recurrent']),
                 ('Instance-recurrent derivatives',lambda b:b['instance_recurrent']),('... with a Space link',lambda b:b['instance_reach']['models_with_space']),
                 ('Distinct artifacts (all verified responses of evaluated models)',lambda b:b['shared']['artifacts']),('Shared artifacts (>=2 evaluated emitters)',lambda b:b['shared']['shared']),
                 ('Emitters median / max',lambda b:f"{b['shared']['emit_median']} / {b['shared']['emit_max']}"),('Shared with a Space-linked emitter',lambda b:b['shared']['reaching_space']),
                 ('Shared beyond recorded lineage (>=1 emitter pair without a path)',lambda b:b['shared']['beyond_lineage']),('Shared with all emitters mutually unlinked',lambda b:b['shared']['all_unlinked']),
                 ('Artifacts recurring on instance-positive Declared comparisons',lambda b:b['shared_recurrence']['shared'])]:
  lines.append('| '+label+' | '+' | '.join(str(f(B[c])) for c in cats)+' |')
 p=r['positive']
 lines += ['','Recorded-lineage statistic: undirected connected components over all '+f"{r['lineage_edges']:,}"+' recorded model-model lineage edges of the frozen graph (every edge type, including new_version/converted). An artifact is beyond recorded lineage when at least one pair of its emitters lies in different components (no recorded path in either direction). This shows occurrence beyond recorded lineage connectivity, not causal or biological independence; lineage records are incomplete.',
  '','## Concentration','Population: '+str(p['models'])+' verified-positive evaluated models ('+str(p['models_with_space'])+' with a Space link); denominator: their '+str(p['total_edges'])+' Model->Space edges.',
  'Top model: '+str(p['top'])+' ('+str(p['top_role'])+'), '+str(p['top_degree'])+' edges; linked Spaces '+str(p['spaces'])+' -> '+str((p['excl_top'] or {}).get('spaces'))+' without it.',
  '','## Validation',*('- '+c['result']+' '+c['name']+': '+c['detail'] for c in v['checks']),'',
  '## Legacy macro compatibility ('+str(len(v['inventory']))+' legacy names; manuscript usage NOT VERIFIED - the manuscript is not on this server)',
  '| Macro | Status | Value | Note |','|---|---|---|---|',*('| \\'+x['macro']+' | '+x['status']+' | '+str(x['value'])+' | '+x['note']+' |' for x in v['inventory']),'',
  '## New macros','Frame (graph frame): '+' '.join('\\'+n for n in v['new_macros'] if n.startswith('rqfiveFrame')),'',
  'Evaluated cohort: '+' '.join('\\'+n for n in v['new_macros'] if n.startswith('rqfiveEval') or n in ('rqfiveSpaceModels','rqfiveSpaceOrGitModels','rqfiveGitRepos')),'',
  'Behavioral: '+' '.join('\\'+n for n in v['new_macros'] if n.startswith(('rqfiveEligDerivs','rqfiveSharedBeyondLineage','rqfiveSharedEmitCell'))),'',
  'Concentration: '+' '.join('\\'+n for n in v['new_macros'] if n.startswith('rqfiveConc')),'',
  'rqfiveSpaces keeps its legacy meaning (Spaces linked to verified-positive models); evaluated-cohort Spaces are rqfiveEvalSpaces.','',
  '## Regeneration','Replay this capture: `python3 -B '+str(WORK/'generate_rq2_analysis.py')+' --source '+v['capture_manifest']+'`',
  'Deliberately adopt a new validated capture: `python3 -B '+str(WORK/'generate_rq2_analysis.py')+'` (new capture; review before replacing Overleaf files).','',
  'TeX: '+v['tex_compilation']+'.']
 return '\n'.join(lines)+'\n'


def build(s,context,frozen,pairs,models,comparisons,model_audit,pair_audit,occurrences):
 sid=s['snapshot_id'];comment=sid+'; '+s['cutoff']+'; primary prompt-level eligibility, Declared recurrence.'
 evalm=Macros(comment);m2=Macros(comment);m3=Macros(comment);m4=Macros(comment);m5=Macros(comment)
 c=s['cohort']['values'];cut=s['cutoff'].split('T')[0]
 for key in ['Bases','FT','AD','QT','Merge','UniqueDerivs','UniqueModels','Overlap','Pairs']:evalm.put('Eval'+key,c[key])
 evalm.put('EvalModels',c['UniqueModels']);evalm.put('EvalTotal',c['UniqueModels']);evalm.put('EvalResponses',s['cohort_verified_responses']);evalm.put('EvalAsOf',cut)
 for suffix,v in [('Models',s['execution_coverage']['complete_both_c1_models']),('Bases',s['model_role_counts']['whole_bank_upstreams']),('UniqueDerivs',s['model_role_counts']['whole_bank_derivatives']),('Responses',sum(r['verified_both_c_one_prompts'] for r in model_audit if r['whole_bank_complete']))]:evalm.put('EvalRQThree'+suffix,v)
 m2.put('rqTwoAsOf',cut);m2.put('rqTwoEligiblePairs',c['Pairs']);m2.put('rqTwoModels',c['UniqueModels'])
 for p in a.POLICIES:
  tag=a.TAGS[p];ref=s['frozen_graph_reference']['counts'][p]
  m2.put('rqTwoGraph'+tag+'Records',ref['labeled_records']);m2.put('rqTwoGraph'+tag+'Pairs',ref['distinct_pairs'])
  for scope,label in [('cumulative',''),('added','Added')]:
   cov=s['coverage'][p][scope];pre='rqTwo'+tag+label
   for key,name in [('pairs','Pairs'),('records','Records'),('bases','Bases'),('derivatives','Derivs')]:m2.put(pre+name,cov[key])
   m2.put(pre+'Coverage',f"{cov['coverage_pct']:.2f}")
   for cat,(code,_) in a.CATEGORIES.items():m2.group(pre+code,s['rq2'][p][scope][cat])
 m3.put('RQThreeAsOf',cut);m3.put('RQThreePrimaryPolicy','Declared');m4.put('RQFourAsOf',cut)
 primaryparents={m['parent_id'] for m in pairs.values() if m['in_declared']=='1'}
 for cat,(code,_) in a.CATEGORIES.items():
  m3.group('RQThree'+code,s['rq3'][cat]);oc=s['occurrences'][cat]
  m3.put('RQThree'+code+'Occ',oc['occurrences']);m3.put('RQThree'+code+'Distinct',oc['distinct_artifacts'])
  m3.put('RQThree'+code+'UpstreamPositivePrompts',sum(r[code+'_upstream_positive_prompts'] for r in model_audit if r['model_id'] in primaryparents))
  for group,r in s['rq4'][cat].items():
   m4.group('RQFour'+code+group,r)
   for metric,tag in [('class','Class'),('instance','Instance')]:
    bounds=r['uncertainty'].get(metric+'_interval')
    m4.put('RQFour'+code+group+tag+'Interval','N/A' if bounds is None else '['+rate(bounds[0])+', '+rate(bounds[1])+']')
  for scope,label in [('prompt_level','Prompt'),('whole_bank','Whole')]:m3.group('RQThree'+code+label,s['scope_sensitivity'][cat][scope])
 rq4_legacy_aliases(m4,s['rq4']);rq4_table_vii_macros(m4,comparisons)
 # Backward-compatible VALID recurrence aliases, explicitly migrated to shared N.
 for p in a.POLICIES:
  tag={'strict':'Strict','intermediate':'Inter','declared':'Decl','extended':'Ext'}[p]
  for cat,(code,_) in a.CATEGORIES.items():
   legacy='Res' if code=='Restricted' else code;r=s['rq2'][p]['cumulative'][cat]
   for letter in ('C','I'):m3.put('rqthreeTriples'+letter+legacy+tag,r['tests'])
   m3.put('rqthreePsi'+legacy+tag,'N/A' if r['class_rate'] is None else rate(r['class_rate'])+r'\%')
   m3.put('rqthreeSigma'+legacy+tag,'N/A' if r['instance_rate'] is None else rate(r['instance_rate'])+r'\%')
   m3.put('rqthreeBases'+legacy+tag,r['upstreams'])
 rq3_compatibility_aliases(m3,s)
 m3.put('rqthreeSnapshotDate',cut)
 # Existing completion-overview names retain WHOLE-BANK semantics; do not silently
 # turn those historical names into prompt-paired model counts.
 for suffix,value in [('Models',s['execution_coverage']['complete_both_c1_models']),('Bases',s['model_role_counts']['whole_bank_upstreams']),('Derivs',s['model_role_counts']['whole_bank_derivatives'])]:m3.put('rqthreeEval'+suffix,value)
 whole_responses=sum(r['verified_both_c_one_prompts'] for r in model_audit if r['whole_bank_complete'])
 m3.put('rqthreeResponsesAll',whole_responses);m3.put('rqthreeResponsesValidAll',whole_responses)
 for link,groups in s['rq5_scope_audit']['association_counts'].items():
  typ,pop=link.split('/');pre='RQFiveScope'+('GitHub' if 'github' in typ else 'Space')+{'prompt_paired':'Prompt','whole_bank':'Whole','recurrence_positive_derivatives':'Recurrent'}[pop]
  for key,tag in [('association_records','Records'),('model_ids','Models'),('target_ids','Targets')]:m5.put(pre+tag,groups[key])
 files={'evaluated_cohort_numbers.tex':evalm.text(),'rq2_numbers_codex.tex':m2.text(),'rq3_numbers_codex.tex':m3.text(),'rq4_numbers_codex.tex':m4.text(),'rq5_scope_numbers.tex':m5.text(),
  'graph_cohort_numbers.tex':(ROOT/'graph_cohort_numbers.tex').read_bytes(),'table2_icdecount.tex':(ROOT/'table2_icdecount.tex').read_bytes()}
 graph_values=dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([^\n]*)\}',files['graph_cohort_numbers.tex'].decode()))
 for stage,values in frozen['counts'].items():
  for key in ('Bases','FT','AD','QT','Merge','UniqueDerivs','UniqueModels'):
   a.require(graph_values[stage+key]==str(values[key]),'Frozen graph macro differs from verified baseline')
 tableii=[r'\begin{table}[t]',r'\centering',r'\caption{Unique text-generation models across identification, readiness and evaluation. Evaluated pairs share at least one completed, verified prompt; whole-bank completion is not required. Categories may overlap; totals are model-ID unions.}',r'\label{tab:graph-cohort}',r'\setlength{\tabcolsep}{3pt}',r'\resizebox{\columnwidth}{!}{%',r'\begin{tabular}{lrrrrrr}',r'\toprule',r'Stage & Base & FT & AD & QT & Merge & Total \\',r'\midrule']
 for label,pre in [('1-hop der.','OneHop'),('Static-ready','Ready'),('Evaluated','Eval')]:tableii.append(label+' & '+' & '.join(count(pre+x) for x in ['Bases','FT','AD','QT','Merge','UniqueModels'])+r' \\')
 tableii += [r'\bottomrule',r'\end{tabular}%','}',r'\end{table}'];files['graph_cohort_table.tex']=('\n'.join(tableii)+'\n').encode()
 policy=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\caption{RQ2: evidence-policy coverage of the same prompt-paired inventory and recurrence on fixed responses. Tests are shared by class and instance estimators; values in parentheses are percentages.}',r'\label{tab:rqtwopolicy}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{lrrrrrrrr}',r'\toprule',r'Policy & Pairs & Retention (\%) & Bases & Pkg tests & Pkg class/instance (\%) & NX tests & NX class/instance (\%) & Added \\',r'\midrule']
 for p in a.POLICIES:
  pre='rqTwo'+a.TAGS[p]
  policy.append(a.TAGS[p]+' & '+' & '.join([count(pre+'Pairs'),'\\'+pre+'Coverage',count(pre+'Bases'),count(pre+'PkgTests'),'\\'+pre+'PkgClassRate / \\'+pre+'PkgInstanceRate',count(pre+'NxTests'),'\\'+pre+'NxClassRate / \\'+pre+'NxInstanceRate',count(pre+'AddedPairs')])+r' \\')
 policy += [r'\bottomrule',r'\end{tabular}%','}',r'\end{table*}'];files['rq2_policy_table.tex']=('\n'.join(policy)+'\n').encode()
 graph=[r'\begin{table}[t]',r'\centering',r'\caption{Frozen historical graph-wide policy references. Original policy evidence remains unavailable; the local four-type graph independently corroborates only the Extended structural totals.}',r'\label{tab:rqtwograph}',r'\begin{tabular}{lrr}',r'\toprule',r'Policy & Labeled records & Distinct pairs \\',r'\midrule']
 for p in a.POLICIES:
  pre='rqTwoGraph'+a.TAGS[p];graph.append(a.TAGS[p]+' & '+count(pre+'Records')+' & '+count(pre+'Pairs')+r' \\')
 graph += [r'\bottomrule',r'\end{tabular}',r'\end{table}'];files['rq2_graph_policy_table.tex']=('\n'.join(graph)+'\n').encode()
 recurrence=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\caption{RQ2 cumulative-policy and newly admitted-stratum recurrence. Both estimators use exactly the same determinate tests. Restricted namespace is diagnostic; N/A denotes no eligible tests.}',r'\label{tab:rqtworecurrence}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Category & Policy/stratum & Bases & Tests & Class rec. & Instance rec. & Class (\%) & Instance (\%) \\',r'\midrule']
 for cat,(code,label) in a.CATEGORIES.items():
  for p in a.POLICIES:
   for scope,suffix in [('cumulative',''),('added','Added')]:
    pre='rqTwo'+a.TAGS[p]+suffix+code
    recurrence.append(label+' & '+a.TAGS[p]+' '+scope+' & '+' & '.join([count(pre+x) for x in ['Upstreams','Tests','ClassRec','InstanceRec']]+['\\'+pre+'ClassRate','\\'+pre+'InstanceRate'])+r' \\')
 recurrence += [r'\bottomrule',r'\end{tabular}%','}',r'\end{table*}'];files['rq2_policy_recurrence_table.tex']=('\n'.join(recurrence)+'\n').encode()
 tablevi=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\caption{RQ3 recurrence under Declared provenance, as of \RQThreeAsOf. Occurrences and distinct artifacts cover verified responses of inventory models; recurrence tests are upstream-positive pair--prompt comparisons, with one shared denominator.}',r'\label{tab:rqthree}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{lrrrrrrr}',r'\toprule',r'Category & Occ. & Dist. & Shared tests & Class rec. & Class rate (\%) & Instance rec. & Instance rate (\%) \\',r'\midrule']
 for cat,(code,label) in a.CATEGORIES.items():
  pre='RQThree'+code;label+=r'$^{\dagger}$' if code=='Restricted' else ''
  tablevi.append(label+' & '+' & '.join([count(pre+x) for x in ['Occ','Distinct','Tests','ClassRec']]+['\\'+pre+'ClassRate',count(pre+'InstanceRec'),'\\'+pre+'InstanceRate'])+r' \\')
 tablevi += [r'\bottomrule',r'\end{tabular}%','}',r'\par\scriptsize $\dagger$ Original closed-brand restricted-namespace diagnostic; not a confirmed exploitable vulnerability. N/A means recurrence is not estimable.',r'\end{table*}'];files['rq3_recurrence_table.tex']=('\n'.join(tablevi)+'\n').encode()
 tablevii=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\caption{RQ4: recurrence by recorded adaptation stratum under Declared provenance. Cells give positive/shared-tests (percentage); both levels share the same tests in each stratum. ndFT is non-default-labeled FT; dFT is a fallback label, not proof of fine-tuning.}',r'\label{tab:rqfour}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Finding & Level & AD & ndFT & dFT & QT & MG & Overall \\',r'\midrule']
 for cat,(code,label) in a.CATEGORIES.items():
  for metric in ('Class','Instance'):
   cells=[]
   for group in list(a.STRATA)+['Overall']:
    pre='RQFour'+code+group
    cells.append('N/A' if not s['rq4'][cat][group]['tests'] else count(pre+metric+'Rec')+'/'+count(pre+'Tests')+' (\\'+pre+metric+'Rate)')
   tablevii.append(label+(' (diag.)' if code=='Restricted' else '')+' & '+metric+' & '+' & '.join(cells)+r' \\')
 tablevii += [r'\bottomrule',r'\end{tabular}%','}',r'\end{table*}'];files['rq4_adaptation_table.tex']=('\n'.join(tablevii)+'\n').encode()
 support=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\caption{RQ4 upstream support and conditional upstream-clustered 95\% intervals. Intervals are suppressed below ten upstreams or insufficient positive/negative family support; they do not describe population-wide uncertainty.}',r'\label{tab:rqfoursupport}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{llrrrrll}',r'\toprule',r'Category & Stratum & Tests & Bases & Derivs. & Pairs & Class interval (\%) & Instance interval (\%) \\',r'\midrule']
 for cat,(code,label) in a.CATEGORIES.items():
  for group in list(a.STRATA)+['Overall']:
   pre='RQFour'+code+group
   support.append(label+' & '+group+' & '+' & '.join([count(pre+x) for x in ['Tests','Upstreams','Derivs','Pairs']]+['\\'+pre+'ClassInterval','\\'+pre+'InstanceInterval'])+r' \\')
 support += [r'\bottomrule',r'\end{tabular}%','}',r'\end{table*}'];files['rq4_upstream_support_table.tex']=('\n'.join(support)+'\n').encode()
 rq2section=[r'\subsection{RQ2: Provenance Evidence and Security Analysis}',r'\label{sec:rqtwounified}',
  r'We distinguish frozen graph-wide evidence from the current Security Server inventory. Historical graph-wide references are preserved in Table~\ref{tab:rqtwograph}; original policy assignments remain unrecovered, so independent four-policy reproduction is pending. The local graph corroborates Extended structural counts without reconstructing provenance evidence.',r'\input{rq2_graph_policy_table.tex}',
  r'Our dynamic inventory includes each selected adaptation relationship with at least one identical prompt completed with applicable verification and both c1 passes on both endpoints. It does not require whole-bank or whole-branch completion. Coverage uses \rqTwoEligiblePairs{} distinct eligible pairs, not the unique-model total.',r'\input{rq2_policy_table.tex}',
  r'Strict admits explicit declared adaptation evidence; Intermediate additionally admits supported tag/field evidence; Declared admits declared identity despite adaptation-label uncertainty; Extended additionally admits eligible inferred ancestry. Actual pair identifiers verify nested membership. Conversion and successor links are excluded before counting.',
  r'All policies reuse the same responses, prompt hashes and verifier evidence. Following Eqs.~(10)--(12), each category uses one shared eligible set for class and canonical-instance recurrence. A known positive can establish an outcome despite unrelated unresolved artifacts; comparisons with either unresolved outcome are excluded, while verified negatives remain eligible.',r'\input{rq2_policy_recurrence_table.tex}',
  r'We separately report cumulative policies and their newly admitted strata. The additions are \rqTwoIntermediateAddedPairs{}, \rqTwoDeclaredAddedPairs{}, and \rqTwoExtendedAddedPairs{} pairs. Changes in observed rates describe changes in evidence-admitted composition; they do not show causal inheritance.',
  r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{rq2_policy_sensitivity.pdf}\caption{RQ2 sensitivity on one verified response snapshot: policy-admitted pair coverage and class/instance recurrence. Malicious-URL recurrence is not plotted as zero when no eligible tests exist. Restricted namespace is diagnostic.}\label{fig:rqtwounified}\end{figure*}']
 files['rq2_section.tex']=('\n\n'.join(rq2section)+'\n').encode()
 rq3section=[r'\subsection{RQ3: Failure Persistence Across Derivatives}',r'\label{sec:rqthreeunified}',
  r'Under the primary Declared provenance policy, we compare identical prompts with completed generation and applicable verification on both endpoints, requiring at least one externally verified upstream artifact. Partial-bank models contribute completed prompt pairs; no whole-bank sampling restriction is imposed. Both estimators use the same category-specific tests after three-valued outcome determination.',r'\input{rq3_recurrence_table.tex}',
  r'Package recurrence is \RQThreePkgClassRec{}/\RQThreePkgTests{} (\RQThreePkgClassRate{}\%) at class level and \RQThreePkgInstanceRec{}/\RQThreePkgTests{} (\RQThreePkgInstanceRate{}\%) at canonical-instance level. Registrable NXDOMAIN recurrence is \RQThreeNxClassRec{}/\RQThreeNxTests{} (\RQThreeNxClassRate{}\%) and \RQThreeNxInstanceRec{}/\RQThreeNxTests{} (\RQThreeNxInstanceRate{}\%), respectively.',
  (r'Exact malicious-URL recurrence is N/A because no eligible upstream-positive comparisons exist.' if not s['rq3']['malicious_url']['tests'] else r'Exact malicious-URL recurrence is \RQThreeMalClassRate{}\% class and \RQThreeMalInstanceRate{}\% instance, using \RQThreeMalTests{} shared tests.'),
  r'Restricted-namespace recurrence uses the original Specification-13 closed-brand diagnostic and remains separate from registrable NXDOMAIN. It does not establish registrability or exploitability. Occurrence counts describe verified finding rows over inventory-model responses, whereas tests count parent--child--prompt comparisons. These are descriptive recurrence rates, not unique-model prevalence or causal inheritance.']
 files['rq3_section.tex']=('\n\n'.join(rq3section)+'\n').encode()
 files['rq4_section.tex']=('\n\n'.join([r'\subsection{RQ4: Adaptation Types and Upstream Characteristics}',
  r'We stratify exactly the same Declared, shared-denominator comparison ledger used in RQ3. AD, non-default FT, default FT, QT and MG form a verified partition of the current relationship labels; every adaptation cell is recomputed. Default FT reflects a fallback metadata label, not experimentally established fine-tuning.',r'\input{rq4_adaptation_table.tex}',r'\input{rq4_upstream_support_table.tex}',
  r'We report contributing upstreams and derivatives with each stratum in the accompanying audit. Upstream-clustered percentile intervals are conditional on this cohort and are suppressed with fewer than ten contributing upstreams or insufficient positive/negative family support. Prompts and derivatives from one upstream are not treated as independent samples.',
  r'Additional descriptive analyses use hash-verified model-type metadata and declared one-hop lineage breadth. Verified parameter counts are unavailable; storage bytes and name-derived size buckets are not treated as parameter estimates. Unequal upstream representation and nonrandom execution coverage limit interpretation; no adaptation effect is claimed as causal.'])+'\n').encode()
 files['abstract_corrections.tex']=(r'Using a dynamically observed cohort of \icdecount{\EvalBases} upstreams and \icdecount{\EvalUniqueDerivs} derivatives, we measure same-prompt recurrence under fixed provenance and verification policies. Package recurrence is \RQThreePkgClassRate{}\% class-level and \RQThreePkgInstanceRate{}\% instance-level; registrable NXDOMAIN recurrence is \RQThreeNxClassRate{}\% and \RQThreeNxInstanceRate{}\%. These are comparison-weighted descriptive rates. Restricted namespace is diagnostic, and exact malicious-URL recurrence is reported only when eligible upstream-positive tests exist.'+'\n').encode()
 files['contribution_corrections.tex']=(r'We provide a reproducible evidence-policy sensitivity analysis, a shared-denominator four-category recurrence ledger, and adaptation/upstream-stratified descriptive analyses. Every current count follows the same validated response snapshot; incomplete observations and unresolved outcomes are not converted into negatives.'+'\n').encode()
 files['conclusion_corrections.tex']=(r'On the observed cohort as of \EvalAsOf{}, package recurrence is \RQThreePkgClassRate{}\% at class level and \RQThreePkgInstanceRate{}\% at canonical-instance level; registrable NXDOMAIN recurrence is \RQThreeNxClassRate{}\% and \RQThreeNxInstanceRate{}\%. Provenance policies change admitted relationships and observed composition. The results do not establish causal checkpoint inheritance or population-wide vulnerability prevalence; restricted-namespace findings remain diagnostic.'+'\n').encode()
 # A future category with zero tests must not produce 0/0 or N/A-percent prose.
 def finding_sentence(cat,code,label):
  if not s['rq3'][cat]['tests']:return label+' recurrence is N/A because no eligible upstream-positive comparisons exist.'
  pre='RQThree'+code
  return label+' recurrence is \\'+pre+'ClassRec{}/\\'+pre+'Tests{} (\\'+pre+'ClassRate{}\\%) at class level and \\'+pre+'InstanceRec{}/\\'+pre+'Tests{} (\\'+pre+'InstanceRate{}\\%) at canonical-instance level.'
 rq3section[4]=finding_sentence('package_hallucination','Pkg','Package')+' '+finding_sentence('nonexistent_domain','Nx','Registrable NXDOMAIN')
 files['rq3_section.tex']=('\n\n'.join(rq3section)+'\n').encode()
 files['abstract_corrections.tex']=(r'We analyze \icdecount{\EvalBases} upstreams and \icdecount{\EvalUniqueDerivs} derivatives using completed prompt pairs rather than whole-bank completion. '+rq3section[4]+' Rates are comparison-weighted and descriptive; restricted namespace is diagnostic. Exact malicious-URL recurrence is reported only where eligible tests exist.\n').encode()
 files['conclusion_corrections.tex']=(r'As of \EvalAsOf{}, '+rq3section[4]+' Provenance-policy changes alter admitted composition, not model behavior. These observations do not establish causal inheritance or population-wide vulnerability prevalence; accepted c1 detector limitations remain.\n').encode()
 files['rq5_scope_revision.tex']=(r'The downstream graph inventory must be reported with its own dated cohort and evidence provenance. Counts of selected, jointly observed, whole-bank-complete and recurrence-positive models are distinct. Recorded model--repository or model--Space links are associations, not proof of vulnerability propagation. The new scope audit recomputes graph-association counts for explicit model-ID sets; it does not replace un-recomputed RQ5 behavioral results.'+'\n').encode()
 files['macro_migration.md']=('Valid recurrence aliases in rq3_numbers_codex.tex now intentionally use the shared eligible set. Old completion overview names retain whole-bank semantics.\n\nInvalid digit-containing names such as EvalRQ3Models are removed from active generated files; use EvalRQThreeModels, EvalRQThreeBases, EvalRQThreeUniqueDerivs and EvalRQThreeResponses.\n\nPrimary counts: EvalBases/EvalFT/EvalAD/EvalQT/EvalMerge/EvalUniqueModels refer to prompt-paired inventory. RQThree*Tests and RQFour*Tests are category-specific shared denominators. rqthreeTriplesC*/TriplesI* both alias the same new tests.\nOther legacy manuscript macros are not silently copied with stale values; use the complete supplied replacement sections.\n').encode()
 files['model_cohort_paragraph.tex']=(r'We identify \icdecount{\OneHopUniqueDerivs} unique text-generation derivatives linked to \icdecount{\OneHopBases} upstreams, yielding \icdecount{\OneHopUniqueModels} distinct models. Static readiness retains \icdecount{\ReadyUniqueDerivs} derivatives linked to \icdecount{\ReadyBases} upstreams (\icdecount{\ReadyUniqueModels} unique models). The dynamic evaluated inventory, as of \EvalAsOf{}, contains \icdecount{\EvalPairs} adaptation pairs connecting \icdecount{\EvalBases} upstreams and \icdecount{\EvalUniqueDerivs} derivatives (\icdecount{\EvalUniqueModels} unique models). A pair enters after at least one identical prompt has completed original verification and both c1 passes on both models; whole-bank and branch completion are not required. This inventory rule is independent of whether any security finding is positive. Recurrence eligibility additionally requires a verified upstream-positive category finding and determinate indicators. Conversion and successor relationships are excluded before counting. '+ '\n').encode()
 files['scope_sensitivity.csv']=csvdata([{'category':cat,'scope':scope,**r} for cat,scopes in s['scope_sensitivity'].items() for scope,r in scopes.items()])
 files['rq4_adaptation_results.csv']=csvdata([{'category':cat,'stratum':g,**r} for cat,groups in s['rq4'].items() for g,r in groups.items()])
 files['rq4_upstream_characteristics.csv']=csvdata(s['upstream_characteristics']['results'])
 files['model_status_audit.csv']=csvdata(model_audit);files['relationship_status_audit.csv']=csvdata(pair_audit)
 files['canonical_comparisons.jsonl']=(''.join(a.stable(r)+'\n' for r in comparisons)).encode()
 files['qualified_occurrences.jsonl']=(''.join(a.stable(r)+'\n' for r in occurrences)).encode()
 files['rq5_scope_audit.json']=a.encoded(s['rq5_scope_audit']);files['historical_regression.json']=a.encoded(s['historical_regression'])
 files['capture_manifest.json']=a.encoded(context)
 selected_modelrows=[r for r in model_audit if r['included_prompt_scope']]
 files['evaluated_model_manifest.csv']=csvdata([{**r,'upstream':int(r['upstream']),'derivative':int(r['derivative'])} for r in selected_modelrows])
 files['evaluated_relationships.csv']=csvdata([{'parent_id':m['parent_id'],'child_id':m['child_id'],'adaptation_label':m['adaptation_label'],'membership_id_sha256':k,'joint_completed_prompts':next(r['joint_completed_prompts'] for r in pair_audit if r['membership_id_sha256']==k)} for k,m in sorted(pairs.items())])
 ev={'change_id':s['version'],'scope':s['primary_scope'],'as_of':s['cutoff'],'rq3_snapshot_id':sid,'source_snapshot_id':s['source_snapshot_id'],
  'values':{**c,'Total':c['UniqueModels'],'Models':c['UniqueModels'],'Responses':s['cohort_verified_responses']},'source_capture':s['capture_manifest'],
  'full_rq3_completed_models':s['execution_coverage']['complete_both_c1_models'],'full_rq3_completed_bases':s['model_role_counts']['whole_bank_upstreams'],
  'full_rq3_completed_derivatives':s['model_role_counts']['whole_bank_derivatives'],
  'full_rq3_completed_responses':whole_responses,'frozen_snapshot_id':frozen['snapshot_id'],
  'whole_bank_complete_model_ids':[r['model_id'] for r in model_audit if r['whole_bank_complete']],
  'comparison_ledger':str(WORK/'snapshots'/sid/'canonical_comparisons.jsonl'),
  'whole_bank_sensitivity':s['whole_bank_pair_scope'],'partial_models_included':sum(not r['whole_bank_complete'] for r in selected_modelrows),
  'completed_models_outside_table2':[r['model_id'] for r in model_audit if r['whole_bank_complete'] and not r['included_prompt_scope']],
  'generator_path':str(WORK/'snapshots'/sid/'unified_analysis.py'),'generator_sha256':s['code']['unified_analysis.py']}
 files['evaluated_cohort_validation.json']=a.encoded(ev)
 files['rq2_validation.json']=a.encoded(s)
 files['unified_protocol.json']=a.encoded(s['analysis_protocol'])
 files['historical_model_status_audit.csv']=csvdata(s['historical_regression']['previous_models_audit'])
 files['historical_relationship_status_audit.csv']=csvdata(s['historical_regression']['previous_relationships_audit'])
 for name in ('unified_analysis.py','unified_exports.py','generate_rq2_analysis.py','test_unified_analysis.py'):
  files[name]=(Path(__file__).resolve().parent/name).read_bytes()
 # Known legacy labels retain their meaning when the supplied sections replace
 # their predecessors; this does not redefine any unrelated scientific macro.
 files['rq3_recurrence_table.tex']=files['rq3_recurrence_table.tex'].replace(br'\label{tab:rqthree}',br'\label{tab:rqthree}\label{tab:rq3}')
 files['rq4_adaptation_table.tex']=files['rq4_adaptation_table.tex'].replace(br'\label{tab:rqfour}',br'\label{tab:rqfour}\label{tab:rq4}\label{tab:rq4-adaptation}')
 files['rq2_section.tex']=files['rq2_section.tex'].replace(br'\label{fig:rqtwounified}',br'\label{fig:rqtwounified}\label{fig:rqtwosensitivity}')
 files['README_PUBLICATION.md']=(
  'Primary scope: at least one jointly original-verified/both-c1 identical prompt per eligible adaptation pair; no whole-bank/branch requirement. Recurrence additionally uses shared determinate upstream-positive tests.\n\n'
  'Download same-named files from current/ or the repository-root aliases. The original ~/icde_rq3 and ~/icde_rq4 exports remain legacy, not this unified publication.\n\n'
  'Preamble inputs: graph_cohort_numbers.tex, evaluated_cohort_numbers.tex, rq2_numbers_codex.tex, rq3_numbers_codex.tex, rq4_numbers_codex.tex; booktabs, graphicx and the supplied table2_icdecount.tex formatter.\n\n'
  'Body inputs: model_cohort_paragraph.tex, graph_cohort_table.tex, rq2_section.tex, rq3_section.tex, rq4_section.tex. Upload all their referenced table/figure files, including rq4_upstream_support_table.tex. Optional abstract/contribution/conclusion and RQ5 scope proposals are separate files.\n\n'
  'Update: python3 -B '+str(WORK/'generate_rq2_analysis.py')+'\n\nReplay: add --source '+s['capture_manifest']+'\n\n'
  'Publication uses one atomic current pointer after validation; immutable older snapshots and exact original-file backups remain. Do not edit a file inside an immutable snapshot.\n').encode()
 for name in ['rq2_graph_frozen_historical.json','rq2_local_graph_structure.json','GRAPH_SERVER_EXPORT.md','export_rq2_graph_evidence.py','rq2_graph_queries.sql']:
  files[name]=(WORK/name).read_bytes()
 files['rq2_table_vi_reconciliation.md']=('Archived unequal-denominator discrepancies are reproduced in historical_regression.json. The primary now uses prompt-level eligibility; whole-bank results are sensitivity only.\n\nThree archived extra package tuples are retained with exact safe prompt IDs in historical_regression.json. Five previously omitted complete upstream IDs are listed there; their CURRENT selected/execution/whole-bank status and category-wise test counts are in model_status_audit.csv. Every selected relationship is audited in relationship_status_audit.csv. A difference of five complete upstreams does not imply five or more upstream-positive prompt tests: they may have no jointly verified or upstream-positive child prompts.\n\n'+json.dumps(s['scope_sensitivity'],indent=2)+'\n').encode()
 report=report_text(s,model_audit,pair_audit)
 files['rq2_redesign_report.md']=report.encode();files['comprehensive_audit_report.md']=report.encode()
 files['unified_compile_test.tex']=(r'\documentclass[twocolumn]{article}'+'\n'+r'\usepackage{booktabs,graphicx}'+'\n'+r'\input{table2_icdecount.tex}'+'\n'+
  '\n'.join(r'\input{'+n+r'}' for n in ['graph_cohort_numbers.tex','evaluated_cohort_numbers.tex','rq2_numbers_codex.tex','rq3_numbers_codex.tex','rq4_numbers_codex.tex','rq5_numbers_codex.tex'])+'\n'+r'\begin{document}'+'\n'+
  '\n'.join(r'\input{'+n+r'}' for n in ['graph_cohort_table.tex','rq2_section.tex','rq3_section.tex','rq4_section.tex','rq5_results_table.tex','rq5_discussion.tex'])+'\n'+r'\end{document}'+'\n').encode()
 files['rq2_compile_test.tex']=files['unified_compile_test.tex']
 files['rq2_policy_sensitivity.pdf']=figure(s)
 s['tex_compilation']='not performed; no installed TeX compiler' if not any(shutil.which(x) for x in ('pdflatex','lualatex','xelatex')) else 'compiler available; integration test required'
 values={**evalm.values,**m2.values,**m3.values,**m4.values}
 rq4v,failures=rq4_validation(s,pairs,comparisons,values)
 a.require(not failures,'RQ4 publication validation failed: '+'; '.join(failures))
 legacy=sorted(n for n in m4.values if n.startswith('rqfour'))
 rq4v.update({'status':'PASS','snapshot_id':sid,'cutoff':s['cutoff'],'capture_manifest':s['capture_manifest'],
  'capture_manifest_sha256':s['capture_manifest_sha256'],'ledger_sha256':s['ledger_sha256'],'source_snapshot_id':s['source_snapshot_id'],'code':s['code'],
  'cohort':{**c,'selected_adaptation_pairs':s['selected_adaptation_pairs']},
  'file_sha256':{n:hashlib.sha256(files[n]).hexdigest() for n in ('rq2_numbers_codex.tex','rq3_numbers_codex.tex','rq4_numbers_codex.tex','canonical_comparisons.jsonl')},
  'legacy_macros':legacy,'uppercase_rq4_macros':sum(n.startswith('RQFour') for n in m4.values),
  'percentage_regression':{x:percentage(x) for x in ('50.00','30.10','43.44','39.00','0.50','0.05','100.00','0.00')},
  'unresolved':[],'tex_compilation':s['tex_compilation']})
 files['rq4_publication_validation.json']=a.encoded(rq4v);files['rq4_publication_validation.md']=rq4_validation_text(rq4v).encode()
 s['checks'].append('PASS RQ4 exact-identity reconciliation, partition, contributing bases and legacy aliases ('+str(len(rq4v['checks']))+' checks)')
 # RQ5 from the same capture and ledger; publication is refused on any failed check.
 graph,graph_sources=rq5_graph();r5=rq5_compute(graph,models,pairs,comparisons,occurrences,model_audit)
 m6=Macros(comment+' RQ5 graph export '+graph['meta']['export_version']+' ('+graph['meta']['snapshot_id']+'); graph acquisition dates are independent of the response cutoff.')
 rq5_macros(m6,r5,s,sid)
 checks5,failures5=rq5_validation(r5,s,m6.values,rq5_table().decode())
 a.require(not failures5,'RQ5 publication validation failed: '+'; '.join(failures5))
 a.require(not set(m6.values)&set(values),'RQ5 macro collides with an existing generated macro')
 inventory,interface_sha=rq5_inventory(m6.values);legacy_names={x['macro'] for x in inventory}
 files['rq5_numbers_codex.tex']=m6.text();files['rq5_results_table.tex']=rq5_table();files['rq5_discussion.tex']=rq5_discussion()
 def plain(x):return {k:(sorted(v) if isinstance(v,set) else plain(v) if isinstance(v,dict) else v) for k,v in x.items() if not k.endswith(('_set',)) and k not in ('space_set','repo_set','set')}
 results={k:plain(v) if isinstance(v,dict) else v for k,v in r5.items() if k not in ('frame_set','eval_set','sens_set','frame_pair_set','eval_pair_set','parents','frame_rows','graph_ms_models','graph_mg_models')}
 results['behavior']={cat:{k:(len(v) if isinstance(v,set) else plain(v) if isinstance(v,dict) else v) for k,v in b.items()} for cat,b in r5['behavior'].items()}
 rq5v={'status':'PASS','snapshot_id':sid,'cutoff':s['cutoff'],'capture_manifest':s['capture_manifest'],'capture_manifest_sha256':s['capture_manifest_sha256'],
  'ledger_sha256':s['ledger_sha256'],'graph':graph['meta'],'graph_sources':graph_sources,'legacy_interface_sha256':interface_sha,'checks':checks5,'results':results,
  'inventory':inventory,'new_macros':sorted(n for n in m6.values if n not in legacy_names),'percentage_regression':{x:percentage(x) for x in ('50.00','30.10','43.44')},
  'tex_compilation':s['tex_compilation'],'file_sha256':{n:hashlib.sha256(files[n]).hexdigest() for n in ('rq5_numbers_codex.tex','rq5_results_table.tex','rq5_discussion.tex')}}
 files['rq5_publication_validation.json']=a.encoded(rq5v);files['rq5_unified_audit.md']=rq5_audit_text(rq5v).encode()
 s['checks'].append('PASS RQ5 graph-frame / evaluated / behavioral / concentration reconciliation ('+str(len(checks5))+' checks)')
 validate_tex(files)
 s['checks'].append('PASS generated letters-only macro definitions, braces, table columns, references and input dependencies')
 files['rq2_validation.json']=a.encoded(s)
 return files


def figure(s):
 with tempfile.TemporaryDirectory() as td:
  os.environ.setdefault('MPLCONFIGDIR',td)
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  fig,axes=plt.subplots(1,2,figsize=(8,3.3))
  xx=list(range(4));tags=['Strict','Inter.','Decl.','Ext.']
  axes[0].bar(xx,[s['coverage'][p]['cumulative']['coverage_pct'] for p in a.POLICIES],color='#526a83')
  axes[0].set_ylabel('Admitted inventory pairs (%)');axes[0].set_ylim(0,105)
  colors={'package_hallucination':'#176b8d','nonexistent_domain':'#b7652c','restricted_namespace':'#6a598a'}
  for cat,label in [('package_hallucination','PkgH'),('nonexistent_domain','NX'),('restricted_namespace','ResNS (diag.)')]:
   for metric,style in [('class_rate','-'),('instance_rate','--')]:
    yy=[s['rq2'][p]['cumulative'][cat][metric] for p in a.POLICIES]
    axes[1].plot(xx,[100*v if v is not None else float('nan') for v in yy],style,marker='o',color=colors[cat],label=label+' '+('class' if metric=='class_rate' else 'instance'))
  if not any(s['rq2'][p]['cumulative']['malicious_url']['tests'] for p in a.POLICIES):axes[1].text(.03,.03,'MalURL: N/A (no eligible tests)',transform=axes[1].transAxes,fontsize=7)
  axes[1].set_ylim(0,100);axes[1].set_ylabel('Recurrence (%)');axes[1].legend(fontsize=6,ncol=2,loc='upper right')
  for ax in axes:ax.set_xticks(xx,tags);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
  fig.tight_layout();p=Path(td)/'figure.pdf';fig.savefig(p,metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
  return p.read_bytes()


def validate_tex(files):
 defs={}
 for name,raw in files.items():
  if not name.endswith('.tex'):continue
  text=raw.decode()
  # Generated count files never introduce digit-containing control sequences.
  for macro,value in re.findall(r'\\newcommand\{\\([^}]+)\}\{([^\n]*)\}',text):
   a.require(re.fullmatch('[A-Za-z]+',macro),'Non-letter macro: '+macro)
   a.require(macro not in defs,'Duplicate macro across generated inputs: '+macro);defs[macro]=value
  # Braces after removing comments and escaped literal braces.
  clean=re.sub(r'(?<!\\)%[^\n]*','',text);clean=clean.replace(r'\{','').replace(r'\}','')
  depth=0
  for ch in clean:
   if ch=='{':depth+=1
   elif ch=='}':depth-=1
   a.require(depth>=0,'Unbalanced TeX braces: '+name)
  a.require(depth==0,'Unbalanced TeX braces: '+name)
  for dependency in re.findall(r'\\input\{([^}]+)\}',text):a.require(dependency in files,'Missing TeX dependency: '+dependency)
  for dependency in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',text):a.require(dependency in files,'Missing figure dependency: '+dependency)
  # Column spec may contain brace groups such as @{}; only l/c/r outside them are columns.
  for spec,body in re.findall(r'\\begin\{tabular\}\{((?:[^{}]|\{[^{}]*\})*)\}(.*?)\\end\{tabular\}',text,re.S):
   n=sum(c in 'lcr' for c in re.sub(r'\{[^{}]*\}','',spec))
   for row in body.splitlines():
    if '&' in row:a.require(row.count('&')+1==n,'Wrong table column count: '+name)
 for name,raw in files.items():
  if name.endswith('.tex'):
   for macro in re.findall(r'\\((?:Eval|OneHop|Ready|Cohort|TextGen|rqTwo|RQThree|RQFour|RQFiveScope|rqthree|rqfour|rqfive)[A-Za-z]+)',raw.decode()):a.require(macro in defs,'Undefined publication macro: '+macro+' in '+name)


def report_text(s,model_audit,pair_audit):
 lines=['# Comprehensive RQ2–RQ4 audit', '',s['version']+'; '+s['snapshot_id'],'As of '+s['cutoff'],
  '## A. Dataset and snapshot audit',s['primary_scope'],'Primary lineage policy: Declared. Exact source capture: '+s['capture_manifest'],
  'Capture SHA256 '+s['capture_manifest_sha256']+'; ledger SHA256 '+s['ledger_sha256'],
  'Active selected manifests: '+json.dumps(s['selection_hashes'],sort_keys=True),'Execution coverage: '+json.dumps(s['execution_coverage'],sort_keys=True),
  '## B. Scope reconciliation','Table II prompt-paired ID counts: '+json.dumps(s['cohort']['values'],sort_keys=True),
  'Whole-bank sensitivity counts: '+json.dumps(s['whole_bank_pair_scope']['values'] if s['whole_bank_pair_scope'] else None,sort_keys=True),
  'Every selected model and relationship, including all excluded identities/reasons, completed prompts, positive prompts and category-wise comparisons, is in model_status_audit.csv / relationship_status_audit.csv.',
  'The archived 34-versus-29 difference and exact three package tuples are regression-tested, not forced on the current scope: '+json.dumps(s['historical_regression'],sort_keys=True),
  '## C. Four-category results','Occurrences count original qualifying finding rows over verified responses of inventory models; tests count parent-child-prompt comparisons. '+s['restricted_taxonomy'],
  '| Category | Shared tests | Class rec. | Class % | Instance rec. | Instance % | Bases | Derivatives |',
  '|---|---:|---:|---:|---:|---:|---:|---:|']
 for cat,r in s['rq3'].items():lines.append('| '+cat+' | '+' | '.join(map(str,[r['tests'],r['class_rec'],rate(r['class_rate']),r['instance_rec'],rate(r['instance_rate']),r['upstreams'],r['derivatives']]))+' |')
 lines += ['## D. RQ2 provenance sensitivity',json.dumps(s['coverage'],indent=2,sort_keys=True),json.dumps(s['rq2'],indent=2,sort_keys=True),
  '## E. RQ4 adaptation and upstream analysis','AD/ndFT/dFT/QT/MG are disjoint relationship strata in this selected export. ndFT means non-default labeled, not necessarily independently verified fine-tuning. Every cell and conditional upstream-cluster interval is in rq4_adaptation_results.csv.',json.dumps(s['upstream_characteristics'],indent=2,sort_keys=True),
  '## F. Historical versus corrected scopes','Archived checkpoints: historical_regression.json. Current Option A versus B: scope_sensitivity.csv. Earlier snapshots and all original verifier/response records remain unchanged.',
  '## G. Validation',*s['checks'],'Both indicator values use the same tests. Verified positives take precedence over unrelated uncertainty; verified negatives remain eligible. Exact raw prompt hashes and membership IDs deduplicate tests.','No TeX compiler installed; static dependency/column/brace/control-sequence validation performed.',
  '## H. Graph Server recovery','Historical four-policy counts are preserved, not rederived from the selected cohort. The local graph corroborates Extended structural records/pairs; original policy evidence is still missing. See GRAPH_SERVER_EXPORT.md.',
  '## I. Overleaf deliverables','Upload the stable same-named files from current/: graph_cohort_numbers.tex, evaluated_cohort_numbers.tex, graph_cohort_table.tex; rq2_numbers_codex.tex, rq2_section.tex, rq2_policy_table.tex, rq2_graph_policy_table.tex, rq2_policy_recurrence_table.tex, rq2_policy_sensitivity.pdf; rq3_numbers_codex.tex, rq3_section.tex, rq3_recurrence_table.tex; rq4_numbers_codex.tex, rq4_section.tex, rq4_adaptation_table.tex. Preamble requires booktabs, graphicx and supplied icdecount formatter. Prose corrections and scoped RQ5 revision are separate files; no manuscript was edited.',
  '## J. Update command','```bash','python3 -B '+str(WORK/'generate_rq2_analysis.py'),'```',
  'Replay without new capture: add --source '+s['capture_manifest'],
  'Scope change: prompt-paired evaluation is PRIMARY under explicit user direction. Whole-bank completion is sensitivity, not Eq. (11). No branch scheduling, model inference, new registry/DNS lookup, or detector relaxation occurs.',
  'Publication: all artifacts validate in staging before one atomic current/ pointer replacement. Stable aliases retain filenames. Original installation bytes receive exact dated backups; old immutable snapshots remain.',
  'RQ5 scope audit: '+json.dumps(s['rq5_scope_audit'],indent=2,sort_keys=True)]
 return '\n\n'.join(lines)+'\n'


def publish(files,s):
 # Public entry points cannot publish even a static-invalid bundle.
 validate_tex(files)
 snapshots=WORK/'snapshots';snapshots.mkdir(exist_ok=True)
 destination=snapshots/s['snapshot_id']
 manifest={'snapshot_id':s['snapshot_id'],'sources':s['code'],'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}}
 if destination.exists():
  for name,raw in files.items():a.require((destination/name).read_bytes()==raw,'Immutable reproducibility mismatch: '+name)
 else:
  temporary=Path(tempfile.mkdtemp(prefix='.unified-staging-',dir=WORK))
  try:
   for name,raw in files.items():
    with (temporary/name).open('xb') as f:f.write(raw)
   with (temporary/'OUTPUT_MANIFEST.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True)
   os.replace(temporary,destination)
  finally:
   if temporary.exists():shutil.rmtree(temporary)
 # Stable exports move together through one pointer. Keep a compatibility frame
 # during the first conversion so existing root files still read their old bytes.
 current=WORK/'current';date=stamp()
 root_names=['evaluated_cohort_numbers.tex','evaluated_model_manifest.csv','evaluated_relationships.csv','evaluated_cohort_validation.json','graph_cohort_table.tex']
 root_names += [n for n in files if n.startswith(('rq2_','rq3_','rq4_')) and n.endswith(('.tex','.pdf'))]
 if not current.is_symlink():
  a.require(not current.exists(),'current exists and is not a managed symlink')
  frame=WORK/'previous_installations'/date;frame.mkdir(parents=True)
  for name in root_names:
   p=ROOT/name
   if p.exists():shutil.copyfile(p,frame/name)
  os.symlink(str(frame),current)
 for directory,names in [(ROOT,root_names),(WORK,[n for n in files if n.endswith(('.tex','.pdf'))])]:
  for name in names:
   p=directory/name;target=os.path.relpath(current/name,directory)
   if p.is_symlink():
    a.require(os.readlink(p)==target,'Unexpected existing export symlink: '+str(p));continue
   if p.exists():
    backup=Path(str(p)+'.bak.'+date)
    with p.open('rb') as src,backup.open('xb') as out:shutil.copyfileobj(src,out)
    a.require(a.sha(p)==a.sha(backup),'Export backup mismatch')
   pending=directory/(name+'.pending.'+date);os.symlink(target,pending);os.replace(pending,p)
 previous=os.readlink(current);backup=WORK/('current.bak.'+date)
 if previous!=str(destination):
  os.symlink(previous,backup)
  temporary=WORK/('.current.pending.'+date);os.symlink(str(destination),temporary);os.replace(temporary,current)
 a.common.publish(WORK/'LATEST.json',json.dumps({'snapshot_id':s['snapshot_id'],'directory':str(destination),'as_of':s['cutoff'],'capture_manifest':s['capture_manifest'],'primary_scope':s['primary_scope']},indent=2)+'\n')
 return destination
