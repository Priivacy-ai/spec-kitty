# Work Packages: Tracker Publish Resource Routing

**Inputs**: Design documents from `kitty-specs/048-tracker-publish-resource-routing/`
**Prerequisites**: plan.md (required), spec.md (user stories), data-model.md, contracts/tracker-snapshot-publish.md, quickstart.md

**Tests**: Included — the spec explicitly requires test coverage for all derivation paths and regression confirmation.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Resource Routing Implementation and Tests (Priority: P1) MVP

**Goal**: Add `RESOURCE_ROUTING_MAP`, `_resolve_resource_routing()`, and integrate routing fields into `sync_publish()` payload. Write unit tests covering all 8 derivation paths.
**Independent Test**: Run `pytest tests/specify_cli/tracker/test_service_publish.py` — all 8 test cases pass; `sync_publish()` payload includes `external_resource_type` and `external_resource_id`.
**Prompt**: `tasks/WP01-resource-routing-implementation.md`
**Estimated prompt size**: ~350 lines

### Included Subtasks
- [x] T001 Add `RESOURCE_ROUTING_MAP` module-level constant to `src/specify_cli/tracker/service.py`
- [x] T002 Add `_resolve_resource_routing()` static method to `TrackerService`
- [x] T003 Integrate routing fields into `sync_publish()` payload dict and update idempotency key hash
- [x] T004 [P] Create `tests/specify_cli/tracker/test_service_publish.py` with derivation unit tests (10 test cases including empty-creds-present and idempotency rebind)
- [x] T005 Add payload integration test verifying both fields appear in the HTTP request body

### Implementation Notes
- `RESOURCE_ROUTING_MAP` is a `dict[str, tuple[str, str]]` mapping normalized provider names to `(external_resource_type, credential_key)` pairs.
- `_resolve_resource_routing()` is a `@staticmethod` — pure function, no I/O, no side effects.
- Payload integration: insert `external_resource_type` and `external_resource_id` into the payload dict in `sync_publish()`, right after `workspace`.
- Idempotency key: the existing hash in `sync_publish()` must be updated to include `resource_type` and `resource_id` so that rebinding to a different project_key/team_id is not deduplicated.
- Tests mock `_load_runtime()` to avoid requiring `spec-kitty-tracker` dependency. Use `httpx_mock` or `respx` to intercept the HTTP POST and inspect the payload.
- Note: `_load_runtime()` does NOT validate credential completeness — it succeeds even when credentials lack routing keys. Tests must cover this path.

### Parallel Opportunities
- T004 (unit tests for derivation logic) can be written in parallel with T001-T003 since the method signature is known from the plan.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Risk**: `spec-kitty-tracker` import needed for `_load_runtime()` in integration tests. **Mitigation**: Mock `_load_runtime()` to return test config/credentials/store without the external dependency.
- **Risk**: Existing `sync_publish()` tests (if any) may need updating. **Mitigation**: Check for existing publish tests; if found, verify they still pass with the new payload shape.

---

## Work Package WP02: Contract Documentation and Regression Validation (Priority: P1)

**Goal**: Update the repo-root `contracts/batch-api-contract.md` to reference the new tracker snapshot payload fields. Confirm zero regressions in event envelope tests, batch contract fixtures, and existing tracker tests.
**Independent Test**: All existing test suites pass unchanged. `contracts/batch-api-contract.md` documents the new fields.
**Prompt**: `tasks/WP02-contract-docs-and-regression.md`
**Estimated prompt size**: ~250 lines

### Included Subtasks
- [x] T006 Update `contracts/batch-api-contract.md` with a new section documenting the tracker snapshot publish payload extension
- [x] T007 [P] Run `tests/contract/test_handoff_fixtures.py` to confirm event envelope fixtures pass unchanged
- [x] T008 [P] Run `tests/specify_cli/tracker/test_credentials.py` and `tests/specify_cli/tracker/test_store.py` to confirm zero regressions
- [x] T009 Verify `docs/reference/event-envelope.md` requires no changes (git event envelope untouched)

### Implementation Notes
- The batch-api-contract.md already covers the event envelope (Section 2) and batch request/response (Section 3). Add a new section or appendix for the tracker snapshot publish payload, referencing `kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md` for full detail.
- Regression tests are confirmation-only — no code changes expected. If any fail, investigate whether WP01 accidentally modified shared code.

### Parallel Opportunities
- T007 and T008 are fully parallel — they test different subsystems.
- T006 can proceed in parallel with T007/T008 since it's documentation-only.

### Dependencies
- Depends on WP01 (routing fields must be implemented before documenting and validating them).

### Risks & Mitigations
- **Risk**: Event envelope test failures. **Mitigation**: WP01 explicitly does not touch `EventEmitter` or the event envelope. If tests fail, the root cause is elsewhere.

---

## Dependency & Execution Summary

- **Sequence**: WP01 (implementation + tests) → WP02 (docs + regression)
- **Parallelization**: WP01 is independent; WP02 depends on WP01. Within WP01, T004 can start before T001-T003 are done.
- **MVP Scope**: WP01 alone delivers the core functionality. WP02 adds documentation and regression confidence.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add RESOURCE_ROUTING_MAP constant | WP01 | P1 | No |
| T002 | Add _resolve_resource_routing() method | WP01 | P1 | No |
| T003 | Integrate routing fields into sync_publish() payload | WP01 | P1 | No |
| T004 | Create derivation unit tests (8 cases) | WP01 | P1 | Yes |
| T005 | Add payload integration test | WP01 | P1 | No |
| T006 | Update contracts/batch-api-contract.md | WP02 | P1 | No |
| T007 | Run event envelope regression tests | WP02 | P1 | Yes |
| T008 | Run existing tracker tests | WP02 | P1 | Yes |
| T009 | Verify event-envelope.md unchanged | WP02 | P1 | Yes |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
<!-- status-model:end -->
