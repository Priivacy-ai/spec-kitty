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
from typing import Any

from specify_cli.core.subtask_rows import iter_unchecked_subtask_rows
from specify_cli.core.vcs.git import merge_base_changed_files
from specify_cli.task_utils import run_git

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

    Consumes the ONE shared coord-read seam
    (:func:`mission_runtime.coord_read_dir_for`, coord-commit-integrity SURFACE A
    #5) — the SAME seam ``accept.py::_coord_worktree_root`` consumes — so the
    topology+existence guard is expressed once (Directive-044, never a hand-rolled
    ``-coord`` path). It routes to the coord surface ONLY when the mission's stored
    topology routes through coordination AND that surface is materialised on disk;
    otherwise it falls back to ``feature_dir`` so flat / ``SINGLE_BRANCH`` /
    ``LANES`` missions read exactly where they do today (regression-preserving).
    """
    from mission_runtime import MissionArtifactKind, coord_read_dir_for

    # ``feature_dir.name`` (not the raw ``feature`` operator handle) keys the
    # resolver here: the caller threads the PRIMARY_METADATA read dir, whose
    # ``.name`` is a materialized primary dir name the resolver accepts and
    # canonicalizes — mirroring ``collect_feature_summary``'s own
    # ``primary_slug = feature_dir.name`` (C-002).
    resolved = coord_read_dir_for(
        repo_root, feature_dir.name, MissionArtifactKind.ACCEPTANCE_MATRIX
    )
    return resolved if resolved is not None else feature_dir


def _evaluate_acceptance_matrix(
    repo_root: Path,
    feature_dir: Path,
    activity_issues: list[str],
    skipped_checks: list[AcceptanceCheckDiagnostic],
    blocked_checks: list[AcceptanceCheckDiagnostic],
    *,
    mutate_matrix: bool,
) -> None:
    """Read/enforce/validate the acceptance matrix once the branch gate passed."""
    from specify_cli.acceptance.matrix import (
        enforce_negative_invariants,
        read_acceptance_matrix,
        validate_matrix_evidence,
        write_acceptance_matrix,
    )

    matrix_dir = _acceptance_matrix_read_dir(repo_root, feature_dir)
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
        acc_matrix.negative_invariants = enforce_negative_invariants(repo_root, acc_matrix.negative_invariants)
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
        repo_root, feature_dir, activity_issues, skipped_checks, blocked_checks, mutate_matrix=mutate_matrix
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
