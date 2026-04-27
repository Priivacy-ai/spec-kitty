"""Shared fixtures for the cli_gate integration test suite (WP08 / T033)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


# ---------------------------------------------------------------------------
# Project-state fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fixture_project_compatible(tmp_path: Path) -> Path:
    """Return a project root with schema_version 3 (compatible with MIN=MAX=3)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(
        "spec_kitty:\n  schema_version: 3\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def fixture_project_stale(tmp_path: Path) -> Path:
    """Return a project root with schema_version 1 (< MIN=3 → STALE)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(
        "spec_kitty:\n  schema_version: 1\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def fixture_project_too_new(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a project root with schema_version 7 (> MAX=3 → TOO_NEW).

    MAX_SUPPORTED_SCHEMA is monkeypatched to 6 to make the test independent
    of the current live constant while still ensuring 7 > max_supported.
    """
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(
        "spec_kitty:\n  schema_version: 7\n",
        encoding="utf-8",
    )
    # Patch MAX_SUPPORTED_SCHEMA so schema 7 is definitively too new
    # regardless of future schema bumps.
    import specify_cli.migration.schema_version as sv

    monkeypatch.setattr(sv, "MAX_SUPPORTED_SCHEMA", 6)
    return tmp_path


@pytest.fixture()
def fixture_project_corrupt(tmp_path: Path) -> Path:
    """Return a project root with an oversized (300 KiB) metadata.yaml (CORRUPT)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    # 300 KiB > 256 KiB limit → planner returns BLOCK_PROJECT_CORRUPT
    (kittify / "metadata.yaml").write_bytes(b"x" * (300 * 1024))
    return tmp_path


# ---------------------------------------------------------------------------
# CLI runner fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def cli_runner() -> CliRunner:
    """Return a typer CliRunner configured for the spec-kitty app."""
    # mix_stderr=False keeps stderr separate from stdout in Result.
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Network-blocker fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def network_blocker(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch httpx.Client.get to raise AssertionError on any real network call.

    Returns the mock so callers can assert call_count == 0.
    """
    mock = MagicMock(side_effect=AssertionError("network call blocked in test"))
    monkeypatch.setattr("httpx.Client.get", mock)
    return mock
