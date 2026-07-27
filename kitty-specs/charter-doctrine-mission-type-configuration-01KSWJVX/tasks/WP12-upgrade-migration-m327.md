---
work_package_id: WP12
title: FR-019 upgrade migration m_3_2_7_activate_builtin_mission_types
dependencies:
- WP11
requirement_refs:
- FR-019
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: ca44e812b575bfc32602d596b34f106b81c28f5a
created_at: '2026-05-30T20:32:42.818622+00:00'
subtasks:
- T071
- T072
- T073
- T074
- T075
- T076
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3348036"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/m_3_2_7_activate_builtin_mission_types.py
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_7_activate_builtin_mission_types.py
- src/specify_cli/upgrade/migrations/__init__.py
- tests/upgrade/test_activate_builtin_types_migration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP12 — FR-019 upgrade migration m_3_2_7_activate_builtin_mission_types

## Context

FR-019: After this mission, DRG traversal is activation-filtered (FR-018). Existing projects that pre-date this mission have no explicit mission-type activation entries in their charter. Without a migration, upgrading would silently make all mission types invisible to charter-mediated resolution — breaking every existing project.

The `m_3_2_7` migration ensures existing projects automatically get all four built-in mission types activated in their charter, preserving all existing functionality after upgrade.

## Objective

Implement `m_3_2_7_activate_builtin_mission_types.py` following the established migration pattern from `m_3_2_6_charter_bundle_v2.py`. Register it in the migration registry. Write idempotency and dry-run tests.

## Migration Logic

```
For each project-level .kittify/config.yaml:
  If the config has NO explicit mission_type activation entries:
    Add mission_type_activations: [software-dev, documentation, research, plan]
  Else:
    Leave existing entries untouched (idempotent)
```

The migration is additive only: it never removes or replaces existing configuration.

## Subtasks

### T071 — Create the migration file

Create `src/specify_cli/upgrade/migrations/m_3_2_7_activate_builtin_mission_types.py`.

Read `src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py` to understand the established pattern:
- Class inheriting from the migration base class
- `version` property
- `apply(project_path: Path, dry_run: bool = False) -> MigrationResult` method
- `description` property

Copy the class structure; do not copy the `m_3_2_6` logic.

### T072 — Migration logic: detect and add activation entries

**First, verify the config key**. Before implementing, read the actual `.kittify/config.yaml` from a real project and/or search the codebase for `mission_type_activations` to confirm this is the correct YAML key. Also read `src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py` and `src/charter/pack_context.py` (WP06) to confirm the key expected by `PackContext.from_config()`.

If the key name differs (e.g., `mission_types` or `activated_mission_types`), use the key that `PackContext.from_config()` actually reads — consistency between the migration writer and the runtime reader is critical.

**Cross-check with WP03**: The built-in type IDs written by this migration must exactly match the IDs of the `MissionType` YAML files created by WP03 (`src/doctrine/missions/mission_types/`). Read those filenames to get the canonical list rather than hardcoding strings:
- If WP03 is merged: read `src/doctrine/missions/mission_types/*.yaml` and collect `id:` values
- If WP03 is not yet merged: use the known list `["software-dev", "documentation", "research", "plan"]` but add a test that verifies this list matches WP03's output once both are merged

In `apply()`:

```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    config_path = project_path / ".kittify" / "config.yaml"

    if not config_path.exists():
        return MigrationResult(applied=False, reason="No .kittify/config.yaml found")

    config = ruamel_yaml.load(config_path.read_text())

    # Check if mission_type activation entries already exist
    # NOTE: verify `mission_type_activations` is the actual key per PackContext.from_config()
    if "mission_type_activations" in config and config["mission_type_activations"]:
        return MigrationResult(applied=False, reason="Mission type activations already present")

    builtin_types = ["software-dev", "documentation", "research", "plan"]

    if not dry_run:
        config["mission_type_activations"] = builtin_types
        config_path.write_text(ruamel_yaml.dump(config))

    return MigrationResult(
        applied=True,
        changes=[f"Added mission_type_activations: {builtin_types}"],
        dry_run=dry_run,
    )
```

(Adjust field/class names to match the actual migration base class and result type.)

### T073 — Preserve existing charter configuration

The migration must:
- **Never** overwrite existing `mission_type_activations` if present
- **Never** remove other config sections (preserve `agents`, `org_packs`, `interview_defaults`, etc.)
- Use `ruamel.yaml` (not `yaml.safe_load`) to preserve YAML formatting and comments

Verify that a config with `agents: available: [claude, opencode]` still has those entries after the migration.

### T074 — Use get_agent_dirs_for_project() pattern

Per CLAUDE.md: migrations that update slash commands must use `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration`. 

This migration does not write to agent directories (it updates config.yaml), so `get_agent_dirs_for_project()` may not be needed. However, if the migration also needs to notify or touch agent directories, use the helper.

Read `m_3_2_6_charter_bundle_v2.py` to see if it uses `get_agent_dirs_for_project()` and follow the same pattern.

### T075 — Register migration in the registry

Open the migration registry file (likely `src/specify_cli/upgrade/migrations/__init__.py` or a `MIGRATIONS` list in another file). Add `m_3_2_7_activate_builtin_mission_types` in version order after `m_3_2_6`.

Follow the exact pattern used to register `m_3_2_6`.

### T076 — Tests for the migration

Write `tests/upgrade/test_activate_builtin_types_migration.py`:

Test cases:
- **Migration on project without mission-type entries**: adds all four built-ins; `config.yaml` now has `mission_type_activations: [software-dev, documentation, research, plan]`
- **Migration on project with existing entries**: `mission_type_activations: [software-dev]` already set; migration is idempotent; does not add or change entries
- **Existing config preserved**: other config sections (agents, org_packs) are untouched
- **Dry-run mode**: `apply(..., dry_run=True)` returns `applied=True` with changes listed but does not write to disk
- **No config.yaml**: migration gracefully returns `applied=False`
- **YAML formatting preserved**: ruamel.yaml round-trip does not destroy comments or formatting

## Acceptance Criteria

- [ ] `m_3_2_7_activate_builtin_mission_types.py` exists and follows the established migration pattern
- [ ] Migration adds `mission_type_activations` with all four built-in types when absent
- [ ] Migration is idempotent when entries already exist
- [ ] Dry-run mode does not write to disk
- [ ] Migration registered in the migration registry
- [ ] All tests pass including idempotency and dry-run tests
- [ ] `mypy --strict` clean

## References

- FR-019: Upgrade migration requirement
- research.md §"Research Task 4" — migration version slot (m_3_2_7)
- CLAUDE.md §"Agent Management Best Practices" — get_agent_dirs_for_project() pattern
- `m_3_2_6_charter_bundle_v2.py` — reference implementation pattern

## Activity Log

- 2026-05-30T20:32:43Z – claude:sonnet:python-pedro:implementer – shell_pid=3323919 – Assigned agent via action command
- 2026-05-30T20:37:30Z – claude:sonnet:python-pedro:implementer – shell_pid=3323919 – Ready for review: m_3_2_7 migration adds mission_type_activations for legacy projects; 17 tests pass, lint clean
- 2026-05-30T20:37:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=3348036 – Started review via action command
