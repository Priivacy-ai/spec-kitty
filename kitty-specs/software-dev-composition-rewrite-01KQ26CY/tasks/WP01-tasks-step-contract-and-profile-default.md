---
work_package_id: WP01
title: Tasks Step Contract + Executor Profile Default
dependencies: []
requirement_refs:
- C-001
- C-002
- C-007
- FR-002
- FR-005
- FR-006
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-25T11:39:00+00:00'
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-04-25T11:39:00Z'
  actor: claude
  action: created
authoritative_surface: src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml
execution_mode: code_change
mission_slug: software-dev-composition-rewrite-01KQ26CY
owned_files:
- src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/mission_step_contracts/test_software_dev_composition.py
priority: P1
tags: []
---

# WP01 — Tasks Step Contract + Executor Profile Default

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- During `/spec-kitty.implement` this WP runs in the lane workspace allocated by `lanes.json`; completed changes merge back to `main` unless the human redirects.

## Objective

Make the `(software-dev, tasks)` action loadable through `MissionStepContractRepository` and route-able through `StepContractExecutor.execute`. After this WP, the executor can compose all five `software-dev` actions in isolation. The runtime bridge is **not** wired here — that is WP02. This WP is therefore self-contained, fully testable through executor-level integration, and a strict prerequisite for WP02.

## Context

Read first:
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/spec.md` — full spec
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/plan.md` — locked decisions D-1..D-3
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/data-model.md` — entity shapes
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/contracts/tasks-step-contract-schema.md` — binding YAML schema
- `src/specify_cli/mission_step_contracts/executor.py` — `StepContractExecutor` (composer)
- `src/doctrine/mission_step_contracts/shipped/{specify,plan,implement,review}.step-contract.yaml` — sibling shipped contracts (templates)
- `src/doctrine/missions/software-dev/actions/tasks/index.yaml` — action governance scope
- `tests/specify_cli/mission_step_contracts/test_executor.py` — existing test patterns

Constraints active for this WP:
- **C-001**: `StepContractExecutor` stays a composer. Do NOT teach it to run shell commands or call models.
- **C-002**: Host LLM owns generation. Spec Kitty owns composition.
- **C-007**: DO NOT touch any file under `src/spec_kitty_events/` or `.kittify/charter/`. A separate agent owns that. If you find yourself reaching for those paths, stop.

## Subtasks

### T001 — Author `tasks.step-contract.yaml`

**Purpose**: Add the missing shipped contract for the `(software-dev, tasks)` action so `MissionStepContractRepository.get_by_action("software-dev", "tasks")` returns a valid `MissionStepContract`.

**File**: `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml` (new)

**Content** (verbatim — derived from `data-model.md` §Entity 1 and `contracts/tasks-step-contract-schema.md`):

```yaml
schema_version: "1.0"
id: tasks
action: tasks
mission: software-dev
steps:
  - id: bootstrap
    description: Load charter context for this action
    command: "spec-kitty charter context --action tasks --role tasks --json"
    inputs:
      - flag: --profile
        source: wp.agent_profile
        optional: true
      - flag: --tool
        source: env.agent_tool
        optional: true

  - id: outline
    description: Produce tasks.md — the work-package outline derived from the plan
    delegates_to:
      kind: tactic
      candidates:
        - problem-decomposition
        - requirements-validation-workflow

  - id: packages
    description: Generate individual tasks/WP##.md prompt files
    delegates_to:
      kind: directive
      candidates:
        - 010-specification-fidelity-requirement
        - 024-locality-of-change

  - id: finalize
    description: Validate dependencies and finalize WP metadata
    command: "spec-kitty agent mission finalize-tasks"
    delegates_to:
      kind: directive
      candidates:
        - 024-locality-of-change
```

**Validation**:
- File loads cleanly via `MissionStepContractRepository`'s YAML loader (covered by T003).
- All `delegates_to.candidates` values are present in `actions/tasks/index.yaml` (`010`, `024` directives + `problem-decomposition`, `requirements-validation-workflow` tactics — verified there).

### T002 — Extend `_ACTION_PROFILE_DEFAULTS` with the `tasks` entry

**Purpose**: Give `StepContractExecutor._resolve_profile_hint` a default profile for `(software-dev, tasks)` per locked decision D-2.

**File**: `src/specify_cli/mission_step_contracts/executor.py` (modify line 36 dict)

**Edit**: Add one entry. The dict becomes:

```python
_ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
    ("software-dev", "specify"): "researcher-robbie",
    ("software-dev", "plan"): "architect-alphonso",
    ("software-dev", "tasks"): "architect-alphonso",
    ("software-dev", "implement"): "implementer-ivan",
    ("software-dev", "review"): "reviewer-renata",
}
```

**Validation**:
- `mypy --strict` clean.
- T003 covers the runtime semantics.

### T003 — Write `test_software_dev_composition.py`

**Purpose**: Cover the new `tasks` contract and assert the full five-action composition surface works at executor level. This is the dedicated regression test required by NFR-002.

**File**: `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` (new)

**Coverage** (one test function each, kept small and focused):

1. `test_tasks_contract_loads_from_repository` — uses `MissionStepContractRepository(project_dir=Path("src/doctrine/mission_step_contracts"))` (see existing test patterns) to load the `(software-dev, tasks)` contract; asserts `id == "tasks"`, `action == "tasks"`, `mission == "software-dev"`, and `[s.id for s in steps] == ["bootstrap","outline","packages","finalize"]`.
2. `test_tasks_default_profile_is_architect_alphonso` — asserts `_ACTION_PROFILE_DEFAULTS[("software-dev","tasks")] == "architect-alphonso"`.
3. `test_all_five_software_dev_actions_have_shipped_contracts` — asserts the repository returns a non-`None` contract for each of `specify`, `plan`, `tasks`, `implement`, `review` against `software-dev`.
4. `test_executor_composes_tasks_through_invocation_executor` — uses a fake `ProfileInvocationExecutor` (mirroring the pattern in `tests/specify_cli/mission_step_contracts/test_executor.py`) to confirm `StepContractExecutor.execute` walks all `tasks` sub-steps in order and produces a non-empty `invocation_ids` chain.
5. `test_tasks_step_delegations_resolve_against_action_index` — calls `_resolve_step_delegations` (or equivalent through `execute`) and asserts at least one delegation per non-bootstrap step resolves (i.e., the candidate is in the action context's `artifact_urns`).

**Patterns to mirror**: `tests/specify_cli/mission_step_contracts/test_executor.py`. Reuse its fake invocation executor and graph fixtures rather than building from scratch.

**Validation**:
- All five tests pass.
- `mypy --strict` clean (existing repository tests' patterns are already strict-clean).

### T004 — Confirm existing `test_executor.py` and shipped-contract loaders still pass

**Purpose**: Regression guard — adding the new contract MUST NOT break the existing four contracts' loading or executor behavior.

**Command**: `cd src && pytest tests/specify_cli/mission_step_contracts/ -v`

**Validation**: All tests in `tests/specify_cli/mission_step_contracts/` (existing + new from T003) green. If any existing test fails, root-cause it before declaring T004 done.

## Definition of Done

- [ ] `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml` exists and matches the verbatim content above.
- [ ] `_ACTION_PROFILE_DEFAULTS` in `executor.py` contains the `("software-dev","tasks") → "architect-alphonso"` entry.
- [ ] `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` exists with the 5 tests listed.
- [ ] `pytest tests/specify_cli/mission_step_contracts/ -v` passes 100%.
- [ ] `mypy --strict src/specify_cli/mission_step_contracts/` passes.
- [ ] No file under `src/spec_kitty_events/` or `.kittify/charter/` was modified (verify with `git diff --name-only`).

## Reviewer Guidance

- Confirm the new YAML's `delegates_to.candidates` are all in `actions/tasks/index.yaml`. Anything not there will be reported as `unresolved_candidates` by the executor at runtime — a soft failure that should be caught here in review.
- Confirm the test file uses the existing fake-invocation-executor pattern; do not allow a real `ProfileInvocationExecutor` instantiation in unit tests.
- Confirm `mypy --strict` passes — the executor module is strict-clean today and must remain so.
- Confirm no fields in `mission.yaml` or `mission-runtime.yaml` were modified in this WP (those are WP03's surface).

## Risks

| Risk | Mitigation |
|------|------------|
| YAML schema drift vs `MissionStepContract` model | T003 first test loads the contract through the repository; any schema mismatch raises here. |
| `delegates_to` candidate not in action scope | Verify `actions/tasks/index.yaml` lists each one before submitting. |
| Profile default typo (`architect-alphonso` vs `architect-alfonso` etc.) | T003 second test pins the exact string; sibling profiles in dict provide a visual pattern. |

## Implementation command

`spec-kitty agent action implement WP01 --agent <your-agent-name>`
