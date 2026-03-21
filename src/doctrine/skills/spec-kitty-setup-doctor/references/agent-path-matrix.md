# Agent Path Matrix

Reference: Framework capability matrix for Spec Kitty 2.0.11+

## Skill Roots and Wrapper Roots by Agent

| Agent | Key | Installation Class | Skill Root(s) | Wrapper Root |
|-------|-----|-------------------|---------------|--------------|
| Claude Code | `claude` | native-root-required | `.claude/skills/` | `.claude/commands/` |
| GitHub Copilot | `copilot` | shared-root-capable | `.agents/skills/`, `.github/skills/` | `.github/prompts/` |
| Gemini CLI | `gemini` | shared-root-capable | `.agents/skills/`, `.gemini/skills/` | `.gemini/commands/` |
| Cursor | `cursor` | shared-root-capable | `.agents/skills/`, `.cursor/skills/` | `.cursor/commands/` |
| Qwen Code | `qwen` | native-root-required | `.qwen/skills/` | `.qwen/commands/` |
| opencode | `opencode` | shared-root-capable | `.agents/skills/`, `.opencode/skills/` | `.opencode/command/` |
| Windsurf | `windsurf` | shared-root-capable | `.agents/skills/`, `.windsurf/skills/` | `.windsurf/workflows/` |
| Codex CLI | `codex` | shared-root-capable | `.agents/skills/` | `.codex/prompts/` |
| Kilo Code | `kilocode` | native-root-required | `.kilocode/skills/` | `.kilocode/workflows/` |
| Auggie CLI | `auggie` | shared-root-capable | `.agents/skills/`, `.augment/skills/` | `.augment/commands/` |
| Roo Code | `roo` | shared-root-capable | `.agents/skills/`, `.roo/skills/` | `.roo/commands/` |
| Amazon Q Developer CLI | `q` | wrapper-only | _(none)_ | `.amazonq/prompts/` |
| Google Antigravity | `antigravity` | shared-root-capable | `.agents/skills/`, `.agent/skills/` | `.agent/workflows/` |

## Installation Classes

### native-root-required

Agents in this class require skills to be placed under their own directory tree.
They do not read from the shared `.agents/skills/` root.

**Agents:** Claude Code, Qwen Code, Kilo Code

### shared-root-capable

Agents in this class can read skills from the shared `.agents/skills/` root in
addition to their agent-specific skill root. When both exist, the agent-specific
root takes precedence.

**Agents:** GitHub Copilot, Gemini CLI, Cursor, opencode, Windsurf, Codex CLI,
Auggie CLI, Roo Code, Google Antigravity

### wrapper-only

Agents in this class do not support a skill root directory. Skills are delivered
exclusively through wrapper slash commands in the wrapper root.

**Agents:** Amazon Q Developer CLI

## Notes

- The shared root `.agents/skills/` is created once and symlinked or referenced
  by all shared-root-capable agents. This avoids duplicating skill content.
- Wrapper roots contain slash-command files (e.g., `spec-kitty.implement.md`)
  that agents use for `/spec-kitty.implement` style invocation.
- When verifying an installation, check the skill root(s) first, then the
  wrapper root. A missing wrapper root means slash commands are unavailable
  even if skills are correctly installed.
