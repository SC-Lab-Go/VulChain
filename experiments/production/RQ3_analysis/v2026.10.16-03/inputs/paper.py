#!/usr/bin/env python3
"""RQ3 persistence analysis: do base-model vulnerabilities persist in 1-hop derivatives?

Created: 2026-10-16
Version: v2026.10.16-rq3-01
Purpose: Re-runnable, read-only analysis of the dual-site probe ledger. Every run
overwrites ~/icde_rq3/out/ (results JSON, LaTeX macros, LaTeX table, run log).

Label layer (decided 2026-10-16): c1-corrected labels.
  pkg = package_finding_effective_c1: verdict 'hallucinated_package' (registry HTTP 404)
        AND c1_status 'retained'; identity (ecosystem, normalized_name).
  mal = url_finding_effective_c1: verdict 'malicious' (exact canonical-URL feed match);
        identity canonical_url.
  nx  = url_finding_reviewed_c1: reviewed_verdict 'registrable_hallucinated'
        (NXDOMAIN on the registrable domain; closed .brand TLDs flagged for review are
        excluded); identity registrable_domain.
An execution counts as complete only if status='complete' AND both c1 passes
(URL native family and package) have processed it.

Safety: the ledger is opened with mode=ro, read in one short transaction, then closed.
No package names or URLs are ever printed or written; outputs hold counts only.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

HOME = os.path.expanduser('~')
LEDGER = os.path.join(HOME, 'HuggingGraph_v3_2026_Oct2/HuggingGraph_v3_2026_Oct2_repo/2026_ICDE/'
                      'graphdb/dual_site_probe_v2026_10_10/analysis.sqlite3')
EXPORT = os.path.join(HOME, 'icde_graph_export')
TIERS_CSV = os.path.join(EXPORT, 'cohort_tiers.csv')
MANIFEST = os.path.join(EXPORT, 'MANIFEST.sha256')
OUT = os.path.join(HOME, 'icde_rq3', 'out')

N_PROMPTS = 1032
SEED = 20261016
MIN_BASE_CLUSTERS = 10
C1_URL = 'url-extract-v2026.10.11-c1'
C1_PKG = 'pkg-extract-v2026.10.11-c1'
TIERS = [('Strict', 'in_strict', 'Strict'), ('Inter', 'in_intermediate', 'Intermediate'),
         ('Decl', 'in_declared', 'Declared'), ('Ext', 'in_extended', 'Extended')]
CATS = [('pkg', 'Pkg', 'Package hallucination'), ('mal', 'Mal', 'Malicious URL'),
        ('nx', 'Nx', 'Registrable NXDOMAIN')]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify_tiers():
    expected = None
    with open(MANIFEST) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and os.path.basename(parts[1]) == 'cohort_tiers.csv':
                expected = parts[0]
    actual = sha256_file(TIERS_CSV)
    if expected is None or actual != expected:
        sys.exit(f'STOP: cohort_tiers.csv sha256 {actual} does not match manifest ({expected})')
    return actual


def read_ledger():
    """One short read-only transaction; the connection is closed before any computation."""
    con = sqlite3.connect(f'file:{LEDGER}?mode=ro', uri=True, timeout=30, isolation_level=None)
    t0 = time.monotonic()
    try:
        con.execute('BEGIN')
        snap = con.execute("SELECT count(*), max(completed_at) FROM execution WHERE status='complete'").fetchone()
        models = dict(con.execute('SELECT root_node_id, root_model FROM model'))
        complete = con.execute(
            """SELECT e.root_node_id, e.seed_id FROM execution e WHERE e.status='complete'
               AND EXISTS (SELECT 1 FROM url_reclassification_execution u WHERE u.policy_version=? AND u.family='native'
                           AND u.root_node_id=e.root_node_id AND u.seed_id=e.seed_id)
               AND EXISTS (SELECT 1 FROM package_reclassification_execution k WHERE k.policy_version=?
                           AND k.root_node_id=e.root_node_id AND k.seed_id=e.seed_id)""",
            (C1_URL, C1_PKG)).fetchall()
        pkg = con.execute(
            """SELECT root_node_id, seed_id, json_extract(evidence_json,'$.ecosystem'),
                      json_extract(evidence_json,'$.normalized_name')
               FROM package_finding_effective_c1 WHERE verdict='hallucinated_package' AND c1_status='retained'""").fetchall()
        url = con.execute(
            """SELECT root_node_id, seed_id, verdict, reviewed_verdict,
                      json_extract(evidence_json,'$.canonical_url'), json_extract(evidence_json,'$.registrable_domain')
               FROM url_finding_reviewed_c1 WHERE verdict IN ('malicious','registrable_hallucinated')""").fetchall()
        con.execute('COMMIT')
    finally:
        con.close()
    return dict(snap=snap, models=models, complete=complete, pkg=pkg, url=url,
                read_seconds=round(time.monotonic() - t0, 3))


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def cluster_bootstrap(clusters, resamples):
    """clusters: list of (sumC, sumI, n). Percentile 95% CIs of the pooled ratios."""
    if not clusters:
        return (None, None), (None, None)
    rng = random.Random(SEED)
    m = len(clusters)
    psi, sig = [], []
    for _ in range(resamples):
        c = i = n = 0
        for _ in range(m):
            sc, si, sn = clusters[rng.randrange(m)]
            c += sc; i += si; n += sn
        psi.append(c / n); sig.append(i / n)
    def pct(values):
        values.sort()
        lo = values[int(math.floor(0.025 * (len(values) - 1)))]
        hi = values[int(math.ceil(0.975 * (len(values) - 1)))]
        return lo, hi
    return pct(psi), pct(sig)


def analyse(data, tiers_rows, resamples):
    name = lambda node: data['models'].get(node, node[7:] if node.startswith('model::') else node)
    done = defaultdict(set)
    for node, seed in data['complete']:
        done[name(node)].add(seed)
    complete_models = {m for m, s in done.items() if len(s) == N_PROMPTS}

    art = {c: defaultdict(set) for c, _, _ in CATS}          # (model, seed) -> identities
    occ = {c: defaultdict(int) for c, _, _ in CATS}          # model -> confirmed occurrences
    brand_excluded = 0
    def add(cat, node, seed, ident):
        model = name(node)
        if seed in done.get(model, ()):                       # only c1-complete executions count
            art[cat][(model, seed)].add(ident)
            occ[cat][model] += 1
    for node, seed, eco, norm in data['pkg']:
        add('pkg', node, seed, f'{eco}:{norm}')
    for node, seed, verdict, reviewed, canon, domain in data['url']:
        if verdict == 'malicious':
            add('mal', node, seed, canon)
        elif reviewed == 'registrable_hallucinated':
            add('nx', node, seed, domain)
        elif seed in done.get(name(node), ()):
            brand_excluded += 1

    pplus = {c: defaultdict(set) for c, _, _ in CATS}
    for c, _, _ in CATS:
        for (model, seed) in art[c]:
            pplus[c][model].add(seed)

    bases_all = {r['parent_id'] for r in tiers_rows}
    eligible_bases = bases_all & complete_models
    base_context = {}
    for b in sorted(eligible_bases):
        distinct = {c: len(set().union(*(art[c][(b, s)] for s in pplus[c][b]))) if pplus[c][b] else 0 for c, _, _ in CATS}
        base_context[b] = {c: dict(p_plus=len(pplus[c][b]), p_plus_share=len(pplus[c][b]) / N_PROMPTS,
                                   confirmed_occurrences=occ[c][b], distinct_confirmed_artifacts=distinct[c])
                           for c, _, _ in CATS}

    tiers, cells = {}, {}
    for tkey, col, tname in TIERS:
        members = [(r['parent_id'], r['child_id']) for r in tiers_rows if r[col] == '1']
        elig = [(x, y) for x, y in members if x in eligible_bases]
        evaluated = [(x, y) for x, y in elig if y in complete_models]
        tiers[tkey] = dict(
            tier=tname, tier_memberships=len(members), tier_bases=len({x for x, _ in members}),
            eligible_memberships=len(elig), eligible_bases=len({x for x, _ in elig}),
            evaluated_memberships=len(evaluated), evaluated_bases=len({x for x, _ in evaluated}),
            evaluated_derivatives=len({y for _, y in evaluated}),
            coverage_members_vs_eligible=len(evaluated) / len(elig) if elig else None,
            coverage_members_vs_tier=len(evaluated) / len(members) if members else None,
            coverage_bases_vs_tier=len({x for x, _ in evaluated}) / len({x for x, _ in members}) if members else None)
        for c, ckey, _ in CATS:
            n = kc = ki = 0
            pairs_c = pairs_i = 0
            bases, derivs = set(), set()
            by_base, by_deriv = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])
            for x, y in evaluated:
                prompts = pplus[c].get(x, set())
                if not prompts:
                    continue
                pc = pi = 0
                for p in prompts:                              # (y, p) complete: y is fully complete
                    yc = art[c].get((y, p), set())
                    cval = 1 if yc else 0
                    ival = 1 if yc & art[c][(x, p)] else 0
                    n += 1; kc += cval; ki += ival; pc += cval; pi += ival
                    for acc in (by_base[x], by_deriv[y]):
                        acc[0] += cval; acc[1] += ival; acc[2] += 1
                bases.add(x); derivs.add(y)
                pairs_c += pc > 0; pairs_i += pi > 0
            clustering = 'base' if len(bases) >= MIN_BASE_CLUSTERS else 'derivative'
            groups = by_base if clustering == 'base' else by_deriv
            (plo, phi), (slo, shi) = cluster_bootstrap([tuple(v) for v in groups.values()], resamples)
            wpl, wph = wilson(kc, n); wsl, wsh = wilson(ki, n)
            cells[f'{ckey}{tkey}'] = dict(
                category=c, tier=tname, eligible_memberships=len([1 for x, _ in elig if pplus[c].get(x)]),
                evaluated_memberships=sum(1 for x, _ in evaluated if pplus[c].get(x)),
                contributing_bases=len(bases), contributing_derivatives=len(derivs),
                sum_p_plus=sum(len(pplus[c][b]) for b in bases), triples=n,
                psi=kc / n if n else None, sigma=ki / n if n else None,
                psi_wilson=[wpl, wph], sigma_wilson=[wsl, wsh],
                psi_bootstrap=[plo, phi], sigma_bootstrap=[slo, shi],
                bootstrap_clustering=clustering if n else None, bootstrap_clusters=len(groups),
                pairs_with_C=pairs_c, pairs_with_I=pairs_i)
    return dict(complete_models=len(complete_models), eligible_bases=len(eligible_bases),
                brand_tld_excluded_occurrences=brand_excluded, tiers=tiers, cells=cells,
                base_context=base_context)


def fmt_int(v):
    return '--' if v is None else f'{v:,}'


def fmt_pct(v):
    return '--' if v is None else f'{100 * v:.2f}\\%'


def write_tex(res, snapshot_date):
    lines = ['% Generated by rq3_persistence.py; overwritten on every run. Do not edit.']
    def mac(name, value):
        lines.append(f'\\newcommand{{\\rqthree{name}}}{{{value}}}')
    mac('SnapshotDate', snapshot_date)
    mac('SnapshotExecs', fmt_int(res['snapshot']['complete_executions']))
    mac('EligibleBases', fmt_int(res['analysis']['eligible_bases']))
    mac('CompleteModels', fmt_int(res['analysis']['complete_models']))
    mac('BrandExcluded', fmt_int(res['analysis']['brand_tld_excluded_occurrences']))
    for tkey, _, _ in TIERS:
        t = res['analysis']['tiers'][tkey]
        mac(f'TierMembers{tkey}', fmt_int(t['tier_memberships']))
        mac(f'TierBases{tkey}', fmt_int(t['tier_bases']))
        mac(f'EligMembers{tkey}', fmt_int(t['eligible_memberships']))
        mac(f'EligBases{tkey}', fmt_int(t['eligible_bases']))
        mac(f'EvalMembers{tkey}', fmt_int(t['evaluated_memberships']))
        mac(f'Bases{tkey}', fmt_int(t['evaluated_bases']))
        mac(f'Derivs{tkey}', fmt_int(t['evaluated_derivatives']))
        mac(f'CoverElig{tkey}', fmt_pct(t['coverage_members_vs_eligible']))
        mac(f'CoverTier{tkey}', fmt_pct(t['coverage_members_vs_tier']))
        mac(f'CoverBases{tkey}', fmt_pct(t['coverage_bases_vs_tier']))
        for _, ckey, _ in CATS:
            c = res['analysis']['cells'][f'{ckey}{tkey}']
            mac(f'EligMembers{ckey}{tkey}', fmt_int(c['eligible_memberships']))
            mac(f'EvalMembers{ckey}{tkey}', fmt_int(c['evaluated_memberships']))
            mac(f'Bases{ckey}{tkey}', fmt_int(c['contributing_bases']))
            mac(f'Derivs{ckey}{tkey}', fmt_int(c['contributing_derivatives']))
            mac(f'SumPplus{ckey}{tkey}', fmt_int(c['sum_p_plus']))
            mac(f'Triples{ckey}{tkey}', fmt_int(c['triples']))
            for metric, key in (('Psi', 'psi'), ('Sigma', 'sigma')):
                mac(f'{metric}{ckey}{tkey}', fmt_pct(c[key]))
                mac(f'{metric}WilsonLo{ckey}{tkey}', fmt_pct(c[f'{key}_wilson'][0]))
                mac(f'{metric}WilsonHi{ckey}{tkey}', fmt_pct(c[f'{key}_wilson'][1]))
                mac(f'{metric}BootLo{ckey}{tkey}', fmt_pct(c[f'{key}_bootstrap'][0]))
                mac(f'{metric}BootHi{ckey}{tkey}', fmt_pct(c[f'{key}_bootstrap'][1]))
            mac(f'PairsC{ckey}{tkey}', fmt_int(c['pairs_with_C']))
            mac(f'PairsI{ckey}{tkey}', fmt_int(c['pairs_with_I']))
            mac(f'Cluster{ckey}{tkey}', c['bootstrap_clustering'] or '--')
    with open(os.path.join(OUT, 'rq3_numbers.tex'), 'w') as f:
        f.write('\n'.join(lines) + '\n')

    rows = []
    for _, ckey, label in CATS:
        m = lambda x: f'\\rqthree{x}{ckey}Decl{{}}'
        rows.append(f'{label} & {m("Bases")} & {m("Triples")} & '
                    f'{m("Psi")} [{m("PsiBootLo")}, {m("PsiBootHi")}] & '
                    f'{m("Sigma")} [{m("SigmaBootLo")}, {m("SigmaBootHi")}] & '
                    f'{m("PairsC")} & {m("PairsI")} \\\\')
    table = [
        '% Generated by rq3_persistence.py; overwritten on every run. Requires booktabs and rq3_numbers.tex.',
        '\\begin{table}[t]',
        '\\centering',
        '\\caption{RQ3 persistence on the Declared tier (snapshot \\rqthreeSnapshotDate{}). '
        '$\\Psi$: share of base-vulnerable prompts on which the derivative is also vulnerable (class level); '
        '$\\Sigma$: share on which it emits the identical canonical artifact (instance level). '
        'Brackets: 95\\% clustered bootstrap intervals. '
        'Coverage: \\rqthreeEvalMembersDecl{} of \\rqthreeEligMembersDecl{} eligible memberships evaluated '
        '(\\rqthreeCoverEligDecl{}; \\rqthreeCoverTierDecl{} of all \\rqthreeTierMembersDecl{} Declared memberships), '
        'across \\rqthreeBasesDecl{} of \\rqthreeTierBasesDecl{} bases.}',
        '\\label{tab:rq3-persistence}',
        '\\begin{tabular}{lrrccrr}',
        '\\toprule',
        'Category & Bases & Triples & $\\Psi$ [95\\% CI] & $\\Sigma$ [95\\% CI] & Pairs ($C$) & Pairs ($I$) \\\\',
        '\\midrule',
        *rows,
        '\\bottomrule',
        '\\end{tabular}',
        '\\end{table}',
    ]
    with open(os.path.join(OUT, 'rq3_table.tex'), 'w') as f:
        f.write('\n'.join(table) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--resamples', type=int, default=2000)
    args = ap.parse_args()
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    tiers_sha = verify_tiers()
    with open(TIERS_CSV, newline='') as f:
        tiers_rows = list(csv.DictReader(f))
    data = read_ledger()
    digest = hashlib.sha256(json.dumps(
        [sorted(data['complete']), sorted(map(list, data['pkg'])), sorted(map(list, data['url']))],
        separators=(',', ':')).encode()).hexdigest()
    analysis = analyse(data, tiers_rows, args.resamples)
    st = os.stat(LEDGER)
    snapshot = dict(complete_executions=data['snap'][0],
                    max_completed_at=data['snap'][1], c1_complete_executions=len(data['complete']),
                    read_at=started.isoformat(), ledger_read_seconds=data['read_seconds'], data_sha256=digest)
    res = dict(version='v2026.10.16-rq3-01', snapshot=snapshot,
               definitions=dict(
                   label_layer='c1 corrected', brand_tld_review='excluded from nx',
                   pkg="package_finding_effective_c1 verdict='hallucinated_package' AND c1_status='retained'; identity ecosystem:normalized_name",
                   mal="url_finding_effective_c1 verdict='malicious' (exact canonical-URL feed match); identity canonical_url",
                   nx="url_finding_reviewed_c1 reviewed_verdict='registrable_hallucinated'; identity registrable_domain",
                   complete_execution="status='complete' and processed by both c1 passes",
                   eligible_base=f'base with all {N_PROMPTS} executions complete',
                   eligible_membership='tier-admitted pair whose base is eligible',
                   evaluated_membership=f'eligible membership whose child has all {N_PROMPTS} executions complete',
                   triple='(x,y,p) with p in P+(x,c), (x,y) evaluated', C='y has >=1 confirmed artifact of c on p',
                   I='x and y share >=1 identical canonical artifact of c on p',
                   sum_p_plus='sum of |P+(x,c)| over distinct contributing bases',
                   bootstrap=f'{args.resamples} resamples, seed {SEED}, percentile 95%; clusters = bases if >= {MIN_BASE_CLUSTERS} contribute, else derivatives'),
               analysis=analysis)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'rq3_results.json'), 'w') as f:
        json.dump(res, f, indent=1, sort_keys=False)
    write_tex(res, (data['snap'][1] or '')[:10])
    script_sha = sha256_file(os.path.abspath(__file__))
    log = [
        f'run_started_utc: {started.isoformat()}',
        f'run_seconds: {time.monotonic() - t0:.2f}',
        f'snapshot_complete_executions: {snapshot["complete_executions"]}',
        f'snapshot_max_completed_at: {snapshot["max_completed_at"]}',
        f'snapshot_c1_complete_executions: {snapshot["c1_complete_executions"]}',
        f'ledger_read_seconds: {snapshot["ledger_read_seconds"]}',
        f'ledger_path: {LEDGER}',
        f'ledger_size_bytes: {st.st_size}',
        f'ledger_mtime_utc: {datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}',
        'ledger_sha256: not computed (live file being written; see data_sha256)',
        f'data_sha256 (rows read): {digest}',
        f'cohort_tiers_sha256 (manifest-verified): {tiers_sha}',
        f'manifest_sha256: {sha256_file(MANIFEST)}',
        f'script_sha256: {script_sha}',
        f'python: {platform.python_version()}  sqlite: {sqlite3.sqlite_version}',
        f'bootstrap: {args.resamples} resamples, seed {SEED}',
    ]
    with open(os.path.join(OUT, 'rq3_run_log.txt'), 'w') as f:
        f.write('\n'.join(log) + '\n')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
