"""Unit tests for the canonical AGENT_SURFACE_CONFIG and derived views."""

from __future__ import annotations

import pytest

from specify_cli.core.agent_surface import (
    AGENT_SURFACE_CONFIG,
    AgentSurface,
    DistributionClass,
    get_agent_command_config,
    get_agent_dir_to_key,
    get_agent_dirs,
    get_agent_surface,
)


ALL_AGENT_KEYS = {
    "claude",
    "copilot",
    "gemini",
    "cursor",
    "qwen",
    "opencode",
    "windsurf",
    "codex",
    "kilocode",
    "auggie",
    "roo",
    "q",
}


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


def test_all_agents_present() -> None:
    assert len(AGENT_SURFACE_CONFIG) == 12
    assert set(AGENT_SURFACE_CONFIG.keys()) == ALL_AGENT_KEYS


# ---------------------------------------------------------------------------
# Distribution class assignments match PRD matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent_key,expected_class",
    [
        ("claude", DistributionClass.NATIVE_ROOT_REQUIRED),
        ("copilot", DistributionClass.SHARED_ROOT_CAPABLE),
        ("gemini", DistributionClass.SHARED_ROOT_CAPABLE),
        ("cursor", DistributionClass.SHARED_ROOT_CAPABLE),
        ("qwen", DistributionClass.NATIVE_ROOT_REQUIRED),
        ("opencode", DistributionClass.SHARED_ROOT_CAPABLE),
        ("windsurf", DistributionClass.SHARED_ROOT_CAPABLE),
        ("codex", DistributionClass.SHARED_ROOT_CAPABLE),
        ("kilocode", DistributionClass.NATIVE_ROOT_REQUIRED),
        ("auggie", DistributionClass.SHARED_ROOT_CAPABLE),
        ("roo", DistributionClass.SHARED_ROOT_CAPABLE),
        ("q", DistributionClass.WRAPPER_ONLY),
    ],
)
def test_distribution_classes(agent_key: str, expected_class: DistributionClass) -> None:
    assert AGENT_SURFACE_CONFIG[agent_key].distribution_class == expected_class


# ---------------------------------------------------------------------------
# Derived AGENT_COMMAND_CONFIG matches old hardcoded values (byte-exact)
# ---------------------------------------------------------------------------


def test_derived_agent_command_config_matches_legacy() -> None:
    derived = get_agent_command_config()

    # Old hardcoded values from config.py before this refactor
    expected: dict[str, dict[str, str]] = {
        "claude": {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
        "copilot": {"dir": ".github/prompts", "ext": "prompt.md", "arg_format": "$ARGUMENTS"},
        "gemini": {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"},
        "cursor": {"dir": ".cursor/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
        "qwen": {"dir": ".qwen/commands", "ext": "toml", "arg_format": "{{args}}"},
        "opencode": {"dir": ".opencode/command", "ext": "md", "arg_format": "$ARGUMENTS"},
        "windsurf": {"dir": ".windsurf/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
        "codex": {"dir": ".codex/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
        "kilocode": {"dir": ".kilocode/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
        "auggie": {"dir": ".augment/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
        "roo": {"dir": ".roo/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
        "q": {"dir": ".amazonq/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
    }

    assert derived == expected


def test_derived_agent_command_config_count() -> None:
    assert len(get_agent_command_config()) == 12


# ---------------------------------------------------------------------------
# Derived AGENT_DIRS matches old hardcoded values
# ---------------------------------------------------------------------------


def test_derived_agent_dirs_matches_legacy() -> None:
    dirs = get_agent_dirs()

    expected: list[tuple[str, str]] = [
        (".claude", "commands"),
        (".github", "prompts"),
        (".gemini", "commands"),
        (".cursor", "commands"),
        (".qwen", "commands"),
        (".opencode", "command"),
        (".windsurf", "workflows"),
        (".codex", "prompts"),
        (".kilocode", "workflows"),
        (".augment", "commands"),
        (".roo", "commands"),
        (".amazonq", "prompts"),
    ]

    assert dirs == expected


def test_derived_agent_dirs_count() -> None:
    assert len(get_agent_dirs()) == 12


# ---------------------------------------------------------------------------
# Derived AGENT_DIR_TO_KEY matches old hardcoded values
# ---------------------------------------------------------------------------


def test_derived_agent_dir_to_key_matches_legacy() -> None:
    mapping = get_agent_dir_to_key()

    expected: dict[str, str] = {
        ".claude": "claude",
        ".github": "copilot",
        ".gemini": "gemini",
        ".cursor": "cursor",
        ".qwen": "qwen",
        ".opencode": "opencode",
        ".windsurf": "windsurf",
        ".codex": "codex",
        ".kilocode": "kilocode",
        ".augment": "auggie",
        ".roo": "roo",
        ".amazonq": "q",
    }

    assert mapping == expected


# ---------------------------------------------------------------------------
# Wrapper-only agents have no skill roots
# ---------------------------------------------------------------------------


def test_wrapper_only_no_skill_roots() -> None:
    assert AGENT_SURFACE_CONFIG["q"].skill_roots == ()


# ---------------------------------------------------------------------------
# Native-root-required agents don't list .agents/skills/
# ---------------------------------------------------------------------------


def test_native_agents_no_shared_root() -> None:
    for key in ("claude", "qwen", "kilocode"):
        surface = AGENT_SURFACE_CONFIG[key]
        assert surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED
        assert ".agents/skills/" not in surface.skill_roots


# ---------------------------------------------------------------------------
# Shared-root-capable agents include .agents/skills/
# ---------------------------------------------------------------------------


def test_shared_root_agents_include_agents_skills() -> None:
    shared_agents = [
        k
        for k, s in AGENT_SURFACE_CONFIG.items()
        if s.distribution_class == DistributionClass.SHARED_ROOT_CAPABLE
    ]
    for key in shared_agents:
        surface = AGENT_SURFACE_CONFIG[key]
        assert ".agents/skills/" in surface.skill_roots, (
            f"{key} is SHARED_ROOT_CAPABLE but missing .agents/skills/"
        )


# ---------------------------------------------------------------------------
# get_agent_surface function
# ---------------------------------------------------------------------------


def test_get_agent_surface() -> None:
    surface = get_agent_surface("claude")
    assert isinstance(surface, AgentSurface)
    assert surface.key == "claude"
    assert surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED


def test_get_agent_surface_invalid_key() -> None:
    with pytest.raises(KeyError):
        get_agent_surface("nonexistent")


# ---------------------------------------------------------------------------
# Structural consistency: wrapper.dir == agent_root/wrapper_subdir
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_dir_consistency(agent_key: str) -> None:
    s = AGENT_SURFACE_CONFIG[agent_key]
    assert s.wrapper.dir == f"{s.agent_root}/{s.wrapper_subdir}"


# ---------------------------------------------------------------------------
# Structural consistency: key matches dict key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_key_matches_dict_key(agent_key: str) -> None:
    assert AGENT_SURFACE_CONFIG[agent_key].key == agent_key


# ---------------------------------------------------------------------------
# Dataclass immutability
# ---------------------------------------------------------------------------


def test_agent_surface_is_frozen() -> None:
    surface = get_agent_surface("claude")
    with pytest.raises(AttributeError):
        surface.key = "changed"  # type: ignore[misc]


def test_wrapper_config_is_frozen() -> None:
    surface = get_agent_surface("claude")
    with pytest.raises(AttributeError):
        surface.wrapper.ext = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DistributionClass enum values
# ---------------------------------------------------------------------------


def test_distribution_class_values() -> None:
    assert DistributionClass.SHARED_ROOT_CAPABLE.value == "shared-root-capable"
    assert DistributionClass.NATIVE_ROOT_REQUIRED.value == "native-root-required"
    assert DistributionClass.WRAPPER_ONLY.value == "wrapper-only"


# ---------------------------------------------------------------------------
# Codex ext is "md" not "prompt.md" (critical distinction)
# ---------------------------------------------------------------------------


def test_codex_ext_is_md_not_prompt_md() -> None:
    assert AGENT_SURFACE_CONFIG["codex"].wrapper.ext == "md"
    # copilot is the one with prompt.md
    assert AGENT_SURFACE_CONFIG["copilot"].wrapper.ext == "prompt.md"


# ---------------------------------------------------------------------------
# AGENT_SURFACE_CONFIG importable from config.py (User Story 2 requirement)
# ---------------------------------------------------------------------------


def test_agent_surface_config_importable_from_config() -> None:
    """Verify AGENT_SURFACE_CONFIG is re-exported from config.py per spec."""
    from specify_cli.core.config import AGENT_SURFACE_CONFIG as config_asc

    assert len(config_asc) == 12
