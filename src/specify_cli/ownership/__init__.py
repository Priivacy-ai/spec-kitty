"""Ownership manifest module for spec-kitty work packages.

Provides execution mode classification, ownership manifest data types,
validation (no-overlap, prefix consistency), best-effort inference from WP
content, and workspace strategy for planning-artifact WPs.
"""

from __future__ import annotations

from specify_cli.ownership.audit_targets import (
    AUDIT_TEMPLATE_TARGETS,
    get_audit_targets,
    validate_audit_coverage,
)
from specify_cli.ownership.inference import infer_ownership
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest, SCOPE_CODEBASE_WIDE
from specify_cli.ownership.validation import ValidationResult, validate_ownership
from specify_cli.ownership.workspace_strategy import create_planning_workspace

__all__ = [
    "AUDIT_TEMPLATE_TARGETS",
    "ExecutionMode",
    "OwnershipManifest",
    "SCOPE_CODEBASE_WIDE",
    "ValidationResult",
    "get_audit_targets",
    "validate_audit_coverage",
    "validate_ownership",
    "infer_ownership",
    "create_planning_workspace",
]
