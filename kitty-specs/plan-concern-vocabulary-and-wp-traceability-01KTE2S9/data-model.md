# Data Model: Plan Concern Vocabulary and WP Traceability

## Modified Entity: WorkPackageEntry

**Location**: `src/specify_cli/core/wps_manifest.py`

### Current schema

```python
class WorkPackageEntry(BaseModel):
    id: str                              # WPnn pattern
    title: str
    dependencies: list[str]             # WPnn refs
    owned_files: list[str]
    requirement_refs: list[str]
    subtasks: list[str]
    prompt_file: str | None
```

### Extended schema (this mission)

```python
class WorkPackageEntry(BaseModel):
    id: str                              # WPnn pattern — unchanged
    title: str                           # unchanged
    dependencies: list[str]             # WPnn refs — unchanged
    owned_files: list[str]              # unchanged
    requirement_refs: list[str]         # unchanged
    subtasks: list[str]                 # unchanged
    prompt_file: str | None             # unchanged

    # New fields
    plan_concern_refs: list[str]        # IC-## refs — default []
    cross_cutting: bool                 # advisory flag — default False
```

### Validation rules

| Field | Pattern | Error on violation |
|-------|---------|-------------------|
| `plan_concern_refs` items | `^IC-\d{2}$` | `ValueError: plan_concern_ref must match IC-## (e.g. IC-01), got: {v!r}` |
| `cross_cutting` | bool | pydantic type coercion |

### Backwards compatibility invariant

A `wps.yaml` entry with neither `plan_concern_refs` nor `cross_cutting` key present must parse successfully. Both fields default to empty list / `False` when absent from the source YAML.

---

## Modified function: generate_tasks_md_from_manifest()

**Location**: `src/specify_cli/core/wps_manifest.py`

### Extended rendering behaviour

When `entry.plan_concern_refs` is non-empty, append the following line to each WP block in `tasks.md`:

```
**Plan concerns**: IC-01, IC-03
```

When `entry.plan_concern_refs` is empty, render nothing (no label, no blank line).

---

## New vocabulary entity: ImplementationConcern

This is a **template-level concept**, not a Python type. It exists only in `plan.md` as markdown prose within the `## Implementation Concern Map` section.

### Concern fields (in plan-template.md placeholder stubs)

| Field | Description |
|-------|-------------|
| `concern-id` | IC-## identifier (e.g. IC-01) |
| `name` | Short human label |
| `purpose` | One sentence: what this concern addresses |
| `relevant-requirements` | FR-### refs from spec.md |
| `affected-surfaces` | File paths or module names |
| `sequencing/dependencies-on` | Other IC-## IDs this concern depends on, or "none" |
| `risks` | Key risks or coordination notes |

### Cardinality rules

- One concern may be covered by one or many WPs.
- One WP may reference one or many concerns.
- Many-to-many is valid and expected.
- A WP with no concern refs must declare `cross_cutting: true` in `wps.yaml` (warning, not error, from `finalize-tasks`).
