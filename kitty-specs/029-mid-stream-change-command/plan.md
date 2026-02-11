# Implementation Plan: Mid-Stream Change Command

**Branch**: `029-mid-stream-change-command` | **Date**: 2026-02-09 | **Spec**: `kitty-specs/029-mid-stream-change-command/spec.md`
**Input**: Deliver `/spec-kitty.change` as a deterministic, branch-aware, append-only change workflow with stack-first execution.

## Summary

This feature adds `/spec-kitty.change` for mid-implementation review changes. Requests are converted into one or more change work packages (WPs), with deterministic complexity scoring, dependency validation, docs/link reconciliation, and required final testing tasks in each generated change WP.

Clarified operating rules are now part of the plan:
- Any contributor with repository access can run `/spec-kitty.change`.
- Ambiguous requests fail fast and require clarification before WP creation.
- Closed/done WPs are never reopened; new linked change WPs are created instead.
- Change WPs may depend on normal open WPs when ordering requires it.
- Implement selection is stack-first: pick any ready change WP first; if none are ready, report blockers and stop normal progression.
- Main stash is embedded directly under the planning root, not as a pseudo-feature.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, Rich, pathlib, re, json, `specify_cli.core.feature_detection`, `specify_cli.core.dependency_graph`, `specify_cli.core.dependency_resolver`, `specify_cli.tasks_support`  
**Storage**: Feature stash in `kitty-specs/<feature>/tasks/`; embedded main stash in `kitty-specs/change-stack/main/`; cross-WP references in `kitty-specs/<feature>/tasks.md`  
**Testing**: pytest unit and integration tests, mypy `--strict`  
**Target Platform**: Linux, macOS, Windows 10+  
**Project Type**: Single Python CLI package  
**Performance Goals**: Complexity preview in <=2s for <=100 open WPs; next-doable stack selection in <=250ms for <=100 open WPs  
**Constraints**: Deterministic scoring only, append-only change planning, flat `tasks/` layout, no dependency cycles, mandatory final test task per generated change WP  
**Scale/Scope**: Up to 100 open WPs per feature stash plus embedded main change stack

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ baseline | PASS | Matches constitution requirement |
| Typer + Rich CLI style | PASS | Command surface follows current architecture |
| pytest 90%+ coverage for new code | PASS (planned) | Unit + integration tests included |
| mypy --strict on new logic | PASS (planned) | New core modules are fully typed |
| Cross-platform support | PASS | No OS-specific assumptions |
| Efficient git/worktree behavior | PASS | Reuses dependency and merge utilities |
| Branch strategy alignment | PASS with note | Runtime supports `main` and feature stash routing without introducing new branch models |

No constitution gate failures detected.

## Project Structure

### Documentation Artifacts

```
kitty-specs/029-mid-stream-change-command/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    `-- change-command.openapi.yaml
```

### Runtime Planning Locations

```
kitty-specs/
|-- change-stack/
|   `-- main/                    # embedded main stash for /spec-kitty.change
`-- 029-mid-stream-change-command/
    `-- tasks/                   # feature-local stash in standard flat WP layout
```

### Source Areas

```
src/specify_cli/
|-- cli/commands/
|   |-- __init__.py                    # register top-level change command
|   |-- change.py                      # NEW: /spec-kitty.change entrypoint
|   `-- agent/
|       |-- __init__.py                # register agent change helpers
|       |-- change.py                  # NEW: preview/apply/reconcile flow
|       `-- workflow.py                # MODIFY: stack-first next-doable behavior
|-- core/
|   |-- change_classifier.py           # NEW: deterministic complexity scoring
|   |-- change_stack.py                # NEW: stash resolution + WP synthesis
|   |-- dependency_graph.py            # reused for validation
|   |-- dependency_resolver.py         # reused for merge coordination heuristics
|   `-- feature_detection.py           # update for embedded main stash routing
|-- templates/command-templates/
|   `-- change.md                      # NEW base slash command template
`-- missions/software-dev/command-templates/
    `-- change.md                      # NEW mission override template

tests/
|-- unit/
|   |-- test_change_classifier.py
|   |-- test_change_stack.py
|   `-- agent/test_change_command.py
`-- integration/
    |-- test_change_main_stash_flow.py
    `-- test_change_stack_priority.py
```

## Architecture

### 1) Command Lifecycle

1. User runs `/spec-kitty.change <request>`.
2. System resolves stash target from active branch.
3. Request validation checks target clarity; ambiguous requests fail fast.
4. Deterministic complexity scoring runs.
5. If high complexity, system recommends `/spec-kitty.specify` and asks explicit continue/stop.
6. If continue, adaptive packaging chooses single/orchestration/targeted mode.
7. New change WPs are written, dependencies validated, links reconciled, and merge coordination jobs added when needed.

### 2) Branch and Stash Routing

- On `main` or `master`: route to embedded main stash path `kitty-specs/change-stack/main/`.
- On feature branch: route to feature-local stash path `kitty-specs/<feature>/tasks/`.
- Missing stash context is treated as a blocking error.

### 3) Deterministic Complexity Model

Score components (fixed weights):
- Scope breadth (0-3)
- Coupling impact (0-2)
- Dependency churn (0-2)
- Request ambiguity (0-2)
- Integration risk (0-1)

Thresholds:
- 0-3: simple (single change WP)
- 4-6: complex (adaptive packaging)
- 7-10: high complexity (recommend `/spec-kitty.specify`, explicit decision required)

### 4) Adaptive Packaging Policy

- **single_wp**: one change WP with multiple tasks.
- **orchestration**: one coordinating change WP for tightly coupled multi-area changes.
- **targeted_multi**: multiple focused change WPs when work can be parallelized.

Selection is deterministic from coupling and dependency indicators.

### 5) Dependency and Execution Semantics

- Change WPs may depend on normal open WPs when ordering requires.
- Closed/done WPs cannot be reopened by `/spec-kitty.change`; only linked for historical context.
- Implement selection priority:
  1) ready change WPs first,
  2) if no ready change WP exists but pending change WPs remain, stop and report blockers,
  3) normal planned WPs only when change stack is empty.

### 6) Consistency and Merge Coordination

Each apply run must:
- validate dependency graph integrity (missing refs, self-edge, cycle),
- update `kitty-specs/<feature>/tasks.md` links and references,
- preserve user guardrails in generated acceptance criteria,
- create merge coordination jobs when cross-stream conflict risk is detected.

## Phase 0: Research

`kitty-specs/029-mid-stream-change-command/research.md` captures final decisions for:
- deterministic complexity model,
- adaptive packaging,
- embedded main stash path,
- append-only change generation,
- stack-first implement behavior,
- merge coordination triggers.

No unresolved clarifications remain.

## Phase 1: Design and Contracts

Generated artifacts:
- `kitty-specs/029-mid-stream-change-command/data-model.md`
- `kitty-specs/029-mid-stream-change-command/contracts/change-command.openapi.yaml`
- `kitty-specs/029-mid-stream-change-command/quickstart.md`

Post-design constitution check remains PASS.

## Test Strategy

### Unit Coverage
- deterministic score boundaries and tie-break behavior
- ambiguity fail-fast validation
- closed WP reference handling (link only, no reopen)
- dependency policy (change->normal allowed when valid)

### Integration Coverage
- embedded main stash routing on `main`
- feature stash routing on feature branches
- high complexity warning + explicit continue path
- stack-first selection behavior with blocked and ready change WPs
- merge coordination job generation for cross-stream risk

### Acceptance Checks
- each generated change WP has a final testing task
- zero broken dependency links after apply
- docs and WP links remain consistent after reconciliation

## Implementation Order

1. Add command entrypoints and command templates for `/spec-kitty.change`.
2. Implement deterministic classifier + stash resolver (including embedded main stash path).
3. Implement change WP generation pipeline with append-only semantics.
4. Integrate stack-first next-doable behavior into workflow implement selection.
5. Add reconciliation and merge coordination logic.
6. Add full unit/integration test suite and type checks.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

---

**END OF IMPLEMENTATION PLAN**
