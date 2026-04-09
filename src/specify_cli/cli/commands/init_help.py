"""Shared help text for the init command."""

INIT_COMMAND_DOC = """
Initialize a new Spec Kitty project.

Creates project files only. Does not initialize a git repository.
Does not create any commits.

If PROJECT_NAME is omitted, init runs in the current directory.
Re-running init in an already-initialized directory exits cleanly (idempotent).

Note: The --no-git flag from previous versions has been removed.
      init never touches git state regardless of flags.

Interactive Mode (default):
- Prompts you to select AI assistants

Non-Interactive Mode:
- Enabled with --non-interactive/--yes, SPEC_KITTY_NON_INTERACTIVE=1, or non-TTY
- Skips all prompts; --ai is required
- Perfect for CI/CD and automation

What Gets Created:
- .kittify/ - Project scaffold (memory, config)
- Agent commands (.claude/commands/, .codex/prompts/, etc.)
- .gitignore and .claudeignore

Specifying AI Assistants (--ai flag):
Use comma-separated agent keys (no spaces). Valid keys include:
codex, claude, gemini, cursor, qwen, opencode, windsurf, kilocode,
auggie, roo, copilot, q.

Template Discovery (Development Mode):
Set SPEC_KITTY_TEMPLATE_ROOT to override bundled templates for local development.

Examples:
  spec-kitty init --ai codex                    # Current directory (default)
  spec-kitty init my-project                    # Interactive mode
  spec-kitty init my-project --ai codex         # With Codex
  spec-kitty init my-project --ai codex,claude  # Multiple agents
  spec-kitty init --ai claude --non-interactive # Non-interactive

Canonical Next Steps (after init):
  spec-kitty next --agent <agent> --mission <slug>         # Enter mission loop
  spec-kitty agent action implement <WP> --agent <name>   # Implement a work package
  spec-kitty agent action review    <WP> --agent <name>   # Review a work package

Missions:
- Missions are selected per-feature during /spec-kitty.specify
"""
