# Data Model — Charter-Mediated Doctrine Selection (Mission B)

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Companion: [plan.md](plan.md) | [contracts/](contracts/)

This document defines the new and extended data shapes introduced by the mission. All schemas are Pydantic v2 (matching the existing codebase conventions). Field defaults preserve NFR-005 backward compatibility — every new field defaults to an empty list / `None` so existing fixtures parse unchanged.

---

## 1. `DoctrineSelectionConfig` — extension (FR-001)

Location: `src/charter/schemas.py`

**Existing fields (kept unchanged):**

| Field | Type | Default |
|-------|------|---------|
| `selected_paradigms` | `list[str]` | `[]` |
| `selected_directives` | `list[str]` | `[]` |
| `selected_tactics` | `list[str]` | `[]` |
| `available_tools` | `list[str]` | `[]` |
| `template_set` | `str \| None` | `None` |
| `authority_paths` | `list[str]` | `[]` |

**New fields (this mission):**

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `selected_styleguides` | `list[str]` | `[]` | Globally active styleguide artifact IDs |
| `selected_toolguides` | `list[str]` | `[]` | Globally active toolguide artifact IDs |
| `selected_procedures` | `list[str]` | `[]` | Globally active procedure artifact IDs |
| `selected_agent_profiles` | `list[str]` | `[]` | Globally active agent-profile artifact IDs |
| `selected_mission_step_contracts` | `list[str]` | `[]` | Globally active mission-step-contract artifact IDs |

**Invariants:**

- Parity rule: the set of `selected_<kind>` fields MUST match 1:1 the set of `@property` artifact kinds on `doctrine.service.DoctrineService` (enforced by `test_artifact_selection_completeness.py::test_every_doctrine_kind_has_a_charter_selected_field`).
- Naming convention: `selected_<plural_kind>` where `<plural_kind>` matches the `DoctrineService` property name verbatim.
- Empty-list defaults serialise via the `_OPTIONAL_EMPTY_OMIT_KEYS` allow-list — when empty, the field is omitted from `governance.yaml` to preserve byte-identical output (NFR-005).

---

## 2. `OrgCharterPolicy` — extension (FR-002, FR-008)

Location: `src/specify_cli/doctrine/org_charter.py`

**Existing fields (kept unchanged):**

| Field | Type | Default |
|-------|------|---------|
| `schema_version` | `str` | `"1"` |
| `org_name` | `str \| None` | `None` |
| `interview_defaults` | `dict[str, str \| bool]` | `{}` |
| `required_directives` | `list[str]` | `[]` |
| `governance_policies` | `list[GovernancePolicy]` | `[]` |

**New `required_<kind>` fields (this mission):**

| Field | Type | Default |
|-------|------|---------|
| `required_paradigms` | `list[str]` | `[]` |
| `required_tactics` | `list[str]` | `[]` |
| `required_styleguides` | `list[str]` | `[]` |
| `required_toolguides` | `list[str]` | `[]` |
| `required_procedures` | `list[str]` | `[]` |
| `required_agent_profiles` | `list[str]` | `[]` |
| `required_mission_step_contracts` | `list[str]` | `[]` |

(`required_directives` remains; the 7 above bring the total to 8 — parity with the 8 `DoctrineService` properties.)

**New activations field (this mission, FR-008):**

| Field | Type | Default |
|-------|------|---------|
| `activations` | `list[ActivationEntry]` | `[]` |

**Invariants:**

- Mirror rule: for every `selected_<kind>` on `DoctrineSelectionConfig`, there MUST be a matching `required_<kind>` on `OrgCharterPolicy` with the same suffix (enforced by `test_artifact_selection_completeness.py::test_selection_and_required_field_names_are_consistent`).
- Merge across packs (`load_org_charter_policies`): each `required_<kind>` is a union preserving first-seen order; `activations` is concatenated with last-duplicate-wins on `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)` key.

---

## 3. `ActivationEntry` — NEW (FR-006)

Location: `src/charter/activations.py`

**Fields:**

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `activation_context` | `dict[str, str]` | yes | Context match key. Recognised keys: `mission_type`, `action`. Either may be absent (= wildcard) or `generic`/`any` (= wildcard). |
| `doctrine_pack_id` | `str` | yes | Pack ID. Recognised values: `project`, `built-in`, or any configured org pack name. |
| `artifact_id` | `str` | yes | Artifact ID within the pack. |
| `artifact_kind` | `str \| None` | no | Optional disambiguator when two artifacts share an ID across kinds. |

**Field validators:**

- `activation_context.mission_type`, if present, MUST be a member of `ALLOWED_MISSION_TYPES`. Typos raise `pydantic.ValidationError`.
- `activation_context.action`, if present, MUST be a member of `ALLOWED_ACTIONS`. Typos raise `pydantic.ValidationError`.
- `doctrine_pack_id` MUST be a non-empty string.
- `artifact_id` MUST be a non-empty string.
- `artifact_kind`, if present, MUST be one of the 8 `DoctrineService` property names.

**Pydantic model_config:** `extra="forbid"` to catch schema typos at parse time.

---

## 4. `Activations` registry shape

The registry is **not a wrapper type**; it's the bare `list[ActivationEntry]` carried on:

- `OrgCharterPolicy.activations` (org-pack-level, FR-008)
- `GovernanceConfig.activations` (project-charter-level, populated by extractor, FR-006)
- `MissionTypeProfile.activations` (mission-type-profile-level, FR-010)

Resolver call (`charter.activations.resolve_for_context`) flattens the three sources into a single list and filters by current `(mission_type, action)`.

**Merge semantics across the three sources:**

| Source | Merge strategy |
|--------|----------------|
| Mission-type profile | Base |
| Project charter | Concatenated after profile |
| Org packs | Concatenated last; org wins on identity-key collisions (last entry of each `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)` tuple wins) |

Identity for collision detection is the 4-tuple
`(json_dumps(activation_context, sort_keys=True), doctrine_pack_id, artifact_id, artifact_kind or "")`. Two entries with the same identity collapse to one (last wins).

---

## 5. `ActivationContext` vocabulary (FR-006)

Two closed sets pinned by `test_activation_registry_schema.py`:

### `ALLOWED_MISSION_TYPES`

```
{"software-dev", "documentation", "research", "plan", "any", "generic"}
```

`any` and `generic` are wildcards; the four named values are the canonical mission types matching `mission.yaml` keys.

### `ALLOWED_ACTIONS`

See [data-model.md §7](#7-trigger-registry-fr-009--canonical-definition) for the canonical 10-token frozenset, the `_REGISTERED_TRIGGERS = _ALLOWED_ACTIONS ∪ {fine-grained tokens}` union formula, and the mandatory runtime re-export contract. Do not restate the vocabulary here.

---

## 6. `MissionTypeProfile` — NEW (FR-010)

Location: `src/charter/mission_type_profiles.py`

YAML on-disk shape (one file per mission type under `src/doctrine/missions/<type>/governance-profile.yaml`):

```yaml
mission_type: documentation        # required, MUST match directory name
template_set: documentation-default  # optional
selected_styleguides: []           # optional, defaults []
selected_toolguides: []            # optional
selected_procedures: []            # optional
selected_directives: []            # optional
selected_tactics: []               # optional
selected_paradigms: []             # optional
selected_agent_profiles: []        # optional
selected_mission_step_contracts: []  # optional
available_tools: []                # optional
activations: []                    # optional, list[ActivationEntry]
```

**Pydantic model:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mission_type` | `Literal["software-dev", "documentation", "research", "plan"]` | yes | — |
| `template_set` | `str \| None` | no | `None` |
| all 8 `selected_<kind>` fields | `list[str]` | no | `[]` |
| `available_tools` | `list[str]` | no | `[]` |
| `activations` | `list[ActivationEntry]` | no | `[]` |

**Invariant**: top-level `mission_type` MUST match the parent directory name (pinned by `test_profile_yaml_declares_its_mission_type`).

---

## 7. Trigger Registry (FR-009) — CANONICAL DEFINITION

This section is the **single source of truth** for both the operator-side activation vocabulary and the artifact-side trigger vocabulary. Every other planning document (plan.md §2.10, §5 of this file, contracts/activation-registry.md, WP05) MUST reference this section instead of restating the vocabulary or the union formula.

### Canonical home and runtime re-export

Both vocabularies are defined as **`frozenset[str]` constants** in `tests/architectural/test_trigger_registry_coverage.py` (the canonical home — purely declarative, no runtime semantics, lives next to the architectural gates that pin them):

- `_ALLOWED_ACTIONS` — **10 tokens** — the closed vocabulary for `activation_context.action` in operator-authored `activations:` blocks. Used by the charter sync validator and by the activation-registry resolver.
- `_REGISTERED_TRIGGERS` — **15 tokens** — the closed vocabulary for the `triggers:` field on rendered artifact stanzas. It is a strict superset of `_ALLOWED_ACTIONS` per the formula below.

```python
# tests/architectural/test_trigger_registry_coverage.py
_ALLOWED_ACTIONS: frozenset[str] = frozenset({
    # Mission-type verbs
    "specify", "plan", "tasks", "implement", "review", "merge", "accept",
    # Charter-loop verbs
    "charter.interview", "charter.generate", "charter.context",
})

# Union formula (the ONLY place this formula appears):
_REGISTERED_TRIGGERS: frozenset[str] = _ALLOWED_ACTIONS | frozenset({
    "write_comment", "write_docstring", "rename_identifier", "add_dependency",
})
```

In set notation: `_REGISTERED_TRIGGERS = _ALLOWED_ACTIONS  ∪  {write_comment, write_docstring, rename_identifier, add_dependency}`.

### MANDATORY runtime re-export

`src/charter/activations.py` **MUST** re-export both sets as `ALLOWED_ACTIONS` and `REGISTERED_TRIGGERS` for runtime consumers (resolvers, prompt builders, validators). The re-export is **non-optional** — it removes the prior ambiguity where the runtime might copy/paste a divergent literal.

```python
# src/charter/activations.py
from tests.architectural.test_trigger_registry_coverage import (
    _ALLOWED_ACTIONS as ALLOWED_ACTIONS,
    _REGISTERED_TRIGGERS as REGISTERED_TRIGGERS,
)
# (or equivalent symbol relocation; the runtime contract is that the two pairs
# are byte-identical frozensets at import time.)
```

A new architectural cross-check test `test_trigger_registry_runtime_export_in_sync` lives in the same `tests/architectural/test_trigger_registry_coverage.py` file and asserts byte-identical equality between the canonical frozensets and the runtime re-exports. This makes any copy/paste drift fail CI immediately.

### Invariants

- Both constants MUST be a `frozenset` (pinned by `test_registered_triggers_constant_is_a_frozenset_for_immutability`).
- Every `triggers:` value declared in a shipped doctrine artifact (`src/doctrine/**/*.yaml`) MUST be a member of `_REGISTERED_TRIGGERS` (pinned by `test_every_declared_trigger_is_in_the_registered_set`).
- `charter.activations.ALLOWED_ACTIONS == _ALLOWED_ACTIONS` and `charter.activations.REGISTERED_TRIGGERS == _REGISTERED_TRIGGERS` (pinned by `test_trigger_registry_runtime_export_in_sync`).

### Mutation rule

Adding a new trigger token is a deliberate amend that requires:

1. Adding the token to the appropriate canonical frozenset in `tests/architectural/test_trigger_registry_coverage.py` (`_ALLOWED_ACTIONS` for operator-authorable verbs, otherwise extend the fine-grained suffix in `_REGISTERED_TRIGGERS`).
2. Teaching the prompt builder to emit a fetch stanza when the token appears in an `activations:` entry or artifact `triggers:` block.
3. Adding a follow-up artifact that declares the new trigger (otherwise the entry is dead).
4. Running the cross-check test to confirm the runtime re-exports still match.

---

## 8. Charter facade module structure (FR-012)

Six new modules under `src/charter/`. Each is a re-export-only module — no behaviour, no abstractions, no new types. The facade table:

| Facade | Re-exported symbols | Source module |
|--------|---------------------|---------------|
| `charter/profiles.py` | `AgentProfile`, `AgentProfileRepository`, `Role`, `DEFAULT_ROLE_CAPABILITIES` | `doctrine.agent_profiles.profile`, `.repository`, `.capabilities` |
| `charter/mission_steps.py` | `MissionStep`, `MissionStepContract`, `MissionStepContractRepository` | `doctrine.mission_step_contracts.models`, `.repository` |
| `charter/drg.py` | `DRGEdge`, `DRGGraph`, `DRGNode`, `Relation`, `NodeKind`, `load_graph`, `merge_layers`, `resolve_context`, `ResolvedContext` | `doctrine.drg`, `doctrine.drg.models`, `doctrine.drg.query` |
| `charter/primitives.py` | `PrimitiveExecutionContext`, `execute_with_glossary` | `doctrine.missions` |
| `charter/resolution.py` | `ResolutionResult`, `ResolutionTier` | `doctrine.resolver` |
| `charter/versioning.py` | `check_bundle_compatibility`, `get_bundle_schema_version` | `doctrine.versioning` |

**Each facade module shape:**

```python
"""<one-line purpose>.

Re-exports the doctrine.<sub> surface used by the runtime, so callers under
src/specify_cli/ can import via the charter proxy (runtime → charter →
doctrine boundary, enforced by test_runtime_charter_doctrine_boundary.py).
"""
from doctrine.<sub> import <SymbolA>, <SymbolB>, ...

__all__ = ["<SymbolA>", "<SymbolB>", ...]
```

No additional logic. Tests for these modules assert (a) the module imports cleanly and (b) each symbol in `__all__` resolves to the doctrine original.

---

## 9. `GovernancePayload` (returned by `resolve_governance`)

Implementation-level dataclass returned by `charter.mission_type_profiles.resolve_governance`. Exact shape determined during implementation; minimum surface required by the ATDD:

| Field | Type | Source test |
|-------|------|-------------|
| `text` | `str` | `test_resolve_governance_picks_documentation_profile_for_documentation_mission` reads `payload.text` |
| `mission_type` | `str` | Same test asserts `payload.mission_type == "documentation"` |

Implementation MAY return `CharterContextResult` (existing dataclass in `charter.context`) extended with a `mission_type` field, or a new `GovernancePayload` type. The decision is left to WP08 implementation.

---

## 10. Field-name normalisation table

Critical for the parity rules to hold. Every artifact kind has exactly one canonical pluralised identifier used everywhere.

| `DoctrineService` property | `selected_<kind>` field | `required_<kind>` field |
|----------------------------|--------------------------|--------------------------|
| `directives` | `selected_directives` | `required_directives` |
| `tactics` | `selected_tactics` | `required_tactics` |
| `styleguides` | `selected_styleguides` | `required_styleguides` |
| `toolguides` | `selected_toolguides` | `required_toolguides` |
| `paradigms` | `selected_paradigms` | `required_paradigms` |
| `procedures` | `selected_procedures` | `required_procedures` |
| `agent_profiles` | `selected_agent_profiles` | `required_agent_profiles` |
| `mission_step_contracts` | `selected_mission_step_contracts` | `required_mission_step_contracts` |
