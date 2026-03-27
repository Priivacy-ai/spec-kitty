"""Schema version gate and compatibility checking for Spec Kitty projects."""

from .schema_version import (
    REQUIRED_SCHEMA_VERSION,
    SCHEMA_CAPABILITIES,
    CompatibilityResult,
    CompatibilityStatus,
    check_compatibility,
    get_project_schema_version,
)
from .gate import check_schema_version

__all__ = [
    "REQUIRED_SCHEMA_VERSION",
    "SCHEMA_CAPABILITIES",
    "CompatibilityResult",
    "CompatibilityStatus",
    "check_compatibility",
    "get_project_schema_version",
    "check_schema_version",
]
