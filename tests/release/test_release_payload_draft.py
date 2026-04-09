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
    """Create a synthetic mission with a done WP under kitty-specs/."""
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
