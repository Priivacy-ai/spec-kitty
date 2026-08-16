#!/usr/bin/env python3
"""Reproducible per-project discovery benchmark (T053 / NFR-006 / FR-011).

Mission ``per-project-sync-consent-ledgers-01KZKMQZ`` WP11. Generates a
deterministic, seeded population of per-project sync stores under a disposable
``SPEC_KITTY_HOME`` — by default 100 stores: 80 opted-out projects carrying
fresh deny hints and 20 opted-in projects that require an authority read —
then measures the daemon-shaped discovery scan two ways:

* **warm** — one warm-up scan observes each store's consent generation (the
  precondition FR-011 places on trusting a deny hint), then N scans run in the
  same warmed process, each over a seeded-random candidate order, and every
  scan's latency is recorded as a raw sample.
* **process-cold** — M fresh Python subprocesses each run exactly one scan
  with no observed generations, so every store takes the authority-read path.
  This is *process*-cold only: the OS page cache is NOT evicted between runs,
  and no disk-cold claim is made.

Correctness gate (always enforced, fail-closed): around every measured scan —
warm and cold — ``sqlite3.connect`` is instrumented exactly as in
``tests/delivery/test_nfr003_predicate_cost_3030.py``, and the run fails if a
single statement touching a payload table (``journal_entries``,
``outbox_tasks``, ``body_upload_tasks``) executes against a denied project's
store. Warm scans additionally must not open a denied store at all: a valid
deny hint is the whole mechanism under measurement.

Release gates (documented here and in ``--help``; timing is enforced only
with ``--enforce-gates``):

* warm scan p95  <= 500 ms  (``WARM_P95_GATE_MS``)
* process-cold scan p95 <= 1 s  (``COLD_P95_GATE_MS``)

These gates are defined for a local-SSD developer/release machine — state the
storage with ``--storage-hint local-ssd`` when claiming them. **CI timing is
advisory only**: shared runners must never fail a build on these thresholds.

Raw randomized samples plus runtime metadata (OS, filesystem, storage hint,
CPU, Python, SQLite versions, git commit, seed) are written as JSON so a
reviewer can recompute every percentile independently.

Candidate enumeration mirrors the daemon's
``_enumerate_project_store_candidates`` (deny-hint filenames plus the runtime
``projects/`` directory) except for the cwd repository identity: the benchmark
deliberately runs with no repository context.

Usage::

    uv run python scripts/benchmarks/bench_project_discovery.py \
        --storage-hint local-ssd \
        --output build/benchmarks/project_discovery_samples.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from kernel.clock import now_utc_iso, timedelta

import specify_cli
from specify_cli.paths import get_runtime_root
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.deny_hints import (
    DenyHintAction,
    enumerate_deny_hint_project_uuids,
    publish_deny_hint,
    read_deny_hint,
)
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore

SCHEMA_VERSION: Final[int] = 1
DEFAULT_SEED: Final[int] = 3262
DEFAULT_STORE_COUNT: Final[int] = 100
DEFAULT_AUTHORITY_READ_COUNT: Final[int] = 20
DEFAULT_WARM_SCAN_COUNT: Final[int] = 200
DEFAULT_COLD_PROCESS_COUNT: Final[int] = 30

#: Local-SSD release gates (NFR-006). CI timing is advisory only.
WARM_P95_GATE_MS: Final[float] = 500.0
COLD_P95_GATE_MS: Final[float] = 1000.0
GATE_SCOPE: Final[str] = (
    "Release gates apply on a local-SSD machine (pass --storage-hint local-ssd "
    "when claiming them): warm scan p95 <= 500 ms, process-cold scan p95 <= 1 s. "
    "CI timing is advisory only and must never fail a build."
)

#: Tables that hold captured project content. A denied project's store may be
#: read for *authority* (consent/admission rows) but never for payload.
PAYLOAD_TABLES: Final[tuple[str, ...]] = (
    "journal_entries",
    "outbox_tasks",
    "body_upload_tasks",
)

ROLE_DENIED_HINT: Final[str] = "denied_hint"
ROLE_AUTHORITY_READ: Final[str] = "authority_read"

_BENCH_ACTOR: Final[str] = "bench-project-discovery"
#: Long enough that hints stay fresh for the whole measured run; deny hints
#: published by ``record_project_opt_out`` default to five minutes.
_HINT_TTL: Final[timedelta] = timedelta(hours=2)
_COLD_WORKER_TIMEOUT_SECONDS: Final[float] = 300.0


class BenchmarkCorrectnessError(RuntimeError):
    """A consent-boundary invariant was violated; all timing numbers are void."""


# --------------------------------------------------------------------------- #
# Deterministic store population                                               #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ProjectSpec:
    """One deterministic project in the generated population."""

    index: int
    project_uuid: str
    role: str


def _derived_rank(*parts: object) -> str:
    """Seeded pseudorandom sort key: uuid5 over the joined parts.

    Deterministic across processes and platforms (SHA-1 based, no
    ``PYTHONHASHSEED`` sensitivity), so the same seed always yields the same
    role assignment and the same per-scan candidate orders.
    """
    return str(uuid5(NAMESPACE_URL, "spec-kitty:bench:project-discovery:" + ":".join(str(part) for part in parts)))


def build_project_specs(
    *,
    seed: int,
    store_count: int,
    authority_read_count: int,
) -> tuple[ProjectSpec, ...]:
    """Derive the seeded project population without touching the filesystem.

    Both the UUIDs and the role assignment come from ``uuid5`` over the seed,
    so the same seed always yields the same population.
    """
    if store_count < 1:
        raise ValueError("store_count must be at least 1")
    if not 0 <= authority_read_count <= store_count:
        raise ValueError("authority_read_count must be between 0 and store_count")
    ranked_indexes = sorted(range(store_count), key=lambda index: _derived_rank("roles", seed, index))
    authority_indexes = frozenset(ranked_indexes[:authority_read_count])
    specs: list[ProjectSpec] = []
    for index in range(store_count):
        project_uuid = str(uuid5(NAMESPACE_URL, f"spec-kitty:bench:project-discovery:{seed}:{index}"))
        role = ROLE_AUTHORITY_READ if index in authority_indexes else ROLE_DENIED_HINT
        specs.append(ProjectSpec(index=index, project_uuid=project_uuid, role=role))
    return tuple(specs)


def generate_stores(specs: Sequence[ProjectSpec]) -> frozenset[str]:
    """Materialize every spec as a real per-project store under the active home.

    Denied projects are opted out through the production consent path (which
    publishes a deny hint) and then re-published with a long TTL so the hint
    stays fresh for the whole measured run. Returns the denied projects'
    database paths for the payload-open instrumentation.
    """
    denied_paths: set[str] = set()
    for spec in specs:
        store = ProjectSyncStore(spec.project_uuid)
        with store.unit_of_work():
            pass  # Initialize schema and the owner row through the production path.
        if spec.role == ROLE_DENIED_HINT:
            record = record_project_opt_out(spec.project_uuid, actor=_BENCH_ACTOR)
            publish_deny_hint(
                spec.project_uuid,
                action=DenyHintAction.REVOKE,
                authority_generation=record.generation,
                reason_category="explicit_opt_out",
                ttl=_HINT_TTL,
            )
            denied_paths.add(str(store.database_path))
        else:
            record_project_opt_in(spec.project_uuid, actor=_BENCH_ACTOR)
    return frozenset(denied_paths)


# --------------------------------------------------------------------------- #
# Instrumentation (as in tests/delivery/test_nfr003_predicate_cost_3030.py)    #
# --------------------------------------------------------------------------- #


@dataclass
class DeniedStoreAccessLog:
    """Connections to denied stores, and any statement touching payload tables."""

    connections: int = 0
    payload_statements: list[str] = field(default_factory=list)


def _normalize_database_argument(database: object) -> str:
    text = str(database)
    if text.startswith("file:"):
        text = text.removeprefix("file:").split("?", 1)[0]
    return str(Path(text)) if text else text


@contextmanager
def denied_payload_guard(
    denied_database_paths: frozenset[str],
) -> Iterator[DeniedStoreAccessLog]:
    """Count denied-store connections and record payload-table statements.

    Patches ``sqlite3.connect`` process-wide and filters on the database
    argument, so stores of admitted projects contribute nothing. Restores the
    original on exit even if the body raises.
    """
    log = DeniedStoreAccessLog()
    real_connect = sqlite3.connect
    normalized_targets = frozenset(_normalize_database_argument(path) for path in denied_database_paths)

    def _connect(
        database: str | bytes | os.PathLike[str] | os.PathLike[bytes] = ":memory:",
        *args: Any,
        **kwargs: Any,
    ) -> sqlite3.Connection:
        conn: sqlite3.Connection = real_connect(database, *args, **kwargs)
        if _normalize_database_argument(database) in normalized_targets:
            log.connections += 1

            def _trace(statement: str | None) -> None:
                text = (statement or "").lower()
                if any(table in text for table in PAYLOAD_TABLES):
                    log.payload_statements.append(statement or "")

            conn.set_trace_callback(_trace)
        return conn

    with patch.object(sqlite3, "connect", _connect):
        yield log


def enforce_zero_denied_payload_opens(payload_statements: Sequence[str]) -> None:
    """Fail closed when any payload table of a denied project's store was read."""
    if payload_statements:
        preview = "; ".join(payload_statements[:5])
        raise BenchmarkCorrectnessError(
            f"correctness gate failed: {len(payload_statements)} statement(s) "
            f"touched a payload table of a denied project's store "
            f"(first: {preview}). Timing numbers from this run are void."
        )


# --------------------------------------------------------------------------- #
# The discovery scan under measurement                                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ScanOutcome:
    """What one discovery scan did, and how long it took."""

    elapsed_seconds: float
    candidates: int
    hint_skips: int
    authority_reads: int


def enumerate_candidates() -> tuple[CanonicalProjectUUID, ...]:
    """Enumerate candidate project UUIDs the way the daemon's discovery does.

    Union of deny-hint filenames and runtime ``projects/`` directory entries;
    the daemon's third source (the cwd repository identity) is deliberately
    absent — the benchmark runs with no repository context.
    """
    candidates = set(enumerate_deny_hint_project_uuids())
    projects_dir = Path(get_runtime_root().base) / "projects"
    if projects_dir.is_dir():
        for path in projects_dir.iterdir():
            if not path.is_dir():
                continue
            try:
                project_uuid = CanonicalProjectUUID.parse(path.name)
            except (TypeError, ValueError):
                continue
            if path.name == project_uuid.storage_token:
                candidates.add(project_uuid)
    return tuple(sorted(candidates))


def run_discovery_scan(
    observed_generations: dict[str, int],
    *,
    order_key: Callable[[CanonicalProjectUUID], str] | None = None,
) -> ScanOutcome:
    """Run one daemon-shaped discovery scan over every candidate store.

    Mirrors ``BackgroundSyncService``: a deny hint may be trusted only after
    this process observed the project's consent generation from authority
    (FR-011); every other state opens the store and reads authority rows only.
    ``order_key`` reorders the candidates so warm samples are randomized
    (seeded pseudorandom, hence reproducible).
    """
    started = time.perf_counter()
    candidates = list(enumerate_candidates())
    if order_key is not None:
        candidates.sort(key=order_key)
    hint_skips = 0
    authority_reads = 0
    for project_uuid in candidates:
        key = project_uuid.storage_token
        expected_generation = observed_generations.get(key)
        if expected_generation is not None and not read_deny_hint(project_uuid, expected_generation=expected_generation).requires_authority:
            hint_skips += 1
            continue
        store = ProjectSyncStore(project_uuid)
        if not store.database_path.is_file():
            continue
        context = store.create_context()
        if context.consent_generation is not None:
            observed_generations[key] = context.consent_generation
        authority_reads += 1
    return ScanOutcome(
        elapsed_seconds=time.perf_counter() - started,
        candidates=len(candidates),
        hint_skips=hint_skips,
        authority_reads=authority_reads,
    )


# --------------------------------------------------------------------------- #
# Warm and process-cold phases                                                 #
# --------------------------------------------------------------------------- #


def _require_warm_composition(
    outcome: ScanOutcome,
    *,
    scan_index: int,
    denied_count: int,
    authority_read_count: int,
) -> None:
    """A warm sample only measures NFR-006 if the scan had the stated shape."""
    if outcome.hint_skips != denied_count or outcome.authority_reads != authority_read_count:
        raise BenchmarkCorrectnessError(
            f"warm scan {scan_index} measured the wrong workload: "
            f"hint_skips={outcome.hint_skips} (expected {denied_count}), "
            f"authority_reads={outcome.authority_reads} (expected {authority_read_count})"
        )


def _run_warm_phase(
    denied_paths: frozenset[str],
    *,
    seed: int,
    store_count: int,
    authority_read_count: int,
    warm_scan_count: int,
) -> tuple[list[float], ScanOutcome, DeniedStoreAccessLog, DeniedStoreAccessLog]:
    """One observing warm-up scan, then ``warm_scan_count`` measured scans."""
    observed_generations: dict[str, int] = {}
    with denied_payload_guard(denied_paths) as warmup_log:
        warmup = run_discovery_scan(observed_generations)
    if warmup.candidates != store_count:
        raise BenchmarkCorrectnessError(f"warm-up scan saw {warmup.candidates} candidates, expected {store_count}")

    denied_count = store_count - authority_read_count
    samples_seconds: list[float] = []
    with denied_payload_guard(denied_paths) as warm_log:
        for scan_index in range(warm_scan_count):

            def _scan_order(project_uuid: CanonicalProjectUUID, scan_index: int = scan_index) -> str:
                return _derived_rank("scan-order", seed, scan_index, project_uuid.storage_token)

            outcome = run_discovery_scan(observed_generations, order_key=_scan_order)
            _require_warm_composition(
                outcome,
                scan_index=scan_index,
                denied_count=denied_count,
                authority_read_count=authority_read_count,
            )
            samples_seconds.append(outcome.elapsed_seconds)
    if warm_log.connections:
        raise BenchmarkCorrectnessError(
            f"warm scans opened denied project stores {warm_log.connections} time(s); "
            "a fresh deny hint must keep denied stores closed"
        )
    return samples_seconds, warmup, warmup_log, warm_log


def _spawn_cold_scan(home: Path, expected_candidates: int) -> tuple[float, dict[str, Any]]:
    """Run one scan in a fresh subprocess; return (wall seconds, worker report)."""
    env = dict(os.environ)
    env["SPEC_KITTY_HOME"] = str(home)
    src_root = Path(specify_cli.__file__).resolve().parents[1]
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(part for part in (str(src_root), existing_pythonpath) if part)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--cold-scan-worker",
        "--expect-candidates",
        str(expected_candidates),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        timeout=_COLD_WORKER_TIMEOUT_SECONDS,
        check=False,
    )
    wall_seconds = time.perf_counter() - started
    if completed.returncode != 0:
        raise BenchmarkCorrectnessError(f"cold-scan worker failed (rc={completed.returncode}): {completed.stderr.strip()}")
    try:
        report_line = completed.stdout.strip().splitlines()[-1]
        report: dict[str, Any] = json.loads(report_line)
    except (IndexError, ValueError) as exc:
        raise BenchmarkCorrectnessError(f"cold-scan worker emitted no parseable JSON report: {completed.stdout!r}") from exc
    return wall_seconds, report


def _run_cold_phase(
    home: Path,
    *,
    store_count: int,
    cold_process_count: int,
) -> tuple[list[float], list[float], int, list[str]]:
    """Spawn ``cold_process_count`` fresh workers; collect raw samples."""
    scan_samples_seconds: list[float] = []
    wall_samples_seconds: list[float] = []
    denied_connections = 0
    payload_statements: list[str] = []
    for _ in range(cold_process_count):
        wall_seconds, report = _spawn_cold_scan(home, store_count)
        wall_samples_seconds.append(wall_seconds)
        scan_samples_seconds.append(float(report["scan_seconds"]))
        denied_connections += int(report["denied_store_connections"])
        payload_statements.extend(str(statement) for statement in report["denied_payload_statements"])
    return scan_samples_seconds, wall_samples_seconds, denied_connections, payload_statements


def _run_cold_scan_worker(expected_candidates: int) -> int:
    """Internal ``--cold-scan-worker`` entry point: one instrumented scan."""
    if not os.environ.get("SPEC_KITTY_HOME"):
        print(
            "cold-scan worker refuses to run without SPEC_KITTY_HOME (it would scan the real home)",
            file=sys.stderr,
        )
        return 2
    denied_paths = frozenset(str(ProjectSyncStore(project_uuid).database_path) for project_uuid in enumerate_deny_hint_project_uuids())
    observed_generations: dict[str, int] = {}
    with denied_payload_guard(denied_paths) as log:
        outcome = run_discovery_scan(observed_generations)
    print(
        json.dumps(
            {
                "scan_seconds": outcome.elapsed_seconds,
                "candidates": outcome.candidates,
                "hint_skips": outcome.hint_skips,
                "authority_reads": outcome.authority_reads,
                "denied_store_connections": log.connections,
                "denied_payload_statements": log.payload_statements,
            }
        )
    )
    if outcome.candidates != expected_candidates:
        print(
            f"cold scan saw {outcome.candidates} candidates, expected {expected_candidates}",
            file=sys.stderr,
        )
        return 3
    return 0


# --------------------------------------------------------------------------- #
# Metadata, statistics, report                                                 #
# --------------------------------------------------------------------------- #


def percentile(samples: Sequence[float], fraction: float) -> float:
    """Nearest-rank percentile over raw samples (deterministic, no interpolation)."""
    if not samples:
        raise ValueError("percentile of an empty sample set is undefined")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    ordered = sorted(samples)
    rank = math.ceil(fraction * len(ordered)) - 1
    return ordered[max(0, min(rank, len(ordered) - 1))]


def _detect_git_commit() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _detect_filesystem(path: Path) -> str:
    """Best-effort filesystem name for the volume holding *path* (else "unknown")."""
    try:
        listing = subprocess.run(
            ["mount"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    resolved = str(path.resolve())
    best_mount = ""
    best_fs = "unknown"
    for line in listing.splitlines():
        if " on " not in line:
            continue
        rest = line.split(" on ", 1)[1]
        if " type " in rest:  # GNU/Linux: "device on /mp type ext4 (rw,...)"
            mount_point, _, fs_part = rest.partition(" type ")
            fs_name = fs_part.split(" ", 1)[0]
        else:  # BSD/macOS: "device on /mp (apfs, local, journaled)"
            mount_point, _, fs_part = rest.rpartition(" (")
            fs_name = fs_part.split(",", 1)[0].rstrip(")")
        mount_point = mount_point.strip()
        if mount_point and resolved.startswith(mount_point) and len(mount_point) > len(best_mount):
            best_mount = mount_point
            best_fs = fs_name.strip() or "unknown"
    return best_fs


def collect_runtime_metadata(*, seed: int, storage_hint: str, probe_path: Path) -> dict[str, Any]:
    """Record the environment a reviewer needs to interpret raw samples."""
    return {
        "os": platform.platform(),
        "filesystem": _detect_filesystem(probe_path),
        "storage_hint": storage_hint,
        "cpu": {
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "logical_cores": os.cpu_count() or 0,
        },
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "sqlite": sqlite3.sqlite_version,
        "git_commit": _detect_git_commit(),
        "seed": seed,
    }


def _timing_section(samples_seconds: Sequence[float]) -> dict[str, Any]:
    samples_ms = [seconds * 1000.0 for seconds in samples_seconds]
    return {
        "samples_ms": samples_ms,
        "sample_count": len(samples_ms),
        "min_ms": min(samples_ms),
        "mean_ms": statistics.fmean(samples_ms),
        "p50_ms": percentile(samples_ms, 0.50),
        "p95_ms": percentile(samples_ms, 0.95),
        "max_ms": max(samples_ms),
    }


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #


def run_benchmark(
    *,
    home: Path,
    seed: int = DEFAULT_SEED,
    store_count: int = DEFAULT_STORE_COUNT,
    authority_read_count: int = DEFAULT_AUTHORITY_READ_COUNT,
    warm_scan_count: int = DEFAULT_WARM_SCAN_COUNT,
    cold_process_count: int = DEFAULT_COLD_PROCESS_COUNT,
    storage_hint: str = "unspecified",
) -> dict[str, Any]:
    """Generate stores under *home*, run both phases, return the full report.

    Sets ``SPEC_KITTY_HOME`` to *home* for this process and every cold worker,
    so the benchmark can never touch the operator's real runtime root.
    """
    os.environ["SPEC_KITTY_HOME"] = str(home)
    home.mkdir(parents=True, exist_ok=True)
    specs = build_project_specs(
        seed=seed,
        store_count=store_count,
        authority_read_count=authority_read_count,
    )
    denied_paths = generate_stores(specs)
    denied_count = store_count - authority_read_count

    warm_samples, warmup, warmup_log, warm_log = _run_warm_phase(
        denied_paths,
        seed=seed,
        store_count=store_count,
        authority_read_count=authority_read_count,
        warm_scan_count=warm_scan_count,
    )
    cold_scans, cold_walls, cold_denied_connections, cold_payload = _run_cold_phase(
        home,
        store_count=store_count,
        cold_process_count=cold_process_count,
    )

    all_payload_statements = [
        *warmup_log.payload_statements,
        *warm_log.payload_statements,
        *cold_payload,
    ]
    enforce_zero_denied_payload_opens(all_payload_statements)

    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "project-discovery",
        "generated_at": now_utc_iso(),
        "seed": seed,
        "config": {
            "store_count": store_count,
            "denied_hint_count": denied_count,
            "authority_read_count": authority_read_count,
            "warm_scan_count": warm_scan_count,
            "cold_process_count": cold_process_count,
            "hint_ttl_seconds": _HINT_TTL.total_seconds(),
        },
        "runtime": collect_runtime_metadata(seed=seed, storage_hint=storage_hint, probe_path=home),
        "release_gates": {
            "warm_p95_gate_ms": WARM_P95_GATE_MS,
            "cold_p95_gate_ms": COLD_P95_GATE_MS,
            "scope": GATE_SCOPE,
        },
        "correctness": {
            "gate": "zero payload-table opens for denied projects",
            "payload_tables": list(PAYLOAD_TABLES),
            "denied_project_count": denied_count,
            "denied_payload_table_opens": len(all_payload_statements),
            "warmup_denied_store_connections": warmup_log.connections,
            "warm_denied_store_connections": warm_log.connections,
            "cold_denied_store_connections": cold_denied_connections,
            "passed": True,
        },
        "warmup": {
            "elapsed_ms": warmup.elapsed_seconds * 1000.0,
            "candidates": warmup.candidates,
            "authority_reads": warmup.authority_reads,
        },
        "warm": _timing_section(warm_samples),
        "cold": {
            **_timing_section(cold_scans),
            "subprocess_wall_ms": [seconds * 1000.0 for seconds in cold_walls],
            "note": (
                "One fresh Python subprocess per sample with no observed consent "
                "generations, so every store takes the authority-read path. "
                "samples_ms is the in-child scan latency; subprocess_wall_ms adds "
                "interpreter start and imports. The OS page cache is NOT evicted: "
                "this measures process-cold, not disk-cold, latency."
            ),
        },
    }


def _timing_gate_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    warm_p95 = float(report["warm"]["p95_ms"])
    cold_p95 = float(report["cold"]["p95_ms"])
    if warm_p95 > WARM_P95_GATE_MS:
        failures.append(f"warm p95 {warm_p95:.1f} ms exceeds the {WARM_P95_GATE_MS:.0f} ms local-SSD release gate")
    if cold_p95 > COLD_P95_GATE_MS:
        failures.append(f"process-cold p95 {cold_p95:.1f} ms exceeds the {COLD_P95_GATE_MS:.0f} ms local-SSD release gate")
    return failures


def _print_summary(report: dict[str, Any], output: Path) -> None:
    warm = report["warm"]
    cold = report["cold"]
    correctness = report["correctness"]
    print(
        f"warm: n={warm['sample_count']} p50={warm['p50_ms']:.2f}ms "
        f"p95={warm['p95_ms']:.2f}ms max={warm['max_ms']:.2f}ms "
        f"(local-SSD release gate {WARM_P95_GATE_MS:.0f}ms; CI advisory)"
    )
    print(
        f"cold: n={cold['sample_count']} p50={cold['p50_ms']:.2f}ms "
        f"p95={cold['p95_ms']:.2f}ms max={cold['max_ms']:.2f}ms "
        f"(local-SSD release gate {COLD_P95_GATE_MS:.0f}ms; CI advisory; "
        f"process-cold, OS cache not evicted)"
    )
    print(f"correctness: denied payload-table opens = {correctness['denied_payload_table_opens']} (gate: zero)")
    print(f"raw samples + runtime metadata written to {output}")


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI surface; ``--help`` documents the local-SSD release gates."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"Release gates (local SSD): warm scan p95 <= {WARM_P95_GATE_MS:.0f} ms; "
            f"process-cold scan p95 <= {COLD_P95_GATE_MS:.0f} ms. CI timing is "
            "advisory only. The zero-denied-payload-open correctness gate is "
            "always enforced."
        ),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Deterministic generation seed (default: {DEFAULT_SEED}).")
    parser.add_argument("--stores", type=int, default=DEFAULT_STORE_COUNT, help=f"Total project stores to generate (default: {DEFAULT_STORE_COUNT}).")
    parser.add_argument(
        "--authority-reads",
        type=int,
        default=DEFAULT_AUTHORITY_READ_COUNT,
        help=f"Stores requiring an authority read per scan; the rest carry fresh deny hints (default: {DEFAULT_AUTHORITY_READ_COUNT}).",
    )
    parser.add_argument(
        "--warm-scans",
        type=int,
        default=DEFAULT_WARM_SCAN_COUNT,
        help=f"Randomized scans in one warmed process (default: {DEFAULT_WARM_SCAN_COUNT}).",
    )
    parser.add_argument(
        "--cold-processes",
        type=int,
        default=DEFAULT_COLD_PROCESS_COUNT,
        help=f"Fresh subprocess scans; OS cache is NOT evicted (default: {DEFAULT_COLD_PROCESS_COUNT}).",
    )
    parser.add_argument(
        "--home",
        type=str,
        default=None,
        help="Directory to use as SPEC_KITTY_HOME (default: a fresh temp dir, removed afterwards).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="build/benchmarks/project_discovery_samples.json",
        help="Where to write the raw-sample JSON report.",
    )
    parser.add_argument(
        "--storage-hint",
        type=str,
        default="unspecified",
        help="Operator-stated storage class (e.g. local-ssd); required context for release-gate claims.",
    )
    parser.add_argument(
        "--enforce-gates",
        action="store_true",
        help="Fail (exit 1) when a local-SSD timing gate is exceeded. Leave off on CI: CI timing is advisory only.",
    )
    parser.add_argument(
        "--cold-scan-worker",
        action="store_true",
        help="Internal: run one process-cold scan and print a JSON report.",
    )
    parser.add_argument(
        "--expect-candidates",
        type=int,
        default=0,
        help="Internal: candidate count the cold-scan worker must observe.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    args = build_arg_parser().parse_args(argv)
    if args.cold_scan_worker:
        return _run_cold_scan_worker(args.expect_candidates)

    created_temp_home = args.home is None
    home = Path(args.home) if args.home is not None else Path(tempfile.mkdtemp(prefix="spec-kitty-bench-discovery-"))
    try:
        report = run_benchmark(
            home=home,
            seed=args.seed,
            store_count=args.stores,
            authority_read_count=args.authority_reads,
            warm_scan_count=args.warm_scans,
            cold_process_count=args.cold_processes,
            storage_hint=args.storage_hint,
        )
    finally:
        if created_temp_home:
            shutil.rmtree(home, ignore_errors=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _print_summary(report, output)

    if args.enforce_gates:
        failures = _timing_gate_failures(report)
        for failure in failures:
            print(f"GATE FAILED: {failure}", file=sys.stderr)
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
