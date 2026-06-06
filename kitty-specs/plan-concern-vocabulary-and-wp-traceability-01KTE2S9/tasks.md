# Tasks: Plan Concern Vocabulary and WP Traceability

**Mission**: plan-concern-vocabulary-and-wp-traceability-01KTE2S9
**Branch**: `kitty/mission-plan-concern-vocabulary-and-wp-traceability-01KTE2S9`
**Merge target**: `main`

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Replace `## Parallel Work Analysis` section with `## Implementation Concern Map` + IC-## stubs in `plan-template.md` | WP01 | |
| T002 | Update `plan/prompt.md` stop-point and report language to reference concerns and explain tasks translates concerns → WPs | WP01 | [P] |
| T003 | Update `tasks/prompt.md` description header from "Break a plan into work packages" to concern-translation wording | WP01 | [P] |
| T004 | Update `tasks.step-contract.yaml` outline step description — remove "work-package outline derived from the plan" | WP01 | [P] |
| T005 | Add `plan_concern_refs: list[str]` to `WorkPackageEntry` with `IC-\d{2}` field validator | WP02 | |
| T006 | Add `cross_cutting: bool = False` to `WorkPackageEntry` | WP02 | [P] |
| T007 | Extend `generate_tasks_md_from_manifest()` to render "Plan concerns: IC-01, IC-03" per WP when non-empty | WP02 | |
| T008 | Update `tasks-outline/prompt.md` to require IC-## citation in `plan_concern_refs` per WP | WP02 | [P] |
| T009 | Update `tasks-packages/prompt.md` to carry `plan_concern_refs` from `wps.yaml` into WP frontmatter | WP02 | [P] |
| T010 | Write unit tests for `plan_concern_refs` — valid IC-## values, invalid values, empty default, backwards-compat | WP03 | |
| T011 | Write unit tests for `cross_cutting` field and `generate_tasks_md_from_manifest()` rendering | WP03 | [P] |
| T012 | Run stale-phrase ripple check; fix any remaining hits in `src/doctrine/missions/` | WP03 | |
| T013 | Regenerate command-renderer snapshots (`PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/skills/`) | WP03 | |
| T014 | Update user docs: `create-plan.md`, `generate-tasks.md`, `missions.md`, `file-structure.md` | WP03 | [P] |

---

## WP01 — Plan Template Language

**Goal**: Eliminate pseudo-WP vocabulary from all plan-phase templates and prompts so planners cannot accidentally produce WP-like slices at the plan stage.

**Priority**: High — prerequisite for WP02 (schema changes must be coherent with updated prompt wording)

**Subtask count**: 4 | **Estimated prompt size**: ~240 lines

**Included subtasks**:
- [x] T001 Replace Parallel Work Analysis section in plan-template.md with Implementation Concern Map + IC-## stubs (WP01)
- [x] T002 Update plan/prompt.md stop-point language for concern vocabulary (WP01)
- [x] T003 Update tasks/prompt.md description header (WP01)
- [x] T004 Update tasks.step-contract.yaml outline step description (WP01)

**Parallelization**: T002, T003, T004 are independent files and can be edited in parallel after T001 establishes the IC-## vocabulary in the template.

**Dependencies**: None

**Success criteria**: `rg "Parallel Work Analysis|Work Distribution|work-package outline derived from the plan|Break a plan into work packages"` returns zero hits in `src/doctrine/missions/`.

**Prompt**: [WP01-plan-template-language.md](tasks/WP01-plan-template-language.md)

---

## WP02 — WP Manifest Schema and Rendering

**Goal**: Give the WP manifest a machine-readable place to record plan concern refs, and surface that in generated tasks.md and WP prompt files.

**Priority**: High — depends on WP01 (prompts must use IC-## vocabulary before tasks-outline/tasks-packages are updated)

**Subtask count**: 5 | **Estimated prompt size**: ~310 lines

**Included subtasks**:
- [ ] T005 Add plan_concern_refs field to WorkPackageEntry with IC-## validator (WP02)
- [ ] T006 Add cross_cutting bool field to WorkPackageEntry (WP02)
- [ ] T007 Extend generate_tasks_md_from_manifest() to render concern refs (WP02)
- [ ] T008 Update tasks-outline/prompt.md to require IC citation (WP02)
- [ ] T009 Update tasks-packages/prompt.md to carry plan_concern_refs (WP02)

**Parallelization**: T005 and T006 can be added to the model simultaneously. T008 and T009 are independent prompt files. T007 depends on T005.

**Dependencies**: WP01

**Success criteria**: A `wps.yaml` with `plan_concern_refs: [IC-01]` parses without error; `generate_tasks_md_from_manifest()` renders "Plan concerns: IC-01" in output; a `wps.yaml` without `plan_concern_refs` also parses without error.

**Prompt**: [WP02-wp-manifest-schema-and-rendering.md](tasks/WP02-wp-manifest-schema-and-rendering.md)

---

## WP03 — Tests, Snapshots, and Docs

**Goal**: Lock in the new behaviour with test coverage, prevent stale-phrase regression, and update user-facing docs.

**Priority**: High — completes the mission; cannot be parallelized with WP02

**Subtask count**: 5 | **Estimated prompt size**: ~290 lines

**Included subtasks**:
- [ ] T010 Write unit tests for plan_concern_refs field (WP03)
- [ ] T011 Write unit tests for cross_cutting field and rendering (WP03)
- [ ] T012 Run stale-phrase ripple check and fix remaining hits (WP03)
- [ ] T013 Regenerate command-renderer snapshots (WP03)
- [ ] T014 Update user docs (WP03)

**Parallelization**: T010 and T011 are independent test cases. T012, T013, T014 are independent after WP01+WP02 land.

**Dependencies**: WP01, WP02

**Success criteria**: `pytest tests/` passes with ≥90% branch coverage on new `wps_manifest.py` paths; `mypy --strict src/specify_cli/core/wps_manifest.py` passes; stale-phrase ripple check returns 0 hits; snapshot tests pass.

**Prompt**: [WP03-tests-snapshots-and-docs.md](tasks/WP03-tests-snapshots-and-docs.md)
