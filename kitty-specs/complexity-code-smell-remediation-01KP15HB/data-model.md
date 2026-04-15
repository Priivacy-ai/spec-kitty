# Data Model: Complexity and Code Smell Remediation

**Phase 1 output** | Mission: `complexity-code-smell-remediation-01KP15HB` | Date: 2026-04-12

This document specifies the interface contracts for the three new constructs introduced by this
mission. Implementing agents must treat these as the normative interface before writing any code.

---

## `TransitionRequest` — status slice (WP01)

**Location**: `src/specify_cli/status/models.py`
**Replaces**: 19-parameter signature of `emit_status_transition`
**FR**: FR-001

### Interface

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class TransitionRequest:
    """All inputs for a single status transition.

    Pass an instance of this as the sole positional argument to
    emit_status_transition(). All fields default to None / False so callers
    only populate what they need.
    """
    # Mission identity
    feature_dir: Path | None = None
    mission_dir: Path | None = None
    mission_slug: str | None = None
    _legacy_mission_slug: str | None = None
    repo_root: Path | None = None

    # Transition
    wp_id: str | None = None
    to_lane: str | None = None
    force: bool = False
    reason: str | None = None

    # Actor
    actor: str | None = None
    execution_mode: str = "worktree"

    # Evidence
    evidence: dict[str, Any] | None = None
    review_ref: str | None = None
    review_result: Any = None

    # Guard hints
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    policy_metadata: dict[str, Any] | None = None
```

### Updated `emit_status_transition` signature

```python
def emit_status_transition(request: TransitionRequest) -> StatusEvent:
    ...
```

### Invariants

- All 27 call-site files are updated in WP01; no deprecated kwargs path is retained.
- `TransitionRequest` is a plain dataclass (not Pydantic) — it holds inputs, not validated state.
  Existing validation logic inside `emit_status_transition` is unchanged.
- mypy must see the full type through all call sites.

---

## `GuardContext` — status slice (WP01)

**Location**: `src/specify_cli/status/transitions.py`
**Replaces**: 10 keyword-only parameters of `validate_transition` / `_run_guard`
**FR**: FR-003

### Interface

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class GuardContext:
    """Guard condition inputs for a lane transition.

    Passed from validate_transition into _run_guard. Fields map 1:1 to
    the current keyword parameters of validate_transition.
    """
    force: bool = False
    actor: str | None = None
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    reason: str | None = None
    review_ref: str | None = None
    evidence: Any = None
    review_result: Any = None
    current_actor: str | None = None
```

### Updated signatures

```python
def validate_transition(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext,
) -> tuple[bool, str | None]:
    ...

def _run_guard(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext,
) -> tuple[bool, str | None]:
    ...
```

### Invariants

- `from_lane` and `to_lane` remain positional (they are routing keys, not guard state).
- `validate_transition` constructs `GuardContext` from its arguments; callers that pass
  individual kwargs migrate to constructing `GuardContext` explicitly.
- All 10 `validate_transition` call-site files updated in WP01.

---

## `BaseDoctrineRepository[T]` — doctrine slice (WP04)

**Location**: `src/doctrine/base.py` (new file)
**Replaces**: 7 duplicate `_load()` implementations across doctrine sub-repositories
**FR**: FR-011

### Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar
import warnings
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

### Per-repository migration

| Repository class | Key attribute | Needs `_key` override? |
|-----------------|--------------|----------------------|
| `DirectivesRepository` | `.code` | Yes |
| `TacticsRepository` | `.id` | No (default) |
| `ParadigmsRepository` | `.id` | No (default) |
| `StyleguidesRepository` | `.id` | No (default) |
| `MissionStepContractsRepository` | `.id` | No (default) |
| `ToolguidesRepository` | `.id` | No (default) |
| `ProceduresRepository` | `.id` | No (default) |

### Migration pattern (strangler-fig)

```python
# Before
class TacticsRepository:
    def _load(self) -> dict[str, Tactic]:
        result = {}
        for yaml_file in self._tactics_dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(yaml_file.read_text())
                tactic = Tactic.model_validate(raw)
                result[tactic.id] = tactic
            except Exception as e:
                warnings.warn(f"...", stacklevel=2)
        return result

# After
class TacticsRepository(BaseDoctrineRepository[Tactic]):
    @property
    def _schema(self) -> type[Tactic]:
        return Tactic

    @property
    def _dir(self) -> Path:
        return self._tactics_dir
```

Migrate one repository at a time. Run tests after each migration.

### Invariants

- `BaseDoctrineRepository` lives in `src/doctrine/base.py`; all 7 sub-repositories import from it.
- The existing `_load()` in each repository is deleted only after its migration tests pass.
- CC for each migrated `_load()` method: effectively 0 (the concrete implementation is in the base).
  Ruff CC check applies to the base class `_load()` which must measure ≤ 4.

---

## State transitions (unchanged)

No new state machine constructs. The existing 9-lane status model is unmodified.
`TransitionRequest` and `GuardContext` are input consolidation constructs only.
