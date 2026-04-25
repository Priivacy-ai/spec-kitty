---
work_package_id: WP03
title: Contract Synthesis + Runtime Registry Shadow
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - Loader core
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "36738"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/mission_loader/contract_synthesis.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_loader/contract_synthesis.py
- src/specify_cli/mission_loader/registry.py
- tests/unit/mission_loader/test_contract_synthesis.py
- tests/unit/mission_loader/test_registry.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 – Contract Synthesis + Runtime Registry Shadow

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Synthesize a `MissionStepContract` per composed step in a custom mission template and provide a per-process registry shadow so `StepContractExecutor` can resolve those contracts alongside on-disk records. Lifetime is scoped to the run via a context manager.

Success criteria:
1. `synthesize_contracts(template) -> list[MissionStepContract]` produces exactly one contract per composed step (skipping decision-required gates and contract-ref-bound steps).
2. `RuntimeContractRegistry` provides `register(contracts) / lookup(id) -> MissionStepContract | None` and a `with registered_runtime_contracts(template):` context manager.
3. Registry shadow takes precedence over on-disk repository inside the `with` block; on exit, shadowed lookups disappear.
4. ≥ 90% coverage on the new modules; `mypy --strict` clean; existing test suites stay green.

## Context & Constraints

- WP03 does **not** modify dispatch (`StepContractExecutor` or `runtime_bridge`) — that's WP04.
- WP03 does **not** modify the on-disk `MissionStepContractRepository` content. The registry is in-memory only.
- See [research.md](../research.md) §R-004 for the auto-synthesis decision.
- See [data-model.md](../data-model.md) §"Synthesized contract record" for the synthesized shape.

## Subtasks & Detailed Guidance

### Subtask T013 — Create `contract_synthesis.py`

- **Purpose**: Convert a custom `MissionTemplate` into the contract records the executor expects.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/contract_synthesis.py`.
  2. Inspect `src/doctrine/mission_step_contracts/models.py` for `MissionStepContract`'s exact constructor signature (`id`, `mission`, `action`, `steps`, etc.). Match it precisely; do NOT copy stale shapes from the spec.
  3. Implement:
     ```python
     def synthesize_contracts(template: MissionTemplate) -> list[MissionStepContract]:
         """Build one MissionStepContract per composed step in `template`.

         Skips:
         - Decision-required gates (step.requires_inputs is non-empty).
         - Steps that already point to an existing contract (step.contract_ref is not None).
         - The retrospective marker step (step.id == 'retrospective').

         Returns: list[MissionStepContract] with id of the form
         "custom:<mission-key>:<step.id>".
         """
     ```
  4. For each in-scope step, build a `MissionStepContract` with:
     - `id = f"custom:{template.mission.key}:{step.id}"`
     - `mission = template.mission.key`
     - `action = step.id`
     - One inner `MissionStep` whose `id = f"{step.id}.execute"` and `title = step.title`. No `delegates_to`. No `drg_context`. No `raci`.
  5. Return list ordered same as `template.steps`.
- **Files**: `src/specify_cli/mission_loader/contract_synthesis.py`.
- **Notes**: If `MissionStepContract` requires fields not listed above (e.g., `version`, `description`), use sensible defaults (`version="1.0.0"`, `description=step.description`).

### Subtask T014 — Create `registry.py` (`RuntimeContractRegistry`)

- **Purpose**: Provide a thread-safe per-process shadow that overlays the on-disk repository for the lifetime of a run.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/registry.py`.
  2. Implement:
     ```python
     class RuntimeContractRegistry:
         """In-memory overlay over MissionStepContractRepository.

         Lifetime: bounded by `with registered_runtime_contracts(template):`.
         Lookups inside the block: shadow first, repository second.
         Lookups outside the block: repository only.
         """

         _instance: ClassVar[RuntimeContractRegistry | None] = None

         def __init__(self) -> None:
             self._contracts: dict[str, MissionStepContract] = {}

         def register(self, contracts: Iterable[MissionStepContract]) -> None: ...
         def lookup(self, contract_id: str) -> MissionStepContract | None: ...
         def clear(self) -> None: ...
     ```
  3. Implement `registered_runtime_contracts(template: MissionTemplate)` as a context manager that:
     - On enter: synthesizes contracts via `synthesize_contracts(template)`, registers them in the singleton registry.
     - On exit: clears the registered subset (does NOT clear pre-existing shadows from outer contexts; use a stack-of-snapshots model).
  4. Provide a module-level accessor `get_runtime_contract_registry()` that returns the singleton and is import-stable.
- **Files**: `src/specify_cli/mission_loader/registry.py`.
- **Notes**: Use `contextlib.contextmanager` for the context manager. Threading is single-threaded for the CLI; do not over-engineer. Document the assumption in the docstring.

### Subtask T015 — Repository façade hook

- **Purpose**: Provide the integration point that WP04 will use without forcing WP04 to know about `mission_loader.registry`.
- **Steps**:
  1. Add a free function `lookup_contract(contract_id: str, repository: MissionStepContractRepository) -> MissionStepContract | None` to `registry.py`:
     ```python
     def lookup_contract(
         contract_id: str,
         repository: MissionStepContractRepository,
     ) -> MissionStepContract | None:
         """Resolve `contract_id` from the runtime registry first, then repository."""
         registry = get_runtime_contract_registry()
         hit = registry.lookup(contract_id)
         if hit is not None:
             return hit
         return repository.get(contract_id)
     ```
  2. Verify `MissionStepContractRepository.get(...)` returns `MissionStepContract | None` (not raise). If it raises on miss, wrap in `try/except` and return None.
- **Files**: `src/specify_cli/mission_loader/registry.py`.
- **Notes**: WP04 will route `StepContractExecutor` lookups through this façade.

### Subtask T016 — Unit tests for `synthesize_contracts`

- **Purpose**: Lock the synthesis output shape (FR-008 alignment).
- **Steps**:
  1. Create `tests/unit/mission_loader/test_contract_synthesis.py`.
  2. Cases:
     - `test_one_contract_per_composed_step` — 4-step template (3 composed + 1 retrospective) → 3 contracts.
     - `test_skips_decision_required_steps` — step with `requires_inputs=["x"]` → not in output.
     - `test_skips_contract_ref_steps` — step with `contract_ref="abc"` → not in output.
     - `test_id_shape` — each output's `id == f"custom:{mission_key}:{step_id}"`.
     - `test_mission_and_action_set` — `contract.mission == template.mission.key`, `contract.action == step.id`.
     - `test_empty_template_returns_empty` — no steps → empty list.
- **Files**: `tests/unit/mission_loader/test_contract_synthesis.py`.
- **Parallel?**: [P].

### Subtask T017 — Unit tests for `RuntimeContractRegistry`

- **Purpose**: Lock the precedence + lifetime semantics.
- **Steps**:
  1. Create `tests/unit/mission_loader/test_registry.py`.
  2. Cases:
     - `test_lookup_inside_with_block_returns_shadow` — register a contract, look it up by id → returns shadow.
     - `test_lookup_outside_with_block_falls_through_to_repository` — exit context, look up same id → repository (mocked) is consulted.
     - `test_lookup_unregistered_id_falls_through` — id not in shadow → repository consulted (returning None or a stub).
     - `test_nested_with_blocks` — outer registers A, inner registers B; inside inner both visible; on inner exit only B disappears.
     - `test_clear_resets_registry` — explicit `clear()` empties the shadow.
- **Files**: `tests/unit/mission_loader/test_registry.py`.
- **Parallel?**: [P].

## Test Strategy (charter required)

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/unit/mission_loader/test_contract_synthesis.py tests/unit/mission_loader/test_registry.py -q
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/mission_loader/contract_synthesis.py src/specify_cli/mission_loader/registry.py
UV_PYTHON=3.13.9 uv run --no-sync ruff check src/specify_cli/mission_loader/contract_synthesis.py src/specify_cli/mission_loader/registry.py tests/unit/mission_loader/test_contract_synthesis.py tests/unit/mission_loader/test_registry.py
```

## Risks & Mitigations

- **Risk**: `MissionStepContract` constructor requires fields not anticipated.
  - **Mitigation**: Read `src/doctrine/mission_step_contracts/models.py` and `src/doctrine/templates/mission-step-contract*.yaml` (if any) before coding. Match the real shape.
- **Risk**: Singleton registry state leaks across tests.
  - **Mitigation**: Provide `clear()`; pytest fixtures call it in `autouse=True` teardown for the test module.
- **Risk**: Existing `StepContractExecutor` calls `repository.get()` directly, bypassing the façade.
  - **Mitigation**: WP04 owns the wiring change. WP03 only provides the façade; WP04 uses it. Document this boundary in the registry's module docstring.

## Review Guidance

- Reviewer reads `src/doctrine/mission_step_contracts/models.py` before reviewing the synthesized shape; they may ask the implementer to add fields if `MissionStepContract` requires them.
- Reviewer confirms no on-disk file is written by either module.
- Reviewer confirms tests pass coverage gate locally.

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T18:29:48Z – claude:sonnet:implementer-ivan:implementer – shell_pid=35895 – Started implementation via action command
- 2026-04-25T18:36:13Z – claude:sonnet:implementer-ivan:implementer – shell_pid=35895 – Contract synthesis + registry shadow done; coverage >= 90%
- 2026-04-25T18:36:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=36738 – Started review via action command
- 2026-04-25T18:39:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=36738 – Review passed: synthesis + registry + facade per spec; uses real MissionStepContract shape (id/schema_version/action/mission/steps + inner MissionStep id/description); 100% coverage on WP03 modules, 96% package; nested-with stack-of-snapshots verified; 13 cases covered; mypy --strict clean on WP03 files (jsonschema errors pre-existing in src/doctrine/.../validation.py); regression suite green (98/98).
