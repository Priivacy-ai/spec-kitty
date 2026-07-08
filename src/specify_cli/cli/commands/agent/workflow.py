"""Action commands for AI agents - display prompts and instructions.

WP04 (#676) — Review-cycle counter inventory
============================================
The ``review-cycle-N.md`` artifact and the implicit counter ``N`` (computed
from ``len(glob("review-cycle-*.md")) + 1``) are mutated in **exactly one**
place across the runtime: ``_persist_review_feedback`` in
``src/specify_cli/cli/commands/agent/tasks.py`` (currently lines 403-456).
That helper is invoked from a single call site —
``move-task ... --to planned --review-feedback-file <path>`` — which is the
canonical reviewer-rejection event (``tasks.py`` ~line 1233).

Sites in this module that **mention** ``review-cycle-*`` artifacts but do
**not** mutate the counter or write any artifact:

* line ~112-113 — docstring of ``_resolve_review_feedback_pointer`` describing
  the canonical pointer scheme.
* line ~279 — ``_has_prior_rejection`` performs a read-only ``glob`` check.
* line ~798-807 — fix-mode prompt rendering reads the latest artifact via
  ``ReviewCycleArtifact.from_file`` / ``.latest``; no write.
* line ~1729-1731 — review-prompt rendering computes a *placeholder* path
  ``review-cycle-{next_cycle}.md`` for inclusion in instructional output to
  the human reviewer. Nothing is written; the file only materialises when
  the reviewer subsequently runs ``move-task --to planned``.

Re-running ``spec-kitty agent action implement WPNN`` is therefore a
counter-no-op by construction: this module never calls
``ReviewCycleArtifact.write`` or ``ReviewCycleArtifact.next_cycle_number``.
The unit and integration tests under
``tests/specify_cli/cli/commands/agent/test_review_cycle_counter.py`` and
``tests/integration/test_review_cycle_rejection_only.py`` lock in this
contract.
"""

from __future__ import annotations

from specify_cli.core.constants import (
    KITTY_SPECS_DIR,
    MISSION_TYPE_RESEARCH,
)
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)
import json
import logging
import re
import subprocess
import contextlib
from datetime import UTC
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from rich.console import Console

    from mission_runtime import PlacementSeam
    from specify_cli.bulk_edit.gate import DiffCheckResult

from charter.context import build_charter_context
from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts
from specify_cli.cli.commands.implement import implement as top_level_implement
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.coordination.types import CommitReceipt
from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    dependency_readiness_for_wp,
    get_dependents,
)
from specify_cli.core.paths import get_feature_target_branch, get_main_repo_root, is_worktree_context, locate_project_root
from specify_cli.core.utils import write_text_within_directory
from mission_runtime import CommitTarget, MissionArtifactKind
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed
from specify_cli.mission import get_deliverables_path, get_mission_type
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.review.prompt_metadata import (
    build_review_prompt_metadata,
    validate_review_prompt_metadata,
    write_review_prompt_with_metadata,
)
from specify_cli.review.antipattern_checklist import render_wp_review_antipattern_checklist
from specify_cli.review.cycle import REVIEW_FEEDBACK_SENTINELS, resolve_review_cycle_pointer
from specify_cli.status import feature_status_lock
from specify_cli.status import AgentAssignment, Lane
from specify_cli.status import (
    WorkPackageClaimConflict,
    WorkPackageStartRejected,
    read_wp_frontmatter,
    start_implementation_status,
    start_review_status,
)
from specify_cli.task_utils import (
    append_activity_log,
    build_document,
    extract_scalar,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)
from specify_cli.workspace.context import (
    ResolvedWorkspace,
    husk_resolution_error,
    resolve_workspace_for_wp,
)

logger = logging.getLogger(__name__)

_REVIEW_FEEDBACK_SENTINELS = REVIEW_FEEDBACK_SENTINELS
_STATUS_EVENTS_FILENAME = "status.events.jsonl"
_STATUS_FILENAME = "status.json"


# ---------------------------------------------------------------------------
# WP06 T027/T029 -- BookkeepingTransaction routing helpers
# ---------------------------------------------------------------------------
#
# These small helpers centralize the policy: when the mission has a
# coordination_branch in meta.json (post-WP03 missions), every lifecycle
# write is routed through BookkeepingTransaction so the event-log append
# is atomically reversible on commit failure (FR-010, fixes #1348).
# Legacy missions fall back to the bare safe_commit path that WP08 will
# replace.

# Module-level accumulator of CommitReceipts for the T029 terminal
# summary. Reset by each top-level invocation.
_WORKFLOW_COMMIT_RECEIPTS: list[dict[str, object]] = []


def _enforce_bulk_edit_diff_compliance(
    *,
    feature_dir: Path,
    main_repo_root: Path,
    target_branch: str,
    review_workspace: ResolvedWorkspace,
    check_review_diff_compliance: Callable[..., DiffCheckResult | None],
    render_diff_check_failure: Callable[..., None],
    rich_console: Console,
) -> None:
    """Enforce per-file bulk-edit diff compliance for a WP under review (FR-007/8).

    Inspects the WP's diff against its lane base branch and rejects modifications
    to forbidden or unclassified surfaces. Raises ``typer.Exit(1)`` on failure;
    surfaces ``manual_review`` warnings without blocking.
    """
    # The mission branch is the canonical base for a WP lane diff. If the
    # review is running from the main repo (not a lane worktree), this
    # still resolves because the mission branch exists until merge
    # cleanup. If the branch cannot be resolved, fall back to the
    # target_branch captured earlier in this function.
    try:
        from specify_cli.lanes.persistence import read_lanes_json as _read_lanes_json

        _lanes_manifest = _read_lanes_json(feature_dir)
        _base_ref = _lanes_manifest.mission_branch if _lanes_manifest is not None else target_branch
    except Exception:
        _base_ref = target_branch
    # The WP diff must be the lane branch's changes on top of the mission
    # branch, NOT `HEAD`. When review runs from the main repo checkout,
    # `HEAD` is the mission's *target* branch (e.g. feat/...), so diffing
    # base..HEAD surfaces the entire target-branch delta (hundreds of
    # unrelated files) and the bulk-edit gate false-blocks. Use the WP's
    # resolved lane branch as head; fall back to HEAD only for repo_root
    # (direct-to-target / planning) workspaces where the changes really
    # are on the current HEAD.
    _head_ref = review_workspace.branch_name or "HEAD"
    _diff_result = check_review_diff_compliance(
        feature_dir=feature_dir,
        repo_root=main_repo_root,
        base_ref=_base_ref,
        head_ref=_head_ref,
    )
    if _diff_result is None:
        # Non-bulk-edit mission — skip silently. check_review_diff_compliance
        # returns None when change_mode is not bulk_edit, which shouldn't
        # happen here given the outer guard, but belt-and-braces.
        pass
    elif not _diff_result.passed:
        render_diff_check_failure(_diff_result, rich_console)
        raise typer.Exit(1)
    elif _diff_result.warnings:
        # Surface manual_review notes but don't block.
        for _w in _diff_result.warnings:
            rich_console.print(f"[yellow]manual_review:[/] {_w}")


def _reset_workflow_receipts() -> None:
    """Clear the per-invocation commit-receipt accumulator."""
    _WORKFLOW_COMMIT_RECEIPTS.clear()


def _record_receipt(
    destination_ref: str,
    message: str,
    outcome: str,
    *,
    sha: str | None = None,
    wp_id: str | None = None,
) -> None:
    """Record a single workflow commit receipt for the T029 summary."""
    _WORKFLOW_COMMIT_RECEIPTS.append({
        "destination_ref": destination_ref,
        "message": message,
        "outcome": outcome,  # "committed" or "refused"
        "sha": sha,
        "wp_id": wp_id,
    })


def _mark_receipt_refused(*, commit_sha: str) -> None:
    """Mark a previously committed receipt refused after rollback."""
    for receipt in reversed(_WORKFLOW_COMMIT_RECEIPTS):
        if receipt.get("sha") == commit_sha:
            receipt["outcome"] = "refused"
            return


def _restore_status_artifacts(
    *,
    events_path: Path,
    pre_emit_event_size: int,
    status_path: Path,
    pre_emit_status_bytes: bytes | None,
) -> None:
    """Restore canonical status files after a failed workflow commit."""
    try:
        if events_path.exists():
            with events_path.open("ab") as _fh:
                _fh.truncate(pre_emit_event_size)
    except OSError:
        logger.exception("Could not truncate %s on commit failure", events_path)

    try:
        if pre_emit_status_bytes is None:
            status_path.unlink(missing_ok=True)
        else:
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_bytes(pre_emit_status_bytes)
    except OSError:
        logger.exception("Could not restore %s on commit failure", status_path)


def _safe_commit_recovery_commit_sha(exc: BaseException) -> str | None:
    """Return commit SHA when a chained safe_commit recovery failure committed."""
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, SafeCommitRecoveryFailed) and current.commit_sha is not None:
            return current.commit_sha
        current = current.__cause__
    return None


def _transaction_path_for(
    *,
    source_path: Path,
    repo_root: Path,
    worktree_root: Path,
) -> Path:
    """Map a canonical-repo path to the same relative path in a worktree."""
    source_path = source_path.resolve()
    try:
        relative_path = source_path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"Refusing to mirror path outside repo/worktree scope: {source_path}"
        ) from exc
    return worktree_root / relative_path


def _load_coord_branch_meta(feature_dir: Path) -> tuple[str | None, str | None, str | None]:
    """Read (coordination_branch, mission_id, mid8) from meta.json.

    Returns ``(None, None, None)`` for legacy missions or when meta.json
    is missing / unreadable. Never raises.
    """
    from specify_cli.lanes.branch_naming import resolve_mid8
    from specify_cli.mission_metadata import load_meta

    try:
        meta = load_meta(feature_dir)
    except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
        return (None, None, None)
    if not isinstance(meta, dict):
        return (None, None, None)
    coord = meta.get("coordination_branch") or None
    mid = meta.get("mission_id") or None
    # Route the mission_id truncation through the canonical resolver (FR-001);
    # the isinstance/>= 8 guard keeps the ``else None`` fallback byte-identical.
    mid8 = meta.get("mid8") or (
        resolve_mid8(feature_dir.name, mission_id=mid)
        if isinstance(mid, str) and len(mid) >= 8
        else None
    )
    return (coord, mid, mid8)


def _canonical_status_feature_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the canonical read-side mission directory for status state.

    Routes through the single guarded read-side seam
    (:func:`resolve_handle_to_read_path`, WP01/IC-01): the seam reads the
    PRIMARY ``meta.json`` to learn the declared identity, runs the ONE
    sanctioned mid8 cascade (``resolve_declared_mid8``), and returns the
    existence-gated topology-aware directory. This subsumes the prior bespoke
    ``candidate_feature_dir_for_mission`` → ``_load_coord_branch_meta`` →
    ``resolve_mid8`` → ``resolve_mission_read_path`` cascade. (FR-002, C-007)

    Subsumption note: the retired ``_mid8_for_mission_read_path`` read the COORD
    branch's meta via ``_load_coord_branch_meta`` to derive mid8, while the seam
    anchors on PRIMARY meta. mid8 is mission *identity* (``mission_id`` / ``mid8``
    are identical on both surfaces), so the primary anchor yields the same mid8;
    no caller of ``_canonical_status_feature_dir`` consumed any coord-branch-only
    meta field (all three read callers only need the resolved directory).
    """
    from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

    return resolve_handle_to_read_path(main_repo_root, mission_slug)


def _merge_event_log_bytes(existing: bytes, incoming: bytes) -> bytes:
    """Compatibility wrapper for the explicit coordination merge contract."""
    from specify_cli.coordination.status_service import (
        merge_append_preserving_coordination_event_log_bytes,
    )

    return merge_append_preserving_coordination_event_log_bytes(existing, incoming)


def _commit_via_coordination_transaction(
    *,
    coord_branch: str,
    repo_root: Path,
    mission_slug: str,
    paths: list[Path],
    message: str,
    operation: str,
    mission_id: str,
    mid8: str,
    wp_id: str,
) -> CommitReceipt:
    """Commit workflow changes via BookkeepingTransaction."""
    from specify_cli.coordination.transaction import (
        BookkeepingPolicyRefused,
        BookkeepingTransaction,
    )

    try:
        with BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=mission_id,
            mission_slug=mission_slug,
            mid8=mid8,
            destination_ref=coord_branch,
            operation=operation,
        ) as txn:
            for path in paths:
                if not path.exists():
                    continue
                if path.resolve().is_relative_to(txn.worktree_root.resolve()):
                    txn.stage_path(path)
                    continue
                txn_path = _transaction_path_for(
                    source_path=path,
                    repo_root=repo_root,
                    worktree_root=txn.worktree_root,
                )
                if txn_path.resolve() == path.resolve():
                    txn.stage_path(path)
                else:
                    incoming = path.read_bytes()
                    # #1602: the canonical event log is append-only. Never let a
                    # main-checkout copy overwrite (clobber) the coordination
                    # branch's lane history — union-merge instead so existing
                    # coord events always survive.
                    if path.name == _STATUS_EVENTS_FILENAME and txn_path.exists():
                        incoming = _merge_event_log_bytes(
                            txn_path.read_bytes(), incoming
                        )
                    txn.write_artifact(txn_path, incoming)
            receipt = txn.commit(message)
    except BookkeepingPolicyRefused as policy_exc:
        _record_receipt(
            coord_branch,
            message,
            "refused",
            wp_id=wp_id,
        )
        print(
            f"Error: Bookkeeping policy refused {operation}: "
            f"{policy_exc.verdict.error_code}: {policy_exc.verdict.message}"
        )
        raise typer.Exit(1) from policy_exc

    _record_receipt(
        coord_branch,
        message,
        "committed",
        sha=receipt.commit_sha,
        wp_id=wp_id,
    )
    return receipt


def _render_lane_auto_rebase_failure(exc: BaseException) -> None:
    from specify_cli.lanes.lifecycle_sync import LaneAutoRebaseSyncError

    if not isinstance(exc, LaneAutoRebaseSyncError):
        print(f"Error: {exc}")
        return

    payload = exc.to_dict()
    print(f"Error: {payload['error_code']}: {payload['halt_reason']}")
    print(f"  lane_id: {payload['lane_id']}")
    print(f"  lane_worktree_path: {payload['lane_worktree_path']}")
    print(f"  coordination_branch: {payload['coordination_branch']}")
    print(f"  coordination_head: {payload['coordination_head']}")


def _sync_lane_after_coordination_commit(
    *,
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    coord_branch: str,
) -> None:
    from specify_cli.lanes.lifecycle_sync import sync_lane_after_coordination_commit

    # No ``feature_dir``: ``sync_lane_after_coordination_commit`` self-resolves the
    # LANE_STATE (lanes.json) read onto the PRIMARY anchor (#2185). Passing the
    # coord-aware STATUS dir here previously routed the lanes read onto the husk.
    sync_lane_after_coordination_commit(
        repo_root=repo_root,
        mission_slug=mission_slug,
        wp_id=wp_id,
        coordination_branch=coord_branch,
    )


def _revert_coordination_commit(receipt: CommitReceipt) -> None:
    """Undo a lifecycle coordination commit after lane sync refusal."""
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=receipt.worktree_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if head_result.returncode != 0:
        raise RuntimeError(
            "could not inspect coordination worktree HEAD before rollback: "
            f"{(head_result.stderr or head_result.stdout).strip()}"
        )
    if head_result.stdout.strip() != receipt.commit_sha:
        raise RuntimeError(
            "refusing to rollback lifecycle commit because coordination branch "
            f"advanced from {receipt.commit_sha} to {head_result.stdout.strip()}"
        )

    revert_result = subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "revert",
            "--no-edit",
            receipt.commit_sha,
        ],
        cwd=receipt.worktree_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if revert_result.returncode != 0:
        raise RuntimeError(
            "failed to rollback lifecycle coordination commit after lane sync "
            f"refusal: {(revert_result.stderr or revert_result.stdout).strip()}"
        )


def _workflow_placement_seam(repo_root: Path, mission_slug: str) -> PlacementSeam:
    """Construct the ONE placement-seam instance every workflow.py wrapper shares.

    read-surface-ssot-closeout WP04 (T017/T018): the pre-existing
    ``_resolve_workflow_placement`` (coord-primary-partition-lock) was the
    lone raw ``placement_seam(...)`` construction in this module — a pinned
    invariant (``test_workflow_has_exactly_one_placement_seam_call_site``).
    Adding the sibling READ-side wrapper (:func:`_resolve_workflow_read_dir`)
    for IC-04's routing without a SECOND raw construction means both wrappers
    now share this one constructor instead of each importing/calling
    ``placement_seam`` independently — the invariant's *intent* (no per-site
    re-derivation) is preserved even though its enclosing-function detail
    moves here.
    """
    from mission_runtime import placement_seam

    return placement_seam(repo_root, mission_slug)


def _resolve_workflow_placement(
    *, repo_root: Path, mission_slug: str, kind: MissionArtifactKind
) -> CommitTarget:
    """Resolve the write :class:`CommitTarget` for ``kind`` via the placement seam.

    The SINGLE choke point every workflow.py lifecycle/status write site
    routes through (coord-primary-partition-lock C-001 / C-005): a thin
    wrapper over :func:`_workflow_placement_seam` — never re-derived
    inline at each write site (reviewer guidance explicitly forbids 4x
    inlining the seam call across a 2800-line module). Callers that already
    hold identity metadata for a DIFFERENT purpose (e.g. the
    ``coord_branch``/``mission_id``/``mid8`` triple
    :func:`_load_coord_branch_meta` reads to select the BookkeepingTransaction
    mechanism) keep reading that separately — this helper answers only "where
    does a write of this kind land", the seam's one job.
    """
    return _workflow_placement_seam(repo_root, mission_slug).write_target(kind)


def _resolve_workflow_read_dir(
    *, repo_root: Path, mission_slug: str, kind: MissionArtifactKind
) -> Path:
    """Resolve the read directory for ``kind`` via the placement seam (IC-04/T017).

    The sibling READ-side choke point to :func:`_resolve_workflow_placement`:
    every workflow.py site that read a mission directory through the
    kind-blind ``resolve_feature_dir_for_mission`` husk (NFR-001 /
    Directive-041 — do not pin the old kind-blind coord husk) now routes
    through this ONE wrapper over :func:`_workflow_placement_seam`
    ``.read_dir(kind)`` instead of re-deriving the seam call inline at each
    read site.
    """
    read_dir: Path = _workflow_placement_seam(repo_root, mission_slug).read_dir(kind)
    return read_dir


def _commit_via_legacy_safe_commit(
    *,
    repo_root: Path,
    target_branch: str,
    paths: list[Path],
    message: str,
    wp_id: str,
) -> None:
    """Commit workflow changes directly on legacy mission branches."""
    # Legacy mission-branch workflow commits land on ``target_branch`` (a lane /
    # mission branch), which is normally not protected. STANDARD asserts no
    # protected-branch flow: a protected ``target_branch`` (legacy missions
    # tracking ``main``) is REFUSED by the guard, never waived (FR-008).
    result = safe_commit(
        repo_root=repo_root,
        worktree_root=repo_root,
        target=CommitTarget(ref=target_branch),
        message=message,
        paths=tuple(paths),
        capability=GuardCapability.STANDARD,
    )
    _record_receipt(
        target_branch,
        message,
        "committed",
        sha=getattr(result, "sha", None),
        wp_id=wp_id,
    )


def _commit_workflow_change(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    target_branch: str,
    paths: list[Path],
    message: str,
    operation: str,
    wp_id: str,
    pre_emit_event_size: int,
    pre_emit_status_bytes: bytes | None,
    auto_rebase_lane_after_commit: bool = False,
) -> None:
    """Commit a workflow change with atomic event-log rollback on failure.

    For modern (post-WP03) missions with ``coordination_branch`` in
    meta.json, routes through :class:`BookkeepingTransaction` so the
    event-log append is atomically reversible (FR-010, FR-011) and the
    commit lands on the coordination branch (FR-005).

    For legacy missions without ``coordination_branch``, falls back to
    the bare :func:`safe_commit` path but still truncates the event log
    on commit failure to ``pre_emit_event_size``. WP08 will replace this
    fallback with a proper legacy bridge.

    Records the outcome via :func:`_record_receipt` so the T029
    terminal summary can render it.

    Raises:
        typer.Exit(1): On commit failure (after rollback).
    """
    coord_branch, mission_id, mid8 = _load_coord_branch_meta(feature_dir)
    events_path = feature_dir / _STATUS_EVENTS_FILENAME
    status_path = feature_dir / _STATUS_FILENAME
    # T017: the seam-resolved STATUS_STATE placement. The MECHANISM choice
    # below (BookkeepingTransaction vs. the legacy safe_commit fallback) still
    # keys off ``_load_coord_branch_meta`` — it needs the concrete
    # ``mission_id``/``mid8`` identity fields the transaction requires, which
    # the seam's ref-only CommitTarget does not carry. But the legacy leaf's
    # DESTINATION ref is threaded from this ONE resolution rather than the
    # raw, un-seam-resolved ``target_branch`` parameter (C-001).
    placement = _resolve_workflow_placement(
        repo_root=repo_root, mission_slug=mission_slug, kind=MissionArtifactKind.STATUS_STATE
    )
    if placement.ref != target_branch:
        # Diagnostic only (never authoritative): the seam is the single
        # placement authority (C-001); ``target_branch`` is whatever ref the
        # caller had checked out (:func:`_ensure_target_branch_checked_out`
        # tracks the user's CURRENT branch, not necessarily the mission's
        # canonical target). A divergence here is exactly the ad hoc-vs-seam
        # drift this mission exists to surface.
        logger.debug(
            "_commit_workflow_change: seam-resolved STATUS_STATE placement %r "
            "diverges from the caller-supplied target_branch %r for mission %r",
            placement.ref,
            target_branch,
            mission_slug,
        )

    if coord_branch and mission_id and mid8:
        try:
            receipt = _commit_via_coordination_transaction(
                coord_branch=str(coord_branch),
                repo_root=repo_root,
                mission_id=str(mission_id),
                mission_slug=mission_slug,
                mid8=str(mid8),
                paths=paths,
                message=message,
                operation=operation,
                wp_id=wp_id,
            )
        except typer.Exit:
            _restore_status_artifacts(
                events_path=events_path,
                pre_emit_event_size=pre_emit_event_size,
                status_path=status_path,
                pre_emit_status_bytes=pre_emit_status_bytes,
            )
            raise
        except Exception as exc:  # noqa: BLE001 — surface + exit
            recovery_commit_sha = _safe_commit_recovery_commit_sha(exc)
            if recovery_commit_sha is None:
                _restore_status_artifacts(
                    events_path=events_path,
                    pre_emit_event_size=pre_emit_event_size,
                    status_path=status_path,
                    pre_emit_status_bytes=pre_emit_status_bytes,
                )
            _record_receipt(
                str(coord_branch),
                message,
                "refused",
                sha=recovery_commit_sha,
                wp_id=wp_id,
            )
            print(
                f"Error: Failed to record {operation} via BookkeepingTransaction: {exc}"
            )
            raise typer.Exit(1) from exc
        if auto_rebase_lane_after_commit:
            try:
                _sync_lane_after_coordination_commit(
                    repo_root=repo_root,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    coord_branch=str(coord_branch),
                )
            except Exception as exc:  # noqa: BLE001 — structured sync refusal
                try:
                    _revert_coordination_commit(receipt)
                    _mark_receipt_refused(commit_sha=receipt.commit_sha)
                    _restore_status_artifacts(
                        events_path=events_path,
                        pre_emit_event_size=pre_emit_event_size,
                        status_path=status_path,
                        pre_emit_status_bytes=pre_emit_status_bytes,
                    )
                except Exception as rollback_exc:  # noqa: BLE001
                    print(f"Error: Failed to rollback lifecycle state after lane sync refusal: {rollback_exc}")
                _render_lane_auto_rebase_failure(exc)
                raise typer.Exit(1) from exc
        return

    # Legacy fallback (TODO(WP08): replace with the legacy bridge).
    try:
        _commit_via_legacy_safe_commit(
            repo_root=repo_root,
            target_branch=placement.ref,
            paths=paths,
            message=message,
            wp_id=wp_id,
        )
    except Exception as exc:  # noqa: BLE001 — surface + truncate + exit
        recovery_commit_sha = _safe_commit_recovery_commit_sha(exc)
        if recovery_commit_sha is None:
            _restore_status_artifacts(
                events_path=events_path,
                pre_emit_event_size=pre_emit_event_size,
                status_path=status_path,
                pre_emit_status_bytes=pre_emit_status_bytes,
            )
        _record_receipt(
            placement.ref,
            message,
            "refused",
            sha=recovery_commit_sha,
            wp_id=wp_id,
        )
        recovery_note = (
            "Commit was created before staging recovery failed; status artifacts were not rolled back."
            if recovery_commit_sha is not None
            else "Event log rolled back to pre-emit state."
        )
        print(
            f"Error: Failed to commit workflow status update for {wp_id}: {exc}. "
            f"{recovery_note}"
        )
        raise typer.Exit(1) from exc


def _print_commit_summary(*, command_name: str, json_output: bool = False) -> None:
    """T029: render the accumulated commit summary to the terminal.

    Human format::

        [implement] Commits recorded:
          - <branch>  <message>  ✓ committed
          - <branch>  <message>  ✗ refused

    JSON format: prints ``{"commits": [...]}`` on its own line so
    machine consumers can parse the trailing record.
    """
    if not _WORKFLOW_COMMIT_RECEIPTS:
        return
    if json_output:
        import json as _json
        print(_json.dumps({"commits": list(_WORKFLOW_COMMIT_RECEIPTS)}))
        return
    print(f"[{command_name}] Commits recorded:")
    for receipt in _WORKFLOW_COMMIT_RECEIPTS:
        glyph = "[ok]" if receipt.get("outcome") == "committed" else "[refused]"
        print(
            f"  - {receipt['destination_ref']}  {receipt['message']}  {glyph}"
        )


def _write_prompt_to_file(
    command_type: str,
    mission_slug: str,
    wp_id: str,
    content: str,
    *,
    repo_root: Path,
) -> Path:
    """Write full prompt content to a temp file for agents with output limits.

    The filename is scoped by ``mission_slug`` so that concurrent missions
    sharing a WP id (e.g. two missions both with ``WP01``) do not collide on the
    same ``/tmp`` path and overwrite each other's prompt (#1831).

    Args:
        command_type: "implement" or "review"
        mission_slug: Mission slug used to scope the temp filename
        wp_id: Work package ID (e.g., "WP01")
        content: Full prompt content to write
        repo_root: Repository root; scopes the file under the shared,
            sweepable prompt namespace (WP02 / FR-003) instead of the flat
            ``tempfile.gettempdir()`` root.

    Returns:
        Path to the written file
    """
    from runtime.next._tmp_namespace import prompt_tmp_dir

    prompt_file = (
        prompt_tmp_dir(repo_root)
        / f"spec-kitty-{command_type}-{mission_slug}-{wp_id}.md"
    )
    prompt_file.write_text(content, encoding="utf-8")
    return prompt_file


def _render_resolved_agent_identity(
    assignment: AgentAssignment,
) -> list[str]:
    """Render the resolved agent 4-tuple for inclusion in implement/review prompts.

    Surfaces ``tool``, ``model``, ``profile_id`` and ``role`` so the implement
    and review prompt-render path no longer silently drops the trailing fields
    of a colon-formatted ``--agent`` string. See WP03 / GitHub issue #833.
    """
    profile_display = assignment.profile_id if assignment.profile_id else "(default)"
    role_display = assignment.role if assignment.role else "(default)"
    return [
        "Resolved agent identity:",
        f"  tool       : {assignment.tool}",
        f"  model      : {assignment.model}",
        f"  profile_id : {profile_display}",
        f"  role       : {role_display}",
    ]


def _resolve_git_common_dir(repo_root: Path) -> Path | None:
    """Resolve absolute git common-dir path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    raw_value = result.stdout.strip()
    if not raw_value:
        return None
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    return common_dir


def _resolve_review_feedback_pointer(repo_root: Path, pointer: str) -> Path | None:
    """Resolve a review feedback pointer to a file path.

    Supports two pointer formats:
    - ``review-cycle://<mission_slug>/<wp_slug>/review-cycle-N.md``
      → ``kitty-specs/<mission_slug>/tasks/<wp_slug>/review-cycle-N.md``
    - ``feedback://<mission_slug>/<task_id>/<filename>``  (legacy)
      → ``.git/spec-kitty/feedback/<mission_slug>/<task_id>/<filename>``

    Also handles legacy absolute-path strings.
    Returns None for sentinel values such as ``"force-override"`` and
    ``"action-review-claim"``, or any
    unrecognised / non-existent pointer.
    """
    try:
        return resolve_review_cycle_pointer(repo_root, pointer).path
    except ValueError:
        return None


def _review_feedback_root(feature_dir: Path) -> Path:
    """The tree root review-feedback pointers resolve against (READ-side only).

    coord-primary-partition-lock WP07 (T034 dedup): the SOLE ``parent.parent``
    navigation for review-feedback pointer resolution, so the write-side
    rederivation ratchet (``test_no_write_side_rederivation.py``) has exactly
    ONE line to allow-list here instead of two duplicate call sites. This is
    NOT an FR-005 write-target/identity derivation -- ``feature_dir`` is
    ``<root>/kitty-specs/<slug>/``, so ``parent.parent`` is the tree root
    (coord worktree or main repo) that review-feedback artifacts are read
    from, a purely structural READ-path navigation unrelated to mission_id /
    mid8 / primary_root or the placement seam.
    """
    return feature_dir.parent.parent


def _read_wp_events(feature_dir: Path, wp_id: str):
    """Return canonical status events for a single work package."""
    try:
        from specify_cli.status import read_events as _read_status_events

        return [event for event in _read_status_events(feature_dir) if event.wp_id == wp_id]
    except Exception:
        return []


def _latest_review_feedback_reference(
    feature_dir: Path,
    wp_id: str,
) -> tuple[str | None, Path | None, int | None]:
    """Return the newest canonical review feedback reference for *wp_id*.

    Operational sentinels like ``action-review-claim`` are intentionally
    skipped so implement/fix handoff uses the persisted review artifact
    instead of the transient reviewer claim marker.
    """
    # Review feedback artifacts are committed under kitty-specs/ inside
    # whichever tree feature_dir lives in (coord worktree or main repo).
    feedback_root = _review_feedback_root(feature_dir)
    wp_events = _read_wp_events(feature_dir, wp_id)
    for index in range(len(wp_events) - 1, -1, -1):
        event = wp_events[index]
        if event.review_ref is None:
            continue
        review_ref = event.review_ref.strip()
        if not review_ref or review_ref in _REVIEW_FEEDBACK_SENTINELS:
            continue
        return review_ref, _resolve_review_feedback_pointer(feedback_root, review_ref), index
    return None, None, None


def _resolve_review_feedback_context(
    feature_dir: Path,
    wp_id: str,
    wp_frontmatter: str,
) -> tuple[bool, str | None, Path | None, str | None]:
    """Resolve review-feedback presence and the canonical readable artifact."""
    review_feedback_ref, review_feedback_file, _ = _latest_review_feedback_reference(feature_dir, wp_id)
    if review_feedback_ref is not None:
        return True, review_feedback_ref, review_feedback_file, "canonical"

    fm_review_status = extract_scalar(wp_frontmatter, "review_status")
    fm_review_feedback = extract_scalar(wp_frontmatter, "review_feedback")
    if fm_review_status and str(fm_review_status) == "has_feedback":
        ref = str(fm_review_feedback).strip() if fm_review_feedback else None
        feedback_root = _review_feedback_root(feature_dir)
        path = _resolve_review_feedback_pointer(feedback_root, ref) if ref else None
        return True, ref, path, "frontmatter"

    return False, None, None, None


def _render_charter_context(repo_root: Path, action: str) -> str:
    """Render charter context for workflow prompts."""
    try:
        context = build_charter_context(repo_root, action=action, mark_loaded=True)
        return context.text
    except Exception as exc:
        return f"Governance: unavailable ({exc})"


def _workspace_contract_description(workspace, wp_id: str) -> str:
    """Describe the canonical execution workspace for prompt output."""
    if workspace.lane_id:
        shared = ", ".join(workspace.lane_wp_ids or [wp_id])
        return f"Workspace contract: lane {workspace.lane_id} shared by {shared}"
    return "Workspace contract: repository root planning workspace"


def _render_isolation_banner(wp_id: str, mode: str) -> list[str]:
    """Render the WP-isolation warning box shared by ``implement``/``review``.

    Campsite SAFE item #2 (S1192, DIRECTIVE_025 tidy-first): extracts the
    9x-duplicated blank-box banner line out of the two inline blocks
    (``implement`` / ``review``). ``mode`` (``"implement"`` or ``"review"``)
    selects the verb line and the two mode-specific bullets — ``implement``
    additionally warns about subtask ownership, ``review`` additionally warns
    about review/approval ownership. The rendered lines are byte-identical to
    the blocks this replaces (behaviour-preserving extraction, no new text).
    """
    lines = [
        "╔" + "=" * 78 + "╗",
        "║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║",
        "╠" + "=" * 78 + "╣",
    ]
    if mode == "implement":
        lines.append(f"║  YOU ARE ASSIGNED TO: {wp_id:<55} ║")
    else:
        lines.append(f"║  YOU ARE REVIEWING: {wp_id:<56} ║")
    lines.append("║                                                                          ║")
    lines.append("║  ✅ DO:                                                                  ║")
    lines.append(f"║     • Only modify status of {wp_id:<47} ║")
    if mode == "implement":
        lines.append(f"║     • Only mark subtasks belonging to {wp_id:<36} ║")
    lines.append("║     • Ignore git commits and status changes from other agents           ║")
    lines.append("║                                                                          ║")
    lines.append("║  ❌ DO NOT:                                                              ║")
    lines.append(f"║     • Change status of any WP other than {wp_id:<34} ║")
    lines.append("║     • React to or investigate other WPs' status changes                 ║")
    if mode == "implement":
        lines.append(f"║     • Mark subtasks that don't belong to {wp_id:<33} ║")
    else:
        lines.append(f"║     • Review or approve any WP other than {wp_id:<32} ║")
    lines.append("║                                                                          ║")
    lines.append("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
    lines.append("║       Git commits from other WPs are other agents - ignore them.        ║")
    lines.append("╚" + "=" * 78 + "╝")
    return lines


def _render_wp_prompt_wrapper(wp_text: str) -> list[str]:
    """Render the WP-prompt BEGIN/END marker wrapper shared by ``implement``/``review``.

    Campsite SAFE item #3 (DIRECTIVE_025 tidy-first): extracts the
    byte-identical 9-line block both commands use to wrap the raw WP file
    text between banner markers. Behaviour-preserving.
    """
    return [
        "╔" + "=" * 78 + "╗",
        "║  WORK PACKAGE PROMPT BEGINS                                            ║",
        "╚" + "=" * 78 + "╝",
        "",
        wp_text,
        "",
        "╔" + "=" * 78 + "╗",
        "║  WORK PACKAGE PROMPT ENDS                                              ║",
        "╚" + "=" * 78 + "╝",
        "",
    ]


def _shared_artifact_guidance(workspace, repo_root: Path, mission_slug: str) -> list[str]:
    """Render workspace-specific guidance about where mission artifacts live."""
    if workspace.lane_id:
        return [
            "📚 SHARED MISSION ARTIFACTS:",
            f"   Spec, plan, and tasks are visible from the primary checkout: {repo_root}/kitty-specs/{mission_slug}/",
            "   Status authority resolves through the coordination worktree for modern missions.",
            "   Use this lane workspace for code/tests; do not expect shared mission artifacts here",
        ]

    return [
        "📚 PLANNING ARTIFACTS:",
        f"   This WP runs in the repository root: {repo_root}",
        f"   Mission artifacts for this WP live here too: {repo_root}/kitty-specs/{mission_slug}/",
        "   Do not look for a separate lane worktree or workspace context file",
    ]


app = typer.Typer(name="action", help="Mission action commands that display prompts and instructions for agents", no_args_is_help=True)

def _is_missing_canonical_status_error(exc: BaseException) -> bool:
    """Return True when *exc* indicates missing canonical status bootstrap.

    Uses a structured ``isinstance`` check against the typed
    :class:`CanonicalStatusNotFoundError` (exported from the status facade)
    rather than matching prose in the exception message. ``locate_work_package``
    raises this type unwrapped (via ``get_wp_lane`` → ``get_lane_from_frontmatter``),
    so the type is visible at the call sites; a substring gate on the message
    would silently break the moment the wording is reworded (Cluster D).
    """
    from specify_cli.status import CanonicalStatusNotFoundError

    return isinstance(exc, CanonicalStatusNotFoundError)


def _missing_canonical_status_message(
    wp_id: str, mission_slug: str, feature_dir: Path | None = None
) -> str:
    """Return a consistent hard-fail message for missing canonical status.

    When *feature_dir* is provided, surface an unresolved WP dependency cycle as
    the actionable root cause (#1589) instead of a "run finalize-tasks" hint that
    loops while the cycle keeps aborting finalize.
    """
    if feature_dir is not None:
        from specify_cli.status import uninitialized_status_error

        return uninitialized_status_error(mission_slug, wp_id, feature_dir)
    return f"WP {wp_id} has no canonical status. Run `spec-kitty agent mission finalize-tasks --mission {mission_slug}` to initialize."


def _has_prior_rejection(
    feature_dir: Path,
    wp_slug: str,
    normalized_wp_id: str,
) -> bool:
    """Check if a WP has review-cycle artifacts from a prior rejection.

    A prior rejection is active when:
    1. Review-cycle artifact files exist in the sub-artifact directory.
    2. The newest canonical review feedback reference for this WP resolves to a
       readable artifact.
    3. The WP has not since resolved to an approved/done terminal state.

    Args:
        feature_dir: Path to kitty-specs/<mission>/ in the main repo.
        wp_slug: Full WP file stem, e.g. "WP01-some-title".
        normalized_wp_id: Canonical WP ID, e.g. "WP01".

    Returns:
        True iff both artifact files and a rejection event are present.
    """
    sub_artifact_dir = feature_dir / "tasks" / wp_slug
    if not sub_artifact_dir.exists():
        return False
    if not list(sub_artifact_dir.glob("review-cycle-*.md")):
        return False

    wp_events = _read_wp_events(feature_dir, normalized_wp_id)
    if not wp_events:
        return False

    review_feedback_ref, review_feedback_file, review_feedback_index = _latest_review_feedback_reference(
        feature_dir,
        normalized_wp_id,
    )
    if review_feedback_ref is None or review_feedback_file is None or review_feedback_index is None:
        return False

    if any(event.to_lane in {Lane.APPROVED, Lane.DONE} for event in wp_events[review_feedback_index + 1 :]):
        return False

    latest_event = wp_events[-1]
    return latest_event.to_lane not in {Lane.APPROVED, Lane.DONE}


def _ensure_target_branch_checked_out(repo_root: Path, mission_slug: str) -> tuple[Path, str]:
    """Resolve branch context without auto-checkout (respects user's current branch).

    Returns the planning repo root and the user's current branch.
    Shows a consistent branch banner.

    Routes target-branch resolution through ``resolve_action_context`` (FR-033:
    ExecutionContext hardening — route residue surfaces).  This is the canonical
    OHS entry point; ``target_branch`` is read from its returned ActionContext
    rather than derived independently.
    """
    from mission_runtime import ActionContextError, resolve_action_context
    from specify_cli.core.git_ops import get_current_branch

    main_repo_root = get_main_repo_root(repo_root)

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        print("Error: Detached HEAD — checkout a branch before continuing.")
        raise typer.Exit(1)

    # Canonical target-branch resolution through the OHS entry point.
    try:
        _ctx = resolve_action_context(
            main_repo_root,
            action="tasks",
            feature=mission_slug,
        )
        target = _ctx.target_branch
    except ActionContextError:
        # Fall back to the direct helper if execution context cannot be resolved
        # (e.g. mission directory not yet created during early planning).
        target = get_feature_target_branch(main_repo_root, mission_slug)

    # Show consistent branch banner
    if current_branch == target:
        print(f"Branch: {current_branch} (target for this mission)")
    else:
        print(f"Branch: on '{current_branch}', mission targets '{target}'")

    # Return current branch (no checkout performed)
    return main_repo_root, current_branch


def _find_mission_slug(
    explicit_mission: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Require an explicit mission slug (no auto-detection).

    When repo_root is supplied the handle is resolved via the canonical
    mission resolver which handles ambiguous numeric-prefix handles, mid8
    prefixes, and full ULID forms.

    Args:
        explicit_mission: Mission slug provided explicitly.
        repo_root: Repository root; if provided, enables canonical resolver.

    Returns:
        Mission slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If mission slug is not provided.
    """
    if not explicit_mission or not explicit_mission.strip():
        print("Error: --mission <slug> is required")
        raise typer.Exit(1)

    raw_handle = explicit_mission.strip()
    if repo_root is not None:
        legacy_dir = candidate_feature_dir_for_mission(get_main_repo_root(repo_root), raw_handle)
        if legacy_dir.exists():
            # F-001: the candidate resolver canonicalizes mid8/ULID/numeric
            # handles, so the resolved directory's NAME — not the raw operator
            # handle — is the canonical mission slug downstream consumers need.
            return legacy_dir.name
        try:
            resolved = resolve_mission_handle(raw_handle, repo_root)
            return resolved.mission_slug
        except (SystemExit, typer.Exit):
            if legacy_dir.exists():
                return legacy_dir.name
            raise

    return raw_handle


def _normalize_wp_id(wp_arg: str) -> str:
    """Normalize WP ID from various formats to standard WPxx format.

    Args:
        wp_arg: User input (e.g., "wp01", "WP01", "WP01-foo-bar")

    Returns:
        Normalized WP ID (e.g., "WP01")
    """
    # Handle formats: wp01 → WP01, WP01 → WP01, WP01-foo-bar → WP01
    wp_upper = wp_arg.upper()

    # Extract just the WPxx part
    if wp_upper.startswith("WP"):
        # Split on hyphen and take first part
        return wp_upper.split("-")[0]
    else:
        # Assume it's like "01" or "1", prefix with WP
        return f"WP{wp_upper.lstrip('WP')}"


def _preview_claimable_wp_for_mission(repo_root: Path, mission_slug: str):
    """Return the shared claimable preview for *mission_slug*, if tasks exist.

    WP04 / T016 / FR-002: tasks/ and dependency reads route to the PRIMARY
    checkout via ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` so a
    coord-topology mission (whose tasks/ live on PRIMARY, not the STATUS-only
    coord husk) is never reported as having no tasks.  The status-event read
    uses the coord-aware ``candidate_feature_dir_for_mission`` so lanes come
    from the authoritative coord husk — never a worktree-local copy, which may
    lag the latest status commit (dependency gate invariant preserved).
    """
    from runtime.next.discovery import preview_claimable_wp

    main_root = get_main_repo_root(repo_root)
    # WORK_PACKAGE_TASK is PRIMARY-partition: routes to the primary checkout
    # regardless of coord topology (no shadowing by STATUS-only coord husk).
    planning_dir = resolve_planning_read_dir(
        main_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    if not (planning_dir / "tasks").is_dir():
        return None
    # status_dir: coord-aware so events come from the coord husk under coord
    # topology (candidate_feature_dir_for_mission is the STATUS-partition leg).
    status_dir = candidate_feature_dir_for_mission(main_root, mission_slug)
    return preview_claimable_wp(planning_dir, status_dir=status_dir)


def _auto_claim_failure_message(preview: object | None) -> str:
    """Return the user-facing error when auto-claim has no selectable WP."""
    selection_reason = getattr(preview, "selection_reason", None)
    if selection_reason == "dependencies_not_satisfied":
        return (
            "dependencies_not_satisfied: planned work packages are waiting on "
            "dependencies; all dependencies must be approved or done before "
            "implementation can start"
        )
    return "No planned work packages found. Specify a WP ID explicitly."


def _analysis_report_gate_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the mission dir the implement gate reads ``analysis-report.md`` from.

    #1989: this MUST be the topology-blind primary checkout — where
    ``record-analysis`` writes the report — NOT the coord-aware
    ``candidate_feature_dir_for_mission`` (which resolves to the coordination
    worktree once one exists, and that worktree lacks the report + ``spec.md`` for
    the freshness hash, so the gate would falsely report it missing). Extracted as
    a named seam so the read-anchor decision is unit-testable in isolation.
    """
    # WP05/FR-005: route through _canonicalize_primary_read_handle so every handle
    # form (bare mid8 / ULID / numeric prefix / bare human slug) lands on the
    # correct composed primary dir.
    return primary_feature_dir_for_mission(
        main_repo_root,
        _canonicalize_primary_read_handle(main_repo_root, mission_slug),
    )


def _require_current_analysis_report(feature_dir: Path, repo_root: Path, mission_slug: str) -> None:
    """Block implementation until `/spec-kitty.analyze` is persisted and fresh."""
    from specify_cli.analysis_report import (
        ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
        check_analysis_report_current,
    )

    analysis_freshness = check_analysis_report_current(feature_dir, repo_root)
    if analysis_freshness.ok:
        return

    # Header line is always emitted first, in every branch.
    print("Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.")

    if analysis_freshness.reason == ANALYSIS_REPORT_REASON_CARRIER_FORMAT:
        print(
            "  Reason: analysis-report.md is in carrier format (analysis-findings/v1) — written directly\n"
            "          rather than via record-analysis. The implement gate requires the persisted\n"
            "          outer-wrapper format (artifact_type: spec-kitty.analysis-report)."
        )
        print(
            "  Recovery: spec-kitty agent mission record-analysis "
            f"--mission {mission_slug} --input-file {analysis_freshness.path}"
        )
    elif analysis_freshness.missing:
        print(f"  Missing: {analysis_freshness.path}")
        print("  Run step 1: /spec-kitty.analyze")
        print(
            "  Run step 2: spec-kitty agent mission record-analysis "
            f"--mission {mission_slug} --input-file -"
        )
    elif analysis_freshness.mismatches:
        print(f"  Reason: {analysis_freshness.reason}")
        print("  Stale inputs:")
        for artifact_name in sorted(analysis_freshness.mismatches):
            print(f"    - {artifact_name}")
        print(f"  Run: /spec-kitty.analyze --mission {mission_slug}")
    else:
        if analysis_freshness.reason:
            print(f"  Reason: {analysis_freshness.reason}")
        print(f"  Run: /spec-kitty.analyze --mission {mission_slug}")

    raise typer.Exit(1)


def _ensure_workspace_materialized(
    workspace: ResolvedWorkspace,
    wp_id: str,
    create_workspace: Callable[[], None],
) -> None:
    """Ensure the already-resolved *workspace* is materialized on disk.

    FR-008/#1832 (C-IC05) — single resolution path. *workspace* is the
    canonical resolution produced once by the caller. This helper consumes that
    resolved context; it never re-runs ``resolve_workspace_for_wp``. A husk
    (path present, no ``.git``) is absent-but-blocked (#1833). When the
    workspace does not yet exist, *create_workspace* is invoked to materialize
    the worktree at the already-resolved path; ``ResolvedWorkspace.exists`` then
    re-stats disk, so the same contract reflects the freshly-created worktree.
    A second resolution authority — which could independently report "no
    workspace could be resolved" on a verified read-path — is exactly what this
    function eliminates.

    A pure side-effect seam: it mutates disk (and re-stats the resolved context
    in place) but returns nothing — the caller already holds the canonical
    ``ResolvedWorkspace`` and must not rebind it to a second value.

    Raises:
        typer.Exit: husk detected, creation attempted from a worktree, or the
            path was not materialized after creation.
    """
    if workspace.is_husk:
        print(f"Error: {husk_resolution_error(workspace.worktree_path)}")
        raise typer.Exit(1)

    if workspace.exists:
        return

    cwd = Path.cwd().resolve()
    if is_worktree_context(cwd):
        print("Error: Workspace does not exist and cannot be created from a worktree.")
        print("Run this command from the main repository:")
        print(f"  spec-kitty agent action implement {wp_id} --agent <your-name>")
        raise typer.Exit(1)

    print(f"Creating workspace for {wp_id}...")
    try:
        create_workspace()
    except typer.Exit:
        # Worktree creation failed - propagate error
        raise
    except Exception as e:
        print(f"Error creating worktree: {e}")
        raise typer.Exit(1) from e

    # Single resolution path: re-stat the already-resolved workspace; do NOT
    # re-resolve via a second authority.
    if not workspace.exists:
        print(
            f"Error: implement completed but the workspace at {workspace.worktree_path} "
            f"for {wp_id} was not materialized."
        )
        raise typer.Exit(1)


@app.command(name="implement")
def implement(
    wp_id: Annotated[str | None, typer.Argument(help="Work package ID (e.g., WP01, wp01, WP01-slug) - auto-detects first planned if omitted")] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name (required for auto-move to in_progress)")] = None,
    allow_sparse_checkout: Annotated[
        bool,
        typer.Option(
            "--allow-sparse-checkout",
            help=(
                "Proceed even if legacy sparse-checkout state is detected. "
                "Use of this override is logged. Does not bypass the commit-time "
                "data-loss backstop."
            ),
        ),
    ] = False,
    acknowledge_not_bulk_edit: Annotated[
        bool,
        typer.Option(
            "--acknowledge-not-bulk-edit",
            help="Suppress the bulk-edit inference warning when spec language resembles a bulk edit but the mission is not one.",
        ),
    ] = False,
) -> None:
    """Display work package prompt with implementation instructions.

    This command outputs the full work package prompt content so agents can
    immediately see what to implement, without navigating the file system.

    Automatically moves WP from planned to in_progress (requires --agent to track who is working).

    Examples:
        spec-kitty agent action implement WP01 --agent claude
        spec-kitty agent action implement WP02 --agent claude
        spec-kitty agent action implement wp01 --agent codex
        spec-kitty agent action implement --agent gemini  # auto-detects first planned WP
    """
    # WP06 T029: reset the commit-receipt accumulator for this invocation.
    _reset_workflow_receipts()
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)
        repo_root = get_main_repo_root(repo_root)

        mission_slug = _find_mission_slug(explicit_mission=mission, repo_root=repo_root)

        # -- WP05/T021 FR-007: Sparse-checkout preflight --
        # Runs BEFORE any worktree creation or state changes. Same surface as
        # merge (see _run_lane_based_merge). If --allow-sparse-checkout is set,
        # require_no_sparse_checkout emits a structured override log and
        # returns; the WP01 commit-layer backstop still guards commits.
        from specify_cli.git.sparse_checkout import (
            SparseCheckoutPreflightError,
            require_no_sparse_checkout,
        )

        _main_repo_for_preflight = get_main_repo_root(repo_root)
        _mission_id_for_preflight: str | None = None
        try:
            from specify_cli.mission_metadata import resolve_mission_identity

            # FR-005 (#2186): anchor the preflight ``mission_id`` on the PRIMARY
            # checkout. The coord-aware resolver lands on the STATUS-only husk (no
            # meta.json) — a wrong/empty id for the sparse-checkout override log.
            _identity = resolve_mission_identity(
                primary_feature_dir_for_mission(
                    _main_repo_for_preflight,
                    _canonicalize_primary_read_handle(
                        _main_repo_for_preflight, mission_slug
                    ),
                )
            )
            _mission_id_for_preflight = _identity.mission_id
        except Exception:  # noqa: BLE001 — meta.json may not exist for legacy missions
            _mission_id_for_preflight = None

        try:
            require_no_sparse_checkout(
                repo_root=_main_repo_for_preflight,
                command="spec-kitty agent action implement",
                override_flag=allow_sparse_checkout,
                actor=agent,
                mission_slug=mission_slug,
                mission_id=_mission_id_for_preflight,
            )
        except SparseCheckoutPreflightError as exc:
            # Surface as a user-facing error. No worktree is created.
            print(f"Error: {exc}")
            raise typer.Exit(1) from exc

        # Ensure planning repo is on the target branch before we start
        # (needed for auto-commits and status tracking inside this command)
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug)

        # Determine which WP to implement
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first planned WP
            _claimable_preview = _preview_claimable_wp_for_mission(repo_root, mission_slug)
            normalized_wp_id = getattr(_claimable_preview, "wp_id", None)
            if not normalized_wp_id:
                print(f"Error: {_auto_claim_failure_message(_claimable_preview)}")
                raise typer.Exit(1)

        # Find WP file to read dependencies
        try:
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        except RuntimeError as e:
            if _is_missing_canonical_status_error(e):
                print(f"Error: {_missing_canonical_status_message(normalized_wp_id, mission_slug)}")
                raise typer.Exit(1)
            print(f"Error locating work package: {e}")
            raise typer.Exit(1)
        except Exception as e:
            print(f"Error locating work package: {e}")
            raise typer.Exit(1)

        # C-006 charter precondition: check BEFORE any worktree creation or
        # status transition.
        _wp_profile = extract_scalar(getattr(wp, "frontmatter", None) or "", "agent_profile")
        if _wp_profile:
            from charter.exceptions import CharterActivationError  # noqa: PLC0415
            from charter.invocation_context import ProjectContext  # noqa: PLC0415

            _pack_ctx = ProjectContext.from_repo(main_repo_root).require_pack_context()
            _activated = _pack_ctx.activated_agent_profiles
            if _activated is not None and _wp_profile not in _activated:
                _activated_list = ", ".join(sorted(_activated)) or "(none)"
                _resolution_cmd = f"spec-kitty charter activate agent-profile {_wp_profile}"
                print(
                    f"Error: WP{normalized_wp_id} charter precondition FAILED\n"
                    f"  Assigned profile '{_wp_profile}' is not accessible through "
                    f"the active charter.\n"
                    f"  Currently activated: {_activated_list}\n"
                    f"  Run: {_resolution_cmd}"
                )
                raise CharterActivationError(
                    f"artifact={_wp_profile!r}, "
                    f"activated={_activated_list!r}, "
                    f"resolution={_resolution_cmd!r}"
                )

        wp_meta, _ = read_wp_frontmatter(wp.path)

        from specify_cli.status import reduce as _dep_reduce_events
        from specify_cli.status import read_events as _dep_read_events
        from specify_cli.status import resolve_lane_alias as _dep_resolve_alias

        _dependency_feature_dir = _canonical_status_feature_dir(main_repo_root, mission_slug)
        _dependency_snapshot = _dep_reduce_events(_dep_read_events(_dependency_feature_dir))
        _dependency_lanes = {
            _wp_id: _state.get("lane", Lane.PLANNED)
            for _wp_id, _state in _dependency_snapshot.work_packages.items()
        }
        if normalized_wp_id not in _dependency_snapshot.work_packages:
            print(f"Error: {_missing_canonical_status_message(normalized_wp_id, mission_slug)}")
            raise typer.Exit(1)

        # Only gate the not-yet-started claim transition. Re-invoking implement on
        # a WP that is already in_progress/for_review/.../approved (resume, prompt
        # redisplay, fix-cycle) must not be rejected just because a dependency
        # later regressed out of approved/done — the lifecycle treats those
        # re-invocations as no-op resumes, not new claims.
        try:
            _self_lane = Lane(_dep_resolve_alias(str(_dependency_lanes.get(normalized_wp_id, Lane.PLANNED))))
        except ValueError:
            _self_lane = Lane.PLANNED
        if _self_lane in (Lane.PLANNED, Lane.CLAIMED):
            _dependency_readiness = dependency_readiness_for_wp(
                normalized_wp_id,
                wp_meta.dependencies,
                _dependency_lanes,
            )
            if not _dependency_readiness.satisfied:
                blocked = ", ".join(_dependency_readiness.unsatisfied)
                print(
                    f"Error: dependencies_not_satisfied: {normalized_wp_id} depends on {blocked}; "
                    "all dependencies must be approved or done before implementation can start"
                )
                raise typer.Exit(1)

        # IC-04/T017: review-feedback-context READ. WORK_PACKAGE_TASK is a
        # PRIMARY-partition kind (review-cycle artifacts + this WP's baseline
        # artifact both live under tasks/<wp_slug>/, reused later in this
        # function at the fix-mode and baseline-commit sites) — routes through
        # the kind-aware seam instead of the kind-blind coord husk (NFR-001 /
        # Directive-041).
        feature_dir = _resolve_workflow_read_dir(
            repo_root=main_repo_root, mission_slug=mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        has_feedback, review_feedback_ref, review_feedback_file, review_feedback_source = _resolve_review_feedback_context(
            feature_dir=feature_dir,
            wp_id=normalized_wp_id,
            wp_frontmatter=getattr(wp, "frontmatter", "") or "",
        )

        if review_feedback_source == "canonical" and review_feedback_file is None:
            print(f"Error: {normalized_wp_id} review feedback artifact is missing or unreadable: {review_feedback_ref}")
            print("Re-run move-task with --review-feedback-file so the fix cycle can attach the canonical review artifact.")
            raise typer.Exit(1)

        # #1989 (read-side companion to WP01): read the report from the PRIMARY
        # checkout where record-analysis writes it (see _analysis_report_gate_dir).
        _require_current_analysis_report(
            _analysis_report_gate_dir(main_repo_root, mission_slug),
            main_repo_root,
            mission_slug,
        )

        # FR-008/#1832 (C-IC05): SINGLE resolution path. Resolve the workspace
        # exactly once here, then *consume* that resolved context for the rest
        # of the implement flow (creation + verification) via
        # ``_ensure_workspace_materialized`` — never re-resolve through a second
        # authority that could independently report "no workspace could be
        # resolved" on a verified read-path.
        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        status_execution_mode = "direct_repo" if workspace.resolution_kind == "repo_root" else "worktree"

        def _create_workspace() -> None:
            top_level_implement(
                wp_id=normalized_wp_id,
                mission=mission_slug,
                json_output=False,
                recover=False,
                acknowledge_not_bulk_edit=acknowledge_not_bulk_edit,
                actor=agent,
            )

        _ensure_workspace_materialized(workspace, normalized_wp_id, _create_workspace)
        workspace_path = workspace.worktree_path

        subtask_ids = [str(item) for item in wp_meta.subtasks if isinstance(item, str)]
        subtask_cmd = " ".join(subtask_ids) if subtask_ids else "<subtask-ids>"

        # Resolve structured agent assignment from WP metadata (centralizes legacy coercion)
        _wp_agent_assignment = wp_meta.resolved_agent()
        logger.debug("WP agent assignment: tool=%s model=%s", _wp_agent_assignment.tool, _wp_agent_assignment.model)

        # Move to in_progress lane if not already there, and ensure agent is recorded
        # Lane is event-log-only; read from canonical event log (no frontmatter fallback)
        _wf_feature_dir = _canonical_status_feature_dir(main_repo_root, mission_slug)
        from specify_cli.status import get_wp_lane as _wf_get_wp_lane
        from specify_cli.status import read_events as _wf_read_events
        from specify_cli.status import reduce as _wf_reduce

        _wf_events = _wf_read_events(_wf_feature_dir)
        _wf_snapshot = _wf_reduce(_wf_events) if _wf_events else None
        _wf_has_canonical = _wf_snapshot is not None and normalized_wp_id in _wf_snapshot.work_packages
        if not _wf_has_canonical:
            raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug, _wf_feature_dir))
        current_lane = _wf_get_wp_lane(_wf_feature_dir, normalized_wp_id)
        needs_agent_assignment = _wp_agent_assignment.tool == "unknown"
        wp_slug = wp.path.stem
        fix_mode_active = _has_prior_rejection(feature_dir, wp_slug, normalized_wp_id)

        if current_lane != Lane.IN_PROGRESS or needs_agent_assignment or agent:
            # Require --agent parameter to track who is working
            if not agent:
                if current_lane == Lane.IN_PROGRESS and not needs_agent_assignment:
                    # Already in_progress with an agent; allow prompt display
                    pass
                else:
                    print("Error: --agent parameter required when starting implementation.")
                    print(f"  Usage: spec-kitty agent action implement {normalized_wp_id} --agent <your-name>")
                    print("  Example: spec-kitty agent action implement WP01 --agent claude")
                    print()
                    print("If you're using a generated agent command file, --agent is already included.")
                    print("This tracks WHO is working on the WP (prevents abandoned tasks).")
                    raise typer.Exit(1)

            from datetime import datetime
            import os

            # FR-008/#1832 (C-IC05): single resolution path — ``status_execution_mode``
            # was already derived from the resolved ``workspace`` above; consume that
            # resolved context instead of re-resolving (the value is identical, and a
            # second resolution authority is exactly what this WP eliminates).
            status_execution_mode = "direct_repo" if workspace.resolution_kind == "repo_root" else "worktree"

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            _impl_feature_dir = _wf_feature_dir
            _actor = agent or "unknown"
            # WP06 T027: capture the pre-emit size of status.events.jsonl
            # so we can surgically truncate on commit failure. This is
            # the byte-for-byte rollback that closes #1348 for the
            # legacy path; the modern path (coord branch) gets the same
            # contract via BookkeepingTransaction.
            _events_path_pre = _impl_feature_dir / _STATUS_EVENTS_FILENAME
            _status_path_pre = _impl_feature_dir / _STATUS_FILENAME
            _pre_emit_event_size = (
                _events_path_pre.stat().st_size if _events_path_pre.exists() else 0
            )
            _pre_emit_status_bytes = (
                _status_path_pre.read_bytes() if _status_path_pre.exists() else None
            )

            # FR-017 / NFR-004: build and validate the runtime OperationalContext
            # via the shared claim builder BEFORE emitting the claim status event
            # or allocating any worktree. The builder is read-only; running its
            # guard here means a missing-context precondition failure aborts
            # before start_implementation_status, leaving zero new status events
            # and zero new worktree paths.
            from runtime.next.runtime_bridge import build_operational_context_for_claim

            operational_context = build_operational_context_for_claim(
                repo_root=main_repo_root,
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=normalized_wp_id,
                actor=_actor,
                active_model=agent or _wp_agent_assignment.model,
                active_role=_wp_agent_assignment.role or _actor,
                current_activity="implement",
                active_profile=_wp_agent_assignment.profile_id,
            )
            operational_context.require_active_role()

            try:
                start_implementation_status(
                    feature_dir=_impl_feature_dir,
                    mission_slug=mission_slug,
                    wp_id=normalized_wp_id,
                    actor=_actor,
                    workspace_context=f"{status_execution_mode}:{workspace_path}",
                    execution_mode=status_execution_mode,
                    repo_root=main_repo_root,
                    allow_rework=current_lane in {Lane.FOR_REVIEW, Lane.APPROVED, Lane.IN_REVIEW},
                )
            except WorkPackageClaimConflict as exc:
                print(f"Error: {exc}")
                raise typer.Exit(1) from exc
            except WorkPackageStartRejected as exc:
                print(f"Error: {exc}")
                raise typer.Exit(1) from exc

            # Update operational metadata in frontmatter (NO lane — event log is sole authority)
            updated_front = wp.frontmatter
            updated_front = set_scalar(updated_front, "agent", agent)
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build history entry (no lane= segment; event log is sole lane authority)
            timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if current_lane != Lane.IN_PROGRESS:
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Started implementation via action command"
            else:
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Assigned agent via action command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Auto-commit to target branch (enables instant status sync)
            actual_wp_path = wp.path.resolve()
            status_artifacts = [path.resolve() for path in _collect_status_artifacts(_impl_feature_dir)]
            # WP06 T027: route through BookkeepingTransaction when the
            # mission has a coordination branch, fall back to safe_commit
            # with surgical event-log truncate on failure otherwise.
            _commit_workflow_change(
                repo_root=main_repo_root,
                feature_dir=_impl_feature_dir,
                mission_slug=mission_slug,
                target_branch=target_branch,
                paths=[actual_wp_path, *status_artifacts],
                message=f"chore: Start {normalized_wp_id} implementation [{agent}]",
                operation=f"planned -> claimed for {normalized_wp_id}",
                wp_id=normalized_wp_id,
                pre_emit_event_size=_pre_emit_event_size,
                pre_emit_status_bytes=_pre_emit_status_bytes,
                auto_rebase_lane_after_commit=True,
            )

            print(f"✓ Claimed {normalized_wp_id} (agent: {agent}, PID: {shell_pid}, target: {target_branch})")

            # Dossier sync (fire-and-forget)
            try:
                from specify_cli.sync.dossier_pipeline import (
                    trigger_feature_dossier_sync_if_enabled,
                )

                # IC-04/T017: dossier-sync READ. The indexer walks the whole
                # mission tree (spec.md/plan.md/tasks.md/tasks/*.md) — the
                # same whole-planning-surface READ the dashboard scanner uses
                # TASKS_INDEX for (mirrors the "tasks" action this call used
                # to resolve via the kind-blind husk) — routed via the
                # kind-aware seam (NFR-001 / Directive-041).
                _impl_feature_dir = _resolve_workflow_read_dir(
                    repo_root=repo_root, mission_slug=mission_slug, kind=MissionArtifactKind.TASKS_INDEX
                )
                trigger_feature_dossier_sync_if_enabled(
                    _impl_feature_dir,
                    mission_slug,
                    repo_root,
                )
            except Exception as _dossier_sync_exc:  # noqa: BLE001 — best-effort fire-and-forget
                logger.debug(
                    "Dossier sync trigger failed for %s (non-fatal, fire-and-forget): %s",
                    mission_slug,
                    _dossier_sync_exc,
                )

            # Reload to get updated content
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Action implement will not move it to in_progress.")

        # Fix-mode detection: if the WP was rejected and has review-cycle artifacts,
        # generate a focused fix-mode prompt instead of the full WP prompt.
        # The fix-prompt completely replaces the full WP prompt (not appended to it).
        if fix_mode_active:
            try:
                from rich.console import Console as _RichConsole
                from specify_cli.review.artifacts import ReviewCycleArtifact as _ReviewCycleArtifact
                from specify_cli.review.fix_prompt import generate_fix_prompt as _generate_fix_prompt

                _sub_artifact_dir = feature_dir / "tasks" / wp_slug
                if review_feedback_ref and review_feedback_ref.startswith("review-cycle://") and review_feedback_file is not None:
                    _latest_artifact = _ReviewCycleArtifact.from_file(review_feedback_file)
                else:
                    _latest_artifact = _ReviewCycleArtifact.latest(_sub_artifact_dir)
                if _latest_artifact is not None:
                    _console = _RichConsole()
                    _console.print(
                        f"[bold]Fix mode[/bold]: generating focused prompt from "
                        f"review-cycle-{_latest_artifact.cycle_number} "
                        f"(Canonical feedback: {_sub_artifact_dir / f'review-cycle-{_latest_artifact.cycle_number}.md'})"
                    )
                    _fix_prompt_text = _generate_fix_prompt(
                        artifact=_latest_artifact,
                        worktree_path=workspace_path,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                    )
                    _fix_prompt_file = _write_prompt_to_file("implement", mission_slug, normalized_wp_id, _fix_prompt_text, repo_root=repo_root)
                    print()
                    print(f"📍 Workspace: cd {workspace_path}")
                    print(f"🔧 Fix mode — Cycle {_latest_artifact.cycle_number}: focused prompt from review artifact")
                    print()
                    print("▶▶▶ NEXT STEP: Read the full fix-mode prompt file now:")
                    print(f"    cat {_fix_prompt_file}")
                    print()
                    return
            except Exception as _fix_mode_err:
                logger.warning("Fix-mode prompt generation failed, falling through to full prompt: %s", _fix_mode_err)

        # Detect mission type and get deliverables_path for research missions.
        # FR-005 (#2186): the mission TYPE is a meta.json read and meta.json lives
        # ONLY on PRIMARY. ``feature_dir`` here is bound from the coord-aware
        # resolver (it is the STATUS leg for this loop), so read the type off its
        # OWN PRIMARY-anchored dir — do NOT re-point the shared ``feature_dir``
        # (it carries STATUS semantics the surrounding code depends on, C-001).
        _mission_type_dir = primary_feature_dir_for_mission(
            repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
        )
        mission_type = get_mission_type(_mission_type_dir)
        deliverables_path = None
        if mission_type == MISSION_TYPE_RESEARCH:
            deliverables_path = get_deliverables_path(_mission_type_dir, mission_slug)

        # Capture baseline test results (one-time, cached) before the agent starts coding
        # wp.path.stem is e.g. "WP04-baseline-test-capture"
        _wp_slug = wp.path.stem
        try:
            from specify_cli.review.baseline import capture_baseline as _capture_baseline

            _baseline = _capture_baseline(
                worktree_path=workspace_path,
                base_branch=target_branch,
                wp_id=normalized_wp_id,
                mission_slug=mission_slug,
                feature_dir=feature_dir,
                wp_slug=_wp_slug,
            )
            if _baseline is not None and _baseline.failed > 0:
                print(f"[dim]Baseline: {_baseline.failed} pre-existing test failure(s) captured[/dim]")
                # Commit the baseline artifact to the feature branch
                _baseline_artifact = feature_dir / "tasks" / _wp_slug / "baseline-tests.json"
                if _baseline_artifact.exists():
                    # Mechanical WP06 pre-step migration.
                    try:
                        # Baseline artifact (tasks/<wp>/baseline-tests.json) is a
                        # WORK_PACKAGE_TASK-kind artifact — a PRIMARY-partition
                        # kind (T017): it lands on the mission/lane
                        # ``target_branch`` for EVERY topology, resolved via the
                        # seam rather than constructed inline. STANDARD asserts
                        # no protected-branch flow, so a protected target is
                        # refused — the best-effort handler below logs the
                        # refusal (FR-008).
                        _baseline_placement = _resolve_workflow_placement(
                            repo_root=main_repo_root,
                            mission_slug=mission_slug,
                            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
                        )
                        safe_commit(
                            repo_root=main_repo_root,
                            worktree_root=main_repo_root,
                            target=_baseline_placement,
                            message=f"chore: Capture baseline tests for {normalized_wp_id}",
                            paths=(_baseline_artifact,),
                            capability=GuardCapability.STANDARD,
                        )
                    except Exception as _bl_commit_exc:  # noqa: BLE001 — best-effort
                        import logging as _bl_logging2
                        _bl_logging2.getLogger(__name__).warning(
                            "Baseline artifact commit failed: %s", _bl_commit_exc
                        )
            elif _baseline is not None and _baseline.failed == -1:
                print("[yellow]Warning: baseline test capture failed — no baseline context available[/yellow]")
        except Exception as _bl_err:
            import logging as _bl_logging

            _bl_logging.getLogger(__name__).warning("Baseline capture error: %s", _bl_err)

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"IMPLEMENT: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append(_workspace_contract_description(workspace, normalized_wp_id))
        lines.append("")
        # WP03 (#833): surface the resolved agent 4-tuple so model / profile_id /
        # role flow into the rendered prompt instead of being silently discarded.
        lines.extend(_render_resolved_agent_identity(_wp_agent_assignment))
        lines.append("")
        lines.append(_render_charter_context(repo_root, "implement"))
        lines.append("")

        # CRITICAL: WP isolation rules
        lines.extend(_render_isolation_banner(normalized_wp_id, "implement"))
        lines.append("")

        # Inject worktree topology context for stacked branches
        try:
            from specify_cli.core.worktree_topology import (
                materialize_worktree_topology,
                render_topology_json,
            )

            topology = materialize_worktree_topology(repo_root, mission_slug)
            if topology.has_stacking:
                lines.extend(render_topology_json(topology, current_wp_id=normalized_wp_id))
                lines.append("")
        except Exception as exc:
            lines.append(f"[Topology unavailable: {exc}]")
            lines.append("")

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append("✓ Implementation complete and tested:")
        lines.append("  1. **Commit your implementation files:**")
        lines.append("     git status  # Check what you changed")
        lines.append("     git add <your-implementation-files>  # NOT WP status files")
        lines.append(f'     git commit -m "feat({normalized_wp_id}): <brief description>"')
        lines.append("     git log -1 --oneline  # Verify commit succeeded")
        lines.append("  2. Mark all subtasks as done:")
        lines.append(f"     spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        lines.append("  3. Move WP to review:")
        lines.append(f'     spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review"')
        lines.append("")
        lines.append("✗ Blocked or cannot complete:")
        lines.append(f'  spec-kitty agent tasks add-history {normalized_wp_id} --mission {mission_slug} --note "Blocked: <reason>"')
        lines.append("=" * 80)
        lines.append("")
        lines.append("📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        if workspace.lane_id:
            lines.append("   # All implementation work happens in this workspace")
            lines.append(f"   # When done, return to repo root: cd {repo_root}")
        else:
            lines.append("   # Planning-artifact work for this WP happens in the repository root")
        lines.append("")
        lines.extend(_shared_artifact_guidance(workspace, repo_root, mission_slug))
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ status is tracked in {target_branch} branch (visible to all agents)")
        lines.append("   Status changes auto-commit to the coordination branch (visible to all agents)")
        lines.append("   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")

        if has_feedback:
            lines.append("⚠️  This work package has review feedback.")
            if review_feedback_ref:
                lines.append(f"   Canonical feedback reference: {review_feedback_ref}")
                if review_feedback_ref.startswith("feedback://"):
                    lines.append("   WARNING: legacy feedback:// reference detected; readable but deprecated.")
                if review_feedback_file is not None:
                    lines.append(f'   Read it first: cat "{review_feedback_file}"')
                else:
                    lines.append("   WARNING: review feedback reference is set, but the artifact is missing/unreadable.")
                    lines.append("   Ask reviewer to re-run move-task with --review-feedback-file.")
            else:
                lines.append("   WARNING: review_status=has_feedback but no review_feedback reference is set.")
                lines.append("   Ask reviewer to re-run move-task with --review-feedback-file.")
            lines.append("")

        # Research mission: Show deliverables path prominently
        if mission_type == MISSION_TYPE_RESEARCH and deliverables_path:
            lines.append("╔" + "=" * 78 + "╗")
            lines.append("║  🔬 RESEARCH MISSION - TWO ARTIFACT TYPES                                 ║")
            lines.append("╠" + "=" * 78 + "╣")
            lines.append("║                                                                          ║")
            lines.append("║  📁 RESEARCH DELIVERABLES (your output):                                 ║")
            deliv_line = f"║     {deliverables_path:<69} ║"
            lines.append(deliv_line)
            lines.append("║     ↳ Create findings, reports, data here                                ║")
            lines.append("║     ↳ Commit to worktree branch                                          ║")
            lines.append(f"║     ↳ Will merge to {target_branch:<62} ║")
            lines.append("║                                                                          ║")
            lines.append("║  📋 PLANNING ARTIFACTS (kitty-specs/):                                   ║")
            lines.append("║     ↳ evidence-log.csv, source-register.csv                              ║")
            lines.append("║     ↳ Edit in planning repo (rare during implementation)                 ║")
            lines.append("║                                                                          ║")
            lines.append("║  ⚠️  DO NOT put research deliverables in kitty-specs/!                   ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")

        # WP content marker and content
        lines.extend(_render_wp_prompt_wrapper(wp.path.read_text(encoding="utf-8")))

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 IMPLEMENTATION COMPLETE? RUN THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append("✅ Implementation complete and tested:")
        lines.append("   1. **Commit your implementation files:**")
        lines.append("      git status  # Check what you changed")
        lines.append("      git add <your-implementation-files>  # NOT WP status files")
        lines.append(f'      git commit -m "feat({normalized_wp_id}): <brief description>"')
        lines.append("      git log -1 --oneline  # Verify commit succeeded")
        lines.append("      (Use fix: for bugs, chore: for maintenance, docs: for documentation)")
        lines.append("   2. Mark all subtasks as done:")
        lines.append(f"      spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        lines.append("   3. Move WP to review (will check for uncommitted changes):")
        lines.append(f'      spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review: <summary>"')
        lines.append("")
        lines.append("⚠️  Blocked or cannot complete:")
        lines.append(f'   spec-kitty agent tasks add-history {normalized_wp_id} --mission {mission_slug} --note "Blocked: <reason>"')
        lines.append("")
        lines.append("⚠️  NOTE: The move-task command will FAIL if you have uncommitted changes!")
        lines.append("     Commit all implementation files BEFORE moving to for_review.")
        lines.append("     Dependent work packages need your committed changes.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        prompt_file = _write_prompt_to_file("implement", mission_slug, normalized_wp_id, full_content, repo_root=repo_root)

        # Output concise summary with directive to read the prompt
        print()
        print(f"📍 Workspace: cd {workspace_path}")
        if workspace.lane_id:
            shared = ", ".join(workspace.lane_wp_ids or [normalized_wp_id])
            print(f"   Lane workspace: {workspace.lane_id} (shared by {shared})")
        else:
            print("   Repository-root planning workspace")
        if has_feedback:
            if review_feedback_ref:
                print(f"⚠️  Has review feedback - read reference: {review_feedback_ref}")
                if review_feedback_ref.startswith("feedback://"):
                    print("   Warning: legacy feedback:// reference detected; readable but deprecated.")
            else:
                print("⚠️  Has review feedback - but no review_feedback reference is set")
        if mission_type == MISSION_TYPE_RESEARCH and deliverables_path:
            print(f"🔬 Research deliverables: {deliverables_path}")
            print("   (NOT in kitty-specs/ - those are planning artifacts)")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After implementation, run:")
        print(f'  1. git status && git add <your-files> && git commit -m "feat({normalized_wp_id}): <description>"')
        print(f"  2. spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        print(f'  3. spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review"')
        print("     (Pre-flight check will verify no uncommitted changes)")

    except typer.Exit:
        with contextlib.suppress(Exception):
            _print_commit_summary(command_name="implement")
        raise
    except Exception as e:
        # WP06 T029: surface any partial commit summary before exiting,
        # so operators see what got recorded vs. refused.
        with contextlib.suppress(Exception):
            _print_commit_summary(command_name="implement")
        print(f"Error: {e}")
        raise typer.Exit(1)

    # WP06 T029: terminal commit summary for the implement command.
    _print_commit_summary(command_name="implement")


def _resolve_review_context(
    workspace_path: Path,
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_frontmatter: str,
) -> dict:
    """Resolve git branch and base context for review prompts.

    Determines the WP's branch name, its base branch (what it was branched
    from), and the number of commits unique to this WP so reviewers know
    exactly what to diff against instead of guessing.

    Strategy:
    1. Get actual branch name from the worktree.
    2. Read canonical mission/lane branch state from workspace context and
       lanes.json.
    3. Use that state directly for review diffs; do not reconstruct branch
       names from slug strings.
    """
    ctx: dict = {
        "branch_name": "unknown",
        "base_branch": "unknown",
        "mission_branch": "unknown",
        "lane_branch": "unknown",
        "base_ref": "unknown",
        "commit_count": 0,
    }

    if not workspace_path.exists():
        return ctx

    workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    # WP04 / T017 / FR-002: lanes.json (LANE_STATE — PRIMARY-partition) and
    # tasks/ (WORK_PACKAGE_TASK — PRIMARY-partition) both route to the primary
    # checkout.  Under coord topology, candidate_feature_dir_for_mission returned
    # the STATUS-only coord husk (no lanes.json, no tasks/) — a wrong-leg read.
    feature_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    # lanes.json is LANE_STATE (PRIMARY-partition) — use its truthful kind so a
    # future LANE_STATE re-partition does not silently misroute.
    _lanes_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )
    lanes_manifest = None
    try:
        from specify_cli.lanes.persistence import read_lanes_json

        lanes_manifest = read_lanes_json(_lanes_dir)
    except Exception:
        lanes_manifest = None

    mission_branch = "unknown"
    if lanes_manifest is not None and lanes_manifest.mission_branch:
        mission_branch = lanes_manifest.mission_branch
    elif workspace.context is not None and workspace.context.base_branch:
        mission_branch = workspace.context.base_branch
    ctx["mission_branch"] = mission_branch

    if workspace.resolution_kind == "repo_root":
        wp_paths = sorted((feature_dir / "tasks").glob(f"{wp_id}*.md"))
        claim = subprocess.run(
            [
                "git",
                "log",
                "--format=%H%x00%s",
                "--",
                *(str(path) for path in wp_paths),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        claim_commit: str | None = None
        for raw in claim.stdout.splitlines():
            commit_hash, _, subject = raw.partition("\x00")
            if not commit_hash:
                continue
            if f"Move {wp_id} to in_progress" in subject or f"{wp_id} claimed for implementation" in subject or f"Start {wp_id} implementation" in subject:
                claim_commit = commit_hash.strip()
                break
        if claim_commit is None:
            return ctx
        count = subprocess.run(
            ["git", "rev-list", "--count", f"{claim_commit}..HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        commit_count = int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip().isdigit() else 1
        ctx["branch_name"] = "HEAD"
        ctx["base_branch"] = claim_commit
        ctx["lane_branch"] = "HEAD"
        ctx["base_ref"] = claim_commit
        ctx["commit_count"] = commit_count
        return ctx

    # Get actual branch name from worktree
    from specify_cli.core.git_ops import get_current_branch

    branch = get_current_branch(workspace_path)
    if branch:
        ctx["branch_name"] = branch
        ctx["lane_branch"] = branch
    else:
        return ctx
    branch = ctx["branch_name"]

    base_ref = "unknown"
    if workspace.context is not None and workspace.context.base_branch:
        base_ref = workspace.context.base_branch
    elif mission_branch != "unknown":
        base_ref = mission_branch

    if base_ref == "unknown":
        candidates: list[str] = []
        dep_match = re.search(r"dependencies:\s*\[([^\]]*)\]", wp_frontmatter)
        if dep_match:
            dep_content = dep_match.group(1).strip()
            if dep_content:
                dep_ids = re.findall(r'"?(WP\d+)"?', dep_content)
                for dep_id in dep_ids:
                    try:
                        dep_workspace = resolve_workspace_for_wp(repo_root, mission_slug, dep_id)
                    except (ValueError, FileNotFoundError):
                        continue
                    dep_branch = dep_workspace.branch_name
                    if dep_branch and dep_branch != branch:
                        candidates.append(dep_branch)

        candidates.extend(["main", "2.x", "master", "develop"])
        best_base = None
        best_count = -1
        for candidate in candidates:
            mb = subprocess.run(
                ["git", "merge-base", branch, candidate],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if mb.returncode != 0:
                continue
            count_r = subprocess.run(
                ["git", "rev-list", "--count", f"{mb.stdout.strip()}..{branch}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if count_r.returncode != 0:
                continue
            count = int(count_r.stdout.strip()) if count_r.stdout.strip().isdigit() else 0
            if best_count == -1 or count < best_count:
                best_count = count
                best_base = candidate

        if best_base is not None:
            ctx["base_branch"] = best_base
            ctx["base_ref"] = best_base
            ctx["commit_count"] = best_count
        return ctx

    count_r = subprocess.run(
        ["git", "rev-list", "--count", f"{base_ref}..{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    commit_count = int(count_r.stdout.strip()) if count_r.returncode == 0 and count_r.stdout.strip().isdigit() else 0
    ctx["base_branch"] = base_ref
    ctx["base_ref"] = base_ref
    ctx["commit_count"] = commit_count

    return ctx


def _find_first_for_review_wp(repo_root: Path, mission_slug: str) -> str | None:
    """Find the first WP file with lane: "for_review".

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug

    Returns:
        WP ID of first for_review task, or None if not found
    """
    # WP04 / T017 / FR-002: tasks/ reads route through the planning seam
    # (WORK_PACKAGE_TASK → PRIMARY) so coord-topology missions find tasks/ on
    # the primary checkout, not the STATUS-only coord husk.
    # resolve_planning_read_dir is cwd-invariant for PRIMARY-partition kinds:
    # primary_feature_dir_for_mission anchors on get_main_repo_root(repo_root),
    # so cwd / walk-up / repo_root all resolve the same primary dir — the
    # multi-branch walk was vestigial after WP04.
    # The STATUS leg uses candidate_feature_dir_for_mission(repo_root, ...) so
    # events come from the authoritative coord husk under coord topology (C-001).
    tasks_dir = (
        resolve_planning_read_dir(
            repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        / "tasks"
    )

    if not tasks_dir.exists():
        return None

    # Find all WP files
    wp_files = sorted(tasks_dir.glob("WP*.md"))

    # Load lanes from canonical event log (lane is event-log-only).
    # WP04: status events stay on the coord-aware resolver so coord-topology
    # missions read the authoritative event log, not the primary decoy (C-001).
    _status_feature_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
    _fr_events = []
    try:
        from specify_cli.status import read_events as _fr_read_events
        from specify_cli.status import reduce as _fr_reduce

        _fr_events = _fr_read_events(_status_feature_dir)
        _fr_snapshot = _fr_reduce(_fr_events) if _fr_events else None
        _fr_lanes: dict = {}
        if _fr_snapshot:
            for _fr_wp_id, _fr_state in _fr_snapshot.work_packages.items():
                _fr_lanes[_fr_wp_id] = Lane(_fr_state.get("lane", Lane.PLANNED))
    except Exception:
        _fr_lanes = {}

    def _is_review_claimed(_wp_id: str) -> bool:
        for _event in reversed(_fr_events):
            if getattr(_event, "wp_id", None) == _wp_id:
                return bool(
                    _event.to_lane == Lane.IN_REVIEW  # new canonical shape
                    or (
                        _event.to_lane == Lane.IN_PROGRESS  # legacy shape
                        and _event.review_ref == "action-review-claim"
                    )
                )
        return False

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_id = extract_scalar(frontmatter, "work_package_id")
        if wp_id and _fr_lanes.get(wp_id, Lane.PLANNED) == Lane.FOR_REVIEW:
            return wp_id

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_id = extract_scalar(frontmatter, "work_package_id")
        if wp_id and _fr_lanes.get(wp_id, Lane.PLANNED) in {Lane.IN_PROGRESS, Lane.IN_REVIEW} and _is_review_claimed(wp_id):
            return wp_id

    return None


def _prepare_review_workspace(
    workspace: ResolvedWorkspace,
    main_repo_root: Path,
    wp_id: str,
    agent: str | None,
) -> ResolvedWorkspace:
    """Validate/create the review workspace, then acquire review isolation.

    Order is load-bearing (#1833 AC-D2): ``ReviewLock`` persists its lock file
    INSIDE the workspace (``.spec-kitty/review-lock.json``), so acquiring it
    before the worktree exists used to mint a husk directory. The workspace
    existence/creation block must succeed first; only then is the lock
    acquired, and a failed ``git worktree add`` is a hard error (not a
    warning), leaving no lock behind.
    """
    workspace_path = workspace.worktree_path

    # A husk (directory without a .git entry) is absent-but-blocked: never
    # silently recreate a worktree on top of it — that hides the anomaly.
    if workspace.is_husk:
        print(f"Error: {husk_resolution_error(workspace_path)}")
        raise typer.Exit(1)

    if not workspace.exists:
        # Ensure .worktrees directory exists
        worktrees_dir = main_repo_root / ".worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)

        branch_name = workspace.branch_name
        if branch_name is None:
            print(f"Error: cannot create review workspace {workspace_path} for {wp_id}: resolved workspace has no branch name.")
            raise typer.Exit(1)
        branch_exists = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=main_repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if branch_exists.returncode == 0:
            worktree_cmd = ["git", "worktree", "add", str(workspace_path), branch_name]
        else:
            worktree_cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name]
        result = subprocess.run(worktree_cmd, cwd=main_repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

        if result.returncode != 0:
            print(
                f"Error: could not create review workspace {workspace_path} for {wp_id}: "
                f"`{' '.join(worktree_cmd)}` failed: {result.stderr.strip()}"
            )
            raise typer.Exit(1)

        print(f"✓ Created workspace: {workspace_path}")
        if not workspace.exists:
            print(f"Error: workspace creation reported success but {workspace_path} is not a git worktree.")
            raise typer.Exit(1)

    # Concurrent review isolation: acquire review lock or apply env-var
    # isolation — only after the workspace is proven to exist.
    from specify_cli.review.lock import ReviewLock, ReviewLockError, _get_isolation_config, _apply_env_var_isolation

    isolation_config = _get_isolation_config(main_repo_root)
    if isolation_config and isolation_config.get("strategy") == "env_var":
        _apply_env_var_isolation(isolation_config, agent or "unknown", wp_id)
    else:
        try:
            ReviewLock.acquire(Path(workspace.worktree_path), wp_id, agent or "unknown")
        except ReviewLockError as e:
            print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e

    return workspace


@app.command(name="review")
def review(
    wp_id: Annotated[str | None, typer.Argument(help="Work package ID (e.g., WP01) - auto-detects first for_review if omitted")] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name (required for auto-move to in_progress)")] = None,
) -> None:
    """Display work package prompt with review instructions.

    This command outputs the full work package prompt (including any review
    feedback from previous reviews) so agents can review the implementation.

    Automatically moves WP from for_review to in_review (requires --agent to track who is reviewing).

    Examples:
        spec-kitty agent action review WP01 --agent claude
        spec-kitty agent action review wp02 --agent codex
        spec-kitty agent action review --agent gemini  # auto-detects first for_review WP
    """
    # WP06 T029: reset the commit-receipt accumulator for this invocation.
    _reset_workflow_receipts()
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, repo_root=repo_root)

        # Ensure planning repo is on the target branch before we start
        # (needed for auto-commits and status tracking inside this command)
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug)

        # Determine which WP to review
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first for_review WP
            normalized_wp_id = _find_first_for_review_wp(repo_root, mission_slug)
            if not normalized_wp_id:
                print("Error: No work packages ready for review. Specify a WP ID explicitly.")
                raise typer.Exit(1)

        # Load work package
        try:
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        except RuntimeError as e:
            if _is_missing_canonical_status_error(e):
                raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug)) from e
            raise

        # Move to in_progress lane if not already there.
        # Explicit WP review requests must target for_review (or already review-claimed in_progress).
        # Lane is event-log-only; read from canonical event log (no frontmatter fallback)
        feature_dir = _canonical_status_feature_dir(main_repo_root, mission_slug)
        from specify_cli.status import get_wp_lane as _rv_get_wp_lane
        from specify_cli.status import read_events as _rv_read_events
        from specify_cli.status import reduce as _rv_reduce

        _rv_events = _rv_read_events(feature_dir)
        _rv_snapshot = _rv_reduce(_rv_events) if _rv_events else None
        _rv_has_canonical = _rv_snapshot is not None and normalized_wp_id in _rv_snapshot.work_packages
        if not _rv_has_canonical:
            raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug, feature_dir))
        current_lane = _rv_get_wp_lane(feature_dir, normalized_wp_id)
        review_workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        status_execution_mode = "direct_repo" if review_workspace.resolution_kind == "repo_root" else "worktree"
        latest_event = None
        for _event in reversed(_rv_events):
            if getattr(_event, "wp_id", None) == normalized_wp_id:
                latest_event = _event
                break
        is_review_claimed = bool(
            latest_event is not None
            and (
                latest_event.to_lane == Lane.IN_REVIEW  # new canonical shape
                or (
                    latest_event.to_lane == Lane.IN_PROGRESS  # legacy shape
                    and latest_event.review_ref == "action-review-claim"
                )
            )
        )
        if current_lane == Lane.IN_PROGRESS and not is_review_claimed:
            print(f"Error: {normalized_wp_id} is still being implemented, not claimed for review.")
            print("Only work packages in 'for_review' (or already review-claimed in_review) can start workflow review.")
            print(f"Move it first: spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug}")
            raise typer.Exit(1)
        if current_lane not in {Lane.FOR_REVIEW, Lane.IN_REVIEW} and not is_review_claimed:
            print(f"Error: {normalized_wp_id} is in lane '{current_lane}', not 'for_review'.")
            print("Only work packages in 'for_review' (or already claimed for review) can start workflow review.")
            print(f"Move it first: spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug}")
            raise typer.Exit(1)

        # Bulk edit occurrence classification gate — artifact admissibility (FR-006)
        from specify_cli.bulk_edit.gate import (
            check_review_diff_compliance,
            ensure_occurrence_classification_ready,
            render_diff_check_failure,
            render_gate_failure,
        )
        from rich.console import Console as _RichConsole
        _rich_console = _RichConsole()
        _gate_result = ensure_occurrence_classification_ready(feature_dir)
        if not _gate_result.passed:
            render_gate_failure(_gate_result, _rich_console)
            raise typer.Exit(1)

        # Bulk edit diff compliance — per-file category enforcement (FR-007, FR-008).
        # When this is a bulk_edit mission, inspect the WP's diff against its lane
        # base branch and reject modifications to forbidden or unclassified surfaces.
        if _gate_result.change_mode == "bulk_edit":
            _enforce_bulk_edit_diff_compliance(
                feature_dir=feature_dir,
                main_repo_root=main_repo_root,
                target_branch=target_branch,
                review_workspace=review_workspace,
                check_review_diff_compliance=check_review_diff_compliance,
                render_diff_check_failure=render_diff_check_failure,
                rich_console=_rich_console,
            )

        if current_lane == Lane.FOR_REVIEW or (current_lane == Lane.IN_REVIEW and agent):
            # Require --agent parameter to track who is reviewing
            if not agent:
                print("Error: --agent parameter required when starting review.")
                print(f"  Usage: spec-kitty agent action review {normalized_wp_id} --agent <your-name>")
                print("  Example: spec-kitty agent action review WP01 --agent claude")
                print()
                print("If you're using a generated agent command file, --agent is already included.")
                print("This tracks WHO is reviewing the WP (prevents abandoned reviews).")
                raise typer.Exit(1)

            from datetime import datetime
            import os

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            with feature_status_lock(main_repo_root, mission_slug):
                # WP06 T027: capture pre-emit event-log size for
                # surgical rollback on commit failure.
                _events_path_pre_rev = feature_dir / _STATUS_EVENTS_FILENAME
                _status_path_pre_rev = feature_dir / _STATUS_FILENAME
                _pre_emit_event_size_rev = (
                    _events_path_pre_rev.stat().st_size
                    if _events_path_pre_rev.exists()
                    else 0
                )
                _pre_emit_status_bytes_rev = (
                    _status_path_pre_rev.read_bytes()
                    if _status_path_pre_rev.exists()
                    else None
                )
                try:
                    start_review_status(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                        actor=agent,
                        review_ref="action-review-claim",
                        workspace_context=f"action-review:{main_repo_root}",
                        execution_mode=status_execution_mode,
                        repo_root=main_repo_root,
                    )
                except WorkPackageClaimConflict as exc:
                    print(f"Error: {exc}")
                    raise typer.Exit(1) from exc
                except WorkPackageStartRejected as exc:
                    print(f"Error: {exc}")
                    raise typer.Exit(1) from exc

                # Post-emit: apply operational metadata fields to WP file (lane is event-log-only)
                wp_content = wp.path.read_text(encoding="utf-8-sig")
                updated_front, updated_body, updated_padding = split_frontmatter(wp_content)
                updated_front = set_scalar(updated_front, "agent", agent)
                updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

                # Build history entry (no lane= segment; event log is sole lane authority)
                timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Started review via action command"

                # Add history entry to body
                updated_body = append_activity_log(updated_body, history_entry)

                # Build and write updated document
                updated_doc = build_document(updated_front, updated_body, updated_padding)
                write_text_within_directory(wp.path, updated_doc, root=main_repo_root, encoding="utf-8")

                # Atomic commit: WP file + all status artifacts (#211, #212)
                actual_wp_path = wp.path.resolve()
                status_artifacts = _collect_status_artifacts(feature_dir)
                # WP06 T027: route through BookkeepingTransaction (modern
                # path) or surgical-truncate fallback (legacy path).
                _commit_workflow_change(
                    repo_root=main_repo_root,
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    target_branch=target_branch,
                    paths=[actual_wp_path, *status_artifacts],
                    message=f"chore: Start {normalized_wp_id} review [{agent}]",
                    operation=f"for_review -> in_review for {normalized_wp_id}",
                    wp_id=normalized_wp_id,
                    pre_emit_event_size=_pre_emit_event_size_rev,
                    pre_emit_status_bytes=_pre_emit_status_bytes_rev,
                    auto_rebase_lane_after_commit=True,
                )

            print(f"✓ Claimed {normalized_wp_id} for review (agent: {agent}, PID: {shell_pid}, target: {target_branch})")

            # Reload to get updated content
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Workflow review will not move it to in_review.")

        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        workspace = _prepare_review_workspace(workspace, main_repo_root, normalized_wp_id, agent)
        workspace_path = workspace.worktree_path

        # Resolve git context (branch name, base branch, commit count)
        review_ctx = _resolve_review_context(workspace_path, main_repo_root, mission_slug, normalized_wp_id, wp.frontmatter)

        # Capture dependency warning for both file and summary
        dependents_warning = []
        # WP04 / T018 / FR-002: build_dependency_graph reads tasks/ (PRIMARY-partition)
        # → route through the planning seam.  Status-event reads stay on the coord-aware
        # resolver (C-001) so dependents' lane comes from the authoritative event log.
        _review_planning_dir = resolve_planning_read_dir(
            repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        graph = build_dependency_graph(_review_planning_dir)
        dependents = get_dependents(normalized_wp_id, graph)
        if dependents:
            # Load lanes from event log (lane is event-log-only).
            # Status reads stay coord-aware (C-001).
            _review_status_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
            try:
                from specify_cli.status import read_events as _rw_read_events
                from specify_cli.status import reduce as _rw_reduce

                _rw_events = _rw_read_events(_review_status_dir)
                _rw_snapshot = _rw_reduce(_rw_events) if _rw_events else None
                _rw_lanes: dict = {}
                if _rw_snapshot:
                    for _rw_wp_id, _rw_state in _rw_snapshot.work_packages.items():
                        _rw_lanes[_rw_wp_id] = Lane(_rw_state.get("lane", Lane.PLANNED))
            except Exception:
                _rw_lanes = {}

            incomplete: list[str] = []
            for dependent_id in dependents:
                lane = _rw_lanes.get(dependent_id, Lane.PLANNED)
                if lane in {Lane.PLANNED, Lane.IN_PROGRESS, Lane.FOR_REVIEW}:
                    incomplete.append(dependent_id)
            if incomplete:
                dependents_list = ", ".join(sorted(incomplete))
                dependents_warning.append(f"⚠️  Dependency Alert: {dependents_list} depend on {normalized_wp_id} (not yet done)")
                dependents_warning.append("   If you request changes, notify those agents to rebase.")

        # WP03 (#833): resolve the agent identity 4-tuple so the review prompt
        # surfaces model / profile_id / role rather than silently dropping them.
        try:
            _review_wp_meta, _ = read_wp_frontmatter(wp.path)
            _review_agent_assignment = _review_wp_meta.resolved_agent()
        except Exception as _agent_err:
            logger.warning("Could not resolve agent identity for review prompt: %s", _agent_err)
            _review_agent_assignment = None

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"REVIEW: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append(_workspace_contract_description(workspace, normalized_wp_id))
        lines.append("")
        if _review_agent_assignment is not None:
            lines.extend(_render_resolved_agent_identity(_review_agent_assignment))
            lines.append("")
        lines.append(_render_charter_context(repo_root, "review"))
        lines.append("")

        # Add dependency warning to file
        if dependents_warning:
            lines.extend(dependents_warning)
            lines.append("")

        # CRITICAL: WP isolation rules
        lines.extend(_render_isolation_banner(normalized_wp_id, "review"))
        lines.append("")

        # Inject worktree topology context for stacked branches
        try:
            from specify_cli.core.worktree_topology import (
                materialize_worktree_topology,
                render_topology_json,
            )

            topology = materialize_worktree_topology(repo_root, mission_slug)
            if topology.has_stacking:
                lines.extend(render_topology_json(topology, current_wp_id=normalized_wp_id))
                lines.append("")
        except Exception as exc:
            lines.append(f"[Topology unavailable: {exc}]")
            lines.append("")

        # Git review context — tells reviewer exactly what to diff against
        if review_ctx["base_branch"] != "unknown":
            base = review_ctx["base_branch"]
            branch_ref = review_ctx["branch_name"]
            review_paths = ""
            if workspace.resolution_kind == "repo_root":
                wp_meta, _ = read_wp_frontmatter(wp.path)
                if wp_meta.owned_files:
                    review_pathspecs = list(wp_meta.owned_files)
                    mission_root = f"kitty-specs/{mission_slug}/"
                    if any(path.startswith(mission_root) for path in review_pathspecs):
                        review_pathspecs.extend(
                            [
                                f":(exclude){mission_root}tasks/**",
                                f":(exclude){mission_root}tasks.md",
                                f":(exclude){mission_root}{_STATUS_EVENTS_FILENAME}",
                                f":(exclude){mission_root}{_STATUS_FILENAME}",
                            ]
                        )
                    review_paths = " -- " + " ".join(review_pathspecs)
            lines.append("─── GIT REVIEW CONTEXT " + "─" * 57)
            lines.append(f"Branch:      {branch_ref}")
            lines.append(f"Base branch: {base} ({review_ctx['commit_count']} commits ahead)")
            lines.append("")
            lines.append("Review commands (run in the workspace):")
            lines.append(f"  cd {workspace_path}")
            lines.append(f"  git log {base}..{branch_ref} --oneline{review_paths}           # WP commits only")
            lines.append(f"  git diff {base}..{branch_ref} --stat{review_paths}             # Changed files")
            lines.append(f"  git diff {base}..{branch_ref}{review_paths}                    # Full diff")
            lines.append("─" * 80)
            lines.append("")
        elif workspace.resolution_kind == "repo_root":
            lines.append("─── GIT REVIEW CONTEXT " + "─" * 57)
            lines.append("Review commands unavailable: no deterministic implementation claim commit found for this WP.")
            lines.append("Re-run review after the WP has a committed implementation claim on this mission.")
            lines.append("─" * 80)
            lines.append("")

        # Baseline Test Context — load cached baseline and surface pre-existing failures
        _rv_wp_slug = wp.path.stem
        # IC-04/T017: baseline-test READ, kept DISTINCT from the write below
        # (they diverge intentionally — campsite note #5 — never dedupe them
        # into one shared call/variable). WORK_PACKAGE_TASK (tasks/<wp_slug>/)
        # is a PRIMARY-partition kind — routed via the kind-aware seam instead
        # of the kind-blind coord husk (NFR-001 / Directive-041).
        _rv_feature_dir = _resolve_workflow_read_dir(
            repo_root=main_repo_root, mission_slug=mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        try:
            from specify_cli.review.baseline import BaselineTestResult as _BaselineTestResult

            _rv_baseline_path = _rv_feature_dir / "tasks" / _rv_wp_slug / "baseline-tests.json"
            _rv_baseline = _BaselineTestResult.load(_rv_baseline_path)
            if _rv_baseline is not None and _rv_baseline.failed > 0:
                lines.append("─── BASELINE TEST CONTEXT " + "─" * 54)
                lines.append(
                    f"**{_rv_baseline.failed} test failure(s) existed BEFORE this WP** (base: {_rv_baseline.base_branch} @ {_rv_baseline.base_commit[:7]}):"
                )
                lines.append("")
                lines.append("| Test | Error | File |")
                lines.append("|------|-------|------|")
                for _rv_f in _rv_baseline.failures:
                    lines.append(f"| {_rv_f.test} | {_rv_f.error[:80]} | {_rv_f.file} |")
                lines.append("")
                lines.append("**These failures are NOT regressions introduced by this WP.** Only flag test failures that are NOT in this list.")
                lines.append("─" * 80)
                lines.append("")
            elif _rv_baseline is not None and _rv_baseline.failed == -1:
                lines.append("─── BASELINE TEST CONTEXT " + "─" * 54)
                lines.append(
                    "**Warning**: Baseline test capture failed at implement time. "
                    "Cannot distinguish pre-existing failures from regressions. "
                    "Exercise caution when attributing test failures to this WP."
                )
                lines.append("─" * 80)
                lines.append("")
        except Exception as _rv_bl_err:
            import logging as _rv_bl_log

            _rv_bl_log.getLogger(__name__).warning("Baseline load error in review: %s", _rv_bl_err)

        # Determine the writable in-repo feedback path.
        # Derive wp_slug from the WP file stem (e.g. "WP03-external-reviewer-handoff").
        wp_slug = wp.path.stem  # e.g. "WP03-external-reviewer-handoff"
        # IC-04/T018: review-cycle sub-artifact WRITE (mkdir), kept DISTINCT
        # from the baseline READ above (campsite note #5 — the two calls look
        # redundant but diverge by design; never dedupe them into one shared
        # call/variable). WORK_PACKAGE_TASK is a PRIMARY-partition kind: the
        # placement seam's write and read projections resolve to the SAME
        # on-disk directory for a PRIMARY kind (INV-5 full read/write
        # symmetry — mission_runtime/artifacts.py). This is a genuine
        # filesystem write (``mkdir`` below), not a git commit — no
        # ``safe_commit``/target ref is consulted at this site (the eventual
        # commit of the reviewer-authored file happens later, out-of-band,
        # via ``move-task --review-feedback-file``). ``PlacementSeam`` has no
        # Path-returning write projection — only ``write_target(kind)``
        # (a git-ref-only ``CommitTarget``, never a filesystem ``Path``) and
        # ``read_dir(kind)`` (a ``Path``) — so the on-disk directory this
        # write needs is resolved via the read-side projection, which is
        # correct precisely because of the INV-5 symmetry above, not a
        # read-routed-for-a-write mistake.
        sub_artifact_dir = (
            _resolve_workflow_read_dir(
                repo_root=main_repo_root, mission_slug=mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
            )
            / "tasks"
            / wp_slug
        )
        sub_artifact_dir.mkdir(parents=True, exist_ok=True)

        # Determine the next review cycle number based on existing files.
        existing_cycles = sorted(sub_artifact_dir.glob("review-cycle-*.md"))
        next_cycle = len(existing_cycles) + 1
        review_feedback_path = sub_artifact_dir / f"review-cycle-{next_cycle}.md"

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append("✓ Review passed, no issues:")
        lines.append(f'  spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed"')
        lines.append("")
        lines.append("⚠️  Changes requested:")
        lines.append("  1. Write feedback to (in-repo, committed with the project):")
        lines.append(f"     {review_feedback_path}")
        lines.append(
            f"  2. spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}"
        )
        lines.append("  3. move-task stores feedback reference in the event log and WP frontmatter")
        lines.append("=" * 80)
        lines.append("")
        lines.append("📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        if workspace.lane_id:
            lines.append("   # Review the implementation in this workspace")
            lines.append("   # Read code, run tests, check against requirements")
            lines.append(f"   # When done, return to repo root: cd {repo_root}")
        else:
            lines.append("   # Review the planning-artifact changes directly in the repository root")
        lines.append("")
        lines.extend(_shared_artifact_guidance(workspace, repo_root, mission_slug))
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ status is tracked in {target_branch} branch (visible to all agents)")
        lines.append("   Status changes auto-commit to the coordination branch (visible to all agents)")
        lines.append("   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Review the implementation against the requirements below.")
        lines.append("Check code quality, tests, documentation, and adherence to spec.")
        lines.append("")
        lines.append(render_wp_review_antipattern_checklist())
        lines.append("")

        # WP content marker and content
        lines.extend(_render_wp_prompt_wrapper(wp.path.read_text(encoding="utf-8")))

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 REVIEW COMPLETE? RUN ONE OF THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append("✅ APPROVE (no issues found):")
        lines.append(f'   spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed: <summary>"')
        lines.append("")
        lines.append("❌ REQUEST CHANGES (issues found):")
        lines.append("   1. Write feedback to the in-repo path (committed with the project):")
        lines.append(f"      cat > {review_feedback_path} <<'EOF'")
        lines.append("**Issue 1**: <description and how to fix>")
        lines.append("**Issue 2**: <description and how to fix>")
        lines.append("EOF")
        lines.append("")
        lines.append("   2. Move to planned with feedback:")
        lines.append(
            f"      spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}"
        )
        lines.append("")
        lines.append("⚠️  NOTE: You MUST run one of these commands to complete the review!")
        lines.append("     The Python script handles all file updates automatically.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        # FR-005 (#2186): the review-prompt metadata ``mission_id`` is a meta.json
        # read → PRIMARY only. Anchor on the topology-blind PRIMARY dir, not the
        # coord-aware resolver (which selects the meta-less husk).
        _mission_identity = resolve_mission_identity(
            primary_feature_dir_for_mission(
                main_repo_root,
                _canonicalize_primary_read_handle(main_repo_root, mission_slug),
            )
        )
        _review_metadata = build_review_prompt_metadata(
            repo_root=main_repo_root,
            mission_id=_mission_identity.mission_id,
            mission_slug=mission_slug,
            work_package_id=normalized_wp_id,
            lane_worktree=Path(workspace_path),
            mission_branch=str(review_ctx.get("mission_branch") or target_branch),
            lane_branch=str(review_ctx.get("lane_branch") or review_ctx.get("branch_name") or "HEAD"),
            base_ref=str(review_ctx.get("base_ref") or review_ctx.get("base_branch") or target_branch),
        )
        prompt_file = write_review_prompt_with_metadata(full_content, _review_metadata)
        validate_review_prompt_metadata(prompt_file, _review_metadata)

        # Output concise summary with directive to read the prompt
        print()
        if dependents_warning:
            for line in dependents_warning:
                print(line)
            print()
        print(f"📍 Workspace: cd {workspace_path}")
        if workspace.lane_id:
            shared = ", ".join(workspace.lane_wp_ids or [normalized_wp_id])
            print(f"   Lane workspace: {workspace.lane_id} (shared by {shared})")
        else:
            print("   Repository-root planning workspace")
        if review_ctx["base_branch"] != "unknown":
            base = review_ctx["base_branch"]
            print(f"🔀 Branch: {review_ctx['branch_name']} (based on {base}, {review_ctx['commit_count']} commits)")
            if workspace.resolution_kind == "repo_root":
                wp_meta, _ = read_wp_frontmatter(wp.path)
                review_pathspecs = list(wp_meta.owned_files)
                mission_root = f"kitty-specs/{mission_slug}/"
                if any(path.startswith(mission_root) for path in review_pathspecs):
                    review_pathspecs.extend(
                        [
                            f":(exclude){mission_root}tasks/**",
                            f":(exclude){mission_root}tasks.md",
                            f":(exclude){mission_root}{_STATUS_EVENTS_FILENAME}",
                            f":(exclude){mission_root}{_STATUS_FILENAME}",
                        ]
                    )
                review_paths = " -- " + " ".join(review_pathspecs) if review_pathspecs else ""
                print(f"   Review diff: git log {base}..{review_ctx['branch_name']} --oneline{review_paths}")
            else:
                print(f"   Review diff: git log {base}..{review_ctx['branch_name']} --oneline")
        elif workspace.resolution_kind == "repo_root":
            print("🔀 Review diff unavailable: no deterministic implementation claim commit found for this WP")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After review, run:")
        print(f'  ✅ spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed"')
        print(f"  ❌ spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}")

    except typer.Exit:
        with contextlib.suppress(Exception):
            _print_commit_summary(command_name="review")
        raise
    except Exception as e:
        with contextlib.suppress(Exception):
            _print_commit_summary(command_name="review")
        print(f"Error: {e}")
        raise typer.Exit(1)

    # WP06 T029: terminal commit summary for the review command.
    _print_commit_summary(command_name="review")
