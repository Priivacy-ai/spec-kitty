---
work_package_id: WP03
title: Manager, CLI Command, init Integration, and Phase 1 Migration
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-013
- FR-014
- NFR-001
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "56507"
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/manager.py
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/manager.py
- src/specify_cli/cli/commands/session_start.py
- src/specify_cli/__init__.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_claude_code.py
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

Build the orchestrating layer: `SessionPresenceManager` iterates all configured agents and calls their writers; `session-start` CLI command emits orientation to stdout (exit 0 always); wire `install()` into `spec-kitty init`; write the Phase 1 upgrade migration.

## Context

After WP01 and WP02, the `session_presence` package exists with a working `ClaudeCodeWriter`. This WP wires everything together so that `spec-kitty init` and `spec-kitty session-start` work end-to-end.

Before implementing, read `src/specify_cli/cli/commands/init.py` to understand the existing agent setup flow. The `install()` call goes **after** the existing agent directory setup block, just before or after `save_agent_config()`.

**References**:
- Spec: FR-003, FR-004, FR-005, FR-007, FR-013, FR-014, NFR-001
- `kitty-specs/session-presence-multi-harness-01KTH57W/research.md` (sections 5 and 6)
- Charter DIR-012 (assign GitHub issues to HiC before starting)

**Implementation command**:
```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Branch Strategy

- **Planning base**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`
- WP01 and WP02 must be merged before this worktree branches.

---

## Subtask T012 — SessionPresenceManager

**Purpose**: Orchestrates `install()` and `update()` across all configured agents. Builds `SessionPresenceContent` using the current version and upgrade cache. Delegates to per-agent writers.

**File**: `src/specify_cli/session_presence/manager.py`

```python
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from .content import SessionPresenceContent
from .upgrade_check import UpgradeChecker
from .writers.registry import get_writer

_logger = logging.getLogger(__name__)


class InstallResult(NamedTuple):
    changes: list[str]
    warnings: list[str]


@dataclass
class SessionPresenceManager:
    project_root: Path
    agent_config: "AgentConfig"  # from specify_cli.core.agent_config

    def _build_content(self) -> SessionPresenceContent:
        from importlib.metadata import version
        from specify_cli.migration.gate import project_needs_migration
        checker = UpgradeChecker()
        checker.check_in_background()
        avail = checker.get_available_version()
        current = version("spec-kitty-cli")
        slug = getattr(self.agent_config, "project_slug", None) or "unknown"
        health: str
        if project_needs_migration(self.project_root):
            health = "migration-required"
        elif avail and avail != current:
            health = "upgrade-available"
        else:
            health = "healthy"
        return SessionPresenceContent(current, slug, health, avail)  # type: ignore[arg-type]

    def install(self) -> InstallResult:
        """Write presence for each configured agent that doesn't have it yet."""
        content = self._build_content()
        changes: list[str] = []
        warnings: list[str] = []
        for key in getattr(self.agent_config, "available", []):
            writer = get_writer(key)
            try:
                if writer.can_write(self.project_root) and not writer.has_presence(self.project_root):
                    writer.write(self.project_root, content)
                    changes.append(f"Wrote orientation for {key}")
            except Exception as exc:
                warnings.append(f"Failed to write orientation for {key}: {exc}")
                _logger.warning("SessionPresenceManager.install failed for %s: %s", key, exc)
        return InstallResult(changes=changes, warnings=warnings)

    def update(
        self,
        agents: set[str] | None = None,
        dry_run: bool = False,
    ) -> InstallResult:
        """Update (replace) presence for specified agents, whether or not already present."""
        content = self._build_content()
        target_agents = agents if agents is not None else set(getattr(self.agent_config, "available", []))
        changes: list[str] = []
        warnings: list[str] = []
        for key in target_agents:
            writer = get_writer(key)
            try:
                if writer.can_write(self.project_root):
                    if not dry_run:
                        writer.write(self.project_root, content)
                    changes.append(f"{'Would write' if dry_run else 'Wrote'} orientation for {key}")
                else:
                    _logger.debug("NullWriter or no harness dir for %s — skipping", key)
            except Exception as exc:
                warnings.append(f"Failed to update orientation for {key}: {exc}")
        return InstallResult(changes=changes, warnings=warnings)
```

**Import note**: `AgentConfig` is imported as a type annotation; avoid circular imports by using `TYPE_CHECKING` if needed. `project_needs_migration` — verify the import path in the codebase before committing.

---

## Subtask T013 — session-start CLI Command

**Purpose**: Called by Claude Code's `SessionStart` hook. Must emit orientation to stdout when inside a spec-kitty project, produce no output outside one, and exit 0 on ALL code paths including exceptions.

**File**: `src/specify_cli/cli/commands/session_start.py`

```python
from __future__ import annotations
import logging
from pathlib import Path

import typer

_logger = logging.getLogger(__name__)
app = typer.Typer()


def _find_project_root() -> Path | None:
    """Walk up from cwd looking for a .kittify/ directory."""
    current = Path.cwd().resolve()
    while True:
        if (current / ".kittify").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


@app.command()
def session_start() -> None:
    """Emit spec-kitty orientation for the Claude Code SessionStart hook."""
    try:
        project_root = _find_project_root()
        if project_root is None:
            return
        from specify_cli.core.agent_config import AgentConfig
        from specify_cli.session_presence.manager import SessionPresenceManager
        agent_config = AgentConfig.load(project_root)
        content = SessionPresenceManager(project_root, agent_config)._build_content()
        typer.echo(content.render())
    except Exception:
        pass  # Always exit 0 — never fail the Claude Code session
```

**Performance constraint (NFR-001)**: Must complete in <200ms on warm filesystem. No network calls on the hot path — `check_in_background()` fires and returns immediately; `get_available_version()` reads only the local cache file.

**Exit 0 guarantee**: The bare `except Exception: pass` is intentional. Document this in the module docstring.

---

## Subtask T014 — Register Command + Wire install() in init.py

**Purpose**: Make `session-start` a real CLI command; call `SessionPresenceManager(...).install()` during `spec-kitty init`.

**`src/specify_cli/__init__.py`**: Find the section where CLI commands are registered (look for other `session_*` or similar commands). Add:
```python
from specify_cli.cli.commands.session_start import app as session_start_app
# Register as: spec-kitty session-start
```
Follow the exact pattern used for adjacent commands in `__init__.py`.

**`src/specify_cli/cli/commands/init.py`**: Read the full file first. Find the agent setup completion point (near `save_agent_config(project_path, agent_config)`). After that block, add:
```python
from specify_cli.session_presence.manager import SessionPresenceManager
result = SessionPresenceManager(project_path, agent_config).install()
for change in result.changes:
    # Optionally display the change using the existing tracker/console pattern
    pass
```
Follow the existing `tracker` / `console` pattern for user-visible output. Use `tracker.add(...)` or equivalent if available. Do NOT add a new output mechanism.

**Key constraint**: The `install()` call must not raise — it already swallows exceptions internally. If for any reason it does raise, wrap in a `try/except` in `init.py`.

**Version bump (CLAUDE.md project policy)**: Modifying `src/specify_cli/__init__.py` to register the new `session-start` command triggers the project's mandatory version bump rule. As part of this subtask:
1. Bump the patch version in `pyproject.toml` (e.g., `3.2.x` → `3.3.0` or next appropriate version — check the current value first).
2. Add a `CHANGELOG.md` entry under a new version heading, noting the addition of the `session-start` command and the `session_presence` package.

Follow the existing CHANGELOG.md entry format exactly (look at adjacent entries for the pattern).

---

## Subtask T015 — Phase 1 Upgrade Migration

**Purpose**: Detect existing Claude Code projects missing session presence and backfill both artefacts on `spec-kitty upgrade`.

**File**: `src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_claude_code.py`

Study an existing migration (e.g., `m_3_2_0rc35_spk_skill_pack.py`) for the exact class structure, registration pattern, and import conventions.

```python
from __future__ import annotations
from pathlib import Path
from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


class SessionPresenceClaudeCodeMigration(BaseMigration):
    migration_id = "3_3_0_session_presence_claude_code"
    target_version = "3.3.0"
    runs_on_worktrees = False

    def detect(self, project_path: Path) -> bool:
        if not (project_path / ".kittify").is_dir():
            return False
        from specify_cli.core.agent_config import load_agent_config
        config = load_agent_config(project_path)
        if "claude" not in (config.available if config else []):
            return False
        from specify_cli.session_presence.writers.claude_code import ClaudeCodeWriter
        return not ClaudeCodeWriter().has_presence(project_path)

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        from specify_cli.core.agent_config import AgentConfig
        from specify_cli.session_presence.manager import SessionPresenceManager
        from specify_cli.session_presence.writers.claude_code import ClaudeCodeWriter
        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=["Would write orientation to .claude/CLAUDE.md and register SessionStart hook"],
            )
        agent_config = AgentConfig.load(project_path)
        manager = SessionPresenceManager(project_path, agent_config)
        content = manager._build_content()
        ClaudeCodeWriter().write(project_path, content)
        return MigrationResult(
            success=True,
            changes_made=[
                "Wrote spec-kitty orientation to .claude/CLAUDE.md",
                "Registered spec-kitty session-start SessionStart hook",
            ],
        )


MigrationRegistry.register(SessionPresenceClaudeCodeMigration)
```

**Notes**:
- `migration_id` must be unique across all migrations — use the version + descriptive name pattern.
- `target_version`: use the version that will be released with this PR (consult `pyproject.toml`).
- `runs_on_worktrees = False` — session presence is per-checkout, not per-worktree.
- `detect()` checks `has_presence()` which requires BOTH CLAUDE.md section AND settings.json hook. If either is missing, the migration applies.

---

## Subtask T016 — Pre-Implementation Test Suite Check (DIR-013)

**Purpose**: Charter directive DIR-013 requires opening a GitHub issue if pre-existing test failures are found before starting implementation.

**Action**:
```bash
pytest tests/ -x --timeout=60 -q 2>&1 | tail -20
```

If failures exist that you did NOT introduce:
1. Determine whether they are pre-existing (not caused by your WP01–WP03 changes).
2. Open a GitHub issue: `gh issue create --title "Pre-existing test failures found during WP03 implementation" --body "Command: pytest tests/ -x -q\n\nFailures:\n<paste output>"`
3. Continue implementing — the pre-existing failures are now tracked.

If all tests pass: proceed normally. Document in your WP review that DIR-013 check passed.

---

## Definition of Done

- [ ] `SessionPresenceManager(root, config).install()` writes orientation for each configured agent (only Claude in Phase 1) and returns `InstallResult`
- [ ] `SessionPresenceManager(root, config).update(dry_run=True)` returns changes list without touching filesystem
- [ ] `spec-kitty session-start` (invoked from inside a spec-kitty project) outputs the orientation block and exits 0
- [ ] `spec-kitty session-start` (invoked from `/tmp`) produces no output and exits 0
- [ ] `spec-kitty session-start` exits 0 when `_build_content()` raises an exception (verified manually)
- [ ] `spec-kitty init --ai claude` writes `.claude/CLAUDE.md` orientation section and `.claude/settings.json` hook
- [ ] Phase 1 migration `detect()` returns True for a project with `claude` configured but missing either artefact
- [ ] Phase 1 migration `apply(dry_run=True)` produces no filesystem changes
- [ ] Phase 1 migration is registered in `MigrationRegistry`
- [ ] DIR-013 check documented in commit message or review note
- [ ] Zero ruff issues, zero mypy --strict issues

## Risks

- `import specify_cli.migration.gate.project_needs_migration` — verify exact import path before using. Check `src/specify_cli/migration/` for the correct module.
- `AgentConfig.load()` vs `load_agent_config()` — the codebase uses both patterns in different contexts. Prefer `AgentConfig.load(project_root)` in `manager.py` for consistency with migration code.
- `target_version` in migration: if the release version for this PR hasn't been decided, use `"3.3.0"` as a placeholder and update at PR time.

## Activity Log

- 2026-06-07T15:16:05Z – claude:sonnet:implementer:implementer – shell_pid=9699 – Assigned agent via action command
- 2026-06-07T15:25:32Z – claude:sonnet:implementer:implementer – shell_pid=9699 – WP03 complete: SessionPresenceManager, session-start CLI, init integration, Phase 1 migration. Ruff clean. DIR-013: pre-existing test failure in test_occurrence_classification (missing implement.md template, unrelated to WP03). WP01/WP02 foundation files copied from lane-b into lane-c worktree.
- 2026-06-07T15:26:02Z – claude:sonnet:reviewer:reviewer – shell_pid=37939 – Started review via action command
- 2026-06-07T15:33:00Z – user – shell_pid=37939 – Moved to planned
- 2026-06-07T15:33:55Z – claude:sonnet:implementer:implementer – shell_pid=49576 – Started implementation via action command
- 2026-06-07T15:36:03Z – claude:sonnet:implementer:implementer – shell_pid=49576 – Cycle 2: fixed AgentConfig.load→load_agent_config, removed unused type-ignore. Ruff and mypy clean.
- 2026-06-07T15:36:36Z – claude:sonnet:reviewer:reviewer – shell_pid=56507 – Started review via action command
