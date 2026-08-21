"""Tests for specify_cli.team_projection.public_view (D1-T1).

Covers §4 N4 (public absent by default), N5 (malformed config fail-closed),
N6 (explicit opt-in), and N9 (team/public closed schema relation).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.utils import write_wp

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


# --- N4: public absent by default --------------------------------------------


def test_is_public_projection_enabled_no_config_file(tmp_path: Path) -> None:
    from specify_cli.team_projection.public_view import is_public_projection_enabled

    assert is_public_projection_enabled(tmp_path) is False


def test_is_public_projection_enabled_no_key(tmp_path: Path) -> None:
    from specify_cli.team_projection.public_view import is_public_projection_enabled

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("agents:\n  available: []\n", encoding="utf-8")

    assert is_public_projection_enabled(tmp_path) is False


# --- N5: malformed config values fail closed ---------------------------------


@pytest.mark.parametrize(
    "yaml_body",
    [
        'public_projection: "yes"\n',
        "public_projection:\n  enabled: 1\n",
        "public_projection: [1, 2\n",  # unparsable YAML
        "public_projection:\n  enabled: null\n",
    ],
)
def test_is_public_projection_enabled_malformed_fails_closed(
    tmp_path: Path, yaml_body: str
) -> None:
    from specify_cli.team_projection.public_view import is_public_projection_enabled

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(yaml_body, encoding="utf-8")

    assert is_public_projection_enabled(tmp_path) is False


# --- N6: explicit opt-in ------------------------------------------------------


def test_is_public_projection_enabled_explicit_true(tmp_path: Path) -> None:
    from specify_cli.team_projection.public_view import is_public_projection_enabled

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "public_projection:\n  enabled: true\n", encoding="utf-8"
    )

    assert is_public_projection_enabled(tmp_path) is True


def test_never_reads_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§6.3: never an environment variable — only the tracked config key."""
    from specify_cli.team_projection.public_view import is_public_projection_enabled

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("PUBLIC_PROJECTION_ENABLED", "1")

    assert is_public_projection_enabled(tmp_path) is False


# --- N9: team/public closed schema relation ----------------------------------


def test_public_allowlists_are_subsets_of_team_allowlists() -> None:
    from specify_cli.team_projection.mission_view import TEAM_WP_ALLOWED_FIELDS
    from specify_cli.team_projection.public_view import (
        PUBLIC_WP_ALLOWED_FIELDS,
    )

    assert PUBLIC_WP_ALLOWED_FIELDS <= TEAM_WP_ALLOWED_FIELDS


def test_public_mission_allowed_fields_subset_of_team_mission_fields() -> None:
    from specify_cli.team_projection.public_view import PUBLIC_MISSION_ALLOWED_FIELDS

    # Top-level mission-identity fields the team snapshot's ``mission`` dict
    # carries (StatusSnapshot.to_dict() shape, mission_identity_fields()).
    team_mission_top_level_fields = {
        "mission_slug",
        "mission_number",
        "mission_type",
        "feature_slug",
        "materialized_at",
        "event_count",
        "last_event_id",
        "work_packages",
        "summary",
        "retrospective",
    }
    assert PUBLIC_MISSION_ALLOWED_FIELDS <= team_mission_top_level_fields


def test_public_index_allowed_fields_subset_of_team_index_entry_fields() -> None:
    from specify_cli.team_projection.public_view import PUBLIC_INDEX_ALLOWED_FIELDS
    from specify_cli.team_projection.team_index import TeamIndexEntry

    assert PUBLIC_INDEX_ALLOWED_FIELDS <= set(TeamIndexEntry.model_fields.keys())


def test_project_public_mission_snapshot_projects_allowlist_only(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot
    from specify_cli.team_projection.public_view import (
        PUBLIC_WP_ALLOWED_FIELDS,
        project_public_mission_snapshot,
    )

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    team = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    public = project_public_mission_snapshot(team)

    assert public is not None
    assert public.schema_ == "public_mission_snapshot/v1"
    assert public.provenance == team.provenance
    for wp_state in public.mission["work_packages"].values():
        assert set(wp_state.keys()) <= PUBLIC_WP_ALLOWED_FIELDS
    # No actor/agent/role/model/provider/review*/assignee key ever appears on
    # a WP row (lane names such as "for_review"/"in_review" legitimately
    # contain the substring "review" in the top-level lane-count summary, so
    # this checks the per-WP key set precisely rather than substring-scanning
    # the whole rendered document).
    forbidden_wp_keys = {
        "actor",
        "agent",
        "role",
        "model",
        "provider",
        "review",
        "review_result",
        "assignee",
    }
    for wp_state in public.mission["work_packages"].values():
        assert not (set(wp_state.keys()) & forbidden_wp_keys)
