"""Regression tests for #2717 / FR-013 — canonical kitty-specs/* discovery.

`retrospect summary` diagnostics must discover mission instances under the
canonical ``kitty-specs/*`` home (where records actually live), NOT anchor on
the ``.kittify/missions/`` support/registry root. Anchoring on the registry
omits the real ``retrospective.yaml`` records and mis-reports the corpus.

These are Scope-B (topology-agnostic) NFR-004 schema/discovery-drift guards:
- The shared ``iter_mission_instance_dirs`` iterator is tested directly.
- ``build_summary`` is asserted to FIND a real kitty-specs record and to
  EXCLUDE ``.kittify`` support modules — red before the FR-013 fix (registry
  anchoring omitted it), green after.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.retrospective.summary import (
    build_summary,
    iter_mission_instance_dirs,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

MISSION_ID = "01KQ6YEGT4YBZ3GZF7X6800001"
MISSION_SLUG = "real-kitty-specs-mission-01KQ6YEG"
LEGACY_MISSION_ID = "01KQ6YEGT4YBZ3GZF7X6800002"
LEGACY_SLUG = "legacy-in-registry-mission-01KQ6YEG"


def _completed_yaml(mission_id: str, slug: str) -> str:
    started = "2026-04-27T10:00:00+00:00"
    completed = "2026-04-27T11:00:00+00:00"
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed
started_at: "{started}"
completed_at: "{completed}"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful: []
gaps: []
proposals: []
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "{completed}"
  schema_version: "1"
"""


def _seed_support_modules(project: Path) -> None:
    """Create .kittify support modules that must NEVER be scanned as missions."""
    for support in ("doctrine", "charter", "glossaries"):
        (project / ".kittify" / support).mkdir(parents=True, exist_ok=True)
    # An (empty) legacy registry root exists but carries no real record here.
    (project / ".kittify" / "missions").mkdir(parents=True, exist_ok=True)


def _seed_kitty_specs_mission(project: Path) -> Path:
    """A real mission instance whose record lives under kitty-specs/<slug>/."""
    mission_dir = project / "kitty-specs" / MISSION_SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "retrospective.yaml").write_text(
        _completed_yaml(MISSION_ID, MISSION_SLUG), encoding="utf-8"
    )
    return mission_dir


class TestCanonicalInstanceIterator:
    """The shared iterator anchors on kitty-specs/*, excluding .kittify."""

    def test_yields_kitty_specs_mission_dir(self, tmp_path: Path) -> None:
        _seed_support_modules(tmp_path)
        mission_dir = _seed_kitty_specs_mission(tmp_path)

        yielded = list(iter_mission_instance_dirs(tmp_path))

        assert mission_dir in yielded

    def test_excludes_kittify_support_modules(self, tmp_path: Path) -> None:
        _seed_support_modules(tmp_path)
        _seed_kitty_specs_mission(tmp_path)

        yielded = list(iter_mission_instance_dirs(tmp_path))

        # No discovered path may live under the .kittify support/registry tree.
        for path in yielded:
            assert ".kittify" not in path.parts, (
                f"support/registry path scanned as a mission: {path}"
            )

    def test_skips_kitty_specs_dirs_without_meta_or_record(self, tmp_path: Path) -> None:
        (tmp_path / "kitty-specs" / "not-a-mission").mkdir(parents=True)
        mission_dir = _seed_kitty_specs_mission(tmp_path)

        yielded = list(iter_mission_instance_dirs(tmp_path))

        assert yielded == [mission_dir]


class TestBuildSummaryDiscoversCanonicalRecords:
    """build_summary finds real kitty-specs records (FR-013 regression)."""

    def test_finds_real_kitty_specs_record(self, tmp_path: Path) -> None:
        _seed_support_modules(tmp_path)
        _seed_kitty_specs_mission(tmp_path)

        snapshot = build_summary(project_path=tmp_path)

        # Before FR-013 this was 0 (registry-anchored discovery omitted it).
        assert snapshot.mission_count == 1
        assert snapshot.completed_count == 1

    def test_support_modules_not_counted_as_missions(self, tmp_path: Path) -> None:
        _seed_support_modules(tmp_path)
        # No kitty-specs missions at all — only .kittify support dirs.

        snapshot = build_summary(project_path=tmp_path)

        assert snapshot.mission_count == 0

    def test_legacy_in_registry_record_still_resolved(self, tmp_path: Path) -> None:
        """A kitty-specs mission whose record was never relocated out of the
        legacy ``.kittify/missions/<mission_id>/`` registry is still counted."""
        import json

        _seed_support_modules(tmp_path)
        kitty_dir = tmp_path / "kitty-specs" / LEGACY_SLUG
        kitty_dir.mkdir(parents=True, exist_ok=True)
        (kitty_dir / "meta.json").write_text(
            json.dumps({"mission_id": LEGACY_MISSION_ID, "mission_slug": LEGACY_SLUG}),
            encoding="utf-8",
        )
        # Record lives ONLY in the legacy in-registry location.
        registry_dir = tmp_path / ".kittify" / "missions" / LEGACY_MISSION_ID
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "retrospective.yaml").write_text(
            _completed_yaml(LEGACY_MISSION_ID, LEGACY_SLUG), encoding="utf-8"
        )

        snapshot = build_summary(project_path=tmp_path)

        assert snapshot.mission_count == 1
        assert snapshot.completed_count == 1
