# Google Antigravity

## Overview

Google Antigravity is an AI-powered IDE (a VS Code fork), not a CLI tool.
There is no standalone CLI binary or API surface to observe.

## Directory Structure

Antigravity uses the `.agent/` directory at the project root:

```
.agent/
├── workflows/     # Slash commands (markdown with YAML frontmatter)
├── skills/        # Reusable skill packages (out of scope for now)
└── rules/         # Project-level rules/context files
```

## Workflows (Slash Commands)

- Located in `.agent/workflows/`
- File format: Markdown (`.md`) with optional YAML frontmatter
- Argument placeholder: `$ARGUMENTS` (same as Claude, Cursor, Windsurf, etc.)
- Equivalent to "commands" in other agents

## Rules (Context Files)

- Located in `.agent/rules/`
- Spec Kitty context file: `.agent/rules/specify-rules.md`
- Follows the same pattern as Cursor (`.cursor/rules/`) and Windsurf (`.windsurf/rules/`)

## Skills

- Located in `.agent/skills/`
- Out of scope for initial integration; deferred to follow-up work

## Integration Notes

- **IDE_AGENT**: Yes — no CLI binary to check, no tool requirement
- **Agent key**: `"antigravity"`
- **No adapter needed**: No CLI/API surface to observe; marked as IDE-only agent
- **Community confirmed**: Copying `.gemini/` to `.agent/` works for basic compatibility (issue #76)

## Mode Guidance

Use **Fast Mode** for spec-driven development workflows.
Planning Mode causes Antigravity to deviate from the spec-driven workflow.
Since the spec IS the plan, Fast Mode is recommended for all `/spec-kitty.*` commands.

## `.agent/` Directory Collision Risk

Unlike `.claude/`, `.gemini/`, etc., the `.agent/` name is generic. Some projects
may already use it for other purposes. This is an inherent Antigravity design choice,
not something Spec Kitty can mitigate. All official tools and community repos use
the same path.

## References

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/76
