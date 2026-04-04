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
        return DoctorCheck("global_runtime_exists", True, f"{home} exists", "info")
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
        return DoctorCheck("stale_legacy", True, "No .kittify/ directory", "info")

    stale_count = 0
    shared_dirs = {"templates", "missions", "scripts", "command-templates"}
    shared_files = {"AGENTS.md"}

    for item in kittify.iterdir():
        if item.name in shared_dirs and item.is_dir():
            stale_count += sum(1 for f in item.rglob("*") if f.is_file())
        elif item.name in shared_files and item.is_file():
            stale_count += 1

    if stale_count == 0:
        return DoctorCheck("stale_legacy", True, "No stale shared assets", "info")
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
            f"Resolved governance: {len(resolution.paradigms)} paradigm(s), "
            f"{len(resolution.directives)} directive(s), "
            f"{len(resolution.tools)} tool(s), template_set={resolution.template_set}"
        ),
        "info",
    )


def check_command_file_health(project_path: Path) -> list[dict]:
    """Check all agent command files for correctness.

    For each configured agent and each of the 16 consumer commands, this
    function verifies that:

    - The command file exists.
    - The file starts with the current ``<!-- spec-kitty-command-version: X.Y.Z -->``
      marker (stale or missing marker indicates a file that needs regeneration).
    - The file type is correct: prompt-driven commands should be long (>50 non-empty
      lines) and CLI-driven commands should be short (<10 non-empty lines).

    Args:
        project_path: Root directory of the project.

    Returns:
        List of issue dicts, each with keys:
        ``agent``, ``command``, ``file``, ``issue``, ``severity``.
        An empty list means all files are healthy.
    """
    try:
        from specify_cli import __version__
        from specify_cli.agent_utils.directories import (
            AGENT_DIR_TO_KEY,
            get_command_agent_dirs_for_project,
        )
        from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, PROMPT_DRIVEN_COMMANDS
        from specify_cli.core.config import AGENT_COMMAND_CONFIG
    except ImportError:
        return []

    try:
        from importlib.metadata import version as pkg_version
        current_version = pkg_version("spec-kitty-cli")
    except Exception:
        current_version = __version__

    expected_marker = f"<!-- spec-kitty-command-version: {current_version} -->"

    def _compute_filename(command: str, agent_key: str) -> str:
        config = AGENT_COMMAND_CONFIG.get(agent_key)
        if config is None:
            return f"spec-kitty.{command}.md"
        ext: str = config["ext"]
        stem = command
        if agent_key == "codex":
            stem = stem.replace("-", "_")
        return f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"

    issues: list[dict] = []
    agent_dirs = get_command_agent_dirs_for_project(project_path)

    for agent_root, subdir in agent_dirs:
        agent_dir = project_path / agent_root / subdir
        if not agent_dir.is_dir():
            continue

        agent_key = AGENT_DIR_TO_KEY.get(agent_root)
        if agent_key is None:
            continue

        for command in sorted(PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS):
            filename = _compute_filename(command, agent_key)
            file_path = agent_dir / filename
            rel_path = str(file_path.relative_to(project_path))
            is_prompt_driven = command in PROMPT_DRIVEN_COMMANDS

            if not file_path.exists():
                issues.append({
                    "agent": agent_key,
                    "command": command,
                    "file": rel_path,
                    "issue": "missing",
                    "severity": "error",
                })
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                issues.append({
                    "agent": agent_key,
                    "command": command,
                    "file": rel_path,
                    "issue": f"unreadable: {exc}",
                    "severity": "error",
                })
                continue

            # Version marker check
            first_line = content.split("\n", 1)[0].strip()
            if first_line != expected_marker:
                issues.append({
                    "agent": agent_key,
                    "command": command,
                    "file": rel_path,
                    "issue": f"stale or missing version marker (expected: {expected_marker})",
                    "severity": "warning",
                })

            # Type check: prompt-driven should be long, CLI-driven should be short
            non_empty_lines = [line for line in content.splitlines() if line.strip()]
            line_count = len(non_empty_lines)
            if is_prompt_driven and line_count < 50:
                issues.append({
                    "agent": agent_key,
                    "command": command,
                    "file": rel_path,
                    "issue": f"prompt-driven command has only {line_count} non-empty lines (expected >50)",
                    "severity": "warning",
                })
            elif not is_prompt_driven and line_count >= 10:
                issues.append({
                    "agent": agent_key,
                    "command": command,
                    "file": rel_path,
                    "issue": f"CLI-driven command has {line_count} non-empty lines (expected <10 for thin shim)",
                    "severity": "warning",
                })

    codex_root = project_path / ".codex" / "prompts"
    if codex_root.is_dir():
        for legacy_file in sorted(codex_root.glob("spec-kitty.*")):
            issues.append({
                "agent": "codex",
                "command": "legacy-prompts",
                "file": str(legacy_file.relative_to(project_path)),
                "issue": "legacy Codex prompt file should be retired; Codex now loads Spec Kitty via skills",
                "severity": "warning",
            })

    return issues


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
