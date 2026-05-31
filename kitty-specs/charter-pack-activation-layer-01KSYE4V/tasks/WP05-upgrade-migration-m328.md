---
work_package_id: WP05
title: 'Upgrade Migration m_3_2_8: Default Charter Pack'
dependencies:
- WP04
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: All changes land on pr/charter-doctrine-mission-type-configuration. Worktree allocated by finalize-tasks.
subtasks:
- T020
- T021
- T022
- T023
agent: claude
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py
- tests/upgrade/test_m_3_2_8_default_charter_pack.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, fix
only what is described, run validation after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Create migration `m_3_2_8_default_charter_pack` that writes the default charter-pack
activation keys into `.kittify/config.yaml` for projects that lack them. The migration
is incremental: only absent keys are written; present keys are never overwritten. It
also backs up any existing `charter.md` before touching config, and degrades gracefully
when `default.yaml` is not found.

This WP has a declared dependency on WP04 (which delivers `CharterPackManager` and
`default.yaml`). WP04 must be in `approved` or `done` before you start.

---

## Context

`m_3_2_7_activate_builtin_mission_types` (already merged) sets
`mission_type_activations`. This migration extends the same pattern to the eight
per-kind activation keys (`activated_directives`, `activated_tactics`, etc.) as well
as `activated_kinds` and `mission_type_activations` (if still absent). Without this
migration, existing projects that pre-date the per-kind keys would silently get
no-activation-filter behavior on their first upgrade, which would expose every doctrine
artifact indiscriminately.

**CRITICAL**: `target_version = "3.2.8"` means this migration NEVER fires against rc
versions (e.g. `3.2.0rc30`). All tests MUST call `detect()` and `apply()` directly —
never via the upgrade pipeline — so rc version checks do not interfere with the test
suite.

Reference implementation: `src/specify_cli/upgrade/migrations/m_3_2_7_activate_builtin_mission_types.py`

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration` in the
lane worktree allocated by `finalize-tasks`. Do not create additional git branches.

---

## Requirement Refs

FR-002, FR-003, NFR-002, NFR-005

---

## Subtasks

---

### T020 — Create migration skeleton with detect / can_apply / apply

**Requirement refs**: FR-002, FR-003

**Files**:
- `src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py` (new)

**Steps**:

1. Read `src/specify_cli/upgrade/migrations/m_3_2_7_activate_builtin_mission_types.py`
   in full to understand the exact class structure and registration idiom before
   writing a single line.

2. Create `src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py`.
   Start with the module docstring explaining the migration's purpose and idempotency
   contract (model the docstring style on `m_3_2_7`).

3. Define the constant at module level:

   ```python
   _PER_KIND_KEYS: list[str] = [
       "activated_directives",
       "activated_tactics",
       "activated_styleguides",
       "activated_toolguides",
       "activated_paradigms",
       "activated_procedures",
       "activated_agent_profiles",
       "activated_mission_step_contracts",
   ]
   ```

4. Register and define the migration class:

   ```python
   @MigrationRegistry.register
   class DefaultCharterPackMigration(BaseMigration):
       migration_id = "3.2.8_default_charter_pack"
       description = (
           "Write per-kind activation keys from default.yaml into "
           ".kittify/config.yaml for projects that lack them (FR-002, FR-003)."
       )
       target_version = "3.2.8"
   ```

5. Implement `detect(self, project_path: Path) -> bool`:
   - Return `False` if `project_path / ".kittify"` does not exist.
   - Load `project_path / ".kittify" / "config.yaml"` with `YAML(typ="safe")`.
   - Return `True` if **any** key from
     `_PER_KIND_KEYS + ["activated_kinds", "mission_type_activations"]` is absent
     from the loaded dict. Return `False` if all keys are present.
   - On any exception (parse error, missing file): return `False`.

6. Implement `can_apply(self, project_path: Path) -> tuple[bool, str]`:
   - Returns `(self.detect(project_path), "")` when detect is True.
   - Returns `(False, "no migration needed")` otherwise.

7. Add a skeleton `apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:`
   with a `raise NotImplementedError` body — T021 fills the real logic.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from specify_cli.upgrade.migrations.m_3_2_8_default_charter_pack import DefaultCharterPackMigration; print('import ok')"
```
Expected: `import ok` (no errors).

---

### T021 — Implement backup pattern and apply() logic

**Requirement refs**: FR-002, FR-003, NFR-002, C-008

**Files**:
- `src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py`

**Steps**:

1. Locate `default.yaml`. The canonical path at runtime is:

   ```python
   _DEFAULT_YAML_PATH = Path(__file__).parent.parent.parent / "charter" / "packs" / "default.yaml"
   ```

   Add this as a module-level constant.

2. Fill in `apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult`:

   a. **Guard — default.yaml missing** (broken install):
      ```python
      if not _DEFAULT_YAML_PATH.exists():
          return MigrationResult(
              success=False,
              errors=[f"default.yaml not found at {_DEFAULT_YAML_PATH}"],
          )
      ```
      Do NOT let `FileNotFoundError` propagate to the caller.

   b. **Backup** (NFR-002, C-008):
      - Check if `project_path / ".kittify" / "charter" / "charter.md"` exists.
      - If yes and `dry_run` is False:
        - Create `project_path / ".kittify" / "charter" / "backups" /` directory
          with `mkdir(parents=True, exist_ok=True)`.
        - Build backup filename:
          `f"charter-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.md"`
        - Copy with `shutil.copy2(charter_md_path, backup_path)`.
        - Emit warning via `rich.console.Console()`:
          `f"Existing charter backed up to {backup_path}. Review after upgrade."`
        - The backup must complete **before** any write to `config.yaml`.

   c. **Load config** (ruamel.yaml round-trip):
      ```python
      yaml = YAML()
      yaml.preserve_quotes = True
      try:
          data = yaml.load(config_file) or {}
      except Exception as exc:
          return MigrationResult(success=False, errors=[f"Invalid YAML: {exc}"])
      ```

   d. **Load default.yaml** (safe load, values only):
      ```python
      safe_yaml = YAML(typ="safe")
      defaults = safe_yaml.load(_DEFAULT_YAML_PATH) or {}
      ```

   e. **Incremental write**: for each key in
      `_PER_KIND_KEYS + ["activated_kinds", "mission_type_activations"]`:
      - If the key is absent from `data`: write `data[key] = defaults.get(key, [])`.
      - If already present: skip (never overwrite).

   f. **dry_run path**: skip the file write and the backup; return
      `MigrationResult(success=True, changes_made=["dry-run: would write missing keys"])`.

   g. **Write back**:
      ```python
      with config_file.open("w", encoding="utf-8") as fh:
          yaml.dump(data, fh)
      ```

   h. Return `MigrationResult(success=True, changes_made=[...list of keys written...])`.

3. Add required imports at the top of the file:
   `datetime`, `shutil`, `YAML` from `ruamel.yaml`, `Console` from `rich.console`,
   `MigrationRegistry`, `BaseMigration`, `MigrationResult`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "
from pathlib import Path
from specify_cli.upgrade.migrations.m_3_2_8_default_charter_pack import DefaultCharterPackMigration
m = DefaultCharterPackMigration()
print('apply signature ok:', m.apply.__doc__ or 'no docstring')
"
```
Expected: runs without error.

---

### T022 — Write direct detect() / apply() tests

**Requirement refs**: FR-002, FR-003, NFR-002, NFR-005

**Files**:
- `tests/upgrade/test_m_3_2_8_default_charter_pack.py` (new)

**Steps**:

1. Create the test file. Use `pytest` with `tmp_path` fixtures throughout. Import
   `DefaultCharterPackMigration` from
   `specify_cli.upgrade.migrations.m_3_2_8_default_charter_pack`. Do NOT call any
   upgrade pipeline function — call `detect()` and `apply()` directly.

2. Write the following test functions:

   **`test_detect_returns_false_without_kittify`**
   - `tmp_path` with no `.kittify/` directory → `detect(tmp_path)` returns `False`.

   **`test_detect_returns_true_when_any_per_kind_key_absent`**
   - Create `tmp_path / ".kittify" / "config.yaml"` containing only
     `activated_kinds: []` (but none of the 8 per-kind keys).
   - `detect(tmp_path)` returns `True`.

   **`test_detect_returns_false_when_all_keys_present`**
   - Create `config.yaml` with all 8 per-kind keys plus `activated_kinds` and
     `mission_type_activations` present (values can be empty lists).
   - `detect(tmp_path)` returns `False`.

   **`test_apply_writes_absent_keys_from_default_pack`**
   - Create minimal `.kittify/config.yaml` (no per-kind keys).
   - Call `apply(tmp_path)`.
   - Reload `config.yaml` with `YAML(typ="safe")`.
   - Assert all 8 per-kind keys are present in the output.
   - Assert that values match what `default.yaml` defines for each key (use the real
     `_DEFAULT_YAML_PATH` to load the expected values).

   **`test_apply_does_not_overwrite_existing_keys`**
   - Create `config.yaml` with `activated_directives: ["my-custom-directive"]`.
   - Call `apply(tmp_path)`.
   - Reload config and assert `activated_directives == ["my-custom-directive"]`
     (value unchanged).

   **`test_apply_creates_backup_when_charter_md_exists`**
   - Create `tmp_path / ".kittify" / "charter" / "charter.md"` with content
     `"# My Charter"`.
   - Call `apply(tmp_path)`.
   - Assert that `tmp_path / ".kittify" / "charter" / "backups" /` exists and
     contains exactly one file matching `charter-*.md`.
   - Assert that backup file content equals `"# My Charter"`.

   **`test_apply_handles_missing_default_yaml_gracefully`**
   - Use `unittest.mock.patch` to set `m_3_2_8_default_charter_pack._DEFAULT_YAML_PATH`
     to a non-existent path.
   - Create minimal `.kittify/config.yaml`.
   - Call `apply(tmp_path)`.
   - Assert `result.success is False`.
   - Assert `"default.yaml not found" in result.errors[0]`.

3. Mark all tests with `@pytest.mark.fast` (they are pure filesystem operations).

4. Add a module docstring explaining that all tests call `detect`/`apply` directly
   to avoid the version guard that prevents `3.2.8` from firing on rc builds.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/upgrade/test_m_3_2_8_default_charter_pack.py -x -v
```
Expected: all 7 tests pass.

---

### T023 — Register migration and verify baseline alignment

**Requirement refs**: NFR-005

**Files**:
- `src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py` (verify `@MigrationRegistry.register`)
- `tests/architectural/test_no_dead_modules.py` (read-only verification)
- `tests/architectural/_baselines.yaml` (read-only verification)

**Steps**:

1. Confirm `@MigrationRegistry.register` is present on `DefaultCharterPackMigration`
   (should be in place from T020). If missing, add it.

2. Verify — do NOT edit — that `tests/architectural/test_no_dead_modules.py` already
   contains `"m_3_2_8_default_charter_pack"` in its auto-discovered-migrations
   allowlist (added by WP01/T003). If it is absent, that is a WP01 gap: open a
   blocker note in the commit message and add the entry yourself under the same
   allowlist, following existing alphabetical ordering.

3. Verify — do NOT edit — that `tests/architectural/_baselines.yaml` shows:
   ```yaml
   category_1_auto_discovered_migrations: 73
   ```
   (bumped by WP01/T003). If the value differs, add a comment to the commit noting
   the discrepancy; adjust the value if required to match the actual count after both
   `m_3_2_7` and `m_3_2_8` are registered.

4. Run the architectural gate:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   pytest tests/architectural/test_no_dead_modules.py -x -v
   ```
   Expected: all tests pass. If they fail, resolve before moving on.

**Validation** (full gate):
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/upgrade/test_m_3_2_8_default_charter_pack.py tests/architectural/test_no_dead_modules.py -x -v
```
Expected: both test modules pass with zero failures.

---

## Definition of Done

Before marking WP05 as `for_review`:

- [ ] `pytest tests/upgrade/test_m_3_2_8_default_charter_pack.py -x` — all 7 tests
  pass.
- [ ] `pytest tests/architectural/test_no_dead_modules.py -x` — passes (migration is
  registered and allowlisted).
- [ ] Manual version-guard spot-check: instantiate `DefaultCharterPackMigration()` and
  confirm `target_version == "3.2.8"` (rc versions such as `3.2.0rc30` must not
  trigger the migration in normal upgrade pipeline execution).
- [ ] `ruff check src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py`
  — no lint errors.
- [ ] `mypy src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py
  --strict` — no type errors.
- [ ] No files outside `owned_files` were modified.
