---
title: "Set up Post-Edit Lint Hooks"
description: "Configure your AI agent harness to automatically run ruff and mypy after every code edit using spec-kitty lint."
---

# Set up Post-Edit Lint Hooks

One of the most effective ways to reduce review cycles is to catch linting and type errors at the **cheapest point**: immediately after the AI agent makes a change.

Spec Kitty provides a universal wrapper command, `spec-kitty lint`, designed specifically for this purpose. When configured as a "post-edit hook," it feeds violations back to the agent in the same turn, allowing it to self-correct.

## 1. The Universal Wrapper

The `spec-kitty lint <file_path>` command:
- Runs `ruff check` (linting).
- Runs `mypy --strict` (type-checking).
- Summarizes errors in an agent-friendly format.
- Exits with `1` if errors are found, triggering the agent's auto-fix logic.

## 2. Configuration by Harness

### Claude Code
Claude Code supports `PostToolUse` hooks in `.claude/settings.json`.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "spec-kitty lint --json"
          }
        ]
      }
    ]
  }
}
```

### Aider
Aider supports the `--lint-cmd` flag. You can set this in your `.aider.conf.yml` or pass it at startup.

```bash
aider --lint-cmd "spec-kitty lint"
```

### Cursor
Cursor (v1.7+) supports hooks in `.cursor/hooks.json`.

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [
      {
        "command": "spec-kitty lint --json"
      }
    ]
  }
}
```

### Windsurf
Add a natural language rule to your `.windsurfrules` file:

```markdown
# Linting Guardrail
After every file edit, you MUST run `spec-kitty lint <file_path>` and fix any reported errors immediately.
```

## 3. Advanced Usage

### Auto-Fixing
You can instruct `spec-kitty lint` to attempt to fix errors automatically (via `ruff --fix`) by adding the `--fix` flag:

```bash
spec-kitty lint <file_path> --fix
```

### JSON Output
For tools that can parse structured feedback, use the `--json` flag to get a machine-readable error report:

```bash
spec-kitty lint <file_path> --json
```

## Why use hooks?

1. **Faster Merges:** Code arrives at the review gate already clean and type-safe.
2. **Lower Costs:** Fewer turns spent on trivial "unused import" or "missing type hint" fixes.
3. **Better Quality:** Enforces project standards (like `mypy --strict`) automatically.
