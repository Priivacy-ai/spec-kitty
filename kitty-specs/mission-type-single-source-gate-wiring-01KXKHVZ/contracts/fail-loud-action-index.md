# Contract — `load_action_index` fail-loud (IC-2 / #2667)

**Location:** `src/doctrine/missions/action_index.py`

## New exception

```python
class ActionIndexError(ValueError):
    """A present action-index file is not a well-formed ActionIndex."""
```

Message names: the index path, the offending key (or `<root>`), and the found type.

## Decision table (the contract)

| Input state | Result |
|-------------|--------|
| File missing | `ActionIndex(action=action)` — silent fallback (UNCHANGED) |
| Present, well-formed, empty content | empty-content `ActionIndex` — **no raise** |
| Present, root is not a mapping | **raise `ActionIndexError`** |
| Present, an artifact-kind field is not a list | **raise `ActionIndexError`** |
| Present, YAML unparseable | **raise `ActionIndexError`** |

## Propagation

Sole `src/` caller is `aggregate_action_grain` (`action_grain.py`, no try/except) → the raise propagates to
`scan_builtin_cross_grain_duplicates`, `resolve_mission_type_context`, and the new `doctor doctrine` wiring.
This is the desired loud path; the FR-013 union can no longer pass falsely over a silently-dropped grain.

## Test obligations

- Re-pin `test_non_list_field_value_returns_empty_list` and the non-dict-root test to `pytest.raises(ActionIndexError)`
  (stale-contract re-pin, NOT deletion).
- New: missing-file-stays-fallback; empty-but-well-formed-index returns empty content without raising;
  unparseable-YAML raises.
