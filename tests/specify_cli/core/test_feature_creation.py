"""Tests for core/mission_creation.py — the programmatic mission-creation API."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import (
    MissionCreationError,
    MissionCreationResult,
    create_mission_core,
)

pytestmark = pytest.mark.fast

_CORE_MODULE = "specify_cli.core.mission_creation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo: Path) -> None:
    """Initialise a minimal git repo with .kittify and kitty-specs."""
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=repo,
        capture_output=True,
        check=True,
    )


def _mission_summary(slug: str) -> dict[str, str]:
    """Return valid stakeholder-facing mission summary fields for test creates."""
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (f"This mission delivers {title} so product and engineering can move forward with a clear outcome and shared understanding."),
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_happy_path_creates_directory_and_returns_result(tmp_path: Path) -> None:
    """create_mission_core creates the mission dir, meta.json, spec.md and returns MissionCreationResult."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "test-feature", **_mission_summary("test-feature"))

    assert isinstance(result, MissionCreationResult)
    # Post-083: mission_slug is "<human-slug>-<mid8>" where mid8 is the first
    # 8 chars of the ULID mission_id. No NNN- prefix is assigned pre-merge.
    assert result.mission_slug.startswith("test-feature-")
    assert len(result.mission_slug) == len("test-feature-") + 8
    # mission_number is None pre-merge (FR-044); a dense display number is
    # assigned only at merge time. Canonical identity is mission_id (ULID).
    assert result.mission_number is None
    assert result.target_branch == "main"
    assert result.current_branch == "main"
    assert result.feature_dir == tmp_path / "kitty-specs" / result.mission_slug
    assert result.feature_dir.is_dir()

    # meta.json exists and has correct content
    meta_file = result.feature_dir / "meta.json"
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    assert meta["mission_slug"] == result.mission_slug
    assert meta["target_branch"] == "main"
    assert meta["mission_type"] == "software-dev"
    # Canonical mission identity fields (083+)
    assert "mission_id" in meta
    assert isinstance(meta["mission_id"], str)
    assert len(meta["mission_id"]) == 26  # ULID is 26 chars
    assert meta["mission_number"] is None  # pre-merge: JSON null

    # spec.md exists
    assert (result.feature_dir / "spec.md").exists()

    # Subdirectories exist
    assert (result.feature_dir / "tasks").is_dir()
    assert (result.feature_dir / "checklists").is_dir()
    assert (result.feature_dir / "research").is_dir()

    # status.events.jsonl exists
    assert (result.feature_dir / "status.events.jsonl").exists()


def test_result_created_files_populated(tmp_path: Path) -> None:
    """MissionCreationResult.created_files lists the key files."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "my-feature", **_mission_summary("my-feature"))

    assert len(result.created_files) == 3
    names = [f.name for f in result.created_files]
    assert "spec.md" in names
    assert "meta.json" in names
    assert "README.md" in names


def test_consumes_pending_origin_after_creation(tmp_path: Path) -> None:
    """A staged pending origin is bound and cleared during mission creation."""
    _init_git_repo(tmp_path)
    pending_origin = tmp_path / ".kittify" / "pending-origin.yaml"
    pending_origin.write_text(
        "\n".join(
            [
                "provider: linear",
                "issue_key: ENG-42",
                "issue_id: issue-123",
                "title: Implement dark mode",
                "url: https://linear.app/acme/ENG-42",
                "status: In Progress",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
        patch("specify_cli.tracker.origin.bind_mission_origin") as mock_bind_origin,
    ):
        mock_bind_origin.return_value = (
            {
                "mission_id": "01KTESTMISSIONID00000000003",
                "mission_number": None,
                "slug": "ticket-feature-01KTESTM",
                "mission_slug": "ticket-feature-01KTESTM",
                "friendly_name": "ticket feature",
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-04-01T00:00:00+00:00",
                "origin_ticket": {"provider": "linear"},
            },
            True,
        )
        result = create_mission_core(tmp_path, "ticket-feature", **_mission_summary("ticket-feature"))

    assert result.origin_binding_attempted is True
    assert result.origin_binding_succeeded is True
    assert result.origin_binding_error is None
    assert pending_origin.exists() is False
    mock_bind_origin.assert_called_once()


def test_pending_origin_failure_is_reported_and_retained(tmp_path: Path) -> None:
    """Bind failures should not clear the staged pending origin."""
    _init_git_repo(tmp_path)
    pending_origin = tmp_path / ".kittify" / "pending-origin.yaml"
    pending_origin.write_text(
        "\n".join(
            [
                "provider: linear",
                "issue_key: ENG-42",
                "issue_id: issue-123",
                "title: Implement dark mode",
                "url: https://linear.app/acme/ENG-42",
                "status: In Progress",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
        patch("specify_cli.tracker.origin.bind_mission_origin", side_effect=RuntimeError("bind failed")),
    ):
        result = create_mission_core(tmp_path, "ticket-feature", **_mission_summary("ticket-feature"))

    assert result.origin_binding_attempted is True
    assert result.origin_binding_succeeded is False
    assert result.origin_binding_error == "bind failed"
    assert pending_origin.exists() is True


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


def test_invalid_slug_raises(tmp_path: Path) -> None:
    """Non-kebab-case slug raises MissionCreationError."""
    _init_git_repo(tmp_path)

    with pytest.raises(MissionCreationError, match="Invalid feature slug"):
        create_mission_core(tmp_path, "Invalid_Slug", **_mission_summary("Invalid_Slug"))


def test_slug_starting_with_number_accepted(tmp_path: Path) -> None:
    """Slug starting with a digit is now valid per FR-017 (e.g. '068-feature-name' convention)."""
    _init_git_repo(tmp_path)

    # Slug validation must pass; creation may succeed or fail for non-slug reasons,
    # but must NOT raise MissionCreationError with "Invalid feature slug".
    try:
        create_mission_core(tmp_path, "123-fix", **_mission_summary("123-fix"))
    except MissionCreationError as exc:
        assert "Invalid feature slug" not in str(exc), f"Digit-prefixed slug '123-fix' must no longer be rejected for slug format. Got: {exc}"


def test_uppercase_slug_raises(tmp_path: Path) -> None:
    """Uppercase slug raises MissionCreationError."""
    _init_git_repo(tmp_path)

    with pytest.raises(MissionCreationError, match="Invalid feature slug"):
        create_mission_core(tmp_path, "User-Auth", **_mission_summary("User-Auth"))


# ---------------------------------------------------------------------------
# Context guard tests
# ---------------------------------------------------------------------------


def test_worktree_context_raises(tmp_path: Path) -> None:
    """Running from inside a worktree raises MissionCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=True),
        pytest.raises(MissionCreationError, match="worktree"),
    ):
        create_mission_core(tmp_path, "test-feature", **_mission_summary("test-feature"))


def test_not_git_repo_raises(tmp_path: Path) -> None:
    """Not being in a git repo raises MissionCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=False),
        pytest.raises(MissionCreationError, match="git repository"),
    ):
        create_mission_core(tmp_path, "test-feature", **_mission_summary("test-feature"))


def test_detached_head_raises(tmp_path: Path) -> None:
    """Detached HEAD raises MissionCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value=None),
        pytest.raises(MissionCreationError, match="branch"),
    ):
        create_mission_core(tmp_path, "test-feature", **_mission_summary("test-feature"))


# ---------------------------------------------------------------------------
# Target branch tests
# ---------------------------------------------------------------------------


def test_explicit_target_branch(tmp_path: Path) -> None:
    """Explicit target_branch overrides the current branch."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(
            tmp_path,
            "test-feature",
            target_branch="2.x",
            **_mission_summary("test-feature"),
        )

    assert result.target_branch == "2.x"
    assert result.current_branch == "main"
    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["target_branch"] == "2.x"

    tasks_readme = (result.feature_dir / "tasks" / "README.md").read_text(encoding="utf-8")
    assert 'planning_base_branch: "2.x"' in tasks_readme
    assert 'merge_target_branch: "2.x"' in tasks_readme


def test_target_branch_defaults_to_current(tmp_path: Path) -> None:
    """When no target_branch provided, uses the current branch."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="develop"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "my-feature", **_mission_summary("my-feature"))

    assert result.target_branch == "develop"
    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["target_branch"] == "develop"

    tasks_readme = (result.feature_dir / "tasks" / "README.md").read_text(encoding="utf-8")
    assert 'planning_base_branch: "develop"' in tasks_readme
    assert 'merge_target_branch: "develop"' in tasks_readme


# ---------------------------------------------------------------------------
# Mission tests
# ---------------------------------------------------------------------------


def test_documentation_mission_sets_doc_state(tmp_path: Path) -> None:
    """mission='documentation' initializes documentation_state in meta.json."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(
            tmp_path,
            "docs-feature",
            mission="documentation",
            **_mission_summary("docs-feature"),
        )

    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mission_type"] == "documentation"
    assert "documentation_state" in meta
    assert meta["documentation_state"]["iteration_mode"] == "initial"


def test_default_mission_is_software_dev(tmp_path: Path) -> None:
    """When mission is None, defaults to 'software-dev'."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "basic-feature", **_mission_summary("basic-feature"))

    assert result.meta["mission_type"] == "software-dev"


# ---------------------------------------------------------------------------
# Mission identity / slug formatting tests (post-083: ULID + mid8)
# ---------------------------------------------------------------------------


def test_slug_uses_mid8_suffix_not_numeric_prefix(tmp_path: Path) -> None:
    """Post-083: mission_slug is '<human-slug>-<mid8>', not '<NNN>-<slug>'.

    The canonical machine identity is mission_id (ULID); mission_number is
    None until merge time. The 8-char mid8 suffix disambiguates missions
    that share a human slug (FR-032, FR-044).
    """
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "padded-test", **_mission_summary("padded-test"))

    # No NNN- prefix — slug is "<human-slug>-<mid8>".
    assert result.mission_slug.startswith("padded-test-")
    assert len(result.mission_slug) == len("padded-test-") + 8
    # mission_number is None pre-merge (no dense number assigned).
    assert result.mission_number is None
    # Canonical identity lives in meta.mission_id (ULID, 26 chars).
    assert isinstance(result.meta["mission_id"], str)
    assert len(result.meta["mission_id"]) == 26
    # The mid8 suffix on the slug matches the first 8 chars of mission_id.
    assert result.mission_slug.endswith(result.meta["mission_id"][:8])
