---
work_package_id: WP03
title: DRIFT-4 — Thin handle_kanban and handle_sync_trigger to Single-Call Adapters
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- NFR-002
- NFR-003
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/services/
execution_mode: code_change
owned_files:
- src/dashboard/services/mission_scan.py
- src/dashboard/services/sync.py
- src/specify_cli/dashboard/handlers/features.py
- src/specify_cli/dashboard/handlers/api.py
- tests/test_dashboard/test_seams.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Complete FR-007 of the parent mission `dashboard-service-extraction-01KQMCA6`: reduce `handle_kanban` and `handle_sync_trigger` to single-call adapters. The post-merge review (DRIFT-4) flagged that `handle_kanban` retained 3 lines of inline path arithmetic and `handle_sync_trigger` was 34 lines with 4-way result dispatch.

## Subtasks (already implemented at commit `dcbba9439`)

### T008 — `parse_kanban_path` helper

Module-level function in `src/dashboard/services/mission_scan.py`:

```python
def parse_kanban_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) < 4:
        return None
    return parts[3]
```

Module-level (not a staticmethod) so seam tests that patch `MissionScanService` do not also intercept this pure function.

### T009 — Thin `handle_kanban`

```python
def handle_kanban(self, path: str) -> None:
    if self.project_dir is None:
        raise RuntimeError("dashboard project_dir is not configured")
    from dashboard.services.mission_scan import MissionScanService, parse_kanban_path

    feature_id = parse_kanban_path(path)
    if feature_id is None:
        self.send_response(404)
        self.end_headers()
        return
    service = MissionScanService(...)
    response = service.get_kanban(feature_id)
    self._send_json(200, response)
```

### T010 — `SyncTriggerResult.body()`

Add a `body()` method that produces the JSON payload per status branch (scheduled / skipped / unavailable / failed). The 4-way dispatch moves from the handler into the dataclass.

### T011 — Thin `handle_sync_trigger`

```python
def handle_sync_trigger(self) -> None:
    from dashboard.services.sync import SyncService

    expected_token = getattr(self, "project_token", None)
    parsed_path = urllib.parse.urlparse(self.path)
    token_values = urllib.parse.parse_qs(parsed_path.query).get("token")
    token = token_values[0] if token_values else None

    if expected_token and token != expected_token:
        self._send_json(403, {"error": "invalid_token"})
        return

    service = SyncService(_ensure_running=ensure_sync_daemon_running, _get_daemon_status=get_sync_daemon_status)
    result = service.trigger_sync(token=token)
    self._send_json(result.http_status, result.body())
```

### T012 — Update kanban seam test

`test_kanban_delegates_to_mission_scan_service` switches to the `_send_json` pattern (consistent with the rest of the seam suite). Add `test_kanban_returns_404_on_short_path` for the no-feature-id path.

### T013 — Parametrized body() coverage + pure-helper tests

Add `test_sync_trigger_dispatches_all_result_branches` parametrized over the 4 status variants. Add a `TestPureHelpers` class with `test_parse_kanban_path` (5 cases) and 5 `body()` variant tests covering scheduled / skipped / unavailable-with-reason / unavailable-without-reason / failed.

## Definition of Done

- [ ] `handle_kanban` body is ≤ 10 lines (excluding docstring).
- [ ] `handle_sync_trigger` body is ≤ 15 lines.
- [ ] Every existing seam test in `tests/test_dashboard/test_seams.py` passes.
- [ ] New pure-helper tests pass.
- [ ] `parse_kanban_path` is module-level (not a staticmethod) so seam-test patches do not intercept it.
- [ ] `SyncTriggerResult.body()` covers all 4 status branches; failed includes the default `error="sync_trigger_failed"`.

## Reviewer guidance

- Eyeball the handler bodies: do they look like adapter code or do they hold business logic?
- Confirm token validation stays in the adapter (FR / spec C-005).
- Confirm `result.body()` is called once in the handler, not deconstructed.

## Risks

- Patch-target divergence in seam tests: `MissionScanService` is patched at `dashboard.services.mission_scan.MissionScanService`; the new module-level `parse_kanban_path` is NOT intercepted by that patch (correct behavior — it's a pure function). Verified by the new `test_kanban_returns_404_on_short_path` test which patches the class but expects the pure function to still parse the path.

## Activity Log

- 2026-05-02T19:50:44Z – claude – Moved to claimed
- 2026-05-02T19:50:47Z – claude – Moved to in_progress
- 2026-05-02T19:52:42Z – claude – Moved to for_review
- 2026-05-02T19:52:45Z – claude – Moved to in_review
- 2026-05-02T19:52:48Z – claude – Moved to approved
- 2026-05-02T19:54:20Z – claude – Done override: Implementation landed directly on feature/650-dashboard-ui-ux-overhaul at commit dcbba9439 without lane worktrees; the work-package decomposition in this followup mission formalizes the post-merge review trail for findings already in the tree
