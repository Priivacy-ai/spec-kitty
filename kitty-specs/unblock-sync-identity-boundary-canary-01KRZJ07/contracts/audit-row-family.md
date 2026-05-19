# Contract: Audit row-family classifier (for #1122)

**Module**: `src/specify_cli/audit/shape_registry.py`, `src/specify_cli/audit/detectors.py`
**WP**: WP01

## API surface

A new public predicate in `shape_registry.py`:

```python
def is_mission_lifecycle_row(row: Mapping[str, Any]) -> bool:
    """Return True iff `row` matches the mission-lifecycle row family.

    A row is a mission-lifecycle row iff it carries both:
      - aggregate_type == "Mission"
      - a non-empty `event_type` string
    """
```

The detector currently at `src/specify_cli/audit/detectors.py:55` consults this predicate:

```python
FORBIDDEN_KEYS: frozenset[str] = frozenset({"event_type", "event_name"})

def detect_forbidden_keys(row: Mapping[str, Any], ...) -> Iterator[Finding]:
    if is_mission_lifecycle_row(row):
        return  # lifecycle rows legitimately carry `event_type`
    for key in FORBIDDEN_KEYS:
        if key in row:
            yield Finding(code="FORBIDDEN_KEY", detail=f"forbidden key: {key!r}", ...)
```

## Behavioral contract

| Input row | Expected behavior |
|-----------|-------------------|
| `{"from_lane": "planned", "to_lane": "claimed", "wp_id": "WP01", ...}` | Status-transition row. FORBIDDEN_KEY check runs; passes (no `event_type`/`event_name`). |
| `{"aggregate_type": "Mission", "event_type": "MissionCreated", ...}` | Lifecycle row. FORBIDDEN_KEY check is skipped. **No finding** emitted. |
| `{"aggregate_type": "Mission", "event_type": "SpecifyStarted", ...}` | Same as above. **No finding**. |
| `{"event_type": "Foo"}` (no `aggregate_type`) | Not a lifecycle row by classifier. FORBIDDEN_KEY check runs; flags `event_type`. |
| `{"aggregate_type": "Mission"}` (no `event_type`) | Not a lifecycle row by classifier. FORBIDDEN_KEY check runs; passes (no `event_type`). |
| `{"from_lane": "planned", "to_lane": "claimed", "event_type": "X"}` | Malformed (carries transition AND lifecycle discriminators). Not a lifecycle row (no `aggregate_type=Mission`). FORBIDDEN_KEY check runs; flags `event_type`. |

## TeamSpace gate downstream

`src/specify_cli/audit/models.py:19-30` keeps `FORBIDDEN_KEY` in `TEAMSPACE_BLOCKER_CODES`. The behavioral result is:
- A fresh mission's lifecycle rows do **not** generate `FORBIDDEN_KEY` findings → no TeamSpace blocker → `spec-kitty sync now` connects.
- A genuinely malformed status-transition row carrying `event_type` still produces a `FORBIDDEN_KEY` finding → still blocks TeamSpace migration → the regression guard remains.

## Test surface (WP01)

`tests/specify_cli/audit/test_detectors_row_family.py`:
- One test per row shape in the table above.
- One scenario test that runs `spec-kitty agent mission create` in a tmp project + `spec-kitty doctor mission-state --audit --json` and asserts zero `FORBIDDEN_KEY` findings.
- One regression test that injects a synthetic status-transition row with `event_type` and asserts the audit still flags it.
