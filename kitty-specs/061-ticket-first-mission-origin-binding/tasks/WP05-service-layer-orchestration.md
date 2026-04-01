---
work_package_id: WP05
title: Service-Layer Orchestration
dependencies: [WP01, WP02, WP03, WP04]
requirement_refs:
- FR-001
- FR-002
- FR-006
- FR-011
- FR-014
planning_base_branch: feat/implement-review-skill
merge_target_branch: feat/implement-review-skill
branch_strategy: Planning artifacts for this feature were generated on feat/implement-review-skill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/implement-review-skill unless the human explicitly redirects the landing branch.
subtasks: [T024, T025, T026, T027, T028, T029, T030]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/origin.py
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/origin.py
- tests/sync/tracker/test_origin.py
---

# WP05: Service-Layer Orchestration

## Objective

Implement the three service-layer functions in `src/specify_cli/tracker/origin.py`: `search_origin_candidates()`, `bind_mission_origin()`, and `start_mission_from_ticket()`. These compose the foundation (WP01), event (WP02), transport (WP03), and creation (WP04) layers into the normative API consumed by `/spec-kitty.specify`.

This is the convergence point and the most critical WP — it establishes the primary contract surface.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP05 --base WP04` (or whichever of WP01-04 merges last)
- **Dependencies**: WP01 (data models), WP02 (event), WP03 (client), WP04 (creation). ALL must be merged before this WP begins.

## Context

- **Spec**: `kitty-specs/061-ticket-first-mission-origin-binding/spec.md` — "Service-Layer API Contract" section (normative)
- **Plan**: `kitty-specs/061-ticket-first-mission-origin-binding/plan.md` — "Module Layering", "Write ordering", D3 (re-bind semantics)
- **WP01 output**: `OriginCandidate`, `SearchOriginResult`, `MissionFromTicketResult` dataclasses in `tracker/origin_models.py`; `set_origin_ticket()` helper in `feature_metadata.py`. Import models into `origin.py` for the public API surface.
- **WP02 output**: `emit_mission_origin_bound()` emitter method
- **WP03 output**: `SaaSTrackerClient.search_issues()`, `.bind_mission_origin()` transport methods
- **WP04 output**: `create_feature_core()` in `core/feature_creation.py`

## Subtasks

### T024: Implement `search_origin_candidates()`

**File**: `src/specify_cli/tracker/origin.py` (extend — dataclasses already exist from WP01)

```python
from specify_cli.tracker.config import load_tracker_config, SAAS_PROVIDERS
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError


class OriginBindingError(RuntimeError):
    """Raised when origin binding operations fail."""


def search_origin_candidates(
    repo_root: Path,
    query_text: str | None = None,
    query_key: str | None = None,
    limit: int = 10,
    *,
    client: SaaSTrackerClient | None = None,
) -> SearchOriginResult:
    """Search for candidate external issues to use as mission origin."""
```

**Implementation steps**:
1. Load tracker config from `.kittify/config.yaml`
2. Validate provider is in `{"jira", "linear"}` (hard error otherwise — C-001)
3. Validate config has `project_slug` (hard error if no binding)
4. Call `client.search_issues(provider, project_slug, query_text=..., query_key=..., limit=...)`
5. Convert response dict to `SearchOriginResult` with `OriginCandidate` list
6. Return structured result

**Error handling**:
- No tracker config: `OriginBindingError("No tracker bound...")`
- Provider not jira/linear: `OriginBindingError("Only Jira and Linear...")`
- `SaaSTrackerClientError` with `user_action_required`: Re-raise as `OriginBindingError` with dashboard link message
- Other `SaaSTrackerClientError`: Re-raise as `OriginBindingError`

**Client injection**: Accept optional `client` parameter for testability. Default to `SaaSTrackerClient()`.

### T025: Implement `bind_mission_origin()`

**File**: `src/specify_cli/tracker/origin.py`

```python
def bind_mission_origin(
    feature_dir: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
    *,
    client: SaaSTrackerClient | None = None,
) -> dict[str, Any]:
    """Bind an origin ticket to a mission. SaaS-first, local-second."""
```

**CRITICAL: SaaS-first write ordering**:
1. Load `meta.json` to get `feature_slug` (needed for SaaS call)
2. Call `client.bind_mission_origin(provider, project_slug, feature_slug=..., ...)` — **if this fails, stop and raise. No local state written.**
3. Build `origin_ticket` dict from candidate + routing context
4. Call `set_origin_ticket(feature_dir, origin_ticket)` — writes to meta.json
5. Emit `MissionOriginBound` event (fire-and-forget)
6. Return updated meta dict

**Re-bind semantics** (per D3):
- Service always calls SaaS first — does NOT inspect local meta.json to short-circuit
- SaaS decides: same-origin → no-op success, different-origin → 409

**project_slug resolution**: Load from tracker config (same as `search_origin_candidates`). The caller may pass it explicitly or the function re-resolves it.

### T026: Implement `start_mission_from_ticket()`

**File**: `src/specify_cli/tracker/origin.py`

```python
def start_mission_from_ticket(
    repo_root: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
    mission_key: str = "software-dev",
    *,
    client: SaaSTrackerClient | None = None,
) -> MissionFromTicketResult:
    """Create a mission from a confirmed external ticket."""
```

**Implementation steps**:
1. Derive slug from candidate (T027)
2. Call `create_feature_core(repo_root, slug, mission=mission_key, target_branch=None)`
3. Call `bind_mission_origin(result.feature_dir, candidate, provider, resource_type, resource_id, client=client)`
4. Return `MissionFromTicketResult`

**Error handling**:
- `FeatureCreationError` → re-raise as `OriginBindingError`
- Bind failure after successful creation: The feature exists but has no origin. This is acceptable — the agent can retry the bind separately.

### T027: Implement slug derivation from ticket key/title

**File**: `src/specify_cli/tracker/origin.py`

```python
def _derive_slug_from_ticket(candidate: OriginCandidate) -> str:
    """Derive a kebab-case feature slug from the ticket key."""
```

**Rules** (per research R5):
- Use `external_issue_key` lowercased as the slug base: `"WEB-123"` → `"web-123"`
- Sanitize to match `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`
- Replace non-alphanumeric chars with hyphens, collapse consecutive hyphens
- Strip leading/trailing hyphens
- If key sanitizes to empty, fall back to sanitized title (first 5 words)

**Examples**:
- `"WEB-123"` → `"web-123"`
- `"IAM-42"` → `"iam-42"`
- `"PROJ_KEY/123"` → `"proj-key-123"`

### T028: Write tests for `search_origin_candidates()`

**File**: `tests/sync/tracker/test_origin.py` (new file)

**Test cases** (mapping to spec scenarios):
1. **Scenario 1**: Free-text search returns multiple candidates → `SearchOriginResult` with candidate list
2. **Scenario 2**: Key search returns single candidate with `match_type="exact"`
3. **Scenario 3**: Search returns empty candidates
4. **Scenario 4**: SaaS returns user_action_required → `OriginBindingError` with dashboard message
5. **Scenario 6**: No tracker binding → `OriginBindingError`
6. **Wrong provider**: Provider is "github" → `OriginBindingError`
7. **query_key precedence**: Both provided → both sent to client

**Pattern**: Inject `MagicMock` client with canned return values.

### T029: Write tests for `bind_mission_origin()`

**Test cases**:
1. **Happy path**: SaaS succeeds → meta.json updated → event emitted → returns meta
2. **SaaS-first ordering**: SaaS fails → meta.json NOT written → `OriginBindingError`
3. **Same-origin no-op**: SaaS returns success → local overwritten identically
4. **Different-origin 409**: SaaS returns 409 → `OriginBindingError` with message
5. **origin_ticket shape**: Verify all 7 required keys present in written block
6. **Event emitted**: Verify `emit_mission_origin_bound()` called with correct args

**Critical test**: The SaaS-first ordering test must verify that `set_origin_ticket()` is NOT called when `client.bind_mission_origin()` raises. Use `MagicMock` side_effect.

### T030: Write tests for `start_mission_from_ticket()`

**Test cases**:
1. **Full flow**: Creation + bind + event → returns `MissionFromTicketResult`
2. **Creation failure**: `FeatureCreationError` → `OriginBindingError`
3. **Bind failure after creation**: Feature exists but no origin → acceptable state
4. **Slug derivation**: `"WEB-123"` → feature slug contains `"web-123"`
5. **event_emitted field**: `True` when event succeeds, `False` when event fails (but no exception)

**Pattern**: Mock both `create_feature_core()` and `SaaSTrackerClient`.

## Definition of Done

- [ ] `search_origin_candidates()` implemented and tested (all 6+ scenarios)
- [ ] `bind_mission_origin()` implemented with SaaS-first ordering and tested
- [ ] `start_mission_from_ticket()` implemented and tested
- [ ] `_derive_slug_from_ticket()` implemented and tested
- [ ] `OriginBindingError` exception class defined
- [ ] All tests pass with 90%+ coverage on `origin.py`
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## Risks

- **High**: Convergence of 4 dependencies. If any upstream WP has issues, this WP is blocked.
- **Medium**: SaaS-first write ordering must be correct — a bug here creates split-brain.
- **Mitigation**: Explicit ordering tests (T029 test case 2) catch ordering bugs.

## Reviewer Guidance

- **Most critical check**: Verify `bind_mission_origin()` calls SaaS BEFORE `set_origin_ticket()` and does NOT call `set_origin_ticket()` on SaaS failure
- Verify `search_origin_candidates()` validates provider is jira/linear (not all SAAS_PROVIDERS)
- Verify slug derivation handles edge cases (special chars, empty key)
- Verify `client` parameter injection works (for testability)
- Verify no local meta.json inspection is used to short-circuit SaaS bind

## Activity Log

- 2026-04-01T18:11:43Z – unknown – Implementation complete: 25 tests passing, SaaS-first ordering verified. Ready for review.
- 2026-04-01T18:13:27Z – unknown – Done override: Code merged from worktree; 25 tests passing; SaaS-first ordering verified; review approved
