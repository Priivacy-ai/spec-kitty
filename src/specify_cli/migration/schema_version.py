"""Schema version detection and compatibility checking for Spec Kitty projects.

This module replaces heuristic version detection with a single integer comparison.
Every project carries a ``spec_kitty.schema_version`` integer in
``.kittify/metadata.yaml``.  The CLI refuses to operate on projects whose schema
version does not match ``REQUIRED_SCHEMA_VERSION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml


# Inclusive range of project schema versions this CLI build supports.
# Both endpoints set to the same value during the no-op activation phase
# (no project is currently blocked by the gate). A later release will bump
# MIN after the migration that retires schemas <MIN ships.
MIN_SUPPORTED_SCHEMA: int = 3
MAX_SUPPORTED_SCHEMA: int = 3

# DEPRECATED: kept for backward-compatible imports. New code should read
# MIN_SUPPORTED_SCHEMA / MAX_SUPPORTED_SCHEMA directly.
REQUIRED_SCHEMA_VERSION: int | None = MIN_SUPPORTED_SCHEMA

# Capabilities introduced by each schema version.
SCHEMA_CAPABILITIES: dict[int, list[str]] = {
    3: ["canonical_context", "event_log_authority", "ownership_manifest", "thin_shims"],
}

# ---------------------------------------------------------------------------
# Canonical "current" stamp targets (issue #840)
# ---------------------------------------------------------------------------
#
# These constants are the single source of truth that ``spec-kitty init``
# stamps into a fresh project's ``.kittify/metadata.yaml``. They MUST agree
# with the schema version and capability set the migration runner targets
# after a clean run (see ``specify_cli.migration.runner``). Keeping both
# code paths bound to the same constants prevents drift between fresh-init
# projects and migrated projects.

#: Schema version a fresh project gets stamped with by ``init``.
CURRENT_SCHEMA_VERSION: int = MAX_SUPPORTED_SCHEMA

#: Capability flags a fresh project gets stamped with by ``init``.
#:
#: This is an additive map of capability-name -> True. The runtime treats a
#: missing key as "off" and a present-True key as "on". It is intentionally
#: a ``dict[str, bool]`` (rather than a list) so operators may extend the
#: map with their own keys without colliding on list ordering. ``init``
#: never overwrites or removes keys an operator has authored.
CURRENT_SCHEMA_CAPABILITIES: dict[str, bool] = {
    name: True for name in SCHEMA_CAPABILITIES[MAX_SUPPORTED_SCHEMA]
}

__all__ = [
    "MIN_SUPPORTED_SCHEMA",
    "MAX_SUPPORTED_SCHEMA",
    "REQUIRED_SCHEMA_VERSION",
    "SCHEMA_CAPABILITIES",
    "CURRENT_SCHEMA_VERSION",
    "CURRENT_SCHEMA_CAPABILITIES",
    "CompatibilityStatus",
    "CompatibilityResult",
    "get_project_schema_version",
    "check_compatibility",
]


class CompatibilityStatus(StrEnum):
    """Outcome of a schema-version compatibility check."""

    COMPATIBLE = "compatible"
    UNMIGRATED = "unmigrated"      # schema_version field absent (legacy project)
    OUTDATED = "outdated"          # project < CLI (must upgrade project)
    CLI_OUTDATED = "cli_outdated"  # project > CLI (must upgrade CLI)


@dataclass
class CompatibilityResult:
    """Structured result returned by ``check_compatibility``."""

    status: CompatibilityStatus
    project_version: int | None
    cli_version: int
    message: str
    exit_code: int

    @property
    def is_compatible(self) -> bool:
        """Return True only when the project and CLI versions match."""
        return self.status == CompatibilityStatus.COMPATIBLE


def get_project_schema_version(repo_root: Path) -> int | None:
    """Read the ``spec_kitty.schema_version`` integer from ``.kittify/metadata.yaml``.

    Args:
        repo_root: Root directory of the project (parent of ``.kittify/``).

    Returns:
        The schema version integer, or ``None`` if the field is absent (legacy
        project that has never been migrated to the schema-version model).
    """
    metadata_path = repo_root / ".kittify" / "metadata.yaml"
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, encoding="utf-8-sig") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None

    if not isinstance(data, dict):
        return None

    spec_kitty = data.get("spec_kitty", {})
    if not isinstance(spec_kitty, dict):
        return None

    raw = spec_kitty.get("schema_version")
    if raw is None:
        return None

    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def check_compatibility(
    project_version: int | None,
    cli_version: int,
) -> CompatibilityResult:
    """Compare project schema version against the CLI's required version.

    Args:
        project_version: Value returned by ``get_project_schema_version``, or
            ``None`` for legacy projects that have no schema_version field.
        cli_version: The CLI's required schema version (``REQUIRED_SCHEMA_VERSION``).

    Returns:
        A ``CompatibilityResult`` describing whether the project can be used
        with this CLI build, with an actionable message and appropriate exit code.
    """
    if project_version is None:
        return CompatibilityResult(
            status=CompatibilityStatus.UNMIGRATED,
            project_version=None,
            cli_version=cli_version,
            message=(
                "Project requires migration. "
                "Run `spec-kitty upgrade` to continue."
            ),
            exit_code=1,
        )

    if project_version < cli_version:
        return CompatibilityResult(
            status=CompatibilityStatus.OUTDATED,
            project_version=project_version,
            cli_version=cli_version,
            message=(
                f"Project schema version {project_version} is outdated. "
                f"Run `spec-kitty upgrade` to update to version {cli_version}."
            ),
            exit_code=1,
        )

    if project_version > cli_version:
        return CompatibilityResult(
            status=CompatibilityStatus.CLI_OUTDATED,
            project_version=project_version,
            cli_version=cli_version,
            message=(
                f"Project schema version {project_version} is newer than this CLI "
                f"supports ({cli_version}). "
                "Upgrade your CLI: `pip install --upgrade spec-kitty-cli`"
            ),
            exit_code=1,
        )

    # project_version == cli_version
    return CompatibilityResult(
        status=CompatibilityStatus.COMPATIBLE,
        project_version=project_version,
        cli_version=cli_version,
        message="",
        exit_code=0,
    )
