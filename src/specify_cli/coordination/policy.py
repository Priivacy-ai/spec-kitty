"""WorkflowMutationPolicy — single chokepoint for protected-branch refusal.

This module implements the contract in
``contracts/workflow_mutation_policy.md``.

The policy is **pure**: it inspects a :class:`GitChangeSet` and returns
a :class:`PolicyVerdict`. It NEVER mutates repo state, NEVER writes
files, NEVER acquires locks. This is a deliberate design choice so the
pre-flight gate in :class:`~specify_cli.coordination.transaction.BookkeepingTransaction`
can refuse BEFORE any write happens.

The protected-branch list itself is owned by
:mod:`specify_cli.git.commit_helpers` and is unchanged by this mission.

Spec source: FR-019, FR-020, FR-021, C-012, C-016, NFR-007, NFR-008.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mission_runtime import CommitTarget
from specify_cli.coordination.types import (
    Allowed,
    DESTINATION_REF_NOT_FOUND,
    GitChangeSet,
    PolicyVerdict,
    PROTECTED_BRANCH_REFUSED,
    Refused,
)
from specify_cli.core.commit_guard import ProtectionState
from specify_cli.core.commit_guard import evaluate as evaluate_commit_guard
from specify_cli.git.protection_policy import ProtectionPolicy


def _normalize_ref(raw: str) -> str:
    """Strip ``refs/heads/`` prefix so all comparisons use short names.

    Provided as a free function so callers and tests can use the same
    helper to validate they are passing the canonical short-form ref.
    """
    return raw.removeprefix("refs/heads/")


def _local_branch_exists(repo_root: Path, branch: str) -> bool:
    """Return True iff ``refs/heads/<branch>`` resolves in ``repo_root``."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


# The ONE documented operator escape hatch (owned by
# :mod:`specify_cli.git.protection_policy`): setting this env var truthy declares
# the target branch unprotected for this repo. Named here so the #3536 no-coord
# remedy points at a real, followable action rather than an impossible one.
_PROTECTED_BRANCH_HATCH_ENV = "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS"


def _protected_branch_refusal(
    operation: str, ref: str, *, coord_available: bool | None,
) -> Refused:
    """Build the ``PROTECTED_BRANCH_REFUSED`` verdict, branching the remedy on
    coord-availability (#3536 / FR-005).

    ``coord_available`` is a topology fact threaded in by the caller from the
    authoritative commit-router predicate
    (:func:`specify_cli.coordination.commit_router.mission_has_coordination_branch`
    — itself ``routes_through_coordination(resolve_topology(...))``). It is NEVER
    a local coord-branch-presence check restated here (INV-3536-3); epic
    **#2739**'s protected-primary sub-issues consume the SAME predicate so the two
    fixes converge. Only ``coord_available is False`` (a ``lanes`` /
    ``single_branch`` topology, where no coord branch is ever minted) switches to
    the no-coord remedy; ``None`` (unknown) conservatively keeps the coord remedy.

    * coord-available (or unknown) → the existing "re-run through the coordination
      transaction" remedy (INV-3536-2 regression guard — the coord worktree really
      is auto-resolved).
    * no-coord → the coord branch does NOT exist, so that remedy is un-followable;
      emit a real one: commit to a non-protected branch, or declare the target
      unprotected for this repo via the operator escape hatch (INV-3536-1).
    """
    base_message = (
        f"Refusing to record {operation!r}: "
        f"destination ref {ref!r} is on this project's "
        "protected branch list. "
    )
    if coord_available is False:
        return Refused(
            error_code=PROTECTED_BRANCH_REFUSED,
            message=(
                base_message
                + "This mission uses a lanes / single-branch topology, which "
                "mints no coordination worktree, so bookkeeping cannot be "
                "redirected to one."
            ),
            destination_ref=ref,
            next_step=(
                f"Commit bookkeeping to a non-protected branch, or declare "
                f"{ref!r} unprotected for this repo by setting "
                f"{_PROTECTED_BRANCH_HATCH_ENV} to a truthy value "
                "(solo-fork operators who own the branch)."
            ),
        )
    return Refused(
        error_code=PROTECTED_BRANCH_REFUSED,
        message=(
            base_message + "Bookkeeping commits must target the coordination branch."
        ),
        destination_ref=ref,
        next_step=(
            "Re-run the command through the coordination "
            "transaction; the coord worktree is auto-resolved."
        ),
    )


def _remote_tracking_branch_exists(repo_root: Path, branch: str) -> bool:
    """Return True iff a remote-tracking ref matches the given name.

    We probe a few common shapes (``refs/remotes/<branch>`` and
    ``refs/remotes/origin/<branch>``) so the policy refuses confidently
    when the caller hands in something like ``origin/main``.
    """
    candidates = [f"refs/remotes/{branch}"]
    if "/" not in branch:
        candidates.append(f"refs/remotes/origin/{branch}")
    for candidate in candidates:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", candidate],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode == 0:
            return True
    return False


class WorkflowMutationPolicy:
    """The single chokepoint for protected-branch refusal.

    Called by
    :meth:`~specify_cli.coordination.transaction.BookkeepingTransaction.acquire`
    *before* any write happens, and called indirectly by
    :func:`safe_commit` *during* the commit attempt as a defense in depth.

    The policy is intentionally static / classmethod-only — there is no
    instance state, no caching, and no side effects.
    """

    @staticmethod
    def assert_allowed(
        change_set: GitChangeSet,
        *,
        coord_available: bool | None = None,
    ) -> PolicyVerdict:
        """Inspect ``change_set.destination_ref``.

        Returns :class:`Allowed` if the would-be commit is permitted;
        :class:`Refused` with a stable ``error_code`` otherwise.

        ``coord_available`` is the mission's topology fact — whether a
        coordination branch exists — threaded in by the caller from the
        authoritative commit-router predicate
        (:func:`specify_cli.coordination.commit_router.mission_has_coordination_branch`).
        It ONLY shapes the ``PROTECTED_BRANCH_REFUSED`` remedy (#3536 / FR-005):
        ``False`` (a ``lanes`` / ``single_branch`` topology that mints no coord
        branch) emits a followable no-coord remedy; ``True`` / ``None`` (default)
        keep the coord-transaction remedy unchanged. The policy NEVER re-derives
        the topology locally (INV-3536-3) — it stays a pure function of its
        inputs and consumes the threaded fact. ``evaluate`` remains ref-only
        (C-GUARD-3a); the fact lives OUTSIDE the ref-only guard.

        Validation order (every step short-circuits the rest):

        1. ``destination_ref`` must be non-empty and short-form
           (``refs/heads/...`` rejected as INVALID_SHAPE).
        2. ``destination_ref`` must not be a remote-tracking ref
           (rejected as NOT_LOCAL).
        3. ``destination_ref`` must exist as a local branch
           (rejected as NOT_FOUND).
        4. ``destination_ref`` must not be on the project's protected
           list (rejected as PROTECTED_BRANCH_REFUSED).

        This function is pure aside from a few read-only ``git
        rev-parse`` probes. It never writes files, never touches the
        feature status lock, never mutates the index.
        """
        ref = change_set.destination_ref
        repo_root = change_set.repo_root

        # 1. Shape check: empty / refs/heads / refs/remotes / leading
        # dash / leading slash / whitespace. The HEAD assertion inside
        # safe_commit() does a short-form compare, so any caller that
        # hands in a long-form ref would already be broken downstream.
        if not ref or not ref.strip() or ref != ref.strip():
            return Refused(
                error_code="DESTINATION_REF_INVALID_SHAPE",
                message=(
                    f"Refusing to record {change_set.operation!r}: "
                    f"destination_ref is empty or contains whitespace."
                ),
                destination_ref=ref,
                next_step=(
                    "Pass the short-form branch name "
                    "(e.g. 'kitty/mission-foo-01ABCDEF')."
                ),
            )
        if ref.startswith("refs/heads/") or ref.startswith("refs/remotes/"):
            return Refused(
                error_code="DESTINATION_REF_INVALID_SHAPE",
                message=(
                    f"Refusing to record {change_set.operation!r}: "
                    f"destination_ref {ref!r} is fully-qualified. "
                    "Use the short-form branch name."
                ),
                destination_ref=ref,
                next_step=(
                    "Strip the 'refs/heads/' prefix and pass the bare "
                    "branch name."
                ),
            )
        if ref.startswith("-") or ref.startswith("/"):
            return Refused(
                error_code="DESTINATION_REF_INVALID_SHAPE",
                message=(
                    f"Refusing to record {change_set.operation!r}: "
                    f"destination_ref {ref!r} has an invalid leading character."
                ),
                destination_ref=ref,
                next_step="Pass a valid short-form branch name.",
            )

        # 2. Remote-tracking shape: refuse explicitly with a NOT_LOCAL
        # code so callers can distinguish missing-branch from
        # wrong-namespace.
        # Only declare NOT_LOCAL when the *only* match is on the remote
        # side. If a local branch with the same name also exists, fall
        # through to the local-existence + protected checks (which can
        # still refuse).
        if _remote_tracking_branch_exists(repo_root, ref) and not _local_branch_exists(repo_root, ref):
            return Refused(
                error_code="DESTINATION_REF_NOT_LOCAL",
                message=(
                    f"Refusing to record {change_set.operation!r}: "
                    f"destination_ref {ref!r} resolves to a "
                    "remote-tracking branch. Bookkeeping commits "
                    "must target a local branch."
                ),
                destination_ref=ref,
                next_step=(
                    "Check out the corresponding local branch "
                    "first, or pass the local branch name."
                ),
            )

        # 3. Existence: local branch must resolve.
        if not _local_branch_exists(repo_root, ref):
            return Refused(
                error_code=DESTINATION_REF_NOT_FOUND,
                message=(
                    f"Refusing to record {change_set.operation!r}: "
                    f"destination_ref {ref!r} does not exist in {repo_root}."
                ),
                destination_ref=ref,
                next_step=(
                    "Confirm the branch exists locally "
                    "('git branch --list'), or create it first."
                ),
            )

        # 4. Protected-branch check. The protection DECISION is the SK policy
        # module's one decision (C-GUARD-1): delegate to ``commit_guard.evaluate``
        # over the asserted-at-the-surface ``capability`` so the pre-flight gate
        # and ``safe_commit`` agree on a single authority. The privilege is
        # NEVER derived from env or message — the caller's capability carries it.
        # The ONE retained operator escape hatch acts on the ProtectionState
        # INPUT (the operator declares the branch unprotected for this repo),
        # mirroring safe_commit's computation so the gate and the mechanism
        # cannot disagree; ``evaluate`` itself stays environment-free.
        # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
        # all config+hatch reads happen once here; is_protected() is I/O-free.
        is_protected = ProtectionPolicy.resolve(repo_root).is_protected(ref)
        # The guard decision reads only ``target.ref`` (commit_guard.evaluate is
        # ref-only, C-GUARD-3a); the topology ``.kind`` was vestigial carrier here
        # and is dropped (WP04 drain) — the VO field defaults transitionally until
        # WP16 removes it.
        guard_verdict = evaluate_commit_guard(
            CommitTarget(ref=ref),
            ProtectionState(is_protected=is_protected),
            change_set.capability,
        )
        if not guard_verdict.allowed:
            # #3536 / FR-005: the remedy branches on coord-availability (threaded
            # in via ``coord_available`` from the authoritative commit-router
            # predicate — never a local topology check here, INV-3536-3). See
            # ``_protected_branch_refusal``.
            return _protected_branch_refusal(
                change_set.operation, ref, coord_available=coord_available,
            )

        return Allowed()
