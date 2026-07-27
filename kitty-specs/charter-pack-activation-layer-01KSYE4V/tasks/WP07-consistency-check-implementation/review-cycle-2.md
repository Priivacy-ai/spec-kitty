---
affected_files: []
cycle_number: 2
mission_slug: charter-pack-activation-layer-01KSYE4V
reproduction_command:
reviewed_at: '2026-05-31T14:35:18Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP07
review_artifact_override_at: "2026-05-31T14:44:06Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP07"
review_artifact_override_reason: "Review passed cycle-2: dead-symbol gate fixed, all AC met. 7/7 tests pass (1.07s), ruff clean, mypy strict clean. ConsistencyReport+run_consistency_check correctly allowlisted in _CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE (WP06 lane-f is documented consumer). All anti-patterns PASS. Cycle-2 rejection resolved."
---

---
review_cycle: 1
reviewer: reviewer-renata
reviewed_at: '2026-05-31'
verdict: reject
wp_id: WP07
---

# WP07 Review — Cycle 1

## Overall Verdict: REJECT (blocking issue)

One architectural gate failure blocks approval. All other criteria are met.

---

## Anti-pattern Checklist

| # | Item | Result |
|---|------|--------|
| 1 | Dead code | **FAIL — blocking** |
| 2 | Synthetic-fixture tests | PASS |
| 3 | Silent empty return | PASS (all have documented rationale) |
| 4 | FR coverage | PASS |
| 5 | Frozen surface | PASS |
| 6 | Locked decision | PASS |
| 7 | Shared-file ownership | PASS (cherry-picks from WP03/WP04 are byte-for-byte identical) |
| 8 | Production fragility | PASS |

---

## Passing Checks

- `src/charter/consistency_check.py` exists with `ConsistencyReport` (all required fields: `coherent`, `unknown_references`, `missing_from_doctrine`, `kind_violations`, `suggestions`) and `run_consistency_check()`.
- `ConsistencyReport.to_json()` is correctly implemented.
- `CharterPackManager.list_available(ctx, kind)` is used (not `get_doctrine_ids`).
- All 7 tests in `tests/charter/test_consistency_check.py` pass.
- `ruff check src/charter/consistency_check.py` — clean.
- `mypy src/charter/consistency_check.py --strict` — clean.
- Cherry-picks from WP03 (`invocation_context.py`) and WP04 (`pack_manager.py`) are byte-for-byte identical to the originals — accepted.
- Silent exception paths have documented rationale (DRG load is best-effort).
- NFR-003 performance: test completes in 1.06s (limit: 2s).

---

## Blocking Issue: Dead-Code Architectural Test Failure

**Test**: `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`
**Status**: FAILS

```
Symbol-level dead-code gate FAILED. The following public symbols are declared
in __all__ but no other src/ file imports them:
    - charter.consistency_check::ConsistencyReport
    - charter.consistency_check::run_consistency_check
```

Additionally, two stale allowlist entries now need removal:
```
Stale `_SYMBOL_ALLOWLIST` entries detected. The following symbols now have
at least one caller and must be removed from the allowlist:
    - charter.invocation_context::ProjectContext
    - doctrine.missions.models::MissionStep
```

### Root Cause

`run_consistency_check` and `ConsistencyReport` are exported in `__all__` but no
file in `src/` imports them. WP06 (the CLI consumer in lane-f) exists in a
separate lane and is not visible to the architectural gate.

### Required Fix

Choose one of the following (in order of preference):

**Option A (preferred)**: Add both symbols to
`_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` in
`tests/architectural/test_no_dead_symbols.py` with a justification comment
referencing WP06 as the pending caller:

```python
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset(
    {
        # ... existing entries ...
        # consumed by charter pack consistency-check CLI command (WP06,
        # charter-pack-activation-layer lane-f); wiring deferred
        "charter.consistency_check::ConsistencyReport",
        "charter.consistency_check::run_consistency_check",
    }
)
```

Update `_baselines.yaml` accordingly (increment `category_c_wp_in_flight_charter_scope`
from 6 to 8).

**Option B**: Add both symbols to the main `_SYMBOL_ALLOWLIST` with a tracker
ticket reference per the test's instruction (FR-303 pattern).

### Also Required

Remove the two stale allowlist entries from `_SYMBOL_ALLOWLIST`:
- `charter.invocation_context::ProjectContext`
- `doctrine.missions.models::MissionStep`

These now have live callers and the test explicitly requests their removal.
Failing to remove them will keep the test in a failing state even after the
new symbols are handled.

---

## Definition of Done — Gap

The WP07 DoD checklist does not explicitly list
`pytest tests/architectural/test_no_dead_symbols.py` but the architectural
test is part of the project's standard quality gate and fires on the new
`__all__` exports. The fix is small: update `test_no_dead_symbols.py` and
`_baselines.yaml`.

No other changes to `src/charter/consistency_check.py` or
`tests/charter/test_consistency_check.py` are needed.
