"""Live results pipeline: discover, stage, recompute, validate and publish RQ results.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Shared logic for scripts/refresh_results.py, scripts/validate_results.py
         and scripts/freeze_submission.py.

The pipeline never reads the live measurement database. It consumes only
analysis snapshots that the production analysis pipeline has already
captured (SQLite backup API at a fixed cutoff), validated, and published
through its LATEST.json pointer. Calculations come from the existing entry
points in experiments/ (which in turn use the production calculation code in
vulchain_rq.py); nothing here redefines an estimator, eligibility rule or
cohort definition.
"""

import hashlib
import importlib.util
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import vulchain_rq as v
import vulchain_table2 as t2

REPO = Path(__file__).resolve().parents[1]
INPUT_FILES = ("canonical_comparisons.jsonl", "qualified_occurrences.jsonl", "evaluated_relationships.csv",
               "evaluated_model_manifest.csv", "model_status_audit.csv")
PRODUCTION_MACROS = ("evaluated_cohort_numbers.tex", "rq2_numbers_codex.tex", "rq3_numbers_codex.tex",
                     "rq4_numbers_codex.tex", "rq5_numbers_codex.tex")
VALIDATION_FILES = ("rq2_validation.json", "rq4_publication_validation.json", "rq5_publication_validation.json")
RQ5_FILES = tuple(v.RQ5_GRAPH_FILES) + ("sha256_manifest.txt",)
GRAPH_SHA256 = "25d669bdef51714de43369ceb6e5bfd22a8a170d616b894f569d4661f4da4c97"
SETUP_KEYS = ("Bases", "FT", "AD", "QT", "Merge", "UniqueDerivs", "UniqueModels", "Overlap", "Pairs")


class PipelineError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_config(path):
    path = Path(path)
    if not path.is_file():
        raise PipelineError(f"Configuration not found: {path} (copy configs/pipeline.example.json)")
    cfg = json.loads(path.read_text())
    for key in ("snapshot_root", "rq5_graph_export", "release_dir", "graph_dot", "results_dir"):
        if key not in cfg:
            raise PipelineError(f"Configuration is missing '{key}'")
        p = Path(cfg[key]).expanduser()
        cfg[key] = p if p.is_absolute() else (REPO / p)
    return cfg


def _module(relpath):
    path = REPO / "experiments" / relpath
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Discovery: latest snapshot the production pipeline published after validation
# ---------------------------------------------------------------------------

def validation_status(snapshot_dir):
    """PASS only if every recorded production validation passed."""
    problems = []
    for name in VALIDATION_FILES:
        path = snapshot_dir / name
        if not path.is_file():
            problems.append(f"{name} missing")
            continue
        data = json.loads(path.read_text())
        if "status" in data and data["status"] != "PASS":
            problems.append(f"{name} status {data['status']}")
        checks = data.get("checks")
        if isinstance(checks, list):
            bad = [c for c in checks if isinstance(c, str) and not c.startswith("PASS")]
            problems += [f"{name}: {c}" for c in bad]
        elif isinstance(checks, dict):
            bad = [k for k, c in checks.items() if (c.get("status") if isinstance(c, dict) else c) not in ("PASS", True)]
            problems += [f"{name}: {k}" for k in bad]
    return problems


def discover(snapshot_root):
    """Return (snapshot_dir, info) for the snapshot LATEST.json points to, verified in full."""
    latest_path = snapshot_root / "LATEST.json"
    raw = latest_path.read_bytes()
    latest = json.loads(raw)
    sid = latest["snapshot_id"]
    snap = snapshot_root / "snapshots" / sid
    if not snap.is_dir():
        raise PipelineError(f"LATEST.json names a missing snapshot: {sid}")
    manifest = json.loads((snap / "OUTPUT_MANIFEST.json").read_text())["files"]
    bad = [n for n, h in manifest.items() if not (snap / n).is_file() or v.sha(snap / n) != h]
    if bad:
        raise PipelineError(f"Snapshot {sid} does not match its OUTPUT_MANIFEST: {bad[:5]}")
    missing = [n for n in INPUT_FILES + PRODUCTION_MACROS if n not in manifest]
    if missing:
        raise PipelineError(f"Snapshot {sid} lacks required files: {missing}")
    problems = validation_status(snap)
    if problems:
        raise PipelineError(f"Snapshot {sid} did not pass production validation: {problems[:5]}")
    return snap, {"snapshot_id": sid, "cutoff_utc": latest.get("as_of"),
                  "latest_json_sha256": hashlib.sha256(raw).hexdigest(),
                  "output_manifest_sha256": v.sha(snap / "OUTPUT_MANIFEST.json"),
                  "primary_scope": latest.get("primary_scope")}


# ---------------------------------------------------------------------------
# Staging: immutable, checksummed copies of every input
# ---------------------------------------------------------------------------

def stage_inputs(snapshot_dir, info, cfg, staging):
    inputs = staging / "inputs"
    (inputs / "rq5_graph_export").mkdir(parents=True)
    (inputs / "production_macros").mkdir()
    manifest = json.loads((snapshot_dir / "OUTPUT_MANIFEST.json").read_text())["files"]
    for name in INPUT_FILES:
        shutil.copy2(snapshot_dir / name, inputs / name)
        if v.sha(inputs / name) != manifest[name]:
            raise PipelineError(f"Copy of {name} changed during staging")
    for name in PRODUCTION_MACROS:
        shutil.copy2(snapshot_dir / name, inputs / "production_macros" / name)
    pins = {}
    for line in (cfg["rq5_graph_export"] / "sha256_manifest.txt").read_text().splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            pins[parts[1].strip().lstrip("*")] = parts[0]
    for name in RQ5_FILES:
        shutil.copy2(cfg["rq5_graph_export"] / name, inputs / "rq5_graph_export" / name)
        if name in pins and v.sha(inputs / "rq5_graph_export" / name) != pins[name]:
            raise PipelineError(f"RQ5 graph export file {name} does not match its pin")
    files = {str(p.relative_to(inputs)): v.sha(p) for p in sorted(inputs.rglob("*")) if p.is_file()}
    record = dict(info, staged_at_utc=now(), source_snapshot_dir=str(snapshot_dir), files=files)
    write_json(inputs / "INPUT_MANIFEST.json", record)
    # LATEST.json must not have moved while we were copying.
    if hashlib.sha256((Path(snapshot_dir).parents[1] / "LATEST.json").read_bytes()).hexdigest() != info["latest_json_sha256"]:
        raise PipelineError("LATEST.json changed during staging; retry")
    return inputs


# ---------------------------------------------------------------------------
# Recompute with the existing entry points
# ---------------------------------------------------------------------------

def compute(inputs, lineage_csv):
    rq2, rq3, rq4, rq5 = (_module(p) for p in ("RQ2/rq2_table_01.py", "RQ3/rq3_table_01.py",
                                                "RQ4/rq4_table_01.py", "RQ5/rq5_table_01.py"))
    comparisons = v.load_comparisons(inputs)
    occurrences = v.load_occurrences(inputs)
    values = {}
    pairs = [(r["parent_id"], r["child_id"], r["adaptation_label"])
             for r in v.csv_rows(inputs / "evaluated_relationships.csv")]
    setup = v.Macros("setup")
    for key, value in t2.summarize(pairs)["values"].items():
        if key in SETUP_KEYS:
            setup.put("Eval" + key, value)
    setup.put("EvalTotal", setup.values["EvalUniqueModels"])
    values["setup"] = setup
    values["rq2"] = rq2.compute(comparisons)
    values["rq3"] = rq3.compute(comparisons, occurrences)
    values["rq4"] = rq4.compute(comparisons)
    if v.sha(lineage_csv) != rq5.LINEAGE_SHA256:
        raise PipelineError("Lineage CSV is not the released 01_model_model_edges.csv")
    g, _ = v.load_rq5_graph(inputs / "rq5_graph_export", lineage_csv)
    r = v.rq5_compute(g, v.load_models(inputs), v.load_pairs(inputs), comparisons, occurrences,
                      v.load_model_audit(inputs))
    values["rq5"] = rq5.table_macros(r)
    return values, comparisons


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def run_checks(values, comparisons, inputs):
    """Return a list of (check, passed, detail)."""
    out = []
    flat = {k: str(x) for m in values.values() for k, x in m.values.items()}
    production = v.manuscript_macros(inputs / "production_macros", *PRODUCTION_MACROS)
    compared = [k for k in flat if k in production]
    mismatched = [k for k in compared if flat[k] != production[k]]
    out.append(("recomputed values equal the snapshot's production macros", not mismatched and len(compared) == len(flat),
                f"{len(compared) - len(mismatched)}/{len(flat)} equal; mismatched {mismatched[:5]}; "
                f"absent {[k for k in flat if k not in production][:5]}"))

    member = lambda r, p: r["in_" + p]  # noqa: E731
    nested = all(not member(r, a) or member(r, b) for r in comparisons
                 for a, b in zip(v.POLICIES, v.POLICIES[1:]))
    out.append(("policy nesting Strict <= Intermediate <= Declared <= Extended", nested, ""))

    ids = [(r["membership_id_sha256"], r["category"], r["raw_prompt_sha256"]) for r in comparisons]
    out.append(("no duplicate comparisons", len(ids) == len(set(ids)), f"{len(ids)} comparisons"))

    rq3, rq4, rq2 = values["rq3"].values, values["rq4"].values, values["rq2"].values
    for code, legacy in (("Pkg", "Pkg"), ("Nx", "Nx")):
        parts = sum(int(rq4[f"rqfourN{legacy}Class{g}"]) for g in ("Adapter", "Finetune", "Quantized", "Merged"))
        out.append((f"{code}: RQ4 strata partition RQ3 tests", parts == int(rq3[f"rqThree{code}Tests"]),
                    f"{parts} vs {rq3[f'rqThree{code}Tests']}"))
        out.append((f"{code}: RQ2 Declared equals RQ3", rq2[f"rqTwoDeclared{code}Tests"] == rq3[f"rqThree{code}Tests"],
                    f"{rq2[f'rqTwoDeclared{code}Tests']} vs {rq3[f'rqThree{code}Tests']}"))
        added = sum(int(rq2[f"rqTwo{v.TAGS[p]}{'' if p == 'strict' else 'Added'}{code}Tests"]) for p in v.POLICIES)
        out.append((f"{code}: newly admitted strata partition Extended", added == int(rq2[f"rqTwoExtended{code}Tests"]),
                    f"{added} vs {rq2[f'rqTwoExtended{code}Tests']}"))
    order = all(int(m.values[k.replace("Tests", "InstanceRec")]) <= int(m.values[k.replace("Tests", "ClassRec")]) <= int(m.values[k])
                for m in (values["rq2"], values["rq3"]) for k in m.values
                if k.endswith("Tests") and k.replace("Tests", "ClassRec") in m.values)
    out.append(("instance <= class <= tests in every cell", order, ""))

    relationships = v.csv_rows(inputs / "evaluated_relationships.csv")
    models = v.csv_rows(inputs / "evaluated_model_manifest.csv")
    planned = v.csv_rows(inputs / "model_status_audit.csv")
    setup = values["setup"].values
    out.append(("EvalPairs equals evaluated relationships", int(setup["EvalPairs"]) == len(relationships),
                f"{setup['EvalPairs']} vs {len(relationships)}"))
    out.append(("EvalUniqueModels equals evaluated model manifest", int(setup["EvalUniqueModels"]) == len(models),
                f"{setup['EvalUniqueModels']} vs {len(models)}"))
    out.append(("evaluated models within the planned cohort", {m["model_id"] for m in models} <= {m["model_id"] for m in planned},
                f"{len(models)} evaluated of {len(planned)} planned"))
    memberships = {r["membership_id_sha256"] for r in relationships}
    out.append(("every comparison belongs to an evaluated relationship",
                all(r["membership_id_sha256"] in memberships for r in comparisons), ""))
    return out


def summary_counts(values, comparisons, inputs):
    s = values["setup"].values
    return {"evaluated_bases": s["EvalBases"], "evaluated_derivatives": s["EvalUniqueDerivs"],
            "evaluated_models": s["EvalUniqueModels"], "evaluated_relationships": s["EvalPairs"],
            "planned_models": len(v.csv_rows(inputs / "model_status_audit.csv")),
            "comparison_records": len(comparisons),
            "declared_tests": {c: int(values["rq3"].values[f"rqThree{c}Tests"]) for c in ("Pkg", "Nx", "Restricted")}}


def code_versions():
    files = sorted(p for p in (REPO / "experiments").rglob("*.py") if "__pycache__" not in p.parts)
    files += sorted((REPO / "scripts").glob("*.py"))
    return {str(p.relative_to(REPO)): v.sha(p) for p in files}


def write_outputs(staging, values):
    out = staging / "outputs"
    out.mkdir()
    for name, macros in values.items():
        (out / f"{name}_macros.tex").write_bytes(macros.text())
    flat = {name: dict(m.values) for name, m in values.items()}
    write_json(out / "VALUES.json", flat)
    return {str(p.relative_to(staging)): v.sha(p) for p in sorted(out.rglob("*")) if p.is_file()}


def diff_values(old, new):
    rows = []
    for group in sorted(set(old) | set(new)):
        a, b = old.get(group, {}), new.get(group, {})
        for k in sorted(set(a) | set(b)):
            if str(a.get(k)) != str(b.get(k)):
                rows.append((k, a.get(k), b.get(k)))
    return rows


def change_report(previous, record, values, manuscript_dir):
    lines = [f"# Results {record['snapshot_id']}", "",
             f"- Capture cutoff: {record['cutoff_utc']}",
             f"- Refreshed: {record['created_at_utc']}",
             f"- Validation: {'PASS' if record['validation_passed'] else 'FAIL'}", ""]
    counts = record["counts"]
    lines += ["| Count | Value |", "|---|---:|"] + [f"| {k} | {x} |" for k, x in counts.items()] + [""]
    new = {k: dict(m.values) for k, m in values.items()}
    if previous:
        rows = diff_values(previous["values"], new)
        lines += [f"## Changes since previous validated version {previous['snapshot_id']}", ""]
        prev_counts = previous["counts"]
        lines += [f"- {k}: {prev_counts.get(k)} -> {counts[k]}" for k in counts if prev_counts.get(k) != counts[k]]
        lines += ["", f"{len(rows)} macro values changed.", ""]
        lines += ["| Macro | Previous | New |", "|---|---|---|"] + [f"| {k} | {a} | {b} |" for k, a, b in rows[:200]]
    else:
        lines += ["No previous validated version."]
    manuscript = v.manuscript_macros(manuscript_dir, "evaluated_cohort_numbers.tex", *PRODUCTION_MACROS[1:])
    stale = [(k, manuscript[k], x) for g in new.values() for k, x in g.items() if k in manuscript and manuscript[k] != str(x)]
    lines += ["", "## Difference from the manuscript snapshot (data/manuscript_macros)", "",
              f"{len(stale)} macro values differ. The manuscript is never modified automatically.", ""]
    if stale:
        lines += ["| Macro | Manuscript | This version |", "|---|---|---|"] + [f"| {k} | {a} | {b} |" for k, a, b in stale[:200]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def read_latest(results):
    link = results / "latest"
    if not link.exists():
        return None
    return json.loads((link / "RESULTS_MANIFEST.json").read_text())


def publish(staging, results, sid):
    """Move a fully written, validated staging directory into versions/ and repoint latest atomically."""
    versions = results / "versions"
    versions.mkdir(exist_ok=True)
    target = versions / sid
    if target.exists():
        raise PipelineError(f"Version {sid} already exists; refusing to overwrite")
    os.rename(staging, target)
    for p in target.rglob("*"):
        if p.is_file():
            p.chmod(0o444)
    tmp = results / f".latest.{os.getpid()}"
    os.symlink(Path("versions") / sid, tmp)
    os.replace(tmp, results / "latest")
    return target


def acquire_lock(results):
    lock = results / ".refresh.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        pid = int((lock.read_text() or "0").strip() or 0)
        if pid and Path(f"/proc/{pid}").exists():
            raise PipelineError(f"Another refresh is running (pid {pid})")
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return lock


def recover_stale_staging(results):
    """Move staging directories left by interrupted runs to failed/ (never deleted, never published)."""
    moved = []
    for d in results.glob(".staging-*"):
        pid = d.name.rsplit("-", 1)[-1]
        if pid.isdigit() and Path(f"/proc/{pid}").exists():
            continue
        dest = results / "failed" / (d.name.lstrip(".") + "-interrupted")
        dest.parent.mkdir(exist_ok=True)
        os.rename(d, dest)
        moved.append(dest)
    return moved
