"""WP04 (T018/T019/T021) — commit_router placement-decision campsite.

Covers the ``coordination/commit_router.py`` side of the WP04 strangle:

* T019 — ``_planning_commit_worktree`` was RENAMED to
  ``_resolve_commit_worktree_for_kind`` (the old name lied post-D2: planning
  never transits coordination). The historical name is preserved as a
  backward-compatible alias (``mission.py``'s re-export shim and several
  existing unit tests key off the literal old name) — both names must resolve
  to the SAME function object, and the PRIMARY-kind invariant guard (a
  primary kind must NEVER reach the coord-staging body, even under coord
  topology) must survive the rename byte-for-byte.
* T021 — the ``CommitRouterResult.status`` outcome vocabulary
  (``"committed"`` / ``"unchanged"`` / ``"no_op_wrong_surface"`` / ``"error"``)
  is promoted from scattered string literals to named module constants
  (Sonar S1192); ``commit_for_mission`` must still PRODUCE the exact same
  string values through the constants.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import CommitTarget, MissionArtifactKind, MissionTopology
from specify_cli.coordination import commit_router
from specify_cli.git.protection_policy import ProtectionPolicy

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T019 — rename-with-alias
# ---------------------------------------------------------------------------


def test_resolve_commit_worktree_for_kind_is_the_real_name() -> None:
    """The renamed function is the canonical, DEFINED symbol."""
    assert callable(commit_router._resolve_commit_worktree_for_kind)
    assert (
        commit_router._resolve_commit_worktree_for_kind.__module__
        == commit_router.__name__
    )


def test_planning_commit_worktree_alias_is_the_same_object() -> None:
    """The historical name is an alias, not a forked duplicate (T019).

    ``mission.py`` still does
    ``from specify_cli.coordination.commit_router import _planning_commit_worktree
    as _planning_commit_worktree`` and several existing unit tests call
    ``commit_router._planning_commit_worktree``/``commit_router_mod.
    _planning_commit_worktree`` directly — the alias MUST be the identical
    object, not a re-implementation that could drift.
    """
    assert (
        commit_router._planning_commit_worktree
        is commit_router._resolve_commit_worktree_for_kind
    )


def test_primary_kind_guard_survives_the_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PRIMARY-partition kind never transits coordination, under either name.

    Real invariant (not incidental): this is what "keep the guard" means for
    T019 — a PRIMARY kind reaching the coord-staging body would mean a
    planning artifact got staged onto the coordination branch, the exact
    mis-route write-surface-coherence WP03 forbids. Proven by spying that
    ``_resolve_mid8`` (only reached PAST the PRIMARY short-circuit) is never
    consulted, under COORD topology, via BOTH the new name and the alias.
    """
    monkeypatch.setattr(
        commit_router, "resolve_topology", lambda _root, _slug: MissionTopology.COORD
    )
    consulted: list[str] = []

    def _spy_resolve_mid8(_root: object, slug: str) -> None:
        consulted.append(slug)
        return None

    monkeypatch.setattr(commit_router, "_resolve_mid8", _spy_resolve_mid8)

    artifact = tmp_path / "kitty-specs" / "001-demo" / "tasks.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Tasks\n", encoding="utf-8")

    for callee in (
        commit_router._resolve_commit_worktree_for_kind,
        commit_router._planning_commit_worktree,
    ):
        consulted.clear()
        worktree, paths = callee(
            tmp_path, "001-demo", (artifact,), kind=MissionArtifactKind.TASKS_INDEX
        )
        assert consulted == [], (
            f"{callee!r}: a PRIMARY kind reached the coord-staging body "
            "(_resolve_mid8 consulted) under coord topology — the T019 guard "
            "was weakened or deleted across the rename"
        )
        assert worktree == tmp_path
        assert paths == (artifact,)


# ---------------------------------------------------------------------------
# T021 — outcome-literal constants
# ---------------------------------------------------------------------------


def test_status_constants_match_the_literal_type_values() -> None:
    """The four named constants are the ONE source for the outcome vocabulary."""
    assert commit_router._STATUS_COMMITTED == "committed"
    assert commit_router._STATUS_UNCHANGED == "unchanged"
    assert commit_router._STATUS_NO_OP_WRONG_SURFACE == "no_op_wrong_surface"
    assert commit_router._STATUS_ERROR == "error"


def _make_policy(*, protected: bool) -> ProtectionPolicy:
    branches: frozenset[str] = frozenset({"main"}) if protected else frozenset()
    return ProtectionPolicy(protected_branches=branches, operator_hatch_active=False)


def test_commit_for_mission_no_op_wrong_surface_uses_the_named_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent artifact at the resolved placement yields the named constant."""
    monkeypatch.setattr(
        commit_router,
        "resolve_placement_only",
        lambda _root, _slug, *, kind: CommitTarget(ref="main"),
    )
    monkeypatch.setattr(
        commit_router, "resolve_topology", lambda _root, _slug: MissionTopology.SINGLE_BRANCH
    )
    monkeypatch.setattr(
        commit_router, "_resolve_primary_target_branch", lambda _root, _slug: "main"
    )

    missing_artifact = tmp_path / "kitty-specs" / "001-demo" / "spec.md"
    result = commit_router.commit_for_mission(
        tmp_path,
        "001-demo",
        (missing_artifact,),
        "chore: spec",
        _make_policy(protected=False),
        kind=MissionArtifactKind.SPEC,
    )

    assert result.status == commit_router._STATUS_NO_OP_WRONG_SURFACE


def test_commit_for_mission_unchanged_uses_the_named_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No committable paths (already-committed artifact) yields the named constant."""
    monkeypatch.setattr(
        commit_router,
        "resolve_placement_only",
        lambda _root, _slug, *, kind: CommitTarget(ref="main"),
    )
    monkeypatch.setattr(
        commit_router, "resolve_topology", lambda _root, _slug: MissionTopology.SINGLE_BRANCH
    )
    monkeypatch.setattr(
        commit_router, "_resolve_primary_target_branch", lambda _root, _slug: "main"
    )

    result = commit_router.commit_for_mission(
        tmp_path,
        "001-demo",
        (),
        "chore: spec",
        _make_policy(protected=False),
        kind=MissionArtifactKind.SPEC,
    )

    assert result.status == commit_router._STATUS_UNCHANGED
