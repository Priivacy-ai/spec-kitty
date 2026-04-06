---
work_package_id: WP01
title: Compatibility Gate Core
dependencies: []
requirement_refs:
- FR-012
- FR-013
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase A - Foundation
assignee: ''
agent: ''
shell_pid: ''
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/core/contract_gate.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/contract_gate.py
- src/specify_cli/core/upstream_contract.json
- tests/specify_cli/core/test_contract_gate.py
---

# Work Package Prompt: WP01 – Compatibility Gate Core

## Objective

Create the central compatibility gate that validates outbound payloads against the vendored upstream 3.0.0 contract artifact before any remote-facing side effect. This WP creates the gate module and tests only — downstream WPs (WP04, WP05, WP06) insert the gate at their respective chokepoints.

## Context

The spec-kitty codebase currently has no central validation primitive for remote-facing payloads. The upstream contract (spec-kitty-events 3.0.0, spec-kitty-saas) defines required and forbidden fields for event envelopes, body sync payloads, tracker bind payloads, and orchestrator API responses. The gate must enforce these rules at runtime so that non-conformant payloads are caught before they reach an external service.

**Critical constraint (FR-023)**: The gate must NOT use hand-maintained constants or inline field lists. It must load validation rules from a vendored JSON artifact derived from the upstream contracts. If upstream evolves, only the artifact file is updated — not the gate code.

The vendored artifact already exists as a planning artifact at `kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json`. This WP copies it into the package and builds the gate around it.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json` after finalize-tasks

## Implementation

### T001: Vendor Upstream Contract Artifact

**Purpose**: Make the machine-readable 3.0.0 contract shape available at runtime.

**Steps**:
1. Copy `kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json` to `src/specify_cli/core/upstream_contract.json`
2. Ensure the file is included in the Python package (check `pyproject.toml` package-data or `MANIFEST.in` if needed)
3. The JSON structure has sections: `envelope`, `payload`, `body_sync`, `tracker_bind`, `orchestrator_api`
4. Each section defines `required_fields`, `forbidden_fields`, and optionally `allowed`/`forbidden` enumerations

**Files**: `src/specify_cli/core/upstream_contract.json`

**Validation**: File is loadable via `json.load()` and contains all expected sections.

### T002: Create ContractViolationError

**Purpose**: Typed exception for gate failures with diagnostic context.

**Steps**:
1. Create `src/specify_cli/core/contract_gate.py`
2. Define `ContractViolationError(Exception)`:
   - `field`: the offending field name
   - `context`: which surface triggered the check (e.g., "event_envelope", "body_sync")
   - `reason`: human-readable explanation (e.g., "forbidden field 'feature_slug' present in body_sync payload")
3. The `__str__` method should produce a clear diagnostic: `"ContractViolationError: {context}: {reason} (field={field})"`

**Files**: `src/specify_cli/core/contract_gate.py`

### T003: Create validate_outbound_payload()

**Purpose**: The single validation function invoked at all remote-facing chokepoints.

**Steps**:
1. In `contract_gate.py`, implement:
   ```python
   def validate_outbound_payload(payload: dict[str, Any], context: str) -> None:
   ```
2. On first call, load `upstream_contract.json` from the package (use `importlib.resources` or `Path(__file__).parent / "upstream_contract.json"`)
3. Cache the loaded JSON in a module-level variable (load once, validate many)
4. Look up the `context` key in the loaded JSON (e.g., `"envelope"`, `"body_sync"`, `"tracker_bind"`)
5. For each `forbidden_fields` entry in that section: if the key exists in `payload`, raise `ContractViolationError`
6. For each `required_fields` entry: if the key is missing from `payload`, raise `ContractViolationError`
7. For `allowed`/`forbidden` enumerations (e.g., `aggregate_type`): validate the value
8. If context is not found in the artifact, skip validation (future-proof for new surfaces)
9. If payload passes all checks, return `None` (no-op)

**Design decisions**:
- The function is synchronous (payload validation is CPU-only, no I/O)
- It raises on first violation (fail-fast)
- Context string must match a top-level key in the artifact JSON
- The gate does NOT correct payloads — it only validates and rejects

**Files**: `src/specify_cli/core/contract_gate.py`

### T004: Unit Tests — Forbidden/Required Field Validation

**Purpose**: Verify the gate correctly rejects non-conformant payloads.

**Steps**:
1. Create `tests/specify_cli/core/test_contract_gate.py`
2. Test cases for `context="envelope"`:
   - Payload with `feature_slug` → `ContractViolationError`
   - Payload with `feature_number` → `ContractViolationError`
   - Payload missing `schema_version` → `ContractViolationError`
   - Payload missing `build_id` → `ContractViolationError`
   - Payload with `aggregate_type: "Feature"` → `ContractViolationError`
3. Test cases for `context="body_sync"`:
   - Payload with `feature_slug` → `ContractViolationError`
   - Payload with `mission_key` → `ContractViolationError`
   - Payload missing `mission_slug` → `ContractViolationError`
4. Test cases for `context="tracker_bind"`:
   - Payload missing `build_id` → `ContractViolationError`
5. Test cases for `context="orchestrator_api"`:
   - Payload with `feature_slug` → `ContractViolationError`
   - Payload missing `mission_slug` → `ContractViolationError`

**Files**: `tests/specify_cli/core/test_contract_gate.py`

### T005: Unit Tests — Pass-Through Behavior

**Purpose**: Verify the gate allows valid payloads without modification.

**Steps**:
1. Valid envelope payload (all required, no forbidden) → returns None
2. Valid body_sync payload → returns None
3. Valid tracker_bind payload → returns None
4. Unknown context string → returns None (future-proof)
5. Verify gate does not mutate the payload dict
6. Verify gate performance: 1000 validations in < 50ms (NFR-003 compliance at scale)

**Files**: `tests/specify_cli/core/test_contract_gate.py`

## Definition of Done

- [ ] `upstream_contract.json` is vendored into the package and loadable at runtime
- [ ] `validate_outbound_payload()` loads rules from the artifact, not inline constants
- [ ] All forbidden field checks raise `ContractViolationError` with diagnostic context
- [ ] All required field checks raise on missing fields
- [ ] Valid payloads pass through without error or mutation
- [ ] Gate is < 5ms per invocation (NFR-003)
- [ ] mypy --strict passes on `contract_gate.py`

## Risks

- Artifact path resolution may differ between dev install and packaged install → test both
- Over-strict validation may break existing valid payloads → derive rules strictly from upstream, test with real payload shapes

## Reviewer Guidance

- Verify the gate loads from the JSON artifact, not hardcoded lists
- Verify `ContractViolationError` messages are diagnostic enough to locate the offending code
- Verify no payload mutation occurs
- Check that the artifact JSON matches `contracts/upstream-3.0.0-shape.json` exactly
