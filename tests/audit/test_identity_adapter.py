"""Tests for src/specify_cli/audit/identity_adapter.py (T009).

Uses real IdentityState objects constructed via classify_mission() with
tmp_path fixtures — no mocking of IdentityState.

Test index:
1. test_orphan_state_emits_identity_missing
2. test_legacy_state_emits_no_findings
3. test_pending_state_emits_no_findings
4. test_assigned_state_emits_no_findings
5. test_duplicate_prefix_two_missions
6. test_duplicate_mission_id_two_missions
7. test_ambiguous_selector_emits_warning
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.audit.identity_adapter import (
    duplicate_ids_to_findings,
    identity_state_to_findings,
    prefix_groups_to_findings,
    selector_groups_to_findings,
)
from specify_cli.audit.models import Severity
from specify_cli.status.identity_audit import (
    classify_mission,
    find_ambiguous_selectors,
    find_duplicate_prefixes,
)


# ---------------------------------------------------------------------------
# Helpers to create mission fixtures
# ---------------------------------------------------------------------------


def _make_mission_dir(
    parent: Path,
    slug: str,
    *,
    mission_id: str | None = None,
    mission_number: int | None = None,
) -> Path:
    """Create a minimal mission directory with an optional meta.json."""
    mission_dir = parent / slug
    mission_dir.mkdir(parents=True, exist_ok=True)

    if mission_id is not None or mission_number is not None:
        meta: dict[str, object] = {}
        if mission_id is not None:
            meta["mission_id"] = mission_id
        if mission_number is not None:
            meta["mission_number"] = mission_number
        (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    return mission_dir


def _make_kitty_specs(parent: Path) -> Path:
    """Create a kitty-specs directory under parent and return it."""
    specs = parent / "kitty-specs"
    specs.mkdir(parents=True, exist_ok=True)
    return specs


# ---------------------------------------------------------------------------
# T1: orphan (meta.json absent) → IDENTITY_MISSING
# ---------------------------------------------------------------------------


class TestIdentityStateToFindings:
    def test_orphan_state_emits_identity_missing(self, tmp_path: Path) -> None:
        """Orphan state (no meta.json) → IDENTITY_MISSING finding."""
        mission_dir = tmp_path / "orphan-mission"
        mission_dir.mkdir()
        # Deliberately do NOT create meta.json

        state = classify_mission(mission_dir)
        assert state.state == "orphan"

        findings = identity_state_to_findings(state, mission_dir)
        assert len(findings) == 1
        assert findings[0].code == "IDENTITY_MISSING"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].artifact_path == "meta.json"
        assert findings[0].detail == "meta.json absent"

    def test_legacy_state_emits_no_findings(self, tmp_path: Path) -> None:
        """Legacy state (meta.json exists, mission_number set, mission_id absent) → [].

        The meta classifier (WP03) handles IDENTITY_MISSING for this case.
        The adapter must NOT duplicate the finding.
        """
        mission_dir = _make_mission_dir(
            tmp_path,
            "042-legacy-mission",
            mission_number=42,
            # mission_id intentionally absent
        )

        state = classify_mission(mission_dir)
        assert state.state == "legacy"

        findings = identity_state_to_findings(state, mission_dir)
        assert findings == []

    def test_pending_state_emits_no_findings(self, tmp_path: Path) -> None:
        """Pending state (mission_id present, mission_number null) → no finding."""
        mission_dir = _make_mission_dir(
            tmp_path,
            "pending-feature-01ABCDEFGH",
            mission_id="01ABCDEFGHJKMNPQRSTVWXYZ01",
            # mission_number intentionally absent (null = pre-merge)
        )

        state = classify_mission(mission_dir)
        assert state.state == "pending"

        findings = identity_state_to_findings(state, mission_dir)
        assert findings == []

    def test_assigned_state_emits_no_findings(self, tmp_path: Path) -> None:
        """Assigned state (both mission_id and mission_number present) → no finding."""
        mission_dir = _make_mission_dir(
            tmp_path,
            "083-assigned-mission",
            mission_id="01ABCDEFGHJKMNPQRSTVWXYZ01",
            mission_number=83,
        )

        state = classify_mission(mission_dir)
        assert state.state == "assigned"

        findings = identity_state_to_findings(state, mission_dir)
        assert findings == []


# ---------------------------------------------------------------------------
# T5: duplicate_prefix_two_missions → DUPLICATE_PREFIX
# ---------------------------------------------------------------------------


class TestPrefixGroupsToFindings:
    def test_duplicate_prefix_two_missions(self, tmp_path: Path) -> None:
        """Two missions with the same NNN- prefix each get a DUPLICATE_PREFIX finding
        listing the other.
        """
        specs = _make_kitty_specs(tmp_path)

        # Both share the "042" prefix
        dir_a = _make_mission_dir(specs, "042-alpha", mission_number=1)
        dir_b = _make_mission_dir(specs, "042-beta", mission_number=2)

        groups = find_duplicate_prefixes(tmp_path)
        assert "042" in groups

        slug_to_dir = {"042-alpha": dir_a, "042-beta": dir_b}
        findings = prefix_groups_to_findings(groups, slug_to_dir)

        assert len(findings) == 2
        codes = {f.code for f in findings}
        assert codes == {"DUPLICATE_PREFIX"}
        severities = {f.severity for f in findings}
        assert severities == {Severity.WARNING}

        # Each finding mentions the other slug
        alpha_finding = next(f for f in findings if "042-beta" in (f.detail or ""))
        beta_finding = next(f for f in findings if "042-alpha" in (f.detail or ""))
        assert alpha_finding is not None
        assert beta_finding is not None

    def test_no_duplicates_returns_empty(self, tmp_path: Path) -> None:
        """No duplicate prefixes → empty findings list."""
        specs = _make_kitty_specs(tmp_path)
        _make_mission_dir(specs, "001-unique", mission_number=1)
        _make_mission_dir(specs, "002-also-unique", mission_number=2)

        groups = find_duplicate_prefixes(tmp_path)
        findings = prefix_groups_to_findings(groups, {})
        assert findings == []


# ---------------------------------------------------------------------------
# T6: duplicate_mission_id_two_missions → DUPLICATE_MISSION_ID
# ---------------------------------------------------------------------------


class TestDuplicateIdsToFindings:
    def test_duplicate_mission_id_two_missions(self, tmp_path: Path) -> None:
        """Two missions sharing the same mission_id each get a DUPLICATE_MISSION_ID
        finding listing the other.
        """
        shared_id = "01ABCDEFGHJKMNPQRSTVWXYZ01"

        dir_a = _make_mission_dir(
            tmp_path, "001-first", mission_id=shared_id, mission_number=1
        )
        dir_b = _make_mission_dir(
            tmp_path, "002-second", mission_id=shared_id, mission_number=2
        )

        from specify_cli.status.identity_audit import classify_mission as cm

        state_a = cm(dir_a)
        state_b = cm(dir_b)

        slug_to_dir = {"001-first": dir_a, "002-second": dir_b}
        findings = duplicate_ids_to_findings([state_a, state_b], slug_to_dir)

        assert len(findings) == 2
        codes = {f.code for f in findings}
        assert codes == {"DUPLICATE_MISSION_ID"}
        severities = {f.severity for f in findings}
        assert severities == {Severity.ERROR}

        # Each finding names the other mission
        first_finding = next(f for f in findings if "002-second" in (f.detail or ""))
        second_finding = next(f for f in findings if "001-first" in (f.detail or ""))
        assert first_finding is not None
        assert second_finding is not None

    def test_unique_mission_ids_returns_empty(self, tmp_path: Path) -> None:
        """Missions with distinct mission_ids → empty findings."""
        dir_a = _make_mission_dir(
            tmp_path, "001-a", mission_id="01AAAAAAAAAAAAAAAAAAAAAAAAA1", mission_number=1
        )
        dir_b = _make_mission_dir(
            tmp_path, "002-b", mission_id="01BBBBBBBBBBBBBBBBBBBBBBBBB1", mission_number=2
        )

        from specify_cli.status.identity_audit import classify_mission as cm

        findings = duplicate_ids_to_findings(
            [cm(dir_a), cm(dir_b)],
            {"001-a": dir_a, "002-b": dir_b},
        )
        assert findings == []

    def test_none_mission_ids_not_grouped(self, tmp_path: Path) -> None:
        """Missions without mission_id (None) are not grouped as duplicates."""
        dir_a = _make_mission_dir(tmp_path, "001-no-id", mission_number=1)
        dir_b = _make_mission_dir(tmp_path, "002-also-no-id", mission_number=2)

        from specify_cli.status.identity_audit import classify_mission as cm

        state_a = cm(dir_a)
        state_b = cm(dir_b)
        assert state_a.mission_id is None
        assert state_b.mission_id is None

        findings = duplicate_ids_to_findings([state_a, state_b], {})
        assert findings == []


# ---------------------------------------------------------------------------
# T7: ambiguous_selector_emits_warning → AMBIGUOUS_SELECTOR
# ---------------------------------------------------------------------------


class TestSelectorGroupsToFindings:
    def test_ambiguous_selector_emits_warning(self, tmp_path: Path) -> None:
        """Two missions that share a selector handle both get an AMBIGUOUS_SELECTOR
        warning.
        """
        specs = _make_kitty_specs(tmp_path)

        # "042-foo" and "042-bar" share the numeric handle "042"
        dir_a = _make_mission_dir(specs, "042-foo", mission_number=42)
        dir_b = _make_mission_dir(specs, "042-bar", mission_number=43)

        from specify_cli.status.identity_audit import audit_repo

        states = audit_repo(tmp_path)
        groups = find_ambiguous_selectors(states)

        # The "042" numeric handle should be ambiguous
        assert any(len(v) >= 2 for v in groups.values()), (
            "Expected at least one ambiguous handle; groups were: " + repr(groups)
        )

        slug_to_dir = {"042-foo": dir_a, "042-bar": dir_b}
        findings = selector_groups_to_findings(groups, slug_to_dir)

        ambiguous = [f for f in findings if f.code == "AMBIGUOUS_SELECTOR"]
        assert len(ambiguous) >= 2  # at least one finding per mission
        severities = {f.severity for f in ambiguous}
        assert severities == {Severity.WARNING}

    def test_unambiguous_selectors_returns_empty(self, tmp_path: Path) -> None:
        """Missions with distinct selectors → empty findings."""
        specs = _make_kitty_specs(tmp_path)
        _make_mission_dir(specs, "001-alpha", mission_number=1)
        _make_mission_dir(specs, "002-beta", mission_number=2)

        from specify_cli.status.identity_audit import audit_repo

        states = audit_repo(tmp_path)
        groups = find_ambiguous_selectors(states)
        findings = selector_groups_to_findings(groups, {})
        assert findings == []
