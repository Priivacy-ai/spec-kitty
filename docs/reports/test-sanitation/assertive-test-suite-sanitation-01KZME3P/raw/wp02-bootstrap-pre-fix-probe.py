"""Accelerated behavior probe for immutable-base issue #3283.

The immutable base holds one FileLock across the complete venv build with a
fixed 60-second waiter timeout. This controlled fault preserves that topology
while compressing 60/90 seconds to 0.25/1.0 seconds. Two spawned OS processes
exercise the live-owner timeout and direct-to-final partial publication.
"""

from __future__ import annotations

import multiprocessing
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout


IMMUTABLE_BASE = "28ae75ea998c898aba57364db7a06d2088bd2af2"
SOURCE_VERSION = "9.9.9"
LOCK_TIMEOUT_SECONDS = 0.25
BUILD_DELAY_SECONDS = 1.0


def _verify_immutable_base_topology() -> None:
    source = subprocess.run(
        ["git", "show", f"{IMMUTABLE_BASE}:tests/conftest.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    ensure_start = source.index("def _ensure_test_venv(")
    ensure_end = source.index("\ndef _venv_site_packages", ensure_start)
    ensure_source = source[ensure_start:ensure_end]
    assert "_LOCK_TIMEOUT_S = 60.0" in source
    assert "with FileLock(str(lock_path), timeout=_LOCK_TIMEOUT_S):" in ensure_source
    assert "_create_test_venv(venv_path, source_version)" in ensure_source
    assert ensure_source.index("with FileLock") < ensure_source.index("_create_test_venv")


def _legacy_valid(final_path: Path) -> bool:
    return (final_path / "VERSION").is_file() and (final_path / "READY").is_file()


def _legacy_fixed_lock_worker(
    project_root: str,
    start: Any,
    build_started: Any,
    outcomes: Any,
) -> None:
    start.wait()
    final_path = Path(project_root) / ".pytest_cache" / "spec-kitty-test-venv"
    lock_path = Path(project_root) / ".pytest_cache" / "spec-kitty-test-venv.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(lock_path), timeout=LOCK_TIMEOUT_SECONDS):
            if not _legacy_valid(final_path):
                shutil.rmtree(final_path, ignore_errors=True)
                final_path.mkdir(parents=True)
                (final_path / "BUILDING").write_text(str(multiprocessing.current_process().pid))
                build_started.set()
                time.sleep(BUILD_DELAY_SECONDS)
                (final_path / "READY").write_text("validated", encoding="utf-8")
                (final_path / "VERSION").write_text(SOURCE_VERSION, encoding="utf-8")
    except Timeout:
        outcomes.put(("timeout", multiprocessing.current_process().pid))
    else:
        outcomes.put(("published", multiprocessing.current_process().pid))


def main() -> int:
    _verify_immutable_base_topology()
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    build_started = context.Event()
    outcomes = context.Queue()
    with tempfile.TemporaryDirectory(prefix="wp02-pre-fix-") as temp_dir:
        builder = context.Process(
            target=_legacy_fixed_lock_worker,
            args=(temp_dir, start, build_started, outcomes),
        )
        builder.start()
        start.set()
        if not build_started.wait(timeout=5):
            raise RuntimeError("builder did not enter the live build")
        final_path = Path(temp_dir) / ".pytest_cache" / "spec-kitty-test-venv"
        partial_final_observed = final_path.is_dir() and not _legacy_valid(final_path)
        waiter = context.Process(
            target=_legacy_fixed_lock_worker,
            args=(temp_dir, start, build_started, outcomes),
        )
        waiter.start()
        builder.join(timeout=5)
        waiter.join(timeout=5)
        recorded = sorted(outcomes.get(timeout=1) for _ in range(2))

    timeout_count = sum(kind == "timeout" for kind, _pid in recorded)
    publication_count = sum(kind == "published" for kind, _pid in recorded)
    oracle_failed = partial_final_observed and timeout_count == publication_count == 1
    print(f"immutable_base={IMMUTABLE_BASE}")
    print("base_topology_verified=fixed lock encloses complete direct-to-final build")
    print(
        "fault=compress fixed lock timeout/build duration from 60s/>90s to "
        f"{LOCK_TIMEOUT_SECONDS}s/{BUILD_DELAY_SECONDS}s; heartbeat absent"
    )
    print("worker_topology=2 spawned OS processes; waiter starts after live builder enters Act")
    print(f"partial_final_observed={str(partial_final_observed).lower()}")
    print(f"outcomes={recorded}")
    print("intended_oracle=live owner completes while waiter never errors and no partial final is visible")
    print(f"oracle_failed={str(oracle_failed).lower()}")
    return 0 if oracle_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
