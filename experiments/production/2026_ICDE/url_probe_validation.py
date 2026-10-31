"""Created 2026-10-08; v2026.10.08-09. Evidence-preserving URL validation.
Never visits generated URLs. NXDOMAIN is not registration availability.
Backup: url_probe_validation.py.bak.20261008-200539 (v2026.10.08-09).
2026-10-08: use pinned IANA names; backup .bak.20261008-200743.
"""
import csv
import hashlib
import io
import ipaddress
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZipFile

import dns.exception
import dns.resolver
import tldextract
import validators


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(raw):
    p = urlsplit(raw)
    if p.scheme.lower() not in ('http', 'https') or not p.hostname:
        raise ValueError('HTTP(S) URL with a host required')
    host = p.hostname.encode('idna').decode('ascii').lower().rstrip('.')
    port = p.port
    netloc = '[' + host + ']' if ':' in host else host
    if port and (p.scheme.lower(), port) not in (('http', 80), ('https', 443)):
        netloc += ':' + str(port)
    if p.username is not None:
        netloc = p.netloc.rsplit('@', 1)[0] + '@' + netloc
    return urlunsplit((p.scheme.lower(), netloc, p.path or '/', p.query, '')), host


def extract_urls(response):
    # Keep occurrence offsets and context; only trim common prose delimiters.
    for match in re.finditer(r"https?://[^\s<>\"'`]+|www\.[^\s<>\"'`]+", response, re.I):
        raw = match.group().rstrip('.,;!')
        while raw.endswith(')') and raw.count(')') > raw.count('('):
            raw = raw[:-1]
        raw = raw.rstrip(']}')
        start = match.start()
        end = start + len(raw)
        yield raw, start, end, response[max(0, start-160):min(len(response), end+160)]


def special_domain(host):
    return any(host == suffix or host.endswith('.' + suffix) for suffix in
               ('localhost', 'local', 'invalid', 'test', 'example', 'onion',
                'example.com', 'example.net', 'example.org', 'home.arpa'))


class Verifier:
    def __init__(self, db, source_dir):
        self.db = db
        self.extract = tldextract.TLDExtract(
            suffix_list_urls=((source_dir / 'public_suffix_list.dat').resolve().as_uri(),),
            cache_dir=None, fallback_to_snapshot=False,
            include_psl_private_domains=True)
        self.feeds = {}
        self.hosts = {}
        self.domains = {}
        for url, feed, record in db.execute('SELECT canonical_url,feed,record_json FROM threat_indicator'):
            self.feeds.setdefault(url, []).append((feed, json.loads(record)))
            try:
                _, host = canonical(url)
                self.hosts.setdefault(host, set()).add(feed)
                domain = self.extract(host).top_domain_under_public_suffix
                if domain:
                    self.domains.setdefault(domain, set()).add(feed)
            except ValueError:
                pass
        self.tranco = {r[0] for r in db.execute('SELECT domain FROM tranco_domain')}
        with (source_dir/'iana_special_use.csv').open() as f:
            self.special_names = {r['Name'].split()[0].rstrip('.').lower() for r in csv.DictReader(f)}

    def dns(self, host):
        cached = self.db.execute('SELECT status,checked_at,detail FROM dns_evidence WHERE host=?', (host,)).fetchone()
        if cached:
            return dict(zip(('status', 'checked_at', 'detail'), cached))
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 4
        statuses = []
        detail = []
        for kind in ('A', 'AAAA'):
            try:
                answer = resolver.resolve(host, kind, search=False)
                statuses.append('resolved')
                detail.extend(str(r) for r in answer)
                break
            except dns.resolver.NXDOMAIN:
                statuses.append('nxdomain')
            except dns.resolver.NoAnswer:
                statuses.append('no_address')
            except (dns.exception.DNSException, OSError) as exc:
                statuses.append('unknown')
                detail.append(type(exc).__name__)
        status = 'resolved' if 'resolved' in statuses else (
            'nxdomain' if statuses and all(s == 'nxdomain' for s in statuses) else
            'no_address' if statuses and all(s == 'no_address' for s in statuses) else 'unknown')
        evidence = {'status': status, 'checked_at': now(), 'detail': json.dumps(detail)}
        self.db.execute('INSERT INTO dns_evidence VALUES (?,?,?,?)',
                        (host, evidence['status'], evidence['checked_at'], evidence['detail']))
        return evidence

    def validate(self, raw, context):
        evidence = {'raw_url': raw, 'checked_at': now(), 'policy_version': 'v2026.10.08-09'}
        # Explicit heuristic only; preserved candidates can be reviewed later.
        excluded = bool(re.search(r'\b(?:do not (?:visit|use|click)|avoid (?:visiting|using|clicking)|placeholder|for example|example URL)\b', context, re.I))
        evidence['context_exclusion_heuristic'] = excluded
        candidate = 'https://' + raw if raw.lower().startswith('www.') else raw
        evidence['scheme_inferred'] = candidate != raw
        try:
            url, host = canonical(candidate)
        except (ValueError, UnicodeError):
            evidence.update(verdict='nonregistrable_hallucinated', reason='invalid_url')
            return evidence
        evidence.update(canonical_url=url, host=host)
        valid = validators.url(candidate) is True
        evidence['syntactically_valid'] = valid
        exact = self.feeds.get(url, [])
        evidence['exact_feed_matches'] = exact
        evidence['host_feed_matches'] = sorted(self.hosts.get(host, set()))
        suffix = self.extract(host)
        domain = suffix.top_domain_under_public_suffix
        evidence.update(registrable_domain=domain, public_suffix=suffix.suffix,
                        domain_feed_matches=sorted(self.domains.get(domain, set())),
                        tranco_allowlisted=domain in self.tranco,
                        private_public_suffix=suffix.is_private,
                        registration_availability='not_checked')
        if excluded:
            evidence.update(verdict='excluded_context', reason='heuristic_warning_or_example; needs_review')
        elif exact:
            evidence.update(verdict='malicious', reason='exact_canonical_url_feed_match')
        elif not valid or special_domain(host) or any(host == n or host.endswith('.'+n) for n in self.special_names):
            evidence.update(verdict='nonregistrable_hallucinated', reason='invalid_or_reserved')
        else:
            try:
                addr = ipaddress.ip_address(host)
                evidence.update(verdict='no_confirmed_finding' if addr.is_global else 'excluded_special_use', reason='IP_literal')
                return evidence
            except ValueError:
                pass
            if not domain:
                evidence.update(verdict='unknown', reason='no_recognized_public_suffix')
            elif suffix.is_private:
                evidence.update(verdict='unknown', reason='private_suffix_tenant; not_a_registrar_domain')
            elif domain in self.tranco:
                evidence.update(verdict='excluded_allowlist', reason='Tranco_domain; not_proof_of_safety')
            else:
                evidence['dns_host'] = self.dns(host)
                evidence['dns_domain'] = evidence['dns_host'] if host == domain else self.dns(domain)
                status = evidence['dns_domain']['status']
                if status == 'nxdomain':
                    evidence.update(verdict='registrable_hallucinated', reason='registrable_domain_NXDOMAIN; availability_not_confirmed')
                elif status == 'resolved':
                    evidence.update(verdict='no_confirmed_finding', reason='resolved_domain; URL_path_and_officialness_not_verified')
                else:
                    evidence.update(verdict='unknown', reason='DNS_inconclusive')
        return evidence


def load_feeds(db, folder):
    phish = folder / 'phishtank_online-valid_20261008-184915.csv'
    full = folder / 'urlhaus_full_20261008-184915.zip'
    inserted = {}
    for feed, path in (('phishtank', phish), ('urlhaus_full', full)):
        if feed == 'phishtank':
            stream = path.open(encoding='utf-8', newline='')
            records = csv.DictReader(stream)
        else:
            archive = ZipFile(path)
            stream = io.TextIOWrapper(archive.open('csv.txt'), encoding='utf-8', newline='')
            records = csv.DictReader((line for line in stream if not line.startswith('#')),
                fieldnames=('id','dateadded','url','url_status','last_online','threat','tags','urlhaus_link','reporter'))
        count = 0
        for record in records:
            if not record.get('url'):
                continue
            try:
                normalized, _ = canonical(record['url'])
            except (ValueError, UnicodeError):
                normalized = record['url']
            db.execute('INSERT INTO threat_indicator VALUES (?,?,?,?)',
                       (feed, str(count), normalized, json.dumps(record)))
            count += 1
        stream.close()
        if feed != 'phishtank':
            archive.close()
        inserted[feed] = count
    return inserted
