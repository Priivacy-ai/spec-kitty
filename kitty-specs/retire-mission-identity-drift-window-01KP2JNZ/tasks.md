# Tasks: Retire Mission Identity Drift Window

**Mission ID**: `01KP2JNZ7FRXE6PZKJMH790HA5`
**Branch**: `main` → `main`
**Blocked on**: [Priivacy-ai/spec-kitty-saas#66](https://github.com/Priivacy-ai/spec-kitty-saas/issues/66)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Remove `legacy_aggregate_id` emission from `StatusEvent.to_dict()` | WP01 | | [D] |
| T002 | Update `StatusEvent` docstring — remove drift-window field documentation | WP01 | | [D] |
| T003 | Remove T025 comment in `emit.py` | WP01 | | [D] |
| T004 | Make `mission_id` mandatory in `emit_mission_created` emitter method, remove fallback | WP02 | |
| T005 | Make `mission_id` mandatory in `emit_mission_closed` emitter method, remove fallback | WP02 | |
| T006 | Make `mission_id` mandatory in `emit_mission_origin_bound` emitter method, remove fallback | WP02 | |
| T007 | Update wrapper `emit_mission_created` in `events.py` — make `mission_id` mandatory | WP02 | |
| T008 | Add `mission_id: str` to wrapper `emit_mission_closed` in `events.py` and forward | WP02 | |
| T009 | Update caller in `mission_creation.py` — ensure non-None `mission_id` | WP02 | |
| T010 | Update caller in `tracker/origin.py` — load and pass `mission_id` | WP02 | |
| T011 | Update docstrings in all modified emitter methods | WP02 | |
| T012 | Flip T025 assertion — `legacy_aggregate_id` presence → absence | WP03 | |
| T013 | Remove `legacy_aggregate_id` from Fixture 2 data | WP03 | |
| T014 | Flip T028 assertion — emitted event `legacy_aggregate_id` → assert absent | WP03 | |
| T015 | Verify legacy event read-tolerance test unchanged (C-002) | WP03 | |
| T016 | Update contract matrix `identity_locations` — remove `legacy_aggregate_id` | WP03 | |
| T017 | Update drift-window backward-compat test to reflect final contract | WP03 | |
| T018 | Grep audit — confirm zero `legacy_aggregate_id` / `effective_aggregate_id` fallback in `src/` | WP04 | |
| T019 | Sweep remaining drift-window comments or docstrings if any found | WP04 | |
| T020 | Prepare close-out comment for GitHub issue #557 | WP04 | |

## Work Packages

### WP01: Remove legacy_aggregate_id from StatusEvent serialization

**Priority**: High (foundational — other WPs depend on this)
**Dependencies**: None
**Estimated prompt size**: ~200 lines
**Prompt file**: [tasks/WP01-remove-legacy-aggregate-id-serialization.md](tasks/WP01-remove-legacy-aggregate-id-serialization.md)

**Summary**: Remove the `legacy_aggregate_id` drift-window shim from `StatusEvent.to_dict()` and clean up related docstrings and comments in the status package.

**Included subtasks**:
- [x] T001 Remove `legacy_aggregate_id` emission from `StatusEvent.to_dict()` (WP01)
- [x] T002 Update `StatusEvent` docstring — remove drift-window field documentation (WP01)
- [x] T003 Remove T025 comment in `emit.py` (WP01)

**Implementation notes**:
- Delete lines 220-223 in `models.py` (the `legacy_aggregate_id` assignment inside `to_dict()`)
- Keep the `if self.mission_id is not None: d["mission_id"] = self.mission_id` guard (still needed for read tolerance)
- Update the docstring block at lines 175-182 to remove the `legacy_aggregate_id` bullet
- Remove the T025 comment at `emit.py:385-386`
- The `mission_id: str | None = None` field on the dataclass stays optional (C-002: legacy read tolerance)

**Risks**: Low. Field only consumed by SaaS, which will have migrated before this WP executes (C-001).

---

### WP02: Remove emitter drift-window fallback and fix callers

**Priority**: High (core logic change)
**Dependencies**: WP01
**Estimated prompt size**: ~450 lines
**Prompt file**: [tasks/WP02-remove-emitter-drift-fallback.md](tasks/WP02-remove-emitter-drift-fallback.md)

**Summary**: Make `mission_id` a mandatory parameter on all three sync emitter methods and their wrappers. Remove the `effective_aggregate_id` slug fallback. Fix the two call sites that don't currently pass `mission_id`.

**Included subtasks**:
- [ ] T004 Make `mission_id` mandatory in `emit_mission_created` emitter method, remove fallback (WP02)
- [ ] T005 Make `mission_id` mandatory in `emit_mission_closed` emitter method, remove fallback (WP02)
- [ ] T006 Make `mission_id` mandatory in `emit_mission_origin_bound` emitter method, remove fallback (WP02)
- [ ] T007 Update wrapper `emit_mission_created` in `events.py` — make `mission_id` mandatory (WP02)
- [ ] T008 Add `mission_id: str` to wrapper `emit_mission_closed` in `events.py` and forward (WP02)
- [ ] T009 Update caller in `mission_creation.py` — ensure non-None `mission_id` (WP02)
- [ ] T010 Update caller in `tracker/origin.py` — load and pass `mission_id` (WP02)
- [ ] T011 Update docstrings in all modified emitter methods (WP02)

**Implementation notes**:
- All three emitter methods follow the same pattern: remove `effective_aggregate_id = mission_slug` fallback, change `mission_id: str | None = None` to `mission_id: str`, always use `mission_id` as `aggregate_id`
- Wrapper gap: `emit_mission_closed` in `events.py` lacks `mission_id` — add and forward
- Caller gap: `tracker/origin.py:265` doesn't pass `mission_id` — load from meta.json context
- `mission_creation.py:350` already passes `meta.get("mission_id")` but should assert non-None

**Parallel opportunities**: T004/T005/T006 can be done in parallel (different methods). T007/T008 are parallel. T009/T010 are parallel.

**Risks**: Medium. If any call site passes `None` at runtime, it will crash (TypeError). The call-site audit confirmed all active paths have `mission_id` available. mypy --strict will catch type mismatches.

---

### WP03: Update tests for final contract state

**Priority**: High (validation)
**Dependencies**: WP01, WP02
**Estimated prompt size**: ~350 lines
**Prompt file**: [tasks/WP03-update-tests-final-contract.md](tasks/WP03-update-tests-final-contract.md)

**Summary**: Update test assertions to reflect the removed shim. Flip tests that asserted `legacy_aggregate_id` presence to assert its absence. Update the contract matrix. Verify legacy read tolerance is preserved.

**Included subtasks**:
- [ ] T012 Flip T025 assertion — `legacy_aggregate_id` presence → absence (WP03)
- [ ] T013 Remove `legacy_aggregate_id` from Fixture 2 data (WP03)
- [ ] T014 Flip T028 assertion — emitted event `legacy_aggregate_id` → assert absent (WP03)
- [ ] T015 Verify legacy event read-tolerance test unchanged (C-002) (WP03)
- [ ] T016 Update contract matrix `identity_locations` — remove `legacy_aggregate_id` (WP03)
- [ ] T017 Update drift-window backward-compat test to reflect final contract (WP03)

**Implementation notes**:
- `test_event_mission_id.py`: Rename/rewrite `test_to_dict_includes_legacy_aggregate_id_when_mission_id_present` → `test_to_dict_omits_legacy_aggregate_id` asserting `"legacy_aggregate_id" not in d`
- Fixture 2 data (line 68): remove `"legacy_aggregate_id": _MISSION_SLUG` from fixture
- `test_emitted_event_legacy_aggregate_id_equals_mission_slug` → assert field absent from on-disk event
- `test_to_dict_omits_legacy_aggregate_id_for_legacy_events` (line 334): keep unchanged — still valid
- Contract matrix: change `identity_locations=("mission_id", "mission_slug", "legacy_aggregate_id")` → `("mission_id", "mission_slug")`
- Drift-window backward-compat test (line 406): update to reflect that the drift window is closed

**Risks**: Low. Test changes are mechanical — flipping assertions.

---

### WP04: Close-out verification and #557 closure

**Priority**: Medium (validation / administrative)
**Dependencies**: WP01, WP02, WP03
**Estimated prompt size**: ~150 lines
**Prompt file**: [tasks/WP04-closeout-verification.md](tasks/WP04-closeout-verification.md)

**Summary**: Final verification sweep — grep audit to confirm complete removal, full test suite run, and preparation of the #557 closure comment.

**Included subtasks**:
- [ ] T018 Grep audit — confirm zero `legacy_aggregate_id` / `effective_aggregate_id` fallback in `src/` (WP04)
- [ ] T019 Sweep remaining drift-window comments or docstrings if any found (WP04)
- [ ] T020 Prepare close-out comment for GitHub issue #557 (WP04)

**Implementation notes**:
- `grep -r legacy_aggregate_id src/` must return zero results
- `grep -r effective_aggregate_id src/` must return zero results
- Full `pytest` suite must pass
- `mypy --strict` must pass
- Draft a comment for #557 listing what was removed and linking the PR

**Risks**: Low. Purely verification and documentation.

## Execution Order

```
WP01 (StatusEvent serialization)
  └── WP02 (emitter + callers)
        └── WP03 (tests)
              └── WP04 (close-out)

All blocked on C-001: spec-kitty-saas#66 must be complete.
Single lane — sequential execution.
```
