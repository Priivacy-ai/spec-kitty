---
work_package_id: WP01
title: Schema Extensions (DoctrineSelectionConfig + OrgCharterPolicy + ActivationEntry)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-006
- FR-008
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-mediated-doctrine-selection-01KRTZCA
base_commit: a0f209d33b59f5728d248b7c14e63445dfcb6618
created_at: '2026-05-17T16:23:49.744822+00:00'
subtasks:
- T001
- T003
- T004
- T005
- T008
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "1612262"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/schemas.py
execution_mode: code_change
owned_files:
- src/charter/schemas.py
- src/charter/activations.py
- tests/charter/test_schemas_selection.py
- tests/charter/test_activations.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope your governance context to Python implementation before proceeding.

---

## Objective

Extend the selection schemas so every artifact kind exposed by `DoctrineService` is addressable from both the project charter (`selected_<kind>`) and an org pack (`required_<kind>`). Introduce the new `charter.activations` module carrying `ActivationEntry`, the closed vocabularies, and the resolver. Preserve NFR-005 byte-stability by extending `_OPTIONAL_EMPTY_OMIT_KEYS`.

This WP unblocks all downstream selection / activation work. It is purely additive; nothing existing breaks.

---

## Context

Today's schemas (`src/charter/schemas.py:DoctrineSelectionConfig` and `src/specify_cli/doctrine/org_charter.py:OrgCharterPolicy`) cover only 3 of the 8 artifact kinds that `doctrine.service.DoctrineService` exposes as properties. The architectural test `test_artifact_selection_completeness.py` was added at commit `bd95f1f5` to pin the parity rule; it fails today on 5 missing `selected_<kind>` fields and 7 missing `required_<kind>` fields.

The activation registry (`charter.activations`) does not yet exist. `test_activation_registry_schema.py` was added at `bd95f1f5` and fails today on `ImportError`.

See:
- [plan.md §2.1, §2.2, §2.5](../plan.md)
- [data-model.md §1, §2, §3, §5](../data-model.md)
- [contracts/selection-schema.md](../contracts/selection-schema.md)
- [contracts/activation-registry.md](../contracts/activation-registry.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`; check `lanes.json`
- **Implement command**: `spec-kitty agent action implement WP01 --agent claude`

---

## Subtasks

### T001 — Extend `DoctrineSelectionConfig`

**File**: `src/charter/schemas.py`

Add five new fields to `DoctrineSelectionConfig`:

```python
selected_styleguides: list[str] = Field(default_factory=list)
selected_toolguides: list[str] = Field(default_factory=list)
selected_procedures: list[str] = Field(default_factory=list)
selected_agent_profiles: list[str] = Field(default_factory=list)
selected_mission_step_contracts: list[str] = Field(default_factory=list)
```

Match field naming verbatim to the corresponding `DoctrineService` property name.

### T002 — Extend `OrgCharterPolicy`

**File**: `src/specify_cli/doctrine/org_charter.py`

Add seven new `required_<kind>` fields (parity with `selected_<kind>`) plus the new `activations` field:

```python
required_paradigms: list[str] = Field(default_factory=list)
required_tactics: list[str] = Field(default_factory=list)
required_styleguides: list[str] = Field(default_factory=list)
required_toolguides: list[str] = Field(default_factory=list)
required_procedures: list[str] = Field(default_factory=list)
required_agent_profiles: list[str] = Field(default_factory=list)
required_mission_step_contracts: list[str] = Field(default_factory=list)
activations: list["ActivationEntry"] = Field(default_factory=list)
```

Import `ActivationEntry` from `charter.activations` (allowed — `specify_cli` may import from `charter`). Keep `extra="forbid"` to catch typos.

### T003 — Create `src/charter/activations.py`

NEW module:

```python
"""Charter-level activation registry (context-scoped mode)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = [
    "ActivationEntry",
    "ALLOWED_MISSION_TYPES",
    "ALLOWED_ACTIONS",
    "resolve_for_context",
]

ALLOWED_MISSION_TYPES: frozenset[str] = frozenset(
    {"software-dev", "documentation", "research", "plan", "any", "generic"}
)
ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "specify", "plan", "tasks", "implement", "review", "merge", "accept",
        "charter.interview", "charter.generate", "charter.context",
    }
)
_ALLOWED_KINDS: frozenset[str] = frozenset(
    {
        "directives", "tactics", "styleguides", "toolguides",
        "paradigms", "procedures", "agent_profiles", "mission_step_contracts",
    }
)


class ActivationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activation_context: dict[str, str]
    doctrine_pack_id: str
    artifact_id: str
    artifact_kind: str | None = None

    @field_validator("activation_context")
    @classmethod
    def _validate_context(cls, value: dict[str, str]) -> dict[str, str]:
        mt = value.get("mission_type")
        if mt is not None and mt not in ALLOWED_MISSION_TYPES:
            raise ValueError(
                f"activation_context.mission_type={mt!r} not in "
                f"ALLOWED_MISSION_TYPES={sorted(ALLOWED_MISSION_TYPES)}"
            )
        action = value.get("action")
        if action is not None and action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"activation_context.action={action!r} not in "
                f"ALLOWED_ACTIONS={sorted(ALLOWED_ACTIONS)}"
            )
        return value

    @field_validator("artifact_kind")
    @classmethod
    def _validate_kind(cls, value: str | None) -> str | None:
        if value is not None and value not in _ALLOWED_KINDS:
            raise ValueError(
                f"artifact_kind={value!r} not in {sorted(_ALLOWED_KINDS)}"
            )
        return value


def resolve_for_context(
    entries: list[ActivationEntry],
    *,
    mission_type: str,
    action: str,
) -> list[ActivationEntry]:
    """Return entries whose activation_context matches (mission_type, action).

    Wildcards: ``generic`` and ``any`` in either slot match anything; absence
    of the key is equivalent to wildcard.
    """
    def matches_slot(declared: str | None, current: str) -> bool:
        return declared is None or declared in ("generic", "any") or declared == current

    return [
        e
        for e in entries
        if matches_slot(e.activation_context.get("mission_type"), mission_type)
        and matches_slot(e.activation_context.get("action"), action)
    ]
```

### T004 — Extend `_OPTIONAL_EMPTY_OMIT_KEYS`

**File**: `src/charter/schemas.py`

Add the 5 new keys to the existing allow-list so empty `governance.yaml` outputs stay byte-identical pre-/post-mission (NFR-005):

```python
_OPTIONAL_EMPTY_OMIT_KEYS: frozenset[str] = frozenset({
    "references",
    "authority_paths",
    "selected_styleguides",
    "selected_toolguides",
    "selected_procedures",
    "selected_agent_profiles",
    "selected_mission_step_contracts",
})
```

### T005 — Unit tests

**Files**: `tests/charter/test_schemas_selection.py`, `tests/charter/test_activations.py`, `tests/specify_cli/doctrine/test_org_charter_schema.py`

Coverage:

- `DoctrineSelectionConfig()` with all defaults parses unchanged; `model_dump()` omits the 5 new empty fields via `_prune_optional_empties`.
- `DoctrineSelectionConfig(selected_styleguides=["caveman-comments"])` round-trips through `emit_yaml` and back.
- `OrgCharterPolicy()` default round-trips byte-identical to today's empty policy.
- `ActivationEntry(activation_context={"action": "implement"}, doctrine_pack_id="project", artifact_id="x")` constructs cleanly; absent slots treated as wildcards.
- Invalid mission_type / action raises `ValidationError` (matches the ATDD test in `test_activation_registry_schema.py`).
- `resolve_for_context([entry], mission_type="software-dev", action="implement")` returns the entry when matching; empty when not.

---

## Definition of Done

The following tests turn green (or stay green) with this WP:

- ✅ `tests/architectural/test_artifact_selection_completeness.py::test_every_doctrine_kind_has_a_charter_selected_field`
- ✅ `tests/architectural/test_artifact_selection_completeness.py::test_every_doctrine_kind_has_an_org_required_field`
- ✅ `tests/architectural/test_artifact_selection_completeness.py::test_selection_and_required_field_names_are_consistent`
- ✅ `tests/architectural/test_activation_registry_schema.py::test_activation_entry_schema_exists_and_carries_required_fields`
- ✅ `tests/architectural/test_activation_registry_schema.py::test_activation_context_mission_type_vocabulary_is_closed`
- ✅ `tests/architectural/test_activation_registry_schema.py::test_activation_context_action_vocabulary_is_closed`
- ✅ `tests/architectural/test_activation_registry_schema.py::test_activation_entry_validates_membership_of_vocabulary`
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 unchanged
- ✅ `tests/architectural/test_layer_rules.py` — 8/8

---

## Risks

| Risk | Mitigation |
|------|------------|
| `OrgCharterPolicy` importing `ActivationEntry` from `charter.activations` introduces a layering question | `specify_cli` is allowed to import from `charter` (audit + ADR confirm). Verified by `test_layer_rules.py`. |
| Adding fields silently breaks an existing fixture | `_OPTIONAL_EMPTY_OMIT_KEYS` extension preserves byte-stability; the 23-test ATDD suite is the regression gate. |
| Pydantic field_validator runs before model_config and fails on `extra="forbid"` extras | Validator order is field-level → model-level; `extra="forbid"` applies before validators. Test with explicit invalid-key fixture. |

---

## Reviewer Guidance

- Verify the 5 new `selected_<kind>` field names match `DoctrineService` properties exactly (no `selected_styleguide` singular slip).
- Verify `_OPTIONAL_EMPTY_OMIT_KEYS` carries all 5 new keys so byte-stability holds.
- Verify the activation Pydantic validators reject `mission_type="dev"` and `action="compile"` (the canonical ATDD assertions).
- Verify no `from doctrine.*` import lands in `charter.activations` (it doesn't need any).

## Activity Log

- 2026-05-17T16:23:50Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1612262 – Assigned agent via action command
- 2026-05-17T16:34:01Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1612262 – Schema extensions land: 5 selected_<kind> parity fields on DoctrineSelectionConfig, ActivationEntry + ALLOWED_MISSION_TYPES/ALLOWED_ACTIONS/REGISTERED_TRIGGERS surface in src/charter/activations.py, _OPTIONAL_EMPTY_OMIT_KEYS extended, GovernanceConfig.activations field added. 4/4 test_activation_registry_schema and 1/3 test_artifact_selection_completeness (the WP01 target) now green; remaining 2 belong to WP06 T002. layer-rules 9/9 still passing; full architectural suite 117 pass / 2 known WP06 failures.
