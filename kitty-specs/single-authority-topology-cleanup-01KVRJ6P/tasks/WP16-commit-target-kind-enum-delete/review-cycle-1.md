# WP16 — Cycle 1: BLOCKED (plan-sequencing defect, re-sequenced)

The WP16 implementer correctly STOPPED (no fake-green, no scope balloon) on a real
plan-sequencing defect: deleting the `CommitTargetKind` enum where WP16 was sequenced
(before WP05's FLATTENED-producer cleanup, before the ~27 enum-referencing test files
were drained) cannot be compile-green — and `WP05` depended on WP16 while owning a
FLATTENED producer (`upgrade.py:214`) that the deletion breaks (circular).

**Resolution (operator-approved 2026-06-23):**
- `WP05` dep re-pointed `WP16 → WP04` (WP05 cleans FLATTENED producers right after WP04).
- `WP16` re-sequenced to run **LAST in lane B** (dep `WP07`): chain
  WP04→WP05→WP06→WP17→WP07→WP16. Scope **expanded** to drain the ~27 enum-referencing
  test files (re-point enum-contract tests to the topology/predicate contract, or
  delete enum-only tests) before removing the VO field + deleting the enum.

Re-claim WP16 only after WP07 is approved. The expanded scope + new subtask T031 are
in the WP16 prompt.
