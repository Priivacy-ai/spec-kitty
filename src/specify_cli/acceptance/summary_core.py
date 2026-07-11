#!/usr/bin/env python3
"""Pure helpers backing ``acceptance.collect_feature_summary`` (CC25).

WP04 (coord-authority-trio-degod-01KX7094) / T021: extracted from
``acceptance/__init__.py`` to bring ``collect_feature_summary`` and
``_build_recommended_fix_order`` under the S3776 <=15 complexity gate. Every
function here is a deterministic transform over already-resolved inputs (a
``WorkPackage``, a lane snapshot, an already-loaded ``mission`` object, or
plain lists/dicts) — no filesystem or git I/O of its own. The orchestrator
(``acceptance.collect_feature_summary``) stays responsible for resolving
directories, iterating work packages, and calling into the seam; it delegates
the per-WP state/metadata-issue computation, the mission path-convention
evaluation, and the final recommendation ordering to the functions below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specify_cli.mission import get_deliverables_path
from specify_cli.task_utils import WorkPackage
from specify_cli.validators.paths import validate_mission_paths

from .gates_core import AcceptanceCheckDiagnostic

# The active-work lanes: a WP in one of these is still in flight, so the
# strict-metadata gate requires the active-phase artifacts (``assignee`` and the
# live-shell ``shell_pid``). A terminal (done/approved) WP is exempt — the
# ``assignee`` and ``shell_pid`` gates key on exactly this set (#2369).
_ACTIVE_METADATA_LANES = frozenset({"doing", "in_progress", "for_review"})

_PATH_CONVENTIONS_NOT_SATISFIED = "Path conventions not satisfied."


@dataclass
class WorkPackageState:
    work_package_id: str
    lane: str
    title: str
    path: str
    has_lane_entry: bool
    latest_lane: str | None
    metadata: dict[str, str | None] = field(default_factory=dict)


def build_work_package_state(
    wp: WorkPackage,
    wp_id: str,
    canonical_lane: str | None,
    *,
    repo_root: Path,
    strict_metadata: bool,
) -> tuple[WorkPackageState, list[str]]:
    """Pure: build one WP's summary state + its metadata-gate issues.

    ``wp`` and ``canonical_lane`` are already-resolved inputs (``canonical_lane``
    comes from the status-event snapshot, looked up by the caller); this
    function does no I/O of its own. Mirrors the exact bucketing/metadata-issue
    logic ``collect_feature_summary`` used to run inline in its WP loop.
    """
    title = (wp.title or "").strip('"')
    bucket_lane = canonical_lane if canonical_lane is not None else "planned"
    metadata: dict[str, str | None] = {
        "lane": canonical_lane,
        "agent": wp.agent,
        "assignee": wp.assignee,
        "shell_pid": wp.shell_pid,
    }

    metadata_issues: list[str] = []
    if strict_metadata:
        if not wp.agent:
            metadata_issues.append(f"{wp_id}: missing agent in frontmatter")
        # ``shell_pid`` identifies the live interactive shell that claimed a WP
        # in ``spec-kitty next`` — an artifact of the ACTIVE-work phase, and one
        # the orchestrator executor never stamps. Require it (and ``assignee``)
        # only for active lanes: a terminal (done/approved) WP has no live
        # shell, so demanding it there is a false positive that blocks every
        # orchestrator-completed mission from passing accept (#2369).
        if canonical_lane in _ACTIVE_METADATA_LANES and not wp.assignee:
            metadata_issues.append(f"{wp_id}: missing assignee in frontmatter")
        if canonical_lane in _ACTIVE_METADATA_LANES and not wp.shell_pid:
            metadata_issues.append(f"{wp_id}: missing shell_pid in frontmatter")

    state = WorkPackageState(
        work_package_id=wp_id,
        lane=bucket_lane,
        title=title,
        path=str(wp.path.relative_to(repo_root)),
        has_lane_entry=canonical_lane is not None,
        latest_lane=canonical_lane,
        metadata=metadata,
    )
    return state, metadata_issues


def _path_prefix_for_mission(mission: Any, feature_dir: Path) -> str | None:
    if getattr(mission, "domain", None) != "research":
        return None
    return get_deliverables_path(feature_dir, mission_slug=feature_dir.name)


def evaluate_path_conventions(
    mission: Any,
    repo_root: Path,
    feature_dir: Path,
    planning_read_dir: Path,
    *,
    strict_metadata: bool,
) -> tuple[list[str], str | None]:
    """Evaluate mission path conventions; returns (path_violations, warning).

    Mission path conventions block acceptance by default, but under
    ``--lenient`` (``strict_metadata=False``) they are advisory: surfaced as a
    non-blocking warning instead of a hard ``path_violations`` entry so repos
    with a non-default layout (e.g. a Go service using ``internal/`` with no
    top-level ``tests/``) can be accepted with ``accept --lenient`` rather than
    the empty-directory workaround (issue #1892). ``validate_mission_paths`` is
    invoked non-strict here so the caller owns the blocking decision rather
    than catching a raise. When ``mission`` has no path conventions this is a
    no-op: ``([], None)``.
    """
    if not (mission and mission.config.paths):
        return [], None

    # Mission-artifact paths (e.g. ``contracts/``) live on the PRIMARY mission
    # surface, not the repo root — resolve them via the canonical
    # ``planning_read_dir`` seam (same surface ``_missing_artifacts`` uses),
    # never ``repo_root`` (#2115 / #1716 residual). Build paths stay repo-root.
    path_result = validate_mission_paths(
        mission,
        repo_root,
        strict=False,
        path_prefix=_path_prefix_for_mission(mission, feature_dir),
        feature_dir=planning_read_dir,
    )
    if not path_result.missing_paths:
        return [], None
    if strict_metadata:
        return [path_result.format_errors() or _PATH_CONVENTIONS_NOT_SATISFIED], None
    return [], path_result.format_warnings() or _PATH_CONVENTIONS_NOT_SATISFIED


def build_warnings(
    *,
    missing_optional: list[str],
    path_violations: list[str],
    path_convention_warning: str | None,
) -> list[str]:
    """Pure: assemble the summary's non-blocking warnings list."""
    warnings: list[str] = []
    if missing_optional:
        warnings.append("Optional artifacts missing: " + ", ".join(missing_optional))
    if path_violations:
        warnings.append(_PATH_CONVENTIONS_NOT_SATISFIED)
    elif path_convention_warning:
        warnings.append(path_convention_warning)
    return warnings


def _has_blocked_check(blocked_checks: list[AcceptanceCheckDiagnostic], check: str) -> bool:
    return any(item.check == check for item in blocked_checks)


def _has_non_terminal_lane(lanes: dict[str, list[str]]) -> bool:
    return any(wp_ids for lane, wp_ids in lanes.items() if lane not in {"approved", "done"})


def _has_issue_containing(issues: list[str], needle: str) -> bool:
    return any(needle in issue for issue in issues)


def _build_recommended_fix_order(
    *,
    lanes: dict[str, list[str]],
    metadata_issues: list[str],
    activity_issues: list[str],
    unchecked_tasks: list[str],
    needs_clarification: list[str],
    missing_artifacts: list[str],
    git_dirty: list[str],
    path_violations: list[str],
    blocked_checks: list[AcceptanceCheckDiagnostic],
) -> list[str]:
    """Pure: each independent trigger contributes exactly one message, in this
    fixed order, regardless of which inputs the caller happened to populate."""
    checks: list[tuple[bool, str]] = [
        (bool(git_dirty), "Commit, stash, or discard working tree changes before acceptance."),
        (
            _has_blocked_check(blocked_checks, "mission_branch"),
            "Switch to the mission branch or configured target branch named in the branch failure.",
        ),
        (bool(missing_artifacts), "Restore required mission artifacts before acceptance."),
        (bool(metadata_issues), "Fix work-package metadata issues."),
        (_has_non_terminal_lane(lanes), "Move all work packages to approved or done."),
        (bool(unchecked_tasks), "Complete unchecked items in tasks.md."),
        (bool(needs_clarification), "Resolve open NEEDS CLARIFICATION markers."),
        (
            _has_blocked_check(blocked_checks, "acceptance_matrix"),
            "Create or restore kitty-specs/<mission>/acceptance-matrix.json.",
        ),
        (
            _has_blocked_check(blocked_checks, "lanes_manifest"),
            "Restore or regenerate kitty-specs/<mission>/lanes.json.",
        ),
        (
            _has_issue_containing(activity_issues, "Evidence:"),
            "Fill missing acceptance matrix evidence fields.",
        ),
        (
            _has_issue_containing(activity_issues, "Acceptance matrix verdict is"),
            "Resolve pending or failing acceptance matrix criteria and negative invariants.",
        ),
        (
            _has_issue_containing(activity_issues, "Workflow run evidence required"),
            "Add successful GitHub Actions run evidence for workflow changes.",
        ),
        (bool(path_violations), "Fix mission path convention violations."),
    ]
    return [message for triggered, message in checks if triggered]


__all__: list[str] = []
