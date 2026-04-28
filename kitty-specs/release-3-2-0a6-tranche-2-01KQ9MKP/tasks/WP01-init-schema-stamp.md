---
work_package_id: WP01
title: Init stamps schema_version + schema_capabilities (#840)
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a6-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a6-tranche-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-release-3-2-0a6-tranche-2-01KQ9MKP
base_commit: 5c2f7508b91f090e31f9b21ed5d7178fbbe9eee4
created_at: '2026-04-28T09:42:49.263569+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
shell_pid: "18929"
agent: "claude:opus-4-7:default:implementer"
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/cli/commands/init.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/init.py
- src/specify_cli/migration/schema_version.py
- tests/specify_cli/cli/commands/test_init_schema_stamp.py
- tests/integration/test_init_fresh_project_chain.py
tags: []
---

# WP01 — Init stamps schema_version + schema_capabilities (#840)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Execution worktrees are allocated per computed lane in `lanes.json` after `finalize-tasks`. This WP runs in Lane A (foundation).
- Implementation command: `spec-kitty agent action implement WP01 --agent claude`

## Objective

Make `spec-kitty init` stamp `schema_version` and `schema_capabilities` into a fresh project's `.kittify/metadata.yaml` so that downstream commands (`charter setup`, `next`, etc.) work without any manual editing of that file.

## Context

GitHub issue #840. Without these fields, fresh projects fail with "missing schema" errors and operators must hand-edit the YAML. The migration runner already knows the current target schema (see `src/specify_cli/migration/schema_version.py`); this WP wires that knowledge into `init`.

**FRs covered**: FR-001, FR-002 · **NFRs**: NFR-008, NFR-002, NFR-003 · **SC**: SC-001 (component) · **Spec sections**: Scenario 1, Domain Language ("Fresh project")

## Always-true rules

- The stamp MUST be additive — operator-authored keys in an existing `metadata.yaml` are preserved byte-identical.
- Re-running `init` MUST be idempotent.
- The stamped values MUST agree with the migration runner's known target.

---

## Subtask T001 — Define schema_version + schema_capabilities canonical map

**Purpose**: Establish the single source of truth for what `init` should stamp.

**Steps**:

1. Open `src/specify_cli/migration/schema_version.py`. Identify or add:
   - `CURRENT_SCHEMA_VERSION: int` — the integer the runtime currently expects on a fresh project (use the same value the migration runner targets after a clean run).
   - `CURRENT_SCHEMA_CAPABILITIES: dict[str, bool]` — the additive map of capability flags the runtime expects to find in `metadata.yaml`. Populate from the runtime's existing capability discovery code.
2. If those names already exist with similar intent, reuse them; otherwise add them with a brief docstring tying them to issue #840.
3. Export both via `__all__` if the module uses one.

**Acceptance**:
- A single import (`from specify_cli.migration.schema_version import CURRENT_SCHEMA_VERSION, CURRENT_SCHEMA_CAPABILITIES`) reaches both values.
- The capabilities map is non-empty.

---

## Subtask T002 — Implement additive metadata.yaml stamp in `init`

**Purpose**: Have `init` produce a complete schema header on a fresh project without touching pre-existing operator keys.

**Steps**:

1. Open `src/specify_cli/cli/commands/init.py`. Locate the path that creates `.kittify/metadata.yaml` (or the helper called from it).
2. After (or as part of) writing the file, perform an **additive merge**:
   - If the file does not exist: create it with `schema_version: <CURRENT_SCHEMA_VERSION>` and `schema_capabilities: <CURRENT_SCHEMA_CAPABILITIES>`.
   - If the file exists and lacks `schema_version`: insert it at the top of the document (using ruamel.yaml round-trip mode to preserve formatting and comments).
   - If the file exists and lacks `schema_capabilities`: insert it as a top-level mapping; do not merge values into an existing capabilities map without explicit operator action.
   - **Never** overwrite an existing `schema_version` or existing keys inside `schema_capabilities`.
3. Use `ruamel.yaml` round-trip parsing to preserve operator-authored keys, comments, and ordering.

**Files to edit**:
- `src/specify_cli/cli/commands/init.py` (+~40 lines)

**Validation hooks**:
- After `init`, `yaml.safe_load(open(path))` returns a dict containing both `schema_version` and `schema_capabilities`.

---

## Subtask T003 — Idempotency + operator-key preservation

**Purpose**: Prove that re-running `init` is a no-op for content and that operator-authored keys survive.

**Steps**:

1. Add a guard near the merge logic: if both schema fields are already present and equal to the canonical values, return early without writing the file.
2. If only one is present, only insert the missing one; do not rewrite the present one.
3. Confirm the merge respects existing comments and key ordering for non-schema keys.

**Acceptance**:
- Running `init` twice on the same directory produces a file whose content is byte-identical between runs (allowing for any unrelated runtime-managed timestamps already in the file, if any — those should not be touched here).

---

## Subtask T004 — Unit tests: empty dir, hand-edited file, idempotency  [P]

**Purpose**: Lock in the additive-merge contract.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_init_schema_stamp.py`. Add tests:
   - `test_fresh_dir_gets_both_schema_fields`: `init` on `tmp_path`, assert `metadata.yaml` contains `schema_version == CURRENT_SCHEMA_VERSION` and `schema_capabilities` equals the canonical map.
   - `test_existing_metadata_with_operator_keys_preserved`: pre-create `.kittify/metadata.yaml` with `{my_custom_key: "custom_value"}`; run `init`; assert `my_custom_key == "custom_value"` and the schema fields are present.
   - `test_existing_schema_version_not_overwritten`: pre-create with `schema_version: <some-other-int>`; run `init`; assert that integer is unchanged.
   - `test_idempotent_init`: run `init` twice; assert file content equal across the two runs.

**Files to create**:
- `tests/specify_cli/cli/commands/test_init_schema_stamp.py` (~120 lines)

**Coverage target**: ≥ 90% on `init.py` schema-stamp paths.

---

## Subtask T005 — Integration test: init then `next` runs without missing-schema errors

**Purpose**: Show the fresh-project chain past the immediate fix.

**Steps**:

1. Create `tests/integration/test_init_fresh_project_chain.py` (or extend the closest existing integration suite).
2. Add `test_init_then_next_no_missing_schema_error`:
   - Use the existing CLI runner fixture.
   - In a `tmp_path`, run `spec-kitty init`.
   - Run `spec-kitty next` (or the smallest invocation that would trip "missing schema" today). Assert exit code 0 and stderr does not contain a `missing schema` style message.
3. Use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` if any subcommand under test touches sync paths (per C-003).

**Files to create**:
- `tests/integration/test_init_fresh_project_chain.py` (~80 lines)

---

## Subtask T006 — Defer CHANGELOG entry to WP07  [P]

**Purpose**: Keep CHANGELOG ownership consolidated.

**Steps**:

1. **Do not edit `CHANGELOG.md`** from this WP — it is owned by WP07 (the capstone tranche-summary entry covers all seven issues including #840).
2. Add a one-line note in the PR description referencing WP07's CHANGELOG entry as the owner of this user-visible change.

---

## Test Strategy

- **Unit**: T004 covers the additive-merge surface at all three branches (fresh, partial existing, complete existing).
- **Integration**: T005 proves the downstream chain unblocks.
- **mypy --strict**: must pass on `init.py` and `schema_version.py`.
- **Coverage**: ≥ 90% on changed lines (NFR-002).

## Definition of Done

- [ ] T001 — canonical map exposed in `migration/schema_version.py`.
- [ ] T002 — `init.py` performs additive merge.
- [ ] T003 — idempotent on second run.
- [ ] T004 — unit tests pass and cover ≥ 90% of changed lines.
- [ ] T005 — integration test passes with `init → next` clean.
- [ ] T006 — CHANGELOG ownership deferred to WP07 (no edits from this WP).
- [ ] `mypy --strict` clean on touched modules.
- [ ] No new top-level dependencies (SC-008).
- [ ] No changes to mission identity fields (C-004).

## Risks

- **Risk**: Overwriting an operator's hand-edited `metadata.yaml` keys.
  **Mitigation**: ruamel.yaml round-trip + explicit "never overwrite" guard. T004 hand-edited test.
- **Risk**: Drift between `init` stamped value and migration runner's expected value.
  **Mitigation**: Both read the same constant from `migration/schema_version.py`.

## Reviewer guidance

- Verify the file-merge code path uses ruamel.yaml round-trip (preserves comments, key order).
- Check there is exactly **one** source of truth for `CURRENT_SCHEMA_VERSION` and `CURRENT_SCHEMA_CAPABILITIES`.
- Confirm idempotency: re-running `init` on a project that already has both fields produces no diff.
- Confirm the integration test does not touch SaaS without `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (or otherwise gates SaaS calls).

## Out of scope

- Migrating existing projects (covered by the migration runner separately).
- Any change to schema versions on already-initialized projects.
- Adding new capabilities to the canonical map beyond what the runtime already requires.

## Activity Log

- 2026-04-28T09:42:50Z – claude:opus-4-7:default:implementer – shell_pid=18929 – Assigned agent via action command
