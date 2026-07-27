---
work_package_id: WP02
title: Registry Loader and Doctor Engine
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-002
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
- T005
agent: "claude"
shell_pid: "1344277"
history:
- date: '2026-04-19'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/compat/
execution_mode: code_change
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- src/specify_cli/compat/**
tags: []
---

# WP02 — Registry Loader and Doctor Engine

## Objective

Implement the two core Python modules that power the shim-registry check: `registry.py` loads and validates the YAML registry with accumulating error reporting, and `doctor.py` classifies each entry into its runtime state and returns a structured report that the CLI (WP03) and tests (WP05/WP06) consume.

## Context

Full design details are in `data-model.md`. Key decisions from `research.md`:

- **R1**: Use `packaging.version.Version` for semver comparisons (handles pre-release suffixes).
- **R2**: Use `stdlib tomllib` to read `[project].version` from `pyproject.toml`.
- **R3**: Manual ruamel.yaml validation — no jsonschema/cerberus dep.
- **R6**: File-existence probe checks `src/specify_cli/<name>.py` then `src/specify_cli/<name>/__init__.py`.

The registry file lives at `architecture/2.x/shim-registry.yaml` (written by WP04). At mission start the registry is empty (`shims: []`). Both modules must handle the empty case without errors.

## Branch Strategy

- **Working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main`
- Run: `spec-kitty agent action implement WP02 --agent <name>`

---

## Subtask T004 — Implement `src/specify_cli/compat/registry.py`

**Purpose**: Load `architecture/2.x/shim-registry.yaml` and validate every entry against the schema contract. Accumulate all errors before raising — no short-circuit.

**Data types** (frozen dataclasses, fully type-annotated):

```python
from __future__ import annotations
import dataclasses
from pathlib import Path
from typing import Union

@dataclasses.dataclass(frozen=True)
class ShimEntry:
    legacy_path: str
    canonical_import: Union[str, list[str]]
    introduced_in_release: str
    removal_target_release: str
    tracker_issue: str
    grandfathered: bool
    extension_rationale: str | None = None
    notes: str | None = None

class RegistrySchemaError(Exception):
    """Raised when the registry YAML fails schema validation."""
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))
```

**`load_registry(repo_root: Path) -> list[ShimEntry]`**:
1. Resolve registry path: `repo_root / "architecture" / "2.x" / "shim-registry.yaml"`.
2. If file does not exist: raise `FileNotFoundError` (caller maps to exit code 2).
3. Parse with `ruamel.yaml` safe loader: `from ruamel.yaml import YAML; yaml = YAML(typ="safe"); data = yaml.load(fp)`.
4. Call `validate_registry(data)` — raises `RegistrySchemaError` on invalid input.
5. Return `[ShimEntry(**entry) for entry in data["shims"]]`.

**`validate_registry(data: object) -> None`**:
Collect all errors in a list; raise `RegistrySchemaError(errors)` at the end if non-empty.

Checks (per `data-model.md` validation rules):
1. Top-level type is `dict` with key `shims` mapping to a `list`.
2. For each entry (index `i`):
   - Required keys present: `legacy_path`, `canonical_import`, `introduced_in_release`, `removal_target_release`, `tracker_issue`, `grandfathered`.
   - `legacy_path`: string matching `^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$`.
   - `canonical_import`: string matching above pattern, OR non-empty list of such strings.
   - `introduced_in_release`, `removal_target_release`: strings matching `^\d+\.\d+\.\d+(?:[a-z]\d+)?$`.
   - `removal_target_release >= introduced_in_release` (semver-aware: `packaging.version.Version`).
   - `tracker_issue`: string matching `^(#\d+|https?://.+)$`.
   - `grandfathered`: `bool` (not a string `"true"`).
   - `extension_rationale`: if present, non-empty string.
   - `notes`: if present, string.
3. `legacy_path` values are unique across entries.

Error message format: `"entry[{i}].{field}: {description}"`.

**Files**:
- `src/specify_cli/compat/registry.py` (new, ~110 lines)

**Validation**:
- [ ] `load_registry(repo_root)` returns `[]` for an empty `shims: []` registry
- [ ] `validate_registry` raises `RegistrySchemaError` with field name in message for each invalid case
- [ ] All type annotations pass `mypy --strict`

---

## Subtask T005 — Implement `src/specify_cli/compat/doctor.py`

**Purpose**: Classify each `ShimEntry` into one of four states (pending/overdue/grandfathered/removed) by comparing the project version and probing for the shim file on disk. Return a structured `ShimRegistryReport`.

**Data types**:

```python
import enum

class ShimStatus(enum.Enum):
    PENDING = "pending"
    OVERDUE = "overdue"
    GRANDFATHERED = "grandfathered"
    REMOVED = "removed"

@dataclasses.dataclass(frozen=True)
class ShimStatusEntry:
    entry: ShimEntry
    status: ShimStatus
    shim_exists: bool

@dataclasses.dataclass(frozen=True)
class ShimRegistryReport:
    entries: list[ShimStatusEntry]
    project_version: str
    registry_path: Path

    @property
    def has_overdue(self) -> bool:
        return any(e.status == ShimStatus.OVERDUE for e in self.entries)

    @property
    def recommended_exit_code(self) -> int:
        if self.has_overdue:
            return 1
        return 0
```

**`check_shim_registry(repo_root: Path) -> ShimRegistryReport`**:

1. **Read project version** (R2):
   ```python
   import tomllib
   pyproject = repo_root / "pyproject.toml"
   if not pyproject.exists():
       raise FileNotFoundError(f"pyproject.toml not found at {pyproject}")
   with pyproject.open("rb") as fp:
       data = tomllib.load(fp)
   project_version = data["project"]["version"]
   ```
   If `data["project"]["version"]` is absent: raise `KeyError` (caller maps to exit 2).

2. **Load registry** via `load_registry(repo_root)` — let `FileNotFoundError` / `RegistrySchemaError` propagate (caller maps to exit 2).

3. **Classify each entry** (R6 file probe + R1 semver):
   ```python
   from packaging.version import Version

   def _shim_exists(repo_root: Path, legacy_path: str) -> bool:
       # e.g. "specify_cli.charter" -> src/specify_cli/charter
       parts = legacy_path.split(".")
       base = repo_root / "src" / Path(*parts)
       return (base.with_suffix(".py")).exists() or (base / "__init__.py").exists()

   def _classify(entry: ShimEntry, current: Version, repo_root: Path) -> ShimStatus:
       if entry.grandfathered:
           return ShimStatus.GRANDFATHERED
       exists = _shim_exists(repo_root, entry.legacy_path)
       if not exists:
           return ShimStatus.REMOVED
       if current >= Version(entry.removal_target_release):
           return ShimStatus.OVERDUE
       return ShimStatus.PENDING
   ```

4. Build and return `ShimRegistryReport`.

**Update `compat/__init__.py`** to activate the real exports:
```python
from specify_cli.compat.registry import RegistrySchemaError
from specify_cli.compat.doctor import ShimRegistryReport, ShimStatus, ShimStatusEntry, check_shim_registry
__all__ = ["check_shim_registry", "ShimRegistryReport", "ShimStatus", "ShimStatusEntry", "RegistrySchemaError"]
```

**Files**:
- `src/specify_cli/compat/doctor.py` (new, ~90 lines)
- `src/specify_cli/compat/__init__.py` (update exports)

**Validation**:
- [ ] Empty registry → `ShimRegistryReport(entries=[], ...)`, `has_overdue=False`, exit code 0
- [ ] Entry with `removal_target_release` > current version and file present → `PENDING`
- [ ] Entry with `removal_target_release` ≤ current version and file present → `OVERDUE`
- [ ] Entry with `grandfathered=True` → `GRANDFATHERED` regardless of version/file
- [ ] Entry with file absent → `REMOVED`
- [ ] Missing `pyproject.toml` → `FileNotFoundError` propagates
- [ ] mypy --strict passes on both files

---

## Definition of Done

- [ ] `src/specify_cli/compat/registry.py` implemented with `ShimEntry`, `RegistrySchemaError`, `load_registry`, `validate_registry`
- [ ] `src/specify_cli/compat/doctor.py` implemented with `ShimStatus`, `ShimStatusEntry`, `ShimRegistryReport`, `check_shim_registry`
- [ ] `compat/__init__.py` exports all public symbols
- [ ] All four status classifications work correctly against synthetic test data
- [ ] `mypy --strict src/specify_cli/compat/` passes
- [ ] `pytest tests/` exits 0 (no regressions)

## Risks

- Pre-release version string in `pyproject.toml` (currently `3.2.0`): `Version("3.3.0") >= Version("3.2.0")` is True, `Version("3.3.0a1") >= Version("3.3.0")` is False — verify these semantics in a quick REPL check.
- `ruamel.yaml` safe loader may return Python `bool` for YAML `true`/`false` — that's correct. YAML `"true"` (string) returns a string, which the validator must reject. Test both cases.

## Activity Log

- 2026-04-19T13:17:31Z – claude – shell_pid=1339370 – Started implementation via action command
- 2026-04-19T13:19:00Z – claude – shell_pid=1339370 – compat package implemented: registry.py, doctor.py, __init__.py — mypy strict passes, smoke tests pass
- 2026-04-19T13:25:02Z – claude – shell_pid=1344277 – Started review via action command
- 2026-04-19T13:25:44Z – claude – shell_pid=1344277 – Review passed: registry.py and doctor.py correct, well-structured, mypy strict + ruff clean. All 4 status classifications correct.
