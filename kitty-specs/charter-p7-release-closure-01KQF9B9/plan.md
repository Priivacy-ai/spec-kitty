# Implementation Plan: Charter Phase 7 Release Closure

**Branch**: `main` → PR on `fix/charter-p7-release-closure` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/charter-p7-release-closure-01KQF9B9/spec.md`

## Summary

Wire the existing `validate_synthesis_state()` helper (already implemented in `src/charter/bundle.py`) into the public `charter bundle validate` CLI command so that synthesized doctrine artifacts without matching provenance sidecars fail validation. Extend the JSON report with a nested `synthesis_state` key and mirror blocking errors into the top-level `errors` list for backward compatibility. Audit and fix any Rich-to-stdout leakage when `--json` is active. Add public-CLI regression tests for each new failure mode and the `--json` contract.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI framework), rich (console output), pytest (testing), mypy strict mode
**Storage**: Filesystem only — `.kittify/doctrine/` artifacts, `.kittify/charter/provenance/*.yaml` sidecars, `.kittify/charter/synthesis-manifest.yaml`
**Testing**: pytest with integration tests for CLI commands; 90%+ coverage for new code; mypy --strict must pass
**Target Platform**: Python CLI tool (Linux, macOS)
**Project Type**: Single project (`spec-kitty` product repo)
**Performance Goals**: ≤2 seconds for bundles up to 50 artifacts on a developer workstation (NFR-003)
**Constraints**: No network calls introduced; backward compatible with legacy no-synthesis-state bundles; no new external dependencies

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| No new subsystems | ✅ Pass | Wiring an existing helper into an existing CLI command |
| No new external dependencies | ✅ Pass | `validate_synthesis_state()` is already in `src/charter/bundle.py` |
| 90%+ test coverage for new code | ✅ Planned | WP02 adds CLI regression tests covering all new paths in WP01 |
| mypy --strict passes | ✅ Planned | `BundleValidationResult` is already typed; WP01 adds typed fields to report |
| Integration tests for CLI commands | ✅ Planned | New tests in `tests/charter/test_bundle_validate_cli.py` via public CLI surface |
| Single project scope | ✅ Pass | Changes isolated to `spec-kitty` product repository |

No violations. No Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-p7-release-closure-01KQF9B9/
├── plan.md                           # This file
├── research.md                       # Phase 0 output
├── contracts/
│   └── validate-json-output.md       # JSON report contract (decision DM-01KQFAPRVNBB7V1QWN1E4C2VJ7)
└── tasks.md                          # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
└── charter_bundle.py     # Modify: call validate_synthesis_state(); extend JSON report; fix --json stdout

src/charter/
└── bundle.py             # Read-only: validate_synthesis_state() and BundleValidationResult already here

tests/charter/
├── test_bundle_validate_cli.py            # Extend: add synthesis-state CLI regression tests
└── synthesizer/
    └── test_bundle_validate_extension.py  # Read-only: existing unit tests (call helper directly, not CLI)

tests/specify_cli/cli/commands/
└── test_charter_status_provenance.py      # Read-only: existing compatibility regression guard
```

**Structure Decision**: Single project; two files modified (`charter_bundle.py` and `test_bundle_validate_cli.py`); one file read-only for reference (`bundle.py`).

## Work Packages

### WP01 — Wire synthesis-state validation and fix `--json` stdout

**Goal**: `charter bundle validate` calls `validate_synthesis_state()` and its results appear in both human-readable and JSON output with no stdout leakage.

**Files**:
- `src/specify_cli/cli/commands/charter_bundle.py` (modify)

**Tasks**:
1. Import `validate_synthesis_state` from `src.charter.bundle`
2. Call it inside `validate()` after existing bundle-compatibility checks, passing `repo_root`
3. Mirror `BundleValidationResult.errors` into the top-level report `errors` list, prefixed with `"synthesis_state: "`
4. Add `synthesis_state` key to the JSON report per the contract in `contracts/validate-json-output.md`
5. Audit the stdout path: ensure no Rich console output reaches stdout before `sys.stdout.write(...)` when `--json` is active; redirect Rich console to stderr or suppress as needed

**Definition of done**:
- `charter bundle validate` exits 1 when doctrine artifacts lack sidecars, when sidecars reference absent files, or when manifest integrity fails
- `charter bundle validate --json` stdout parses with `json.loads()` on every failure path
- Legacy bundles with no synthesis state exit 0; `synthesis_state.present` is `false`, `synthesis_state.passed` is `true`
- mypy --strict passes on modified file
- Existing tests in `tests/charter/test_bundle_validate_cli.py` and `tests/specify_cli/cli/commands/test_charter_status_provenance.py` continue to pass

### WP02 — Add public-CLI regression tests

**Goal**: Every new failure mode and the `--json` contract are exercised through the public CLI surface, not just the internal helper.

**Prerequisite**: WP01 complete.

**Files**:
- `tests/charter/test_bundle_validate_cli.py` (extend)

**Tests to add**:
1. Doctrine artifact without provenance sidecar → CLI exits 1; top-level `errors` contains `"synthesis_state: ..."` prefix
2. Provenance sidecar referencing absent artifact file → CLI exits 1
3. Synthesis manifest with invalid or mismatched integrity hash → CLI exits 1
4. `--json` for each failure type above → `json.loads(result.stdout)` succeeds; `passed` is `false`; `synthesis_state.errors` is non-empty
5. Legacy bundle (no synthesis state, no sidecars, no manifest) → exits 0; `synthesis_state.present` is `false`; `synthesis_state.passed` is `true`
6. Complete v2 bundle with valid sidecars and manifest → exits 0; `synthesis_state.passed` is `true`
7. Complete v2 bundle with `--json` → `json.loads(result.stdout)` succeeds; top-level `passed` is `true`

**Definition of done**:
- All new tests pass
- ruff check passes on the modified test file
- All existing Phase 7 tests pass (full suite from spec's Required Verification commands)
- Coverage for new code in WP01 ≥ 90%

## Phase 0: Research

See [`research.md`](research.md) for codebase findings, decisions, and alternatives considered.

## Phase 1: Design & Contracts

See [`contracts/validate-json-output.md`](contracts/validate-json-output.md) for the extended JSON report contract.

No new data-model entities. `BundleValidationResult` (existing typed dataclass in `src/charter/bundle.py`) is the only model involved.

No quickstart needed — the existing development workflow (uv run pytest, uv run mypy) applies without changes.
