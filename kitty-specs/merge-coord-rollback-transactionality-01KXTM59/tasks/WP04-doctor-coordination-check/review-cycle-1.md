---
work_package_id: WP04
review_cycle: 1
verdict: rejected
reviewer: reviewer-renata
mission: merge-coord-rollback-transactionality-01KXTM59
requirement_refs:
- FR-007
---

# WP04 Review Cycle 1 — REJECT (reviewer-renata)

**Verdict:** REJECT — single blocker. The entire FR-007 contract is implemented correctly
(negative-AC re-verification, committed-ref derivation via `coord_incoherent_done_wps`,
canonical-surface registration, `iter_pending_coord_reconcile_markers` enumeration, delegated
idempotent `repair_coord_strand` fix). 52 tests green. Only a hygiene-suppression violation blocks.

## [MUST-FIX] Remove 3 new `# noqa: E402` suppressions
**File:** `tests/specify_cli/cli/commands/test_coordination_doctor.py:494,496,499`

Three new `# noqa: E402` were added on the WP04-block imports:
- `import json as _json`
- `from specify_cli.coordination.coherence import ...`
- `from specify_cli.merge.state import ...`

This violates DIR-030 / the charter's suppression standing order ("Do NOT disable, suppress, or
relax checks … no blanket `# noqa` … fix the code instead"). The stated rationale ("grouped with the
WP04 block, not module-top") is a locality preference, NOT a "the check is genuinely wrong about
correct code" justification — E402 is correct, and the suppression is avoidable.

**Required change:** hoist those three imports to the module top (alongside the existing
`import subprocess` / `from specify_cli.cli.commands import _coordination_doctor as cd`) and DELETE
the three `# noqa: E402` comments. Trivial, no logic change. Re-run `ruff check` to confirm clean
without the suppressions, and re-run the doctor test file to confirm still 52 passed.

## Everything else: PASS (no changes needed)
- Negative AC separator (`test_stranded_check_no_finding_for_stale_marker_over_coherent_ref`) — verified reds a marker-presence-only impl.
- Re-verification reads committed ref; enumeration via `iter_pending_coord_reconcile_markers` (not `load_state(None)`); canonical surface only; fix delegates to `repair_coord_strand`; idempotent; positive AC exit-1 + stable `error_code`; `_apply_coordination_fixes` extracted; only 2 owned files touched.
