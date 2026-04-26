---
work_package_id: WP02
title: Shipped Step Contracts
dependencies: []
requirement_refs:
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
- T009
- T010
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: src/doctrine/mission_step_contracts/shipped/
execution_mode: code_change
owned_files:
- src/doctrine/mission_step_contracts/shipped/documentation-discover.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/documentation-audit.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/documentation-design.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/documentation-generate.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/documentation-validate.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/documentation-publish.step-contract.yaml
- tests/specify_cli/mission_step_contracts/test_documentation_composition.py
tags: []
---

# WP02 — Shipped Step Contracts

## Objective

Author 6 step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml` mirroring the research contracts. Author a parametrized test that loads all 6 and asserts schema invariants. Per spec C-009, contracts MUST NOT add `expected_artifacts` or any other new top-level field.

## Context

The contract schema is identical to the existing research contracts (`src/doctrine/mission_step_contracts/shipped/research-*.step-contract.yaml`). Each contract is a delegation record; it is consumed by the `StepContractExecutor` which composes the action via the profile binding. Contracts MUST NOT become model runners or text generators (C-009).

Reference: [contracts/step-contracts.md](../contracts/step-contracts.md) gives a one-paragraph spec for each of the 6 contracts.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: enter via `spec-kitty agent action implement WP02 --agent <name>`. Lane assigned by `finalize-tasks`.

## Subtasks

### T004 — `documentation-discover.step-contract.yaml`

**Purpose**: ship the discover-action delegation contract.

**Steps**:
1. Read `src/doctrine/mission_step_contracts/shipped/research-scoping.step-contract.yaml` end-to-end as the template.
2. Author `src/doctrine/mission_step_contracts/shipped/documentation-discover.step-contract.yaml`:

   ```yaml
   schema_version: "1.0"
   id: documentation-discover
   action: discover
   mission: documentation
   steps:
     - id: bootstrap
       description: Load charter context for this action
       command: "spec-kitty charter context --action discover --role discover --json"
       inputs:
         - flag: --profile
           source: wp.agent_profile
           optional: true
         - flag: --tool
           source: env.agent_tool
           optional: true

     - id: capture_documentation_needs
       description: Capture target audience, iteration mode, and goals; emit spec.md
       delegates_to:
         kind: directive
         candidates:
           - 010-specification-fidelity-requirement
           - 003-decision-documentation-requirement

     - id: validate_scope
       description: Validate documentation scope boundaries and feasibility
       delegates_to:
         kind: tactic
         candidates:
           - requirements-validation-workflow

     - id: write_spec
       description: Write spec.md to kitty-specs/{mission_slug}/
       command: "Write spec.md in kitty-specs/{mission_slug}/"

     - id: commit_spec
       description: Commit the documentation spec to main branch
       delegates_to:
         kind: directive
         candidates:
           - 029-agent-commit-signing-policy
           - 033-targeted-staging-policy
   ```

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-discover.step-contract.yaml` (new, ~35 lines).

**Validation**:
- [ ] YAML parses.
- [ ] Top-level keys: only `schema_version`, `id`, `action`, `mission`, `steps`. No `expected_artifacts`.
- [ ] `id == "documentation-discover"`, `action == "discover"`, `mission == "documentation"`.

### T005 — `documentation-audit.step-contract.yaml`

Same shape as T004 with these differences:
- `id: documentation-audit`, `action: audit`.
- Bootstrap command: `--action audit --role audit`.
- Capture step renamed `inventory_existing_docs`; description: "Inventory existing documentation surfaces and prior coverage". Delegates to directive: `037-living-documentation-sync`.
- Validate step renamed `identify_gaps`; delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write gap-analysis.md in kitty-specs/{mission_slug}/`.
- Commit step: same as T004.

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-audit.step-contract.yaml` (new, ~35 lines).

### T006 — `documentation-design.step-contract.yaml`

- `id: documentation-design`, `action: design`.
- Bootstrap: `--action design --role design`.
- Step `plan_divio_types`: delegates to directive `001-architectural-integrity-standard`.
- Step `architecture_decision`: delegates to tactic `adr-drafting-workflow`.
- Step `validate_design`: delegates to tactic `requirements-validation-workflow`.
- Write step: `Write plan.md in kitty-specs/{mission_slug}/`.
- Commit step same as T004.

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-design.step-contract.yaml` (new, ~40 lines).

### T007 — `documentation-generate.step-contract.yaml`

- `id: documentation-generate`, `action: generate`.
- Bootstrap: `--action generate --role generate`.
- Step `produce_artifacts`: delegates to directive `010-specification-fidelity-requirement`.
- Step `living_doc_sync`: delegates to directive `037-living-documentation-sync`.
- Step `validate_output`: delegates to tactic `requirements-validation-workflow`.
- Write step: `Write docs/**/*.md under kitty-specs/{mission_slug}/`.
- Commit step same as T004.

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-generate.step-contract.yaml` (new, ~40 lines).

### T008 — `documentation-validate.step-contract.yaml`

- `id: documentation-validate`, `action: validate`.
- Bootstrap: `--action validate --role validate`.
- Step `quality_gates`: delegates to directive `010-specification-fidelity-requirement`.
- Step `risk_review`: delegates to tactic `premortem-risk-identification`.
- Step `validate_against_spec`: delegates to tactic `requirements-validation-workflow`.
- Write step: `Write audit-report.md in kitty-specs/{mission_slug}/`.
- Commit step same as T004.

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-validate.step-contract.yaml` (new, ~40 lines).

### T009 — `documentation-publish.step-contract.yaml`

- `id: documentation-publish`, `action: publish`.
- Bootstrap: `--action publish --role publish`.
- Step `living_doc_sync`: delegates to directive `037-living-documentation-sync`.
- Step `specification_fidelity`: delegates to directive `010-specification-fidelity-requirement`.
- Step `final_validation`: delegates to tactic `requirements-validation-workflow`.
- Write step: `Write release.md in kitty-specs/{mission_slug}/`.
- Commit step same as T004.

**Files**: `src/doctrine/mission_step_contracts/shipped/documentation-publish.step-contract.yaml` (new, ~40 lines).

### T010 — Parametrized contract structure test

**Purpose**: pin all 6 contracts via a parametrized test that asserts schema invariants (FR-015, C-009). The profile-defaults assertion is owned by WP05's test file, not this one — WP02 must not import from `executor.py` because that module is WP05's authoritative surface.

**Steps**:
1. Create `tests/specify_cli/mission_step_contracts/test_documentation_composition.py`.
2. Author the test:

   ```python
   """Parametrized structure tests for documentation mission step contracts (#502).

   Owned by WP02. The profile-default assertion (FR-016) lives in WP05's
   tests/specify_cli/next/test_runtime_bridge_documentation_composition.py
   because executor._ACTION_PROFILE_DEFAULTS is WP05's authoritative surface.
   """

   from __future__ import annotations

   from pathlib import Path

   import pytest
   import yaml

   _DOC_ACTIONS = ["discover", "audit", "design", "generate", "validate", "publish"]
   _SHIPPED = (
       Path(__file__).resolve().parents[3]
       / "src"
       / "doctrine"
       / "mission_step_contracts"
       / "shipped"
   )


   @pytest.mark.parametrize("action", _DOC_ACTIONS)
   def test_contract_loads_with_correct_keys(action: str) -> None:
       path = _SHIPPED / f"documentation-{action}.step-contract.yaml"
       assert path.is_file(), f"contract missing: {path}"
       data = yaml.safe_load(path.read_text(encoding="utf-8"))

       # Top-level keys (C-009 — no expected_artifacts).
       allowed_top = {"schema_version", "id", "action", "mission", "steps"}
       assert set(data.keys()) <= allowed_top, (
           f"unexpected top-level keys: {set(data.keys()) - allowed_top}"
       )
       assert data["id"] == f"documentation-{action}"
       assert data["action"] == action
       assert data["mission"] == "documentation"
       assert isinstance(data["steps"], list) and len(data["steps"]) >= 4

       # No expected_artifacts on any step (C-009).
       for step in data["steps"]:
           assert "expected_artifacts" not in step, (
               f"step {step.get('id')} has forbidden expected_artifacts key"
           )
   ```

3. Run: `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/mission_step_contracts/test_documentation_composition.py -v`.

**Files**: `tests/specify_cli/mission_step_contracts/test_documentation_composition.py` (new, ~50 lines).

**Validation**:
- [ ] All 6 parametrized tests pass.
- [ ] No mocks; the test uses pure file IO + YAML.
- [ ] No imports from `specify_cli.mission_step_contracts.executor` (that module is WP05's authoritative surface).

## Definition of Done

- [ ] T004-T009 — six YAML files exist, each with the correct `id`/`action`/`mission` keys and no `expected_artifacts`.
- [ ] T010 — `test_documentation_composition.py` passes 12 parametrized cases.
- [ ] `ruff check tests/specify_cli/mission_step_contracts/test_documentation_composition.py` passes cleanly.
- [ ] `mypy --strict tests/specify_cli/mission_step_contracts/test_documentation_composition.py` passes.

## Risks

1. The contract loader (or a separate validator) may require additional fields not visible from the research contract shape (e.g. a `version:` key). Mitigation — copy `research-scoping.step-contract.yaml` shape exactly; if loading fails, inspect the loader's required fields.
2. The `delegates_to.candidates` slugs must match existing directives/tactics or the validated DRG load (in WP04) will reject them. Mitigation — only reference directives/tactics already present in `src/doctrine/graph.yaml` (DIRECTIVE_001/003/010/037 and tactics `requirements-validation-workflow`, `premortem-risk-identification`, `adr-drafting-workflow`, `living-documentation-sync` — verify in graph.yaml before authoring).

## Reviewer Guidance

- Verify each YAML's `id` exactly matches `documentation-<action>` (basename minus `.step-contract.yaml`).
- Verify no `expected_artifacts` key anywhere (grep all 6 YAMLs).
- Verify the parametrized test parametrizes over exactly 6 actions in alphabetical or workflow order.
- Verify the test file is under `tests/specify_cli/mission_step_contracts/` (matches the existing research test path).
