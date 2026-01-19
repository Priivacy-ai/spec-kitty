"""Orchestrator test fixtures.

Available checkpoints:
- wp_created: WPs exist in planned lane
- wp_implemented: WP01 implemented, awaiting review
- review_pending: WP01 in review
- review_rejected: WP01 review rejected (WP11)
- review_approved: WP01 review approved (WP11)
- wp_merged: WP01 merged to main (WP11)

Usage:
    from tests.fixtures.orchestrator import get_checkpoint_path, list_checkpoints

    # Get path to a specific checkpoint
    path = get_checkpoint_path("wp_created")

    # List all available checkpoints
    names = list_checkpoints()
"""

from pathlib import Path

# Directory containing this module (and all checkpoint fixtures)
FIXTURES_DIR = Path(__file__).parent

# Checkpoint registry with descriptions
# Note: Some checkpoints added by WP11 (Additional Checkpoint Fixtures)
CHECKPOINTS: dict[str, str] = {
    "wp_created": "Initial state with WPs in planned lane",
    "wp_implemented": "WP01 implemented, awaiting review",
    "review_pending": "WP01 submitted for review",
    # Added by WP11:
    # "review_rejected": "WP01 review rejected, needs re-implementation",
    # "review_approved": "WP01 review approved, ready for merge",
    # "wp_merged": "WP01 merged to main",
}


def get_checkpoint_path(name: str) -> Path:
    """Get path to a checkpoint fixture directory.

    Args:
        name: Checkpoint name (e.g., 'wp_created', 'review_pending')

    Returns:
        Path to checkpoint directory containing state.json, feature/, worktrees.json

    Raises:
        ValueError: If checkpoint name is unknown or directory doesn't exist
    """
    if name not in CHECKPOINTS:
        available = ", ".join(sorted(CHECKPOINTS.keys()))
        raise ValueError(f"Unknown checkpoint: {name}. Available: {available}")

    path = FIXTURES_DIR / f"checkpoint_{name}"
    if not path.exists():
        raise ValueError(f"Checkpoint directory missing: {path}")

    return path


def list_checkpoints() -> list[str]:
    """List all available checkpoint names.

    Returns:
        Sorted list of checkpoint names
    """
    return sorted(CHECKPOINTS.keys())


def get_checkpoint_description(name: str) -> str:
    """Get description for a checkpoint.

    Args:
        name: Checkpoint name

    Returns:
        Human-readable description of checkpoint state

    Raises:
        ValueError: If checkpoint name is unknown
    """
    if name not in CHECKPOINTS:
        available = ", ".join(sorted(CHECKPOINTS.keys()))
        raise ValueError(f"Unknown checkpoint: {name}. Available: {available}")

    return CHECKPOINTS[name]


# Version for staleness detection
# Bump this when fixture structure changes
FIXTURES_VERSION = "021.1"
