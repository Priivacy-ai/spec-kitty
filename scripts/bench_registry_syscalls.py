#!/usr/bin/env python3
"""Benchmark dashboard syscall counts with and without the MissionRegistry.

Spawns the dashboard under both transports for 30s each, traces openat/stat/statx
syscalls via strace, polls /api/features once per second, and writes a JSON
comparison report.

NOTE: This script requires Linux and strace. On macOS, use dtruss instead;
macOS measurements are advisory only. The canonical NFR verification must be
performed on Linux.

If strace -p is denied (kernel.yama.ptrace_scope!=0), run the dashboard process
under strace from the start by patching _bench_stack to use strace as a wrapper
instead of attaching via -p.

Usage:
    .venv/bin/python scripts/bench_registry_syscalls.py [--out /tmp/bench-registry-syscalls.json]
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class StackBenchmark:
    transport: str
    duration_seconds: float
    poll_count: int
    openat_total: int
    stat_total: int
    statx_total: int
    openat_per_request: float
    stat_per_request: float


@dataclass
class BenchmarkReport:
    machine: str
    python: str
    project_path: str
    legacy: StackBenchmark
    registry: StackBenchmark
    nfr_001_threshold_syscalls: int
    nfr_001_legacy_within_threshold: bool
    nfr_001_registry_within_threshold: bool
    nfr_002_threshold_factor: float
    nfr_002_within_threshold: bool


def _wait_for_port(port: int, timeout: float = 30.0) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.socket() as sock:
                sock.settimeout(0.1)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    return True
        except OSError:
            pass
        time.sleep(0.05)
    return False


def _bench_stack(transport: str, project_dir: Path, port: int, duration: int = 30) -> StackBenchmark:
    """Spawn the dashboard under strace, poll for `duration` seconds, parse the output.

    Runs the dashboard process *wrapped* by strace (rather than attaching with -p)
    to work around kernel.yama.ptrace_scope=1 on hardened Linux systems where
    only the parent process can attach to a child.

    For the 'fastapi' transport, we bypass the CLI's single-instance-per-project-root
    guard by launching uvicorn directly with create_app(). This allows two transports
    to run on different ports simultaneously for side-by-side measurement.
    """
    if transport == "fastapi":
        # Bypass CLI single-instance guard by launching uvicorn directly.
        # Build a small inline script that adds src/ to sys.path then starts uvicorn.
        src_dir = str((Path(__file__).parent.parent / "src").resolve())
        shim = (
            f"import sys, uvicorn; sys.path.insert(0, {src_dir!r}); "
            f"from pathlib import Path; from dashboard.api.app import create_app; "
            f"app = create_app(project_dir=Path({str(project_dir.resolve())!r}), project_token=None); "
            f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='error')"
        )
        dashboard_cmd = [sys.executable, "-c", shim]
    else:
        dashboard_cmd = [
            sys.executable, "-m", "specify_cli", "dashboard",
            "--transport", transport,
            "--port", str(port),
        ]
    # Run strace as the parent, wrapping the dashboard process.
    # -f: follow child processes spawned by the target.
    # -c: summary mode (writes report on exit).
    # -e trace=openat,stat,statx: only the filesystem syscalls that matter.
    strace_cmd = [
        "strace", "-f", "-c", "-e", "trace=openat,stat,statx",
    ] + dashboard_cmd

    strace_proc = subprocess.Popen(
        strace_cmd,
        cwd=str(project_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_for_port(port, timeout=30):
            strace_proc.terminate()
            strace_proc.wait(timeout=5)
            raise RuntimeError(f"Dashboard ({transport}) did not bind {port} in 30s")

        poll_count = 0
        start = time.monotonic()
        while time.monotonic() - start < duration:
            subprocess.run(
                ["curl", "-s", "-o", "/dev/null", f"http://127.0.0.1:{port}/api/features"],
                check=False,
            )
            poll_count += 1
            time.sleep(1.0)

        strace_proc.terminate()
        _, stderr = strace_proc.communicate(timeout=10)
        # Parse strace -c output: lines like " 35.42  0.000123     1   123       openat"
        openat_total = stat_total = statx_total = 0
        for line in stderr.decode().splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[-1] in ("openat", "stat", "statx"):
                try:
                    count = int(parts[3])
                except (IndexError, ValueError):
                    continue
                if parts[-1] == "openat":
                    openat_total = count
                elif parts[-1] == "stat":
                    stat_total = count
                elif parts[-1] == "statx":
                    statx_total = count
        return StackBenchmark(
            transport=transport,
            duration_seconds=duration,
            poll_count=poll_count,
            openat_total=openat_total,
            stat_total=stat_total,
            statx_total=statx_total,
            openat_per_request=openat_total / max(poll_count, 1),
            stat_per_request=(stat_total + statx_total) / max(poll_count, 1),
        )
    except Exception:
        strace_proc.terminate()
        try:
            strace_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            strace_proc.kill()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/tmp/bench-registry-syscalls.json"))
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    print(f"Benchmarking legacy transport (port 19000) for {args.duration}s...", flush=True)
    legacy = _bench_stack("legacy", args.project_dir, 19000, args.duration)
    print(f"  openat/req={legacy.openat_per_request:.2f}  stat+statx/req={legacy.stat_per_request:.2f}", flush=True)

    print(f"Benchmarking fastapi transport (port 19001) for {args.duration}s...", flush=True)
    registry = _bench_stack("fastapi", args.project_dir, 19001, args.duration)
    print(f"  openat/req={registry.openat_per_request:.2f}  stat+statx/req={registry.stat_per_request:.2f}", flush=True)

    nfr_001_threshold = 5
    nfr_002_threshold = 1.25  # 25% regression allowed
    legacy_within_001 = legacy.openat_per_request <= nfr_001_threshold
    registry_within_001 = registry.openat_per_request <= nfr_001_threshold
    legacy_openat = legacy.openat_per_request
    nfr_002_factor = (registry.openat_per_request / max(legacy_openat, 1)) if legacy_openat > 0 else 0.0
    nfr_002_within = nfr_002_factor <= nfr_002_threshold

    report = BenchmarkReport(
        machine=platform.uname().release,
        python=platform.python_version(),
        project_path=str(args.project_dir.resolve()),
        legacy=legacy,
        registry=registry,
        nfr_001_threshold_syscalls=nfr_001_threshold,
        nfr_001_legacy_within_threshold=legacy_within_001,
        nfr_001_registry_within_threshold=registry_within_001,
        nfr_002_threshold_factor=nfr_002_threshold,
        nfr_002_within_threshold=nfr_002_within,
    )
    report_json = json.dumps(asdict(report), indent=2, default=str)
    args.out.write_text(report_json, encoding="utf-8")
    print(f"\nReport written to {args.out}")
    print(report_json)

    if not (registry_within_001 and nfr_002_within):
        print("\n⚠️  One or more NFR thresholds exceeded. See report above.", file=sys.stderr)
        return 1
    print("\n✅ All NFR thresholds met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
