---
work_package_id: WP01
title: Upgrade Migration — Pi and Letta Backfill
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-012
- FR-013
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pi-and-letta-agent-support-01KT4Q26
base_commit: be3123202b5184c61ffd6d133429ea3f9668938d
created_at: '2026-06-02T20:17:30.282550+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 0 - Foundation
agent: "claude:claude-sonnet-4-6:implementer-ivan:reviewer"
shell_pid: "35915"
history:
- timestamp: '2026-06-02T17:52:08Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
mission_id: 01KT4Q26YT9B4ZNBC4GH0D2WNM
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py
- tests/specify_cli/upgrade/migrations/test_m_3_2_10_pi_letta_backfill.py
role: implementer
tags: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

This profile configures your implementation style, quality standards, and review criteria.

---

## Objective

Write, register, and test a `spec-kitty upgrade` migration (`m_3_2_10_pi_letta_backfill`) that backfills two things for existing projects that have `pi` or `letta` configured: (1) `.pi/` and `.letta/` entries in `.gitignore`, and (2) Agent Skills files in `.agents/skills/` when any canonical skill is missing.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent claude
```

No `--base` flag needed — this is a foundation WP with no dependencies.

## Branch Strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Your execution worktree is allocated per the lane computed from `lanes.json`

## Context

**Background**: Pi and Letta are registered as `SKILL_CLASS_SHARED` agents in `config.py` with skill roots at `.agents/skills/` (and `.pi/skills/` for Pi). The `init` command already handles new projects correctly. However, **existing projects** initialized before Pi/Letta support was added may be missing:
- `.pi/` and/or `.letta/` gitignore entries (which prevent committing runtime state, auth tokens, and session logs)
- `.agents/skills/spec-kitty.*` files for these agents (if they were added to config after initialization)

The existing `m_2_1_1_repair_skill_pack` migration handles skill repair for agents that were present when that migration ran, but not for agents added to config after the fact.

**Pattern to follow**: `src/specify_cli/upgrade/migrations/m_3_2_9_sync_state_gitignore.py` uses `GitignoreManager` and `@MigrationRegistry.register`. `src/specify_cli/upgrade/migrations/m_2_1_1_repair_skill_pack.py` handles skill installation. Use both as models.

**Do not touch**: `AGENT_DIRS` in `directories.py` — Pi and Letta are intentionally skill-only agents and are correctly absent from `AGENT_DIRS`. Tests in `test_twelve_agent_parity.py:203-204` assert this.

## Subtask Guidance

### T001 — Write migration class skeleton

**File**: `src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py`

**Purpose**: Create the `BaseMigration` subclass with correct metadata.

**Steps**:

1. Add module docstring describing the migration's purpose.
2. Import: `from __future__ import annotations`, `from pathlib import Path`, `from ..registry import MigrationRegistry`, `from .base import BaseMigration, MigrationResult`.
3. Decorate the class with `@MigrationRegistry.register`.
4. Set class attributes:
   ```python
   migration_id = "3.2.10_pi_letta_agent_backfill"
   description = "Backfill .pi/ and .letta/ gitignore entries and skill files for configured agents"
   target_version = "3.2.10"
   ```
5. Stub out `apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult` with `pass`.

**Files**: `src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py` (new, ~15 lines for skeleton)

**Validation**: `mypy --strict` passes on the file. Class is importable.

---

### T002 — Implement gitignore backfill logic

**Purpose**: For each of `pi` and `letta`, if the agent is configured for the project and its directory entry is absent from `.gitignore`, add it.

**Steps**:

1. Import `GitignoreManager` from `specify_cli.gitignore_manager`.
2. Import `get_configured_agents` from `specify_cli.core.agent_config`.
3. In `apply()`, get `configured_agents = get_configured_agents(project_path)` — wrap in try/except for `AgentConfigError` and return a failed result if it throws.
4. Build a mapping of agent key → gitignore entry string:
   ```python
   AGENT_GITIGNORE_ENTRIES: dict[str, str] = {
       "pi": ".pi/",
       "letta": ".letta/",
   }
   ```
5. For each `(agent_key, entry)` in `AGENT_GITIGNORE_ENTRIES.items()`:
   - Skip if `agent_key not in configured_agents`.
   - Use `GitignoreManager(project_path / ".gitignore")` to check if entry is present; if not and `not dry_run`, add it and append `f"Added {entry} to .gitignore"` to `changes_made`.
6. In dry-run mode, report what would be changed without mutating anything.

**Files**: `src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py` (~30 additional lines)

**Reference**: `m_3_2_9_sync_state_gitignore.py` lines 77–120 for `GitignoreManager` usage pattern.

**Validation**:
- If `pi` is configured and `.pi/` is absent from `.gitignore`: entry is added.
- If `pi` is configured and `.pi/` already exists: no duplicate added, `changes_made` is empty.
- If `pi` is not configured: nothing touched.

---

### T003 — Implement skill-pack trigger

**Purpose**: For each configured Pi/Letta agent, check if any canonical skill file is missing from `.agents/skills/` and trigger a repair install if so.

**Steps**:

1. Import `CANONICAL_COMMANDS` from `specify_cli.skills.command_installer`.
2. Import `install` (or the relevant public function) from `specify_cli.skills.command_installer`.
3. For each `agent_key` in `("pi", "letta")` if in `configured_agents`:
   - Check `project_path / ".agents" / "skills" / f"spec-kitty.{cmd}" / "SKILL.md"` for every `cmd` in `CANONICAL_COMMANDS`.
   - If any `SKILL.md` is missing and `not dry_run`:
     - Call the installer for this agent (pass `project_path` and `[agent_key]`).
     - Append `f"Repaired skill pack for {agent_key}"` to `changes_made`.
     - Break the inner loop (one repair call covers all commands for this agent).
4. Wrap the installer call in a broad except that logs a warning and continues (missing wheel case).
5. In dry-run mode, report which agents need repair without calling the installer.
6. Return `MigrationResult(success=True, changes_made=changes_made)`.

**Files**: `src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py` (~30 additional lines)

**Reference**: `m_2_1_1_repair_skill_pack.py` for the installer call pattern and error handling.

**Validation**:
- If `.agents/skills/spec-kitty.specify/SKILL.md` is missing and `pi` is configured: installer is called for `pi`.
- If all skill files exist: no installer call, `changes_made` is empty.
- If installer raises: warning logged, migration still returns success.

---

### T004 — Register migration and verify chain

**Purpose**: Ensure the new migration is discovered by the upgrade detector and appears in the correct position in the version chain.

**Steps**:

1. Check `src/specify_cli/upgrade/migrations/__init__.py` (or equivalent auto-discovery) for how migrations are imported/registered. The `@MigrationRegistry.register` decorator should handle registration automatically when the module is imported.
2. Verify the migration is imported: check if there is an explicit import in `__init__.py` or a glob import. If explicit, add:
   ```python
   from .m_3_2_10_pi_letta_backfill import *  # noqa: F401,F403
   ```
   (match the pattern of the previous migration import).
3. Run `python -c "from specify_cli.upgrade.migrations import *; from specify_cli.upgrade.registry import MigrationRegistry; print([m.migration_id for m in MigrationRegistry.all()])"` and confirm `"3.2.10_pi_letta_agent_backfill"` appears.

**Files**: `src/specify_cli/upgrade/migrations/__init__.py` (may need one import line)

**Validation**: Migration appears in registry; `target_version = "3.2.10"` does not conflict with any existing migration.

---

### T005 — Write integration tests

**File**: `tests/specify_cli/upgrade/migrations/test_m_3_2_10_pi_letta_backfill.py`

**Purpose**: Verify the migration behaves correctly across all relevant scenarios.

**Test cases** (use `pytest` + `tmp_path`):

1. **`test_adds_pi_gitignore_when_configured`**: Create a project with `pi` in config but `.pi/` absent from `.gitignore`. Run migration. Assert `.pi/` is in `.gitignore` and `changes_made` is non-empty.

2. **`test_adds_letta_gitignore_when_configured`**: Same as above for `letta`/`.letta/`.

3. **`test_skips_gitignore_if_already_present`**: Create project with `pi` configured and `.pi/` already in `.gitignore`. Run migration. Assert `changes_made` is empty.

4. **`test_skips_unconfigured_agent`**: Create project with only `claude` configured (no `pi`, no `letta`). Run migration. Assert neither `.pi/` nor `.letta/` is added to `.gitignore`.

5. **`test_dry_run_does_not_mutate`**: Create project with `pi` configured, `.pi/` absent. Run migration with `dry_run=True`. Assert `.pi/` is still absent from `.gitignore`.

6. **`test_idempotent`**: Run migration twice on the same project. Assert second run produces empty `changes_made` and `.gitignore` has no duplicates.

7. **`test_skill_repair_triggered_when_skills_missing`** (may require mocking installer): Create project with `pi` configured, no skill files present. Assert installer is called.

8. **`test_no_skill_repair_when_skills_present`**: Create project with `pi` configured and all skill files present. Assert installer is NOT called.

**Markers**: Apply `@pytest.mark.integration` to all tests (matches project convention for tests that touch filesystem).

**Files**: `tests/specify_cli/upgrade/migrations/test_m_3_2_10_pi_letta_backfill.py` (new, ~150 lines)

**Validation**: All 8 tests pass. `mypy --strict` passes on the test file.

---

## Definition of Done

- [ ] `m_3_2_10_pi_letta_backfill.py` created and importable
- [ ] Migration adds `.pi/` to `.gitignore` for projects with `pi` configured
- [ ] Migration adds `.letta/` to `.gitignore` for projects with `letta` configured
- [ ] Migration triggers skill repair when canonical skill files are missing
- [ ] Migration is idempotent (running twice produces no duplicate entries)
- [ ] Migration appears in `MigrationRegistry.all()` output
- [ ] `mypy --strict` passes on both new files
- [ ] All 8 tests pass with `pytest tests/specify_cli/upgrade/migrations/test_m_3_2_10_pi_letta_backfill.py`
- [ ] No regressions in `tests/specify_cli/regression/test_twelve_agent_parity.py`

## Risks

- `GitignoreManager` API may differ from the model in `m_3_2_9`; check its public interface before writing T002.
- The `command_installer.install()` signature may require specific arguments (agent list, registry, project_path); check `m_2_1_1_repair_skill_pack.py` for the exact call pattern.
- Migration version `3.2.10` must not conflict with any existing migration; verify in the registry before finalizing.

## Reviewer Guidance

- Confirm migration is idempotent: apply twice to the same tmp project, assert second run returns empty `changes_made`.
- Confirm skill repair is gated on actual absence (not always triggered).
- Confirm unconfigured agents (e.g., `claude`-only project) see no changes to `.gitignore`.
- Run `pytest tests/specify_cli/regression/` to confirm no parity regressions.

## Activity Log

- 2026-06-02T20:17:53Z – claude – shell_pid=17073 – Moved to in_progress
- 2026-06-02T20:18:22Z – user – shell_pid=18226 – Assigned agent via action command
- 2026-06-02T20:23:30Z – user – shell_pid=18226 – Migration + tests implemented, mypy + ruff clean
- 2026-06-02T20:23:55Z – claude:claude-sonnet-4-6:implementer-ivan:reviewer – shell_pid=35915 – Started review via action command
