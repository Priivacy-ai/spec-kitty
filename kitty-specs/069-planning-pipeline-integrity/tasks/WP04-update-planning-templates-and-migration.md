---
work_package_id: WP04
title: Update planning templates and migration
dependencies: [WP02]
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T022, T023, T024, T025, T026]
shell_pid: '16944'
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/software-dev/command-templates/tasks-outline.md
- src/specify_cli/missions/software-dev/command-templates/tasks-packages.md
- src/specify_cli/upgrade/migrations/m_3_2_0_update_planning_templates.py
- tests/upgrade/migrations/test_m_3_2_0_update_planning_templates.py
---

# WP04: Update Planning Templates and Migration

## Objective

Rewrite `tasks-outline.md` and `tasks-packages.md` source command templates so that LLMs produce `wps.yaml` instead of `tasks.md` prose. Write a new migration `m_3_2_0_update_planning_templates.py` that propagates these changes to existing user installations.

**Success criterion**: After `spec-kitty upgrade`, a project that had the old `tasks-outline.md` deployed (with "Create `tasks.md`" in its Purpose section) now has the new version (with wps.yaml instructions). The `detect()` method returns True for stale files and False for fresh ones.

## Context

`tasks-outline` and `tasks-packages` are **prompt-driven commands** — their command files contain the full LLM prompt. They live in:
- Source: `src/specify_cli/missions/software-dev/command-templates/`
- Deployed: `<project>/.claude/commands/spec-kitty.tasks-outline.md`, `<project>/.amazonq/prompts/spec-kitty.tasks-outline.md`, etc. (12 agent directories)

The deployment pipeline (`m_2_1_3_restore_prompt_commands`) only activates for thin shims. Existing full prompts from prior upgrades are skipped. A new migration is needed to push content-level updates.

**WP02 dependency**: The migration's documentation (comments, docstring) references the wps.yaml schema file path from WP02. No runtime import dependency on WP02.

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (Lane C worktree, after WP02)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP04`

---

## Subtask T022: Rewrite `tasks-outline.md` template

**Purpose**: Change the LLM's output target from `tasks.md` to `wps.yaml`.

**File**: `src/specify_cli/missions/software-dev/command-templates/tasks-outline.md`

**Key changes** (do not change the prompt's Context Resolution, Setup, or branch guidance sections):

1. **Purpose section** — replace:
   > Create `tasks.md` — the task breakdown document...

   With:
   > Create `wps.yaml` — the structured work package manifest that defines WP metadata, dependencies, and file ownership. `tasks.md` is generated automatically from this manifest by `finalize-tasks`. Do NOT write `tasks.md`.

2. **Step 5 (was "Write `tasks.md`")** — replace with "Write `wps.yaml`":
   - Show the full wps.yaml schema with a concrete example (3–4 WPs)
   - Include all required fields: `id`, `title`, `dependencies`, `owned_files`, `requirement_refs`, `subtasks`, `prompt_file`
   - State the dependency semantics: `dependencies: []` = explicitly no deps (authoritative); absent `dependencies` = may be populated by tasks-packages
   - Example:
     ```yaml
     work_packages:
       - id: WP01
         title: "Foundation Setup"
         dependencies: []
         owned_files: ["src/myapp/core/**"]
         requirement_refs: [FR-001, FR-002]
         subtasks: [T001, T002, T003]
         prompt_file: "tasks/WP01-foundation-setup.md"
     ```

3. **Step 6 (Analyze dependencies)** — update to say: "Analyze the spec and plan for dependency relationships. Express them in `wps.yaml` `dependencies` fields. Do NOT include a Dependency Graph section in prose — it is not needed and cannot be parsed."

4. **Output section** — update from `feature_dir/tasks.md` to `feature_dir/wps.yaml`.

5. Add a clear warning box:
   > ⚠️ DO NOT write `tasks.md`. The system generates it from `wps.yaml`. Writing `tasks.md` manually will have it overwritten by `finalize-tasks`.

**Version bump**: Update or add the version comment at the top: `<!-- spec-kitty-command-version: 3.2.0 -->`

---

## Subtask T023: Rewrite `tasks-packages.md` template

**Purpose**: Update the LLM to read/update `wps.yaml` instead of reading `tasks.md`, then generate WP prompt files.

**File**: `src/specify_cli/missions/software-dev/command-templates/tasks-packages.md`

**Key changes**:

1. **Purpose section** — add: "This step reads `wps.yaml` (written in tasks-outline), updates it with per-WP details, then generates the WP prompt files."

2. **Step 2 (was "Load tasks.md")** — replace with "Load `wps.yaml`":
   > Read `feature_dir/wps.yaml`. This is the manifest written in the previous step. Each entry defines a WP with its id, title, dependencies, and partial metadata.

3. **Step 3 (Generate Prompt Files)** — unchanged in structure. WP files still go in `feature_dir/tasks/` with the same frontmatter requirements.

4. **Step 4 (Dependencies in Frontmatter)** — update: "After generating each WP prompt file, update the corresponding entry in `wps.yaml` to add `owned_files`, `requirement_refs`, `subtasks`, and `prompt_file`. Write the updated `wps.yaml` back to disk."

5. Add: "Do NOT modify a `dependencies` field that is already present in `wps.yaml` — even if it is empty (`[]`). It is authoritative. Only populate `dependencies` for entries where the key is absent."

6. **Output section** — update: "After this step, `wps.yaml` is fully populated and WP prompt files exist in `feature_dir/tasks/`."

**Version bump**: `<!-- spec-kitty-command-version: 3.2.0 -->`

---

## Subtask T024: Write migration `m_3_2_0_update_planning_templates.py`

**Purpose**: Push the template content changes to existing installations that have full prompt files from prior upgrades.

**File**: `src/specify_cli/upgrade/migrations/m_3_2_0_update_planning_templates.py` (new)

**Pattern**: Follow `m_2_1_3_restore_prompt_commands.py` exactly. Import `get_agent_dirs_for_project`, `_get_runtime_command_templates_dir`, and `_render_full_prompt` from that module (or extract to shared helpers).

```python
"""Migration 3.2.0: Update tasks-outline and tasks-packages to wps.yaml-based prompts.

Projects that ran spec-kitty upgrade before 3.2.0 have the old prompt-driven
command files for tasks-outline and tasks-packages. These instruct the LLM to
write tasks.md prose instead of wps.yaml. This migration detects and replaces them.

Detection: checks for the string "Create `tasks.md`" in any tasks-outline command
file. This string is unique to the pre-3.2.0 template and absent in the new version.

Idempotency: files already using the new wps.yaml instructions do not contain the
detection string and are left unchanged.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

logger = logging.getLogger(__name__)

# String present in old tasks-outline (pre-3.2.0), absent in new version.
_STALE_MARKER = "Create `tasks.md`"
_COMMANDS_TO_UPDATE = ("tasks-outline", "tasks-packages")


@MigrationRegistry.register
class UpdatePlanningTemplatesMigration(BaseMigration):
    """Replace pre-3.2.0 tasks-outline / tasks-packages with wps.yaml-based versions."""

    migration_id = "3.2.0_update_planning_templates"
    description = (
        "Update tasks-outline and tasks-packages command files from prose tasks.md "
        "authoring to structured wps.yaml manifest authoring"
    )
    target_version = "3.2.0"

    def detect(self, project_path: Path) -> bool:
        """Return True if any tasks-outline command file contains the stale marker."""
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue
            for command in _COMMANDS_TO_UPDATE:
                for candidate in agent_dir.glob(f"spec-kitty.{command}.*"):
                    try:
                        if _STALE_MARKER in candidate.read_text(encoding="utf-8"):
                            return True
                    except OSError:
                        continue
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        from specify_cli.upgrade.migrations.m_2_1_3_restore_prompt_commands import (
            _get_runtime_command_templates_dir,
        )
        templates_dir = _get_runtime_command_templates_dir()
        if templates_dir is None:
            return False, "Runtime command templates not found. Run 'spec-kitty upgrade' after reinstalling."
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        from specify_cli.upgrade.migrations.m_2_1_3_restore_prompt_commands import (
            _get_runtime_command_templates_dir,
            _render_full_prompt,
            _agent_root_to_key,
            _compute_output_filename,
            _resolve_script_type,
        )

        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        templates_dir = _get_runtime_command_templates_dir()
        if templates_dir is None:
            return MigrationResult(success=False, changes_made=[], errors=["Templates dir not found"])

        script_type = _resolve_script_type()
        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue

            agent_key = _agent_root_to_key(agent_root)
            if agent_key is None:
                continue

            for command in _COMMANDS_TO_UPDATE:
                template_path = templates_dir / f"{command}.md"
                if not template_path.is_file():
                    warnings.append(f"Template not found for '{command}' — skipping")
                    continue

                # Find stale file
                stale_file = None
                for candidate in agent_dir.glob(f"spec-kitty.{command}.*"):
                    try:
                        if _STALE_MARKER in candidate.read_text(encoding="utf-8"):
                            stale_file = candidate
                            break
                    except OSError:
                        continue

                if stale_file is None:
                    continue  # Already up-to-date

                output_filename = _compute_output_filename(command, agent_key)
                output_path = agent_dir / output_filename
                rel = str(output_path.relative_to(project_path))

                if dry_run:
                    changes.append(f"Would update: {rel}")
                    continue

                rendered = _render_full_prompt(template_path, agent_key, script_type)
                if rendered is None:
                    errors.append(f"Failed to render {command} for {agent_key}")
                    continue

                try:
                    output_path.write_text(rendered, encoding="utf-8")
                    changes.append(f"Updated: {rel}")
                except OSError as exc:
                    errors.append(f"Failed to write {rel}: {exc}")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
```

---

## Subtask T025: Migration unit tests — detect()

**File**: `tests/upgrade/migrations/test_m_3_2_0_update_planning_templates.py` (new)

```python
"""Unit tests for m_3_2_0_update_planning_templates migration."""
from __future__ import annotations

from pathlib import Path
import pytest


class TestDetect:
    def _write_agent_file(self, tmp_path: Path, content: str) -> Path:
        agent_dir = tmp_path / ".claude" / "commands"
        agent_dir.mkdir(parents=True)
        f = agent_dir / "spec-kitty.tasks-outline.md"
        f.write_text(content, encoding="utf-8")
        return tmp_path

    def test_detect_stale_tasks_outline(self, tmp_path: Path) -> None:
        """Returns True when stale marker present."""
        # Also write config
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n")

        self._write_agent_file(tmp_path, "# spec-kitty.tasks-outline\nCreate `tasks.md`\n")

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(tmp_path) is True

    def test_detect_fresh_tasks_outline(self, tmp_path: Path) -> None:
        """Returns False when new wps.yaml instructions present (no stale marker)."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n")

        self._write_agent_file(tmp_path, "# spec-kitty.tasks-outline\nCreate `wps.yaml`\n")

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(tmp_path) is False

    def test_detect_absent_agent_dir(self, tmp_path: Path) -> None:
        """Returns False when no agent directories exist."""
        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(tmp_path) is False
```

---

## Subtask T026: Migration unit tests — apply()

**File**: `tests/upgrade/migrations/test_m_3_2_0_update_planning_templates.py`

```python
from unittest.mock import patch, MagicMock

class TestApply:
    def test_apply_overwrites_stale_file(self, tmp_path: Path) -> None:
        """apply() replaces stale tasks-outline with new template content."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n")

        agent_dir = tmp_path / ".claude" / "commands"
        agent_dir.mkdir(parents=True)
        stale = agent_dir / "spec-kitty.tasks-outline.md"
        stale.write_text("Create `tasks.md`", encoding="utf-8")

        new_content = "# New wps.yaml instructions\nCreate `wps.yaml`"

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()

        with patch(
            "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates._get_runtime_command_templates_dir"
        ) as mock_dir, patch(
            "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates._render_full_prompt",
            return_value=new_content,
        ):
            mock_dir.return_value = MagicMock()  # non-None
            result = migration.apply(tmp_path)

        assert result.success
        assert stale.read_text() == new_content
        assert len(result.changes_made) == 1

    def test_apply_is_idempotent(self, tmp_path: Path) -> None:
        """apply() on a fresh file (no stale marker) makes no changes."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n")

        agent_dir = tmp_path / ".claude" / "commands"
        agent_dir.mkdir(parents=True)
        fresh = agent_dir / "spec-kitty.tasks-outline.md"
        fresh.write_text("Create `wps.yaml`", encoding="utf-8")  # no stale marker

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()
        result = migration.apply(tmp_path)

        assert result.success
        assert len(result.changes_made) == 0  # no files changed

    def test_apply_respects_agent_config(self, tmp_path: Path) -> None:
        """apply() only processes configured agents."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        # Only opencode configured; claude NOT configured
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - opencode\n")

        # Create stale file in claude (NOT configured)
        claude_dir = tmp_path / ".claude" / "commands"
        claude_dir.mkdir(parents=True)
        stale_claude = claude_dir / "spec-kitty.tasks-outline.md"
        stale_claude.write_text("Create `tasks.md`")

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )
        migration = UpdatePlanningTemplatesMigration()
        # detect() should not see the claude file as stale (not configured)
        assert migration.detect(tmp_path) is False
```

---

## Definition of Done

- [ ] `tasks-outline.md` instructs LLM to produce `wps.yaml`, not `tasks.md`; contains wps.yaml schema example
- [ ] `tasks-packages.md` instructs LLM to read/update `wps.yaml`; warns not to modify explicit `dependencies` fields
- [ ] `m_3_2_0_update_planning_templates.py` registered with `@MigrationRegistry.register`
- [ ] `detect()` returns True for files with `"Create \`tasks.md\`"`, False otherwise
- [ ] `apply()` uses `get_agent_dirs_for_project()` (config-aware)
- [ ] T025, T026 tests pass
- [ ] `mypy --strict` passes on migration file

## Reviewer Guidance

- Verify `target_version = "3.2.0"` matches the pyproject.toml version that will ship this feature
- Confirm the migration only imports from `m_2_1_3_restore_prompt_commands` (same-package, safe) and `m_0_9_1_complete_lane_migration` (pattern used by all other migrations)
- The stale marker `"Create \`tasks.md\`"` must exactly match a string in the current `tasks-outline.md` Purpose section — verify before committing

## Activity Log

- 2026-04-07T12:09:57Z – unknown – shell_pid=16944 – T022-T026: templates rewritten for wps.yaml, migration m_3_2_0 with detect/apply/tests (16 tests, all passing)
