"""Merge state persistence for resume capability.

Implements FR-013: per-mission merge state at the canonical runtime location
.kittify/runtime/merge/<mission_id>/state.json with lock support to prevent
concurrent merge operations.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specify_cli.merge.workspace import get_merge_runtime_dir

__all__ = [
    "MergeState",
    "save_state",
    "load_state",
    "clear_state",
    "has_active_merge",
    "get_state_path",
    "acquire_merge_lock",
    "release_merge_lock",
    "is_merge_locked",
    "detect_git_merge_state",
    "abort_git_merge",
]

_STATE_FILE = "state.json"
_LOCK_FILE = "lock"


@dataclass
class MergeState:
    """Persisted state for resumable merge operations."""

    mission_id: str  # Per-mission scoping (e.g. "057-feature-name")
    feature_slug: str  # Display alias for the feature
    target_branch: str
    wp_order: list[str]
    completed_wps: list[str] = field(default_factory=list)
    current_wp: str | None = None
    has_pending_conflicts: bool = False
    strategy: str = "merge"  # "merge", "squash", or "rebase"
    workspace_path: str | None = None  # Absolute path to merge workspace
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeState:
        """Create from dict (loaded JSON)."""
        return cls(**data)

    @property
    def remaining_wps(self) -> list[str]:
        """WPs not yet merged."""
        completed_set = set(self.completed_wps)
        return [wp for wp in self.wp_order if wp not in completed_set]

    @property
    def progress_percent(self) -> float:
        """Completion percentage."""
        if not self.wp_order:
            return 0.0
        return len(self.completed_wps) / len(self.wp_order) * 100

    def mark_wp_complete(self, wp_id: str) -> None:
        """Mark a WP as successfully merged."""
        if wp_id not in self.completed_wps:
            self.completed_wps.append(wp_id)
        self.current_wp = None
        self.has_pending_conflicts = False
        self.updated_at = datetime.now(UTC).isoformat()

    def set_current_wp(self, wp_id: str) -> None:
        """Set the currently-merging WP."""
        self.current_wp = wp_id
        self.updated_at = datetime.now(UTC).isoformat()

    def set_pending_conflicts(self, has_conflicts: bool = True) -> None:
        """Mark that there are pending conflicts to resolve."""
        self.has_pending_conflicts = has_conflicts
        self.updated_at = datetime.now(UTC).isoformat()


def get_state_path(repo_root: Path, mission_id: str | None = None) -> Path:
    """Return the path to the merge state file.

    When mission_id is provided (new canonical location):
        .kittify/runtime/merge/<mission_id>/state.json

    When mission_id is None (legacy compatibility, deprecated):
        .kittify/merge-state.json
    """
    if mission_id is not None:
        return get_merge_runtime_dir(mission_id, repo_root) / _STATE_FILE
    # Legacy path — only used by the CLI's --abort/--resume handlers
    return repo_root / ".kittify" / "merge-state.json"


def save_state(state: MergeState, repo_root: Path) -> None:
    """Persist merge state to .kittify/runtime/merge/<mission_id>/state.json.

    Args:
        state: MergeState to persist (must have mission_id set)
        repo_root: Repository root path
    """
    state_path = get_state_path(repo_root, state.mission_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state.updated_at = datetime.now(UTC).isoformat()

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def load_state(repo_root: Path, mission_id: str | None = None) -> MergeState | None:
    """Load merge state from the canonical runtime location.

    Args:
        repo_root: Repository root path
        mission_id: If given, load from the per-mission path; otherwise scan
                    for the first active state file under .kittify/runtime/merge/.

    Returns:
        MergeState if found and valid, None otherwise
    """
    if mission_id is not None:
        return _load_state_file(get_state_path(repo_root, mission_id))

    # Scan for any active state file
    runtime_merge_dir = repo_root / ".kittify" / "runtime" / "merge"
    if runtime_merge_dir.exists():
        for candidate in sorted(runtime_merge_dir.iterdir()):
            state_file = candidate / _STATE_FILE
            state = _load_state_file(state_file)
            if state is not None:
                return state

    return None


def _load_state_file(state_path: Path) -> MergeState | None:
    """Load and parse a single state JSON file."""
    if not state_path.exists():
        return None
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        return MergeState.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def clear_state(repo_root: Path, mission_id: str | None = None) -> bool:
    """Remove merge state file.

    Args:
        repo_root: Repository root path
        mission_id: If given, clear only that mission's state.

    Returns:
        True if a file was removed, False if it didn't exist
    """
    if mission_id is not None:
        state_path = get_state_path(repo_root, mission_id)
        if state_path.exists():
            state_path.unlink()
            return True
        return False

    # Clear the first active state found
    runtime_merge_dir = repo_root / ".kittify" / "runtime" / "merge"
    if runtime_merge_dir.exists():
        for candidate in sorted(runtime_merge_dir.iterdir()):
            state_file = candidate / _STATE_FILE
            if state_file.exists():
                state_file.unlink()
                return True

    return False


def has_active_merge(repo_root: Path, mission_id: str | None = None) -> bool:
    """Check if there is an active merge state with remaining WPs.

    Args:
        repo_root: Repository root path
        mission_id: If given, check only that mission's state.
    """
    state = load_state(repo_root, mission_id)
    if state is None:
        return False
    return len(state.remaining_wps) > 0


# ---------------------------------------------------------------------------
# Lock management
# ---------------------------------------------------------------------------

def acquire_merge_lock(mission_id: str, repo_root: Path) -> bool:
    """Create a lock file to prevent concurrent merge operations.

    Args:
        mission_id: Mission/feature slug identifier
        repo_root: Repository root path

    Returns:
        True if the lock was acquired, False if already locked
    """
    lock_path = get_merge_runtime_dir(mission_id, repo_root) / _LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        return False

    lock_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    return True


def release_merge_lock(mission_id: str, repo_root: Path) -> None:
    """Remove the merge lock file.

    Args:
        mission_id: Mission/feature slug identifier
        repo_root: Repository root path
    """
    lock_path = get_merge_runtime_dir(mission_id, repo_root) / _LOCK_FILE
    if lock_path.exists():
        lock_path.unlink()


def is_merge_locked(mission_id: str, repo_root: Path) -> bool:
    """Check whether a merge lock file exists for the given mission.

    Args:
        mission_id: Mission/feature slug identifier
        repo_root: Repository root path
    """
    lock_path = get_merge_runtime_dir(mission_id, repo_root) / _LOCK_FILE
    return lock_path.exists()


# ---------------------------------------------------------------------------
# Git merge state helpers (unchanged from original)
# ---------------------------------------------------------------------------

def detect_git_merge_state(repo_root: Path) -> bool:
    """Check if git has an active merge in progress via MERGE_HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def abort_git_merge(repo_root: Path) -> bool:
    """Abort an in-progress git merge.

    Returns:
        True if merge was aborted, False if no merge was in progress
    """
    if not detect_git_merge_state(repo_root):
        return False

    subprocess.run(
        ["git", "merge", "--abort"],
        cwd=str(repo_root),
        check=False,
    )
    return True
