"""Regression test for issue #1981.

map-requirements must resolve spec.md from the primary checkout even
when a coordination worktree exists for the mission.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.missions.feature_dir_resolver import primary_feature_dir_for_mission

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

    # Primary checkout: holds spec.md (and nothing else for this mission).
    primary_root = tmp_path / "primary"
    primary_mission_dir = primary_root / "kitty-specs" / MISSION_SLUG
    primary_mission_dir.mkdir(parents=True)
    (primary_mission_dir / "spec.md").write_text(_SPEC_MD_TEXT, encoding="utf-8")

    # Coordination worktree: holds the WP task files but deliberately NO spec.md.
    coord_mission_dir = (
        primary_root / ".worktrees" / f"{MISSION_SLUG}-coord" / "kitty-specs" / MISSION_SLUG
    )
    coord_tasks_dir = coord_mission_dir / "tasks"
    coord_tasks_dir.mkdir(parents=True)
    (coord_tasks_dir / "WP01-example.md").write_text(_WP01_FRONTMATTER, encoding="utf-8")
    assert not (coord_mission_dir / "spec.md").exists()

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
        "specify_cli.missions.feature_dir_resolver.resolve_feature_dir_for_slug",
        lambda _root, _slug: coord_mission_dir,
    )
    monkeypatch.setattr(
        "specify_cli.missions.feature_dir_resolver.primary_feature_dir_for_mission",
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
