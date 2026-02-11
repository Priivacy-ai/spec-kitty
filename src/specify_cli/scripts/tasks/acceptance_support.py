#!/usr/bin/env python3
"""Acceptance workflow utilities without external dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

from task_helpers import (
    LANES,
    TaskCliError,
    WorkPackage,
    activity_entries,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    run_git,
    split_frontmatter,
)

AcceptanceMode = str  # Expected values: "pr", "local", "checklist"


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


@dataclass
class WorkPackageState:
    work_package_id: str
    lane: str
    title: str
    path: str
    has_lane_entry: bool
    latest_lane: Optional[str]
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class AcceptanceSummary:
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
    warnings: List[str]

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


def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    """Iterate work packages for a feature.

    Supports both legacy (directory-based) and new (frontmatter-only) lane formats.
    """
    feature_dir = repo_root / "kitty-specs" / feature
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        raise AcceptanceError(f"Feature '{feature}' has no tasks directory at {tasks_dir}.")

    if is_legacy_format(feature_dir):
        # Legacy format: lane determined by subdirectory
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
        # New format: flat directory, lane from frontmatter
        for path in sorted(tasks_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            text = _read_text_strict(path)
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


def detect_feature_slug(
    repo_root: Path,
    *,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Detect feature slug from environment, git branch, or current directory.

    This is a backward-compatible wrapper that delegates to the centralized
    feature detection module (specify_cli.core.feature_detection).

    Priority:
    1. SPECIFY_FEATURE environment variable
    2. Git branch name (if starts with ###-)
    3. Current directory path (walks up looking for .worktrees or ###- pattern)

    Raises:
        AcceptanceError: If feature cannot be auto-detected
    """
    # Note: We can't import centralized_detect_feature_slug here because
    # this file must remain standalone (used in packaged scripts).
    # So we maintain the original implementation for backward compatibility.

    env = env or os.environ
    if "SPECIFY_FEATURE" in env and env["SPECIFY_FEATURE"].strip():
        return env["SPECIFY_FEATURE"].strip()

    try:
        branch = (
            run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True)
            .stdout.strip()
        )
        if branch and branch != "HEAD" and re.match(r"^\d{3}-", branch):
            return branch
    except TaskCliError:
        pass

    cwd = (cwd or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if parent.name.startswith(".worktrees"):
            parts = list(parent.parts)
            try:
                idx = parts.index(".worktrees")
                candidate = parts[idx + 1]
                if re.match(r"^\d{3}-", candidate):
                    return candidate
            except (ValueError, IndexError):
                continue
        if parent.name.startswith("0") and re.match(r"^\d{3}-", parent.name):
            return parent.name

    raise AcceptanceError(
        "Unable to determine feature slug automatically. Provide --feature explicitly."
    )


def _read_file(path: Path) -> str:
    return _read_text_strict(path) if path.exists() else ""


def _read_text_strict(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactEncodingError(path, exc) from exc


def _find_unchecked_tasks(tasks_file: Path) -> List[str]:
    if not tasks_file.exists():
        return ["tasks.md missing"]

    unchecked: List[str] = []
    for line in _read_text_strict(tasks_file).splitlines():
        if re.match(r"^\s*-\s*\[ \]", line):
            unchecked.append(line.strip())
    return unchecked


def _check_needs_clarification(files: Sequence[Path]) -> List[str]:
    results: List[str] = []
    for file_path in files:
        if file_path.exists():
            text = _read_text_strict(file_path)
            if "[NEEDS CLARIFICATION" in text:
                results.append(str(file_path))
    return results


def _missing_artifacts(feature_dir: Path) -> Tuple[List[str], List[str]]:
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


def normalize_feature_encoding(repo_root: Path, feature: str) -> List[Path]:
    """Normalize file encoding from Windows-1252 to UTF-8 with ASCII character mapping.

    Converts Windows-1252 encoded files to UTF-8, replacing Unicode smart quotes
    and special characters with ASCII equivalents for maximum compatibility.
    """
    # Map Unicode characters to ASCII equivalents
    NORMALIZE_MAP = {
        '\u2018': "'",    # Left single quotation mark → apostrophe
        '\u2019': "'",    # Right single quotation mark → apostrophe
        '\u201A': "'",    # Single low-9 quotation mark → apostrophe
        '\u201C': '"',    # Left double quotation mark → straight quote
        '\u201D': '"',    # Right double quotation mark → straight quote
        '\u201E': '"',    # Double low-9 quotation mark → straight quote
        '\u2014': '--',   # Em dash → double hyphen
        '\u2013': '-',    # En dash → hyphen
        '\u2026': '...',  # Horizontal ellipsis → three dots
        '\u00A0': ' ',    # Non-breaking space → regular space
        '\u2022': '*',    # Bullet → asterisk
        '\u00B7': '*',    # Middle dot → asterisk
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

    for subdir in [feature_dir / "tasks", feature_dir / "research", feature_dir / "checklists"]:
        if subdir.exists():
            candidates.extend(path for path in subdir.rglob("*.md"))

    rewritten: List[Path] = []
    seen: Set[Path] = set()
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

        # Strip UTF-8 BOM if present in the text
        text = text.lstrip('\ufeff')

        # Normalize Unicode characters to ASCII equivalents
        for unicode_char, ascii_replacement in NORMALIZE_MAP.items():
            text = text.replace(unicode_char, ascii_replacement)

        path.write_text(text, encoding="utf-8")
        rewritten.append(path)

    return rewritten


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

    try:
        worktree_root = Path(
            run_git(["rev-parse", "--show-toplevel"], cwd=repo_root, check=True)
            .stdout.strip()
        ).resolve()
    except TaskCliError:
        worktree_root = repo_root

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
            elif lane_value != wp.current_lane:
                metadata_issues.append(
                    f"{wp_id}: frontmatter lane '{lane_value}' does not match expected '{wp.current_lane}'"
                )

            if not wp.agent:
                metadata_issues.append(f"{wp_id}: missing agent in frontmatter")
            if wp.current_lane in {"doing", "for_review"} and not wp.assignee:
                metadata_issues.append(f"{wp_id}: missing assignee in frontmatter")
            if not wp.shell_pid:
                metadata_issues.append(f"{wp_id}: missing shell_pid in frontmatter")

        if not entries:
            activity_issues.append(f"{wp_id}: Activity Log missing entries")
        else:
            if wp.current_lane not in lanes_logged:
                activity_issues.append(
                    f"{wp_id}: Activity Log missing entry for lane={wp.current_lane}"
                )
            if wp.current_lane == "done" and entries[-1]["lane"] != "done":
                activity_issues.append(f"{wp_id}: latest Activity Log entry not lane=done")

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
        warnings.append("Optional artifacts missing: " + ", ".join(missing_optional))

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
    if mode != "checklist" and not summary.ok:
        raise AcceptanceError(
            "Acceptance checks failed; run verify to see outstanding issues."
        )

    actor_name = (actor or os.getenv("USER") or os.getenv("USERNAME") or "system").strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_commit: Optional[str] = None
    accept_commit: Optional[str] = None

    if auto_commit and mode != "checklist":
        try:
            parent_commit = (
                run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=False)
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

        history: List[Dict[str, object]] = meta.setdefault("acceptance_history", [])
        history.append(acceptance_record)
        if len(history) > 20:
            meta["acceptance_history"] = history[-20:]

        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run_git(
            ["add", str(meta_path.relative_to(summary.repo_root))],
            cwd=summary.repo_root,
            check=True,
        )

        status = run_git(["diff", "--cached", "--name-only"], cwd=summary.repo_root, check=True)
        staged_files = [line.strip() for line in status.stdout.splitlines() if line.strip()]
        commit_created = False
        if staged_files:
            commit_msg = f"Accept {summary.feature}"
            run_git(["commit", "-m", commit_msg], cwd=summary.repo_root, check=True)
            commit_created = True
            try:
                accept_commit = (
                    run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=True)
                    .stdout.strip()
                )
            except TaskCliError:
                accept_commit = None
        else:
            commit_created = False
    else:
        commit_created = False

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
    cleanup_instructions.append(f"Delete the feature branch when done: `git branch -d {branch}`")

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


__all__ = [
    "AcceptanceError",
    "ArtifactEncodingError",
    "AcceptanceResult",
    "AcceptanceSummary",
    "AcceptanceMode",
    "collect_feature_summary",
    "detect_feature_slug",
    "choose_mode",
    "perform_acceptance",
    "normalize_feature_encoding",
]
