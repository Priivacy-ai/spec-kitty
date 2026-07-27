---
work_package_id: WP04
title: Atomic Write Conversion — Local State Files
dependencies: [WP01]
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- FR-016
- NFR-001
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Hardening
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9Q0
owned_files:
- src/specify_cli/constitution/context.py
- src/specify_cli/core/atomic.py
- src/specify_cli/dashboard/lifecycle.py
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/upgrade/metadata.py
- src/specify_cli/workspace_context.py
wp_code: WP04
---

# Work Package Prompt: WP04 – Atomic Write Conversion — Local State Files

## Objectives & Success Criteria

- Convert 5 local-state write paths to use the shared `atomic_write()` from `src/specify_cli/core/atomic.py`.
- Each converted path produces identical file content as before.
- No `.write_text()` or direct `open() + dump()` patterns remain in these 5 modules for their state files.

## Context & Constraints

- **Depends on WP01**: The shared `atomic_write()` utility must exist.
- **Pattern**: For each module, the conversion follows: serialize content to string → call `atomic_write(path, content, mkdir=True)`.
- **Constraint C-004**: Temp files in same directory as target.

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T014 – Convert runtime_bridge.py

**Purpose**: Make `.kittify/runtime/feature-runs.json` writes atomic.

**Steps**:

1. In `src/specify_cli/next/runtime_bridge.py`, find `_save_feature_runs()` (lines 73-76):
   ```python
   def _save_feature_runs(repo_root: Path, index: dict[str, dict[str, str]]) -> None:
       path = _feature_runs_path(repo_root)
       path.parent.mkdir(parents=True, exist_ok=True)
       path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
   ```

2. Replace with:
   ```python
   from specify_cli.core.atomic import atomic_write

   def _save_feature_runs(repo_root: Path, index: dict[str, dict[str, str]]) -> None:
       path = _feature_runs_path(repo_root)
       content = json.dumps(index, indent=2, sort_keys=True)
       atomic_write(path, content, mkdir=True)
   ```

**Files**: `src/specify_cli/next/runtime_bridge.py`

### Subtask T015 – Convert workspace_context.py

**Purpose**: Make `.kittify/workspaces/*.json` writes atomic.

**Steps**:

1. In `src/specify_cli/workspace_context.py`, find `save_context()` (lines 89-108):
   ```python
   context_path.write_text(
       json.dumps(context.to_dict(), indent=2) + "\n",
       encoding="utf-8"
   )
   ```

2. Replace with:
   ```python
   from specify_cli.core.atomic import atomic_write

   content = json.dumps(context.to_dict(), indent=2) + "\n"
   atomic_write(context_path, content)
   ```

3. Note: `save_context()` also calls `context_path.parent.mkdir(parents=True, exist_ok=True)` earlier. You can either keep that or use `mkdir=True` on `atomic_write`. Check if the mkdir is also needed for the directory creation (not just the parent).

**Files**: `src/specify_cli/workspace_context.py`

### Subtask T016 – Convert constitution/context.py

**Purpose**: Make `.kittify/constitution/context-state.json` writes atomic.

**Steps**:

1. In `src/specify_cli/constitution/context.py`, find `_write_state()` (lines 213-215):
   ```python
   def _write_state(path: Path, state: dict[str, object]) -> None:
       path.parent.mkdir(parents=True, exist_ok=True)
       path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
   ```

2. Replace with:
   ```python
   from specify_cli.core.atomic import atomic_write

   def _write_state(path: Path, state: dict[str, object]) -> None:
       content = json.dumps(state, indent=2, sort_keys=True)
       atomic_write(path, content, mkdir=True)
   ```

**Files**: `src/specify_cli/constitution/context.py`

### Subtask T017 – Convert dashboard/lifecycle.py

**Purpose**: Make `.kittify/.dashboard` writes atomic.

**Steps**:

1. In `src/specify_cli/dashboard/lifecycle.py`, find `_write_dashboard_file()` (lines 77-99):
   ```python
   dashboard_file.parent.mkdir(parents=True, exist_ok=True)
   lines = [url, str(port)]
   if token:
       lines.append(token)
   if pid is not None:
       lines.append(str(pid))
   dashboard_file.write_text("\n".join(lines) + "\n", encoding='utf-8')
   ```

2. Replace the write with:
   ```python
   from specify_cli.core.atomic import atomic_write

   content = "\n".join(lines) + "\n"
   atomic_write(dashboard_file, content, mkdir=True)
   ```

**Files**: `src/specify_cli/dashboard/lifecycle.py`

### Subtask T018 – Convert upgrade/metadata.py

**Purpose**: Make `.kittify/metadata.yaml` writes atomic.

**Steps**:

1. In `src/specify_cli/upgrade/metadata.py`, find `ProjectMetadata.save()` (lines 105-149):
   ```python
   with open(metadata_path, "w", encoding="utf-8") as f:
       f.write(header)
       yaml.dump(data, f, default_flow_style=False, sort_keys=False)
   ```

2. Replace with string serialization then atomic write:
   ```python
   import io
   from specify_cli.core.atomic import atomic_write

   # Serialize to string
   buf = io.StringIO()
   buf.write(header)
   yaml.dump(data, buf, default_flow_style=False, sort_keys=False)
   content = buf.getvalue()

   atomic_write(metadata_path, content, mkdir=True)
   ```

3. Remove the `kittify_dir.mkdir(parents=True, exist_ok=True)` call — `mkdir=True` handles it.

**Files**: `src/specify_cli/upgrade/metadata.py`

**Edge Case**: Verify that `yaml.dump()` to `StringIO` produces identical output to `yaml.dump()` to a file handle. Test by comparing before/after.

## Test Strategy

For each converted module, add or verify a test that:
1. Writes state successfully.
2. Reads it back and confirms content integrity.
3. (Optional) Mocks `os.replace` to raise and confirms original is preserved.

Run: `pytest tests/ -k "runtime_bridge or workspace_context or constitution or dashboard or metadata" -v`

## Risks & Mitigations

- **YAML StringIO divergence**: `yaml.dump(data, StringIO())` vs `yaml.dump(data, file)` should be identical, but test to confirm.
- **Permission changes**: `os.replace()` creates a new inode. If any code checks file permissions after write, it may see different permissions. Not expected for these 5 files.

## Review Guidance

- Verify each module no longer has direct `write_text()` or `open() + dump()` for its state file.
- Verify `mkdir=True` is used where the original code created parent directories.
- Verify content output is byte-identical before and after conversion.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
