---
work_package_id: WP02
title: Fresh Init Schema Metadata (#840)
dependencies:
- WP01
requirement_refs:
- FR-001
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Mission base branch is fix/charter-e2e-827-tranche-2; lane worktree path/branch resolved by finalize-tasks.
subtasks:
- T008
- T009
- T010
agent: claude
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/init/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/init/**
- src/specify_cli/cli/init.py
- tests/specify_cli/init/**
- tests/specify_cli/test_init*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run `/ad-hoc-profile-load implementer-ivan` (or your equivalent skill) to apply the profile, then return here.

## Objective

Make `spec-kitty init` stamp `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` into `.kittify/metadata.yaml` at create time, using the canonical constants already defined for upgrade migrations. Eliminate the need for the E2E to bootstrap them.

Closes (in conjunction with the strict E2E gate): `#840`. Satisfies: `FR-001`, `NFR-006` (per-fix regression test).

## Context

- **Spec FR-001**: Fresh `spec-kitty init` writes `.kittify/metadata.yaml` with `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` without external bootstrap.
- **Research R6** (`research.md`): identifies the canonical schema constants and the current init metadata writer file:line.
- **Brief**: `start-here.md` "Fresh init must produce schema metadata" section.
- **Charter check**: 90%+ test coverage on new code; mypy --strict; integration tests for CLI commands.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks` from `lanes.json`. Enter via `spec-kitty agent action implement WP02 --agent <name>`.

## Subtasks

### T008 — Stamp schema_version + schema_capabilities in init metadata writer

**Purpose**: Add the two fields to the metadata `spec-kitty init` writes, reusing the upgrade-migration's canonical constants. Do not duplicate literals.

**Steps**:
1. Read research R6 for the exact source-of-truth file:line for the schema constants.
2. Locate the init metadata writer (per R6).
3. If the constants live in a place that would cause a circular import when consumed from init, extract them to a small shared module (e.g., `src/specify_cli/schema_metadata.py`) and have both init and the upgrade migration import from there.
4. Update the init writer to populate both fields when creating `.kittify/metadata.yaml`.
5. Confirm the YAML structure under `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` matches what `bundle validate`, `next`, and other consumers expect today.

**Files**:
- Source: as identified in R6 (likely `src/specify_cli/init/...` and `src/specify_cli/upgrade/migrations/...`)
- Possibly new: `src/specify_cli/schema_metadata.py` (only if extraction is needed)

**Validation**:
- After `spec-kitty init` in a temp dir, `.kittify/metadata.yaml` contains both fields.
- The values match what an existing upgraded project carries.

### T009 — Add fresh-init integration test asserting fields present

**Purpose**: Lock the fix with a targeted regression test. NFR-006 requires per-fix coverage.

**Steps**:
1. Add (or extend) a test under `tests/specify_cli/test_init*.py` (or `tests/specify_cli/init/`) following existing fresh-init test patterns.
2. The test should:
   - Use the existing temp-dir fixture (or `tmp_path`).
   - Run `git init` then invoke `spec-kitty init` via subprocess.
   - Read `.kittify/metadata.yaml`.
   - Assert `spec_kitty.schema_version` is present and matches the canonical constant.
   - Assert `spec_kitty.schema_capabilities` is present and contains the canonical capabilities (compare to constant, not hard-coded list).
3. Use `ruamel.yaml` to parse (per charter's YAML parsing convention).

**Files**:
- New or extended: `tests/specify_cli/test_init*.py` (or `tests/specify_cli/init/test_fresh_init_metadata.py`)

**Validation**:
- Test passes against the fix; fails if T008 is reverted.

### T010 — Verify upgrade-version tests still pass

**Purpose**: Ensure the canonical-constant reuse does not regress upgrade-version tests.

**Steps**:
1. Identify upgrade-version test files (likely `tests/specify_cli/upgrade/test_migration*.py` or similar — confirmed in R6).
2. Run them: `uv run pytest tests/specify_cli/upgrade -q` (adjust path per R6).
3. If any test fails because constants moved, update the import path in the test (do not change test semantics).

**Validation**:
- All upgrade-version tests pass.
- `uv run pytest tests/specify_cli -q` exits 0.
- `uv run mypy --strict src/specify_cli` exits 0.
- `uv run ruff check src tests` exits 0.

## Test Strategy

- **Per-fix regression test (T009)**: required by NFR-006.
- **Existing test sweep**: targeted gate `tests/specify_cli/` must remain green.

## Definition of Done

- [ ] `spec-kitty init` writes both schema fields into `.kittify/metadata.yaml` using canonical constants.
- [ ] No literal duplication; extraction to a shared module if needed.
- [ ] New integration test in T009 passes.
- [ ] Existing upgrade-version tests pass unchanged.
- [ ] `mypy --strict` passes on `src/specify_cli`.
- [ ] `ruff check src tests` passes.
- [ ] Owned files limited to `src/specify_cli/init/**`, `src/specify_cli/cli/init.py`, related tests, and an optional shared schema-metadata module.

## Risks

- **Circular import** when init imports constants from upgrade migrations. **Mitigation**: extract to a neutral module (`src/specify_cli/schema_metadata.py`) and have both consume from there.
- **Schema_capabilities drift**: if the canonical list is itself a moving target, ensure the test compares to the constant rather than a hard-coded list.
- **Existing init writer encodes assumptions** (e.g., metadata file-format version): update other consumers if needed and document in the WP review notes.

## Reviewer Guidance

- Confirm fields appear in a fresh-init project's `.kittify/metadata.yaml`.
- Confirm the source of the values is the canonical constant (one source of truth).
- Confirm WP02 owned-files declaration was respected.
- Confirm upgrade-version tests still green.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <your-agent-key>
```
