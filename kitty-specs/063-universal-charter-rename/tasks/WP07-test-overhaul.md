---
work_package_id: WP07
title: Test Overhaul
dependencies: [WP01, WP02, WP03, WP06]
requirement_refs:
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning branch: main. Merge target: main. Depends on WP01, WP02, WP03, WP06 — use spec-kitty implement WP07 --base WP03 (or whichever completes last).'
subtasks: [T039, T040, T041, T042, T043, T044, T045]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/
execution_mode: code_change
owned_files: [tests/**]
---

# WP07: Test Overhaul

## Objective

Rename all test directories and files containing "constitution". Update all test content (imports, strings, paths, assertions, fixtures). Write comprehensive tests for the charter-rename migration and metadata normalization.

## Context

The test suite has 16 files in `tests/constitution/` plus 8 additional test files with "constitution" in their names, plus references in worktree tests. All must be renamed and updated. New tests are needed for the charter-rename migration (WP06) and metadata normalization.

## Implementation Command

```bash
spec-kitty implement WP07 --base WP03
```

## Subtask T039: Rename tests/constitution/ → tests/charter/ + update content

**Purpose**: Rename the main constitution test directory and update all 16 files within.

**Steps**:
1. `git mv tests/constitution/ tests/charter/`
2. For each of the 16 files in `tests/charter/`:
   - Update imports: `from constitution.X` → `from charter.X`, `from specify_cli.constitution.X` → `from specify_cli.charter.X`
   - Update class/function references: `CompiledConstitution` → `CompiledCharter`, `ConstitutionParser` → `CharterParser`, etc.
   - Update string literals: path references, error messages, test data containing "constitution"
   - Update fixture names and return values
   - Update test function names if they contain "constitution"
3. Files to update:
   - `conftest.py`, `test_catalog.py`, `test_compiler.py`, `test_context.py`, `test_extractor.py`, `test_generator.py`, `test_hasher.py`, `test_integration.py`, `test_interview.py`, `test_parser.py`, `test_reference_resolver.py`, `test_resolver.py`, `test_schemas.py`, `test_sync.py`, `test_template_resolver.py`, `__init__.py`

**Validation**: `rg -i constitution tests/charter/` returns zero matches. `python -m pytest tests/charter/ -x -q` passes.

## Subtask T040: Rename 8 additional test files + update content

**Purpose**: Rename scattered test files with "constitution" in their names.

**Steps**: For each file, `git mv` then update content:

1. `tests/init/test_constitution_runtime_integration.py` → `tests/init/test_charter_runtime_integration.py`
2. `tests/test_dashboard/test_api_constitution.py` → `tests/test_dashboard/test_api_charter.py`
3. `tests/upgrade/migrations/test_constitution_migration.py` → `tests/upgrade/migrations/test_charter_migration.py`
4. `tests/upgrade/test_constitution_template_migration.py` → `tests/upgrade/test_charter_template_migration.py`
5. `tests/upgrade/test_migration_constitution_cleanup_unit.py` → `tests/upgrade/test_migration_charter_cleanup_unit.py`
6. `tests/merge/test_profile_constitution_e2e.py` → `tests/merge/test_profile_charter_e2e.py`
7. `tests/agent/cli/commands/test_constitution_cli.py` → `tests/agent/cli/commands/test_charter_cli.py`
8. `tests/agent/test_workflow_constitution_context.py` → `tests/agent/test_workflow_charter_context.py`

For each renamed file:
- Update imports to charter modules
- Update all string literals, path references, fixture names
- Update test class and function names if they contain "constitution"
- Update mock targets: `patch("specify_cli.constitution.X")` → `patch("specify_cli.charter.X")`

**Important**: The migration tests (items 3, 4, 5) now test STUB behavior, not the old migration logic. Update assertions to verify stubs return `detect() → False` and `success=True`.

**Validation**: `rg -i constitution` on each renamed file returns zero matches.

## Subtask T041: Update tests/git_ops/test_worktree.py

**Purpose**: Update worktree tests that reference constitution.md.

**Steps**:
1. In `tests/git_ops/test_worktree.py`:
   - Line ~339: `(memory_dir / "constitution.md").write_text("Constitution content")` → `(memory_dir / "charter.md").write_text("Charter content")` (or update to use `.kittify/charter/charter.md` path)
   - Line ~349: `assert (worktree_memory / "constitution.md").read_text() == "Constitution content"` → update assertion
   - Line ~875: `(memory_dir / "constitution.md").write_text("Constitution")` → update
   - Any other "constitution" references in the file

**Note**: The worktree memory path may have changed (from `.kittify/memory/constitution.md` to `.kittify/charter/charter.md`). Align test expectations with the updated `setup_feature_directory()` from WP02.

**Validation**: `rg -i constitution tests/git_ops/test_worktree.py` returns zero matches.

## Subtask T042: Write charter-rename migration tests (layouts A, B, C)

**Purpose**: Test the comprehensive charter-rename migration handles all 3 legacy layouts.

**Steps**: Create test file (e.g., `tests/upgrade/test_charter_rename_migration.py`):

**Test Layout A**:
```python
def test_layout_a_migration(tmp_path):
    """Modern .kittify/constitution/ directory is renamed to .kittify/charter/."""
    kittify = tmp_path / ".kittify"
    const_dir = kittify / "constitution"
    const_dir.mkdir(parents=True)
    (const_dir / "constitution.md").write_text("# Project Constitution")
    (const_dir / "governance.yaml").write_text("testing: {}")
    (const_dir / "references.yaml").write_text('source_path: ".kittify/constitution/interview/answers.yaml"')
    
    migration = CharterRenameMigration()
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    
    assert result.success
    assert not const_dir.exists()
    charter_dir = kittify / "charter"
    assert (charter_dir / "charter.md").exists()
    assert (charter_dir / "governance.yaml").exists()
```

**Test Layout B**:
```python
def test_layout_b_migration(tmp_path):
    """Legacy .kittify/memory/constitution.md is moved to .kittify/charter/charter.md."""
    memory_dir = tmp_path / ".kittify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text("# Constitution")
    
    migration = CharterRenameMigration()
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    
    assert result.success
    assert not (memory_dir / "constitution.md").exists()
    assert (tmp_path / ".kittify" / "charter" / "charter.md").exists()
```

**Test Layout C**:
```python
def test_layout_c_migration(tmp_path):
    """Pre-0.10.12 mission-specific constitutions are removed."""
    missions = tmp_path / ".kittify" / "missions"
    (missions / "software-dev" / "constitution").mkdir(parents=True)
    (missions / "software-dev" / "constitution" / "local.md").write_text("old")
    
    migration = CharterRenameMigration()
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    
    assert result.success
    assert not (missions / "software-dev" / "constitution").exists()
```

**Validation**: All 3 tests pass.

## Subtask T043: Write content rewriting + agent prompt tests

**Purpose**: Test that embedded "constitution" references are rewritten in generated files and agent prompts.

**Steps**: Add tests to the charter-rename test file:

```python
def test_content_rewriting(tmp_path):
    """Generated files have embedded constitution references rewritten."""
    charter_dir = tmp_path / ".kittify" / "constitution"
    charter_dir.mkdir(parents=True)
    (charter_dir / "constitution.md").write_text("# Project Constitution\n<!-- Generated by spec-kitty constitution generate -->")
    (charter_dir / "references.yaml").write_text('source_path: ".kittify/constitution/interview/answers.yaml"')
    
    migration = CharterRenameMigration()
    result = migration.apply(tmp_path)
    
    assert result.success
    content = (tmp_path / ".kittify" / "charter" / "charter.md").read_text()
    assert "constitution" not in content.lower()
    assert "Charter" in content
    
    refs = (tmp_path / ".kittify" / "charter" / "references.yaml").read_text()
    assert "constitution" not in refs.lower()
    assert "charter" in refs

def test_agent_prompt_command_rewrite(tmp_path):
    """Agent prompts have bootstrap command updated."""
    # Setup: create agent prompt with old command
    claude_dir = tmp_path / ".claude" / "commands"
    claude_dir.mkdir(parents=True)
    (claude_dir / "spec-kitty.specify.md").write_text(
        "Run: spec-kitty constitution context --action specify --json"
    )
    # Also create constitution dir so migration detects work
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)
    (tmp_path / ".kittify" / "constitution" / "constitution.md").write_text("test")
    
    migration = CharterRenameMigration()
    result = migration.apply(tmp_path)
    
    assert result.success
    prompt = (claude_dir / "spec-kitty.specify.md").read_text()
    assert "constitution" not in prompt.lower()
    assert "charter" in prompt
```

**Validation**: Content rewriting and prompt tests pass.

## Subtask T044: Write metadata normalization tests

**Purpose**: Test that old migration IDs in metadata are rewritten to charter-era IDs.

**Steps**: Create or add to test file:

```python
def test_metadata_normalization_rewrites_old_ids(tmp_path):
    """Old constitution-era migration IDs are rewritten to charter-era IDs on load."""
    metadata_dir = tmp_path / ".kittify"
    metadata_dir.mkdir(parents=True)
    # Write metadata with old-style IDs
    (metadata_dir / "metadata.yaml").write_text("""
spec_kitty:
  version: 3.1.0a0
migrations:
  applied:
    - id: "0.10.12_constitution_cleanup"
      applied_at: "2026-01-01T00:00:00"
      result: "success"
    - id: "2.0.0_constitution_directory"
      applied_at: "2026-01-02T00:00:00"
      result: "success"
""")
    
    metadata = ProjectMetadata.load(metadata_dir)
    
    # IDs should be normalized
    ids = [m.id for m in metadata.applied_migrations]
    assert "0.10.12_charter_cleanup" in ids
    assert "2.0.0_charter_directory" in ids
    assert "0.10.12_constitution_cleanup" not in ids

def test_metadata_normalization_persists(tmp_path):
    """Normalization writes back to file so it only happens once."""
    # Same setup as above, verify file is rewritten

def test_metadata_normalization_noop_when_already_charter(tmp_path):
    """No changes when IDs are already charter-era."""
    # Setup with charter-era IDs, verify no write
```

**Validation**: All metadata normalization tests pass.

## Subtask T045: Write idempotency + partial state tests

**Purpose**: Test edge cases: running migration twice, partial state, concurrent conditions.

**Steps**:

```python
def test_idempotency(tmp_path):
    """Running migration twice produces same result."""
    # Setup Layout A
    const_dir = tmp_path / ".kittify" / "constitution"
    const_dir.mkdir(parents=True)
    (const_dir / "constitution.md").write_text("# Project Constitution")
    
    migration = CharterRenameMigration()
    result1 = migration.apply(tmp_path)
    assert result1.success
    
    # Second run: detect should return False
    assert migration.detect(tmp_path) is False

def test_partial_state_both_exist(tmp_path):
    """Both constitution/ and charter/ exist — merge and cleanup."""
    kittify = tmp_path / ".kittify"
    (kittify / "constitution").mkdir(parents=True)
    (kittify / "constitution" / "constitution.md").write_text("old")
    (kittify / "constitution" / "extra.yaml").write_text("extra")
    (kittify / "charter").mkdir(parents=True)
    (kittify / "charter" / "charter.md").write_text("new")
    
    migration = CharterRenameMigration()
    result = migration.apply(tmp_path)
    
    assert result.success
    assert not (kittify / "constitution").exists()
    # charter.md preserved (not overwritten)
    assert (kittify / "charter" / "charter.md").read_text() == "new"
    # extra.yaml merged
    assert (kittify / "charter" / "extra.yaml").exists()

def test_no_constitution_state(tmp_path):
    """Fresh project with no constitution state — detect returns False."""
    (tmp_path / ".kittify").mkdir()
    migration = CharterRenameMigration()
    assert migration.detect(tmp_path) is False

def test_stale_memory_file_removed(tmp_path):
    """Memory/constitution.md removed when charter/charter.md already exists."""
    kittify = tmp_path / ".kittify"
    (kittify / "memory").mkdir(parents=True)
    (kittify / "memory" / "constitution.md").write_text("stale")
    (kittify / "charter").mkdir(parents=True)
    (kittify / "charter" / "charter.md").write_text("current")
    
    migration = CharterRenameMigration()
    result = migration.apply(tmp_path)
    
    assert result.success
    assert not (kittify / "memory" / "constitution.md").exists()
    assert (kittify / "charter" / "charter.md").read_text() == "current"
```

**Validation**: All edge case tests pass.

## Definition of Done

- [ ] `tests/constitution/` does not exist; `tests/charter/` exists with 16 updated files
- [ ] 8 additional test files renamed and content updated
- [ ] `tests/git_ops/test_worktree.py` updated (zero "constitution")
- [ ] Charter-rename migration tests: Layout A, B, C all pass
- [ ] Content rewriting tests pass
- [ ] Metadata normalization tests pass
- [ ] Idempotency + partial state tests pass
- [ ] `python -m pytest tests/ -x -q` passes (full suite)
- [ ] `rg -i constitution tests/` returns zero matches

## Risks

- **Test pollution**: Existing tests may have fixtures or conftest entries that reference constitution. Search broadly.
- **Mock targets**: `@patch("specify_cli.constitution.X")` must become `@patch("specify_cli.charter.X")`.
- **Pre-existing failures**: ~50 tests may fail in full suite due to pre-existing cross-test pollution (documented in MEMORY.md). Focus on zero NEW failures.

## Reviewer Guidance

- Verify all mock/patch targets use charter paths
- Check that migration tests cover all 3 layouts + edge cases
- Verify content rewriting tests check for ABSENCE of "constitution" (not just presence of "charter")
- Verify metadata tests confirm file persistence after normalization
