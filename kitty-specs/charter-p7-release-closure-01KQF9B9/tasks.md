# Tasks: Charter Phase 7 Release Closure

**Mission**: charter-p7-release-closure-01KQF9B9
**Branch**: `main` → PR on `fix/charter-p7-release-closure`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Generated**: 2026-04-30T13:57:24Z

---

## Summary

Two sequential work packages. WP01 wires `validate_synthesis_state()` from
`src/charter/bundle.py` into the public `charter bundle validate` CLI command
and fixes the `--json` stdout contract (currently Rich text leaks to stdout
before the JSON write on sidecar failures). WP02 adds regression tests
through the public CLI surface for every new failure mode.

WP02 depends on WP01.

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|--------------|----|----------|
| T001 | Extend `charter_bundle.py` import to include `validate_synthesis_state` and `BundleValidationResult` from `charter.bundle` | WP01 | | [D] |
| T002 | Refactor sidecar error handling: remove early exit before json_output branch; collect sidecar errors into a local list; redirect Rich rendering to `err_console` | WP01 | | [D] |
| T003 | Call `validate_synthesis_state(canonical_root)` after sidecar collection; capture `BundleValidationResult` | WP01 | | [D] |
| T004 | Build `synthesis_state` dict; compute mirrored `errors` list (sidecar errors + `"synthesis_state: "` prefixed synth errors); add both to `report` | WP01 | | [D] |
| T005 | Update `result`/`passed` in report to reflect combined compliance (bundle_compliant AND no provenance errors AND synth passed); single exit gate | WP01 | | [D] |
| T006 | Extend `_render_human` to display `synthesis_state` section; confirm `mypy --strict` passes; existing tests pass | WP01 | | [D] |
| T007 | Add fixture helpers (`_add_doctrine_artifact`, `_add_provenance_sidecar`, `_add_synthesis_manifest`) to `test_bundle_validate_cli.py` | WP02 | | [D] |
| T008 | Test: doctrine artifact without sidecar → exits 1; `synthesis_state.errors` non-empty | WP02 | [D] |
| T009 | Test: provenance sidecar referencing absent artifact → exits 1 | WP02 | [D] |
| T010 | Test: synthesis manifest with mismatched `content_hash` → exits 1 | WP02 | [D] |
| T011 | Test: `--json` for each failure type → `json.loads(result.stdout)` succeeds; `passed` is False; `synthesis_state` key present | WP02 | [D] |
| T012 | Test: legacy bundle (no synthesis state) → exits 0; `synthesis_state.present` False; `synthesis_state.passed` True | WP02 | [D] |
| T013 | Test: complete v2 bundle (valid artifacts, sidecars, manifest) → exits 0; `synthesis_state.passed` True | WP02 | [D] |
| T014 | Update `test_validate_json_shape_matches_contract` to assert `synthesis_state` key in required keys | WP02 | | [D] |

---

## Work Package 01 — Wire Synthesis-State Validation and Fix `--json` Stdout

**Priority**: P0 — blocks WP02
**Estimated prompt size**: ~350 lines
**Files**: [tasks/WP01-wire-synthesis-state-and-fix-json.md](tasks/WP01-wire-synthesis-state-and-fix-json.md)

### Summary

Fix two bugs in `src/specify_cli/cli/commands/charter_bundle.py`:
1. `validate_synthesis_state()` is never called — synthesis-state failures silently pass validation.
2. When sidecar content errors occur, Rich output goes to stdout before the `--json` branch is reached — the JSON contract is broken.

### Included subtasks

- [x] T001 Extend import to include `validate_synthesis_state` and `BundleValidationResult` (WP01)
- [x] T002 Refactor sidecar error handling: remove early exit, collect locally, fix stdout leakage (WP01)
- [x] T003 Call `validate_synthesis_state(canonical_root)` after sidecar collection (WP01)
- [x] T004 Build `synthesis_state` dict and mirrored `errors` list; add to `report` (WP01)
- [x] T005 Update `result`/`passed` to reflect combined compliance; single exit gate (WP01)
- [x] T006 Extend `_render_human` for synthesis_state; mypy --strict; existing tests green (WP01)

### Implementation sketch

1. Update import line 24 to add `validate_synthesis_state, BundleValidationResult`.
2. Remove the `if sidecar_errors: console.print(...); raise typer.Exit(code=1)` block (lines 379–382) — this is the stdout leak and premature exit.
3. After sidecar collection, call `validate_synthesis_state(canonical_root)` and store result.
4. Build `synthesis_state` dict and `errors` list; add to `report` before the json_output branch.
5. Move exit logic to a single gate at the end, after rendering.
6. Extend `_render_human` to print a synthesis state section when `synthesis_state` is in the report.

### Dependencies

None (first WP).

### Risks

- `_render_human` uses `console` (stdout by default). For human mode this is fine; only `--json` mode requires stdout to be pure JSON. Keep existing `console` for human output.
- The existing test `test_validate_fails_on_missing_tracked_file` asserts `payload["bundle_compliant"] is False` — keep `bundle_compliant` semantics unchanged; add `passed` as the new overall gate.

---

## Work Package 02 — Add Public-CLI Regression Tests

**Priority**: P0
**Estimated prompt size**: ~450 lines
**Depends on**: WP01
**Files**: [tasks/WP02-regression-tests.md](tasks/WP02-regression-tests.md)

### Summary

Extend `tests/charter/test_bundle_validate_cli.py` with regression tests that exercise every new failure mode through the public CLI surface. The existing `test_bundle_validate_extension.py` tests `validate_synthesis_state()` directly — these new tests must go through the CLI.

### Included subtasks

- [x] T007 Add fixture helpers for synthesis state to `test_bundle_validate_cli.py` (WP02)
- [x] T008 Test: missing sidecar → exits 1, synthesis_state.errors non-empty (WP02)
- [x] T009 Test: sidecar referencing absent artifact → exits 1 (WP02)
- [x] T010 Test: manifest with bad content_hash → exits 1 (WP02)
- [x] T011 Test: `--json` for each failure type → strict JSON, passed=False (WP02)
- [x] T012 Test: legacy bundle → exits 0, synthesis_state.present=False (WP02)
- [x] T013 Test: complete v2 bundle → exits 0, synthesis_state.passed=True (WP02)
- [x] T014 Update `test_validate_json_shape_matches_contract` to assert `synthesis_state` key (WP02)

### Implementation sketch

1. Add three helper functions above the fixture definitions to build synthesis state fixtures.
2. Write one test per failure mode; reuse `compliant_repo` fixture as the base and mutate state.
3. Verify JSON output with `json.loads(result.stdout)` — must not raise.
4. Update `test_validate_json_shape_matches_contract` required_keys set.
5. Run full suite including Phase 7 guards.

### Dependencies

WP01 (validate_synthesis_state must be wired before tests can pass).

### Risks

- Fixture helpers must create `synthesis-manifest.yaml` with real `content_hash` and `manifest_hash` values so the valid-bundle test passes; corrupt fixture variants should target only the field under test.
