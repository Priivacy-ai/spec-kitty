---
work_package_id: WP02
title: Add wps_manifest module
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-007
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-069-planning-pipeline-integrity
base_commit: 1423753b3ab63d421652c24fee008f2863be2e1c
created_at: '2026-04-07T11:48:00.612086+00:00'
subtasks: [T007, T008, T009, T010, T011, T012, T013, T014]
shell_pid: '9844'
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
owned_files:
- src/specify_cli/core/wps_manifest.py
- src/specify_cli/schemas/wps.schema.json
- tests/core/test_wps_manifest.py
---

# WP02: Add wps_manifest Module

## Objective

Create `src/specify_cli/core/wps_manifest.py` — the standalone module that WP03 (finalize-tasks integration) and WP04 (template updates) depend on. Includes the Pydantic data model, YAML loader, presence-tracking helper, tasks.md generator, and published JSON Schema.

**Success criterion**: `from specify_cli.core.wps_manifest import load_wps_manifest` works; all public functions behave as specified; JSON Schema file is valid Draft 2020-12.

## Context

The `wps.yaml` manifest is a new file format introduced in this feature. It is the primary source of truth for WP metadata in new missions. The module must:
- Load `wps.yaml` if it exists, return `None` if absent (allowing legacy fallback in `finalize-tasks`)
- Track whether the `dependencies` key was explicitly present in the YAML (distinct from the Pydantic default `[]`)
- Generate a human-readable `tasks.md` from the manifest for display purposes
- Validate the YAML structure and report field-level errors with actionable messages

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (worktree for this lane)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP02`

---

## Subtask T007: Define Pydantic models

**Purpose**: Establish the data model for `WorkPackageEntry` and `WpsManifest`.

**File**: `src/specify_cli/core/wps_manifest.py` (new)

```python
"""Structured WP manifest reader for wps.yaml.

Provides the canonical data model, YAML loader, and tasks.md generator
for spec-kitty missions that use wps.yaml as their primary WP source.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorkPackageEntry(BaseModel):
    """One work package entry in wps.yaml."""

    id: str                    # e.g. "WP01" — validated as WPnn pattern
    title: str
    dependencies: list[str] = Field(default_factory=list)
    owned_files: list[str] = Field(default_factory=list)
    requirement_refs: list[str] = Field(default_factory=list)
    subtasks: list[str] = Field(default_factory=list)
    prompt_file: str | None = None

    # Internal: True when 'dependencies' key was present in the source YAML.
    # Set by load_wps_manifest(); NOT part of the serialized schema.
    _dependencies_explicit: bool = False


class WpsManifest(BaseModel):
    """Top-level wps.yaml manifest."""

    work_packages: list[WorkPackageEntry]
```

**Validation rules** to add via Pydantic `field_validator`:
- `id` must match `^WP\d{2}$` — raise `ValueError` with message `"WP id must be WPnn (e.g. WP01), got: {value}"`
- Each item in `dependencies` must match `^WP\d{2}$`

---

## Subtask T008: Implement `load_wps_manifest()`

**Purpose**: Load `feature_dir/wps.yaml` using `ruamel.yaml`, track which WP entries had an explicit `dependencies` key, validate with Pydantic.

**File**: `src/specify_cli/core/wps_manifest.py`

```python
from ruamel.yaml import YAML


def load_wps_manifest(feature_dir: Path) -> WpsManifest | None:
    """Load wps.yaml from feature_dir if present.

    Returns None if wps.yaml does not exist (legacy mission — use prose parser).
    Raises pydantic.ValidationError if the file exists but is malformed,
    with the failing field name and value in the error message.

    Args:
        feature_dir: Path to the kitty-specs/<mission>/ directory.
    """
    wps_path = feature_dir / "wps.yaml"
    if not wps_path.exists():
        return None

    yaml = YAML(typ="safe")
    raw: dict[str, Any] = yaml.load(wps_path)

    # Track explicit dependencies before Pydantic validation
    wps_raw: list[dict] = raw.get("work_packages", [])
    manifest = WpsManifest.model_validate(raw)

    # Back-fill _dependencies_explicit on each entry
    for entry, raw_wp in zip(manifest.work_packages, wps_raw):
        object.__setattr__(entry, "_dependencies_explicit", "dependencies" in raw_wp)

    return manifest
```

**Error handling**: Let Pydantic's `ValidationError` propagate as-is. The caller (`finalize-tasks`) will catch it and emit a user-readable error with `exc.errors()`.

**Notes**:
- `ruamel.yaml` `YAML(typ="safe")` is the charter-mandated parser.
- `object.__setattr__` bypasses Pydantic's immutability for the private field. Alternatively, use a `PrivateAttr(default=False)` approach from Pydantic v2.

---

## Subtask T009: Implement `dependencies_are_explicit()`

**Purpose**: Public helper for `finalize-tasks` to check whether to protect the `dependencies` field (FR-007).

**File**: `src/specify_cli/core/wps_manifest.py`

```python
def dependencies_are_explicit(entry: WorkPackageEntry) -> bool:
    """Return True if the 'dependencies' key was present in the source YAML.

    When True, the pipeline must not overwrite or augment the value.
    When False, the field was absent from YAML and may be populated by tasks-packages.
    """
    return getattr(entry, "_dependencies_explicit", False)
```

**Distinction**:
- `dependencies_are_explicit(e) == True, e.dependencies == []` → explicitly declared as no-deps; pipeline must NOT add anything
- `dependencies_are_explicit(e) == False, e.dependencies == []` → absent from YAML; pipeline may populate

---

## Subtask T010: Implement `generate_tasks_md_from_manifest()`

**Purpose**: Generate a human-readable `tasks.md` from a `WpsManifest`. Output follows the structure expected by downstream tools that parse `tasks.md` (titles, dependency lines, requirement refs).

**File**: `src/specify_cli/core/wps_manifest.py`

```python
def generate_tasks_md_from_manifest(manifest: WpsManifest, feature_name: str) -> str:
    """Generate tasks.md content from a WpsManifest.

    Output is a human-readable markdown document following tasks-template.md
    conventions. Does NOT include implementation notes or risks — those live
    in the WP prompt files.

    Args:
        manifest: Loaded WpsManifest.
        feature_name: Mission slug or friendly name for the heading.
    """
    lines: list[str] = [
        f"# Work Packages: {feature_name}",
        "",
        "_Generated by finalize-tasks from wps.yaml. Do not edit directly._",
        "",
        "---",
        "",
    ]

    for wp in manifest.work_packages:
        lines.append(f"## Work Package {wp.id}: {wp.title}")
        lines.append("")

        if wp.dependencies:
            lines.append(f"**Dependencies**: {', '.join(wp.dependencies)}")
        else:
            lines.append("**Dependencies**: None")

        if wp.requirement_refs:
            lines.append(f"**Requirement Refs**: {', '.join(wp.requirement_refs)}")

        if wp.owned_files:
            lines.append(f"**Owned Files**: {', '.join(wp.owned_files)}")

        if wp.subtasks:
            lines.append(f"**Subtasks**: {', '.join(wp.subtasks)}")

        if wp.prompt_file:
            lines.append(f"**Prompt**: `{wp.prompt_file}`")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
```

**C-007 compliance**: The output must include WP titles, dependencies, and subtask counts. Verify:
- Every WP has a heading with its title
- Dependencies are listed (even when empty: "None")
- Subtask IDs are listed

---

## Subtask T011: Write `src/specify_cli/schemas/wps.schema.json`

**Purpose**: Publish the authoritative JSON Schema for `wps.yaml` (FR-005).

**File**: `src/specify_cli/schemas/wps.schema.json` (create `src/specify_cli/schemas/` directory if absent)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://spec-kitty.ai/schemas/wps.schema.json",
  "title": "WPS Manifest",
  "description": "Structured work package manifest for spec-kitty missions. Place at kitty-specs/<mission-slug>/wps.yaml.",
  "type": "object",
  "required": ["work_packages"],
  "additionalProperties": false,
  "properties": {
    "work_packages": {
      "type": "array",
      "minItems": 1,
      "description": "Ordered list of work packages for this mission.",
      "items": {
        "type": "object",
        "required": ["id", "title"],
        "additionalProperties": false,
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^WP\\d{2}$",
            "description": "Work package identifier, e.g. WP01, WP12."
          },
          "title": {
            "type": "string",
            "minLength": 1,
            "description": "Human-readable WP title."
          },
          "dependencies": {
            "type": "array",
            "items": {"type": "string", "pattern": "^WP\\d{2}$"},
            "default": [],
            "description": "WP IDs this WP depends on. Present-but-empty [] is authoritative and will not be modified by the pipeline."
          },
          "owned_files": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Glob patterns for files exclusively owned by this WP."
          },
          "requirement_refs": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Spec requirement IDs (e.g. FR-001, NFR-002)."
          },
          "subtasks": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Subtask IDs (e.g. T001)."
          },
          "prompt_file": {
            "type": ["string", "null"],
            "default": null,
            "description": "Relative path to the WP prompt file (e.g. tasks/WP01-title.md)."
          }
        }
      }
    }
  }
}
```

---

## Subtask T012: Unit tests — load, absent, malformed

**File**: `tests/core/test_wps_manifest.py` (new)

```python
"""Unit tests for wps_manifest module."""
from __future__ import annotations

from pathlib import Path
import pytest
from pydantic import ValidationError
from specify_cli.core.wps_manifest import load_wps_manifest, WpsManifest


class TestLoadWpsManifest:
    def test_load_valid_manifest(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'First WP'\n"
            "    dependencies: []\n",
            encoding="utf-8"
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert len(manifest.work_packages) == 1
        assert manifest.work_packages[0].id == "WP01"

    def test_absent_returns_none(self, tmp_path: Path) -> None:
        result = load_wps_manifest(tmp_path)
        assert result is None

    def test_malformed_raises_validation_error_with_field_name(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: INVALID_ID\n    title: 'test'\n",
            encoding="utf-8"
        )
        with pytest.raises(ValidationError) as exc_info:
            load_wps_manifest(tmp_path)
        error_str = str(exc_info.value)
        assert "id" in error_str or "WP" in error_str  # field name appears in error

    def test_missing_required_title_raises(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n",  # missing title
            encoding="utf-8"
        )
        with pytest.raises(ValidationError):
            load_wps_manifest(tmp_path)
```

---

## Subtask T013: Unit tests — `dependencies_are_explicit`

**File**: `tests/core/test_wps_manifest.py`

```python
from specify_cli.core.wps_manifest import dependencies_are_explicit

class TestDependenciesAreExplicit:
    def test_present_empty_list_is_explicit(self, tmp_path: Path) -> None:
        """dependencies: [] in YAML → explicit."""
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n    title: 'T'\n    dependencies: []\n",
            encoding="utf-8"
        )
        manifest = load_wps_manifest(tmp_path)
        assert dependencies_are_explicit(manifest.work_packages[0]) is True

    def test_absent_key_is_not_explicit(self, tmp_path: Path) -> None:
        """No 'dependencies' key in YAML → not explicit."""
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n    title: 'T'\n",
            encoding="utf-8"
        )
        manifest = load_wps_manifest(tmp_path)
        assert dependencies_are_explicit(manifest.work_packages[0]) is False

    def test_present_nonempty_list_is_explicit(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP02\n    title: 'T'\n    dependencies: [WP01]\n",
            encoding="utf-8"
        )
        manifest = load_wps_manifest(tmp_path)
        assert dependencies_are_explicit(manifest.work_packages[0]) is True
```

---

## Subtask T014: Unit tests — `generate_tasks_md_from_manifest`

**File**: `tests/core/test_wps_manifest.py`

```python
from specify_cli.core.wps_manifest import generate_tasks_md_from_manifest, WpsManifest, WorkPackageEntry

class TestGenerateTasksMd:
    def _make_manifest(self) -> WpsManifest:
        return WpsManifest(work_packages=[
            WorkPackageEntry(id="WP01", title="First", dependencies=[], subtasks=["T001", "T002"],
                             requirement_refs=["FR-001"]),
            WorkPackageEntry(id="WP02", title="Second", dependencies=["WP01"]),
        ])

    def test_contains_all_wp_titles(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "First" in md
        assert "Second" in md

    def test_contains_dependency_lines(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "WP01" in md  # WP02 depends on WP01

    def test_empty_deps_shows_none(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "None" in md  # WP01 has no deps

    def test_subtask_ids_present(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "T001" in md
        assert "T002" in md

    def test_has_generated_header_note(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "Generated by finalize-tasks" in md
```

---

## Definition of Done

- [x] `src/specify_cli/core/wps_manifest.py` exists with all 4 public symbols exported: `WorkPackageEntry`, `WpsManifest`, `load_wps_manifest`, `dependencies_are_explicit`, `generate_tasks_md_from_manifest`
- [x] `src/specify_cli/schemas/wps.schema.json` exists and validates as JSON Schema Draft 2020-12
- [x] `tests/core/test_wps_manifest.py` passes with pytest
- [x] `mypy --strict src/specify_cli/core/wps_manifest.py` passes
- [x] `load_wps_manifest(absent_dir)` returns `None` in < 10ms (NFR-003)

## Reviewer Guidance

- Confirm `_dependencies_explicit` is NOT serialized by Pydantic (it must be a `PrivateAttr` or excluded field, not a schema field)
- Confirm `generate_tasks_md_from_manifest()` output contains WP titles and dependency lines (C-007)
- Verify `ValidationError` raised by `load_wps_manifest()` includes the field name in the error message (NFR-002)
