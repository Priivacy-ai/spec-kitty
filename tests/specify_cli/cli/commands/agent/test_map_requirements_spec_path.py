"""Regression test for issue #1981.

map-requirements must resolve spec.md from the primary checkout even
when a coordination worktree exists for the mission.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mission_runtime import CommitTarget
from specify_cli.coordination.commit_router import CommitRouterResult
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission

pytestmark = [pytest.mark.fast]

MISSION_SLUG = "my-mission-01ABCDEF"
_SPEC_MD_TEXT = "# Spec\n\n| FR-001 | Do the thing. | Proposed |\n"
_WP01_FRONTMATTER = (
    "---\n"
    "work_package_id: WP01\n"
    "title: Example\n"
    "requirement_refs: []\n"
    "---\n"
    "# WP01\n"
)


def test_primary_feature_dir_is_not_coord_worktree(tmp_path: Path) -> None:
    """primary_feature_dir_for_mission returns primary-checkout path, not coord path."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Simulate coord worktree existing on disk
    coord_root = repo_root / ".worktrees" / "my-mission-01ABCDEF-coord"
    coord_root.mkdir(parents=True)
    coord_spec = coord_root / "kitty-specs" / MISSION_SLUG
    coord_spec.mkdir(parents=True)

    # Call the primary resolver (topology-blind)
    result = primary_feature_dir_for_mission(repo_root, MISSION_SLUG)

    # Result must be under the primary checkout, not the coord worktree
    assert ".worktrees" not in str(result), (
        f"primary_feature_dir_for_mission returned a path under .worktrees/: {result}. "
        "map-requirements spec.md lookup will fail when the coord dir lacks spec.md."
    )
    assert str(result).startswith(str(repo_root)), (
        f"Expected path under {repo_root}, got {result}"
    )


def test_map_requirements_reads_spec_from_primary_when_coord_lacks_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-005: map-requirements succeeds when spec.md lives only in the primary checkout.

    This drives the real ``map_requirements`` command body (via CliRunner) so the
    fixed line — ``spec_md = primary_dir / SPEC_MD_FILENAME`` — is actually
    executed. The topology-aware resolver (``resolve_feature_dir_for_slug``)
    returns the coord worktree dir, which holds the WP task files but NOT
    ``spec.md``; only the primary checkout holds ``spec.md``. If the fix were
    reverted to read spec.md from the coord ``feature_dir``, the command would
    exit non-zero with "spec.md not found" and this test would fail.

    Infrastructure seams (project-root location, mission-slug discovery, target
    branch checkout, auto-commit) are mocked so the test exercises the spec.md
    resolution behavior directly rather than standing up a real git repo.
    """
    import typer

    from specify_cli.cli.commands.agent import tasks as tasks_mod

    # Primary checkout: holds spec.md and the WP task file. With no
    # ``coordination_branch``/``topology`` in meta this mission classifies as
    # ``single_branch``, so the single-authority read path resolves WP files from
    # the PRIMARY tasks surface — map-requirements must find WP01 here to reach
    # the spec.md resolution under test (#2070 single-authority topology cleanup).
    primary_root = tmp_path / "primary"
    primary_mission_dir = primary_root / "kitty-specs" / MISSION_SLUG
    primary_mission_dir.mkdir(parents=True)
    (primary_mission_dir / "spec.md").write_text(_SPEC_MD_TEXT, encoding="utf-8")
    primary_tasks_dir = primary_mission_dir / "tasks"
    primary_tasks_dir.mkdir(parents=True)
    (primary_tasks_dir / "WP01-example.md").write_text(_WP01_FRONTMATTER, encoding="utf-8")
    (primary_mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_number": 17,
                "mission_type": "documentation",
            }
        ),
        encoding="utf-8",
    )

    # Coordination worktree: holds the WP task files but deliberately NO spec.md.
    coord_root = primary_root / ".worktrees" / f"{MISSION_SLUG}-coord"
    coord_mission_dir = coord_root / "kitty-specs" / MISSION_SLUG
    coord_tasks_dir = coord_mission_dir / "tasks"
    coord_tasks_dir.mkdir(parents=True)
    (coord_tasks_dir / "WP01-example.md").write_text(_WP01_FRONTMATTER, encoding="utf-8")
    assert not (coord_mission_dir / "spec.md").exists()
    assert not (coord_mission_dir / "meta.json").exists()

    # Mock the upstream infrastructure seams.
    monkeypatch.setattr(tasks_mod, "locate_project_root", lambda: primary_root)
    monkeypatch.setattr(
        tasks_mod, "_find_mission_slug", lambda **_kwargs: MISSION_SLUG
    )
    monkeypatch.setattr(
        tasks_mod,
        "_ensure_target_branch_checked_out",
        lambda *_args, **_kwargs: (primary_root, "main"),
    )
    monkeypatch.setattr(tasks_mod, "get_auto_commit_default", lambda *_a, **_k: False)
    monkeypatch.setattr(
        tasks_mod, "_emit_sparse_session_warning", lambda *_a, **_k: None
    )

    # The two resolvers are late-imported inside map_requirements from this module.
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.resolve_feature_dir_for_slug",
        lambda _root, _slug: coord_mission_dir,
    )
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.primary_feature_dir_for_mission",
        lambda _root, _slug: primary_mission_dir,
    )

    app = typer.Typer()
    app.command()(tasks_mod.map_requirements)

    result = CliRunner().invoke(
        app,
        ["--wp", "WP01", "--refs", "FR-001", "--mission", MISSION_SLUG, "--json", "--no-auto-commit"],
    )

    assert result.exit_code == 0, (
        f"map-requirements should exit 0 reading spec.md from the primary checkout; "
        f"exit={result.exit_code}, output={result.output!r}"
    )
    assert "spec.md not found" not in result.output, (
        "map-requirements must not report 'spec.md not found' when spec.md is present "
        f"in the primary checkout. Output: {result.output!r}"
    )
    payload = json.loads(result.output)
    assert payload["mission_type"] == "documentation"
    assert payload["mission_number"] == 17


def test_map_requirements_auto_commit_uses_coord_placement_for_coord_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auto-commit must commit coord-owned WP files from the coord worktree."""
    import typer

    # #2056 WP08: the planning-commit primitives relocated to commit_router and
    # tasks.py imports them from there, so patch the canonical home.
    from specify_cli.coordination import commit_router as commit_router_mod
    from specify_cli.cli.commands.agent import tasks as tasks_mod

    primary_root = tmp_path / "primary"
    primary_mission_dir = primary_root / "kitty-specs" / MISSION_SLUG
    primary_mission_dir.mkdir(parents=True)
    (primary_mission_dir / "spec.md").write_text(_SPEC_MD_TEXT, encoding="utf-8")
    # With no ``coordination_branch``/``topology`` in meta this mission classifies
    # as ``single_branch``: the single-authority read path resolves WP files from
    # the PRIMARY tasks surface, so ``map-requirements`` collects ``written_files``
    # from here. The real ``_planning_commit_worktree`` is what relocates those
    # primary paths into the coord worktree (faked below) — the commit still lands
    # on the coord placement (#2070 single-authority topology cleanup).
    primary_tasks_dir = primary_mission_dir / "tasks"
    primary_tasks_dir.mkdir(parents=True)
    primary_wp_file = primary_tasks_dir / "WP01-example.md"
    primary_wp_file.write_text(_WP01_FRONTMATTER, encoding="utf-8")
    (primary_mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_number": 17,
                "mission_type": "documentation",
            }
        ),
        encoding="utf-8",
    )

    coord_root = primary_root / ".worktrees" / f"{MISSION_SLUG}-coord"
    coord_mission_dir = coord_root / "kitty-specs" / MISSION_SLUG
    coord_tasks_dir = coord_mission_dir / "tasks"
    coord_tasks_dir.mkdir(parents=True)
    wp_file = coord_tasks_dir / "WP01-example.md"
    wp_file.write_text(_WP01_FRONTMATTER, encoding="utf-8")

    placement = CommitTarget(
        ref=f"kitty/mission-{MISSION_SLUG}",
    )
    captured: dict[str, object] = {}

    def fake_commit_for_mission(
        repo_root: Path,
        mission_slug: str,
        files: tuple[Path, ...],
        message: str,
        policy: object,
        *,
        kind: object,
        target_branch: str | None = None,
        **_kwargs: object,
    ) -> CommitRouterResult:
        # WP07 / FR-006: the WP-file commit now routes through the canonical
        # ``commit_for_mission`` router, which OWNS placement + worktree resolution
        # internally. The command's only contract is: pass the resolved WP files,
        # the WORK_PACKAGE_TASK kind, and the threaded ``target_branch`` for the
        # WP09 ff-advance. Capture those to pin the call shape.
        from mission_runtime import MissionArtifactKind

        captured.update(
            {
                "repo_root": repo_root,
                "mission_slug": mission_slug,
                "files": files,
                "message": message,
                "kind": kind,
                "target_branch": target_branch,
            }
        )
        assert repo_root == primary_root
        assert mission_slug == MISSION_SLUG
        assert kind == MissionArtifactKind.WORK_PACKAGE_TASK
        # WP07: ``target_branch`` is threaded for the ff-advance (previously absent).
        assert target_branch == "main"
        return CommitRouterResult(
            status="committed",
            placement_ref=placement.ref,
            commit_hash="abc1234",
        )

    monkeypatch.setattr(tasks_mod, "locate_project_root", lambda: primary_root)
    monkeypatch.setattr(
        tasks_mod, "_find_mission_slug", lambda **_kwargs: MISSION_SLUG
    )
    monkeypatch.setattr(
        tasks_mod,
        "_ensure_target_branch_checked_out",
        lambda *_args, **_kwargs: (primary_root, "main"),
    )
    monkeypatch.setattr(
        tasks_mod, "_emit_sparse_session_warning", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(tasks_mod, "commit_for_mission", fake_commit_for_mission)
    # write-surface-coherence WP02 / T009: ``_resolve_planning_placement`` now takes
    # a required ``kind`` keyword; the stub accepts it (used only by the pre-check).
    monkeypatch.setattr(
        commit_router_mod, "_resolve_planning_placement", lambda *_args, **_kwargs: placement
    )
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.resolve_feature_dir_for_slug",
        lambda _root, _slug: coord_mission_dir,
    )
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.primary_feature_dir_for_mission",
        lambda _root, _slug: primary_mission_dir,
    )

    app = typer.Typer()
    app.command()(tasks_mod.map_requirements)

    result = CliRunner().invoke(
        app,
        ["--wp", "WP01", "--refs", "FR-001", "--mission", MISSION_SLUG, "--json", "--auto-commit"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["committed"] is True
    assert payload["commit_sha"] == "abc1234"
    assert payload["mission_type"] == "documentation"
    # The WP file the router received is a real WP01 task path (primary surface).
    assert captured["files"]
    assert all("WP01" in path.name for path in captured["files"])  # type: ignore[attr-defined]
