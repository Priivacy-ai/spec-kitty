"""State management for orchestration runs.

This module handles:
    - OrchestrationRun and WPExecution dataclasses
    - State persistence to .kittify/orchestration-state.json
    - State loading for resume capability
    - State updates during execution
    - Active orchestration detection
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from specify_cli.orchestrator.config import OrchestrationStatus, WPStatus

logger = logging.getLogger(__name__)

# State file location
STATE_FILENAME = "orchestration-state.json"
STATE_BACKUP_SUFFIX = ".bak"


# =============================================================================
# Exceptions
# =============================================================================


class StateValidationError(Exception):
    """Raised when state validation fails."""

    pass


class StateLoadError(Exception):
    """Raised when state cannot be loaded."""

    pass


# =============================================================================
# WPExecution Dataclass (T018)
# =============================================================================


@dataclass
class WPExecution:
    """Tracks individual work package execution state.

    Captures all relevant information for a single WP's progression
    through implementation and review phases.
    """

    wp_id: str
    status: WPStatus = WPStatus.PENDING

    # Implementation phase
    implementation_agent: str | None = None
    implementation_started: datetime | None = None
    implementation_completed: datetime | None = None
    implementation_exit_code: int | None = None
    implementation_retries: int = 0

    # Review phase
    review_agent: str | None = None
    review_started: datetime | None = None
    review_completed: datetime | None = None
    review_exit_code: int | None = None
    review_retries: int = 0
    review_feedback: str | None = None  # Feedback from rejected review for re-implementation

    # Output tracking
    log_file: Path | None = None
    worktree_path: Path | None = None

    # Error tracking
    last_error: str | None = None
    fallback_agents_tried: list[str] = field(default_factory=list)

    # Restart tracking (for orphan/intermediate state detection)
    restart_count: int = 0

    def validate(self) -> None:
        """Validate state transitions per data-model.md rules.

        Raises:
            StateValidationError: If state is invalid.
        """
        # Implementation completion requires start
        if self.implementation_completed and not self.implementation_started:
            raise StateValidationError(
                f"WP {self.wp_id}: implementation_completed requires implementation_started"
            )

        # Review start requires implementation completion
        if self.review_started and not self.implementation_completed:
            raise StateValidationError(
                f"WP {self.wp_id}: review_started requires implementation_completed"
            )

        # Review completion requires review start
        if self.review_completed and not self.review_started:
            raise StateValidationError(
                f"WP {self.wp_id}: review_completed requires review_started"
            )

        # COMPLETED status requires review_completed (or single-agent mode)
        if self.status == WPStatus.COMPLETED:
            if not self.implementation_completed:
                raise StateValidationError(
                    f"WP {self.wp_id}: COMPLETED status requires implementation_completed"
                )

        # IMPLEMENTATION status requires implementation_started
        if self.status == WPStatus.IMPLEMENTATION and not self.implementation_started:
            raise StateValidationError(
                f"WP {self.wp_id}: IMPLEMENTATION status requires implementation_started"
            )

        # REVIEW status requires review_started
        if self.status == WPStatus.REVIEW and not self.review_started:
            raise StateValidationError(
                f"WP {self.wp_id}: REVIEW status requires review_started"
            )

        # REWORK status requires review_feedback (rejection reason)
        if self.status == WPStatus.REWORK and not self.review_feedback:
            raise StateValidationError(
                f"WP {self.wp_id}: REWORK status requires review_feedback"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "wp_id": self.wp_id,
            "status": self.status.value,
            "implementation_agent": self.implementation_agent,
            "implementation_started": (
                self.implementation_started.isoformat()
                if self.implementation_started
                else None
            ),
            "implementation_completed": (
                self.implementation_completed.isoformat()
                if self.implementation_completed
                else None
            ),
            "implementation_exit_code": self.implementation_exit_code,
            "implementation_retries": self.implementation_retries,
            "review_agent": self.review_agent,
            "review_started": (
                self.review_started.isoformat() if self.review_started else None
            ),
            "review_completed": (
                self.review_completed.isoformat() if self.review_completed else None
            ),
            "review_exit_code": self.review_exit_code,
            "review_retries": self.review_retries,
            "review_feedback": self.review_feedback,
            "log_file": str(self.log_file) if self.log_file else None,
            "worktree_path": str(self.worktree_path) if self.worktree_path else None,
            "last_error": self.last_error,
            "fallback_agents_tried": self.fallback_agents_tried,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WPExecution":
        """Deserialize from dict."""
        return cls(
            wp_id=data["wp_id"],
            status=WPStatus(data.get("status", "pending")),
            implementation_agent=data.get("implementation_agent"),
            implementation_started=(
                datetime.fromisoformat(data["implementation_started"])
                if data.get("implementation_started")
                else None
            ),
            implementation_completed=(
                datetime.fromisoformat(data["implementation_completed"])
                if data.get("implementation_completed")
                else None
            ),
            implementation_exit_code=data.get("implementation_exit_code"),
            implementation_retries=data.get("implementation_retries", 0),
            review_agent=data.get("review_agent"),
            review_started=(
                datetime.fromisoformat(data["review_started"])
                if data.get("review_started")
                else None
            ),
            review_completed=(
                datetime.fromisoformat(data["review_completed"])
                if data.get("review_completed")
                else None
            ),
            review_exit_code=data.get("review_exit_code"),
            review_retries=data.get("review_retries", 0),
            review_feedback=data.get("review_feedback"),
            log_file=Path(data["log_file"]) if data.get("log_file") else None,
            worktree_path=(
                Path(data["worktree_path"]) if data.get("worktree_path") else None
            ),
            last_error=data.get("last_error"),
            fallback_agents_tried=data.get("fallback_agents_tried", []),
        )


# =============================================================================
# OrchestrationRun Dataclass (T017)
# =============================================================================


@dataclass
class OrchestrationRun:
    """Tracks complete orchestration execution state.

    This is the top-level state object persisted to disk, containing
    all information needed to resume an interrupted orchestration.
    """

    run_id: str
    feature_slug: str
    started_at: datetime
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    completed_at: datetime | None = None

    # Configuration snapshot
    config_hash: str = ""
    concurrency_limit: int = 5

    # Progress tracking
    wps_total: int = 0
    wps_completed: int = 0
    wps_failed: int = 0

    # Metrics
    parallel_peak: int = 0
    total_agent_invocations: int = 0

    # Work package states
    work_packages: dict[str, WPExecution] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate overall orchestration state.

        Raises:
            StateValidationError: If state is invalid.
        """
        # Validate each WP
        for wp in self.work_packages.values():
            wp.validate()

        # Completed count should match
        completed_count = sum(
            1
            for wp in self.work_packages.values()
            if wp.status == WPStatus.COMPLETED
        )
        if completed_count != self.wps_completed:
            logger.warning(
                f"wps_completed mismatch: stored={self.wps_completed}, "
                f"actual={completed_count}"
            )

        # Failed count should match
        failed_count = sum(
            1
            for wp in self.work_packages.values()
            if wp.status == WPStatus.FAILED
        )
        if failed_count != self.wps_failed:
            logger.warning(
                f"wps_failed mismatch: stored={self.wps_failed}, "
                f"actual={failed_count}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "run_id": self.run_id,
            "feature_slug": self.feature_slug,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "status": self.status.value,
            "config_hash": self.config_hash,
            "concurrency_limit": self.concurrency_limit,
            "wps_total": self.wps_total,
            "wps_completed": self.wps_completed,
            "wps_failed": self.wps_failed,
            "parallel_peak": self.parallel_peak,
            "total_agent_invocations": self.total_agent_invocations,
            "work_packages": {
                wp_id: wp.to_dict() for wp_id, wp in self.work_packages.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrchestrationRun":
        """Deserialize from dict."""
        work_packages = {
            wp_id: WPExecution.from_dict(wp_data)
            for wp_id, wp_data in data.get("work_packages", {}).items()
        }

        return cls(
            run_id=data["run_id"],
            feature_slug=data["feature_slug"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            status=OrchestrationStatus(data.get("status", "pending")),
            config_hash=data.get("config_hash", ""),
            concurrency_limit=data.get("concurrency_limit", 5),
            wps_total=data.get("wps_total", 0),
            wps_completed=data.get("wps_completed", 0),
            wps_failed=data.get("wps_failed", 0),
            parallel_peak=data.get("parallel_peak", 0),
            total_agent_invocations=data.get("total_agent_invocations", 0),
            work_packages=work_packages,
        )


# =============================================================================
# JSON Serialization Helpers (T021)
# =============================================================================


def _json_serializer(obj: Any) -> Any:
    """JSON serializer for datetime and Path objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically via temp file rename.

    Creates a backup of existing state before writing.
    Uses atomic rename to ensure either old or new state exists,
    never a partial write.

    Args:
        path: Target file path.
        data: Data to serialize as JSON.
    """
    # Create backup of existing state
    if path.exists():
        backup_path = path.with_suffix(path.suffix + STATE_BACKUP_SUFFIX)
        try:
            shutil.copy2(path, backup_path)
        except OSError as e:
            logger.warning(f"Failed to create backup: {e}")

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (ensures same filesystem for atomic rename)
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".orchestration-state-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=_json_serializer)
        # Atomic rename
        os.rename(temp_path, path)
        logger.debug(f"State saved to {path}")
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


# =============================================================================
# State Persistence Functions (T020)
# =============================================================================


def get_state_path(repo_root: Path) -> Path:
    """Get the path to the state file.

    Args:
        repo_root: Repository root directory.

    Returns:
        Path to orchestration-state.json.
    """
    return repo_root / ".kittify" / STATE_FILENAME


def save_state(state: OrchestrationRun, repo_root: Path) -> None:
    """Save orchestration state to JSON file.

    Uses atomic writes to prevent corruption on crash.

    Args:
        state: Orchestration state to save.
        repo_root: Repository root directory.
    """
    state_file = get_state_path(repo_root)
    data = state.to_dict()
    _atomic_write(state_file, data)
    logger.info(f"Saved orchestration state for {state.feature_slug}")


def load_state(repo_root: Path) -> OrchestrationRun | None:
    """Load orchestration state from JSON file.

    Args:
        repo_root: Repository root directory.

    Returns:
        Loaded OrchestrationRun or None if no state file exists.

    Raises:
        StateLoadError: If state file exists but cannot be parsed.
    """
    state_file = get_state_path(repo_root)
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            data = json.load(f)
        state = OrchestrationRun.from_dict(data)
        logger.info(f"Loaded orchestration state for {state.feature_slug}")
        return state
    except json.JSONDecodeError as e:
        raise StateLoadError(f"Failed to parse state file: {e}")
    except KeyError as e:
        raise StateLoadError(f"Missing required field in state file: {e}")
    except Exception as e:
        raise StateLoadError(f"Failed to load state: {e}")


def has_active_orchestration(repo_root: Path) -> bool:
    """Check if there's an active (running/paused) orchestration.

    Args:
        repo_root: Repository root directory.

    Returns:
        True if an orchestration is running or paused.
    """
    state = load_state(repo_root)
    if state is None:
        return False
    return state.status in [OrchestrationStatus.RUNNING, OrchestrationStatus.PAUSED]


def clear_state(repo_root: Path) -> None:
    """Remove state file and its backup.

    Args:
        repo_root: Repository root directory.
    """
    state_file = get_state_path(repo_root)
    backup_file = state_file.with_suffix(state_file.suffix + STATE_BACKUP_SUFFIX)

    if state_file.exists():
        state_file.unlink()
        logger.info(f"Removed state file: {state_file}")

    if backup_file.exists():
        backup_file.unlink()
        logger.debug(f"Removed backup file: {backup_file}")


def restore_from_backup(repo_root: Path) -> OrchestrationRun | None:
    """Attempt to restore state from backup file.

    Useful if the main state file was corrupted.

    Args:
        repo_root: Repository root directory.

    Returns:
        Restored OrchestrationRun or None if backup doesn't exist.
    """
    state_file = get_state_path(repo_root)
    backup_file = state_file.with_suffix(state_file.suffix + STATE_BACKUP_SUFFIX)

    if not backup_file.exists():
        return None

    try:
        with open(backup_file) as f:
            data = json.load(f)
        state = OrchestrationRun.from_dict(data)
        logger.info(f"Restored orchestration state from backup for {state.feature_slug}")
        return state
    except Exception as e:
        logger.error(f"Failed to restore from backup: {e}")
        return None
