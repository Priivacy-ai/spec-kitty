"""Adapter wrapping specify_cli.core.version_checker (WP05)."""

# adapter:no-logic

from __future__ import annotations

from specify_cli.core.version_checker import (
    MismatchType,
    compare_versions,
    format_version_error,
    get_cli_version,
    get_project_version,
    should_check_version,
)

__all__ = [
    "MismatchType",
    "compare_versions",
    "format_version_error",
    "get_cli_version",
    "get_project_version",
    "should_check_version",
]
