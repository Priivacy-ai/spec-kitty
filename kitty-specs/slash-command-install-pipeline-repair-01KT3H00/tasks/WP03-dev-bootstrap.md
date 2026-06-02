---
work_package_id: WP03
title: Dev bootstrap — Makefile dev-setup and contributor docs
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-009
- FR-010
- C-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
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

---

## Objective

Add a `Makefile` with a `dev-setup` target and update `CONTRIBUTING.md` to close the dev-repo bootstrap gap (GitHub #1610 Layer B). After running `make dev-setup`, all 15 slash commands are installed.

**Prerequisite**: WP02 merged.

```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Subtask T018 — Create Makefile

Check if `Makefile` exists: `ls Makefile 2>/dev/null`. If not, create:

```makefile
.DEFAULT_GOAL := help

.PHONY: help dev-setup lint typecheck test

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev-setup: ## Sync deps and install all slash commands for configured agents
	uv sync --frozen --all-extras
	uv run spec-kitty doctor skills --fix

lint: ## Run ruff linter
	uv run ruff check src/

typecheck: ## Run mypy strict type checking
	uv run mypy --strict src/specify_cli/

test: ## Run test suite
	uv run pytest tests/ -x -q
```

If `Makefile` already exists, add only the `dev-setup` target without disturbing existing content.

---

## Subtask T019 — Verify `.PHONY` and help target

Confirm `dev-setup` is in `.PHONY`. Run `make help` to verify readable output.

---

## Subtask T020 — Update CONTRIBUTING.md

Find or create `CONTRIBUTING.md`. Add a **Developer Setup** section near the top:

```markdown
## Developer Setup

After cloning, bootstrap your environment:

```bash
uv sync --frozen --all-extras
make dev-setup
```

`make dev-setup` syncs dependencies and installs all spec-kitty slash commands
for your configured AI agents (including `/spec-kitty.specify` and related
commands in Claude Code). Re-run after pulling changes or updating templates.

Without running `make dev-setup`, planning commands like `/spec-kitty.specify`
may be absent from your AI coding agent. `make dev-setup` always repairs this.
```

---

## Subtask T021 — Verify idempotency

Run `make dev-setup` twice. Second run must produce no errors and no "installing" output (all files already present, doctor --fix is a no-op). Delete one command file, run again — confirm it reinstalls.

---

## Definition of Done

- [ ] `Makefile` exists with `dev-setup` target calling `uv sync` + `doctor skills --fix`
- [ ] `make help` lists available targets
- [ ] `CONTRIBUTING.md` has Developer Setup section with `make dev-setup` instructions
- [ ] `make dev-setup` is idempotent
- [ ] Note in CONTRIBUTING.md that Windows users may need WSL for `make`
