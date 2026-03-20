# Work Packages: Orchestrator-API JSON Contract Fidelity

**Inputs**: Design documents from `/kitty-specs/053-orchestrator-api-json-contract-fidelity/`
**Prerequisites**: plan.md (root cause analysis), spec.md (user stories & requirements)

**Tests**: Integration tests explicitly required (FR-003, NFR-003).

**Organization**: 7 subtasks roll into 2 work packages. Each WP is independently deliverable.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`.

---

## Work Package WP01: Fix _JSONErrorGroup Error Handling + Docs (Priority: P0)

**Goal**: Make `_JSONErrorGroup` catch errors at both the `invoke()` and `main()` levels, ensuring JSON envelopes regardless of invocation path. Fix stale docs.
**Independent Test**: Run `spec-kitty orchestrator-api contract-version --bogus` from a shell — should produce JSON envelope on stdout, not prose stderr. Existing sub-app tests still pass.
**Prompt**: `/tasks/WP01-fix-json-error-group-and-docs.md`
**Requirement Refs**: FR-001, FR-002, FR-004, FR-005, NFR-001, NFR-002, C-001, C-003

### Included Subtasks
- [x] T001 Extract `_emit_error()` helper method on `_JSONErrorGroup`
- [x] T002 Add `invoke()` override to `_JSONErrorGroup` for nested dispatch path
- [x] T003 Update `_JSONErrorGroup` class docstring with two-level error handling explanation
- [x] T004 Remove `--json` from `docs/reference/orchestrator-api.md` contract-version signature

### Implementation Notes
- T001 and T002 are tightly coupled — `invoke()` uses `_emit_error()`, and the existing `main()` should be refactored to use it too.
- T003 is a documentation-in-code task — the docstring should explain WHY both `invoke()` and `main()` are needed.
- T004 is a one-line edit but critical for the contract.

### Parallel Opportunities
- T004 (docs fix) is independent of T001-T003 (code fix) and can be done in parallel.

### Dependencies
- None (starting package).

### Risks & Mitigations
- `ctx.exit(2)` in `invoke()` might behave differently from `raise SystemExit(2)` in `main()` → `ctx.exit()` internally raises `SystemExit`, verified in Click source.
- Double JSON emission if both `invoke()` and `main()` catch the same error → `invoke()` errors raise `SystemExit` which `main()` passes through via `except SystemExit: raise`.

---

## Work Package WP02: Root CLI Integration Tests (Priority: P0)

**Goal**: Add integration tests that invoke orchestrator-api commands through the root CLI app, proving the contract holds end-to-end.
**Independent Test**: `pytest tests/agent/test_json_envelope_contract_integration.py -v -k TestRootCLIPath` passes.
**Prompt**: `/tasks/WP02-root-cli-integration-tests.md`
**Requirement Refs**: FR-003, NFR-003, C-002

### Included Subtasks
- [ ] T005 [P] Add `TestRootCLIPath` success tests (contract-version through root CLI)
- [ ] T006 [P] Add `TestRootCLIPath` error tests (unknown flag, unknown subcommand through root CLI)
- [ ] T007 Verify existing sub-app tests still pass (regression check)

### Implementation Notes
- Import `app` from `specify_cli` (the root CLI), not from `specify_cli.orchestrator_api.commands`.
- Reuse existing `_parse_envelope()` and `_assert_usage_error()` helpers.
- Tests should run without mocking — the root CLI path is the point.

### Parallel Opportunities
- T005 and T006 are parallel (different test classes/methods, same file).

### Dependencies
- Depends on WP01 (the `invoke()` fix must be in place for root CLI path tests to pass).

### Risks & Mitigations
- Root CLI callback (`ensure_runtime`) might interfere with test isolation → Use CliRunner's `catch_exceptions=False` and mock only `ensure_runtime` if needed.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02
- **Parallelization**: WP01 and WP02 are sequential (WP02 depends on WP01).
- **MVP Scope**: WP01 alone fixes the bug. WP02 proves it.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP02 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| NFR-001 | WP01 |
| NFR-002 | WP01 |
| NFR-003 | WP02 |
| C-001 | WP01 |
| C-002 | WP02 |
| C-003 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Extract `_emit_error()` helper | WP01 | P0 | No |
| T002 | Add `invoke()` override | WP01 | P0 | No |
| T003 | Update class docstring | WP01 | P0 | No |
| T004 | Remove `--json` from docs | WP01 | P0 | Yes |
| T005 | Root CLI success tests | WP02 | P0 | Yes |
| T006 | Root CLI error tests | WP02 | P0 | Yes |
| T007 | Regression check | WP02 | P0 | No |
