"""Configuration constants shared across the Spec Kitty CLI."""

from __future__ import annotations

AI_CHOICES = {
    "copilot": "GitHub Copilot",
    "claude": "Claude Code",
    "gemini": "Gemini CLI",
    "cursor": "Cursor",
    "qwen": "Qwen Code",
    "opencode": "opencode",
    "codex": "Codex CLI",
    "windsurf": "Windsurf",
    "kilocode": "Kilo Code",
    "auggie": "Auggie CLI",
    "roo": "Roo Code",
    "q": "Amazon Q Developer CLI",
    "antigravity": "Google Antigravity",
    "vibe": "Mistral Vibe",
}

MISSION_CHOICES = {
    "software-dev": "Software Dev Kitty",
    "research": "Deep Research Kitty",
}

DEFAULT_MISSION_KEY = "software-dev"

AGENT_TOOL_REQUIREMENTS: dict[str, tuple[str, str]] = {
    "claude": ("claude", "https://docs.anthropic.com/en/docs/claude-code/setup"),
    "gemini": ("gemini", "https://github.com/google-gemini/gemini-cli"),
    "qwen": ("qwen", "https://github.com/QwenLM/qwen-code"),
    "opencode": ("opencode", "https://opencode.ai"),
    "codex": ("codex", "https://github.com/openai/codex"),
    "auggie": ("auggie", "https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli"),
    "q": ("q", "https://aws.amazon.com/developer/learning/q-developer-cli/"),
    "vibe": ("vibe", "https://github.com/mistralai/mistral-vibe"),
}

SCRIPT_TYPE_CHOICES = {"sh": "POSIX Shell (bash/zsh)", "ps": "PowerShell"}

DEFAULT_TEMPLATE_REPO = "spec-kitty/spec-kitty"

# IDE-integrated agents that don't require CLI installation
IDE_AGENTS = {"cursor", "windsurf", "copilot", "kilocode", "antigravity"}

AGENT_COMMAND_CONFIG: dict[str, dict[str, str]] = {
    "claude": {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "gemini": {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"},
    "copilot": {"dir": ".github/prompts", "ext": "prompt.md", "arg_format": "$ARGUMENTS"},
    "cursor": {"dir": ".cursor/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "qwen": {"dir": ".qwen/commands", "ext": "toml", "arg_format": "{{args}}"},
    "opencode": {"dir": ".opencode/command", "ext": "md", "arg_format": "$ARGUMENTS"},
    "windsurf": {"dir": ".windsurf/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "kilocode": {"dir": ".kilocode/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "auggie": {"dir": ".augment/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "roo": {"dir": ".roo/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "q": {"dir": ".amazonq/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
    "antigravity": {"dir": ".agent/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
}

# Skill installation classes (PRD section 6)
SKILL_CLASS_SHARED: str = "shared-root-capable"
SKILL_CLASS_NATIVE: str = "native-root-required"
SKILL_CLASS_WRAPPER: str = "wrapper-only"

AGENT_SKILL_CONFIG: dict[str, dict[str, str | list[str] | None]] = {
    "claude":       {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".claude/skills/"]},
    "copilot":      {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".github/skills/"]},
    "gemini":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".gemini/skills/"]},
    "cursor":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".cursor/skills/"]},
    "qwen":         {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".qwen/skills/"]},
    "opencode":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".opencode/skills/"]},
    "windsurf":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".windsurf/skills/"]},
    "codex":        {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/"]},
    "vibe":         {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/"]},
    "kilocode":     {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".kilocode/skills/"]},
    "auggie":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".augment/skills/"]},
    "roo":          {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".roo/skills/"]},
    "q":            {"class": SKILL_CLASS_WRAPPER, "skill_roots": None},
    "antigravity":  {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".agent/skills/"]},
}

BANNER = """
`````````````````````````````````````````````````````````

           ▄█▄_                            ╓▄█_
          ▐█ └▀█▄_                      ▄█▀▀ ╙█
          █"    `▀█▄                  ▄█▀     █▌
         ▐█        ▀█▄▄▄██████████▄▄▄█"       ▐█
         ║█          "` ╟█  ╫▌  █" '"          █
         ║█              ▀  ╚▀  ▀             J█
          █                                   █▌
          █▀   ,▄█████▄           ,▄█████▄_   █▌
         █▌  ▄█"      "██       ╓█▀      `▀█_  █▌
        ▐█__▐▌    ▄██▄  ╙█_____╒█   ▄██,   '█__'█
        █▀▀▀█M    ████   █▀╙\"\"\"██  ▐████    █▀▀"█▌
        █─  ╟█    ╙▀▀"  ██      █╕  ╙▀▀    ╓█   ║▌
   ╓▄▄▄▄█▌,_ ╙█▄_    _▄█▀╒██████ ▀█╥     ▄█▀ __,██▄▄▄▄
        ╚█'`"  `╙▀▀▀▀▀"   `▀██▀    "▀▀▀▀▀"   ""▐█
     _,▄▄███▀               █▌              ▀▀███▄▄,_
    ▀"`   ▀█_         '▀█▄▄█▀▀█▄▄█▀          ▄█"  '"▀"
           ╙██_                            ▄█▀
             └▀█▄_                      ,▓█▀
                └▀▀██▄,__        __╓▄██▀▀
                     `"▀▀▀▀▀▀▀▀▀▀▀╙"`

`````````````````````````````````````````````````````````
"""

__all__ = [
    "AI_CHOICES",
    "MISSION_CHOICES",
    "DEFAULT_MISSION_KEY",
    "AGENT_TOOL_REQUIREMENTS",
    "SCRIPT_TYPE_CHOICES",
    "DEFAULT_TEMPLATE_REPO",
    "AGENT_COMMAND_CONFIG",
    "IDE_AGENTS",
    "SKILL_CLASS_SHARED",
    "SKILL_CLASS_NATIVE",
    "SKILL_CLASS_WRAPPER",
    "AGENT_SKILL_CONFIG",
    "BANNER",
]
