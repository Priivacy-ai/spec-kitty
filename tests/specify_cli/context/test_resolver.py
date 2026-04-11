"""Tests for context/resolver.py -- context resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.context.errors import (
    FeatureNotFoundError,
    MissingArgumentError,
    MissingIdentityError,
    WorkPackageNotFoundError,
)
from specify_cli.context.models import MissionContext
from specify_cli.context.resolver import resolve_context, resolve_or_load
from specify_cli.context.store import save_context
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json


# Default canonical mission_id (ULID shape) used by the fixture.
# WP07 removed silent fallback: meta.json MUST carry mission_id, or the
# resolver raises MissingIdentityError. Legacy tests that previously relied
# on implicit slug-as-mission_id must now pass an explicit mission_id.
_DEFAULT_TEST_MISSION_ID = "01HVXYZTESTMISSION000000000"


def _setup_project(
    tmp_path: Path,
    *,
    mission_slug: str = "057-test-feature",
    wp_code: str = "WP01",
    execution_mode: str = "code_change",
    dependencies: list[str] | None = None,
    owned_files: list[str] | None = None,
    mission_id: str | None = None,
    lane_id: str = "lane-a",
    omit_mission_id: bool = False,
) -> Path:
    """Set up a minimal project structure for resolver tests.

    By default the fixture writes a canonical ``mission_id`` into
    ``meta.json`` because the resolver (post-WP07) hard-fails without one.
    Pass ``omit_mission_id=True`` to exercise the MissingIdentityError path.
    """
    # .kittify/config.yaml with project.uuid
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    config_content = "vcs:\n  type: git\nproject:\n  uuid: test-project-uuid-1234\n  slug: test-project\n  node_id: abcdef012345\n"
    (kittify_dir / "config.yaml").write_text(config_content, encoding="utf-8")

    # kitty-specs/<mission_slug>/meta.json
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "057",
        "slug": "test-feature",
        "mission_slug": mission_slug,
        "friendly_name": "Test Feature",
        "mission": "software-dev",
        "target_branch": "main",
        "created_at": "2026-03-27T16:00:00+00:00",
    }
    if not omit_mission_id:
        meta["mission_id"] = mission_id or _DEFAULT_TEST_MISSION_ID
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # kitty-specs/<mission_slug>/tasks/<wp_code>-*.md
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    deps = dependencies or []
    files = owned_files or ["src/specify_cli/context/**"]
    deps_yaml = "[" + ", ".join(f'"{d}"' for d in deps) + "]" if deps else "[]"
    owned_yaml = "\n".join(f'- "{f}"' for f in files)

    wp_content = (
        f"---\n"
        f"work_package_id: {wp_code}\n"
        f"title: Test WP\n"
        f"lane: planned\n"
        f"dependencies: {deps_yaml}\n"
        f"execution_mode: {execution_mode}\n"
        f"owned_files:\n"
        f"{owned_yaml}\n"
        f"---\n"
        f"\n"
        f"# Work Package: {wp_code}\n"
    )
    (tasks_dir / f"{wp_code}-test-wp.md").write_text(wp_content, encoding="utf-8")

    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=mission_slug,
            mission_id=mission_id or mission_slug,
            mission_branch=f"kitty/mission-{mission_slug}",
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id=lane_id,
                    wp_ids=(wp_code,),
                    write_scope=("src/**",),
                    predicted_surfaces=("context",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-04-04T10:00:00Z",
            computed_from="test",
        ),
    )

    return tmp_path


class TestResolveContext:
    """resolve_context builds a MissionContext from explicit args."""

    def test_basic_resolution(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)

        assert isinstance(ctx, MissionContext)
        assert ctx.wp_code == "WP01"
        assert ctx.mission_slug == "057-test-feature"
        # mission_number is display-only. The legacy fixture stores
        # feature_number="057" as a string, which the resolver preserves
        # verbatim via mission_identity_fields (it only drops leading zeros
        # when the source is an int). Canonical identity is mission_id.
        assert ctx.mission_number == "057"
        assert ctx.mission_id == _DEFAULT_TEST_MISSION_ID
        assert ctx.mission_type == "software-dev"
        assert ctx.project_uuid == "test-project-uuid-1234"
        assert ctx.target_branch == "main"
        assert ctx.authoritative_repo == str(repo)
        assert ctx.execution_mode == "code_change"
        assert ctx.dependency_mode == "independent"
        assert ctx.created_by == "claude"

    def test_token_has_ctx_prefix(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.token.startswith("ctx-")

    def test_token_is_unique(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        ctx1 = resolve_context("WP01", "057-test-feature", "claude", repo)
        ctx2 = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx1.token != ctx2.token

    def test_context_is_persisted(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)

        # Verify the file was created
        context_path = repo / ".kittify" / "runtime" / "contexts" / f"{ctx.token}.json"
        assert context_path.exists()

    def test_authoritative_ref_for_code_change(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, execution_mode="code_change")
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.authoritative_ref == "kitty/mission-057-test-feature-lane-a"

    def test_authoritative_ref_none_for_planning_artifact(self, tmp_path: Path) -> None:
        # planning_artifact WPs are assigned to lane-planning; lane_branch_name returns
        # target_branch ("main") for lane-planning (FR-102, FR-103).
        repo = _setup_project(tmp_path, execution_mode="planning_artifact", lane_id="lane-planning")
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.authoritative_ref == "main"

    def test_dependency_mode_chained(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, dependencies=["WP00"])
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.dependency_mode == "chained"

    def test_dependency_mode_independent(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, dependencies=[])
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.dependency_mode == "independent"

    def test_owned_files_as_tuple(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, owned_files=["src/**", "tests/**"])
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert isinstance(ctx.owned_files, tuple)
        assert ctx.owned_files == ("src/**", "tests/**")

    def test_missing_mission_id_raises_missing_identity_error(self, tmp_path: Path) -> None:
        """WP07 removed silent fallback: missing mission_id is a hard error.

        Pre-083 tests expected resolve_context to silently fall back to the
        mission_slug when meta.json had no mission_id. That fallback has been
        removed — the canonical identity is mission_id and missing it must
        raise MissingIdentityError, never silently succeed.
        """
        repo = _setup_project(tmp_path, omit_mission_id=True)
        with pytest.raises(MissingIdentityError, match="mission_id"):
            resolve_context("WP01", "057-test-feature", "claude", repo)

    def test_mission_id_from_meta_json(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, mission_id="01HVXYZ-REAL-MISSION-ID")
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.mission_id == "01HVXYZ-REAL-MISSION-ID"

    def test_created_at_is_iso_format(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        # Should be parseable as ISO 8601
        assert "T" in ctx.created_at
        assert "+" in ctx.created_at or "Z" in ctx.created_at


class TestResolveContextErrors:
    """Error cases for resolve_context."""

    def test_empty_wp_code_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(MissingArgumentError, match="wp_code is required"):
            resolve_context("", "057-test-feature", "claude", repo)

    def test_empty_mission_slug_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(MissingArgumentError, match="mission_slug is required"):
            resolve_context("WP01", "", "claude", repo)

    def test_missing_config_raises(self, tmp_path: Path) -> None:
        # No .kittify/config.yaml
        with pytest.raises(MissingIdentityError, match="config not found"):
            resolve_context("WP01", "057-test-feature", "claude", tmp_path)

    def test_missing_project_uuid_raises(self, tmp_path: Path) -> None:
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir(parents=True)
        (kittify_dir / "config.yaml").write_text("vcs:\n  type: git\n", encoding="utf-8")

        with pytest.raises(MissingIdentityError, match="project.uuid not found"):
            resolve_context("WP01", "057-test-feature", "claude", tmp_path)

    def test_feature_not_found_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path, mission_slug="057-test-feature")
        with pytest.raises(FeatureNotFoundError, match="not found"):
            resolve_context("WP01", "999-nonexistent", "claude", repo)

    def test_wp_not_found_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(WorkPackageNotFoundError, match="No task file found"):
            resolve_context("WP99", "057-test-feature", "claude", repo)

    def test_missing_meta_json_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        # Delete meta.json
        (repo / "kitty-specs" / "057-test-feature" / "meta.json").unlink()

        with pytest.raises(MissingIdentityError, match="meta.json not found"):
            resolve_context("WP01", "057-test-feature", "claude", repo)

    def test_missing_tasks_dir_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        import shutil

        shutil.rmtree(repo / "kitty-specs" / "057-test-feature" / "tasks")

        with pytest.raises(WorkPackageNotFoundError, match="tasks/ directory not found"):
            resolve_context("WP01", "057-test-feature", "claude", repo)


class TestResolveOrLoad:
    """resolve_or_load dispatches to load or resolve."""

    def test_load_from_token(self, tmp_path: Path) -> None:
        """When token is provided, load from store directly."""
        repo = _setup_project(tmp_path)
        original = resolve_context("WP01", "057-test-feature", "claude", repo)

        loaded = resolve_or_load(
            token=original.token,
            wp_code=None,
            mission_slug=None,
            agent="claude",
            repo_root=repo,
        )
        assert loaded == original

    def test_resolve_from_args(self, tmp_path: Path) -> None:
        """When no token, resolve from wp_code + mission_slug."""
        repo = _setup_project(tmp_path)
        ctx = resolve_or_load(
            token=None,
            wp_code="WP01",
            mission_slug="057-test-feature",
            agent="claude",
            repo_root=repo,
        )
        assert isinstance(ctx, MissionContext)
        assert ctx.wp_code == "WP01"

    def test_missing_wp_code_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(MissingArgumentError, match="--wp"):
            resolve_or_load(
                token=None,
                wp_code=None,
                mission_slug="057-test-feature",
                agent="claude",
                repo_root=repo,
            )

    def test_missing_mission_slug_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(MissingArgumentError, match="--mission"):
            resolve_or_load(
                token=None,
                wp_code="WP01",
                mission_slug=None,
                agent="claude",
                repo_root=repo,
            )

    def test_both_missing_raises(self, tmp_path: Path) -> None:
        repo = _setup_project(tmp_path)
        with pytest.raises(MissingArgumentError, match="--wp.*--mission"):
            resolve_or_load(
                token=None,
                wp_code=None,
                mission_slug=None,
                agent="claude",
                repo_root=repo,
            )

    def test_token_takes_precedence(self, tmp_path: Path) -> None:
        """If token is provided, wp_code/mission_slug are ignored."""
        repo = _setup_project(tmp_path)
        original = resolve_context("WP01", "057-test-feature", "claude", repo)

        # Provide both token and args -- token wins
        loaded = resolve_or_load(
            token=original.token,
            wp_code="WP99",  # This would fail if used
            mission_slug="999-nonexistent",  # This would fail if used
            agent="claude",
            repo_root=repo,
        )
        assert loaded == original


class TestTypedFrontmatterResolution:
    """Verify resolver uses WPMetadata typed frontmatter access."""

    def test_owned_files_from_typed_metadata(self, tmp_path: Path) -> None:
        """owned_files are extracted from WPMetadata.owned_files attribute."""
        repo = _setup_project(tmp_path, owned_files=["src/foo.py", "tests/test_foo.py"])
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.owned_files == ("src/foo.py", "tests/test_foo.py")

    def test_execution_mode_from_typed_metadata(self, tmp_path: Path) -> None:
        """execution_mode is extracted from WPMetadata.execution_mode attribute."""
        repo = _setup_project(tmp_path, execution_mode="planning_artifact")
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.execution_mode == "planning_artifact"

    def test_dependencies_from_typed_metadata(self, tmp_path: Path) -> None:
        """dependencies are extracted from WPMetadata.dependencies attribute."""
        repo = _setup_project(tmp_path, dependencies=["WP00"])
        ctx = resolve_context("WP01", "057-test-feature", "claude", repo)
        assert ctx.dependency_mode == "chained"

    def test_work_package_id_from_typed_metadata(self, tmp_path: Path) -> None:
        """work_package_id is extracted from WPMetadata.work_package_id attribute."""
        repo = _setup_project(tmp_path, wp_code="WP07")
        ctx = resolve_context("WP07", "057-test-feature", "claude", repo)
        assert ctx.work_package_id == "WP07"
