---
work_package_id: WP12
title: Canonical Field Rollout and feature_* Compat Gating (Scope B)
dependencies:
- WP11
requirement_refs:
- FR-014
- FR-015
- FR-017
- FR-018
- FR-019
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
- T056
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/specify_cli/agent/**
- src/specify_cli/status/**
- src/specify_cli/next/**
- tests/contract/test_machine_facing_canonical_fields.py
priority: P1
tags: []
---

# WP12 — Canonical Field Rollout and `feature_*` Compat Gating (Scope B)

> ⚠️ **GATED**: This WP cannot start until WP11 (Scope B inventory) is complete. WP11 itself depends on WP10 (Scope A acceptance).
>
> ⚠️ **OWNED FILES SUBJECT TO REVISION**: The exact `owned_files` glob list above is a placeholder. The WP11 inventory determines the precise files this WP needs to touch. After WP11 is complete, update the `owned_files` field to match the actual surfaces identified, then re-run `spec-kitty agent mission finalize-tasks --validate-only` to confirm no ownership conflicts.

## Objective

For every first-party machine-facing payload identified in WP11, ensure `mission_slug`, `mission_number`, and `mission_type` are present and canonical. For each residual `feature_*` field, execute the remove/dual-write/deprecate decision from the WP11 alignment plan. Add contract tests that lock the canonical state.

This satisfies FR-014 through FR-020 from spec §10.2.

## Context

Scope B's behavior changes are mostly mechanical once the inventory is in hand. The constraints (C-008, C-009, C-010, and the §3.3 non-goals) prevent any architectural changes — this is a field-naming alignment, not a redesign.

**Locked**:
- No `mission_run_slug` (C-009)
- No `MissionRunCreated` rename (§3.3)
- No `MissionRunClosed` rename (§3.3)
- No `aggregate_type="MissionRun"` (§3.3)
- No `kitty-specs/<slug>/` directory rename (FR-020)
- No widening of the orchestrator-api envelope (C-010)

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP12` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T051 — Ensure canonical fields present in first-party payloads

**Purpose**: For every surface identified in the WP11 inventory, ensure `mission_slug`, `mission_number`, and `mission_type` are emitted as canonical fields.

**Steps**:
1. Read `kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md` (from WP11).
2. For each surface in the inventory that does NOT currently emit the canonical fields, add them.
3. Make sure existing tests still pass — adding fields is a non-breaking change for consumers that ignore unknown fields, but a breaking change for consumers with strict schemas.

### T052 — Execute remove/dual-write/deprecate decisions for `feature_*` fields

**Purpose**: Apply the per-field decisions from the WP11 alignment plan.

**Steps**:
1. For each field with **remove** decision: delete the field emit from the producing function. Update any consumer reading the field to read the canonical replacement.
2. For each field with **dual-write** decision: keep emitting the legacy field alongside the canonical field. Add a comment referencing the WP11 alignment plan and the named removal date (if any).
3. For each field with **deprecate** decision: keep the field but add a code-level deprecation marker (docstring + future-removal note). Add a contract test that fails if the field is read-without-warning.

### T053 — Add contract tests asserting canonical fields are present

**Purpose**: Lock the canonical state via tests.

**Steps**:
1. Create `tests/contract/test_machine_facing_canonical_fields.py`:
   ```python
   """Contract tests for canonical mission identity fields in machine-facing payloads.

   Authority: spec FR-014, FR-015, spec §10.2 acceptance gates 1-2.
   """
   import pytest

   # For each surface in scope-b-inventory.md:
   def test_<surface>_emits_canonical_mission_fields():
       """The <surface> payload must include mission_slug, mission_number, mission_type."""
       payload = ...  # invoke the surface
       assert "mission_slug" in payload
       assert "mission_number" in payload
       assert "mission_type" in payload
   ```

2. Add one test per surface in the inventory.

### T054 — Add contract test that fails if `mission_run_slug` is introduced (FR-019)

**Purpose**: Lock the C-009 / FR-019 non-goal.

**Steps**:
1. Add to `test_machine_facing_canonical_fields.py`:
   ```python
   def test_no_mission_run_slug_in_first_party_payloads():
       """No first-party machine-facing payload may introduce mission_run_slug.

       Authority: C-009, FR-019, locked non-goal §3.3.
       """
       # Search src/specify_cli/ for any string literal "mission_run_slug"
       from pathlib import Path
       repo_root = Path(__file__).resolve().parents[2]
       offending = []
       for path in repo_root.glob("src/specify_cli/**/*.py"):
           content = path.read_text(encoding="utf-8")
           if "mission_run_slug" in content:
               offending.append(str(path.relative_to(repo_root)))
       assert not offending, f"mission_run_slug introduced in: {offending}. Forbidden by C-009/FR-019."
   ```

### T055 — Verify `MissionCreated`/`MissionClosed` event names unchanged (FR-017)

**Purpose**: Lock the §3.3 non-goal that catalog event names are not renamed.

**Steps**:
1. Add to `test_machine_facing_canonical_fields.py`:
   ```python
   def test_mission_created_and_closed_event_names_unchanged():
       """The canonical catalog event names must not be renamed.

       Authority: FR-017, locked non-goal §3.3.
       """
       from pathlib import Path
       repo_root = Path(__file__).resolve().parents[2]
       # Look for any rename to MissionRunCreated or MissionRunClosed
       offending = []
       for path in repo_root.glob("src/specify_cli/**/*.py"):
           content = path.read_text(encoding="utf-8")
           if "MissionRunCreated" in content or "MissionRunClosed" in content:
               offending.append(str(path.relative_to(repo_root)))
       assert not offending, f"MissionRun* catalog event rename detected in: {offending}. Forbidden by FR-017/§3.3."
   ```

### T056 — Verify `aggregate_type="Mission"` unchanged (locked non-goal §3.3)

**Purpose**: Lock the §3.3 non-goal that aggregate type is not changed.

**Steps**:
1. Add to `test_machine_facing_canonical_fields.py`:
   ```python
   def test_aggregate_type_mission_unchanged():
       """aggregate_type must remain 'Mission'; no rename to 'MissionRun'.

       Authority: locked non-goal §3.3.
       """
       from pathlib import Path
       repo_root = Path(__file__).resolve().parents[2]
       offending = []
       for path in repo_root.glob("src/specify_cli/**/*.py"):
           content = path.read_text(encoding="utf-8")
           if 'aggregate_type="MissionRun"' in content or "aggregate_type='MissionRun'" in content:
               offending.append(str(path.relative_to(repo_root)))
       assert not offending, f"aggregate_type renamed to MissionRun in: {offending}. Forbidden by §3.3."
   ```

2. Run the full Scope B contract test suite:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_machine_facing_canonical_fields.py -v
   ```

## Files Touched

The exact files are determined by the WP11 inventory. Likely candidates:
- Files under `src/specify_cli/agent/`, `src/specify_cli/status/`, `src/specify_cli/next/` that emit machine-facing JSON
- New: `tests/contract/test_machine_facing_canonical_fields.py`

**Out of bounds**:
- `src/specify_cli/orchestrator_api/**` (C-010 — no widening)
- `src/specify_cli/core/upstream_contract.json` orchestrator_api section (out of scope)
- Any directory under `kitty-specs/**` other than this mission's
- Any directory under `architecture/**`

## Definition of Done

- [ ] Every surface in the WP11 inventory now emits `mission_slug`, `mission_number`, `mission_type` as canonical
- [ ] Every residual `feature_*` field has the WP11 decision applied (remove/dual-write/deprecate)
- [ ] All four contract tests in `test_machine_facing_canonical_fields.py` pass:
  - canonical fields present per surface
  - no `mission_run_slug` anywhere (FR-019)
  - no `MissionRun*` event rename (FR-017)
  - no `aggregate_type="MissionRun"` (§3.3)
- [ ] No file under `src/specify_cli/orchestrator_api/` is modified
- [ ] No file under `kitty-specs/**` (other than this mission) or `architecture/**` is modified
- [ ] mypy --strict is clean on all modified files
- [ ] Existing tests still pass (no regression in machine-facing consumer tests)

## Risks and Reviewer Guidance

**Risks**:
- A consumer with a strict schema may break when canonical fields are added. Run the cross-repo consumer fixtures from WP13 before declaring done.
- The dual-write decision for some fields means the field name appears in both the canonical and legacy positions. Don't accidentally remove the canonical-side write while removing the legacy-side write.
- This WP's owned_files glob is broad (`src/specify_cli/agent/**` etc.). The WP11 inventory should narrow it to specific files before this WP is finalized — coordinate with the planner if needed.

**Reviewer checklist**:
- [ ] Every change traces back to a row in `scope-b-inventory.md`
- [ ] Locked non-goals (C-009, FR-017, FR-019, §3.3) are enforced by contract tests
- [ ] Orchestrator-api files unchanged
- [ ] Scope-A acceptance evidence (`scope-a-acceptance.md`) is referenced as the precondition

## Implementation Command

```bash
spec-kitty implement WP12
```

This WP depends on WP11. Do not start until WP11 is merged on `main`.

## References

- Spec FR-014..FR-020
- Spec §3.3 — Locked non-goals
- Spec §10.2 — Scope B acceptance criteria
- WP11 inventory document
- `src/specify_cli/core/upstream_contract.json`
