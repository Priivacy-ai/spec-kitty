---
work_package_id: WP06
title: Phase 2 Migration and Tests
dependencies:
- WP05
requirement_refs:
- C-005
- FR-015
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
agent: "claude:sonnet:implementer:implementer"
shell_pid: "82481"
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_all_harnesses.py
- tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Write the Phase 2 upgrade migration that backfills orientation for all non-Claude harnesses on existing projects, write its full test suite, and run an integration smoke to verify end-to-end correctness across all patterns.

## Context

After WP05 merges, the `WRITER_REGISTRY` covers all 19 harnesses. This WP writes the migration that detects which configured non-Claude harnesses are missing orientation and calls `SessionPresenceManager` to backfill them. The migration must use `get_agent_dirs_for_project()` (C-005 constraint) — it must never hardcode the agent list, create missing agent directories, or process agents absent from `.kittify/config.yaml`.

**C-005 constraint** (CRITICAL):
> The upgrade migration for Phase 2 uses `get_agent_dirs_for_project()` to enumerate configured agents. It must not hardcode the full list of 19 agents, must not create agent directories that do not exist, and must not process agents absent from `.kittify/config.yaml`.

**References**:
- Spec: FR-015, FR-016, FR-017, C-005
- `CLAUDE.md` — Agent Management section (Writing Migrations subsection): `get_agent_dirs_for_project()` usage pattern
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` — contains `get_agent_dirs_for_project()` and `AGENT_DIRS`
- `src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_claude_code.py` (from WP03) — model for migration structure
- `kitty-specs/session-presence-multi-harness-01KTH57W/spec.md` Scenario 8

**Implementation command**:
```bash
spec-kitty agent action implement WP06 --agent claude
```

---

## Branch Strategy

- **Planning base**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`
- WP05 must be merged before this worktree branches.

---

## Subtask T028 — Phase 2 Upgrade Migration

**Purpose**: Detect existing projects where non-Claude configured harnesses lack session presence and backfill them via `SessionPresenceManager`.

**File**: `src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_all_harnesses.py`

Study `m_3_3_0_session_presence_claude_code.py` (WP03 output) and an existing complex migration like `m_0_9_1_complete_lane_migration.py` for the exact class structure, registration pattern, and `get_agent_dirs_for_project()` usage.

```python
from __future__ import annotations
from pathlib import Path
from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


class SessionPresenceAllHarnessesMigration(BaseMigration):
    migration_id = "3_3_0_session_presence_all_harnesses"
    target_version = "3.3.0"
    runs_on_worktrees = False

    def _get_non_claude_configured_keys(self, project_path: Path) -> list[str]:
        """Return agent keys configured in .kittify/config.yaml, excluding 'claude'."""
        from specify_cli.upgrade.migrations.m_0_9_1_complete_lane_migration import (
            get_agent_dirs_for_project,
        )
        from specify_cli.agent_utils.directories import AGENT_DIR_TO_KEY
        keys: list[str] = []
        for agent_root, _subdir in get_agent_dirs_for_project(project_path):
            key = AGENT_DIR_TO_KEY.get(agent_root)
            if key and key != "claude":
                keys.append(key)
        return keys

    def detect(self, project_path: Path) -> bool:
        """Return True when at least one configured non-Claude harness lacks presence."""
        if not (project_path / ".kittify").is_dir():
            return False
        from specify_cli.session_presence.writers.registry import get_writer
        from specify_cli.session_presence.writers.null_writer import NullWriter
        for key in self._get_non_claude_configured_keys(project_path):
            writer = get_writer(key)
            if isinstance(writer, NullWriter):
                continue  # NullWriter can never have presence; skip silently
            if writer.can_write(project_path) and not writer.has_presence(project_path):
                return True
        return False

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        from specify_cli.core.agent_config import AgentConfig
        from specify_cli.session_presence.manager import SessionPresenceManager
        from specify_cli.session_presence.writers.null_writer import NullWriter
        from specify_cli.session_presence.writers.registry import get_writer

        non_claude_keys = self._get_non_claude_configured_keys(project_path)
        active_keys = {
            k for k in non_claude_keys
            if not isinstance(get_writer(k), NullWriter) and get_writer(k).can_write(project_path)
        }

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Would write orientation for: {', '.join(sorted(active_keys)) or 'none'}"
                ],
            )

        agent_config = AgentConfig.load(project_path)
        manager = SessionPresenceManager(project_path, agent_config)
        result = manager.update(agents=active_keys, dry_run=False)
        return MigrationResult(
            success=True,
            changes_made=result.changes,
        )


MigrationRegistry.register(SessionPresenceAllHarnessesMigration)
```

**Important implementation notes**:

1. **`get_agent_dirs_for_project()` return value**: Yields `(agent_root, subdir)` tuples where `agent_root` is the directory string (e.g., `".cursor"`). `AGENT_DIR_TO_KEY` in `src/specify_cli/agent_utils/directories.py` maps directory roots to agent keys. Read this file before implementing `_get_non_claude_configured_keys()` to ensure the mapping is correct.

2. **Import verification**: Confirm the import path for `AgentConfig.load()` before committing. It may differ between `from specify_cli.core.agent_config import AgentConfig` and `from specify_cli.agent_utils.agent_config import AgentConfig`. Check what WP03's migration uses.

3. **Never create directories**: `get_agent_dirs_for_project()` only returns directories that exist (C-005). Do NOT create missing agent directories as part of migration.

4. **FR-017 — forward-compatibility**: `detect()` calls `get_writer(key)` dynamically. When a Pattern E harness is later promoted to a real writer, the migration's detection logic automatically includes it — no new migration needed. This satisfies FR-017.

5. **`runs_on_worktrees = False`**: Session presence is per-checkout state. Worktrees share the same agent config as the main checkout but each has its own working directory. The migration should only run on the main checkout.

---

## Subtask T029 — Migration Test Suite

**Purpose**: Full test coverage for the Phase 2 migration's detection and application logic.

**File**: `tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py`

Required test cases:

**`detect()` tests**:
- Returns False for project without `.kittify/`
- Returns False for project with no non-Claude configured agents
- Returns False for project where all configured non-Claude agents have presence already
- Returns False for project where only NullWriter agents are configured (qwen, auggie, etc.)
- Returns True for project where at least one configured non-Claude agent (cursor) is missing presence
- Returns True for project where some agents have presence and some don't (partial backfill scenario)
- Returns False after `apply()` has run (detect + apply + detect cycle)

**`apply()` tests**:
- `apply()` on project with cursor configured but missing presence: creates `.cursor/rules/spec-kitty.mdc`
- `apply()` on project with both cursor and copilot configured: writes both files
- `apply()` skips NullWriter agents (qwen, q) without error
- `apply(dry_run=True)` produces no filesystem changes (verify with `listdir`/`exists` before and after)
- `apply()` is idempotent — calling twice leaves files in same state as calling once
- `apply()` does NOT process agents absent from `.kittify/config.yaml`

**Forward-compatibility test** (FR-017):
- Monkey-patch `WRITER_REGISTRY["qwen"]` with a real `MarkdownRulesWriter` instance (simulating Pattern E promotion in a future release). Verify that `detect()` returns `True` for a qwen-configured project missing presence — **without** requiring a new migration. This validates that dynamic `get_writer(key)` in `detect()` picks up promoted writers automatically:
```python
def test_detect_picks_up_promoted_pattern_e_writer(tmp_path, monkeypatch):
    """FR-017: promoted Pattern E writer is found by detect() without a new migration."""
    make_project(tmp_path, agents=["qwen"])
    (tmp_path / ".qwen").mkdir()  # harness root exists → can_write returns True
    real_writer = MarkdownRulesWriter(
        harness_key="qwen",
        rules_path=".qwen/spec-kitty.md",
        append_mode=False,
        check_dir=".qwen",
    )
    monkeypatch.setitem(WRITER_REGISTRY, "qwen", real_writer)
    migration = SessionPresenceAllHarnessesMigration()
    assert migration.detect(tmp_path) is True
```

**Property tests**:
- `runs_on_worktrees == False`
- Migration is registered in `MigrationRegistry` (test via registry lookup by migration_id)
- `migration_id` is unique across all registered migrations

**Setup helpers**: Use `tmp_path` for all filesystem operations. Create minimal project structure:
```python
def make_project(tmp_path, agents=None):
    """Create a minimal spec-kitty project configured for the given agents."""
    (tmp_path / ".kittify").mkdir()
    # Write a minimal config.yaml with the specified agents
    # ... follow existing test patterns in tests/specify_cli/test_agent_config_migration.py
```

---

## Subtask T030 — Integration Smoke and Full Test Run

**Purpose**: Verify end-to-end idempotency across all patterns on a simulated multi-harness project; confirm the full test suite passes.

**Integration smoke** (implement as a single pytest integration test):

```
tests/specify_cli/session_presence/test_integration_smoke.py
```

Test case: `test_full_harness_install_idempotent(tmp_path)`:

1. Create a project directory with `.kittify/`, `.claude/`, `.cursor/`, `.github/`, and `AGENTS.md` pre-created.
2. Configure mock agent_config to report: `["claude", "cursor", "copilot", "codex", "pi", "qwen"]`
3. Call `SessionPresenceManager(project_root, mock_config).install()` → verify:
   - `.claude/CLAUDE.md` has orientation section
   - `.claude/settings.json` has SessionStart hook
   - `.cursor/rules/spec-kitty.mdc` exists and has orientation section
   - `.github/copilot-instructions.md` has orientation section appended
   - `AGENTS.md` has orientation section (written by both `codex` [AgentsMdWriter] and `pi` [SkillsPreambleWriter] — but only ONE section present)
   - No `.qwen/` files created (NullWriter)
4. Call `install()` a second time → verify all files are byte-for-byte identical (true idempotency)
5. Call `update()` → verify all files are updated (health/version may differ if mocked to change)
6. Verify `has_presence()` returns True for claude, cursor, copilot, codex, pi
7. Verify `has_presence()` returns False for qwen (NullWriter)

**AGENTS.md shared-write test**: Verify that when both `codex` and `pi` are configured, a single `AGENTS.md` section exists (not two). The second writer's `write()` replaces the section that the first writer wrote — no duplication.

**Full test run**:
```bash
pytest tests/specify_cli/session_presence/ \
       tests/specify_cli/cli/commands/test_session_start.py \
       tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py \
       tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py \
       -v
```

All tests must pass. Zero ruff issues and zero mypy --strict issues across the entire `src/specify_cli/session_presence/` package.

**Regression check**: Run the full project test suite:
```bash
pytest tests/ -x --timeout=60 -q 2>&1 | tail -30
```

If any pre-existing tests fail that are unrelated to this WP, open a GitHub issue (DIR-013) and document it in the WP review. Do not attempt to fix pre-existing failures.

---

## Definition of Done

- [ ] `m_3_3_0_session_presence_all_harnesses.py` exists and is registered in `MigrationRegistry`
- [ ] `detect()` returns True for a project with at least one configured non-Claude harness missing presence
- [ ] `detect()` returns False after `apply()` runs (no re-detection on already-migrated project)
- [ ] `apply(dry_run=True)` produces zero filesystem changes
- [ ] `apply()` is idempotent — calling twice leaves files unchanged
- [ ] Migration uses `get_agent_dirs_for_project()` — zero hardcoded agent lists
- [ ] Integration smoke: multi-harness `install()` is idempotent (two calls → same file content)
- [ ] Integration smoke: AGENTS.md has exactly one `<!-- spec-kitty:orientation -->` section even when multiple Pattern C/D harnesses write to it
- [ ] `pytest tests/specify_cli/session_presence/ ... -v` — all green
- [ ] Zero ruff issues, zero mypy --strict issues

## Risks

- **`AGENT_DIR_TO_KEY` mapping**: The `AGENT_DIR_TO_KEY` dict maps directory paths (e.g., `".augment"`) to agent keys (e.g., `"auggie"`). Some mappings are non-obvious (directory name ≠ key name). Read `src/specify_cli/agent_utils/directories.py` before implementing `_get_non_claude_configured_keys()`.
- **`get_agent_dirs_for_project()` import path**: It lives in `m_0_9_1_complete_lane_migration.py` as an exported function. Verify it is importable from tests without side effects (the migration module may register things on import).
- **AGENTS.md single-section invariant**: Multiple Pattern C/D writers will all call `write(root, content)` for the same `AGENTS.md`. The second call finds `SECTION_OPEN` already present and invokes `_replace_section()`. This is correct but relies on `_replace_section()` being deterministic. Add the AGENTS.md deduplication test explicitly (T030 integration smoke covers this).
- **Migration `target_version`**: Use the same version as the Phase 1 migration (`"3.3.0"` placeholder). Update at PR time once the release version is confirmed.

## Activity Log

- 2026-06-07T16:15:43Z – claude:sonnet:implementer:implementer – shell_pid=82481 – Assigned agent via action command
