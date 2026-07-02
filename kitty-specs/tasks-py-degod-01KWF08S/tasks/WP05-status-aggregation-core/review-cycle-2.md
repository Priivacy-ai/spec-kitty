---
affected_files: []
cycle_number: 2
mission_slug: tasks-py-degod-01KWF08S
reproduction_command:
reviewed_at: '2026-07-01T22:47:41Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

# WP05 Review — Cycle 1 (reviewer-renata)

**Verdict: Changes requested.** The pure-parity substance is impeccable — the ONLY
blocker is a strict-mypy hygiene gap in the new **test** file. This is a ~6-line
fix; do NOT touch the (correct) core, do NOT weaken any assertion, do NOT add
`# type: ignore` / `# noqa`.

## What is verified GREEN (no action needed)

- **Byte-identical aggregation (FR-006/FR-002/NFR-002):** confirmed against the
  original `status` body:
  - `lane_counts` reproduces `dict(Counter(...))` first-seen order (explicit
    `+= 1` loop over the same row order).
  - `_kanban_rollup` seeds every non-`GENESIS` `Lane` in enum order, appends to
    the lane bucket, and routes off-board rows to `"other"` via `setdefault` —
    identical key set / insertion order / row-object identity to the inline
    `by_lane` grouping.
  - `0` vs `0.0`: `_weighted_progress_percentage` returns `cast(float, 0)` — a
    runtime **int** `0` on the no-snapshot arm, so `--json` emits `0` not `0.0`.
    Directly pinned by `test_progress_percentage_falls_through_to_int_zero_without_snapshot`
    (asserts `isinstance(..., int)`).
  - Shared row-object mutation aliasing (`view.lanes` holds the same dicts the
    shell later mutates with stale/display fields) is faithful to the original.
- **`build_stale_fallback_results` move:** verbatim parity with the deleted
  `_build_stale_fallback_results` (the added `str(...)` wraps are runtime no-ops
  for string WP ids, required only for the `object`-typed row). Old private name
  has **no other callers** in `src/` or `tests/`; both `except MissingLanesError`
  arms (JSON + rich leg) are rewired; the helper is pure.
- **Purity (INV-4):** no filesystem / git / `datetime.now` / emit in
  `tasks_status_view.py`. `dependency_readiness_for_wp` is pure (no I/O).
- **Inline block genuinely deleted, not shadowed;** sentinel T025 is
  non-tautological (monkeypatches `build_status_view` to a contradictory view and
  asserts JSON envelope + human summary follow the sentinel).
- **Gates:** `test_tasks_status_view.py` + `test_tasks_cli_contract.py` = 62
  passed / 1 skipped, **100% branch cov (16/16 arcs)** on the core; full
  `tests/specify_cli/cli/commands/agent/` = **899 passed / 2 xfailed**; core
  `tasks_status_view.py` is strict-mypy clean; ruff clean; zero suppressions added.
- Anti-pattern checklist 1–8: PASS. (Note item 1: `StatusView.dependency_readiness`
  is computed-but-unread today — it is the documented forward seam for WP06, which
  depends on WP05; the `build_status_view` function itself is live-called. Item 7:
  the `tasks.py` edit is the documented WP09-owned leeway edit per the WP prompt.)

## Blocker — fix before re-review

**`tests/specify_cli/cli/commands/agent/test_tasks_status_view.py` fails
`mypy --strict` (6 errors).** Every sibling pure-core test in THIS mission
(`test_tasks_ports.py`, `test_tasks_transition_core.py`, `test_tasks_mapping_core.py`)
is strict-clean, and CLAUDE.md / the charter Code Review Checklist require new code
to pass `mypy --strict` with zero issues. (CI's mypy job is src-scoped + advisory,
so it will not fail the gate — but the in-mission peer norm and project MUST make
this a real regression.)

```
test_tasks_status_view.py:242: error: "object" has no attribute "stale"      [attr-defined]
test_tasks_status_view.py:243: error: "object" has no attribute "stale"      [attr-defined]
test_tasks_status_view.py:244: error: "object" has no attribute "is_stale"   [attr-defined]
test_tasks_status_view.py:245: error: "object" has no attribute "error"      [attr-defined]
test_tasks_status_view.py:253: error: "object" has no attribute "stale"      [attr-defined]
test_tasks_status_view.py:299: error: Missing type arguments for generic type "list"  [type-arg]
```

**Fix (no suppressions):**
1. `build_stale_fallback_results` returns `dict[str, object]`, so the `results[...]`
   lookups at lines 241–245 / 253 are typed `object`. Bind through a
   `cast("StaleCheckResult", results["WP01"])` (import `StaleCheckResult` from
   `specify_cli.core.stale_detection`) before dereferencing `.stale` / `.is_stale`
   / `.error`.
2. Line 299 (`_sentinel_view`): annotate the empty-bucket dict fully, e.g.
   `lanes: dict[Lane | str, list[dict[str, object]]] = {...}` (or reuse the core's
   `StatusRow` alias).

Re-run to confirm before resubmitting:
`mypy tests/specify_cli/cli/commands/agent/test_tasks_status_view.py` → `Success`,
then the WP05 test module + `--cov-branch` stays 100%.
