"""Tests for src/specify_cli/audit/serializer.py (T005).

The determinism test (NFR-001) is the most important test here: calling
``build_report_json()`` twice on the same object must produce byte-identical
output.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.audit.models import (
    MissionAuditResult,
    MissionFinding,
    RepoAuditReport,
    Severity,
)
from specify_cli.audit.serializer import build_report_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(code: str, severity: Severity, artifact_path: str, detail: str | None = None) -> MissionFinding:
    return MissionFinding(code=code, severity=severity, artifact_path=artifact_path, detail=detail)


def _result(slug: str, findings: list[MissionFinding]) -> MissionAuditResult:
    return MissionAuditResult(
        mission_slug=slug,
        mission_dir=Path("kitty-specs") / slug,
        findings=findings,
    )


def _rich_report() -> RepoAuditReport:
    """Build a report with >=3 missions covering all 3 severity levels."""
    alpha_findings = [
        _finding("CORRUPT_JSONL", Severity.ERROR, "status.events.jsonl", "line 3 malformed"),
        _finding("LEGACY_KEY", Severity.WARNING, "meta.json"),
        _finding("UNKNOWN_SHAPE", Severity.INFO, "tasks/WP01.md"),
    ]
    beta_findings = [
        _finding("IDENTITY_MISSING", Severity.ERROR, "meta.json"),
        _finding("ACTOR_DRIFT", Severity.WARNING, "status.events.jsonl", "actor mismatch"),
    ]
    gamma_findings = [
        _finding("DUPLICATE_PREFIX", Severity.WARNING, "meta.json"),
        _finding("UNKNOWN_SHAPE", Severity.INFO, "spec.md"),
    ]
    return RepoAuditReport(
        missions=[
            _result("alpha-mission", alpha_findings),
            _result("beta-mission", beta_findings),
            _result("gamma-mission", gamma_findings),
        ],
        shape_counters={
            "CORRUPT_JSONL": 1,
            "LEGACY_KEY": 1,
            "UNKNOWN_SHAPE": 2,
            "IDENTITY_MISSING": 1,
            "ACTOR_DRIFT": 1,
            "DUPLICATE_PREFIX": 1,
        },
        repo_summary={
            "total_missions": 3,
            "missions_with_errors": 2,
            "missions_with_warnings": 3,
            "total_findings": 7,
            "findings_by_severity": {"error": 2, "warning": 4, "info": 1},
        },
    )


# ---------------------------------------------------------------------------
# NFR-001: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_byte_identical_on_same_object(self) -> None:
        """Calling build_report_json() twice on the same object is byte-identical."""
        report = _rich_report()
        first = build_report_json(report)
        second = build_report_json(report)
        assert first == second, "build_report_json() must produce identical output on repeated calls"

    def test_byte_identical_on_equal_objects(self) -> None:
        """Two independently constructed equal reports serialize identically."""
        report_a = _rich_report()
        report_b = _rich_report()
        assert build_report_json(report_a) == build_report_json(report_b)

    def test_valid_json(self) -> None:
        result = build_report_json(_rich_report())
        # Must not raise
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_top_level_keys_present(self) -> None:
        result = build_report_json(_rich_report())
        parsed = json.loads(result)
        assert "missions" in parsed
        assert "shape_counters" in parsed
        assert "repo_summary" in parsed

    def test_uses_indent_2(self) -> None:
        """Output must be pretty-printed with indent=2."""
        result = build_report_json(_rich_report())
        # A pretty-printed JSON has lines starting with "  " (two spaces)
        lines = result.splitlines()
        indented = [ln for ln in lines if ln.startswith("  ")]
        assert len(indented) > 0, "Expected indented output"

    def test_keys_sorted(self) -> None:
        """sort_keys=True means dict keys appear in lexicographic order."""
        result = build_report_json(_rich_report())
        parsed = json.loads(result)
        # shape_counters must be in sorted order
        sc_keys = list(parsed["shape_counters"].keys())
        assert sc_keys == sorted(sc_keys)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEmptyReport:
    def test_zero_missions(self) -> None:
        report = RepoAuditReport(
            missions=[],
            shape_counters={},
            repo_summary={
                "total_missions": 0,
                "missions_with_errors": 0,
                "missions_with_warnings": 0,
                "total_findings": 0,
                "findings_by_severity": {"error": 0, "warning": 0, "info": 0},
            },
        )
        result = build_report_json(report)
        parsed = json.loads(result)
        assert parsed["missions"] == []
        assert parsed["shape_counters"] == {}
        assert "repo_summary" in parsed

    def test_empty_report_is_deterministic(self) -> None:
        report = RepoAuditReport(missions=[], shape_counters={}, repo_summary={})
        assert build_report_json(report) == build_report_json(report)


class TestSingleMission:
    def test_single_finding_round_trips(self) -> None:
        report = RepoAuditReport(
            missions=[
                _result(
                    "solo-mission",
                    [_finding("LEGACY_KEY", Severity.WARNING, "meta.json", "found 'lane' key")],
                )
            ],
            shape_counters={"LEGACY_KEY": 1},
            repo_summary={"total_missions": 1},
        )
        result = build_report_json(report)
        parsed = json.loads(result)
        mission = parsed["missions"][0]
        assert mission["mission_slug"] == "solo-mission"
        finding = mission["findings"][0]
        assert finding["code"] == "LEGACY_KEY"
        assert finding["severity"] == "warning"
        assert finding["artifact_path"] == "meta.json"
        assert finding["detail"] == "found 'lane' key"
