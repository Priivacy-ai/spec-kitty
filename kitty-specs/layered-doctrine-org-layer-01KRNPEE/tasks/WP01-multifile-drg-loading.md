---
work_package_id: WP01
title: Multi-file DRG Loading
dependencies: []
requirement_refs:
- FR-004
- FR-005
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
owned_files:
- src/doctrine/drg/loader.py
- src/doctrine/drg/__init__.py
- src/charter/_drg_helpers.py
- src/charter/synthesizer/validation_gate.py
- src/charter/synthesizer/project_drg.py
- src/charter/synthesizer/resynthesize_pipeline.py
- src/charter/synthesizer/write_pipeline.py
- tests/doctrine/drg/test_loader_multifile.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile scopes your governance context to Python implementation. Apply it before
proceeding.

---

## Objective

Introduce `load_graph_or_dir()` as the single, canonical entry point for DRG graph loading
throughout the spec-kitty codebase. Replace all hardcoded `path / "graph.yaml"` constructions
in `charter/` and `charter/synthesizer/` with calls to this new function. After this WP:

- Any DRG root directory may contain either a single `graph.yaml` or multiple
  `*.graph.yaml` fragment files — both load correctly.
- All existing tests pass unchanged (no behavioral regression).
- WP02 can safely add org-layer graph loading by passing additional roots to
  `load_validated_graph()`.

---

## Context

The DRG (Doctrine Reference Graph) is currently loaded from a single `graph.yaml` file per
layer. The shipped graph alone is 1,856 lines. Two call paths exist:

1. **`_drg_helpers.py`**: `load_validated_graph(repo_root)` — the shared helper used by
   `resolver.py` and `compiler.py` for shipped + project merge. This is the cleanest path.
2. **Direct inline loads**: `context.py`, `compiler.py`, `reference_resolver.py`, and the
   entire `synthesizer/` subdirectory all call `load_graph(path / "graph.yaml")` directly,
   bypassing the helper.

This WP fixes the fragmentation by:
- Adding `load_graph_or_dir()` (single file OR directory of fragments).
- Updating `_drg_helpers.py` to use it.
- Replacing all direct synthesizer inline calls.

`context.py` is **not** owned by this WP — its DRG routing update is handled in WP07.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`; check `lanes.json` for your lane
- **Implement command**: `spec-kitty agent action implement WP01 --agent codex`

---

## Subtask T001 — Add `load_graph_or_dir()` to `loader.py`

**File**: `src/doctrine/drg/loader.py`

**Purpose**: Create the new entry point that accepts either a file path or a directory.
When given a directory, it globs `*.graph.yaml` in alphabetical order, loads each with the
existing `load_graph()`, and reduces with `merge_layers()`. When given a file path, it
delegates to `load_graph()` unchanged.

**Signature**:

```python
def load_graph_or_dir(path: Path) -> DRGGraph:
    """Load a DRGGraph from a file or a directory of fragment files.

    If *path* is a file, delegates to :func:`load_graph`.
    If *path* is a directory, globs ``*.graph.yaml`` in alphabetical order,
    loads each, and merges them left-to-right with :func:`merge_layers`.

    Raises :class:`DRGLoadError` if the path does not exist, is not a file
    or directory, or if any fragment fails to load.
    """
```

**Implementation notes**:
- `path.is_file()` → delegate to `load_graph(path)` unchanged
- `path.is_dir()` → `sorted(path.glob("*.graph.yaml"))`, raise `DRGLoadError` if empty,
  load each fragment, reduce: `graph = fragments[0]; for f in fragments[1:]: graph = merge_layers(graph, f)`
- `not path.exists()` → raise `DRGLoadError(f"Path not found: {path}")`
- Edge case: directory exists but contains no `*.graph.yaml` files → raise `DRGLoadError`
  with a clear message (callers should check existence before calling)

**Validation**: the merged result from fragments is NOT validated here — callers that need
validation call `assert_valid()` themselves (as today).

---

## Subtask T002 — Export `load_graph_or_dir` from `__init__.py`

**File**: `src/doctrine/drg/__init__.py`

**Purpose**: Add `load_graph_or_dir` to the public API surface.

Add `load_graph_or_dir` to:
- The import from `doctrine.drg.loader`
- The `__all__` list

---

## Subtask T003 — Update `_drg_helpers.load_validated_graph()`

**File**: `src/charter/_drg_helpers.py`

**Purpose**: Replace `load_graph(doctrine_root / "graph.yaml")` and
`load_graph(project_path) if project_path.exists() else None` with `load_graph_or_dir`
calls. Retain the `assert_valid()` call on the merged result.

**Current code** (lines 34–37):
```python
shipped = load_graph(doctrine_root / "graph.yaml")
project_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
project = load_graph(project_path) if project_path.exists() else None
merged = merge_layers(shipped, project)
```

**New code**:
```python
shipped = load_graph_or_dir(doctrine_root)
project_dir = repo_root / ".kittify" / "doctrine"
project = load_graph_or_dir(project_dir) if project_dir.exists() else None
merged = merge_layers(shipped, project)
```

Note: the project directory check changes from `"graph.yaml" exists` to `dir exists`.
A project with no doctrine directory still produces `project = None` correctly.

Also add an `org_root: Path | None = None` parameter (defaulting to `None` for now). The
three-layer merge using org_root will be added in WP03; this WP just adds the parameter
signature so WP03's changes are additive.

---

## Subtask T004 — Update synthesizer pipeline call sites

**Files** (four files, multiple sites each):
- `src/charter/synthesizer/validation_gate.py` line 61
- `src/charter/synthesizer/project_drg.py` line 240
- `src/charter/synthesizer/resynthesize_pipeline.py` lines 450 and 547
- `src/charter/synthesizer/write_pipeline.py` line 516

**Pattern**: Replace `path / "doctrine" / "graph.yaml"` or `staging_dir / "doctrine" / "graph.yaml"`
constructions with `load_graph_or_dir(path / "doctrine")` or
`load_graph_or_dir(staging_dir / "doctrine")`.

For each site:
1. Remove the `path / "graph.yaml"` construction.
2. Replace `load_graph(...)` call with `load_graph_or_dir(parent_dir)`.
3. Ensure `import` at top of file includes `load_graph_or_dir` (add if missing).
4. Where sites check `path.exists()` before loading, change the check to `parent_dir.exists()`
   (checking the directory, not the file).

**Example transformation** (validation_gate.py line 61):

Before:
```python
overlay_path = staging_dir / "doctrine" / "graph.yaml"
overlay = load_graph(overlay_path) if overlay_path.exists() else None
```

After:
```python
overlay_doctrine_dir = staging_dir / "doctrine"
overlay = load_graph_or_dir(overlay_doctrine_dir) if overlay_doctrine_dir.exists() else None
```

---

## Subtask T005 — Unit tests for `load_graph_or_dir`

**File**: `tests/doctrine/drg/test_loader_multifile.py` (new file)

**Test cases** (use `tmp_path` pytest fixture for all):

| Test | Setup | Expected |
|---|---|---|
| `test_single_file_path` | `path/graph.yaml` with valid content | Returns same result as `load_graph(path/graph.yaml)` |
| `test_directory_single_fragment` | `path/` containing `010.graph.yaml` | Returns same graph as loading that file |
| `test_directory_multiple_fragments` | `path/` containing `010.graph.yaml`, `020.graph.yaml` | Returns merged graph (nodes and edges from both) |
| `test_directory_alphabetical_order` | `path/` with `zzz.graph.yaml` and `aaa.graph.yaml` defining same node | `aaa` wins (loaded first, `zzz` overrides it in merge — verify precedence) |
| `test_directory_empty` | `path/` with no `*.graph.yaml` files | Raises `DRGLoadError` |
| `test_path_not_exists` | Non-existent path | Raises `DRGLoadError` |
| `test_directory_one_invalid_fragment` | Two files, one malformed | Raises `DRGLoadError` (propagates from `load_graph`) |

---

## Definition of Done

- [ ] `load_graph_or_dir()` exists in `loader.py` and is exported from `__init__.py`
- [ ] `_drg_helpers.load_validated_graph()` uses `load_graph_or_dir` for shipped and project
- [ ] All four synthesizer files updated; no remaining `"graph.yaml"` string literal in those files
- [ ] `test_loader_multifile.py` passes
- [ ] All existing DRG tests pass (`pytest tests/doctrine/drg/`)
- [ ] No `"graph.yaml"` string literal remains in any file under `src/charter/synthesizer/`

## Risks

- Missing a synthesizer call site causes silent single-file-only behavior. Run
  `grep -r "graph\.yaml" src/charter/` and verify every hit is addressed or intentionally
  retained (e.g., docstring references are fine).
- Fragment merge order: alphabetical filename ordering must be tested explicitly.

## Reviewer Guidance

Check that:
1. The `load_graph_or_dir()` function handles the "directory with single file" case
   identically to `load_graph(dir / "graph.yaml")` — both must produce the same `DRGGraph`.
2. All synthesizer sites check directory existence (not file existence) before calling.
3. The `org_root: Path | None = None` parameter is present on `load_validated_graph()` but
   has no effect yet (will be used in WP03).
