# Contract: pre-review gate decoupling (#2801)

**Location**: `src/specify_cli/cli/commands/agent/tasks_move_task.py:~993`

## Before
`_mt_pre_review_gate_env_disable_reason()` reads `first_set_sync_disable_env()` (SYNC_DISABLE / MINIMAL_IMPORT).

## After (clean cut)
Reads ONLY `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`. The sync toggles have **no** effect on the gate.

## Invariants
- **INV-1**: on a bare install (sync inactive), a `for_review` transition with a failing gate condition is BLOCKED. (SC-002)
- **INV-2**: `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE=1` ⇒ gate skipped; nothing else changes.
- **INV-3**: setting/unsetting SYNC_DISABLE / MINIMAL_IMPORT / ENABLE_SAAS_SYNC never changes gate behavior.
- **INV-4**: `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` is a gate flag, not a sync flag — C-001/FR-016 preserved.
- Tests: `tests/review/test_pre_review_gate_*.py` rewritten to the new env.
