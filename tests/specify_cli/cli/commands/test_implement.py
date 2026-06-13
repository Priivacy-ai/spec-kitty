"""WP06 (T026) -- unit tests for the implement planning-artifact migration.

These tests pin the behavior that planning-artifact commits route
through :class:`BookkeepingTransaction` when the mission has a
``coordination_branch`` in ``meta.json``, and fall back to the legacy
raw-git path when it does not.

The full end-to-end flow lives in
``tests/integration/test_implement_review_flow.py``; this file covers
the small pure-Python shape changes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _make_meta(
    feature_dir: Path,
    *,
    with_coord: bool = True,
    mission_id: str = "01JZZZZZZZZZZZZZZZZZZZZZZZ",
    mission_slug: str = "wp06-impl-mission",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mid8": mission_id[:8],
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-05-28T00:00:00+00:00",
        "friendly_name": "WP06 implement test mission",
    }
    if with_coord:
        payload["coordination_branch"] = f"kitty/mission-{mission_slug}-{mission_id[:8]}"
    (feature_dir / "meta.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


class TestFeatureDirStatusPaths:
    """Regression: porcelain parsing must not truncate worktree-only changes.

    ``git status --porcelain`` emits ``XY<space>PATH``. For a tracked file that
    is modified but **not staged**, ``X`` is a space → the line is ``" M path"``.
    ``_git_stdout`` ``.strip()``s the whole output, which removes the leading
    space of the *first* line, shifting its columns so the previous ``line[3:]``
    slice ate the first path character (``kitty-specs`` → ``itty-specs``). The
    bogus path then fails ``source.exists()``, the planning-artifact transaction
    stages nothing, and the claim dies with "commit() called with no events or
    artifacts to commit" — so status never advances. This pins the real path.
    """

    def _git_repo_with_modified_tracked_file(self, tmp_path: Path) -> tuple[Path, Path]:
        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        feature_dir = repo / "kitty-specs" / "demo-feature"
        feature_dir.mkdir(parents=True)
        status_json = feature_dir / "status.json"
        status_json.write_text('{"v":1}\n', encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "initial")
        # Modify WITHOUT staging → porcelain emits " M kitty-specs/.../status.json"
        status_json.write_text('{"v":2}\n', encoding="utf-8")
        return repo, feature_dir

    def test_worktree_modified_tracked_file_path_not_truncated(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.implement import _feature_dir_status_paths

        repo, feature_dir = self._git_repo_with_modified_tracked_file(tmp_path)

        paths = _feature_dir_status_paths(repo, feature_dir)

        assert paths == ["kitty-specs/demo-feature/status.json"], (
            f"expected the full untruncated path; got {paths!r}"
        )
        # The parsed path must actually exist on disk (the claim loop checks this).
        assert (repo / paths[0]).exists()


class TestPlanningArtifactIdempotentCommit:
    """Sequential claims must not fail on already-committed planning edits.

    The coordination model commits a claim's planning-artifact edits to the
    coordination branch but leaves them uncommitted in the main checkout. A
    later claim re-discovers those edits as "uncommitted"; committing the
    identical content again is an empty commit, which ``safe_commit`` rejects
    with "git commit failed" — blocking every claim after the first. The commit
    path must treat already-on-coord content as an idempotent no-op.
    """

    def test_committing_content_already_on_coord_is_noop(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.implement import (
            _ensure_planning_artifacts_committed_git,
        )

        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True, text=True
            ).stdout.strip()

        mission_slug = "demo-feature"
        mission_id = "01J6XW9K00000000000000000P"
        mid8 = mission_id[:8]
        coord_branch = f"kitty/mission-{mission_slug}-{mid8}"

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        git("add", "seed.txt")
        git("commit", "-q", "-m", "initial")

        feature_dir = repo / "kitty-specs" / mission_slug
        _make_meta(
            feature_dir,
            with_coord=True,
            mission_id=mission_id,
            mission_slug=mission_slug,
        )
        wp = feature_dir / "tasks" / "WP01.md"
        wp.parent.mkdir(parents=True, exist_ok=True)

        # 1) Commit the WP file with content X; point coord at it (coord HEAD == X).
        wp.write_text("lane: in_progress\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "feature dir @ X")
        git("branch", coord_branch)
        coord_before = git("rev-parse", coord_branch)

        # 2) Advance main HEAD so the tracked WP file differs (content Y).
        wp.write_text("lane: in_progress\nY\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "main @ Y")

        # 3) Working tree: restore content X. Now `git status` reports WP as
        #    modified (differs from main HEAD=Y) but its content equals coord=X.
        wp.write_text("lane: in_progress\n", encoding="utf-8")
        assert git("status", "--porcelain", str(feature_dir))  # dirty

        # MUST NOT raise: the only dirty file already matches coord, so the
        # commit is an idempotent no-op (previously raised "git commit failed").
        _ensure_planning_artifacts_committed_git(
            repo_root=repo,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id="WP02",
            planning_branch="main",
            auto_commit=True,
        )

        # No empty commit was created on the coordination branch.
        assert git("rev-parse", coord_branch) == coord_before


class TestStructuralPlanningArtifactsFailClosed:
    """Deletions/renames of planning artifacts must FAIL CLOSED, not proceed.

    The planning-artifact commit routes through ``BookkeepingTransaction.write_artifact``
    — a write-only API that cannot remove an old path from the coordination branch.
    Before this fix, a deleted/renamed artifact was silently dropped (the parser kept
    only the rename's new path; the idempotency filter ``continue``d on a non-existent
    source) and the claim PROCEEDED, leaving the coordination branch incoherent
    (stale deleted/renamed-from artifacts) — #1598 review P1. The claim must refuse.
    """

    def _seeded_repo(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True, text=True
            ).stdout.strip()

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        feature_dir = repo / "kitty-specs" / "demo-feature"
        _make_meta(
            feature_dir,
            with_coord=True,
            mission_id="01J6XW9K00000000000000000P",
            mission_slug="demo-feature",
        )
        wp = feature_dir / "tasks" / "WP01.md"
        wp.parent.mkdir(parents=True, exist_ok=True)
        wp.write_text("lane: planned\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "seed feature dir")
        return repo, feature_dir, git, wp

    def test_deleted_planning_artifact_fails_closed(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.implement import (
            _ensure_planning_artifacts_committed_git,
        )

        repo, feature_dir, git, wp = self._seeded_repo(tmp_path)
        head_before = git("rev-parse", "HEAD")

        wp.unlink()  # unstaged deletion → porcelain " D kitty-specs/.../WP01.md"

        with pytest.raises(typer.Exit):
            _ensure_planning_artifacts_committed_git(
                repo_root=repo,
                feature_dir=feature_dir,
                mission_slug="demo-feature",
                wp_id="WP02",
                planning_branch="main",
                auto_commit=True,
            )
        # The claim refused: nothing was committed (no silent advance).
        assert git("rev-parse", "HEAD") == head_before

    def test_renamed_planning_artifact_fails_closed(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.implement import (
            _ensure_planning_artifacts_committed_git,
        )

        repo, feature_dir, git, wp = self._seeded_repo(tmp_path)
        head_before = git("rev-parse", "HEAD")

        # Staged rename → porcelain "R  <old> -> <new>".
        git(
            "mv",
            "kitty-specs/demo-feature/tasks/WP01.md",
            "kitty-specs/demo-feature/tasks/WP01-renamed.md",
        )

        with pytest.raises(typer.Exit):
            _ensure_planning_artifacts_committed_git(
                repo_root=repo,
                feature_dir=feature_dir,
                mission_slug="demo-feature",
                wp_id="WP02",
                planning_branch="main",
                auto_commit=True,
            )
        assert git("rev-parse", "HEAD") == head_before


class TestPlanningArtifactPath:
    """Modern (post-WP03) mission routes planning artifacts through coord branch."""

    def test_modern_mission_resolves_coord_branch_from_meta(
        self, tmp_path: Path
    ) -> None:
        from specify_cli.mission_metadata import load_meta

        feature_dir = tmp_path / "kitty-specs" / "wp06-impl-mission"
        _make_meta(feature_dir, with_coord=True)
        meta = load_meta(feature_dir)
        assert isinstance(meta, dict)
        assert meta["coordination_branch"].startswith("kitty/mission-")
        assert meta["mission_id"] == "01JZZZZZZZZZZZZZZZZZZZZZZZ"

    def test_legacy_mission_has_no_coord_branch(self, tmp_path: Path) -> None:
        from specify_cli.mission_metadata import load_meta

        feature_dir = tmp_path / "kitty-specs" / "wp06-legacy-mission"
        _make_meta(feature_dir, with_coord=False)
        meta = load_meta(feature_dir)
        assert isinstance(meta, dict)
        assert "coordination_branch" not in meta


class TestImplementModuleImports:
    """The migrated implement module imports cleanly after WP01/WP06."""

    def test_implement_imports_safe_commit_with_new_signature(self) -> None:
        from specify_cli.cli.commands import implement
        from specify_cli.git import safe_commit
        import inspect

        sig = inspect.signature(safe_commit)
        assert "destination_ref" in sig.parameters
        assert "worktree_root" in sig.parameters
        # The implement module still imports safe_commit (legacy
        # auto-commit path).
        assert hasattr(implement, "safe_commit")

    def test_implement_command_callable(self) -> None:
        from specify_cli.cli.commands.implement import implement

        # Just ensure the symbol is importable as a Typer command.
        assert callable(implement)


class TestNonCoordStatusFilesCommitted:
    """#1775 review M3: the coord-owned status-file exclusion must be coord-only.

    On a non-coordination (flat/legacy) mission there is no coord branch that owns
    the canonical status log/snapshot, so the primary checkout's ``status.events.jsonl``
    / ``status.json`` ARE canonical and must be committed. The pre-fix code excluded
    them unconditionally, silently dropping a status edit on flat missions.
    """

    def _entries(self):
        from specify_cli.cli.commands.implement import _PorcelainEntry

        return [
            _PorcelainEntry(xy=" M", path="kitty-specs/m/status.events.jsonl", is_structural=False),
            _PorcelainEntry(xy=" M", path="kitty-specs/m/status.json", is_structural=False),
            _PorcelainEntry(xy=" M", path="kitty-specs/m/tasks.md", is_structural=False),
        ]

    def test_non_coord_includes_status_files(self) -> None:
        from specify_cli.cli.commands.implement import _status_paths_for_commit

        # No coordination branch → the primary checkout's status files are
        # canonical and must be committed (not dropped).
        paths = _status_paths_for_commit(self._entries(), coord_branch_for_filter=None)
        assert "kitty-specs/m/status.events.jsonl" in paths
        assert "kitty-specs/m/status.json" in paths
        assert "kitty-specs/m/tasks.md" in paths

    def test_coord_excludes_status_files(self) -> None:
        from specify_cli.cli.commands.implement import _status_paths_for_commit

        # Coordination branch present → status log/snapshot are coord-owned and
        # excluded so the primary checkout's stale copies do not clobber the seed.
        paths = _status_paths_for_commit(
            self._entries(), coord_branch_for_filter="kitty/mission-m-01ABCDEF"
        )
        assert "kitty-specs/m/status.events.jsonl" not in paths
        assert "kitty-specs/m/status.json" not in paths
        assert "kitty-specs/m/tasks.md" in paths


class TestPlanningArtifactAutoCommit:
    """Planning artifacts stage from the transaction worktree, not the caller checkout."""

    def test_auto_commit_uses_coordination_worktree_paths(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.implement import _ensure_planning_artifacts_committed_git

        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        mission_slug = "demo-feature"
        mission_id = "01J6XW9K00000000000000000P"
        mid8 = mission_id[:8]
        coord_branch = f"kitty/mission-{mission_slug}-{mid8}"

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        git("add", "seed.txt")
        git("commit", "-q", "-m", "initial")
        git("branch", coord_branch)

        feature_dir = repo / "kitty-specs" / mission_slug
        _make_meta(
            feature_dir,
            with_coord=True,
            mission_id=mission_id,
            mission_slug=mission_slug,
        )
        (feature_dir / "tasks.md").write_text("# tasks\n", encoding="utf-8")

        _ensure_planning_artifacts_committed_git(
            repo_root=repo,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id="WP01",
            planning_branch="main",
            auto_commit=True,
        )

        assert git("rev-parse", "main") != git("rev-parse", coord_branch)
        assert (
            git("show", f"{coord_branch}:kitty-specs/{mission_slug}/tasks.md").strip()
            == "# tasks"
        )
        main_tasks = subprocess.run(
            ["git", "show", f"main:kitty-specs/{mission_slug}/tasks.md"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert main_tasks.returncode != 0

    def test_auto_commit_with_coord_feature_dir_uses_primary_artifact_source(
        self, tmp_path: Path
    ) -> None:
        from specify_cli.cli.commands.implement import (
            _ensure_planning_artifacts_committed_git,
        )

        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        mission_slug = "demo-feature"
        mission_id = "01J6XW9K00000000000000000P"
        mid8 = mission_id[:8]
        coord_branch = f"kitty/mission-{mission_slug}-{mid8}"

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        git("add", "seed.txt")
        git("commit", "-q", "-m", "initial")
        git("branch", coord_branch)

        primary_feature_dir = repo / "kitty-specs" / mission_slug
        _make_meta(
            primary_feature_dir,
            with_coord=True,
            mission_id=mission_id,
            mission_slug=mission_slug,
        )
        tasks = primary_feature_dir / "tasks.md"
        tasks.write_text("# tasks\n", encoding="utf-8")

        _ensure_planning_artifacts_committed_git(
            repo_root=repo,
            feature_dir=primary_feature_dir,
            mission_slug=mission_slug,
            wp_id="WP01",
            planning_branch="main",
            auto_commit=True,
        )
        coord_feature_dir = (
            repo
            / ".worktrees"
            / f"{mission_slug}-{mid8}-coord"
            / "kitty-specs"
            / mission_slug
        )
        assert (coord_feature_dir / "meta.json").exists()

        tasks.write_text("# tasks\n\nupdated\n", encoding="utf-8")

        _ensure_planning_artifacts_committed_git(
            repo_root=repo,
            feature_dir=coord_feature_dir,
            mission_slug=mission_slug,
            wp_id="WP02",
            planning_branch="main",
            auto_commit=True,
        )

        assert (
            git("show", f"{coord_branch}:kitty-specs/{mission_slug}/tasks.md").strip()
            == "# tasks\n\nupdated"
        )
