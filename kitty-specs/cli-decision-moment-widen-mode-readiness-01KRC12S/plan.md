# Implementation Plan: CLI Decision Moment Widen Mode Readiness

**Branch**: `kitty/mission-cli-decision-moment-widen-mode-readiness-01KRC12S-lane-a` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/cli-decision-moment-widen-mode-readiness-01KRC12S/spec.md`

## Summary

The 4 failing `test_plan_widen.py` tests exit at the `assert_initialized(require_specs=True)` gate (introduced by FR-032 / WP07-T039) because the test helper `_setup_repo` creates `.kittify/` and `kitty-specs/<MISSION_SLUG>/` but never writes the required `.kittify/config.yaml`. The `_enforce_initialized` guard at the top of `plan()` (`src/specify_cli/cli/commands/lifecycle.py:109`) calls `assert_initialized()` with the default `require_specs=True`, which checks both `<root>/.kittify/config.yaml` and `<root>/kitty-specs/` and raises `SpecKittyNotInitialized` when either is missing.

The fix is to update `_setup_repo` in `tests/specify_cli/cli/commands/test_plan_widen.py` to write a minimal valid `.kittify/config.yaml` (mirroring what `spec-kitty init` produces). No production code changes are required for the test fix; FR-003/FR-004 are verified to already hold by the existing charter-widen and decision-widen-subcommand test coverage that runs against the same production code paths.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI), pytest (test runner), ruamel.yaml (YAML config parsing), readchar (interactive interview)
**Storage**: Filesystem only — `.kittify/config.yaml`, `kitty-specs/<slug>/meta.json`, `widen-pending.jsonl`
**Testing**: `uv run pytest tests/specify_cli/cli/commands/test_*_widen*.py tests/status/test_read_events_tolerates_decision_events.py`
**Target Platform**: macOS / Linux developer workstations (CLI)
**Project Type**: single-project Python CLI
**Performance Goals**: Acceptance test set executes in ≤ 30 s wall-clock
**Constraints**: MUST NOT weaken `assert_initialized`; tests stay hermetic with `SPEC_KITTY_ENABLE_SAAS_SYNC` unset; no SaaS contact
**Scale/Scope**: 1 test helper update, 0 production code changes (validation-only mission)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ DIRECTIVE_003 (Decision Documentation): This plan records why the fix is fixture-only (the production widen path is already exercised by passing tests).
- ✅ DIRECTIVE_010 (Specification Fidelity): Production behavior is not modified; the spec is faithful to what ships.
- ✅ Test coverage policy (90 %+ for new code): No new production code; existing widen-path coverage is preserved.
- ✅ mypy --strict: No production code change; type contracts unchanged.

## Project Structure

### Documentation (this feature)

```
kitty-specs/cli-decision-moment-widen-mode-readiness-01KRC12S/
├── spec.md
├── plan.md              # This file
├── meta.json
├── status.events.jsonl
└── tasks/               # Populated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/lifecycle.py          # plan() command; calls _enforce_initialized()
├── workspace/assert_initialized.py    # The gate being satisfied
├── widen/                             # Widen state + flow (no change)
└── missions/plan/plan_interview.py    # run_plan_interview entry point

tests/specify_cli/cli/commands/
├── test_plan_widen.py                 # 4 failing tests; _setup_repo to be fixed
├── test_charter_widen.py              # Passing (reference)
├── test_decision_widen_subcommand.py  # Passing
└── test_charter_prereq_suppression.py # Passing

tests/status/
└── test_read_events_tolerates_decision_events.py  # Passing
```

**Structure Decision**: Single-project Python CLI. Scope is a single test file plus its helper.

## Phase 0 — Research Outcome

- **Root cause** confirmed by running `uv run pytest tests/specify_cli/cli/commands/test_plan_widen.py -q`: all 4 failures emit `SPEC_KITTY_REPO_NOT_INITIALIZED: ... Missing: <tmpdir>/.kittify/config.yaml`.
- **Reference fix** is the equivalent of what `spec-kitty init` would write: a minimal `.kittify/config.yaml` that satisfies `assert_initialized`. The gate only checks for the file's existence (`config_path.exists()`), not its contents, so an empty-but-present file is sufficient for FR-001. We will still write valid minimal YAML so subsequent code that loads the file (`load_agent_config`, `context/resolver.py` reading `project.uuid`, etc.) does not blow up if the plan-widen flow later reads it.
- **Charter-widen passes** because, while its `_setup_repo` has the same omission, `charter` is invoked via a different code path in the affected tests (it doesn't hit `_enforce_initialized()` in the same way the integration-test wiring exercises). The cleanest, least invasive fix is to harden the plan-widen fixture rather than relax the production guard.

## Phase 1 — Design

### Implementation steps

1. Update `tests/specify_cli/cli/commands/test_plan_widen.py:_setup_repo`:
   - After creating `.kittify/`, write `.kittify/config.yaml` containing minimal valid YAML (a single `version: 1` mapping plus a `project: {uuid: <fixed-test-uuid>}` block so downstream resolvers do not raise).
   - Ensure `kitty-specs/` is created at the repo root (it already is by virtue of creating `kitty-specs/<MISSION_SLUG>/`, but make it explicit by `mkdir(parents=True, exist_ok=True)` on the parent).
2. Re-run `uv run pytest tests/specify_cli/cli/commands/test_plan_widen.py -q` and confirm 4-pass.
3. Re-run the full acceptance set (SC-001) and confirm 51 → 55 passing tests, zero failures.
4. Re-run the broader CLI slice (`tests/specify_cli/cli/commands -q`) and confirm no regressions versus the 51-baseline (SC-003).

### Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------:|-------:|-----------|
| Minimal config.yaml omits a field a downstream loader needs, causing a different exception | Low | Low | Use the well-known minimum schema (`version: 1`, `project: {uuid: …}`); fall through path was working for the equivalent charter-widen tests up to the gate change. |
| Fixture change masks a genuine production bug | Low | High | After fixing the fixture, the 4 tests must still assert the same widen behavior (Absent/Cancel/Continue/Block). No assertions are weakened. |
| Other test files have the same fixture bug | Medium | Low | If the broader CLI slice regresses, apply the same fix to other helpers. Audit via `grep -l "_setup_repo\|kitty.*mkdir" tests/`. |

## Phase 2 — Work Package outline

This mission resolves into a single sequential lane. The work is small enough that splitting into multiple WPs adds overhead without parallelism benefit.

- **WP01**: Fix `_setup_repo` in `test_plan_widen.py`; verify SC-001/SC-002/SC-003.

## Complexity Tracking

*No charter violations.*
