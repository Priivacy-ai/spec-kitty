"""
Adversarial Test Suite for spec-kitty 0.13.0

This module contains tests designed to find edge cases, security vulnerabilities,
and robustness issues in the 0.13.0 release. Tests are organized by attack category:

- test_distribution.py: PyPI user experience (no SPEC_KITTY_TEMPLATE_ROOT bypass)
- test_path_validation.py: Directory traversal, symlinks, path injection
- test_csv_attacks.py: Formula injection, encoding attacks, malformed files
- test_git_state.py: Detached HEAD, merge state, branch divergence
- test_migration_robustness.py: Atomicity, concurrency, recovery
- test_multi_parent_merge.py: Diamond dependencies, determinism
- test_workspace_context.py: Orphaned/corrupted context files
- test_context_validation.py: Decorator bypass prevention
- test_agent_config.py: Corrupt YAML handling

Run all adversarial tests:
    pytest tests/adversarial/ -v

Run only distribution tests:
    pytest tests/adversarial/ -v -m distribution
"""
