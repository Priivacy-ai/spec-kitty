"""Integration tests for dual-write consistency (T075).

Verifies that emit_status_transition keeps the event log (JSONL),
materialized snapshot (status.json), and frontmatter views in sync.
"""

from __future__ import annotations

import json
from pathlib import Path


from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import Lane
from specify_cli.status.store import read_events, read_events_raw
from specify_cli.status.reducer import SNAPSHOT_FILENAME


# ── Helpers ──────────────────────────────────────────────────────


def _setup_feature_dir(tmp_path: Path, feature_slug: str = "099-test") -> Path:
    """Create a minimal feature directory with tasks/ and a WP file."""
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 file with frontmatter
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text(
        "---\nwork_package_id: WP01\ntitle: Test WP\nlane: planned\ndependencies: []\n---\n\n# WP01 Content\n",
        encoding="utf-8",
    )

    # Set up phase 1 (dual-write) via meta.json
    meta = {"status_phase": 1}
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    return feature_dir


def _read_snapshot(feature_dir: Path) -> dict:
    """Read the status.json snapshot from disk."""
    path = feature_dir / SNAPSHOT_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def _read_wp_frontmatter_lane(feature_dir: Path, wp_id: str) -> str | None:
    """Read the lane field from a WP file's frontmatter."""
    tasks_dir = feature_dir / "tasks"
    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    if not wp_files:
        return None
    content = wp_files[0].read_text(encoding="utf-8")
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("lane:"):
            return stripped.split(":", 1)[1].strip()
    return None


# ── Tests ────────────────────────────────────────────────────────


class TestDualWriteEventAndFrontmatterConsistent:
    """T075: Verify event log, status.json, and frontmatter all agree."""

    def test_dual_write_event_and_frontmatter_consistent(self, tmp_path: Path):
        """Emit planned->claimed, verify event in JSONL, status.json,
        and frontmatter all agree."""
        feature_dir = _setup_feature_dir(tmp_path)

        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="099-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="test-agent",
            repo_root=feature_dir.parent.parent,
        )

        # 1. Verify event in JSONL
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].event_id == event.event_id
        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.CLAIMED

        # 2. Verify status.json
        snapshot = _read_snapshot(feature_dir)
        assert snapshot["work_packages"]["WP01"]["lane"] == "claimed"
        assert snapshot["event_count"] == 1

        # 3. Verify frontmatter updated
        fm_lane = _read_wp_frontmatter_lane(feature_dir, "WP01")
        assert fm_lane == "claimed"


class TestDualWriteMultipleTransitions:
    """T075: Multiple transitions maintain consistency."""

    def test_dual_write_multiple_transitions(self, tmp_path: Path):
        """Emit planned->claimed->in_progress->for_review,
        verify 3 events, final state consistent everywhere."""
        feature_dir = _setup_feature_dir(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Transition 1: planned -> claimed
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Transition 2: claimed -> in_progress
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="in_progress",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Transition 3: in_progress -> for_review
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="for_review",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Verify 3 events in JSONL
        events = read_events(feature_dir)
        assert len(events) == 3

        # Verify final state in status.json
        snapshot = _read_snapshot(feature_dir)
        assert snapshot["work_packages"]["WP01"]["lane"] == "for_review"
        assert snapshot["event_count"] == 3

        # Verify frontmatter
        fm_lane = _read_wp_frontmatter_lane(feature_dir, "WP01")
        assert fm_lane == "for_review"


class TestDualWriteAliasResolvedEverywhere:
    """T075: Alias 'doing' is resolved to 'in_progress' everywhere."""

    def test_dual_write_alias_resolved_everywhere(self, tmp_path: Path):
        """Emit using 'doing', verify event has 'in_progress' everywhere."""
        feature_dir = _setup_feature_dir(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # First move to claimed (required intermediate step)
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Now use the alias "doing" instead of "in_progress"
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="doing",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Event should have canonical "in_progress", not alias "doing"
        assert event.to_lane == Lane.IN_PROGRESS

        # JSONL should have canonical value
        events = read_events(feature_dir)
        assert events[-1].to_lane == Lane.IN_PROGRESS

        # Raw JSONL should have canonical string
        raw_events = read_events_raw(feature_dir)
        assert raw_events[-1]["to_lane"] == "in_progress"

        # status.json should have canonical value
        snapshot = _read_snapshot(feature_dir)
        assert snapshot["work_packages"]["WP01"]["lane"] == "in_progress"


class TestDualWriteForceTransitionRecorded:
    """T075: Force transitions record force flag and reason."""

    def test_dual_write_force_transition_recorded(self, tmp_path: Path):
        """Force done->in_progress, verify force flag and reason in event."""
        feature_dir = _setup_feature_dir(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Set up WP01 as "done" via full lifecycle
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="in_progress",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="for_review",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="done",
            actor="reviewer-1",
            repo_root=repo_root,
            evidence={
                "review": {
                    "reviewer": "reviewer-1",
                    "verdict": "approved",
                    "reference": "PR#99",
                },
            },
        )

        # Now force done -> in_progress (illegal without force)
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="in_progress",
            actor="admin",
            force=True,
            reason="Rework needed after production issue",
            repo_root=repo_root,
        )

        # Verify force flag and reason in event
        assert event.force is True
        assert event.reason == "Rework needed after production issue"

        # Verify in raw JSONL
        raw_events = read_events_raw(feature_dir)
        last_raw = raw_events[-1]
        assert last_raw["force"] is True
        assert last_raw["reason"] == "Rework needed after production issue"

        # Verify snapshot reflects the forced state
        snapshot = _read_snapshot(feature_dir)
        assert snapshot["work_packages"]["WP01"]["lane"] == "in_progress"
        assert snapshot["work_packages"]["WP01"]["force_count"] == 1
