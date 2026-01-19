"""Orchestrator test fixtures.

Available checkpoints:
- wp_created: WPs exist in planned lane
- wp_implemented: WP01 implemented, awaiting review
- review_pending: WP01 in review
- review_rejected: WP01 review rejected
- review_approved: WP01 review approved
- wp_merged: WP01 merged to main

Usage:
    from tests.fixtures.orchestrator import get_checkpoint_path, list_checkpoints

    # Get path to a specific checkpoint
    path = get_checkpoint_path("wp_created")

    # List all available checkpoints
    names = list_checkpoints()

    # Get checkpoint with staleness validation
    path = get_checkpoint_with_validation("wp_created")

    # Validate all checkpoints
    warnings = validate_all_checkpoints()
"""

from pathlib import Path
import json
import warnings

# Directory containing this module (and all checkpoint fixtures)
FIXTURES_DIR = Path(__file__).parent

# Fixture version - update when fixture schema changes
FIXTURES_VERSION = "021.1"

# Checkpoint registry with descriptions
CHECKPOINTS: dict[str, str] = {
    "wp_created": "Initial state with WPs in planned lane",
    "wp_implemented": "WP01 implemented, awaiting review",
    "review_pending": "WP01 submitted for review",
    "review_rejected": "WP01 review rejected, needs re-implementation",
    "review_approved": "WP01 review approved, ready for merge",
    "wp_merged": "WP01 merged to main",
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


def check_fixture_staleness(checkpoint_path: Path) -> tuple[bool, str | None]:
    """Check if a fixture might be stale.

    A fixture is considered stale if:
    - state.json is missing
    - state.json has invalid JSON
    - fixture_version field is missing
    - fixture_version doesn't match FIXTURES_VERSION

    Args:
        checkpoint_path: Path to checkpoint directory

    Returns:
        Tuple of (is_stale, warning_message)
        - is_stale: True if fixture may be stale
        - warning_message: Human-readable warning or None if not stale
    """
    state_file = checkpoint_path / "state.json"
    if not state_file.exists():
        return True, f"Missing state.json in {checkpoint_path}"

    try:
        with open(state_file) as f:
            state = json.load(f)

        # Check for version field
        fixture_version = state.get("fixture_version")
        if fixture_version is None:
            return True, (
                f"Fixture {checkpoint_path.name} has no version field. "
                f"Current version: {FIXTURES_VERSION}"
            )

        if fixture_version != FIXTURES_VERSION:
            return True, (
                f"Fixture {checkpoint_path.name} version mismatch: "
                f"fixture={fixture_version}, current={FIXTURES_VERSION}"
            )

        return False, None

    except json.JSONDecodeError as e:
        return True, f"Invalid JSON in {state_file}: {e}"


def validate_all_checkpoints() -> list[str]:
    """Validate all checkpoints and return any warnings.

    Checks each registered checkpoint for:
    - Directory existence
    - Valid state.json
    - Matching fixture version

    Returns:
        List of warning messages (empty if all valid)
    """
    warnings_list = []

    for name in CHECKPOINTS:
        try:
            path = get_checkpoint_path(name)
            is_stale, warning = check_fixture_staleness(path)
            if is_stale and warning:
                warnings_list.append(warning)
        except ValueError as e:
            warnings_list.append(str(e))

    return warnings_list


def get_checkpoint_with_validation(name: str) -> Path:
    """Get checkpoint path with staleness warning.

    Same as get_checkpoint_path() but emits a UserWarning if the
    fixture may be stale (version mismatch or missing version).

    Args:
        name: Checkpoint name

    Returns:
        Path to checkpoint directory

    Warns:
        UserWarning: If fixture may be stale
    """
    path = get_checkpoint_path(name)
    is_stale, warning = check_fixture_staleness(path)

    if is_stale and warning:
        warnings.warn(warning, UserWarning, stacklevel=2)

    return path
