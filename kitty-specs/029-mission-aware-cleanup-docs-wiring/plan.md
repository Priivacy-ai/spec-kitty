# Implementation Plan: Mission-Aware Cleanup & Docs Wiring
*Path: [templates/plan-template.md](templates/plan-template.md)*


**Branch**: `029-mission-aware-cleanup-docs-wiring` | **Date**: 2026-02-04 | **Spec**: kitty-specs/029-mission-aware-cleanup-docs-wiring/spec.md
**Input**: Feature specification from `/kitty-specs/029-mission-aware-cleanup-docs-wiring/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/specify_cli/missions/software-dev/command-templates/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

Clean up duplicated script entrypoints, consolidate task/acceptance helpers into a single non-deprecated implementation with consistent worktree behavior, and wire documentation mission tooling into existing CLI flows (specify, plan, research, validate/accept) without adding new public commands. Target release is 0.13.29 on `main`, then cherry-pick into `2.x`.

## Phase Plan

### Phase A – Script Cleanup & Template Alignment (WP01)
- Remove root `scripts/` duplicates after updating all references.
- Align base plan template feature detection guidance with mission template.
- Outputs: updated tests/utilities, updated `src/specify_cli/templates/command-templates/plan.md`.

### Phase B – Task Helper Consolidation (WP02)
- Introduce shared helper module and update both CLI and script entrypoints to import it.
- Ensure worktree-aware behavior parity.
- Outputs: shared helper module + updated tasks support/helper files + tests.

### Phase C – Acceptance Core Unification (WP03)
- Extract shared acceptance core and update both acceptance entrypoints to use it.
- Outputs: acceptance core module + updated acceptance entrypoints + parity tests.

### Phase D – Documentation Mission Wiring (WP04)
- Initialize documentation state during specify.
- Run gap analysis during plan/research and record canonical output.
- Detect/configure generators during plan and persist configuration in state.
- Outputs: `gap-analysis.md` for doc missions, updated `documentation_state`.

### Phase E – Documentation Mission Validation (WP05)
- Enforce presence/recency of gap analysis + documentation state during validation/acceptance.
- Add tests for missing/stale/fresh artifacts and non-doc mission gating.
- Outputs: validation logic + tests.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic  
**Storage**: N/A (file-based CLI artifacts)  
**Testing**: pytest, mypy --strict  
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows 10+)  
**Project Type**: Single repo CLI  
**Performance Goals**: CLI operations complete <2s for typical projects; dashboard handles 100+ WPs without lag  
**Constraints**: No symlinks; maintain cross-platform paths; git required; release on main (0.13.29) then cherry-pick to 2.x  
**Scale/Scope**: Medium-size CLI codebase with templates, scripts, and tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python 3.11+**: Compliant (no runtime changes beyond existing baseline).
- **Testing**: Must add/adjust pytest coverage for consolidated helpers and new mission-aware behaviors.
- **Type checking**: Maintain mypy --strict compliance for new/updated modules.
- **Cross-platform**: Changes must avoid symlinks and keep path handling portable.
- **Two-branch strategy**: **Violation/Exception required**. Constitution says new features target 2.x, but this release targets `main` (0.13.29) before cherry-picking to `2.x`.
- **Exception approval step**: Record a brief approval note in the PR/issue referencing this planned exception and the 0.13.29 release need.
- **Exception formalization**: If required by maintainers, add an ADR or explicit PR review note referencing this exception and the two-branch policy.

## Project Structure

### Documentation (this feature)

```
kitty-specs/029-mission-aware-cleanup-docs-wiring/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
└── specify_cli/
    ├── core/
    │   ├── task_helpers.py
    │   └── acceptance_core.py
    ├── cli/
    │   └── commands/
    ├── missions/
    │   ├── software-dev/
    │   └── documentation/
    ├── scripts/
    │   └── tasks/
    ├── templates/
    ├── acceptance.py
    ├── tasks_support.py
    ├── doc_generators.py
    ├── doc_state.py
    └── gap_analysis.py

scripts/
└── tasks/

tests/
├── specify_cli/
└── test_tasks_cli_commands.py
```

**Structure Decision**: Single-repo CLI structure. Work happens in `src/specify_cli` and `tests/`. Root `scripts/` will be removed after tests and references are updated to use packaged scripts.

## Module Touchpoints

- `src/specify_cli/acceptance.py`
- `src/specify_cli/core/acceptance_core.py`
- `src/specify_cli/tasks_support.py`
- `src/specify_cli/core/task_helpers.py`
- `src/specify_cli/scripts/tasks/task_helpers.py`
- `src/specify_cli/scripts/tasks/tasks_cli.py`
- `src/specify_cli/scripts/tasks/acceptance_support.py`
- `src/specify_cli/cli/commands/accept.py`
- `src/specify_cli/cli/commands/research.py`
- `src/specify_cli/cli/commands/validate_tasks.py`
- `src/specify_cli/cli/commands/agent/feature.py`
- `src/specify_cli/doc_state.py`
- `src/specify_cli/gap_analysis.py`
- `src/specify_cli/doc_generators.py`
- `src/specify_cli/templates/command-templates/plan.md`
- `src/specify_cli/missions/software-dev/command-templates/plan.md`
- `src/specify_cli/missions/documentation/mission.yaml`
- `tests/test_tasks_cli_commands.py`
- `tests/test_acceptance_support.py`
- `tests/specify_cli/` (doc mission + helper tests)

## Test Mapping

- **FR-001/SC-001**: Test suite passes after root `scripts/` removal; update tests to use packaged scripts.
- **FR-003/FR-004/SC-002**: Worktree-aware detection and conflict handling parity tests in task helper suite.
- **FR-005/FR-006/SC-003**: Documentation mission plan/research runs gap analysis and updates `documentation_state`.
- **FR-007/SC-004**: Validation/acceptance fails for missing/stale doc state or gap analysis; passes for fresh state.
- **Non-doc regression**: Plan/research/validate/accept must not invoke doc tooling for software-dev missions.
- **SC-005**: CI passes with `mypy --strict` and 90%+ coverage for new/modified modules.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New feature on `main` vs 2.x-only | 0.13.29 needs cleanup before release; users on main require fixes | Waiting for 2.x only would leave main broken and delay release readiness |
