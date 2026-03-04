#!/usr/bin/env python3
"""Acceptance workflow utilities for Spec Kitty features."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence

from .tasks_support import (
    LANES,
    TaskCliError,
    WorkPackage,
    activity_entries,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    run_git,
    split_frontmatter,
)
from specify_cli.mission import MissionError, get_mission_for_feature
from specify_cli.validators.paths import PathValidationError, validate_mission_paths
from specify_cli.core.feature_detection import (
    detect_feature_slug as centralized_detect_feature_slug,
    FeatureDetectionError,
)

AcceptanceMode = str  # Expected values: "pr", "local", "checklist"

_TASKS_MD = "tasks.md"


class AcceptanceError(TaskCliError):
    """Raised when acceptance cannot complete due to outstanding issues."""


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
        return not (self.lanes.get("planned") or self.lanes.get("doing") or self.lanes.get("for_review"))

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
                *self.lanes.get("doing", []),
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
        return {
            "feature": self.feature,
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


def _iter_legacy_wps(feature: str, tasks_dir: Path) -> Iterable[WorkPackage]:
    for lane_dir in sorted(tasks_dir.iterdir()):
        if not lane_dir.is_dir():
            continue
        lane = lane_dir.name
        if lane not in LANES:
            continue
        for path in sorted(lane_dir.rglob("*.md")):
            text = path.read_text(encoding="utf-8-sig")
            front, body, padding = split_frontmatter(text)
            yield WorkPackage(
                feature=feature,
                path=path,
                current_lane=lane,
                relative_subpath=path.relative_to(lane_dir),
                frontmatter=front,
                body=body,
                padding=padding,
            )


def _iter_flat_wps(feature: str, tasks_dir: Path) -> Iterable[WorkPackage]:
    for path in sorted(tasks_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8-sig")
        front, body, padding = split_frontmatter(text)
        lane = get_lane_from_frontmatter(path, warn_on_missing=False)
        yield WorkPackage(
            feature=feature,
            path=path,
            current_lane=lane,
            relative_subpath=path.relative_to(tasks_dir),
            frontmatter=front,
            body=body,
            padding=padding,
        )


def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    """Iterate over work packages, supporting both legacy and new formats.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    feature_path = repo_root / "kitty-specs" / feature
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        raise AcceptanceError(f"Feature '{feature}' has no tasks directory at {tasks_dir}.")
    if is_legacy_format(feature_path):
        yield from _iter_legacy_wps(feature, tasks_dir)
    else:
        yield from _iter_flat_wps(feature, tasks_dir)


def detect_feature_slug(
    repo_root: Path,
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    announce_fallback: bool = True,
) -> str:
    """Detect feature slug using centralized detection.

    This function maintains backward compatibility while delegating
    to the centralized feature detection module.

    Args:
        repo_root: Repository root path
        env: Environment variables (defaults to os.environ)
        cwd: Current working directory (defaults to Path.cwd())

    Returns:
        Feature slug (e.g., "020-my-feature")

    Raises:
        AcceptanceError: If feature slug cannot be determined
    """
    try:
        return centralized_detect_feature_slug(
            repo_root,
            env=env,
            cwd=cwd,
            mode="strict",
            announce_fallback=announce_fallback,
        )
    except FeatureDetectionError as e:
        # Convert to AcceptanceError for backward compatibility
        raise AcceptanceError(str(e)) from e


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def _find_unchecked_tasks(tasks_file: Path) -> list[str]:
    if not tasks_file.exists():
        return [f"{_TASKS_MD} missing"]

    unchecked: list[str] = []
    for line in tasks_file.read_text(encoding="utf-8-sig").splitlines():
        if re.match(r"^\s*-\s*\[ \]", line):
            unchecked.append(line.strip())
    return unchecked


def _check_needs_clarification(files: Sequence[Path]) -> list[str]:
    results: list[str] = []
    for file_path in files:
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8-sig")
            if "[NEEDS CLARIFICATION" in text:
                results.append(str(file_path))
    return results


def _missing_artifacts(feature_dir: Path) -> tuple[list[str], list[str]]:
    required = [feature_dir / "spec.md", feature_dir / "plan.md", feature_dir / _TASKS_MD]
    optional = [
        feature_dir / "quickstart.md",
        feature_dir / "data-model.md",
        feature_dir / "research.md",
        feature_dir / "contracts",
    ]
    missing_required = [str(p.relative_to(feature_dir)) for p in required if not p.exists()]
    missing_optional = [str(p.relative_to(feature_dir)) for p in optional if not p.exists()]
    return missing_required, missing_optional


def _get_git_context(repo_root: Path) -> tuple[str | None, Path, Path]:
    branch: str | None = None
    try:
        branch_value = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True).stdout.strip()
        if branch_value and branch_value != "HEAD":
            branch = branch_value
    except TaskCliError:
        pass

    try:
        worktree_root = Path(
            run_git(["rev-parse", "--show-toplevel"], cwd=repo_root, check=True).stdout.strip()
        ).resolve()
    except TaskCliError:
        worktree_root = repo_root

    try:
        git_common_dir = Path(
            run_git(["rev-parse", "--git-common-dir"], cwd=repo_root, check=True).stdout.strip()
        ).resolve()
        primary_repo_root = git_common_dir.parent
    except TaskCliError:
        primary_repo_root = repo_root

    return branch, worktree_root, primary_repo_root


def _check_wp_metadata(wp: WorkPackage, wp_id: str, use_legacy: bool) -> list[str]:
    issues: list[str] = []
    lane_value = (wp.lane or "").strip()
    if not lane_value:
        issues.append(f"{wp_id}: missing lane in frontmatter")
    elif use_legacy and lane_value != wp.current_lane:
        issues.append(f"{wp_id}: frontmatter lane '{lane_value}' does not match directory '{wp.current_lane}'")
    if not wp.agent:
        issues.append(f"{wp_id}: missing agent in frontmatter")
    if wp.current_lane in {"doing", "for_review"} and not wp.assignee:
        issues.append(f"{wp_id}: missing assignee in frontmatter")
    if not wp.shell_pid:
        issues.append(f"{wp_id}: missing shell_pid in frontmatter")
    return issues


def _check_wp_activity(wp: WorkPackage, wp_id: str, entries: list[dict[str, str]]) -> list[str]:
    if not entries:
        return [f"{wp_id}: Activity Log missing entries"]
    issues: list[str] = []
    lanes_logged = {entry["lane"] for entry in entries}
    if wp.current_lane not in lanes_logged:
        issues.append(f"{wp_id}: Activity Log missing entry for lane={wp.current_lane}")
    if wp.current_lane == "done" and entries[-1]["lane"] != "done":
        issues.append(f"{wp_id}: latest Activity Log entry not lane=done")
    return issues


def _get_path_violations(feature_dir: Path, repo_root: Path) -> list[str]:
    violations: list[str] = []
    try:
        mission = get_mission_for_feature(feature_dir)
    except MissionError:
        return violations
    if mission and mission.config.paths:
        try:
            validate_mission_paths(mission, repo_root, strict=True)
        except PathValidationError as exc:
            violations.append(exc.result.format_errors() or str(exc))
    return violations


def collect_feature_summary(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool = True,
) -> AcceptanceSummary:
    feature_dir = repo_root / "kitty-specs" / feature
    tasks_dir = feature_dir / "tasks"
    if not feature_dir.exists():
        raise AcceptanceError(f"Feature directory not found: {feature_dir}")

    branch, worktree_root, primary_repo_root = _get_git_context(repo_root)

    lanes: dict[str, list[str]] = {lane: [] for lane in LANES}
    work_packages: list[WorkPackageState] = []
    metadata_issues: list[str] = []
    activity_issues: list[str] = []

    use_legacy = is_legacy_format(feature_dir)

    for wp in _iter_work_packages(repo_root, feature):
        wp_id = wp.work_package_id or wp.path.stem
        title = (wp.title or "").strip('"')
        lanes[wp.current_lane].append(wp_id)

        entries = activity_entries(wp.body)
        latest_lane = entries[-1]["lane"] if entries else None
        has_lane_entry = wp.current_lane in {entry["lane"] for entry in entries}

        metadata: dict[str, str | None] = {
            "lane": wp.lane,
            "agent": wp.agent,
            "assignee": wp.assignee,
            "shell_pid": wp.shell_pid,
        }

        if strict_metadata:
            metadata_issues.extend(_check_wp_metadata(wp, wp_id, use_legacy))
        activity_issues.extend(_check_wp_activity(wp, wp_id, entries))

        work_packages.append(
            WorkPackageState(
                work_package_id=wp_id,
                lane=wp.current_lane,
                title=title,
                path=str(wp.path.relative_to(repo_root)),
                has_lane_entry=has_lane_entry,
                latest_lane=latest_lane,
                metadata=metadata,
            )
        )

    unchecked_tasks = _find_unchecked_tasks(feature_dir / _TASKS_MD)
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

    try:
        git_dirty = git_status_lines(repo_root)
    except TaskCliError:
        git_dirty = []

    path_violations = _get_path_violations(feature_dir, repo_root)

    warnings: list[str] = []
    if missing_optional:
        warnings.append("Optional artifacts missing: " + ", ".join(missing_optional))
    if path_violations:
        warnings.append("Path conventions not satisfied.")

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


def _persist_acceptance_commit(
    summary: AcceptanceSummary,
    actor_name: str,
    mode: AcceptanceMode,
    parent_commit: str | None,
    timestamp: str,
    tests: Sequence[str] | None,
) -> tuple[str | None, bool]:
    meta_path = summary.feature_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.exists() else {}

    acceptance_record: dict[str, object] = {
        "accepted_at": timestamp,
        "accepted_by": actor_name,
        "mode": mode,
        "branch": summary.branch,
        "accepted_from_commit": parent_commit,
    }
    if tests:
        acceptance_record["validation_commands"] = list(tests)

    meta.update(
        {
            "accepted_at": timestamp,
            "accepted_by": actor_name,
            "acceptance_mode": mode,
            "accepted_from_commit": parent_commit,
            "accept_commit": None,
        }
    )

    history: list[dict[str, object]] = meta.setdefault("acceptance_history", [])
    history.append(acceptance_record)
    if len(history) > 20:
        meta["acceptance_history"] = history[-20:]

    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_git(["add", str(meta_path.relative_to(summary.repo_root))], cwd=summary.repo_root, check=True)

    staged_files = [
        line.strip()
        for line in run_git(["diff", "--cached", "--name-only"], cwd=summary.repo_root, check=True).stdout.splitlines()
        if line.strip()
    ]
    if not staged_files:
        return None, False

    run_git(["commit", "-m", f"Accept {summary.feature}"], cwd=summary.repo_root, check=True)
    try:
        accept_commit = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=True).stdout.strip()
    except TaskCliError:
        accept_commit = None
    return accept_commit, True


def _build_acceptance_instructions(
    mode: AcceptanceMode,
    branch: str,
    summary: AcceptanceSummary,
) -> tuple[list[str], list[str]]:
    if mode == "pr":
        instructions: list[str] = [
            f"Review the acceptance commit on branch `{branch}`.",
            f"Push your branch: `git push origin {branch}`",
            "Open a pull request referencing spec/plan/tasks artifacts.",
            "Include acceptance summary and test evidence in the PR description.",
        ]
    elif mode == "local":
        instructions = [
            "Switch to your integration branch (e.g., `git checkout main`).",
            "Synchronize it (e.g., `git pull --ff-only`).",
            f"Merge the feature: `git merge {branch}`",
        ]
    else:
        instructions = ["All checks passed. Proceed with your manual acceptance workflow."]

    cleanup_instructions: list[str] = []
    if summary.worktree_root != summary.primary_repo_root:
        cleanup_instructions.append(
            f"After merging, remove the worktree: `git worktree remove {summary.worktree_root}`"
        )
    cleanup_instructions.append(f"Delete the feature branch when done: `git branch -d {branch}`")
    return instructions, cleanup_instructions


def perform_acceptance(
    summary: AcceptanceSummary,
    *,
    mode: AcceptanceMode,
    actor: str | None,
    tests: Sequence[str] | None = None,
    auto_commit: bool = True,
) -> AcceptanceResult:
    if mode != "checklist" and not summary.ok:
        raise AcceptanceError("Acceptance checks failed; run verify to see outstanding issues.")

    actor_name = (actor or os.getenv("USER") or os.getenv("USERNAME") or "system").strip()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_commit: str | None = None
    accept_commit: str | None = None
    commit_created = False

    if auto_commit and mode != "checklist":
        try:
            parent_commit = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=False).stdout.strip() or None
        except TaskCliError:
            parent_commit = None
        accept_commit, commit_created = _persist_acceptance_commit(
            summary, actor_name, mode, parent_commit, timestamp, tests
        )

    branch = summary.branch or summary.feature
    instructions, cleanup_instructions = _build_acceptance_instructions(mode, branch, summary)

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
    "AcceptanceResult",
    "AcceptanceSummary",
    "AcceptanceMode",
    "collect_feature_summary",
    "detect_feature_slug",
    "choose_mode",
    "perform_acceptance",
]
