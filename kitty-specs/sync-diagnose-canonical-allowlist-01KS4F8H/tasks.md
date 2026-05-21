---
mission_slug: sync-diagnose-canonical-allowlist-01KS4F8H
mission_id: 01KS4F8HRBAQMQ5A2GNNA47JJF
generated_at: "2026-05-21T05:20:00Z"
target_branch: kitty/mission-sync-diagnose-canonical-allowlist-01KS4F8H
merge_target_branch: main
---

# Tasks — Sync Diagnose Canonical Event-Type Registry

**Mission**: `sync-diagnose-canonical-allowlist-01KS4F8H`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Anchor issue**: `Priivacy-ai/spec-kitty#1222`
**Branch**: `kitty/mission-sync-diagnose-canonical-allowlist-01KS4F8H` → merges into `main`

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Add 4 new tests in `tests/sync/test_diagnose.py`: canonical-registry recognition, CLI-internal recognition, genuinely-unknown rejection, drift detector | WP01 | [D] |
| T002 | Refactor `src/specify_cli/sync/diagnose.py`: introduce `KNOWN_EVENT_TYPES` (union of `_EVENT_TYPE_TO_MODEL.keys()` and `_PAYLOAD_RULES.keys()`), drop `VALID_EVENT_TYPES` import, update `_validate_extended_envelope` | WP01 | [D] |
| T003 | Verify: run `pytest tests/sync/test_diagnose.py tests/sync/test_forward_compatibility.py tests/contract/test_handoff_fixtures.py -v`; all green | WP01 | [D] |

---

## Work Packages

### WP01 — Replace stale allowlist in diagnose with canonical registry union

**Goal**: Delete the stale hardcoded recognition allowlist in `spec-kitty sync diagnose` and replace it with a union of the canonical events registry (`spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL`) and the local `_PAYLOAD_RULES.keys()`, so canonical event types like `TasksCompleted`, `PlanCompleted`, `GatePassed`, etc., stop surfacing as "unknown event type".
**Priority**: Critical — this is the entire mission; without it the false-positive noise in canary diagnostic output remains.
**Estimated prompt size**: ~200 lines (small mechanical refactor + four targeted tests).
**Dependencies**: none.

**Included subtasks**:
- [ ] T001 Add 4 new tests in `tests/sync/test_diagnose.py`: canonical-registry recognition, CLI-internal recognition, genuinely-unknown rejection, drift detector (WP01)
- [ ] T002 Refactor `src/specify_cli/sync/diagnose.py`: introduce `KNOWN_EVENT_TYPES` (union of `_EVENT_TYPE_TO_MODEL.keys()` and `_PAYLOAD_RULES.keys()`), drop `VALID_EVENT_TYPES` import, update `_validate_extended_envelope` (WP01)
- [ ] T003 Verify: run `pytest tests/sync/test_diagnose.py tests/sync/test_forward_compatibility.py tests/contract/test_handoff_fixtures.py -v`; all green (WP01)

**Implementation sketch**:
1. **T001 — tests first.** Append a new `TestCanonicalRegistryRecognition` class to `tests/sync/test_diagnose.py`. Each test constructs a minimal valid envelope via the existing `_make_valid_event` helper (which already produces a canonical `Event`-shaped envelope) and varies only `event_type`. The drift-detector test uses `monkeypatch.setitem` against `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` and re-imports / re-computes `KNOWN_EVENT_TYPES` via `importlib.reload` on the diagnose module to prove the registry is genuinely the source of truth.
2. **T002 — production change.** In `src/specify_cli/sync/diagnose.py`:
   - Replace `from .emitter import _PAYLOAD_RULES, VALID_EVENT_TYPES, VALID_AGGREGATE_TYPES` with `from .emitter import _PAYLOAD_RULES, VALID_AGGREGATE_TYPES`.
   - Add `from spec_kitty_events.conformance.validators import _EVENT_TYPE_TO_MODEL as _CANONICAL_EVENT_TYPE_MODELS` with a comment block explaining the precedent and pointing at `src/specify_cli/status/lifecycle_events.py:210`.
   - Define `KNOWN_EVENT_TYPES: frozenset[str] = frozenset(set(_CANONICAL_EVENT_TYPE_MODELS.keys()) | set(_PAYLOAD_RULES.keys()))`.
   - In `_validate_extended_envelope`, replace the literal-list error and `VALID_EVENT_TYPES` membership with `KNOWN_EVENT_TYPES` and a clearer error message.
3. **T003 — verify.** Run the three affected test modules. They must all pass.

**Parallel opportunities**: T001 and T002 are intentionally sequenced (test-first); T003 is the verification gate. No within-WP parallelism.

**Risks**: see plan.md → Risks and mitigations.

**Owned files**:
- `src/specify_cli/sync/diagnose.py`
- `tests/sync/test_diagnose.py`
- `kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/**`

**Acceptance criteria**:
- `pytest tests/sync/test_diagnose.py -v` green.
- `pytest tests/sync/test_forward_compatibility.py tests/contract/test_handoff_fixtures.py -v` green (FR-007 — outbound surface unchanged).
- `grep -n 'VALID_EVENT_TYPES' src/specify_cli/sync/diagnose.py` returns nothing (allowlist genuinely removed).
- `git diff main...HEAD --stat` touches only the three locations listed in NFR-003.
