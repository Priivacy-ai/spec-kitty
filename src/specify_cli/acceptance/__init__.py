#!/usr/bin/env python3
"""Acceptance workflow utilities for Spec Kitty missions."""

from __future__ import annotations

from specify_cli.missions._read_path_resolver import (
    primary_feature_dir_for_mission,
    resolve_feature_dir_for_mission,
)
import logging
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specify_cli.core.agent_config import get_auto_commit_default
from specify_cli.core.paths import require_explicit_feature as _require_explicit_feature
from specify_cli.decisions.models import DecisionStatus
from specify_cli.decisions.store import load_index
from specify_cli.mission import MissionError, get_deliverables_path, get_mission_for_feature
from specify_cli.mission_metadata import load_meta, record_acceptance, resolve_mission_identity, write_meta
from specify_cli.status import CanonicalStatusNotFoundError
from specify_cli.status import Lane
from specify_cli.status import EVENTS_FILENAME, StoreError
from specify_cli.validators.paths import validate_mission_paths

from specify_cli.task_utils import (
    LANES,
    TaskCliError,
    WorkPackage,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    run_git,
    split_frontmatter,
)

logger = logging.getLogger(__name__)

AcceptanceMode = str  # Expected values: "pr", "local", "checklist"

SPEC_FILE = "spec.md"
PLAN_FILE = "plan.md"
TASKS_FILE = "tasks.md"
QUICKSTART_FILE = "quickstart.md"
DATA_MODEL_FILE = "data-model.md"
RESEARCH_FILE = "research.md"
WORKFLOW_EVIDENCE_FILE = "workflow-evidence.md"
WORKFLOW_RUN_URL_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/actions/runs/\d+\b")
PRIMARY_ARTIFACT_FILES = (
    SPEC_FILE,
    PLAN_FILE,
    QUICKSTART_FILE,
    TASKS_FILE,
    RESEARCH_FILE,
    DATA_MODEL_FILE,
)

_DECISION_ID_MARKER = "decision_id:"
_ACCEPTED_READY_LANES = frozenset({"approved", "done"})
_PATH_CONVENTIONS_NOT_SATISFIED = "Path conventions not satisfied."

# Paths written by the accept pipeline itself.  These must be excluded from the
# git-dirty gate so that a second accept run on unchanged mission state produces
# the same pass/fail verdict as the first (convergence / idempotency guarantee).
# ``status.json`` is a daemon-materialized view; ``acceptance-matrix.json`` is
# written by ``_check_lane_gates`` when ``mutate_matrix=True``.
ACCEPT_OWNED_PATHS = frozenset(
    {
        "acceptance-matrix.json",
        "status.json",
    }
)
_LEGACY_NOT_DONE_LANES = ("planned", "claimed", "doing", "in_progress", "for_review")
_ACTIONABLE_LANE_BLOCKER_HINTS = {
    "in_review": "review is still in progress; complete the review and move the work package to approved or done",
    "blocked": "work package is blocked; resolve the blocker and move the work package to approved or done",
    "canceled": "work package is canceled; reopen or replace it, then move the work package to approved or done",
}


def _porcelain_dirty_path(line: str) -> str:
    """Return the path component from a git porcelain v1 status line."""
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def _accept_owned_dirty_paths(repo_root: Path, *feature_dirs: Path) -> set[str]:
    """Return repo-relative accept-owned paths for the current mission only."""
    owned: set[str] = set()
    for feature_dir in feature_dirs:
        try:
            feature_rel = feature_dir.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            continue
        for filename in ACCEPT_OWNED_PATHS:
            owned.add(f"{feature_rel}/{filename}")
    return owned


def _mission_routes_through_coordination(repo_root: Path, feature: str) -> bool:
    """True when ``feature`` routes through coordination under its STORED topology.

    FR-008 / FR-005: the accept dirty-tree gate is topology-aware. Read the WP02
    **stored** :class:`MissionTopology` via :func:`resolve_topology` and ask the
    ONE canonical :func:`routes_through_coordination` predicate — never the
    retired per-ref ``.kind`` arm (the predicate takes a ``MissionTopology``, not
    a ``CommitTarget``; passing a placement ref made it always-``False`` and
    silently disabled the residue filter). Under coordination topology the
    recognized coordination residue on the primary checkout is dropped from the
    dirty set; under a flat (``single_branch`` / ``lanes``) topology the predicate
    is ``False`` so the residue filter never runs and a flat mission's real
    primary artifacts STILL block.

    An unresolvable handle degrades to a non-coordination shape (fail-closed /
    conservative: the full dirty set is preserved, never widening the gate on a
    resolution edge case — NFR-003 / C-004), exactly as the canonical
    ``cli/commands/agent/mission.py`` routing site relies on.
    """
    from mission_runtime import resolve_topology, routes_through_coordination

    return routes_through_coordination(resolve_topology(repo_root, feature))


def _accept_dirty_gate(
    git_dirty_raw: list[str],
    *,
    repo_root: Path,
    feature: str,
    feature_dir: Path,
    read_feature_dir: Path,
    status_feature_dir: Path,
) -> list[str]:
    """Compute the accept dirty set: accept-owned exclusion + FR-008 coord residue.

    Two filters compose:

    1. **Accept-owned convergence (#1883):** the accept gate's own writes
       (``acceptance-matrix.json`` + ``status.json``) are scoped to this
       mission's primary anchor dir, the coord-aware read dir, and the canonical
       status-read dir. Excluding all three absorbs accept-owned residue left
       dirty by a prior ``--no-commit`` / diagnose run, so ``accept ∘ accept``
       converges in every mode.
    2. **FR-008 topology-aware residue:** under coordination topology the
       recognized coordination residue (stale primary copies of artifacts owned
       by the coordination branch) is excluded via the SAME per-ref pattern the
       record-analysis preflight uses (:func:`routes_through_coordination` + the
       WP04 :func:`is_coordination_artifact_residue_path` predicate). A flat
       mission routes through PRIMARY, so its real primary artifacts STILL block.
       ``ACCEPT_OWNED_PATHS`` is NOT widened.

    Non-accept-owned, non-residue dirt is preserved verbatim (fail-closed,
    NFR-003).
    """
    accept_owned_dirty_paths = _accept_owned_dirty_paths(
        repo_root,
        feature_dir,
        read_feature_dir,
        status_feature_dir,
    )
    git_dirty = [
        line
        for line in git_dirty_raw
        if _porcelain_dirty_path(line) not in accept_owned_dirty_paths
    ]
    return _filter_coordination_residue(git_dirty, repo_root=repo_root, feature=feature)


def _filter_coordination_residue(
    dirty_lines: list[str],
    *,
    repo_root: Path,
    feature: str,
) -> list[str]:
    """Drop coordination-residue dirty lines when the mission routes through coord.

    FR-008 convergence on the ``mission.py`` reference pattern: only when
    :func:`routes_through_coordination` holds does
    :func:`is_coordination_artifact_residue_path` (the WP04 stored-topology
    residue authority — flat→``False``) get to exclude a path. The predicate is
    NOT a widening of ``ACCEPT_OWNED_PATHS``: it is the per-ref coordination gate
    applied to recognized coordination-owned artifacts (spec / plan / tasks /
    lanes / status / matrices / checklists) left stale on the primary checkout.
    Real source edits, unknown mission scratch files, and another mission's
    artifacts are not recognized residue, so they still block.
    """
    from mission_runtime import is_coordination_artifact_residue_path

    if not _mission_routes_through_coordination(repo_root, feature):
        return dirty_lines
    return [
        line
        for line in dirty_lines
        if not is_coordination_artifact_residue_path(
            _porcelain_dirty_path(line), mission_slug=feature
        )
    ]


class AcceptanceError(TaskCliError):
    """Raised when acceptance cannot complete due to outstanding issues."""


class ArtifactEncodingError(AcceptanceError):
    """Raised when a project artifact cannot be decoded as UTF-8."""

    def __init__(self, path: Path, error: UnicodeDecodeError):
        byte = error.object[error.start : error.start + 1]
        byte_display = f"0x{byte[0]:02x}" if byte else "unknown"
        message = f"Invalid UTF-8 encoding in {path}: byte {byte_display} at offset {error.start}. Run with --normalize-encoding to fix automatically."
        super().__init__(message)
        self.path = path
        self.error = error


@dataclass
class WorkPackageState:
    work_package_id: str
    lane: str
    title: str
    path: str
    has_lane_entry: bool
    latest_lane: str | None
    metadata: dict[str, str | None] = field(default_factory=dict)


@dataclass
class AcceptanceCheckDiagnostic:
    check: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"check": self.check, "detail": self.detail}


def _format_lane_blocker(lane: str, wp_id: str) -> str:
    hint = _ACTIONABLE_LANE_BLOCKER_HINTS.get(lane)
    if hint is None:
        hint = "move the work package to approved or done"
    return f"{wp_id}: canonical lane is '{lane}'; {hint}."


@dataclass
class AcceptanceSummary:
    feature: str
    repo_root: Path
    feature_dir: Path
    tasks_dir: Path
    branch: str | None
    worktree_root: Path
    primary_repo_root: Path
    lanes: dict[str, list[str]]
    work_packages: list[WorkPackageState]
    metadata_issues: list[str]
    activity_issues: list[str]
    unchecked_tasks: list[str]
    needs_clarification: list[str]
    missing_artifacts: list[str]
    optional_missing: list[str]
    git_dirty: list[str]
    path_violations: list[str]
    warnings: list[str]
    skipped_checks: list[AcceptanceCheckDiagnostic] = field(default_factory=list)
    blocked_checks: list[AcceptanceCheckDiagnostic] = field(default_factory=list)
    recommended_fix_order: list[str] = field(default_factory=list)

    @property
    def all_done(self) -> bool:
        """True when all WPs are approved or done (no WPs still in progress or review)."""
        return not any(wp_ids for lane, wp_ids in self.lanes.items() if lane not in _ACCEPTED_READY_LANES)

    @property
    def ok(self) -> bool:
        return (
            self.all_done
            and not self.metadata_issues
            and not self.activity_issues
            and not self.unchecked_tasks
            and not self.needs_clarification
            and not self.missing_artifacts
            and not self.git_dirty
            and not self.path_violations
        )

    def outstanding(self) -> dict[str, list[str]]:
        buckets = {
            "not_done": [
                *(wp_id for lane in _LEGACY_NOT_DONE_LANES for wp_id in self.lanes.get(lane, [])),
            ],
            "lane_blockers": [
                _format_lane_blocker(lane, wp_id)
                for lane in _ACTIONABLE_LANE_BLOCKER_HINTS
                for wp_id in self.lanes.get(lane, [])
            ],
            "metadata": self.metadata_issues,
            "activity": self.activity_issues,
            "unchecked_tasks": self.unchecked_tasks,
            "needs_clarification": self.needs_clarification,
            "missing_artifacts": self.missing_artifacts,
            "git_dirty": self.git_dirty,
            "path_violations": self.path_violations,
        }
        return {key: value for key, value in buckets.items() if value}

    def failed_checks(self) -> list[AcceptanceCheckDiagnostic]:
        return [
            AcceptanceCheckDiagnostic(check=check, detail=detail)
            for check, details in self.outstanding().items()
            for detail in details
        ]

    def to_dict(self) -> dict[str, object]:
        identity = resolve_mission_identity(self.feature_dir)
        return {
            "mission_slug": identity.mission_slug,
            "mission_number": identity.mission_number,
            "mission_type": identity.mission_type,
            "branch": self.branch,
            "repo_root": str(self.repo_root),
            "feature_dir": str(self.feature_dir),
            "tasks_dir": str(self.tasks_dir),
            "worktree_root": str(self.worktree_root),
            "primary_repo_root": str(self.primary_repo_root),
            "lanes": self.lanes,
            "work_packages": [
                {
                    "id": wp.work_package_id,
                    "lane": wp.lane,
                    "title": wp.title,
                    "path": wp.path,
                    "latest_lane": wp.latest_lane,
                    "has_lane_entry": wp.has_lane_entry,
                    "metadata": wp.metadata,
                }
                for wp in self.work_packages
            ],
            "metadata_issues": self.metadata_issues,
            "activity_issues": self.activity_issues,
            "unchecked_tasks": self.unchecked_tasks,
            "needs_clarification": self.needs_clarification,
            "missing_artifacts": self.missing_artifacts,
            "optional_missing": self.optional_missing,
            "git_dirty": self.git_dirty,
            "path_violations": self.path_violations,
            "warnings": self.warnings,
            "failed_checks": [item.to_dict() for item in self.failed_checks()],
            "skipped_checks": [item.to_dict() for item in self.skipped_checks],
            "blocked_checks": [item.to_dict() for item in self.blocked_checks],
            "recommended_fix_order": self.recommended_fix_order,
            "all_done": self.all_done,
            "ok": self.ok,
        }


@dataclass
class AcceptanceResult:
    summary: AcceptanceSummary
    mode: AcceptanceMode
    accepted_at: str
    accepted_by: str
    parent_commit: str | None
    accept_commit: str | None
    commit_created: bool
    instructions: list[str]
    cleanup_instructions: list[str]
    notes: list[str] = field(default_factory=list)
    accepted_wps: list[str] = field(default_factory=list)
    approved_wps: list[str] = field(default_factory=list)
    done_wps: list[str] = field(default_factory=list)
    merge_pending_wps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted_at": self.accepted_at,
            "accepted_by": self.accepted_by,
            "mode": self.mode,
            "parent_commit": self.parent_commit,
            "accept_commit": self.accept_commit,
            "commit_created": self.commit_created,
            "instructions": self.instructions,
            "cleanup_instructions": self.cleanup_instructions,
            "notes": self.notes,
            "accepted_wps": self.accepted_wps,
            "approved_wps": self.approved_wps,
            "done_wps": self.done_wps,
            "merge_pending_wps": self.merge_pending_wps,
            "summary": self.summary.to_dict(),
        }


def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    """Iterate over work packages, supporting both legacy and new formats.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    # WORK_PACKAGE_TASK is a PRIMARY-partition kind: route the WP-task read
    # through the kind-aware seam so a coord-topology mission reads its tasks off
    # the PRIMARY surface (where they live), not the materialized -coord husk
    # whose tasks/ dir is absent (closeout N+1 — debbie §3).
    feature_path = _wp_tasks_read_dir(repo_root, feature)
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        raise AcceptanceError(f"Feature '{feature}' has no tasks directory at {tasks_dir}.")

    use_legacy = is_legacy_format(feature_path)

    if use_legacy:
        # Legacy format: iterate over lane subdirectories
        for lane_dir in sorted(tasks_dir.iterdir()):
            if not lane_dir.is_dir():
                continue
            lane = lane_dir.name
            if lane not in LANES:
                continue
            for path in sorted(lane_dir.rglob("*.md")):
                text = _read_text_strict(path)
                front, body, padding = split_frontmatter(text)
                relative = path.relative_to(lane_dir)
                yield WorkPackage(
                    feature=feature,
                    path=path,
                    current_lane=lane,
                    relative_subpath=relative,
                    frontmatter=front,
                    body=body,
                    padding=padding,
                )
    else:
        # New format: flat tasks/ directory, lane from frontmatter
        for path in sorted(tasks_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            text = _read_text_strict(path)
            front, body, padding = split_frontmatter(text)
            try:
                lane = get_lane_from_frontmatter(path, warn_on_missing=False)
            except CanonicalStatusNotFoundError:
                lane = "uninitialized"
            relative = path.relative_to(tasks_dir)
            yield WorkPackage(
                feature=feature,
                path=path,
                current_lane=lane,
                relative_subpath=relative,
                frontmatter=front,
                body=body,
                padding=padding,
            )


def detect_mission_slug(
    repo_root: Path,
    *,
    explicit_feature: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    announce_fallback: bool = True,
) -> str:
    """Require an explicit mission slug; no auto-detection.

    Args:
        repo_root: Repository root path (unused — kept for signature compatibility)
        explicit_feature: Mission slug to use (required).
        env: Unused; kept for backward-compatible call sites.
        cwd: Unused; kept for backward-compatible call sites.
        announce_fallback: Unused; kept for backward-compatible call sites.

    Returns:
        Mission slug (e.g., "020-my-feature")

    Raises:
        AcceptanceError: If no explicit feature slug is provided.
    """
    _ = (repo_root, env, cwd, announce_fallback)
    try:
        return _require_explicit_feature(explicit_feature, command_hint="--mission <slug>")
    except ValueError as e:
        raise AcceptanceError(str(e)) from e


def _read_text_strict(path: Path) -> str:
    """Read a file as UTF-8, raising ArtifactEncodingError on decode failure."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactEncodingError(path, exc) from exc


def _read_file(path: Path) -> str:
    return _read_text_strict(path) if path.exists() else ""


def _find_unchecked_tasks(tasks_file: Path) -> list[str]:
    if not tasks_file.exists():
        return [f"{TASKS_FILE} missing"]

    unchecked: list[str] = []
    for line in _read_text_strict(tasks_file).splitlines():
        if re.match(r"^\s*-\s*\[ \]", line):
            unchecked.append(line.strip())
    return unchecked


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
    if unchecked_tasks == [f"{TASKS_FILE} missing"]:
        return []
    if _all_work_packages_terminal(lanes):
        return []
    return unchecked_tasks


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


def _check_needs_clarification(files: Sequence[Path]) -> list[str]:
    results: list[str] = []
    for file_path in files:
        if file_path.exists():
            text = _read_text_strict(file_path)
            if _has_blocking_clarification_marker(file_path, text):
                results.append(str(file_path))
    return results


def _has_blocking_clarification_marker(file_path: Path, text: str) -> bool:
    markers = list(_iter_clarification_decision_ids(text))
    if not markers:
        return False

    index = load_index(file_path.parent)
    entries_by_id = {entry.decision_id: entry for entry in index.entries}
    for decision_id in markers:
        entry = entries_by_id.get(decision_id)
        if entry is None or entry.status in {DecisionStatus.OPEN, DecisionStatus.DEFERRED}:
            return True
    return False


def _iter_clarification_decision_ids(text: str) -> Iterable[str]:
    for line in text.splitlines():
        marker_start = line.find("[NEEDS CLARIFICATION:")
        if marker_start == -1:
            continue
        marker_end = line.find("]", marker_start)
        if marker_end == -1:
            continue
        comment_start = line.find("<!--", marker_end)
        if comment_start == -1:
            continue
        comment_end = line.find("-->", comment_start + 4)
        if comment_end == -1:
            continue
        comment_body = line[comment_start + 4 : comment_end]
        decision_id_index = comment_body.find(_DECISION_ID_MARKER)
        if decision_id_index == -1:
            continue
        decision_id_text = comment_body[decision_id_index + len(_DECISION_ID_MARKER) :].strip()
        if decision_id_text:
            yield decision_id_text.split(maxsplit=1)[0]


def _missing_artifacts(feature_dir: Path) -> tuple[list[str], list[str]]:
    required = [feature_dir / SPEC_FILE, feature_dir / PLAN_FILE, feature_dir / TASKS_FILE]
    optional = [
        feature_dir / QUICKSTART_FILE,
        feature_dir / DATA_MODEL_FILE,
        feature_dir / RESEARCH_FILE,
        feature_dir / "contracts",
    ]
    missing_required = [str(p.relative_to(feature_dir)) for p in required if not p.exists()]
    missing_optional = [str(p.relative_to(feature_dir)) for p in optional if not p.exists()]
    return missing_required, missing_optional


def normalize_feature_encoding(repo_root: Path, feature: str) -> list[Path]:
    """Normalize file encoding from Windows-1252 to UTF-8 with ASCII character mapping.

    Converts Windows-1252 encoded files to UTF-8, replacing Unicode smart quotes
    and special characters with ASCII equivalents for maximum compatibility.
    """
    # Map Unicode characters to ASCII equivalents
    NORMALIZE_MAP = {
        "\u2018": "'",  # Left single quotation mark -> apostrophe
        "\u2019": "'",  # Right single quotation mark -> apostrophe
        "\u201a": "'",  # Single low-9 quotation mark -> apostrophe
        "\u201c": '"',  # Left double quotation mark -> straight quote
        "\u201d": '"',  # Right double quotation mark -> straight quote
        "\u201e": '"',  # Double low-9 quotation mark -> straight quote
        "\u2014": "--",  # Em dash -> double hyphen
        "\u2013": "-",  # En dash -> hyphen
        "\u2026": "...",  # Horizontal ellipsis -> three dots
        "\u00a0": " ",  # Non-breaking space -> regular space
        "\u2022": "*",  # Bullet -> asterisk
        "\u00b7": "*",  # Middle dot -> asterisk
    }

    # Every artifact this normalizer touches — the planning docs in
    # ``PRIMARY_ARTIFACT_FILES`` plus the ``tasks/`` (WORK_PACKAGE_TASK),
    # ``research/`` (RESEARCH) and ``checklists/`` (CHECKLIST) subtrees — is a
    # PRIMARY-partition kind, so the encoding-recovery scan must read the PRIMARY
    # surface, not the coord-aware husk. Pre-fix this used
    # ``resolve_feature_dir_for_mission`` (coord-aware); on a coord-topology
    # mission it scanned the materialized ``-coord`` worktree, missing the real
    # primary artifacts an encoding fault lives in (closeout N+1 sibling — debbie
    # §3). ``_planning_read_dir`` resolves the PRIMARY surface via the same
    # kind-aware seam; behavior-neutral for a FLATTENED mission.
    feature_dir = _planning_read_dir(repo_root, feature)
    if not feature_dir.exists():
        return []

    candidates: list[Path] = []
    primary_files = [feature_dir / artifact_name for artifact_name in PRIMARY_ARTIFACT_FILES]
    candidates.extend(p for p in primary_files if p.exists())

    for subdir in [feature_dir / "tasks", feature_dir / "research", feature_dir / "checklists"]:
        if subdir.exists():
            candidates.extend(path for path in subdir.rglob("*.md"))

    rewritten: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        data = path.read_bytes()
        try:
            data.decode("utf-8")
            continue
        except UnicodeDecodeError:
            pass

        text: str | None = None
        for encoding in ("cp1252", "latin-1"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = data.decode("utf-8", errors="replace")

        # Strip UTF-8 BOM if present in the text
        text = text.lstrip("\ufeff")

        # Normalize Unicode characters to ASCII equivalents
        for unicode_char, ascii_replacement in NORMALIZE_MAP.items():
            text = text.replace(unicode_char, ascii_replacement)

        path.write_text(text, encoding="utf-8")
        rewritten.append(path)

    return rewritten


def _resolve_git_context(repo_root: Path) -> tuple[str | None, Path, Path, list[str]]:
    """Collect branch, worktree root, primary repo root, and dirty files."""
    branch: str | None = None
    try:
        branch_value = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True).stdout.strip()
        if branch_value and branch_value != "HEAD":
            branch = branch_value
    except TaskCliError:
        pass

    try:
        worktree_root = Path(run_git(["rev-parse", "--show-toplevel"], cwd=repo_root, check=True).stdout.strip()).resolve()
    except TaskCliError:
        worktree_root = repo_root

    try:
        git_common_dir = Path(run_git(["rev-parse", "--git-common-dir"], cwd=repo_root, check=True).stdout.strip()).resolve()
        primary_repo_root = git_common_dir.parent
    except TaskCliError:
        primary_repo_root = repo_root

    try:
        git_dirty = git_status_lines(repo_root)
    except TaskCliError:
        git_dirty = []

    return branch, worktree_root, primary_repo_root, git_dirty


def _collect_snapshot_wps(feature: str, feature_dir: Path, activity_issues: list[str]) -> dict[str, dict[str, Any]]:
    """Load canonical WP states from status.events.jsonl; append issues on failure."""
    events_path = feature_dir / EVENTS_FILENAME
    _missing_msg = (
        f"No canonical state found for feature '{feature}'. "
        "Cannot validate acceptance without status.events.jsonl. "
        f"Run 'spec-kitty agent mission finalize-tasks --mission {feature}' to bootstrap the event log."
    )
    if not events_path.exists():
        activity_issues.append(_missing_msg)
        return {}
    try:
        from specify_cli.status import reduce
        from specify_cli.status import read_events

        snapshot = reduce(read_events(feature_dir))
    except StoreError as exc:
        raise AcceptanceError(f"Status event log is corrupted for feature '{feature}': {exc}") from exc
    if not snapshot.work_packages:
        activity_issues.append(_missing_msg)
    return snapshot.work_packages


def _status_read_feature_dir(repo_root: Path, feature: str, feature_dir: Path) -> Path:
    """Return canonical status read path for acceptance lane validation.

    Routes through the SINGLE guarded read-side seam
    (:func:`resolve_handle_to_read_path`, IC-01 / FR-001): the seam owns the
    primary-meta probe and the ONE sanctioned mid8 cascade
    (``meta.mid8`` → ``resolve_mid8(meta.mission_id)`` → ``mid8_from_slug``,
    NFR-005/#1868) internally, so this caller no longer derives the mid8 in
    parallel (WP01 reroute — byte-identical: the seam derives the same mid8 and
    forwards it to the existence-gated topology resolver with
    ``require_exists=False``).

    The acceptance-specific ``status_dir if status_dir.exists() else feature_dir``
    fallback is preserved verbatim: acceptance validation must stay LENIENT and
    degrade to the primary anchor dir rather than fail-close.
    """
    from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

    status_dir = resolve_handle_to_read_path(repo_root, feature)
    return status_dir if status_dir.exists() else feature_dir


# Planning artifacts the accept gate inspects, mapped to their canonical
# ``MissionArtifactKind`` (FR-002 / data-model.md site map rows 2-9). Every entry
# is a PRIMARY-partition kind (``is_primary_artifact_kind`` True), so each resolves
# the SAME primary feature dir through the WP01 read seam. ``quickstart.md`` carries
# no dedicated kind; it is a planning checklist doc and is classified ``CHECKLIST``
# (a PRIMARY-partition kind) explicitly here — no silent default (DECISION 1 spirit).
def _accept_planning_artifact_kinds() -> dict[str, Any]:
    from mission_runtime import MissionArtifactKind

    return {
        SPEC_FILE: MissionArtifactKind.SPEC,
        PLAN_FILE: MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
        TASKS_FILE: MissionArtifactKind.TASKS_INDEX,
        RESEARCH_FILE: MissionArtifactKind.RESEARCH,
        DATA_MODEL_FILE: MissionArtifactKind.DATA_MODEL,
        QUICKSTART_FILE: MissionArtifactKind.CHECKLIST,
    }


def _planning_read_dir(repo_root: Path, feature: str) -> Path:
    """Return the PRIMARY mission dir the accept gate reads planning artifacts from.

    FR-002 (#2085): the accept gate's PLANNING reads (spec/plan/tasks/research/
    data-model/quickstart) are split off the coord-aware ``status_feature_dir`` and
    routed onto the SINGLE kind-aware read seam
    (:func:`~specify_cli.missions._read_path_resolver.resolve_planning_read_dir`,
    WP01). Because every planning artifact the gate reads is a PRIMARY-partition
    kind, they all resolve the same primary feature dir; we resolve once (keyed on
    ``SPEC``) and the per-artifact existence checks reuse it. This is NOT a parallel
    resolver (C-001 forbids a NEW resolver, not consuming the existing one): it is a
    thin caller of the shared chokepoint, mirroring ``mission.py::_planning_read_dir``.

    The STATUS/acceptance reads (``status.events.jsonl``, acceptance-matrix) keep
    using ``status_feature_dir`` with its leniency (C-002) — they are NOT routed here.
    """
    from mission_runtime import is_primary_artifact_kind

    from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

    kinds = _accept_planning_artifact_kinds()
    # Guard the "resolve once and reuse" invariant: every planning artifact the gate
    # reads MUST be a PRIMARY-partition kind, so they all resolve the same primary
    # dir. If a future single-line reclassification in ``mission_runtime.artifacts``
    # moves one across the partition (NFR-004), fail LOUD here rather than silently
    # reading a stale coord surface for one artifact.
    non_primary = sorted(name for name, kind in kinds.items() if not is_primary_artifact_kind(kind))
    if non_primary:
        raise AcceptanceError(
            "Accept-gate planning split invariant violated: planning artifact(s) "
            f"{non_primary} are no longer PRIMARY-partition kinds; the per-artifact "
            "read dir must be resolved individually (FR-002 / data-model.md)."
        )
    # Explicit ``Path`` annotation: under the project's ``follow_imports = "skip"``
    # mypy config the cross-module ``resolve_planning_read_dir`` return is seen as
    # ``Any``; the annotation re-narrows it (the function IS typed ``-> Path``) so the
    # chokepoint return is not an ``Any`` leak — matching ``mission.py::_planning_read_dir``.
    read_dir: Path = resolve_planning_read_dir(repo_root, feature, kind=kinds[SPEC_FILE])
    return read_dir


def _wp_tasks_read_dir(repo_root: Path, feature: str) -> Path:
    """Return the PRIMARY mission dir the accept gate reads WP tasks from.

    Closeout N+1 (debbie §3): the accept gate's WP-task iteration
    (:func:`_iter_work_packages`) reads ``tasks/WP*.md`` — a
    ``WORK_PACKAGE_TASK`` artifact, a PRIMARY-partition kind. Pre-fix it resolved
    the coord-aware :func:`resolve_feature_dir_for_mission`, landing on the
    materialized ``-coord`` worktree whose ``tasks/`` directory is ABSENT (WP
    tasks live on PRIMARY for both read and write — INV-5 symmetry). The REAL
    accept gate then raised ``AcceptanceError: ... has no tasks directory`` for a
    coord-topology mission whose WP tasks live (correctly) only on primary.

    This routes the WP-task read through the SAME kind-aware chokepoint
    (:func:`~specify_cli.missions._read_path_resolver.resolve_planning_read_dir`)
    the planning-doc reads use, keyed on ``WORK_PACKAGE_TASK`` — mirroring the
    WP04 ``map-requirements`` fix (tasks.py: ``resolve_planning_read_dir`` for the
    WP-task glob). Behavior-neutral for a FLATTENED mission (candidate == primary).
    The STATUS reads stay on ``status_feature_dir`` (C-002), unchanged.
    """
    from mission_runtime import MissionArtifactKind, is_primary_artifact_kind

    from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

    # Fail LOUD if a future reclassification moves WORK_PACKAGE_TASK off the
    # primary partition (NFR-004): the gate's WP-task read must stay on the same
    # single primary surface as the WP-task write, never silently a coord husk.
    if not is_primary_artifact_kind(MissionArtifactKind.WORK_PACKAGE_TASK):
        raise AcceptanceError(
            "Accept-gate WP-task read invariant violated: WORK_PACKAGE_TASK is no "
            "longer a PRIMARY-partition kind; the WP-task read dir must be resolved "
            "against its current partition (closeout N+1 / data-model.md)."
        )
    read_dir: Path = resolve_planning_read_dir(
        repo_root, feature, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    return read_dir


def _primary_anchor_feature_dir(repo_root: Path, feature: str, read_dir: Path) -> Path:
    """Return the primary-checkout mission dir anchoring ``AcceptanceSummary``.

    ``resolve_feature_dir_for_mission`` hands back the coord-aware READ
    directory — the coordination worktree once one is materialized. The
    summary's identity anchor (``AcceptanceSummary.feature_dir``) must stay on
    the primary checkout (status source of truth is feature metadata on main:
    ``_commit_acceptance_meta`` records acceptance into the primary
    ``meta.json``), while artifact/status reads stay coord-aware through
    ``_status_read_feature_dir``.

    The primary dir name can differ from the read dir name — backfilled legacy
    missions carry no ``-<mid8>`` suffix on the primary side while their coord
    mission dir does — so the anchor is derived from the mission *handle*,
    never recomposed from the read dir's name:

    1. literal handle → primary composition (covers canonical ``<slug>-<mid8>``
       names AND backfilled legacy names);
    2. handle resolver (mid8 / ULID / numeric prefix / human slug) → the
       primary directory it indexed;
    3. fall back to the resolved read dir rather than fail when no
       primary-side directory exists (identity/existence was already validated
       by the read resolution).
    """
    primary_candidate: Path = primary_feature_dir_for_mission(repo_root, feature)
    if primary_candidate.exists():
        return primary_candidate

    from specify_cli.context.mission_resolver import (
        AmbiguousHandleError,
        MissionNotFoundError,
        resolve_mission,
    )

    try:
        resolved = resolve_mission(feature, repo_root)
    except (AmbiguousHandleError, MissionNotFoundError):
        return read_dir
    resolved_primary: Path = resolved.feature_dir
    if resolved_primary.exists():
        return resolved_primary
    return read_dir


def _validate_wp_readiness(
    expected_wp_ids: list[str],
    snapshot_wps: dict[str, dict[str, Any]],
    events_path: Path,
    activity_issues: list[str],
) -> None:
    """WPs must be in 'approved' or 'done' for acceptance."""
    if not (events_path.exists() and snapshot_wps):
        return
    for wp_id in expected_wp_ids:
        wp_snapshot = snapshot_wps.get(wp_id)
        if wp_snapshot is None:
            activity_issues.append(f"{wp_id}: no canonical state found in status.events.jsonl")
        elif wp_snapshot.get("lane") not in {Lane.APPROVED, Lane.DONE}:
            activity_issues.append(f"{wp_id}: canonical lane is '{wp_snapshot.get('lane')}', expected 'approved' or 'done'")


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


def _path_prefix_for_mission(mission: Any, feature_dir: Path) -> str | None:
    if getattr(mission, "domain", None) != "research":
        return None
    return get_deliverables_path(feature_dir, mission_slug=feature_dir.name)


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
    from specify_cli.lanes.compute import is_planning_artifact_only
    from specify_cli.lanes.persistence import CorruptLanesError, read_lanes_json

    try:
        lanes_manifest = read_lanes_json(feature_dir)
    except CorruptLanesError as exc:
        message = str(exc)
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="lanes_manifest", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="lanes.json is corrupt or malformed",
            include_matrix_presence=True,
        )
        return

    if lanes_manifest is None:
        return

    meta_target_branch = _target_branch_for_feature(feature_dir)
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
        return

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
        return

    if planning_artifact_only:
        _append_skipped_lane_checks(
            skipped_checks,
            reason="planning_artifact-only missions do not produce acceptance-matrix.json",
            include_matrix_presence=True,
        )
        return

    from specify_cli.acceptance.matrix import (
        enforce_negative_invariants,
        read_acceptance_matrix,
        validate_matrix_evidence,
        write_acceptance_matrix,
    )

    acc_matrix = read_acceptance_matrix(feature_dir)
    if acc_matrix is None:
        message = "Acceptance matrix (acceptance-matrix.json) is required for lane-based features but was not found"
        activity_issues.append(message)
        blocked_checks.append(AcceptanceCheckDiagnostic(check="acceptance_matrix", detail=message))
        _append_skipped_lane_checks(
            skipped_checks,
            reason="acceptance-matrix.json is missing",
        )
        return

    if acc_matrix.negative_invariants and mutate_matrix:
        acc_matrix.negative_invariants = enforce_negative_invariants(repo_root, acc_matrix.negative_invariants)
        write_acceptance_matrix(feature_dir, acc_matrix)
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


def _target_branch_for_feature(feature_dir: Path) -> str | None:
    meta = load_meta(feature_dir) or {}
    value = meta.get("target_branch")
    return str(value) if value else None


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    return run_git(["rev-parse", "--verify", "--quiet", ref], cwd=repo_root, check=False).returncode == 0


def _changed_workflow_files(repo_root: Path, feature_dir: Path, branch: str | None) -> list[str]:
    """Return workflow files changed by the current mission branch."""
    target_branch = _target_branch_for_feature(feature_dir)
    if not target_branch or branch == target_branch:
        return []

    base_ref = target_branch if _git_ref_exists(repo_root, target_branch) else f"origin/{target_branch}"
    if not _git_ref_exists(repo_root, base_ref):
        return []

    merge_base = run_git(["merge-base", "HEAD", base_ref], cwd=repo_root, check=False)
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        return []

    diff = run_git(
        [
            "diff",
            "--name-only",
            "--diff-filter=AMR",
            f"{merge_base.stdout.strip()}...HEAD",
            "--",
            ".github/workflows",
        ],
        cwd=repo_root,
        check=False,
    )
    if diff.returncode != 0:
        return []
    return sorted({line.strip() for line in diff.stdout.splitlines() if line.strip()})


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
    recommendations: list[str] = []

    if git_dirty:
        recommendations.append("Commit, stash, or discard working tree changes before acceptance.")
    if any(item.check == "mission_branch" for item in blocked_checks):
        recommendations.append("Switch to the mission branch or configured target branch named in the branch failure.")
    if missing_artifacts:
        recommendations.append("Restore required mission artifacts before acceptance.")
    if metadata_issues:
        recommendations.append("Fix work-package metadata issues.")
    if any(wp_ids for lane, wp_ids in lanes.items() if lane not in {"approved", "done"}):
        recommendations.append("Move all work packages to approved or done.")
    if unchecked_tasks:
        recommendations.append("Complete unchecked items in tasks.md.")
    if needs_clarification:
        recommendations.append("Resolve open NEEDS CLARIFICATION markers.")
    if any(item.check == "acceptance_matrix" for item in blocked_checks):
        recommendations.append("Create or restore kitty-specs/<mission>/acceptance-matrix.json.")
    if any(item.check == "lanes_manifest" for item in blocked_checks):
        recommendations.append("Restore or regenerate kitty-specs/<mission>/lanes.json.")
    if any("Evidence:" in issue for issue in activity_issues):
        recommendations.append("Fill missing acceptance matrix evidence fields.")
    if any("Acceptance matrix verdict is" in issue for issue in activity_issues):
        recommendations.append("Resolve pending or failing acceptance matrix criteria and negative invariants.")
    if any("Workflow run evidence required" in issue for issue in activity_issues):
        recommendations.append("Add successful GitHub Actions run evidence for workflow changes.")
    if path_violations:
        recommendations.append("Fix mission path convention violations.")

    return recommendations


def collect_feature_summary(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool = True,
    mutate_matrix: bool = True,
) -> AcceptanceSummary:
    read_feature_dir = resolve_feature_dir_for_mission(repo_root, feature)
    feature_dir = _primary_anchor_feature_dir(repo_root, feature, read_feature_dir)
    tasks_dir = feature_dir / "tasks"
    if not feature_dir.exists():
        raise AcceptanceError(f"Mission directory not found: {feature_dir}")

    branch, worktree_root, primary_repo_root, git_dirty_raw = _resolve_git_context(repo_root)

    status_feature_dir = _status_read_feature_dir(repo_root, feature, feature_dir)
    git_dirty = _accept_dirty_gate(
        git_dirty_raw,
        repo_root=repo_root,
        feature=feature,
        feature_dir=feature_dir,
        read_feature_dir=read_feature_dir,
        status_feature_dir=status_feature_dir,
    )

    lanes: dict[str, list[str]] = {lane: [] for lane in LANES}
    work_packages: list[WorkPackageState] = []
    metadata_issues: list[str] = []
    activity_issues: list[str] = []
    skipped_checks: list[AcceptanceCheckDiagnostic] = []
    blocked_checks: list[AcceptanceCheckDiagnostic] = []

    snapshot_wps = _collect_snapshot_wps(feature, status_feature_dir, activity_issues)

    # #2122: PRIMARY-partition reads (WP tasks/, planning artifacts) must key on
    # the canonical PRIMARY slug, not the raw handle. A mid8/ULID/numeric handle
    # passed straight to the kind-aware seam composes a nonexistent
    # `kitty-specs/<handle>` dir. `feature_dir` is the already-resolved primary
    # anchor, so its name is the canonical primary slug (which can legitimately
    # differ from the coord read-dir name for backfilled legacy missions).
    # STATUS reads above/below stay coord-aware on the raw `feature` (C-002).
    primary_slug = feature_dir.name

    expected_wp_ids: list[str] = []
    for wp in _iter_work_packages(repo_root, primary_slug):
        wp_id = wp.work_package_id or wp.path.stem
        title = (wp.title or "").strip('"')
        expected_wp_ids.append(wp_id)

        wp_snapshot = snapshot_wps.get(wp_id)
        canonical_lane = wp_snapshot.get("lane") if wp_snapshot else None
        bucket_lane = canonical_lane if canonical_lane is not None else "planned"
        if bucket_lane in lanes:
            lanes[bucket_lane].append(wp_id)
        else:
            lanes["planned"].append(wp_id)

        metadata: dict[str, str | None] = {
            "lane": canonical_lane,
            "agent": wp.agent,
            "assignee": wp.assignee,
            "shell_pid": wp.shell_pid,
        }

        if strict_metadata:
            if not wp.agent:
                metadata_issues.append(f"{wp_id}: missing agent in frontmatter")
            if canonical_lane in {"doing", Lane.IN_PROGRESS, Lane.FOR_REVIEW} and not wp.assignee:
                metadata_issues.append(f"{wp_id}: missing assignee in frontmatter")
            if not wp.shell_pid:
                metadata_issues.append(f"{wp_id}: missing shell_pid in frontmatter")

        work_packages.append(
            WorkPackageState(
                work_package_id=wp_id,
                lane=bucket_lane,
                title=title,
                path=str(wp.path.relative_to(repo_root)),
                has_lane_entry=canonical_lane is not None,
                latest_lane=canonical_lane,
                metadata=metadata,
            )
        )

    _validate_wp_readiness(expected_wp_ids, snapshot_wps, status_feature_dir / EVENTS_FILENAME, activity_issues)

    # FR-002 (#2085): PLANNING reads (spec/plan/tasks/research/data-model/quickstart)
    # resolve the PRIMARY surface via the WP01 kind-aware seam; the STATUS reads above
    # (status.events.jsonl) and below (acceptance-matrix via _check_lane_gates) stay on
    # the coord-aware status_feature_dir (C-002). The single status_feature_dir variable
    # is split per-partition WITHOUT renaming it (additive: a new planning_read_dir).
    planning_read_dir = _planning_read_dir(repo_root, primary_slug)

    unchecked_tasks = _find_unchecked_tasks(planning_read_dir / TASKS_FILE)
    needs_clarification = _check_needs_clarification(
        [
            planning_read_dir / "spec.md",
            planning_read_dir / "plan.md",
            planning_read_dir / "quickstart.md",
            planning_read_dir / TASKS_FILE,
            planning_read_dir / "research.md",
            planning_read_dir / "data-model.md",
        ]
    )
    missing_required, missing_optional = _missing_artifacts(planning_read_dir)

    path_violations: list[str] = []
    path_convention_warning: str | None = None
    try:
        mission = get_mission_for_feature(feature_dir)
    except MissionError:
        mission = None

    if mission and mission.config.paths:
        # Mission path conventions block acceptance by default, but under
        # ``--lenient`` (``strict_metadata=False``) they are advisory: surface
        # them as a non-blocking warning instead of a hard ``path_violations``
        # so repos with a non-default layout (e.g. a Go service using
        # ``internal/`` with no top-level ``tests/``) can be accepted with
        # ``accept --lenient`` rather than the empty-directory workaround
        # (issue #1892). ``validate_mission_paths`` is invoked non-strict here so
        # we own the blocking decision rather than catching a raise.
        path_result = validate_mission_paths(
            mission,
            repo_root,
            strict=False,
            path_prefix=_path_prefix_for_mission(mission, feature_dir),
        )
        if path_result.missing_paths:
            if strict_metadata:
                path_violations.append(
                    path_result.format_errors() or _PATH_CONVENTIONS_NOT_SATISFIED
                )
            else:
                path_convention_warning = (
                    path_result.format_warnings() or _PATH_CONVENTIONS_NOT_SATISFIED
                )

    warnings: list[str] = []
    if missing_optional:
        warnings.append("Optional artifacts missing: " + ", ".join(missing_optional))
    if path_violations:
        warnings.append(_PATH_CONVENTIONS_NOT_SATISFIED)
    elif path_convention_warning:
        warnings.append(path_convention_warning)

    # T028: use coord-resolved read_feature_dir for lane-gate checks so that
    # lanes.json and acceptance-matrix.json are read from the coordination
    # worktree rather than the primary checkout when coord topology is active.
    _check_lane_gates(
        repo_root,
        read_feature_dir,
        branch,
        activity_issues,
        skipped_checks,
        blocked_checks,
        mutate_matrix=mutate_matrix,
    )
    _check_workflow_run_evidence(repo_root, read_feature_dir, branch, activity_issues)

    normalized_unchecked_tasks = _normalized_unchecked_tasks(unchecked_tasks, lanes)
    recommended_fix_order = _build_recommended_fix_order(
        lanes=lanes,
        metadata_issues=metadata_issues,
        activity_issues=activity_issues,
        unchecked_tasks=normalized_unchecked_tasks,
        needs_clarification=needs_clarification,
        missing_artifacts=missing_required,
        git_dirty=git_dirty,
        path_violations=path_violations,
        blocked_checks=blocked_checks,
    )

    return AcceptanceSummary(
        feature=feature,
        repo_root=repo_root,
        feature_dir=feature_dir,
        tasks_dir=tasks_dir,
        branch=branch,
        worktree_root=worktree_root,
        primary_repo_root=primary_repo_root,
        lanes=lanes,
        work_packages=work_packages,
        metadata_issues=metadata_issues,
        activity_issues=activity_issues,
        unchecked_tasks=normalized_unchecked_tasks,
        needs_clarification=needs_clarification,
        missing_artifacts=missing_required,
        optional_missing=missing_optional,
        git_dirty=git_dirty,
        path_violations=path_violations,
        warnings=warnings,
        skipped_checks=skipped_checks,
        blocked_checks=blocked_checks,
        recommended_fix_order=recommended_fix_order,
    )


def choose_mode(preference: str | None, repo_root: Path) -> AcceptanceMode:
    if preference in {"pr", "local", "checklist"}:
        return preference
    try:
        remotes = run_git(["remote"], cwd=repo_root, check=False).stdout.strip().splitlines()
        if remotes:
            return "pr"
    except TaskCliError:
        pass
    return "local"


def resolve_acceptance_actor(actor: str | None) -> str:
    return (actor or os.getenv("USER") or os.getenv("USERNAME") or "system").strip()


def acceptance_lane_derivations(summary: AcceptanceSummary) -> dict[str, list[str]]:
    approved_wps = list(summary.lanes.get("approved", []))
    done_wps = list(summary.lanes.get("done", []))
    return {
        "accepted_wps": [*approved_wps, *done_wps],
        "approved_wps": approved_wps,
        "done_wps": done_wps,
        "merge_pending_wps": approved_wps,
    }


_WELL_KNOWN_INTEGRATION_BRANCHES = frozenset({"main", "master", "develop", "development", "2.x", "3.x"})


def _commit_acceptance_meta(
    summary: AcceptanceSummary,
    actor_name: str,
    mode: AcceptanceMode,
) -> tuple[str | None, str | None, bool]:
    """Record acceptance in meta.json and commit; return (parent_commit, accept_commit, commit_created).

    T016 / WP04 / FR-001 / FR-003 / FR-009: the former
    ``assert_not_protected_branch → raise`` deadlock is removed.  Protection
    provenance flows through ``ProtectionPolicy.resolve`` (FR-007 / SF-2).

    When HEAD is on an UNPROTECTED branch (the normal mission-lane path):
    commits go directly to that branch, preserving existing behaviour.

    When HEAD is on a PROTECTED branch (e.g. ``main``, direct-repo solo-fork
    operator): commits are routed through ``commit_for_mission`` which
    materialises the coordination worktree on demand (C-001 / FR-003).
    """
    from specify_cli.core.git_ops import get_current_branch
    from specify_cli.git.protection_policy import ProtectionPolicy

    repo_root = summary.repo_root
    mission_slug = summary.feature
    policy = ProtectionPolicy.resolve(repo_root)
    current_branch = get_current_branch(repo_root)
    on_protected_primary = current_branch is not None and policy.is_protected(current_branch)

    try:
        parent_commit: str | None = run_git(["rev-parse", "HEAD"], cwd=repo_root, check=False).stdout.strip() or None
    except TaskCliError:
        parent_commit = None

    record_acceptance(summary.feature_dir, accepted_by=actor_name, mode=mode, from_commit=parent_commit, accept_commit=None)

    meta_path = summary.feature_dir / "meta.json"
    meta_rel = str(meta_path.relative_to(repo_root))

    if on_protected_primary:
        # Protected primary: route through commit_for_mission so the coord
        # worktree is materialised on demand (C-001 / FR-003).
        return _commit_acceptance_meta_via_router(
            repo_root=repo_root,
            mission_slug=mission_slug,
            meta_path=meta_path,
            policy=policy,
            parent_commit=parent_commit,
        )

    # Unprotected path (mission-lane branch): commit directly to current branch.
    run_git(["add", meta_rel], cwd=repo_root, check=True)

    # Scope the staged-check and commit to meta.json. A bare ``git commit`` would
    # sweep in any unrelated files the operator had pre-staged before running
    # ``accept``; the explicit ``-- <meta>`` pathspec commits only the
    # acceptance metadata and leaves the operator's staged work untouched.
    status = run_git(["diff", "--cached", "--name-only", "--", meta_rel], cwd=repo_root, check=True)
    staged_files = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    if not staged_files:
        return parent_commit, None, False

    run_git(["commit", "-m", f"Accept {mission_slug}", "--", meta_rel], cwd=repo_root, check=True)
    try:
        accept_commit: str | None = run_git(["rev-parse", "HEAD"], cwd=repo_root, check=True).stdout.strip()
    except TaskCliError:
        accept_commit = None

    if accept_commit:
        _meta = load_meta(summary.feature_dir)
        if _meta is not None:
            _meta["accept_commit"] = accept_commit
            _history = _meta.get("acceptance_history", [])
            if _history:
                _history[-1]["accept_commit"] = accept_commit
            write_meta(summary.feature_dir, _meta)
            run_git(["add", meta_rel], cwd=repo_root, check=True)
            commit_status = run_git(["diff", "--cached", "--name-only", "--", meta_rel], cwd=repo_root, check=True)
            commit_staged_files = [line.strip() for line in commit_status.stdout.splitlines() if line.strip()]
            if commit_staged_files:
                run_git(
                    ["commit", "-m", f"Record acceptance commit for {mission_slug}", "--", meta_rel],
                    cwd=repo_root,
                    check=True,
                )

    return parent_commit, accept_commit, True


def _commit_acceptance_meta_via_router(
    *,
    repo_root: Path,
    mission_slug: str,
    meta_path: Path,
    policy: Any,
    parent_commit: str | None,
) -> tuple[str | None, str | None, bool]:
    """Route acceptance commit through ``commit_for_mission`` on a protected primary.

    Called by :func:`_commit_acceptance_meta` when HEAD is on a protected branch.
    ``commit_for_mission`` handles coord-worktree materialisation (C-001).
    Extracted to keep ``_commit_acceptance_meta`` complexity within the C901 ceiling.

    ``policy`` accepts any object satisfying the ``_ProtectionPolicyProtocol``
    structural protocol in ``commit_router`` (duck-typed; always a ``ProtectionPolicy``
    instance at runtime — using ``Any`` avoids a cross-module Protocol import).
    """
    from mission_runtime import MissionArtifactKind
    from specify_cli.coordination.commit_router import commit_for_mission

    router_result = commit_for_mission(
        repo_root=repo_root,
        mission_slug=mission_slug,
        files=(meta_path,),
        message=f"Accept {mission_slug}",
        policy=policy,
        # meta.json is PRIMARY_METADATA (write-surface-coherence WP02 / T009):
        # acceptance meta moves to the primary surface on the WRITE side too,
        # realizing the INV-5 read↔write symmetry. Primary kind → primary target.
        kind=MissionArtifactKind.PRIMARY_METADATA,
    )

    if router_result.status == "unchanged":
        return parent_commit, None, False

    if router_result.status not in ("committed",):
        raise AcceptanceError(
            f"Acceptance commit failed ({router_result.status}): "
            + (router_result.diagnostic or "no diagnostic available")
        )

    accept_commit: str | None = router_result.commit_hash

    if accept_commit:
        _meta = load_meta(meta_path.parent)
        if _meta is not None:
            _meta["accept_commit"] = accept_commit
            _history = _meta.get("acceptance_history", [])
            if _history:
                _history[-1]["accept_commit"] = accept_commit
            write_meta(meta_path.parent, _meta)
            # Second commit: record the accept_commit SHA back into meta.json.
            commit_for_mission(
                repo_root=repo_root,
                mission_slug=mission_slug,
                files=(meta_path,),
                message=f"Record acceptance commit for {mission_slug}",
                policy=policy,
                # meta.json → PRIMARY_METADATA (write-surface-coherence WP02 / T009).
                kind=MissionArtifactKind.PRIMARY_METADATA,
            )

    return parent_commit, accept_commit, True


def _build_acceptance_instructions(
    summary: AcceptanceSummary,
    mode: AcceptanceMode,
    branch: str,
    is_integration_branch: bool,
) -> tuple[list[str], list[str]]:
    """Build human-readable next-step and cleanup instruction lists."""
    instructions: list[str] = []
    cleanup_instructions: list[str] = []

    if mode == "pr":
        if is_integration_branch:
            instructions.append(f"Acceptance recorded on integration branch `{branch}`. Push and open a pull request if needed.")
        else:
            instructions.extend([
                f"Review the acceptance commit on branch `{branch}`.",
                f"Run the mission merge when ready: `spec-kitty merge --mission {summary.feature}`",
                "After merge, run /spec-kitty-mission-review and the retrospective workflow.",
            ])
    elif mode == "local":
        if is_integration_branch:
            instructions.append(f"Acceptance recorded directly on `{branch}`. No merge needed.")
        else:
            instructions.extend([
                f"Acceptance passed. Run the mission merge: `spec-kitty merge --mission {summary.feature}`",
                "After merge, run /spec-kitty-mission-review and the retrospective workflow.",
            ])
    else:  # checklist
        instructions.append(
            f"All checks passed. Recommended next step: `spec-kitty merge --mission {summary.feature}`."
        )

    if summary.worktree_root != summary.primary_repo_root:
        cleanup_instructions.append(f"After merging, remove the worktree: `git worktree remove {summary.worktree_root}`")
    if not is_integration_branch:
        cleanup_instructions.append(f"Delete the feature branch when done: `git branch -d {branch}`")

    return instructions, cleanup_instructions


def perform_acceptance(
    summary: AcceptanceSummary,
    *,
    mode: AcceptanceMode,
    actor: str | None,
    tests: Sequence[str] | None = None,
    auto_commit: bool | None = None,
) -> AcceptanceResult:
    if auto_commit is None:
        auto_commit = get_auto_commit_default(summary.repo_root)

    if mode != "checklist" and not summary.ok:
        raise AcceptanceError("Acceptance checks failed; run verify to see outstanding issues.")

    actor_name = resolve_acceptance_actor(actor)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_commit: str | None = None
    accept_commit: str | None = None
    commit_created = False

    if auto_commit and mode != "checklist":
        parent_commit, accept_commit, commit_created = _commit_acceptance_meta(summary, actor_name, mode)

    branch = summary.branch or summary.feature
    _meta = load_meta(summary.feature_dir)
    _target_branch = (_meta or {}).get("target_branch")
    is_integration_branch = branch == _target_branch or (_target_branch is None and branch in _WELL_KNOWN_INTEGRATION_BRANCHES)

    instructions, cleanup_instructions = _build_acceptance_instructions(summary, mode, branch, is_integration_branch)

    notes: list[str] = []
    if accept_commit:
        notes.append(f"Acceptance commit: {accept_commit}")
    if parent_commit:
        notes.append(f"Accepted from parent commit: {parent_commit}")
    if tests:
        notes.append("Validation commands:")
        notes.extend(f"  - {cmd}" for cmd in tests)

    lane_derivations = acceptance_lane_derivations(summary)

    return AcceptanceResult(
        summary=summary,
        mode=mode,
        accepted_at=timestamp,
        accepted_by=actor_name,
        parent_commit=parent_commit,
        accept_commit=accept_commit,
        commit_created=commit_created,
        instructions=instructions,
        cleanup_instructions=cleanup_instructions,
        notes=notes,
        accepted_wps=lane_derivations["accepted_wps"],
        approved_wps=lane_derivations["approved_wps"],
        done_wps=lane_derivations["done_wps"],
        merge_pending_wps=lane_derivations["merge_pending_wps"],
    )


__all__ = [
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "acceptance_lane_derivations",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_mission_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
    "resolve_acceptance_actor",
]
