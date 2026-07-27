# Implementation Plan: Retire Mission Identity Drift Window

**Branch**: `main` | **Date**: 2026-04-13 | **Spec**: [spec.md](spec.md)
**Mission ID**: `01KP2JNZ7FRXE6PZKJMH790HA5`
**Blocked on**: [Priivacy-ai/spec-kitty-saas#66](https://github.com/Priivacy-ai/spec-kitty-saas/issues/66)

## Summary

Remove the `legacy_aggregate_id` compatibility shim from `StatusEvent.to_dict()` and the `effective_aggregate_id` slug-fallback from three sync emitter methods. Fix two call-site gaps where `mission_id` is not currently forwarded. Update tests to assert absence of the removed field. This is a post-SaaS cleanup — implementation must not begin until `spec-kitty-saas#66` confirms drift-window closure readiness.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (existing — no new deps)
**Storage**: Filesystem only (JSONL event logs, JSON meta files)
**Testing**: pytest (90%+ coverage for new code, mypy --strict)
**Target Platform**: CLI tool (cross-platform)
**Project Type**: Single project
**Performance Goals**: N/A (no performance-critical changes)
**Constraints**: C-001 blocker on spec-kitty-saas#66; legacy event read tolerance must be preserved (C-002)
**Scale/Scope**: ~6 source files, ~2 test files, ~0 doc files with drift-window references

## Charter Check

*GATE: Passed.*

- **typer/rich/ruamel.yaml/pytest**: No new dependencies. Existing stack only. **Pass.**
- **pytest 90%+ coverage**: Shim removal will update existing tests; no new untested code. **Pass.**
- **mypy --strict**: Type signature changes (Optional → mandatory) will be checked. **Pass.**
- **Integration tests for CLI commands**: Emitter methods are tested via contract matrix. **Pass.**
- **DIRECTIVE_010 (Specification Fidelity)**: Changes map 1:1 to spec FRs. **Pass.**
- **DIRECTIVE_003 (Decision Documentation)**: The ADR already documents the identity decision. This plan documents the shim removal rationale. **Pass.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/retire-mission-identity-drift-window-01KP2JNZ/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (call-site audit)
├── meta.json            # Mission metadata
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (affected files)

```
src/specify_cli/
├── status/
│   └── models.py            # StatusEvent.to_dict() — remove legacy_aggregate_id emission
├── sync/
│   ├── emitter.py           # 3 methods — remove effective_aggregate_id fallback, make mission_id mandatory
│   └── events.py            # 2 wrapper functions — add mission_id as mandatory parameter
├── core/
│   └── mission_creation.py  # Caller — ensure mission_id is passed (already is, but verify non-None guarantee)
└── tracker/
    └── origin.py            # Caller — must start passing mission_id (currently missing)

tests/
├── status/
│   └── test_event_mission_id.py    # Flip T025/T027/T028 assertions
└── contract/
    └── test_identity_contract_matrix.py  # Update identity_locations, drift-window test
```

## Research Findings (Phase 0)

### Call-Site Audit

Verified every production call site for the three emitter methods:

| Method | Call site | Passes `mission_id`? | Action needed |
|--------|-----------|---------------------|---------------|
| `emit_mission_created` | `mission_creation.py:345` via wrapper `events.py:248` | Yes (`meta.get("mission_id")`) | Ensure non-None guarantee; tighten wrapper type |
| `emit_mission_closed` | No external callers; wrapper `events.py:275` | Wrapper omits `mission_id` entirely | Add `mission_id: str` parameter to wrapper |
| `emit_mission_origin_bound` | `tracker/origin.py:265` (direct) | No — `mission_id` not passed | Load from meta.json and pass it |

### Key Findings

1. **`emit_mission_closed` wrapper gap**: The wrapper function in `events.py:275` does not accept or forward `mission_id`. The emitter class method has it as optional. No external callers exist yet, so making `mission_id` mandatory in both the method and the wrapper is safe.

2. **`emit_mission_origin_bound` caller gap**: The call in `tracker/origin.py:265` does not pass `mission_id`. The function has access to `mission_slug` and the meta dict — it will need to load or receive `mission_id` from the caller context.

3. **`emit_mission_created` is already correct**: The caller in `mission_creation.py:350` passes `mission_id=meta.get("mission_id")`. Since all new missions get a ULID at creation time, this is always non-None for the active code path. The type can be tightened from `str | None` to `str`.

4. **Legacy event read tolerance is separate**: The reducer/store reads events from disk and deserializes them into `StatusEvent` objects. The `mission_id: str | None = None` field on the dataclass itself must remain optional because legacy events lack it. Only the *write path* (`to_dict()`) and *emit path* (emitter methods) change.

5. **No docs or CLAUDE.md updates needed**: Grep confirms no drift-window or `legacy_aggregate_id` references exist in `docs/` or `CLAUDE.md` beyond the source code docstrings being modified.

### Decision Log

| Decision | Rationale | Alternative rejected |
|----------|-----------|---------------------|
| Make `mission_id` mandatory on emitter methods | All active code paths already have it; optional type masks the invariant | Keep optional with runtime assertion — adds dead branch |
| Keep `mission_id: str | None` on `StatusEvent` dataclass | Legacy events on disk lack the field; read tolerance is C-002 | Make mandatory on dataclass — would break deserialization |
| Fix `origin.py` caller to pass `mission_id` | Required to make the emitter method mandatory | Leave as-is — would require keeping the fallback |

## Change Breakdown

### WP01: Remove `legacy_aggregate_id` from StatusEvent serialization

**Files**: `src/specify_cli/status/models.py`
**Changes**:
- Remove lines 220-223 from `to_dict()` (the `legacy_aggregate_id` assignment)
- Update the docstring (lines 175-182) to remove drift-window field documentation
- Remove the T025 comment in `src/specify_cli/status/emit.py:385`
- `mission_id` field on the dataclass stays `str | None` (legacy read tolerance)

**Risk**: Low. The field is only consumed by SaaS, which will have migrated (C-001 gate).

### WP02: Remove sync emitter drift-window fallback and make `mission_id` mandatory

**Files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/events.py`
**Changes**:
- `emit_mission_created`: change `mission_id: str | None = None` → `mission_id: str`; remove `effective_aggregate_id` fallback; always use `mission_id` as `aggregate_id`
- `emit_mission_closed`: same signature and logic change
- `emit_mission_origin_bound`: same signature and logic change
- Wrapper `emit_mission_created` in `events.py`: change `mission_id: str | None = None` → `mission_id: str`
- Wrapper `emit_mission_closed` in `events.py`: add `mission_id: str` parameter and forward it
- Update docstrings to remove backward-compat and drift-window references

**Dependency**: WP01 (conceptually parallel but cleaner if models change first)

### WP03: Fix call-site gaps for `mission_id` forwarding

**Files**: `src/specify_cli/core/mission_creation.py`, `src/specify_cli/tracker/origin.py`
**Changes**:
- `mission_creation.py:350`: change `mission_id=meta.get("mission_id")` to pass the value directly (ensure it's non-None at this point in the flow, or assert)
- `tracker/origin.py:265`: load `mission_id` from the mission's meta.json and pass it to `emit_mission_origin_bound`

**Dependency**: WP02 (must compile after signature changes)

### WP04: Update tests for final contract state

**Files**: `tests/status/test_event_mission_id.py`, `tests/contract/test_identity_contract_matrix.py`
**Changes**:
- `test_event_mission_id.py`:
  - T025 test (`test_to_dict_includes_legacy_aggregate_id_when_mission_id_present`): flip to assert `legacy_aggregate_id` is **absent**
  - T027 Fixture 2 class: remove `legacy_aggregate_id` from fixture data
  - T028 test (`test_emitted_event_legacy_aggregate_id_equals_mission_slug`): flip to assert **absence**
  - Legacy event test (`test_to_dict_omits_legacy_aggregate_id_for_legacy_events`): keep as-is (still valid)
- `test_identity_contract_matrix.py`:
  - Remove `legacy_aggregate_id` from `identity_locations` tuple for `wp_status_event`
  - Update drift-window backward-compat test to reflect new contract
  - Keep legacy event tests that verify `mission_id` absence on pre-migration events

**Dependency**: WP01 + WP02 (tests must run against updated code)

### WP05: Close-out — verify and document

**Changes**:
- Run full test suite, confirm zero regressions
- Grep codebase for `legacy_aggregate_id` — must return zero hits in `src/`
- Grep for `effective_aggregate_id` slug fallback — must return zero hits
- Update any remaining docstrings or comments that reference the drift window
- Prepare close-out comment for GitHub issue #557

**Dependency**: WP01 + WP02 + WP03 + WP04

## Execution Order

```
WP01 (models.py shim removal)
  │
  ├── WP02 (emitter signature + logic changes)  ← can start after WP01
  │     │
  │     └── WP03 (call-site fixes)  ← depends on WP02 signatures
  │           │
  │           └── WP04 (test updates)  ← depends on WP01 + WP02 + WP03
  │                 │
  │                 └── WP05 (close-out verification)  ← depends on all
  │
  └── [all blocked on C-001: spec-kitty-saas#66 complete]
```

Single lane execution — the changes are small and sequential.

## Post-Phase 1 Charter Re-check

- No new dependencies introduced. **Pass.**
- All changes are deletion or type-tightening. **Pass.**
- Test coverage maintained (updated, not reduced). **Pass.**
- No new CLI commands or user-facing surfaces. **Pass.**
