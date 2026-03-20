"""Skill root directory resolution for all distribution modes.

Pure computation module — no filesystem I/O, no side effects.
Determines the minimum set of project skill root directories to create
based on the selected agents and the chosen distribution mode.
"""

from __future__ import annotations

from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG, DistributionClass

VALID_MODES = ("auto", "native", "shared", "wrappers-only")

SHARED_ROOT = ".agents/skills/"


def resolve_skill_roots(
    selected_agents: list[str],
    mode: str = "auto",
) -> list[str]:
    """Return the minimum set of project skill root directories to create.

    Args:
        selected_agents: Agent keys selected by the user.
        mode: One of "auto", "native", "shared", "wrappers-only".

    Returns:
        Sorted list of unique directory paths relative to project root.
        Empty list if mode is "wrappers-only" or no skill-capable agents selected.

    Raises:
        ValueError: If mode is not a recognized value.
    """
    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid skills mode: {mode}. "
            f"Must be one of: auto, native, shared, wrappers-only"
        )

    if mode == "wrappers-only":
        return []

    if mode in ("auto", "shared"):
        return _resolve_auto_shared(selected_agents)

    # mode == "native"
    return _resolve_native(selected_agents)


def _resolve_auto_shared(selected_agents: list[str]) -> list[str]:
    """Resolve skill roots for auto and shared modes.

    Algorithm:
    - If any selected agent is SHARED_ROOT_CAPABLE, add .agents/skills/
    - For each NATIVE_ROOT_REQUIRED agent, add its first (only) skill root
    - WRAPPER_ONLY agents contribute nothing
    """
    roots: set[str] = set()

    for agent_key in selected_agents:
        surface = AGENT_SURFACE_CONFIG.get(agent_key)
        if surface is None:
            continue

        if surface.distribution_class == DistributionClass.SHARED_ROOT_CAPABLE:
            roots.add(SHARED_ROOT)
        elif surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED:
            if surface.skill_roots:
                roots.add(surface.skill_roots[0])
        # WRAPPER_ONLY: nothing

    return sorted(roots)


def _resolve_native(selected_agents: list[str]) -> list[str]:
    """Resolve skill roots for native mode.

    Algorithm:
    - For SHARED_ROOT_CAPABLE agents: use the vendor-native root (second in
      skill_roots if available), or the first root if only one exists (e.g.
      codex which only lists .agents/skills/).
    - For NATIVE_ROOT_REQUIRED agents: use the first (only) skill root.
    - For WRAPPER_ONLY agents: nothing.
    """
    roots: set[str] = set()

    for agent_key in selected_agents:
        surface = AGENT_SURFACE_CONFIG.get(agent_key)
        if surface is None:
            continue

        if surface.distribution_class == DistributionClass.SHARED_ROOT_CAPABLE:
            if len(surface.skill_roots) >= 2:
                # Prefer vendor-native root (second entry)
                roots.add(surface.skill_roots[1])
            elif surface.skill_roots:
                # Only one root available (e.g. codex → .agents/skills/)
                roots.add(surface.skill_roots[0])
        elif surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED:
            if surface.skill_roots:
                roots.add(surface.skill_roots[0])
        # WRAPPER_ONLY: nothing

    return sorted(roots)
