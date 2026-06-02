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

typecheck: ## Run targeted mypy strict type checking
	uv run mypy --strict src/specify_cli/runtime/agent_commands.py

test: ## Run test suite (targeted surface only)
	uv run pytest tests/specify_cli/runtime/test_agent_commands.py \
	  tests/specify_cli/cli/commands/test_doctor_slash_commands.py -v
