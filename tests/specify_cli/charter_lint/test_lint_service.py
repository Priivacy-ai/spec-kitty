"""Unit tests for LintService.get_decay_tile() (T016).

Parity tests verify output structure matches DecayWatchTileResponse TypedDict keys.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.charter_lint.service import LintService
from specify_cli.charter_lint.types import DecayWatchTileResponse

_EXPECTED_KEYS = {
    "has_data",
    "scanned_at",
    "orphan_count",
    "contradiction_count",
    "staleness_count",
    "reference_integrity_count",
    "high_severity_count",
    "total_count",
    "feature_scope",
    "duration_seconds",
}

_KITTIFY = ".kittify"
_REPORT = "lint-report.json"


def _write_report(project_dir: Path, data: dict) -> None:
    kittify = project_dir / _KITTIFY
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / _REPORT).write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# T016-1: missing report returns empty-like response
# ---------------------------------------------------------------------------


def test_no_report_returns_empty_response(tmp_path: Path) -> None:
    """Without a lint-report.json the tile must report has_data=False."""
    svc = LintService(tmp_path)
    result = svc.get_decay_tile()

    assert result["has_data"] is False
    assert result["total_count"] == 0
    assert result["scanned_at"] is None


# ---------------------------------------------------------------------------
# T016-2: parity — returned keys match DecayWatchTileResponse
# ---------------------------------------------------------------------------


def test_parity_keys_match_typeddict(tmp_path: Path) -> None:
    """Returned dict keys must exactly match DecayWatchTileResponse annotation."""
    _write_report(tmp_path, {"findings": [], "scanned_at": "2026-01-01T00:00:00Z"})
    result = LintService(tmp_path).get_decay_tile()

    assert set(result.keys()) == _EXPECTED_KEYS


# ---------------------------------------------------------------------------
# T016-3: counts are correct for a populated report
# ---------------------------------------------------------------------------


def test_counts_are_aggregated_correctly(tmp_path: Path) -> None:
    """Category and severity counts must be computed from findings list."""
    findings = [
        {"category": "orphan", "severity": "low"},
        {"category": "orphan", "severity": "high"},
        {"category": "contradiction", "severity": "critical"},
        {"category": "staleness", "severity": "medium"},
        {"category": "reference_integrity", "severity": "low"},
    ]
    _write_report(
        tmp_path,
        {
            "findings": findings,
            "scanned_at": "2026-05-01T12:00:00Z",
            "feature_scope": "myfeature",
            "duration_seconds": 1.23,
        },
    )
    result = LintService(tmp_path).get_decay_tile()

    assert result["has_data"] is True
    assert result["total_count"] == 5
    assert result["orphan_count"] == 2
    assert result["contradiction_count"] == 1
    assert result["staleness_count"] == 1
    assert result["reference_integrity_count"] == 1
    assert result["high_severity_count"] == 2  # high + critical
    assert result["scanned_at"] == "2026-05-01T12:00:00Z"
    assert result["feature_scope"] == "myfeature"
    assert result["duration_seconds"] == pytest.approx(1.23)


# ---------------------------------------------------------------------------
# T016-4: malformed JSON returns empty-like response (no exception leaks)
# ---------------------------------------------------------------------------


def test_malformed_json_returns_empty_response(tmp_path: Path) -> None:
    """A broken lint-report.json must not raise; returns empty-like response."""
    kittify = tmp_path / _KITTIFY
    kittify.mkdir(parents=True)
    (kittify / _REPORT).write_text("{not valid json!!!", encoding="utf-8")

    result = LintService(tmp_path).get_decay_tile()

    assert result["has_data"] is False
    assert result["total_count"] == 0


# ---------------------------------------------------------------------------
# T016-5: empty findings list is handled gracefully
# ---------------------------------------------------------------------------


def test_empty_findings_list(tmp_path: Path) -> None:
    """A report with zero findings must set has_data=True but all counts to 0."""
    _write_report(
        tmp_path,
        {"findings": [], "scanned_at": "2026-03-15T08:00:00Z"},
    )
    result = LintService(tmp_path).get_decay_tile()

    assert result["has_data"] is True
    assert result["total_count"] == 0
    assert result["high_severity_count"] == 0


# ---------------------------------------------------------------------------
# T016-6: optional fields default to None when absent from report
# ---------------------------------------------------------------------------


def test_optional_fields_default_to_none(tmp_path: Path) -> None:
    """feature_scope and duration_seconds should be None when not in report."""
    _write_report(tmp_path, {"findings": []})
    result = LintService(tmp_path).get_decay_tile()

    assert result["feature_scope"] is None
    assert result["duration_seconds"] is None
    assert result["scanned_at"] is None
