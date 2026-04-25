---
work_package_id: WP02
title: Loader Errors, Validator, and Reserved-Key Discovery Extension
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- FR-013
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - Loader core
assignee: ''
agent: claude
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/mission_loader/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_loader/__init__.py
- src/specify_cli/mission_loader/errors.py
- src/specify_cli/mission_loader/retrospective.py
- src/specify_cli/mission_loader/validator.py
- src/specify_cli/next/_internal_runtime/discovery.py
- tests/unit/mission_loader/__init__.py
- tests/unit/mission_loader/test_retrospective_marker.py
- tests/unit/mission_loader/test_validator_errors.py
- tests/unit/mission_loader/test_loader_facade.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Loader Errors, Validator, and Reserved-Key Discovery Extension

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Stand up the `mission_loader/` package: the closed enum of error / warning codes, the retrospective-marker check, the discovery-side reserved-key constant, and the orchestrating `validate_custom_mission()` function. Test-first for every stable error code (FR-004 / NFR-002).

Success criteria:
1. `LoaderErrorCode` and `LoaderWarningCode` are `StrEnum`s containing exactly the codes in [contracts/validation-errors.md](../contracts/validation-errors.md).
2. `LoaderError`, `LoaderWarning`, and `ValidationReport` are frozen Pydantic models with stable shapes.
3. `validate_custom_mission(mission_key, context)` returns a `ValidationReport` covering every closed error / warning code per the §Validation flow in [data-model.md](../data-model.md).
4. `RESERVED_BUILTIN_KEYS` lives in `_internal_runtime/discovery.py`; the validator consults it to reject built-in shadowing with `MISSION_KEY_RESERVED`.
5. ≥ 90% line coverage on the new modules; `mypy --strict` clean; existing tests stay green.

## Context & Constraints

- WP02 does **not** modify dispatch, runtime, or CLI surfaces. It produces only validation outputs that WP05 will render.
- WP02 does **not** add a new loader. Reuse `discovery.discover_missions_with_warnings()` and `load_mission_template_file()`.
- Reserved keys are: `software-dev`, `research`, `documentation`, `plan`. Defined as `frozenset[str]`. Built-in tier is exempt (built-ins can declare their own keys; only non-builtin tiers are rejected).
- Validation never throws on operator-fixable errors — always returns them inside `ValidationReport.errors`.
- See [research.md](../research.md) §R-001 (retrospective marker), §R-002 (reserved-key policy), §R-008 (envelope shape).

## Subtasks & Detailed Guidance

### Subtask T005 — Create `mission_loader/__init__.py` package stub

- **Purpose**: Establish the package and export the stable public API for downstream WPs.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/__init__.py`.
  2. Re-export the public surface that other modules will import:
     ```python
     from specify_cli.mission_loader.errors import (
         LoaderError,
         LoaderErrorCode,
         LoaderWarning,
         LoaderWarningCode,
         ValidationReport,
     )
     from specify_cli.mission_loader.retrospective import has_retrospective_marker
     from specify_cli.mission_loader.validator import validate_custom_mission

     __all__ = [
         "LoaderError",
         "LoaderErrorCode",
         "LoaderWarning",
         "LoaderWarningCode",
         "ValidationReport",
         "has_retrospective_marker",
         "validate_custom_mission",
     ]
     ```
- **Files**: `src/specify_cli/mission_loader/__init__.py`.
- **Notes**: Keep imports lazy if circular issues appear, but the module graph here is straightforward.

### Subtask T006 — Create `errors.py`

- **Purpose**: Define the closed enums + Pydantic models that all validation outputs use. The shape is stability-critical (NFR-002).
- **Steps**:
  1. Create `src/specify_cli/mission_loader/errors.py`.
  2. Define `LoaderErrorCode(StrEnum)` with the exact values listed in [contracts/validation-errors.md](../contracts/validation-errors.md) §Errors. Match the wire spelling exactly (e.g., `MISSION_RETROSPECTIVE_MISSING`, not `RETROSPECTIVE_MISSING`).
  3. Define `LoaderWarningCode(StrEnum)` with the values from §Warnings (`MISSION_KEY_SHADOWED`, `MISSION_PACK_LOAD_FAILED`).
  4. Define `LoaderError(BaseModel)`:
     ```python
     class LoaderError(BaseModel):
         model_config = ConfigDict(frozen=True)
         code: LoaderErrorCode
         message: str
         details: dict[str, Any] = Field(default_factory=dict)
     ```
  5. Define `LoaderWarning(BaseModel)` with the same shape but `LoaderWarningCode`.
  6. Define `ValidationReport(BaseModel)` per [data-model.md](../data-model.md):
     ```python
     class ValidationReport(BaseModel):
         model_config = ConfigDict(frozen=True)
         template: MissionTemplate | None = None
         discovered: DiscoveredMission | None = None
         errors: list[LoaderError] = Field(default_factory=list)
         warnings: list[LoaderWarning] = Field(default_factory=list)

         @property
         def ok(self) -> bool:
             return self.template is not None and not self.errors
     ```
- **Files**: `src/specify_cli/mission_loader/errors.py`.
- **Notes**: Import `MissionTemplate` and `DiscoveredMission` from `specify_cli.next._internal_runtime.schema`.

### Subtask T007 — Create `retrospective.py`

- **Purpose**: Single-responsibility helper for FR-005's structural marker rule.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/retrospective.py`.
  2. Implement:
     ```python
     RETROSPECTIVE_MARKER_ID = "retrospective"

     def has_retrospective_marker(template: MissionTemplate) -> bool:
         """Return True iff the template's last step has id == 'retrospective'."""
         if not template.steps:
             return False
         return template.steps[-1].id == RETROSPECTIVE_MARKER_ID
     ```
- **Files**: `src/specify_cli/mission_loader/retrospective.py`.
- **Parallel?**: [P] — independent of T005/T006.
- **Notes**: Future tranches (#506-#511) may attach behavior to this id. Keep the marker constant exported.

### Subtask T008 — Add `RESERVED_BUILTIN_KEYS` to `discovery.py`

- **Purpose**: Single source of truth for which keys built-in dispatch reserves.
- **Steps**:
  1. Open `src/specify_cli/next/_internal_runtime/discovery.py`.
  2. Add (just below the imports, near top of module):
     ```python
     RESERVED_BUILTIN_KEYS: frozenset[str] = frozenset({
         "software-dev",
         "research",
         "documentation",
         "plan",
     })


     def is_reserved_key(key: str) -> bool:
         """Return True iff `key` is a reserved built-in mission key."""
         return key in RESERVED_BUILTIN_KEYS
     ```
- **Files**: `src/specify_cli/next/_internal_runtime/discovery.py`.
- **Notes**: Don't change `_build_tiers` or any other discovery function; only add the constant + helper.

### Subtask T009 — Create `validator.py`

- **Purpose**: Orchestrate discovery → load → structural validation → return ValidationReport.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/validator.py`.
  2. Implement `validate_custom_mission(mission_key: str, context: DiscoveryContext) -> ValidationReport` per the [data-model.md](../data-model.md) §Validation flow pseudocode. Specifically:
     - Call `discover_missions_with_warnings(context)`.
     - Locate the *selected* `DiscoveredMission` for `mission_key`. If none → `MISSION_KEY_UNKNOWN`. Capture `tiers_searched` for `details`.
     - If the selected entry's `precedence_tier != "builtin"` and `is_reserved_key(mission_key)` → `MISSION_KEY_RESERVED`. Don't load.
     - Wrap `load_mission_template_file(Path(selected.path))` in `try/except`. Map `pydantic.ValidationError` → `MISSION_REQUIRED_FIELD_MISSING` if the missing field can be identified, else `MISSION_YAML_MALFORMED`. `yaml.YAMLError` → `MISSION_YAML_MALFORMED`. Other → `MISSION_YAML_MALFORMED`.
     - On a successfully loaded template:
       - If not `has_retrospective_marker(template)` → `MISSION_RETROSPECTIVE_MISSING` with `details={"actual_last_step_id": template.steps[-1].id if template.steps else None, "expected": "retrospective"}`.
       - For each `step` in `template.steps`:
         - If `step.requires_inputs == [] and step.agent_profile is None and step.contract_ref is None and step.id != "retrospective"` → `MISSION_STEP_NO_PROFILE_BINDING` with `details={"step_id": step.id}`.
         - If `step.agent_profile is not None and step.contract_ref is not None` → `MISSION_STEP_AMBIGUOUS_BINDING`.
       - **Note**: `MISSION_CONTRACT_REF_UNRESOLVED` is checked at run-start in WP05 (not here), since the on-disk repository may not be loaded at this stage. Document the boundary.
     - Build warnings: for every shadowed entry of the selected key (entries with `selected=False` matching the same key), emit `MISSION_KEY_SHADOWED`. For every load-failure warning in `discovery_result.warnings`, emit `MISSION_PACK_LOAD_FAILED` (when the warning came from a pack tier).
- **Files**: `src/specify_cli/mission_loader/validator.py`.
- **Notes**: Keep the function pure — no I/O beyond what `discover_missions_with_warnings` and `load_mission_template_file` already do. Do NOT register synthesized contracts here (that's WP03).

### Subtask T010 — Unit tests for `has_retrospective_marker`

- **Purpose**: FR-005 / NFR-002 compliance.
- **Steps**:
  1. Create `tests/unit/mission_loader/__init__.py` (empty).
  2. Create `tests/unit/mission_loader/test_retrospective_marker.py`.
  3. Cases:
     - `test_marker_present` — last step id == "retrospective" → True.
     - `test_marker_absent` — last step id == "write-report" → False.
     - `test_no_steps` — `template.steps == []` → False.
     - `test_marker_not_last` — "retrospective" appears earlier but last is something else → False.
- **Files**: `tests/unit/mission_loader/test_retrospective_marker.py`.
- **Parallel?**: [P].

### Subtask T011 — Parametrized unit tests covering every error code

- **Purpose**: NFR-002 enforces "every closed error code reachable". This is the test that locks the contract.
- **Steps**:
  1. Create `tests/unit/mission_loader/test_validator_errors.py`.
  2. Author test fixtures under `tmp_path` for each error code:
     - `MISSION_YAML_MALFORMED`: write a `.kittify/missions/<key>/mission.yaml` with `<<<` invalid YAML.
     - `MISSION_REQUIRED_FIELD_MISSING`: omit `mission.key` field.
     - `MISSION_KEY_UNKNOWN`: invoke validator with a key not present anywhere.
     - `MISSION_KEY_RESERVED`: write a custom mission with `mission.key: software-dev` under `.kittify/missions/`.
     - `MISSION_RETROSPECTIVE_MISSING`: valid YAML, last step id != "retrospective".
     - `MISSION_STEP_NO_PROFILE_BINDING`: composed step without `agent_profile`/`contract_ref`/`requires_inputs`.
     - `MISSION_STEP_AMBIGUOUS_BINDING`: step with both `agent_profile` and `contract_ref`.
  3. Each test asserts `report.errors[0].code == LoaderErrorCode.<code>` and inspects required `details` keys per [contracts/validation-errors.md](../contracts/validation-errors.md).
  4. Add `MISSION_CONTRACT_REF_UNRESOLVED` as a TODO comment with rationale (deferred to WP05's run-start check).
- **Files**: `tests/unit/mission_loader/test_validator_errors.py`.
- **Parallel?**: [P].

### Subtask T012 — Unit tests for precedence + shadow + reserved-key rules

- **Purpose**: FR-002 / FR-011 / R-002.
- **Steps**:
  1. Create `tests/unit/mission_loader/test_loader_facade.py`.
  2. Cases:
     - `test_precedence_explicit_over_env` — `DiscoveryContext(explicit_paths=[a])` wins over env-set `b`.
     - `test_project_override_over_legacy` — `.kittify/overrides/missions/foo/mission.yaml` wins over `.kittify/missions/foo/mission.yaml`; report carries one warning `MISSION_KEY_SHADOWED`.
     - `test_user_global_lower_than_project` — both define `foo`; selected is project; warning emitted.
     - `test_loads_from_kittify_missions` — single project_legacy entry → no warnings, ok=True.
     - `test_loads_from_overrides` — single project_override entry.
     - `test_loads_from_mission_pack_manifest` — `.kittify/config.yaml` declares a mission pack containing `foo` → discovery resolves it.
     - `test_reserved_key_shadow_rejected_with_MISSION_KEY_RESERVED` — write `software-dev` under `.kittify/missions/` → report.errors[0].code == `MISSION_KEY_RESERVED`.
     - `test_builtin_software_dev_not_rejected` — invoking the validator with `mission_key="software-dev"` from the built-in tier returns ok=True (built-in tier is exempt).
- **Files**: `tests/unit/mission_loader/test_loader_facade.py`.
- **Parallel?**: [P].

## Test Strategy (charter required)

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/unit/mission_loader/ tests/architectural/test_shared_package_boundary.py -q
UV_PYTHON=3.13.9 uv run --no-sync ruff check src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py tests/unit/mission_loader
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py
UV_PYTHON=3.13.9 uv run --no-sync pytest --cov=src/specify_cli/mission_loader --cov-report=term-missing tests/unit/mission_loader/ -q
```

The coverage report must show ≥ 90% line coverage on the `mission_loader/` package (NFR-003). If a code branch can't be covered, leave a comment explaining why.

## Risks & Mitigations

- **Risk**: `MissionTemplate.model_validate` raises a generic `pydantic.ValidationError` that bundles multiple field errors; mapping to a single error code is lossy.
  - **Mitigation**: Iterate `e.errors()` and emit one `LoaderError(MISSION_REQUIRED_FIELD_MISSING)` per missing required field, falling back to `MISSION_YAML_MALFORMED` for malformed-shape errors. Document the fallback in the validator docstring.
- **Risk**: Adding `MISSION_KEY_RESERVED` rejection breaks any existing test that creates a `software-dev` mission YAML under `.kittify/missions/`.
  - **Mitigation**: Search existing tests; they should be using built-in tier or different keys. Confirm no regressions before completing.
- **Risk**: `pyproject.toml` may not have a coverage config that includes the new package.
  - **Mitigation**: WP07 owns CI coverage configuration; this WP only runs the local check. Coordinate at integration time.

## Review Guidance

- Reviewer verifies that the validator does NOT load the on-disk MissionStepContractRepository (WP05 owns that boundary).
- Reviewer verifies error codes match `contracts/validation-errors.md` exactly (case + spelling).
- Reviewer runs the full local pytest suite to confirm no regression in `tests/specify_cli/next/test_runtime_bridge_composition.py`.

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
