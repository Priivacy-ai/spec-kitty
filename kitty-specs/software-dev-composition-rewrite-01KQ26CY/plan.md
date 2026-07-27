# Implementation Plan: Software-Dev Mission Composition Rewrite

**Mission slug**: `software-dev-composition-rewrite-01KQ26CY`
**Mission ID**: `01KQ26CYMMB4SZP2RKVH74RRB5`
**Branch**: `main` (planning base = merge target = `main`, branch_matches_target = true)
**Date**: 2026-04-25
**Spec**: [spec.md](spec.md)
**Tracker**: [#503] · parent epic [#468] · umbrella [#461]

## Summary

Rewire the built-in `software-dev` mission so its five public actions (`specify`, `plan`, `tasks`, `implement`, `review`) execute through `StepContractExecutor` composing `ProfileInvocationExecutor` invocations on the live runtime path. The `tasks` action becomes a single public composition step whose internal substructure preserves the legacy `tasks_outline → tasks_packages → tasks_finalize` semantics. The runtime bridge stops dispatching via `mission-runtime.yaml` step IDs for `software-dev` and instead delegates to composition; the legacy template is marked deprecated with a header comment but left on disk as a transitional reference.

## Locked Decisions (from spec assumption table)

- **D-1 (was A-1) — Tasks-phase mapping:** `tasks` is the single public composition step. A new `tasks.step-contract.yaml` carries three internal sub-steps (`outline`, `packages`, `finalize`) with the same artifact and validation semantics the legacy DAG had.
- **D-2 (was A-2) — Tasks profile default:** Reuse `architect-alphonso` for `(software-dev, tasks)`. No new profile is introduced. (Existing default for `plan` is also `architect-alphonso`; this keeps the planning-lineage interpretation explicit.)
- **D-3 (was A-3) — Legacy file disposition:** `mission-runtime.yaml` stays on disk and gains a deprecation header comment. `mission.yaml` v0/v1 fields stay untouched. No deletions in this slice.

## Technical Context

**Language/Version**: Python 3.11+ (per existing spec-kitty codebase; charter pins this).
**Primary Dependencies**: `typer` (CLI), `rich` (console), `ruamel.yaml` (frontmatter / YAML), `pytest` (tests), `mypy --strict` (type check). Internal dependencies: `charter` (DRG loader), `doctrine` (mission-step-contract models + repository), `specify_cli.invocation.executor.ProfileInvocationExecutor`, `specify_cli.mission_step_contracts.executor.StepContractExecutor`, `specify_cli.next.runtime_bridge`, `specify_cli.runtime.agent_commands`.
**Storage**: Filesystem only. Step contracts live under `src/doctrine/mission_step_contracts/shipped/`. Action governance lives under `src/doctrine/missions/software-dev/actions/<action>/index.yaml`. No DB.
**Testing**: pytest with `PWHEADLESS=1` for any browser-touching paths (none expected here). Run from project root: `cd src && pytest`. Charter requires ≥90% coverage on new code and `mypy --strict` clean.
**Target Platform**: macOS / Linux developer workstations + CI. No runtime OS branching introduced.
**Project Type**: Single project (existing `src/`, `tests/`).
**Performance Goals**: Live-path wall-clock per action within ±15% of pre-rewrite baseline (NFR-001). Composition adds at most a small constant overhead (DRG load + step-contract repository read), both already paid by the executor's existing tests.
**Constraints**: C-001..C-008 from spec.md, in particular C-007 (no touching of `spec-kitty-events` package or libraries-vs-`charter.md` alignment — concurrent agent owns that). C-001 keeps `StepContractExecutor` a pure composer.
**Scale/Scope**: One mission (built-in `software-dev`), five actions, one new step-contract file, one runtime-bridge integration seam, ~3 focused test files, plus deprecation comments on two YAML files.

## Charter Check

*Gate: must pass before Phase 0. Re-checked after Phase 1.*

Charter (`.kittify/charter/charter.md`) policy summary loaded via `spec-kitty charter context --action plan`. Action doctrine for `plan`: DIRECTIVE_003 (decision documentation), DIRECTIVE_010 (specification fidelity); tactics include adr-drafting-workflow, problem-decomposition, premortem-risk-identification, requirements-validation-workflow, stakeholder-alignment.

| Charter constraint | This plan | Verdict |
|-------------------|-----------|---------|
| typer / rich / ruamel.yaml / pytest stack | All touched files already in this stack; no new deps introduced | ✅ Pass |
| mypy --strict clean | New step-contract YAML carries no Python; new runtime-bridge code uses existing typed abstractions (`StepContractExecutionContext`, `MissionStepContract`) | ✅ Pass |
| ≥90% coverage on new code | New code paths are narrow: one runtime-bridge branch + one new step-contract loader entry + new composition test file. Coverage target met by dedicated tests in WP3. | ✅ Pass |
| DIRECTIVE_003 (decision documentation) | Three locked decisions (D-1, D-2, D-3) recorded in this plan; ADR not warranted (these are tactical scope decisions inside one mission slice, not architecture-shifting). | ✅ Pass — record-in-plan satisfies |
| DIRECTIVE_010 (specification fidelity) | Plan derives directly from FR-001..011, NFR-001..004, C-001..008. No drift. | ✅ Pass |
| C-007 boundary (no events / charter alignment work) | Plan touches zero files in `src/spec_kitty_events/` or anything under `.kittify/charter/`. Verified by file list below. | ✅ Pass |

Post-Phase-1 re-check: deferred to end of plan generation.

## Project Structure

### Documentation (this feature)

```
kitty-specs/software-dev-composition-rewrite-01KQ26CY/
├── plan.md              # this file
├── spec.md              # already committed
├── research.md          # Phase 0 output (this plan)
├── data-model.md        # Phase 1 output (this plan)
├── quickstart.md        # Phase 1 output (this plan)
├── contracts/           # Phase 1 output (this plan)
├── checklists/
│   └── requirements.md  # already committed
└── tasks/               # /spec-kitty.tasks output (NOT this command)
```

### Source Code (repository root) — files this slice touches

```
src/doctrine/missions/software-dev/
├── mission-runtime.yaml                 # MODIFY: prepend deprecation header
└── (mission.yaml left untouched per D-3)

src/doctrine/missions/software-dev/actions/tasks/
├── index.yaml                           # READ-ONLY (already correct)
└── guidelines.md                        # CREATE: parity with other actions
                                          # (specify/plan/implement/review each have one;
                                          # tasks does not — see research.md R-3)

src/doctrine/mission_step_contracts/shipped/
├── tasks.step-contract.yaml             # CREATE: new contract for tasks action
                                          # with sub-steps outline/packages/finalize
└── (specify, plan, implement, review contracts left untouched)

src/specify_cli/mission_step_contracts/
└── executor.py                          # MODIFY: add ("software-dev","tasks")
                                          # entry to _ACTION_PROFILE_DEFAULTS

src/specify_cli/next/
└── runtime_bridge.py                    # MODIFY: add composition dispatch path
                                          # for software-dev's five public actions;
                                          # legacy DAG branch kept reachable but
                                          # bypassed for composed actions
                                          # (see data-model.md §Integration Seam)

tests/specify_cli/mission_step_contracts/
└── test_software_dev_composition.py     # CREATE: dedicated test file per NFR-002

tests/specify_cli/next/
└── test_runtime_bridge_composition.py   # CREATE: integration test for the
                                          # runtime-bridge → composition handoff
```

**Structure Decision**: Single-project layout (existing). No new top-level packages. The composition rewrite is additive plus one targeted modification per affected file. `mission-runtime.yaml` and the legacy v0/v1 sections of `mission.yaml` remain on disk per D-3 to keep the diff small and avoid blast radius for parallel work (in particular the C-007-protected concurrent agent's churn in `spec-kitty-events` and library boundaries).

## Phase 0 — Research

See [research.md](research.md). Three resolved items:

- **R-1**: How `StepContractExecutor.execute` resolves action context and routes through `ProfileInvocationExecutor` — confirmed from source review.
- **R-2**: Where the runtime bridge currently dispatches step IDs and runs CLI guards — pinpointed in `runtime_bridge.py` lines 180–225 and 254–360.
- **R-3**: Why a `tasks.step-contract.yaml` does not yet exist while `actions/tasks/index.yaml` does — confirmed: only `specify`, `plan`, `implement`, `review` have shipped contracts. The `tasks` action was always handled in the legacy DAG split. This slice closes that gap.

No `[NEEDS CLARIFICATION]` markers remain.

## Phase 1 — Design

### Data model

See [data-model.md](data-model.md). Captures:

- **`MissionStepContract` for `tasks`**: schema_version 1.0, id `tasks`, action `tasks`, mission `software-dev`, three sub-steps (`outline`, `packages`, `finalize`), each with declared command + delegations matching the legacy guard semantics.
- **Profile defaults extension**: one new entry in `_ACTION_PROFILE_DEFAULTS` — `("software-dev", "tasks") → "architect-alphonso"`.
- **Runtime-bridge composition dispatch**: the integration seam, expressed as a single function-level decision: when `mission == "software-dev"` and `step_id ∈ {"specify","plan","tasks","implement","review"}` (note: collapsed `tasks_*` to single `tasks`), construct `StepContractExecutionContext` and call `StepContractExecutor.execute`. CLI guards in `_check_step_guards` are migrated to fire post-composition for the five action IDs (with the `tasks_*` triplet collapsed into one composed `tasks` guard).

### Contracts

See [contracts/](contracts/). Two artifacts:

- `contracts/tasks-step-contract-schema.md` — the YAML shape the new `tasks.step-contract.yaml` must obey, in human-readable form.
- `contracts/runtime-bridge-composition-api.md` — the call-site contract between the runtime bridge and `StepContractExecutor` for software-dev (inputs, outputs, error propagation, lane-state invariant).

### Quickstart

See [quickstart.md](quickstart.md). Operator-facing walkthrough: how a fresh `software-dev` mission flows through composition end-to-end after this slice lands. Includes the verification commands a reviewer can run to confirm composition (not the legacy DAG) routed each action.

## Migration Path (smallest safe slice)

1. **Add `tasks.step-contract.yaml`** under `src/doctrine/mission_step_contracts/shipped/`. Three sub-steps mirror the legacy guards.
2. **Extend `_ACTION_PROFILE_DEFAULTS`** in `executor.py` with the `tasks` entry. Single-line change.
3. **Wire the composition dispatch branch** in `runtime_bridge.py`. New helper function selects composition for the five action IDs on `software-dev`; everything else falls through to the existing DAG path. This keeps blast radius minimal for any non-software-dev mission still using the runtime bridge.
4. **Migrate `_check_step_guards` semantics** for the five IDs into composition (call them after the composed run completes, on the same artifacts). Collapse the legacy `tasks_outline`/`tasks_packages`/`tasks_finalize` guard set into one composed-`tasks` guard that asserts: `tasks.md` exists, ≥1 `tasks/WP*.md` exists, and every WP has a raw `dependencies` field in frontmatter. Reuses `_has_raw_dependencies_field`.
5. **Add `actions/tasks/guidelines.md`** for parity with other action directories (per R-3). Content: a short, action-scoped guideline document mirroring the structure of the other four.
6. **Mark legacy templates deprecated**: prepend a header comment block to `src/doctrine/missions/software-dev/mission-runtime.yaml` indicating it is a transitional reference and the live path is now composition-driven. `mission.yaml` left untouched (D-3).
7. **Tests**:
   - `test_software_dev_composition.py`: exercises each of the five action IDs through `StepContractExecutor.execute` against the real shipped contracts; asserts profile defaults, action-scoped governance scope, invocation_id chain.
   - `test_runtime_bridge_composition.py`: end-to-end through the bridge, asserting composition is selected for software-dev and CLI guards still fire.
   - Existing tests (`test_executor.py`, `test_runtime_bridge.py`, `test_agent_commands_routing.py`) must remain green.

## Premortem (sabotage check)

| Failure mode | Likelihood | Mitigation |
|---|---|---|
| New `tasks.step-contract.yaml` schema diverges from `MissionStepContract` model | Low | Run executor's repository loader in tests; will raise validation error early. |
| Composition dispatch branch fires for non-software-dev missions and breaks them | Medium | Guard branch on `mission == "software-dev"` AND `step_id` membership. Tests cover the negative case. |
| `tasks` guard collapse silently weakens validation | Medium | New guard reuses every legacy assertion (`tasks.md`, `WP*.md` existence, `dependencies` frontmatter). Test asserts each negative case still fails. |
| `architect-alphonso` profile default for `tasks` is wrong | Low — D-2 user-locked | Operator can override via `--profile`. Documented in plan; flip is a one-line change. |
| Legacy DAG path bit-rots while still on disk | Low | Header comment marks deprecation; existing tests still exercise it; this slice does not touch that code path's logic. |
| Concurrent C-007 agent edits `mission.yaml` and creates a merge conflict | Medium | We touch only `mission-runtime.yaml` (header comment) and add NEW files. `mission.yaml` is left untouched per D-3, eliminating the most likely conflict surface. |
| `actions/tasks/guidelines.md` content drifts from action's actual scope | Low | Mirror structure and tone of `implement/guidelines.md` and `plan/guidelines.md`; keep it minimal. |

## Re-evaluated Charter Check (post-Phase 1)

Re-running the gates above after design artifacts are drafted: no new violations. The data-model and contract artifacts stay within the typed substrate (`MissionStepContract`, `StepContractExecutionContext`); no Python-level abstractions are introduced; no new dependencies; no shifts in the C-002 boundary (host LLM owns generation, Spec Kitty owns composition). ✅

## Complexity Tracking

*No charter violations — section intentionally empty.*

## Out-of-scope reaffirmations

- `#505` custom mission loading. Not in any WP.
- `#506`/`#507`/`#508`/`#509`/`#511` retrospective work. Not in any WP.
- `spec-kitty explain` / Phase 4 / Phase 5 reopens. Not in any WP.
- `spec-kitty-events` package layout, libraries-vs-charter alignment. Owned by concurrent agent (C-007). Not in any WP.

## Branch Contract (restated, per command requirement)

- **Current branch at plan start**: `main`
- **Planning / base branch**: `main`
- **Final merge target for completed changes**: `main`
- **branch_matches_target**: `true` ✅

## Next command

`/spec-kitty.tasks` — to break this plan into work packages.
