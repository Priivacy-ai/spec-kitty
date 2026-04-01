#!/usr/bin/env python3
"""Acceptance workflow utilities for Spec Kitty features."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

from .tasks_support import (
    LANES,
    TaskCliError,
    WorkPackage,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    run_git,
    split_frontmatter,
)
from specify_cli.status.store import EVENTS_FILENAME, StoreError
from specify_cli.feature_metadata import load_meta, record_acceptance, write_meta
from specify_cli.mission import MissionError, get_mission_for_feature
from specify_cli.validators.paths import PathValidationError, validate_mission_paths
from specify_cli.core.paths import require_explicit_feature as _require_explicit_feature
from specify_cli.core.agent_config import get_auto_commit_default

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
    path_violations: List[str]
    warnings: List[str]

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


def detect_feature_slug(
    repo_root: Path,
    *,
    explicit_feature: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,  # noqa: ARG001 -- kept for signature compat
    cwd: Optional[Path] = None,  # noqa: ARG001 -- kept for signature compat
    announce_fallback: bool = True,  # noqa: ARG001 -- kept for signature compat
) -> str:
    """Require an explicit feature slug; no auto-detection.

    Args:
        repo_root: Repository root path (unused — kept for signature compatibility)
        explicit_feature: Feature slug to use (required).
        env: Unused; kept for backward-compatible call sites.
        cwd: Unused; kept for backward-compatible call sites.
        announce_fallback: Unused; kept for backward-compatible call sites.

    Returns:
        Feature slug (e.g., "020-my-feature")

    Raises:
        AcceptanceError: If no explicit feature slug is provided.
    """
    try:
        return _require_explicit_feature(explicit_feature, command_hint="--feature <slug>")
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
        text = text.lstrip("\ufeff")

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
        branch_value = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True).stdout.strip()
        if branch_value and branch_value != "HEAD":
            branch = branch_value
    except TaskCliError:
        branch = None

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

    # Capture git cleanliness before any status inspection. Query paths must
    # not rewrite derived files like status.json.
    try:
        git_dirty = git_status_lines(repo_root)
    except TaskCliError:
        git_dirty = []

    lanes: Dict[str, List[str]] = {lane: [] for lane in LANES}
    work_packages: List[WorkPackageState] = []
    metadata_issues: List[str] = []
    activity_issues: List[str] = []

    use_legacy = is_legacy_format(feature_dir)

    # ── Canonical state validation via reducer-only snapshot ──────────────
    events_path = feature_dir / EVENTS_FILENAME
    if not events_path.exists():
        activity_issues.append(
            f"No canonical state found for feature '{feature}'. "
            "Cannot validate acceptance without status.events.jsonl. "
            "Run status migration to bootstrap the event log."
        )
        snapshot_wps: Dict[str, dict] = {}
    else:
        try:
            from specify_cli.status.reducer import reduce
            from specify_cli.status.store import read_events

            snapshot = reduce(read_events(feature_dir))
        except StoreError as exc:
            raise AcceptanceError(f"Status event log is corrupted for feature '{feature}': {exc}") from exc
        snapshot_wps = snapshot.work_packages
        if not snapshot_wps:
            activity_issues.append(
                f"No canonical state found for feature '{feature}'. "
                "Cannot validate acceptance without status.events.jsonl. "
                "Run status migration to bootstrap the event log."
            )

    # Collect WP IDs from task files
    from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

    expected_wp_ids: List[str] = []
    try:
        wp_iter = list(_iter_work_packages(repo_root, feature))
    except CanonicalStatusNotFoundError:
        # Event log missing — already reported in activity_issues above.
        # Cannot iterate WPs without canonical state.
        logger.warning("Skipping WP iteration for '%s' — no event log", feature)
        wp_iter = []
    for wp in wp_iter:
        wp_id = wp.work_package_id or wp.path.stem
        title = (wp.title or "").strip('"')
        expected_wp_ids.append(wp_id)

        # Check canonical state for this WP
        wp_snapshot = snapshot_wps.get(wp_id)
        canonical_lane = wp_snapshot.get("lane") if wp_snapshot else None
        has_lane_entry = canonical_lane is not None
        latest_lane = canonical_lane

        # Use canonical lane for bucketing (event log is sole authority).
        bucket_lane = canonical_lane if canonical_lane is not None else "planned"
        if bucket_lane in lanes:
            lanes[bucket_lane].append(wp_id)
        else:
            lanes["planned"].append(wp_id)

        metadata: Dict[str, Optional[str]] = {
            "lane": canonical_lane,
            "agent": wp.agent,
            "assignee": wp.assignee,
            "shell_pid": wp.shell_pid,
        }

        if strict_metadata:
            if not wp.agent:
                metadata_issues.append(f"{wp_id}: missing agent in frontmatter")
            if canonical_lane in {"doing", "in_progress", "for_review"} and not wp.assignee:
                metadata_issues.append(f"{wp_id}: missing assignee in frontmatter")
            if not wp.shell_pid:
                metadata_issues.append(f"{wp_id}: missing shell_pid in frontmatter")

        work_packages.append(
            WorkPackageState(
                work_package_id=wp_id,
                lane=bucket_lane,
                title=title,
                path=str(wp.path.relative_to(repo_root)),
                has_lane_entry=has_lane_entry,
                latest_lane=latest_lane,
                metadata=metadata,
            )
        )

    # Validate canonical state for all WPs (only if event log exists and has events)
    if events_path.exists() and snapshot_wps:
        for wp_id in expected_wp_ids:
            wp_snapshot = snapshot_wps.get(wp_id)
            if wp_snapshot is None:
                activity_issues.append(f"{wp_id}: no canonical state found in status.events.jsonl")
            elif wp_snapshot.get("lane") != "done":
                activity_issues.append(f"{wp_id}: canonical lane is '{wp_snapshot.get('lane')}', expected 'done'")

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

    path_violations: List[str] = []
    try:
        mission = get_mission_for_feature(feature_dir)
    except MissionError:
        mission = None

    if mission and mission.config.paths:
        try:
            validate_mission_paths(mission, repo_root, strict=True)
        except PathValidationError as exc:
            message = exc.result.format_errors() or str(exc)
            path_violations.append(message)

    warnings: List[str] = []
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


def choose_mode(preference: Optional[str], repo_root: Path) -> AcceptanceMode:
    if preference in {"pr", "local", "checklist"}:
        return preference
    try:
        remotes = run_git(["remote"], cwd=repo_root, check=False).stdout.strip().splitlines()
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
    auto_commit: Optional[bool] = None,
) -> AcceptanceResult:
    # Resolve auto_commit: explicit value wins, then project config, then default True
    if auto_commit is None:
        auto_commit = get_auto_commit_default(summary.repo_root)

    if mode != "checklist" and not summary.ok:
        raise AcceptanceError("Acceptance checks failed; run verify to see outstanding issues.")

    actor_name = (actor or os.getenv("USER") or os.getenv("USERNAME") or "system").strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_commit: Optional[str] = None
    accept_commit: Optional[str] = None

    if auto_commit and mode != "checklist":
        try:
            parent_commit = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=False).stdout.strip() or None
        except TaskCliError:
            parent_commit = None

        record_acceptance(
            summary.feature_dir,
            accepted_by=actor_name,
            mode=mode,
            from_commit=parent_commit,
            accept_commit=None,
        )

        meta_path = summary.feature_dir / "meta.json"
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
                accept_commit = run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=True).stdout.strip()
            except TaskCliError:
                accept_commit = None
            # Persist commit SHA to meta.json
            if accept_commit:
                _meta = load_meta(summary.feature_dir)
                if _meta is not None:
                    _meta["accept_commit"] = accept_commit
                    _history = _meta.get("acceptance_history", [])
                    if _history:
                        _history[-1]["accept_commit"] = accept_commit
                    write_meta(summary.feature_dir, _meta)
        else:
            commit_created = False
    else:
        commit_created = False

    instructions: List[str] = []
    cleanup_instructions: List[str] = []

    branch = summary.branch or summary.feature

    # Determine whether `branch` is the integration/target branch itself.
    # If so, merge and branch-deletion guidance is nonsensical and dangerous
    # (e.g. "git merge main" or "git branch -d main" when already on main).
    _WELL_KNOWN_INTEGRATION_BRANCHES = frozenset({
        "main", "master", "develop", "development", "2.x", "3.x",
    })
    _meta = load_meta(summary.feature_dir)
    _target_branch = (_meta or {}).get("target_branch")
    _is_integration_branch = (
        branch == _target_branch
        or (_target_branch is None and branch in _WELL_KNOWN_INTEGRATION_BRANCHES)
    )

    if mode == "pr":
        if _is_integration_branch:
            instructions.append(
                f"Acceptance recorded on integration branch `{branch}`. "
                "Push and open a pull request if needed."
            )
        else:
            instructions.extend(
                [
                    f"Review the acceptance commit on branch `{branch}`.",
                    f"Push your branch: `git push origin {branch}`",
                    "Open a pull request referencing spec/plan/tasks artifacts.",
                    "Include acceptance summary and test evidence in the PR description.",
                ]
            )
    elif mode == "local":
        if _is_integration_branch:
            instructions.append(
                f"Acceptance recorded directly on `{branch}`. No merge needed."
            )
        else:
            instructions.extend(
                [
                    "Switch to your integration branch (e.g., `git checkout main`).",
                    "Synchronize it (e.g., `git pull --ff-only`).",
                    f"Merge the feature: `git merge {branch}`",
                ]
            )
    else:  # checklist
        instructions.append("All checks passed. Proceed with your manual acceptance workflow.")

    if summary.worktree_root != summary.primary_repo_root:
        cleanup_instructions.append(
            f"After merging, remove the worktree: `git worktree remove {summary.worktree_root}`"
        )
    if not _is_integration_branch:
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
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_feature_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
