---
affected_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
cycle_number: 3
mission_slug: lifecycle-gate-execution-context-01KY72GQ
reproduction_command: PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py tests/architectural/test_exemption_registry_ratchet.py -q
reviewed_at: '2026-07-24T09:05:00Z'
reviewer_agent: reviewer-renata (claude/opus)
verdict: approved
wp_id: WP16
---

# WP16 Review — Cycle 3: APPROVE

**Reviewer:** reviewer-renata (claude / opus) · **WP:** WP16 — Retire `new_checkout_paths` + genuine byproduct enrolment
**Fix commit reviewed:** `62e8797b2` ("wire subprocess byproduct to the owner compensator (commit-on-pass / revert-on-block); pin tests on byte effect"), lane-p HEAD `b61653e07`. · **Verdict:** APPROVE

This re-review confirms the two load-bearing cycle-1/cycle-2 blocking defects are resolved. It is a
focused re-verification of the enrolment fix, not a re-derivation of the already-verified-correct
surface (symbol retirement, forced fixture edits, return-shape plumbing — all confirmed correct in
cycle 1/2 and unchanged).

## Focused re-verification of the compensator fix (the sole outstanding defect)

1. **[C3 — RESOLVED] The enrolment is now genuinely wired to a live compensator.**
   `_mt_run_transition_gates` (`tasks_move_task.py:1614-1626`) captures the snapshot
   (`byproduct_snapshots = _mt_enrol_gate_byproducts(...)`) and, on the two hard-stops
   (`if byproduct_snapshots and effect.should_exit:`), routes it through
   `restore_generated_artifact_snapshots(byproduct_snapshots)` — the SAME single restore
   compensator (TAO-3) that `merge/executor.py` uses. Committed-on-success is simply not
   restoring; reverted-on-abort/terminal-block is a real unlink. The cycle-2 "cosmetic no-op /
   discarded return value" defect is gone: the return value is retained and consumed.

2. **[DIR-041 — RESOLVED] The migrated tests now pin the observable byte effect, not the spy call.**
   The block/terminal-block arms assert `assert not sentinel.exists()`
   (`test_...observability.py:549, 739`) plus `"preserved without cleanup" not in result.output`
   (`:749`) — the created byproduct is genuinely unlinked. The success arm
   (`test_gate_created_path_is_committed_on_pass`, `:752`) asserts the byproduct is committed
   (left in place). These would red on the cycle-2 no-op; they pass now for the right reason.

3. **[C6 — RESOLVED] No observability regression.** Finding 1's real commit-or-revert removes the
   "orphan manufactured and silently abandoned" regression; falls out of finding 1 as predicted.

## Gate evidence (green)

- Byte-effect + compat: `test_tasks_move_task_pre_review_gate_observability.py` +
  `test_tasks_compat_surface.py` → **335 passed**.
- Per-symbol absence: `grep -rn new_checkout_paths src/` → EMPTY; registry row deleted (no
  `*checkout*` under `tool_artifact_enrolment/registry/`); ratchet
  `test_exemption_registry_ratchet.py` → **12 passed**; compat golden `len(SYMBOL_TO_MODULE) == 157`.

## Verdict

APPROVE. The retirement is complete and the byproduct enrolment is a genuine one-compensator
commit-on-pass / revert-on-abort wiring mirroring the merge executor. No blocking findings.
