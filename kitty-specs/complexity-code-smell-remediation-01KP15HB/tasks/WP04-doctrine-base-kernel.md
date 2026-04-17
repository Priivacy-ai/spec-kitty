---
work_package_id: WP04
title: 'Doctrine: Repository Base Class and Kernel Import Fixes'
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
planning_base_branch: feat/complexity-debt-remediation
merge_target_branch: feat/complexity-debt-remediation
branch_strategy: Planning artifacts for this feature were generated on feat/complexity-debt-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/complexity-debt-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-complexity-code-smell-remediation-01KP15HB
base_commit: cf17d751d273f8896e901ced4811b034d9b4d7e9
created_at: '2026-04-14T08:27:14.665300+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
shell_pid: "137613"
agent: "claude"
history:
- date: '2026-04-12'
  action: created
  author: spec-kitty.tasks
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files:
- src/doctrine/base.py
- src/doctrine/__init__.py
- src/doctrine/styleguides/repository.py
- src/doctrine/toolguides/repository.py
- src/doctrine/tactics/repository.py
- src/doctrine/directives/repository.py
- src/doctrine/mission_step_contracts/repository.py
- src/doctrine/procedures/repository.py
- src/doctrine/paradigms/repository.py
- src/doctrine/curation/workflow.py
- src/doctrine/agent_profiles/repository.py
- src/kernel/atomic.py
- src/kernel/_safe_re.py
- src/kernel/glossary_runner.py
- tests/cross_cutting/test_doctrine_curation_unit.py
- tests/doctrine/test_shipped_doctrine_cycle_free.py
- tests/unit/test_doctrine_curation.py
- tests/kernel/
tags: []
---

# WP04 — Doctrine: Repository Base Class and Kernel Import Fixes

## Objective

Eliminate 7-way duplication of `_load()` implementations in doctrine sub-repositories by
introducing `BaseDoctrineRepository[T]`. Rename `CurationAborted` to `CurationAbortedError`.
Replace magic workload constants. Fix import-organization violations in the kernel.

**FRs**: FR-011, FR-012, FR-013, FR-014
**Governing tactics**: `refactoring-extract-class-by-responsibility-split`, `refactoring-extract-first-order-concept`, `refactoring-strangler-fig`, `refactoring-replace-magic-number-with-symbolic-constant`, `change-apply-smallest-viable-diff`
**Procedure**: `src/doctrine/procedures/shipped/refactoring.procedure.yaml`
**Directives**: DIRECTIVE_034, DIRECTIVE_001, DIRECTIVE_024, DIRECTIVE_030

## Branch Strategy

- **Lane**: C (independent)
- **Planning base / merge target**: `feat/complexity-debt-remediation`
- **Worktree**: Allocated by `finalize-tasks` — check `lanes.json` for the exact path.
- **Implementation command**: `spec-kitty agent action implement WP04 --agent <name>`

## Context

Seven doctrine sub-repositories each implement a `_load()` method with the same 3-step pattern:
walk a YAML directory, parse each file with Pydantic `model_validate`, warn on failures.
The only variation is the key attribute used to index the dict (`.id` in most cases; one or two
use `.code` or `.slug`).

`BaseDoctrineRepository[T]` (defined in `data-model.md`) captures this pattern once with a
generic `TypeVar` bound to `BaseModel`. Each sub-repository then declares `_schema` and `_dir`
as abstract properties, and optionally overrides `_key()` if it doesn't use `.id`.

**Repositories NOT in scope for FR-011** (their `_load()` differs materially):
- `src/doctrine/agent_profiles/repository.py` — complex multi-step load with CC=13; out of scope
- `src/doctrine/templates/repository.py` — if present, verify its `_load()` pattern before deciding
- `src/doctrine/missions/repository.py` — if present, verify its `_load()` pattern before deciding

---

## Pre-work: Verify key attributes

Before writing the base class, run:
```bash
grep -n "result\[" src/doctrine/*/repository.py | grep -v "agent_profiles"
```

This shows how each repository keys its dict. Identify which ones do NOT use `.id` and plan
their `_key()` override accordingly. Document findings in your WP notes.

---

## Subtask T020 — Create `BaseDoctrineRepository[T]`

**Purpose**: Define the generic abstract base class per the interface in `data-model.md`.

**File**: `src/doctrine/base.py` (new file — does not exist yet)

**Implementation** (full interface in `kitty-specs/complexity-code-smell-remediation-01KP15HB/data-model.md`):

```python
from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class BaseDoctrineRepository(ABC, Generic[T]):
    """Abstract base for all doctrine asset repositories.

    Subclasses declare _schema and _dir as abstract properties.
    The concrete _load() implementation handles YAML walking, parsing,
    warning emission, and keying.
    """

    @property
    @abstractmethod
    def _schema(self) -> type[T]:
        """Pydantic model class for this repository's asset type."""
        ...

    @property
    @abstractmethod
    def _dir(self) -> Path:
        """Directory containing the YAML asset files."""
        ...

    def _key(self, obj: T) -> str:
        """Extract the dict key for a loaded asset. Default: obj.id."""
        return obj.id  # type: ignore[attr-defined]

    def _load(self) -> dict[str, T]:
        """Walk _dir, parse each YAML file with _schema, warn on failure."""
        result: dict[str, T] = {}
        for yaml_file in sorted(self._dir.glob("*.yaml")):
            try:
                raw: Any = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                obj = self._schema.model_validate(raw)
                result[self._key(obj)] = obj
            except (ValidationError, KeyError, AttributeError) as exc:
                warnings.warn(
                    f"Failed to load doctrine asset {yaml_file.name}: {exc}",
                    stacklevel=2,
                )
        return result
```

Also add `BaseDoctrineRepository` to `src/doctrine/__init__.py` exports.

**Validation**:
- `from doctrine.base import BaseDoctrineRepository` — no import error
- `mypy src/doctrine/base.py` — zero errors

---

## Subtask T021 — Migrate 7 repositories to `BaseDoctrineRepository[T]` (strangler-fig)

**Purpose**: Replace 7 `_load()` implementations with inheritance from `BaseDoctrineRepository[T]`.

**Files**: `src/doctrine/{paradigms,procedures,toolguides,styleguides,mission_step_contracts,tactics,directives}/repository.py`

**Recommended migration order** (simplest first to validate pattern):
1. `paradigms/repository.py`
2. `procedures/repository.py`
3. `toolguides/repository.py`
4. `styleguides/repository.py`
5. `mission_step_contracts/repository.py`
6. `tactics/repository.py`
7. `directives/repository.py`

**Per-repository migration pattern**:

```python
# Before
class TacticsRepository:
    def __init__(self, shipped_root: Path, project_root: Path | None = None):
        self._tactics_dir = shipped_root / "tactics" / "shipped"
        self._items: dict[str, Tactic] | None = None

    def _load(self) -> None:
        result = {}
        for yaml_file in self._tactics_dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(yaml_file.read_text())
                tactic = Tactic.model_validate(raw)
                result[tactic.id] = tactic
            except Exception as e:
                warnings.warn(f"...", stacklevel=2)
        self._items = result

# After
class TacticsRepository(BaseDoctrineRepository[Tactic]):
    def __init__(self, shipped_root: Path, project_root: Path | None = None):
        self._tactics_dir = shipped_root / "tactics" / "shipped"
        self._items: dict[str, Tactic] | None = None

    @property
    def _schema(self) -> type[Tactic]:
        return Tactic

    @property
    def _dir(self) -> Path:
        return self._tactics_dir
    # _load() is inherited — delete the old implementation
```

**For repositories using a key other than `.id`**:
```python
def _key(self, obj: Directive) -> str:
    return obj.code  # override for directives repository
```

**After each migration**:
```bash
pytest tests/doctrine/ -x        # must pass
pytest tests/ -k "doctrine" -x   # broader check
```

**Important**: Only delete the old `_load()` after the tests pass. Do not touch
`agent_profiles/repository.py` — it is explicitly out of scope.

---

## Subtask T022 — Rename `CurationAborted` → `CurationAbortedError`

**Purpose**: Apply `Error` suffix convention to the curation exception (FR-012).

**Files** (only 2):
```bash
grep -rn "CurationAborted" src/ tests/ --include="*.py"
```

Expected: `src/doctrine/curation/workflow.py` (definition) + 1-2 import sites.

**Steps**:
1. Rename the class in `src/doctrine/curation/workflow.py`
2. Update `__all__` if present
3. Update all import sites atomically (C-004: all in one commit)
4. Verify: `grep -r "CurationAborted[^E]" src/ tests/ --include="*.py"` → zero matches

**Validation**: `pytest tests/ -x -k "curation"` — passes.

---

## Subtask T023 — Named workload constants in `agent_profiles/repository.py`

**Purpose**: Replace magic literals 2 and 4 with named constants (FR-013).

**File**: `src/doctrine/agent_profiles/repository.py`

**Finding** (from analysis): Lines near the `_load()` method use `2` and `4` as workload
thresholds for profile categorization.

**Change**:
```python
# Add at module scope (after imports, before class definition)
_MAX_LOW_WORKLOAD = 2
_MAX_MEDIUM_WORKLOAD = 4
```

Replace every occurrence of the bare `2` and `4` used as workload thresholds with the named
constants. Verify no other numeric literals `2` or `4` are accidentally replaced (check context).

**Validation**: `ruff check src/doctrine/agent_profiles/repository.py --select PLR2004` — zero violations.

---

## Subtask T024 — Fix kernel import-organization violations

**Purpose**: Resolve TC003, PTH105, PTH108, I001 in the kernel slice (FR-014).

**Violations** (confirmed by ruff analysis):

| File | Code | Line | Issue |
|------|------|------|-------|
| `src/kernel/atomic.py` | TC003 | 12 | stdlib import not in `TYPE_CHECKING` block |
| `src/kernel/atomic.py` | PTH105 | 41 | `os.path.basename()` → use `Path(...).name` |
| `src/kernel/atomic.py` | PTH108 | 46 | `os.rename()` → use `Path(...).rename()` |
| `src/kernel/glossary_runner.py` | TC003 | 43 | stdlib import not in `TYPE_CHECKING` block |
| `src/kernel/_safe_re.py` | I001 | 48 | unsorted imports |
| `src/kernel/_safe_re.py` | TC003 | 41 | stdlib import not in `TYPE_CHECKING` block |

**Auto-fixable** (TC003 and I001 — run first):
```bash
ruff check --fix src/kernel/atomic.py src/kernel/glossary_runner.py src/kernel/_safe_re.py
```

Review the auto-fixes before committing — ruff moves TYPE_CHECKING imports into an
`if TYPE_CHECKING:` block. Ensure the moved imports do not break runtime usage.

**Manual fixes** (PTH — must edit by hand):

`src/kernel/atomic.py` line 41 — PTH105:
```python
# Before
import os
name = os.path.basename(some_path)

# After (ensure Path is imported)
from pathlib import Path
name = Path(some_path).name
```

`src/kernel/atomic.py` line 46 — PTH108:
```python
# Before
os.rename(src, dst)

# After
Path(src).rename(dst)
```

If `os` is only used for these two PTH violations, remove the `os` import after fixing both.

**Validation**:
```bash
ruff check src/kernel/
mypy src/kernel/
pytest tests/kernel/ -x
```

---

## Subtask T025 — Quality gate

```bash
ruff check src/doctrine/ src/kernel/
mypy src/doctrine/ src/kernel/
pytest tests/ -x --timeout=120
```

**Expected outcomes**:
- ruff: zero violations in `src/doctrine/` and `src/kernel/`
- mypy: zero errors
- pytest: no new failures
- All 7 doctrine repositories have CC ≤ 4 for their `_load()` (base class `_load()` CC ≤ 4)
- `CurationAbortedError` is the only name; `CurationAborted` (without Error) is gone
- `_MAX_LOW_WORKLOAD` and `_MAX_MEDIUM_WORKLOAD` constants present in `agent_profiles/repository.py`

---

## Definition of Done

- [ ] `src/doctrine/base.py` exists with `BaseDoctrineRepository[T]` generic ABC
- [ ] All 7 target repositories inherit from `BaseDoctrineRepository[T]` and have no `_load()` override
- [ ] Each migrated `_load()` (in base class) measures CC ≤ 4
- [ ] `CurationAbortedError` is the only name; `grep -r "CurationAborted[^E]"` returns nothing
- [ ] `_MAX_LOW_WORKLOAD = 2` and `_MAX_MEDIUM_WORKLOAD = 4` defined in `agent_profiles/repository.py`
- [ ] TC003, PTH105, PTH108, I001 violations in kernel are resolved
- [ ] `ruff check src/doctrine/ src/kernel/` — zero violations
- [ ] `mypy src/doctrine/ src/kernel/` — zero errors
- [ ] `pytest tests/` — no new failures
- [ ] `agent_profiles/repository.py` untouched except for T023 (named constants only)
- [ ] `templates/repository.py` and `missions/repository.py` untouched (not in scope)

## Reviewer Guidance

1. Verify that exactly 7 repositories are migrated (not 8 — `agent_profiles/repository.py` is excluded from FR-011).
2. Run `grep -rn "def _load" src/doctrine/ --include="*.py"` — should appear only in `base.py` and `agent_profiles/repository.py`.
3. Confirm `_key()` override is present for repositories that don't use `.id` as their key.
4. Confirm `grep -r "CurationAborted[^E]" src/ tests/ --include="*.py"` returns zero results.
5. Run `ruff check src/kernel/ --select TC003,PTH,I001` — zero violations.

## Activity Log

- 2026-04-14T08:27:14Z – claude – shell_pid=137613 – Assigned agent via action command
