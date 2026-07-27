# Implementation Plan: Plan Concern Vocabulary and WP Traceability

**Branch**: `kitty/mission-plan-concern-vocabulary-and-wp-traceability-01KTE2S9` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/plan-concern-vocabulary-and-wp-traceability-01KTE2S9/spec.md`

## Summary

Introduce a formal "implementation concern" vocabulary (`IC-01`, `IC-02`, …) at the plan phase and add `plan_concern_refs` traceability to the WP manifest schema. The plan templates' pseudo-WP sections ("Parallel Work Analysis", "Work Distribution", "Agent Assignments") are replaced with an "Implementation Concern Map". The `WorkPackageEntry` pydantic model gains an optional `plan_concern_refs: list[str]` field with IC-## validation. Task prompts are updated to require concern citation. The rendering function is extended to surface concern coverage in generated `tasks.md`.

**Approach**: Three sequential implementation concerns — (1) template language, (2) schema + rendering, (3) tests/snapshots/docs. WP boundaries follow this IC decomposition. The schema change (IC-02) depends on IC-01 being merged so snapshot tests in IC-03 can reflect the final template content.

**Alternatives rejected**: Implementing all three concerns in a single WP was considered but rejected because the template-only changes in IC-01 are reviewable in isolation and do not require Python changes; mixing them increases review surface unnecessarily.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (WorkPackageEntry schema), ruamel.yaml (wps.yaml parsing), pytest (tests), ruff (lint), mypy --strict (type checking)
**Storage**: No new storage — extends existing `wps.yaml` YAML manifest with optional field
**Testing**: pytest with ≥90% branch coverage on modified `wps_manifest.py` paths; command-renderer snapshot tests regenerated via `PYTEST_UPDATE_SNAPSHOTS=1`
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Performance Goals**: N/A — offline, local file operations only
**Constraints**: `plan_concern_refs` empty-list default; zero regressions in existing `finalize-tasks` calls; `mypy --strict` must pass
**Scale/Scope**: ~8 source files modified; ~3 prompt files updated; ~4 test files added/updated

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **typer / rich / ruamel.yaml / pydantic**: All in use already — no new dependencies introduced. ✓
- **pytest, mypy --strict**: Both required; this mission adds tests and must pass type checking. ✓
- **90%+ test coverage**: New `plan_concern_refs` paths (field validator, rendering, backwards-compat) require explicit test coverage. ✓
- **DIRECTIVE_003** (Decision Documentation): Template section naming and IC-## format are decisions; rationale captured in this plan. ✓
- **DIRECTIVE_010** (Specification Fidelity): Implementation must produce the IC-## placeholder structure and `plan_concern_refs` field exactly as specified in FR-001–FR-013. ✓
- **No charter violations found.** ✓

## Project Structure

### Documentation (this mission)

```
kitty-specs/plan-concern-vocabulary-and-wp-traceability-01KTE2S9/
├── plan.md         # This file
├── research.md     # Phase 0 output (minimal — codebase is fully understood)
├── data-model.md   # Phase 1 output
└── tasks.md        # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source files modified (repository root)

```
src/doctrine/missions/software-dev/templates/
└── plan-template.md                         # IC-01: replace Parallel Work Analysis

src/doctrine/missions/mission-steps/software-dev/
├── plan/prompt.md                           # IC-01: update stop-point language
├── tasks/prompt.md                          # IC-01: update description header
├── tasks-outline/prompt.md                  # IC-02: add IC citation requirement
└── tasks-packages/prompt.md                 # IC-02: carry plan_concern_refs to frontmatter

src/doctrine/missions/built_in_step_contracts/
└── tasks.step-contract.yaml                 # IC-01: fix "derived from the plan" wording

src/specify_cli/core/
└── wps_manifest.py                          # IC-02: add plan_concern_refs + cross_cutting fields

tests/specify_cli/core/
└── test_wps_manifest.py                     # IC-03: new/extended unit tests

tests/specify_cli/skills/
└── test_command_renderer.py                 # IC-03: regenerate snapshots if needed

tests/specify_cli/regression/_twelve_agent_baseline/
└── **/plan.*  **/tasks*.*                   # IC-03: refresh if renderer touches these
```

## Implementation Concern Map

### IC-01 — Plan template language

**Purpose**: Eliminate plan-phase pseudo-WP vocabulary so planners cannot accidentally produce WP-like slices at the plan stage.

**Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005

**Affected surfaces**:
- `src/doctrine/missions/software-dev/templates/plan-template.md` — canonical template read by `MissionTemplateRepository`
- `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md` — stop-point and report language
- `src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md` — description header
- `src/doctrine/missions/built_in_step_contracts/tasks.step-contract.yaml` — step outline description

**Sequencing**: No dependencies. Can start immediately. IC-02 and IC-03 may begin after IC-01 is merged.

**Risks**: The `plan-template.md` is the canonical template loaded by `MissionTemplateRepository`; the `src/specify_cli/missions/software-dev/templates/plan-template.md` copy (stranded, no live consumer) is out of scope per spec assumption. Do not edit the stranded copy.

**Coordination**: This concern is text-only. No Python changes. Fast to review.

---

### IC-02 — WP manifest schema and rendering

**Purpose**: Give the task manifest a machine-readable place to record which plan concerns each WP addresses, and surface that in generated artifacts.

**Relevant requirements**: FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-013

**Affected surfaces**:
- `src/specify_cli/core/wps_manifest.py` — `WorkPackageEntry` model, `generate_tasks_md_from_manifest()`
- `src/doctrine/missions/mission-steps/software-dev/tasks-outline/prompt.md`
- `src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md`

**Sequencing**: Depends on IC-01 being merged (so the prompt changes are coherent). Schema change is backwards-compatible — field defaults to `[]`.

**Risks**:
- `cross_cutting` is a new boolean field; must also default to `False` and not break existing `wps.yaml` files.
- `finalize-tasks` warning (FR-013) must be non-fatal — existing missions must not break.
- The `field_validator` for `plan_concern_refs` must use `re.ASCII` or an explicit `[A-Za-z0-9\-]` pattern per project constraint DIR-010/011.

**Coordination**: Python change reviewed with mypy --strict. Pydantic v2 field_validator syntax required (project uses pydantic v2 per existing `wps_manifest.py` imports).

---

### IC-03 — Tests, snapshots, docs

**Purpose**: Lock in the new behaviour with coverage, prevent stale-phrase regression, and update docs so planners understand the new terminology.

**Relevant requirements**: FR-010, FR-012, NFR-001, NFR-002, NFR-003, NFR-004

**Affected surfaces**:
- `tests/specify_cli/core/test_wps_manifest.py` — new/extended unit tests
- `tests/specify_cli/skills/test_command_renderer.py` — snapshot regeneration
- `tests/specify_cli/regression/_twelve_agent_baseline/` — refresh if renderer expects current artifacts
- Stale-phrase ripple check: `rg "Parallel Work Analysis|Work Distribution|work-package outline derived from the plan|Break a plan into work packages"` in `src/`
- Docs: update relevant sections in `docs/how-to/create-plan.md`, `docs/how-to/generate-tasks.md`, `docs/reference/missions.md`, `docs/reference/file-structure.md` (search for stale wording, update to concern vocabulary)

**Sequencing**: Depends on IC-01 and IC-02 both merged. All snapshot tests must be regenerated after IC-01 template changes land.

**Risks**: Twelve-agent regression baseline may reference "Parallel Work Analysis" in expected plan fixtures. Those must be updated (not preserved as-is) since they are test fixtures for the renderer, not historical artifacts.

## Complexity Tracking

*No charter violations requiring justification.*

## REASONS

**Approach**: The IC-## vocabulary was chosen over alternatives ("workstream", "concern-group", "theme") because "implementation concern" is unambiguous in the SDD context and does not collide with any existing spec-kitty term. The two-digit numeric suffix (`IC-01`) matches `WP##` pattern discipline and is easily validated with a regex.

**Structure**: `plan_concern_refs` lives on `WorkPackageEntry` (not a separate join table or sidecar) because the existing pydantic model is the canonical schema authority for `wps.yaml`, and optional fields with empty-list defaults are the established extension pattern in this codebase (see `owned_files`, `requirement_refs`).
