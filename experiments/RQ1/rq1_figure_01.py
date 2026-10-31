#!/usr/bin/env python3
"""Reproduce Figure fig:rq1 (RQ1) - offline DOT assembly scaling.

Created: 2026-10-30
Version: v2026.10.30-04
Purpose: "DOT assembly scaling for released graph: (a) wall time, (b) peak
         memory, (c) throughput; mean +/- std. over three runs."

Graph version. The benchmark assembled the full HuggingGraph v3 release
(HuggingGraph_v3.dot: 7,775,872 edges, 3,137,207 nodes, SHA-256 348d92cd...),
not the canonical VulChain.dot analytical view (7,666,919 edges, 25d669bd...).

What is recomputed, and with which code (experiments/production/graph_server_rq1/):
  1. Per-run wall time and peak RSS are parsed from the nine /usr/bin/time -v
     records with the original elapsed() and metric()
     (benchmark/scripts/summarize_scaling_benchmarks.py). Throughput is input
     records / wall seconds, with input records from SCALING_INPUT_MANIFEST.json,
     as in that script.
  2. Mean and sample SD per input size use the original stat()
     (benchmark/scripts/analyze_scaling_results.py). Edge and node totals use its
     parse_total() on the run stdout.
  3. Steps 1-2 are compared exactly with the recorded scaling_performance.csv and
     scaling_summary.csv, and, after rounding to the plotted precision, with the
     constants in the original plotting script (source/rq1_scaling_figure.py).
  4. The figure is drawn by running that original plotting script unchanged.
  5. The figure values quoted in the manuscript text are compared.
Optional (--rebuild-dot): the original benchmark builder assembles the 100%
input (the 17 released edge files) and the result must hash to 348d92cd...
The timings themselves are a hardware benchmark and are not re-measured.

Inputs:  experiments/production/graph_server_rq1/figure_rq1/{benchmark,source}/
         --release-dir (only with --rebuild-dot)
Output:  outputs/RQ1/figure_01/rq1_scaling_figure{,_cropped}.{pdf,png},
         outputs/RQ1/rq1_figure_01_values.csv, outputs/RQ1/rq1_figure_01_verification.md
Command: python experiments/RQ1/rq1_figure_01.py [--rebuild-dot --release-dir <release> --work <dir>]
"""

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vulchain_rq as v  # noqa: E402

PKG = v.REPO / "experiments" / "production" / "graph_server_rq1"
FIG = PKG / "figure_rq1"
RUN = FIG / "benchmark" / "results-local-20261015-scaling-03"
RELEASED_GRAPH_SHA256 = "348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b"
SIZES, RUNS = (25, 50, 100), (1, 2, 3)

# Figure values quoted in the manuscript text (experiments.tex, RQ1 paragraph on fig:rq1).
MANUSCRIPT_TEXT = {"wall 25% (s)": "13.30", "wall 100% (s)": "53.34",
                   "peak RSS 25% (GiB)": "0.207", "peak RSS 100% (GiB)": "0.447"}
# Known text discrepancy: "throughput remains stable near 144K edges/s"; recorded means are 145.8-146.3K.
MANUSCRIPT_THROUGHPUT_TEXT_K = 144


def verified_module(name, relpath):
    """Import a production file after checking it against the RQ1 source manifest."""
    manifest = {f["path"]: f for f in json.loads((PKG / "SOURCE_MANIFEST.json").read_text())["files"]}
    path = PKG / relpath
    v.require(v.sha(path) == manifest[relpath]["published_sha256"], "Production source changed: " + relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plotted_constants(script):
    tree = ast.parse(script.read_text())
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper()
            and isinstance(n.value, ast.List)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=v.REPO / "outputs" / "RQ1")
    parser.add_argument("--rebuild-dot", action="store_true",
                        help="also assemble the 100%% input with the original builder (~55 s, writes 1 GB to --work)")
    parser.add_argument("--release-dir", type=Path, help="extracted graph release (needed for --rebuild-dot)")
    parser.add_argument("--work", type=Path, help="scratch directory for --rebuild-dot (must not contain pct-100.dot)")
    args = parser.parse_args()

    summarize = verified_module("summarize_scaling_benchmarks", "figure_rq1/benchmark/scripts/summarize_scaling_benchmarks.py")
    analyze = verified_module("analyze_scaling_results", "figure_rq1/benchmark/scripts/analyze_scaling_results.py")
    script = FIG / "source" / "rq1_scaling_figure.py"
    verified_module("rq1_scaling_figure_check", "figure_rq1/source/rq1_scaling_figure.py")  # hash check only

    rows, ok = [], True

    def check(name, got, want, exact=True):
        nonlocal ok
        match = (got == want) if exact else abs(float(got) - float(want)) <= 1e-9 * max(1.0, abs(float(want)))
        ok &= match
        rows.append((name, str(got), str(want), "MATCH" if match else "MISMATCH"))

    # 1. per-run measurements from the raw /usr/bin/time records
    totals = json.loads((RUN / "inputs" / "SCALING_INPUT_MANIFEST.json").read_text())["totals"]
    recorded = {(int(r["size_percent"]), int(r["run"])): r
                for r in csv.DictReader((RUN / "scaling_performance.csv").open(newline=""))}
    per_size = {}
    for size in SIZES:
        wall, rss, eps = [], [], []
        for run in RUNS:
            stem = RUN / "runs" / f"pct-{size:03d}-run-{run}"
            seconds = summarize.elapsed(stem.with_suffix(".time"))
            peak = summarize.metric(stem.with_suffix(".time"), "Maximum resident set size (kbytes)", int)
            records = totals[str(size)]["records"]
            rec = recorded[(size, run)]
            check(f"{size}% run {run} wall s", seconds, float(rec["wall_seconds"]), exact=False)
            check(f"{size}% run {run} peak RSS KiB", peak, int(rec["peak_rss_kib"]))
            check(f"{size}% run {run} edges/s", records / seconds, float(rec["edges_per_second"]), exact=False)
            check(f"{size}% run {run} stderr empty", stem.with_suffix(".stderr").stat().st_size, 0)
            wall.append(seconds)
            rss.append(peak / 1048576)
            eps.append(records / seconds)
        edges = {analyze.parse_total(RUN / "runs" / f"pct-{size:03d}-run-{r}.stdout", "Total edges") for r in RUNS}
        nodes = {analyze.parse_total(RUN / "runs" / f"pct-{size:03d}-run-{r}.stdout", "Total nodes") for r in RUNS}
        v.require(len(edges) == 1 and len(nodes) == 1, f"Runs disagree at {size}%")
        check(f"{size}% edges (stdout) = input records", edges.pop(), totals[str(size)]["records"])
        per_size[size] = dict(records=totals[str(size)]["records"], nodes=nodes.pop(),
                              wall=analyze.stat(wall), rss=analyze.stat(rss), eps=analyze.stat(eps))

    # 2. summary statistics vs the recorded summary
    summary = {int(r["size_percent"]): r for r in csv.DictReader((RUN / "scaling_summary.csv").open(newline=""))}
    for size, s in per_size.items():
        r = summary[size]
        for key, col in (("wall", "wall"), ("eps", "throughput")):
            mean_col = f"{col}_mean_seconds" if key == "wall" else "throughput_mean_edges_s"
            sd_col = f"{col}_sd_seconds" if key == "wall" else "throughput_sd_edges_s"
            check(f"{size}% {key} mean", s[key]["mean"], float(r[mean_col]), exact=False)
            check(f"{size}% {key} SD", s[key]["sample_sd"], float(r[sd_col]), exact=False)
        check(f"{size}% peak RSS mean GiB", s["rss"]["mean"], float(r["peak_rss_mean_gib"]), exact=False)
        check(f"{size}% output nodes", s["nodes"], int(r["output_nodes"]))
    check("100% output = released graph (recorded sha)", summary[100]["output_sha256"], RELEASED_GRAPH_SHA256)
    check("100% edges", per_size[100]["records"], 7775872)
    check("100% nodes", per_size[100]["nodes"], 3137207)

    # 3. plotted constants in the original figure script
    const = plotted_constants(script)
    expect = {
        "INPUT_PERCENT": list(SIZES),
        "EDGES_MILLIONS": [round(per_size[s]["records"] / 1e6, 3) for s in SIZES],
        "WALL_MEAN_S": [round(per_size[s]["wall"]["mean"], 2) for s in SIZES],
        "WALL_SD_S": [round(per_size[s]["wall"]["sample_sd"], 2) for s in SIZES],
        "RSS_MEAN_GIB": [round(per_size[s]["rss"]["mean"], 3) for s in SIZES],
        "THROUGHPUT_MEAN_KEDGES_S": [round(per_size[s]["eps"]["mean"] / 1000, 1) for s in SIZES],
        "THROUGHPUT_SD_KEDGES_S": [round(per_size[s]["eps"]["sample_sd"] / 1000, 1) for s in SIZES],
    }
    for name, want in expect.items():
        check(f"plotted {name}", const[name], want)

    # 4. manuscript text values
    text = {"wall 25% (s)": f"{per_size[25]['wall']['mean']:.2f}", "wall 100% (s)": f"{per_size[100]['wall']['mean']:.2f}",
            "peak RSS 25% (GiB)": f"{per_size[25]['rss']['mean']:.3f}", "peak RSS 100% (GiB)": f"{per_size[100]['rss']['mean']:.3f}"}
    for name, want in MANUSCRIPT_TEXT.items():
        check(f"manuscript text {name}", text[name], want)
    eps_k = sorted(round(per_size[s]["eps"]["mean"] / 1000, 1) for s in SIZES)
    notes = [f"Known text discrepancy (not counted): the manuscript says throughput is 'near {MANUSCRIPT_THROUGHPUT_TEXT_K}K edges/s'; "
             f"recomputed means are {eps_k[0]}K-{eps_k[-1]}K (100%: {per_size[100]['eps']['mean']:,.0f} edges/s, ~146K)."]

    # 5. draw the figure with the original script, unchanged
    fig_dir = args.out / "figure_01"
    fig_dir.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib
        run = subprocess.run([sys.executable, "-B", str(script)], cwd=fig_dir, capture_output=True, text=True)
        drawn = run.returncode == 0
        notes.append(f"Figure drawn by the original rq1_scaling_figure.py with matplotlib {matplotlib.__version__} -> {fig_dir}"
                     if drawn else "Figure script failed: " + run.stderr.strip()[-300:])
        ok &= drawn
        reference = FIG / "output" / "rq1_scaling_figure_cropped.pdf"
        notes.append("The manuscript's images/rq1_scaling_figure_cropped.pdf is byte-identical to the archived "
                     f"output {reference.relative_to(v.REPO)} (SHA-256 {v.sha(reference)[:16]}...); re-rendered files "
                     "depend on the matplotlib and font versions (original: matplotlib 3.10.0, DejaVu Serif).")
    except ImportError:
        notes.append("matplotlib not installed: values verified, figure not drawn.")

    # optional: rebuild the 100% graph with the original benchmark builder
    if args.rebuild_dot:
        v.require(args.release_dir and args.work, "--rebuild-dot needs --release-dir and --work")
        args.work.mkdir(parents=True, exist_ok=True)
        dot = args.work / "pct-100.dot"
        build = subprocess.run([sys.executable, "-B", str(FIG / "benchmark" / "scripts" / "build_hugginggraph_scaling.py"),
                                "--reference-builder", str(FIG / "benchmark" / "reference_builder" / "build_hugginggraph_v3.py"),
                                "--edge-dir", str(args.release_dir / "edges" / "csv"), "--output", str(dot)],
                               capture_output=True, text=True)
        v.require(build.returncode == 0, "Benchmark builder failed: " + build.stderr[-300:])
        check("rebuilt 100% DOT SHA-256 (HuggingGraph_v3.dot)", v.sha(dot), RELEASED_GRAPH_SHA256)

    with (args.out / "rq1_figure_01_values.csv").open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["size_percent", "edges", "nodes", "wall_mean_s", "wall_sd_s", "peak_rss_mean_gib",
                    "throughput_mean_edges_s", "throughput_sd_edges_s"])
        for s in SIZES:
            p = per_size[s]
            w.writerow([s, p["records"], p["nodes"], p["wall"]["mean"], p["wall"]["sample_sd"], p["rss"]["mean"],
                        p["eps"]["mean"], p["eps"]["sample_sd"]])
    return v.write_report(args.out / "rq1_figure_01_verification.md",
                          "RQ1 Figure fig:rq1 (DOT assembly scaling; HuggingGraph v3 release, not VulChain.dot)",
                          rows, ok, notes)


if __name__ == "__main__":
    raise SystemExit(main())
