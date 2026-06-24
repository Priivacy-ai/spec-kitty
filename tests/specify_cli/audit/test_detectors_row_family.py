"""Regression matrix for the audit row-family classifier (WP01, #1122).

These tests pin the behavioral contract documented in
``kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/contracts/
audit-row-family.md`` so a regression in either:

- ``specify_cli.audit.shape_registry.is_mission_lifecycle_row``, or
- ``specify_cli.audit.detectors.detect_forbidden_keys``

will surface as a failing unit test rather than a runtime ``FORBIDDEN_KEY``
finding on a fresh mission's lifecycle rows (the user-visible bug in
``Priivacy-ai/spec-kitty#1122``).

The matrix has one test per row shape in the contract's "Behavioral contract"
table. A final end-to-end test runs the real ``run_audit`` engine against a
tmp ``kitty-specs/`` tree seeded with a mix of legitimate lifecycle rows and
canonical status-transition rows, and asserts zero ``FORBIDDEN_KEY`` findings
on the lifecycle rows while still flagging a synthetic malformed row that
carries ``event_type`` outside the lifecycle family.

NB: this regression test does NOT shell out to ``spec-kitty agent mission
create``. The contract under test is purely the audit-side classifier; the
mission-create writers are already covered by ``tests/status/`` and are
out-of-scope for WP01's owned files. Driving ``run_audit`` against a tmp tree
populated with the exact row shapes that ``status/lifecycle_events.py`` emits
is the smallest-viable diff that proves the bug is fixed end-to-end.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]
from specify_cli.audit.detectors import detect_forbidden_keys
from specify_cli.audit.engine import run_audit
from specify_cli.audit.models import AuditOptions
from specify_cli.audit.shape_registry import (
    check_unknown_keys,
    is_decisionpoint_status_event_row,
    is_mission_lifecycle_row,
    status_event_row_artifact_type,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding_codes(findings: list[Any]) -> list[str]:
    return [f.code for f in findings]


def _seed_mission(
    kitty_specs: Path,
    slug: str,
    *,
    mission_id: str,
    rows: list[Mapping[str, Any]],
) -> Path:
    """Create a minimal mission directory with a status.events.jsonl seeded.

    Writes only the artifacts the audit engine needs to traverse the mission:
    ``meta.json`` (so the identity adapter sees a registered mission) and
    ``status.events.jsonl`` (the file under test). The audit engine treats
    missing optional artifacts as "nothing to check", not as findings, so we
    deliberately leave out ``status.json`` / ``tasks/`` to keep the test
    surface narrow.
    """
    mission_dir = kitty_specs / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_id": mission_id,
        "mission_slug": slug,
        "friendly_name": slug.replace("-", " ").title(),
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-05-19T00:00:00+00:00",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta, sort_keys=True))
    with (mission_dir / "status.events.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True))
            fh.write("\n")
    return mission_dir


# ---------------------------------------------------------------------------
# Predicate-level tests — pins is_mission_lifecycle_row directly
# ---------------------------------------------------------------------------


class TestIsMissionLifecycleRow:
    """Direct tests for the row-family classifier predicate."""

    def test_lifecycle_row_with_aggregate_and_event_type(self) -> None:
        row = {"aggregate_type": "Mission", "event_type": "MissionCreated"}
        assert is_mission_lifecycle_row(row) is True

    def test_lifecycle_row_specify_started(self) -> None:
        row = {"aggregate_type": "Mission", "event_type": "SpecifyStarted"}
        assert is_mission_lifecycle_row(row) is True

    def test_lifecycle_row_project_aggregate(self) -> None:
        """Issue #1142: ``Project`` aggregate is a lifecycle row family member."""
        row = {"aggregate_type": "Project", "event_type": "ProjectRegistered"}
        assert is_mission_lifecycle_row(row) is True

    def test_lifecycle_row_work_package_aggregate(self) -> None:
        """Issue #1142: ``WorkPackage`` aggregate is a lifecycle row family member.

        Pre-#1142 this row was mis-classified as a malformed status-transition
        row and raised ``FORBIDDEN_KEY`` for the legitimate ``event_type`` key.
        """
        row = {"aggregate_type": "WorkPackage", "event_type": "WPStatusChanged"}
        assert is_mission_lifecycle_row(row) is True

    def test_lifecycle_row_mission_dossier_aggregate(self) -> None:
        """Issue #1142: ``MissionDossier`` aggregate is a lifecycle row family member."""
        row = {
            "aggregate_type": "MissionDossier",
            "event_type": "MissionDossierArtifactIndexed",
        }
        assert is_mission_lifecycle_row(row) is True

    def test_event_type_without_aggregate_is_not_lifecycle(self) -> None:
        """Either-or alone must NOT classify — both must hold (AND, not OR)."""
        row = {"event_type": "Foo"}
        assert is_mission_lifecycle_row(row) is False

    def test_aggregate_without_event_type_is_not_lifecycle(self) -> None:
        row = {"aggregate_type": "Mission"}
        assert is_mission_lifecycle_row(row) is False

    def test_aggregate_with_empty_event_type_is_not_lifecycle(self) -> None:
        """An empty ``event_type`` does not count as the lifecycle discriminator."""
        row = {"aggregate_type": "Mission", "event_type": ""}
        assert is_mission_lifecycle_row(row) is False

    def test_aggregate_with_non_string_event_type_is_not_lifecycle(self) -> None:
        row = {"aggregate_type": "Mission", "event_type": 123}
        assert is_mission_lifecycle_row(row) is False

    def test_non_mapping_input_is_not_lifecycle(self) -> None:
        """The predicate must be conservative on garbage input — return False."""
        assert is_mission_lifecycle_row(["not", "a", "mapping"]) is False  # type: ignore[arg-type]

    def test_unknown_aggregate_is_not_lifecycle(self) -> None:
        """Issue #1142 regression guard: aggregate_types outside the known set still reject.

        The fix accepts ``{Mission, Project, WorkPackage, MissionDossier}``.
        Any other value (typo, drift, hand-edit) must still be rejected so the
        ``FORBIDDEN_KEYS`` rule retains its teeth against malformed rows.
        """
        row = {"aggregate_type": "Foo", "event_type": "Bar"}
        assert is_mission_lifecycle_row(row) is False

    def test_transition_discriminators_are_not_lifecycle(self) -> None:
        row = {
            "aggregate_type": "WorkPackage",
            "event_type": "WPStatusChanged",
            "from_lane": "planned",
            "to_lane": "claimed",
        }
        assert is_mission_lifecycle_row(row) is False

    def test_none_aggregate_is_not_lifecycle(self) -> None:
        row = {"aggregate_type": None, "event_type": "Bar"}
        assert is_mission_lifecycle_row(row) is False

    def test_empty_aggregate_is_not_lifecycle(self) -> None:
        row = {"aggregate_type": "", "event_type": "Bar"}
        assert is_mission_lifecycle_row(row) is False


class TestIsDecisionPointStatusEventRow:
    """Direct tests for DecisionPoint rows sharing ``status.events.jsonl``."""

    def test_decisionpoint_event_envelope_is_decisionpoint_row(self) -> None:
        row = {
            "event_id": "01KTESTDECISIONEVENT0000001",
            "at": "2026-05-31T12:00:00+00:00",
            "event_type": "DecisionPointOpened",
            "payload": {"decision_point_id": "01KTESTDECISION0000000001"},
        }
        assert is_decisionpoint_status_event_row(row) is True

    def test_decisionpoint_event_without_payload_is_not_decisionpoint_row(self) -> None:
        row = {"event_type": "DecisionPointOpened"}
        assert is_decisionpoint_status_event_row(row) is False

    def test_hybrid_transition_keys_are_not_decisionpoint_row(self) -> None:
        row = {
            "event_id": "01KTESTDECISIONEVENT0000001",
            "at": "2026-05-31T12:00:00+00:00",
            "event_type": "DecisionPointOpened",
            "payload": {"decision_point_id": "01KTESTDECISION0000000001"},
            "wp_id": "WP01",
        }
        assert is_decisionpoint_status_event_row(row) is False


# ---------------------------------------------------------------------------
# Behavioral contract matrix — one test per row in the contract table
# ---------------------------------------------------------------------------


class TestDetectForbiddenKeysRowFamily:
    """Pins ``detect_forbidden_keys`` against the contract's row table.

    Contract: ``kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/
    contracts/audit-row-family.md``.
    """

    def test_status_transition_row_passes(self) -> None:
        """Row 1: canonical transition row — FORBIDDEN_KEY check runs, passes."""
        row: dict[str, object] = {
            "from_lane": "planned",
            "to_lane": "claimed",
            "wp_id": "WP01",
            "actor": "claude",
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_lifecycle_row_mission_created_skipped(self) -> None:
        """Row 2: lifecycle row (Mission/MissionCreated) — check SKIPPED."""
        row: dict[str, object] = {
            "aggregate_type": "Mission",
            "event_type": "MissionCreated",
            "event_id": "01HXYZ",
            "at": "2026-05-19T00:00:00+00:00",
            "payload": {"foo": "bar"},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == [], (
            "Lifecycle rows legitimately carry `event_type` and must not be "
            "flagged. Regression of WP01 / issue #1122."
        )

    def test_lifecycle_row_specify_started_skipped(self) -> None:
        """Row 3: lifecycle row (Mission/SpecifyStarted) — check SKIPPED."""
        row: dict[str, object] = {
            "aggregate_type": "Mission",
            "event_type": "SpecifyStarted",
            "event_id": "01HXYZ",
            "at": "2026-05-19T00:00:00+00:00",
            "payload": {},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_event_type_without_aggregate_is_flagged(self) -> None:
        """Row 4: ``event_type`` present, no ``aggregate_type`` — FLAGGED.

        This is the regression-guard half of the contract: malformed
        pre-migration rows that carry ``event_type`` without the lifecycle
        aggregate marker must still surface as ``FORBIDDEN_KEY`` findings,
        otherwise the TeamSpace blocker rule loses its teeth.
        """
        row: dict[str, object] = {"event_type": "Foo"}
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        codes = _finding_codes(findings)
        assert codes == ["FORBIDDEN_KEY"]
        assert "event_type" in (findings[0].detail or "")

    def test_aggregate_without_event_type_passes(self) -> None:
        """Row 5: ``aggregate_type=Mission``, no ``event_type`` — passes.

        Predicate returns False (no event_type), so the FORBIDDEN_KEY check
        runs. The row has no forbidden key present, so the check passes.
        """
        row: dict[str, object] = {"aggregate_type": "Mission"}
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_malformed_transition_with_event_type_is_flagged(self) -> None:
        """Row 6: malformed transition row carrying lifecycle discriminator.

        Has ``from_lane`` + ``to_lane`` (transition shape) AND ``event_type``
        (lifecycle discriminator) but no ``aggregate_type=Mission``. Predicate
        returns False, check runs, ``event_type`` is flagged.
        """
        row: dict[str, object] = {
            "from_lane": "planned",
            "to_lane": "claimed",
            "event_type": "X",
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        codes = _finding_codes(findings)
        assert codes == ["FORBIDDEN_KEY"]
        assert "event_type" in (findings[0].detail or "")

    def test_event_name_without_aggregate_is_flagged(self) -> None:
        """Sibling regression guard for the second forbidden key (event_name)."""
        row: dict[str, object] = {"event_name": "legacy_thing"}
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        codes = _finding_codes(findings)
        assert codes == ["FORBIDDEN_KEY"]

    def test_decisionpoint_event_envelope_skipped(self) -> None:
        row: dict[str, object] = {
            "event_id": "01KTESTDECISIONEVENT0000001",
            "at": "2026-05-31T12:00:00+00:00",
            "event_type": "DecisionPointOpened",
            "payload": {"decision_point_id": "01KTESTDECISION0000000001"},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_decisionpoint_event_without_payload_is_flagged(self) -> None:
        row: dict[str, object] = {"event_type": "DecisionPointOpened"}
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        codes = _finding_codes(findings)
        assert codes == ["FORBIDDEN_KEY"]

    def test_hybrid_decisionpoint_transition_row_is_flagged(self) -> None:
        row: dict[str, object] = {
            "event_id": "01KTESTDECISIONEVENT0000001",
            "at": "2026-05-31T12:00:00+00:00",
            "event_type": "DecisionPointOpened",
            "payload": {"decision_point_id": "01KTESTDECISION0000000001"},
            "wp_id": "WP01",
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        codes = _finding_codes(findings)
        assert codes == ["FORBIDDEN_KEY"]

    def test_lifecycle_row_work_package_skipped(self) -> None:
        """Issue #1142: ``WorkPackage`` lifecycle rows skip the FORBIDDEN_KEYS rule.

        Pre-fix the audit raised ``FORBIDDEN_KEY`` against this legitimate row
        shape, blocking the canary's scenarios 1 + 2 with a TeamSpace gate.
        """
        row: dict[str, object] = {
            "aggregate_type": "WorkPackage",
            "event_type": "WPStatusChanged",
            "event_id": "01HXYZ",
            "at": "2026-05-19T00:00:00+00:00",
            "payload": {"wp_id": "WP01"},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == [], (
            "Issue #1142 regression: WorkPackage lifecycle rows must not "
            "trigger FORBIDDEN_KEY findings."
        )

    def test_lifecycle_row_project_skipped(self) -> None:
        """Issue #1142: ``Project`` lifecycle rows skip the FORBIDDEN_KEYS rule."""
        row: dict[str, object] = {
            "aggregate_type": "Project",
            "event_type": "ProjectRegistered",
            "event_id": "01HXYZ",
            "at": "2026-05-19T00:00:00+00:00",
            "payload": {},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_lifecycle_row_mission_dossier_skipped(self) -> None:
        """Issue #1142: ``MissionDossier`` lifecycle rows skip the FORBIDDEN_KEYS rule."""
        row: dict[str, object] = {
            "aggregate_type": "MissionDossier",
            "event_type": "MissionDossierArtifactIndexed",
            "event_id": "01HXYZ",
            "at": "2026-05-19T00:00:00+00:00",
            "payload": {},
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []

    def test_lifecycle_row_with_event_name_still_skipped(self) -> None:
        """Both forbidden keys are scoped out for lifecycle rows.

        ``event_name`` is the other member of ``FORBIDDEN_KEYS``. A lifecycle
        row that happens to carry ``event_name`` (hypothetical drift) is
        still scoped out — the predicate matches on
        ``aggregate_type``+``event_type``, and once a row is classified as
        lifecycle the entire FORBIDDEN_KEYS rule is suppressed.
        """
        row: dict[str, object] = {
            "aggregate_type": "Mission",
            "event_type": "MissionCreated",
            "event_name": "legacy_alias",
        }
        findings = detect_forbidden_keys(row, "status.events.jsonl")
        assert findings == []


# ---------------------------------------------------------------------------
# Unknown-shape row-family tests — pins issue #1426
# ---------------------------------------------------------------------------


class TestStatusEventUnknownShapeRowFamily:
    """Pins ``UNKNOWN_SHAPE`` routing for mixed ``status.events.jsonl`` rows."""

    def test_lifecycle_envelope_keys_are_known_for_lifecycle_rows(self) -> None:
        row: dict[str, object] = {
            "event_id": "01KTESTLIFECYCLE00000000001",
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "schema_version": "5.0.0",
            "timestamp": "2026-05-31T12:00:00+00:00",
            "payload": {"wp_id": "WP01", "to_lane": "in_progress"},
            "project_uuid": "01KTESTPROJECT0000000001",
            "project_slug": "demo-project",
        }

        artifact_type = status_event_row_artifact_type(row)
        findings = check_unknown_keys(artifact_type, row, "status.events.jsonl")

        assert artifact_type == "mission_lifecycle_row"
        assert findings == []

    def test_malformed_transition_with_lifecycle_keys_still_uses_transition_shape(
        self,
    ) -> None:
        row: dict[str, object] = {
            "event_id": "01KTESTMALFORMED000000001",
            "event_type": "WPStatusChanged",
            "from_lane": "planned",
            "to_lane": "claimed",
            "wp_id": "WP01",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "schema_version": "5.0.0",
            "timestamp": "2026-05-31T12:00:00+00:00",
            "payload": {"wp_id": "WP01"},
        }

        artifact_type = status_event_row_artifact_type(row)
        findings = check_unknown_keys(artifact_type, row, "status.events.jsonl")

        assert artifact_type == "status_event_row"
        assert {f.detail for f in findings} >= {
            "unknown key: 'aggregate_id' (artifact_type='status_event_row')",
            "unknown key: 'aggregate_type' (artifact_type='status_event_row')",
            "unknown key: 'schema_version' (artifact_type='status_event_row')",
            "unknown key: 'timestamp' (artifact_type='status_event_row')",
            "unknown key: 'payload' (artifact_type='status_event_row')",
        }


# ---------------------------------------------------------------------------
# End-to-end integration: run_audit against a synthetic mission tree
# ---------------------------------------------------------------------------


class TestRunAuditRowFamily:
    """Drive the real audit engine against a mixed-row mission tree.

    Rationale for shape (vs. shelling out to ``mission create``):
    The bug reproduction calls ``spec-kitty agent mission create`` then
    ``spec-kitty doctor mission-state --audit``. The ``mission create`` half
    is implemented in modules NOT owned by WP01 and is already exercised by
    other tests. To keep WP01's regression test focused on the audit-side
    classifier (the contract WP01 owns), this test hand-writes the exact row
    shapes ``status/lifecycle_events.py`` produces into a tmp
    ``status.events.jsonl`` and runs the engine. If a future writer changes
    the lifecycle row shape, that change is caught by the producer-side
    tests under ``tests/status/`` and the predicate here can be updated in
    lockstep.
    """

    def test_fresh_mission_lifecycle_rows_yield_no_forbidden_key_findings(
        self, tmp_path: Path
    ) -> None:
        kitty_specs = tmp_path / "kitty-specs"
        # Mission #1: only lifecycle rows (the user-visible bug scenario for #1122).
        _seed_mission(
            kitty_specs,
            "001-fresh-mission",
            mission_id="01JZZZZZZZZZZZZZZZZZZZZZZZ",
            rows=[
                {
                    "aggregate_type": "Mission",
                    "event_type": "MissionCreated",
                    "event_id": "01HXYZ00000000000000000001",
                    "at": "2026-05-19T00:00:00+00:00",
                    "payload": {"mission_slug": "001-fresh-mission"},
                },
                {
                    "aggregate_type": "Mission",
                    "event_type": "SpecifyStarted",
                    "event_id": "01HXYZ00000000000000000002",
                    "at": "2026-05-19T00:01:00+00:00",
                    "payload": {},
                },
            ],
        )

        report = run_audit(AuditOptions(repo_root=tmp_path, scan_root=kitty_specs))

        # No FORBIDDEN_KEY findings should be emitted against the lifecycle rows.
        codes_001 = [
            f.code
            for m in report.missions
            if m.mission_slug == "001-fresh-mission"
            for f in m.findings
        ]
        assert "FORBIDDEN_KEY" not in codes_001, (
            "WP01 regression (#1122): lifecycle rows triggered FORBIDDEN_KEY in "
            f"run_audit output: {codes_001!r}"
        )

    def test_lifecycle_envelope_rows_yield_no_unknown_shape_findings(
        self, tmp_path: Path
    ) -> None:
        kitty_specs = tmp_path / "kitty-specs"
        _seed_mission(
            kitty_specs,
            "004-lifecycle-envelope",
            mission_id="01JZZZZZZZZZZZZZZZZZZZZZZC",
            rows=[
                {
                    "event_id": "01KTESTLIFECYCLE00000000002",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP01",
                    "aggregate_type": "WorkPackage",
                    "schema_version": "5.0.0",
                    "timestamp": "2026-05-31T12:00:00+00:00",
                    "payload": {"wp_id": "WP01", "to_lane": "in_progress"},
                    "project_uuid": "01KTESTPROJECT0000000002",
                    "project_slug": "demo-project",
                },
            ],
        )

        report = run_audit(AuditOptions(repo_root=tmp_path, scan_root=kitty_specs))

        unknown_findings = [
            f
            for m in report.missions
            if m.mission_slug == "004-lifecycle-envelope"
            for f in m.findings
            if f.code == "UNKNOWN_SHAPE"
        ]
        assert unknown_findings == [], (
            "Issue #1426 regression: lifecycle envelopes must not be checked "
            f"against status_event_row. Got: {unknown_findings!r}"
        )

    def test_malformed_transition_row_still_flagged_in_run_audit(
        self, tmp_path: Path
    ) -> None:
        kitty_specs = tmp_path / "kitty-specs"
        # Malformed: transition shape with lifecycle discriminator but no
        # aggregate_type=Mission. The audit must still raise FORBIDDEN_KEY.
        _seed_mission(
            kitty_specs,
            "002-malformed-transition",
            mission_id="01JZZZZZZZZZZZZZZZZZZZZZZA",
            rows=[
                {
                    "from_lane": "planned",
                    "to_lane": "claimed",
                    "event_type": "ShouldNotBeHere",
                    "wp_id": "WP01",
                    "actor": "claude",
                },
            ],
        )

        report = run_audit(AuditOptions(repo_root=tmp_path, scan_root=kitty_specs))

        codes_002 = [
            f.code
            for m in report.missions
            if m.mission_slug == "002-malformed-transition"
            for f in m.findings
        ]
        assert "FORBIDDEN_KEY" in codes_002, (
            "Regression guard: a malformed status-transition row carrying "
            "`event_type` must still be flagged. Got codes: "
            f"{codes_002!r}"
        )

    def test_mixed_rows_only_flag_the_malformed_one(self, tmp_path: Path) -> None:
        """Lifecycle rows + transition rows + one malformed row in same mission.

        Exactly one FORBIDDEN_KEY finding should be produced — from the
        malformed row only. This guards against an over-broad fix that
        suppresses the rule for all rows once any lifecycle row is present.
        """
        kitty_specs = tmp_path / "kitty-specs"
        _seed_mission(
            kitty_specs,
            "003-mixed",
            mission_id="01JZZZZZZZZZZZZZZZZZZZZZZB",
            rows=[
                {
                    "aggregate_type": "Mission",
                    "event_type": "MissionCreated",
                    "event_id": "01HXYZ00000000000000000003",
                    "at": "2026-05-19T00:00:00+00:00",
                    "payload": {},
                },
                {
                    "from_lane": "planned",
                    "to_lane": "claimed",
                    "wp_id": "WP01",
                    "actor": "claude",
                    "at": "2026-05-19T00:01:00+00:00",
                    "event_id": "01HXYZ00000000000000000004",
                },
                {
                    "from_lane": "claimed",
                    "to_lane": "in_progress",
                    "wp_id": "WP01",
                    "actor": "claude",
                    "event_type": "LegacyDiscriminator",  # malformed
                    "at": "2026-05-19T00:02:00+00:00",
                    "event_id": "01HXYZ00000000000000000005",
                },
            ],
        )

        report = run_audit(AuditOptions(repo_root=tmp_path, scan_root=kitty_specs))

        forbidden_findings = [
            f
            for m in report.missions
            if m.mission_slug == "003-mixed"
            for f in m.findings
            if f.code == "FORBIDDEN_KEY"
        ]
        assert len(forbidden_findings) == 1, (
            "Expected exactly one FORBIDDEN_KEY finding (from the malformed "
            f"row only). Got {len(forbidden_findings)}: {forbidden_findings!r}"
        )
        assert "event_type" in (forbidden_findings[0].detail or "")
