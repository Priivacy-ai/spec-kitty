from specify_cli.core import (
    AI_CHOICES,
    AGENT_COMMAND_CONFIG,
    AGENT_TOOL_REQUIREMENTS,
    BANNER,
    DEFAULT_MISSION_KEY,
    DEFAULT_TEMPLATE_REPO,
    MISSION_CHOICES,
    SCRIPT_TYPE_CHOICES,
)


def test_ai_choices_contains_known_agents():
    assert "claude" in AI_CHOICES
    assert AI_CHOICES["claude"] == "Claude Code"
    assert "q" in AI_CHOICES


def test_agent_command_config_shapes():
    config = AGENT_COMMAND_CONFIG["claude"]
    assert config["dir"].startswith(".claude")
    assert config["ext"] == "md"
    assert config["arg_format"] == "$ARGUMENTS"


def test_defaults_and_banner_present():
    assert DEFAULT_MISSION_KEY in MISSION_CHOICES
    assert isinstance(DEFAULT_TEMPLATE_REPO, str) and DEFAULT_TEMPLATE_REPO
    assert isinstance(BANNER, str) and BANNER.strip()


def test_script_type_choices_are_human_readable():
    assert set(SCRIPT_TYPE_CHOICES.keys()) == {"sh", "ps"}
    assert "POSIX" in SCRIPT_TYPE_CHOICES["sh"]


def test_agent_tool_requirements_urls():
    claude_tool = AGENT_TOOL_REQUIREMENTS["claude"]
    assert claude_tool[0] == "claude"
    assert claude_tool[1].startswith("https://")
