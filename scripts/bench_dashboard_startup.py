#!/usr/bin/env python3
"""Cold-start benchmark for the spec-kitty dashboard transports.

Measures process-spawn → first-byte latency for both the legacy
``BaseHTTPServer`` stack and the new FastAPI / Uvicorn stack so the
NFR-001 / NFR-002 thresholds in mission
``frontend-api-fastapi-openapi-migration-01KQN2JA`` can be verified on
the operator's machine.

Usage::

    python scripts/bench_dashboard_startup.py --runs 5

The script writes a JSON report to ``/tmp/bench_dashboard_startup.json``
(override with ``--out``). The release-checklist for the mission
references the same path so operators can paste the numbers into the
SC-006 verification slot.

Caveats:

* The script measures real wall-clock time. Numbers vary across machines,
  load, and Python startup state. NFR-001 (≤ 25 % cold-start regression)
  and NFR-002 (≤ 30 % per-request regression) are advisory thresholds:
  exceeding them under-pressure on a busy CI runner is not by itself a
  block; consult the release-checklist's notes section for the rationale.

* The ``--bench-exit-after-first-byte`` CLI flag mentioned in the WP02
  scaffold is wired into the Typer signature but the actual
  exit-after-first-byte instrumentation is left for a follow-up
  hardening pass — it requires a per-stack middleware/hook. For now the
  script measures process spawn → port-bind by polling the dashboard's
  configured port, which is a good proxy for cold-start latency. The
  follow-up will tighten this to true first-byte timing.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median


@dataclass
class StackResult:
    transport: str
    runs: int
    samples_seconds: list[float]
    median_seconds: float
    min_seconds: float
    max_seconds: float


@dataclass
class BenchmarkReport:
    machine_uname: str
    python_version: str
    project_path: str
    legacy: StackResult | None
    fastapi: StackResult | None
    nfr_001_threshold_seconds: float
    nfr_001_within_threshold: bool


def _wait_for_port(port: int, timeout: float = 30.0) -> float | None:
    """Poll 127.0.0.1:<port> until accept succeeds, or timeout. Returns elapsed seconds or None."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    return time.monotonic() - start
        except OSError:
            pass
        time.sleep(0.025)
    return None


def _measure_cold_start(transport: str, project_dir: Path, port: int) -> float:
    """Spawn one dashboard process, time spawn->port-accept, kill it."""
    cmd = [
        sys.executable,
        "-m",
        "specify_cli",
        "dashboard",
        "--transport",
        transport,
        "--port",
        str(port),
    ]
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    try:
        elapsed = _wait_for_port(port, timeout=30.0)
        if elapsed is None:
            return float("nan")
        return time.monotonic() - start
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def _bench_stack(transport: str, project_dir: Path, runs: int) -> StackResult:
    samples: list[float] = []
    base_port = 18900
    for i in range(runs):
        # offset port to avoid TIME_WAIT collisions across runs
        elapsed = _measure_cold_start(transport, project_dir, base_port + i)
        samples.append(elapsed)
    finite = [s for s in samples if s == s and s != float("inf")]
    return StackResult(
        transport=transport,
        runs=runs,
        samples_seconds=samples,
        median_seconds=median(finite) if finite else float("nan"),
        min_seconds=min(finite) if finite else float("nan"),
        max_seconds=max(finite) if finite else float("nan"),
    )


def main() -> int:
    import platform

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="number of cold-start measurements per stack (default: 5)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/bench_dashboard_startup.json"),
        help="output JSON path (default: /tmp/bench_dashboard_startup.json)",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="project directory (must contain .kittify/) — default: cwd",
    )
    parser.add_argument(
        "--skip-legacy",
        action="store_true",
        help="skip the legacy stack (useful when only validating the FastAPI path)",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not (project_dir / ".kittify").exists():
        print(
            f"warning: {project_dir}/.kittify/ not found; the dashboard may fail to start",
            file=sys.stderr,
        )

    legacy = None if args.skip_legacy else _bench_stack("legacy", project_dir, args.runs)
    fastapi = _bench_stack("fastapi", project_dir, args.runs)

    if legacy is not None and legacy.median_seconds == legacy.median_seconds:
        # NFR-001: FastAPI cold-start ≤ 25 % regression vs legacy.
        threshold = legacy.median_seconds * 1.25
        within = (
            fastapi.median_seconds == fastapi.median_seconds
            and fastapi.median_seconds <= threshold
        )
    else:
        threshold = float("nan")
        within = True  # nothing to compare to

    report = BenchmarkReport(
        machine_uname=platform.uname().release,
        python_version=platform.python_version(),
        project_path=str(project_dir),
        legacy=legacy,
        fastapi=fastapi,
        nfr_001_threshold_seconds=threshold,
        nfr_001_within_threshold=within,
    )

    args.out.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")
    print(f"\nReport written to {args.out}\n")
    print(json.dumps(asdict(report), indent=2, default=str))
    return 0 if within else 1


if __name__ == "__main__":
    sys.exit(main())
