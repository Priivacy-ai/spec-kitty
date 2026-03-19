---
work_package_id: WP03
title: Standalone Script Contract
lane: planned
dependencies: [WP01]
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 2 - Runtime Contract
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-19T16:39:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-003
- C-002
---

# Work Package Prompt: WP03 – Standalone Script Contract

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Objectives & Success Criteria

- `python3 src/specify_cli/scripts/tasks/tasks_cli.py --help` works from a repo checkout without pip install.
- `acceptance_support.py` can import `specify_cli.status.*` and `specify_cli.feature_metadata` via the `sys.path` bootstrap.
- Both `src/` and `scripts/` copies have the bootstrap.
- No vendoring of `specify_cli` modules — only `sys.path` manipulation.

**Success gate**: From a checkout with no pip install, `python3 .../tasks_cli.py --help` exits 0 with no `ModuleNotFoundError`.

## Context & Constraints

- **Spec**: `kitty-specs/052-acceptance-pipeline-regression-fixes/spec.md` — User Story 3
- **Plan**: `kitty-specs/052-acceptance-pipeline-regression-fixes/plan.md` — Bug Analysis P1 (standalone)
- **Constraint C-002**: No vendoring — sys.path only

**Root cause**: `tasks_cli.py` (line 18-20) adds only `SCRIPT_DIR` to `sys.path`. When `acceptance_support.py` was refactored to import `specify_cli.status.reducer`, `specify_cli.status.store`, and `specify_cli.feature_metadata`, it gained a dependency on the package being importable. But the bootstrap never adds the repo `src/` root.

**Directory structure**:
```
repo/
├── src/
│   └── specify_cli/         # ← This needs to be importable
│       ├── status/
│       │   ├── reducer.py
│       │   └── store.py
│       ├── feature_metadata.py
│       └── scripts/
│           └── tasks/
│               ├── tasks_cli.py        # SCRIPT_DIR = here
│               ├── acceptance_support.py
│               └── task_helpers.py
├── scripts/
│   └── tasks/
│       ├── tasks_cli.py        # SCRIPT_DIR = here (different depth!)
│       ├── acceptance_support.py
│       └── task_helpers.py
└── .kittify/
    └── scripts/tasks/...      # Identical to scripts/
```

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T008 – Add repo `src/` root to `sys.path` in `src/specify_cli/scripts/tasks/tasks_cli.py`

- **Purpose**: Make `specify_cli.*` importable when the script is invoked directly from a checkout.
- **File**: `src/specify_cli/scripts/tasks/tasks_cli.py`
- **Steps**:
  1. Locate the existing `sys.path` bootstrap (lines 18-20):
     ```python
     SCRIPT_DIR = Path(__file__).resolve().parent
     if str(SCRIPT_DIR) not in sys.path:
         sys.path.insert(0, str(SCRIPT_DIR))
     ```
  2. Add the `src/` root bootstrap immediately after:
     ```python
     # Add repo src/ root so specify_cli.* is importable from checkout
     _SRC_ROOT = SCRIPT_DIR.parent.parent.parent.parent  # tasks/ → scripts/ → specify_cli/ → src/
     if _SRC_ROOT.name == "src" and str(_SRC_ROOT) not in sys.path:
         sys.path.insert(0, str(_SRC_ROOT))
     ```
  3. The `_SRC_ROOT.name == "src"` guard ensures this only activates when the directory structure is correct. If someone moves the script, the guard fails silently.
  4. Verify the parent chain:
     - `SCRIPT_DIR` = `.../src/specify_cli/scripts/tasks/`
     - `.parent` = `.../src/specify_cli/scripts/`
     - `.parent.parent` = `.../src/specify_cli/`
     - `.parent.parent.parent` = `.../src/`
     - `.parent.parent.parent.parent` — wait, that's 4 levels. Let me recount.
     - Actually: SCRIPT_DIR = `src/specify_cli/scripts/tasks/`. We need `src/`.
     - `SCRIPT_DIR.parent` = `src/specify_cli/scripts/`
     - `SCRIPT_DIR.parent.parent` = `src/specify_cli/`
     - `SCRIPT_DIR.parent.parent.parent` = `src/`
     - So it's `.parent.parent.parent`, NOT `.parent.parent.parent.parent`.
     ```python
     _SRC_ROOT = SCRIPT_DIR.parent.parent.parent  # tasks/ → scripts/ → specify_cli/ → src/
     ```
- **Parallel?**: No
- **Notes**: `sys.path.insert(0, ...)` puts the local source BEFORE any pip-installed version. This is correct for development — the checkout should shadow the installed package.

### Subtask T009 – Add repo `src/` root to `sys.path` in `src/specify_cli/scripts/tasks/acceptance_support.py`

- **Purpose**: Make `specify_cli.*` importable when `acceptance_support.py` is imported by `tasks_cli.py` in standalone mode.
- **File**: `src/specify_cli/scripts/tasks/acceptance_support.py`
- **Steps**:
  1. This file currently has NO `sys.path` manipulation. Add the bootstrap AFTER the stdlib imports (after line 11 `from typing import ...`) and BEFORE the `from task_helpers import ...` line (line 13):
     ```python
     import sys

     SCRIPT_DIR = Path(__file__).resolve().parent
     if str(SCRIPT_DIR) not in sys.path:
         sys.path.insert(0, str(SCRIPT_DIR))

     # Add repo src/ root so specify_cli.* is importable from checkout
     _SRC_ROOT = SCRIPT_DIR.parent.parent.parent  # tasks/ → scripts/ → specify_cli/ → src/
     if _SRC_ROOT.name == "src" and str(_SRC_ROOT) not in sys.path:
         sys.path.insert(0, str(_SRC_ROOT))
     ```
  2. Note: `sys` may not be imported yet in this file — check and add `import sys` if missing. Actually, looking at the imports, `os` and `re` are imported but NOT `sys`. Add `import sys` after `import os` (line 8).
  3. The bootstrap must come BEFORE `from specify_cli.status.reducer import materialize` (line 25), because that's the import that fails.
  4. Same parent chain as T008: `SCRIPT_DIR.parent.parent.parent` = `src/`.
- **Parallel?**: No
- **Notes**: The `from task_helpers import ...` line (line 13) already works because `tasks_cli.py` adds `SCRIPT_DIR` to `sys.path` before importing `acceptance_support`. However, `acceptance_support.py` should also be independently importable (it could be imported by other scripts). Adding its own bootstrap makes it self-contained.

### Subtask T010 – Add repo `src/` root to `sys.path` in `scripts/tasks/` copies

- **Purpose**: The `scripts/tasks/` copies are at a different depth than `src/specify_cli/scripts/tasks/`. They need their own bootstrap.
- **Files**:
  - `scripts/tasks/tasks_cli.py`
  - `scripts/tasks/acceptance_support.py`
- **Steps**:
  1. For scripts at `scripts/tasks/`, the path to `src/` is different:
     - `SCRIPT_DIR` = `repo/scripts/tasks/`
     - `SCRIPT_DIR.parent` = `repo/scripts/`
     - `SCRIPT_DIR.parent.parent` = `repo/`
     - `SCRIPT_DIR.parent.parent / "src"` = `repo/src/`
  2. Since WP01 T004 and WP02 T007 sync the src/ copy to scripts/, the scripts/ copies will ALREADY have the `_SRC_ROOT = SCRIPT_DIR.parent.parent.parent` line. But this points to the wrong directory from `scripts/tasks/`.
  3. **Solution**: Use a bounded walk approach that works from ANY location:
     ```python
     # Add repo src/ root so specify_cli.* is importable from checkout
     _candidate = SCRIPT_DIR
     for _ in range(6):
         _candidate = _candidate.parent
         _src = _candidate / "src"
         if (_src / "specify_cli").is_dir() and str(_src) not in sys.path:
             sys.path.insert(0, str(_src))
             break
     ```
  4. **Alternative (simpler)**: Since T004/T007 sync the entire file, the scripts/ copies would get the `SCRIPT_DIR.parent.parent.parent` line which wouldn't work. Instead, replace the fixed-depth approach with the bounded walk in ALL copies (src/ and scripts/). This way one codebase works from both locations.
  5. **Recommended approach**: Use the bounded walk in ALL copies (T008, T009, T010) instead of the fixed-depth `.parent.parent.parent`. This makes the bootstrap location-agnostic and keeps the copies truly identical:
     ```python
     # Add repo src/ root so specify_cli.* is importable from checkout
     _candidate = SCRIPT_DIR
     for _ in range(6):
         _candidate = _candidate.parent
         _src = _candidate / "src"
         if (_src / "specify_cli").is_dir() and str(_src) not in sys.path:
             sys.path.insert(0, str(_src))
             break
     ```
- **Parallel?**: No
- **Notes**: The bounded walk (6 levels max) is safe — it won't go above the filesystem root. The `(_src / "specify_cli").is_dir()` check ensures we find the right `src/` directory (not some unrelated one).

### Subtask T011 – Sync `.kittify/scripts/tasks/` copies

- **Purpose**: The `.kittify/` copies must match `scripts/tasks/`.
- **Files**: `.kittify/scripts/tasks/acceptance_support.py`, `.kittify/scripts/tasks/tasks_cli.py`
- **Steps**:
  1. Copy `scripts/tasks/acceptance_support.py` to `.kittify/scripts/tasks/acceptance_support.py`.
  2. Copy `scripts/tasks/tasks_cli.py` to `.kittify/scripts/tasks/tasks_cli.py`.
  3. Verify with `diff`.
- **Parallel?**: No

## Risks & Mitigations

- **Risk**: `sys.path` walk finds wrong `src/` directory. **Mitigation**: Guard checks for `specify_cli` subdirectory existence.
- **Risk**: If pip-installed version exists, local source shadows it. **Mitigation**: `sys.path.insert(0, ...)` intentionally prefers local — correct for development.
- **Risk**: Script invoked from outside repo tree. **Mitigation**: Walk is bounded (6 levels); if not found, `sys.path` is unchanged — the import will fail with a clear error.

## Review Guidance

- Verify the bootstrap approach is consistent across all 4 files (use bounded walk, not fixed depth).
- Verify `import sys` is present in files that use `sys.path`.
- Verify bootstrap comes BEFORE any `from specify_cli.*` imports.
- Test: `python3 src/specify_cli/scripts/tasks/tasks_cli.py --help` exits 0.
- Test: `python3 scripts/tasks/tasks_cli.py --help` exits 0.
- Verify `.kittify/` copies are byte-identical to `scripts/` copies.

## Activity Log

- 2026-03-19T16:39:32Z – system – lane=planned – Prompt created.
