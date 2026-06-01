---
work_package_id: WP03
title: Create MissionType YAML definitions + MissionTypeRepository
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-015
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 56775025232aa879026777b03e4aee23066123df
created_at: '2026-05-30T19:34:43.824443+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3151531"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission_types/
- src/doctrine/missions/mission_type_repository.py
- tests/doctrine/missions/test_mission_type_repository.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP03 — Create MissionType YAML definitions + MissionTypeRepository

## Context

`MissionType` is a first-class governed artifact in the doctrine layer (FR-004). Each of the four built-in mission types (`software-dev`, `documentation`, `research`, `plan`) must be described in a YAML file under `src/doctrine/missions/mission_types/`. The `MissionTypeRepository` loads and indexes these files, making them available for resolution.

The `action_sequence` in each YAML must match the current hardcoded sequences from `_COMPOSED_ACTIONS_BY_MISSION` in `runtime_bridge.py` to ensure NFR-002 zero-regression.

## Objective

Author the four built-in `MissionType` YAML files, implement the `MissionType` Pydantic model, implement `MissionTypeRepository`, and cover the `template_set` dict evolution required by FR-015.

## MissionType Pydantic Model

Add `MissionType` to `src/doctrine/missions/models.py`:

```python
class MissionType(BaseModel):
    schema_version: int = 1
    id: str                                    # IDENTIFIER_PATTERN enforced
    display_name: str
    extends: str | None = None                 # base mission type ID at same layer
    action_sequence: list[str]                 # non-empty, unique step IDs
    governance_refs: list[str] = Field(default_factory=list)
    template_set: dict[str, str] | None = None # {artifact_type: template_id}

    @model_validator(mode="after")
    def _validate_action_sequence(self) -> "MissionType":
        if not self.action_sequence:
            raise ValueError("action_sequence must be non-empty")
        if len(self.action_sequence) != len(set(self.action_sequence)):
            raise ValueError("action_sequence must contain unique step IDs")
        return self
```

Also update `__all__` to include `MissionType`.

## Subtasks

### T017 — Author software-dev.yaml

Read the current hardcoded `_COMPOSED_ACTIONS_BY_MISSION` table in `src/specify_cli/next/runtime_bridge.py` to find the exact `software-dev` action sequence.

Create `src/doctrine/missions/mission_types/software-dev.yaml`:

```yaml
schema_version: 1
id: software-dev
display_name: "Software Development"
action_sequence:
  - specify
  - plan
  - tasks
  - implement
  - review
governance_refs:
  - DIR-010
  - DIR-011
template_set:
  spec: spec-template.md
  plan: plan-template.md
```

**Critical**: `action_sequence` must exactly match the current hardcoded sequence (NFR-002).

### T018 — Author documentation.yaml, research.yaml, plan.yaml

Read `_COMPOSED_ACTIONS_BY_MISSION` for the remaining three mission types, then author:

`src/doctrine/missions/mission_types/documentation.yaml`:
```yaml
schema_version: 1
id: documentation
display_name: "Documentation"
action_sequence:
  - <exact sequence from runtime_bridge.py>
```

`src/doctrine/missions/mission_types/research.yaml`:
```yaml
schema_version: 1
id: research
display_name: "Research"
action_sequence:
  - <exact sequence from runtime_bridge.py>
```

`src/doctrine/missions/mission_types/plan.yaml`:
```yaml
schema_version: 1
id: plan
display_name: "Plan"
action_sequence:
  - <exact sequence from runtime_bridge.py>
```

### T019 — Implement MissionType Pydantic model

Add the `MissionType` model to `src/doctrine/missions/models.py` as specified above.

Validation rules:
- `id` must pass `IDENTIFIER_PATTERN`
- `action_sequence` must be non-empty (raise `ValueError`)
- `action_sequence` must have unique step IDs (raise `ValueError`)
- `id` must match the filename stem (enforced by `MissionTypeRepository`, not the model itself)

### T020 — Implement MissionTypeRepository

Create `src/doctrine/missions/mission_type_repository.py`:

```python
class MissionTypeRepository:
    """Loads and indexes MissionType YAML files from a directory."""

    def __init__(self, mission_types_dir: Path) -> None: ...

    def load_all(self) -> list[MissionType]: ...

    def get(self, mission_type_id: str) -> MissionType | None: ...

    def ids(self) -> list[str]: ...
```

Implementation:
- Scan `mission_types_dir` for `*.yaml` files
- Parse each via `MissionType.model_validate(yaml.safe_load(...))`
- Validate that `mission_type.id` matches the filename stem
- Index by `id` for O(1) lookup
- `load_all()` returns sorted list by id
- `ids()` returns sorted list of all IDs

Add `__all__ = ["MissionTypeRepository"]`.

### T021 — template_set dict evolution

The existing codebase may have `template_set: software-dev-default` (string form). FR-015 evolves this to `dict[str, str]` form.

Tasks:
1. Find all existing references to `template_set` in the codebase
2. Update any callers that assume `template_set` is a `str` to handle `dict[str, str] | None`
3. Update the ATDD test suite `test_wp_prompt_governance_contract.py`: migrate any tests using the string form to the dict form
4. Note: the string form is deprecated; no migration is required for existing YAML files in this WP (the migration is handled by WP12)

### T022 — Unit tests for MissionType and MissionTypeRepository

Write `tests/doctrine/missions/test_mission_type_repository.py`:

Test cases:
- `software-dev.yaml` loads correctly and produces a `MissionType` with the expected `action_sequence`
- All four built-in YAMLs load without error
- `MissionType.action_sequence` non-empty validator fires on empty list
- `MissionType.action_sequence` uniqueness validator fires on duplicate step IDs
- `MissionType.id` rejected on non-kebab-case input
- `MissionTypeRepository.get("software-dev")` returns the correct artifact
- `MissionTypeRepository.get("nonexistent")` returns `None`
- Repository raises on YAML with `id` mismatching filename stem

## Acceptance Criteria

- [ ] `src/doctrine/missions/mission_types/` contains all four built-in YAML files
- [ ] Each YAML file `action_sequence` matches the current hardcoded sequence in `runtime_bridge.py`
- [ ] `MissionType` Pydantic model validates `action_sequence` invariants
- [ ] `MissionTypeRepository` loads and indexes all four YAMLs
- [ ] `__all__` updated in `doctrine/missions/models.py` and in the new repository module
- [ ] `tests/doctrine/missions/test_mission_type_repository.py` passes
- [ ] `mypy --strict` clean on all new/modified files

## References

- FR-004: MissionType as governed artifact
- FR-005: MissionType fields
- FR-015: template_set dict evolution
- data-model.md §"MissionType" — field specification and invariants
- research.md §"Research Task 1" — action sequence source in runtime_bridge.py

## Activity Log

- 2026-05-30T19:34:44Z – claude:sonnet:python-pedro:implementer – shell_pid=3138635 – Assigned agent via action command
- 2026-05-30T19:40:27Z – claude:sonnet:python-pedro:implementer – shell_pid=3138635 – Ready for review: MissionType model + 4 built-in YAMLs + MissionTypeRepository + 26 tests, all passing
- 2026-05-30T19:41:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=3151531 – Started review via action command
