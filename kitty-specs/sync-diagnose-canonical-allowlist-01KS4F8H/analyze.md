# Analyze — Sync Diagnose Canonical Event-Type Registry

**Date**: 2026-05-21
**Mission**: `sync-diagnose-canonical-allowlist-01KS4F8H`

## Prerequisites check

`spec-kitty agent mission check-prerequisites --json --include-tasks --mission sync-diagnose-canonical-allowlist-01KS4F8H`
returns:

```json
{"valid": true, "errors": [], "warnings": []}
```

Available artifacts: `spec.md`, `plan.md`, `tasks.md`, `tasks/WP01.md`,
`checklists/requirements.md`.

## Cross-artifact consistency

| Question | Answer | Evidence |
|---|---|---|
| Does the spec describe a single, well-bounded change? | Yes. Spec.md scopes the diff to `diagnose.py` + `test_diagnose.py` + mission dir; all out-of-scope artifacts named explicitly. | spec.md → "In-scope artifacts" / "Out of scope" |
| Does the plan implement the spec? | Yes. plan.md → Design → "Recognition set construction" maps 1:1 to FR-001/002/005; "Drift detector" maps to FR-004. | plan.md sections |
| Do tasks decompose the plan? | Yes. tasks.md / WP01.md split into T001 (tests), T002 (refactor), T003 (verify) — TDD order is explicit. | tasks.md → Subtask Index |
| Are FR references covered? | Yes. WP01 `requirement_refs` includes every FR-001..FR-007, NFR-001..NFR-004, and C-001..C-007. | tasks/WP01.md frontmatter |
| Any drift-class hazards (hand-rolled event dicts, non-canonical producers)? | Tests construct envelopes via the existing `_make_valid_event` helper. The envelope itself is dict-shaped because diagnose validates dicts (it's not an emission path), but the *payload contents* in any test that exercises payload shape will continue to use the canonical pydantic models per the existing convention. NFR-004 documents this. | spec.md NFR-004; existing test_diagnose.py uses canonical-shaped payloads already |
| Is the private-import (`_EVENT_TYPE_TO_MODEL`) justified? | Yes. Justified by precedent at `src/specify_cli/status/lifecycle_events.py:210`, captured in plan.md → Complexity tracking and NFR-001. | plan.md |
| Is the outbound gate (`emitter.VALID_EVENT_TYPES`) preserved? | Yes. FR-007 asserts it; plan.md → "Why not modify `emitter.VALID_EVENT_TYPES`?" explains why; existing tests at `tests/sync/test_forward_compatibility.py::TestValidEventTypesOnlyGatesOutgoing` lock it. | spec.md, plan.md |

## Coverage matrix

| Requirement | WP | Subtask(s) | Test |
|---|---|---|---|
| FR-001 (recognise every registry type) | WP01 | T001, T002 | `TestCanonicalRegistryRecognition.test_recognises_every_registry_type` |
| FR-002 (recognise CLI-internal types) | WP01 | T001, T002 | `TestCanonicalRegistryRecognition.test_recognises_cli_internal_types` |
| FR-003 (reject genuinely-unknown) | WP01 | T001, T002 | `TestCanonicalRegistryRecognition.test_rejects_genuinely_unknown_type` + existing `test_unknown_event_type` |
| FR-004 (drift detector) | WP01 | T001 | `TestCanonicalRegistryRecognition.test_drift_detector_picks_up_new_registry_entries` |
| FR-005 (no hardcoded list left) | WP01 | T002 | Source inspection + grep |
| FR-006 (existing tests pass) | WP01 | T003 | Existing `tests/sync/test_diagnose.py` |
| FR-007 (outbound surface unchanged) | WP01 | T003 | `tests/sync/test_forward_compatibility.py` + `tests/contract/test_handoff_fixtures.py` |
| NFR-001..004 | WP01 | T002 | Source inspection + diff scope |
| C-001..C-007 | WP01 | T002, T003 | Diff scope + PR ceremony |

## Findings

None. The plan, tasks, and WP01 are internally consistent and aligned
to the spec. Advance to Renata review.

## Doctrine note

This mission is the doctrine work tracked under `spec-kitty#1198` in
concrete form: the canonical-registry **is** the source of truth for
event-type recognition; tools that maintain their own allowlist are
expected to delegate. We are concretising the doctrine here, not
proposing it. Any other tool spotted with its own hardcoded allowlist
during implementation will be documented in `mission-review.md` as a
follow-up for `#1198`.
