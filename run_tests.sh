#!/bin/bash
# Test runner for the worktree that ensures correct imports

# Change to worktree directory
cd "$(dirname "$0")"

# Add the src directory to PYTHONPATH
export PYTHONPATH="${PWD}/src:${PWD}:${PYTHONPATH}"

# Run tests with explicit path settings
python -m pytest tests/ "$@"