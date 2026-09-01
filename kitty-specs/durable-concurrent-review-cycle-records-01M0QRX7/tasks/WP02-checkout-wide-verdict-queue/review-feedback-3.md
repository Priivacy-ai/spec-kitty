# WP02 Review Feedback — Cycle 5

## Verdict

Rejected after the first hosted quality run found that the new queue module enlarges the public API without production consumers.

## Evidence

- `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` failed on the PR.
- The unused `__all__` exports are `DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS`, `VerdictSaveReentrant`, `verdict_save_queue_is_held`, and `verdict_save_queue_path`.
- The names are used by focused tests but are not imported by another production module.

## Required correction

Remove only these unused names from `verdict_commit_queue.__all__`. Preserve their module-level definitions and explicit test imports; do not weaken the dead-symbol gate or widen production usage merely to satisfy it.

## Required evidence

- Focused queue tests pass.
- The dead-symbol architecture test passes.
- Ruff and strict mypy pass on the owned files.

