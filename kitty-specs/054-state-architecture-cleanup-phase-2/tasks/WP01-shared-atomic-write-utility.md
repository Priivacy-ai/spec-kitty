---
work_package_id: WP01
title: Shared Atomic Write Utility
lane: planned
dependencies: []
subtasks:
- T001
- T002
- T003
phase: Phase 0 - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- NFR-001
- C-004
---

# Work Package Prompt: WP01 – Shared Atomic Write Utility

## Objectives & Success Criteria

- Extract the atomic-write pattern from `feature_metadata.py` into a shared public utility at `src/specify_cli/core/atomic.py`.
- Refactor `feature_metadata.py` to import the shared utility instead of using its private copy.
- All existing `feature_metadata.py` tests still pass.
- New tests cover success, interrupt, cleanup, mkdir, and bytes/str modes.

## Context & Constraints

- **Source pattern**: `src/specify_cli/feature_metadata.py` lines 84-108 contain the canonical `_atomic_write()` implementation.
- **Plan reference**: Design decision D1 in `kitty-specs/054-state-architecture-cleanup-phase-2/plan.md`.
- **Data model**: See `data-model.md` → "Entity: AtomicWriter" for the API contract.
- **Constraint C-004**: Temp files MUST be in the same directory as target for same-filesystem `os.replace()` atomicity.
- **9 downstream consumers** (WP04/WP05) will import this utility.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/specify_cli/core/atomic.py`

**Purpose**: Provide a single, shared atomic-write function for the entire package.

**Steps**:

1. Create `src/specify_cli/core/atomic.py` with:

```python
"""Atomic file write utility.

Guarantees: file is either complete old content or complete new content,
never partial. Uses write-to-temp-then-rename on the same filesystem.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str | bytes, *, mkdir: bool = False) -> None:
    """Write *content* atomically to *path*.

    Parameters
    ----------
    path : Path
        Target file path.
    content : str | bytes
        File content. ``str`` is encoded to UTF-8; ``bytes`` is written raw.
    mkdir : bool
        If True, create parent directories before writing.
    """
    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)

    raw = content.encode("utf-8") if isinstance(content, str) else content

    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".atomic-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        # fd is now closed by the context manager
        os.replace(tmp_path, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
```

2. Ensure `src/specify_cli/core/__init__.py` exports `atomic_write` if it has an `__all__`.

**Files**:
- `src/specify_cli/core/atomic.py` (NEW, ~45 lines)
- `src/specify_cli/core/__init__.py` (MODIFY if needed)

### Subtask T002 – Refactor `feature_metadata.py` to use shared utility

**Purpose**: Eliminate the private `_atomic_write()` copy and import from the shared module.

**Steps**:

1. In `src/specify_cli/feature_metadata.py`:
   - Remove the private `_atomic_write()` function (lines 84-108).
   - Add import: `from specify_cli.core.atomic import atomic_write`
   - Update the call in `write_meta()` (around line 151): replace `_atomic_write(meta_path, content)` with `atomic_write(meta_path, content)`.

2. Verify no other code in this file references `_atomic_write`.

**Files**:
- `src/specify_cli/feature_metadata.py` (MODIFY)

**Validation**:
- `pytest tests/specify_cli/test_feature_metadata.py -v` must pass.

### Subtask T003 – Create `tests/specify_cli/test_atomic_write.py`

**Purpose**: Comprehensive tests for the shared atomic-write utility.

**Steps**:

1. Create `tests/specify_cli/test_atomic_write.py` with these test cases:

   - **test_atomic_write_str**: Write a string, read back, confirm UTF-8 content matches.
   - **test_atomic_write_bytes**: Write raw bytes, read back, confirm content matches.
   - **test_atomic_write_mkdir**: Target path with non-existent parents + `mkdir=True` → succeeds.
   - **test_atomic_write_mkdir_false_missing_parent**: Target path with non-existent parents + `mkdir=False` → raises `FileNotFoundError`.
   - **test_atomic_write_interrupt_preserves_original**: Write an initial file, then mock `os.replace` to raise `OSError`. Confirm original content is preserved and temp file is cleaned up.
   - **test_atomic_write_keyboard_interrupt_cleanup**: Mock `os.replace` to raise `KeyboardInterrupt`. Confirm temp file is cleaned up (tests `BaseException` catch).
   - **test_atomic_write_overwrites_existing**: Write to existing file → new content replaces old.
   - **test_atomic_write_temp_in_same_dir**: After a successful write, confirm no `.atomic-*.tmp` files remain in the target directory.

2. Use `tmp_path` fixture for isolation.

**Files**:
- `tests/specify_cli/test_atomic_write.py` (NEW, ~100 lines)

**Validation**:
- `pytest tests/specify_cli/test_atomic_write.py -v` must pass.
- `ruff check src/specify_cli/core/atomic.py tests/specify_cli/test_atomic_write.py`

## Risks & Mitigations

- **Permission preservation**: `os.replace()` on some systems may not preserve permissions of the original file. For this utility, this is acceptable — callers that need specific permissions (like `auth.py`) will apply them after the atomic write.
- **Temp file left behind on crash**: If the process is killed with SIGKILL (uncatchable), a `.atomic-*.tmp` file may remain. This is inherent to the pattern and acceptable — the next write will succeed regardless.

## Review Guidance

- Verify `BaseException` catch (not just `Exception`) — must handle `KeyboardInterrupt`.
- Verify temp file is in the same directory as target (same filesystem guarantee).
- Verify `os.fdopen` wraps the fd so the context manager closes it.
- Verify `feature_metadata.py` tests still pass after refactor.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
