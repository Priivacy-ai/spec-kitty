---
work_package_id: WP06
title: Skill Verifier
lane: planned
dependencies: [WP03]
subtasks:
- T024
- T025
- T026
- T027
phase: Phase 1 - Core Implementation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-006
- FR-007
---

# Work Package Prompt: WP06 – Skill Verifier

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement verification of installed skills against the managed manifest
- Implement repair of missing/drifted skill files from canonical source
- Return structured results for use by verify integration (WP07)
- Unit tests with 90%+ coverage

**Success**: Verify detects missing and drifted files. Repair restores them from canonical source and updates the manifest.

## Context & Constraints

- **PRD reference**: Section 9.3 (Manifest and Drift)
- **Dependencies**: WP03 (manifest dataclass and persistence)
- **Data model**: `VerifyResult` from `data-model.md`

**Implementation command**: `spec-kitty implement WP06 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T024 – Implement `verify_installed_skills()`

- **Purpose**: Check all manifest entries against the filesystem.
- **Steps**:
  1. Create `src/specify_cli/skills/verifier.py`
  2. Implement:
     ```python
     def verify_installed_skills(project_path: Path) -> VerifyResult:
         """Verify all installed skill files against the manifest."""
     ```
  3. Logic:
     - Load manifest from project_path
     - If no manifest exists → return VerifyResult(ok=True) with empty lists
     - For each entry in manifest:
       - Check if file exists at `project_path / entry.installed_path`
       - If missing → add to `missing` list
       - If exists, compute hash and compare to `entry.content_hash`
       - If hash differs → add to `drifted` list with actual hash
     - Return populated `VerifyResult`
- **Files**: `src/specify_cli/skills/verifier.py` (new, ~80 lines)

### Subtask T025 – Implement `VerifyResult` dataclass

- **Purpose**: Structured result type for verify operations.
- **Steps**:
  1. Add to `src/specify_cli/skills/verifier.py`:
     ```python
     @dataclass
     class VerifyResult:
         ok: bool
         missing: list[ManagedFileEntry] = field(default_factory=list)
         drifted: list[tuple[ManagedFileEntry, str]] = field(default_factory=list)  # (entry, actual_hash)
         unmanaged: list[str] = field(default_factory=list)  # paths not in manifest
         errors: list[str] = field(default_factory=list)

         @property
         def total_issues(self) -> int:
             return len(self.missing) + len(self.drifted) + len(self.errors)
     ```
- **Files**: `src/specify_cli/skills/verifier.py` (modify)

### Subtask T026 – Implement `repair_skills()`

- **Purpose**: Restore missing/drifted files from canonical source.
- **Steps**:
  1. Implement:
     ```python
     def repair_skills(
         project_path: Path,
         verify_result: VerifyResult,
         registry: SkillRegistry,
     ) -> tuple[int, int]:
         """Repair missing and drifted skill files. Returns (repaired, failed) counts."""
     ```
  2. Logic:
     - For each missing entry:
       - Look up skill in registry by `entry.skill_name`
       - Find source file matching `entry.source_file`
       - Copy to `project_path / entry.installed_path`
       - Update manifest entry hash
     - For each drifted entry:
       - Same as missing — overwrite with canonical source
     - Save updated manifest
     - Return counts
  3. Handle errors per-file (don't abort on first failure)
- **Files**: `src/specify_cli/skills/verifier.py` (modify)
- **Notes**: If canonical source is not found (registry returns None), add to errors list with clear message.

### Subtask T027 – Unit tests for verifier

- **Purpose**: Verify detection and repair work correctly.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_verifier.py`
  2. Test cases:
     - `test_verify_no_manifest_returns_ok` — no manifest → ok=True
     - `test_verify_all_files_present_and_matching` — all good → ok=True
     - `test_verify_detects_missing_file` — deleted file → in missing list
     - `test_verify_detects_drifted_file` — modified file → in drifted list with actual hash
     - `test_verify_multiple_issues` — mix of missing and drifted
     - `test_repair_restores_missing_file` — repair copies from source
     - `test_repair_restores_drifted_file` — repair overwrites
     - `test_repair_handles_missing_source` — registry can't find skill → error count
     - `test_repair_updates_manifest` — manifest hashes updated after repair
  3. Create test fixtures with installed files and manifest in `tmp_path`
- **Files**: `tests/specify_cli/skills/test_verifier.py` (new, ~160 lines)
- **Parallel?**: Yes

## Risks & Mitigations

- **Missing canonical source during repair**: Package may be corrupted → return error with reinstall instructions
- **File permissions**: Restored files may need correct permissions → use `shutil.copy2` to preserve metadata

## Review Guidance

- Verify `ok` is `True` only when all lists are empty
- Verify repair actually writes files (not just returns success)
- Verify manifest is updated after repair
- Verify per-file error handling (no abort on first failure)

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
