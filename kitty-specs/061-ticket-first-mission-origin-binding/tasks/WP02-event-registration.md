---
work_package_id: WP02
title: Event Registration
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: feat/implement-review-skill
merge_target_branch: feat/implement-review-skill
branch_strategy: Planning artifacts for this feature were generated on feat/implement-review-skill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/implement-review-skill unless the human explicitly redirects the landing branch.
subtasks: [T008, T009, T010, T011, T012]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/emitter.py
- tests/sync/test_emitter_origin.py
---

# WP02: Event Registration

## Objective

Register `MissionOriginBound` as a new event type in `src/specify_cli/sync/emitter.py`. Add payload validation rules, the `emit_mission_origin_bound()` method, and tests.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP02`
- No dependencies — can run in parallel with WP01, WP03, WP04.

## Context

- **Spec**: `kitty-specs/061-ticket-first-mission-origin-binding/spec.md` — "Event Emission" section
- **Data model**: `kitty-specs/061-ticket-first-mission-origin-binding/data-model.md` — "Event Model" section
- **Existing pattern**: `src/specify_cli/sync/emitter.py` — study `emit_feature_created()` and its `_PAYLOAD_RULES["FeatureCreated"]` entry

## Subtasks

### T008: Add `MissionOriginBound` to `_PAYLOAD_RULES`

**File**: `src/specify_cli/sync/emitter.py`

Add a new entry to the `_PAYLOAD_RULES` dict (after `MissionDossierParityDriftDetected`):

```python
"MissionOriginBound": {
    "required": {"feature_slug", "provider", "external_issue_id", "external_issue_key", "external_issue_url", "title"},
    "validators": {
        "feature_slug": lambda v: isinstance(v, str) and bool(_FEATURE_SLUG_PATTERN.match(v)),
        "provider": lambda v: v in {"jira", "linear"},
        "external_issue_id": lambda v: isinstance(v, str) and len(v) >= 1,
        "external_issue_key": lambda v: isinstance(v, str) and len(v) >= 1,
        "external_issue_url": lambda v: isinstance(v, str) and len(v) >= 1,
        "title": lambda v: isinstance(v, str) and len(v) >= 1,
    },
},
```

`VALID_EVENT_TYPES` is derived from `_PAYLOAD_RULES.keys()` automatically — no separate update needed.

### T009: Add `emit_mission_origin_bound()` method

**File**: `src/specify_cli/sync/emitter.py`

Add to the `EventEmitter` class, following the pattern of `emit_feature_created()`:

```python
def emit_mission_origin_bound(
    self,
    feature_slug: str,
    provider: str,
    external_issue_id: str,
    external_issue_key: str,
    external_issue_url: str,
    title: str,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit MissionOriginBound event (observational telemetry only)."""
    payload: dict[str, Any] = {
        "feature_slug": feature_slug,
        "provider": provider,
        "external_issue_id": external_issue_id,
        "external_issue_key": external_issue_key,
        "external_issue_url": external_issue_url,
        "title": title,
    }
    return self._emit(
        event_type="MissionOriginBound",
        aggregate_id=feature_slug,
        aggregate_type="Feature",
        payload=payload,
        causation_id=causation_id,
    )
```

**Key points**:
- `aggregate_type` is `"Feature"` (same as `FeatureCreated`)
- `aggregate_id` is `feature_slug`
- This event is **observational telemetry only** — it does not create the SaaS-side record

### T010: Add `MissionOriginBound` validators

Already handled in T008 — the validators dict in `_PAYLOAD_RULES` covers this. Verify:
- `feature_slug` matches `^\d{3}-[a-z0-9-]+$` pattern (uses existing `_FEATURE_SLUG_PATTERN`)
- `provider` is constrained to `{"jira", "linear"}`
- All other fields are non-empty strings

### T011: Write tests for payload validation

**File**: `tests/sync/test_emitter_origin.py` (new file)

**Test cases**:
- Valid payload passes validation
- Missing required field (e.g., no `provider`) is rejected
- Invalid `feature_slug` (doesn't match pattern) is rejected
- Invalid `provider` (e.g., `"github"`) is rejected
- Empty `title` is rejected
- Empty `external_issue_key` is rejected

**Pattern**: Follow existing emitter tests — use `EventEmitter` with mocked auth, clock, and queue.

### T012: Write tests for event routing and offline queue

**Test cases**:
- Event is queued when no WebSocket is connected (offline queue)
- Event includes correct `aggregate_type="Feature"` and `aggregate_id=feature_slug`
- Event `event_type` is `"MissionOriginBound"`
- `causation_id` is passed through when provided
- Event emission is fire-and-forget (never raises)

## Definition of Done

- [ ] `MissionOriginBound` in `_PAYLOAD_RULES` with all 6 required fields
- [ ] `emit_mission_origin_bound()` method on `EventEmitter`
- [ ] Payload validation tests pass
- [ ] Event routing tests pass
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## Risks

- **Low**: Following a well-established pattern. No new infrastructure.

## Reviewer Guidance

- Verify `provider` validator only accepts `"jira"` and `"linear"` (not all SAAS_PROVIDERS)
- Verify `aggregate_type` is `"Feature"` (not a new aggregate type)
- Confirm the event is documented as observational telemetry only

## Activity Log

- 2026-04-01T17:59:59Z – unknown – Implementation complete: 15 tests passing. Ready for review.
- 2026-04-01T18:03:42Z – unknown – Done override: Code merged to feat/implement-review-skill from worktree branches; all tests passing; review approved by Codex reviewer
