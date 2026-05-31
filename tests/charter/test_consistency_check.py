"""Tests for ``charter.consistency_check`` (WP07, T033).

Covers:
- ``test_coherent_when_all_activated_ids_exist_in_doctrine``: All activated IDs
  are real doctrine IDs → report is coherent.
- ``test_unknown_reference_detected``: A planted fake ID → appears in
  ``unknown_references``; ``coherent`` is False.
- ``test_suggestion_contains_resolution_command``: Suggestion for unknown ID
  contains "charter deactivate".
- ``test_none_kind_skipped``: A kind with None activation (no config key) is
  skipped and produces no ``unknown_references`` entry for that kind.
- ``test_coherent_false_when_incoherent``: Any unknown ID → coherent is False.
- ``test_run_consistency_check_returns_report_object``: Return type and field
  types are correct.
- ``test_run_consistency_check_completes_within_2s``: NFR-003 performance guard.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.consistency_check import ConsistencyReport, run_consistency_check
from charter.invocation_context import ProjectContext

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# A real directive ID that exists in the built-in doctrine.
# Used in coherent tests to avoid false unknowns.
# ---------------------------------------------------------------------------
_REAL_DIRECTIVE_ID = "001-architectural-integrity-standard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> None:
    """Write a .kittify/config.yaml with the given content."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _ctx_with_config(tmp_path: Path, config_yaml: str) -> ProjectContext:
    """Build a ProjectContext with the supplied config content."""
    _write_config(tmp_path, config_yaml)
    return ProjectContext.from_repo(tmp_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_coherent_when_all_activated_ids_exist_in_doctrine(tmp_path: Path) -> None:
    """Activating a real doctrine directive ID → report is coherent."""
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_ID}\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.unknown_references == []


@pytest.mark.doctrine
def test_unknown_reference_detected(tmp_path: Path) -> None:
    """A planted fake directive ID → appears in unknown_references."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any(fake_id in ref for ref in report.unknown_references), (
        f"Expected '{fake_id}' in unknown_references but got: "
        f"{report.unknown_references}"
    )
    assert report.coherent is False


@pytest.mark.doctrine
def test_suggestion_contains_resolution_command(tmp_path: Path) -> None:
    """Suggestion for an unknown ID must contain 'charter deactivate'."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any("charter deactivate" in s for s in report.suggestions), (
        f"Expected a suggestion containing 'charter deactivate' but got: "
        f"{report.suggestions}"
    )


@pytest.mark.doctrine
def test_none_kind_skipped(tmp_path: Path) -> None:
    """When a kind has no config key (None state), it is skipped silently.

    No 'directive/' entries should appear in unknown_references when
    activated_directives is absent from config.yaml.
    """
    # Config with no activated_directives key at all.
    ctx = _ctx_with_config(tmp_path, "# no activation keys\n")
    report = run_consistency_check(ctx)

    assert not any(
        ref.startswith("directive/") for ref in report.unknown_references
    ), (
        f"Expected no directive/ unknown_references but got: "
        f"{report.unknown_references}"
    )


@pytest.mark.doctrine
def test_coherent_false_when_incoherent(tmp_path: Path) -> None:
    """Any planted unknown ID → coherent is False."""
    ctx = _ctx_with_config(
        tmp_path,
        "activated_directives:\n  - totally-fake-id-xyz\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is False


@pytest.mark.doctrine
def test_run_consistency_check_returns_report_object(tmp_path: Path) -> None:
    """Return type is ConsistencyReport with correct field types."""
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")
    report = run_consistency_check(ctx)

    assert isinstance(report, ConsistencyReport)
    assert isinstance(report.coherent, bool)
    assert isinstance(report.unknown_references, list)
    assert isinstance(report.missing_from_doctrine, list)
    assert isinstance(report.kind_violations, list)
    assert isinstance(report.suggestions, list)


@pytest.mark.doctrine
def test_run_consistency_check_completes_within_2s(tmp_path: Path) -> None:
    """NFR-003: consistency check against the built-in doctrine must finish < 2s."""
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")

    start = time.perf_counter()
    run_consistency_check(ctx)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, (
        f"consistency check took {elapsed:.2f}s (limit: 2s)"
    )
