# Research: Complexity and Code Smell Remediation

**Phase 0 output** | Mission: `complexity-code-smell-remediation-01KP15HB` | Date: 2026-04-12

---

## R-01: DRG Rebuild EPIC Status

**Question**: Is there an active DRG rebuild mission that would gate FR-007?

**Method**: Inspected `kitty-specs/` for any mission with "drg", "dependency-resolution", or "charter-rebuild" in its slug.

**Finding**: No active DRG rebuild mission exists as of 2026-04-12.

**Decision**: FR-007 (`resolve_governance` decomposition) is **unblocked**.

**Rationale**: C-001 is a gate, not a deferral. With no active DRG mission, the gate condition
is false and FR-007 proceeds as a normal work item within WP03.

**Action for implementer**: Re-check at WP03 claim time. If a DRG mission appears in `planned`
or `in_progress` state, exclude FR-007 from WP03 scope and deliver WP03 with FR-006, FR-008,
FR-009, FR-010 only.

---

## R-02: `emit_status_transition` Call-Site Map

**Question**: How many call sites must be updated for FR-001? What do the parameter clusters look like?

**Method**: `grep -r "emit_status_transition" src/ tests/ -l` → 27 files.

### Current signature (19 parameters)

```python
def emit_status_transition(
    feature_dir: Path | None = None,          # positional 1: mission dir (legacy name)
    _legacy_mission_slug: str | None = None,  # positional 2: deprecated slug path
    wp_id: str | None = None,                 # positional 3
    to_lane: str | None = None,               # positional 4
    actor: str | None = None,                 # positional 5
    *,
    mission_dir: Path | None = None,          # kw: preferred dir argument (replaces feature_dir)
    mission_slug: str | None = None,          # kw: explicit slug
    force: bool = False,                      # kw: override terminal lane guard
    reason: str | None = None,                # kw: human-readable justification
    evidence: dict[str, Any] | None = None,  # kw: structured evidence for approved/done
    review_ref: str | None = None,            # kw: review artifact reference
    workspace_context: str | None = None,     # kw: guard hint (claimed)
    subtasks_complete: bool | None = None,    # kw: guard hint (in_progress → for_review)
    implementation_evidence_present: bool | None = None,  # kw: guard hint
    execution_mode: str = "worktree",         # kw: actor context
    repo_root: Path | None = None,            # kw: root resolution fallback
    policy_metadata: dict[str, Any] | None = None,  # kw: SaaS telemetry
    review_result: Any = None,               # kw: guard hint (approved)
) -> StatusEvent:
```

### Proposed `TransitionRequest` grouping

| Field group | Fields |
|-------------|--------|
| Mission identity | `feature_dir`, `mission_dir`, `mission_slug`, `_legacy_mission_slug`, `repo_root` |
| Transition | `wp_id`, `to_lane`, `force`, `reason` |
| Actor | `actor`, `execution_mode` |
| Evidence | `evidence`, `review_ref`, `review_result` |
| Guard hints | `workspace_context`, `subtasks_complete`, `implementation_evidence_present`, `policy_metadata` |

### Migration approach

`emit_status_transition(request: TransitionRequest) -> StatusEvent` becomes the canonical
signature. Call sites that pass keyword arguments individually get migrated to construct
a `TransitionRequest` explicitly. No wrapper shim is needed — all 27 files are Python source
files in this repo, so full migration within one WP is feasible.

**Alternatives considered**: Keeping backward-compatible kwargs via `**kwargs` — rejected because
it defeats the goal of a clean typed boundary and makes mypy less useful.

---

## R-03: `validate_transition` / `_run_guard` Call-Site Map

**Question**: How many call sites for FR-003? Does GuardContext overlap with TransitionRequest?

**Method**: `grep -r "validate_transition" src/ tests/ -l` → 10 files; `_run_guard` → 3 files (internal).

### Current `validate_transition` signature (12 parameters)

```python
def validate_transition(
    from_lane: str,
    to_lane: str,
    *,
    force: bool = False,
    actor: str | None = None,
    workspace_context: str | None = None,
    subtasks_complete: bool | None = None,
    implementation_evidence_present: bool | None = None,
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: Any = None,
    review_result: Any = None,
    current_actor: str | None = None,
) -> tuple[bool, str | None]:
```

### Proposed `GuardContext` grouping

All keyword parameters of `validate_transition` become fields of `GuardContext`. The `from_lane`
and `to_lane` positional parameters remain as direct arguments to both `validate_transition` and
`_run_guard` (they are routing keys, not guard state).

**Relationship to TransitionRequest**: `GuardContext` is a strict subset of `TransitionRequest`.
The implementer may choose to construct `GuardContext` from a `TransitionRequest` within
`emit_status_transition`, or keep them independent. Either is acceptable — the spec only
requires the public boundaries to be ≤ 5 parameters each.

---

## R-04: Doctrine `_load()` Duplication Pattern

**Question**: Are all 7 `_load()` methods structurally identical? What generic interface suffices?

**Method**: Read each sub-repository class in `src/doctrine/`.

### Confirmed duplication

All 7 repositories implement `_load()` with this pattern:

```python
def _load(self) -> dict[str, ModelType]:
    result = {}
    for yaml_file in self._dir.glob("*.yaml"):
        try:
            raw = yaml.safe_load(yaml_file.read_text())
            obj = ModelType.model_validate(raw)
            result[obj.id] = obj          # key varies: .id, .slug, .code, etc.
        except (ValidationError, KeyError) as e:
            warnings.warn(f"Failed to load {yaml_file}: {e}", stacklevel=2)
    return result
```

**Variation point**: The key used to index the dict (`obj.id`, `obj.slug`, etc.) differs.
This can be resolved by requiring that all models implement a `canonical_key` property, or by
passing a key extractor as a constructor argument, or by abstracting to `_key(obj: T) -> str`.

**Decision**: Abstract `_key(obj: T) -> str` as a second abstract method alongside `_schema` and
`_dir`. Default implementation returns `obj.id` (covers 5 of 7 repositories). The remaining 2
override `_key`.

### Generic base interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class BaseDoctrineRepository(ABC, Generic[T]):
    @property
    @abstractmethod
    def _schema(self) -> type[T]: ...

    @property
    @abstractmethod
    def _dir(self) -> Path: ...

    def _key(self, obj: T) -> str:
        return obj.id  # default; override in repositories that use .slug, .code, etc.

    def _load(self) -> dict[str, T]:
        result = {}
        for yaml_file in self._dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(yaml_file.read_text())
                obj = self._schema.model_validate(raw)
                result[self._key(obj)] = obj
            except Exception as e:
                warnings.warn(f"Failed to load {yaml_file}: {e}", stacklevel=2)
        return result
```

**Alternatives considered**: Mixin class instead of Generic ABC — rejected; mixins lack the
`TypeVar` bound that makes mypy understand the return type of `_load()`. Protocol — rejected;
Protocol cannot carry a default implementation of `_load()`.

---

## Summary: Unresolved items

None. All research questions are answered. WP01–WP04 may proceed to implementation.
