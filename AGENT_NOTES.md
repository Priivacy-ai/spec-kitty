# Notes for Agent Working on WP01

## Test Import Issue Resolved

The test import errors you're experiencing are because pytest is importing from the installed `specify_cli` package in site-packages instead of the local worktree modules.

### Solution:

1. **pytest.ini** has been created with proper Python path settings
2. **run_tests.sh** script created for running tests with correct imports

### To run tests:
```bash
# From the worktree directory:
./run_tests.sh

# Or with specific test files:
./run_tests.sh tests/specify_cli/test_core/
```

### Alternative (direct pytest):
```bash
# Set PYTHONPATH explicitly:
PYTHONPATH=./src:. pytest tests/
```

## Directory Cleanup Done

The incorrectly placed `.kittify` directories have been removed from:
- `/src/specify_cli/.kittify` (both in main repo and worktree)

The correct locations are:
- `/.kittify/` at repository/worktree root only

## Important for Module Development

When creating new modules in `src/specify_cli/`, ensure imports work in three contexts:

1. **Local development**: Direct imports
2. **Pip installed**: Package imports
3. **Subprocess**: Try/except pattern

Example pattern:
```python
try:
    from .module import function  # Package import
except ImportError:
    from specify_cli.module import function  # Subprocess fallback
```