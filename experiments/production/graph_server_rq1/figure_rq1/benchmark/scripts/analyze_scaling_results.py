#!/usr/bin/env python3
"""Validate and summarize the completed controlled assembly benchmark.

Created: 2026-10-15
Version: v2026.10.15-01
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,statistics
from collections import defaultdict
from pathlib import Path

OFFICIAL="348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b"
def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()
def parse_total(path,label):
    m=re.search(rf"^{re.escape(label)}\s+([0-9,]+)$",path.read_text(),re.M)
    if not m:raise ValueError(f"Missing {label} in {path}")
    return int(m.group(1).replace(",",""))
def stat(values):
    mean=statistics.mean(values);sd=statistics.stdev(values)
    return {"mean":mean,"sample_sd":sd,"cv_percent":100*sd/mean}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("result",type=Path);a=ap.parse_args()
    with (a.result/"scaling_performance.csv").open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
    groups=defaultdict(list);verified=[]
    for row in rows:
        size=int(row["size_percent"]);run=int(row["run"]);groups[size].append(row)
        stem=a.result/f"runs/pct-{size:03d}-run-{run}"
        dot=stem.with_suffix(".dot");stdout=stem.with_suffix(".stdout");stderr=stem.with_suffix(".stderr")
        digest=sha256(dot);edges=parse_total(stdout,"Total edges");nodes=parse_total(stdout,"Total nodes")
        if stderr.stat().st_size:raise ValueError(f"Nonempty stderr: {stderr}")
        if digest != row["output_sha256"]:raise ValueError(f"Hash mismatch: {dot}")
        if edges != int(row["input_records"]):raise ValueError(f"Count mismatch: {dot}")
        verified.append({"size_percent":size,"run":run,"edges":edges,"nodes":nodes,"sha256":digest,"bytes":dot.stat().st_size})
    summaries=[]
    for size in sorted(groups):
        rr=groups[size]
        hashes={x["sha256"] for x in verified if x["size_percent"]==size}
        counts={x["edges"] for x in verified if x["size_percent"]==size}
        nodes={x["nodes"] for x in verified if x["size_percent"]==size}
        if len(hashes)!=1 or len(counts)!=1 or len(nodes)!=1:raise ValueError(f"Nondeterministic size {size}")
        digest=next(iter(hashes))
        if size==100 and digest!=OFFICIAL:raise ValueError("100% DOT does not match release")
        wall=stat([float(x["wall_seconds"]) for x in rr]);rss=stat([int(x["peak_rss_kib"])/1048576 for x in rr]);through=stat([float(x["edges_per_second"]) for x in rr])
        summaries.append({"size_percent":size,"input_records":next(iter(counts)),"output_nodes":next(iter(nodes)),
                          "input_bytes":int(rr[0]["input_bytes"]),"output_bytes":int(rr[0]["output_bytes"]),
                          "wall_mean_seconds":wall["mean"],"wall_sd_seconds":wall["sample_sd"],"wall_cv_percent":wall["cv_percent"],
                          "peak_rss_mean_gib":rss["mean"],"peak_rss_sd_gib":rss["sample_sd"],"peak_rss_cv_percent":rss["cv_percent"],
                          "throughput_mean_edges_s":through["mean"],"throughput_sd_edges_s":through["sample_sd"],"throughput_cv_percent":through["cv_percent"],
                          "output_sha256":digest,"matches_official_release":size==100})
    with (a.result/"scaling_summary.csv").open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    (a.result/"scaling_summary.json").write_text(json.dumps({"summary":summaries,"verified_runs":verified,"official_release_sha256":OFFICIAL},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tex=[r"\begin{table}[t]",r"\centering",r"\caption{Controlled offline DOT assembly scalability (three sequential runs per size).}",r"\label{tab:rq1-scaling}",r"\begin{tabular}{r r r r r}",r"\toprule",r"Input & Edges & Wall time (s) & Peak RSS (GiB) & Throughput (edges/s) " + r"\\",r"\midrule"]
    for s in summaries:tex.append(f"{s['size_percent']}\\% & {s['input_records']:,} & {s['wall_mean_seconds']:.2f} $\\pm$ {s['wall_sd_seconds']:.2f} & {s['peak_rss_mean_gib']:.3f} $\\pm$ {s['peak_rss_sd_gib']:.3f} & {s['throughput_mean_edges_s']:,.0f} $\\pm$ {s['throughput_sd_edges_s']:,.0f} \\\\")
    tex += [r"\bottomrule",r"\end{tabular}",r"\vspace{2pt}",r"\begin{minipage}{0.98\columnwidth}\footnotesize Values are mean $\pm$ sample standard deviation. Inputs preserve all 17 relationship families. Network acquisition is excluded; the archived builder is single-process and CPU-bound.\end{minipage}",r"\end{table}"]
    (a.result/"RQ1_SCALING_TABLE.tex").write_text("\n".join(tex)+"\n",encoding="utf-8")
    print(json.dumps(summaries,indent=2))
if __name__=="__main__":main()
