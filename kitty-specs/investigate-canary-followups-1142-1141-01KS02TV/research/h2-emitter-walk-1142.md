# #1142 H2 emitter walk — static audit

**Predicate under test** (`src/specify_cli/audit/shape_registry.py:169–198`, function `is_mission_lifecycle_row`):

```python
def is_mission_lifecycle_row(row: Mapping[str, Any]) -> bool:
    if not isinstance(row, Mapping):
        return False
    if row.get("aggregate_type") != "Mission":
        return False
    event_type = row.get("event_type")
    return isinstance(event_type, str) and bool(event_type)
```

**FORBIDDEN_KEYS** (`src/specify_cli/audit/detectors.py:64–69`):

```python
FORBIDDEN_KEYS: frozenset[str] = frozenset({"event_type", "event_name"})
```

`detect_forbidden_keys` (lines 113–148) skips rows for which `is_mission_lifecycle_row()` returns True, otherwise flags every key in the row that appears in `FORBIDDEN_KEYS`. Since every lifecycle envelope structurally carries `event_type` as a top-level key, any envelope whose `aggregate_type` ≠ `"Mission"` is automatically flagged.

## Emitter inventory (named in spec.md and research.md R3)

| File | Line | `aggregate_type` literal | Passes predicate? | Notes |
|---|---|---|---|---|
| `src/specify_cli/status/lifecycle_events.py` | 234 | (dynamic — read from envelope param) | depends | Internal SaaS fan-out path; trusts caller |
| `src/specify_cli/status/lifecycle_events.py` | 365 | (passed through) | depends | `append_lifecycle_event` helper |
| `src/specify_cli/status/lifecycle_events.py` | **410** | `"Project"` | **NO** | `emit_project_initialized` — writes `ProjectInitialized` to project log |
| `src/specify_cli/status/lifecycle_events.py` | 459 | `"Mission"` | YES | `emit_mission_created_local` |
| `src/specify_cli/status/lifecycle_events.py` | 521 | `"Mission"` | YES | (other Mission lifecycle helper) |
| `src/specify_cli/status/lifecycle_events.py` | **562** | `"WorkPackage"` | **NO** | WP-lifecycle event emitter |
| `src/specify_cli/invocation/propagator.py` | — | (no `aggregate_type` literal) | n/a | Does not emit lifecycle envelopes directly |
| `src/specify_cli/next/_internal_runtime/engine.py` | — | (no `aggregate_type` literal) | n/a | Does not emit lifecycle envelopes directly |
| `src/specify_cli/retrospective/events.py` | — | (no `aggregate_type` literal) | n/a | Does not emit lifecycle envelopes directly |
| `src/specify_cli/dossier/events.py` | **414** | `"MissionDossier"` | **NO** | Dossier event emitter |
| `src/specify_cli/dossier/events.py` | **490** | `"MissionDossier"` | **NO** | Dossier event emitter |
| `src/specify_cli/dossier/events.py` | **555** | `"MissionDossier"` | **NO** | Dossier event emitter |
| `src/specify_cli/dossier/events.py` | **628** | `"MissionDossier"` | **NO** | Dossier event emitter |
| `src/specify_cli/dossier/emitter_adapter.py` | 78 | (passed through) | depends | Adapter — trusts caller |

**Verdict**: 3 distinct `aggregate_type` literals in lifecycle envelopes besides `"Mission"`:
- `"Project"` (1 emit site)
- `"WorkPackage"` (1 emit site)
- `"MissionDossier"` (4 emit sites)

All seven non-`Mission` emit sites produce envelopes that:
1. Carry `event_type` as a top-level structural key (built by `_build_envelope` at line 156–169)
2. Fail `is_mission_lifecycle_row()` because `aggregate_type` ≠ `"Mission"`
3. Are therefore flagged by `detect_forbidden_keys` as `FORBIDDEN_KEY`

## Concrete row caught by `detect_forbidden_keys`

A `ProjectInitialized` row emitted by `spec-kitty init` (sample captured by local repro in `outcome-1142.md`):

```json
{
  "aggregate_id": "23860ff5-ad42-484d-bde7-8c327edf9cba",
  "aggregate_type": "Project",
  "event_id": "01KS05J4W9RCFD9J9D03K4DG71",
  "event_type": "ProjectInitialized",
  "payload": { "actor": "spec-kitty init", "initialized_at": "...", "project_slug": "test-project", ... },
  "project_slug": "test-project",
  "project_uuid": "23860ff5-ad42-484d-bde7-8c327edf9cba",
  "schema_version": "5.0.0",
  "timestamp": "..."
}
```

- `aggregate_type == "Project"` → predicate returns False → audit does NOT skip
- top-level `event_type` key present → matches `FORBIDDEN_KEYS` → finding emitted with `code="FORBIDDEN_KEY"`

The same construction holds for every `WorkPackage` and `MissionDossier` envelope.

## Conclusion

**H2 CONFIRMED.** The WP01 predicate is structurally too narrow. It restricts the lifecycle-row family to `aggregate_type == "Mission"` only, but spec-kitty emits four distinct lifecycle aggregate types (`Project`, `Mission`, `WorkPackage`, `MissionDossier`). The three non-`Mission` ones are mis-classified as non-lifecycle rows and trip the `FORBIDDEN_KEYS` rule because their envelopes carry the structural `event_type` field.

The fix surface is well-bounded: extend `is_mission_lifecycle_row` (or rename to `is_lifecycle_row`) to accept the full `{"Project", "Mission", "WorkPackage", "MissionDossier"}` set, possibly via a single `LIFECYCLE_AGGREGATE_TYPES: frozenset[str]` constant co-located with `FORBIDDEN_KEYS` in `detectors.py`. This is a 1-WP follow-up mission — exactly the path the issue body's hypothesis-2 recommendation calls for.
