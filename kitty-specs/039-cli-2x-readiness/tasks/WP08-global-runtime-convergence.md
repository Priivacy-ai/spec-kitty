---
work_package_id: "WP08"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "Converge global runtime resolution"
phase: "Wave 1 - Independent Fixes"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP08 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Converge global runtime resolution

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP08
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- After `spec-kitty migrate`, zero legacy fallback warnings during normal template resolution
- Resolution chain includes `~/.kittify/` between project-level paths and package defaults
- `spec-kitty migrate` is idempotent (running twice produces identical state)
- Pre-migration projects get a clear "run `spec-kitty migrate`" message (not warning flood)
- Credential path decision documented: `~/.spec-kitty/credentials` stays separate

## Context & Constraints

- **Delivery branch**: 2.x
- **Current state on 2.x**: Partial `~/.kittify` global runtime bootstrap exists, but still shows legacy fallback warnings
- **Resolution target order**: project `.kittify/missions/{key}/templates/` → project `.kittify/templates/` → `~/.kittify/missions/{key}/templates/` → `~/.kittify/templates/` → package defaults
- **Key file**: `src/specify_cli/core/project_resolver.py` — contains `resolve_template_path()` and `locate_project_root()`
- **Migrate command**: `src/specify_cli/cli/commands/migrate.py` — already exists, needs idempotency and global install
- **Credential path**: `~/.spec-kitty/credentials` stays separate from `~/.kittify/` (different security model)
- **Reference**: `spec.md` (User Story 4, FR-009/010/011), `plan.md` (WP08), `research.md` (R3)

## Subtasks & Detailed Guidance

### Subtask T034 – Audit current resolution chain on 2.x

- **Purpose**: Understand what already exists before making changes. 2.x has partial global runtime — don't duplicate or break existing work.
- **Steps**:
  1. Read `src/specify_cli/core/project_resolver.py` on 2.x:
     ```bash
     git show 2.x:src/specify_cli/core/project_resolver.py
     ```
  2. Identify the `resolve_template_path()` function and trace its resolution chain
  3. Document the current chain:
     - Where does it look first? (project `.kittify/`?)
     - Does it already look in `~/.kittify/`?
     - Where does it fall back to? (package defaults?)
     - When does it emit warnings?
  4. Read `src/specify_cli/cli/commands/migrate.py` to understand current migration behavior
  5. Check for any `~/.kittify` references already in the codebase:
     ```bash
     grep -rn "\.kittify\|home.*kittify\|expanduser.*kittify" src/specify_cli/
     ```
  6. Document findings as comments in your implementation PR
- **Files**: Read-only (audit)
- **Parallel?**: No — must complete before T035-T039
- **Notes**: Do NOT assume the 2.x codebase matches main. It may already have partial global runtime logic.

### Subtask T035 – Add ~/.kittify to resolution chain

- **Purpose**: Make template resolution check the global runtime directory.
- **Steps**:
  1. In `resolve_template_path()`, add `~/.kittify/` to the search path:
     ```python
     from pathlib import Path

     def resolve_template_path(template_name: str, mission_key: str = None, project_root: Path = None) -> Path:
         candidates = []

         # 1. Project-level: .kittify/missions/{key}/templates/
         if project_root and mission_key:
             candidates.append(project_root / ".kittify" / "missions" / mission_key / "templates" / template_name)

         # 2. Project-level: .kittify/templates/
         if project_root:
             candidates.append(project_root / ".kittify" / "templates" / template_name)

         # 3. Global: ~/.kittify/missions/{key}/templates/
         home_kittify = Path.home() / ".kittify"
         if mission_key:
             candidates.append(home_kittify / "missions" / mission_key / "templates" / template_name)

         # 4. Global: ~/.kittify/templates/
         candidates.append(home_kittify / "templates" / template_name)

         # 5. Package defaults (bundled in src/specify_cli/missions/)
         candidates.append(get_package_template_path(template_name, mission_key))

         for candidate in candidates:
             if candidate.exists():
                 return candidate

         raise FileNotFoundError(f"Template '{template_name}' not found in any resolution path")
     ```
  2. Adapt this to the actual function signature on 2.x (may already have some of this)
  3. Ensure the function handles missing `project_root` gracefully (e.g., running outside a project)
- **Files**: `src/specify_cli/core/project_resolver.py` (edit)
- **Parallel?**: No — core change, must be done carefully

### Subtask T036 – Eliminate legacy fallback warnings after migration

- **Purpose**: After a user runs `spec-kitty migrate`, no warning messages should appear during normal operations.
- **Steps**:
  1. Find where legacy fallback warnings are emitted:
     ```bash
     grep -rn "warn\|fallback\|legacy\|deprecat" src/specify_cli/core/project_resolver.py
     ```
  2. Add a check: if `~/.kittify/` exists and has content, suppress legacy warnings
  3. Implementation:
     ```python
     def _is_global_runtime_configured() -> bool:
         """Check if ~/.kittify has been set up by spec-kitty migrate."""
         home_kittify = Path.home() / ".kittify"
         return (home_kittify / "templates").exists() or (home_kittify / "missions").exists()

     # In the warning path:
     if not _is_global_runtime_configured():
         # Emit warning only if global runtime is NOT configured
         warn_once("...")
     ```
  4. Ensure warnings are suppressed ONLY after migration, not for brand-new installs
- **Files**: `src/specify_cli/core/project_resolver.py` (edit)
- **Parallel?**: No — depends on T035

### Subtask T037 – Emit one-time "run spec-kitty migrate" message

- **Purpose**: Guide users who haven't migrated without flooding them with warnings on every command.
- **Steps**:
  1. When resolution falls through to legacy/package-default paths AND `~/.kittify/` doesn't exist:
     ```python
     _migrate_warning_shown = False

     def _warn_migrate_once():
         global _migrate_warning_shown
         if not _migrate_warning_shown:
             import sys
             print("Note: Run `spec-kitty migrate` to set up global runtime (~/.kittify/)", file=sys.stderr)
             _migrate_warning_shown = True
     ```
  2. Call this function when a template resolves from package defaults (step 5 in the chain) and `~/.kittify/` doesn't exist
  3. This is a soft nudge, not an error — the CLI should still work without migration
  4. Use `stderr` so it doesn't interfere with JSON output from `--json` flags
- **Files**: `src/specify_cli/core/project_resolver.py` (edit)
- **Parallel?**: No — depends on T035/T036

### Subtask T038 – Make spec-kitty migrate idempotent

- **Purpose**: Users should be able to run `spec-kitty migrate` multiple times without issues.
- **Steps**:
  1. Read `src/specify_cli/cli/commands/migrate.py` on 2.x
  2. Add global runtime installation to the migrate command:
     ```python
     def install_global_runtime():
         """Install templates and missions to ~/.kittify/."""
         home_kittify = Path.home() / ".kittify"

         # Create directories
         (home_kittify / "templates").mkdir(parents=True, exist_ok=True)
         (home_kittify / "missions").mkdir(parents=True, exist_ok=True)

         # Copy package templates to global location
         package_templates = get_package_templates_dir()
         for template in package_templates.glob("**/*"):
             if template.is_file():
                 dest = home_kittify / "templates" / template.relative_to(package_templates)
                 dest.parent.mkdir(parents=True, exist_ok=True)
                 # Only copy if source is newer or dest doesn't exist
                 if not dest.exists() or template.stat().st_mtime > dest.stat().st_mtime:
                     shutil.copy2(template, dest)

         # Copy mission configs similarly
         # ...
     ```
  3. Ensure idempotency:
     - `mkdir(exist_ok=True)` for directories
     - Only overwrite if source is newer (or use checksum comparison)
     - Don't delete user customizations in `~/.kittify/`
  4. Report what was installed: "Global runtime: X templates installed to ~/.kittify/"
  5. Add `--dry-run` flag to preview what would be installed:
     ```python
     if dry_run:
         console.print("Would install N templates to ~/.kittify/templates/")
         return
     ```
- **Files**: `src/specify_cli/cli/commands/migrate.py` (edit)
- **Parallel?**: No — depends on understanding T034's audit

### Subtask T039 – Write tests for resolution chain

- **Purpose**: Validate the resolution chain works correctly in all scenarios.
- **Steps**:
  1. Create or extend `tests/specify_cli/core/test_project_resolver.py`:
     ```python
     def test_resolves_from_project_mission_templates(tmp_path, monkeypatch):
         """Template in project .kittify/missions/{key}/templates/ is found first."""

     def test_resolves_from_project_templates(tmp_path, monkeypatch):
         """Template in project .kittify/templates/ is found second."""

     def test_resolves_from_global_mission_templates(tmp_path, monkeypatch):
         """Template in ~/.kittify/missions/{key}/templates/ is found third."""

     def test_resolves_from_global_templates(tmp_path, monkeypatch):
         """Template in ~/.kittify/templates/ is found fourth."""

     def test_resolves_from_package_defaults(tmp_path, monkeypatch):
         """Falls back to package defaults when no other source exists."""

     def test_no_warning_after_migration(tmp_path, monkeypatch, capsys):
         """No legacy warnings when ~/.kittify/ exists."""

     def test_one_time_warning_before_migration(tmp_path, monkeypatch, capsys):
         """One-time migrate nudge when ~/.kittify/ doesn't exist."""

     def test_migrate_idempotent(tmp_path, monkeypatch):
         """Running migrate twice produces identical state."""
     ```
  2. Use `monkeypatch` to override `Path.home()`:
     ```python
     @pytest.fixture
     def mock_home(tmp_path, monkeypatch):
         home_dir = tmp_path / "home"
         home_dir.mkdir()
         monkeypatch.setattr(Path, "home", lambda: home_dir)
         return home_dir
     ```
  3. Run: `python -m pytest tests/specify_cli/core/test_project_resolver.py -x -v`
- **Files**: `tests/specify_cli/core/test_project_resolver.py` (new/extend)
- **Parallel?**: No — depends on T035-T038

## Test Strategy

- **New tests**: ~8 tests covering all resolution paths, warnings, and idempotency
- **Run command**: `python -m pytest tests/specify_cli/core/test_project_resolver.py -x -v`
- **Fixtures**: Mock home directory with `monkeypatch`, temp project directories

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 2.x already has partial global runtime logic | Audit first (T034); extend, don't duplicate |
| migrate.py has different structure on 2.x | Read before editing; adapt to actual structure |
| Overwriting user customizations in ~/.kittify/ | Only copy if source is newer; never delete user files |
| Breaking existing project-level resolution | Test both with and without project root |

## Review Guidance

- Verify resolution chain order: project-mission → project → global-mission → global → package
- Verify no warnings after successful migration
- Verify migrate is idempotent (run twice, check same state)
- Verify pre-migration projects still work (graceful degradation)
- Run `python -m pytest tests/specify_cli/core/test_project_resolver.py -x -v` — all green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
