#!/bin/bash
# Test runner for the worktree (delegates to the canonical uv-managed test path).

# Change to the worktree directory so uv resolves the project venv.
cd "$(dirname "$0")"

# Run the suite via uv (the canonical authority; see the Makefile `test` target and
# CONTRIBUTING). uv sync's editable install handles src/ imports, so no manual PYTHONPATH.
uv run pytest tests/ "$@"
