"""Shared help text for the init command."""

INIT_COMMAND_DOC = """
Initialize a new Spec Kitty project from templates.

Interactive Mode (default):
- Prompts you to select AI assistants
- Choose script type (sh/ps)
- Select mission (software-dev/research)

Non-Interactive Mode (with --ai flag):
- Skips all prompts
- Uses provided options or defaults
- Perfect for CI/CD and automation

What Gets Created:
- .kittify/ - Scripts, templates, memory
- Agent commands (.claude/commands/, .codex/prompts/, etc.)
- Context files (CLAUDE.md, .cursorrules, AGENTS.md, etc.)
- Git repository (unless --no-git)
- Background dashboard (http://127.0.0.1:PORT)

Specifying AI Assistants (--ai flag):
Use comma-separated agent keys (no spaces). Valid keys include:
codex, claude, gemini, cursor, qwen, opencode, windsurf, kilocode,
auggie, roo, copilot, q.

Examples:
  spec-kitty init my-project                    # Interactive mode
  spec-kitty init my-project --ai codex         # Non-interactive with Codex
  spec-kitty init my-project --ai codex,claude  # Multiple agents
  spec-kitty init my-project --ai codex,claude --script sh --mission software-dev
  spec-kitty init . --ai codex --force          # Current directory (skip prompts)
  spec-kitty init --here --ai claude            # Alternative syntax for current dir

Non-interactive automation example:
  spec-kitty init my-project --ai codex,claude --script sh --mission software-dev --no-git

Missions:
- software-dev: Standard software development workflows
- research: Deep research with evidence tracking

See docs/non-interactive-init.md for automation patterns and CI examples.
"""
