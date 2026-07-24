#!/usr/bin/env python3
"""Pure(ish) lane-gate and workflow-evidence checks for the acceptance package.

WP04 (coord-authority-trio-degod-01KX7094) / T022: extracted from
``acceptance/__init__.py`` to bring ``_check_lane_gates`` (CC19) and
``_check_workflow_run_evidence`` under the S3776 <=15 complexity gate without
changing behaviour. This module owns the deterministic lane/branch/matrix
evaluation and the workflow-evidence detection; the executor
(``acceptance.collect_feature_summary`` / ``perform_acceptance``) stays the
thin I/O-and-wiring layer.

Cross-module note: a couple of call sites here resolve
``specify_cli.acceptance._target_branch_for_feature`` and
``specify_cli.acceptance._read_text_strict`` via a **deferred** import inside
the function body rather than a top-level import. This is deliberate, not an
oversight: the WP01 characterization suite
(``tests/characterization/test_trio_pure_cores.py``) monkeypatches
``specify_cli.acceptance.read_target_branch_from_meta`` to isolate
``_check_lane_gates`` from real ``meta.json`` I/O. A Python function's free
variables resolve through the globals of the module it is *defined* in, so a
direct top-level ``from specify_cli.core.paths import read_target_branch_from_meta``
here would bind a private, unpatchable copy and silently ignore the test
double. Reading the collaborator off the live ``specify_cli.acceptance``
namespace at call time keeps the monkeypatch visible across the module
boundary. Do not "simplify" this into a top-level import.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mission_runtime import TopologySurface
from specify_cli.acceptance.execution_context import GateSurfaceRefMismatch
from specify_cli.core.subtask_rows import iter_unchecked_subtask_rows
from specify_cli.core.vcs.git import merge_base_changed_files
from specify_cli.task_utils import run_git

if TYPE_CHECKING:
    from specify_cli.acceptance.execution_context import (
        CannotEvaluate,
        GateExecutionContext,
    )

# Mirrors ``specify_cli.acceptance._ACCEPTED_READY_LANES``. Duplicated here
# (rather than imported) because it is a tiny, immutable, non-monkeypatched
# value-level constant — importing it back from the package would require the
# same deferred-lookup indirection as the collaborators above for zero benefit.
_ACCEPTED_READY_LANES = frozenset({"approved", "done"})

# Mirrors ``specify_cli.acceptance.TASKS_FILE`` — see the note on
# ``_ACCEPTED_READY_LANES`` above; same rationale.
_TASKS_FILE = "tasks.md"

WORKFLOW_EVIDENCE_FILE = "workflow-evidence.md"
WORKFLOW_RUN_URL_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/actions/runs/\d+\b")


@dataclass
class AcceptanceCheckDiagnostic:
    check: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"check": self.check, "detail": self.detail}


def _all_work_packages_terminal(lanes: Mapping[str, list[str]]) -> bool:
    """True when every tracked WP is in a terminal-ready lane (approved/done).

    FR-009: WP terminal status is the authority for completion, so an
    orchestrated mission whose work landed through the lane lifecycle is
    complete even if the ``tasks.md`` checkboxes were never hand-ticked. Mirrors
    :attr:`AcceptanceSummary.all_done` but operates on the lane buckets directly
    so the ``unchecked_tasks`` derivation does not depend on summary
    construction order. Returns ``False`` when no WP is tracked at all (an empty
    mission has nothing terminal to vouch for completion).
    """
    tracked = any(wp_ids for wp_ids in lanes.values())
    if not tracked:
        return False
    return not any(
        wp_ids for lane, wp_ids in lanes.items() if lane not in _ACCEPTED_READY_LANES
    )


def _normalized_unchecked_tasks(
    unchecked_tasks: list[str],
    lanes: Mapping[str, list[str]],
) -> list[str]:
    """Apply FR-009 + the ``tasks.md missing`` normalization to unchecked tasks.

    FR-009 (#2085a): unchecked-tasks completion derives from WP terminal status.
    When every tracked WP is approved/done, the work landed through the lane
    lifecycle, so the redundant ``tasks.md`` checkbox bookkeeping is not
    required — unticked checkboxes must not strand a finished mission. A mission
    with a non-terminal WP (e.g. ``in_review`` / ``for_review``) still reports
    its unchecked items. The ``[<tasks.md> missing]`` sentinel is also dropped
    (it is surfaced separately via the missing-artifacts gate).

    The acceptance-MATRIX gate (C-010) is untouched: it remains the genuine
    verification surface — this normalization only governs the checkbox gate.
    """
    if unchecked_tasks == [f"{_TASKS_FILE} missing"]:
        return []
    if _all_work_packages_terminal(lanes):
        return []
    return unchecked_tasks


def _find_unchecked_tasks(tasks_file: Path) -> list[str]:
    if not tasks_file.exists():
        return [f"{_TASKS_FILE} missing"]

    from specify_cli import acceptance as _acceptance_pkg

    return list(iter_unchecked_subtask_rows(_acceptance_pkg._read_text_strict(tasks_file)))


def _append_skipped_lane_checks(
    skipped_checks: list[AcceptanceCheckDiagnostic],
    *,
    reason: str,
    include_matrix_presence: bool = False,
) -> None:
    checks = [
        ("acceptance_matrix_presence", "Acceptance matrix presence check"),
        ("acceptance_matrix_evidence", "Acceptance matrix evidence validation"),
        ("negative_invariants", "Negative invariant execution"),
        ("acceptance_matrix_verdict", "Acceptance matrix verdict evaluation"),
    ]
    for check, label in checks[0 if include_matrix_presence else 1:]:
        skipped_checks.append(
            AcceptanceCheckDiagnostic(
                check=check,
                detail=f"{label} skipped: {reason}",
            )
        )


def _resolve_lanes_manifest_or_stop(
    feature_dir: Path,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
) -> Any:
    """Read ``lanes.json``; return ``None`` when the caller should stop.

    Two distinct "stop" causes collapse to the same ``None`` sentinel because
    the caller's only remaining decision is whether to continue — corruption
    already records its own blocked/skipped diagnostics here, and a genuinely
    absent ``lanes.json`` (flat/legacy mission) is a silent no-op, matching the
    pre-extraction behaviour exactly.
    """
    from specify_cli.lanes.persistence import CorruptLanesError, read_lanes_json

    try:
        return read_lanes_json(feature_dir)
    except CorruptLanesError as exc:
        message = str(exc)
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="lanes_manifest", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="lanes.json is corrupt or malformed",
            include_matrix_presence=True,
        )
        return None


def _evaluate_branch_gate(
    lanes_manifest: Any,
    feature_dir: Path,
    branch: str | None,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
) -> bool:
    """Target-branch mismatch + allowed-branch + planning-only gate.

    Returns ``True`` when the caller should continue on to the acceptance
    matrix evaluation, ``False`` when it should stop (blocked or a
    planning-artifact-only mission, which never carries a matrix).
    """
    from specify_cli.lanes.compute import is_planning_artifact_only

    from specify_cli import acceptance as _acceptance_pkg

    meta_target_branch = _acceptance_pkg._target_branch_for_feature(feature_dir)
    if meta_target_branch and meta_target_branch != lanes_manifest.target_branch:
        message = (
            "Acceptance target branch mismatch: "
            f"meta.json targets {meta_target_branch}, lanes.json targets {lanes_manifest.target_branch}"
        )
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="mission_branch", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="meta.json target_branch does not match lanes.json target_branch",
            include_matrix_presence=True,
        )
        return False

    planning_artifact_only = is_planning_artifact_only(lanes_manifest)
    allowed_branches = {lanes_manifest.target_branch}
    if not planning_artifact_only:
        allowed_branches.add(lanes_manifest.mission_branch)

    if branch is None or branch not in allowed_branches:
        allowed_label = ", ".join(sorted(branch_name for branch_name in allowed_branches if branch_name))
        current_label = branch or "detached HEAD"
        message = f"Acceptance must run on mission or target branch ({allowed_label}), not {current_label}"
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="mission_branch", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="current branch is neither mission branch nor target branch",
            include_matrix_presence=True,
        )
        return False

    if planning_artifact_only:
        _append_skipped_lane_checks(
            skipped_checks,
            reason="planning_artifact-only missions do not produce acceptance-matrix.json",
            include_matrix_presence=True,
        )
        return False

    return True


def _acceptance_gate_context(
    repo_root: Path, feature_dir: Path, *, branch: str | None = None
) -> GateExecutionContext:
    """Build the ACCEPT-phase :class:`GateExecutionContext` for the acceptance matrix.

    The ONE gate-context construction door for the acceptance-matrix gate (GEC-1 /
    T017): it resolves the surface through the WP02 total resolver
    (:func:`mission_runtime.resolve_artifact_surface`) so the four ``CoordState``
    answers are total by construction — ``DELETED`` raises ``CoordinationBranchDeleted``
    (C3 fail-loud), ``EMPTY`` / ``UNMATERIALIZED`` stamp ``PRIMARY`` (the create
    window), ``MATERIALIZED`` stamps ``COORD``. The gate is then handed the surface
    (never an ambient ``repo_root`` / cwd), and every verdict/refusal it emits names
    the returned ``surface_kind`` + ``ref`` (C6). ``ref`` prefers the caller-observed
    currently-checked-out ``branch`` (GEC-2 / C5's reference point — see
    :func:`_assert_ref_agreement`), falling back to the mission target branch, then
    the ``HEAD`` symbolic ref when neither is available.

    ``feature_dir.name`` (not the raw operator handle) keys the resolver: the caller
    threads the ``PRIMARY_METADATA`` read dir, whose ``.name`` is a materialized
    primary dir name the resolver canonicalizes — mirroring
    ``collect_feature_summary``'s own ``primary_slug = feature_dir.name`` (C-002).
    """
    from mission_runtime import MissionArtifactKind

    from specify_cli import acceptance as _acceptance_pkg
    from specify_cli.acceptance.execution_context import (
        LifecyclePhase,
        build_gate_execution_context,
    )

    # ``_target_branch_for_feature`` is resolved off the live ``specify_cli.acceptance``
    # namespace at call time (not a top-level import) so the WP01 characterization
    # monkeypatch of ``read_target_branch_from_meta`` stays visible — see the module
    # docstring's cross-module note.
    ref = branch or _acceptance_pkg._target_branch_for_feature(feature_dir) or "HEAD"
    return build_gate_execution_context(
        repo_root,
        feature_dir.name,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        phase=LifecyclePhase.ACCEPT,
        ref=ref,
    )


def _assert_ref_agreement(context: GateExecutionContext) -> GateSurfaceRefMismatch | None:
    """GEC-2 / C5: refuse rather than judge a surface that drifted from its ref.

    Ref-agreement is asserted only for a ``PRIMARY``-stamped surface. ``context.ref``
    names the branch this evaluation resolved as its reference point — the
    caller-observed currently-checked-out branch when available, else the mission's
    target branch (:func:`_acceptance_gate_context`) — and a ``PRIMARY`` surface
    lives in that SAME checkout, so the two must agree absent a race between when
    ``branch`` was read and when this gate runs (mirroring the ``safe_commit``
    HEAD-vs-destination assert this method is built on).

    A ``COORD``-stamped surface is a genuinely different worktree on its OWN
    coordination branch — ``ref`` was never meant to name that branch (C6 pins it to
    the mission's target/observed branch even for a coord-topology mission,
    ``test_c6_recorded_judgement_names_surface_and_ref``), so asserting branch
    identity there would be a category error: it would refuse every legitimate
    coordination-topology run, not merely a drifted one, which is precisely the
    topology-neutrality GEC-4/C7 forbids. That surface's structural validity is
    already guarded by GEC-3's total resolution (``CoordinationBranchDeleted``) and
    GEC-5's create-window check (:func:`_matrix_surface_cannot_hold`); this method
    does not duplicate those with an inapplicable branch comparison.

    Also a no-op when ``context.surface`` does not exist on disk: a surface with
    nothing checked out there has no branch to have drifted FROM (there is no git
    worktree to read), and the WP18 unit-level deferral tests
    (``tests/integration/test_deferral_enforcement_and_disclosure.py``, "no git
    shelling required" by design) drive this function against a synthetic,
    never-created ``tmp_path`` surface -- a distinct absence already reported
    honestly elsewhere (e.g. "acceptance-matrix.json ... not found"), not a
    ref-agreement refusal to invent here.
    """
    if context.surface_kind is not TopologySurface.PRIMARY:
        return None
    if not context.surface.exists():
        return None
    try:
        context.assert_at_ref()
    except GateSurfaceRefMismatch as exc:
        return exc
    return None


def _record_ref_mismatch_cannot_evaluate(
    exc: GateSurfaceRefMismatch,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
) -> None:
    """Record the C5 ref-mismatch refusal, naming the surface + expected/actual ref (C6).

    Mirrors :func:`_record_matrix_cannot_evaluate`'s shape: a blocking diagnostic and
    the matching skipped-checks fan-out, never a pass/fail verdict.
    """
    detail = (
        f"Acceptance matrix cannot be evaluated ({exc.error_code}): surface "
        f"(stamped {exc.surface_kind.value}) is at {exc.actual_ref!r} but the gate "
        f"expected it at {exc.expected_ref!r} [surface={exc.surface_kind.value} "
        f"ref={exc.expected_ref}]"
    )
    activity_issues.append(detail)
    blocked_checks.append(
        AcceptanceCheckDiagnostic(check="acceptance_matrix_cannot_evaluate", detail=detail)
    )
    _append_skipped_lane_checks(skipped_checks, reason=exc.error_code)


def _acceptance_matrix_read_dir(repo_root: Path, feature_dir: Path) -> Path:
    """Resolve the dir the acceptance-matrix must be READ from for this mission.

    ``ACCEPTANCE_MATRIX`` is a *coordination*-partition kind
    (:data:`mission_runtime.artifacts._PLACEMENT_ARTIFACT_KINDS`): under coord
    topology ``write_acceptance_matrix`` lands it on the coordination
    worktree's ``feature_dir`` (T008), NOT the PRIMARY ``feature_dir`` threaded
    through the gate pipeline — that ``feature_dir`` is the ``PRIMARY_METADATA``
    read dir (``collect_feature_summary``), which resolves PRIMARY for every
    topology. Reading the matrix off the raw PRIMARY ``feature_dir`` therefore
    reports a false "acceptance-matrix.json not found" for a coord-topology
    mission whose matrix correctly lives on coord.

    Thin projection of the surface off :func:`_acceptance_gate_context` (the ONE
    gate-context door) — the ``.surface`` of the resolved
    :class:`GateExecutionContext`. The seam resolves the coord surface ONLY when the
    mission's stored topology routes through coordination AND that surface is
    materialised (``MATERIALIZED``); otherwise it resolves the primary mission dir
    AFFIRMATIVELY (AH-2) — so flat / ``SINGLE_BRANCH`` / ``LANES`` and the ``EMPTY``
    / ``UNMATERIALIZED`` create window read exactly where they do today
    (regression-preserving). A ``DELETED`` coordination branch raises
    :class:`CoordinationBranchDeleted` (C3 "fail loud"): a deleted coord branch
    carries unmerged acceptance state, so accept must refuse, not silently pass on a
    stale surface.
    """
    return _acceptance_gate_context(repo_root, feature_dir).surface


def _matrix_surface_cannot_hold(
    context: GateExecutionContext, repo_root: Path, feature_dir: Path
) -> CannotEvaluate | None:
    """GEC-5 / C2: refuse when the coord-homed matrix is judged on a PRIMARY stamp.

    A stamp is not permission: when the acceptance matrix's declared home is
    ``COORD`` (a coordination-routing mission) but the resolved surface came back
    stamped ``PRIMARY`` — the ``EMPTY`` / ``UNMATERIALIZED`` create-window
    substitution — the coordination surface is not materialised, so the primary
    surface cannot hold the coord-homed matrix. Returns the distinguishable
    cannot-evaluate outcome (naming its surface + ref) rather than reading an empty
    primary and passing by default (#2885). Returns ``None`` for flat /
    ``SINGLE_BRANCH`` / ``LANES`` (declared home IS primary, AH-2) and for a
    materialised coord surface — both can legitimately hold the fact (C7 neutrality:
    the flat and coord-materialised cases behave identically).
    """
    from specify_cli.acceptance.execution_context import declared_home_surface

    from mission_runtime import MissionArtifactKind

    home = declared_home_surface(
        repo_root, feature_dir.name, MissionArtifactKind.ACCEPTANCE_MATRIX
    )
    return context.surface_cannot_hold(home)


def _record_matrix_cannot_evaluate(
    cannot: CannotEvaluate,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
) -> None:
    """Record the cannot-evaluate outcome, naming the surface + ref it refused on (C6)."""
    detail = (
        f"Acceptance matrix cannot be evaluated ({cannot.reason.value}): "
        f"{cannot.detail} [surface={cannot.surface_kind.value} ref={cannot.ref}]"
    )
    activity_issues.append(detail)
    blocked_checks.append(
        AcceptanceCheckDiagnostic(check="acceptance_matrix_cannot_evaluate", detail=detail)
    )
    _append_skipped_lane_checks(skipped_checks, reason=cannot.reason.value)


def _evaluate_acceptance_matrix(
    repo_root: Path,
    feature_dir: Path,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
    *,
    mutate_matrix: bool,
    branch: str | None = None,
) -> None:
    """Read/enforce/validate the acceptance matrix once the branch gate passed.

    The matrix is judged strictly from the gate context's surface (C1) — the WP02
    total resolver picks coord vs primary; this gate never re-reads an ambient
    ``repo_root`` / cwd. GEC-2 (C5) refuses rather than judges when a ``PRIMARY``
    surface has drifted from the branch this evaluation resolved as its reference
    point (:func:`_assert_ref_agreement`). GEC-5 (C2) short-circuits to
    cannot-evaluate when the coord-homed matrix would be judged against a
    create-window PRIMARY substitution, rather than silently passing on an empty
    surface (#2885).
    """
    from specify_cli.acceptance.matrix import (
        VERDICT_PASS_PENDING_CONSOLIDATION,
        enforce_negative_invariants,
        read_acceptance_matrix,
        validate_matrix_evidence,
        write_acceptance_matrix,
    )

    context = _acceptance_gate_context(repo_root, feature_dir, branch=branch)
    ref_mismatch = _assert_ref_agreement(context)
    if ref_mismatch is not None:
        _record_ref_mismatch_cannot_evaluate(
            ref_mismatch, activity_issues, skipped_checks, blocked_checks
        )
        return

    cannot = _matrix_surface_cannot_hold(context, repo_root, feature_dir)
    if cannot is not None:
        _record_matrix_cannot_evaluate(cannot, activity_issues, skipped_checks, blocked_checks)
        return

    matrix_dir = context.surface
    acc_matrix = read_acceptance_matrix(matrix_dir)
    if acc_matrix is None:
        message = (
            "Acceptance matrix (acceptance-matrix.json) is required for lane-based "
            "features but was not found. This file is normally scaffolded "
            "automatically. If it is missing, regenerate it: "
            f"spec-kitty agent mission finalize-tasks --mission {feature_dir.name}"
        )
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="acceptance_matrix", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="acceptance-matrix.json is missing",
        )
        return

    if acc_matrix.negative_invariants and mutate_matrix:
        # WP04 T023: hand the gate context to the enforcer so a pending invariant
        # whose subject cannot exist on this surface defers (NI-3/C4) instead of
        # reporting a false still_present, and a freshly judged result is stamped
        # with the surface + ref it was established against (NI-1 provenance).
        acc_matrix.negative_invariants = enforce_negative_invariants(
            repo_root, acc_matrix.negative_invariants, context=context
        )
        write_acceptance_matrix(matrix_dir, acc_matrix)
    elif acc_matrix.negative_invariants:
        skipped_checks.append(
            AcceptanceCheckDiagnostic(
                check="negative_invariants",
                detail="Negative invariant execution skipped: diagnose mode is read-only",
            )
        )

    for err in validate_matrix_evidence(acc_matrix):
        activity_issues.append(f"Evidence: {err}")

    verdict = acc_matrix.overall_verdict
    if verdict == "fail":
        activity_issues.append("Acceptance matrix verdict is 'fail' — negative invariants or criteria not satisfied")
    elif verdict == "pending":
        activity_issues.append("Acceptance matrix verdict is 'pending' — criteria or invariants have not been verified")
    elif verdict == VERDICT_PASS_PENDING_CONSOLIDATION:
        # NI-5 (C5): deferral does NOT block acceptance — this is deliberately a
        # skipped-check (informational), never an activity issue. NI-7: disclose to
        # the operator that the mission loop will not verify the deferral (it has a
        # single pre-consolidation reader) — the post-consolidation verification op
        # / PR CI is the enforcer, and the mission cannot reach ``done`` until then.
        skipped_checks.append(
            AcceptanceCheckDiagnostic(
                check="negative_invariants_deferred",
                detail=(
                    "One or more negative invariants are deferred to post-consolidation "
                    "verification; acceptance is not blocked, but this loop does not verify "
                    "them — the post-consolidation op (or PR CI) must, before the mission is done."
                ),
            )
        )


def _check_lane_gates(
    repo_root: Path,
    feature_dir: Path,
    branch: str | None,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
    *,
    mutate_matrix: bool = True,
) -> None:
    """Enforce lane-based acceptance gates and acceptance matrix."""
    lanes_manifest = _resolve_lanes_manifest_or_stop(feature_dir, activity_issues, skipped_checks, blocked_checks)
    if lanes_manifest is None:
        return

    should_continue = _evaluate_branch_gate(
        lanes_manifest, feature_dir, branch, activity_issues, skipped_checks, blocked_checks
    )
    if not should_continue:
        return

    _evaluate_acceptance_matrix(
        repo_root,
        feature_dir,
        activity_issues,
        skipped_checks,
        blocked_checks,
        mutate_matrix=mutate_matrix,
        branch=branch,
    )


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    return bool(run_git(["rev-parse", "--verify", "--quiet", ref], cwd=repo_root, check=False).returncode == 0)


def _changed_workflow_files(repo_root: Path, feature_dir: Path, branch: str | None) -> list[str]:
    """Return workflow files changed by the current mission branch."""
    from specify_cli import acceptance as _acceptance_pkg

    target_branch = _acceptance_pkg._target_branch_for_feature(feature_dir)
    if not target_branch or branch == target_branch:
        return []

    base_ref = target_branch if _git_ref_exists(repo_root, target_branch) else f"origin/{target_branch}"
    if not _git_ref_exists(repo_root, base_ref):
        return []

    changed = merge_base_changed_files(
        repo_root, base_ref, pathspec=".github/workflows", diff_filter="AMR"
    )
    return sorted({line.strip() for line in changed if line.strip()})


def _workflow_evidence_missing(feature_dir: Path) -> bool:
    evidence_path = feature_dir / WORKFLOW_EVIDENCE_FILE
    if not evidence_path.is_file():
        return True
    text = evidence_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return True
    return WORKFLOW_RUN_URL_RE.search(text) is None and not _contains_workflow_run_id(text)


def _contains_workflow_run_id(text: str) -> bool:
    """Return True when evidence text includes a standalone GitHub Actions run id."""

    for raw_line in text.splitlines():
        normalized = _normalize_workflow_evidence_line(raw_line)
        if normalized is None:
            continue
        remainder = _extract_workflow_run_remainder(normalized)
        if remainder is None:
            continue
        if remainder.isdigit() and len(remainder) >= 5:
            return True
    return False


def _normalize_workflow_evidence_line(raw_line: str) -> str | None:
    normalized = " ".join(raw_line.strip().lower().split())
    if not normalized:
        return None
    for prefix in ("successful ", "github actions "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def _extract_workflow_run_remainder(normalized: str) -> str | None:
    if normalized.startswith("run id"):
        remainder = normalized[len("run id") :]
    elif normalized.startswith("run"):
        remainder = normalized[len("run") :]
    else:
        return None
    remainder = remainder.lstrip()
    if remainder[:1] in ":#-":
        remainder = remainder[1:].lstrip()
    return remainder


def _check_workflow_run_evidence(
    repo_root: Path,
    feature_dir: Path,
    branch: str | None,
    activity_issues: list[str],
) -> None:
    changed = _changed_workflow_files(repo_root, feature_dir, branch)
    if changed and _workflow_evidence_missing(feature_dir):
        activity_issues.append(
            "Workflow run evidence required: this mission changes "
            + ", ".join(changed)
            + f". Add a successful real GitHub Actions run ID or URL to {feature_dir.name}/{WORKFLOW_EVIDENCE_FILE}."
        )


__all__: list[str] = []
