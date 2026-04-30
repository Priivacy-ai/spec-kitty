---
work_package_id: WP01
title: Compatibility Registry and Bundle Schema Version Infrastructure
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-p7-schema-versioning-provenance-01KQEG13
base_commit: aa832233760ba5a11bc54800dd90b094c3cd4e0a
created_at: '2026-04-30T07:03:36.565638+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
agent: claude:opus-4-7:reviewer-renata:reviewer
shell_pid: '54664'
history:
- at: '2026-04-30T06:23:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files:
- src/doctrine/versioning.py
- src/charter/schemas.py
- src/charter/extractor.py
- tests/doctrine/__init__.py
- tests/doctrine/test_versioning.py
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — Compatibility Registry and Bundle Schema Version Infrastructure

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load reviewer-renata
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Create `src/doctrine/versioning.py` — the compatibility registry that maps bundle integer schema versions to supported CLI version ranges and migration functions. Wire `bundle_schema_version` into `ExtractionMetadata` and stamp it on every new bundle written by `extractor.py`. Write a comprehensive unit test suite for the registry.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` (Lane A); do not guess the worktree path

## Context

Charter synthesis bundles currently have no integer schema version field. This WP creates the foundation: a pure-Python compatibility registry that other modules call to decide whether a bundle can be read or needs migration. WP02 works on the Pydantic model layer. WP03 depends on both WP01 and WP02; it completes the `migrate_v1_to_v2()` implementation and wires the reader blocks into the CLI.

**Execution workspace**: all three WPs are in **lane-a**. WP01 and WP02 can be done in either order within the lane; WP03 must come after both.

**Working directory**: `src/` (run `cd src && mypy --strict doctrine/versioning.py` for type-checks; run `cd src && pytest ../tests/doctrine/` for tests).

**Key invariants**:
- `src/doctrine/` already exists as a package (`__init__.py` present) — do not recreate it
- `CURRENT_BUNDLE_SCHEMA_VERSION = 2` (the version Phase 7 synthesis will write)
- `MIN_READABLE_BUNDLE_SCHEMA = 1` (oldest version this CLI can read after migration)
- `MAX_READABLE_BUNDLE_SCHEMA = 2` (newest version this CLI reads natively)
- **`bundle_schema_version = None` (field absent) is treated as v1 (NEEDS_MIGRATION), NOT as v0.** Phase 3 bundles have `schema_version: "1"` on their sidecars; treating absent metadata as v0 would require a two-hop migration. The spec.md assumption 5 ("treated as version 0") was written before this research decision — the correct behavior is None → v1 → NEEDS_MIGRATION. This is consistent with the `check_bundle_compatibility(None)` → `MISSING_VERSION` → needs_migration=True contract.
- `bundle_schema_version = 0` or negative → INCOMPATIBLE_OLD (below MIN_READABLE; no migration)
- `bundle_schema_version = 3+` → INCOMPATIBLE_NEW

**Import safety**: `doctrine.versioning` must not import from `charter.*`. The dependency direction is charter → doctrine, never the reverse. Circular import risk is low as long as this is respected.

## Subtask Guidance

### T001 — Create `src/doctrine/versioning.py`: constants, enums, dataclasses

**File**: `src/doctrine/versioning.py` (new file)

Create the module skeleton. All public symbols must be exported.

```python
from __future__ import annotations

import dataclasses
from enum import Enum
from pathlib import Path
from typing import Callable


# --- Constants ---
CURRENT_BUNDLE_SCHEMA_VERSION: int = 2
MIN_READABLE_BUNDLE_SCHEMA: int = 1
MAX_READABLE_BUNDLE_SCHEMA: int = 2

# --- Enums ---
class BundleCompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    NEEDS_MIGRATION = "NEEDS_MIGRATION"
    INCOMPATIBLE_OLD = "INCOMPATIBLE_OLD"
    INCOMPATIBLE_NEW = "INCOMPATIBLE_NEW"
    MISSING_VERSION = "MISSING_VERSION"

# --- Dataclasses ---
@dataclasses.dataclass(frozen=True)
class BundleCompatibilityResult:
    status: BundleCompatibilityStatus
    bundle_version: int | None
    supported_min: int
    supported_max: int
    message: str
    exit_code: int

    @property
    def is_compatible(self) -> bool:
        return self.status == BundleCompatibilityStatus.COMPATIBLE

    @property
    def needs_migration(self) -> bool:
        return self.status in (
            BundleCompatibilityStatus.NEEDS_MIGRATION,
            BundleCompatibilityStatus.MISSING_VERSION,
        )

@dataclasses.dataclass
class MigrationResult:
    changes_made: list[str]
    errors: list[str]
    from_version: int
    to_version: int
```

**Type check**: `mypy --strict src/doctrine/versioning.py` must pass after every subtask.

### T002 — Implement `check_bundle_compatibility()`

**Function signature**: `(bundle_version: int | None) -> BundleCompatibilityResult`

Pure function. No filesystem I/O. Logic:

| Input | Status | exit_code |
|-------|--------|-----------|
| `None` | `MISSING_VERSION` | 1 |
| `bundle_version == CURRENT_BUNDLE_SCHEMA_VERSION` | `COMPATIBLE` | 0 |
| `MIN_READABLE ≤ bundle_version < CURRENT` | `NEEDS_MIGRATION` | 1 |
| `bundle_version < MIN_READABLE` | `INCOMPATIBLE_OLD` | 1 |
| `bundle_version > MAX_READABLE` | `INCOMPATIBLE_NEW` | 1 |

Human-readable `message` must include the remediation action:
- COMPATIBLE: "Bundle schema version {v} is supported."
- NEEDS_MIGRATION: "Bundle schema version {v} requires migration. Run `spec-kitty upgrade`."
- MISSING_VERSION: "Bundle schema version not found; treating as v1. Run `spec-kitty upgrade`."
- INCOMPATIBLE_OLD: "Bundle schema version {v} predates the earliest supported version ({MIN}). Contact support."
- INCOMPATIBLE_NEW: "Bundle schema version {v} is newer than this CLI supports ({MAX}). Upgrade your CLI."

### T003 — Implement `get_bundle_schema_version()`

**Function signature**: `(charter_dir: Path) -> int | None`

Read `bundle_schema_version` integer from `<charter_dir>/metadata.yaml`. Returns `None` if:
- The file does not exist
- The file exists but `bundle_schema_version` key is absent
- The value is `None` (null in YAML)

Never raises; always returns `int | None`. Use `ruamel.yaml` for YAML parsing (existing project pattern — not `pyyaml`):

```python
from ruamel.yaml import YAML

def get_bundle_schema_version(charter_dir: Path) -> int | None:
    metadata_path = charter_dir / "metadata.yaml"
    if not metadata_path.exists():
        return None
    yaml = YAML()
    data = yaml.load(metadata_path)
    if not isinstance(data, dict):
        return None
    value = data.get("bundle_schema_version")
    if not isinstance(value, int):
        return None
    return value
```

### T004 — Stub `migrate_v1_to_v2()` and `run_migration()`

WP03 will complete the full implementation. This WP provides working stubs so WP03 can import and extend them.

```python
# Migration registry: maps from_version → migration_function
_MIGRATIONS: dict[int, Callable[[Path, bool], MigrationResult]] = {}

def _register_migration(
    from_version: int,
    fn: Callable[[Path, bool], MigrationResult],
) -> None:
    _MIGRATIONS[from_version] = fn

def migrate_v1_to_v2(bundle_root: Path, dry_run: bool = False) -> MigrationResult:
    """Stub — WP03 completes the full implementation."""
    raise NotImplementedError("migrate_v1_to_v2 not yet implemented — complete in WP03")

_register_migration(1, migrate_v1_to_v2)

def run_migration(
    from_version: int, bundle_root: Path, dry_run: bool = False
) -> MigrationResult:
    if from_version not in _MIGRATIONS:
        raise KeyError(f"No migration registered for bundle version {from_version}")
    fn = _MIGRATIONS[from_version]
    return fn(bundle_root, dry_run)
```

Note: `_register_migration(1, migrate_v1_to_v2)` must remain present so WP03 can detect the registration without reimporting. WP03 replaces the `migrate_v1_to_v2` function body in place (same file).

### T005 — Add `bundle_schema_version` to `ExtractionMetadata`

**File**: `src/charter/schemas.py`

Locate the `ExtractionMetadata` Pydantic model. Read the full file before editing. Add one optional field:

```python
bundle_schema_version: int | None = None
```

Placement: after the existing fields (do not change field order of pre-existing fields). The field must be optional with `None` default so existing bundles without the field continue to parse without error (AC #6 from plan).

Run `mypy --strict src/charter/schemas.py` after the edit.

### T006 — Stamp `bundle_schema_version` in `extractor.py`

**File**: `src/charter/extractor.py`

Read the file. Find the location where `ExtractionMetadata(...)` is constructed and serialized to `metadata.yaml`. Add `bundle_schema_version=CURRENT_BUNDLE_SCHEMA_VERSION` to the constructor call.

Import: `from doctrine.versioning import CURRENT_BUNDLE_SCHEMA_VERSION` (or the equivalent relative import path used by other charter modules).

Verify that `ruamel.yaml` serializes the new integer field correctly — the metadata.yaml written must contain `bundle_schema_version: 2`.

Run `mypy --strict src/charter/extractor.py` after the edit.

### T007 — Write `tests/doctrine/test_versioning.py`

**File**: `tests/doctrine/test_versioning.py` (new file; also ensure `tests/doctrine/__init__.py` exists)

Cover all branches of `check_bundle_compatibility()`, `get_bundle_schema_version()`, and the `run_migration()` error path. Minimum test cases:

```python
# check_bundle_compatibility
test_compatible_current_version()          # bundle_version=2 → COMPATIBLE, exit_code=0
test_needs_migration_v1()                  # bundle_version=1 → NEEDS_MIGRATION, exit_code=1
test_missing_version()                     # bundle_version=None → MISSING_VERSION, exit_code=1
test_incompatible_new()                    # bundle_version=99 → INCOMPATIBLE_NEW, exit_code=1
test_incompatible_old_zero()               # bundle_version=0 → INCOMPATIBLE_OLD, exit_code=1
test_incompatible_old_negative()           # bundle_version=-1 → INCOMPATIBLE_OLD, exit_code=1
test_is_compatible_property()              # COMPATIBLE → True; others → False
test_needs_migration_property()            # NEEDS_MIGRATION, MISSING_VERSION → True

# get_bundle_schema_version
test_returns_none_when_file_absent(tmp_path)
test_returns_none_when_field_absent(tmp_path)
test_returns_int_when_present(tmp_path)    # write metadata.yaml with bundle_schema_version: 2
test_returns_none_when_field_is_null(tmp_path)  # bundle_schema_version: null

# run_migration
test_run_migration_raises_key_error_for_unregistered_version()
```

Also test message content for the key statuses (ensure "spec-kitty upgrade" appears in NEEDS_MIGRATION and MISSING_VERSION messages).

Use `pytest` and `tmp_path` fixtures. Do not use `unittest.mock` unless absolutely necessary — test real behavior.

**Coverage check**:
```bash
cd src && pytest ../tests/doctrine/test_versioning.py --cov=doctrine.versioning --cov-report=term-missing
```
Must show ≥90% line coverage.

## Definition of Done

- [ ] `src/doctrine/versioning.py` created with all public symbols: constants, `BundleCompatibilityStatus`, `BundleCompatibilityResult`, `MigrationResult`, `check_bundle_compatibility()`, `get_bundle_schema_version()`, `run_migration()`, `migrate_v1_to_v2()` stub
- [ ] `src/charter/schemas.py` — `ExtractionMetadata` has `bundle_schema_version: int | None = None`
- [ ] `src/charter/extractor.py` — stamps `bundle_schema_version=CURRENT_BUNDLE_SCHEMA_VERSION` in metadata.yaml
- [ ] `tests/doctrine/test_versioning.py` passes and achieves ≥90% coverage
- [ ] `mypy --strict src/doctrine/versioning.py src/charter/schemas.py src/charter/extractor.py` — zero errors
- [ ] No changes to any file outside `owned_files`

## Risks

- **ruamel.yaml int serialization**: Confirm that `bundle_schema_version: 2` (Python `int`) round-trips through ruamel.yaml as an integer, not a string. Test this in T007.
- **Import path for `doctrine.versioning` in `charter/extractor.py`**: Check how other `charter/` modules import from `doctrine/` (e.g., `from doctrine.xxx import ...` or `from specify_cli.doctrine.xxx import ...`). Match the existing pattern.
- **`tests/doctrine/__init__.py` missing**: Create it (empty file) if it does not exist, otherwise pytest cannot discover the module.
