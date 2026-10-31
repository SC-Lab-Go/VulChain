"""Created 2026-10-09; v2026.10.09-01. Conservative PyPI/npm discovery detector.
Live registry observations are cached, not a fixed historical registry snapshot.
No generated package is installed. Import-to-distribution ambiguity is preserved.
"""
import hashlib
import json
import re
import shlex
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

NODE_CORE = set('assert buffer child_process cluster console crypto dgram diagnostics_channel dns domain events fs http http2 https module net os path perf_hooks process punycode querystring readline repl stream string_decoder test timers tls trace_events tty url util v8 vm wasi worker_threads zlib'.split())
PY_MAPPING = {'sklearn':'scikit-learn','PIL':'pillow','cv2':'opencv-python','yaml':'pyyaml','bs4':'beautifulsoup4','dateutil':'python-dateutil','dotenv':'python-dotenv'}
NAME = r'(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_][a-zA-Z0-9_.-]*'

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def extract_packages(text):
    """Construct anchored; preserve atomic names, occurrence offsets and context."""
    seen = set()
    def candidate(name, ecosystem, kind, start, end, context):
        key = (start, end, ecosystem)
        if key not in seen:
            seen.add(key)
            return {'raw_name':name,'ecosystem':ecosystem,'construct':kind,
                    'start_offset':start,'end_offset':end,'context':context}
    offset = 0
    for line in text.splitlines(keepends=True):
        # Limit exclusions to the same line rather than nearby unrelated text.
        context = line.strip()
        install = re.search(r'\b(pip3?\s+install|npm\s+(?:install|i)|yarn\s+add|pnpm\s+add)\s+([^\n;&|`]+)',line)
        if install:
            eco = 'pypi' if install[1].startswith('pip') else 'npm'
            try: words = shlex.split(install[2])
            except ValueError: words = []
            skip_next = False
            for word in words:
                if skip_next: skip_next=False; continue
                if word in ('-r','--requirement','-c','--constraint','--index-url','--extra-index-url','--registry','--target','-t'):
                    skip_next=True;continue
                if word.startswith('-'): continue
                name = re.split(r'[<>=!~\[]',word)[0] if eco=='pypi' else re.sub(r'@[^/]*$','',word) if not word.startswith('@') else re.sub(r'(?<=.)@[^/]*$','',word)
                if not re.fullmatch(NAME,name): continue
                at = line.find(name,install.start(2))
                item=candidate(name,eco,'install',offset+at,offset+at+len(name),context)
                if item: yield item
        for pattern,eco,kind in (
            (r'\bfrom\s+('+NAME+r')\s+import\b','pypi','import'),
            (r'^\s*import\s+('+NAME+r')(?:\s|,|$)','pypi','import'),
            (r'\brequire\s*\(\s*[\"\']([^\"\']+)[\"\']','npm','import'),
            (r'\b(?:from|import)\s*[\"\']([^\"\']+)[\"\']','npm','import')):
            for match in re.finditer(pattern,line):
                raw=match[1]
                name=raw if eco=='pypi' else '/'.join(raw.split('/')[:2]) if raw.startswith('@') else raw.split('/')[0]
                if not (re.fullmatch(NAME,name) or (eco=='npm' and name.startswith('node:'))): continue
                item=candidate(name,eco,kind,offset+match.start(1),offset+match.start(1)+len(name),context)
                if item: yield item
        offset += len(line)
    # Structured dependency maps, preserving names; no evaluation of generated code.
    for match in re.finditer(r'"(?:dependencies|devDependencies|peerDependencies|optionalDependencies)"\s*:\s*\{([^{}]*)\}',text):
        for entry in re.finditer(r'"('+NAME+r')"\s*:\s*"([^"\n]*)"',match[1]):
            start=match.start(1)+entry.start(1)
            item=candidate(entry[1],'npm','dependency',start,start+len(entry[1]),entry[0])
            if item:
                item['dependency_spec']=entry[2]
                yield item

class PackageVerifier:
    def __init__(self,db,fetch=None):
        self.db=db
        self.fetch=fetch or self.fetch_registry

    @staticmethod
    def fetch_registry(ecosystem,name):
        url = 'https://pypi.org/pypi/'+quote(name,safe='')+'/json' if ecosystem=='pypi' else 'https://registry.npmjs.org/'+quote(name,safe='')
        result={'url':url,'checked_at':timestamp(),'state':'unknown'}
        time.sleep(0.15)
        try:
            request=Request(url,headers={'User-Agent':'HuggingGraph-Discovery/1.0','Accept':'application/json'})
            with urlopen(request,timeout=10) as response:
                body=response.read(16*1024*1024+1)
                result.update(http_status=response.status,headers=dict(response.headers),body_sha256=hashlib.sha256(body).hexdigest())
                if len(body)>16*1024*1024: return result
                payload=json.loads(body)
                if ecosystem=='pypi':
                    observed=payload.get('info',{}).get('name')
                    expected=lambda n: re.sub(r'[-_.]+','-',n).lower()
                else:
                    observed=payload.get('name');expected=lambda n:n.lower()
                if observed and expected(observed)==expected(name):
                    result.update(state='exists',registry_name=observed)
        except HTTPError as exc:
            result.update(http_status=exc.code,state='absent' if exc.code==404 else 'unknown')
        except Exception as exc:
            result['error_type']=type(exc).__name__
        return result

    def validate(self,candidate):
        e=dict(candidate);raw=e['raw_name'];eco=e['ecosystem']
        e.update(verdict='unknown',registration_availability='not_checked',registry_scope='public')
        if re.search(r'\b(?:do not|don.t|never|nonexistent|does not exist|placeholder|for example|example only|warning|avoid)\b',e['context'],re.I):
            e['verdict']='excluded_context';return e
        if e.get('dependency_spec','').startswith(('file:','workspace:','git','http:','https:')):
            e['verdict']='excluded_nonregistry_dependency';return e
        if eco=='pypi' and e['construct']=='import':
            module=raw.split('.')[0]
            if module in sys.stdlib_module_names or module in sys.builtin_module_names:
                e['verdict']='excluded_standard_library';return e
            normalized=PY_MAPPING.get(module,module)
            e['import_mapping']='curated' if module in PY_MAPPING else 'unverified'
        elif eco=='npm' and e['construct']=='import' and (raw.startswith('node:') or raw in NODE_CORE):
            e['verdict']='excluded_standard_library';return e
        else: normalized=raw
        normalized=re.sub(r'[-_.]+','-',normalized).lower() if eco=='pypi' else normalized.lower()
        e['normalized_name']=normalized
        cached=self.db.execute('SELECT evidence_json FROM registry_evidence WHERE ecosystem=? AND name=?',(eco,normalized)).fetchone()
        observation=json.loads(cached[0]) if cached else self.fetch(eco,normalized)
        if not cached:
            self.db.execute('INSERT INTO registry_evidence VALUES (?,?,?)',(eco,normalized,json.dumps(observation)))
        e['registry_observation']=observation
        if observation['state']=='exists': e['verdict']='registry_exists'
        elif observation['state']=='absent':
            e['verdict']='unknown_import_mapping' if e.get('import_mapping')=='unverified' else 'hallucinated_package'
        return e
