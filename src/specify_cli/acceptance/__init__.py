#!/usr/bin/env python3
"""Acceptance workflow utilities for Spec Kitty missions."""

from __future__ import annotations

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
from specify_cli.mission import MissionError, get_mission_for_feature
from specify_cli.mission_metadata import load_meta, record_acceptance, resolve_mission_identity, write_meta
from specify_cli.status.models import Lane
from specify_cli.status.store import EVENTS_FILENAME, StoreError
from specify_cli.validators.paths import PathValidationError, validate_mission_paths

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

    @property
    def all_done(self) -> bool:
        """True when all WPs are approved or done (no WPs still in progress or review)."""
        return not (
            self.lanes.get("planned") or self.lanes.get("claimed") or self.lanes.get("doing") or self.lanes.get("in_progress") or self.lanes.get("for_review")
        )

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
                *self.lanes.get("planned", []),
                *self.lanes.get("claimed", []),
                *self.lanes.get("doing", []),
                *self.lanes.get("in_progress", []),
                *self.lanes.get("for_review", []),
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
            "summary": self.summary.to_dict(),
        }


def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    """Iterate over work packages, supporting both legacy and new formats.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    feature_path = repo_root / "kitty-specs" / feature
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
            lane = get_lane_from_frontmatter(path, warn_on_missing=False)
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
        return ["tasks.md missing"]

    unchecked: list[str] = []
    for line in _read_text_strict(tasks_file).splitlines():
        if re.match(r"^\s*-\s*\[ \]", line):
            unchecked.append(line.strip())
    return unchecked


def _check_needs_clarification(files: Sequence[Path]) -> list[str]:
    results: list[str] = []
    for file_path in files:
        if file_path.exists():
            text = _read_text_strict(file_path)
            if "[NEEDS CLARIFICATION" in text:
                results.append(str(file_path))
    return results


def _missing_artifacts(feature_dir: Path) -> tuple[list[str], list[str]]:
    required = [feature_dir / "spec.md", feature_dir / "plan.md", feature_dir / "tasks.md"]
    optional = [
        feature_dir / "quickstart.md",
        feature_dir / "data-model.md",
        feature_dir / "research.md",
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

    feature_dir = repo_root / "kitty-specs" / feature
    if not feature_dir.exists():
        return []

    candidates: list[Path] = []
    primary_files = [
        feature_dir / "spec.md",
        feature_dir / "plan.md",
        feature_dir / "quickstart.md",
        feature_dir / "tasks.md",
        feature_dir / "research.md",
        feature_dir / "data-model.md",
    ]
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
        "Run status migration to bootstrap the event log."
    )
    if not events_path.exists():
        activity_issues.append(_missing_msg)
        return {}
    try:
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events

        snapshot = reduce(read_events(feature_dir))
    except StoreError as exc:
        raise AcceptanceError(f"Status event log is corrupted for feature '{feature}': {exc}") from exc
    if not snapshot.work_packages:
        activity_issues.append(_missing_msg)
    return snapshot.work_packages


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


def _check_lane_gates(
    repo_root: Path,
    feature_dir: Path,
    branch: str | None,
    activity_issues: list[str],
) -> None:
    """Enforce lane-based acceptance gates: branch check + acceptance matrix."""
    try:
        from specify_cli.lanes.persistence import read_lanes_json

        lanes_manifest = read_lanes_json(feature_dir)
    except Exception:
        return

    if lanes_manifest is None:
        return

    if branch and branch != lanes_manifest.mission_branch:
        activity_issues.append(f"Acceptance must run on mission branch {lanes_manifest.mission_branch}, not {branch}")

    from specify_cli.acceptance.matrix import (
        enforce_negative_invariants,
        read_acceptance_matrix,
        validate_matrix_evidence,
        write_acceptance_matrix,
    )

    acc_matrix = read_acceptance_matrix(feature_dir)
    if acc_matrix is None:
        activity_issues.append("Acceptance matrix (acceptance-matrix.json) is required for lane-based features but was not found")
        return

    if acc_matrix.negative_invariants:
        acc_matrix.negative_invariants = enforce_negative_invariants(repo_root, acc_matrix.negative_invariants)
        write_acceptance_matrix(feature_dir, acc_matrix)

    for err in validate_matrix_evidence(acc_matrix):
        activity_issues.append(f"Evidence: {err}")

    verdict = acc_matrix.overall_verdict
    if verdict == "fail":
        activity_issues.append("Acceptance matrix verdict is 'fail' — negative invariants or criteria not satisfied")
    elif verdict == "pending":
        activity_issues.append("Acceptance matrix verdict is 'pending' — criteria or invariants have not been verified")


def collect_feature_summary(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool = True,
) -> AcceptanceSummary:
    feature_dir = repo_root / "kitty-specs" / feature
    tasks_dir = feature_dir / "tasks"
    if not feature_dir.exists():
        raise AcceptanceError(f"Mission directory not found: {feature_dir}")

    branch, worktree_root, primary_repo_root, git_dirty = _resolve_git_context(repo_root)

    lanes: dict[str, list[str]] = {lane: [] for lane in LANES}
    work_packages: list[WorkPackageState] = []
    metadata_issues: list[str] = []
    activity_issues: list[str] = []

    snapshot_wps = _collect_snapshot_wps(feature, feature_dir, activity_issues)

    expected_wp_ids: list[str] = []
    for wp in _iter_work_packages(repo_root, feature):
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

    _validate_wp_readiness(expected_wp_ids, snapshot_wps, feature_dir / EVENTS_FILENAME, activity_issues)

    unchecked_tasks = _find_unchecked_tasks(feature_dir / "tasks.md")
    needs_clarification = _check_needs_clarification(
        [
            feature_dir / "spec.md",
            feature_dir / "plan.md",
            feature_dir / "quickstart.md",
            feature_dir / "tasks.md",
            feature_dir / "research.md",
            feature_dir / "data-model.md",
        ]
    )
    missing_required, missing_optional = _missing_artifacts(feature_dir)

    path_violations: list[str] = []
    try:
        mission = get_mission_for_feature(feature_dir)
    except MissionError:
        mission = None

    if mission and mission.config.paths:
        try:
            validate_mission_paths(mission, repo_root, strict=True)
        except PathValidationError as exc:
            path_violations.append(exc.result.format_errors() or str(exc))

    warnings: list[str] = []
    if missing_optional:
        warnings.append("Optional artifacts missing: " + ", ".join(missing_optional))
    if path_violations:
        warnings.append("Path conventions not satisfied.")

    _check_lane_gates(repo_root, feature_dir, branch, activity_issues)

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
        unchecked_tasks=unchecked_tasks if unchecked_tasks != ["tasks.md missing"] else [],
        needs_clarification=needs_clarification,
        missing_artifacts=missing_required,
        optional_missing=missing_optional,
        git_dirty=git_dirty,
        path_violations=path_violations,
        warnings=warnings,
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


_WELL_KNOWN_INTEGRATION_BRANCHES = frozenset({"main", "master", "develop", "development", "2.x", "3.x"})


def _commit_acceptance_meta(
    summary: AcceptanceSummary,
    actor_name: str,
    mode: AcceptanceMode,
) -> tuple[str | None, str | None, bool]:
    """Record acceptance in meta.json and commit; return (parent_commit, accept_commit, commit_created)."""
    try:
        parent_commit: str | None = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=False).stdout.strip() or None
    except TaskCliError:
        parent_commit = None

    record_acceptance(summary.feature_dir, accepted_by=actor_name, mode=mode, from_commit=parent_commit, accept_commit=None)

    meta_path = summary.feature_dir / "meta.json"
    run_git(["add", str(meta_path.relative_to(summary.repo_root))], cwd=summary.repo_root, check=True)

    status = run_git(["diff", "--cached", "--name-only"], cwd=summary.repo_root, check=True)
    staged_files = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    if not staged_files:
        return parent_commit, None, False

    run_git(["commit", "-m", f"Accept {summary.feature}"], cwd=summary.repo_root, check=True)
    try:
        accept_commit: str | None = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=True).stdout.strip()
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
                f"Push your branch: `git push origin {branch}`",
                "Open a pull request referencing spec/plan/tasks artifacts.",
                "Include acceptance summary and test evidence in the PR description.",
            ])
    elif mode == "local":
        if is_integration_branch:
            instructions.append(f"Acceptance recorded directly on `{branch}`. No merge needed.")
        else:
            instructions.extend([
                "Switch to your integration branch (e.g., `git checkout main`).",
                "Synchronize it (e.g., `git pull --ff-only`).",
                f"Merge the feature: `git merge {branch}`",
            ])
    else:  # checklist
        instructions.append("All checks passed. Proceed with your manual acceptance workflow.")

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

    actor_name = (actor or os.getenv("USER") or os.getenv("USERNAME") or "system").strip()
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
    )


__all__ = [
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_mission_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
