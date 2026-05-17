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

```
{
  # Mission-type verbs
  "specify", "plan", "tasks", "implement", "review", "merge", "accept",
  # Charter-loop verbs
  "charter.interview", "charter.generate", "charter.context",
}
```

10 values total. **Note**: this is the activation-context vocabulary; the **Trigger Registry** (§7 below) is a strict superset that also includes the 4 fine-grained agent-action tokens (`write_comment`, `write_docstring`, `rename_identifier`, `add_dependency`).

Two-vocabulary design rationale: `ALLOWED_ACTIONS` is what a charter operator writes in an `activations:` block; `_REGISTERED_TRIGGERS` is what an artifact author may declare in a `triggers:` block. The two diverge by design — the fine-grained tokens are artifact-driven and never appear in charter-side activation contexts.

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

## 7. Trigger Registry (FR-009)

Location: `tests/architectural/test_trigger_registry_coverage.py::_REGISTERED_TRIGGERS` (the canonical home is in the test file per the test's contract; runtime consumers reference it indirectly via the test as the architectural gate).

```python
_REGISTERED_TRIGGERS: frozenset[str] = frozenset({
    # Mission-type verbs
    "specify", "plan", "tasks", "implement", "review", "merge", "accept",
    # Charter-loop verbs
    "charter.interview", "charter.generate", "charter.context",
    # Fine-grained tokens (initial set)
    "write_comment", "write_docstring", "rename_identifier", "add_dependency",
})
```

**Invariants:**

- MUST be a `frozenset` (pinned by `test_registered_triggers_constant_is_a_frozenset_for_immutability`).
- Every `triggers:` value declared in a shipped doctrine artifact (`src/doctrine/**/*.yaml`) MUST be a member (pinned by `test_every_declared_trigger_is_in_the_registered_set`).

**Mutation rule:** adding a new trigger token is a deliberate amend that requires:

1. Adding the token to `_REGISTERED_TRIGGERS` in this file.
2. Teaching the prompt builder to emit a fetch stanza when the token appears in an `activations:` entry or artifact `triggers:` block.
3. Adding a follow-up artifact that declares the new trigger (otherwise the entry is dead).

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
