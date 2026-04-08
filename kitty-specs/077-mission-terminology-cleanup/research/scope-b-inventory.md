# Scope B: Machine-Facing Inventory and Alignment Plan

**Mission**: `077-mission-terminology-cleanup`  
**Scope**: Scope B (`#543`)  
**Date**: 2026-04-08  
**HEAD commit at inventory capture**: `d90a6465f801a160a75c812c404c5936d260eac8`

## Summary

The active first-party machine-facing code is already canonical on `mission_slug`.
The remaining Scope B drift falls into two buckets:

1. Several machine-facing serializers identify a mission with `mission_slug` only and still omit the canonical companion fields `mission_number` and `mission_type`.
2. Contract docs still describe legacy `feature_slug` compatibility behavior that the current code no longer emits.

I did **not** find any active first-party emitter in the Scope B surfaces that still writes `feature_slug` today. The remaining `feature_slug` references in code are read-compat or migration-only paths.

## Surfaces Inventory

| Surface | File | Function / serializer | Current fields | Required fields (per spec / upstream) | Drift? |
|---|---|---|---|---|---|
| Status snapshot JSON | `src/specify_cli/status/models.py` | `StatusSnapshot.to_dict()` | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Board summary JSON | `src/specify_cli/status/views.py` | `_build_board_summary()` | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Progress JSON | `src/specify_cli/status/progress.py` | `ProgressResult.to_dict()` | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Context token JSON | `src/specify_cli/context/models.py` | `MissionContext.to_dict()` | `mission_slug`, `mission_id` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Acceptance matrix JSON | `src/specify_cli/acceptance_matrix.py` | `AcceptanceMatrix.to_dict()` | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Merge gate evaluation JSON | `src/specify_cli/policy/merge_gates.py` | `MergeGateEvaluation.to_dict()` | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| `spec-kitty next --json` decision payload | `src/specify_cli/next/decision.py` | `Decision.to_dict()` | `mission_slug`, legacy-ish `mission` field for mission type | `mission_slug`, `mission_number`, `mission_type` | Yes, missing canonical `mission_type` field name and missing `mission_number` |
| Orchestrator API response payloads | `src/specify_cli/orchestrator_api/commands.py` | `mission-state`, `list-ready`, `start-implementation`, `start-review`, `transition`, `append-history`, `accept-mission`, `merge-mission`, merge failures | `mission_slug` | `mission_slug`, `mission_number`, `mission_type` | Yes, missing `mission_number` + `mission_type` |
| Orchestrator API envelope | `src/specify_cli/orchestrator_api/envelope.py` | top-level envelope | fixed 7-key envelope | fixed 7-key envelope | No drift; locked by C-010 |
| Status event readers | `src/specify_cli/status/models.py` | `StatusEvent.from_dict()`, `StatusSnapshot.from_dict()` | accept `mission_slug` or legacy `feature_slug` | canonical output only; read-compat allowed for history | No emit drift; keep read-compat |
| Status event validator | `src/specify_cli/status/validate.py` | event validation | accepts `mission_slug` or legacy `feature_slug` | canonical output only; read-compat allowed for history | No emit drift; keep read-compat |
| WP metadata model | `src/specify_cli/status/wp_metadata.py` | `WPMetadata` | legacy `feature_slug` field in model | internal/frontmatter compatibility only | Out of Scope for Scope B emitters |

## Residual `feature_*` Fields

| Field | Surface | Decision | Rationale |
|---|---|---|---|
| `feature_slug` | `src/specify_cli/status/models.py` read paths (`from_dict`) | Keep as read-compat only | Historical `status.events.jsonl` / `status.json` payloads may still contain the legacy field; current serializers already emit canonical-only output. |
| `feature_slug` | `src/specify_cli/status/validate.py` inbound validation | Keep as read-compat only | Validator must continue to accept historical event logs while Scope B avoids rewriting historical artifacts (C-011). |
| `feature_slug` | `src/specify_cli/status/wp_metadata.py` model field | Leave for now; do not treat as machine-facing emit | Frontmatter parsing compatibility, not an active first-party JSON contract. |
| `feature_slug` | `docs/reference/event-envelope.md` and `docs/reference/orchestrator-api.md` | Remove from active contract docs | The current code no longer emits this field on the active machine-facing surfaces inventoried above. |

## Upstream Contract Mapping

| `upstream_contract.json` section | Forbidden fields | Required fields | First-party surfaces |
|---|---|---|---|
| `envelope` | `feature_slug`, `feature_number` | `schema_version`, `build_id`, `aggregate_type`, `event_type` | Orchestrator envelope, event-envelope docs |
| `payload.mission_scoped` | `feature_slug`, `feature_number`, `feature_type` | `mission_slug`, `mission_number`, `mission_type` | Status snapshot, board summary, progress JSON, context JSON, acceptance matrix, merge gate evaluation, next decision payload, orchestrator response payloads |
| `body_sync` | `feature_slug`, `mission_key` | `project_uuid`, `mission_slug`, `target_branch`, `mission_type`, `manifest_version` | Sync/body transport surfaces (already canonical; not part of current drift set) |
| `orchestrator_api` | `feature_slug` | `mission_slug` | `src/specify_cli/orchestrator_api/commands.py`, `docs/reference/orchestrator-api.md` |

## Alignment Plan (input to WP12)

### Field changes

1. Introduce one small shared helper rooted in `meta.json` to resolve:
   - `mission_slug`
   - `mission_number`
   - `mission_type`
2. Use that helper to enrich the active machine-facing serializers listed above.
3. Keep the orchestrator envelope width unchanged; only enrich the `data` payloads.
4. Add canonical `mission_type` to `Decision.to_dict()` while keeping the existing `mission` field for compatibility unless a direct consumer break is proven safe to remove.

### Compat gating

1. Do **not** reintroduce `feature_slug` into any active output surface.
2. Preserve `feature_slug` acceptance on historical read paths only:
   - `StatusEvent.from_dict()`
   - `StatusSnapshot.from_dict()`
   - `status.validate`
3. Document those read-compat paths as historical-ingestion compatibility, not as active contract aliases.

### Removal-date assignments

1. Active contract docs:
   - Remove `feature_slug` from `docs/reference/event-envelope.md`.
   - Remove `feature_slug` from `docs/reference/orchestrator-api.md`.
2. Historical read-compat:
   - Keep without a removal in this mission because C-011 forbids rewriting old artifacts and Scope B is not a historical-log migration mission.

## Constraints (locked)

- C-008: no abstraction that makes a future Mission → MissionRun rename easier
- C-009: no `mission_run_slug` field
- C-010: no widening of the orchestrator-api envelope
- C-011: do not rewrite historical artifacts outside this mission
- All spec §3.3 non-goals stay locked

## WP12 Write Set

Planned code-change write set based on the inventory above:

- `src/specify_cli/mission_metadata.py` or adjacent helper module
- `src/specify_cli/status/models.py`
- `src/specify_cli/status/reducer.py`
- `src/specify_cli/status/views.py`
- `src/specify_cli/status/progress.py`
- `src/specify_cli/context/models.py`
- `src/specify_cli/context/resolver.py`
- `src/specify_cli/acceptance_matrix.py`
- `src/specify_cli/policy/merge_gates.py`
- `src/specify_cli/next/decision.py`
- `src/specify_cli/next/runtime_bridge.py`
- `src/specify_cli/orchestrator_api/commands.py`
- `tests/contract/test_machine_facing_canonical_fields.py`

## Review Notes

- The planning assumption that active drift lives under `src/specify_cli/agent/**` does not match the current repo layout. The real Scope B emitters are under `status/`, `context/`, `next/`, `policy/`, and `orchestrator_api/`.
- The code-side machine-facing drift is mostly omission drift (`mission_number` / `mission_type` missing), not alias drift (`feature_slug` still emitted).
