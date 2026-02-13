#!/usr/bin/env python3
"""Shared acceptance core logic for Spec Kitty features.

This module is the single source of truth for acceptance workflow logic used by:
- ``specify_cli.acceptance`` (installed package CLI entrypoint)
- ``specify_cli.scripts.tasks.acceptance_support`` (standalone script entrypoint)

All data structures and core functions live here.  Both consumers import and
delegate to this module so that acceptance behaviour is identical regardless
of the entrypoint.

Design constraints:
- Depends only on ``specify_cli.task_helpers_shared`` (stdlib-only helpers).
- Does **not** import mission, validator, or Typer modules.
- Callers that need mission-aware validation (``path_violations``) compose the
  result after calling the core functions.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)

try:
    from specify_cli.task_helpers_shared import (
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
except ImportError:
    # Standalone context: task_helpers_shared was loaded under its bare name
    # (e.g. via task_helpers.py sibling import in .kittify/scripts/tasks/).
    from task_helpers_shared import (  # type: ignore[no-redef]
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

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

AcceptanceMode = str  # Expected values: "pr", "local", "checklist"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AcceptanceError(TaskCliError):
    """Raised when acceptance cannot complete due to outstanding issues."""


class ArtifactEncodingError(AcceptanceError):
    """Raised when a project artifact cannot be decoded as UTF-8."""

    def __init__(self, path: Path, error: UnicodeDecodeError):
        byte = error.object[error.start : error.start + 1]
        byte_display = f"0x{byte[0]:02x}" if byte else "unknown"
        message = (
            f"Invalid UTF-8 encoding in {path}: byte {byte_display} at offset {error.start}. "
            "Run with --normalize-encoding to fix automatically."
        )
        super().__init__(message)
        self.path = path
        self.error = error


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class WorkPackageState:
    """Snapshot of a work package's state for acceptance reporting."""

    work_package_id: str
    lane: str
    title: str
    path: str
    has_lane_entry: bool
    latest_lane: Optional[str]
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class AcceptanceSummary:
    """Collected readiness information for a feature."""

    feature: str
    repo_root: Path
    feature_dir: Path
    tasks_dir: Path
    branch: Optional[str]
    worktree_root: Path
    primary_repo_root: Path
    lanes: Dict[str, List[str]]
    work_packages: List[WorkPackageState]
    metadata_issues: List[str]
    activity_issues: List[str]
    unchecked_tasks: List[str]
    needs_clarification: List[str]
    missing_artifacts: List[str]
    optional_missing: List[str]
    git_dirty: List[str]
    path_violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def all_done(self) -> bool:
        return not (
            self.lanes.get("planned")
            or self.lanes.get("doing")
            or self.lanes.get("for_review")
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

    def outstanding(self) -> Dict[str, List[str]]:
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

    def to_dict(self) -> Dict[str, object]:
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
    """Outcome of performing an acceptance workflow."""

    summary: AcceptanceSummary
    mode: AcceptanceMode
    accepted_at: str
    accepted_by: str
    parent_commit: Optional[str]
    accept_commit: Optional[str]
    commit_created: bool
    instructions: List[str]
    cleanup_instructions: List[str]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_text_strict(path: Path) -> str:
    """Read a file as UTF-8, raising ``ArtifactEncodingError`` on decode failure."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactEncodingError(path, exc) from exc


def _read_file(path: Path) -> str:
    """Read a file or return the empty string if it does not exist."""
    return _read_text_strict(path) if path.exists() else ""


def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    """Iterate over work packages, supporting both legacy and new formats.

    Legacy format: WP files in ``tasks/{lane}/`` subdirectories.
    New format: WP files in flat ``tasks/`` directory with lane in frontmatter.
    """
    feature_path = repo_root / "kitty-specs" / feature
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        raise AcceptanceError(
            f"Feature '{feature}' has no tasks directory at {tasks_dir}."
        )

    use_legacy = is_legacy_format(feature_path)

    if use_legacy:
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


def _find_unchecked_tasks(tasks_file: Path) -> List[str]:
    """Return unchecked task lines from ``tasks.md``."""
    if not tasks_file.exists():
        return ["tasks.md missing"]

    unchecked: List[str] = []
    for line in _read_text_strict(tasks_file).splitlines():
        if re.match(r"^\s*-\s*\[ \]", line):
            unchecked.append(line.strip())
    return unchecked


def _check_needs_clarification(files: Sequence[Path]) -> List[str]:
    """Return paths of files that contain ``[NEEDS CLARIFICATION`` markers."""
    results: List[str] = []
    for file_path in files:
        if file_path.exists():
            text = _read_text_strict(file_path)
            if "[NEEDS CLARIFICATION" in text:
                results.append(str(file_path))
    return results


def _missing_artifacts(feature_dir: Path) -> Tuple[List[str], List[str]]:
    """Return lists of missing required and optional artifacts."""
    required = [
        feature_dir / "spec.md",
        feature_dir / "plan.md",
        feature_dir / "tasks.md",
    ]
    optional = [
        feature_dir / "quickstart.md",
        feature_dir / "data-model.md",
        feature_dir / "research.md",
        feature_dir / "contracts",
    ]
    missing_required = [
        str(p.relative_to(feature_dir)) for p in required if not p.exists()
    ]
    missing_optional = [
        str(p.relative_to(feature_dir)) for p in optional if not p.exists()
    ]
    return missing_required, missing_optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_feature_summary(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool = True,
) -> AcceptanceSummary:
    """Collect feature readiness information for acceptance.

    This is the core collection logic shared by both CLI and script entrypoints.
    It does **not** perform mission-aware path validation -- callers that need
    that should augment the returned summary with ``path_violations`` after
    calling this function.

    Args:
        repo_root: Repository root path.
        feature: Feature slug (e.g. ``"020-my-feature"``).
        strict_metadata: If True, enforce metadata completeness checks.

    Returns:
        Populated :class:`AcceptanceSummary`.

    Raises:
        AcceptanceError: If the feature directory or tasks directory is missing.
    """
    feature_dir = repo_root / "kitty-specs" / feature
    tasks_dir = feature_dir / "tasks"
    if not feature_dir.exists():
        raise AcceptanceError(f"Feature directory not found: {feature_dir}")

    # Resolve branch
    branch: Optional[str] = None
    try:
        branch_value = (
            run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True)
            .stdout.strip()
        )
        if branch_value and branch_value != "HEAD":
            branch = branch_value
    except TaskCliError:
        branch = None

    # Resolve worktree root
    try:
        worktree_root = Path(
            run_git(["rev-parse", "--show-toplevel"], cwd=repo_root, check=True)
            .stdout.strip()
        ).resolve()
    except TaskCliError:
        worktree_root = repo_root

    # Resolve primary (main) repo root
    try:
        git_common_dir = Path(
            run_git(["rev-parse", "--git-common-dir"], cwd=repo_root, check=True)
            .stdout.strip()
        ).resolve()
        primary_repo_root = git_common_dir.parent
    except TaskCliError:
        primary_repo_root = repo_root

    lanes: Dict[str, List[str]] = {lane: [] for lane in LANES}
    work_packages: List[WorkPackageState] = []
    metadata_issues: List[str] = []
    activity_issues: List[str] = []

    use_legacy = is_legacy_format(feature_dir)

    for wp in _iter_work_packages(repo_root, feature):
        wp_id = wp.work_package_id or wp.path.stem
        title = (wp.title or "").strip('"')
        lanes[wp.current_lane].append(wp_id)

        entries = activity_entries(wp.body)
        lanes_logged = {entry["lane"] for entry in entries}
        latest_lane = entries[-1]["lane"] if entries else None
        has_lane_entry = wp.current_lane in lanes_logged

        metadata: Dict[str, Optional[str]] = {
            "lane": wp.lane,
            "agent": wp.agent,
            "assignee": wp.assignee,
            "shell_pid": wp.shell_pid,
        }

        if strict_metadata:
            lane_value = (wp.lane or "").strip()
            if not lane_value:
                metadata_issues.append(f"{wp_id}: missing lane in frontmatter")
            elif use_legacy and lane_value != wp.current_lane:
                metadata_issues.append(
                    f"{wp_id}: frontmatter lane '{lane_value}' does not match directory '{wp.current_lane}'"
                )

            if not wp.agent:
                metadata_issues.append(f"{wp_id}: missing agent in frontmatter")
            if wp.current_lane in {"doing", "for_review"} and not wp.assignee:
                metadata_issues.append(
                    f"{wp_id}: missing assignee in frontmatter"
                )
            if not wp.shell_pid:
                metadata_issues.append(
                    f"{wp_id}: missing shell_pid in frontmatter"
                )

        if not entries:
            activity_issues.append(f"{wp_id}: Activity Log missing entries")
        else:
            if wp.current_lane not in lanes_logged:
                activity_issues.append(
                    f"{wp_id}: Activity Log missing entry for lane={wp.current_lane}"
                )
            if wp.current_lane == "done" and entries[-1]["lane"] != "done":
                activity_issues.append(
                    f"{wp_id}: latest Activity Log entry not lane=done"
                )

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

    try:
        git_dirty = git_status_lines(repo_root)
    except TaskCliError:
        git_dirty = []

    warnings: List[str] = []
    if missing_optional:
        warnings.append(
            "Optional artifacts missing: " + ", ".join(missing_optional)
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
        unchecked_tasks=unchecked_tasks if unchecked_tasks != ["tasks.md missing"] else [],
        needs_clarification=needs_clarification,
        missing_artifacts=missing_required,
        optional_missing=missing_optional,
        git_dirty=git_dirty,
        warnings=warnings,
    )


def choose_mode(preference: Optional[str], repo_root: Path) -> AcceptanceMode:
    """Choose an acceptance mode (``pr``, ``local``, or ``checklist``).

    Args:
        preference: Explicit mode preference, or None/``"auto"`` to auto-detect.
        repo_root: Repository root path used for remote detection.

    Returns:
        Resolved acceptance mode string.
    """
    if preference in {"pr", "local", "checklist"}:
        return preference
    try:
        remotes = (
            run_git(["remote"], cwd=repo_root, check=False).stdout.strip().splitlines()
        )
        if remotes:
            return "pr"
    except TaskCliError:
        pass
    return "local"


def perform_acceptance(
    summary: AcceptanceSummary,
    *,
    mode: AcceptanceMode,
    actor: Optional[str],
    tests: Optional[Sequence[str]] = None,
    auto_commit: bool = True,
) -> AcceptanceResult:
    """Execute the acceptance workflow for a feature.

    Args:
        summary: Previously collected :class:`AcceptanceSummary`.
        mode: Acceptance mode (``pr``, ``local``, ``checklist``).
        actor: Name of the accepting actor (falls back to ``$USER``).
        tests: Validation commands that were executed.
        auto_commit: If True and mode is not ``checklist``, write
            ``meta.json`` and create an acceptance commit.

    Returns:
        Populated :class:`AcceptanceResult`.

    Raises:
        AcceptanceError: If the summary is not ``ok`` and mode is not
            ``checklist``.
    """
    if mode != "checklist" and not summary.ok:
        raise AcceptanceError(
            "Acceptance checks failed; run verify to see outstanding issues."
        )

    actor_name = (
        actor or os.getenv("USER") or os.getenv("USERNAME") or "system"
    ).strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_commit: Optional[str] = None
    accept_commit: Optional[str] = None
    commit_created = False

    if auto_commit and mode != "checklist":
        try:
            parent_commit = (
                run_git(
                    ["rev-parse", "HEAD"], cwd=summary.repo_root, check=False
                )
                .stdout.strip()
                or None
            )
        except TaskCliError:
            parent_commit = None

        meta_path = summary.feature_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(_read_text_strict(meta_path))
        else:
            meta = {}

        acceptance_record: Dict[str, object] = {
            "accepted_at": timestamp,
            "accepted_by": actor_name,
            "mode": mode,
            "branch": summary.branch,
            "accepted_from_commit": parent_commit,
        }
        if tests:
            acceptance_record["validation_commands"] = list(tests)

        meta["accepted_at"] = timestamp
        meta["accepted_by"] = actor_name
        meta["acceptance_mode"] = mode
        meta["accepted_from_commit"] = parent_commit
        meta["accept_commit"] = None

        history: List[Dict[str, object]] = meta.setdefault(
            "acceptance_history", []
        )
        history.append(acceptance_record)
        if len(history) > 20:
            meta["acceptance_history"] = history[-20:]

        meta_path.write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        run_git(
            ["add", str(meta_path.relative_to(summary.repo_root))],
            cwd=summary.repo_root,
            check=True,
        )

        status = run_git(
            ["diff", "--cached", "--name-only"],
            cwd=summary.repo_root,
            check=True,
        )
        staged_files = [
            line.strip() for line in status.stdout.splitlines() if line.strip()
        ]
        if staged_files:
            commit_msg = f"Accept {summary.feature}"
            run_git(
                ["commit", "-m", commit_msg],
                cwd=summary.repo_root,
                check=True,
            )
            commit_created = True
            try:
                accept_commit = (
                    run_git(
                        ["rev-parse", "HEAD"],
                        cwd=summary.repo_root,
                        check=True,
                    )
                    .stdout.strip()
                )
            except TaskCliError:
                accept_commit = None

    instructions: List[str] = []
    cleanup_instructions: List[str] = []

    branch = summary.branch or summary.feature
    if mode == "pr":
        instructions.extend(
            [
                f"Review the acceptance commit on branch `{branch}`.",
                f"Push your branch: `git push origin {branch}`",
                "Open a pull request referencing spec/plan/tasks artifacts.",
                "Include acceptance summary and test evidence in the PR description.",
            ]
        )
    elif mode == "local":
        instructions.extend(
            [
                "Switch to your integration branch (e.g., `git checkout main`).",
                "Synchronize it (e.g., `git pull --ff-only`).",
                f"Merge the feature: `git merge {branch}`",
            ]
        )
    else:  # checklist
        instructions.append(
            "All checks passed. Proceed with your manual acceptance workflow."
        )

    if summary.worktree_root != summary.primary_repo_root:
        cleanup_instructions.append(
            f"After merging, remove the worktree: `git worktree remove {summary.worktree_root}`"
        )
    cleanup_instructions.append(
        f"Delete the feature branch when done: `git branch -d {branch}`"
    )

    notes: List[str] = []
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


def normalize_feature_encoding(repo_root: Path, feature: str) -> List[Path]:
    """Normalize file encoding from Windows-1252 to UTF-8.

    Converts Windows-1252 encoded files to UTF-8, replacing Unicode smart
    quotes and special characters with ASCII equivalents for maximum
    compatibility.

    Args:
        repo_root: Repository root path.
        feature: Feature slug.

    Returns:
        List of paths that were rewritten.
    """
    NORMALIZE_MAP = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201A": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u201E": '"',
        "\u2014": "--",
        "\u2013": "-",
        "\u2026": "...",
        "\u00A0": " ",
        "\u2022": "*",
        "\u00B7": "*",
    }

    feature_dir = repo_root / "kitty-specs" / feature
    if not feature_dir.exists():
        return []

    candidates: List[Path] = []
    primary_files = [
        feature_dir / "spec.md",
        feature_dir / "plan.md",
        feature_dir / "quickstart.md",
        feature_dir / "tasks.md",
        feature_dir / "research.md",
        feature_dir / "data-model.md",
    ]
    candidates.extend(p for p in primary_files if p.exists())

    for subdir in [
        feature_dir / "tasks",
        feature_dir / "research",
        feature_dir / "checklists",
    ]:
        if subdir.exists():
            candidates.extend(path for path in subdir.rglob("*.md"))

    rewritten: List[Path] = []
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

        text: Optional[str] = None
        for encoding in ("cp1252", "latin-1"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = data.decode("utf-8", errors="replace")

        text = text.lstrip("\ufeff")

        for unicode_char, ascii_replacement in NORMALIZE_MAP.items():
            text = text.replace(unicode_char, ascii_replacement)

        path.write_text(text, encoding="utf-8")
        rewritten.append(path)

    return rewritten


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "normalize_feature_encoding",
    "perform_acceptance",
]
