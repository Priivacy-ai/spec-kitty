"""Tests for src/specify_cli/audit/models.py (T001–T004)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.audit.models import (
    AuditOptions,
    MissionAuditResult,
    MissionFinding,
    RepoAuditReport,
    Severity,
)


# ---------------------------------------------------------------------------
# T001: Severity StrEnum
# ---------------------------------------------------------------------------


class TestSeverity:
    def test_has_exactly_three_members(self) -> None:
        members = list(Severity)
        assert len(members) == 3

    def test_member_names(self) -> None:
        assert Severity.ERROR
        assert Severity.WARNING
        assert Severity.INFO

    def test_string_values(self) -> None:
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"
        assert Severity.INFO == "info"

    def test_ordering_error_lt_warning(self) -> None:
        assert Severity.ERROR < Severity.WARNING

    def test_ordering_warning_lt_info(self) -> None:
        assert Severity.WARNING < Severity.INFO

    def test_ordering_error_lt_info(self) -> None:
        assert Severity.ERROR < Severity.INFO

    def test_le_same_member(self) -> None:
        assert Severity.ERROR <= Severity.ERROR
        assert Severity.WARNING <= Severity.WARNING
        assert Severity.INFO <= Severity.INFO

    def test_le_across_members(self) -> None:
        assert Severity.ERROR <= Severity.WARNING
        assert Severity.ERROR <= Severity.INFO
        assert Severity.WARNING <= Severity.INFO

    def test_not_lt_reversed(self) -> None:
        assert not (Severity.WARNING < Severity.ERROR)
        assert not (Severity.INFO < Severity.ERROR)
        assert not (Severity.INFO < Severity.WARNING)

    def test_not_le_reversed(self) -> None:
        assert not (Severity.WARNING <= Severity.ERROR)
        assert not (Severity.INFO <= Severity.ERROR)
        assert not (Severity.INFO <= Severity.WARNING)

    def test_is_str(self) -> None:
        assert isinstance(Severity.ERROR, str)

    def test_fail_on_threshold_pattern(self) -> None:
        """Verify the --fail-on threshold idiom works correctly."""
        findings = [
            MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="a.md"),
            MissionFinding(code="CORRUPT_JSONL", severity=Severity.ERROR, artifact_path="b.jsonl"),
        ]
        # fail_on=ERROR: only errors trigger failure
        assert any(f.severity <= Severity.ERROR for f in findings)
        # fail_on=WARNING: errors and warnings trigger failure
        assert any(f.severity <= Severity.WARNING for f in findings)
        # fail_on=INFO: everything triggers failure
        assert any(f.severity <= Severity.INFO for f in findings)


# ---------------------------------------------------------------------------
# T002: MissionFinding frozen dataclass
# ---------------------------------------------------------------------------


class TestMissionFinding:
    def test_basic_construction(self) -> None:
        f = MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="tasks/WP01.md")
        assert f.code == "LEGACY_KEY"
        assert f.severity == Severity.WARNING
        assert f.artifact_path == "tasks/WP01.md"
        assert f.detail is None

    def test_with_detail(self) -> None:
        f = MissionFinding(
            code="CORRUPT_JSONL",
            severity=Severity.ERROR,
            artifact_path="status.events.jsonl",
            detail="line 7 is not valid JSON",
        )
        assert f.detail == "line 7 is not valid JSON"

    def test_frozen_immutable(self) -> None:
        f = MissionFinding(code="X", severity=Severity.INFO, artifact_path="foo")
        with pytest.raises((AttributeError, TypeError)):
            f.code = "Y"  # type: ignore[misc]

    def test_hashable(self) -> None:
        f = MissionFinding(code="X", severity=Severity.INFO, artifact_path="foo")
        assert hash(f) is not None
        s: set[MissionFinding] = {f}
        assert f in s

    def test_to_dict_keys(self) -> None:
        f = MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="meta.json")
        d = f.to_dict()
        assert set(d.keys()) == {"code", "severity", "artifact_path", "detail"}

    def test_to_dict_severity_is_string(self) -> None:
        f = MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="meta.json")
        d = f.to_dict()
        assert d["severity"] == "warning"
        assert isinstance(d["severity"], str)

    def test_to_dict_detail_none(self) -> None:
        f = MissionFinding(code="X", severity=Severity.INFO, artifact_path="foo")
        assert f.to_dict()["detail"] is None

    def test_to_dict_detail_present(self) -> None:
        f = MissionFinding(code="X", severity=Severity.INFO, artifact_path="foo", detail="some detail")
        assert f.to_dict()["detail"] == "some detail"

    def test_to_dict_values(self) -> None:
        f = MissionFinding(
            code="IDENTITY_MISSING",
            severity=Severity.ERROR,
            artifact_path="meta.json",
            detail="mission_id field absent",
        )
        d = f.to_dict()
        assert d["code"] == "IDENTITY_MISSING"
        assert d["severity"] == "error"
        assert d["artifact_path"] == "meta.json"
        assert d["detail"] == "mission_id field absent"


# ---------------------------------------------------------------------------
# T003: MissionAuditResult dataclass
# ---------------------------------------------------------------------------


def _make_result(
    slug: str = "my-feature",
    findings: list[MissionFinding] | None = None,
) -> MissionAuditResult:
    return MissionAuditResult(
        mission_slug=slug,
        mission_dir=Path("kitty-specs") / slug,
        findings=findings or [],
    )


class TestMissionAuditResult:
    def test_has_errors_false_when_empty(self) -> None:
        r = _make_result()
        assert r.has_errors is False

    def test_has_errors_false_with_only_warnings(self) -> None:
        r = _make_result(
            findings=[MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="x")]
        )
        assert r.has_errors is False

    def test_has_errors_true(self) -> None:
        r = _make_result(
            findings=[MissionFinding(code="CORRUPT_JSONL", severity=Severity.ERROR, artifact_path="x")]
        )
        assert r.has_errors is True

    def test_has_warnings_false_when_empty(self) -> None:
        r = _make_result()
        assert r.has_warnings is False

    def test_has_warnings_false_with_only_errors(self) -> None:
        r = _make_result(
            findings=[MissionFinding(code="CORRUPT_JSONL", severity=Severity.ERROR, artifact_path="x")]
        )
        assert r.has_warnings is False

    def test_has_warnings_true(self) -> None:
        r = _make_result(
            findings=[MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="x")]
        )
        assert r.has_warnings is True

    def test_finding_codes(self) -> None:
        r = _make_result(
            findings=[
                MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="a"),
                MissionFinding(code="CORRUPT_JSONL", severity=Severity.ERROR, artifact_path="b"),
                MissionFinding(code="LEGACY_KEY", severity=Severity.WARNING, artifact_path="c"),
            ]
        )
        assert r.finding_codes == {"LEGACY_KEY", "CORRUPT_JSONL"}

    def test_to_dict_keys(self) -> None:
        r = _make_result()
        d = r.to_dict()
        assert "mission_slug" in d
        assert "mission_dir" in d
        assert "findings" in d
        assert "finding_count" in d
        assert "has_errors" in d

    def test_to_dict_mission_dir_is_string(self) -> None:
        r = _make_result()
        d = r.to_dict()
        assert isinstance(d["mission_dir"], str)

    def test_to_dict_finding_count(self) -> None:
        r = _make_result(
            findings=[
                MissionFinding(code="X", severity=Severity.INFO, artifact_path="a"),
                MissionFinding(code="Y", severity=Severity.INFO, artifact_path="b"),
            ]
        )
        assert r.to_dict()["finding_count"] == 2


# ---------------------------------------------------------------------------
# T004: RepoAuditReport and AuditOptions
# ---------------------------------------------------------------------------


class TestRepoAuditReport:
    def _make_report(self) -> RepoAuditReport:
        return RepoAuditReport(
            missions=[_make_result("alpha"), _make_result("beta")],
            shape_counters={"CORRUPT_JSONL": 2, "LEGACY_KEY": 5, "ACTOR_DRIFT": 1},
            repo_summary={
                "total_missions": 2,
                "missions_with_errors": 0,
                "missions_with_warnings": 0,
                "total_findings": 0,
                "findings_by_severity": {"error": 0, "warning": 0, "info": 0},
            },
        )

    def test_to_dict_top_level_keys(self) -> None:
        d = self._make_report().to_dict()
        assert set(d.keys()) == {"missions", "shape_counters", "repo_summary"}

    def test_to_dict_shape_counters_sorted(self) -> None:
        report = self._make_report()
        d = report.to_dict()
        keys = list(d["shape_counters"].keys())  # type: ignore[union-attr]
        assert keys == sorted(keys)

    def test_to_dict_shape_counters_values(self) -> None:
        report = self._make_report()
        d = report.to_dict()
        sc = d["shape_counters"]
        assert sc == {"ACTOR_DRIFT": 1, "CORRUPT_JSONL": 2, "LEGACY_KEY": 5}  # type: ignore[comparison-overlap]

    def test_empty_missions(self) -> None:
        report = RepoAuditReport(
            missions=[],
            shape_counters={},
            repo_summary={},
        )
        d = report.to_dict()
        assert d["missions"] == []
        assert d["shape_counters"] == {}

    def test_missions_serialized(self) -> None:
        report = self._make_report()
        d = report.to_dict()
        assert isinstance(d["missions"], list)
        assert len(d["missions"]) == 2  # type: ignore[arg-type]


class TestAuditOptions:
    def test_required_repo_root(self) -> None:
        opts = AuditOptions(repo_root=Path("/repo"))
        assert opts.repo_root == Path("/repo")

    def test_defaults(self) -> None:
        opts = AuditOptions(repo_root=Path("/repo"))
        assert opts.scan_root is None
        assert opts.mission_filter is None
        assert opts.fail_on is None

    def test_with_all_fields(self) -> None:
        opts = AuditOptions(
            repo_root=Path("/repo"),
            scan_root=Path("/repo/kitty-specs"),
            mission_filter="my-feature",
            fail_on=Severity.ERROR,
        )
        assert opts.scan_root == Path("/repo/kitty-specs")
        assert opts.mission_filter == "my-feature"
        assert opts.fail_on == Severity.ERROR

    def test_fail_on_warning_threshold(self) -> None:
        opts = AuditOptions(repo_root=Path("/repo"), fail_on=Severity.WARNING)
        assert opts.fail_on == Severity.WARNING
        assert opts.fail_on <= Severity.WARNING
        # error is also <= warning (more severe)
        assert opts.fail_on >= Severity.ERROR  # type: ignore[operator]
