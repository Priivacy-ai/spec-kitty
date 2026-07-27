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


class TestDegradeRefStaysLazyOnTheHappyPath:
    """PR #2963 landing-fold (P2): the call-site's OWN eager
    ``get_feature_target_branch`` call must be gone from the happy path.

    Before this fix, ``degrade_ref = coord_branch or
    get_feature_target_branch(...)`` was computed unconditionally at the top
    of ``_resolve_write_target`` — the ``or`` only short-circuits on a
    *truthy* ``coord_branch``, so every mission WITHOUT one in hand (all
    SINGLE_BRANCH/LANES topologies, and even coord-topology callers that
    genuinely have no ``coord_branch`` handy) paid for a REDUNDANT eager call
    on every status transition, on top of the ONE call
    ``resolve_placement_only`` already makes internally to build its
    ``CommitTarget`` (``resolution.py:1332`` — unconditional, unavoidable,
    and not part of this fix). Old behavior: 2 calls (1 discarded). Fixed
    behavior: 1 call (the port's own).

    This pins the fix as an observable call-COUNT: a counting spy on the
    single origin (``specify_cli.core.paths.get_feature_target_branch`` --
    both the old call site and the port import it fresh via a
    function-scoped ``from ... import``, so patching the origin module
    attribute intercepts either) must see exactly ONE invocation, not two,
    for a resolvable coord mission with ``coord_branch=None``.
    """

    def test_no_coord_branch_resolvable_mission_calls_target_branch_lookup_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        coord = build_coord(tmp_path)
        monkeypatch.chdir(coord.coord_worktree)

        import specify_cli.core.paths as core_paths

        original = core_paths.get_feature_target_branch
        calls: list[tuple[Path, str]] = []

        def _spy(repo_root: Path, mission_slug: str) -> str:
            calls.append((repo_root, mission_slug))
            return original(repo_root, mission_slug)

        monkeypatch.setattr(core_paths, "get_feature_target_branch", _spy)

        resolved = _resolve_write_target(coord.main_root, coord.mission_slug, None)

        # The load-bearing assertion: exactly ONE call (the port's own
        # internal resolution inside ``resolve_placement_only``), not two
        # (the retired redundant eager call-site computation this
        # landing-fold removes). Checked BEFORE any further calls the test
        # itself might make below, so it reflects only the production call
        # graph. A regression reintroducing the eager ``coord_branch or
        # get_feature_target_branch(...)`` at the top of
        # ``_resolve_write_target`` flips this back to 2.
        assert len(calls) == 1, (
            "expected exactly one get_feature_target_branch call (the "
            f"placement port's own internal resolution); got {len(calls)} "
            f"calls={calls!r} -- the call-site eager computation has regressed"
        )

        # The port still resolves to the coord ref -- passing coord_branch=None
        # must not change the resolved value for a resolvable coord mission;
        # STATUS_STATE routes to the coordination branch regardless of what
        # the caller happens to have in hand. (This comparison call is made
        # AFTER the call-count assertion above, so it does not pollute it.)
        assert resolved == coord.coord_branch
        assert (
            resolved
            == resolve_placement_only(
                coord.main_root,
                coord.mission_slug,
                kind=MissionArtifactKind.STATUS_STATE,
            ).ref
        )

    def test_degrade_path_still_returns_feature_target_branch_when_port_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Companion case: when the port genuinely fails to resolve (no
        ``meta.json``) and no ``coord_branch`` is supplied, the lazy
        ``except`` arm still degrades to ``get_feature_target_branch`` --
        the laziness must not regress the fallback into never firing at all.
        """
        repo = tmp_path / "bare-repo-lazy-degrade"
        _bare_repo(repo)
        monkeypatch.chdir(repo)

        mission_slug = "no-such-mission-01kwp05lazydegrade"

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
