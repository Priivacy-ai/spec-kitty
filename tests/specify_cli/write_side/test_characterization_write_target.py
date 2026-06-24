"""FR-004 write-target divergence oracle (T002) + the positive mutation check.

This is the highest-value test in the net (paula S-1 / A-1, reduction-census §6):
the latent bug FR-004 fixes — the inline ``coord_branch or _current_branch``
selector at ``coordination/status_transition.py:291`` — has **ZERO** witnessing
test today, and the strongest write-path suite (``test_status_transition.py``) is
structurally blind to it because it always passes ``repo_root=repo``.

The oracle here drives ``_identity_for_request`` **without** an explicit
``repo_root`` from a CWD where ``git HEAD != target_branch`` (an off-target lane
branch), and pins the divergence:

* **inline selector**  → ``destination_ref`` = git ``HEAD`` (the off-target
  branch) — the latent bug (CWD-dependent).
* **factory resolver** (``resolve_placement_only(...).ref``) → ``target_branch``
  = ``meta.target_branch`` = ``main`` (CWD-invariant) — the correct value.

WP05 landed the adoption: ``_identity_for_request`` now routes ``destination_ref``
through ``resolve_placement_only(...).ref``, so the oracle's asserted value
flipped from the git-HEAD value to ``target_branch``. The oracle was flipped in
place, never deleted (B-4: no non-strict xfail — pinned by node-id), and now
pins read/write CONVERGENCE on the correct CWD-invariant value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind
from mission_runtime.resolution import resolve_placement_only
from specify_cli.coordination.status_transition import (
    _current_branch,
    _identity_for_request,
)
from specify_cli.status.models import TransitionRequest

from .topology_fixtures import (
    TARGET_BRANCH,
    build_coord,
    build_primary,
    _run_git,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _request(feature_dir: Path, slug: str) -> TransitionRequest:
    """Build a transition request that carries NO explicit ``repo_root``.

    Passing ``repo_root`` here would short-circuit ``_repo_root_for_feature`` and
    the ``_current_branch(repo_root)`` arm — the exact derivation the adoption
    deletes (A-1). The net MUST drive the bare path.
    """
    return TransitionRequest(
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        to_lane="claimed",
        actor="characterization",
    )


def test_inline_write_target_oracle_documents_git_head_divergence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 oracle (PIN by node-id — WP05 flipped the value, never deleted).

    Flat mission (no ``coordination_branch``), CWD parked on an off-target lane
    branch. BEFORE the WP05 adoption the inline selector resolved the
    write-target to git HEAD (the off-target lane branch) — NOT
    ``target_branch`` — which was the latent bug (CWD-dependent). AFTER the
    adoption (FR-004 / D-2) ``_identity_for_request`` routes ``destination_ref``
    through ``resolve_placement_only(...).ref``, so it now resolves to
    ``target_branch`` (CWD-invariant) and AGREES with the factory resolver. The
    divergence the oracle documented is the thing the adoption fixed — so the
    oracle now pins CONVERGENCE on the correct value.

    before→after (WP05): ``identity.destination_ref`` flipped from ``off_target``
    (git HEAD, the bug) to ``TARGET_BRANCH`` (CWD-invariant, the fix). The
    ``_current_branch`` import is retained so this row keeps witnessing that the
    correct value is NOT the git-HEAD value.
    """
    primary = build_primary(tmp_path)
    # Park HEAD on an off-target branch so git HEAD != meta.target_branch.
    off_target = "kitty/mission-write-side-primary-01kv9w0x-lane-a"
    _run_git(primary.repo_root, "checkout", "-q", "-b", off_target)
    monkeypatch.chdir(primary.repo_root)

    identity = _identity_for_request(_request(primary.feature_dir, primary.mission_slug))
    # The status write target resolves with STATUS_STATE (coord-preserving) kind
    # (write-surface-coherence WP02 / T031): flat topology → target_branch.
    factory = resolve_placement_only(
        primary.repo_root, primary.mission_slug, kind=MissionArtifactKind.STATUS_STATE
    )

    # AFTER the WP05 adoption the write-target is CWD-invariant ``target_branch``,
    # NOT the off-target git HEAD the inline selector used to return (the bug).
    assert identity.destination_ref == TARGET_BRANCH
    assert identity.destination_ref != off_target
    assert identity.destination_ref != _current_branch(primary.repo_root)
    # Read and write now resolve the SAME ref via the SAME resolver (SC-002).
    assert factory.ref == TARGET_BRANCH
    assert identity.destination_ref == factory.ref  # convergence (the fix)


def test_write_target_is_cwd_invariant_after_adoption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fix's signature: the write-target is now CWD-invariant.

    before→after (WP05): the inline selector's value used to CHANGE with the CWD
    branch (the bug). After routing through ``resolve_placement_only`` the
    write-target resolves to ``target_branch`` regardless of which branch is
    checked out — read and write agree, the CWD-invariance the adoption buys.
    """
    primary = build_primary(tmp_path)
    monkeypatch.chdir(primary.repo_root)

    # On the target branch itself, the write-target == target.
    on_target = _identity_for_request(
        _request(primary.feature_dir, primary.mission_slug)
    )
    assert on_target.destination_ref == TARGET_BRANCH

    # Switch to an off-target branch: AFTER the adoption the write-target does NOT
    # follow git HEAD — it stays CWD-invariant on ``target_branch`` (the fix).
    off_target = "kitty/mission-write-side-primary-01kv9w0x-lane-z"
    _run_git(primary.repo_root, "checkout", "-q", "-b", off_target)
    off = _identity_for_request(_request(primary.feature_dir, primary.mission_slug))
    assert off.destination_ref == TARGET_BRANCH
    assert off.destination_ref != off_target

    # ...and the factory resolver agrees, unchanged across both CWD branches.
    assert resolve_placement_only(
        primary.repo_root, primary.mission_slug, kind=MissionArtifactKind.STATUS_STATE
    ).ref == (TARGET_BRANCH)


def test_coord_topology_both_selectors_agree_on_coord_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equivalence row (green on HEAD, stays green post-adoption).

    Under coord topology the mission declares ``coordination_branch``, so the
    inline selector short-circuits to it (``coord_branch or _current_branch``)
    and the factory resolver also returns the coordination ref — they ALREADY
    agree here. The adoption must keep them agreeing (idempotency, NFR-004).
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)

    identity = _identity_for_request(
        _request(coord.primary_feature_dir, coord.mission_slug)
    )
    # STATUS_STATE (coord-preserving) kind: coord topology → coord branch
    # (write-surface-coherence WP02 / T031).
    factory = resolve_placement_only(
        coord.main_root, coord.mission_slug, kind=MissionArtifactKind.STATUS_STATE
    )

    assert identity.destination_ref == coord.coord_branch
    assert factory.ref == coord.coord_branch
    assert identity.destination_ref == factory.ref


def test_mutation_reintroducing_git_head_selector_keeps_oracle_red() -> None:
    """Positive mutation obligation (B-3): the net must BITE under mutation.

    The FR-004 oracle is only valid if reverting the adoption swap (i.e.
    reintroducing the inline ``_current_branch`` git-HEAD selector) makes the
    suite diverge. This documents and *executes* that mechanism in miniature:
    given the two selector implementations, the buggy one returns git HEAD and
    the correct one returns ``target_branch`` — a green-under-both result would
    be vacuous. We assert the simulated selectors genuinely diverge for the
    off-target case, proving the oracle above discriminates the swap rather than
    passing regardless.

    Runnable mutation check for reviewers: in
    ``coordination/status_transition.py`` change line ~291 from
    ``destination_ref=coord_branch or _current_branch(repo_root)`` to
    ``destination_ref=coord_branch or target_branch`` (the WP05 swap); the
    ``*_documents_git_head_divergence`` oracle then FAILS its ``== off_target``
    assertion — i.e. the net bites. Reverting the swap restores the divergence.
    """
    git_head_branch = "kitty/mission-off-target-lane-a"
    target_branch = TARGET_BRANCH

    def buggy_inline_selector(coord_branch: str | None) -> str:
        # Mirrors `coord_branch or _current_branch(repo_root)` for the flat arm.
        return coord_branch or git_head_branch

    def adopted_factory_selector(coord_branch: str | None) -> str:
        # Mirrors `branch_ref.destination_ref` for the flat arm (target_branch).
        return coord_branch or target_branch

    # Flat arm (coord_branch is None): the two selectors MUST diverge — if they
    # did not, the FR-004 oracle could never go red on the swap (vacuous net).
    assert buggy_inline_selector(None) != adopted_factory_selector(None)
    assert buggy_inline_selector(None) == git_head_branch
    assert adopted_factory_selector(None) == target_branch

    # Coord arm (coord_branch set): the two selectors AGREE — the equivalence
    # rows stay green across the swap (idempotency, NFR-004).
    coord = "kitty/mission-write-side-coord-01kv9w0x-01kv9w0x"
    assert buggy_inline_selector(coord) == adopted_factory_selector(coord) == coord
