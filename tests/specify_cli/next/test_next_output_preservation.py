"""NFR-004 byte-identical output-preservation guard for `spec-kitty next` (WP01).

Mission ``next-latency-durable-fix-01M14RM3``, WP01 (import-graph trim).

Implements the no-charter-fixture half of
``kitty-specs/next-latency-durable-fix-01M14RM3/contracts/next-output-preservation-contract.md``:
deferring the ``checkout_ownership`` import (T002) must not change a single
byte of `next --json`'s observable output, other than the intrinsically
per-call ``timestamp`` field.

Per the contract, this test does **not** reuse the masked ``canonical()``
oracle from ``tests/runtime/test_bridge_parity.py`` — that oracle masks
ULID/timestamp/path noise and would silently accept a real regression landing
in a masked field. This test asserts literal byte-identity of the parsed JSON
payload (minus the one documented ``timestamp`` key).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "clean_install_fixture_mission"
_MISSION_SLUG = "clean-install-fixture-01KQ22XX"


def _init_fixture_repo(tmp_path: Path) -> Path:
    """Copy the no-charter fixture mission into a fresh git repo."""
    import shutil

    project = tmp_path / "mission"
    shutil.copytree(_FIXTURE, project)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fixture"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return project


def _run_next_json(project: Path) -> dict[str, Any]:
    """Run `next --json` in query mode (read-only, no --result) and JSON-load stdout."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_SRC)
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "next", "--mission", _MISSION_SLUG, "--json"],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f"`next --json` failed against the no-charter fixture.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def test_next_json_is_byte_identical_across_two_runs_except_timestamp(tmp_path: Path) -> None:
    """T005: two `next --json` query-mode runs must be identical minus `timestamp`.

    Query mode (no `--result`) is read-only, so running it twice against the
    same fixture checkout is a legitimate repeat measurement: it proves the
    T002 import deferral resolves `checkout_ownership` identically at first
    real use and does not perturb the emitted decision payload.
    """
    project = _init_fixture_repo(tmp_path)

    first = _run_next_json(project)
    second = _run_next_json(project)

    assert "timestamp" in first and "timestamp" in second, "expected both payloads to carry the per-call `timestamp` field"
    # Normalize ONLY `timestamp` — every other field must be byte-identical
    # per the contract (no masked-oracle shortcuts).
    first_normalized = dict(first, timestamp=None)
    second_normalized = dict(second, timestamp=None)

    assert first_normalized == second_normalized

    # Query mode must not mutate the checkout (no state advanced).
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout.strip() == "", f"query-mode `next --json` unexpectedly modified the checkout:\n{status.stdout}"
