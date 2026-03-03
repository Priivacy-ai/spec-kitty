"""Integration tests for read-cutover phases (T076).

Verifies that status.json is the authoritative source, that
materialize regenerates views, and that phase-2 validate fails
on drift.
"""

from __future__ import annotations

import json
from pathlib import Path


from specify_cli.status.emit import emit_status_transition
from specify_cli.status.reducer import SNAPSHOT_FILENAME, materialize, reduce
from specify_cli.status.store import read_events
from specify_cli.status.validate import (
    validate_derived_views,
    validate_materialization_drift,
)


# ── Helpers ──────────────────────────────────────────────────────


def _setup_feature(
    tmp_path: Path,
    feature_slug: str = "099-test",
    phase: int = 1,
) -> Path:
    """Create a feature directory with WP files and meta.json."""
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 and WP02 files
    for wp_id in ("WP01", "WP02"):
        wp_file = tasks_dir / f"{wp_id}-task.md"
        wp_file.write_text(
            f"---\n"
            f"work_package_id: {wp_id}\n"
            f"title: Test {wp_id}\n"
            f"lane: planned\n"
            f"dependencies: []\n"
            f"---\n"
            f"\n# {wp_id} Content\n",
            encoding="utf-8",
        )

    meta = {"status_phase": phase}
    (feature_dir / "meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )

    return feature_dir


def _read_snapshot_dict(feature_dir: Path) -> dict:
    """Read status.json from disk."""
    path = feature_dir / SNAPSHOT_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def _tamper_snapshot_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Manually modify a WP's lane in status.json to simulate drift."""
    path = feature_dir / SNAPSHOT_FILENAME
    data = json.loads(path.read_text(encoding="utf-8"))
    data["work_packages"][wp_id]["lane"] = lane
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _tamper_frontmatter_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Manually modify a WP file's frontmatter lane to simulate drift."""
    tasks_dir = feature_dir / "tasks"
    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    assert wp_files, f"No WP file found for {wp_id}"
    wp_file = wp_files[0]
    content = wp_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("lane:"):
            lines[i] = f"lane: {lane}"
            break
    wp_file.write_text("\n".join(lines), encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────


class TestReadCutoverStatusJsonIsAuthority:
    """T076: status.json is the authoritative read source."""

    def test_read_cutover_status_json_is_authority(self, tmp_path: Path):
        """After emit, status.json has the canonical state and the reducer
        reproduces it exactly from the event log."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Emit transition
        emit_status_transition(
            feature_dir=feature_dir, feature_slug=slug,
            wp_id="WP01", to_lane="claimed", actor="agent-1",
            repo_root=repo_root,
        )

        # Read status.json (the authority)
        snapshot_disk = _read_snapshot_dict(feature_dir)
        assert snapshot_disk["work_packages"]["WP01"]["lane"] == "claimed"

        # Re-reduce from events and compare
        events = read_events(feature_dir)
        reduced = reduce(events)
        assert reduced.work_packages["WP01"]["lane"] == "claimed"

        # The work_packages should be identical
        assert snapshot_disk["work_packages"] == reduced.work_packages


class TestReadCutoverMaterializeRegeneratesViews:
    """T076: materialize() regenerates snapshot from event log."""

    def test_read_cutover_materialize_regenerates_views(self, tmp_path: Path):
        """Tamper with status.json, then materialize restores correct state."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Emit transitions for WP01
        emit_status_transition(
            feature_dir=feature_dir, feature_slug=slug,
            wp_id="WP01", to_lane="claimed", actor="agent-1",
            repo_root=repo_root,
        )

        # Tamper: manually change WP01 to "done" in status.json
        _tamper_snapshot_lane(feature_dir, "WP01", "done")

        # Verify tamper took effect
        tampered = _read_snapshot_dict(feature_dir)
        assert tampered["work_packages"]["WP01"]["lane"] == "done"

        # Re-materialize from event log
        snapshot = materialize(feature_dir)

        # Should be "claimed" again (restored from events)
        assert snapshot.work_packages["WP01"]["lane"] == "claimed"

        # Disk should also reflect the corrected state
        restored = _read_snapshot_dict(feature_dir)
        assert restored["work_packages"]["WP01"]["lane"] == "claimed"


class TestPhase2ValidateFailsOnDrift:
    """T076: Phase 2 validation detects frontmatter drift as ERROR."""

    def test_phase2_validate_fails_on_drift(self, tmp_path: Path):
        """When frontmatter lane differs from canonical, phase 2 reports ERROR."""
        feature_dir = _setup_feature(tmp_path, phase=2)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Emit transitions for WP01
        emit_status_transition(
            feature_dir=feature_dir, feature_slug=slug,
            wp_id="WP01", to_lane="claimed", actor="agent-1",
            repo_root=repo_root,
        )

        # Tamper: set frontmatter lane to "in_progress" (canonical is "claimed")
        _tamper_frontmatter_lane(feature_dir, "WP01", "in_progress")

        # Read canonical snapshot
        snapshot_data = _read_snapshot_dict(feature_dir)

        # Validate derived views at phase 2
        findings = validate_derived_views(
            feature_dir,
            snapshot_data.get("work_packages", {}),
            phase=2,
        )

        # Should have ERROR findings (not just WARNING)
        assert len(findings) > 0
        error_findings = [f for f in findings if f.startswith("ERROR")]
        assert len(error_findings) > 0
        assert "WP01" in error_findings[0]

    def test_phase1_validate_warns_on_drift(self, tmp_path: Path):
        """At phase 1, frontmatter drift is a WARNING, not ERROR."""
        feature_dir = _setup_feature(tmp_path, phase=1)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        emit_status_transition(
            feature_dir=feature_dir, feature_slug=slug,
            wp_id="WP01", to_lane="claimed", actor="agent-1",
            repo_root=repo_root,
        )

        # Tamper frontmatter
        _tamper_frontmatter_lane(feature_dir, "WP01", "in_progress")

        snapshot_data = _read_snapshot_dict(feature_dir)

        findings = validate_derived_views(
            feature_dir,
            snapshot_data.get("work_packages", {}),
            phase=1,
        )

        assert len(findings) > 0
        warning_findings = [f for f in findings if f.startswith("WARNING")]
        assert len(warning_findings) > 0

    def test_materialization_drift_detected(self, tmp_path: Path):
        """validate_materialization_drift detects status.json / event mismatch."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        emit_status_transition(
            feature_dir=feature_dir, feature_slug=slug,
            wp_id="WP01", to_lane="claimed", actor="agent-1",
            repo_root=repo_root,
        )

        # Tamper status.json to create drift
        _tamper_snapshot_lane(feature_dir, "WP01", "done")

        findings = validate_materialization_drift(feature_dir)
        assert len(findings) > 0
        assert any("WP01" in f for f in findings)
