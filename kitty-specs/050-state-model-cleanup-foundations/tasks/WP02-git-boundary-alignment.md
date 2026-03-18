---
work_package_id: WP02
title: Git Boundary Alignment
lane: "doing"
dependencies:
- WP01
base_branch: 050-state-model-cleanup-foundations-WP01
base_commit: 224fc89984e7bba1aac90032c254569380e6091d
created_at: '2026-03-18T19:21:17.263914+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Alignment
assignee: ''
agent: "codex"
shell_pid: "32698"
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://050-state-model-cleanup-foundations/WP02/20260318T193659Z-ce03e9fa.md
history:
- timestamp: '2026-03-18T18:52:42Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-006
- FR-007
- FR-010
- C-005
---

# Work Package Prompt: WP02 – Git Boundary Alignment

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

> **Reference-only section** – Canonical review feedback is stored via frontmatter `review_feedback` (`feedback://...`).

---

## Objectives & Success Criteria

- `GitignoreManager.RUNTIME_PROTECTED_ENTRIES` is derived from `state_contract.get_runtime_gitignore_entries()`, not hardcoded.
- A migration adds `.kittify/runtime/`, `.kittify/merge-state.json`, `.kittify/events/`, `.kittify/dossiers/` to `.gitignore` for existing projects.
- Integration tests validate:
  - (A) The repo `.gitignore` covers all `LOCAL_RUNTIME` project surfaces from the contract.
  - (B) `RUNTIME_PROTECTED_ENTRIES` matches the contract output.
- Migration is idempotent — running it twice produces the same result.

## Context & Constraints

- **Spec**: FR-006 (GitignoreManager derivation), FR-007 (gitignore update), FR-010 (migration), C-005 (idempotent)
- **Plan**: Design decisions D3 (derivation) and D4 (migration strategy)
- **Existing code**: `src/specify_cli/gitignore_manager.py` — current `RUNTIME_PROTECTED_ENTRIES = [".kittify/.dashboard", ".kittify/missions/__pycache__/"]`
- **Migration registry**: Check `src/specify_cli/upgrade/migrations/` for naming convention. Latest: `m_2_0_7_fix_stale_overrides.py`. Use `m_2_0_9_state_gitignore.py`.
- **Key constraint**: Constitution surfaces are NOT added to `.gitignore` (C-001). Only unambiguous runtime surfaces.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T006 – Derive GitignoreManager Entries from Contract

- **Purpose**: Replace the hardcoded `RUNTIME_PROTECTED_ENTRIES` list with a contract-derived list, ensuring the gitignore policy is always consistent with the state contract.
- **File**: `src/specify_cli/gitignore_manager.py`
- **Steps**:
  1. Add import at top of module:
     ```python
     from specify_cli.state_contract import get_runtime_gitignore_entries
     ```
  2. Replace the constant:
     ```python
     # Before:
     RUNTIME_PROTECTED_ENTRIES = [
         ".kittify/.dashboard",
         ".kittify/missions/__pycache__/",
     ]

     # After:
     RUNTIME_PROTECTED_ENTRIES = get_runtime_gitignore_entries()
     ```
  3. Verify `protect_all_agents()` still works — it extends `all_directories` with `RUNTIME_PROTECTED_ENTRIES`. No code change needed there since the variable name stays the same.
- **Notes**: `get_runtime_gitignore_entries()` returns a `list[str]` of path patterns. It includes the old entries (`.kittify/.dashboard`) plus new ones (`.kittify/runtime/`, etc.). The `.kittify/missions/__pycache__/` entry needs to be included in the contract (add as a surface with authority `LOCAL_RUNTIME` if not already present, or add it to `get_runtime_gitignore_entries()` explicitly).

  **Important edge case**: `.kittify/missions/__pycache__/` is a Python cache artifact, not really a "state surface" in the audit sense. Two options:
  - (a) Add it as a surface in the contract with a note "Python cache, not architectural state"
  - (b) Keep it in `get_runtime_gitignore_entries()` as a hardcoded addition alongside the contract-derived list

  **Recommendation**: Option (a) — add it as a surface. It keeps the derivation clean and single-source.

### Subtask T007 – Write Gitignore Integration Tests

- **Purpose**: Prevent drift between the state contract and actual gitignore policy.
- **File**: `tests/specify_cli/test_gitignore_contract.py` (new file)
- **Steps**:
  1. **Test A — Repo `.gitignore` covers all `LOCAL_RUNTIME` project surfaces**:
     ```python
     def test_repo_gitignore_covers_local_runtime():
         """Every LOCAL_RUNTIME project surface has a matching .gitignore entry."""
         repo_root = Path(__file__).resolve().parents[2]  # up to repo root
         gitignore_path = repo_root / ".gitignore"
         gitignore_content = gitignore_path.read_text()
         gitignore_lines = set(gitignore_content.splitlines())

         from specify_cli.state_contract import (
             STATE_SURFACES, StateRoot, AuthorityClass, GitClass
         )

         local_runtime_project = [
             s for s in STATE_SURFACES
             if s.root == StateRoot.PROJECT
             and (s.authority == AuthorityClass.LOCAL_RUNTIME
                  or s.git_class == GitClass.IGNORED)
         ]

         missing = []
         for surface in local_runtime_project:
             pattern = surface.path_pattern
             # Check if pattern or a parent directory pattern is in gitignore
             if not any(
                 pattern.startswith(line.rstrip("/"))
                 or line.rstrip("/").startswith(pattern.rstrip("/"))
                 or pattern in line
                 for line in gitignore_lines
                 if line and not line.startswith("#")
             ):
                 missing.append(f"{surface.name}: {pattern}")

         assert not missing, f"Local runtime surfaces not in .gitignore: {missing}"
     ```

  2. **Test B — `RUNTIME_PROTECTED_ENTRIES` matches contract**:
     ```python
     def test_runtime_entries_match_contract():
         """GitignoreManager entries are derived from state contract."""
         from specify_cli.gitignore_manager import RUNTIME_PROTECTED_ENTRIES
         from specify_cli.state_contract import get_runtime_gitignore_entries

         contract_entries = get_runtime_gitignore_entries()
         assert set(RUNTIME_PROTECTED_ENTRIES) == set(contract_entries), (
             f"Drift detected. Manager has {set(RUNTIME_PROTECTED_ENTRIES) - set(contract_entries)} extra, "
             f"contract has {set(contract_entries) - set(RUNTIME_PROTECTED_ENTRIES)} extra"
         )
     ```

  3. **Test C — Contract runtime entries are non-empty and contain known patterns**:
     ```python
     def test_contract_runtime_entries_complete():
         entries = get_runtime_gitignore_entries()
         assert len(entries) >= 4  # at minimum: .dashboard, runtime/, merge-state, events/
         assert ".kittify/.dashboard" in entries
         assert ".kittify/merge-state.json" in entries
     ```
- **Notes**: Test A uses simple string matching against gitignore lines. This is intentionally conservative — it may produce false negatives for complex gitignore patterns (e.g., negation rules), but for our use case the patterns are simple directory/file paths.

### Subtask T008 – Create State Gitignore Migration

- **Purpose**: Add missing runtime gitignore entries to existing projects during `spec-kitty upgrade`.
- **File**: `src/specify_cli/upgrade/migrations/m_2_0_9_state_gitignore.py` (new file)
- **Steps**:
  1. Follow the existing migration pattern. Check a recent migration (e.g., `m_2_0_7_fix_stale_overrides.py`) for the class structure.
  2. The migration should:
     ```python
     """Add runtime state gitignore entries from state contract."""
     from pathlib import Path
     from specify_cli.gitignore_manager import GitignoreManager
     from specify_cli.state_contract import get_runtime_gitignore_entries

     class Migration:
         version = "2.0.9"
         description = "Add runtime state surfaces to .gitignore"

         def should_apply(self, project_path: Path) -> bool:
             # Check if any runtime entries are missing from .gitignore
             gitignore_path = project_path / ".gitignore"
             if not gitignore_path.exists():
                 return True
             content = gitignore_path.read_text()
             entries = get_runtime_gitignore_entries()
             return any(entry not in content for entry in entries)

         def apply(self, project_path: Path, dry_run: bool = False) -> str:
             if dry_run:
                 return "Would add runtime state entries to .gitignore"
             manager = GitignoreManager(project_path)
             entries = get_runtime_gitignore_entries()
             modified = manager.ensure_entries(entries)
             if modified:
                 return f"Added {len(entries)} runtime state entries to .gitignore"
             return "All runtime state entries already present in .gitignore"
     ```
  3. Register the migration in the migrations registry. Check how existing migrations are registered (likely auto-discovery by module name pattern).
- **Notes**: `ensure_entries()` is additive-only and idempotent — calling it with entries already present is a no-op. The migration must handle the case where `.gitignore` doesn't exist yet (GitignoreManager handles this).

### Subtask T009 – Write Migration Tests

- **Purpose**: Validate idempotent migration behavior on fresh and pre-existing gitignore files.
- **File**: `tests/specify_cli/test_state_gitignore_migration.py` (new file)
- **Steps**:
  1. **Test: migration adds entries to empty `.gitignore`**:
     ```python
     def test_migration_adds_entries_to_empty_gitignore(tmp_path):
         (tmp_path / ".gitignore").write_text("")
         migration = Migration()
         result = migration.apply(tmp_path)
         content = (tmp_path / ".gitignore").read_text()
         assert ".kittify/runtime/" in content
         assert ".kittify/merge-state.json" in content
         assert ".kittify/events/" in content
         assert ".kittify/dossiers/" in content
     ```
  2. **Test: migration is idempotent**:
     ```python
     def test_migration_idempotent(tmp_path):
         (tmp_path / ".gitignore").write_text("")
         migration = Migration()
         migration.apply(tmp_path)
         content_after_first = (tmp_path / ".gitignore").read_text()
         migration.apply(tmp_path)
         content_after_second = (tmp_path / ".gitignore").read_text()
         assert content_after_first == content_after_second
     ```
  3. **Test: migration preserves existing entries**:
     ```python
     def test_migration_preserves_existing(tmp_path):
         (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")
         migration = Migration()
         migration.apply(tmp_path)
         content = (tmp_path / ".gitignore").read_text()
         assert "*.pyc" in content
         assert "__pycache__/" in content
         assert ".kittify/runtime/" in content
     ```
  4. **Test: `should_apply()` returns False when all entries present**:
     ```python
     def test_should_apply_false_when_complete(tmp_path):
         entries = get_runtime_gitignore_entries()
         (tmp_path / ".gitignore").write_text("\n".join(entries) + "\n")
         migration = Migration()
         assert not migration.should_apply(tmp_path)
     ```
  5. **Test: dry run does not modify files**:
     ```python
     def test_dry_run_no_changes(tmp_path):
         (tmp_path / ".gitignore").write_text("")
         migration = Migration()
         migration.apply(tmp_path, dry_run=True)
         assert (tmp_path / ".gitignore").read_text() == ""
     ```

## Test Strategy

Run tests with:
```bash
pytest tests/specify_cli/test_gitignore_contract.py tests/specify_cli/test_state_gitignore_migration.py -v
```

## Risks & Mitigations

- **Risk**: Migration version `m_2_0_9` conflicts with another migration. **Mitigation**: Check existing migration files before creating; adjust version if needed.
- **Risk**: Import cycle if `gitignore_manager` imports `state_contract` at module level and vice versa. **Mitigation**: `state_contract` has no dependency on `gitignore_manager`; the dependency is one-way.
- **Risk**: `.kittify/missions/__pycache__/` not in audit → not in contract → missing from derived entries. **Mitigation**: Explicitly add it as a surface in the contract (see T006 notes).

## Review Guidance

- Verify `RUNTIME_PROTECTED_ENTRIES` is no longer hardcoded — it must be derived from the contract.
- Verify the migration only adds the four new entries (runtime/, merge-state.json, events/, dossiers/) plus any already-covered entries. It must NOT add constitution surfaces.
- Verify idempotency tests pass (apply twice → same result).
- Verify Test A correctly validates against the real repo `.gitignore`.

## Activity Log

- 2026-03-18T18:52:42Z – system – lane=planned – Prompt created.
- 2026-03-18T19:21:17Z – coordinator – shell_pid=21643 – lane=doing – Assigned agent via workflow command
- 2026-03-18T19:29:11Z – coordinator – shell_pid=21643 – lane=for_review – Git boundary alignment complete: derived RUNTIME_PROTECTED_ENTRIES from contract, added mission_pycache surface, created m_2_0_9 migration, 83 tests passing
- 2026-03-18T19:29:38Z – codex – shell_pid=26925 – lane=doing – Started review via workflow command
- 2026-03-18T19:36:59Z – codex – shell_pid=26925 – lane=planned – Codex review: missions/ collapse too broad, constitution entries in migration
- 2026-03-18T19:37:07Z – coordinator – shell_pid=29854 – lane=doing – Started implementation via workflow command
- 2026-03-18T19:42:21Z – coordinator – shell_pid=29854 – lane=for_review – Fixed both Codex findings: (1) missions/__pycache__/ no longer collapsed to missions/, (2) migration scoped to 4 new entries only
- 2026-03-18T19:42:47Z – codex – shell_pid=32698 – lane=doing – Started review via workflow command
