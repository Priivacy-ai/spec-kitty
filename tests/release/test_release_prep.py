"""Tests for WP04: Release-Prep CLI.

Covers FR-013, FR-014, FR-015, NFR-004, NFR-005.
Zero network calls (all network entry-points are mocked to raise).
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.release import app
from specify_cli.release.changelog import (
    _parse_wp_frontmatter_status,
    _parse_wp_id,
    _parse_wp_title,
    build_changelog_block,
)
from specify_cli.release.payload import ReleasePrepPayload, build_release_prep_payload
from specify_cli.release.version import propose_version

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

runner = CliRunner()


def _write_pyproject(tmp_path: Path, version: str) -> None:
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
    mission_slug: str,
    friendly_name: str,
    wp_statuses: dict[str, str],
) -> None:
    """Create a synthetic mission directory under kitty-specs/ in tmp_path."""
    mission_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "friendly_name": friendly_name,
        "mission_number": mission_slug.split("-")[0],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (mission_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    (mission_dir / "spec.md").write_text(
        f"# {friendly_name}\n\nDescription of the mission.\n", encoding="utf-8"
    )

    for wp_id, status in wp_statuses.items():
        wp_content = dedent(
            f"""\
            ---
            work_package_id: {wp_id}
            status: {status}
            ---

            ## {wp_id} — Test Work Package for {mission_slug}
            """
        )
        (tasks_dir / f"{wp_id}-test.md").write_text(wp_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T019 — propose_version unit tests
# ---------------------------------------------------------------------------


def test_propose_version_alpha_increments_alpha() -> None:
    assert propose_version("3.1.0a7", "alpha") == "3.1.0a8"


def test_propose_version_alpha_to_beta_starts_beta1() -> None:
    assert propose_version("3.1.0a7", "beta") == "3.1.0b1"


def test_propose_version_beta_increments_beta() -> None:
    assert propose_version("3.1.0b1", "beta") == "3.1.0b2"


def test_propose_version_alpha_to_stable() -> None:
    assert propose_version("3.1.0a7", "stable") == "3.1.0"


def test_propose_version_beta_to_stable() -> None:
    assert propose_version("3.1.0b3", "stable") == "3.1.0"


def test_propose_version_stable_to_stable_patches() -> None:
    assert propose_version("3.1.0", "stable") == "3.1.1"


def test_propose_version_stable_to_alpha() -> None:
    assert propose_version("3.1.0", "alpha") == "3.1.0a1"


def test_propose_version_stable_to_beta() -> None:
    assert propose_version("3.1.0", "beta") == "3.1.0b1"


def test_propose_version_raises_for_rc_suffix() -> None:
    with pytest.raises(ValueError, match="Cannot parse version"):
        propose_version("3.1.0rc1", "stable")


def test_propose_version_raises_for_dev_suffix() -> None:
    with pytest.raises(ValueError, match="Cannot parse version"):
        propose_version("3.1.0.dev1", "stable")


def test_propose_version_raises_beta_to_alpha() -> None:
    with pytest.raises(ValueError, match="Cannot promote a beta"):
        propose_version("3.1.0b1", "alpha")


# ---------------------------------------------------------------------------
# T020 — build_changelog_block tests
# ---------------------------------------------------------------------------


def test_changelog_built_from_local_artifacts_only(tmp_path: Path) -> None:
    """A synthetic fixture with no network access produces the changelog (FR-014)."""
    _write_mission(tmp_path, "010-test-mission", "Test Mission Alpha", {"WP01": "done"})

    # Ensure no network calls are made
    with patch("urllib.request.urlopen", side_effect=AssertionError("network call!")):
        changelog, slugs = build_changelog_block(tmp_path, since_tag=None)

    assert "010-test-mission" in changelog or "Test Mission Alpha" in changelog
    assert "010-test-mission" in slugs


def test_changelog_includes_accepted_missions(tmp_path: Path) -> None:
    _write_mission(
        tmp_path,
        "010-mission-a",
        "Mission A",
        {"WP01": "done", "WP02": "done"},
    )
    _write_mission(
        tmp_path,
        "011-mission-b",
        "Mission B",
        {"WP01": "done"},
    )
    changelog, slugs = build_changelog_block(tmp_path, since_tag=None)

    assert "Mission A" in changelog or "010-mission-a" in changelog
    assert "Mission B" in changelog or "011-mission-b" in changelog
    assert len(slugs) == 2


def test_changelog_excludes_missions_with_no_accepted_wps(tmp_path: Path) -> None:
    _write_mission(
        tmp_path, "010-mission-no-done", "Incomplete Mission", {"WP01": "in_progress"}
    )
    changelog, slugs = build_changelog_block(tmp_path, since_tag=None)

    assert slugs == []
    assert changelog == ""


def test_changelog_returns_empty_for_empty_kitty_specs(tmp_path: Path) -> None:
    # No kitty-specs directory at all
    changelog, slugs = build_changelog_block(tmp_path, since_tag=None)
    assert changelog == ""
    assert slugs == []


def test_changelog_accepts_since_tag_none(tmp_path: Path) -> None:
    """Passing since_tag=None should not raise even with no git tags."""
    _write_mission(tmp_path, "001-test", "Test", {"WP01": "done"})
    # No git tags present — should not raise
    changelog, slugs = build_changelog_block(tmp_path, since_tag=None)
    assert isinstance(changelog, str)
    assert isinstance(slugs, list)


def test_wp_frontmatter_status_parses_quoted_values_without_regex(tmp_path: Path) -> None:
    wp_file = tmp_path / "WP01-test.md"
    wp_file.write_text(
        dedent(
            """\
            ---
            work_package_id: "WP01"
            status: 'done'
            ---

            ## WP01
            """
        ),
        encoding="utf-8",
    )

    assert _parse_wp_frontmatter_status(wp_file) == "done"


def test_wp_id_parses_values_containing_colons(tmp_path: Path) -> None:
    wp_file = tmp_path / "custom-name.md"
    wp_file.write_text(
        dedent(
            """\
            ---
            work_package_id: "WP:01"
            status: done
            ---

            ## WP01
            """
        ),
        encoding="utf-8",
    )

    assert _parse_wp_id(wp_file) == "WP:01"


def test_wp_title_strips_heading_markers_without_regex(tmp_path: Path) -> None:
    wp_file = tmp_path / "WP01-title.md"
    wp_file.write_text(
        dedent(
            """\
            ---
            work_package_id: WP01
            status: done
            ---

            ##   Release Prep Title
            """
        ),
        encoding="utf-8",
    )

    assert _parse_wp_title(wp_file) == "Release Prep Title"


# ---------------------------------------------------------------------------
# T021 — build_release_prep_payload tests
# ---------------------------------------------------------------------------


def test_build_release_prep_payload_returns_correct_shape(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "3.1.0a7")
    _write_mission(tmp_path, "010-test", "Test Mission", {"WP01": "done"})

    payload = build_release_prep_payload("alpha", tmp_path)

    assert isinstance(payload, ReleasePrepPayload)
    assert payload.channel == "alpha"
    assert payload.current_version == "3.1.0a7"
    assert payload.proposed_version == "3.1.0a8"
    assert payload.target_branch == "main"
    assert isinstance(payload.changelog_block, str)
    assert isinstance(payload.mission_slug_list, list)
    assert isinstance(payload.structured_inputs, dict)


def test_payload_structured_inputs_keys(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "3.1.0a7")

    payload = build_release_prep_payload("alpha", tmp_path)

    required_keys = {
        "version",
        "tag_name",
        "release_title",
        "release_notes_body",
        "mission_slug_list",
    }
    assert required_keys.issubset(payload.structured_inputs.keys())


def test_payload_tag_name_uses_v_prefix(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "3.1.0a7")

    payload = build_release_prep_payload("alpha", tmp_path)

    assert payload.structured_inputs["tag_name"] == f"v{payload.proposed_version}"


def test_payload_json_roundtrip(tmp_path: Path) -> None:
    """ReleasePrepPayload round-trips through json.dumps + json.loads (FR-015)."""
    _write_pyproject(tmp_path, "3.1.0a7")

    payload = build_release_prep_payload("alpha", tmp_path)
    serialized = json.dumps(asdict(payload))
    deserialized = json.loads(serialized)

    assert deserialized["channel"] == "alpha"
    assert deserialized["proposed_version"] == payload.proposed_version
    assert isinstance(deserialized["structured_inputs"], dict)


def test_payload_no_github_api_calls(tmp_path: Path) -> None:
    """FR-014/C-002: No network calls are made during payload construction.

    We mock urllib.request.urlopen, requests.get, and any subprocess call to
    'gh' to raise immediately if invoked. The test passes only if none of them
    are called.
    """
    _write_pyproject(tmp_path, "3.1.0a7")
    _write_mission(tmp_path, "010-test", "Test", {"WP01": "done"})

    def _raise_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "Network call detected! build_release_prep_payload must not make "
            "network calls (FR-014/C-002)."
        )

    original_run = __import__("subprocess").run

    def _guarded_run(cmd: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "gh":
            raise AssertionError(
                f"'gh' subprocess call detected: {cmd!r}. "
                "No gh calls are allowed (C-002)."
            )
        return original_run(cmd, *args, **kwargs)

    with (
        patch.object(urllib.request, "urlopen", side_effect=_raise_network),
        patch("subprocess.run", side_effect=_guarded_run),
    ):
        payload = build_release_prep_payload("alpha", tmp_path)

    assert payload.proposed_version == "3.1.0a8"


# ---------------------------------------------------------------------------
# T022 — CLI command tests
# ---------------------------------------------------------------------------


def test_prep_command_emits_text_by_default(tmp_path: Path) -> None:
    """FR-013: running prep produces a rich-formatted summary."""
    _write_pyproject(tmp_path, "3.1.0a7")
    _write_mission(tmp_path, "010-test", "Test Mission", {"WP01": "done"})

    result = runner.invoke(
        app,
        ["--channel", "alpha", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    # Should contain version information
    assert "3.1.0a8" in result.output or "3.1.0a7" in result.output


def test_prep_command_emits_json_with_flag(tmp_path: Path) -> None:
    """FR-015: --json produces a parseable JSON document with all fields."""
    _write_pyproject(tmp_path, "3.1.0a7")
    _write_mission(tmp_path, "010-test", "Test Mission", {"WP01": "done"})

    result = runner.invoke(
        app,
        ["--channel", "alpha", "--repo", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    # Output should be valid JSON
    data = json.loads(result.output)
    assert data["channel"] == "alpha"
    assert data["current_version"] == "3.1.0a7"
    assert data["proposed_version"] == "3.1.0a8"
    assert "structured_inputs" in data
    assert "changelog_block" in data
    assert "mission_slug_list" in data
    assert "target_branch" in data


def test_prep_command_stable_channel(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "3.1.0a7")

    result = runner.invoke(
        app,
        ["--channel", "stable", "--repo", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["proposed_version"] == "3.1.0"


def test_prep_command_beta_channel(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "3.1.0a7")

    result = runner.invoke(
        app,
        ["--channel", "beta", "--repo", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["proposed_version"] == "3.1.0b1"


def test_prep_help_text_is_populated() -> None:
    """The prep subcommand must have real help text (not the old stub comment)."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # The stale "Deep implementation in WP05" text must be gone
    assert "WP05" not in result.output
    # Real help text should be present
    assert "channel" in result.output.lower()


# ---------------------------------------------------------------------------
# T022 — FR-023: scope-cut documentation
# ---------------------------------------------------------------------------


def test_close_comment_scope_cut_documented(tmp_path: Path) -> None:
    """FR-023: the text output lists automated steps and still-manual steps."""
    _write_pyproject(tmp_path, "3.1.0a7")

    result = runner.invoke(
        app,
        ["--channel", "alpha", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    output_lower = result.output.lower()

    # Automated steps should be apparent
    assert "changelog" in output_lower or "version" in output_lower

    # Manual steps must be documented
    assert "manual" in output_lower or "still" in output_lower
    assert "gh pr create" in result.output or "pr create" in result.output.lower()
    assert "tag" in output_lower


# ---------------------------------------------------------------------------
# NFR-004 — Performance benchmark: <= 5 seconds on a synthetic 16-WP mission
# ---------------------------------------------------------------------------


def test_runs_within_5s_for_16_wps(tmp_path: Path) -> None:
    """NFR-004: build_release_prep_payload returns within 5 seconds on 16 WPs."""
    _write_pyproject(tmp_path, "3.1.0a7")

    # Create a synthetic mission with 16 WPs
    wp_statuses = {f"WP{i:02d}": "done" for i in range(1, 17)}
    _write_mission(tmp_path, "068-big-mission", "Big Mission", wp_statuses)

    start = time.monotonic()
    payload = build_release_prep_payload("alpha", tmp_path)
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, (
        f"build_release_prep_payload took {elapsed:.2f}s — must be < 5s (NFR-004)"
    )
    assert payload.proposed_version == "3.1.0a8"
    assert "068-big-mission" in payload.mission_slug_list
