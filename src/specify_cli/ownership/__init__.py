"""Ownership manifest module for spec-kitty work packages.

Provides execution mode classification, ownership manifest data types,
validation (no-overlap, prefix consistency), and best-effort inference
from WP content.
"""

from __future__ import annotations

from specify_cli.ownership.inference import infer_ownership
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import ValidationResult, validate_ownership

__all__ = [
    "ExecutionMode",
    "OwnershipManifest",
    "ValidationResult",
    "validate_ownership",
    "infer_ownership",
]
