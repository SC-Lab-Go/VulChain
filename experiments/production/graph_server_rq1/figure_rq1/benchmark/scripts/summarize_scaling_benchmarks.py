#!/usr/bin/env python3
"""Summarize controlled DOT assembly scaling runs.

Created: 2026-10-15
Version: v2026.10.15-01
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def elapsed(path):
    value=re.search(r"Elapsed \(wall clock\) time.*: (.+)",path.read_text()).group(1).strip()
    parts=[float(x) for x in value.split(":")]
    return parts[-1]+(parts[-2]*60 if len(parts)>1 else 0)+(parts[-3]*3600 if len(parts)>2 else 0)
def metric(path,name,cast=float):
    return cast(re.search(rf"\s*{re.escape(name)}:\s*(.+)",path.read_text()).group(1).strip())
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--result",type=Path,required=True);a=ap.parse_args()
    manifest=json.loads((a.result/"inputs/SCALING_INPUT_MANIFEST.json").read_text()); rows=[]
    for size in (25,50,100):
        for run in (1,2,3):
            stem=a.result/f"runs/pct-{size:03d}-run-{run}"
            time=stem.with_suffix(".time"); dot=stem.with_suffix(".dot")
            seconds=elapsed(time); inputs=manifest["totals"][str(size)]
            rows.append({"size_percent":size,"run":run,"wall_seconds":seconds,
                         "user_seconds":metric(time,"User time (seconds)"),"system_seconds":metric(time,"System time (seconds)"),
                         "cpu_percent":metric(time,"Percent of CPU this job got",lambda x:float(x.rstrip('%'))),
                         "peak_rss_kib":metric(time,"Maximum resident set size (kbytes)",int),
                         "input_records":inputs["records"],"input_bytes":inputs["bytes"],
                         "output_bytes":dot.stat().st_size,"edges_per_second":inputs["records"]/seconds,
                         "output_sha256":sha256(dot),"load_before":str(stem)+".load-before.txt","load_after":str(stem)+".load-after.txt"})
    with (a.result/"scaling_performance.csv").open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.result/"scaling_performance.json").write_text(json.dumps({"runs":rows},indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__ == "__main__": main()
