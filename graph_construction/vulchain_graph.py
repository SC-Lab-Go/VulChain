#!/usr/bin/env python3
"""VulChain graph construction: all 17 relationship families in one file.

Created: 2026-10-30
Version: v2026.10.30-01
Purpose: Single-file distribution of the October 2, 2026 HuggingGraph v3
         construction pipeline that produced graph/VulChain.dot
         (byte-identical to HuggingGraph_v3.dot).

Each stage below is one original pipeline script, embedded verbatim and
executed exactly as `python <script>.py ...` would run it. Cross-script
imports resolve to the embedded copies. The SHA-256 of every embedded
script is recorded in MODULES and checked before any stage runs, so the
methodology cannot drift from the archived source.

Usage:
    python vulchain_graph.py list
    python vulchain_graph.py verify
    python vulchain_graph.py extract --to ./original_scripts
    python vulchain_graph.py [--workdir DIR] <stage> [stage options]

Example (rebuild the DOT from the 17 archived edge files):
    python vulchain_graph.py assemble --edge-dir edges/csv --output VulChain.dot

Stages that use script-relative default paths (model-lineage,
dataset-dataset-baseline, dataset-attributes, audit-datasets) treat
--workdir as the original script directory.

Source: SC-Lab-Go/HuggingGraph source/ (release v2026.10.02-07).
"""

import argparse
import builtins
import hashlib
import importlib.abc
import importlib.util
import sys
import types
from pathlib import Path

MODULES = {
    'model_lineage_edges': {
        "path": 'model_lineage_edges.py',
        "sha256": '7e984d912e9ca9d144015d75d690cd244e2f77c6161588004fd9945255763134',
        "relationships": '1',
        "summary": 'Model->Model lineage (finetune, adapter, quantized, merged, converted, new_version)',
    },
    'count_model_types': {
        "path": 'count_model_types.py',
        "sha256": 'd028d06ae0ada73d70fe06d479860f6b31e27272646273237ed4c99b2a02cd14',
        "relationships": '1',
        "summary": 'Model derivation-type classifier used by model-lineage',
    },
    'dataset_model_edges': {
        "path": 'dataset_model_edges.py',
        "sha256": '3c9008b80370003f12b991b9e1fe723283d3c139bdaece6038b7b7d57dae5b00',
        "relationships": '2',
        "summary": 'Dataset->Model trained_on edges',
    },
    'dataset_dataset_edges': {
        "path": 'baselines/dataset_dataset_edges.py',
        "sha256": '8f40a7f0742c631e52e673357695b5c819f64b5f444eeb76746018ef4da8b69a',
        "relationships": '3',
        "summary": 'Dataset->Dataset metadata-only baseline (derived_from)',
    },
    'extract_dataset_dataset_extended': {
        "path": 'extract_dataset_dataset_extended.py',
        "sha256": '0d8981274b78d9dd3cc3ddb5a850ce6393bdbcd9be55975c708b622efe44baf7',
        "relationships": '3',
        "summary": 'Dataset->Dataset evidence-aware candidate union',
    },
    'model_library_edges': {
        "path": 'model_library_edges.py',
        "sha256": '5bfcaf00aa82f2a17c982b71c7e51d6dcbe6ff6fceabcbc8dcc9d46b8235e137',
        "relationships": '4',
        "summary": 'Model->Library edges from card metadata',
    },
    'model_license_task_github_edges': {
        "path": 'model_license_task_github_edges.py',
        "sha256": 'e2ee9b66ecba5aaa41a3d15de1593c10ba24c1e7cedb73a312ce8abb3b28dd54',
        "relationships": '6,8',
        "summary": 'Model->License and Model->Task edges from card metadata',
    },
    'model_dataset_attribute_edges': {
        "path": 'model_dataset_attribute_edges.py',
        "sha256": '822f5e1eac42cebea2dd0470c8e156d30607e342f28094ea51e6549dfff02e2a',
        "relationships": '4-9',
        "summary": 'Shared model and Dataset attribute normalization',
    },
    'build_model_readme_attribute_subgraphs': {
        "path": 'build_model_readme_attribute_subgraphs.py',
        "sha256": '427412e776bee769a2edb5d6cb7e1435e11db76103ffa941a3d5643544d2b5cd',
        "relationships": '4,6,8',
        "summary": 'README-derived Model->Library/License/Task merge',
    },
    'build_latest_dataset_attributes': {
        "path": 'build_latest_dataset_attributes.py',
        "sha256": 'a0d5600950b97bb4be67e5d7e5310dad01bec14010e349eade0866e8091f23a1',
        "relationships": '5,7,9',
        "summary": 'Dataset->Library/License/Task from latest full READMEs',
    },
    'extract_model_github_edges_streaming': {
        "path": 'extract_model_github_edges_streaming.py',
        "sha256": '5b5e18563096a23aa290ec2b6ff323c781f6a7f03bb67bc744b83a67226de6dd',
        "relationships": '10',
        "summary": 'Model->GitHub streaming extraction',
    },
    'extract_dataset_github_edges_streaming': {
        "path": 'extract_dataset_github_edges_streaming.py',
        "sha256": '1312c53348ff3af238dca0ff39f4197d0efcaaf97c840d56ff81632ce1bda6f7',
        "relationships": '11',
        "summary": 'Dataset->GitHub streaming extraction',
    },
    'build_space_subgraphs': {
        "path": 'build_space_subgraphs.py',
        "sha256": '59d039fcf56d988d9e32eb7edac01c49e8f7e801fae76962738c01ab44294d3b',
        "relationships": '12,13',
        "summary": 'Model->Space and Dataset->Space used_by_space edges',
    },
    'extract_space_github_edges_streaming_full': {
        "path": 'extract_space_github_edges_streaming_full.py',
        "sha256": 'fcb4e6df3b8eb6278e00be860f8040cd62dedba61aa82719b12b3b1d039fec0e',
        "relationships": '14',
        "summary": 'Space->GitHub streaming extraction',
    },
    'build_space_license_task_agent_subgraphs': {
        "path": 'build_space_license_task_agent_subgraphs.py',
        "sha256": '6f4839b4db9c6140d702572831b0e35e808176ffd97d8614734ec635a5d39d6e',
        "relationships": '15,16,17',
        "summary": 'Space->License, Space->Task, Space->Agent framework',
    },
    'audit_dataset_subgraphs': {
        "path": 'audit_dataset_subgraphs.py',
        "sha256": '8387792154d41a50d393848886226abc750c544b2c2f8229f972d4c7afab337f',
        "relationships": '3,5,7,9,11',
        "summary": 'Dataset relationship coverage and consistency audit',
    },
    'prepare_hugginggraph_v3_edges': {
        "path": 'prepare_hugginggraph_v3_edges.py',
        "sha256": '2366486c0ee15aedd6472e199df41691ca03df3c4663e31296eddcd7f14d562a',
        "relationships": '1-17',
        "summary": 'Normalize and count-check the 17 numbered edge files (Space step queries the Hub API)',
    },
    'build_hugginggraph_v3': {
        "path": 'build_hugginggraph_v3.py',
        "sha256": 'a5c96d108b5800c1907a9f0eec129a80eb5d9ac67442b0cf1f67e701fdc8e1a2',
        "relationships": '1-17',
        "summary": 'Validate counts and write the DOT graph',
    },
}

STAGES = {
    'model-lineage': 'model_lineage_edges',
    'model-types': 'count_model_types',
    'dataset-model': 'dataset_model_edges',
    'dataset-dataset-baseline': 'dataset_dataset_edges',
    'dataset-dataset': 'extract_dataset_dataset_extended',
    'model-library': 'model_library_edges',
    'model-license-task-github': 'model_license_task_github_edges',
    'model-dataset-attributes': 'model_dataset_attribute_edges',
    'model-readme-attributes': 'build_model_readme_attribute_subgraphs',
    'dataset-attributes': 'build_latest_dataset_attributes',
    'model-github': 'extract_model_github_edges_streaming',
    'dataset-github': 'extract_dataset_github_edges_streaming',
    'space-edges': 'build_space_subgraphs',
    'space-github': 'extract_space_github_edges_streaming_full',
    'space-attributes': 'build_space_license_task_agent_subgraphs',
    'audit-datasets': 'audit_dataset_subgraphs',
    'prepare': 'prepare_hugginggraph_v3_edges',
    'assemble': 'build_hugginggraph_v3',
}


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _BundledModules(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve the embedded original scripts as importable modules."""

    def __init__(self, workdir):
        self.workdir = workdir

    def filename(self, name):
        return str(self.workdir / MODULES[name]["path"])

    def find_spec(self, fullname, path=None, target=None):
        if fullname in MODULES:
            return importlib.util.spec_from_loader(
                fullname, self, origin=self.filename(fullname)
            )
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.filename(module.__name__)
        code = compile(SOURCES[module.__name__], module.__file__, "exec")
        exec(code, module.__dict__)


def _install(workdir):
    finder = _BundledModules(workdir)
    sys.meta_path.insert(0, finder)
    # model_lineage_edges.py loads count_model_types.py by file path; resolve
    # that request to the embedded copy so no extra file is required.
    original = importlib.util.spec_from_file_location

    def spec_from_file_location(name, location=None, *args, **kwargs):
        if name in MODULES and location is not None:
            return importlib.util.spec_from_loader(
                name, finder, origin=finder.filename(name)
            )
        return original(name, location, *args, **kwargs)

    importlib.util.spec_from_file_location = spec_from_file_location
    return finder


def _run_stage(stage, argv, workdir):
    name = STAGES[stage]
    finder = _install(workdir)
    filename = finder.filename(name)
    main = types.ModuleType("__main__")
    main.__file__ = filename
    main.__builtins__ = builtins
    saved_main, saved_argv = sys.modules.get("__main__"), sys.argv
    sys.modules["__main__"] = main
    sys.argv = [filename] + list(argv)
    try:
        exec(compile(SOURCES[name], filename, "exec"), main.__dict__)
    finally:
        sys.argv = saved_argv
        if saved_main is not None:
            sys.modules["__main__"] = saved_main
    return 0


def _verify():
    failures = 0
    for name, meta in MODULES.items():
        status = "OK" if _sha256(SOURCES[name]) == meta["sha256"] else "MISMATCH"
        failures += status != "OK"
        print(f"{status:8} {meta['sha256']}  {meta['path']}")
    return 1 if failures else 0


def _extract(destination):
    destination = destination.expanduser().resolve()
    for name, meta in MODULES.items():
        path = destination / meta["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(SOURCES[name])
        print(path)
    return 0


def _list():
    print(f"{'stage':28} {'rel.':10} source script")
    for stage, name in STAGES.items():
        meta = MODULES[name]
        print(f"{stage:28} {meta['relationships']:10} {meta['path']}")
        print(f"{'':28} {'':10} {meta['summary']}")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Run '<stage> --help' for the options of an individual stage.",
    )
    parser.add_argument(
        "--workdir", type=Path, default=Path.cwd(),
        help="directory that stands in for the original script directory; stages "
             "with script-relative default paths read and write there (default: cwd)",
    )
    parser.add_argument("command", choices=["list", "verify", "extract", *STAGES])
    parser.add_argument("--to", type=Path, help="destination directory for 'extract'")
    # Everything after the stage name belongs to the stage, including --help.
    split = next((i for i, a in enumerate(argv) if a in STAGES), len(argv))
    args = parser.parse_args(argv[:split + 1])
    rest = argv[split + 1:]
    if args.command == "list":
        return _list()
    if args.command == "verify":
        return _verify()
    if args.command == "extract":
        if args.to is None:
            parser.error("extract requires --to")
        return _extract(args.to)
    if _verify_quiet() != 0:
        print("Embedded source checksum mismatch; refusing to run.", file=sys.stderr)
        return 1
    return _run_stage(args.command, rest, args.workdir.expanduser().resolve())


def _verify_quiet():
    return sum(_sha256(SOURCES[n]) != m["sha256"] for n, m in MODULES.items())



# ==========================================================================
# Embedded original scripts (verbatim).
# ==========================================================================

SOURCES = {}

# --- model_lineage_edges.py ------------------------------------------------
SOURCES['model_lineage_edges'] = r'''"""Create model-lineage edges from saved Hugging Face card metadata.

Two outputs are produced and deliberately kept separate:

model_lineage_edges.csv / .jsonl
    Declared lineage only. Schema is unchanged: source, edge_type, target.
    Every edge here comes from a field or tag that names a parent model
    explicitly.

model_lineage_edges_inferred.csv / .jsonl
    Weaker evidence, never mixed into the declared output. Schema is
    source, edge_type, target, evidence, confidence.

Change history:
2026-09-08 v2026.09.08-05
- Add the separate inferred-edge output described above.
- Mine five additional explicit parent fields into the declared output:
  base\\_model (markdown-escaped key), basemodel, source_model,
  duplicated_from and teacher_model.
- Add four inference layers, written only to the inferred output:
  ambiguous parent-ish fields, model IDs embedded in free-form card tags,
  same-owner license_link references whose name is contained in the child
  name, and same-owner repository-name suffix stripping.
- Record declared new_version successor relationships in the inferred output
  with edge_type new_version. Direction is older -> newer, which is the
  opposite of a parent edge, so these are never placed in the declared file.
- Consume trailing quantization shorthands such as q4_k_m as single
  repository-name tokens.
- Read models_without_metadata.jsonl and recover same-owner parents from
  repository names, the only signal those records carry.
- Validate every newly mined or inferred parent ID against the full crawled
  model-ID universe in all_huggingface_models_2026Aug28.csv.
- Backup: model_lineage_edges.py.bak.20260908-215638
2026-09-08 v2026.09.08-04
- Add validated parent IDs from an explicit allowlist of alternative fields.
- Normalize three observed misspellings of base_model_relationship.
- Backup: model_lineage_edges.py.bak.20260908-212730
2026-09-08 v2026.09.08-03
- Recover parent IDs encoded in base_model/base-model tags.
- Preserve tag-specific relationship types for tag-only parents.
- Backup: model_lineage_edges.py.bak.20260908-211848
"""

import csv
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse


# Directory containing this script, independent of the current working directory.
root = Path(__file__).resolve().parent
input_path = root / "models_with_metadata.jsonl"
no_metadata_path = root / "models_without_metadata.jsonl"
universe_path = root / "all_huggingface_models_2026Aug28.csv"
csv_path = root / "model_lineage_edges.csv"
jsonl_path = root / "model_lineage_edges.jsonl"
inferred_csv_path = root / "model_lineage_edges_inferred.csv"
inferred_jsonl_path = root / "model_lineage_edges_inferred.jsonl"

# Reuse the repository's existing model-type classification logic.
classifier_path = root / "count_model_types.py"
spec = importlib.util.spec_from_file_location(
    "count_model_types",
    classifier_path,
)
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)

valid_edge_types = {
    "finetune",
    "adapter",
    "quantized",
    "merged",
}

# Format-only conversions are not quantization, so they are reported with
# their own type and only ever appear in the inferred output.
conversion_edge_type = "converted"
successor_edge_type = "new_version"

# Applied when a field names a parent but no relationship is recognizable.
# This follows rule 7 in count_model_types.py, which already defaults a
# declared parent with no recognized relationship to fine-tune.
default_edge_type = "finetune"

alternative_parent_fields = {
    "Base Model": None,
    "Base model": None,
    "Base_model": None,
    "base model": None,
    "base-model": None,
    "base_models": None,
    "derived_from": "finetune",
    "finetuned_from": "finetune",
    "parent_model": None,
    "original_model": None,
    "real_base_model": None,
    "base_model_original": None,
    "base_model_sources": None,
}

# Additional fields that name a parent explicitly. Observed only on records
# with no base_model field, so they extend the declared output.
additional_parent_fields = {
    "base\\_model": None,
    "basemodel": None,
    "source_model": None,
    "duplicated_from": None,
    "teacher_model": "finetune",
}

# Fields that sometimes name a parent and sometimes name something else.
# Never written to the declared output.
weak_parent_fields = (
    "model",
    "models",
    "model_id",
    "model_link",
    "repo",
    "host_model",
    "prior",
    "lm_studio",
)

misspelled_relationship_fields = (
    "base_model_ralation",
    "base_model_realtion",
    "base_model_relatin",
)

# Card tags that are namespaced index entries rather than model references.
ignored_tag_prefixes = (
    "base_model:",
    "base-model:",
    "dataset:",
    "datasets:",
    "license:",
    "arxiv:",
    "doi:",
    "region:",
    "language:",
)

quantization_tokens = {
    "gguf", "awq", "gptq", "exl2", "exl3", "exllama", "aqlm", "hqq", "quanto",
    "bnb", "eetq", "spqr", "vptq", "torchao", "autoround", "imatrix", "imat",
    "i1", "int2", "int3", "int4", "int8", "fp4", "fp8", "nf4", "nvfp4",
    "mxfp4", "w4a16", "w8a8", "quantized", "quantization", "quant", "quants",
    "gptqmodel", "smashed",
}

adapter_tokens = {
    "lora", "qlora", "loras", "adapter", "adapters", "peft", "dora",
    "adalora", "loha", "lokr", "ia3", "oft", "boft", "vera",
}

merge_tokens = {
    "merge", "merged", "mergekit", "slerp", "ties", "dare", "linear-merge",
    "task-arithmetic",
}

conversion_tokens = {
    "onnx", "openvino", "ov", "ct2", "ctranslate2", "coreml", "tflite",
    "trt", "tensorrt", "neuron", "mlx", "safetensors", "bf16", "fp16",
    "ggml", "gguf-imat",
}

derivation_tokens = (
    quantization_tokens | adapter_tokens | merge_tokens | conversion_tokens
)

model_id_part = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
quantization_shorthand = re.compile(r"^(?:iq|q)\d(?:[_-][a-z0-9]+)*$")
bit_width_token = re.compile(r"^\d+bit$")
quantization_block = re.compile(
    r"[-_.](i?q\d(?:[_-][A-Za-z0-9]{1,3})+)$",
    re.IGNORECASE,
)
model_reference = re.compile(
    r"(?:https?://(?:www\.)?(?:huggingface\.co|hf\.co)/)?"
    r"([A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9._-]{1,96})"
)


def normalize_model_id(value):
    """Return a validated owner/repository ID, including from an HF URL."""
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.netloc.lower() not in {
            "huggingface.co",
            "www.huggingface.co",
            "hf.co",
            "www.hf.co",
        }:
            return None

        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0].lower() in {
            "datasets",
            "spaces",
            "organizations",
        }:
            return None
        candidate = "/".join(parts[:2])

    if len(candidate) > 96 or candidate.count("/") != 1:
        return None

    namespace, repository = candidate.split("/", 1)
    for part in (namespace, repository):
        if (
            not model_id_part.fullmatch(part)
            or part[-1] in ".-"
            or "--" in part
            or ".." in part
        ):
            return None

    if repository.endswith(".git"):
        return None

    return candidate


def load_model_id_universe(path):
    """Load every crawled model ID, keyed by lowercase form."""
    universe = {}

    if not path.exists():
        return universe

    with path.open(encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            model_id = line.strip()
            if model_id:
                universe.setdefault(model_id.lower(), model_id)

    return universe


def resolve_known_id(value, universe):
    """Return the canonical crawled ID for a candidate parent reference."""
    candidate = normalize_model_id(value)

    if candidate is None:
        return None

    if not universe:
        return candidate

    return universe.get(candidate.lower())


def referenced_ids(value, universe, depth=0):
    """Return canonical IDs for every model reference inside a value."""
    found = []

    if depth > 6:
        return found

    if isinstance(value, str):
        for match in model_reference.finditer(value):
            resolved = resolve_known_id(
                match.group(1).rstrip("./-"),
                universe,
            )
            if resolved is not None:
                found.append(resolved)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            found.extend(referenced_ids(item, universe, depth + 1))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(referenced_ids(item, universe, depth + 1))

    return found


def alternative_parent_values(field, value):
    """Extract candidate strings only from the approved field structures."""
    if field != "base_model_sources":
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if isinstance(item, str)]
        return []

    items = value if isinstance(value, (list, tuple, set)) else [value]
    candidates = []

    for item in items:
        if isinstance(item, str):
            candidates.append(item)
            continue
        if not isinstance(item, dict):
            continue

        for key in ("modelId", "model_id", "repo_id", "name", "repo_url", "url"):
            candidate = item.get(key)
            if isinstance(candidate, str):
                candidates.append(candidate)

    return candidates


def normalized_relationship_metadata(metadata):
    """Map observed relationship-key misspellings to the accepted alias."""
    if metadata.get("base_model_relation") is not None or metadata.get(
        "base_model_relationship"
    ) is not None:
        return metadata, False

    for field in misspelled_relationship_fields:
        if metadata.get(field) is not None:
            normalized = dict(metadata)
            normalized["base_model_relationship"] = metadata[field]
            return normalized, True

    return metadata, False


def tagged_parent_edges(metadata, fallback_edge_type):
    """Return parent/type pairs declared by indexed or legacy base-model tags."""
    tags = metadata.get("tags")

    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, (list, tuple, set)):
        return [], 0

    edges = []
    malformed = 0

    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue

        tag = raw_tag.strip()
        normalized_tag = tag.lower()

        if not normalized_tag.startswith(("base_model:", "base-model:")):
            continue

        payload = tag.split(":", 1)[1].strip()

        if not payload:
            malformed += 1
            continue

        relationship_text, separator, parent_text = payload.partition(":")
        relationship = classifier.RELATION_ALIASES.get(
            classifier.normalize_text(relationship_text)
        )

        if separator and relationship:
            source = parent_text.strip()
            edge_type = relationship
        else:
            # Legacy form: base_model:<model-id>.
            source = payload
            edge_type = fallback_edge_type

        if not source or edge_type not in valid_edge_types:
            malformed += 1
            continue

        edges.append((source, edge_type))

    return edges, malformed


def is_derivation_token(token):
    """Report whether a repository-name token marks a derived artifact."""
    return (
        token in derivation_tokens
        or quantization_shorthand.match(token) is not None
        or bit_width_token.match(token) is not None
    )


def name_candidates(repository):
    """Strip trailing derivation tokens, preserving the original separators."""
    stripped = []
    candidates = []
    remaining = repository

    while True:
        # A quantization shorthand such as q4_k_m contains separators of its
        # own, so it is consumed as one token before the word split.
        block = quantization_block.search(remaining)

        if block is not None:
            stripped.append(block.group(1).lower())
            remaining = remaining[: block.start()]
            candidates.append(remaining)
            continue

        pieces = re.split(r"([-_.])", remaining)
        words = pieces[0::2]
        separators = pieces[1::2]

        if len(words) < 2 or not is_derivation_token(words[-1].lower()):
            break

        stripped.append(words[-1].lower())
        name = words[0]

        for index in range(1, len(words) - 1):
            name += separators[index - 1] + words[index]

        remaining = name
        candidates.append(remaining)

    if not stripped:
        return [], []

    return candidates, stripped


def name_edge_type(tokens):
    """Choose an edge type from the stripped repository-name tokens."""
    if any(
        token in quantization_tokens
        or quantization_shorthand.match(token)
        or bit_width_token.match(token)
        for token in tokens
    ):
        return "quantized"
    if any(token in adapter_tokens for token in tokens):
        return "adapter"
    if any(token in merge_tokens for token in tokens):
        return "merged"
    if any(token in conversion_tokens for token in tokens):
        return conversion_edge_type
    return None


def same_owner_name_parent(model_id, universe):
    """Infer a same-owner parent from the child's repository name."""
    if not universe or "/" not in model_id:
        return None, None

    owner, repository = model_id.split("/", 1)
    candidates, tokens = name_candidates(repository)

    if not candidates:
        return None, None

    edge_type = name_edge_type(tokens)

    if edge_type is None:
        return None, None

    for candidate in candidates:
        resolved = universe.get(f"{owner}/{candidate}".lower())
        if resolved is not None and resolved != model_id:
            return resolved, edge_type

    return None, None


def comparable_name(text):
    """Reduce a repository name to comparable alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def license_link_parent(model_id, metadata, universe):
    """Return a same-owner license_link target contained in the child name."""
    if "/" not in model_id:
        return None

    owner, repository = model_id.split("/", 1)
    child = comparable_name(repository)

    for field in metadata:
        normalized_field = str(field).lower().replace("-", "_")

        if not normalized_field.startswith("license_link"):
            continue

        for reference in referenced_ids(metadata[field], universe):
            reference_owner, _, reference_name = reference.partition("/")

            if reference_owner.lower() != owner.lower():
                continue
            if reference == model_id:
                continue

            token = comparable_name(reference_name)

            if token and token != child and token in child:
                return reference

    return None


def tag_embedded_parents(metadata, universe):
    """Return model IDs embedded in free-form card tags."""
    tags = metadata.get("tags")

    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, (list, tuple, set)):
        return []

    found = []

    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue

        tag = raw_tag.strip()

        if tag.lower().startswith(ignored_tag_prefixes):
            continue

        found.extend(referenced_ids(tag, universe))

    return found


class EdgeWriter:
    """Write one edge row to a CSV file and a JSON Lines file together."""

    def __init__(self, csv_file, jsonl_file, fieldnames):
        self.fieldnames = fieldnames
        self.csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self.jsonl_file = jsonl_file

    def write(self, row):
        self.csv_writer.writerow(row)
        self.jsonl_file.write(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        )


universe = load_model_id_universe(universe_path)

seen_edges = set()
declared_edges_written = 0
tag_edges_written = 0
alternative_edges_written = 0
additional_edges_written = 0
skipped_self_edges = 0
skipped_duplicate_edges = 0
malformed_parent_tags = 0
invalid_alternative_parent_values = 0
normalized_relationship_records = 0

inferred_counts = {
    "weak_field": 0,
    "tag_embedded_id": 0,
    "license_link_sameowner": 0,
    "name_heuristic_sameowner": 0,
    "name_heuristic_no_metadata": 0,
    "new_version_field": 0,
}
no_metadata_records = 0
parentless_records = 0

inferred_fieldnames = ["source", "edge_type", "target", "evidence", "confidence"]


def register_edge(source, edge_type, target):
    """Validate and deduplicate one edge, reporting whether to write it."""
    global skipped_self_edges, skipped_duplicate_edges

    if source == target:
        skipped_self_edges += 1
        return False

    edge = (source, edge_type, target)

    if edge in seen_edges:
        skipped_duplicate_edges += 1
        return False

    seen_edges.add(edge)
    return True


with (
    input_path.open(encoding="utf-8") as input_file,
    csv_path.open("w", encoding="utf-8", newline="") as csv_file,
    jsonl_path.open("w", encoding="utf-8") as jsonl_file,
    inferred_csv_path.open("w", encoding="utf-8", newline="") as inferred_csv_file,
    inferred_jsonl_path.open("w", encoding="utf-8") as inferred_jsonl_file,
):
    declared_writer = EdgeWriter(
        csv_file,
        jsonl_file,
        ["source", "edge_type", "target"],
    )
    inferred_writer = EdgeWriter(
        inferred_csv_file,
        inferred_jsonl_file,
        inferred_fieldnames,
    )

    def write_inferred(source, edge_type, target, evidence, confidence):
        """Record one inferred edge with its provenance."""
        if edge_type not in valid_edge_types | {
            conversion_edge_type,
            successor_edge_type,
        }:
            return

        if not register_edge(source, edge_type, target):
            return

        inferred_counts[evidence] = inferred_counts.get(evidence, 0) + 1
        inferred_writer.write(
            {
                "source": source,
                "edge_type": edge_type,
                "target": target,
                "evidence": evidence,
                "confidence": confidence,
            }
        )

    for line_number, line in enumerate(input_file, start=1):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"Skipping invalid JSON on line {line_number}: {exc}")
            continue

        target = record.get("modelId")
        metadata = record.get("readme_metadata")

        if not isinstance(target, str) or not isinstance(metadata, dict):
            continue

        target = target.strip()
        if not target:
            continue

        classification_metadata, relationship_was_normalized = (
            normalized_relationship_metadata(metadata)
        )
        normalized_relationship_records += int(relationship_was_normalized)

        declared_parents = classifier.normalize_base_models(
            classification_metadata.get("base_model")
        )
        fallback_edge_type, _reason = classifier.classify_model(
            classification_metadata
        )

        # A source may be declared in base_model, in a base-model tag, or both.
        # Prefer the ordinary metadata field when both forms name the same source.
        parent_edges = {}

        if fallback_edge_type in valid_edge_types:
            for source in declared_parents:
                source = source.strip()
                if source:
                    parent_edges[source] = (fallback_edge_type, "base_model")

        tagged_edges, malformed = tagged_parent_edges(
            classification_metadata,
            fallback_edge_type,
        )
        malformed_parent_tags += malformed

        for source, edge_type in tagged_edges:
            parent_edges.setdefault(source, (edge_type, "tag"))

        for field, forced_edge_type in alternative_parent_fields.items():
            if field not in classification_metadata:
                continue

            candidates = alternative_parent_values(
                field,
                classification_metadata[field],
            )

            for candidate in candidates:
                source = normalize_model_id(candidate)
                edge_type = forced_edge_type or fallback_edge_type

                if source is None or edge_type not in valid_edge_types:
                    invalid_alternative_parent_values += 1
                    continue

                parent_edges.setdefault(
                    source,
                    (edge_type, f"alternative:{field}"),
                )

        # Additional explicit parent fields. A parent is accepted only when the
        # named model exists in the crawled ID universe.
        for field, forced_edge_type in additional_parent_fields.items():
            if field not in classification_metadata:
                continue

            for candidate in alternative_parent_values(
                field,
                classification_metadata[field],
            ):
                source = resolve_known_id(candidate, universe)

                if source is None:
                    invalid_alternative_parent_values += 1
                    continue

                edge_type = forced_edge_type or fallback_edge_type

                if edge_type not in valid_edge_types:
                    edge_type = default_edge_type

                parent_edges.setdefault(
                    source,
                    (edge_type, f"additional:{field}"),
                )

        for source, (edge_type, evidence) in parent_edges.items():
            if not register_edge(source, edge_type, target):
                continue

            if evidence == "base_model":
                declared_edges_written += 1
            elif evidence == "tag":
                tag_edges_written += 1
            elif evidence.startswith("additional:"):
                additional_edges_written += 1
            else:
                alternative_edges_written += 1

            declared_writer.write(
                {
                    "source": source,
                    "edge_type": edge_type,
                    "target": target,
                }
            )

        # Declared successor relationships. Direction is older -> newer, so
        # these are kept out of the parent-lineage output.
        for successor in referenced_ids(
            classification_metadata.get("new_version"),
            universe,
        ):
            write_inferred(
                target,
                successor_edge_type,
                successor,
                "new_version_field",
                "declared_successor",
            )

        if parent_edges:
            continue

        # No declared parent: fall back to the inference layers, in order of
        # decreasing evidence strength.
        parentless_records += 1

        weak_edge_type = (
            fallback_edge_type
            if fallback_edge_type in valid_edge_types
            else default_edge_type
        )

        for field in weak_parent_fields:
            if field not in classification_metadata:
                continue

            for source in referenced_ids(
                classification_metadata[field],
                universe,
            ):
                write_inferred(
                    source,
                    weak_edge_type,
                    target,
                    "weak_field",
                    "declared_weak",
                )

        license_source = license_link_parent(target, classification_metadata, universe)

        if license_source is not None:
            _, license_tokens = name_candidates(target.split("/", 1)[1])
            license_edge_type = (
                name_edge_type(license_tokens)
                or (
                    fallback_edge_type
                    if fallback_edge_type in valid_edge_types
                    else default_edge_type
                )
            )
            write_inferred(
                license_source,
                license_edge_type,
                target,
                "license_link_sameowner",
                "inferred_high",
            )

        for source in tag_embedded_parents(classification_metadata, universe):
            write_inferred(
                source,
                weak_edge_type,
                target,
                "tag_embedded_id",
                "inferred_medium",
            )

        name_source, name_type = same_owner_name_parent(target, universe)

        if name_source is not None:
            write_inferred(
                name_source,
                name_type,
                target,
                "name_heuristic_sameowner",
                "inferred_high",
            )

    # Records with no card metadata at all carry only their repository name.
    if no_metadata_path.exists():
        with no_metadata_path.open(encoding="utf-8") as no_metadata_file:
            for line_number, line in enumerate(no_metadata_file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Skipping invalid JSON on no-metadata line {line_number}: {exc}")
                    continue

                target = record.get("modelId")

                if not isinstance(target, str) or not target.strip():
                    continue

                target = target.strip()
                no_metadata_records += 1

                name_source, name_type = same_owner_name_parent(target, universe)

                if name_source is not None:
                    write_inferred(
                        name_source,
                        name_type,
                        target,
                        "name_heuristic_no_metadata",
                        "inferred_high",
                    )

declared_total = (
    declared_edges_written
    + tag_edges_written
    + alternative_edges_written
    + additional_edges_written
)
inferred_total = sum(inferred_counts.values())

if not universe:
    print(f"WARNING: {universe_path.name} not found; inference layers disabled")

print(f"Model IDs in crawled universe: {len(universe):,}")
print()
print(f"Declared edges: {declared_total:,}")
print(f"  From base_model fields:      {declared_edges_written:,}")
print(f"  From tag-only parents:       {tag_edges_written:,}")
print(f"  From alternative fields:     {alternative_edges_written:,}")
print(f"  From additional fields:      {additional_edges_written:,}")
print()
print(f"Inferred edges: {inferred_total:,}")
print(f"  Weak parent fields:          {inferred_counts['weak_field']:,}")
print(f"  Tag-embedded model IDs:      {inferred_counts['tag_embedded_id']:,}")
print(f"  license_link same owner:     {inferred_counts['license_link_sameowner']:,}")
print(f"  Name, with metadata:         {inferred_counts['name_heuristic_sameowner']:,}")
print(f"  Name, no metadata:           {inferred_counts['name_heuristic_no_metadata']:,}")
print(f"  Declared new_version:        {inferred_counts['new_version_field']:,}")
print()
print(f"Total unique edges:            {len(seen_edges):,}")
print(f"Parentless metadata records:   {parentless_records:,}")
print(f"No-metadata records scanned:   {no_metadata_records:,}")
print(f"Skipped self-edges:            {skipped_self_edges:,}")
print(f"Skipped duplicate edges:       {skipped_duplicate_edges:,}")
print(f"Malformed parent tags:         {malformed_parent_tags:,}")
print(f"Invalid alternative values:    {invalid_alternative_parent_values:,}")
print(f"Normalized relationship keys:  {normalized_relationship_records:,}")
print()
print(f"Declared CSV:   {csv_path}")
print(f"Declared JSONL: {jsonl_path}")
print(f"Inferred CSV:   {inferred_csv_path}")
print(f"Inferred JSONL: {inferred_jsonl_path}")
'''

# --- count_model_types.py --------------------------------------------------
SOURCES['count_model_types'] = r'''#!/usr/bin/env python3
"""Count model types from saved Hugging Face README metadata.

Change history:
2026-09-04 v2026.09.04-03
- Recognize legacy finetune:<value> tags as fine-tuning evidence.
- Default a remaining legacy base_model:<model-id> tag to fine-tune.
- Backup: count_model_types.py.bak.20260904-151244
2026-09-04 v2026.09.04-02
- Classify a legacy base_model:<model-id> tag accompanied by a merge tag as
  a heuristic merge only after the existing classification rules are checked.
- Backup: count_model_types.py.bak.20260904-150719
2026-09-04 v2026.09.04-01
- Default models with a declared base_model but no recognized relationship to
  finetune, while preserving all existing explicit and tag-based rules.
- Backup: count_model_types.py.bak.20260904-145808
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ADAPTER_TAGS = {
    "adapter", "peft", "lora", "adalora", "ia3",
    "loha", "lokr", "oft", "boft", "vera",
    "prompt-tuning", "prefix-tuning", "p-tuning",
}

MERGE_TAGS = {
    "merge", "merged", "mergekit", "mergekit-moe",
    "ties", "ties-merging", "dare", "dare-ties",
    "slerp", "linear-merge", "task-arithmetic",
}

FINETUNE_TAGS = {
    "finetune", "fine-tune", "fine-tuned", "finetuned",
    "fine-tuning", "sft", "instruction-tuning",
    "instruction-tuned", "dpo", "orpo", "kto", "rlhf",
}

QUANTIZED_TAGS = {
    "quantized", "quantization", "gguf", "gptq", "awq",
    "aqlm", "exl2", "hqq", "quanto", "bitsandbytes",
    "bnb", "compressed-tensors", "eetq", "autoround",
    "spqr", "vptq", "torchao", "int4", "int8", "fp8",
}


# Normalize alternative spellings to the five output classes.
RELATION_ALIASES = {
    # Fine-tuned
    "finetune": "finetune",
    "fine-tune": "finetune",
    "fine-tuned": "finetune",
    "finetuned": "finetune",
    "fine_tune": "finetune",
    "fine_tuned": "finetune",

    # Adapter
    "adapter": "adapter",
    "adapters": "adapter",
    "peft": "adapter",

    # Quantized
    "quantized": "quantized",
    "quantization": "quantized",
    "quantize": "quantized",

    # Merge
    "merge": "merged",
    "merged": "merged",
}


def normalize_text(value: Any) -> str:
    """Convert a metadata value to normalized lowercase text."""
    return str(value).strip().lower().replace("_", "-")


def normalize_tags(value: Any) -> set[str]:
    """Return normalized tags regardless of whether tags is a string or list."""
    if value is None:
        return set()

    if isinstance(value, str):
        return {normalize_text(value)}

    if isinstance(value, (list, tuple, set)):
        return {
            normalize_text(tag)
            for tag in value
            if tag is not None and str(tag).strip()
        }

    return {normalize_text(value)}


def normalize_base_models(value: Any) -> list[str]:
    """Convert base_model metadata into a list of model IDs."""
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, (list, tuple, set)):
        return [
            str(model_id).strip()
            for model_id in value
            if model_id is not None and str(model_id).strip()
        ]

    return [str(value).strip()] if str(value).strip() else []


def explicit_relationship(metadata: dict[str, Any]) -> str | None:
    """
    Read the explicit relationship first.

    Hugging Face's official field is base_model_relation.
    base_model_relationship is also accepted in case it appears in the data.
    """
    relationship = metadata.get("base_model_relation")

    if relationship is None:
        relationship = metadata.get("base_model_relationship")

    if relationship is None:
        return None

    # The standard field is normally a string, but handle a one-value list too.
    if isinstance(relationship, (list, tuple, set)):
        normalized_values = {
            normalize_text(value)
            for value in relationship
            if value is not None and str(value).strip()
        }

        resolved = {
            RELATION_ALIASES[value]
            for value in normalized_values
            if value in RELATION_ALIASES
        }

        return next(iter(resolved)) if len(resolved) == 1 else None

    normalized = normalize_text(relationship)
    return RELATION_ALIASES.get(normalized)


def indexed_relationship(tags: set[str]) -> str | None:
    """
    Read authoritative indexed tags such as:

        base_model:finetune:organization/model
        base_model:adapter:organization/model
    """
    relationships = set()

    for tag in tags:
        if not tag.startswith("base-model:") and not tag.startswith("base_model:"):
            continue

        parts = tag.replace("base_model:", "base-model:", 1).split(":", 2)

        if len(parts) < 2:
            continue

        relationship = RELATION_ALIASES.get(normalize_text(parts[1]))

        if relationship:
            relationships.add(relationship)

    return next(iter(relationships)) if len(relationships) == 1 else None


def classify_model(metadata: dict[str, Any]) -> tuple[str, str]:
    """
    Return (model_type, reason).

    Classification priority:
      1. Explicit base_model_relation/base_model_relationship
      2. Indexed base_model:<relationship>:<model> tags
      3. Merge condition
      4. Quantization tags
      5. Adapter tags
      6. Fine-tuning tags
      7. Declared base_model fallback to fine-tune
      8. Legacy base_model:<model> tag plus merge tag (heuristic)
      9. Remaining legacy base_model:<model> tag fallback to fine-tune
      10. Base model
    """
    tags = normalize_tags(metadata.get("tags"))
    base_models = normalize_base_models(metadata.get("base_model"))

    # 1. Explicit metadata relationship has highest priority.
    relationship = explicit_relationship(metadata)

    if relationship:
        return relationship, "explicit_base_model_relation"

    # 2. Check Hugging Face's indexed relationship tags.
    relationship = indexed_relationship(tags)

    if relationship:
        return relationship, "indexed_base_model_tag"

    has_indexed_base_tag = any(
        tag.startswith("base_model:") or tag.startswith("base-model:")
        for tag in tags
    )

    # 3. Merge: at least two parents and a merge-related tag.
    if len(set(base_models)) >= 2 and tags.intersection(MERGE_TAGS):
        return "merged", "multiple_base_models_and_merge_tag"

    # 4. A quantized artifact can also carry fine-tuning tags.
    if tags.intersection(QUANTIZED_TAGS):
        return "quantized", "quantization_tag"

    # 5. Adapter models are also technically fine-tuned, so check adapters first.
    if tags.intersection(ADAPTER_TAGS):
        return "adapter", "adapter_tag"

    # 6. General fine-tuning indicators.
    has_legacy_finetune_tag = any(
        tag.startswith((
            "finetune:",
            "fine-tune:",
            "fine-tuned:",
            "finetuned:",
            "fine-tuning:",
        ))
        for tag in tags
    )

    if tags.intersection(FINETUNE_TAGS) or has_legacy_finetune_tag:
        return "finetune", "finetune_tag"

    # 7. Approved fallback: a declared parent with no recognized relationship
    # or qualifying tag is treated as a fine-tuned model.
    if base_models:
        return "finetune", "base_model_present_default_finetune"

    # 8. Legacy metadata sometimes encodes only base_model:<model-id>. When a
    # merge tag is also present, retain the otherwise unresolved model as a
    # heuristic merge without overriding any established classification rule.
    if has_indexed_base_tag and tags.intersection(MERGE_TAGS):
        return "merged", "legacy_indexed_base_model_and_merge_tag"

    # 9. Approved fallback for legacy base_model:<model-id> tags with no
    # recognized relationship or higher-priority classification evidence.
    if has_indexed_base_tag:
        return "finetune", "legacy_base_model_tag_default_finetune"

    # 10. No relationship and no base_model means treat it as a base model.
    if not base_models and not has_indexed_base_tag:
        return "base", "no_base_model_relationship"

    return "unclassified", "unresolved_model_metadata"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count model types from Hugging Face README metadata."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path("models_with_metadata.jsonl"),
    )
    args = parser.parse_args()

    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    invalid_lines = 0
    total = 0

    with args.input.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_lines += 1
                print(f"Invalid JSON at line {line_number}: {exc}")
                continue

            metadata = record.get("readme_metadata")

            if not isinstance(metadata, dict):
                counts["unclassified"] += 1
                reasons["missing_metadata_object"] += 1
                total += 1
                continue

            model_type, reason = classify_model(metadata)
            counts[model_type] += 1
            reasons[reason] += 1
            total += 1

    print("\nModel type counts")
    print("-----------------")

    categories = [
        "base",
        "finetune",
        "adapter",
        "quantized",
        "merged",
        "unclassified",
    ]

    for category in categories:
        count = counts[category]
        percentage = (count / total * 100) if total else 0
        print(f"{category:15} {count:12,}  {percentage:7.2f}%")

    print("-----------------")
    print(f"{'total':15} {total:12,}")
    print(f"{'invalid JSON':15} {invalid_lines:12,}")

    print("\nClassification reasons")
    print("----------------------")

    for reason, count in reasons.most_common():
        print(f"{reason:45} {count:12,}")


if __name__ == "__main__":
    main()
'''

# --- dataset_model_edges.py ------------------------------------------------
SOURCES['dataset_model_edges'] = r'''#!/usr/bin/env python3
"""Create validated dataset-to-model ``trained_on`` edges.

The training relationship is declared by model-card metadata (the standard
``datasets`` field or ``dataset:``/``datasets:`` tags). The downloaded dataset
metadata supplies the authoritative dataset-ID universe used to validate and
canonicalize each source. Dataset-card fields that merely mention a model are
not treated as training evidence because they may describe generation,
evaluation, or provenance instead.

Created: 2026-09-14
Version: v2026.09.14-04

Change history:
2026-09-14 v2026.09.14-04
- Validate and canonicalize dataset sources against downloaded dataset metadata.
- Resolve case variants, Hub URLs, path suffixes, and unique bare names.
- Add configurable paths and detailed coverage accounting.
- Write new validated outputs by default, preserving previous files.
- Backup: dataset_model_edges.py.bak.20260914-163220
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_METADATA = SCRIPT_DIR / "all_model_readme_metadata_2026Aug28.jsonl"
DEFAULT_DATASET_METADATA = SCRIPT_DIR / "all_dataset_readme_metadata_2026Aug28.jsonl"
DEFAULT_CSV = SCRIPT_DIR / "dataset_model_edges_validated.csv"
DEFAULT_JSONL = SCRIPT_DIR / "dataset_model_edges_validated.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create dataset -> trained_on -> model edges from model-card "
            "declarations, validated against downloaded dataset metadata."
        )
    )
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA)
    parser.add_argument("--dataset-metadata", type=Path, default=DEFAULT_DATASET_METADATA)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    return parser.parse_args()


def validated_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    model_path = args.model_metadata.expanduser().resolve()
    dataset_path = args.dataset_metadata.expanduser().resolve()
    csv_path = args.csv.expanduser().resolve()
    jsonl_path = args.jsonl.expanduser().resolve()

    for path, label in ((model_path, "model metadata"), (dataset_path, "dataset metadata")):
        if not path.is_file():
            raise FileNotFoundError(f"{label.title()} file not found: {path}")
    if len({model_path, dataset_path, csv_path, jsonl_path}) != 4:
        raise ValueError("Input and output paths must all be different")
    for path in (csv_path, jsonl_path):
        if path.exists():
            raise FileExistsError(
                f"Output already exists: {path}\n"
                "Choose another path with --csv/--jsonl, or move the old "
                "output before rerunning."
            )
    return model_path, dataset_path, csv_path, jsonl_path


def scalar_strings(value: object) -> tuple[list[str], int]:
    """Return nonempty string values and a count of invalid members."""
    if isinstance(value, str):
        cleaned = value.strip()
        return ([cleaned] if cleaned else []), 0
    if isinstance(value, (list, tuple, set)):
        strings = []
        invalid = 0
        for item in value:
            if isinstance(item, str) and item.strip():
                strings.append(item.strip())
            elif item not in (None, ""):
                invalid += 1
        return strings, invalid
    if value in (None, ""):
        return [], 0
    return [], 1


def dataset_tags(value: object) -> tuple[list[str], int]:
    """Extract values from ``dataset:`` and ``datasets:`` card tags."""
    tags, invalid = scalar_strings(value)
    datasets = []
    for tag in tags:
        normalized = tag.lower()
        if normalized.startswith("dataset:"):
            dataset_id = tag.split(":", 1)[1].strip()
        elif normalized.startswith("datasets:"):
            dataset_id = tag.split(":", 1)[1].strip()
        else:
            continue
        if dataset_id:
            datasets.append(dataset_id)
    return datasets, invalid


def load_dataset_universe(
    path: Path,
) -> tuple[set[str], dict[str, str], dict[str, str], Counter[str], int]:
    """Load canonical dataset IDs plus safe lookup indexes."""
    exact_ids: set[str] = set()
    lowercase_ids: dict[str, str] = {}
    # A value of None marks a basename shared by multiple dataset IDs.
    basename_candidates: dict[str, str | None] = {}
    statuses: Counter[str] = Counter()
    invalid_json = 0

    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_json += 1
                print(f"Skipping invalid dataset JSON at line {line_number}: {exc}")
                continue
            statuses[str(record.get("status", "unknown"))] += 1
            dataset_id = record.get("datasetId")
            if not isinstance(dataset_id, str) or not dataset_id.strip():
                continue
            canonical = dataset_id.strip()
            exact_ids.add(canonical)
            lowercase_ids.setdefault(canonical.lower(), canonical)
            basename = canonical.rsplit("/", 1)[-1].lower()
            if basename not in basename_candidates:
                basename_candidates[basename] = canonical
            elif basename_candidates[basename] != canonical:
                basename_candidates[basename] = None

    unique_basenames = {
        basename: canonical
        for basename, canonical in basename_candidates.items()
        if canonical is not None
    }
    return exact_ids, lowercase_ids, unique_basenames, statuses, invalid_json


def clean_dataset_reference(value: str) -> tuple[str, bool]:
    """Return a trimmed dataset reference and whether it came from a URL."""
    candidate = value.strip().strip("'\"")
    parsed = urlparse(candidate)
    if not (parsed.scheme or parsed.netloc):
        return candidate.strip("/"), False
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
        "huggingface.co", "www.huggingface.co", "hf.co", "www.hf.co",
    }:
        return "", True
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() == "datasets":
        parts = parts[1:]
    if len(parts) < 2:
        return "", True
    return "/".join(parts), True


def resolve_dataset_id(
    value: str,
    exact_ids: set[str],
    lowercase_ids: dict[str, str],
    unique_basenames: dict[str, str],
) -> tuple[str | None, str]:
    """Resolve one card value to a canonical downloaded dataset ID."""
    candidate, was_url = clean_dataset_reference(value)
    if not candidate:
        return None, "unresolved"
    if candidate in exact_ids:
        return candidate, "url" if was_url else "exact"
    canonical = lowercase_ids.get(candidate.lower())
    if canonical is not None:
        return canonical, "url" if was_url else "case_normalized"

    # Some cards append a config or path to owner/repository. Strip it only
    # when the resulting owner/repository exists in the downloaded universe.
    parts = candidate.split("/")
    if len(parts) > 2:
        canonical = lowercase_ids.get("/".join(parts[:2]).lower())
        if canonical is not None:
            return canonical, "suffix_removed"

    # Resolve a bare repository name only when exactly one downloaded dataset
    # has that basename. Ambiguous bare names remain unresolved.
    if "/" not in candidate:
        canonical = unique_basenames.get(candidate.lower())
        if canonical is not None:
            return canonical, "unique_bare_name"
    return None, "unresolved"


def write_edges(
    model_path: Path,
    csv_path: Path,
    jsonl_path: Path,
    exact_ids: set[str],
    lowercase_ids: dict[str, str],
    unique_basenames: dict[str, str],
) -> Counter[str]:
    counters: Counter[str] = Counter()
    seen_edges: set[tuple[str, str, str]] = set()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        model_path.open(encoding="utf-8") as input_file,
        csv_path.open("x", encoding="utf-8", newline="") as csv_file,
        jsonl_path.open("x", encoding="utf-8") as jsonl_file,
    ):
        csv_writer = csv.DictWriter(
            csv_file, fieldnames=["source", "edge_type", "target"]
        )
        csv_writer.writeheader()

        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            counters["model_records"] += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                counters["invalid_model_json"] += 1
                print(f"Skipping invalid model JSON at line {line_number}: {exc}")
                continue

            target = record.get("modelId")
            metadata = record.get("readme_metadata")
            if not isinstance(target, str) or not target.strip():
                counters["invalid_model_ids"] += 1
                continue
            if not isinstance(metadata, dict) or not metadata:
                continue

            target = target.strip()
            counters["models_with_metadata"] += 1
            candidates: dict[str, str] = {}
            raw_datasets = metadata.get("datasets")
            if raw_datasets is not None:
                values, invalid = scalar_strings(raw_datasets)
                counters["invalid_dataset_values"] += invalid
                for value in values:
                    candidates.setdefault(value, "datasets_field")

            tag_values, invalid_tags = dataset_tags(metadata.get("tags"))
            counters["invalid_tag_values"] += invalid_tags
            for value in tag_values:
                candidates.setdefault(value, "dataset_tag")

            resolved_for_model: dict[str, str] = {}
            for raw_source, evidence in candidates.items():
                counters["candidate_references"] += 1
                source, resolution = resolve_dataset_id(
                    raw_source, exact_ids, lowercase_ids, unique_basenames
                )
                counters[f"resolution_{resolution}"] += 1
                if source is not None:
                    # Prefer the standard field if field and tag resolve to
                    # the same dataset for this model.
                    resolved_for_model.setdefault(source, evidence)

            model_has_edge = False
            for source, evidence in resolved_for_model.items():
                edge = (source, "trained_on", target)
                if edge in seen_edges:
                    counters["duplicate_edges"] += 1
                    continue
                seen_edges.add(edge)
                model_has_edge = True
                row = {"source": source, "edge_type": "trained_on", "target": target}
                csv_writer.writerow(row)
                jsonl_file.write(
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                )
                counters[f"edges_{evidence}"] += 1
            if model_has_edge:
                counters["models_with_edges"] += 1

    counters["unique_edges"] = len(seen_edges)
    return counters


def print_report(
    statuses: Counter[str],
    dataset_ids: int,
    invalid_dataset_json: int,
    counters: Counter[str],
    csv_path: Path,
    jsonl_path: Path,
) -> None:
    print("\nDataset universe\n----------------")
    print(f"Unique dataset IDs:             {dataset_ids:12,}")
    print(f"With dataset-card metadata:     {statuses.get('with_metadata', 0):12,}")
    print(f"Empty dataset-card metadata:    {statuses.get('no_metadata', 0):12,}")
    print(
        "Not returned by datasets API:   "
        f"{statuses.get('not_returned_by_datasets_api', 0):12,}"
    )
    print(f"Invalid dataset JSON lines:     {invalid_dataset_json:12,}")

    print("\nModel-card relationship extraction\n----------------------------------")
    print(f"Model records scanned:           {counters['model_records']:12,}")
    print(f"Models with metadata:            {counters['models_with_metadata']:12,}")
    print(f"Candidate dataset references:    {counters['candidate_references']:12,}")
    print(f"  Exact dataset IDs:             {counters['resolution_exact']:12,}")
    print(f"  Hugging Face URLs:             {counters['resolution_url']:12,}")
    print(f"  Case-normalized IDs:           {counters['resolution_case_normalized']:12,}")
    print(f"  Config/path suffix removed:    {counters['resolution_suffix_removed']:12,}")
    print(f"  Unique bare-name matches:      {counters['resolution_unique_bare_name']:12,}")
    print(f"  Unresolved references omitted: {counters['resolution_unresolved']:12,}")
    print(f"Models with validated edges:     {counters['models_with_edges']:12,}")
    print(f"Dataset-field edges:             {counters['edges_datasets_field']:12,}")
    print(f"Tag-only dataset edges:          {counters['edges_dataset_tag']:12,}")
    print(f"Total unique edges:              {counters['unique_edges']:12,}")
    print(f"Duplicate edges skipped:         {counters['duplicate_edges']:12,}")
    print(f"Invalid dataset values:          {counters['invalid_dataset_values']:12,}")
    print(f"Invalid tag members:             {counters['invalid_tag_values']:12,}")
    print(f"Invalid model IDs:               {counters['invalid_model_ids']:12,}")
    print(f"Invalid model JSON lines:        {counters['invalid_model_json']:12,}")
    print(f"\nCSV:   {csv_path}\nJSONL: {jsonl_path}")


def main() -> int:
    try:
        model_path, dataset_path, csv_path, jsonl_path = validated_paths(parse_args())
        exact_ids, lowercase_ids, unique_basenames, statuses, invalid_dataset_json = (
            load_dataset_universe(dataset_path)
        )
        counters = write_edges(
            model_path, csv_path, jsonl_path,
            exact_ids, lowercase_ids, unique_basenames,
        )
        print_report(
            statuses, len(exact_ids), invalid_dataset_json,
            counters, csv_path, jsonl_path,
        )
    except KeyboardInterrupt:
        print("Interrupted; incomplete outputs must be moved before rerunning.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- baselines/dataset_dataset_edges.py ------------------------------------
SOURCES['dataset_dataset_edges'] = r'''#!/usr/bin/env python3
"""Create dataset -> derived_from -> dataset lineage edges."""

import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent

INPUT_PATH = ROOT / "all_dataset_readme_metadata_2026Aug28.jsonl"

VALIDATED_CSV = ROOT / "dataset_dataset_edges_validated.csv"
VALIDATED_JSONL = ROOT / "dataset_dataset_edges_validated.jsonl"

UNRESOLVED_CSV = ROOT / "dataset_dataset_edges_unresolved.csv"
UNRESOLVED_JSONL = ROOT / "dataset_dataset_edges_unresolved.jsonl"

MAX_COVERAGE_CSV = ROOT / "dataset_dataset_edges_max_coverage.csv"
MAX_COVERAGE_JSONL = ROOT / "dataset_dataset_edges_max_coverage.jsonl"


# Exact metadata fields that can identify an upstream/parent dataset.
# Field names are normalized to lowercase with punctuation replaced by "_".
PARENT_FIELDS = {
    "source_dataset",
    "source_datasets",
    "source_dataasets",       # observed misspelling
    "derived_from",
    "parent_dataset",
    "parent_datasets",
    "base_dataset",
    "base_datasets",
    "dataset_source",
    "dataset_sources",
    "original_dataset",
    "original_dataset_id",
    "original_source",
    "prov_wasderivedfrom",
    "datasets",
}

# Relevant keys when a parent field contains dictionaries.
REFERENCE_KEYS = {
    "id",
    "dataset",
    "dataset_id",
    "datasetid",
    "repo_id",
    "repository",
    "name",
    "path",
    "url",
}

ID_PART = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")


def normalize_field_name(value):
    """Normalize different spellings of a metadata field."""
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


def reference_strings(value):
    """Extract possible dataset references from strings, lists, and dictionaries."""
    if isinstance(value, str):
        value = value.strip()
        if value:
            yield value
        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from reference_strings(item)
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if normalize_field_name(key) in REFERENCE_KEYS:
                yield from reference_strings(item)


def clean_reference(value):
    """Clean a dataset ID or Hugging Face dataset URL."""
    candidate = value.strip().strip("'\"`")

    for prefix in ("dataset:", "datasets:"):
        if candidate.lower().startswith(prefix):
            candidate = candidate.split(":", 1)[1].strip()
            break

    parsed = urlparse(candidate)

    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"}:
            return None

        if parsed.netloc.lower() not in {
            "huggingface.co",
            "www.huggingface.co",
            "hf.co",
            "www.hf.co",
        }:
            return None

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if parts and parts[0].lower() == "datasets":
            parts = parts[1:]

        if len(parts) < 2:
            return None

        candidate = "/".join(parts)

    return candidate.strip("/")


def plausible_hf_dataset_id(value):
    """Check whether a value has a plausible owner/dataset form."""
    if not isinstance(value, str):
        return False

    if len(value) > 200 or value.count("/") != 1:
        return False

    owner, repository = value.split("/", 1)

    for part in (owner, repository):
        if not part or not ID_PART.fullmatch(part):
            return False
        if part[-1] in ".-":
            return False
        if "--" in part or ".." in part:
            return False

    return not repository.endswith(".git")


def load_dataset_universe(path):
    """Load canonical dataset IDs and indexes for safe normalization."""
    exact_ids = set()
    lowercase_ids = {}
    basename_candidates = {}

    status_counts = {}
    records_scanned = 0
    invalid_json = 0

    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            records_scanned += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_json += 1
                print(
                    f"Skipping invalid JSON at line {line_number}: {exc}"
                )
                continue

            status = str(record.get("status", "unknown"))
            status_counts[status] = status_counts.get(status, 0) + 1

            dataset_id = record.get("datasetId")

            if not isinstance(dataset_id, str) or not dataset_id.strip():
                continue

            dataset_id = dataset_id.strip()
            exact_ids.add(dataset_id)
            lowercase_ids.setdefault(dataset_id.lower(), dataset_id)

            basename = dataset_id.rsplit("/", 1)[-1].lower()

            if basename not in basename_candidates:
                basename_candidates[basename] = dataset_id
            elif basename_candidates[basename] != dataset_id:
                # None means the bare name is ambiguous.
                basename_candidates[basename] = None

    unique_basenames = {
        basename: dataset_id
        for basename, dataset_id in basename_candidates.items()
        if dataset_id is not None
    }

    return (
        exact_ids,
        lowercase_ids,
        unique_basenames,
        status_counts,
        records_scanned,
        invalid_json,
    )


def resolve_dataset_reference(
    value,
    exact_ids,
    lowercase_ids,
    unique_basenames,
):
    """
    Return (source, category).

    category:
      validated  - matched downloaded dataset universe
      unresolved - plausible owner/dataset ID absent from universe
      rejected   - descriptive, ambiguous, malformed, or external value
    """
    candidate = clean_reference(value)

    if not candidate:
        return None, "rejected"

    if candidate in exact_ids:
        return candidate, "validated"

    canonical = lowercase_ids.get(candidate.lower())

    if canonical is not None:
        return canonical, "validated"

    # Handle owner/dataset/config or owner/dataset/path.
    parts = candidate.split("/")

    if len(parts) > 2:
        possible_repository = "/".join(parts[:2])
        canonical = lowercase_ids.get(possible_repository.lower())

        if canonical is not None:
            return canonical, "validated"

        # Do not retain arbitrary multi-component paths.
        return None, "rejected"

    # Resolve a bare name only when exactly one downloaded dataset has it.
    if "/" not in candidate:
        canonical = unique_basenames.get(candidate.lower())

        if canonical is not None:
            return canonical, "validated"

        # Values such as "original", "wikipedia", descriptions, filenames,
        # and ambiguous dataset names are not treated as graph nodes.
        return None, "rejected"

    # Maximum-coverage tier: preserve a plausible owner/dataset reference
    # even if it was absent from the downloaded snapshot.
    if plausible_hf_dataset_id(candidate):
        return candidate, "unresolved"

    return None, "rejected"


def extract_edges(
    path,
    exact_ids,
    lowercase_ids,
    unique_basenames,
):
    validated_edges = set()
    unresolved_edges = set()

    counters = {
        "records_scanned": 0,
        "records_with_metadata": 0,
        "candidate_values": 0,
        "validated_candidates": 0,
        "unresolved_candidates": 0,
        "rejected_candidates": 0,
        "self_edges": 0,
        "invalid_json": 0,
    }

    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            counters["records_scanned"] += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                counters["invalid_json"] += 1
                print(
                    f"Skipping invalid JSON at line {line_number}: {exc}"
                )
                continue

            target = record.get("datasetId")
            metadata = record.get("readme_metadata")

            if not isinstance(target, str) or not target.strip():
                continue

            if not isinstance(metadata, dict) or not metadata:
                continue

            target = target.strip()
            counters["records_with_metadata"] += 1

            candidates = set()

            for raw_field, value in metadata.items():
                field = normalize_field_name(raw_field)

                if field not in PARENT_FIELDS:
                    continue

                for candidate in reference_strings(value):
                    candidates.add(candidate)

            for candidate in candidates:
                counters["candidate_values"] += 1

                source, category = resolve_dataset_reference(
                    candidate,
                    exact_ids,
                    lowercase_ids,
                    unique_basenames,
                )

                if source is None:
                    counters["rejected_candidates"] += 1
                    continue

                if source.lower() == target.lower():
                    counters["self_edges"] += 1
                    continue

                edge = (source, "derived_from", target)

                if category == "validated":
                    validated_edges.add(edge)
                    counters["validated_candidates"] += 1
                else:
                    unresolved_edges.add(edge)
                    counters["unresolved_candidates"] += 1

    # If an edge appears in both categories, prefer validated.
    unresolved_edges.difference_update(validated_edges)

    return validated_edges, unresolved_edges, counters


def write_outputs(edges, csv_path, jsonl_path):
    """Write identical edge sets to CSV and JSONL."""
    for output_path in (csv_path, jsonl_path):
        if output_path.exists():
            raise FileExistsError(
                f"Output already exists: {output_path}\n"
                "Move or rename it before running the script again."
            )

    ordered_edges = sorted(edges)

    with (
        csv_path.open("x", encoding="utf-8", newline="") as csv_file,
        jsonl_path.open("x", encoding="utf-8") as jsonl_file,
    ):
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["source", "edge_type", "target"],
        )
        writer.writeheader()

        for source, edge_type, target in ordered_edges:
            row = {
                "source": source,
                "edge_type": edge_type,
                "target": target,
            }

            writer.writerow(row)
            jsonl_file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )


def endpoint_counts(edges):
    sources = {source for source, _, _ in edges}
    targets = {target for _, _, target in edges}
    return len(sources), len(targets)


def main():
    (
        exact_ids,
        lowercase_ids,
        unique_basenames,
        status_counts,
        universe_records,
        universe_invalid_json,
    ) = load_dataset_universe(INPUT_PATH)

    validated_edges, unresolved_edges, counters = extract_edges(
        INPUT_PATH,
        exact_ids,
        lowercase_ids,
        unique_basenames,
    )

    maximum_coverage_edges = validated_edges | unresolved_edges

    write_outputs(
        validated_edges,
        VALIDATED_CSV,
        VALIDATED_JSONL,
    )
    write_outputs(
        unresolved_edges,
        UNRESOLVED_CSV,
        UNRESOLVED_JSONL,
    )
    write_outputs(
        maximum_coverage_edges,
        MAX_COVERAGE_CSV,
        MAX_COVERAGE_JSONL,
    )

    validated_sources, validated_targets = endpoint_counts(
        validated_edges
    )
    unresolved_sources, unresolved_targets = endpoint_counts(
        unresolved_edges
    )
    maximum_sources, maximum_targets = endpoint_counts(
        maximum_coverage_edges
    )

    print()
    print("Dataset universe")
    print("----------------")
    print(f"Records scanned:                {universe_records:,}")
    print(f"Unique dataset IDs:             {len(exact_ids):,}")
    print(
        "With metadata:                 "
        f"{status_counts.get('with_metadata', 0):,}"
    )
    print(
        "Empty metadata:                "
        f"{status_counts.get('no_metadata', 0):,}"
    )
    print(
        "Not returned by API:           "
        f"{status_counts.get('not_returned_by_datasets_api', 0):,}"
    )
    print(f"Invalid JSON lines:             {universe_invalid_json:,}")

    print()
    print("Dataset lineage")
    print("---------------")
    print(f"Metadata records examined:      {counters['records_scanned']:,}")
    print(f"Records with metadata:          {counters['records_with_metadata']:,}")
    print(f"Candidate parent values:        {counters['candidate_values']:,}")
    print(f"Rejected descriptive values:    {counters['rejected_candidates']:,}")
    print(f"Self-edges skipped:             {counters['self_edges']:,}")

    print()
    print("Validated")
    print(f"  Edges:                        {len(validated_edges):,}")
    print(f"  Unique parent datasets:       {validated_sources:,}")
    print(f"  Unique child datasets:        {validated_targets:,}")

    print()
    print("Unresolved but plausible")
    print(f"  Edges:                        {len(unresolved_edges):,}")
    print(f"  Unique parent strings:        {unresolved_sources:,}")
    print(f"  Unique child datasets:        {unresolved_targets:,}")

    print()
    print("Maximum coverage")
    print(f"  Edges:                        {len(maximum_coverage_edges):,}")
    print(f"  Unique parent identifiers:    {maximum_sources:,}")
    print(f"  Unique child datasets:        {maximum_targets:,}")

    print()
    print(f"Validated CSV:     {VALIDATED_CSV}")
    print(f"Validated JSONL:   {VALIDATED_JSONL}")
    print(f"Unresolved CSV:    {UNRESOLVED_CSV}")
    print(f"Unresolved JSONL:  {UNRESOLVED_JSONL}")
    print(f"Maximum CSV:       {MAX_COVERAGE_CSV}")
    print(f"Maximum JSONL:     {MAX_COVERAGE_JSONL}")


if __name__ == "__main__":
    main()'''

# --- extract_dataset_dataset_extended.py -----------------------------------
SOURCES['extract_dataset_dataset_extended'] = r'''#!/usr/bin/env python3
"""Build evidence-aware Dataset-to-Dataset relationship graphs.

Created: 2026-10-02
Version: v2026.10.02-01
Purpose: Extend the metadata-only Dataset-Dataset baseline with preserved
         metadata evidence and full-README relationship evidence.

Change history:
- 2026-10-02 v2026.10.02-01: distinguish successful README responses from
  non-empty README bodies. Backup: extract_dataset_dataset_extended.py.bak.20261002-163418
- 2026-10-02 v2026.10.02-01: tighten reference-to-phrase association and
  suppress duplicate bare IDs inside URLs/code. Backup:
  extract_dataset_dataset_extended.py.bak.20261002-163636
- 2026-10-02 v2026.10.02-01: enforce sentence-boundary association and keep
  load_dataset calls as usage evidence. Backup:
  extract_dataset_dataset_extended.py.bak.20261002-164256
- 2026-10-02 v2026.10.02-01: add deduplicated graph-edge exports and a
  relationship-stratified lineage review sample. Backup:
  extract_dataset_dataset_extended.py.bak.20261002-164822

This program reads saved local snapshots only. It performs no network calls,
does not modify the baseline graph files, and can resume both input scans from
byte offsets stored in SQLite.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse


CHANGE_ID = "v2026.10.02-01"
SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
DEFAULT_METADATA = PARENT_DIR / "all_dataset_readme_metadata_2026Aug28.jsonl"
DEFAULT_READMES = PARENT_DIR / "all_dataset_readmes_full_2026Sep28.jsonl"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "refined_v3"

FIELD_RELATION = {
    "derived_from": ("derived_from", "high"),
    "parent_dataset": ("derived_from", "high"),
    "parent_datasets": ("derived_from", "high"),
    "base_dataset": ("derived_from", "high"),
    "base_datasets": ("derived_from", "high"),
    "original_dataset": ("derived_from", "high"),
    "original_dataset_id": ("derived_from", "high"),
    "prov_wasderivedfrom": ("derived_from", "high"),
    "source_dataset": ("uses_source_data", "medium"),
    "source_datasets": ("uses_source_data", "medium"),
    "source_dataasets": ("uses_source_data", "medium"),
    "dataset_source": ("uses_source_data", "medium"),
    "dataset_sources": ("uses_source_data", "medium"),
    "original_source": ("uses_source_data", "medium"),
    "datasets": ("unknown_dataset_relation", "low"),
}

REFERENCE_KEYS = {
    "id", "dataset", "dataset_id", "datasetid", "repo_id", "repository",
    "name", "path", "url",
}

LINEAGE_RELATIONS = {
    "derived_from", "merged_from", "filtered_from", "translated_from",
    "synthetic_from", "subset_of",
}

CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
ID_PART = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
HF_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:huggingface\.co|hf\.co)/datasets/"
    r"([A-Za-z0-9_][A-Za-z0-9._-]*/[A-Za-z0-9_][A-Za-z0-9._-]*)",
    re.IGNORECASE,
)
LOAD_DATASET_RE = re.compile(
    r"\bload_dataset\s*\(\s*[rubfRUBF]*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
BARE_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"([A-Za-z0-9_][A-Za-z0-9._-]*/[A-Za-z0-9_][A-Za-z0-9._-]*)"
)

RELATION_PATTERNS = (
    ("translated_from", "high", re.compile(
        r"\b(?:translated|translation|machine[- ]translated)\b.{0,80}\b(?:from|of)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("filtered_from", "high", re.compile(
        r"\b(?:filtered|cleaned|deduplicated)\b.{0,80}\b(?:from|version of)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("merged_from", "high", re.compile(
        r"\b(?:merged|combined|concatenated)\s+(?:from|using)\b|"
        r"\b(?:merge|combination|mixture|concatenation)\s+of\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("synthetic_from", "high", re.compile(
        r"\b(?:synthetic(?:ally)?\s+)?generated\s+(?:from|using|based on)\b|"
        r"\bsynthetic\s+(?:dataset|data).{0,50}\b(?:from|using|based on)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("subset_of", "high", re.compile(
        r"\b(?:subset|sampled|sampling)\b.{0,80}\b(?:from|of)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("derived_from", "high", re.compile(
        r"\b(?:derived|adapted|built|created|constructed|based)\b.{0,80}"
        r"\b(?:from|on)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("evaluates_on", "medium", re.compile(
        r"\b(?:evaluation|evaluate[sd]?|benchmark(?:ed|ing)?|test(?:ed|ing)?)\b",
        re.IGNORECASE,
    )),
    ("uses_source_data", "medium", re.compile(
        r"\b(?:source dataset|source data|data source|sourced from|collected from)\b",
        re.IGNORECASE,
    )),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract evidence-aware dataset relationships from local snapshots."
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--readmes", type=Path, default=DEFAULT_READMES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--max-metadata-records", type=int, default=0)
    parser.add_argument("--max-readme-records", type=int, default=0)
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args()


def normalize_field_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def reference_strings(value: object):
    if isinstance(value, str):
        value = value.strip()
        if value:
            yield value
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from reference_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if normalize_field_name(key) in REFERENCE_KEYS:
                yield from reference_strings(item)


def clean_reference(value: str) -> str | None:
    candidate = value.strip().strip("'\"`").rstrip(".,;:!?)\]}>")
    for prefix in ("dataset:", "datasets:"):
        if candidate.lower().startswith(prefix):
            candidate = candidate.split(":", 1)[1].strip()
            break
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.netloc.lower() not in {
            "huggingface.co", "www.huggingface.co", "hf.co", "www.hf.co",
        }:
            return None
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if parts and parts[0].lower() == "datasets":
            parts = parts[1:]
        if len(parts) < 2:
            return None
        candidate = "/".join(parts[:2])
    return candidate.strip("/")


def plausible_hf_id(value: str) -> bool:
    if len(value) > 200 or value.count("/") != 1:
        return False
    owner, repository = value.split("/", 1)
    for part in (owner, repository):
        if not part or not ID_PART.fullmatch(part):
            return False
        if part[-1] in ".-" or "--" in part or ".." in part:
            return False
    return not repository.endswith(".git")


def load_universe(path: Path):
    exact: set[str] = set()
    lowercase: dict[str, str] = {}
    basenames: dict[str, str | None] = {}
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
            counts[str(record.get("status") or "unknown")] += 1
            dataset_id = record.get("datasetId")
            if not isinstance(dataset_id, str) or not dataset_id.strip():
                continue
            dataset_id = dataset_id.strip()
            exact.add(dataset_id)
            lowercase.setdefault(dataset_id.lower(), dataset_id)
            basename = dataset_id.rsplit("/", 1)[-1].lower()
            if basename not in basenames:
                basenames[basename] = dataset_id
            elif basenames[basename] != dataset_id:
                basenames[basename] = None
    unique_basenames = {key: value for key, value in basenames.items() if value}
    return exact, lowercase, unique_basenames, counts


def readme_snapshot_counts(path: Path):
    """Independently count README statuses and non-empty bodies."""
    statuses: Counter[str] = Counter()
    nonempty = 0
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
            status = str(record.get("status") or "unknown")
            statuses[status] += 1
            if status == "ok" and isinstance(record.get("readme"), str) and record["readme"]:
                nonempty += 1
    return statuses, nonempty


def resolve_reference(value, exact, lowercase, unique_basenames):
    candidate = clean_reference(value)
    if not candidate:
        return None, "rejected"
    if candidate in exact:
        return candidate, "validated"
    canonical = lowercase.get(candidate.lower())
    if canonical:
        return canonical, "validated"
    parts = candidate.split("/")
    if len(parts) > 2:
        canonical = lowercase.get("/".join(parts[:2]).lower())
        return (canonical, "validated") if canonical else (None, "rejected")
    if len(parts) == 1:
        canonical = unique_basenames.get(candidate.lower())
        return (canonical, "validated") if canonical else (None, "rejected")
    if plausible_hf_id(candidate):
        return candidate, "unresolved"
    return None, "rejected"


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS evidence("
        "source_dataset TEXT NOT NULL,target_dataset TEXT NOT NULL,"
        "relationship_type TEXT NOT NULL,evidence_source TEXT NOT NULL,"
        "evidence_field TEXT NOT NULL,raw_reference TEXT NOT NULL,"
        "context TEXT NOT NULL,source_status TEXT NOT NULL,"
        "confidence TEXT NOT NULL,retrieved_at_utc TEXT NOT NULL,"
        "PRIMARY KEY(source_dataset,target_dataset,relationship_type,"
        "evidence_source,evidence_field,raw_reference))"
    )
    db.execute("CREATE INDEX IF NOT EXISTS evidence_target ON evidence(target_dataset)")
    db.execute("CREATE INDEX IF NOT EXISTS evidence_status ON evidence(source_status,confidence)")
    db.commit()
    return db


def state_get(db: sqlite3.Connection, key: str, default: str = "0") -> str:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return default if row is None else str(row[0])


def state_set(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def input_signature(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def initialize_state(db, metadata_path: Path, readme_path: Path):
    configuration = json.dumps({
        "change_id": CHANGE_ID,
        "metadata": input_signature(metadata_path),
        "readmes": input_signature(readme_path),
    }, sort_keys=True)
    stored = state_get(db, "configuration", "")
    if stored and stored != configuration:
        raise RuntimeError("State database belongs to different input snapshots")
    if not stored:
        with db:
            state_set(db, "configuration", configuration)
            state_set(db, "metadata_offset", 0)
            state_set(db, "metadata_records", 0)
            state_set(db, "metadata_complete", 0)
            state_set(db, "readme_offset", 0)
            state_set(db, "readme_records", 0)
            state_set(db, "readme_ok", 0)
            state_set(db, "readme_complete", 0)


def evidence_row(source, target, relation, evidence_source, field, raw,
                 context, status, confidence, retrieved):
    return (
        source, target, relation, evidence_source, field, raw[:1000],
        re.sub(r"\s+", " ", context).strip()[:1000], status, confidence,
        str(retrieved or ""),
    )


UPSERT = (
    "INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?) "
    "ON CONFLICT(source_dataset,target_dataset,relationship_type,evidence_source,"
    "evidence_field,raw_reference) DO UPDATE SET "
    "context=CASE WHEN length(excluded.context)>length(context) "
    "THEN excluded.context ELSE context END,"
    "source_status=CASE WHEN source_status='validated' THEN source_status "
    "ELSE excluded.source_status END,"
    "confidence=CASE confidence "
    "WHEN 'high' THEN confidence WHEN 'medium' THEN CASE WHEN excluded.confidence='high' "
    "THEN excluded.confidence ELSE confidence END ELSE excluded.confidence END"
)


def scan_metadata(db, path, exact, lowercase, unique_basenames, batch_size, limit):
    if state_get(db, "metadata_complete") == "1":
        print("Metadata scan already complete.", flush=True)
        return
    offset = int(state_get(db, "metadata_offset"))
    total_records = int(state_get(db, "metadata_records"))
    processed_run = 0
    pending = []
    counters = Counter()
    with path.open("rb") as stream:
        stream.seek(offset)
        while not limit or processed_run < limit:
            line = stream.readline()
            if not line:
                break
            processed_run += 1
            total_records += 1
            record = json.loads(line)
            target = record.get("datasetId")
            metadata = record.get("readme_metadata")
            if isinstance(target, str) and target.strip() and isinstance(metadata, dict):
                target = target.strip()
                for raw_field, value in metadata.items():
                    field = normalize_field_name(raw_field)
                    specification = FIELD_RELATION.get(field)
                    if not specification:
                        continue
                    relation, confidence = specification
                    for raw in set(reference_strings(value)):
                        source, status = resolve_reference(
                            raw, exact, lowercase, unique_basenames
                        )
                        counters[f"candidate_{status}"] += 1
                        if not source or source.lower() == target.lower():
                            continue
                        pending.append(evidence_row(
                            source, target, relation, "card_metadata", field, raw,
                            "", status, confidence, record.get("retrieved_at_utc"),
                        ))
            if processed_run % batch_size == 0:
                with db:
                    db.executemany(UPSERT, pending)
                    state_set(db, "metadata_offset", stream.tell())
                    state_set(db, "metadata_records", total_records)
                pending.clear()
                print(
                    f"metadata records={total_records:,} "
                    f"evidence={db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]:,}",
                    flush=True,
                )
        with db:
            db.executemany(UPSERT, pending)
            state_set(db, "metadata_offset", stream.tell())
            state_set(db, "metadata_records", total_records)
            if not line:
                state_set(db, "metadata_complete", 1)
    print(f"Metadata pass stopped at records={total_records:,}.", flush=True)


def context_window(text: str, start: int, end: int, radius: int = 280) -> str:
    return text[max(0, start - radius):min(len(text), end + radius)]


def classify_reference(text: str, start: int, end: int, evidence_kind: str):
    """Classify a reference only from language directly attached to it."""
    before = text[max(0, start - 220):start]
    after = text[end:min(len(text), end + 100)]

    # A loader call demonstrates use, but surrounding prose is not sufficient
    # to infer that the README's dataset was derived from the loaded dataset.
    if evidence_kind == "load_dataset":
        return "uses_source_data", "medium"

    # Do not borrow a relationship phrase from a completed previous sentence
    # or table cell. Markdown lists without sentence punctuation remain intact,
    # allowing "combined from:\n- dataset" constructions.
    boundaries = list(re.finditer(r"(?:[.!?](?=\s|[|]))|(?:\n\s*\n)", before))
    if boundaries:
        before = before[boundaries[-1].end():]
    for relation, confidence, pattern in RELATION_PATTERNS:
        matches = list(pattern.finditer(before))
        if matches and len(before) - matches[-1].end() <= 120:
            return relation, confidence

    # Limited post-reference constructions such as "X is the source dataset"
    # are allowed, but general keywords elsewhere in the paragraph are not.
    post = after[:80]
    if re.match(r"^\s*(?:\)|\]|[,:;-])*\s*(?:is|was)\s+(?:the\s+|a\s+)?source\b", post, re.I):
        return "uses_source_data", "medium"
    if re.match(r"^\s*(?:\)|\]|[,:;-])*\s*(?:is|was)\s+(?:the\s+|a\s+)?parent\b", post, re.I):
        return "derived_from", "high"
    return "references_dataset", "low"


def readme_references(text: str, exact, lowercase, unique_basenames):
    seen = set()
    occupied = []

    for kind, pattern in (("hf_dataset_url", HF_URL_RE), ("load_dataset", LOAD_DATASET_RE)):
        for match in pattern.finditer(text):
            raw = match.group(1)
            reference_start, reference_end = match.span(1)
            key = (kind, raw, reference_start)
            if key in seen:
                continue
            seen.add(key)
            occupied.append((match.start(), match.end()))
            context = context_window(text, match.start(), match.end())
            yield (
                kind, raw, context,
                classify_reference(text, match.start(), match.end(), kind), True,
            )

    # Bare owner/repository references are accepted only when they exist in the
    # saved universe and directly follow explicit lineage language. IDs already
    # captured inside URLs or load_dataset calls are suppressed.
    for match in BARE_ID_RE.finditer(text):
        if any(match.start() < end and match.end() > start for start, end in occupied):
            continue
        raw = match.group(1)
        key = ("lineage_context_id", raw, match.start())
        if key in seen:
            continue
        source, status = resolve_reference(raw, exact, lowercase, unique_basenames)
        if not source or status != "validated":
            continue
        classified = classify_reference(
            text, match.start(), match.end(), "lineage_context_id"
        )
        if classified[0] not in LINEAGE_RELATIONS:
            continue
        seen.add(key)
        context = context_window(text, match.start(), match.end())
        yield "lineage_context_id", raw, context, classified, False


def scan_readmes(db, path, exact, lowercase, unique_basenames, batch_size, limit):
    if state_get(db, "readme_complete") == "1":
        print("README scan already complete.", flush=True)
        return
    offset = int(state_get(db, "readme_offset"))
    total_records = int(state_get(db, "readme_records"))
    readme_ok = int(state_get(db, "readme_ok"))
    processed_run = 0
    pending = []
    with path.open("rb") as stream:
        stream.seek(offset)
        while not limit or processed_run < limit:
            line = stream.readline()
            if not line:
                break
            processed_run += 1
            total_records += 1
            record = json.loads(line)
            target = record.get("datasetId")
            text = record.get("readme")
            if (
                record.get("status") == "ok" and isinstance(target, str)
                and target.strip() and isinstance(text, str) and text
            ):
                readme_ok += 1
                target = target.strip()
                for kind, raw, context, classified, _ in readme_references(
                    text, exact, lowercase, unique_basenames
                ):
                    relation, confidence = classified
                    source, status = resolve_reference(
                        raw, exact, lowercase, unique_basenames
                    )
                    if not source or source.lower() == target.lower():
                        continue
                    pending.append(evidence_row(
                        source, target, relation, "readme", kind, raw, context,
                        status, confidence, record.get("retrieved_at_utc"),
                    ))
            if processed_run % batch_size == 0:
                with db:
                    db.executemany(UPSERT, pending)
                    state_set(db, "readme_offset", stream.tell())
                    state_set(db, "readme_records", total_records)
                    state_set(db, "readme_ok", readme_ok)
                pending.clear()
                print(
                    f"readmes records={total_records:,} ok={readme_ok:,} "
                    f"evidence={db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]:,}",
                    flush=True,
                )
        with db:
            db.executemany(UPSERT, pending)
            state_set(db, "readme_offset", stream.tell())
            state_set(db, "readme_records", total_records)
            state_set(db, "readme_ok", readme_ok)
            if not line:
                state_set(db, "readme_complete", 1)
    print(f"README pass stopped at records={total_records:,}, ok={readme_ok:,}.", flush=True)


OUTPUT_FIELDS = [
    "source_dataset", "target_dataset", "relationship_type", "evidence_source",
    "evidence_field", "raw_reference", "context", "source_status", "confidence",
    "retrieved_at_utc",
]


def atomic_csv(path: Path, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(OUTPUT_FIELDS)
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def graph_stats(rows):
    edge_keys = {(row[0], row[1], row[2]) for row in rows}
    nodes = {value for source, target, _ in edge_keys for value in (source, target)}
    return {"edges": len(edge_keys), "nodes": len(nodes)}


EDGE_FIELDS = [
    "source", "edge_type", "target", "evidence_count", "evidence_sources",
    "evidence_fields", "max_confidence", "source_status",
]


def aggregate_graph_edges(rows):
    grouped = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        item = grouped.setdefault(key, {
            "count": 0, "sources": set(), "fields": set(),
            "confidence": "low", "statuses": set(),
        })
        item["count"] += 1
        item["sources"].add(row[3])
        item["fields"].add(row[4])
        item["statuses"].add(row[7])
        if CONFIDENCE_RANK[row[8]] > CONFIDENCE_RANK[item["confidence"]]:
            item["confidence"] = row[8]
    output = []
    for (source, target, relation), item in sorted(grouped.items()):
        output.append((
            source, relation, target, item["count"],
            ";".join(sorted(item["sources"])),
            ";".join(sorted(item["fields"])), item["confidence"],
            "validated" if "validated" in item["statuses"] else "unresolved",
        ))
    return output


def atomic_edge_csv(path: Path, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(EDGE_FIELDS)
        writer.writerows(aggregate_graph_edges(rows))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_lineage_validation_sample(path: Path, rows):
    representatives = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        current = representatives.get(key)
        if current is None or (row[3] == "readme" and len(row[6]) > len(current[6])):
            representatives[key] = row
    groups = defaultdict(list)
    for row in representatives.values():
        groups[row[2]].append(row)
    rng = random.Random(20261002)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(OUTPUT_FIELDS + ["sample_group", "manual_label", "review_notes"])
        for relation in sorted(groups):
            candidates = groups[relation]
            selected = candidates if len(candidates) <= 100 else rng.sample(candidates, 100)
            for row in sorted(selected):
                writer.writerow(list(row) + [f"lineage_{relation}", "", ""])
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def export_outputs(
    db: sqlite3.Connection,
    output_dir: Path,
    universe_counts,
    readme_status_counts,
    readme_nonempty,
):
    all_rows = db.execute(
        "SELECT source_dataset,target_dataset,relationship_type,evidence_source,"
        "evidence_field,raw_reference,context,source_status,confidence,retrieved_at_utc "
        "FROM evidence ORDER BY source_dataset,target_dataset,relationship_type,"
        "evidence_source,evidence_field,raw_reference"
    ).fetchall()
    high = [
        row for row in all_rows if row[7] == "validated" and row[8] == "high"
        and row[2] in LINEAGE_RELATIONS
    ]
    probable = [
        row for row in all_rows if row[7] == "validated"
        and row[8] in {"high", "medium"} and row[2] in LINEAGE_RELATIONS
    ]
    unresolved = [row for row in all_rows if row[7] == "unresolved"]

    atomic_csv(output_dir / "dataset_lineage_high_confidence.csv", high)
    atomic_csv(output_dir / "dataset_lineage_probable.csv", probable)
    atomic_csv(output_dir / "dataset_relationships_extended.csv", all_rows)
    atomic_csv(output_dir / "unresolved_dataset_references.csv", unresolved)
    atomic_edge_csv(output_dir / "dataset_lineage_high_confidence_edges.csv", high)
    atomic_edge_csv(output_dir / "dataset_lineage_probable_edges.csv", probable)
    atomic_edge_csv(output_dir / "dataset_relationships_extended_edges.csv", all_rows)
    atomic_edge_csv(output_dir / "unresolved_dataset_reference_edges.csv", unresolved)
    atomic_lineage_validation_sample(
        output_dir / "validation_sample_lineage.csv", high
    )

    groups = defaultdict(list)
    for row in all_rows:
        if row[7] == "unresolved":
            group = "unresolved"
        elif row[3] == "readme":
            group = "readme"
        elif row[4] == "datasets":
            group = "metadata_generic_datasets"
        elif row[8] == "high":
            group = "metadata_explicit_high"
        else:
            group = "metadata_source_medium"
        groups[group].append(row)
    rng = random.Random(20261002)
    sample_path = output_dir / "validation_sample.csv"
    temporary = sample_path.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(OUTPUT_FIELDS + ["sample_group", "manual_label", "review_notes"])
        for group in sorted(groups):
            candidates = groups[group]
            selected = candidates if len(candidates) <= 100 else rng.sample(candidates, 100)
            for row in sorted(selected):
                writer.writerow(list(row) + [group, "", ""])
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, sample_path)

    by_relation = Counter(row[2] for row in all_rows)
    by_evidence = Counter(row[3] for row in all_rows)
    by_confidence = Counter(row[8] for row in all_rows)
    by_status = Counter(row[7] for row in all_rows)
    summary = {
        "change_id": CHANGE_ID,
        "inputs": json.loads(state_get(db, "configuration")),
        "scan": {
            "metadata_records": int(state_get(db, "metadata_records")),
            "metadata_complete": state_get(db, "metadata_complete") == "1",
            "readme_records": int(state_get(db, "readme_records")),
            "readme_status_counts": dict(readme_status_counts),
            "readme_nonempty_bodies_analyzed": readme_nonempty,
            "readme_complete": state_get(db, "readme_complete") == "1",
            "dataset_population_status": dict(universe_counts),
        },
        "evidence_rows": len(all_rows),
        "high_confidence_lineage": graph_stats(high),
        "probable_lineage": graph_stats(probable),
        "extended_relationships": graph_stats(all_rows),
        "unresolved_relationships": graph_stats(unresolved),
        "by_relationship_type": dict(sorted(by_relation.items())),
        "by_evidence_source": dict(sorted(by_evidence.items())),
        "by_confidence": dict(sorted(by_confidence.items())),
        "by_source_status": dict(sorted(by_status.items())),
        "validation_sample_rows": sum(min(100, len(rows)) for rows in groups.values()),
        "validation_sample_groups": {key: min(100, len(value)) for key, value in sorted(groups.items())},
    }
    summary_path = output_dir / "summary.json"
    temporary = summary_path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, summary_path)
    return summary


def main() -> int:
    args = parse_args()
    metadata_path = args.metadata.expanduser().resolve()
    readme_path = args.readmes.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not metadata_path.is_file() or not readme_path.is_file():
        raise FileNotFoundError("Both saved metadata and README snapshots are required")
    if args.batch_size < 1 or args.max_metadata_records < 0 or args.max_readme_records < 0:
        raise ValueError("Invalid batch or record limit")
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "dataset_dataset_extended.state.sqlite3"
    if args.rebuild and state_path.exists():
        raise RuntimeError(
            "Refusing to delete state automatically; move it aside before rebuilding"
        )

    print("Loading saved dataset universe...", flush=True)
    exact, lowercase, unique_basenames, universe_counts = load_universe(metadata_path)
    print(f"Dataset IDs: {len(exact):,}", flush=True)
    print("Verifying saved README status counts...", flush=True)
    readme_status_counts, readme_nonempty = readme_snapshot_counts(readme_path)
    db = connect(state_path)
    try:
        initialize_state(db, metadata_path, readme_path)
        scan_metadata(
            db, metadata_path, exact, lowercase, unique_basenames,
            args.batch_size, args.max_metadata_records,
        )
        scan_readmes(
            db, readme_path, exact, lowercase, unique_basenames,
            args.batch_size, args.max_readme_records,
        )
        summary = export_outputs(
            db, output_dir, universe_counts, readme_status_counts, readme_nonempty
        )
    finally:
        db.close()
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- model_library_edges.py ------------------------------------------------
SOURCES['model_library_edges'] = r'''#!/usr/bin/env python3
"""Create and query model-to-library edges from saved model-card metadata.

Created: 2026-09-14
Version: v2026.09.14-07
Purpose: Represent model library declarations and recognized library tags as
         ``model -> uses_library -> library`` relationships.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_model_readme_metadata_2026Aug28.jsonl"
DEFAULT_CSV = SCRIPT_DIR / "model_library_edges.csv"
DEFAULT_JSONL = SCRIPT_DIR / "model_library_edges.jsonl"
DEFAULT_DETAILED_CSV = SCRIPT_DIR / "model_library_edges_detailed.csv"
DEFAULT_DETAILED_JSONL = SCRIPT_DIR / "model_library_edges_detailed.jsonl"

EDGE_TYPE = "uses_library"
FIELD_PRIORITY = {
    "library_name": 0,
    "alternative_field": 1,
    "library_tag": 2,
}

# These alternatives were observed in the downloaded card metadata. Generic
# fields such as developmentLibrary are excluded because their values are often
# descriptions rather than one library identifier.
ALTERNATIVE_LIBRARY_FIELDS = {
    "library",
    "libraries",
    "library_tag",
    "library_tags",
    "model_hub_library",
    "libray_name",
    "librairy_name",
    "librar_yname",
    "libraryname",
    "library_name2",
}

# Tags are weaker than library_name. Only recognized library/technology tags
# are accepted, rather than treating every arbitrary card tag as a library.
KNOWN_LIBRARY_TAGS = {
    "adapters", "allennlp", "asteroid", "bertopic", "coreml", "dduf",
    "diffusers", "espnet", "executorch", "fairseq", "fastai", "fasttext",
    "flair", "gguf", "graphcore", "habana", "jax", "joblib", "keras",
    "keras-hub", "litert", "llamafile", "ml-agents", "mlx", "nemo",
    "onnx", "openclip", "openvino", "paddleocr", "paddlenlp",
    "paddlepaddle", "peft", "pyannote.audio", "pytorch", "rust",
    "safetensors", "sample-factory", "scikit-learn", "sentence-transformers",
    "setfit", "spacy", "speechbrain", "stable-baselines3", "stanza",
    "tensorflow", "tf-keras", "timm", "transformers", "transformers.js",
    "tensorboard", "unity-sentis", "univa",
}

LIBRARY_ALIASES = {
    "torch": "pytorch",
    "sentence transformers": "sentence-transformers",
    "sentence_transformers": "sentence-transformers",
    "core ml": "coreml",
    "core-ml": "coreml",
    "scikit_learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "keras_hub": "keras-hub",
    "kerashub": "keras-hub",
    "open_clip": "openclip",
    "tf_keras": "tf-keras",
    "stable_baselines3": "stable-baselines3",
    "pyannote_audio": "pyannote.audio",
    "transformers_js": "transformers.js",
    "llama_cpp": "llama.cpp",
}

LIBRARY_ID = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,79}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or query model -> uses_library -> library edges."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--detailed-csv", type=Path, default=DEFAULT_DETAILED_CSV)
    parser.add_argument(
        "--detailed-jsonl", type=Path, default=DEFAULT_DETAILED_JSONL
    )
    query = parser.add_mutually_exclusive_group()
    query.add_argument(
        "--query-library",
        metavar="LIBRARY",
        help="Count and list models associated with a library.",
    )
    query.add_argument(
        "--query-model",
        metavar="MODEL_ID",
        help="List libraries associated with one model.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum query results to print; 0 prints all (default: 20).",
    )
    return parser.parse_args()


def normalize_field_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def string_values(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
    return []


def normalize_library(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower().strip("'\"`")
    if not candidate or "://" in candidate or "\n" in candidate:
        return None
    candidate = LIBRARY_ALIASES.get(candidate, candidate)
    candidate = re.sub(r"[ _]+", "-", candidate)
    candidate = LIBRARY_ALIASES.get(candidate, candidate)
    return candidate if LIBRARY_ID.fullmatch(candidate) else None


def candidate_libraries(metadata: dict) -> dict[str, tuple[str, str]]:
    """Return library -> (evidence, confidence), preferring strong evidence."""
    candidates: dict[str, tuple[str, str]] = {}

    def register(library: str, evidence: str, confidence: str, group: str) -> None:
        current = candidates.get(library)
        if current is None:
            candidates[library] = (evidence, confidence)
            return
        current_group = (
            "library_name"
            if current[0] == "library_name"
            else "library_tag"
            if current[0] == "tags"
            else "alternative_field"
        )
        if FIELD_PRIORITY[group] < FIELD_PRIORITY[current_group]:
            candidates[library] = (evidence, confidence)

    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field == "library_name":
            group = "library_name"
            confidence = "declared"
        elif field in ALTERNATIVE_LIBRARY_FIELDS:
            group = "alternative_field"
            confidence = "declared_nonstandard"
        else:
            continue

        for raw_library in string_values(raw_value):
            library = normalize_library(raw_library)
            if library is None:
                continue
            # library_tag fields are custom and receive the same allowlist rule
            # as ordinary tags. Other explicit fields may declare custom tools.
            if field in {"library_tag", "library_tags"} and library not in KNOWN_LIBRARY_TAGS:
                continue
            evidence = "library_name" if group == "library_name" else field
            register(library, evidence, confidence, group)

    for raw_tag in string_values(metadata.get("tags")):
        library = normalize_library(raw_tag)
        if library in KNOWN_LIBRARY_TAGS:
            register(library, "tags", "tag_association", "library_tag")

    return candidates


def output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    input_path = args.input.expanduser().resolve()
    outputs = tuple(
        path.expanduser().resolve()
        for path in (
            args.csv,
            args.jsonl,
            args.detailed_csv,
            args.detailed_jsonl,
        )
    )
    if not input_path.is_file():
        raise FileNotFoundError(f"Input metadata not found: {input_path}")
    if len({input_path, *outputs}) != 5:
        raise ValueError("Input and output paths must all be different")
    return (input_path, *outputs)


def generate(args: argparse.Namespace) -> None:
    input_path, csv_path, jsonl_path, detailed_csv_path, detailed_jsonl_path = (
        output_paths(args)
    )
    outputs = (csv_path, jsonl_path, detailed_csv_path, detailed_jsonl_path)
    for path in outputs:
        if path.exists():
            raise FileExistsError(
                f"Output already exists: {path}\n"
                "Move it or choose another output path before rerunning."
            )
        path.parent.mkdir(parents=True, exist_ok=True)

    counters: Counter[str] = Counter()
    library_counts: Counter[str] = Counter()
    simple_fields = ["source", "edge_type", "target"]
    detailed_fields = simple_fields + ["evidence", "confidence"]

    with (
        input_path.open(encoding="utf-8") as input_file,
        csv_path.open("x", newline="", encoding="utf-8") as csv_file,
        jsonl_path.open("x", encoding="utf-8") as jsonl_file,
        detailed_csv_path.open("x", newline="", encoding="utf-8") as detailed_csv,
        detailed_jsonl_path.open("x", encoding="utf-8") as detailed_jsonl,
    ):
        csv_writer = csv.DictWriter(csv_file, fieldnames=simple_fields)
        detailed_writer = csv.DictWriter(detailed_csv, fieldnames=detailed_fields)
        csv_writer.writeheader()
        detailed_writer.writeheader()

        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            counters["records"] += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                counters["invalid_json"] += 1
                print(f"Skipping invalid JSON at line {line_number}: {exc}")
                continue

            model_id = record.get("modelId")
            metadata = record.get("readme_metadata")
            if not isinstance(model_id, str) or not model_id.strip():
                counters["invalid_model_id"] += 1
                continue
            if not isinstance(metadata, dict) or not metadata:
                continue

            counters["metadata_records"] += 1
            model_id = model_id.strip()
            libraries = candidate_libraries(metadata)
            if not libraries:
                continue

            counters["models_with_library"] += 1
            if len(libraries) > 1:
                counters["models_with_multiple_libraries"] += 1

            for library, (evidence, confidence) in sorted(libraries.items()):
                simple_row = {
                    "source": f"model::{model_id}",
                    "edge_type": EDGE_TYPE,
                    "target": f"library::{library}",
                }
                detailed_row = {
                    **simple_row,
                    "evidence": evidence,
                    "confidence": confidence,
                }
                csv_writer.writerow(simple_row)
                jsonl_file.write(
                    json.dumps(simple_row, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
                detailed_writer.writerow(detailed_row)
                detailed_jsonl.write(
                    json.dumps(
                        detailed_row, ensure_ascii=False, separators=(",", ":")
                    )
                    + "\n"
                )
                counters["edges"] += 1
                counters[f"confidence_{confidence}"] += 1
                library_counts[library] += 1

    print("\nModel-library graph")
    print("-------------------")
    print(f"Model records scanned:          {counters['records']:12,}")
    print(f"Records with metadata:          {counters['metadata_records']:12,}")
    print(f"Models with library edges:      {counters['models_with_library']:12,}")
    print(f"Models with multiple libraries: {counters['models_with_multiple_libraries']:12,}")
    print(f"Unique library nodes:           {len(library_counts):12,}")
    print(f"Total unique edges:             {counters['edges']:12,}")
    print(f"Declared-field edges:           {counters['confidence_declared']:12,}")
    print(f"Nonstandard-field edges:        {counters['confidence_declared_nonstandard']:12,}")
    print(f"Tag-association edges:          {counters['confidence_tag_association']:12,}")
    print(f"Invalid model IDs:              {counters['invalid_model_id']:12,}")
    print(f"Invalid JSON lines:             {counters['invalid_json']:12,}")
    print("\nMost common libraries")
    for library, count in library_counts.most_common(20):
        print(f"  {library:28} {count:12,}")
    print(f"\nCSV:            {csv_path}")
    print(f"JSONL:          {jsonl_path}")
    print(f"Detailed CSV:   {detailed_csv_path}")
    print(f"Detailed JSONL: {detailed_jsonl_path}")


def query(args: argparse.Namespace) -> None:
    csv_path = args.csv.expanduser().resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Edge CSV not found: {csv_path}\nRun the script without a query first."
        )
    if args.limit < 0:
        raise ValueError("--limit cannot be negative")

    results = []
    if args.query_library is not None:
        library = normalize_library(args.query_library)
        if library is None:
            raise ValueError(f"Invalid library query: {args.query_library!r}")
        wanted = f"library::{library}"
        with csv_path.open(newline="", encoding="utf-8") as input_file:
            for row in csv.DictReader(input_file):
                if row.get("target") == wanted:
                    results.append(row["source"].removeprefix("model::"))
        print(f"Library: {library}")
        print(f"Distinct models: {len(set(results)):,}")
        heading = "Models"
    else:
        model_id = args.query_model.removeprefix("model::").strip()
        wanted = f"model::{model_id}"
        with csv_path.open(newline="", encoding="utf-8") as input_file:
            for row in csv.DictReader(input_file):
                if row.get("source") == wanted:
                    results.append(row["target"].removeprefix("library::"))
        print(f"Model: {model_id}")
        print(f"Distinct libraries: {len(set(results)):,}")
        heading = "Libraries"

    ordered = sorted(set(results), key=str.lower)
    displayed = ordered if args.limit == 0 else ordered[: args.limit]
    print(f"{heading} shown: {len(displayed):,}/{len(ordered):,}")
    for value in displayed:
        print(value)


def main() -> int:
    args = parse_args()
    try:
        if args.query_library is not None or args.query_model is not None:
            query(args)
        else:
            generate(args)
    except KeyboardInterrupt:
        print("Interrupted; move incomplete output files before rerunning.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- model_license_task_github_edges.py ------------------------------------
SOURCES['model_license_task_github_edges'] = r'''#!/usr/bin/env python3
"""Create and query model-license, model-task, and model-GitHub edges.

Created: 2026-09-14
Version: v2026.09.14-08
Purpose: Extract three typed relationship sets from saved Hugging Face
         model-card metadata while preserving evidence strength.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_model_readme_metadata_2026Aug28.jsonl"
SIMPLE_FIELDS = ["source", "edge_type", "target"]
DETAILED_FIELDS = SIMPLE_FIELDS + ["evidence", "confidence"]

RELATIONS = {
    "license": {
        "edge_type": "has_license",
        "target_prefix": "license::",
        "stem": "model_license_edges",
    },
    "task": {
        "edge_type": "performs_task",
        "target_prefix": "task::",
        "stem": "model_task_edges",
    },
    "github": {
        "edge_type": "links_to_github",
        "target_prefix": "github::",
        "stem": "model_github_edges",
    },
}

PRIORITY = {
    "standard": 0,
    "alternative": 1,
    "tag": 2,
    "embedded": 2,
}

ALTERNATIVE_LICENSE_FIELDS = {
    "licenses",
    "additional_licenses",
    "adapter_license",
    "repo_license",
    "anemll_license",
    "sdlicense",
    "name_license",
}

KNOWN_LICENSE_TAGS = {
    "afl-3.0", "apache-2.0", "artistic-2.0", "bsl-1.0", "bsd",
    "bsd-2-clause", "bsd-3-clause", "bsd-3-clause-clear", "c-uda",
    "cc", "cc-by-2.0", "cc-by-2.5", "cc-by-3.0", "cc-by-4.0",
    "cc-by-nc-2.0", "cc-by-nc-3.0", "cc-by-nc-4.0",
    "cc-by-nc-nd-3.0", "cc-by-nc-nd-4.0", "cc-by-nc-sa-2.0",
    "cc-by-nc-sa-3.0", "cc-by-nc-sa-4.0", "cc-by-nd-3.0",
    "cc-by-nd-4.0", "cc-by-sa-3.0", "cc-by-sa-4.0", "cc0-1.0",
    "ecl-2.0", "gpl", "gpl-2.0", "gpl-3.0", "isc", "lgpl",
    "lgpl-2.1", "lgpl-3.0", "mit", "mpl-2.0", "ms-pl", "ncsa",
    "odc-by", "odbl", "openrail", "openrail++", "openrail++-m",
    "other", "pddl", "postgresql", "unlicense", "wtfpl", "zlib",
}

LICENSE_ALIASES = {
    "apache 2": "apache-2.0",
    "apache 2.0": "apache-2.0",
    "apache license 2.0": "apache-2.0",
    "apache-2": "apache-2.0",
    "apache2": "apache-2.0",
    "bsd 2 clause": "bsd-2-clause",
    "bsd 3 clause": "bsd-3-clause",
    "cc by 4.0": "cc-by-4.0",
    "cc-by": "cc-by-4.0",
    "creative commons attribution 4.0": "cc-by-4.0",
    "mit license": "mit",
}

ALTERNATIVE_TASK_FIELDS = {
    "task_categories",
    "tasks",
    "task",
    "task_ids",
    "pipeline_tags",
    "validated_tasks",
    "finetuning_task",
    "training_task",
    "task_type",
    "pipeline",
    "finetuned_task",
}

# Only these tags are interpreted as task evidence. Explicit task fields may
# still contain custom task identifiers not present in this list.
KNOWN_TASK_TAGS = {
    "audio-classification", "audio-to-audio", "automatic-speech-recognition",
    "conversational", "depth-estimation", "document-question-answering",
    "feature-extraction", "fill-mask", "image-classification",
    "image-feature-extraction", "image-segmentation", "image-text-to-text",
    "image-to-3d", "image-to-image", "image-to-text", "image-to-video",
    "keypoint-detection", "mask-generation", "object-detection",
    "question-answering", "reinforcement-learning", "robotics",
    "sentence-similarity", "summarization", "table-question-answering",
    "tabular-classification", "tabular-regression", "text-classification",
    "text-generation", "text-ranking", "text-to-3d", "text-to-audio",
    "text-to-image", "text-to-speech", "text-to-video",
    "text2text-generation", "time-series-forecasting", "token-classification",
    "translation", "unconditional-image-generation", "video-classification",
    "video-to-video", "visual-question-answering",
    "zero-shot-classification", "zero-shot-image-classification",
    "zero-shot-object-detection",
}

TASK_ALIASES = {
    "asr": "automatic-speech-recognition",
    "image generation": "text-to-image",
    "named entity recognition": "token-classification",
    "ner": "token-classification",
    "sentiment analysis": "text-classification",
    "summarisation": "summarization",
    "text to text": "text2text-generation",
    "text-to-text": "text2text-generation",
    "text-to-video-synthesis": "text-to-video",
}

DIRECT_GITHUB_FIELDS = {
    "github", "github_url", "github_repo", "repo_url", "repository",
    "repo_link", "source_repo", "source_repos", "source_code", "code",
    "code_url", "finetune_code", "code_base", "newest_code",
    "original_code",
}

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,159}$")
GITHUB_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
GITHUB_RAW_URL = re.compile(
    r"https?://raw\.githubusercontent\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
GITHUB_SSH = re.compile(
    r"git@github\.com:(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or query model-license, model-task, and GitHub edges."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    query = parser.add_mutually_exclusive_group()
    query.add_argument("--query-license", metavar="LICENSE")
    query.add_argument("--query-task", metavar="TASK")
    query.add_argument(
        "--query-github",
        metavar="OWNER/REPOSITORY",
        help="Accepts owner/repository or a GitHub URL.",
    )
    query.add_argument(
        "--query-model",
        metavar="MODEL_ID",
        help="List this model's licenses, tasks, and GitHub repositories.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum query results to print; 0 prints all (default: 20).",
    )
    return parser.parse_args()


def normalize_field_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def string_values(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
    return []


def task_values(value: object) -> list[str]:
    values = string_values(value)
    if isinstance(value, dict):
        # Standard task dictionaries commonly contain {name, type}. Prefer the
        # machine-readable type and use name only when no type is available.
        raw = value.get("type") or value.get("id") or value.get("name")
        values.extend(string_values(raw))
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, dict):
                raw = item.get("type") or item.get("id") or item.get("name")
                values.extend(string_values(raw))
    return values


def normalize_identifier(value: object, aliases: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower().strip("'\"`")
    if not candidate or "://" in candidate or "\n" in candidate:
        return None
    candidate = aliases.get(candidate, candidate)
    candidate = re.sub(r"[ _]+", "-", candidate)
    candidate = aliases.get(candidate, candidate)
    candidate = re.sub(r"-+", "-", candidate).strip("-")
    return candidate if IDENTIFIER.fullmatch(candidate) else None


def register(
    candidates: dict[str, tuple[str, str, str]],
    value: str,
    evidence: str,
    confidence: str,
    group: str,
) -> None:
    current = candidates.get(value)
    if current is None or PRIORITY[group] < PRIORITY[current[2]]:
        candidates[value] = (evidence, confidence, group)


def candidate_licenses(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates: dict[str, tuple[str, str, str]] = {}
    specific_names = {
        value
        for raw in string_values(metadata.get("license_name"))
        if (value := normalize_identifier(raw, LICENSE_ALIASES)) is not None
    }

    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field == "license":
            group, confidence = "standard", "declared"
        elif field == "license_name":
            group, confidence = "standard", "declared"
        elif field in ALTERNATIVE_LICENSE_FIELDS:
            group, confidence = "alternative", "declared_nonstandard"
        else:
            continue
        for raw in string_values(raw_value):
            license_id = normalize_identifier(raw, LICENSE_ALIASES)
            if license_id is None:
                continue
            # license_name is the specific identity when the standard field is
            # the generic value "other".
            if field == "license" and license_id == "other" and specific_names:
                continue
            register(candidates, license_id, field, confidence, group)

    for raw_tag in string_values(metadata.get("tags")):
        license_id = normalize_identifier(raw_tag, LICENSE_ALIASES)
        if license_id in KNOWN_LICENSE_TAGS:
            register(
                candidates,
                license_id,
                "tags",
                "tag_association",
                "tag",
            )
    return {key: (value[0], value[1]) for key, value in candidates.items()}


def candidate_tasks(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates: dict[str, tuple[str, str, str]] = {}
    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field == "pipeline_tag":
            group, confidence = "standard", "declared"
        elif field in ALTERNATIVE_TASK_FIELDS:
            group, confidence = "alternative", "declared_nonstandard"
        else:
            continue
        for raw in task_values(raw_value):
            task = normalize_identifier(raw, TASK_ALIASES)
            if task is not None:
                register(candidates, task, field, confidence, group)

    for raw_tag in string_values(metadata.get("tags")):
        task = normalize_identifier(raw_tag, TASK_ALIASES)
        if task in KNOWN_TASK_TAGS:
            register(candidates, task, "tags", "tag_association", "tag")
    return {key: (value[0], value[1]) for key, value in candidates.items()}


def nested_strings(value: object, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{normalize_field_name(key)}" if path else normalize_field_name(key)
            yield from nested_strings(item, child)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from nested_strings(item, path)


def github_repositories(value: str) -> set[str]:
    repositories = set()
    for pattern in (GITHUB_URL, GITHUB_RAW_URL, GITHUB_SSH):
        for match in pattern.finditer(value):
            owner = match.group("owner").lower()
            repo = match.group("repo").rstrip(".,;:)]}").removesuffix(".git").lower()
            if repo:
                repositories.add(f"{owner}/{repo}")
    return repositories


def normalize_github_query(value: str) -> str | None:
    matches = github_repositories(value)
    if len(matches) == 1:
        return next(iter(matches))
    candidate = value.strip().lower().removeprefix("github::").strip("/")
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,38}/[a-z0-9._-]+", candidate):
        return candidate.removesuffix(".git")
    return None


def candidate_github(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates: dict[str, tuple[str, str, str]] = {}
    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        for path, text in nested_strings(raw_value, field):
            for repository in github_repositories(text):
                if field in DIRECT_GITHUB_FIELDS:
                    group, confidence = "standard", "declared_link"
                else:
                    group, confidence = "embedded", "embedded_reference"
                register(candidates, repository, path, confidence, group)
    return {key: (value[0], value[1]) for key, value in candidates.items()}


EXTRACTORS: dict[str, Callable[[dict], dict[str, tuple[str, str]]]] = {
    "license": candidate_licenses,
    "task": candidate_tasks,
    "github": candidate_github,
}


def relation_paths(output_dir: Path, relation: str) -> dict[str, Path]:
    stem = RELATIONS[relation]["stem"]
    return {
        "csv": output_dir / f"{stem}.csv",
        "jsonl": output_dir / f"{stem}.jsonl",
        "detailed_csv": output_dir / f"{stem}_detailed.csv",
        "detailed_jsonl": output_dir / f"{stem}_detailed.jsonl",
    }


def validate_generation_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    input_path = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input metadata not found: {input_path}")
    outputs = [
        path.resolve()
        for relation in RELATIONS
        for path in relation_paths(output_dir, relation).values()
    ]
    if input_path in outputs or len(set(outputs)) != len(outputs):
        raise ValueError("Input and output paths must all be different")
    existing = [path for path in outputs if path.exists()]
    if existing:
        formatted = "\n".join(str(path) for path in existing)
        raise FileExistsError(
            "Refusing to overwrite existing output files:\n" + formatted
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_path, output_dir


def generate(args: argparse.Namespace) -> None:
    input_path, output_dir = validate_generation_paths(args)
    counters = {relation: Counter() for relation in RELATIONS}
    target_counts = {relation: Counter() for relation in RELATIONS}

    with ExitStack() as stack:
        handles: dict[str, dict[str, object]] = {}
        writers: dict[str, dict[str, csv.DictWriter]] = {}
        for relation in RELATIONS:
            paths = relation_paths(output_dir, relation)
            relation_handles = {
                "csv": stack.enter_context(paths["csv"].open("x", newline="", encoding="utf-8")),
                "jsonl": stack.enter_context(paths["jsonl"].open("x", encoding="utf-8")),
                "detailed_csv": stack.enter_context(
                    paths["detailed_csv"].open("x", newline="", encoding="utf-8")
                ),
                "detailed_jsonl": stack.enter_context(
                    paths["detailed_jsonl"].open("x", encoding="utf-8")
                ),
            }
            handles[relation] = relation_handles
            writers[relation] = {
                "csv": csv.DictWriter(relation_handles["csv"], fieldnames=SIMPLE_FIELDS),
                "detailed_csv": csv.DictWriter(
                    relation_handles["detailed_csv"], fieldnames=DETAILED_FIELDS
                ),
            }
            writers[relation]["csv"].writeheader()
            writers[relation]["detailed_csv"].writeheader()

        with input_path.open(encoding="utf-8") as input_file:
            for line_number, line in enumerate(input_file, start=1):
                if not line.strip():
                    continue
                for relation in RELATIONS:
                    counters[relation]["records"] += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    for relation in RELATIONS:
                        counters[relation]["invalid_json"] += 1
                    print(f"Skipping invalid JSON at line {line_number}: {exc}")
                    continue

                model_id = record.get("modelId")
                metadata = record.get("readme_metadata")
                if not isinstance(model_id, str) or not model_id.strip():
                    for relation in RELATIONS:
                        counters[relation]["invalid_model_id"] += 1
                    continue
                if not isinstance(metadata, dict) or not metadata:
                    continue

                model_id = model_id.strip()
                for relation, extractor in EXTRACTORS.items():
                    counters[relation]["metadata_records"] += 1
                    candidates = extractor(metadata)
                    if not candidates:
                        continue
                    counters[relation]["models_with_edges"] += 1
                    if len(candidates) > 1:
                        counters[relation]["models_with_multiple"] += 1

                    config = RELATIONS[relation]
                    for target, (evidence, confidence) in sorted(candidates.items()):
                        simple_row = {
                            "source": f"model::{model_id}",
                            "edge_type": config["edge_type"],
                            "target": f"{config['target_prefix']}{target}",
                        }
                        detailed_row = {
                            **simple_row,
                            "evidence": evidence,
                            "confidence": confidence,
                        }
                        writers[relation]["csv"].writerow(simple_row)
                        handles[relation]["jsonl"].write(
                            json.dumps(simple_row, ensure_ascii=False, separators=(",", ":"))
                            + "\n"
                        )
                        writers[relation]["detailed_csv"].writerow(detailed_row)
                        handles[relation]["detailed_jsonl"].write(
                            json.dumps(detailed_row, ensure_ascii=False, separators=(",", ":"))
                            + "\n"
                        )
                        counters[relation]["edges"] += 1
                        counters[relation][f"confidence:{confidence}"] += 1
                        target_counts[relation][target] += 1

    for relation in RELATIONS:
        title = relation.capitalize()
        stats = counters[relation]
        print(f"\n## Model-{title} subgraph")
        print(f"Records scanned:             {stats['records']:12,}")
        print(f"Records with metadata:       {stats['metadata_records']:12,}")
        print(f"Models with edges:           {stats['models_with_edges']:12,}")
        print(f"Models with multiple values: {stats['models_with_multiple']:12,}")
        print(f"Unique {relation} nodes:      {len(target_counts[relation]):12,}")
        print(f"Total unique edges:          {stats['edges']:12,}")
        for key in sorted(stats):
            if key.startswith("confidence:"):
                print(f"  {key.removeprefix('confidence:'):25} {stats[key]:12,}")
        print(f"Invalid model IDs:           {stats['invalid_model_id']:12,}")
        print(f"Invalid JSON lines:          {stats['invalid_json']:12,}")
        print(f"Most common {relation} values:")
        for value, count in target_counts[relation].most_common(15):
            print(f"  {value:35} {count:12,}")
        paths = relation_paths(output_dir, relation)
        print(f"CSV:            {paths['csv']}")
        print(f"JSONL:          {paths['jsonl']}")
        print(f"Detailed CSV:   {paths['detailed_csv']}")
        print(f"Detailed JSONL: {paths['detailed_jsonl']}")


def read_query_results(
    csv_path: Path,
    source: str | None = None,
    target: str | None = None,
) -> list[str]:
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Edge CSV not found: {csv_path}\nRun the script without a query first."
        )
    results = []
    with csv_path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            if source is not None and row.get("source") == source:
                results.append(row["target"].split("::", 1)[-1])
            elif target is not None and row.get("target") == target:
                results.append(row["source"].removeprefix("model::"))
    return sorted(set(results), key=str.lower)


def print_results(heading: str, results: list[str], limit: int) -> None:
    shown = results if limit == 0 else results[:limit]
    print(f"Distinct results: {len(results):,}")
    print(f"{heading} shown: {len(shown):,}/{len(results):,}")
    for result in shown:
        print(result)


def query(args: argparse.Namespace) -> None:
    if args.limit < 0:
        raise ValueError("--limit cannot be negative")
    output_dir = args.output_dir.expanduser().resolve()

    if args.query_model is not None:
        model_id = args.query_model.removeprefix("model::").strip()
        if not model_id:
            raise ValueError("Model query cannot be empty")
        print(f"Model: {model_id}")
        for relation in RELATIONS:
            results = read_query_results(
                relation_paths(output_dir, relation)["csv"],
                source=f"model::{model_id}",
            )
            print(f"\n{relation.capitalize()} values")
            print_results(relation.capitalize(), results, args.limit)
        return

    if args.query_license is not None:
        relation, raw = "license", args.query_license
        value = normalize_identifier(raw, LICENSE_ALIASES)
    elif args.query_task is not None:
        relation, raw = "task", args.query_task
        value = normalize_identifier(raw, TASK_ALIASES)
    else:
        relation, raw = "github", args.query_github
        value = normalize_github_query(raw)
    if value is None:
        raise ValueError(f"Invalid {relation} query: {raw!r}")

    config = RELATIONS[relation]
    results = read_query_results(
        relation_paths(output_dir, relation)["csv"],
        target=f"{config['target_prefix']}{value}",
    )
    print(f"{relation.capitalize()}: {value}")
    print_results("Models", results, args.limit)


def main() -> int:
    args = parse_args()
    try:
        if any(
            value is not None
            for value in (
                args.query_license,
                args.query_task,
                args.query_github,
                args.query_model,
            )
        ):
            query(args)
        else:
            generate(args)
    except KeyboardInterrupt:
        print("Interrupted; move incomplete output files before rerunning.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- model_dataset_attribute_edges.py --------------------------------------
SOURCES['model_dataset_attribute_edges'] = r'''#!/usr/bin/env python3
"""Build combined model+dataset library, license, task, and GitHub subgraphs.

Created: 2026-09-14
Version: v2026.09.14-09
Purpose: Preserve validated model attribute edges, add dataset-card evidence,
         and emit four typed subgraphs with graph-ready and detailed outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Iterator

from model_library_edges import (
    KNOWN_LIBRARY_TAGS,
    candidate_libraries,
    normalize_library,
)
from model_license_task_github_edges import (
    LICENSE_ALIASES,
    TASK_ALIASES,
    candidate_github,
    candidate_licenses,
    candidate_tasks,
    normalize_github_query,
    normalize_identifier,
    normalize_field_name,
    string_values,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_INPUT = SCRIPT_DIR / "all_dataset_readme_metadata_2026Aug28.jsonl"
SIMPLE_FIELDS = ["source", "edge_type", "target"]
DETAILED_FIELDS = SIMPLE_FIELDS + ["evidence", "confidence"]

RELATIONS = {
    "library": {
        "model_input": SCRIPT_DIR / "model_library_edges_detailed.csv",
        "stem": "model_dataset_library_edges",
        "target_prefix": "library::",
        "dataset_edge_type": "uses_library",
    },
    "license": {
        "model_input": SCRIPT_DIR / "model_license_edges_detailed.csv",
        "stem": "model_dataset_license_edges",
        "target_prefix": "license::",
        "dataset_edge_type": "has_license",
    },
    "task": {
        "model_input": SCRIPT_DIR / "model_task_edges_detailed.csv",
        "stem": "model_dataset_task_edges",
        "target_prefix": "task::",
        "dataset_edge_type": "supports_task",
    },
    "github": {
        "model_input": SCRIPT_DIR / "model_github_edges_detailed.csv",
        "stem": "model_dataset_github_edges",
        "target_prefix": "github::",
        "dataset_edge_type": "links_to_github",
    },
}

DATASET_LIBRARY_TAGS = KNOWN_LIBRARY_TAGS | {
    "dask", "datasets", "duckdb", "mlcroissant", "numpy", "pandas",
    "parquet", "polars", "pyarrow", "spark", "webdataset",
}
DATASET_LIBRARY_FIELDS = {"library_names", "librarys"}

DATASET_LICENSE_FIELDS = {
    "bigbio_license_shortname",
    "bigbio_license_short_name",
    "license_policy",
    "expert_generated_license",
    "annotations_and_code_license",
    "spdx_license_identifier",
    "source_licence_variant",
}
DATASET_LICENSE_ALIASES = {
    **LICENSE_ALIASES,
    "apache_2p0": "apache-2.0",
    "gpl_3p0": "gpl-3.0",
    "cc_by_4p0": "cc-by-4.0",
    "cc_by_nc_4p0": "cc-by-nc-4.0",
    "cc_by_nc_sa_4p0": "cc-by-nc-sa-4.0",
    "mit only": "mit",
}

DATASET_TASK_FIELDS = {
    "bigbio_tasks",
    "subtasks",
    "sub_tasks",
    "task_types",
    "task_category",
    "supported_tasks",
    "taskcategories",
    "fine_grained_tasks",
    "subtask_categories",
    "custom_task",
    "task_names",
    "primary_task",
    "secondary_tasks",
    "task_family",
}

DATASET_DIRECT_GITHUB_FIELDS = {
    "github", "github_link", "source_github", "repo_url", "repository",
    "repo", "source", "source_url", "challenge_repository", "code",
    "source_code", "source_code_repository", "repository_code",
    "restored_repository", "source_repository", "upstream_repository",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or query four combined model+dataset attribute subgraphs."
    )
    parser.add_argument("--dataset-input", type=Path, default=DEFAULT_DATASET_INPUT)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    query = parser.add_mutually_exclusive_group()
    query.add_argument("--query-library", metavar="LIBRARY")
    query.add_argument("--query-license", metavar="LICENSE")
    query.add_argument("--query-task", metavar="TASK")
    query.add_argument("--query-github", metavar="OWNER/REPOSITORY")
    query.add_argument(
        "--query-source",
        metavar="TYPED_ID",
        help="List all four attributes for model::id or dataset::id.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum query results to print; 0 prints all (default: 20).",
    )
    return parser.parse_args()


def relation_paths(output_dir: Path, relation: str) -> dict[str, Path]:
    stem = RELATIONS[relation]["stem"]
    return {
        "csv": output_dir / f"{stem}.csv",
        "jsonl": output_dir / f"{stem}.jsonl",
        "detailed_csv": output_dir / f"{stem}_detailed.csv",
        "detailed_jsonl": output_dir / f"{stem}_detailed.jsonl",
    }


def add_candidate(
    candidates: dict[str, tuple[str, str]],
    value: str | None,
    evidence: str,
    confidence: str,
) -> None:
    if value is not None and value not in candidates:
        candidates[value] = (evidence, confidence)


def candidate_dataset_libraries(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = candidate_libraries(metadata)
    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field in DATASET_LIBRARY_FIELDS:
            for raw in string_values(raw_value):
                add_candidate(
                    candidates,
                    normalize_library(raw),
                    field,
                    "declared_nonstandard",
                )
    for raw in string_values(metadata.get("tags")):
        library = normalize_library(raw)
        if library in DATASET_LIBRARY_TAGS:
            add_candidate(candidates, library, "tags", "tag_association")
    return candidates


def license_values(value: object) -> Iterator[str]:
    yield from string_values(value)
    if isinstance(value, dict):
        for key in ("id", "spdx", "name", "license"):
            yield from string_values(value.get(key))
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, dict):
                yield from license_values(item)


def candidate_dataset_licenses(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = candidate_licenses(metadata)
    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field == "license_info" or field in DATASET_LICENSE_FIELDS:
            for raw in license_values(raw_value):
                add_candidate(
                    candidates,
                    normalize_identifier(raw, DATASET_LICENSE_ALIASES),
                    field,
                    "declared_nonstandard",
                )
    return candidates


def nested_task_values(value: object) -> Iterator[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            yield cleaned
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from nested_task_values(item)
    elif isinstance(value, dict):
        conventional = value.get("type") or value.get("id") or value.get("name")
        if conventional is not None:
            yield from nested_task_values(conventional)
        else:
            for key, item in value.items():
                yield str(key)
                yield from nested_task_values(item)


def candidate_dataset_tasks(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = candidate_tasks(metadata)
    for raw_field, raw_value in metadata.items():
        field = normalize_field_name(raw_field)
        if field in DATASET_TASK_FIELDS:
            for raw in nested_task_values(raw_value):
                add_candidate(
                    candidates,
                    normalize_identifier(raw, TASK_ALIASES),
                    field,
                    "declared_nonstandard",
                )
    return candidates


def candidate_dataset_github(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = candidate_github(metadata)
    upgraded = {}
    for repository, (evidence, confidence) in candidates.items():
        top_field = evidence.split(".", 1)[0]
        if top_field in DATASET_DIRECT_GITHUB_FIELDS:
            upgraded[repository] = (evidence, "declared_link")
        else:
            upgraded[repository] = (evidence, confidence)
    return upgraded


DATASET_EXTRACTORS = {
    "library": candidate_dataset_libraries,
    "license": candidate_dataset_licenses,
    "task": candidate_dataset_tasks,
    "github": candidate_dataset_github,
}


def validate_generation_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    dataset_input = args.dataset_input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not dataset_input.is_file():
        raise FileNotFoundError(f"Dataset metadata not found: {dataset_input}")
    for relation, config in RELATIONS.items():
        if not config["model_input"].is_file():
            raise FileNotFoundError(
                f"Model {relation} detailed input not found: {config['model_input']}"
            )
    outputs = [
        path.resolve()
        for relation in RELATIONS
        for path in relation_paths(output_dir, relation).values()
    ]
    existing = [path for path in outputs if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing output files:\n"
            + "\n".join(str(path) for path in existing)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return dataset_input, output_dir


def write_edge(
    handles: dict[str, object],
    writers: dict[str, csv.DictWriter],
    row: dict[str, str],
) -> None:
    simple = {key: row[key] for key in SIMPLE_FIELDS}
    detailed = {key: row[key] for key in DETAILED_FIELDS}
    writers["csv"].writerow(simple)
    handles["jsonl"].write(
        json.dumps(simple, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    writers["detailed_csv"].writerow(detailed)
    handles["detailed_jsonl"].write(
        json.dumps(detailed, ensure_ascii=False, separators=(",", ":")) + "\n"
    )


def generate(args: argparse.Namespace) -> None:
    dataset_input, output_dir = validate_generation_paths(args)
    counters = {relation: Counter() for relation in RELATIONS}
    target_counts = {relation: Counter() for relation in RELATIONS}

    with ExitStack() as stack:
        handles: dict[str, dict[str, object]] = {}
        writers: dict[str, dict[str, csv.DictWriter]] = {}
        for relation in RELATIONS:
            paths = relation_paths(output_dir, relation)
            handles[relation] = {
                "csv": stack.enter_context(paths["csv"].open("x", newline="", encoding="utf-8")),
                "jsonl": stack.enter_context(paths["jsonl"].open("x", encoding="utf-8")),
                "detailed_csv": stack.enter_context(
                    paths["detailed_csv"].open("x", newline="", encoding="utf-8")
                ),
                "detailed_jsonl": stack.enter_context(
                    paths["detailed_jsonl"].open("x", encoding="utf-8")
                ),
            }
            writers[relation] = {
                "csv": csv.DictWriter(handles[relation]["csv"], fieldnames=SIMPLE_FIELDS),
                "detailed_csv": csv.DictWriter(
                    handles[relation]["detailed_csv"], fieldnames=DETAILED_FIELDS
                ),
            }
            writers[relation]["csv"].writeheader()
            writers[relation]["detailed_csv"].writeheader()

        # Reuse the already-generated, validated model edge sets exactly.
        for relation, config in RELATIONS.items():
            previous_source = None
            with config["model_input"].open(newline="", encoding="utf-8") as model_file:
                reader = csv.DictReader(model_file)
                if reader.fieldnames != DETAILED_FIELDS:
                    raise ValueError(
                        f"Unexpected schema in {config['model_input']}: {reader.fieldnames}"
                    )
                for row in reader:
                    write_edge(handles[relation], writers[relation], row)
                    counters[relation]["model_edges"] += 1
                    counters[relation][f"model_confidence:{row['confidence']}"] += 1
                    if row["source"] != previous_source:
                        counters[relation]["model_nodes"] += 1
                        previous_source = row["source"]
                    target_counts[relation][row["target"]] += 1

        with dataset_input.open(encoding="utf-8") as dataset_file:
            for line_number, line in enumerate(dataset_file, start=1):
                if not line.strip():
                    continue
                for relation in RELATIONS:
                    counters[relation]["dataset_records"] += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    for relation in RELATIONS:
                        counters[relation]["invalid_json"] += 1
                    print(f"Skipping invalid JSON at line {line_number}: {exc}")
                    continue
                dataset_id = record.get("datasetId")
                metadata = record.get("readme_metadata")
                if not isinstance(dataset_id, str) or not dataset_id.strip():
                    for relation in RELATIONS:
                        counters[relation]["invalid_dataset_id"] += 1
                    continue
                if not isinstance(metadata, dict) or not metadata:
                    continue
                dataset_id = dataset_id.strip()
                for relation, extractor in DATASET_EXTRACTORS.items():
                    counters[relation]["dataset_metadata_records"] += 1
                    candidates = extractor(metadata)
                    if not candidates:
                        continue
                    counters[relation]["dataset_nodes"] += 1
                    if len(candidates) > 1:
                        counters[relation]["dataset_nodes_multiple"] += 1
                    config = RELATIONS[relation]
                    for target, (evidence, confidence) in sorted(candidates.items()):
                        row = {
                            "source": f"dataset::{dataset_id}",
                            "edge_type": config["dataset_edge_type"],
                            "target": f"{config['target_prefix']}{target}",
                            "evidence": evidence,
                            "confidence": confidence,
                        }
                        write_edge(handles[relation], writers[relation], row)
                        counters[relation]["dataset_edges"] += 1
                        counters[relation][f"dataset_confidence:{confidence}"] += 1
                        target_counts[relation][row["target"]] += 1

    for relation in RELATIONS:
        stats = counters[relation]
        model_nodes = stats["model_nodes"]
        dataset_nodes = stats["dataset_nodes"]
        total_edges = stats["model_edges"] + stats["dataset_edges"]
        attribute_nodes = len(target_counts[relation])
        print(f"\n## Combined {relation} subgraph")
        print(f"Model source nodes:          {model_nodes:12,}")
        print(f"Dataset source nodes:        {dataset_nodes:12,}")
        print(f"Unique attribute nodes:      {attribute_nodes:12,}")
        print(f"Total unique nodes:          {model_nodes + dataset_nodes + attribute_nodes:12,}")
        print(f"Model edges:                 {stats['model_edges']:12,}")
        print(f"Dataset edges:               {stats['dataset_edges']:12,}")
        print(f"Total unique edges:          {total_edges:12,}")
        print(f"Datasets with multiple:      {stats['dataset_nodes_multiple']:12,}")
        print("Evidence-edge counts:")
        for key in sorted(stats):
            if "confidence:" in key:
                print(f"  {key:38} {stats[key]:12,}")
        print(f"Most common {relation} targets:")
        for target, count in target_counts[relation].most_common(15):
            print(f"  {target:45} {count:12,}")
        paths = relation_paths(output_dir, relation)
        print(f"CSV:            {paths['csv']}")
        print(f"JSONL:          {paths['jsonl']}")
        print(f"Detailed CSV:   {paths['detailed_csv']}")
        print(f"Detailed JSONL: {paths['detailed_jsonl']}")
    print(f"\nDataset records scanned: {counters['library']['dataset_records']:,}")
    print(
        "Dataset records with metadata: "
        f"{counters['library']['dataset_metadata_records']:,}"
    )
    print(f"Invalid dataset IDs: {counters['library']['invalid_dataset_id']:,}")
    print(f"Invalid JSON lines: {counters['library']['invalid_json']:,}")


def read_results(
    path: Path,
    source: str | None = None,
    target: str | None = None,
) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Combined edge CSV not found: {path}")
    results = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            if source is not None and row.get("source") == source:
                results.append(row["target"])
            elif target is not None and row.get("target") == target:
                results.append(row["source"])
    return sorted(set(results), key=str.lower)


def print_results(results: list[str], limit: int) -> None:
    shown = results if limit == 0 else results[:limit]
    print(f"Distinct results: {len(results):,}")
    print(f"Results shown: {len(shown):,}/{len(results):,}")
    for result in shown:
        print(result)


def query(args: argparse.Namespace) -> None:
    if args.limit < 0:
        raise ValueError("--limit cannot be negative")
    output_dir = args.output_dir.expanduser().resolve()
    if args.query_source is not None:
        source = args.query_source.strip()
        if not source.startswith(("model::", "dataset::")):
            raise ValueError("--query-source must start with model:: or dataset::")
        print(f"Source: {source}")
        for relation in RELATIONS:
            print(f"\n{relation.capitalize()} targets")
            print_results(
                read_results(relation_paths(output_dir, relation)["csv"], source=source),
                args.limit,
            )
        return

    if args.query_library is not None:
        relation = "library"
        value = normalize_library(args.query_library)
    elif args.query_license is not None:
        relation = "license"
        value = normalize_identifier(args.query_license, DATASET_LICENSE_ALIASES)
    elif args.query_task is not None:
        relation = "task"
        value = normalize_identifier(args.query_task, TASK_ALIASES)
    else:
        relation = "github"
        value = normalize_github_query(args.query_github)
    if value is None:
        raise ValueError(f"Invalid {relation} query")
    target = f"{RELATIONS[relation]['target_prefix']}{value}"
    print(f"Target: {target}")
    print_results(
        read_results(relation_paths(output_dir, relation)["csv"], target=target),
        args.limit,
    )


def main() -> int:
    args = parse_args()
    try:
        if any(
            value is not None
            for value in (
                args.query_library,
                args.query_license,
                args.query_task,
                args.query_github,
                args.query_source,
            )
        ):
            query(args)
        else:
            generate(args)
    except KeyboardInterrupt:
        print("Interrupted; move incomplete output files before rerunning.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- build_model_readme_attribute_subgraphs.py -----------------------------
SOURCES['build_model_readme_attribute_subgraphs'] = r'''#!/usr/bin/env python3
"""Build and merge README-derived model library, license, and task edges.

Created: 2026-09-28
Version: v2026.09.28-02
Purpose: Persist reproducible attribute subgraphs from full model READMEs.

Only YAML front matter is parsed. Existing metadata-derived graph files are
read as evidence and are never overwritten. SQLite provides exact scan resume
and case-independent edge deduplication through normalized target identifiers.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

import yaml
from huggingface_hub.repocard import REGEX_YAML_BLOCK

from model_library_edges import candidate_libraries
from model_license_task_github_edges import candidate_licenses, candidate_tasks


CHANGE_ID = "v2026.09.28-02"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_model_readmes_full_2026Sep25.jsonl"
DEFAULT_STATE = SCRIPT_DIR / "model_readme_attribute_subgraphs_v2.state.sqlite3"
SNAPSHOT = "full_model_readmes_2026Sep25"
RELATIONS = {
    "library": {
        "edge_type": "uses_library",
        "prefix": "library::",
        "metadata": SCRIPT_DIR / "model_library_edges_detailed.csv",
    },
    "license": {
        "edge_type": "has_license",
        "prefix": "license::",
        "metadata": SCRIPT_DIR / "model_license_edges_detailed.csv",
    },
    "task": {
        "edge_type": "performs_task",
        "prefix": "task::",
        "metadata": SCRIPT_DIR / "model_task_edges_detailed.csv",
    },
}
EXTRACTORS = {
    "library": candidate_libraries,
    "license": candidate_licenses,
    "task": candidate_tasks,
}
SIMPLE_FIELDS = ("source", "edge_type", "target")
README_DETAIL_FIELDS = SIMPLE_FIELDS + ("evidence", "confidence", "evidence_source", "snapshot")
MERGED_DETAIL_FIELDS = SIMPLE_FIELDS + (
    "evidence_sources",
    "metadata_evidence",
    "metadata_confidence",
    "readme_evidence",
    "readme_confidence",
    "readme_snapshot",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build README model attribute subgraphs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--commit-records", type=int, default=2_000)
    parser.add_argument("--max-records", type=int, default=0)
    return parser.parse_args()


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS edges("
        "relation TEXT NOT NULL,source TEXT NOT NULL,edge_type TEXT NOT NULL,target TEXT NOT NULL,"
        "readme_evidence TEXT,readme_confidence TEXT,metadata_evidence TEXT,metadata_confidence TEXT,"
        "PRIMARY KEY(relation,source,target))"
    )
    db.commit()
    return db


def state_get(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def state_set(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def initialize(db: sqlite3.Connection, input_path: Path, output_dir: Path) -> None:
    stat = input_path.stat()
    config = json.dumps(
        {
            "change_id": CHANGE_ID,
            "input": str(input_path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "output_dir": str(output_dir),
            "metadata": {key: str(value["metadata"]) for key, value in RELATIONS.items()},
        },
        sort_keys=True,
    )
    stored = state_get(db, "configuration")
    if stored is not None and stored != config:
        raise RuntimeError("State database belongs to another configuration")
    if stored is not None:
        return
    with db:
        state_set(db, "configuration", config)
        state_set(db, "input_offset", 0)
        state_set(db, "raw_records", 0)
        state_set(db, "readable_records", 0)
        state_set(db, "yaml_records", 0)
        state_set(db, "no_yaml", 0)
        state_set(db, "invalid_yaml", 0)
        state_set(db, "empty_yaml", 0)
        state_set(db, "readme_complete", 0)
        state_set(db, "export_complete", 0)


def scan_readmes(db: sqlite3.Connection, input_path: Path, commit_records: int, max_records: int) -> None:
    if state_get(db, "readme_complete") == "1":
        return
    offset = int(state_get(db, "input_offset") or 0)
    counts = Counter(
        {
            key: int(state_get(db, key) or 0)
            for key in ("raw_records", "readable_records", "yaml_records", "no_yaml", "invalid_yaml", "empty_yaml")
        }
    )
    pending: list[tuple[str, str, str, str, str, str]] = []
    processed_this_run = 0
    with input_path.open("rb") as stream:
        stream.seek(offset)
        while max_records == 0 or processed_this_run < max_records:
            line = stream.readline()
            if not line:
                with db:
                    state_set(db, "readme_complete", 1)
                break
            counts["raw_records"] += 1
            processed_this_run += 1
            record = json.loads(line)
            if record.get("status") == "ok" and isinstance(record.get("readme"), str):
                counts["readable_records"] += 1
                match = REGEX_YAML_BLOCK.search(record["readme"])
                if not match:
                    counts["no_yaml"] += 1
                else:
                    try:
                        metadata = yaml.safe_load(match.group(2))
                    except Exception:
                        counts["invalid_yaml"] += 1
                        metadata = None
                    if isinstance(metadata, dict) and metadata:
                        counts["yaml_records"] += 1
                        source = f"model::{str(record.get('modelId') or '').strip()}"
                        for relation, extractor in EXTRACTORS.items():
                            config = RELATIONS[relation]
                            for target, (evidence, confidence) in extractor(metadata).items():
                                pending.append(
                                    (
                                        relation,
                                        source,
                                        str(config["edge_type"]),
                                        f"{config['prefix']}{target}",
                                        evidence,
                                        confidence,
                                    )
                                )
                    elif metadata is not None:
                        counts["empty_yaml"] += 1
            if processed_this_run % commit_records == 0:
                with db:
                    db.executemany(
                        "INSERT INTO edges(relation,source,edge_type,target,readme_evidence,readme_confidence) "
                        "VALUES(?,?,?,?,?,?) ON CONFLICT(relation,source,target) DO UPDATE SET "
                        "readme_evidence=excluded.readme_evidence,readme_confidence=excluded.readme_confidence",
                        pending,
                    )
                    pending.clear()
                    state_set(db, "input_offset", stream.tell())
                    for key, value in counts.items():
                        state_set(db, key, value)
                if counts["readable_records"] and counts["readable_records"] % 100_000 < commit_records:
                    print(
                        f"readable={counts['readable_records']:,} yaml={counts['yaml_records']:,} "
                        f"stored_edges={db.execute('SELECT COUNT(*) FROM edges WHERE readme_evidence IS NOT NULL').fetchone()[0]:,}",
                        flush=True,
                    )
        if pending or int(state_get(db, "input_offset") or 0) != stream.tell():
            with db:
                db.executemany(
                    "INSERT INTO edges(relation,source,edge_type,target,readme_evidence,readme_confidence) "
                    "VALUES(?,?,?,?,?,?) ON CONFLICT(relation,source,target) DO UPDATE SET "
                    "readme_evidence=excluded.readme_evidence,readme_confidence=excluded.readme_confidence",
                    pending,
                )
                state_set(db, "input_offset", stream.tell())
                for key, value in counts.items():
                    state_set(db, key, value)


def import_metadata(db: sqlite3.Connection) -> None:
    for relation, config in RELATIONS.items():
        state_key = f"metadata_complete_{relation}"
        if state_get(db, state_key) == "1":
            continue
        path = Path(config["metadata"])
        pending = []
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                pending.append(
                    (
                        relation,
                        row["source"],
                        row["edge_type"],
                        row["target"],
                        row.get("evidence", ""),
                        row.get("confidence", ""),
                    )
                )
                if len(pending) >= 10_000:
                    with db:
                        db.executemany(
                            "INSERT INTO edges(relation,source,edge_type,target,metadata_evidence,metadata_confidence) "
                            "VALUES(?,?,?,?,?,?) ON CONFLICT(relation,source,target) DO UPDATE SET "
                            "metadata_evidence=excluded.metadata_evidence,metadata_confidence=excluded.metadata_confidence",
                            pending,
                        )
                    pending.clear()
        with db:
            db.executemany(
                "INSERT INTO edges(relation,source,edge_type,target,metadata_evidence,metadata_confidence) "
                "VALUES(?,?,?,?,?,?) ON CONFLICT(relation,source,target) DO UPDATE SET "
                "metadata_evidence=excluded.metadata_evidence,metadata_confidence=excluded.metadata_confidence",
                pending,
            )
            state_set(db, state_key, 1)
        print(f"Imported metadata evidence: {relation}", flush=True)


def paths(output_dir: Path, relation: str, scope: str) -> dict[str, Path]:
    stem = f"model_{relation}_edges_{scope}"
    return {
        "csv": output_dir / f"{stem}.csv",
        "jsonl": output_dir / f"{stem}.jsonl",
        "detailed_csv": output_dir / f"{stem}_detailed.csv",
        "detailed_jsonl": output_dir / f"{stem}_detailed.jsonl",
    }


def export_relation(db: sqlite3.Connection, output_dir: Path, relation: str, scope: str) -> None:
    final = paths(output_dir, relation, scope)
    existing = [path for path in final.values() if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite:\n" + "\n".join(map(str, existing)))
    temporary = {key: path.with_name(path.name + ".tmp") for key, path in final.items()}
    for path in temporary.values():
        if path.exists():
            path.unlink()
    condition = "readme_evidence IS NOT NULL" if scope == "readme_full" else "1=1"
    fields = README_DETAIL_FIELDS if scope == "readme_full" else MERGED_DETAIL_FIELDS
    handles = {key: path.open("x" if "jsonl" in key else "x", newline="" if "csv" in key else None, encoding="utf-8") for key, path in temporary.items()}
    try:
        csv_writer = csv.DictWriter(handles["csv"], fieldnames=SIMPLE_FIELDS)
        detailed_writer = csv.DictWriter(handles["detailed_csv"], fieldnames=fields)
        csv_writer.writeheader()
        detailed_writer.writeheader()
        query = (
            "SELECT source,edge_type,target,readme_evidence,readme_confidence,metadata_evidence,metadata_confidence "
            f"FROM edges WHERE relation=? AND {condition} ORDER BY source,target"
        )
        count = 0
        for source, edge_type, target, revidence, rconfidence, mevidence, mconfidence in db.execute(query, (relation,)):
            simple = {"source": source, "edge_type": edge_type, "target": target}
            if scope == "readme_full":
                detailed = {
                    **simple,
                    "evidence": revidence,
                    "confidence": rconfidence,
                    "evidence_source": "full_readme_yaml",
                    "snapshot": SNAPSHOT,
                }
            else:
                sources = []
                if mevidence is not None:
                    sources.append("api_card_metadata")
                if revidence is not None:
                    sources.append("full_readme_yaml")
                detailed = {
                    **simple,
                    "evidence_sources": ";".join(sources),
                    "metadata_evidence": mevidence or "",
                    "metadata_confidence": mconfidence or "",
                    "readme_evidence": revidence or "",
                    "readme_confidence": rconfidence or "",
                    "readme_snapshot": SNAPSHOT if revidence is not None else "",
                }
            csv_writer.writerow(simple)
            detailed_writer.writerow(detailed)
            handles["jsonl"].write(json.dumps(simple, ensure_ascii=False, separators=(",", ":")) + "\n")
            handles["detailed_jsonl"].write(json.dumps(detailed, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
        for handle in handles.values():
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        for handle in handles.values():
            handle.close()
    for key, temp in temporary.items():
        temp.rename(final[key])
    print(f"Exported {relation} {scope}: {count:,} edges", flush=True)


def main() -> int:
    args = parse_args()
    if args.commit_records < 1 or args.max_records < 0:
        raise ValueError("Invalid commit or record limit")
    input_path = args.input.expanduser().resolve()
    state_path = args.state_db.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not input_path.is_file() or input_path == state_path:
        raise ValueError("Invalid input/state paths")
    output_dir.mkdir(parents=True, exist_ok=True)
    db = connect(state_path)
    try:
        initialize(db, input_path, output_dir)
        scan_readmes(db, input_path, args.commit_records, args.max_records)
        if state_get(db, "readme_complete") != "1":
            print("Stopped at --max-records; rerun to resume.")
            return 0
        import_metadata(db)
        if state_get(db, "export_complete") != "1":
            for relation in RELATIONS:
                export_relation(db, output_dir, relation, "readme_full")
                export_relation(db, output_dir, relation, "merged_v2")
            with db:
                state_set(db, "export_complete", 1)
        for relation in RELATIONS:
            readme_edges = db.execute(
                "SELECT COUNT(*) FROM edges WHERE relation=? AND readme_evidence IS NOT NULL", (relation,)
            ).fetchone()[0]
            merged_edges = db.execute("SELECT COUNT(*) FROM edges WHERE relation=?", (relation,)).fetchone()[0]
            print(f"{relation}: README={readme_edges:,} merged={merged_edges:,}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- build_latest_dataset_attributes.py ------------------------------------
SOURCES['build_latest_dataset_attributes'] = r'''#!/usr/bin/env python3
"""Build Dataset Library, License, and Task edges from the latest full READMEs.

Created: 2026-10-02
Version: v2026.10.02-02
Purpose: Parse YAML front matter from the 2026-09-28 full Dataset README
         snapshot into independent, resumable, evidence-bearing subgraphs.

Change history:
- 2026-10-02 v2026.10.02-02: use LibYAML's safe loader for the full-corpus
  scan. Backup: build_latest_dataset_attributes.py.bak.20261002-184103
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from huggingface_hub.repocard import REGEX_YAML_BLOCK


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INPUT = ROOT / "all_dataset_readmes_full_2026Sep28.jsonl"
STATE = HERE / "latest_dataset_attributes.state.sqlite3"
RESULTS = HERE / "results"
SNAPSHOT = "full_dataset_readmes_2026Sep28"

import sys
sys.path.insert(0, str(ROOT))
from model_dataset_attribute_edges import DATASET_EXTRACTORS, RELATIONS  # noqa: E402


CONFIG = {
    relation: {
        "edge_type": RELATIONS[relation]["dataset_edge_type"],
        "prefix": RELATIONS[relation]["target_prefix"],
    }
    for relation in ("library", "license", "task")
}


def connect():
    db = sqlite3.connect(STATE, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS edges("
        "relation TEXT NOT NULL,source TEXT NOT NULL,edge_type TEXT NOT NULL,target TEXT NOT NULL,"
        "evidence TEXT NOT NULL,confidence TEXT NOT NULL,retrieved_at_utc TEXT NOT NULL,"
        "PRIMARY KEY(relation,source,target))"
    )
    db.commit()
    return db


def get(db, key, default="0"):
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return default if row is None else str(row[0])


def set_value(db, key, value):
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def initialize(db):
    stat = INPUT.stat()
    config = json.dumps({
        "change_id": "v2026.10.02-02", "input": str(INPUT),
        "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
    }, sort_keys=True)
    stored = get(db, "configuration", "")
    if stored and stored != config:
        raise RuntimeError("State database belongs to a different input snapshot")
    if stored:
        return
    with db:
        set_value(db, "configuration", config)
        for key in (
            "input_offset", "records", "ok", "restricted", "no_readme",
            "yaml_records", "no_yaml", "invalid_yaml", "empty_yaml", "complete",
        ):
            set_value(db, key, 0)


def scan(db):
    if get(db, "complete") == "1":
        return
    keys = (
        "records", "ok", "restricted", "no_readme", "yaml_records",
        "no_yaml", "invalid_yaml", "empty_yaml",
    )
    counts = Counter({key: int(get(db, key)) for key in keys})
    offset = int(get(db, "input_offset"))
    pending = []
    with INPUT.open("rb") as stream:
        stream.seek(offset)
        while True:
            line = stream.readline()
            if not line:
                with db:
                    set_value(db, "complete", 1)
                break
            record = json.loads(line)
            counts["records"] += 1
            status = str(record.get("status") or "unknown")
            counts[status] += 1
            if status == "ok" and isinstance(record.get("readme"), str):
                match = REGEX_YAML_BLOCK.search(record["readme"])
                if not match:
                    counts["no_yaml"] += 1
                else:
                    try:
                        metadata = yaml.load(match.group(2), Loader=yaml.CSafeLoader)
                    except Exception:
                        metadata = None
                        counts["invalid_yaml"] += 1
                    if isinstance(metadata, dict) and metadata:
                        counts["yaml_records"] += 1
                        dataset_id = str(record.get("datasetId") or "").strip()
                        if dataset_id:
                            source = f"dataset::{dataset_id}"
                            for relation, cfg in CONFIG.items():
                                for target, (evidence, confidence) in DATASET_EXTRACTORS[relation](metadata).items():
                                    pending.append((
                                        relation, source, cfg["edge_type"], cfg["prefix"] + target,
                                        evidence, confidence, str(record.get("retrieved_at_utc") or ""),
                                    ))
                    elif metadata is not None:
                        counts["empty_yaml"] += 1
            if counts["records"] % 2000 == 0:
                with db:
                    db.executemany(
                        "INSERT INTO edges VALUES(?,?,?,?,?,?,?) ON CONFLICT(relation,source,target) "
                        "DO UPDATE SET evidence=excluded.evidence,confidence=excluded.confidence,"
                        "retrieved_at_utc=excluded.retrieved_at_utc",
                        pending,
                    )
                    pending.clear()
                    set_value(db, "input_offset", stream.tell())
                    for key, value in counts.items():
                        set_value(db, key, value)
                if counts["records"] % 100000 < 2000:
                    stored = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                    print(
                        f"records={counts['records']:,} ok={counts['ok']:,} "
                        f"yaml={counts['yaml_records']:,} edges={stored:,}", flush=True,
                    )
        if pending:
            with db:
                db.executemany(
                    "INSERT INTO edges VALUES(?,?,?,?,?,?,?) ON CONFLICT(relation,source,target) "
                    "DO UPDATE SET evidence=excluded.evidence,confidence=excluded.confidence,"
                    "retrieved_at_utc=excluded.retrieved_at_utc",
                    pending,
                )
                set_value(db, "input_offset", stream.tell())
                for key, value in counts.items():
                    set_value(db, key, value)


def write_csv(path, fields, rows):
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export(db):
    summary = {
        "change_id": "v2026.10.02-02",
        "snapshot": SNAPSHOT,
        "input": str(INPUT),
        "input_sha256": sha256(INPUT),
        "scan": {key: int(get(db, key)) for key in (
            "records", "ok", "restricted", "no_readme", "yaml_records",
            "no_yaml", "invalid_yaml", "empty_yaml",
        )},
        "subgraphs": {},
    }
    rng = random.Random(20261002)
    for relation in CONFIG:
        query = (
            "SELECT source,edge_type,target,evidence,confidence,retrieved_at_utc "
            "FROM edges WHERE relation=? ORDER BY source,target"
        )
        data = [dict(zip(
            ("source", "edge_type", "target", "evidence", "confidence", "retrieved_at_utc"), row
        )) for row in db.execute(query, (relation,))]
        simple = [{key: row[key] for key in ("source", "edge_type", "target")} for row in data]
        write_csv(
            RESULTS / f"dataset_{relation}_latest_readme_edges.csv",
            ["source", "edge_type", "target"], simple,
        )
        write_csv(
            RESULTS / f"dataset_{relation}_latest_readme_evidence.csv",
            ["source", "edge_type", "target", "evidence", "confidence", "retrieved_at_utc"], data,
        )
        grouped = defaultdict(list)
        for row in data:
            grouped[row["confidence"]].append(row)
        sample = []
        for confidence in sorted(grouped):
            candidates = grouped[confidence]
            selected = candidates if len(candidates) <= 100 else rng.sample(candidates, 100)
            for row in selected:
                sample.append({**row, "manual_label": "", "review_notes": ""})
        write_csv(
            RESULTS / f"dataset_{relation}_latest_validation_sample.csv",
            ["source", "edge_type", "target", "evidence", "confidence", "retrieved_at_utc",
             "manual_label", "review_notes"],
            sample,
        )
        sources = {row["source"] for row in data}
        targets = {row["target"] for row in data}
        summary["subgraphs"][relation] = {
            "edges": len(data), "source_nodes": len(sources), "target_nodes": len(targets),
            "nodes": len(sources | targets),
            "confidence": dict(sorted(Counter(row["confidence"] for row in data).items())),
            "evidence": dict(Counter(row["evidence"] for row in data).most_common()),
            "duplicate_edges": len(data) - len({(r["source"], r["target"]) for r in data}),
            "self_loops": len(sources & targets),
            "validation_sample_rows": len(sample),
        }
    (RESULTS / "latest_dataset_attributes_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def main():
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)
    RESULTS.mkdir(parents=True, exist_ok=True)
    db = connect()
    try:
        initialize(db)
        scan(db)
        if get(db, "complete") != "1":
            raise RuntimeError("Scan did not complete")
        export(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
'''

# --- extract_model_github_edges_streaming.py -------------------------------
SOURCES['extract_model_github_edges_streaming'] = r'''#!/usr/bin/env python3
"""Incrementally extract Model-GitHub edges from the full README crawl.

Created: 2026-09-25
Version: v2026.09.25-03
Purpose: Build deduplicated Model-GitHub outputs while README collection runs.

Only bytes committed by the downloader's SQLite state are read. Output byte
offsets and unique edges are committed together, allowing exact resumption.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import time
from pathlib import Path

CHANGE_ID = "v2026.09.25-03"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_model_readmes_full_2026Sep25.jsonl"
DEFAULT_CRAWL_STATE = SCRIPT_DIR / "all_model_readmes_full_2026Sep25.jsonl.state.sqlite3"
DEFAULT_STATE = SCRIPT_DIR / "model_github_edges_full.state.sqlite3"
SIMPLE_FIELDS = ("source", "edge_type", "target")
DETAILED_FIELDS = SIMPLE_FIELDS + ("evidence", "confidence", "population")
MARKDOWN_LINK = re.compile(
    r"(?P<image>!)?\[(?P<label>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+[^)]*)?\)"
)
GITHUB_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
GITHUB_RAW_URL = re.compile(
    r"https?://raw\.githubusercontent\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
GITHUB_SSH = re.compile(
    r"git@github\.com:(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
STRONG_LABEL = re.compile(
    r"\b(github|source|source code|code|repository|implementation)\b", re.IGNORECASE
)
RESERVED_OWNERS = {
    "about", "apps", "collections", "contact", "customer-stories", "enterprise",
    "features", "issues", "join", "login", "marketplace", "new", "notifications",
    "orgs", "organizations", "pricing", "pulls", "search", "security", "settings",
    "site", "sponsors", "topics", "trending", "users",
}
PRIORITY = {"readme_declared_link": 0, "readme_reference": 1, "badge_reference": 2}


def repository_matches(text: str):
    """Yield case-preserving owner/repository pairs from supported GitHub URLs."""
    for pattern in (GITHUB_URL, GITHUB_RAW_URL, GITHUB_SSH):
        for match in pattern.finditer(text):
            owner = match.group("owner")
            repository = match.group("repo").rstrip(".,;:!?")
            if repository.lower().endswith(".git"):
                repository = repository[:-4]
            if owner.lower() in RESERVED_OWNERS or not repository:
                continue
            yield owner, repository


def github_candidates(markdown: str) -> dict[str, tuple[str, str, str]]:
    """Return repo key -> (canonical URL, evidence, confidence)."""
    found: dict[str, tuple[str, str, str]] = {}
    linked_keys: set[str] = set()
    for match in MARKDOWN_LINK.finditer(markdown):
        context = markdown[max(0, match.start() - 100):match.start()]
        confidence = (
            "badge_reference"
            if match.group("image")
            else "readme_declared_link"
            if STRONG_LABEL.search(match.group("label")) or STRONG_LABEL.search(context)
            else "readme_reference"
        )
        evidence = f"model_card_markdown:{match.group('label').strip() or 'unlabelled_link'}"
        for owner, repository in repository_matches(match.group("url")):
            key = f"{owner}/{repository}".lower()
            linked_keys.add(key)
            proposed = (f"https://github.com/{owner}/{repository}", evidence, confidence)
            current = found.get(key)
            if current is None or PRIORITY[confidence] < PRIORITY[current[2]]:
                found[key] = proposed
    for owner, repository in repository_matches(markdown):
        key = f"{owner}/{repository}".lower()
        if key in linked_keys:
            continue
        found.setdefault(
            key,
            (
                f"https://github.com/{owner}/{repository}",
                "model_card_markdown:embedded_url",
                "readme_reference",
            ),
        )
    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream full-crawl Model-GitHub extraction.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--crawl-state", type=Path, default=DEFAULT_CRAWL_STATE)
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--batch-records", type=int, default=1_000)
    return parser.parse_args()


def output_paths(directory: Path) -> dict[str, Path]:
    return {
        "csv": directory / "model_github_edges_full.csv",
        "jsonl": directory / "model_github_edges_full.jsonl",
        "detailed_csv": directory / "model_github_edges_full_detailed.csv",
        "detailed_jsonl": directory / "model_github_edges_full_detailed.jsonl",
    }


def connect_state(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS edges("
        "source TEXT NOT NULL,repo_key TEXT NOT NULL,target TEXT NOT NULL,evidence TEXT NOT NULL,"
        "confidence TEXT NOT NULL,population TEXT NOT NULL,"
        "PRIMARY KEY(source,repo_key))"
    )
    db.commit()
    return db


def state_get(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def state_set(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def crawl_value(path: Path, key: str) -> str | None:
    uri = f"file:{path.resolve()}?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=60)
    try:
        row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])
    finally:
        db.close()


def csv_bytes(fields: tuple[str, ...], row: dict[str, str], header: bool = False) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    if header:
        writer.writeheader()
    else:
        writer.writerow({field: row[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def jsonl_bytes(fields: tuple[str, ...], row: dict[str, str]) -> bytes:
    value = {field: row[field] for field in fields}
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def initialize(
    db: sqlite3.Connection,
    input_path: Path,
    crawl_state: Path,
    paths: dict[str, Path],
) -> None:
    identity = json.dumps(
        {
            "change_id": CHANGE_ID,
            "input": str(input_path),
            "crawl_state": str(crawl_state),
            "outputs": {key: str(value) for key, value in paths.items()},
        },
        sort_keys=True,
    )
    stored = state_get(db, "configuration")
    if stored is not None and stored != identity:
        raise RuntimeError("Extractor state belongs to another configuration")
    if stored is not None:
        return
    existing = [path for path in paths.values() if path.exists() and path.stat().st_size]
    if existing:
        raise RuntimeError(f"Non-empty outputs exist without state: {existing}")

    streams = {key: path.open("w+b") for key, path in paths.items()}
    try:
        streams["csv"].write(csv_bytes(SIMPLE_FIELDS, {}, header=True))
        streams["detailed_csv"].write(csv_bytes(DETAILED_FIELDS, {}, header=True))
        for stream in streams.values():
            stream.flush()
            os.fsync(stream.fileno())
        with db:
            state_set(db, "configuration", identity)
            state_set(db, "input_offset", 0)
            state_set(db, "records_processed", 0)
            state_set(db, "readmes_processed", 0)
            state_set(db, "edges", 0)
            state_set(db, "finished", 0)
            for key, stream in streams.items():
                state_set(db, f"output_offset_{key}", stream.tell())
    finally:
        for stream in streams.values():
            stream.close()


def open_outputs(db: sqlite3.Connection, paths: dict[str, Path]):
    streams = {key: path.open("r+b") for key, path in paths.items()}
    for key, stream in streams.items():
        committed = int(state_get(db, f"output_offset_{key}") or 0)
        stream.seek(0, os.SEEK_END)
        if stream.tell() < committed:
            raise RuntimeError(f"Output shorter than committed offset: {paths[key]}")
        if stream.tell() > committed:
            stream.truncate(committed)
        stream.seek(committed)
    return streams


def main() -> int:
    args = parse_args()
    if args.poll_seconds <= 0 or args.batch_records < 1:
        raise ValueError("Invalid polling or batch configuration")
    input_path = args.input.expanduser().resolve()
    crawl_state = args.crawl_state.expanduser().resolve()
    state_path = args.state_db.expanduser().resolve()
    directory = args.output_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    paths = output_paths(directory)
    if not input_path.is_file() or not crawl_state.is_file():
        raise FileNotFoundError("README input or crawler state is missing")

    db = connect_state(state_path)
    initialize(db, input_path, crawl_state, paths)
    streams = open_outputs(db, paths)
    input_stream = input_path.open("rb")
    try:
        while True:
            input_offset = int(state_get(db, "input_offset") or 0)
            committed = int(crawl_value(crawl_state, "output_offset") or 0)
            crawl_finished = crawl_value(crawl_state, "finished") == "1"
            if input_offset >= committed:
                if crawl_finished:
                    with db:
                        state_set(db, "finished", 1)
                    print("Extraction complete.", flush=True)
                    break
                time.sleep(args.poll_seconds)
                continue

            input_stream.seek(input_offset)
            batch: list[tuple[int, dict]] = []
            while len(batch) < args.batch_records and input_stream.tell() < committed:
                line = input_stream.readline()
                if not line or input_stream.tell() > committed:
                    break
                batch.append((input_stream.tell(), json.loads(line)))
            if not batch:
                time.sleep(args.poll_seconds)
                continue

            records_processed = int(state_get(db, "records_processed") or 0)
            readmes_processed = int(state_get(db, "readmes_processed") or 0)
            edges_count = int(state_get(db, "edges") or 0)
            db.execute("BEGIN IMMEDIATE")
            try:
                for _, record in batch:
                    records_processed += 1
                    if record.get("status") != "ok" or not isinstance(record.get("readme"), str):
                        continue
                    readmes_processed += 1
                    model_id = str(record.get("modelId") or "").strip()
                    population = str(record.get("population") or "unknown")
                    for repo_key, (target, evidence, confidence) in github_candidates(record["readme"]).items():
                        row = {
                            "source": f"model::{model_id}",
                            "edge_type": "links_to_github",
                            "target": target,
                            "evidence": evidence,
                            "confidence": confidence,
                            "population": population,
                        }
                        inserted = db.execute(
                            "INSERT OR IGNORE INTO edges(source,repo_key,target,evidence,confidence,population) "
                            "VALUES(?,?,?,?,?,?)",
                            (row["source"], repo_key, row["target"], evidence, confidence, population),
                        ).rowcount
                        if not inserted:
                            continue
                        streams["csv"].write(csv_bytes(SIMPLE_FIELDS, row))
                        streams["jsonl"].write(jsonl_bytes(SIMPLE_FIELDS, row))
                        streams["detailed_csv"].write(csv_bytes(DETAILED_FIELDS, row))
                        streams["detailed_jsonl"].write(jsonl_bytes(DETAILED_FIELDS, row))
                        edges_count += 1
                for stream in streams.values():
                    stream.flush()
                    os.fsync(stream.fileno())
                state_set(db, "input_offset", batch[-1][0])
                state_set(db, "records_processed", records_processed)
                state_set(db, "readmes_processed", readmes_processed)
                state_set(db, "edges", edges_count)
                for key, stream in streams.items():
                    state_set(db, f"output_offset_{key}", stream.tell())
                db.commit()
            except Exception:
                db.rollback()
                raise
            print(
                f"records={records_processed:,} readmes={readmes_processed:,} "
                f"unique_edges={edges_count:,}",
                flush=True,
            )
    finally:
        input_stream.close()
        for stream in streams.values():
            stream.close()
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- extract_dataset_github_edges_streaming.py -----------------------------
SOURCES['extract_dataset_github_edges_streaming'] = r'''#!/usr/bin/env python3
"""Incrementally extract Dataset-GitHub edges from the full README crawl.

Created: 2026-09-28
Version: v2026.09.28-01
Purpose: Build deduplicated Dataset-GitHub outputs during README collection.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sqlite3
import time
from pathlib import Path

from extract_model_github_edges_streaming import github_candidates


CHANGE_ID = "v2026.09.28-01"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_dataset_readmes_full_2026Sep28.jsonl"
DEFAULT_CRAWL_STATE = SCRIPT_DIR / "all_dataset_readmes_full_2026Sep28.jsonl.state.sqlite3"
DEFAULT_STATE = SCRIPT_DIR / "dataset_github_edges_full.state.sqlite3"
SIMPLE_FIELDS = ("source", "edge_type", "target")
DETAILED_FIELDS = SIMPLE_FIELDS + ("evidence", "confidence", "population")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream full-crawl Dataset-GitHub extraction.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--crawl-state", type=Path, default=DEFAULT_CRAWL_STATE)
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--batch-records", type=int, default=1_000)
    return parser.parse_args()


def output_paths(directory: Path) -> dict[str, Path]:
    return {
        "csv": directory / "dataset_github_edges_full.csv",
        "jsonl": directory / "dataset_github_edges_full.jsonl",
        "detailed_csv": directory / "dataset_github_edges_full_detailed.csv",
        "detailed_jsonl": directory / "dataset_github_edges_full_detailed.jsonl",
    }


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS edges("
        "source TEXT NOT NULL,repo_key TEXT NOT NULL,target TEXT NOT NULL,evidence TEXT NOT NULL,"
        "confidence TEXT NOT NULL,population TEXT NOT NULL,"
        "PRIMARY KEY(source,repo_key))"
    )
    db.commit()
    return db


def state_get(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def state_set(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def crawl_value(path: Path, key: str) -> str | None:
    db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=60)
    try:
        row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])
    finally:
        db.close()


def csv_bytes(fields: tuple[str, ...], row: dict[str, str], header: bool = False) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    if header:
        writer.writeheader()
    else:
        writer.writerow({field: row[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def jsonl_bytes(fields: tuple[str, ...], row: dict[str, str]) -> bytes:
    value = {field: row[field] for field in fields}
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def initialize(db: sqlite3.Connection, input_path: Path, crawl_state: Path, paths: dict[str, Path]) -> None:
    config = json.dumps(
        {
            "change_id": CHANGE_ID,
            "input": str(input_path),
            "crawl_state": str(crawl_state),
            "outputs": {key: str(value) for key, value in paths.items()},
        },
        sort_keys=True,
    )
    stored = state_get(db, "configuration")
    if stored is not None and stored != config:
        raise RuntimeError("Extractor state belongs to another configuration")
    if stored is not None:
        return
    existing = [path for path in paths.values() if path.exists() and path.stat().st_size]
    if existing:
        raise RuntimeError(f"Non-empty outputs exist without state: {existing}")
    streams = {key: path.open("w+b") for key, path in paths.items()}
    try:
        streams["csv"].write(csv_bytes(SIMPLE_FIELDS, {}, header=True))
        streams["detailed_csv"].write(csv_bytes(DETAILED_FIELDS, {}, header=True))
        for stream in streams.values():
            stream.flush()
            os.fsync(stream.fileno())
        with db:
            state_set(db, "configuration", config)
            state_set(db, "input_offset", 0)
            state_set(db, "records_processed", 0)
            state_set(db, "readmes_processed", 0)
            state_set(db, "edges", 0)
            state_set(db, "finished", 0)
            for key, stream in streams.items():
                state_set(db, f"output_offset_{key}", stream.tell())
    finally:
        for stream in streams.values():
            stream.close()


def open_outputs(db: sqlite3.Connection, paths: dict[str, Path]):
    streams = {key: path.open("r+b") for key, path in paths.items()}
    for key, stream in streams.items():
        committed = int(state_get(db, f"output_offset_{key}") or 0)
        stream.seek(0, os.SEEK_END)
        if stream.tell() < committed:
            raise RuntimeError(f"Output shorter than committed offset: {paths[key]}")
        if stream.tell() > committed:
            stream.truncate(committed)
        stream.seek(committed)
    return streams


def main() -> int:
    args = parse_args()
    if args.poll_seconds <= 0 or args.batch_records < 1:
        raise ValueError("Invalid polling or batch configuration")
    input_path = args.input.expanduser().resolve()
    crawl_state = args.crawl_state.expanduser().resolve()
    state_path = args.state_db.expanduser().resolve()
    directory = args.output_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    paths = output_paths(directory)
    if not input_path.is_file() or not crawl_state.is_file():
        raise FileNotFoundError("Dataset README input or crawler state is missing")
    db = connect(state_path)
    initialize(db, input_path, crawl_state, paths)
    streams = open_outputs(db, paths)
    input_stream = input_path.open("rb")
    try:
        while True:
            input_offset = int(state_get(db, "input_offset") or 0)
            committed = int(crawl_value(crawl_state, "output_offset") or 0)
            crawl_finished = crawl_value(crawl_state, "finished") == "1"
            if input_offset >= committed:
                if crawl_finished:
                    with db:
                        state_set(db, "finished", 1)
                    print("Extraction complete.", flush=True)
                    break
                time.sleep(args.poll_seconds)
                continue
            input_stream.seek(input_offset)
            batch: list[tuple[int, dict]] = []
            while len(batch) < args.batch_records and input_stream.tell() < committed:
                line = input_stream.readline()
                if not line or input_stream.tell() > committed:
                    break
                batch.append((input_stream.tell(), json.loads(line)))
            if not batch:
                time.sleep(args.poll_seconds)
                continue
            records_processed = int(state_get(db, "records_processed") or 0)
            readmes_processed = int(state_get(db, "readmes_processed") or 0)
            edges_count = int(state_get(db, "edges") or 0)
            db.execute("BEGIN IMMEDIATE")
            try:
                for _, record in batch:
                    records_processed += 1
                    markdown = record.get("readme")
                    if record.get("status") != "ok" or not isinstance(markdown, str):
                        continue
                    readmes_processed += 1
                    dataset_id = str(record.get("datasetId") or "").strip()
                    population = str(record.get("population") or "unknown")
                    for repo_key, (target, evidence, confidence) in github_candidates(markdown).items():
                        row = {
                            "source": f"dataset::{dataset_id}",
                            "edge_type": "links_to_github",
                            "target": target,
                            "evidence": evidence,
                            "confidence": confidence,
                            "population": population,
                        }
                        inserted = db.execute(
                            "INSERT OR IGNORE INTO edges(source,repo_key,target,evidence,confidence,population) "
                            "VALUES(?,?,?,?,?,?)",
                            (row["source"], repo_key, target, evidence, confidence, population),
                        ).rowcount
                        if not inserted:
                            continue
                        streams["csv"].write(csv_bytes(SIMPLE_FIELDS, row))
                        streams["jsonl"].write(jsonl_bytes(SIMPLE_FIELDS, row))
                        streams["detailed_csv"].write(csv_bytes(DETAILED_FIELDS, row))
                        streams["detailed_jsonl"].write(jsonl_bytes(DETAILED_FIELDS, row))
                        edges_count += 1
                for stream in streams.values():
                    stream.flush()
                    os.fsync(stream.fileno())
                state_set(db, "input_offset", batch[-1][0])
                state_set(db, "records_processed", records_processed)
                state_set(db, "readmes_processed", readmes_processed)
                state_set(db, "edges", edges_count)
                for key, stream in streams.items():
                    state_set(db, f"output_offset_{key}", stream.tell())
                db.commit()
            except Exception:
                db.rollback()
                raise
            print(
                f"records={records_processed:,} readmes={readmes_processed:,} "
                f"unique_edges={edges_count:,}",
                flush=True,
            )
    finally:
        input_stream.close()
        for stream in streams.values():
            stream.close()
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- build_space_subgraphs.py ----------------------------------------------
SOURCES['build_space_subgraphs'] = r'''#!/usr/bin/env python3
"""Build model-to-Space and dataset-to-Space HuggingGraph subgraphs.

Created: 2026-09-24
Version: v2026.09.24-02
Purpose: Convert Space API relationships, supplemented by reciprocal card
         declarations, into the existing HuggingGraph edge schema.

No existing graph artifact is read as an output or modified. Simple outputs
use ``source,edge_type,target``; detailed outputs additionally preserve
evidence and confidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote, urlparse


CHANGE_ID = "v2026.09.24-02"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SPACE_INPUT = SCRIPT_DIR / "all_space_relationship_metadata_2026Sep24.jsonl"
DEFAULT_MODEL_INPUT = SCRIPT_DIR / "all_model_readme_metadata_2026Aug28.jsonl"
DEFAULT_DATASET_INPUT = SCRIPT_DIR / "all_dataset_readme_metadata_2026Aug28.jsonl"
SIMPLE_FIELDS = ["source", "edge_type", "target"]
DETAILED_FIELDS = SIMPLE_FIELDS + ["evidence", "confidence"]
REPO_ID = re.compile(r"^[^\s/]+(?:/[^\s/]+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Space relationship subgraphs.")
    parser.add_argument("--space-input", type=Path, default=DEFAULT_SPACE_INPUT)
    parser.add_argument("--model-input", type=Path, default=DEFAULT_MODEL_INPUT)
    parser.add_argument("--dataset-input", type=Path, default=DEFAULT_DATASET_INPUT)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    return parser.parse_args()


def normalize_repo_id(value: object, kind: str) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
            "huggingface.co", "www.huggingface.co", "hf.co", "www.hf.co",
        }:
            return None
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if kind == "space":
            if len(parts) < 3 or parts[0].lower() != "spaces":
                return None
            candidate = "/".join(parts[1:3])
        elif kind == "dataset":
            if len(parts) < 3 or parts[0].lower() != "datasets":
                return None
            candidate = "/".join(parts[1:3])
        else:
            if len(parts) < 2 or parts[0].lower() in {"datasets", "spaces"}:
                return None
            candidate = "/".join(parts[:2])
    if candidate.endswith(".git"):
        candidate = candidate[:-4]
    if not REPO_ID.fullmatch(candidate):
        return None
    if kind == "space" and "/" not in candidate:
        return None
    return candidate


def declared_spaces(value: object) -> Iterator[str]:
    values = value if isinstance(value, list) else [value]
    for item in values:
        normalized = normalize_repo_id(item, "space")
        if normalized is not None:
            yield normalized


def connect_edges(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute(
        """
        CREATE TABLE edges(
            source TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            target TEXT NOT NULL,
            api_evidence INTEGER NOT NULL DEFAULT 0,
            card_evidence INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(source, edge_type, target)
        ) WITHOUT ROWID
        """
    )
    return connection


def add_edge(
    connection: sqlite3.Connection,
    source: str,
    edge_type: str,
    target: str,
    evidence: str,
) -> None:
    api = int(evidence.startswith("space_api."))
    card = int(evidence.endswith("_card.spaces"))
    connection.execute(
        """
        INSERT INTO edges(source, edge_type, target, api_evidence, card_evidence)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(source, edge_type, target) DO UPDATE SET
            api_evidence = MAX(api_evidence, excluded.api_evidence),
            card_evidence = MAX(card_evidence, excluded.card_evidence)
        """,
        (source, edge_type, target, api, card),
    )


def load_space_api(connection: sqlite3.Connection, path: Path) -> tuple[int, int]:
    records = invalid = 0
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {line_number}: {exc}") from exc
            space_id = normalize_repo_id(record.get("spaceId"), "space")
            if space_id is None:
                invalid += 1
                continue
            records += 1
            for model in record.get("models") or []:
                model_id = normalize_repo_id(model, "model")
                if model_id is None:
                    invalid += 1
                    continue
                add_edge(connection, f"model::{model_id}", "used_by_space", f"space::{space_id}", "space_api.models")
            for dataset in record.get("datasets") or []:
                dataset_id = normalize_repo_id(dataset, "dataset")
                if dataset_id is None:
                    invalid += 1
                    continue
                add_edge(connection, f"dataset::{dataset_id}", "used_by_space", f"space::{space_id}", "space_api.datasets")
            if records % 10_000 == 0:
                connection.commit()
    connection.commit()
    return records, invalid


def load_card_declarations(
    connection: sqlite3.Connection,
    path: Path,
    id_field: str,
    prefix: str,
) -> tuple[int, int]:
    accepted = invalid = 0
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {line_number}: {exc}") from exc
            repo_id = normalize_repo_id(record.get(id_field), prefix)
            metadata = record.get("readme_metadata")
            if repo_id is None or not isinstance(metadata, dict) or "spaces" not in metadata:
                continue
            raw = metadata.get("spaces")
            normalized = list(declared_spaces(raw))
            if raw not in (None, False, "") and not normalized:
                invalid += 1
            for space_id in normalized:
                add_edge(
                    connection,
                    f"{prefix}::{repo_id}",
                    "used_by_space",
                    f"space::{space_id}",
                    f"{prefix}_card.spaces",
                )
                accepted += 1
            if accepted and accepted % 10_000 == 0:
                connection.commit()
    connection.commit()
    return accepted, invalid


def output_paths(output_dir: Path, prefix: str) -> tuple[Path, Path, Path, Path]:
    return (
        output_dir / f"{prefix}_edges.csv",
        output_dir / f"{prefix}_edges.jsonl",
        output_dir / f"{prefix}_edges_detailed.csv",
        output_dir / f"{prefix}_edges_detailed.jsonl",
    )


def evidence_and_confidence(api: int, card: int, kind: str) -> tuple[str, str]:
    if api and card:
        return f"space_api.{kind}s;{kind}_card.spaces", "corroborated"
    if api:
        return f"space_api.{kind}s", "platform_linked"
    return f"{kind}_card.spaces", "declared"


def export_family(
    connection: sqlite3.Connection, output_dir: Path, kind: str
) -> int:
    prefix = f"{kind}_space"
    paths = output_paths(output_dir, prefix)
    existing = [path for path in paths if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite:\n" + "\n".join(map(str, existing)))
    count = 0
    with (
        paths[0].open("x", newline="", encoding="utf-8") as simple_csv,
        paths[1].open("x", encoding="utf-8") as simple_jsonl,
        paths[2].open("x", newline="", encoding="utf-8") as detailed_csv,
        paths[3].open("x", encoding="utf-8") as detailed_jsonl,
    ):
        simple_writer = csv.DictWriter(simple_csv, fieldnames=SIMPLE_FIELDS)
        detailed_writer = csv.DictWriter(detailed_csv, fieldnames=DETAILED_FIELDS)
        simple_writer.writeheader()
        detailed_writer.writeheader()
        rows = connection.execute(
            """
            SELECT source, edge_type, target, api_evidence, card_evidence
            FROM edges WHERE source LIKE ? ORDER BY source, target
            """,
            (f"{kind}::%",),
        )
        for source, edge_type, target, api, card in rows:
            simple = {"source": source, "edge_type": edge_type, "target": target}
            evidence, confidence = evidence_and_confidence(api, card, kind)
            detailed = {**simple, "evidence": evidence, "confidence": confidence}
            simple_writer.writerow(simple)
            detailed_writer.writerow(detailed)
            simple_jsonl.write(json.dumps(simple, ensure_ascii=False, separators=(",", ":")) + "\n")
            detailed_jsonl.write(json.dumps(detailed, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    space_input = args.space_input.expanduser().resolve()
    model_input = args.model_input.expanduser().resolve()
    dataset_input = args.dataset_input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    for path in (space_input, model_input, dataset_input):
        if not path.is_file():
            raise FileNotFoundError(path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="hugginggraph-space-edges-") as temp_dir:
        connection = connect_edges(Path(temp_dir) / "edges.sqlite3")
        spaces, api_invalid = load_space_api(connection, space_input)
        model_declared, model_invalid = load_card_declarations(
            connection, model_input, "modelId", "model"
        )
        dataset_declared, dataset_invalid = load_card_declarations(
            connection, dataset_input, "datasetId", "dataset"
        )
        model_edges = export_family(connection, output_dir, "model")
        dataset_edges = export_family(connection, output_dir, "dataset")
        connection.close()

    print(f"Space records:             {spaces:12,}")
    print(f"Model-Space edges:         {model_edges:12,}")
    print(f"Dataset-Space edges:       {dataset_edges:12,}")
    print(f"Model-card declarations:   {model_declared:12,}")
    print(f"Dataset-card declarations: {dataset_declared:12,}")
    print(f"Rejected values:           {api_invalid + model_invalid + dataset_invalid:12,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- extract_space_github_edges_streaming_full.py --------------------------
SOURCES['extract_space_github_edges_streaming_full'] = r'''#!/usr/bin/env python3
"""Stream Space-GitHub edges from the full Space README crawl.

Created: 2026-09-28
Version: v2026.09.28-04
Purpose: Add README-body Space-GitHub evidence with canonical URL targets.

Change history:
2026-09-30 v2026.09.30-01
- Replaced embedded NUL characters before persisting edge text so CSV output
  remains serializable during checkpointed extraction.
- Backup: extract_space_github_edges_streaming_full.py.bak.20260930-173616
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import time
from pathlib import Path

from extract_model_github_edges_streaming import github_candidates


CHANGE_ID = "v2026.09.28-04"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_space_readmes_full_2026Sep28.jsonl"
DEFAULT_CRAWL_STATE = SCRIPT_DIR / "all_space_readmes_full_2026Sep28.jsonl.state.sqlite3"
DEFAULT_STATE = SCRIPT_DIR / "space_github_edges_full.state.sqlite3"
SIMPLE_FIELDS = ("source", "edge_type", "target")
DETAILED_FIELDS = SIMPLE_FIELDS + ("evidence", "confidence", "population")


def clean_text(value: object) -> str:
    """Return text that is safe and consistent across SQLite, CSV, and JSONL."""
    return str(value).replace("\x00", " ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream full-crawl Space-GitHub extraction.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--crawl-state", type=Path, default=DEFAULT_CRAWL_STATE)
    p.add_argument("--state-db", type=Path, default=DEFAULT_STATE)
    p.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    p.add_argument("--poll-seconds", type=float, default=10.0)
    p.add_argument("--batch-records", type=int, default=1_000)
    return p.parse_args()


def output_paths(directory: Path) -> dict[str, Path]:
    return {
        "csv": directory / "space_github_edges_full.csv",
        "jsonl": directory / "space_github_edges_full.jsonl",
        "detailed_csv": directory / "space_github_edges_full_detailed.csv",
        "detailed_jsonl": directory / "space_github_edges_full_detailed.jsonl",
    }


def state_get(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def state_set(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute(
        "INSERT INTO state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS edges("
        "source TEXT NOT NULL,repo_key TEXT NOT NULL,target TEXT NOT NULL,evidence TEXT NOT NULL,"
        "confidence TEXT NOT NULL,population TEXT NOT NULL,PRIMARY KEY(source,repo_key))"
    )
    db.commit()
    return db


def crawl_value(path: Path, key: str) -> str | None:
    db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=60)
    try:
        row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])
    finally:
        db.close()


def initialize(db: sqlite3.Connection, input_path: Path, crawl_state: Path, paths: dict[str, Path]) -> None:
    config = json.dumps(
        {"change_id": CHANGE_ID, "input": str(input_path), "crawl_state": str(crawl_state),
         "outputs": {key: str(value) for key, value in paths.items()}},
        sort_keys=True,
    )
    stored = state_get(db, "configuration")
    if stored is not None and stored != config:
        raise RuntimeError("Extractor state belongs to another configuration")
    if stored is not None:
        return
    existing = [path for path in paths.values() if path.exists() and path.stat().st_size]
    if existing:
        raise RuntimeError(f"Non-empty outputs exist without state: {existing}")
    streams = {key: path.open("w", newline="" if "csv" in key else None, encoding="utf-8") for key, path in paths.items()}
    try:
        csv.DictWriter(streams["csv"], fieldnames=SIMPLE_FIELDS).writeheader()
        csv.DictWriter(streams["detailed_csv"], fieldnames=DETAILED_FIELDS).writeheader()
        for stream in streams.values():
            stream.flush(); os.fsync(stream.fileno())
        with db:
            state_set(db, "configuration", config); state_set(db, "input_offset", 0)
            state_set(db, "records_processed", 0); state_set(db, "readmes_processed", 0)
            state_set(db, "edges", 0); state_set(db, "finished", 0)
            for key, stream in streams.items(): state_set(db, f"output_offset_{key}", stream.tell())
    finally:
        for stream in streams.values(): stream.close()


def open_outputs(db: sqlite3.Connection, paths: dict[str, Path]):
    streams = {key: path.open("r+", newline="" if "csv" in key else None, encoding="utf-8") for key, path in paths.items()}
    for key, stream in streams.items():
        committed = int(state_get(db, f"output_offset_{key}") or 0)
        stream.seek(0, os.SEEK_END)
        if stream.tell() < committed: raise RuntimeError(f"Output shorter than state: {paths[key]}")
        if stream.tell() > committed: stream.truncate(committed)
        stream.seek(committed)
    return streams


def main() -> int:
    args = parse_args()
    input_path=args.input.expanduser().resolve(); crawl_state=args.crawl_state.expanduser().resolve()
    state_path=args.state_db.expanduser().resolve(); directory=args.output_dir.expanduser().resolve()
    if args.poll_seconds <= 0 or args.batch_records < 1: raise ValueError("Invalid arguments")
    if not input_path.is_file() or not crawl_state.is_file(): raise FileNotFoundError("Crawl input/state missing")
    directory.mkdir(parents=True,exist_ok=True); paths=output_paths(directory); db=connect(state_path)
    initialize(db,input_path,crawl_state,paths); streams=open_outputs(db,paths); raw=input_path.open("rb")
    csv_writer=csv.DictWriter(streams["csv"],fieldnames=SIMPLE_FIELDS,lineterminator="\n")
    detailed_writer=csv.DictWriter(streams["detailed_csv"],fieldnames=DETAILED_FIELDS,lineterminator="\n")
    try:
        while True:
            offset=int(state_get(db,"input_offset") or 0); committed=int(crawl_value(crawl_state,"output_offset") or 0)
            finished=crawl_value(crawl_state,"finished")=="1"
            if offset>=committed:
                if finished:
                    with db: state_set(db,"finished",1)
                    print("Extraction complete.",flush=True); break
                time.sleep(args.poll_seconds); continue
            raw.seek(offset); batch=[]
            while len(batch)<args.batch_records and raw.tell()<committed:
                line=raw.readline()
                if not line or raw.tell()>committed: break
                batch.append((raw.tell(),json.loads(line)))
            if not batch: time.sleep(args.poll_seconds); continue
            records=int(state_get(db,"records_processed") or 0); readmes=int(state_get(db,"readmes_processed") or 0); edges=int(state_get(db,"edges") or 0)
            db.execute("BEGIN IMMEDIATE")
            try:
                for _,record in batch:
                    records+=1; markdown=record.get("readme")
                    if record.get("status")!="ok" or not isinstance(markdown,str): continue
                    readmes+=1; space_id=clean_text(record.get("spaceId") or record.get("datasetId") or "").strip()
                    population=clean_text(record.get("population") or "unknown")
                    for repo_key,(target,evidence,confidence) in github_candidates(markdown).items():
                        repo_key=clean_text(repo_key); target=clean_text(target)
                        evidence=clean_text(evidence); confidence=clean_text(confidence)
                        source=f"space::{space_id}"
                        inserted=db.execute(
                            "INSERT OR IGNORE INTO edges(source,repo_key,target,evidence,confidence,population) VALUES(?,?,?,?,?,?)",
                            (source,repo_key,target,evidence,confidence,population),
                        ).rowcount
                        if not inserted: continue
                        simple={"source":source,"edge_type":"links_to_github","target":target}
                        detailed={**simple,"evidence":evidence,"confidence":confidence,"population":population}
                        csv_writer.writerow(simple); detailed_writer.writerow(detailed)
                        streams["jsonl"].write(json.dumps(simple,ensure_ascii=False,separators=(",",":"))+"\n")
                        streams["detailed_jsonl"].write(json.dumps(detailed,ensure_ascii=False,separators=(",",":"))+"\n")
                        edges+=1
                for stream in streams.values(): stream.flush(); os.fsync(stream.fileno())
                state_set(db,"input_offset",batch[-1][0]); state_set(db,"records_processed",records)
                state_set(db,"readmes_processed",readmes); state_set(db,"edges",edges)
                for key,stream in streams.items(): state_set(db,f"output_offset_{key}",stream.tell())
                db.commit()
            except Exception:
                db.rollback(); raise
            print(f"records={records:,} readmes={readmes:,} unique_edges={edges:,}",flush=True)
    finally:
        raw.close()
        for stream in streams.values(): stream.close()
        db.close()
    return 0


if __name__=="__main__": raise SystemExit(main())
'''

# --- build_space_license_task_agent_subgraphs.py ---------------------------
SOURCES['build_space_license_task_agent_subgraphs'] = r'''#!/usr/bin/env python3
"""Build Space-license, Space-task, and Space-agent-framework subgraphs.

Created: 2026-09-24
Version: v2026.09.24-01
Purpose: Convert explicit Space-card attributes into graph-ready relationship
         files while reusing HuggingGraph license/task normalization.

The builder creates new artifacts only. Generic agent category tags map to
``task::agents``; only recognized framework tags create ``agent::`` nodes.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from model_license_task_github_edges import candidate_licenses, candidate_tasks


CHANGE_ID = "v2026.09.24-01"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "all_space_card_metadata_2026Sep24.jsonl"
SIMPLE_FIELDS = ["source", "edge_type", "target"]
DETAILED_FIELDS = SIMPLE_FIELDS + ["evidence", "confidence"]

AGENT_CATEGORY_TAGS = {
    "agent", "agents", "ai-agent", "ai-agents", "agentic", "agentic-ai",
    "multi-agent", "smolagent", "smolagents", "langchain", "langgraph",
    "crewai", "llamaindex", "llama-index", "pydantic-ai", "autogen",
    "haystack", "google-adk", "agno", "openai-agents", "openai-agents-sdk",
}

AGENT_FRAMEWORK_ALIASES = {
    "smolagent": "smolagents",
    "smolagents": "smolagents",
    "langchain": "langchain",
    "langgraph": "langgraph",
    "crewai": "crewai",
    "llamaindex": "llamaindex",
    "llama-index": "llamaindex",
    "pydantic-ai": "pydantic-ai",
    "autogen": "autogen",
    "haystack": "haystack",
    "google-adk": "google-adk",
    "agno": "agno",
    "openai-agents": "openai-agents",
    "openai-agents-sdk": "openai-agents",
}

FAMILIES = {
    "license": ("has_license", "license::"),
    "task": ("supports_task", "task::"),
    "agent": ("uses_agent_framework", "agent::"),
}

CONFIDENCE_PRIORITY = {
    "declared": 0,
    "declared_nonstandard": 1,
    "tag_association": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Space license, task, and agent-framework subgraphs."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    return parser.parse_args()


def string_tags(metadata: dict) -> set[str]:
    value = metadata.get("tags")
    values = value if isinstance(value, (list, tuple)) else [value]
    return {
        item.strip().lower()
        for item in values
        if isinstance(item, str) and item.strip()
    }


def agent_candidates(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = {}
    for tag in string_tags(metadata):
        framework = AGENT_FRAMEWORK_ALIASES.get(tag)
        if framework is not None:
            candidates[framework] = ("tags", "tag_association")
    return candidates


def task_candidates(metadata: dict) -> dict[str, tuple[str, str]]:
    candidates = candidate_tasks(metadata)
    tags = string_tags(metadata)
    if tags & AGENT_CATEGORY_TAGS:
        existing = candidates.get("agents")
        proposed = ("tags", "tag_association")
        if existing is None or CONFIDENCE_PRIORITY.get(proposed[1], 99) < CONFIDENCE_PRIORITY.get(existing[1], 99):
            candidates["agents"] = proposed
    return candidates


def output_paths(output_dir: Path, family: str) -> dict[str, Path]:
    stem = f"space_{family}_edges"
    return {
        "csv": output_dir / f"{stem}.csv",
        "jsonl": output_dir / f"{stem}.jsonl",
        "detailed_csv": output_dir / f"{stem}_detailed.csv",
        "detailed_jsonl": output_dir / f"{stem}_detailed.jsonl",
    }


def emit_family(
    output_dir: Path,
    family: str,
    edges: dict[tuple[str, str, str], tuple[str, str]],
) -> None:
    paths = output_paths(output_dir, family)
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite:\n" + "\n".join(map(str, existing)))
    with (
        paths["csv"].open("x", newline="", encoding="utf-8") as csv_file,
        paths["jsonl"].open("x", encoding="utf-8") as jsonl_file,
        paths["detailed_csv"].open("x", newline="", encoding="utf-8") as detailed_csv,
        paths["detailed_jsonl"].open("x", encoding="utf-8") as detailed_jsonl,
    ):
        writer = csv.DictWriter(csv_file, fieldnames=SIMPLE_FIELDS)
        detailed_writer = csv.DictWriter(detailed_csv, fieldnames=DETAILED_FIELDS)
        writer.writeheader()
        detailed_writer.writeheader()
        for key in sorted(edges):
            source, edge_type, target = key
            evidence, confidence = edges[key]
            simple = {"source": source, "edge_type": edge_type, "target": target}
            detailed = {**simple, "evidence": evidence, "confidence": confidence}
            writer.writerow(simple)
            detailed_writer.writerow(detailed)
            jsonl_file.write(json.dumps(simple, ensure_ascii=False, separators=(",", ":")) + "\n")
            detailed_jsonl.write(json.dumps(detailed, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    for family in FAMILIES:
        existing = [p for p in output_paths(output_dir, family).values() if p.exists()]
        if existing:
            raise FileExistsError("Refusing to overwrite:\n" + "\n".join(map(str, existing)))

    edges: dict[str, dict[tuple[str, str, str], tuple[str, str]]] = {
        family: {} for family in FAMILIES
    }
    records = metadata_records = invalid = 0
    with input_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON line {line_number}: {exc}") from exc
            records += 1
            space_id = record.get("spaceId")
            metadata = record.get("card_metadata")
            if not isinstance(space_id, str) or not space_id.strip():
                invalid += 1
                continue
            if not isinstance(metadata, dict) or not metadata:
                continue
            metadata_records += 1
            source = f"space::{space_id.strip()}"
            candidates_by_family = {
                "license": candidate_licenses(metadata),
                "task": task_candidates(metadata),
                "agent": agent_candidates(metadata),
            }
            for family, candidates in candidates_by_family.items():
                edge_type, target_prefix = FAMILIES[family]
                for value, detail in candidates.items():
                    key = (source, edge_type, f"{target_prefix}{value}")
                    previous = edges[family].get(key)
                    if previous is None or CONFIDENCE_PRIORITY.get(detail[1], 99) < CONFIDENCE_PRIORITY.get(previous[1], 99):
                        edges[family][key] = detail

    for family in FAMILIES:
        emit_family(output_dir, family, edges[family])

    print(f"Space records:          {records:12,}")
    print(f"Cards with metadata:    {metadata_records:12,}")
    for family in FAMILIES:
        sources = {edge[0] for edge in edges[family]}
        targets = {edge[2] for edge in edges[family]}
        print(f"Space-{family} edges:   {len(edges[family]):12,}")
        print(f"  source Spaces:        {len(sources):12,}")
        print(f"  target nodes:         {len(targets):12,}")
    print(f"Invalid Space records:  {invalid:12,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- audit_dataset_subgraphs.py --------------------------------------------
SOURCES['audit_dataset_subgraphs'] = r'''#!/usr/bin/env python3
"""Audit and package five Dataset-centered HuggingGraph subgraphs.

Created: 2026-10-02
Version: v2026.10.02-02
Purpose: Reproduce declared Dataset attributes, canonicalize Dataset-GitHub
         links, preserve Dataset-Dataset candidate tiers, and create validation
         evidence without modifying existing graph files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path


CHANGE_ID = "v2026.10.02-02"
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT))

from model_dataset_attribute_edges import DATASET_EXTRACTORS, RELATIONS  # noqa: E402


RELATION_CONFIG = {
    "library": {
        "baseline": ROOT / "hugginggraph_v3_2026Sep30/edges/05_dataset_library_edges.csv",
        "edge_name": "dataset_library_declared_edges.csv",
        "evidence_name": "dataset_library_declared_evidence.csv",
    },
    "license": {
        "baseline": ROOT / "hugginggraph_v3_2026Sep30/edges/07_dataset_license_edges.csv",
        "edge_name": "dataset_license_declared_edges.csv",
        "evidence_name": "dataset_license_declared_evidence.csv",
    },
    "task": {
        "baseline": ROOT / "hugginggraph_v3_2026Sep30/edges/09_dataset_task_edges.csv",
        "edge_name": "dataset_task_declared_edges.csv",
        "evidence_name": "dataset_task_declared_evidence.csv",
    },
}

SIMPLE_FIELDS = ["source", "edge_type", "target"]
EVIDENCE_FIELDS = SIMPLE_FIELDS + ["evidence", "confidence", "snapshot_status"]
GITHUB_EVIDENCE_FIELDS = SIMPLE_FIELDS + [
    "original_target", "evidence", "confidence", "population",
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "all_dataset_readme_metadata_2026Aug28.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "results")
    return parser.parse_args()


def atomic_csv(path: Path, fields, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_simple(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != SIMPLE_FIELDS:
            raise ValueError(f"Unexpected schema in {path}: {reader.fieldnames}")
        return {(row["source"], row["edge_type"], row["target"]) for row in reader}


def graph_stats(edges):
    sources = {edge[0] for edge in edges}
    targets = {edge[2] for edge in edges}
    return {
        "edges": len(edges),
        "source_nodes": len(sources),
        "target_nodes": len(targets),
        "nodes": len(sources | targets),
    }


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_github(value: str):
    prefix = "https://github.com/"
    if not value.lower().startswith(prefix):
        raise ValueError(f"Non-canonical GitHub target: {value}")
    parts = value[len(prefix):].strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid GitHub repository target: {value}")
    return prefix + parts[0].lower() + "/" + parts[1].lower()


def validation_sample(rows, fields, group_fields, seed=20261002, per_group=100):
    groups = defaultdict(list)
    for row in rows:
        group = "|".join(row[field] for field in group_fields)
        groups[group].append(row)
    rng = random.Random(seed)
    output = []
    for group in sorted(groups):
        candidates = groups[group]
        chosen = candidates if len(candidates) <= per_group else rng.sample(candidates, per_group)
        for row in sorted(chosen, key=lambda item: tuple(item[field] for field in fields)):
            output.append({
                **row,
                "sample_group": group,
                "manual_label": "",
                "review_notes": "",
            })
    return output


def copy_new(source: Path, target: Path):
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite: {target}")
    shutil.copyfile(source, target)


def main():
    args = parse_args()
    metadata_path = args.metadata.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")

    edge_sets = {relation: set() for relation in RELATION_CONFIG}
    evidence_rows = {relation: [] for relation in RELATION_CONFIG}
    status_counts = Counter()
    records = 0
    with_metadata = 0

    with metadata_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            records += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {metadata_path}:{line_number}") from exc
            status = str(record.get("status") or "unknown")
            status_counts[status] += 1
            dataset_id = record.get("datasetId")
            metadata = record.get("readme_metadata")
            if not isinstance(dataset_id, str) or not dataset_id.strip():
                continue
            if not isinstance(metadata, dict) or not metadata:
                continue
            with_metadata += 1
            source = "dataset::" + dataset_id.strip()
            for relation in RELATION_CONFIG:
                config = RELATIONS[relation]
                for target, (evidence, confidence) in DATASET_EXTRACTORS[relation](metadata).items():
                    edge = (
                        source,
                        config["dataset_edge_type"],
                        config["target_prefix"] + target,
                    )
                    edge_sets[relation].add(edge)
                    evidence_rows[relation].append(dict(zip(
                        EVIDENCE_FIELDS,
                        (*edge, evidence, confidence, status),
                    )))

    summary = {
        "change_id": CHANGE_ID,
        "snapshot": {
            "metadata_path": str(metadata_path),
            "metadata_sha256": file_sha256(metadata_path),
            "records": records,
            "records_with_metadata": with_metadata,
            "status_counts": dict(status_counts),
        },
        "subgraphs": {},
        "verification": {},
        "outputs": {},
    }

    for relation, config in RELATION_CONFIG.items():
        baseline = read_simple(config["baseline"])
        generated = edge_sets[relation]
        if generated != baseline:
            raise RuntimeError(
                f"{relation} mismatch: missing={len(generated - baseline)}, "
                f"extra={len(baseline - generated)}"
            )
        edge_path = output_dir / config["edge_name"]
        evidence_path = output_dir / config["evidence_name"]
        sample_path = output_dir / f"dataset_{relation}_validation_sample.csv"
        atomic_csv(edge_path, SIMPLE_FIELDS, [
            dict(zip(SIMPLE_FIELDS, edge)) for edge in sorted(generated)
        ])
        ordered_evidence = sorted(
            evidence_rows[relation],
            key=lambda row: tuple(row[field] for field in EVIDENCE_FIELDS),
        )
        atomic_csv(evidence_path, EVIDENCE_FIELDS, ordered_evidence)
        sample = validation_sample(
            ordered_evidence, EVIDENCE_FIELDS, ("confidence",), per_group=100
        )
        atomic_csv(
            sample_path,
            EVIDENCE_FIELDS + ["sample_group", "manual_label", "review_notes"],
            sample,
        )
        confidence = Counter(row["confidence"] for row in ordered_evidence)
        evidence = Counter(row["evidence"] for row in ordered_evidence)
        summary["subgraphs"][relation] = {
            **graph_stats(generated),
            "confidence": dict(confidence),
            "top_evidence": evidence.most_common(25),
            "validation_sample_rows": len(sample),
        }
        summary["verification"][relation] = {
            "reproduced_exactly": True,
            "baseline_edges": len(baseline),
            "missing": 0,
            "extra": 0,
            "duplicates": 0,
        }
        summary["outputs"][relation] = {
            "edges": edge_path.name,
            "evidence": evidence_path.name,
            "validation_sample": sample_path.name,
        }

    github_simple = ROOT / "dataset_github_edges_full.csv"
    github_detailed = ROOT / "dataset_github_edges_full_detailed.csv"
    baseline_github = read_simple(github_simple)
    canonical_edges = set()
    github_evidence = []
    with github_detailed.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        expected = SIMPLE_FIELDS + ["evidence", "confidence", "population"]
        if reader.fieldnames != expected:
            raise ValueError(f"Unexpected schema in {github_detailed}: {reader.fieldnames}")
        for row in reader:
            canonical = canonical_github(row["target"])
            edge = (row["source"], row["edge_type"], canonical)
            canonical_edges.add(edge)
            github_evidence.append({
                "source": row["source"],
                "edge_type": row["edge_type"],
                "target": canonical,
                "original_target": row["target"],
                "evidence": row["evidence"],
                "confidence": row["confidence"],
                "population": row["population"],
            })
    canonical_baseline = {
        (source, edge_type, canonical_github(target))
        for source, edge_type, target in baseline_github
    }
    if canonical_edges != canonical_baseline:
        raise RuntimeError("Detailed and simple Dataset-GitHub projections differ")
    github_edge_path = output_dir / "dataset_github_readme_edges.csv"
    github_evidence_path = output_dir / "dataset_github_readme_evidence.csv"
    github_sample_path = output_dir / "dataset_github_validation_sample.csv"
    atomic_csv(github_edge_path, SIMPLE_FIELDS, [
        dict(zip(SIMPLE_FIELDS, edge)) for edge in sorted(canonical_edges)
    ])
    github_evidence.sort(key=lambda row: tuple(row[field] for field in GITHUB_EVIDENCE_FIELDS))
    atomic_csv(github_evidence_path, GITHUB_EVIDENCE_FIELDS, github_evidence)
    github_sample = validation_sample(
        github_evidence, GITHUB_EVIDENCE_FIELDS, ("confidence",), per_group=100
    )
    atomic_csv(
        github_sample_path,
        GITHUB_EVIDENCE_FIELDS + ["sample_group", "manual_label", "review_notes"],
        github_sample,
    )
    github_stats = graph_stats(canonical_edges)
    github_stats.update({
        "repository_nodes_case_insensitive": len({edge[2] for edge in canonical_edges}),
        "confidence": dict(Counter(row["confidence"] for row in github_evidence)),
        "population": dict(Counter(row["population"] for row in github_evidence)),
        "validation_sample_rows": len(github_sample),
    })
    summary["subgraphs"]["github"] = github_stats
    summary["verification"]["github"] = {
        "simple_detailed_projection_exact": True,
        "baseline_edges": len(baseline_github),
        "canonical_edges": len(canonical_edges),
        "missing": 0,
        "extra": 0,
        "duplicates": 0,
    }
    summary["outputs"]["github"] = {
        "edges": github_edge_path.name,
        "evidence": github_evidence_path.name,
        "validation_sample": github_sample_path.name,
    }

    dataset_dataset_sources = {
        "official_metadata": ROOT / "dataset_dataset_edges_max_coverage.csv",
        "refined_lineage": ROOT / (
            "dataset_dataset_extended_2026Oct02/refined_v3/"
            "dataset_lineage_high_confidence_edges.csv"
        ),
        "candidate_union": ROOT / (
            "dataset_dataset_extended_2026Oct02/refined_v3/"
            "dataset_dataset_expanded_union_pairs.csv"
        ),
        "validation_sample": ROOT / (
            "dataset_dataset_extended_2026Oct02/refined_v3/"
            "validation_sample_lineage.csv"
        ),
    }
    copied = {}
    for label, source in dataset_dataset_sources.items():
        target = output_dir / f"dataset_dataset_{label}.csv"
        copy_new(source, target)
        copied[label] = target.name
    official = read_simple(dataset_dataset_sources["official_metadata"])
    with dataset_dataset_sources["refined_lineage"].open(newline="", encoding="utf-8") as stream:
        refined_rows = list(csv.DictReader(stream))
    refined_typed = {
        (row["source"], row["edge_type"], row["target"])
        for row in refined_rows
    }
    refined_pairs = {(edge[0], edge[2]) for edge in refined_typed}
    official_pairs = {(edge[0], edge[2]) for edge in official}
    union_pairs = official_pairs | refined_pairs
    summary["subgraphs"]["dataset_dataset"] = {
        "official_metadata": graph_stats(official),
        "refined_typed_edges": len(refined_typed),
        "refined_pairs": len(refined_pairs),
        "refined_nodes": len({node for pair in refined_pairs for node in pair}),
        "pair_overlap": len(official_pairs & refined_pairs),
        "new_refined_pairs": len(refined_pairs - official_pairs),
        "candidate_union_pairs": len(union_pairs),
        "candidate_union_nodes": len({node for pair in union_pairs for node in pair}),
        "publication_status": "requires_manual_validation",
    }
    summary["verification"]["dataset_dataset"] = {
        "official_metadata_reproduced_in_prior_evidence_audit": True,
        "official_edges": len(official),
        "validation_sample_rows": 600,
    }
    summary["outputs"]["dataset_dataset"] = copied

    summary_path = output_dir / "summary.json"
    with summary_path.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")

    manifest_rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            manifest_rows.append({
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            })
    atomic_csv(output_dir / "manifest.csv", ["file", "bytes", "sha256"], manifest_rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- prepare_hugginggraph_v3_edges.py --------------------------------------
SOURCES['prepare_hugginggraph_v3_edges'] = r'''#!/usr/bin/env python3
"""Prepare normalized, count-verified edge inputs for HuggingGraph v3.

Created: 2026-09-30
Version: v2026.10.02-04
Purpose: Reconcile the latest Space population, normalize all GitHub nodes,
         and prepare the October 2, 2026 Dataset relationship inputs.

Change history:
- 2026-10-02 v2026.10.02-04: updated Dataset relationship counts for the
  October 2 v3 release.
  Backup: prepare_hugginggraph_v3_edges.py.bak.20261002-200822
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import HfApi


FIELDS = ["source", "edge_type", "target"]
CORE_FILES = (
    ("01_model_model_edges.csv", "model", "model", 966_035),
    ("02_model_dataset_edges.csv", "dataset", "model", 362_064),
    ("03_dataset_dataset_edges.csv", "dataset", "dataset", 12_541),
    ("04_model_library_edges.csv", "model", "library", 1_311_386),
    ("05_dataset_library_edges.csv", "dataset", "library", 16_864),
    ("06_model_license_edges.csv", "model", "license", 1_090_845),
    ("07_dataset_license_edges.csv", "dataset", "license", 331_317),
    ("08_model_task_edges.csv", "model", "task", 577_077),
    ("09_dataset_task_edges.csv", "dataset", "task", 317_412),
)
EXPECTED_UNAVAILABLE = {
    "Gpo128482owppw/exppo-vision",
    "sumabfron/Crumble",
    "tostido/K-os",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-edge-dir", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def typed(value: str, kind: str) -> str:
    prefix = f"{kind}::"
    return value if value.startswith(prefix) else prefix + value


def open_writer(path: Path):
    stream = path.open("x", newline="", encoding="utf-8")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    return stream, writer


def copy_core(source: Path, destination: Path, source_type: str, target_type: str) -> int:
    count = 0
    output, writer = open_writer(destination)
    try:
        with source.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"Unexpected schema in {source}: {reader.fieldnames}")
            for row in reader:
                writer.writerow(
                    {
                        "source": typed(row["source"], source_type),
                        "edge_type": row["edge_type"],
                        "target": typed(row["target"], target_type),
                    }
                )
                count += 1
    finally:
        output.close()
    return count


def write_github(db_path: Path, destination: Path) -> int:
    count = 0
    output, writer = open_writer(destination)
    db = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        for source, repo_key in db.execute(
            "SELECT source,repo_key FROM edges ORDER BY source,repo_key"
        ):
            writer.writerow(
                {
                    "source": source,
                    "edge_type": "links_to_github",
                    "target": f"https://github.com/{repo_key}",
                }
            )
            count += 1
    finally:
        db.close()
        output.close()
    return count


def read_ids(path: Path) -> set[str]:
    result: set[str] = set()
    with path.open(encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue
            record = json.loads(line)
            result.add(str(record.get("spaceId") or "").strip())
    return result


def fetch_space(space_id: str):
    try:
        info = HfApi().space_info(
            space_id, expand=["models", "datasets"], timeout=30
        )
        return space_id, list(info.models or []), list(info.datasets or []), None
    except Exception as exc:  # API status is reported and checked below.
        return space_id, [], [], type(exc).__name__


def reconcile_space_edges(workspace: Path, workers: int):
    relationship_ids = read_ids(workspace / "all_space_relationship_metadata_2026Sep24.jsonl")
    card_ids = read_ids(workspace / "all_space_card_metadata_2026Sep24.jsonl")
    obsolete_targets = {f"space::{space_id}" for space_id in relationship_ids - card_ids}

    model_edges: set[tuple[str, str, str]] = set()
    dataset_edges: set[tuple[str, str, str]] = set()
    for filename, output in (
        ("model_space_edges.csv", model_edges),
        ("dataset_space_edges.csv", dataset_edges),
    ):
        with (workspace / filename).open(newline="", encoding="utf-8") as input_file:
            for row in csv.DictReader(input_file):
                if row["target"] not in obsolete_targets:
                    output.add((row["source"], row["edge_type"], row["target"]))

    unavailable: set[str] = set()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_space, space_id) for space_id in card_ids - relationship_ids]
        for future in as_completed(futures):
            space_id, model_ids, dataset_ids, error = future.result()
            if error is not None:
                unavailable.add(space_id)
                continue
            target = f"space::{space_id}"
            model_edges.update(
                (f"model::{model_id}", "used_by_space", target) for model_id in model_ids
            )
            dataset_edges.update(
                (f"dataset::{dataset_id}", "used_by_space", target)
                for dataset_id in dataset_ids
            )

    if unavailable != EXPECTED_UNAVAILABLE:
        raise RuntimeError(
            f"Unexpected unavailable Space set: {sorted(unavailable)}; "
            f"expected {sorted(EXPECTED_UNAVAILABLE)}"
        )
    return model_edges, dataset_edges, unavailable


def write_edge_set(path: Path, edges: set[tuple[str, str, str]]) -> int:
    output, writer = open_writer(path)
    try:
        for source, edge_type, target in sorted(edges):
            writer.writerow({"source": source, "edge_type": edge_type, "target": target})
    finally:
        output.close()
    return len(edges)


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    core = args.core_edge_dir.expanduser().resolve()
    workspace = args.workspace_dir.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)

    for filename, source_type, target_type, expected in CORE_FILES:
        actual = copy_core(core / filename, output / filename, source_type, target_type)
        if actual != expected:
            raise ValueError(f"Unexpected {filename} count: {actual:,} != {expected:,}")

    for filename, state_name, expected in (
        ("10_model_github_edges.csv", "model_github_edges_full.state.sqlite3", 962_855),
        ("11_dataset_github_edges.csv", "dataset_github_edges_full.state.sqlite3", 188_888),
        ("14_space_github_edges.csv", "space_github_edges_full.state.sqlite3", 113_755),
    ):
        actual = write_github(workspace / state_name, output / filename)
        if actual != expected:
            raise ValueError(f"Unexpected {filename} count: {actual:,} != {expected:,}")

    model_edges, dataset_edges, unavailable = reconcile_space_edges(
        workspace, args.workers
    )
    for filename, edges, expected in (
        ("12_model_space_edges.csv", model_edges, 941_121),
        ("13_dataset_space_edges.csv", dataset_edges, 83_061),
    ):
        actual = write_edge_set(output / filename, edges)
        if actual != expected:
            raise ValueError(f"Unexpected {filename} count: {actual:,} != {expected:,}")

    for source_name, destination_name, source_type, target_type, expected in (
        ("space_license_edges.csv", "15_space_license_edges.csv", "space", "license", 420_369),
        ("space_task_edges.csv", "16_space_task_edges.csv", "space", "task", 43_223),
        ("space_agent_edges.csv", "17_space_agent_edges.csv", "space", "agent", 37_059),
    ):
        actual = copy_core(
            workspace / source_name,
            output / destination_name,
            source_type,
            target_type,
        )
        if actual != expected:
            raise ValueError(f"Unexpected {destination_name} count: {actual:,} != {expected:,}")

    print(f"Prepared 17 subgraphs in {output}")
    print(f"Unavailable Spaces excluded: {len(unavailable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# --- build_hugginggraph_v3.py ----------------------------------------------
SOURCES['build_hugginggraph_v3'] = r'''#!/usr/bin/env python3
"""Build the count-verified HuggingGraph v3 DOT release.

Created: 2026-09-30
Version: v2026.10.02-03
Purpose: Assemble the eleven v2 relationship families and six Space families.

Change history:
- 2026-10-02 v2026.10.02-03: updated v3 validation constants for the
  October 2 Dataset relationship analysis.
  Backup: build_hugginggraph_v3.py.bak.20261002-195338
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = ["source", "edge_type", "target"]
SUBGRAPHS = (
    ("model-model", "01_model_model_edges.csv", "model", "model", 966_035),
    ("model-dataset", "02_model_dataset_edges.csv", "dataset", "model", 362_064),
    ("dataset-dataset", "03_dataset_dataset_edges.csv", "dataset", "dataset", 12_541),
    ("model-library", "04_model_library_edges.csv", "model", "library", 1_311_386),
    ("dataset-library", "05_dataset_library_edges.csv", "dataset", "library", 16_864),
    ("model-license", "06_model_license_edges.csv", "model", "license", 1_090_845),
    ("dataset-license", "07_dataset_license_edges.csv", "dataset", "license", 331_317),
    ("model-task", "08_model_task_edges.csv", "model", "task", 577_077),
    ("dataset-task", "09_dataset_task_edges.csv", "dataset", "task", 317_412),
    ("model-github", "10_model_github_edges.csv", "model", "github", 962_855),
    ("dataset-github", "11_dataset_github_edges.csv", "dataset", "github", 188_888),
    ("model-space", "12_model_space_edges.csv", "model", "space", 941_121),
    ("dataset-space", "13_dataset_space_edges.csv", "dataset", "space", 83_061),
    ("space-github", "14_space_github_edges.csv", "space", "github", 113_755),
    ("space-license", "15_space_license_edges.csv", "space", "license", 420_369),
    ("space-task", "16_space_task_edges.csv", "space", "task", 43_223),
    ("space-agent", "17_space_agent_edges.csv", "space", "agent", 37_059),
)
EXPECTED_NODES = {
    "model": 1_888_591,
    "dataset": 431_324,
    "space": 712_728,
    "library": 2_148,
    "license": 4_888,
    "task": 839,
    "github": 96_678,
    "agent": 11,
}
EXPECTED_EDGES = 7_775_872
EXPECTED_TOTAL_NODES = 3_137_207


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("HuggingGraph_v3.dot"))
    return parser.parse_args()


def node_type(node: str) -> str:
    if node.startswith("https://github.com/"):
        return "github"
    if "::" not in node:
        raise ValueError(f"Untyped node: {node!r}")
    return node.split("::", 1)[0]


def validate_node(node: str, expected_type: str, context: str) -> None:
    actual = node_type(node)
    if actual != expected_type:
        raise ValueError(
            f"Unexpected {actual} node in {context}; expected {expected_type}: {node!r}"
        )


def dot_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build(edge_dir: Path, output: Path) -> tuple[Counter[str], dict[str, set[str]]]:
    edge_dir = edge_dir.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")

    counters: Counter[str] = Counter()
    nodes = {kind: set() for kind in EXPECTED_NODES}
    with output.open("x", encoding="utf-8") as dot_file:
        dot_file.write(
            'digraph HuggingGraph {\n'
            '  graph [rankdir="LR"];\n'
            '  node [shape="box"];\n'
        )
        for name, filename, source_type, target_type, expected_edges in SUBGRAPHS:
            path = edge_dir / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            with path.open(newline="", encoding="utf-8") as input_file:
                reader = csv.DictReader(input_file)
                if reader.fieldnames != FIELDS:
                    raise ValueError(f"Unexpected schema in {path}: {reader.fieldnames}")
                for line_number, row in enumerate(reader, start=2):
                    source = row["source"]
                    target = row["target"]
                    edge_type = row["edge_type"]
                    context = f"{filename}:{line_number}"
                    validate_node(source, source_type, context)
                    validate_node(target, target_type, context)
                    label = "merge" if edge_type == "merged" else edge_type
                    dot_file.write(
                        f"  {dot_string(source)} -> {dot_string(target)} "
                        f"[label={dot_string(label)}, edge_type={dot_string(edge_type)}];\n"
                    )
                    nodes[source_type].add(source)
                    nodes[target_type].add(target)
                    counters[name] += 1
                    counters["edges"] += 1
            if counters[name] != expected_edges:
                raise ValueError(
                    f"Unexpected {name} count: {counters[name]:,} != {expected_edges:,}"
                )
        dot_file.write("}\n")

    actual_nodes = {kind: len(values) for kind, values in nodes.items()}
    if counters["edges"] != EXPECTED_EDGES:
        raise ValueError(f"Unexpected edge total: {counters['edges']:,}")
    if actual_nodes != EXPECTED_NODES:
        raise ValueError(f"Unexpected node counts: {actual_nodes} != {EXPECTED_NODES}")
    if sum(actual_nodes.values()) != EXPECTED_TOTAL_NODES:
        raise ValueError("Unexpected global node total")
    return counters, nodes


def main() -> int:
    args = parse_args()
    counters, nodes = build(args.edge_dir, args.output)
    print("HuggingGraph v3")
    print("---------------")
    for name, _filename, _source, _target, _expected in SUBGRAPHS:
        print(f"{name:24} {counters[name]:12,}")
    print(f"{'Total edges':24} {counters['edges']:12,}")
    for kind in EXPECTED_NODES:
        print(f"{kind + ' nodes':24} {len(nodes[kind]):12,}")
    print(f"{'Total nodes':24} {sum(map(len, nodes.values())):12,}")
    print(f"DOT: {args.output.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


if __name__ == "__main__":
    raise SystemExit(main())
