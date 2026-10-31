#!/usr/bin/env python3
"""Check the production sources in this folder against SOURCE_MANIFEST.json.

Created: 2026-10-30
Version: v2026.10.30-05 (missing files are reported, not a traceback)
Purpose: Show that experiments/production/ holds the production analysis code
         unchanged except for the documented machine-specific literals.

Without options, every published file is checked against its published_sha256.
With --private-values (a JSON file held privately by the authors, listing the
redacted literals), every file is also restored and checked against the
original_sha256 recorded from the production server.
With --originals DIR (the production repository root), files are compared
byte for byte with the originals after restoration.

Command: python experiments/production/verify_sources.py [--private-values FILE] [--originals DIR]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def restore(data, values):
    text = data.decode("utf-8")
    for value, placeholder in reversed(values):
        text = text.replace(placeholder, value)
    return text.encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--private-values", type=Path)
    parser.add_argument("--originals", type=Path)
    parser.add_argument("--root", type=Path, default=HERE,
                        help="folder holding SOURCE_MANIFEST.json (default: this folder; "
                             "graph_server_rq1/ for the RQ1 Graph Server files)")
    args = parser.parse_args()
    root = args.root.resolve()

    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    values = json.loads(args.private_values.read_text())["redactions"] if args.private_values else None
    if args.originals and values is None:
        parser.error("--originals needs --private-values to restore redacted files")
    failures = 0
    for entry in manifest["files"]:
        if not (root / entry["path"]).is_file():
            failures += 1
            print(f"MISSING  {entry['path']}  (a GitHub Release asset? see the README's Download section)")
            continue
        data = (root / entry["path"]).read_bytes()
        checks = [("published", sha(data) == entry["published_sha256"])]
        if values is not None:
            restored = data if entry["verbatim"] else restore(data, values)
            checks.append(("original", sha(restored) == entry["original_sha256"]))
            if args.originals:
                checks.append(("byte-equal", restored == (args.originals / entry["path"]).read_bytes()))
        ok = all(result for _, result in checks)
        failures += not ok
        kind = "verbatim" if entry["verbatim"] else "redacted"
        print(f"{'OK  ' if ok else 'FAIL'} {kind:8} {entry['path']}  "
              + " ".join(f"{name}={'ok' if result else 'MISMATCH'}" for name, result in checks))
    print(f"{len(manifest['files']) - failures}/{len(manifest['files'])} files verified")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
