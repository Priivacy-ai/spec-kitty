---
work_package_id: WP05
title: 'Wave 3: schema field additions for overrides/enhances (FR-010, FR-011)'
dependencies: []
requirement_refs:
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: f3cfe86a8a0304f505f5a06f6380451c747b05cf
created_at: '2026-05-24T08:34:34.184659+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
- T033
- T034
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "968553"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/doctrine/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- architecture/3.x/adr/2026-05-DD-2-pack-augmentation-vocabulary.md
- .kittify/glossaries/spec_kitty_core.yaml
- src/doctrine/tactics/models.py
- src/doctrine/styleguides/models.py
- src/doctrine/paradigms/models.py
- src/doctrine/procedures/models.py
- src/doctrine/agent_profiles/profile.py
- src/doctrine/schemas/tactic.schema.yaml
- src/doctrine/schemas/styleguide.schema.yaml
- src/doctrine/schemas/paradigm.schema.yaml
- src/doctrine/schemas/procedure.schema.yaml
- src/doctrine/schemas/agent-profile.schema.yaml
- tests/doctrine/test_tactic_augmentation_fields.py
- tests/doctrine/test_styleguide_augmentation_fields.py
- tests/doctrine/test_paradigm_augmentation_fields.py
- tests/doctrine/test_procedure_augmentation_fields.py
- tests/doctrine/test_agent_profile_augmentation_fields.py
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pedro's Pydantic + JSON Schema + cross-field-validator focus is the strict overmatch for the 5 symmetric model+schema changes. (The glossary subtask T029 is curator-adjacent but a single artifact among 8; Pedro authors it with curator-style discipline.)

## Objective

Add `overrides: <id>` and `enhances: <id>` as first-class optional declarative fields on five doctrine artifact kinds (Tactic, Styleguide, Paradigm, Procedure, AgentProfile), with a mutually-exclusive cross-field validator. Land the ADR for the vocabulary decision and the glossary entries that bind `enhances` (canonical) / `augments` (synonym to-avoid) per DIR-032.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `kitty-specs/.../spec.md` — FR-010, FR-011
- `kitty-specs/.../data-model.md` — §1 (full model spec including validator)
- `kitty-specs/.../research.md` — R-1 (field name decision), R-6 (mutual exclusion), R-8 (fixture compatibility)
- `kitty-specs/.../contracts/pack-validator-advisory.md` — downstream consumer of these fields (WP06)
- Existing models: `src/doctrine/tactics/models.py`, `styleguides/models.py`, `paradigms/models.py`, `procedures/models.py`, `agent_profiles/profile.py`
- Existing schemas: `src/doctrine/schemas/tactic.schema.yaml` + four siblings

## Subtask details

### T027 — ADR-2 (`2026-05-DD-2-pack-augmentation-vocabulary.md`)

**Files**: `architecture/3.x/adr/2026-05-DD-2-pack-augmentation-vocabulary.md` (NEW)

Outline per plan.md Cross-cutting table row:
- **Problem**: Issue #1291 — `extra="forbid"` blocks declarative augmentation intent; validator wording does not match the field-merge semantics ratified in `2026-05-16-1`.
- **Decision**: Add `overrides`/`enhances` declarative fields on five artifact kinds; mutually-exclusive validator; auto-emit DRG edges (WP06).
- **Alternatives considered**: Drop `extra="forbid"` (rejected — loses validation); magic precedence (rejected — implicit).
- **Consequences**: Cross-references `2026-05-16-1`. Enables WP06 advisory reconciliation.

### T028 — DIR-012 assign #1291 to HiC

```bash
unset GITHUB_TOKEN
gh issue edit 1291 --add-assignee @stijn-dejongh --repo Priivacy-ai/spec-kitty
```

### T029 — Glossary entries (DIR-032)

**Files**: `.kittify/glossaries/spec_kitty_core.yaml` (or the appropriate scope file under `.kittify/glossaries/`)

Add two new terms following the existing entry shape:
```yaml
- term: enhances
  definition: >
    Declarative field on a doctrine pack artifact (tactic, styleguide, paradigm,
    procedure, agent profile) that asserts the artifact augments a built-in
    artifact with the same ID via field-merge. Suppresses the same-ID-collision
    advisory and auto-emits an `ENHANCES` DRG edge.
  synonyms_to_avoid: [augments, extends]
  introduced_in_mission: charter-ux-and-org-pack-vocabulary-01KSAF14
- term: overrides
  definition: >
    Declarative field on a doctrine pack artifact that asserts the artifact
    fully replaces a built-in artifact with the same ID. Suppresses the same-ID
    advisory and auto-emits an `OVERRIDES` DRG edge.
  synonyms_to_avoid: [replaces, supersedes]
  introduced_in_mission: charter-ux-and-org-pack-vocabulary-01KSAF14
```

### T030 [P] — `Tactic` model + schema YAML

**Files**: `src/doctrine/tactics/models.py`, `src/doctrine/schemas/tactic.schema.yaml`, NEW `tests/doctrine/test_tactic_augmentation_fields.py`

Per data-model §1.1, extend `Tactic`:
```python
from typing import Self
from pydantic import model_validator

class Tactic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$", alias="schema_version")
    name: str
    overrides: str | None = Field(default=None, description="ID of a built-in tactic this artifact replaces in full.")
    enhances: str | None = Field(default=None, description="ID of a built-in tactic this artifact augments via field-merge.")
    # ... existing fields ...

    @model_validator(mode="after")
    def _augmentation_intent_is_exclusive(self) -> Self:
        if self.overrides is not None and self.enhances is not None:
            raise ValueError(
                f"overrides and enhances are mutually exclusive on tactic {self.id}"
            )
        return self
```

Schema YAML (`tactic.schema.yaml`) under `properties`:
```yaml
  overrides:
    type: string
    pattern: ^[a-z][a-z0-9-]*$
    description: ID of a built-in tactic this artifact replaces in full.
  enhances:
    type: string
    pattern: ^[a-z][a-z0-9-]*$
    description: ID of a built-in tactic this artifact augments via field-merge.
```

Tests:
1. Tactic with neither field loads (backward compatibility — NFR-004).
2. Tactic with `enhances: foo` loads.
3. Tactic with `overrides: foo` loads.
4. Tactic with both raises `ValidationError` mentioning "mutually exclusive".

### T031 [P] — `Styleguide` model + schema YAML

**Files**: `src/doctrine/styleguides/models.py`, `src/doctrine/schemas/styleguide.schema.yaml`, NEW `tests/doctrine/test_styleguide_augmentation_fields.py`

Apply the same pattern as T030. Mirror the regex pattern from the existing styleguide ID validation. Mirror the four-case test set.

### T032 [P] — `Paradigm` model + schema YAML

**Files**: `src/doctrine/paradigms/models.py`, `src/doctrine/schemas/paradigm.schema.yaml`, NEW `tests/doctrine/test_paradigm_augmentation_fields.py`

Same pattern as T030. Same four-case test set.

### T033 [P] — `Procedure` model + schema YAML

**Files**: `src/doctrine/procedures/models.py`, `src/doctrine/schemas/procedure.schema.yaml`, NEW `tests/doctrine/test_procedure_augmentation_fields.py`

Same pattern. Same four-case test set.

### T034 [P] — `AgentProfile` model + schema YAML

**Files**: `src/doctrine/agent_profiles/profile.py`, `src/doctrine/schemas/agent-profile.schema.yaml`, NEW `tests/doctrine/test_agent_profile_augmentation_fields.py`

Same pattern. AgentProfile may use `profile-id` as the identifier; use the same regex it uses today. Same four-case test set.

## Definition of Done

- [ ] ADR-2 file exists and cross-references `2026-05-16-1`.
- [ ] Issue #1291 assigned to HiC.
- [ ] Glossary has `enhances` and `overrides` entries with `synonyms_to_avoid`.
- [ ] All 5 Pydantic models accept the two new optional fields.
- [ ] All 5 models reject both-set with a named `ValidationError`.
- [ ] All 5 JSON Schemas list the two new properties.
- [ ] All 5 four-case test files pass.
- [ ] Existing fixture YAMLs that omit both fields continue to load (NFR-004 — verified by running the full pytest suite).
- [ ] `mypy --strict` and `ruff check` pass.

## Risks

- **Cross-cutting fixture load**: many fixture YAMLs across the test suite construct these models. NFR-004 demands zero failures. If a fixture fails, investigate whether it relies on `extra="forbid"` rejecting unrelated typos (unlikely but possible).
- **AgentProfile regex difference**: the AgentProfile ID pattern differs from tactic IDs (`profile-id` vs `id`). Verify the schema YAML's regex matches the model.

## Reviewer guidance

1. Verify the validator error message includes the artifact ID — operators need that for debugging pack YAML.
2. Confirm the field descriptions match `data-model.md §1` wording (so dashboards and IDE tooltips stay consistent).
3. Spot-check one parallel YAML fixture per artifact kind to confirm it still loads.

## Activity Log

- 2026-05-24T08:34:34Z – claude:opus-4-7:python-pedro:implementer – shell_pid=929128 – Assigned agent via action command
- 2026-05-24T08:43:14Z – claude:opus-4-7:python-pedro:implementer – shell_pid=929128 – Ready for review: 5 models + 5 schemas + glossary + ADR-2
- 2026-05-24T08:43:45Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=968553 – Started review via action command
- 2026-05-24T08:46:50Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=968553 – Review passed: ADR-2 landed (cross-refs 2026-05-16-1 x5), #1291 assigned to stijn-dejongh, glossary terms present with synonyms_to_avoid, 5 models + 5 schemas + 20/20 tests, NFR-004 verified (1679 doctrine tests pass), 4 pre-existing failures (glossary anchors, five-paradigm tactic) confirmed out of scope
- 2026-05-24T11:46:52Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=968553 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
