---
work_package_id: WP08
title: Profile-Context Upgrade Migration
lane: planned
dependencies: [WP07]
requirement_refs:
- FR-010
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
phase: Phase C - Init-Time Doctrine
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP08 – Profile-Context Upgrade Migration

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP07** (Phase C sequential).

```bash
spec-kitty implement WP08 --base WP07
```

---

## Objectives & Success Criteria

- `spec-kitty upgrade` deploys `spec-kitty.profile-context.md` to all configured agent command directories.
- Migration skips unconfigured agents (respects `.kittify/config.yaml`).
- Migration is idempotent — running upgrade twice does not duplicate or corrupt the template.
- Missing agent directory is skipped (user deletion respected).
- All 4 ATDD scenarios pass.
- Requirements FR-010, SC-004, C-003 satisfied.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-C2
- **Spec**: US-4, FR-010, SC-004, C-003
- **Template source**: `src/doctrine/templates/command-templates/profile-context.md` (already exists)
- **Template destination filename**: `spec-kitty.profile-context.md` (consistent with other commands)
- **Config-aware helper**: `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration`
- **Pattern to follow**: `src/specify_cli/upgrade/migrations/m_2_0_11_install_skills.py`
- **Start command**: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### Subtask T033 – Write ATDD acceptance tests (tests first)

- **Purpose**: 4 US-4 scenarios must fail before the migration exists.
- **Files**: Create `tests/specify_cli/test_profile_context_migration.py`.
- **Steps**:
  1. Study `tests/specify_cli/test_agent_config_migration.py` and similar migration tests for patterns (tmp_path fixture, config setup, migration.apply() call).
  2. Write 4 test functions:
     - `test_migration_deploys_to_configured_agents` — configure claude + opencode, run migration, confirm `spec-kitty.profile-context.md` exists in both agent command dirs.
     - `test_migration_skips_unconfigured_agents` — configure only opencode, run migration, confirm `.claude/commands/spec-kitty.profile-context.md` does NOT exist.
     - `test_migration_idempotent` — run migration twice on same project, confirm no error and no duplicate files.
     - `test_migration_skips_missing_directory` — agent is configured but directory was manually deleted, run migration → no error, no directory created.
  3. Run `pytest tests/specify_cli/test_profile_context_migration.py -v` — all must FAIL.

### Subtask T034 – Create migration file

- **Purpose**: The migration deploys `profile-context.md` to all configured agents during `spec-kitty upgrade`.
- **Files**: Create `src/specify_cli/upgrade/migrations/m_2_2_0_profile_context_deployment.py`.
- **Steps**:
  1. Read `m_2_0_11_install_skills.py` fully for the pattern.
  2. Create the migration:
     ```python
     """Migration: deploy profile-context command template to configured agents.

     Adds the /spec-kitty.profile-context slash command to all configured agent
     command directories, enabling agents to load specialist profiles for advisory sessions.
     """
     from __future__ import annotations
     import shutil
     from pathlib import Path

     from ..registry import MigrationRegistry
     from .base import BaseMigration, MigrationResult
     from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project


     @MigrationRegistry.register
     class ProfileContextDeploymentMigration(BaseMigration):
         """Deploy profile-context command template to configured agent directories."""

         version = "2.2.0"
         name = "profile_context_deployment"
         description = "Deploy /spec-kitty.profile-context slash command to configured agents"

         def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
             template_source = self._get_template_source()
             if not template_source.exists():
                 return MigrationResult(success=False, message=f"Template not found: {template_source}")

             agent_dirs = get_agent_dirs_for_project(project_path)
             deployed = []
             skipped = []

             for agent_root, subdir in agent_dirs:
                 agent_dir = project_path / agent_root / subdir
                 if not agent_dir.exists():
                     skipped.append(str(agent_root))
                     continue

                 dest = agent_dir / "spec-kitty.profile-context.md"
                 if not dry_run:
                     shutil.copy2(template_source, dest)
                 deployed.append(str(dest.relative_to(project_path)))

             msg = f"Deployed to {len(deployed)} agents" + (f" (skipped {len(skipped)})" if skipped else "")
             return MigrationResult(success=True, message=msg, changes=deployed)

         def _get_template_source(self) -> Path:
             from specify_cli.core.assets import get_package_asset_root
             asset_root = get_package_asset_root()
             return asset_root / "templates" / "command-templates" / "profile-context.md"
     ```
  3. Adjust imports and `get_package_asset_root()` call to match the actual pattern used in other migrations.

### Subtask T035 – Make migration idempotent

- **Purpose**: Running `spec-kitty upgrade` multiple times must not break anything.
- **Files**: `src/specify_cli/upgrade/migrations/m_2_2_0_profile_context_deployment.py`
- **Steps**:
  1. In the `apply()` method, before copying, check if the destination already exists AND has the same content:
     ```python
     if dest.exists():
         if dest.read_text() == template_source.read_text():
             skipped.append(str(dest.relative_to(project_path)))
             continue
         # Content differs — overwrite (template was updated)
     ```
  2. This ensures: first run deploys, subsequent runs are no-ops if content matches, and re-deploys if the template was updated.

### Subtask T036 – Register migration and verify it runs

- **Purpose**: The migration must be discovered by the upgrade system's autodiscovery mechanism.
- **Files**: `src/specify_cli/upgrade/migrations/__init__.py` (verify autodiscovery picks up the new file).
- **Steps**:
  1. Read `__init__.py` in the migrations directory. It uses autodiscovery (imports all `m_*.py` files in the directory). No manual registration step should be needed if the file follows the `m_{version}_{name}.py` naming convention and uses `@MigrationRegistry.register`.
  2. Verify: `python -c "from specify_cli.upgrade.migrations import load_all_migrations; migrations = load_all_migrations(); print([m.name for m in migrations])"` — should include `profile_context_deployment`.
  3. Run `pytest tests/specify_cli/test_profile_context_migration.py -v` — all 4 tests should now pass (green).
  4. Run `pytest tests/ -x` — full suite must pass.

## Test Strategy

```bash
# ATDD acceptance tests
rtk test pytest tests/specify_cli/test_profile_context_migration.py -v

# Full suite regression
rtk test pytest tests/ -x

# Coverage gate (90%+ on new modules — constitution requirement)
rtk test pytest tests/ --cov=specify_cli --cov=doctrine --cov=constitution --cov-fail-under=90 -q

# Type check
mypy --strict src/specify_cli/upgrade/migrations/m_2_2_0_profile_context_deployment.py

# Lint
rtk ruff check src/specify_cli/upgrade/migrations/
```

## Risks & Mitigations

- **Asset path resolution**: `get_package_asset_root()` returns a path into the installed package. Ensure the path resolves correctly in both development and installed contexts. Check how `m_2_0_11_install_skills.py` resolves skill assets.
- **Agent directory naming**: The `commands` vs `command` subdirectory difference (e.g., `.opencode/command/` vs `.claude/commands/`) is handled by `get_agent_dirs_for_project()`. Don't hardcode paths.
- **MigrationResult API**: Check the exact fields and constructor signature in `base.py` — `changes` may or may not be a supported field.

## Review Guidance

- Run `spec-kitty upgrade` on a test project with claude configured. Verify `spec-kitty.profile-context.md` exists in `.claude/commands/`.
- Run upgrade again. Confirm no error and the file is not duplicated.
- Temporarily remove `.claude/commands/spec-kitty.profile-context.md` and run upgrade — confirm it is re-deployed.

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
