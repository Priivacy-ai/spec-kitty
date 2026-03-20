---
work_package_id: WP07
title: Acceptance Implementation Deduplication
lane: "doing"
dependencies: []
base_branch: 2.x
base_commit: edec05ad2c5de16cc7a13967b341f5d4e4e52aec
created_at: '2026-03-20T13:52:02.220960+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase 2 - Consolidation
assignee: ''
agent: "codex"
shell_pid: "1446"
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
- FR-020
- NFR-002
---

# Work Package Prompt: WP07 – Acceptance Implementation Deduplication

## Objectives & Success Criteria

- `acceptance.py` becomes the single canonical implementation (~720 lines) with all logic.
- `acceptance_support.py` becomes a pure re-export wrapper (~25 lines).
- Both import paths (`specify_cli.acceptance` and `scripts.tasks.acceptance_support`) work identically.
- The regression parity test validates re-exports match canonical `__all__`.

## Context & Constraints

- **Plan reference**: Design decision D4 in plan.md.
- **Current state**: `acceptance.py` (657 lines, 10 functions) and `acceptance_support.py` (758 lines, 13 functions) are ~95% duplicated. The standalone copy has 3 unique additions.
- **Existing guard**: `test_acceptance_regressions.py` keeps the two copies API-aligned via signature parity checks.
- **Import path contract**: `scripts/tasks/acceptance_support.py` MUST remain importable because standalone `tasks_cli.py` imports it.

## Implementation Command

```bash
spec-kitty implement WP07
```

## Subtasks & Detailed Guidance

### Subtask T027 – Move `ArtifactEncodingError` to acceptance.py

**Purpose**: Centralize the custom exception for UTF-8 decode failures.

**Steps**:

1. Find `ArtifactEncodingError` in `src/specify_cli/scripts/tasks/acceptance_support.py` (lines 50-62):
   ```python
   class ArtifactEncodingError(AcceptanceError):
       """Raised when an artifact file cannot be decoded as UTF-8."""
       def __init__(self, path: Path, original_error: Exception):
           self.path = path
           self.original_error = original_error
           super().__init__(
               f"Cannot decode {path} as UTF-8: {original_error}\n"
               f"Hint: Fix encoding with: iconv -f WINDOWS-1252 -t UTF-8 '{path}' > '{path}.fixed' && mv '{path}.fixed' '{path}'"
           )
   ```

2. Copy this class to `src/specify_cli/acceptance.py`, placed after `AcceptanceError`.

3. Add `"ArtifactEncodingError"` to `acceptance.py`'s `__all__`.

**Files**: `src/specify_cli/acceptance.py` (MODIFY)

### Subtask T028 – Move `normalize_feature_encoding()` to acceptance.py

**Purpose**: Centralize the Windows-1252/Latin-1 → UTF-8 conversion function.

**Steps**:

1. Find `normalize_feature_encoding()` in `acceptance_support.py` (lines 346-420). This is a substantial function that:
   - Iterates over feature directory files
   - Detects encoding issues (Windows-1252, Latin-1)
   - Maps smart quotes and dashes to ASCII equivalents
   - Re-encodes files to UTF-8

2. Copy the entire function to `acceptance.py`.

3. Ensure all imports used by this function exist in `acceptance.py` (e.g., any encoding-related imports).

4. Add `"normalize_feature_encoding"` to `acceptance.py`'s `__all__`.

**Files**: `src/specify_cli/acceptance.py` (MODIFY)

### Subtask T029 – Move `_read_text_strict()` to acceptance.py

**Purpose**: Centralize the encoding-strict file reader.

**Steps**:

1. Find `_read_text_strict()` in `acceptance_support.py` (lines 305-309):
   ```python
   def _read_text_strict(path: Path) -> str:
       try:
           return path.read_text(encoding="utf-8")
       except UnicodeDecodeError as e:
           raise ArtifactEncodingError(path, e) from e
   ```

2. Copy to `acceptance.py`. This is a private function, so no `__all__` change needed.

3. Update any internal callers in `acceptance.py` that currently use plain `path.read_text()` to consider using `_read_text_strict()` where appropriate.

**Files**: `src/specify_cli/acceptance.py` (MODIFY)

### Subtask T030 – Align `AcceptanceSummary` path_violations

**Purpose**: Ensure the `AcceptanceSummary` dataclass is consistent.

**Steps**:

1. The canonical `acceptance.py` includes `path_violations: List[str]` in `AcceptanceSummary.__init__()` and checks it in `ok()`.

2. The standalone copy was MISSING this field.

3. After consolidation, verify:
   - `AcceptanceSummary` in `acceptance.py` includes `path_violations`
   - The `ok()` method checks `path_violations`
   - The `outstanding()` method includes `path_violations` in its dict

4. No changes needed if `acceptance.py` already has this correct — just verify.

**Files**: `src/specify_cli/acceptance.py` (VERIFY, possibly no change needed)

### Subtask T031 – Rewrite `acceptance_support.py` as re-export wrapper

**Purpose**: Replace the 758-line duplicate with a ~25-line re-export module.

**Steps**:

1. Replace the entire content of `src/specify_cli/scripts/tasks/acceptance_support.py` with:

```python
"""Thin compatibility wrapper for standalone tasks_cli.py usage.

All logic lives in specify_cli.acceptance. This module re-exports
the public API for backwards compatibility with standalone scripts.
"""
from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceResult,
    AcceptanceSummary,
    ArtifactEncodingError,
    WorkPackageState,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    normalize_feature_encoding,
    perform_acceptance,
)

__all__ = [
    "AcceptanceError",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_feature_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
```

2. **Handle `detect_feature_slug` signature divergence**: The standalone copy has a different signature (no `announce_fallback` parameter). In `acceptance.py`, ensure `detect_feature_slug()` has `announce_fallback: bool = True` as a keyword argument with a default — this makes the re-export backward compatible.

**Files**: `src/specify_cli/scripts/tasks/acceptance_support.py` (REWRITE)

### Subtask T032 – Update acceptance regression tests

**Purpose**: Adapt the parity test to validate re-exports instead of duplicated implementations.

**Steps**:

1. In `tests/specify_cli/test_acceptance_regressions.py`, find `test_copy_parity_between_acceptance_modules()` (lines 321-355):
   ```python
   core_exports = set(acceptance.__all__)
   standalone_exports = set(acceptance_support.__all__)
   assert core_exports.issubset(standalone_exports)
   ```

2. Update to validate that `acceptance_support.__all__` equals `acceptance.__all__`:
   ```python
   core_exports = set(acceptance.__all__)
   standalone_exports = set(acceptance_support.__all__)
   assert core_exports == standalone_exports, (
       f"Wrapper must re-export all canonical names. "
       f"Missing: {core_exports - standalone_exports}, "
       f"Extra: {standalone_exports - core_exports}"
   )
   ```

3. The signature parity checks can remain — they now validate re-exports match originals (which they will, since they ARE the originals).

4. Add a test that verifies each re-exported name is the same object (not a copy):
   ```python
   for name in acceptance.__all__:
       assert getattr(acceptance, name) is getattr(acceptance_support, name), (
           f"{name} in acceptance_support is not the same object as in acceptance"
       )
   ```

**Files**: `tests/specify_cli/test_acceptance_regressions.py` (MODIFY)

**Validation**:
```bash
pytest tests/specify_cli/test_acceptance_regressions.py tests/specify_cli/test_canonical_acceptance.py -v
```

## Risks & Mitigations

- **Import path breakage**: If `tasks_cli.py` imports a name that's NOT in the re-export wrapper, it will fail at import time. Mitigation: ensure `__all__` in wrapper includes everything `tasks_cli.py` uses.
- **`detect_feature_slug` signature**: The standalone version lacks `announce_fallback`. Adding it as a keyword arg with default in the canonical version is backward compatible.
- **Hidden callers**: Grep for any other imports from `acceptance_support` outside `tasks_cli.py`.

## Review Guidance

- Verify `acceptance_support.py` is truly just re-exports — no logic.
- Verify `detect_feature_slug` handles both call signatures.
- Verify the parity test asserts object identity, not just name equality.
- Run both CLI acceptance and standalone `tasks_cli.py` acceptance to verify behavior.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
- 2026-03-20T13:52:02Z – coordinator – shell_pid=73852 – lane=doing – Assigned agent via workflow command
- 2026-03-20T14:03:26Z – coordinator – shell_pid=73852 – lane=for_review – Ready for review: acceptance.py is single canonical impl (~760 lines), acceptance_support.py is thin re-export wrapper (55 lines). All 34 tests pass.
- 2026-03-20T14:03:45Z – codex – shell_pid=1446 – lane=doing – Started review via workflow command
