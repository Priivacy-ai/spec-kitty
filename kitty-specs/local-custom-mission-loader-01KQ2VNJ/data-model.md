# Phase 1 Data Model: Local Custom Mission Loader

## Schema additions

### `PromptStep` (extend, in `src/specify_cli/next/_internal_runtime/schema.py`)

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `id` | `str` (non-empty) | required | Existing. Used as the `action` field on synthesized contracts. |
| `title` | `str` (non-empty) | required | Existing. |
| `description` | `str` | `""` | Existing. |
| `prompt` | `str \| None` | `None` | Existing. |
| `prompt_template` | `str \| None` | `None` | Existing. |
| `expected_output` | `str \| None` | `None` | Existing. |
| `requires_inputs` | `list[str]` | `[]` | Existing. When non-empty, the engine planner routes this step through the `decision_required` path. |
| `depends_on` | `list[str]` | `[]` | Existing. |
| `raci` | `RACIAssignment \| None` | `None` | Existing. |
| `raci_override_reason` | `str \| None` | `None` | Existing. |
| **`agent_profile`** | **`str \| None`** | **`None`** | **NEW.** Pydantic field alias `agent-profile`. When set, the composition gate dispatches this step through `StepContractExecutor` with `profile_hint=<value>`. |
| **`contract_ref`** | **`str \| None`** | **`None`** | **NEW.** Optional pointer to a pre-existing `MissionStepContract.id`. When present, contract synthesis is skipped for this step; the repository must resolve the ID. |

#### Invariants on `PromptStep`

1. If `requires_inputs` is empty and `agent_profile` is `None` and `contract_ref` is `None`, the step is interpreted as a "narrative" step (legacy DAG / engine-only). This case is allowed but does NOT participate in composition.
2. If `agent_profile` is non-empty AND `contract_ref` is non-empty, the loader emits a `MISSION_STEP_AMBIGUOUS_BINDING` error (operator must pick one).
3. The Pydantic config for `PromptStep` MUST set `populate_by_name=True` and `alias_generator` such that `agent_profile` is also accepted as `agent-profile` from YAML.

### `MissionTemplate` (no field change; cross-step rules)

#### Invariants enforced at validate time (`mission_loader.validator`)

1. **R-001:** `template.steps[-1].id == "retrospective"`. Error code: `MISSION_RETROSPECTIVE_MISSING`.
2. **R-002:** `template.mission.key not in RESERVED_BUILTIN_KEYS` UNLESS the discovered tier is `builtin`. Error code: `MISSION_KEY_RESERVED`.
3. **FR-008:** for every step with `requires_inputs == []`, at least one of `agent_profile` or `contract_ref` MUST be set. Error code: `MISSION_STEP_NO_PROFILE_BINDING`.
4. **R-004:** if `step.contract_ref` is set, the (final) repository MUST resolve it. Error code: `MISSION_CONTRACT_REF_UNRESOLVED`.

### `DiscoveryWarning` and `DiscoveryResult` (existing, no schema change)

The validator wraps the existing `DiscoveryResult.warnings` and folds them into the loader's `ValidationReport` so warnings flow through unchanged. `DiscoveryWarning` is the wire shape for things like load failures already.

## New types (in `src/specify_cli/mission_loader/`)

### `LoaderErrorCode` (closed enum, in `errors.py`)

```python
from enum import StrEnum

class LoaderErrorCode(StrEnum):
    MISSION_YAML_MALFORMED = "MISSION_YAML_MALFORMED"
    MISSION_KEY_UNKNOWN = "MISSION_KEY_UNKNOWN"
    MISSION_KEY_AMBIGUOUS = "MISSION_KEY_AMBIGUOUS"
    MISSION_KEY_RESERVED = "MISSION_KEY_RESERVED"
    MISSION_RETROSPECTIVE_MISSING = "MISSION_RETROSPECTIVE_MISSING"
    MISSION_STEP_NO_PROFILE_BINDING = "MISSION_STEP_NO_PROFILE_BINDING"
    MISSION_STEP_AMBIGUOUS_BINDING = "MISSION_STEP_AMBIGUOUS_BINDING"
    MISSION_CONTRACT_REF_UNRESOLVED = "MISSION_CONTRACT_REF_UNRESOLVED"
    MISSION_REQUIRED_FIELD_MISSING = "MISSION_REQUIRED_FIELD_MISSING"
```

### `LoaderWarningCode` (closed enum)

```python
class LoaderWarningCode(StrEnum):
    MISSION_KEY_SHADOWED = "MISSION_KEY_SHADOWED"
    MISSION_PACK_LOAD_FAILED = "MISSION_PACK_LOAD_FAILED"
```

### `LoaderError` (Pydantic)

```python
class LoaderError(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: LoaderErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
```

`details` keys MAY include: `file` (str), `mission_key` (str), `step_id` (str), `tier` (str), `origin` (str), `shadowed_paths` (list[str]).

### `LoaderWarning` (Pydantic)

```python
class LoaderWarning(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: LoaderWarningCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
```

### `ValidationReport` (Pydantic)

```python
class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    template: MissionTemplate | None = None
    discovered: DiscoveredMission | None = None
    errors: list[LoaderError] = Field(default_factory=list)
    warnings: list[LoaderWarning] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0 and self.template is not None
```

## Synthesized contract record (per R-004)

```python
# pseudo-shape produced by mission_loader.contract_synthesis.synthesize_contracts
MissionStepContract(
    id=f"custom:{template.mission.key}:{step.id}",
    mission=template.mission.key,
    action=step.id,
    steps=[
        MissionStep(
            id=f"{step.id}.execute",
            title=step.title,
            description=step.description,
            delegates_to=None,        # no delegation in v1; flat contracts
            ...
        ),
    ],
    drg_context=None,                  # uses defaults
    raci=step.raci,                    # if set; else None
)
```

The synthesized contracts are kept in a per-process registry that wraps `MissionStepContractRepository.get(id)` to fall through to the synthesized table when the on-disk repo doesn't know the ID. This keeps the on-disk repository immutable.

## Reserved built-in keys constant

```python
# src/specify_cli/next/_internal_runtime/discovery.py
RESERVED_BUILTIN_KEYS: frozenset[str] = frozenset({
    "software-dev",
    "research",
    "documentation",
    "plan",
})
```

## Validation flow

```
load_and_validate(mission_key, ctx) -> ValidationReport:
  result = discover_missions_with_warnings(ctx)
  selected = next((m for m in result.missions if m.key == mission_key and m.selected), None)
  if selected is None:
    # if no selected entry exists at all → MISSION_KEY_UNKNOWN
    # if multiple entries exist with selected=False (none selected) → MISSION_KEY_AMBIGUOUS
    return ValidationReport(errors=[...])
  if selected.key in RESERVED_BUILTIN_KEYS and selected.precedence_tier != "builtin":
    return ValidationReport(errors=[LoaderError(MISSION_KEY_RESERVED, ...)])
  template = load_mission_template_file(Path(selected.path))  # may raise MissionRuntimeError → MISSION_YAML_MALFORMED
  errors = []
  if template.steps[-1].id != "retrospective":
    errors.append(LoaderError(MISSION_RETROSPECTIVE_MISSING, ...))
  for step in template.steps:
    if not step.requires_inputs and step.agent_profile is None and step.contract_ref is None:
      errors.append(LoaderError(MISSION_STEP_NO_PROFILE_BINDING, ...))
    if step.agent_profile is not None and step.contract_ref is not None:
      errors.append(LoaderError(MISSION_STEP_AMBIGUOUS_BINDING, ...))
  warnings = [LoaderWarning(MISSION_KEY_SHADOWED, ...) for shadow in shadowed(selected.key, result)]
  return ValidationReport(template=template, discovered=selected, errors=errors, warnings=warnings)
```

## State transitions (custom mission lifecycle)

```
operator -> "spec-kitty mission run <key> --mission <slug>"
        -> validator.validate_custom_mission(key, ctx)
        -> if errors: render & exit 2; STOP
        -> if ok:
            -> contract_synthesis.synthesize_contracts(template) → in-process registry
            -> runtime_bridge.get_or_start_run(slug, repo_root, key, custom_template=template)
            -> render success envelope; exit 0

operator -> "spec-kitty next --agent <name> --mission <slug>"
        -> runtime_bridge.decide_next_via_runtime(...)
            -> for composed step: dispatch via StepContractExecutor with profile_hint=step.agent_profile
            -> for decision_required step: pause + emit DecisionInputRequested
            -> for retrospective step (id == "retrospective"): treat as terminal narrative step (no execution side effect this tranche)
```
