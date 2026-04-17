# Research: Retire Mission Identity Drift Window

**Date**: 2026-04-13
**Mission**: `01KP2JNZ7FRXE6PZKJMH790HA5`

## Call-Site Audit

### emit_mission_created

- **Emitter method**: `src/specify_cli/sync/emitter.py:468` — `mission_id: str | None = None`
- **Wrapper**: `src/specify_cli/sync/events.py:248` — `mission_id: str | None = None` (forwards correctly)
- **Caller**: `src/specify_cli/core/mission_creation.py:345` — passes `mission_id=meta.get("mission_id")`
- **Assessment**: Working correctly. `meta.get("mission_id")` is always non-None for new missions since mission creation mints a ULID. Safe to make mandatory.

### emit_mission_closed

- **Emitter method**: `src/specify_cli/sync/emitter.py:514` — `mission_id: str | None = None`
- **Wrapper**: `src/specify_cli/sync/events.py:275` — **does NOT accept or forward `mission_id`** (gap)
- **External callers**: None found. Wrapper is exported via `sync/__init__.py` but not yet called by any production code.
- **Assessment**: Wrapper needs `mission_id: str` added. No callers to update beyond the wrapper itself.

### emit_mission_origin_bound

- **Emitter method**: `src/specify_cli/sync/emitter.py:628` — `mission_id: str | None = None`
- **No wrapper function** — called directly from `tracker/origin.py:265`
- **Caller**: `src/specify_cli/tracker/origin.py:265` — **does NOT pass `mission_id`** (gap)
- **Assessment**: Caller must be updated to load `mission_id` from meta.json and pass it.

## legacy_aggregate_id Surface

| File | Line(s) | What | Action |
|------|---------|------|--------|
| `src/specify_cli/status/models.py` | 181 | Docstring describing field | Update |
| `src/specify_cli/status/models.py` | 220-223 | `to_dict()` emits field | Remove |
| `src/specify_cli/status/emit.py` | 385-386 | Comment referencing T025 | Remove |
| `tests/status/test_event_mission_id.py` | 9, 68, 166, 171, 294, 317-350, 414-444 | Fixtures and assertions | Flip/remove |
| `tests/contract/test_identity_contract_matrix.py` | 190, 281-282, 406-412 | Contract surface, backward-compat test | Update |

## effective_aggregate_id Fallback Surface

| File | Line(s) | Method | Action |
|------|---------|--------|--------|
| `src/specify_cli/sync/emitter.py` | 497-505 | `emit_mission_created` | Remove fallback, use `mission_id` directly |
| `src/specify_cli/sync/emitter.py` | 540-544 | `emit_mission_closed` | Remove fallback, use `mission_id` directly |
| `src/specify_cli/sync/emitter.py` | 656-660 | `emit_mission_origin_bound` | Remove fallback, use `mission_id` directly |

## Documentation Surface

- `docs/`: No references to `legacy_aggregate_id` or drift window found.
- `CLAUDE.md`: No references to `legacy_aggregate_id` or drift window found (mentions "drift" only in context of status-model drift detection, which is a different concept).
- Source docstrings in `models.py` and `emitter.py`: Reference drift window — will be updated inline with code changes.

## Decisions

| Decision | Rationale | Alternative rejected |
|----------|-----------|---------------------|
| Make `mission_id` mandatory on emitter methods and wrappers | All active code paths have it; Optional type masks the invariant | Keep optional with runtime assertion — adds dead branch and test complexity |
| Keep `mission_id: str \| None` on `StatusEvent` dataclass | Legacy events on disk lack the field; removing would break deserialization (violates C-002) | Make mandatory — would require backfilling all historical event logs |
| Fix `origin.py` caller before making method mandatory | Clean compilation; prevents runtime crash in origin-binding flow | Leave caller broken — defeats purpose of mandatory type |
