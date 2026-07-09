"""Issue-matrix evaluation, review-verdict, and review-readiness validation.

WP06 (#2058): cohesive seam extracted from the ``tasks`` god-module. These
helpers parse and validate review-side state: the issue-matrix approval
blocker, the latest review-cycle verdict, the self-review fallback option
guard, the stale/stalled review status annotations, and the
``move-task → for_review/approved/done`` readiness validation.

Import direction is one-way (INV-2): this module may import from
``tasks_outline`` / ``tasks_materialization`` (seam↔seam is allowed) but MUST
NOT import from ``tasks`` (the god-module re-exports these names back for
existing call sites).

Collaborators that live in ``tasks.py`` and that tests monkeypatch on the
``tasks`` namespace (``get_main_repo_root``, ``get_mission_type``,
``get_feature_target_branch``, ``resolve_workspace_for_wp``, and the
``tasks``-resident git helpers) are *injected* into
:func:`_validate_ready_for_review` by the thin ``tasks.py`` wrapper rather
than imported here. This keeps the existing patch contracts byte-for-byte
without re-importing the god-module.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from datetime import datetime, UTC
from kernel._safe_re import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from specify_cli.cli.commands.review._issue_matrix import (
        IssueMatrixValidationResult,
        IssueMatrixVerdict,
    )
    from specify_cli.workspace.context import ResolvedWorkspace

from specify_cli.core.constants import (
    KITTY_SPECS_DIR,
    MISSION_TYPE_RESEARCH,
    MISSION_TYPE_SOFTWARE_DEV,
)
from specify_cli.lanes._git import lane_has_commit_beyond_base
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
from specify_cli.status import Lane, StatusEvent
from specify_cli.status import is_dossier_snapshot as _is_dossier_snapshot
from specify_cli.task_utils import extract_scalar, split_frontmatter

logger = logging.getLogger(__name__)

# Mirror of the constant defined in ``tasks``. Hoisted as a module-local
# constant so this seam has no back-import to the god-module.
SPEC_MD_FILENAME = "spec.md"

# Known verdict values from the review-cycle schema.
# Unknown values warn but do NOT block (backward compatibility).
_VALID_VERDICTS: frozenset[str] = frozenset(
    {"approved", "approved_after_orchestrator_fix", "arbiter_override", "rejected"}
)


# ---------------------------------------------------------------------------
# Issue-matrix evaluation helpers (verbatim move from tasks.py, WP06/T022)
# ---------------------------------------------------------------------------


def _issue_matrix_evaluation(
    feature_dir: Path,
    *,
    spec_feature_dir: Path | None = None,
) -> tuple[IssueMatrixValidationResult, set[str], list[str], list[str]]:
    from specify_cli.cli.commands.review._issue_matrix import (
        IssueMatrixVerdict,
        validate_issue_matrix,
    )
    from specify_cli.tasks.issue_matrix import detect_issue_references

    refs = detect_issue_references((spec_feature_dir or feature_dir) / SPEC_MD_FILENAME)
    result = validate_issue_matrix(feature_dir / "issue-matrix.md")
    referenced_issues = {f"#{ref.number}" for ref in refs}
    matrix_issues = _issue_matrix_row_issues(result)
    unresolved_in_mission = _issue_matrix_in_mission_rows(
        result,
        referenced_issues,
        IssueMatrixVerdict.IN_MISSION,
    )
    missing_issues = sorted(referenced_issues - matrix_issues)
    return result, referenced_issues, missing_issues, unresolved_in_mission


def _issue_matrix_row_issues(result: IssueMatrixValidationResult) -> set[str]:
    matrix_issues = {row.issue for row in result.rows}
    for diagnostic in result.diagnostics:
        match = re.search(r"Row for issue '([^']+)'", diagnostic.get("message", ""))
        if match:
            matrix_issues.add(match.group(1))
    return matrix_issues


def _issue_matrix_in_mission_rows(
    result: IssueMatrixValidationResult,
    referenced_issues: set[str],
    in_mission_verdict: IssueMatrixVerdict,
) -> list[str]:
    return sorted(
        row.issue
        for row in result.rows
        if row.verdict is in_mission_verdict and row.issue in referenced_issues
    )


def _issue_matrix_diagnostic_lines(result: IssueMatrixValidationResult) -> tuple[list[str], list[str]]:
    from specify_cli.cli.commands.review._diagnostics import MissionReviewDiagnostic

    unknown_issues: list[str] = []
    other_messages: list[str] = []
    for diagnostic in result.diagnostics:
        message = diagnostic.get("message", "")
        if diagnostic.get("diagnostic_code") == str(MissionReviewDiagnostic.ISSUE_MATRIX_VERDICT_UNKNOWN):
            match = re.search(r"issue '([^']+)'", message)
            unknown_issues.append(match.group(1) if match else message)
        else:
            other_messages.append(message)
    return unknown_issues, other_messages


def _issue_matrix_approval_blocker(
    feature_dir: Path,
    *,
    target_lane: Lane | None = None,
    primary_feature_dir: Path | None = None,
) -> str | None:
    """Return a blocking message when referenced issues still lack final verdicts.

    ``target_lane`` controls how the non-terminal ``in-mission`` verdict is
    treated. At ``approved`` (or when unspecified) an ``in-mission`` row is
    acceptable — the issue is being closed by a later WP in this same mission,
    so a dependency chain is not blocked on its own downstream work. At ``done``
    (mission merge/acceptance) ``in-mission`` is rejected: every issue must have
    reached a terminal verdict (``fixed`` / ``verified-already-fixed`` /
    ``deferred-with-followup``) before the mission lands.
    """
    spec_feature_dir = (
        primary_feature_dir
        if primary_feature_dir is not None and (primary_feature_dir / SPEC_MD_FILENAME).exists()
        else feature_dir
    )
    spec_path = spec_feature_dir / SPEC_MD_FILENAME
    if not spec_path.exists():
        return None

    try:
        from specify_cli.tasks.issue_matrix import detect_issue_references

        refs = detect_issue_references(spec_path)
    except Exception as exc:  # noqa: BLE001 -- approval guard must fail closed
        logger.debug("Could not evaluate issue-matrix approval blocker: %s", exc)
        return (
            "ERROR: issue-matrix.md could not be evaluated before approval.\n"
            f"Reason: {exc}\n"
            "Fix the issue-matrix check before approving."
        )

    if not refs:
        return None

    matrix_path = feature_dir / "issue-matrix.md"
    if not matrix_path.exists():
        if _primary_issue_matrix_satisfies(
            primary_feature_dir=primary_feature_dir,
            feature_dir=feature_dir,
            spec_feature_dir=spec_feature_dir,
            target_lane=target_lane,
        ):
            return None
        issue_list = ", ".join(f"#{ref.number}" for ref in refs)
        return (
            "ERROR: issue-matrix.md is required before approval.\n"
            f"Referenced issues: {issue_list}\n"
            "Fill verdicts before approving."
        )

    result, _, missing_issues, unresolved_in_mission = _issue_matrix_evaluation(
        feature_dir,
        spec_feature_dir=spec_feature_dir,
    )
    if target_lane != Lane.DONE:
        unresolved_in_mission = []

    if result.passed and not missing_issues and not unresolved_in_mission:
        return None
    if _primary_issue_matrix_satisfies(
        primary_feature_dir=primary_feature_dir,
        feature_dir=feature_dir,
        spec_feature_dir=spec_feature_dir,
        target_lane=target_lane,
    ):
        return None

    unknown_issues, other_messages = _issue_matrix_diagnostic_lines(result)

    lines = ["ERROR: issue-matrix.md has unresolved entries. Fill in verdicts before approving."]
    if missing_issues:
        lines.append(f"Missing rows: {', '.join(missing_issues)}")
    if unknown_issues:
        lines.append(f"Unknown: {', '.join(sorted(set(unknown_issues)))}")
    if unresolved_in_mission:
        lines.append(
            "Still 'in-mission' (resolve to fixed / verified-already-fixed / "
            f"deferred-with-followup before done): {', '.join(unresolved_in_mission)}"
        )
    for message in other_messages:
        lines.append(f"- {message}")
    return "\n".join(lines)


def _primary_issue_matrix_satisfies(
    *,
    primary_feature_dir: Path | None,
    feature_dir: Path,
    spec_feature_dir: Path,
    target_lane: Lane | None,
) -> bool:
    if primary_feature_dir is None or primary_feature_dir == feature_dir:
        return False
    if not (primary_feature_dir / "issue-matrix.md").exists():
        return False

    try:
        result, _, missing_issues, unresolved_in_mission = _issue_matrix_evaluation(
            primary_feature_dir,
            spec_feature_dir=spec_feature_dir,
        )
    except Exception as exc:  # noqa: BLE001 -- fallback must not hide real blockers
        logger.debug("Could not evaluate primary issue-matrix fallback: %s", exc)
        return False

    if target_lane != Lane.DONE:
        unresolved_in_mission = []
    return result.passed and not missing_issues and not unresolved_in_mission


# ---------------------------------------------------------------------------
# Self-review fallback option guard (verbatim move from tasks.py, WP06/T022)
# ---------------------------------------------------------------------------


def _self_review_fallback_option_error(
    *,
    enabled: bool,
    target_lane: str,
    force: bool,
    intended_reviewer: str | None,
    failure_reason: str | None,
) -> str | None:
    """Validate explicit self-review fallback metadata before approval."""
    from specify_cli.status import resolve_lane_alias

    if not enabled:
        if intended_reviewer or failure_reason:
            return "--intended-reviewer/--reviewer-failure-reason require --self-review-fallback."
        return None

    if resolve_lane_alias(target_lane) not in (Lane.APPROVED, Lane.DONE):
        return "--self-review-fallback is only valid when approving or marking done."
    if not force:
        return "--self-review-fallback requires --force so force_count records the independence override."
    if not (intended_reviewer or "").strip():
        return "--self-review-fallback requires --intended-reviewer <agent>."
    if not (failure_reason or "").strip():
        return "--self-review-fallback requires --reviewer-failure-reason <reason>."
    return None


# ---------------------------------------------------------------------------
# Review-cycle verdict + status-flag helpers (verbatim move, WP06/T022)
# ---------------------------------------------------------------------------


def _review_cycle_number(path: Path) -> int:
    """Return the numeric review-cycle suffix for sorting review artifacts."""
    match = re.search(r"review-cycle-(\d+)\.md", path.name)
    return int(match.group(1)) if match else 0


def _get_latest_review_cycle_verdict(wp_dir: Path) -> tuple[str | None, Path | None]:
    """Return (verdict_value, artifact_path) for the latest review-cycle-N.md.

    Scans *wp_dir* for ``review-cycle-<N>.md`` files, picks the highest-numbered
    one, and returns the ``verdict`` frontmatter value together with the artifact
    path so callers can name the file in error messages.

    Returns (None, None) when no review-cycle artifacts exist.
    Returns (None, artifact_path) when the artifact exists but verdict is absent
    or malformed.

    If the verdict is present but not in :data:`_VALID_VERDICTS`, a warning is
    logged (but the value is still returned — callers decide what to do with it).
    """
    cycles = sorted(
        wp_dir.glob("review-cycle-*.md"),
        key=_review_cycle_number,
    )
    if not cycles:
        return None, None
    artifact = cycles[-1]
    try:
        text = artifact.read_text(encoding="utf-8")
        frontmatter_str, _, _ = split_frontmatter(text)
        if not frontmatter_str:
            return None, artifact
        verdict = extract_scalar(frontmatter_str, "verdict")
        if verdict is not None and verdict not in _VALID_VERDICTS:
            logger.warning(
                "Warning: %s has unrecognized verdict '%s' — expected one of %s",
                artifact.name,
                verdict,
                sorted(_VALID_VERDICTS),
            )
        return verdict, artifact
    except Exception:  # noqa: BLE001 — review-cycle artifact may be malformed; fail-open
        return None, artifact


def _review_artifact_dir_for_wp(tasks_dir: Path, wp: dict[str, object]) -> Path | None:
    """Return the review-cycle artifact dir for a WP status row."""
    wp_file = wp.get("file")
    if isinstance(wp_file, str) and wp_file.endswith(".md"):
        return tasks_dir / Path(wp_file).stem
    wp_id = wp.get("id")
    return tasks_dir / str(wp_id) if wp_id else None


def _latest_status_event_time(events: list[StatusEvent], wp_id: str) -> datetime | None:
    """Return the latest parsed event time for a WP."""
    latest: datetime | None = None
    for event in events:
        if event.wp_id != wp_id or not event.at:
            continue
        try:
            parsed = datetime.fromisoformat(event.at)
        except ValueError:
            continue
        parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _apply_review_status_flags(
    work_packages: list[dict[str, object]],
    *,
    tasks_dir: Path,
    events: list[StatusEvent],
    stall_threshold_minutes: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Annotate status rows with stale verdict and stalled-review warnings."""
    stale_verdicts: list[dict[str, object]] = []
    stalled_wps: list[dict[str, object]] = []
    now = datetime.now(UTC)

    for wp in work_packages:
        wp_id = wp.get("id")
        if not isinstance(wp_id, str) or not wp_id:
            continue

        lane = wp.get("lane")
        if lane in (Lane.APPROVED, Lane.DONE):
            wp_dir = _review_artifact_dir_for_wp(tasks_dir, wp)
            if wp_dir is not None:
                verdict, artifact = _get_latest_review_cycle_verdict(wp_dir)
                if verdict == "rejected" and artifact is not None:
                    stale_warning: dict[str, object] = {
                        "wp_id": wp_id,
                        "artifact": artifact.name,
                        "verdict": verdict,
                    }
                    stale_verdicts.append(stale_warning)
                    wp["_stale_verdict"] = True
                    wp["stale_review_artifact"] = stale_warning

        if lane == Lane.IN_REVIEW:
            last_event_time = _latest_status_event_time(events, wp_id)
            if last_event_time is None:
                continue
            age_minutes = int((now - last_event_time).total_seconds() / 60)
            if age_minutes > stall_threshold_minutes:
                stall_label = f"STALLED — no move-task in {age_minutes}m"
                stall_warning: dict[str, object] = {
                    "wp_id": wp_id,
                    "age_minutes": age_minutes,
                    "threshold_minutes": stall_threshold_minutes,
                }
                stalled_wps.append(stall_warning)
                wp["_stall_label"] = stall_label
                wp["review_stall"] = stall_warning

    return stale_verdicts, stalled_wps


# ---------------------------------------------------------------------------
# Review-readiness validation (WP06/T023): the ~348-LOC god-function
# ``_validate_ready_for_review`` decomposed into named, behavior-preserving
# sub-validators, each maxCC <= 15. Validation order, every gate, every error
# string, and the (bool, list[str]) return shape are preserved exactly.
# ---------------------------------------------------------------------------


class _ConsoleLike(Protocol):
    # Positional ``print`` only — the validators render with
    # ``console.print(message)`` and never pass keyword options. A ``**kwargs``
    # protocol method is structurally UNsatisfiable by ``rich.console.Console``
    # (whose ``print`` exposes named keyword options, not ``**kwargs``), so the
    # narrow positional shape is what lets the real ``Console`` conform.
    def print(self, *values: object) -> None: ...


def _validate_research_artifacts(
    *,
    main_repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    mission_type: str,
    target_lane: str,
    console: _ConsoleLike,
) -> list[str] | None:
    """Check 1: uncommitted planning artifacts in the planning repo (all missions).

    Returns ``None`` when this gate passes (no blocking dirty files), otherwise
    a populated ``guidance`` list that the caller returns as the failure result.
    Mutates nothing outside its local ``guidance`` accumulator.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", str(feature_dir)], cwd=main_repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    uncommitted_in_main = result.stdout.rstrip()
    if not uncommitted_in_main:
        return None

    # Use the dirty classifier to partition paths into blocking vs. benign.
    # Benign paths (status artifacts, other WPs' task files, metadata) are
    # expected during concurrent multi-agent work and must NOT block handoff.
    from specify_cli.review.dirty_classifier import classify_dirty_paths

    raw_paths = []
    raw_lines = []
    for line in uncommitted_in_main.split("\n"):
        if not line.strip():
            continue
        # git status --porcelain format: "XY path" (first 3 chars are status)
        file_part = line[3:] if len(line) > 3 else line.strip()
        # EXCLUDE policy (C-006): dossier snapshot writes are derived,
        # ephemeral, and recomputable; they must never self-block a
        # transition. Drop them before classification so they cannot
        # leak into the blocking bucket via a path that bypasses
        # ``.gitignore``.
        if _is_dossier_snapshot(file_part):
            continue
        raw_paths.append(file_part)
        raw_lines.append(line)

    blocking, benign = classify_dirty_paths(
        dirty_paths=raw_paths,
        wp_id=wp_id,
        mission_slug=mission_slug,
    )

    if benign:
        # Log info only — benign dirty files do not block review handoff
        console.print(f"[dim]Note: {len(benign)} unrelated dirty file(s) ignored (not owned by {wp_id})[/dim]")

    if not blocking:
        return None

    guidance: list[str] = []
    # Only show lines whose file_part is in the blocking list
    blocking_set = set(blocking)
    blocking_lines = [line for line, fp in zip(raw_lines, raw_paths, strict=False) if fp in blocking_set]
    guidance.append(f"Blocking: {len(blocking)} uncommitted file(s) owned by {wp_id}:")
    guidance.append("")
    guidance.append("Modified files in kitty-specs/:")
    for line in blocking_lines[:5]:
        guidance.append(f"  {line}")
    if len(blocking_lines) > 5:
        guidance.append(f"  ... and {len(blocking_lines) - 5} more")
    guidance.append("")
    guidance.append(f"Commit these files before moving to {target_lane}.")
    guidance.append(f"  cd {main_repo_root}")
    guidance.append(f"  git add kitty-specs/{mission_slug}/")
    if mission_type == MISSION_TYPE_RESEARCH:
        guidance.append(f'  git commit -m "research({wp_id}): <describe your research outputs>"')
    else:
        guidance.append(f'  git commit -m "docs({wp_id}): <describe your changes>"')
    guidance.append("")
    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
    return guidance


def _resolve_worktree_path(
    *,
    main_repo_root: Path,
    mission_slug: str,
    workspace: ResolvedWorkspace | None,
) -> Path:
    """Return the lane worktree path, reproducing the legacy lane-a fallback."""
    if workspace is None:
        from specify_cli.lanes.branch_naming import worktree_path as _seam_worktree_path

        # Legacy lane-a worktree grammar ({slug}-lane-a, no mid8) ⇒
        # mission_id=None reproduces the historical name byte-identically (FR-005).
        # ``Path(...)`` is a narrow coercion: the cross-module ``specify_cli.*``
        # imports are ``follow_imports = skip`` under mypy --strict, so the
        # seam's already-``Path`` return is otherwise inferred as ``Any``.
        return Path(
            _seam_worktree_path(
                main_repo_root, mission_slug, mission_id=None, lane_id="lane-a"
            )
        )
    return Path(workspace.worktree_path)


def _check_worktree_health(worktree_path: Path, wp_id: str, target_lane: str) -> list[str] | None:
    """Husk / toplevel / detached-HEAD / in-progress-operation guards.

    Returns ``None`` when the worktree is healthy, otherwise a populated
    ``guidance`` list. Order is load-bearing (#1833): the ``.git``-marker check
    runs BEFORE any git invocation so a husk directory never causes git to walk
    up into the primary repo.
    """
    from specify_cli.workspace.context import husk_resolution_error, verify_workspace_toplevel

    guidance: list[str] = []
    if not (worktree_path / ".git").exists():
        guidance.append(str(husk_resolution_error(worktree_path)))
        return guidance

    # Last-line defense (R4): the resolved path must be the toplevel
    # of its own working tree before any other git call runs there.
    toplevel_error = verify_workspace_toplevel(worktree_path)
    if toplevel_error is not None:
        guidance.append(str(toplevel_error))
        return guidance

    # Check for detached HEAD before other git status checks
    from specify_cli.core.git_ops import get_current_branch as _get_branch

    wt_branch = _get_branch(worktree_path)
    if wt_branch is None:
        guidance.append("Detached HEAD detected in worktree!")
        guidance.append("")
        guidance.append("Please reattach to a branch before review:")
        guidance.append(f"  cd {worktree_path}")
        guidance.append("  git checkout <your-branch>")
        guidance.append("")
        guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
        return guidance

    # Check for in-progress git operations (merge/rebase/cherry-pick)
    in_progress = []
    state_checks = {
        "MERGE_HEAD": "merge",
        "REBASE_HEAD": "rebase",
        "CHERRY_PICK_HEAD": "cherry-pick",
    }
    for ref, label in state_checks.items():
        state_result = subprocess.run(
            ["git", "rev-parse", "-q", "--verify", ref], cwd=worktree_path, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        if state_result.returncode == 0:
            in_progress.append(label)

    if in_progress:
        guidance.append("In-progress git operation detected in worktree!")
        guidance.append("")
        guidance.append(f"Active operation(s): {', '.join(in_progress)}")
        guidance.append("")
        guidance.append("Resolve or abort before review:")
        guidance.append(f"  cd {worktree_path}")
        guidance.append("  git status")
        guidance.append("  git merge --abort   # if merge")
        guidance.append("  git rebase --abort  # if rebase")
        guidance.append("  git cherry-pick --abort  # if cherry-pick")
        guidance.append("")
        guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
        return guidance

    return None


def _check_branch_currency(
    *,
    worktree_path: Path,
    check_branch: str,
    mission_slug: str,
    wp_id: str,
    target_lane: str,
    behind_commits_touch_only_planning_artifacts: Callable[[Path, str, str], bool],
) -> list[str] | None:
    """Block when the lane worktree is behind its base by non-planning commits."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"HEAD..{check_branch}"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    behind_count = 0
    if result.returncode == 0 and result.stdout.strip():
        try:
            behind_count = int(result.stdout.strip())
        except ValueError:
            behind_count = 0

    # Allow status/planning-only commits to avoid repeated rebase friction.
    if behind_count > 0 and not behind_commits_touch_only_planning_artifacts(
        worktree_path,
        check_branch,
        mission_slug,
    ):
        guidance: list[str] = []
        guidance.append(f"{check_branch} branch has new commits not in this worktree!")
        guidance.append("")
        guidance.append(f"Your branch is behind {check_branch} by {behind_count} commit(s).")
        guidance.append("Rebase before review:")
        guidance.append(f"  cd {worktree_path}")
        guidance.append(f"  git rebase {check_branch}")
        guidance.append("")
        guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
        return guidance
    return None


def _check_uncommitted_worktree_changes(
    *,
    worktree_path: Path,
    wp_id: str,
    target_lane: str,
    filter_runtime_state_paths: Callable[[str], str],
) -> list[str] | None:
    """Block when the worktree has genuine uncommitted implementation work."""
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=worktree_path, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    # FR-015 / C-003: strip spec-kitty's own runtime-state files (e.g.
    # .spec-kitty/review-lock.json written by the review tooling, or
    # .kittify/ merge metadata) before deciding whether the worktree
    # has genuine uncommitted implementation work. The deny-list is a
    # fixed, named tuple (no patterns) so paths outside it still reach
    # the blocking branch and surface as "Uncommitted implementation
    # changes in worktree!" (C-004).
    uncommitted_in_worktree = filter_runtime_state_paths(result.stdout.strip())
    if not uncommitted_in_worktree:
        return None

    staged_lines = []
    unstaged_lines = []
    for line in uncommitted_in_worktree.split("\n"):
        if not line.strip():
            continue
        if line.startswith("??"):
            unstaged_lines.append(line)
            continue
        status = line[:2]
        if status[0] != " ":
            staged_lines.append(line)
        if status[1] != " ":
            unstaged_lines.append(line)

    guidance: list[str] = []
    if staged_lines and not unstaged_lines:
        guidance.append("Staged but uncommitted changes in worktree!")
    elif staged_lines and unstaged_lines:
        guidance.append("Staged and unstaged changes in worktree!")
    else:
        guidance.append("Uncommitted implementation changes in worktree!")
    guidance.append("")
    guidance.append("Modified files:")
    for line in uncommitted_in_worktree.split("\n")[:5]:
        guidance.append(f"  {line}")
    guidance.append("")
    guidance.append("Commit your work first:")
    guidance.append(f"  cd {worktree_path}")
    guidance.append("  git add <deliverable-path-1> <deliverable-path-2> ...")
    guidance.append(f'  git commit -m "feat({wp_id}): <describe implementation>"')
    guidance.append("")
    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
    return guidance


def _check_implementation_commit_present(
    *,
    worktree_path: Path,
    check_branch: str,
    wp_id: str,
    target_lane: str,
) -> list[str] | None:
    """Block when the lane branch has no commit beyond its base."""
    # Check if branch has commits beyond base (use actual base, not target).
    # Shared with the orchestrator-api for_review gate so both enforce the
    # same "an implementation commit exists" rule.
    if lane_has_commit_beyond_base(worktree_path, check_branch):
        return None

    guidance: list[str] = []
    guidance.append("No implementation commits on lane branch!")
    guidance.append("")
    guidance.append(f"The worktree exists but has no commits beyond {check_branch}.")
    guidance.append("Either:")
    guidance.append("  1. Commit your implementation work to the worktree")
    guidance.append("  2. Or verify work is complete (use --force if nothing to commit)")
    guidance.append("")
    guidance.append(f"  cd {worktree_path}")
    guidance.append("  git add <deliverable-path-1> <deliverable-path-2> ...")
    guidance.append(f'  git commit -m "feat({wp_id}): <describe implementation>"')
    guidance.append("")
    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
    return guidance


def _check_kitty_specs_contamination(
    *,
    worktree_path: Path,
    check_branch: str,
    feature_dir: Path,
    wp_id: str,
    target_lane: str,
    list_wp_branch_specs_changes_for_guard: Callable[..., list[str]],
) -> list[str] | None:
    """Block when kitty-specs/ files were committed on the lane branch."""
    contamination_files = list_wp_branch_specs_changes_for_guard(
        worktree_path=worktree_path,
        base_branch=check_branch,
    )
    if not contamination_files:
        return None

    # FR-009 / FR-010: resolve the planning branch from meta.json so
    # the error message names the branch and gives a `git show` example.
    # Falls back gracefully for legacy missions without meta.json.
    # FR-008 / #2139: the target_branch half of this lookup routes through the
    # single read_target_branch_from_meta authority rather than a raw
    # `_meta.get("target_branch")` extraction; planning_base_branch keeps
    # precedence exactly as before.
    _planning_branch: str | None = None
    try:
        from specify_cli.core.paths import read_target_branch_from_meta as _read_target_branch_lggrd
        from specify_cli.mission_metadata import load_meta as _load_meta_lggrd

        _meta = _load_meta_lggrd(feature_dir)
        if _meta:
            _planning_branch = _meta.get("planning_base_branch") or _read_target_branch_lggrd(feature_dir)
    except Exception as _lane_meta_exc:  # noqa: BLE001 - lane guard still reports contamination without optional metadata
        logger.debug(
            "Could not resolve planning_base_branch for lane guard: %s", _lane_meta_exc
        )

    guidance: list[str] = []
    guidance.append("Committed kitty-specs files on this lane branch:")
    for path in contamination_files[:5]:
        guidance.append(f"  {path}")
    if len(contamination_files) > 5:
        guidance.append(f"  ... and {len(contamination_files) - 5} more")
    guidance.append("")
    if _planning_branch:
        _first_planning_path = (
            contamination_files[0] if contamination_files else f"{KITTY_SPECS_DIR}/<path-to-file>"
        )
        guidance.append(
            f"{KITTY_SPECS_DIR}/ changes are not allowed on lane branches.\n"
            f"Planning artifacts must live on: {_planning_branch}\n\n"
            f"To verify a file exists on the planning branch:\n"
            f"  git show {_planning_branch}:{_first_planning_path}"
        )
    else:
        guidance.append(
            f"{KITTY_SPECS_DIR}/ changes are not allowed on lane branches "
            f"(planning branch unknown — check {KITTY_SPECS_DIR}/ on the base branch)."
        )
    guidance.append("")
    guidance.append(f"Clean the branch before moving to {target_lane}:")
    guidance.append(f"  cd {worktree_path}")
    guidance.append(f"  git restore --source {check_branch} --staged --worktree -- {KITTY_SPECS_DIR}/")
    guidance.append('  git commit -m "chore: remove planning artifacts from lane branch"')
    guidance.append("")
    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
    return guidance


def _validate_worktree_state(
    *,
    repo_root: Path,
    main_repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    target_lane: str,
    resolve_workspace_for_wp: Callable[[Path, str, str], ResolvedWorkspace],
    get_feature_target_branch: Callable[[Path, str], str],
    review_currency_check_branch: Callable[..., str],
    behind_commits_touch_only_planning_artifacts: Callable[[Path, str, str], bool],
    filter_runtime_state_paths: Callable[[str], str],
    list_wp_branch_specs_changes_for_guard: Callable[..., list[str]],
) -> tuple[bool, list[str]] | None:
    """Check 2 (software-dev): worktree currency + commit gates.

    Returns ``None`` to signal "fall through to the final success result"
    (e.g. planning-artifact repo_root WP, or the worktree does not exist).
    Returns ``(True, [])`` for the early repo_root short-circuit, and
    ``(False, guidance)`` for any blocking gate.
    """
    # Planning-artifact WPs run in the repo root and have no separate worktree
    # to validate. We only short-circuit on planning-artifact mode when the
    # canonical resolver succeeds; if the WP has no on-disk markdown file (e.g.
    # in tests that mock surrounding state), fall through to the legacy
    # worktree-existence checks below rather than hard-failing.
    workspace: ResolvedWorkspace | None
    try:
        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)
    except (ValueError, FileNotFoundError):
        workspace = None

    if workspace is not None and workspace.resolution_kind == "repo_root":
        return True, []

    worktree_path = _resolve_worktree_path(
        main_repo_root=main_repo_root,
        mission_slug=mission_slug,
        workspace=workspace,
    )

    if not worktree_path.exists():
        return None

    health = _check_worktree_health(worktree_path, wp_id, target_lane)
    if health is not None:
        return False, health

    # Check if the lane worktree is behind the branch it is expected to
    # track. In the lane-only model this is usually the mission branch.
    target_branch = get_feature_target_branch(repo_root, mission_slug)

    check_branch = review_currency_check_branch(
        main_repo_root=main_repo_root,
        mission_slug=mission_slug,
        target_branch=target_branch,
        workspace=workspace,
    )

    currency = _check_branch_currency(
        worktree_path=worktree_path,
        check_branch=check_branch,
        mission_slug=mission_slug,
        wp_id=wp_id,
        target_lane=target_lane,
        behind_commits_touch_only_planning_artifacts=behind_commits_touch_only_planning_artifacts,
    )
    if currency is not None:
        return False, currency

    uncommitted = _check_uncommitted_worktree_changes(
        worktree_path=worktree_path,
        wp_id=wp_id,
        target_lane=target_lane,
        filter_runtime_state_paths=filter_runtime_state_paths,
    )
    if uncommitted is not None:
        return False, uncommitted

    no_commit = _check_implementation_commit_present(
        worktree_path=worktree_path,
        check_branch=check_branch,
        wp_id=wp_id,
        target_lane=target_lane,
    )
    if no_commit is not None:
        return False, no_commit

    contamination = _check_kitty_specs_contamination(
        worktree_path=worktree_path,
        check_branch=check_branch,
        feature_dir=feature_dir,
        wp_id=wp_id,
        target_lane=target_lane,
        list_wp_branch_specs_changes_for_guard=list_wp_branch_specs_changes_for_guard,
    )
    if contamination is not None:
        return False, contamination

    return None


def _validate_ready_for_review(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    force: bool,
    target_lane: str = "for_review",
    *,
    get_main_repo_root: Callable[[Path], Path],
    get_mission_type: Callable[[Path], str],
    get_feature_target_branch: Callable[[Path, str], str],
    resolve_workspace_for_wp: Callable[[Path, str, str], ResolvedWorkspace],
    review_currency_check_branch: Callable[..., str],
    behind_commits_touch_only_planning_artifacts: Callable[[Path, str, str], bool],
    filter_runtime_state_paths: Callable[[str], str],
    list_wp_branch_specs_changes_for_guard: Callable[..., list[str]],
    console: _ConsoleLike,
) -> tuple[bool, list[str]]:
    """Validate that WP is ready for review by checking for uncommitted changes.

    For research missions: Checks for uncommitted research artifacts in planning repo.
    For software-dev missions: Checks for uncommitted changes in worktree AND
    verifies at least one implementation commit exists.

    The ``tasks``-resident collaborators are injected so that the existing
    monkeypatch contracts on the ``tasks`` namespace continue to apply; the
    thin ``tasks.py`` wrapper binds them to its live (patchable) globals.

    Args:
        repo_root: Repository root path (could be main or worktree)
        mission_slug: Feature slug (e.g., "010-lane-only-runtime")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, skip validation (return success)
        target_lane: Lane the caller is transitioning to. Used to parameterize
            the retry hints emitted in guidance messages (FR-015) so reviewers
            transitioning to ``approved``/``planned`` see the correct retry
            command instead of a hard-coded ``for_review`` string.

    Returns:
        Tuple of (is_valid, guidance_messages)
        - is_valid: True if ready for review, False if blocked
        - guidance_messages: List of actionable instructions if blocked
    """
    if force:
        return True, []

    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = get_main_repo_root(repo_root)
    # WP06 / FR-006 / T027: route research-artifact read to PRIMARY-partition seam.
    # research.md / meta.json / spec.md all live on PRIMARY (not the coord husk).
    # resolve_feature_dir_for_mission (coord-aware) would return the STATUS-only
    # coord husk for coord-topology missions, where these planning artifacts are absent.
    from mission_runtime import MissionArtifactKind  # late import — keeps cold-start cost low

    feature_dir = resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.RESEARCH
    )

    # Detect mission type from feature's meta.json
    mission_type = get_mission_type(feature_dir)

    # Check 1: Uncommitted research artifacts in planning repo (applies to ALL missions)
    # Research artifacts live in kitty-specs/ which is in the planning repo, not worktrees
    research_guidance = _validate_research_artifacts(
        main_repo_root=main_repo_root,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        mission_type=mission_type,
        target_lane=target_lane,
        console=console,
    )
    if research_guidance is not None:
        return False, research_guidance

    # Check 2: For software-dev missions, check worktree for implementation commits
    if mission_type == MISSION_TYPE_SOFTWARE_DEV:
        worktree_result = _validate_worktree_state(
            repo_root=repo_root,
            main_repo_root=main_repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            target_lane=target_lane,
            resolve_workspace_for_wp=resolve_workspace_for_wp,
            get_feature_target_branch=get_feature_target_branch,
            review_currency_check_branch=review_currency_check_branch,
            behind_commits_touch_only_planning_artifacts=behind_commits_touch_only_planning_artifacts,
            filter_runtime_state_paths=filter_runtime_state_paths,
            list_wp_branch_specs_changes_for_guard=list_wp_branch_specs_changes_for_guard,
        )
        if worktree_result is not None:
            return worktree_result

    return True, []


__all__ = [
    "_apply_review_status_flags",
    # _check_branch_currency, _check_implementation_commit_present,
    # _check_kitty_specs_contamination, _check_uncommitted_worktree_changes,
    # _check_worktree_health, _issue_matrix_diagnostic_lines,
    # _issue_matrix_evaluation, _issue_matrix_in_mission_rows,
    # _issue_matrix_row_issues, _latest_status_event_time,
    # _primary_issue_matrix_satisfies:
    # demoted — no cross-module src/ callers (WP01 harden-dead-symbol-gate).
    # _review_artifact_dir_for_wp, _review_cycle_number,
    # _validate_research_artifacts, _validate_worktree_state:
    # demoted — no cross-module src/ callers (WP01 harden-dead-symbol-gate).
    "_get_latest_review_cycle_verdict",
    "_issue_matrix_approval_blocker",
    "_self_review_fallback_option_error",
    "_validate_ready_for_review",
]
