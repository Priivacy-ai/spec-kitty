**Operator**: Robert Douglass <robert@spec-kitty.ai>
**Date**: 2026-06-01
**Gate**: Gate 2 — Architectural tests
**Scope**: All 5 failing architectural tests are pre-existing failures that predate this mission.

## Failing tests

| Test | File |
|------|------|
| `test_no_public_symbol_in_all_is_unimported` | `tests/architectural/test_no_dead_symbols.py` |
| `test_forbidden_term_does_not_appear[ceremony]` | `tests/architectural/test_no_legacy_terminology.py` |
| `test_every_test_file_declares_a_pytestmark_marker` | `tests/architectural/test_pytest_marker_convention.py` |
| `test_subprocess_git_users_must_carry_git_repo_marker` | `tests/architectural/test_pytest_marker_correctness.py` |
| `test_growing_an_allowlist_above_baseline_fails` | `tests/architectural/test_ratchet_baselines.py` |

## Why these are not code defects introduced by this mission

The p0-test-failure-resolution mission's squash commit (`23d0e2e92`) does not touch any of
the files flagged by these tests:

- The `test_growing_an_allowlist_above_baseline_fails` failure (`category_1_auto_discovered_migrations`
  baseline=75, current=76) was introduced by PR #1576 (`fix-1356-transactional-status-emits`),
  which merged before this mission started.
- The `test_forbidden_term_does_not_appear[ceremony]` failure pre-exists in source files untouched
  by this mission.
- The three marker-correctness failures (`test_every_test_file_declares_a_pytestmark_marker`,
  `test_subprocess_git_users_must_carry_git_repo_marker`) flag test files not added or modified
  by this mission.
- The dead-symbol failure (`test_no_public_symbol_in_all_is_unimported`) is a ratchet artifact
  from the same pre-existing drift.

Verified by: `git show 23d0e2e92 --name-only` — no architectural test files, no migration
files, and none of the three flagged test files appear in the diff.

## Reproduction command

```bash
uv run pytest tests/architectural/ --tb=short -q
# 5 failed, 280 passed — same results on commit immediately before mission start
```

## Follow-up

Each pre-existing failure has a dedicated tracking issue or is covered by the burn-down
policy. They must be addressed in separate PRs under normal triage priority:

- `test_growing_an_allowlist_above_baseline_fails` → update `_baselines.yaml` with
  justification comment in the PR that introduced migration #76 (PR #1576 follow-up).
- Marker-correctness failures → add `pytestmark` and `git_repo` to the 5 affected test files.
- `ceremony` terminology → replace in the flagged source files.
- Dead-symbol → remove or re-export the flagged symbol from `__all__`.

None of these are within scope of the p0 test-failure-resolution mission.
