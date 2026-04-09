"""Regression tests for FR-603: structured draft release payload.

Test T7.4 from WP07 mission 079-post-555-release-hardening.
Verifies that build_release_prep_payload() produces a ``proposed_changelog_block``
field in its output, and that the JSON serialization exposes it.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from textwrap import dedent

import pytest

from specify_cli.release.payload import ReleasePrepPayload, build_release_prep_payload


def _write_pyproject(tmp_path: Path, version: str = "3.1.0a7") -> None:
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            f"""\
            [project]
            name = "spec-kitty-cli"
            version = "{version}"
            description = "Test project"
            """
        ),
        encoding="utf-8",
    )


def _write_mission(
    tmp_path: Path,
    mission_slug: str = "079-test-mission",
    friendly_name: str = "Test Mission",
) -> None:
    """Create a synthetic mission with a done WP under kitty-specs/.

    Uses legacy frontmatter ``status: done`` (pre-3.x format).
    For event-log based detection, use ``_write_mission_with_event_log``.
    """
    import json as _json

    mission_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "friendly_name": friendly_name,
        "mission_number": mission_slug.split("-")[0],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (mission_dir / "meta.json").write_text(
        _json.dumps(meta, indent=2), encoding="utf-8"
    )
    (mission_dir / "spec.md").write_text(
        f"# {friendly_name}\n\nDescription.\n", encoding="utf-8"
    )

    wp_content = dedent(
        f"""\
        ---
        work_package_id: WP01
        status: done
        ---

        ## WP01 — Test Work Package
        """
    )
    (tasks_dir / "WP01-test.md").write_text(wp_content, encoding="utf-8")


def _write_mission_with_event_log(
    tmp_path: Path,
    mission_slug: str = "080-event-log-mission",
    friendly_name: str = "Event Log Mission",
    wp_lane: str = "approved",
) -> None:
    """Create a synthetic 3.x mission whose WP status is in the event log (FR-605).

    The WP markdown file does NOT have a ``status`` frontmatter field —
    status lives exclusively in ``status.events.jsonl``.
    """
    import json as _json

    mission_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "friendly_name": friendly_name,
        "mission_number": mission_slug.split("-")[0],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (mission_dir / "meta.json").write_text(
        _json.dumps(meta, indent=2), encoding="utf-8"
    )
    (mission_dir / "spec.md").write_text(
        f"# {friendly_name}\n\nDescription.\n", encoding="utf-8"
    )

    # WP file has NO status frontmatter — 3.x format
    wp_content = dedent(
        """\
        ---
        work_package_id: WP01
        title: Test Work Package
        ---

        ## WP01 — Test Work Package
        """
    )
    (tasks_dir / "WP01-test.md").write_text(wp_content, encoding="utf-8")

    # Bootstrap event log with a transition to the requested lane
    event = {
        "actor": "finalize-tasks",
        "at": "2026-01-01T00:00:00+00:00",
        "event_id": "01TESTBOOTSTRAP0000000000A",
        "evidence": None,
        "execution_mode": "worktree",
        "force": True,
        "from_lane": "planned",
        "mission_slug": mission_slug,
        "policy_metadata": None,
        "reason": "test bootstrap",
        "review_ref": None,
        "to_lane": wp_lane,
        "wp_id": "WP01",
    }
    (mission_dir / "status.events.jsonl").write_text(
        _json.dumps(event) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# T7.4 — proposed_changelog_block present in payload
# ---------------------------------------------------------------------------


def test_payload_has_proposed_changelog_block_field(tmp_path: Path) -> None:
    """ReleasePrepPayload must carry a proposed_changelog_block field (FR-603)."""
    _write_pyproject(tmp_path)

    payload = build_release_prep_payload("stable", tmp_path)

    assert hasattr(payload, "proposed_changelog_block")


def test_proposed_changelog_block_is_string(tmp_path: Path) -> None:
    """proposed_changelog_block must be a string, even when no missions are present."""
    _write_pyproject(tmp_path)

    payload = build_release_prep_payload("stable", tmp_path)

    assert isinstance(payload.proposed_changelog_block, str)


def test_proposed_changelog_block_non_empty_when_missions_present(
    tmp_path: Path,
) -> None:
    """proposed_changelog_block contains content when accepted missions exist."""
    _write_pyproject(tmp_path)
    _write_mission(tmp_path)

    payload = build_release_prep_payload("stable", tmp_path)

    assert len(payload.proposed_changelog_block) > 0
    assert "## [" in payload.proposed_changelog_block or "079-test-mission" in payload.proposed_changelog_block or "Test Mission" in payload.proposed_changelog_block


def test_proposed_changelog_block_matches_changelog_block(tmp_path: Path) -> None:
    """proposed_changelog_block must equal changelog_block (they are the same content)."""
    _write_pyproject(tmp_path)
    _write_mission(tmp_path)

    payload = build_release_prep_payload("alpha", tmp_path)

    assert payload.proposed_changelog_block == payload.changelog_block


def test_proposed_changelog_block_in_json_serialization(tmp_path: Path) -> None:
    """asdict(payload) must include proposed_changelog_block for JSON output (FR-603)."""
    _write_pyproject(tmp_path)
    _write_mission(tmp_path)

    payload = build_release_prep_payload("stable", tmp_path)
    data = json.loads(json.dumps(asdict(payload)))

    assert "proposed_changelog_block" in data
    assert isinstance(data["proposed_changelog_block"], str)


# ---------------------------------------------------------------------------
# FR-605 — event-log-based WP detection (3.x status model)
# ---------------------------------------------------------------------------


def test_changelog_block_includes_event_log_approved_wp(tmp_path: Path) -> None:
    """WP with lane=approved in status.events.jsonl must appear in changelog (FR-605)."""
    _write_pyproject(tmp_path)
    _write_mission_with_event_log(tmp_path, wp_lane="approved")

    payload = build_release_prep_payload("stable", tmp_path)

    assert len(payload.proposed_changelog_block) > 0
    assert "080-event-log-mission" in payload.proposed_changelog_block


def test_changelog_block_includes_event_log_done_wp(tmp_path: Path) -> None:
    """WP with lane=done in status.events.jsonl must appear in changelog (FR-605)."""
    _write_pyproject(tmp_path)
    _write_mission_with_event_log(tmp_path, wp_lane="done")

    payload = build_release_prep_payload("stable", tmp_path)

    assert len(payload.proposed_changelog_block) > 0
    assert "080-event-log-mission" in payload.proposed_changelog_block


def test_changelog_block_excludes_event_log_planned_wp(tmp_path: Path) -> None:
    """WP with lane=planned in status.events.jsonl must NOT appear in changelog (FR-605)."""
    _write_pyproject(tmp_path)
    _write_mission_with_event_log(tmp_path, wp_lane="planned")

    payload = build_release_prep_payload("stable", tmp_path)

    assert "080-event-log-mission" not in payload.proposed_changelog_block


def test_changelog_block_event_log_takes_precedence_over_frontmatter(
    tmp_path: Path,
) -> None:
    """Event log must take precedence: WP with status:done in frontmatter but
    lane=planned in event log must be excluded from changelog (FR-605).
    """
    import json as _json

    # Create a mission where the WP has status:done in frontmatter...
    mission_dir = tmp_path / "kitty-specs" / "081-precedence-test"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    meta = {"friendly_name": "Precedence Test", "created_at": "2026-01-01T00:00:00+00:00"}
    (mission_dir / "meta.json").write_text(_json.dumps(meta), encoding="utf-8")
    (mission_dir / "spec.md").write_text("# Precedence Test\n", encoding="utf-8")
    wp_content = dedent(
        """\
        ---
        work_package_id: WP01
        status: done
        ---

        ## WP01 — Precedence Test WP
        """
    )
    (tasks_dir / "WP01-test.md").write_text(wp_content, encoding="utf-8")
    # ...but the event log says planned (event log is authoritative in 3.x)
    event = {
        "actor": "finalize-tasks",
        "at": "2026-01-01T00:00:00+00:00",
        "event_id": "01TESTPRECEDENCE000000000A",
        "evidence": None,
        "execution_mode": "worktree",
        "force": True,
        "from_lane": "planned",
        "mission_slug": "081-precedence-test",
        "policy_metadata": None,
        "reason": "test",
        "review_ref": None,
        "to_lane": "planned",
        "wp_id": "WP01",
    }
    (mission_dir / "status.events.jsonl").write_text(
        _json.dumps(event) + "\n", encoding="utf-8"
    )
    _write_pyproject(tmp_path)

    payload = build_release_prep_payload("stable", tmp_path)

    # Event log says planned → must be excluded despite frontmatter saying done
    assert "081-precedence-test" not in payload.proposed_changelog_block
