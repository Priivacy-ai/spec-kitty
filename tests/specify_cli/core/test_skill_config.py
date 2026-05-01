"""Tests for AGENT_SKILL_CONFIG capability matrix."""

from __future__ import annotations

from specify_cli.core.config import (
    AGENT_SKILL_CONFIG,
    AI_CHOICES,
    SKILL_CLASS_NATIVE,
    SKILL_CLASS_SHARED,
    SKILL_CLASS_WRAPPER,
)

VALID_CLASSES = {SKILL_CLASS_SHARED, SKILL_CLASS_NATIVE, SKILL_CLASS_WRAPPER}


def test_all_agents_have_skill_config() -> None:
    """Every key in AI_CHOICES must exist in AGENT_SKILL_CONFIG."""
    missing = set(AI_CHOICES) - set(AGENT_SKILL_CONFIG)
    assert not missing, f"Agents missing from AGENT_SKILL_CONFIG: {missing}"


def test_no_extra_agents_in_skill_config() -> None:
    """No keys in AGENT_SKILL_CONFIG that aren't in AI_CHOICES."""
    extra = set(AGENT_SKILL_CONFIG) - set(AI_CHOICES)
    assert not extra, f"Extra agents in AGENT_SKILL_CONFIG: {extra}"


def test_installation_classes_are_valid() -> None:
    """Every 'class' value must be one of the three constants."""
    for agent, cfg in AGENT_SKILL_CONFIG.items():
        assert cfg["class"] in VALID_CLASSES, (
            f"Agent '{agent}' has invalid class '{cfg['class']}'"
        )


def test_wrapper_only_has_no_roots() -> None:
    """Agents with wrapper-only class must have skill_roots=None."""
    for agent, cfg in AGENT_SKILL_CONFIG.items():
        if cfg["class"] == SKILL_CLASS_WRAPPER:
            assert cfg["skill_roots"] is None, (
                f"Wrapper-only agent '{agent}' should have skill_roots=None"
            )


def test_non_wrapper_has_roots() -> None:
    """Non-wrapper agents must have a non-empty list of skill_roots."""
    for agent, cfg in AGENT_SKILL_CONFIG.items():
        if cfg["class"] != SKILL_CLASS_WRAPPER:
            roots = cfg["skill_roots"]
            assert isinstance(roots, list) and len(roots) > 0, (
                f"Agent '{agent}' (class={cfg['class']}) must have non-empty skill_roots list"
            )


def test_shared_root_includes_agents_skills() -> None:
    """Shared-root agents must have .agents/skills/ as their first root."""
    for agent, cfg in AGENT_SKILL_CONFIG.items():
        if cfg["class"] == SKILL_CLASS_SHARED:
            roots = cfg["skill_roots"]
            assert isinstance(roots, list), f"Agent '{agent}' should have list roots"
            assert roots[0] == ".agents/skills/", (
                f"Agent '{agent}' first root should be '.agents/skills/', got '{roots[0]}'"
            )


def test_native_root_is_vendor_specific() -> None:
    """Native-root agents must not have any root starting with .agents/."""
    for agent, cfg in AGENT_SKILL_CONFIG.items():
        if cfg["class"] == SKILL_CLASS_NATIVE:
            roots = cfg["skill_roots"]
            assert isinstance(roots, list), f"Agent '{agent}' should have list roots"
            for root in roots:
                assert not root.startswith(".agents/"), (
                    f"Native agent '{agent}' should not have .agents/ prefix, got '{root}'"
                )
