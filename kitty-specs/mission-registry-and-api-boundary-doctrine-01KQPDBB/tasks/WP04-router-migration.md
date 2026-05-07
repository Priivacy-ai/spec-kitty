---
work_package_id: WP04
title: Router migration — wire MissionRegistry into FastAPI + CLI
dependencies:
- WP02
- WP03
requirement_refs:
- C-003
- C-005
- FR-004
- FR-005
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
agent: "opencode:claude-sonnet-4.6:python-pedro:reviewer"
shell_pid: "1505960"
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/
execution_mode: code_change
owned_files:
- src/dashboard/api/app.py
- src/dashboard/api/deps.py
- src/dashboard/api/routers/features.py
- src/dashboard/api/routers/kanban.py
- src/dashboard/services/mission_scan.py
- src/specify_cli/cli/commands/dashboard.py
role: implementer
tags:
- migration
- transport
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are Python Pedro. This WP changes nothing about the JSON wire shape — only the data flow underneath. Per spec C-005, no public API surface change. Existing parity tests must continue to pass.

## Objective

Wire `MissionRegistry` (delivered by WP03) into:

1. The FastAPI app via `app.state.mission_registry` + a `Depends` helper.
2. The two existing routers that read mission data (`features.py`, `kanban.py`) — switch from `MissionScanService` scanner calls to registry calls.
3. The `MissionScanService` itself — delegate its reads to the registry instead of calling the scanner directly.
4. The CLI `spec-kitty dashboard --json` mode — switch from `build_mission_registry(project_root)` direct call to the new registry.

## Context

Today's data flow:

```
FastAPI router → MissionScanService → scanner.scan_all_features → filesystem
CLI dashboard --json → scanner.build_mission_registry → filesystem
glossary router internals → ad-hoc filesystem reads
```

After this WP:

```
FastAPI router → MissionScanService → MissionRegistry → scanner (cached) → filesystem
CLI dashboard --json → MissionRegistry → scanner (cached) → filesystem
glossary router internals: untouched (out of scope, mission C #954)
```

The `MissionScanService` stays in place — it owns active-feature resolution and other logic that's not pure registry data. It now receives registry data through delegation rather than calling the scanner.

The legacy scanner shim (`src/specify_cli/scanner.py`) and the underlying `specify_cli.dashboard.scanner` module remain for the strangler period. WP05's architectural test will FAIL CI on any new transport import of either one.

## Subtasks

### T011 — Wire `MissionRegistry` into FastAPI app state

**Files**: `src/dashboard/api/app.py`, `src/dashboard/api/deps.py`.

**Action**: in `create_app(project_dir, project_token)`, after `app.state.project_dir = ...`, add:

```python
from dashboard.services.registry import MissionRegistry
app.state.mission_registry = MissionRegistry(project_dir=app.state.project_dir)
```

In `deps.py`, add the Depends helper:

```python
def get_mission_registry(request: Request) -> MissionRegistry:
    """Pull the MissionRegistry from app.state.

    Raises RuntimeError (mapped to 500) when app.state.mission_registry is
    absent — matches the existing get_project_dir dependency's pattern.
    """
    registry = getattr(request.app.state, "mission_registry", None)
    if registry is None:
        raise RuntimeError("dashboard mission_registry is not configured")
    return registry
```

Add `get_mission_registry` to the `__all__` of `deps.py`.

**Validation**: existing `tests/test_dashboard/test_fastapi_app.py` must continue to pass. The `app.state.mission_registry` is a strict addition; no breaking changes.

### T012 — Migrate FastAPI routers + `MissionScanService`

**Files**: `src/dashboard/api/routers/features.py`, `src/dashboard/api/routers/kanban.py`, `src/dashboard/services/mission_scan.py`.

**Action**:

1. In `features.py` and `kanban.py`, use `Depends(get_mission_registry)` to receive a `MissionRegistry`. Pass it to `MissionScanService` (or a new method on the service that accepts the registry).

2. In `mission_scan.py`, refactor `MissionScanService` so its data access goes through the registry:

```python
class MissionScanService:
    def __init__(
        self,
        project_dir: Path,
        registry: MissionRegistry | None = None,
        ...
    ):
        self._project_dir = project_dir
        self._registry = registry or MissionRegistry(project_dir=project_dir)
        ...

    def get_features_list(self) -> FeaturesListResponse:
        # Was: features = scan_all_features(self._project_dir)
        # Now: derive from registry
        missions = self._registry.list_missions()
        features = [self._mission_record_to_feature_item(m) for m in missions]
        ...
```

The `_mission_record_to_feature_item` helper is the mapping from the new `MissionRecord` dataclass to the existing `FeatureItem` TypedDict (the wire shape). This is the boundary between the registry's stable Python contract and the existing API's wire shape; document it in the helper's docstring.

**`get_features_list` return shape MUST be byte-identical** to today's response (per spec C-005). The existing `tests/test_dashboard/test_seams.py` and the OpenAPI snapshot test catch any divergence.

### T013 — Migrate CLI `spec-kitty dashboard --json`

**File**: `src/specify_cli/cli/commands/dashboard.py`.

**Action**: in the `--json` mode block (around line 59), replace:

```python
from specify_cli.dashboard.scanner import build_mission_registry, sort_missions_for_display
registry = build_mission_registry(project_root)
display_order = sort_missions_for_display(registry)
```

with:

```python
from dashboard.services.registry import MissionRegistry
registry = MissionRegistry(project_root)
missions = registry.list_missions()

# Map MissionRecord list back to the wire-shape dict the CLI emits.
mission_dict = {m.mission_id: _mission_record_to_cli_dict(m) for m in missions}
display_order = [m.mission_id for m in missions]  # already sorted by registry
```

The `_mission_record_to_cli_dict` helper mirrors the wire shape `build_mission_registry` produced today. The existing CLI smoke test (`spec-kitty dashboard --json`) must produce the same output count and the same set of `mission_id` keys.

**Verify CLI parity**: run `spec-kitty dashboard --json | jq '.missions | keys | length'` before and after the change; the count must match.

## Branch Strategy

Lane-less on `feature/650-dashboard-ui-ux-overhaul`. Three coordinated changes; keep them in one or two commits with clear `feat(WP04-...)` messages.

## Definition of Done

- [ ] `app.state.mission_registry` is set at FastAPI startup.
- [ ] `get_mission_registry()` Depends helper exists in `deps.py`.
- [ ] `features.py` + `kanban.py` consume the registry via `Depends(get_mission_registry)`.
- [ ] `MissionScanService.get_features_list()` derives from `registry.list_missions()`, not from `scan_all_features` directly.
- [ ] `MissionScanService.get_kanban()` derives from `registry.workpackages_for(...)`, not from `scan_feature_kanban` directly.
- [ ] CLI `dashboard --json` consumes the registry; before/after count matches.
- [ ] Existing parity tests in `tests/test_dashboard/test_seams.py` pass without modification (wire shape preserved).
- [ ] OpenAPI snapshot test passes without modification (FR-006 of mission #01KQN2JA — no schema drift).
- [ ] No imports of `specify_cli.dashboard.scanner` or `specify_cli.scanner` remain in:
  - `src/dashboard/api/routers/`
  - `src/specify_cli/cli/commands/dashboard.py`

  WP05's architectural test will enforce this; this WP must produce the compliant code that test will scan.

## Reviewer guidance

- **Wire-shape parity**: the routers and the CLI must return byte-identical JSON before and after this WP. Diff a pre-WP `curl /api/features` against post-WP; deltas indicate a bug.
- **No re-implementation of mission identity logic**: the `_mission_record_to_feature_item` and `_mission_record_to_cli_dict` helpers are pure mappings. They MUST NOT add fields, omit fields, or transform values beyond format conversion (e.g., `Path` → str).
- **Test sanity** (mission-wide C-003): no mocked registries in the migration tests; if a test mocks `MissionRegistry`, that's a sign the test is bypassing the production data flow. Use real fixture projects.

## Risks

- **`features` shape divergence**: the `kanban_stats.weighted_percentage` field was added by mission #01KQN2JA's post-merge fix. Confirm the registry's `MissionRecord.lane_counts` + `weighted_percentage` fields are mapped into the wire `kanban_stats` dict identically.
- **CLI `display_order` ordering**: the existing `sort_missions_for_display` may sort by display_number THEN by mission_slug; confirm the registry's `list_missions()` returns the same order (it does per the `data-model.md` ordering contract, but verify against the CLI smoke test).
- **`MissionScanService` constructor backward compat**: external callers (if any) construct `MissionScanService(project_dir=..., _scan_all=...)` with explicit injectables. The registry parameter is additive (default constructs its own); no breakage.

## Activity Log

- 2026-05-03T14:34:22Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1427345 – Started implementation via action command
- 2026-05-03T17:02:03Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1427345 – Stale agent recovery — previous claude agent (pid=1427345) did not complete. Resuming implementation.
- 2026-05-03T17:02:09Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1427345 – Stale agent recovery — force-advancing to for_review so we can reject and re-queue cleanly.
- 2026-05-03T17:02:17Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1427345 – Moved to planned
- 2026-05-03T17:02:31Z – opencode:claude-sonnet-4.6:python-pedro:implementer – shell_pid=1498620 – Started implementation via action command
- 2026-05-03T17:04:47Z – opencode:claude-sonnet-4.6:python-pedro:implementer – shell_pid=1498620 – T011/T012/T013 complete: MissionRegistry wired into FastAPI app state + deps + routers + CLI; 270 tests pass; no scanner imports in transport layer
- 2026-05-03T17:04:54Z – opencode:claude-sonnet-4.6:python-pedro:reviewer – shell_pid=1505960 – Started review via action command
- 2026-05-03T17:06:10Z – opencode:claude-sonnet-4.6:python-pedro:reviewer – shell_pid=1505960 – Review passed: all DoD items verified — app.state.mission_registry set at startup; get_mission_registry in deps.__all__; features.py + kanban.py use Depends(get_mission_registry); get_features_list drives iteration via registry.list_missions(); get_kanban pre-resolves via registry.get_mission(); no banned scanner imports in transport layer; 270 tests pass; seams + OpenAPI snapshot clean.
