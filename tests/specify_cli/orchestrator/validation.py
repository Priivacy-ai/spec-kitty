"""Validation utilities for orchestrator test results.

Provides functions to validate OrchestrationRun state after tests.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.orchestrator.testing.fixtures import TestContext


@dataclass
class ValidationResult:
    """Result of state validation."""

    valid: bool
    """Whether validation passed."""

    errors: list[str]
    """List of validation errors."""

    warnings: list[str]
    """List of validation warnings (non-fatal)."""

    def __bool__(self) -> bool:
        return self.valid


def validate_state_file(state_path: Path) -> ValidationResult:
    """Validate an OrchestrationRun state file.

    Args:
        state_path: Path to state.json

    Returns:
        ValidationResult with any errors/warnings
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not state_path.exists():
        return ValidationResult(False, ["State file does not exist"], [])

    try:
        with open(state_path) as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        return ValidationResult(False, [f"Invalid JSON: {e}"], [])

    # Required top-level fields
    required_fields = [
        "run_id",
        "feature_slug",
        "started_at",
        "status",
        "wps_total",
        "wps_completed",
        "wps_failed",
        "work_packages",
    ]
    for field in required_fields:
        if field not in state:
            errors.append(f"Missing required field: {field}")

    if errors:
        return ValidationResult(False, errors, warnings)

    # Validate counts
    wps = state.get("work_packages", {})
    actual_completed = sum(1 for wp in wps.values() if wp.get("status") == "done")
    actual_failed = sum(1 for wp in wps.values() if wp.get("status") == "failed")

    if state["wps_completed"] != actual_completed:
        errors.append(
            f"wps_completed mismatch: "
            f"field={state['wps_completed']}, actual={actual_completed}"
        )
    if state["wps_failed"] != actual_failed:
        errors.append(
            f"wps_failed mismatch: "
            f"field={state['wps_failed']}, actual={actual_failed}"
        )
    if state["wps_total"] != len(wps):
        warnings.append(
            f"wps_total ({state['wps_total']}) != work_packages count ({len(wps)})"
        )

    # Validate timestamps
    try:
        datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        errors.append(f"Invalid started_at timestamp: {state.get('started_at')}")

    # Validate each WP
    for wp_id, wp in wps.items():
        if "wp_id" not in wp:
            errors.append(f"WP {wp_id} missing wp_id field")
        elif wp["wp_id"] != wp_id:
            errors.append(f"WP key {wp_id} != wp_id field {wp['wp_id']}")

        if "status" not in wp:
            errors.append(f"WP {wp_id} missing status field")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_lane_consistency(
    feature_dir: Path, state_path: Path
) -> ValidationResult:
    """Validate WP frontmatter lanes match state file.

    Args:
        feature_dir: Path to feature directory
        state_path: Path to state.json

    Returns:
        ValidationResult with any mismatches
    """
    try:
        import yaml
    except ImportError:
        # Fall back to ruamel.yaml if pyyaml not available
        from ruamel.yaml import YAML
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True

        def safe_load(content: str):
            return yaml_parser.load(content)

        yaml = type("yaml", (), {"safe_load": safe_load})()

    errors: list[str] = []
    warnings: list[str] = []

    # Load state
    try:
        with open(state_path) as f:
            state = json.load(f)
    except Exception as e:
        return ValidationResult(False, [f"Cannot load state: {e}"], [])

    # Status to lane mapping
    status_to_lane = {
        "pending": "planned",
        "in_progress": "doing",
        "implementation_complete": "for_review",
        "in_review": "for_review",
        "review_rejected": "doing",
        "review_approved": "for_review",
        "done": "done",
        "failed": "done",
    }

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return ValidationResult(False, ["tasks/ directory not found"], [])

    for wp_file in tasks_dir.glob("WP*.md"):
        wp_id = wp_file.stem
        content = wp_file.read_text()

        # Extract frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            warnings.append(f"{wp_id}: No frontmatter found")
            continue

        try:
            fm = yaml.safe_load(match.group(1))
        except Exception:
            warnings.append(f"{wp_id}: Invalid YAML frontmatter")
            continue

        fm_lane = fm.get("lane")
        state_wp = state.get("work_packages", {}).get(wp_id, {})
        state_status = state_wp.get("status")

        expected_lane = status_to_lane.get(state_status)

        if fm_lane != expected_lane:
            errors.append(
                f"{wp_id}: lane='{fm_lane}' but expected='{expected_lane}' "
                f"(status={state_status})"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_test_result(ctx: "TestContext") -> ValidationResult:
    """Comprehensive validation of test context after orchestration.

    Args:
        ctx: TestContext to validate

    Returns:
        Combined ValidationResult
    """
    all_errors: list[str] = []
    all_warnings: list[str] = []

    # Validate state file
    state_result = validate_state_file(ctx.state_file)
    all_errors.extend(state_result.errors)
    all_warnings.extend(state_result.warnings)

    # Validate lane consistency
    lane_result = validate_lane_consistency(ctx.feature_dir, ctx.state_file)
    all_errors.extend(lane_result.errors)
    all_warnings.extend(lane_result.warnings)

    # Validate temp directory exists
    if not ctx.temp_dir.exists():
        all_errors.append("temp_dir does not exist")

    # Validate repo root has .git
    if not (ctx.repo_root / ".git").exists():
        all_warnings.append("repo_root missing .git directory")

    return ValidationResult(
        valid=len(all_errors) == 0, errors=all_errors, warnings=all_warnings
    )


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result for test output.

    Args:
        result: ValidationResult to format

    Returns:
        Formatted string for test output
    """
    lines = []

    if result.valid:
        lines.append("✓ Validation passed")
    else:
        lines.append("✗ Validation failed")

    if result.errors:
        lines.append("\nErrors:")
        for error in result.errors:
            lines.append(f"  - {error}")

    if result.warnings:
        lines.append("\nWarnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
