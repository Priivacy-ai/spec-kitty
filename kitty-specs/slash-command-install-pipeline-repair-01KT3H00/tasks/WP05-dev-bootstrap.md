---
work_package_id: WP05
title: Dev Bootstrap — Makefile dev-setup target and contributor docs
dependencies:
- WP04
requirement_refs:
- C-003
- FR-008
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Depends on WP04. Run: spec-kitty agent action implement WP05 --agent claude'
subtasks:
- T018
- T019
- T020
- T021
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: implementer-ivan
authoritative_surface: Makefile
execution_mode: code_change
owned_files:
- Makefile
- CONTRIBUTING.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

Wait for confirmation before proceeding.

---

## Objective

Add a `Makefile` with a `dev-setup` target and update `CONTRIBUTING.md` so that developers can bootstrap a complete spec-kitty development environment — including all slash commands — with a single command.

This is the "Layer B" bootstrap fix for GitHub issue #1610. Layer C (CLI-startup auto-repair) is already handled by WP01/WP02.

**Prerequisite**: WP04 must be merged (so `doctor skills --fix` works correctly).

```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Context

### Why this matters

After cloning the dev repo and running `uv sync`, a contributor has the spec-kitty CLI installed but all 8 prompt-driven slash commands are missing from `~/.claude/commands/`. The only way to discover this is to open Claude Code and notice `/spec-kitty.specify` doesn't appear. There is no proactive signal.

`make dev-setup` gives contributors a one-step command that:
1. Syncs the Python environment
2. Detects and repairs any missing slash commands

It is idempotent — running it twice is always safe.

### Constraint: no `make` for end-users (C-003)

`make dev-setup` is a dev-repo-only convenience. It is NOT required for end-user installations. End-users get CLI-startup auto-repair (WP01/WP02). `make` is only required in the dev environment, which already expects it (standard macOS/Linux dev tool).

---

## Subtask T018 — Create `Makefile`

Check whether a `Makefile` already exists at the repo root:

```bash
ls Makefile 2>/dev/null && echo "EXISTS" || echo "CREATE"
```

**If it does not exist**, create `Makefile` at the repo root:

```makefile
# Spec Kitty development tasks
# Run `make help` for available targets.

.DEFAULT_GOAL := help

.PHONY: help dev-setup lint test typecheck

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev-setup: ## Bootstrap dev environment: sync deps and install all slash commands
	uv sync --frozen --all-extras
	uv run spec-kitty doctor skills --fix

lint: ## Run ruff linter
	uv run ruff check src/

typecheck: ## Run mypy strict type checking
	uv run mypy --strict src/specify_cli/

test: ## Run test suite
	uv run pytest tests/ -x -q
```

**If it already exists**, add only the `dev-setup` target (and the `.PHONY` entry for it) without disrupting existing targets.

---

## Subtask T019 — Verify `.PHONY` and `help` target

Confirm the Makefile includes:
- `dev-setup` in `.PHONY`
- A `help` target that lists available targets
- At minimum `dev-setup`, `lint`, `typecheck`, `test` in `.PHONY`

Run `make help` to verify it produces readable output without error.

---

## Subtask T020 — Update CONTRIBUTING.md

Check whether `CONTRIBUTING.md` exists:

```bash
ls CONTRIBUTING.md 2>/dev/null && echo "EXISTS" || echo "FIND"
# If not found, check: ls docs/CONTRIBUTING.md docs/contributing.md 2>/dev/null
```

**Add a "Developer Setup" section** near the top (after any initial intro paragraph), before "Release Process" or similar sections:

```markdown
## Developer Setup

After cloning the repo, bootstrap your development environment with:

```bash
uv sync --frozen --all-extras
make dev-setup
```

`make dev-setup` syncs Python dependencies and installs all spec-kitty slash
commands for your configured AI agents (including `/spec-kitty.specify` and
related commands in Claude Code). It is idempotent — safe to run again after
pulling changes or updating templates.

**Without running `make dev-setup`**, you may find that `/spec-kitty.specify`
and other planning commands are missing from Claude Code or your configured
agent. Re-running `make dev-setup` always repairs this.
```

If `CONTRIBUTING.md` does not exist, create it with just this section plus a brief intro.

---

## Subtask T021 — Verify idempotency

Manually verify (and document in a comment in `Makefile`):

1. Run `make dev-setup` once — observe output (commands installed/skipped)
2. Run `make dev-setup` again — confirm no errors, no "installing" output (all already present)
3. Delete `~/.claude/commands/spec-kitty.specify.md` and run again — confirm it reinstalls

The idempotency is provided by `doctor skills --fix` (implemented in WP04). No additional logic in the Makefile is needed — just verify it behaves correctly end-to-end.

---

## Definition of Done

- [ ] `Makefile` exists at repo root with `dev-setup` target
- [ ] `make dev-setup` runs `uv sync --frozen --all-extras && uv run spec-kitty doctor skills --fix`
- [ ] `make help` lists available targets clearly
- [ ] `CONTRIBUTING.md` has a "Developer Setup" section with `make dev-setup` instructions
- [ ] Running `make dev-setup` twice produces no errors on second run
- [ ] Running `make dev-setup` after deleting a command file reinstalls it

## Risks

- If `Makefile` already exists with targets that conflict with the proposed ones, merge carefully — do not overwrite existing working targets.
- `uv sync --frozen` will fail if `uv.lock` is out of date. This is intentional — it surfaces the problem. Do not change to `uv sync` (non-frozen) without explicit instruction.
- On Windows, `make` is not standard. C-003 says `make dev-setup` is dev-only (fine), but CONTRIBUTING.md should note Windows developers may need WSL or a PowerShell alternative if they need this command.
