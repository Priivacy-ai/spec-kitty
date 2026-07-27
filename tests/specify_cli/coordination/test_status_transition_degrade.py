"""Red-first coverage for the WP05 pre-gate adoption (FR-005, IC-06b, C-004).

``status_transition._resolve_write_target`` now routes through the shared
``resolve_write_target_or_degrade`` helper (WP04, ``mission_runtime``), which
ADDS a ``_mission_meta_exists`` pre-gate the hand-rolled selector never had.

**The real behavior change this pins**: before this WP, the ``try`` arm
unconditionally called ``resolve_placement_only`` -- which, per its own
documented contract, *never raises* for a merely-absent mission; it silently
degrades **internally** to ``get_feature_target_branch(repo_root,
mission_slug)`` (the repo's generic target/primary branch), with **no
awareness of the caller's ``coord_branch`` argument at all** (that value only
ever fed the ``except`` arm, which this silent-internal-degrade contract made
unreachable in the merely-absent-mission window). So a caller supplying a real
``coord_branch`` in the bootstrap window got it silently DISCARDED -- the
write landed on the repo's primary branch instead.

The new pre-gate closes this: when ``meta.json`` is absent, resolution is
skipped entirely and ``degrade_ref = coord_branch or
get_feature_target_branch(...)`` is returned directly -- honoring a supplied
``coord_branch`` instead of silently dropping it.

See: spec.md FR-005 / C-004; contracts/degrade-and-read-hygiene.md
(C-DEGRADE-1); tasks/WP05-status-transition-pregate.md (T021-T023).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind
from mission_runtime.resolution import resolve_placement_only
from specify_cli.coordination.status_transition import _resolve_write_target
from specify_cli.core.paths import get_feature_target_branch

from tests.specify_cli.write_side.topology_fixtures import (
    TARGET_BRANCH,
    _run_git,
    build_coord,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _bare_repo(repo: Path) -> None:
    """A minimal real git repo with NO ``kitty-specs/`` mission dir at all."""
    repo.mkdir(parents=True, exist_ok=True)
    _run_git(repo, "init", "-q", "-b", TARGET_BRANCH)
    _run_git(repo, "config", "user.email", "x@e.test")
    _run_git(repo, "config", "user.name", "X")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "init")


class TestPreGateHonorsCoordBranchInBootstrapWindow:
    """T021 -- the added pre-gate branch.

    RED before the fix: the old ``_resolve_write_target`` discards a supplied
    ``coord_branch`` in the no-``meta.json`` window because
    ``resolve_placement_only`` silently degrades internally (never reaching
    the ``except`` arm that would have honored it) -- so the mission-less
    write lands on the repo's primary branch instead of the caller's coord
    ref. GREEN after: the pre-gate short-circuits before ``resolve_placement_only``
    is ever consulted, so ``degrade_ref = coord_branch or ...`` is honored
    directly.
    """

    def test_no_meta_json_with_coord_branch_now_returns_coord_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = tmp_path / "bare-repo"
        _bare_repo(repo)
        monkeypatch.chdir(repo)

        mission_slug = "no-such-mission-01kwp05pregate"
        coord_branch = "kitty/mission-no-such-mission-01kwp05pregate-coord"

        resolved = _resolve_write_target(repo, mission_slug, coord_branch)

        # Pre-fix, ``resolve_placement_only``'s silent internal degrade
        # returns the repo's generic target/primary branch here -- NOT the
        # caller's coord_branch. Post-fix, the pre-gate honors it directly.
        assert resolved == coord_branch
        # Sanity: the two candidate values genuinely differ in this fixture,
        # so the assertion above is a real discriminator, not a coincidence.
        assert coord_branch != get_feature_target_branch(repo, mission_slug)

    def test_no_meta_json_without_coord_branch_degrades_to_target_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Companion case: no ``coord_branch`` supplied -- the pre-gate's
        ``degrade_ref`` falls through to ``get_feature_target_branch``,
        matching the pre-existing (non-regressing) fallback behavior pinned
        by ``test_resolve_write_target_helper_no_meta_degrades_to_branch``.
        """
        repo = tmp_path / "bare-repo-no-coord"
        _bare_repo(repo)
        monkeypatch.chdir(repo)

        mission_slug = "no-such-mission-01kwp05pregate2"

        resolved = _resolve_write_target(repo, mission_slug, None)

        assert resolved == get_feature_target_branch(repo, mission_slug) == TARGET_BRANCH


class TestStatusStateStaysCoordAfterPreGateAdoption:
    """T023 -- C-004: STATUS_STATE keeps degrading to the coord ref, never PRIMARY.

    Normal-case (bootstrapped mission) preservation proof: adding the
    pre-gate must not disturb the coord-topology routing for a mission that
    genuinely HAS a ``meta.json`` -- the pre-gate passes through and
    ``resolve_placement_only`` is consulted exactly as before.
    """

    def test_bootstrapped_coord_mission_resolves_status_state_to_coord_ref(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        coord = build_coord(tmp_path)
        monkeypatch.chdir(coord.coord_worktree)

        resolved = _resolve_write_target(
            coord.main_root, coord.mission_slug, coord.coord_branch
        )

        assert resolved == coord.coord_branch
        assert resolved != TARGET_BRANCH
        assert (
            resolved
            == resolve_placement_only(
                coord.main_root,
                coord.mission_slug,
                kind=MissionArtifactKind.STATUS_STATE,
            ).ref
        )
