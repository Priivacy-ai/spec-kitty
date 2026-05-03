"""Workspace context management for runtime visibility.

This module manages persistent workspace context files stored in .kittify/workspaces/.
These files provide runtime visibility into workspace state for LLM agents and CLI tools.

Context files are:
- Created during `spec-kitty implement` command
- Stored in main repo's .kittify/workspaces/ directory
- Readable from both main repo and worktrees (via relative path)
- Cleaned up during merge or explicit workspace deletion

Execution topology is determined by work-package execution mode:
- code_change WPs resolve to a lane worktree
- planning_artifact WPs resolve to the main repository root
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from specify_cli.core.atomic import atomic_write
from specify_cli.ownership.inference import infer_execution_mode, score_execution_mode_signals
from specify_cli.ownership.models import ExecutionMode
from specify_cli.ownership.workspace_strategy import create_planning_workspace
from specify_cli.status.wp_metadata import WPMetadata, read_wp_frontmatter


_FEATURE_CONTEXT_INDEX_CACHE: dict[tuple[str, str], dict[str, WorkspaceContext]] = {}
_FEATURE_WP_METADATA_CACHE: dict[tuple[str, str], dict[str, NormalizedWorkPackage]] = {}
_FEATURE_WP_METADATA_ERROR_CACHE: dict[tuple[str, str], dict[str, ValueError]] = {}
_FEATURE_WP_METADATA_SNAPSHOT_CACHE: dict[tuple[str, str], tuple[tuple[str, int], ...]] = {}


@dataclass(frozen=True)
class NormalizedWorkPackage:
    """Mission-scoped in-memory normalized WP metadata.

    A legacy WP may be missing ``execution_mode`` on disk. This structure keeps
    the normalized typed metadata in memory so every caller sees the same
    classification result for the lifetime of the process.
    """

    wp_id: str
    path: Path
    metadata: WPMetadata
    mode_source: str
    diagnostic: str | None = None


def clear_workspace_resolution_caches() -> None:
    """Invalidate all process-local workspace resolution caches."""
    _FEATURE_CONTEXT_INDEX_CACHE.clear()
    _FEATURE_WP_METADATA_CACHE.clear()
    _FEATURE_WP_METADATA_ERROR_CACHE.clear()
    _FEATURE_WP_METADATA_SNAPSHOT_CACHE.clear()


def _clear_feature_context_index_cache() -> None:
    """Invalidate the process-local feature context index cache."""
    _FEATURE_CONTEXT_INDEX_CACHE.clear()


@dataclass
class WorkspaceContext:
    """
    Runtime context for a work package workspace.

    Provides all information an agent needs to understand workspace state.
    Stored as JSON in .kittify/workspaces/###-feature-lane-x.json
    """

    # Identity
    wp_id: str  # e.g., "WP02"
    mission_slug: str  # e.g., "010-lane-only-runtime"

    # Paths
    worktree_path: str  # Relative path from repo root (e.g., ".worktrees/010-feature-lane-a")
    branch_name: str  # Git branch name (e.g., "kitty/mission-010-feature-lane-a")

    # Base tracking
    base_branch: str  # Branch this was created from (e.g., "kitty/mission-010-feature-lane-a" or "main")
    base_commit: str  # Git SHA this was created from

    # Dependencies
    dependencies: list[str]  # List of WP IDs this depends on (e.g., ["WP01"])

    # Metadata
    created_at: str  # ISO timestamp when workspace was created
    created_by: str  # Command that created this (e.g., "implement-command")
    vcs_backend: str  # "git" or "jj"

    # Lane fields
    lane_id: str  # e.g., "lane-a"
    lane_wp_ids: list[str]  # All WPs assigned to this lane
    current_wp: str | None = None  # Which WP is currently active in the lane

    # Lane-specific test database isolation env vars (FR-006).
    # Empty dict for repo-root planning workspaces (no parallel-lane DB risk).
    # Populated by `lane_test_env(mission_slug, lane_id)` so two parallel
    # SaaS / Django lanes cannot collide on a single shared test DB.
    lane_test_env: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceContext:
        """Create from dictionary (JSON deserialization)."""
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        if not filtered.get("lane_id"):
            raise ValueError("Workspace context is missing required lane_id")
        if not isinstance(filtered.get("lane_wp_ids"), list):
            raise ValueError("Workspace context is missing required lane_wp_ids")
        return cls(**filtered)


@dataclass(frozen=True)
class ResolvedWorkspace:
    """Resolved workspace contract for a work package.

    This describes the execution workspace that owns a work package.
    """

    mission_slug: str
    wp_id: str
    execution_mode: str
    mode_source: str
    resolution_kind: str
    workspace_name: str
    worktree_path: Path
    branch_name: str | None
    lane_id: str | None
    lane_wp_ids: list[str]
    context: WorkspaceContext | None = None

    @property
    def exists(self) -> bool:
        """Return True when the resolved worktree currently exists on disk."""
        return self.worktree_path.exists()


@dataclass(frozen=True)
class ActiveWPResolution:
    """Active WP ownership resolved for a lane branch at guard time."""

    mission_slug: str | None = None
    wp_id: str | None = None
    owned_files: list[str] = field(default_factory=list)
    lane_id: str | None = None
    branch_name: str | None = None
    context_source: str = "absent"
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None
    warnings: list[str] = field(default_factory=list)


def get_workspaces_dir(repo_root: Path) -> Path:
    """Get or create the workspaces context directory.

    Args:
        repo_root: Repository root path

    Returns:
        Path to .kittify/workspaces/ directory
    """
    workspaces_dir = repo_root / ".kittify" / "workspaces"
    workspaces_dir.mkdir(parents=True, exist_ok=True)
    return workspaces_dir


def get_context_path(repo_root: Path, workspace_name: str) -> Path:
    """Get path to workspace context file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        Path to context JSON file
    """
    workspaces_dir = get_workspaces_dir(repo_root)
    return workspaces_dir / f"{workspace_name}.json"


def save_context(repo_root: Path, context: WorkspaceContext) -> Path:
    """Save workspace context to JSON file.

    Args:
        repo_root: Repository root path
        context: Workspace context to save

    Returns:
        Path to saved context file
    """
    workspace_name = f"{context.mission_slug}-{context.lane_id}"
    context_path = get_context_path(repo_root, workspace_name)

    # Write JSON with pretty formatting
    content = json.dumps(context.to_dict(), indent=2) + "\n"
    atomic_write(context_path, content)
    _clear_feature_context_index_cache()

    return context_path


def load_context(repo_root: Path, workspace_name: str) -> WorkspaceContext | None:
    """Load workspace context from JSON file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        WorkspaceContext if file exists, None otherwise
    """
    context_path = get_context_path(repo_root, workspace_name)

    if not context_path.exists():
        return None

    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
        return WorkspaceContext.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        # Malformed context file
        return None


def delete_context(repo_root: Path, workspace_name: str) -> bool:
    """Delete workspace context file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        True if deleted, False if didn't exist
    """
    context_path = get_context_path(repo_root, workspace_name)

    if context_path.exists():
        context_path.unlink()
        _clear_feature_context_index_cache()
        return True

    return False


def list_contexts(repo_root: Path) -> list[WorkspaceContext]:
    """List all workspace contexts.

    Args:
        repo_root: Repository root path

    Returns:
        List of all workspace contexts (empty if none exist)
    """
    workspaces_dir = get_workspaces_dir(repo_root)

    if not workspaces_dir.exists():
        return []

    contexts = []
    for context_file in sorted(workspaces_dir.glob("*.json"), key=lambda path: path.name):
        workspace_name = context_file.stem
        context = load_context(repo_root, workspace_name)
        if context:
            contexts.append(context)

    return contexts


def build_feature_context_index(
    repo_root: Path,
    mission_slug: str,
) -> dict[str, WorkspaceContext]:
    """Index feature contexts by WP ID, expanding lane contexts to all WPs.

    Lane-mode contexts are stored one-per-lane and retain `lane_wp_ids`, so a
    caller asking for WP01 should still find the lane context even after the
    active WP in that lane has advanced to WP02.
    """
    cache_key = (str(repo_root.resolve()), mission_slug)
    cached = _FEATURE_CONTEXT_INDEX_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    index: dict[str, WorkspaceContext] = {}

    for context in list_contexts(repo_root):
        if context.mission_slug != mission_slug:
            continue

        if context.lane_wp_ids:
            for lane_wp_id in context.lane_wp_ids:
                index.setdefault(lane_wp_id, context)

        if context.current_wp:
            index[context.current_wp] = context
        if context.wp_id:
            index.setdefault(context.wp_id, context)

    _FEATURE_CONTEXT_INDEX_CACHE[cache_key] = dict(index)
    return index


def find_context_for_wp(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
) -> WorkspaceContext | None:
    """Return the lane workspace context for a work package."""
    return build_feature_context_index(repo_root, mission_slug).get(wp_id)


def resolve_active_wp_for_branch(
    repo_root: Path,
    branch_name: str,
) -> ActiveWPResolution:
    """Resolve the active WP for a lane branch from canonical status state.

    Shared lane worktrees are reused across sequential WPs. The workspace
    context can therefore identify the lane while its ``current_wp`` field may
    lag behind the canonical task board. This resolver treats canonical status
    as authoritative for the active WP and returns diagnostics instead of
    falling back to stale ownership when the active WP cannot be proven.
    """
    matching_contexts = [
        context
        for context in list_contexts(repo_root)
        if context.branch_name == branch_name
    ]
    if not matching_contexts:
        return ActiveWPResolution(branch_name=branch_name, context_source="absent")

    if len(matching_contexts) > 1:
        lanes = ", ".join(sorted(context.lane_id for context in matching_contexts))
        return ActiveWPResolution(
            branch_name=branch_name,
            context_source="workspace_context",
            diagnostic_code="ACTIVE_WP_CONTEXT_AMBIGUOUS",
            diagnostic_message=(
                "ACTIVE_WP_CONTEXT_AMBIGUOUS: Multiple workspace contexts match "
                f"branch {branch_name}; lanes: {lanes}"
            ),
        )

    context = matching_contexts[0]
    feature_dir = repo_root / "kitty-specs" / context.mission_slug
    lane_wp_ids = _context_lane_wp_ids(context)

    if not feature_dir.is_dir():
        return _active_wp_diagnostic(
            context,
            code="ACTIVE_WP_CONTEXT_MISSING",
            message=f"Mission directory not found: {feature_dir}",
        )

    try:
        from specify_cli.status.lane_reader import get_all_wp_lanes
        from specify_cli.status.models import Lane

        lanes_by_wp = get_all_wp_lanes(feature_dir)
        active_candidates = [
            wp_id
            for wp_id in lane_wp_ids
            if str(lanes_by_wp.get(wp_id)) == Lane.IN_PROGRESS.value
        ]
    except Exception as exc:
        return _active_wp_diagnostic(
            context,
            code="ACTIVE_WP_STATUS_UNAVAILABLE",
            message=f"Could not read canonical status for mission {context.mission_slug}: {exc}",
        )

    if len(active_candidates) != 1:
        candidates = ", ".join(active_candidates) if active_candidates else "none"
        lane_states = ", ".join(
            f"{wp_id}={lanes_by_wp.get(wp_id, 'uninitialized')}"
            for wp_id in lane_wp_ids
        )
        return _active_wp_diagnostic(
            context,
            code="ACTIVE_WP_CONTEXT_AMBIGUOUS",
            message=(
                f"Cannot prove active WP for branch {branch_name}; "
                f"lane_id={context.lane_id}; active candidates: {candidates}; "
                f"lane states: {lane_states}"
            ),
        )

    active_wp_id = active_candidates[0]
    warnings: list[str] = []
    if context.current_wp and context.current_wp != active_wp_id:
        warnings.append(
            "ACTIVE_WP_CONTEXT_STALE: "
            f"workspace context current_wp={context.current_wp}, "
            f"canonical active_wp={active_wp_id}; lane_id={context.lane_id}"
        )

    wp_path = _find_wp_file(feature_dir / "tasks", active_wp_id)
    if wp_path is None:
        return _active_wp_diagnostic(
            context,
            code="ACTIVE_WP_METADATA_MISSING",
            message=f"Could not find task file for active_wp={active_wp_id}",
            wp_id=active_wp_id,
        )

    try:
        metadata, _body = read_wp_frontmatter(wp_path)
    except Exception as exc:
        return _active_wp_diagnostic(
            context,
            code="ACTIVE_WP_METADATA_INVALID",
            message=f"Could not read task frontmatter for active_wp={active_wp_id}: {exc}",
            wp_id=active_wp_id,
        )

    return ActiveWPResolution(
        mission_slug=context.mission_slug,
        wp_id=active_wp_id,
        owned_files=list(metadata.owned_files),
        lane_id=context.lane_id,
        branch_name=branch_name,
        context_source="canonical_status",
        warnings=warnings,
    )


def _context_lane_wp_ids(context: WorkspaceContext) -> list[str]:
    lane_wp_ids = list(context.lane_wp_ids)
    if not lane_wp_ids:
        lane_wp_ids = [wp_id for wp_id in (context.current_wp, context.wp_id) if wp_id]
    return lane_wp_ids


def _active_wp_diagnostic(
    context: WorkspaceContext,
    *,
    code: str,
    message: str,
    wp_id: str | None = None,
) -> ActiveWPResolution:
    return ActiveWPResolution(
        mission_slug=context.mission_slug,
        wp_id=wp_id,
        lane_id=context.lane_id,
        branch_name=context.branch_name,
        context_source="canonical_status",
        diagnostic_code=code,
        diagnostic_message=f"{code}: {message}",
    )


def _find_wp_file(tasks_dir: Path, wp_id: str) -> Path | None:
    if not tasks_dir.is_dir():
        return None
    return next(iter(sorted(tasks_dir.glob(f"{wp_id}*.md"))), None)


def _normalized_feature_cache_key(repo_root: Path, mission_slug: str) -> tuple[str, str]:
    return (str(repo_root.resolve()), mission_slug)


def _normalized_feature_snapshot(tasks_dir: Path) -> tuple[tuple[str, int], ...]:
    if not tasks_dir.is_dir():
        return ()
    snapshot: list[tuple[str, int]] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        snapshot.append((wp_file.name, wp_file.stat().st_mtime_ns))
    return tuple(snapshot)


def _wp_id_from_path(wp_file: Path) -> str:
    match = re.match(r"^(WP\d{2,})(?:[-_.]|$)", wp_file.name)
    if match:
        return match.group(1)
    return wp_file.stem


def _normalize_wp_file(wp_file: Path, mission_slug: str) -> NormalizedWorkPackage:
    metadata, _body = read_wp_frontmatter(wp_file)
    normalized_meta = metadata
    mode_source = "frontmatter"
    diagnostic: str | None = None

    raw_mode = metadata.execution_mode
    if raw_mode is None:
        raw_content = wp_file.read_text(encoding="utf-8")
        planning_score, code_score = score_execution_mode_signals(raw_content, list(metadata.owned_files))
        try:
            inferred_mode = infer_execution_mode(raw_content, list(metadata.owned_files))
            execution_mode = ExecutionMode(inferred_mode)
        except Exception as exc:  # pragma: no cover - defensive; covered by tests via monkeypatch
            raise ValueError(
                "Could not classify execution_mode for legacy work package "
                f"{metadata.work_package_id} in mission {mission_slug}. "
                "Add execution_mode to the WP frontmatter or rerun "
                f"`spec-kitty agent tasks finalize-tasks --mission {mission_slug}`."
            ) from exc

        normalized_meta = normalized_meta.update(execution_mode=str(execution_mode))
        mode_source = "inferred_legacy"
        if planning_score == 0 and code_score == 0:
            diagnostic = (
                f"Inferred execution_mode={execution_mode.value!r} for {metadata.work_package_id} "
                "by default — neither planning nor code signals were present in the WP body. "
                "Add an explicit execution_mode in the WP frontmatter to silence this default."
            )
        else:
            diagnostic = (
                f"Inferred execution_mode={execution_mode.value!r} for {metadata.work_package_id} from existing mission content."
            )
    else:
        try:
            execution_mode = ExecutionMode(raw_mode)
        except ValueError as exc:
            raise ValueError(f"Invalid execution_mode {raw_mode!r} for {metadata.work_package_id} in mission {mission_slug}.") from exc
        normalized_meta = normalized_meta.update(execution_mode=str(execution_mode))

    if normalized_meta.feature_slug != mission_slug:
        normalized_meta = normalized_meta.update(feature_slug=mission_slug)

    return NormalizedWorkPackage(
        wp_id=normalized_meta.work_package_id,
        path=wp_file,
        metadata=normalized_meta,
        mode_source=mode_source,
        diagnostic=diagnostic,
    )


def build_normalized_wp_index(
    repo_root: Path,
    mission_slug: str,
) -> dict[str, NormalizedWorkPackage]:
    """Load and normalize mission WP metadata once per process.

    Normalization is intentionally read-only. Missing ``execution_mode`` values
    for supported historical missions are inferred in memory so downstream
    callers share one canonical classification result.
    """
    cache_key = _normalized_feature_cache_key(repo_root, mission_slug)
    feature_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    snapshot = _normalized_feature_snapshot(tasks_dir)
    cached = _FEATURE_WP_METADATA_CACHE.get(cache_key)
    if cached is not None and _FEATURE_WP_METADATA_SNAPSHOT_CACHE.get(cache_key) == snapshot:
        return dict(cached)

    index: dict[str, NormalizedWorkPackage] = {}
    errors: dict[str, ValueError] = {}

    if not tasks_dir.is_dir():
        _FEATURE_WP_METADATA_CACHE[cache_key] = {}
        _FEATURE_WP_METADATA_ERROR_CACHE[cache_key] = {}
        _FEATURE_WP_METADATA_SNAPSHOT_CACHE[cache_key] = snapshot
        return {}

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            normalized_wp = _normalize_wp_file(wp_file, mission_slug)
        except Exception as exc:
            if isinstance(exc, ValueError):
                error = exc
            else:
                error = ValueError(
                    f"Could not read work package metadata for {_wp_id_from_path(wp_file)} in mission {mission_slug}. Fix malformed frontmatter in {wp_file}."
                )
            errors[_wp_id_from_path(wp_file)] = error
            continue
        index[normalized_wp.wp_id] = normalized_wp

    _FEATURE_WP_METADATA_CACHE[cache_key] = dict(index)
    _FEATURE_WP_METADATA_ERROR_CACHE[cache_key] = dict(errors)
    _FEATURE_WP_METADATA_SNAPSHOT_CACHE[cache_key] = snapshot
    return dict(index)


def get_normalized_wp(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
) -> NormalizedWorkPackage:
    """Return the normalized metadata entry for a work package."""
    cache_key = _normalized_feature_cache_key(repo_root, mission_slug)
    entry = build_normalized_wp_index(repo_root, mission_slug).get(wp_id)
    if entry is None:
        error = _FEATURE_WP_METADATA_ERROR_CACHE.get(cache_key, {}).get(wp_id)
        if error is not None:
            raise error
        raise ValueError(f"Work package {wp_id} was not found under {repo_root / 'kitty-specs' / mission_slug / 'tasks'}")
    return entry


def resolve_workspace_for_wp(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
) -> ResolvedWorkspace:
    """Resolve the real workspace/branch contract for a work package.

    Resolution order:
    1. Normalize WP metadata and execution mode once per process
    2. planning_artifact -> repository root
    3. Existing lane workspace context for code_change
    4. `lanes.json` lane mapping for code_change

    The returned path may not exist yet; callers can inspect `.exists`.
    """
    normalized_wp = get_normalized_wp(repo_root, mission_slug, wp_id)
    execution_mode = ExecutionMode(normalized_wp.metadata.execution_mode or ExecutionMode.CODE_CHANGE)

    if execution_mode == ExecutionMode.PLANNING_ARTIFACT:
        # planning_artifact WPs are first-class lane-owned entities assigned to
        # "lane-planning".  That lane resolves to the main repository checkout.
        # We still call create_planning_workspace() for the path, but we now
        # populate lane_id so the ResolvedWorkspace contract is uniform.
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        from specify_cli.lanes.persistence import read_lanes_json

        planning_workspace = create_planning_workspace(
            mission_slug=mission_slug,
            wp_code=wp_id,
            owned_files=list(normalized_wp.metadata.owned_files),
            repo_root=repo_root,
        )
        # Try to populate lane_wp_ids from lanes.json if available.
        lane_wp_ids: list[str] = []
        feature_dir = repo_root / "kitty-specs" / mission_slug
        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is not None:
            planning_lane = lanes_manifest.lane_for_wp(wp_id)
            if planning_lane is not None:
                lane_wp_ids = list(planning_lane.wp_ids)

        return ResolvedWorkspace(
            mission_slug=mission_slug,
            wp_id=wp_id,
            execution_mode=execution_mode.value,
            mode_source=normalized_wp.mode_source,
            resolution_kind="repo_root",
            workspace_name=f"{mission_slug}-{PLANNING_LANE_ID}",
            worktree_path=planning_workspace,
            branch_name=None,
            lane_id=PLANNING_LANE_ID,
            lane_wp_ids=lane_wp_ids,
            context=None,
        )

    context = find_context_for_wp(repo_root, mission_slug, wp_id)
    if context is not None:
        worktree_path = repo_root / context.worktree_path
        return ResolvedWorkspace(
            mission_slug=mission_slug,
            wp_id=wp_id,
            execution_mode=execution_mode.value,
            mode_source=normalized_wp.mode_source,
            resolution_kind="lane_workspace",
            workspace_name=worktree_path.name,
            worktree_path=worktree_path,
            branch_name=context.branch_name,
            lane_id=context.lane_id,
            lane_wp_ids=list(context.lane_wp_ids),
            context=context,
        )

    feature_dir = repo_root / "kitty-specs" / mission_slug
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import PLANNING_LANE_ID
    from specify_cli.lanes.persistence import require_lanes_json

    lanes_manifest = require_lanes_json(feature_dir)
    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None:
        raise ValueError(f"{wp_id} resolved to execution_mode={execution_mode.value!r} but is not assigned to any lane in {feature_dir / 'lanes.json'}")

    # lane-planning resolves to the main repository checkout, not a .worktrees/ path.
    if lane.lane_id == PLANNING_LANE_ID:
        target_branch = lanes_manifest.target_branch
        return ResolvedWorkspace(
            mission_slug=mission_slug,
            wp_id=wp_id,
            execution_mode=execution_mode.value,
            mode_source=normalized_wp.mode_source,
            resolution_kind="repo_root",
            workspace_name=f"{mission_slug}-{PLANNING_LANE_ID}",
            worktree_path=repo_root,
            branch_name=lane_branch_name(mission_slug, PLANNING_LANE_ID, planning_base_branch=target_branch),
            lane_id=PLANNING_LANE_ID,
            lane_wp_ids=list(lane.wp_ids),
            context=None,
        )

    workspace_name = f"{mission_slug}-{lane.lane_id}"
    return ResolvedWorkspace(
        mission_slug=mission_slug,
        wp_id=wp_id,
        execution_mode=execution_mode.value,
        mode_source=normalized_wp.mode_source,
        resolution_kind="lane_workspace",
        workspace_name=workspace_name,
        worktree_path=repo_root / ".worktrees" / workspace_name,
        branch_name=lane_branch_name(mission_slug, lane.lane_id),
        lane_id=lane.lane_id,
        lane_wp_ids=list(lane.wp_ids),
        context=None,
    )


def resolve_feature_worktree(repo_root: Path, mission_slug: str) -> Path | None:
    """Find a deterministic worktree to operate on for a feature.

    Prefer active lane workspace contexts first, then lane paths inferred from
    `lanes.json`.
    """
    for context in list_contexts(repo_root):
        if context.mission_slug != mission_slug:
            continue
        candidate = repo_root / context.worktree_path
        if candidate.is_dir():
            return candidate

    feature_dir = repo_root / "kitty-specs" / mission_slug
    from specify_cli.lanes.persistence import read_lanes_json

    lanes_manifest = read_lanes_json(feature_dir)

    if lanes_manifest is not None:
        for lane in lanes_manifest.lanes:
            candidate = repo_root / ".worktrees" / f"{mission_slug}-{lane.lane_id}"
            if candidate.is_dir():
                return candidate
    return None


def find_orphaned_contexts(repo_root: Path) -> list[tuple[str, WorkspaceContext]]:
    """Find context files for workspaces that no longer exist.

    Args:
        repo_root: Repository root path

    Returns:
        List of (workspace_name, context) tuples for orphaned contexts
    """
    orphaned = []

    for context in list_contexts(repo_root):
        workspace_path = repo_root / context.worktree_path
        if not workspace_path.exists():
            workspace_name = f"{context.mission_slug}-{context.lane_id}"
            orphaned.append((workspace_name, context))

    return orphaned


def cleanup_orphaned_contexts(repo_root: Path) -> int:
    """Remove context files for deleted workspaces.

    Args:
        repo_root: Repository root path

    Returns:
        Number of orphaned contexts cleaned up
    """
    orphaned = find_orphaned_contexts(repo_root)

    for workspace_name, _ in orphaned:
        delete_context(repo_root, workspace_name)

    return len(orphaned)


__all__ = [
    "ActiveWPResolution",
    "NormalizedWorkPackage",
    "ResolvedWorkspace",
    "WorkspaceContext",
    "build_normalized_wp_index",
    "build_feature_context_index",
    "clear_workspace_resolution_caches",
    "get_normalized_wp",
    "get_workspaces_dir",
    "get_context_path",
    "save_context",
    "load_context",
    "resolve_active_wp_for_branch",
    "delete_context",
    "list_contexts",
    "find_context_for_wp",
    "resolve_workspace_for_wp",
    "resolve_feature_worktree",
    "find_orphaned_contexts",
    "cleanup_orphaned_contexts",
]
