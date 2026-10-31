#!/usr/bin/env python3
"""Create exact 25/50/100% family-preserving edge inputs.

Created: 2026-10-15
Version: v2026.10.15-01
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    sources=sorted(args.source.glob("*.csv"))
    if len(sources) != 17: raise ValueError(f"Expected 17 CSVs, found {len(sources)}")
    args.output.mkdir(parents=True)
    dirs={p:(args.output/f"pct-{p:03d}") for p in (25,50,100)}
    for directory in dirs.values(): directory.mkdir()
    manifest={"version":"v2026.10.15-01","method":"exact-count deterministic systematic sampling within each immutable family CSV","families":[]}
    for source in sources:
        with source.open("rb") as stream: population=max(0,sum(1 for _ in stream)-1)
        targets={p:round(population*p/100) for p in (25,50)}
        streams={}; writers={}
        with source.open(newline="",encoding="utf-8") as inp:
            reader=csv.DictReader(inp)
            for p in (25,50):
                stream=(dirs[p]/source.name).open("x",newline="",encoding="utf-8")
                streams[p]=stream; writers[p]=csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator="\n"); writers[p].writeheader()
            for index,row in enumerate(reader,1):
                for p in (25,50):
                    k=targets[p]
                    if index*k//population > (index-1)*k//population: writers[p].writerow(row)
        for stream in streams.values(): stream.close()
        os.symlink(source,dirs[100]/source.name)
        entry={"file":source.name,"population":population,"source_bytes":source.stat().st_size,"source_sha256":sha256(source),"sizes":{}}
        for p in (25,50,100):
            path=dirs[p]/source.name
            entry["sizes"][str(p)]={"records":targets.get(p,population),"bytes":path.stat().st_size,"sha256":sha256(path.resolve())}
        manifest["families"].append(entry)
    for p in (25,50,100):
        manifest.setdefault("totals",{})[str(p)]={
            "records":sum(x["sizes"][str(p)]["records"] for x in manifest["families"]),
            "bytes":sum(x["sizes"][str(p)]["bytes"] for x in manifest["families"])}
    (args.output/"SCALING_INPUT_MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(manifest["totals"],indent=2,sort_keys=True))

if __name__ == "__main__": main()
