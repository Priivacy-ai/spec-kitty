---
work_package_id: WP01
title: Unify MissionStep model + migrate callers
dependencies: []
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: eadb88fdd0e7eacc7804179ee1fad32112c77544
created_at: '2026-05-30T18:09:33.947981+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3108459"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/models.py
execution_mode: code_change
owned_files:
- src/doctrine/missions/models.py
- src/doctrine/mission_step_contracts/
- src/doctrine/artifact_kinds.py
- src/doctrine/service.py
- src/specify_cli/doctrine/pack_assembler.py
- src/specify_cli/doctrine/pack_validator.py
- src/specify_cli/doctrine/snapshot.py
- src/charter/schemas.py
- src/charter/mission_steps.py
- src/charter/activations.py
- src/charter/context.py
- tests/doctrine/missions/test_models.py
- tests/architectural/test_layer_rules.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP01 — Unify MissionStep model + migrate callers

## Context

The codebase currently has two Pydantic classes both named `MissionStep` in separate doctrine subpackages:

- `doctrine.missions.models.MissionStep` — schema-validation shape for `mission.yaml`
- `doctrine.mission_step_contracts.models.MissionStep` — governance-delegation shape for step contracts

These are fragmented manifestations of a single concept, split by evolutionary accident. This WP consolidates them into one canonical `MissionStep` model — an entity owned by `MissionType`, globally identified by `(mission_type_id, step_id)`. All callers of either legacy class are migrated; the `doctrine/mission_step_contracts/` subpackage is then deleted.

**Critical boundary**: `specify_cli/mission_step_contracts/` is a separate execution-layer package — do NOT delete it.

## Objective

Produce a single, unified `MissionStep` Pydantic model in `src/doctrine/missions/models.py` with the `step_type` discriminant field, migrate all callers, delete the fragmented `doctrine/mission_step_contracts/` subpackage, and extend the architectural boundary test.

## Subtasks

### T001 — Audit existing MissionStep models

Read both files:
- `src/doctrine/missions/models.py` — find the existing `MissionStep` class definition; document all fields
- `src/doctrine/mission_step_contracts/models.py` — find the duplicate `MissionStep` class; document all fields

Also read `src/doctrine/mission_step_contracts/repository.py` to understand `MissionStepContractRepository`.

Produce a field-diff table (fields unique to each, fields shared). This drives the unified model design.

### T002 — Author unified MissionStep Pydantic model

In `src/doctrine/missions/models.py`, consolidate into a single `MissionStep` class with ALL of these fields:

```python
class MissionStep(BaseModel):
    id: str                              # validated by IDENTIFIER_PATTERN
    display_name: str
    step_type: Literal["agent", "human_in_loop", "integration"]
    prompt_template: str                 # relative path to Markdown file
    agent_profile: str | None = None
    guidance: str | None = None
    delegates_to: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
```

`step_type` is the executor discriminant:
- `agent` → `Decision.kind = step` (prompt dispatched to LLM)
- `human_in_loop` → `Decision.kind = decision_required`
- `integration` → `Decision.kind = blocked` (reserved; no providers in this release)

The unified model supersedes BOTH legacy classes. All fields from both legacy models must be preserved or intentionally deprecated with rationale.

### T003 — Add IDENTIFIER_PATTERN and __all__

`MissionStep.id` must be validated by `IDENTIFIER_PATTERN` (ASCII kebab-case, per C-003). Reuse or define the pattern at the module level.

Add `__all__` declaration listing all public symbols (C-007).

### T004 — Migrate doctrine/ callers

Migrate these files to import from `doctrine.missions.models.MissionStep` instead of `doctrine.mission_step_contracts.*`:
- `src/doctrine/artifact_kinds.py` — update `mission_step_contracts` artifact kind reference
- `src/doctrine/service.py` — update DRG loading call

**Note**: `src/doctrine/drg/org_pack_loader.py` (`_ORG_DRG_CANONICAL_KINDS`) is owned by WP11 (activation-filtered DRG). Leave that file untouched here; WP11 will handle both the kind-alias migration and the activation filter in the same pass. Verify via grep that `org_pack_loader.py` still builds without import errors after this WP (it should, since the module it imports from is not removed until T007).

### T005 — Migrate specify_cli/ callers

Migrate these files to the unified model:
- `src/specify_cli/doctrine/pack_assembler.py`
- `src/specify_cli/doctrine/pack_validator.py`
- `src/specify_cli/doctrine/snapshot.py`

Do not change any functionality — only update the import paths and model references.

### T006 — Migrate charter/ callers

Migrate these charter-layer files to the unified model:
- `src/charter/schemas.py`
- `src/charter/mission_steps.py`
- `src/charter/activations.py`
- `src/charter/context.py`
- `src/charter/drg.py`

Respect C-004 boundary (kernel ← doctrine ← charter ← specify_cli):
- `charter.*` MAY import from `doctrine.*` — this is correct and expected.
- `specify_cli.*` must NOT import from `doctrine.*` directly — only through `charter.*`.
- These charter-layer callers importing `doctrine.missions.models.MissionStep` is exactly the right direction. Confirm no new `specify_cli.*` → `doctrine.*` direct imports are introduced in this or any earlier subtask.

### T007 — Delete doctrine/mission_step_contracts/ subpackage

After all callers are migrated:
1. Verify zero references remain to `doctrine.mission_step_contracts` (use `grep -r` or equivalent)
2. Delete `src/doctrine/mission_step_contracts/` directory entirely
3. **DO NOT touch** `src/specify_cli/mission_step_contracts/` — this is a separate execution-layer package

### T008 — Extend architectural boundary test

In `tests/architectural/test_layer_rules.py`, add or update the test that verifies:
- `specify_cli.*` does not import from `doctrine.*` directly (C-004)
- `doctrine.*` does not import from `charter.*` or `specify_cli.*`

The test should fail if any new cross-boundary import is introduced.

### T009 — Unit tests for unified MissionStep model

Write tests in `tests/doctrine/missions/test_models.py` covering:
- Valid `step_type` values: `agent`, `human_in_loop`, `integration`
- Invalid `step_type` raises `ValidationError`
- `id` rejected when it does not match `IDENTIFIER_PATTERN` (e.g., spaces, capitals)
- Valid `id` accepted (e.g., `specify`, `plan-tasks`, `exec-summary`)
- Default field values (`delegates_to`, `depends_on` default to empty lists)
- Optional fields can be `None`

## Acceptance Criteria

- [ ] `doctrine/mission_step_contracts/` directory is gone; `specify_cli/mission_step_contracts/` is untouched
- [ ] `grep -r "from doctrine.mission_step_contracts" src/` returns no results
- [ ] Unified `MissionStep` model in `doctrine/missions/models.py` has all required fields
- [ ] `__all__` declared in `doctrine/missions/models.py`
- [ ] All doctests + unit tests pass: `cd src && pytest tests/doctrine/missions/test_models.py`
- [ ] `tests/architectural/test_layer_rules.py` passes with the new boundary assertions
- [ ] `mypy --strict src/doctrine/missions/models.py` clean

## References

- FR-011: Unified MissionStep model specification
- spec.md §"Assumptions" — fragmentation background
- data-model.md §"MissionStep (unified)" — field specification
- `tests/architectural/test_layer_rules.py` — boundary enforcement pattern

## Activity Log

- 2026-05-30T18:09:34Z – claude:opus:python-pedro:implementer – shell_pid=2976400 – Assigned agent via action command
- 2026-05-30T19:02:01Z – claude:opus:python-pedro:implementer – shell_pid=2976400 – Ready for review: unified MissionStep model, deleted mission_step_contracts subpackage, migrated all callers
- 2026-05-30T19:03:32Z – claude:opus:python-pedro:reviewer – shell_pid=3083834 – Started review via action command
- 2026-05-30T19:11:46Z – claude:opus:python-pedro:reviewer – shell_pid=3083834 – Review passed: unified MissionStep model correctly placed in doctrine/missions/models.py with IDENTIFIER_PATTERN, Literal step_type discriminant, and __all__. Legacy doctrine/mission_step_contracts/ subpackage deleted; specify_cli/mission_step_contracts/ correctly preserved. Built-in step-contract YAMLs relocated to doctrine/missions/built_in_step_contracts/ (git rename, R100). Legacy contract types (MissionStepContract*, DelegatesTo) sensibly moved to doctrine/missions/step_contracts.py as compatibility surface. All callers migrated cleanly with import-only changes (mechanical updates to pack_validator, mission_loader/command, mission_loader/registry, mission_loader/contract_synthesis, next/runtime_bridge, doctrine/service, charter/mission_steps). Architectural test extended with TestUnifiedMissionStepBoundary covering legacy-subpackage-gone + new-location anchors. test_no_dead_symbols allowlist updated for WP-in-flight surface. 42 targeted tests pass; 2773 broader doctrine+charter+missions tests pass. One unrelated failing test (specify_cli.scripts.tasks.acceptance_support symbols) is preexisting on the base branch (introduced by upstream commit 4de2a5678), not caused by WP01.
- 2026-05-30T19:12:15Z – claude:opus:python-pedro:reviewer – shell_pid=3083834 – Returning for second review pass with reviewer-renata; stale documentation paths (YAML comments + .md guidelines still referencing src/doctrine/mission_step_contracts/built-in/) are a blocking finding, not a nit
- 2026-05-30T19:12:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3096277 – Started review via action command
- 2026-05-30T19:15:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3096277 – Moved to planned
- 2026-05-30T19:16:01Z – claude:sonnet:python-pedro:implementer – shell_pid=3102853 – Started implementation via action command
- 2026-05-30T19:18:35Z – claude:sonnet:python-pedro:implementer – shell_pid=3102853 – Cycle 2 fix: updated 7 stale mission_step_contracts path references to built_in_step_contracts
- 2026-05-30T19:18:53Z – claude:opus:reviewer-renata:reviewer – shell_pid=3108459 – Started review via action command
