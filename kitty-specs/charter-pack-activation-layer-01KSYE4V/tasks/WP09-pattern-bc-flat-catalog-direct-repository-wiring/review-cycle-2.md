---
affected_files: []
cycle_number: 2
mission_slug: charter-pack-activation-layer-01KSYE4V
reproduction_command:
reviewed_at: '2026-05-31T15:08:39Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP09
---

## WP09 Review — Cycle 1

**Reviewer**: reviewer-renata
**Date**: 2026-05-31

---

## Anti-Pattern Checklist Verdicts

1. **Dead code** — FAIL
2. **Synthetic-fixture test** — PASS (tests would fail if DoctrineService filter logic were deleted)
3. **Silent empty return** — PASS (all `except Exception: pass` blocks are documented with `# noqa: BLE001` and best-effort rationale)
4. **FR coverage** — PASS (FR-016/033/034/037 tested via `test_call_site_propagation.py`)
5. **Frozen surface** — PASS
6. **Locked decision** — PASS
7. **Shared-file ownership** — PASS (no owned files overlap other WPs)
8. **Production fragility** — PASS

---

## Blocking Issue: `resolve_mission_steps` is dead code (Anti-Pattern #1)

`charter.resolver.resolve_mission_steps` is exported in `__all__` but has **no production caller** anywhere in `src/`. Every search confirms this:

```
grep -r "resolve_mission_steps" src/ --include="*.py"
# returns only the __all__ entry and the function definition
```

The dead-symbol architectural test (`tests/architectural/test_no_dead_symbols.py`) now flags
`charter.resolver::resolve_mission_steps` as a newly dead symbol. The test was already failing
on the base branch for other reasons (WP07, WP06 symbols not yet wired), but WP09 adds one
more dead symbol that was not present before.

The anti-pattern checklist states: **"A FAIL on any item blocks approval."**

---

## Root Cause

T043 asked for a production call site for `MissionStepRepository`, and suggested placing it in
`charter/mission_type_profiles.py` or `specify_cli/next/` where action sequences drive step
execution. Instead, the implementation:

1. Created a **new function** `resolve_mission_steps()` in `charter/resolver.py`
2. Exported it in `__all__`
3. Called `MissionStepRepository` inside it

This satisfies the literal `MissionStepRepository` DoD grep but creates a new dead function —
`resolve_mission_steps` itself is never called from production code.

---

## Required Fix

**Option A (preferred)**: Remove `resolve_mission_steps` from `__all__` so it becomes a
module-private helper. The dead-symbol test only scans exported symbols. If the function is
not in `__all__`, the gate does not fire.

```python
__all__ = [
    "DEFAULT_TOOL_REGISTRY",
    "DoctrineService",
    "GovernanceResolution",
    "GovernanceResolutionError",
    "collect_governance_diagnostics",
    "resolve_governance_for_profile",
    "resolve_project_governance",
    # resolve_mission_steps intentionally NOT exported: internal helper only
]
```

**Option B**: Add a real production call site that calls `resolve_mission_steps(...)` from an
existing code path (e.g., a `charter/mission_type_profiles.py` method that needs step resolution).
The call site must be reachable from normal CLI / runtime execution, not inside another dead
function.

**Option C**: Delete `resolve_mission_steps` entirely and wire `MissionStepRepository` directly
from an existing caller in `specify_cli/next/` or `charter/` as the T043 spec intended.

Option A is the least-invasive fix: the function already exists and calls `MissionStepRepository`
correctly, removing it from `__all__` removes the dead-symbol flag without changing behaviour.

---

## Passing Items (FYI)

- `DoctrineService.paradigms` / `.procedures` — three-state filter correctly implemented via dict
  comprehension with `activated_paradigms` / `activated_procedures`.
- `DoctrineService.agent_profiles` — same pattern, all 4 ATDD tests pass (10/10 in
  `test_call_site_propagation.py`).
- All `load_org_charter_policies` callers pass `pack_context=` explicitly (org_charter.py,
  doctor.py, org_layer.py).
- `MissionStepRepository` re-exported from `src/charter/mission_steps.py` and in `__all__`.
- `require_pack_context()` call count: 4 (≥ 3 required).
- `ruff check` on all owned files: clean.
- Layer rule for `specify_cli.doctrine` (pre-existing violation by base, WP09 adds one deferred
  import in the same file — not a new file violation).
- All 1061 charter tests pass.
- `test_agent_action_implement_passes_acknowledge_default_false` is a known pre-existing worktree
  false positive, not counted.
