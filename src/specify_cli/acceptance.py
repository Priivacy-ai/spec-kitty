#!/usr/bin/env python3
"""Acceptance workflow utilities for Spec Kitty features.

This module is the installed-package entrypoint for the acceptance workflow.
All core logic is delegated to ``specify_cli.core.acceptance_core``.

This module adds:
- Mission-aware path validation (``path_violations``).
- Documentation mission validation (``validate_documentation_mission``).
- Centralized feature detection via ``specify_cli.core.feature_detection``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Optional

# Re-export core data structures so existing callers keep working.
from specify_cli.core.acceptance_core import (
    AcceptanceError,
    AcceptanceMode,
    AcceptanceResult,
    AcceptanceSummary,
    ArtifactEncodingError,
    WorkPackageState,
    choose_mode,
    normalize_feature_encoding,
    perform_acceptance,
)
from specify_cli.core.acceptance_core import (
    collect_feature_summary as _core_collect_feature_summary,
)
from specify_cli.core.feature_detection import (
    FeatureDetectionError,
    detect_feature_slug as centralized_detect_feature_slug,
)
from specify_cli.mission import MissionError, get_mission_for_feature
from specify_cli.validators.documentation import validate_documentation_mission
from specify_cli.validators.paths import PathValidationError, validate_mission_paths


def detect_feature_slug(
    repo_root: Path,
    *,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Detect feature slug using centralized detection.

    This function maintains backward compatibility while delegating
    to the centralized feature detection module.

    Args:
        repo_root: Repository root path
        env: Environment variables (defaults to os.environ)
        cwd: Current working directory (defaults to Path.cwd())

    Returns:
        Feature slug (e.g., "020-my-feature")

    Raises:
        AcceptanceError: If feature slug cannot be determined
    """
    try:
        return centralized_detect_feature_slug(
            repo_root,
            env=env,
            cwd=cwd,
            mode="strict",
        )
    except FeatureDetectionError as e:
        raise AcceptanceError(str(e)) from e


def collect_feature_summary(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool = True,
) -> AcceptanceSummary:
    """Collect feature readiness information with mission-aware path validation.

    Delegates to the shared core and then augments the result with
    ``path_violations`` derived from the feature's mission configuration,
    and documentation mission validation when applicable.

    Args:
        repo_root: Repository root path.
        feature: Feature slug.
        strict_metadata: If True, enforce metadata completeness checks.

    Returns:
        Populated :class:`AcceptanceSummary` (including ``path_violations``).
    """
    summary = _core_collect_feature_summary(
        repo_root, feature, strict_metadata=strict_metadata
    )

    # Mission-aware path validation (CLI-only concern).
    path_violations: List[str] = []
    try:
        mission = get_mission_for_feature(summary.feature_dir)
    except MissionError:
        mission = None

    if mission and mission.config.paths:
        try:
            validate_mission_paths(mission, repo_root, strict=True)
        except PathValidationError as exc:
            message = exc.result.format_errors() or str(exc)
            path_violations.append(message)

    if path_violations:
        summary.path_violations = path_violations
        if "Path conventions not satisfied." not in summary.warnings:
            summary.warnings.append("Path conventions not satisfied.")

    # Documentation mission validation (mission-scoped)
    doc_result = validate_documentation_mission(summary.feature_dir)
    if doc_result.is_documentation_mission and doc_result.has_errors:
        summary.missing_artifacts.extend(doc_result.error_messages())
    if doc_result.is_documentation_mission and doc_result.warning_count > 0:
        for issue in doc_result.issues:
            if issue.issue_type == "warning":
                summary.warnings.append(f"[doc-validation] {issue.message}")

    return summary


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
