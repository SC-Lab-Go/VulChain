#!/usr/bin/env python3
"""Build model-to-model Hugging Face base-model relation edges.

Reads model IDs from CSV, queries the authenticated Hugging Face Hub API for
derived models, and writes a resumable edge-list CSV.

Change history:
2026-08-31 v2026.08.31-01
- Replaced HTML scraping with authenticated Hub API pagination.
- Added rate limiting, checkpoints, deduplication, and failure logging.
- Added validated CLI options and the missing merge relation.
- Backup: graph_model_model_emma.py.bak.20260831-150035
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Iterator

import requests
from huggingface_hub import get_token
from tqdm import tqdm


CHANGE_ID = "v2026.08.31-01"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "delta_model-2026-Aug28.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "graph_model_emma-test.csv"
API_URL = "https://huggingface.co/api/models"
RELATION_TYPES = ("finetune", "quantized", "adapter", "merge")
OUTPUT_COLUMNS = ("Source", "Edge_type", "Target")
TRANSIENT_STATUS_CODES = {500, 502, 503, 504}


class GlobalRateLimiter:
    """Limit aggregate request frequency across all worker threads."""

    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = interval_seconds
        self._next_request = 0.0
        self._lock = threading.Lock()

    def wait_for_turn(self) -> None:
        with self._lock:
            delay = max(0.0, self._next_request - time.monotonic())
            if delay:
                time.sleep(delay)
            self._next_request = time.monotonic() + self.interval_seconds

    def pause_all(self, seconds: float) -> None:
        with self._lock:
            self._next_request = max(
                self._next_request, time.monotonic() + max(0.0, seconds)
            )


_thread_local = threading.local()


def thread_session(token: str) -> requests.Session:
    """Return one authenticated requests session per worker thread."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "User-Agent": f"hugging-graph-collector/{CHANGE_ID}",
                "Accept": "application/json",
            }
        )
        _thread_local.session = session
    return session


def rate_limit_wait_seconds(response: requests.Response) -> float:
    """Read server reset hints, falling back to a full quota window."""
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after:
        try:
            return max(1.0, float(retry_after)) + 1.0
        except ValueError:
            try:
                reset_at = parsedate_to_datetime(retry_after)
                if reset_at.tzinfo is None:
                    reset_at = reset_at.replace(tzinfo=timezone.utc)
                seconds = (reset_at - datetime.now(timezone.utc)).total_seconds()
                return max(1.0, seconds) + 1.0
            except (TypeError, ValueError, OverflowError):
                pass

    for header_name in ("RateLimit-Reset", "X-RateLimit-Reset"):
        raw_value = response.headers.get(header_name, "").strip()
        if not raw_value:
            continue
        try:
            value = float(raw_value)
            if value > 10_000_000_000:
                value /= 1000.0
            if value > time.time():
                return max(1.0, value - time.time()) + 1.0
            return max(1.0, value) + 1.0
        except ValueError:
            pass

    rate_limit = response.headers.get("RateLimit", "")
    match = re.search(r"(?:reset|t)\s*=\s*(\d+)", rate_limit, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0

    return 310.0


def get_json_page(
    url: str,
    params: dict[str, str] | None,
    token: str,
    limiter: GlobalRateLimiter,
    max_retries: int,
) -> requests.Response:
    """Fetch one API page, respecting rate limits and transient failures."""
    transient_attempts = 0
    while True:
        limiter.wait_for_turn()
        try:
            response = thread_session(token).get(url, params=params, timeout=60)
        except (requests.ConnectionError, requests.Timeout) as exc:
            transient_attempts += 1
            if transient_attempts > max_retries:
                raise RuntimeError(
                    f"Request failed after {max_retries} retries: {url}"
                ) from exc
            time.sleep(min(60.0, 2.0**transient_attempts))
            continue

        if response.status_code == 429:
            wait_seconds = rate_limit_wait_seconds(response)
            limiter.pause_all(wait_seconds)
            tqdm.write(
                "Rate limited by Hugging Face; pausing all requests for "
                f"{wait_seconds:.0f} seconds."
            )
            continue

        if response.status_code in TRANSIENT_STATUS_CODES:
            transient_attempts += 1
            if transient_attempts <= max_retries:
                time.sleep(min(60.0, 2.0**transient_attempts))
                continue

        if response.status_code == 401:
            raise RuntimeError(
                "Hugging Face rejected the token. Run `hf auth login` and retry."
            )
        response.raise_for_status()
        return response


def fetch_relation_targets(
    source_model: str,
    relation: str,
    token: str,
    limiter: GlobalRateLimiter,
    max_retries: int,
) -> set[str]:
    """Return all models tagged as deriving from source_model by relation."""
    url: str | None = API_URL
    params: dict[str, str] | None = {
        "filter": f"base_model:{relation}:{source_model}"
    }
    targets: set[str] = set()

    while url is not None:
        response = get_json_page(url, params, token, limiter, max_retries)
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Unexpected API response for {source_model!r} ({relation})"
            )

        for item in payload:
            if not isinstance(item, dict):
                continue
            target = item.get("modelId") or item.get("id")
            if isinstance(target, str) and target and target != source_model:
                targets.add(target)

        next_link = response.links.get("next", {}).get("url")
        url = str(next_link) if next_link else None
        params = None

    return targets


def process_model(
    model_name: str,
    token: str,
    limiter: GlobalRateLimiter,
    max_retries: int,
) -> set[tuple[str, str, str]]:
    """Collect all supported outgoing derivation edges for one base model."""
    edges: set[tuple[str, str, str]] = set()
    for relation in RELATION_TYPES:
        for target in fetch_relation_targets(
            model_name, relation, token, limiter, max_retries
        ):
            edges.add((model_name, relation, target))
    return edges


def iter_input_models(
    input_path: Path, start_row: int, end_row: int | None
) -> Iterator[str]:
    """Yield unique, non-empty model IDs in the selected zero-based range."""
    with input_path.open(newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames:
            raise ValueError(f"Input CSV has no header: {input_path}")

        field_lookup = {name.strip().lower(): name for name in reader.fieldnames}
        model_column = field_lookup.get("modelid") or field_lookup.get("model_id")
        if model_column is None:
            raise ValueError(
                f"Input CSV must contain a modelId column; found {reader.fieldnames}"
            )

        seen: set[str] = set()
        for row_index, row in enumerate(reader):
            if row_index < start_row:
                continue
            if end_row is not None and row_index >= end_row:
                break
            model_name = (row.get(model_column) or "").strip()
            if model_name and model_name not in seen:
                seen.add(model_name)
                yield model_name


def load_completed_models(checkpoint_path: Path) -> set[str]:
    if not checkpoint_path.exists():
        return set()
    with checkpoint_path.open(encoding="utf-8") as checkpoint_file:
        return {line.strip() for line in checkpoint_file if line.strip()}


def load_existing_edges(output_path: Path) -> set[tuple[str, str, str]]:
    """Validate existing output and load edges for restart deduplication."""
    if not output_path.exists() or output_path.stat().st_size == 0:
        return set()

    with output_path.open(newline="", encoding="utf-8-sig") as output_file:
        reader = csv.reader(output_file)
        header = tuple(next(reader, []))
        if header != OUTPUT_COLUMNS:
            raise ValueError(
                f"Output CSV header must be {OUTPUT_COLUMNS}; found {header}"
            )
        edges: set[tuple[str, str, str]] = set()
        for line_number, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise ValueError(
                    f"Malformed output row {line_number} in {output_path}: {row}"
                )
            edges.add((row[0], row[1], row[2]))
        return edges


def append_durable(file_handle, writer: csv.writer, row: Iterable[str]) -> None:
    writer.writerow(row)
    file_handle.flush()
    os.fsync(file_handle.fileno())


def default_sidecar_path(output_path: Path, suffix: str) -> Path:
    return output_path.with_name(output_path.name + suffix)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create resumable Hugging Face model-to-model relation edges."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Completed-model file (default: <output>.completed.txt)",
    )
    parser.add_argument(
        "--errors", type=Path, help="Failure CSV (default: <output>.errors.csv)"
    )
    parser.add_argument("--start", type=int, default=0, help="First input row")
    parser.add_argument(
        "--end",
        type=int,
        default=2000,
        help="Exclusive final input row; use 0 for all remaining rows",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--request-interval",
        type=float,
        default=0.5,
        help="Minimum seconds between aggregate API requests",
    )
    parser.add_argument("--max-retries", type=int, default=8)
    return parser.parse_args()


def validate_args(
    args: argparse.Namespace,
) -> tuple[Path, Path, Path, Path, int | None]:
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    checkpoint_path = (
        args.checkpoint.expanduser().resolve()
        if args.checkpoint
        else default_sidecar_path(output_path, ".completed.txt")
    )
    errors_path = (
        args.errors.expanduser().resolve()
        if args.errors
        else default_sidecar_path(output_path, ".errors.csv")
    )
    end_row = None if args.end == 0 else args.end

    if not input_path.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")
    if args.start < 0:
        raise ValueError("--start must be zero or greater")
    if end_row is not None and end_row <= args.start:
        raise ValueError("--end must exceed --start, or be 0 for no limit")
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.request_interval < 0:
        raise ValueError("--request-interval cannot be negative")
    if args.max_retries < 0:
        raise ValueError("--max-retries cannot be negative")
    if len({output_path, checkpoint_path, errors_path}) != 3:
        raise ValueError("Output, checkpoint, and error paths must be different")

    return input_path, output_path, checkpoint_path, errors_path, end_row


def run(args: argparse.Namespace) -> None:
    input_path, output_path, checkpoint_path, errors_path, end_row = validate_args(args)
    token = get_token()
    if not token:
        raise RuntimeError(
            "No Hugging Face token found. Run `hf auth login` before this script."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    errors_path.parent.mkdir(parents=True, exist_ok=True)

    completed_models = load_completed_models(checkpoint_path)
    existing_edges = load_existing_edges(output_path)
    limiter = GlobalRateLimiter(args.request_interval)
    model_iterator = iter_input_models(input_path, args.start, end_row)

    output_needs_header = not output_path.exists() or output_path.stat().st_size == 0
    error_needs_header = not errors_path.exists() or errors_path.stat().st_size == 0
    succeeded = failed = skipped = 0
    scheduled = set(completed_models)

    with (
        output_path.open("a", newline="", encoding="utf-8") as output_file,
        checkpoint_path.open("a", encoding="utf-8") as checkpoint_file,
        errors_path.open("a", newline="", encoding="utf-8") as error_file,
        ThreadPoolExecutor(max_workers=args.workers) as pool,
    ):
        output_writer = csv.writer(output_file)
        error_writer = csv.writer(error_file)
        if output_needs_header:
            append_durable(output_file, output_writer, OUTPUT_COLUMNS)
        if error_needs_header:
            append_durable(
                error_file, error_writer, ("modelId", "error", "timestamp_utc")
            )

        pending: dict[Future[set[tuple[str, str, str]]], str] = {}

        def submit_next() -> bool:
            nonlocal skipped
            for model_name in model_iterator:
                if model_name in scheduled:
                    skipped += 1
                    continue
                scheduled.add(model_name)
                future = pool.submit(
                    process_model,
                    model_name,
                    token,
                    limiter,
                    args.max_retries,
                )
                pending[future] = model_name
                return True
            return False

        for _ in range(args.workers * 2):
            if not submit_next():
                break

        with tqdm(desc="Models", unit="model") as progress:
            while pending:
                finished, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in finished:
                    model_name = pending.pop(future)
                    try:
                        edges = future.result()
                        new_edges = sorted(edges - existing_edges)
                        for edge in new_edges:
                            output_writer.writerow(edge)
                        if new_edges:
                            output_file.flush()
                            os.fsync(output_file.fileno())
                            existing_edges.update(new_edges)

                        checkpoint_file.write(model_name + "\n")
                        checkpoint_file.flush()
                        os.fsync(checkpoint_file.fileno())
                        completed_models.add(model_name)
                        succeeded += 1
                    except Exception as exc:  # keep other models running
                        append_durable(
                            error_file,
                            error_writer,
                            (
                                model_name,
                                f"{type(exc).__name__}: {exc}",
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                        failed += 1
                        tqdm.write(f"Failed {model_name}: {exc}")
                    finally:
                        progress.update(1)
                        submit_next()

    print(
        f"Done: {succeeded} completed, {failed} failed, "
        f"{skipped} already completed; output: {output_path}"
    )
    if failed:
        print(f"Failures were recorded in {errors_path}; rerun to retry them.")


def main() -> int:
    try:
        run(parse_args())
    except KeyboardInterrupt:
        print("Interrupted. Completed models are checkpointed; rerun to resume.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
