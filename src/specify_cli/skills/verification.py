"""Post-init verification for agent skill installations.

Validates that the installed state on disk matches the expectations recorded
in the skills manifest.  Returns a structured ``VerificationResult`` with
actionable error messages that name the specific agent and resource.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.core.agent_surface import (
    AGENT_SURFACE_CONFIG,
    DistributionClass,
)
from specify_cli.skills.manifest import SkillsManifest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass  (T018)
# ---------------------------------------------------------------------------


@dataclass
class VerificationResult:
    """Outcome of ``verify_installation()``.

    Attributes:
        passed: ``True`` when no errors were detected.
        errors: Actionable problems that must be fixed before the
            installation can be considered valid.
        warnings: Non-blocking observations (e.g. zero wrappers for an
            agent, which is unusual but not invalid).
    """

    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API  (T018 / T019)
# ---------------------------------------------------------------------------


def verify_installation(
    project_root: Path,
    selected_agents: list[str],
    manifest: SkillsManifest,
) -> VerificationResult:
    """Verify that the installed state matches expectations.

    Performs four checks:

    1. **Agent coverage** -- every selected agent has either a skill root
       listed in the manifest that it can scan *or* at least one managed
       wrapper file.  Wrapper-only agents are not expected to have skill
       roots.
    2. **Skill root existence** -- every directory listed in
       ``manifest.installed_skill_roots`` exists on disk.
    3. **Wrapper count** -- warns (does not error) when a selected agent
       has zero managed wrapper files.
    4. **Duplicate skill names** -- no two skill roots scanned by the same
       agent contain files with the same name.  (Always passes in Phase 0
       when roots are empty, but the structure is in place for later
       phases.)

    Args:
        project_root: Absolute path to the project root directory.
        selected_agents: Agent keys that were selected during init.
        manifest: The persisted skills manifest to verify against.

    Returns:
        A :class:`VerificationResult` whose ``passed`` field is ``False``
        when any error was recorded.
    """
    result = VerificationResult()

    _check_agent_coverage(selected_agents, manifest, result)
    _check_skill_root_existence(project_root, manifest, result)
    _check_wrapper_counts(selected_agents, manifest, result)
    _check_duplicate_skill_names(project_root, selected_agents, manifest, result)

    result.passed = len(result.errors) == 0
    return result


# ---------------------------------------------------------------------------
# Internal checks  (T019)
# ---------------------------------------------------------------------------


def _check_agent_coverage(
    selected_agents: list[str],
    manifest: SkillsManifest,
    result: VerificationResult,
) -> None:
    """Check 1: every selected agent has a skill root or wrapper files."""
    # Build lookup: which agents have at least one managed wrapper?
    agents_with_wrappers: set[str] = set()
    for mf in manifest.managed_files:
        if mf.file_type == "wrapper":
            for agent_key in selected_agents:
                surface = AGENT_SURFACE_CONFIG.get(agent_key)
                if surface is None:
                    continue
                # Check if this managed file lives inside the agent's wrapper dir
                if mf.path.startswith(surface.wrapper.dir):
                    agents_with_wrappers.add(agent_key)

    # Build lookup: which agents have at least one installed skill root?
    agents_with_roots: set[str] = set()
    for agent_key in selected_agents:
        surface = AGENT_SURFACE_CONFIG.get(agent_key)
        if surface is None:
            continue
        for root in manifest.installed_skill_roots:
            if root in surface.skill_roots:
                agents_with_roots.add(agent_key)

    for agent_key in selected_agents:
        surface = AGENT_SURFACE_CONFIG.get(agent_key)
        if surface is None:
            continue

        # Wrapper-only agents only need wrappers, not skill roots
        if surface.distribution_class == DistributionClass.WRAPPER_ONLY:
            if agent_key not in agents_with_wrappers:
                result.errors.append(
                    f"Agent '{agent_key}' has no managed skill root or wrapper root"
                )
            continue

        # Non-wrapper-only agents need either a skill root or wrappers
        if agent_key not in agents_with_roots and agent_key not in agents_with_wrappers:
            result.errors.append(
                f"Agent '{agent_key}' has no managed skill root or wrapper root"
            )


def _check_skill_root_existence(
    project_root: Path,
    manifest: SkillsManifest,
    result: VerificationResult,
) -> None:
    """Check 2: every installed skill root exists on disk."""
    for root in manifest.installed_skill_roots:
        root_path = project_root / root
        if not root_path.exists():
            result.errors.append(
                f"Skill root '{root}' listed in manifest but does not exist on disk"
            )


def _check_wrapper_counts(
    selected_agents: list[str],
    manifest: SkillsManifest,
    result: VerificationResult,
) -> None:
    """Check 3: warn when an agent has zero managed wrapper files."""
    # Count wrappers per agent
    wrapper_counts: dict[str, int] = {agent_key: 0 for agent_key in selected_agents}

    for mf in manifest.managed_files:
        if mf.file_type != "wrapper":
            continue
        for agent_key in selected_agents:
            surface = AGENT_SURFACE_CONFIG.get(agent_key)
            if surface is None:
                continue
            if mf.path.startswith(surface.wrapper.dir):
                wrapper_counts[agent_key] = wrapper_counts.get(agent_key, 0) + 1

    for agent_key in selected_agents:
        if wrapper_counts.get(agent_key, 0) == 0:
            result.warnings.append(
                f"Agent '{agent_key}' has 0 managed wrapper files"
            )


def _check_duplicate_skill_names(
    project_root: Path,
    selected_agents: list[str],
    manifest: SkillsManifest,
    result: VerificationResult,
) -> None:
    """Check 4: no duplicate skill names in roots scanned by the same agent.

    In Phase 0, skill roots are empty so this always passes.  The structure
    is in place for later phases when skill packs populate the roots.
    """
    for agent_key in selected_agents:
        surface = AGENT_SURFACE_CONFIG.get(agent_key)
        if surface is None:
            continue
        if surface.distribution_class == DistributionClass.WRAPPER_ONLY:
            continue

        # Collect only the installed roots that this agent scans
        agent_roots = [
            root
            for root in manifest.installed_skill_roots
            if root in surface.skill_roots
        ]

        if len(agent_roots) < 2:
            continue

        # Map skill filename -> list of roots that contain it
        name_to_roots: dict[str, list[str]] = defaultdict(list)
        for root in agent_roots:
            root_path = project_root / root
            if not root_path.is_dir():
                continue
            for child in root_path.iterdir():
                if child.is_file():
                    name_to_roots[child.name].append(root)

        for name, roots in name_to_roots.items():
            if len(roots) > 1:
                result.errors.append(
                    f"Duplicate skill '{name}' in roots scanned by agent "
                    f"'{agent_key}': {roots[0]}, {roots[1]}"
                )
