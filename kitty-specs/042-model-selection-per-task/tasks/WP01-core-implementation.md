---
work_package_id: WP01
title: Core Implementation
lane: "done"
dependencies: []
base_branch: 042-model-selection-per-task
base_commit: cd9aec8b060c3603e8eb509ad8cf777751135653
created_at: '2026-03-09T11:21:04.235231+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundation
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: "40682"
review_status: "approved"
reviewed_by: "Zohar Stolar"
history:
- timestamp: '2026-03-09T11:13:06Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
---

# Work Package Prompt: WP01 – Core Implementation

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above. If `has_feedback`, read the Review Feedback section first.
- **Mark as acknowledged**: Set `review_status: acknowledged` when you start addressing feedback.

---

## Review Feedback

*[Empty — reviewers will populate if work is returned.]*

---

## Objectives & Success Criteria

Implement two new files:
1. `src/specify_cli/global_config.py` — reads `~/.spec-kitty/config.yaml` and returns a model mapping
2. `src/specify_cli/upgrade/migrations/m_2_0_4_model_injection.py` — injects `model:` frontmatter into agent command files during `spec-kitty upgrade`

**Done when**:
- `spec-kitty upgrade` on a project with a `~/.spec-kitty/config.yaml` injects the correct `model:` values into matching command files for all configured agents
- A project with no `~/.spec-kitty/config.yaml` runs upgrade without any change to existing behaviour
- Migration is idempotent (safe to run multiple times)
- A malformed `~/.spec-kitty/config.yaml` causes upgrade to abort with a clear error

## Context & Constraints

- **Spec**: `kitty-specs/042-model-selection-per-task/spec.md`
- **Plan**: `kitty-specs/042-model-selection-per-task/plan.md`
- **Data model**: `kitty-specs/042-model-selection-per-task/data-model.md`
- **Global config location**: `~/.spec-kitty/config.yaml` (consistent with `collaboration/session.py`, `events/store.py`)
- **MANDATORY**: All frontmatter reads/writes MUST go through `FrontmatterManager` from `src/specify_cli/frontmatter.py`
- **MANDATORY**: Use `get_agent_dirs_for_project()` from `src/specify_cli/agent_utils/directories.py` (not hardcoded `AGENT_DIRS`)
- **Implement command** (no dependencies): `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/specify_cli/global_config.py`

**Purpose**: Provide a single, well-tested entry point for reading the user's global model mapping from `~/.spec-kitty/config.yaml`.

**Steps**:

1. Create `src/specify_cli/global_config.py` with the following:

```python
"""Global user configuration for spec-kitty.

Reads ~/.spec-kitty/config.yaml and provides model mapping per command.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

# Commands that can have a model assigned
KNOWN_COMMANDS = frozenset([
    "specify", "plan", "tasks", "implement", "review",
    "accept", "merge", "clarify", "status", "checklist",
    "analyze", "research",
])

_GLOBAL_CONFIG_PATH = Path.home() / ".spec-kitty" / "config.yaml"


class GlobalConfigError(Exception):
    """Raised when the global config file is malformed."""


def load_model_mapping(home: Optional[Path] = None) -> dict[str, str]:
    """Return {command_name: model_string} from ~/.spec-kitty/config.yaml.

    Returns an empty dict if:
    - The config file does not exist
    - The file exists but has no `models:` key

    Raises:
        GlobalConfigError: If the YAML is malformed or `models:` is not a dict
    """
    config_path = (home or Path.home()) / ".spec-kitty" / "config.yaml"
    if not config_path.exists():
        return {}

    yaml = YAML()
    try:
        data = yaml.load(config_path)
    except ScannerError as e:
        raise GlobalConfigError(
            f"Malformed global config at {config_path}: {e}"
        ) from e

    if data is None or "models" not in data:
        return {}

    models = data["models"]
    if not isinstance(models, dict):
        raise GlobalConfigError(
            f"Expected `models:` to be a mapping in {config_path}, got {type(models).__name__}"
        )

    return {str(k): str(v) for k, v in models.items()}


def get_unknown_commands(mapping: dict[str, str]) -> list[str]:
    """Return command names in mapping that are not in KNOWN_COMMANDS."""
    return [k for k in mapping if k not in KNOWN_COMMANDS]
```

2. Add `GlobalConfigError` and the two functions to `src/specify_cli/__init__.py` exports if appropriate (check existing pattern — only export if the module has an `__all__`).

**Files**:
- `src/specify_cli/global_config.py` (new, ~60 lines)

**Notes**:
- The `home` parameter exists purely for testability — production callers pass `None` (uses `Path.home()`)
- `ruamel.yaml` is already a project dependency; no new dependencies needed

---

### Subtask T002 – Create `src/specify_cli/upgrade/migrations/m_2_0_4_model_injection.py`

**Purpose**: The migration that wires the global config into the upgrade pipeline. On every `spec-kitty upgrade`, this migration reads the user's model mapping and injects/updates/removes `model:` in the frontmatter of each matching agent command file.

**Steps**:

1. Create the migration file. Pattern it after `m_2_0_1_fix_generated_command_templates.py`:

```python
"""Migration: Inject model: frontmatter into agent command files from global config."""
from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from specify_cli.agent_utils.directories import get_agent_dirs_for_project
from specify_cli.frontmatter import FrontmatterManager, FrontmatterError
from specify_cli.global_config import (
    GlobalConfigError,
    get_unknown_commands,
    load_model_mapping,
)


@MigrationRegistry.register
class ModelInjectionMigration(BaseMigration):
    """Inject model: frontmatter into agent command files based on global config."""

    migration_id = "2.0.4_model_injection"
    description = "Inject model selection into agent command frontmatter from ~/.spec-kitty/config.yaml"
    target_version = "2.0.4"

    FILE_GLOB = "spec-kitty.*.md"

    def detect(self, project_path: Path) -> bool:
        """True if global config has a models: section with at least one entry."""
        try:
            mapping = load_model_mapping()
            return bool(mapping)
        except GlobalConfigError:
            return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        result = MigrationResult(success=True)

        # Load global model mapping
        try:
            mapping = load_model_mapping()
        except GlobalConfigError as e:
            result.success = False
            result.errors.append(str(e))
            return result

        # No config → nothing to do (backwards-compatible no-op)
        if not mapping:
            return result

        # Warn on unknown command names
        unknowns = get_unknown_commands(mapping)
        for unknown in unknowns:
            result.warnings.append(
                f"Unknown command '{unknown}' in ~/.spec-kitty/config.yaml models: — ignored"
            )

        fm = FrontmatterManager()
        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue

            for cmd_file in agent_dir.glob(self.FILE_GLOB):
                # Extract command name: "spec-kitty.specify.md" → "specify"
                parts = cmd_file.stem.split(".", 1)
                if len(parts) != 2:
                    continue
                cmd_name = parts[1]

                try:
                    self._process_file(cmd_file, cmd_name, mapping, fm, dry_run, result)
                except FrontmatterError as e:
                    result.warnings.append(f"Skipped {cmd_file}: {e}")

        return result

    def _process_file(
        self,
        cmd_file: Path,
        cmd_name: str,
        mapping: dict[str, str],
        fm: FrontmatterManager,
        dry_run: bool,
        result: MigrationResult,
    ) -> None:
        """Inject, update, or remove model: field in a single command file."""
        desired_model = mapping.get(cmd_name)  # None if not in config

        # Read existing frontmatter (may be absent)
        try:
            frontmatter, body = fm.read(cmd_file)
        except FrontmatterError:
            frontmatter, body = {}, cmd_file.read_text(encoding="utf-8")

        current_model = frontmatter.get("model")

        if desired_model is None:
            # Command not in config → remove model: if present
            if "model" not in frontmatter:
                return  # nothing to do
            if not dry_run:
                del frontmatter["model"]
                fm.write(cmd_file, frontmatter, body)
            result.changes_made.append(f"Removed model: from {cmd_file.relative_to(cmd_file.parent.parent.parent)}")
        else:
            # Command in config → inject or update
            if current_model == desired_model:
                return  # already correct
            if not dry_run:
                frontmatter["model"] = desired_model
                fm.write(cmd_file, frontmatter, body)
            result.changes_made.append(
                f"Set model: {desired_model} in {cmd_file.relative_to(cmd_file.parent.parent.parent)}"
            )
```

**Files**:
- `src/specify_cli/upgrade/migrations/m_2_0_4_model_injection.py` (new, ~110 lines)

**Notes**:
- `@MigrationRegistry.register` decorator auto-registers — no manual registry edit needed (verify this matches how other migrations register)
- `migration_id` ordering: the registry sorts by version string; `2.0.4` will run after `2.0.1`

---

### Subtask T003 – Handle edge cases: no-frontmatter files and stale model removal

**Purpose**: Ensure the migration gracefully handles command files that have no YAML frontmatter block, and correctly cleans up `model:` when a command is removed from the user's config.

**Steps**:

1. **No-frontmatter case**: When `fm.read()` raises `FrontmatterError` (file has no `---` block), fall back to treating `frontmatter = {}` and `body = full_file_content`. When writing back, `fm.write()` will prepend the frontmatter block.

   Verify `FrontmatterManager.write()` behaviour with an empty-frontmatter baseline file. Read `src/specify_cli/frontmatter.py` to confirm the `write()` signature and whether it handles `{}` frontmatter correctly. If `write()` requires at least one key, add `description: ""` as a sentinel, or write the block manually.

2. **Stale model removal**: The `_process_file` logic already handles this (the `desired_model is None` branch). Double-check that after removal and re-write, the frontmatter block is not left empty (some agents may break on `---\n---`). If the result would be an empty frontmatter, remove the block entirely.

3. **Read `FrontmatterManager` source** to understand exact API before finalising:
   ```bash
   # From repo root:
   grep -n "def read\|def write\|def normalize" src/specify_cli/frontmatter.py
   ```

**Files**: Modifications to `m_2_0_4_model_injection.py` from T002 (no new files)

**Notes**:
- The distinction between "no frontmatter" and "malformed frontmatter" matters — only skip on truly malformed YAML, not on absent frontmatter

---

### Subtask T004 – Verify migration auto-registration and ordering

**Purpose**: Confirm the migration integrates correctly with the upgrade pipeline without manual wiring.

**Steps**:

1. Check how `MigrationRegistry.register` works — read `src/specify_cli/upgrade/registry.py` to understand if migrations auto-import or need explicit import:
   ```bash
   grep -n "import\|register\|discover" src/specify_cli/upgrade/registry.py | head -30
   grep -rn "m_2_0_1\|m_0_9_1" src/specify_cli/upgrade/ --include="*.py" | grep import
   ```

2. If migrations need to be explicitly imported (e.g., there's an `__init__.py` that imports all migrations), add the import for `m_2_0_4_model_injection`.

3. Verify version ordering: the registry should sort `2.0.4` after `2.0.1`. If it uses string sort, `2.0.4 > 2.0.1` ✓. If numeric, confirm the comparison logic handles it.

4. Run a quick smoke test:
   ```bash
   cd /path/to/any/spec-kitty-project
   spec-kitty upgrade --dry-run
   ```
   The migration should appear in the list of pending migrations (or "nothing to do" if already applied).

**Files**:
- `src/specify_cli/upgrade/__init__.py` or migration registry file — add import if required

---

## Test Strategy

Tests live in WP02. Manual validation:

```bash
# Create test config
mkdir -p ~/.spec-kitty
cat > ~/.spec-kitty/config.yaml << 'EOF'
models:
  specify: claude-opus-4-6
  implement: claude-sonnet-4-6
EOF

# Run upgrade in this project
spec-kitty upgrade

# Verify injection
head -6 .claude/commands/spec-kitty.specify.md
# Expected: model: claude-opus-4-6 in frontmatter

head -6 .claude/commands/spec-kitty.implement.md
# Expected: model: claude-sonnet-4-6 in frontmatter

head -6 .claude/commands/spec-kitty.plan.md
# Expected: no model: field (not in config)
```

## Risks & Mitigations

- **`FrontmatterManager.write()` API mismatch**: Read `frontmatter.py` source before assuming the signature. The `write()` method may need specific arguments.
- **Empty frontmatter after removal**: Guard against writing `---\n---` which may confuse agents. If all keys removed, delete the frontmatter block.
- **Registry import**: Check if migrations need to be explicitly imported. Missing import = migration silently never runs.
- **`ruamel.yaml` import in migration**: `global_config.py` uses `ruamel.yaml` directly; the migration imports `global_config`. No circular deps — verify with a quick import test.

## Review Guidance

Reviewers should verify:
- [ ] `~/.spec-kitty/config.yaml` with model mapping → correct `model:` injected in all configured agent command files
- [ ] No config file → upgrade runs without error, no frontmatter changes
- [ ] Partial config (some commands only) → only mapped commands get `model:`, others untouched
- [ ] Config with unknown command name → warning printed, upgrade continues
- [ ] Malformed YAML in config → upgrade aborts with clear error message pointing to the file
- [ ] Running upgrade twice → idempotent (no duplicate fields, no spurious changes)
- [ ] Command removed from config → `model:` field removed from frontmatter on next upgrade
- [ ] Migration appears in `spec-kitty upgrade` output

## Activity Log

- 2026-03-09T11:13:06Z – system – lane=planned – Prompt created.
- 2026-03-09T11:21:04Z – claude-sonnet-4-6 – shell_pid=38532 – lane=doing – Assigned agent via workflow command
- 2026-03-09T11:36:46Z – claude-sonnet-4-6 – shell_pid=38532 – lane=for_review – Implemented global_config.py and m_2_0_4_model_injection.py. Auto-registration verified. Smoke tests pass.
- 2026-03-09T11:39:53Z – claude-sonnet-4-6 – shell_pid=40682 – lane=doing – Started review via workflow command
- 2026-03-09T11:47:11Z – claude-sonnet-4-6 – shell_pid=40682 – lane=done – Review passed. Fixed: import convention (m_0_9_1 alias), removed dead FrontmatterError except, added detect() comment, Optional->Path|None. Tests covered by WP02.
