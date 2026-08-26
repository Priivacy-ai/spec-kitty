.DEFAULT_GOAL := help

.PHONY: help dev-setup lint typecheck test-fast test-full

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

# The subsystem directories an implementer's blast radius typically covers
# (see AGENTS.md "Test policy"). `make test-fast` is a baseline, not a
# substitute for running the tests of the modules your diff actually touches.
FAST_TIER_DIRS := tests/unit tests/status tests/cli tests/specify_cli/runtime

# Fast tier = pure-logic tests only; every slow tier is deselected by marker.
FAST_TIER_MARKERS = (fast or unit) and not slow and not e2e and not integration and not regression and not distribution and not live_adapter and not stress and not windows_ci and not platform_darwin

# Parallel-unsafe marker families (pytest.ini): `stress` spawns real
# multi-process/subprocess concurrency and `timing` measures wall-clock — both
# are corrupted by co-scheduled xdist workers, so they are deselected from the
# parallel pass below and get their own dedicated -n0 passes mirroring the
# stress-tests-serial / timing-nfr-serial CI jobs (.github/workflows/ci-quality.yml).
PARALLEL_UNSAFE_MARKERS = not stress and not timing

test-fast: ## Run fast tier of the typical blast-radius dirs (target <2 min)
	env -u FORCE_COLOR NO_COLOR=1 PWHEADLESS=1 uv run pytest $(FAST_TIER_DIRS) \
	  -m "$(FAST_TIER_MARKERS)" -n auto --dist loadfile -p no:cacheprovider -q

test-full: ## Run everything: one parallel pass + serial marker passes (CI agent's target)
	env -u FORCE_COLOR NO_COLOR=1 PWHEADLESS=1 uv run pytest tests/ \
	  -m "$(PARALLEL_UNSAFE_MARKERS)" -n auto --dist loadfile -p no:cacheprovider -q
	# Serial passes: the two parallel-unsafe marker families, mirroring the
	# stress-tests-serial / timing-nfr-serial CI jobs (--timeout guards a hung
	# fork/process from stalling the lane indefinitely).
	env -u FORCE_COLOR NO_COLOR=1 PWHEADLESS=1 uv run pytest tests/ \
	  -m "stress and not windows_ci" -n0 --timeout=240 --timeout-method=signal -q
	env -u FORCE_COLOR NO_COLOR=1 PWHEADLESS=1 uv run pytest tests/ \
	  -m timing -n0 --timeout=240 --timeout-method=signal -q
