"""Ownership manifest module for spec-kitty work packages.

Provides execution mode classification, ownership manifest data types,
validation (no-overlap, prefix consistency), best-effort inference from WP
content, and workspace strategy for planning-artifact WPs.
"""

from __future__ import annotations

from specify_cli.ownership.inference import infer_ownership
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import ValidationResult, validate_ownership
from specify_cli.ownership.workspace_strategy import create_planning_workspace

__all__ = [
    "ExecutionMode",
    "OwnershipManifest",
    "ValidationResult",
    "validate_ownership",
    "infer_ownership",
    "create_planning_workspace",
]
