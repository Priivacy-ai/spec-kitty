"""Tests for WP07 / FR-012 / SC-04: finalize-tasks canonical target branch.

The legacy ``_resolve_planning_branch()`` returned the current checkout
branch. When operators ran ``finalize-tasks`` from a ``prep/...`` branch
(a documented workaround for the legacy main-pin guard), the prep
branch name leaked into every WP's ``merge_target_branch`` frontmatter
and into ``lanes.json``. Once the prep branch was deleted, downstream
lane allocation crashed because the parent ref was gone (issue #1348).

These tests verify the WP07 fix: ``_resolve_planning_branch()`` reads
the canonical target from ``meta.json`` and refuses to inspect the
current checkout. The ``--target-branch`` override exists as an escape
hatch for legacy missions and for explicit operator overrides.

We focus on the resolver itself rather than driving the full
``finalize-tasks`` Typer command — the full command has a heavy
dependency surface (SaaS preflight, ownership inference, scaffold
generation) and the canonical-target behavior is fully expressed by
the resolver path. The integration test in
``tests/integration/test_mission_close.py`` exercises the full pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

from specify_cli.cli.commands.agent.mission import _resolve_planning_branch
from specify_cli.missions._resolve_planning_branch import (
    PlanningBranchResolutionFailed,
    load_mission_target_branch,
    resolve_planning_branch_from_meta,
)


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": feature_dir.name, **fields}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Pure resolver: resolve_planning_branch_from_meta
# ---------------------------------------------------------------------------


def test_resolve_from_meta_prefers_target_branch() -> None:
    """target_branch wins over merge_target_branch when both present."""
    assert (
        resolve_planning_branch_from_meta(
            {"target_branch": "main", "merge_target_branch": "develop"}
        )
        == "main"
    )


def test_resolve_from_meta_falls_back_to_merge_target_branch() -> None:
    """merge_target_branch is read when target_branch is absent."""
    assert (
        resolve_planning_branch_from_meta({"merge_target_branch": "develop"})
        == "develop"
    )


def test_resolve_from_meta_strips_whitespace() -> None:
    """Surrounding whitespace is trimmed (defensive against hand-edits)."""
    assert (
        resolve_planning_branch_from_meta({"target_branch": "  main\n"})
        == "main"
    )


def test_resolve_from_meta_raises_on_missing_fields() -> None:
    """No target_branch + no merge_target_branch → structured error."""
    with pytest.raises(PlanningBranchResolutionFailed) as excinfo:
        resolve_planning_branch_from_meta({})
    assert excinfo.value.error_code == "PLANNING_BRANCH_NOT_PERSISTED"


def test_resolve_from_meta_raises_on_whitespace_only_value() -> None:
    """A field that decodes to whitespace is treated as absent."""
    with pytest.raises(PlanningBranchResolutionFailed):
        resolve_planning_branch_from_meta({"target_branch": "   "})


def test_resolve_from_meta_raises_on_non_string_value() -> None:
    """Hand-edits that produce a non-string are rejected, not coerced."""
    with pytest.raises(PlanningBranchResolutionFailed):
        resolve_planning_branch_from_meta({"target_branch": 42})


# ---------------------------------------------------------------------------
# Disk loader: load_mission_target_branch
# ---------------------------------------------------------------------------


def test_load_mission_target_branch_from_disk(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    _write_meta(feature_dir, target_branch="main")
    assert load_mission_target_branch(feature_dir) == "main"


def test_load_mission_target_branch_missing_meta_raises(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    feature_dir.mkdir(parents=True)
    with pytest.raises(PlanningBranchResolutionFailed):
        load_mission_target_branch(feature_dir)


def test_load_mission_target_branch_corrupt_meta_raises(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(PlanningBranchResolutionFailed):
        load_mission_target_branch(feature_dir)


def test_load_mission_target_branch_non_object_meta_raises(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(PlanningBranchResolutionFailed):
        load_mission_target_branch(feature_dir)


# ---------------------------------------------------------------------------
# CLI helper: _resolve_planning_branch
# ---------------------------------------------------------------------------


def test_resolve_planning_branch_reads_from_meta(tmp_path: Path) -> None:
    """SC-04 core: a mission whose meta.json says target_branch=main resolves
    to "main" regardless of which branch the CLI process is currently on.
    """
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    _write_meta(feature_dir, target_branch="main")
    repo_root = tmp_path
    assert _resolve_planning_branch(repo_root, feature_dir) == "main"


def test_resolve_planning_branch_ignores_current_checkout(tmp_path: Path) -> None:
    """SC-04 direct verification: even when the resolver is called from a
    process whose checkout is on ``prep/foo``, the canonical target from
    meta.json wins. The resolver has no notion of "current branch" anymore.
    """
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    _write_meta(feature_dir, target_branch="main")
    # The signature still accepts repo_root for API stability; the value is
    # ignored. We pass a tmp path that has no git state at all to prove no
    # subprocess git call is being made under the hood.
    assert _resolve_planning_branch(tmp_path, feature_dir) == "main"


def test_resolve_planning_branch_override_wins(tmp_path: Path) -> None:
    """The --target-branch CLI override beats meta.json (legacy escape hatch)."""
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    _write_meta(feature_dir, target_branch="main")
    resolved = _resolve_planning_branch(
        tmp_path, feature_dir, target_branch_override="develop"
    )
    assert resolved == "develop"


def test_resolve_planning_branch_override_empty_falls_back(tmp_path: Path) -> None:
    """Empty / whitespace override is treated as absent — meta.json wins."""
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    _write_meta(feature_dir, target_branch="main")
    resolved = _resolve_planning_branch(
        tmp_path, feature_dir, target_branch_override="  "
    )
    assert resolved == "main"


def test_resolve_planning_branch_legacy_missing_meta_raises(tmp_path: Path) -> None:
    """Legacy mission without target_branch in meta.json surfaces a structured
    error so the CLI can suggest --target-branch.
    """
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": "demo-feature-01J6XW9K"}),
        encoding="utf-8",
    )
    with pytest.raises(PlanningBranchResolutionFailed):
        _resolve_planning_branch(tmp_path, feature_dir)


def test_resolve_planning_branch_legacy_override_succeeds(tmp_path: Path) -> None:
    """Legacy missions without persisted target_branch are recoverable via
    --target-branch <ref>.
    """
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": "demo-feature-01J6XW9K"}),
        encoding="utf-8",
    )
    resolved = _resolve_planning_branch(
        tmp_path, feature_dir, target_branch_override="main"
    )
    assert resolved == "main"


# ---------------------------------------------------------------------------
# SC-04 direct verification: prep-branch checkout scenario
# ---------------------------------------------------------------------------


def test_finalize_tasks_resolver_records_canonical_target_from_prep_branch(
    tmp_path: Path,
) -> None:
    """SC-04: mission created on main, operator runs finalize-tasks from a
    prep/foo branch — the resolver MUST return "main" (from meta.json),
    NOT "prep/foo" (the current checkout).

    We do not need to actually create a git repo for this assertion: the
    resolver no longer consults git at all. That is the structural fix.
    """
    feature_dir = tmp_path / "kitty-specs" / "demo-feature-01J6XW9K"
    # meta.json was written by `mission create` when the operator was on main.
    _write_meta(
        feature_dir,
        target_branch="main",
        coordination_branch="kitty/mission-demo-feature-01J6XW9K",
        mid8="01J6XW9K",
    )

    # Even if some upstream caller patches "current branch" detection to
    # return prep/foo, the resolver returns main. There is no code path
    # left that returns "prep/foo".
    assert _resolve_planning_branch(tmp_path, feature_dir) == "main"
