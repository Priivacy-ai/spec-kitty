"""Shared help text for the init command."""

INIT_COMMAND_DOC = """
Initialize a new Spec Kitty project from templates.

Interactive Mode (default):
- Prompts you to select AI assistants

Non-Interactive Mode:
- Enabled with --non-interactive/--yes, SPEC_KITTY_NON_INTERACTIVE=1, or non-TTY
- Skips all prompts
- Uses provided options or defaults
- Perfect for CI/CD and automation

What Gets Created:
- .kittify/ - Scripts, templates, memory
- Agent commands (.claude/commands/, .codex/prompts/, etc.)
- Context files (CLAUDE.md, .cursorrules, AGENTS.md, etc.)
- Git repository (unless --no-git)
- Background dashboard (http://127.0.0.1:PORT)

⚠️  AFTER INIT, READ BELOW ⚠️
Your next step is to establish project governance using `/spec-kitty.constitution`
in the main repo root (NOT in any worktree). This creates project-wide principles
that will guide all subsequent development.

Specifying AI Assistants (--ai flag):
Use comma-separated agent keys (no spaces). Valid keys include:
codex, claude, gemini, cursor, qwen, opencode, windsurf, kilocode,
auggie, roo, copilot, q.

Template Discovery (Development Mode):
By default, spec-kitty searches for templates in this order:
  1. --template-root flag (if provided)
  2. SPEC_KITTY_TEMPLATE_ROOT environment variable
  3. Packaged templates (from PyPI installation)
  4. SPECIFY_TEMPLATE_REPO environment variable (remote)

For development installs from source, use either:
  export SPEC_KITTY_TEMPLATE_ROOT=$(pwd) && spec-kitty init my-project --ai claude
  OR
  spec-kitty init my-project --ai claude --template-root=$(pwd)

Examples:
  spec-kitty init my-project                    # Interactive mode
  spec-kitty init my-project --ai codex         # Non-interactive with Codex
  spec-kitty init my-project --ai codex,claude  # Multiple agents
  spec-kitty init my-project --ai codex,claude --script sh
  spec-kitty init . --ai codex --force          # Current directory (skip prompts)
  spec-kitty init --here --ai claude            # Alternative syntax for current dir
  spec-kitty init my-project --ai claude --template-root=/path/to/spec-kitty  # Dev mode

Non-interactive automation example:
  spec-kitty init my-project --ai codex,claude --script sh --no-git --non-interactive

Missions:
- Missions are selected per-feature during /spec-kitty.specify

See docs/non-interactive-init.md for automation patterns and CI examples.
"""
