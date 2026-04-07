---
work_package_id: WP03
title: Integrate wps.yaml into finalize-tasks
dependencies: [WP02]
requirement_refs:
- C-006
- FR-006
- FR-007
- FR-008
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T015, T016, T017, T018, T019, T020, T021]
shell_pid: '13338'
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- tests/tasks/test_finalize_tasks_wps_yaml_unit.py
---

# WP03: Integrate wps.yaml into finalize-tasks

## Objective

Update `finalize_tasks()` in `mission.py` to:
1. Use `wps.yaml` as the authoritative dependency source when present (tier 0 — bypasses prose parser)
2. Regenerate `tasks.md` from the manifest after processing

**Success criterion**: With a `wps.yaml` declaring `WP05: dependencies: []` and a `tasks.md` prose body containing "WP02 (depends on WP01)" inside WP05's section, running `finalize-tasks` leaves WP05 with no dependencies in its frontmatter.

## Context

`finalize_tasks()` in `src/specify_cli/cli/commands/agent/mission.py` (~line 1181) currently:
1. Reads `tasks.md` (line ~1278)
2. Calls `parse_dependencies_from_tasks_md(tasks_content)` (line ~1282) — prose parser
3. Uses the resulting `wp_dependencies` dict to update WP frontmatter

The fix adds a new tier 0 block before this: if `wps.yaml` exists, call `load_wps_manifest()` and derive `wp_dependencies` directly from the manifest. The prose parser block becomes an else branch.

After all processing, if wps.yaml is present, `tasks.md` is regenerated from the manifest.

**WP02 must be merged first** (or at minimum, its module must be importable from the worktree).

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (Lane B worktree, after WP02)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP03`

---

## Subtask T015: Add wps.yaml detection at top of `finalize_tasks()`

**Purpose**: Load manifest and build `wp_dependencies` from it when wps.yaml is present.

**File**: `src/specify_cli/cli/commands/agent/mission.py`

**Location**: Find the section starting around line 1268: `# Parse dependencies and requirement refs using 2-tier priority:`. Insert the new wps.yaml block immediately before this comment.

**Change**:

```python
# ─── TIER 0: wps.yaml manifest (new) ─────────────────────────────────────
from specify_cli.core.wps_manifest import (
    load_wps_manifest,
    dependencies_are_explicit,
    generate_tasks_md_from_manifest,
)
try:
    wps_manifest = load_wps_manifest(feature_dir)
except Exception as exc:
    error_msg = f"wps.yaml is present but could not be loaded: {exc}"
    if json_output:
        _emit_json({"error": error_msg})
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
    raise typer.Exit(1)

# ─── TIER 1+: existing dependency resolution ──────────────────────────────
wp_dependencies: dict[str, list[str]] = {}
wp_requirement_refs = {}

if wps_manifest is not None:
    # Build wp_dependencies from manifest (explicit deps only)
    for entry in wps_manifest.work_packages:
        if dependencies_are_explicit(entry):
            wp_dependencies[entry.id] = list(entry.dependencies)
        else:
            wp_dependencies[entry.id] = []
```

Move the import to the top of the function body or the module-level imports block. Prefer module-level to avoid repeated import overhead on each call.

---

## Subtask T016: Bypass prose parser when wps.yaml present

**Purpose**: The existing `if tasks_md.exists(): ...parse_dependencies_from_tasks_md(tasks_content)` block must be skipped when wps.yaml is the authority.

**File**: `src/specify_cli/cli/commands/agent/mission.py`

**Change** (around line 1278):

```python
# BEFORE:
if tasks_md.exists():
    tasks_content = tasks_md.read_text(encoding="utf-8")
    from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md as _shared_parse_deps
    wp_dependencies = _shared_parse_deps(tasks_content)
    # ... requirement_refs fallback ...

# AFTER:
if wps_manifest is None and tasks_md.exists():  # ← added guard
    tasks_content = tasks_md.read_text(encoding="utf-8")
    from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md as _shared_parse_deps
    wp_dependencies = _shared_parse_deps(tasks_content)
    # ... requirement_refs fallback — unchanged ...
```

The only change is adding `wps_manifest is None and` to the condition. When wps.yaml is present, the entire block is skipped — the existing `wp_dependencies` dict (built in T015) is used.

**Important**: The requirement_refs fallback inside this block (`tasks_md_refs = _parse_requirement_refs_from_tasks_md(tasks_content)`) also gets skipped when wps.yaml is present. This is correct — requirement refs should come from WP frontmatter or wps.yaml's `requirement_refs` field when the manifest is in use.

---

## Subtask T017: Add tasks.md regeneration step

**Purpose**: When wps.yaml is present, regenerate tasks.md from the manifest after all WP frontmatter has been written (FR-008, FR-011).

**File**: `src/specify_cli/cli/commands/agent/mission.py`

**Location**: After the existing WP frontmatter writing block and before the status bootstrap / commit step. Look for the section that writes WP frontmatter files (around line 1300–1400) and insert after it.

**Change**:

```python
# After WP frontmatter is written:
if wps_manifest is not None:
    # Regenerate tasks.md from manifest (FR-008, FR-011)
    tasks_md_content = generate_tasks_md_from_manifest(wps_manifest, mission_slug)
    tasks_md.write_text(tasks_md_content, encoding="utf-8")
    if not json_output:
        console.print(
            f"[green]Regenerated[/green] tasks.md from wps.yaml "
            f"({len(wps_manifest.work_packages)} WPs)"
        )
```

**C-007 compliance**: `generate_tasks_md_from_manifest()` must include WP titles, dependency lines, and subtask counts — verified in WP02's tests.

---

## Subtask T018: Integration test — wps.yaml present, manifest deps used

**Purpose**: End-to-end test that the prose parser is bypassed.

**File**: `tests/tasks/test_finalize_tasks_wps_yaml_unit.py` (new)

```python
"""Unit tests for finalize-tasks with wps.yaml (FR-006, FR-007, FR-012)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.mission import app

pytestmark = pytest.mark.fast
runner = CliRunner()


def _build_feature_with_wps_yaml(
    tmp_path: Path,
    wps_yaml_content: str,
    tasks_md_content: str = "",
) -> Path:
    """Create a minimal feature dir with wps.yaml and optional tasks.md."""
    feature_dir = tmp_path / "kitty-specs" / "069-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Minimal spec.md with a requirement
    (feature_dir / "spec.md").write_text(
        "# Spec\n## Functional Requirements\n"
        "| ID | Requirement | Status |\n| --- | --- | --- |\n"
        "| FR-001 | Test req | proposed |\n",
        encoding="utf-8",
    )

    (feature_dir / "wps.yaml").write_text(wps_yaml_content, encoding="utf-8")

    if tasks_md_content:
        (feature_dir / "tasks.md").write_text(tasks_md_content, encoding="utf-8")

    # Create a WP01 prompt file
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text(
        "---\nwork_package_id: 'WP01'\ntitle: 'Test'\n"
        "dependencies: []\nsubtasks: []\nowned_files: ['src/**']\n"
        "authoritative_surface: 'src/'\nexecution_mode: 'code_change'\n---\n# WP01\n",
        encoding="utf-8",
    )
    return feature_dir


class TestFinalizTasksWithWpsYaml:
    def test_wps_yaml_deps_used_not_prose(self, tmp_path: Path) -> None:
        """wps.yaml dependencies take precedence over tasks.md prose."""
        wps_yaml = (
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'Test'\n"
            "    dependencies: []\n"  # explicit empty
        )
        # tasks.md has a misleading prose dependency reference
        misleading_tasks_md = (
            "## Work Package WP01: Test\n"
            "Depends on WP02, WP03\n"  # this should be IGNORED
        )
        feature_dir = _build_feature_with_wps_yaml(
            tmp_path, wps_yaml, misleading_tasks_md
        )

        with patch("specify_cli.cli.commands.agent.mission.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.agent.mission._ensure_branch_checked_out"), \
             patch("specify_cli.cli.commands.agent.mission._resolve_planning_branch",
                   return_value="main"), \
             patch("specify_cli.cli.commands.agent.mission._commit_files",
                   return_value="abc123"):

            result = runner.invoke(
                app, ["finalize-tasks", "--mission", "069-test", "--json"]
            )

        # WP01 should have no deps despite prose saying it depends on WP02, WP03
        wp_file = feature_dir / "tasks" / "WP01-test.md"
        content = wp_file.read_text()
        assert "WP02" not in content.split("dependencies:")[1][:100]
```

---

## Subtask T019: Integration test — explicit `dependencies: []` not overwritten

**File**: `tests/tasks/test_finalize_tasks_wps_yaml_unit.py`

Test that `dependencies: []` in wps.yaml → after finalize, WP01 frontmatter `dependencies` field is empty/absent (not populated with prose-inferred deps).

```python
    def test_explicit_empty_deps_not_overwritten(self, tmp_path: Path) -> None:
        """FR-007: dependencies: [] in wps.yaml is authoritative, not overwritten."""
        wps_yaml = (
            "work_packages:\n"
            "  - id: WP01\n    title: 'T'\n    dependencies: []\n"
        )
        # Create scenario where prose parser would infer a dependency
        tasks_md = "## WP01: T\nDepends on WP02\n"
        feature_dir = _build_feature_with_wps_yaml(tmp_path, wps_yaml, tasks_md)

        # Also create WP02 prompt file so finalize doesn't complain
        (feature_dir / "tasks" / "WP02-test.md").write_text(
            "---\nwork_package_id: 'WP02'\ntitle: 'T2'\n"
            "dependencies: []\nsubtasks: []\nowned_files: ['tests/**']\n"
            "authoritative_surface: 'tests/'\nexecution_mode: 'code_change'\n---\n",
            encoding="utf-8",
        )

        with patch(...):  # same patches as T018
            runner.invoke(app, ["finalize-tasks", "--mission", "069-test", "--json"])

        wp1_content = (feature_dir / "tasks" / "WP01-test.md").read_text()
        # dependencies line should show [] or be absent — NOT include WP02
        assert "WP02" not in wp1_content
```

---

## Subtask T020: Integration test — tasks.md regenerated

**File**: `tests/tasks/test_finalize_tasks_wps_yaml_unit.py`

```python
    def test_tasks_md_regenerated_from_manifest(self, tmp_path: Path) -> None:
        """FR-011: finalize-tasks regenerates tasks.md when wps.yaml present."""
        wps_yaml = (
            "work_packages:\n"
            "  - id: WP01\n    title: 'My First WP'\n    dependencies: []\n"
        )
        old_tasks_md = "# Old content that should be overwritten\n"
        feature_dir = _build_feature_with_wps_yaml(tmp_path, wps_yaml, old_tasks_md)

        with patch(...):
            runner.invoke(app, ["finalize-tasks", "--mission", "069-test", "--json"])

        new_tasks_md = (feature_dir / "tasks.md").read_text()
        assert "Old content" not in new_tasks_md
        assert "My First WP" in new_tasks_md
        assert "Generated by finalize-tasks" in new_tasks_md
```

---

## Subtask T021: Integration test — no wps.yaml, legacy path unchanged

**File**: `tests/tasks/test_finalize_tasks_wps_yaml_unit.py`

```python
    def test_no_wps_yaml_uses_prose_parser(self, tmp_path: Path) -> None:
        """FR-012: Missions without wps.yaml use prose parser (backward compat)."""
        feature_dir = tmp_path / "kitty-specs" / "069-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        # ... set up feature WITHOUT wps.yaml ...
        tasks_md = (
            "## Work Package WP01: Test\n"
            "Depends on WP02\n"
        )
        (feature_dir / "tasks.md").write_text(tasks_md, encoding="utf-8")
        # ... WP01 prompt file setup, spec.md ...

        with patch(...):
            result = runner.invoke(app, ["finalize-tasks", "--mission", "069-test", "--json"])

        # WP01 should have WP02 in its dependencies (from prose parser)
        wp1_content = (feature_dir / "tasks" / "WP01-test.md").read_text()
        assert "WP02" in wp1_content
```

---

## Definition of Done

- [ ] `finalize_tasks()` checks for `wps.yaml` before calling prose parser
- [ ] When `wps.yaml` present: `wp_dependencies` comes from manifest, prose parser block skipped
- [ ] When `wps.yaml` present: `tasks.md` regenerated after WP frontmatter written
- [ ] When `wps.yaml` absent: existing prose parser behavior completely unchanged
- [ ] T018–T021 tests pass
- [ ] `mypy --strict` passes on `mission.py`

## Reviewer Guidance

- The change is intentionally minimal: one block added before the prose parser, one guard condition (`wps_manifest is None and`) on the existing `if tasks_md.exists():`, and one regeneration block after frontmatter writing.
- Verify the imports (`load_wps_manifest`, `dependencies_are_explicit`, `generate_tasks_md_from_manifest`) don't create a circular import chain. These are `core/` imports from a `cli/commands/agent/` module — no cycle expected.
- Confirm the `wps_manifest is None and` guard correctly preserves legacy behavior: when wps.yaml is absent, the code executes identically to the pre-WP03 version.
