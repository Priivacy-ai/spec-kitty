"""Merge state persistence for resume capability.

Implements FR-021 through FR-024: persisting merge state to enable
resuming interrupted merge operations.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "MergeState",
    "save_state",
    "load_state",
    "clear_state",
    "has_active_merge",
    "get_state_path",
    "detect_git_merge_state",
]

STATE_FILE = ".kittify/merge-state.json"


@dataclass
class MergeState:
    """Persisted state for resumable merge operations."""

    feature_slug: str
    target_branch: str
    wp_order: list[str]  # Ordered list of WP IDs to merge
    completed_wps: list[str] = field(default_factory=list)
    current_wp: str | None = None
    has_pending_conflicts: bool = False
    strategy: str = "merge"  # "merge", "squash", "rebase"
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


def get_state_path(repo_root: Path) -> Path:
    """Get path to merge state file."""
    return repo_root / STATE_FILE


def save_state(state: MergeState, repo_root: Path) -> None:
    """Save merge state to JSON file.

    Args:
        state: MergeState to persist
        repo_root: Repository root path
    """
    state_path = get_state_path(repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state.updated_at = datetime.now(UTC).isoformat()

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def load_state(repo_root: Path) -> MergeState | None:
    """Load merge state from JSON file.

    Args:
        repo_root: Repository root path

    Returns:
        MergeState if file exists and is valid, None otherwise
    """
    state_path = get_state_path(repo_root)

    if not state_path.exists():
        return None

    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        return MergeState.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        # Invalid state file - return None, caller should clear
        return None


def clear_state(repo_root: Path) -> bool:
    """Remove merge state file.

    Args:
        repo_root: Repository root path

    Returns:
        True if file was removed, False if it didn't exist
    """
    state_path = get_state_path(repo_root)

    if state_path.exists():
        state_path.unlink()
        return True
    return False


def has_active_merge(repo_root: Path) -> bool:
    """Check if there's an active merge state.

    Returns True if state file exists and has remaining WPs.
    """
    state = load_state(repo_root)
    if state is None:
        return False
    return len(state.remaining_wps) > 0


def detect_git_merge_state(repo_root: Path) -> bool:
    """Check if git has an active merge in progress.

    Uses MERGE_HEAD presence to detect mid-merge state.
    """
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
