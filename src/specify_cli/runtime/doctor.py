"""Global runtime health checks for spec-kitty doctor.

Provides reusable check functions that detect:
- Missing ~/.kittify/ directory (1A-11)
- version.lock mismatch with CLI version (1A-12)
- Corrupted/missing managed mission directories (1A-13)
- Stale legacy shared assets in project .kittify/ (1A-10)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specify_cli.constitution.resolver import (
    GovernanceResolutionError,
    resolve_governance,
)
from specify_cli.runtime.home import get_kittify_home

# Managed mission directories expected under ~/.kittify/missions/.
# These correspond to the bundled missions shipped with the package.
MANAGED_MISSION_DIRS: tuple[str, ...] = (
    "missions/software-dev",
    "missions/research",
    "missions/documentation",
)


@dataclass
class DoctorCheck:
    """Result of a single doctor health check."""

    name: str
    passed: bool
    message: str
    severity: str  # "error", "warning", "info"


def check_global_runtime_exists() -> DoctorCheck:
    """Check if ~/.kittify/ exists (1A-11)."""
    home = get_kittify_home()
    if home.is_dir():
        return DoctorCheck(
            "global_runtime_exists", True, f"{home} exists", "info"
        )
    return DoctorCheck(
        "global_runtime_exists",
        False,
        f"Missing global runtime: {home}",
        "error",
    )


def check_version_lock() -> DoctorCheck:
    """Check if version.lock matches CLI version (1A-12)."""
    home = get_kittify_home()
    version_file = home / "cache" / "version.lock"
    if not version_file.exists():
        return DoctorCheck(
            "version_lock",
            False,
            "version.lock missing (incomplete update?)",
            "warning",
        )
    from specify_cli import __version__

    stored = version_file.read_text().strip()
    if stored == __version__:
        return DoctorCheck(
            "version_lock",
            True,
            f"Version lock: {stored} (matches CLI)",
            "info",
        )
    return DoctorCheck(
        "version_lock",
        False,
        f"Version mismatch: lock={stored}, CLI={__version__}",
        "warning",
    )


def check_mission_integrity() -> DoctorCheck:
    """Check if all expected managed mission directories exist (1A-13)."""
    home = get_kittify_home()
    missing = []
    for managed_dir in MANAGED_MISSION_DIRS:
        if not (home / managed_dir).is_dir():
            missing.append(managed_dir)
    if not missing:
        return DoctorCheck(
            "mission_integrity",
            True,
            f"{len(MANAGED_MISSION_DIRS)} mission dirs present",
            "info",
        )
    return DoctorCheck(
        "mission_integrity",
        False,
        f"Missing: {', '.join(missing)}",
        "error",
    )


def check_stale_legacy_assets(project_dir: Path) -> DoctorCheck:
    """Count legacy shared assets in project .kittify/ (1A-10)."""
    kittify = project_dir / ".kittify"
    if not kittify.exists():
        return DoctorCheck(
            "stale_legacy", True, "No .kittify/ directory", "info"
        )

    stale_count = 0
    shared_dirs = {"templates", "missions", "scripts", "command-templates"}
    shared_files = {"AGENTS.md"}

    for item in kittify.iterdir():
        if item.name in shared_dirs and item.is_dir():
            stale_count += sum(1 for f in item.rglob("*") if f.is_file())
        elif item.name in shared_files and item.is_file():
            stale_count += 1

    if stale_count == 0:
        return DoctorCheck(
            "stale_legacy", True, "No stale shared assets", "info"
        )
    return DoctorCheck(
        "stale_legacy",
        False,
        f"{stale_count} shared assets could be migrated. Run 'spec-kitty migrate'.",
        "warning",
    )


def check_governance_resolution(project_dir: Path) -> DoctorCheck:
    """Validate constitution-centric governance resolution for this project."""
    try:
        resolution = resolve_governance(project_dir)
    except GovernanceResolutionError as exc:
        return DoctorCheck(
            "governance_resolution",
            False,
            str(exc),
            "error",
        )
    except Exception as exc:
        return DoctorCheck(
            "governance_resolution",
            False,
            f"Could not resolve governance: {exc}",
            "warning",
        )

    if resolution.metadata.get("template_set_source") == "fallback":
        return DoctorCheck(
            "governance_resolution",
            True,
            (
                f"Resolved governance with template fallback '{resolution.template_set}'. "
                "Set doctrine.template_set in constitution to make this explicit."
            ),
            "warning",
        )

    return DoctorCheck(
        "governance_resolution",
        True,
        (
            f"Resolved governance: {len(resolution.agent_profiles)} profile(s), "
            f"{len(resolution.tools)} tool(s), template_set={resolution.template_set}"
        ),
        "info",
    )


def run_global_checks(
    project_dir: Path | None = None,
) -> list[DoctorCheck]:
    """Run all global runtime health checks.

    Args:
        project_dir: Optional project directory for legacy asset detection.

    Returns:
        List of DoctorCheck results.
    """
    checks = [
        check_global_runtime_exists(),
        check_version_lock(),
        check_mission_integrity(),
    ]
    if project_dir:
        checks.append(check_stale_legacy_assets(project_dir))
        checks.append(check_governance_resolution(project_dir))
    return checks
