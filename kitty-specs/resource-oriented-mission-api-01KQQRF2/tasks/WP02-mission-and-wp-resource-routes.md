---
work_package_id: WP02
title: New mission and workpackage resource routes
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-013
- FR-014
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
- T016
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/dashboard/api/routers/missions.py
- src/dashboard/api/app.py
- tests/test_dashboard/test_missions_api.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create `src/dashboard/api/routers/missions.py` with all five new resource-oriented endpoints, register it in `app.py`, and cover it with tests. After this WP, clients can fetch mission lists, single missions, mission status, WP lists, and individual WPs via HATEOAS-LITE linked resources.

## Branch Strategy

- **Planning base / merge target**: `feature/650-dashboard-ui-ux-overhaul`
- Depends on WP01 — run: `spec-kitty agent action implement WP02 --agent claude`
- Execution workspace: same Lane A worktree as WP01.

## Context

**Prerequisites from WP01** (must be present before starting):
- `WorkPackageRecord` has `claimed_at` and `blocked_reason`.
- `models.py` exports: `MissionSummary`, `Mission`, `MissionStatus`, `WorkPackageSummary`, `WorkPackage`, `WorkPackageAssignment`, `ReviewEvidence`.
- `ResourceModel` and `Link` are importable from `dashboard.api.models`.

**Registry API** (`src/dashboard/services/registry.py`):
- `MissionRegistry.list_missions() → list[MissionRecord]`
- `MissionRegistry.get_mission(id_or_slug: str) → MissionRecord | None` — returns `None` for not-found; raises an exception (check the actual implementation) for ambiguous `mid8`.
- `WorkPackageRegistry.list_work_packages() → list[WorkPackageRecord]`
- `WorkPackageRegistry.get_work_package(wp_id: str) → WorkPackageRecord | None`

**Depends pattern** (`src/dashboard/api/deps.py`):
- `get_mission_registry() → MissionRegistry` — inject via `Depends`.

**App registration** (`src/dashboard/api/app.py`):
- Look for the `create_app()` factory function; it includes routers with `app.include_router(...)`.
- Add `from dashboard.api.routers import missions as missions_router` and `app.include_router(missions_router.router)`.

**Arch test constraints** (must stay green):
- `tests/architectural/test_transport_does_not_import_scanner.py` — new router must not import from `specify_cli.dashboard.scanner` or any `*scanner*` path.
- `tests/architectural/test_url_naming_convention.py` — new URLs must match the resource-noun convention.

## Implementation Guide

### T007 — Create missions.py skeleton

**File**: `src/dashboard/api/routers/missions.py` (new file)

```python
"""Resource-oriented mission and workpackage endpoints.

All routes call get_mission_registry() — never the scanner directly.
Tags: missions
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from dashboard.api.deps import get_mission_registry
from dashboard.api.models import (
    Link, Mission, MissionStatus, MissionSummary,
    WorkPackage, WorkPackageAssignment, WorkPackageSummary,
)
from dashboard.services.registry import MissionRegistry, MissionRecord, WorkPackageRecord

router = APIRouter(tags=["missions"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def _mission_links(mission_id: str) -> dict[str, Link]:
    return {
        "self": Link(href=f"/api/missions/{mission_id}"),
        "status": Link(href=f"/api/missions/{mission_id}/status"),
        "workpackages": Link(href=f"/api/missions/{mission_id}/workpackages"),
    }


def _wp_links(mission_id: str, wp_id: str) -> dict[str, Link]:
    return {
        "self": Link(href=f"/api/missions/{mission_id}/workpackages/{wp_id}"),
        "mission": Link(href=f"/api/missions/{mission_id}"),
        "workpackages": Link(href=f"/api/missions/{mission_id}/workpackages"),
    }


def _get_mission_or_raise(registry: MissionRegistry, mission_id: str) -> MissionRecord:
    """Resolve mission_id/mid8/slug; raise 404 or 409 appropriately."""
    try:
        record = registry.get_mission(mission_id)
    except Exception as exc:
        # Catch AmbiguousMissionSelector or equivalent from the registry
        error_str = str(exc)
        if "ambiguous" in error_str.lower() or "AMBIGUOUS" in error_str:
            raise HTTPException(
                status_code=409,
                detail={"error": "MISSION_AMBIGUOUS_SELECTOR", "input": mission_id},
            )
        raise
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mission not found: {mission_id}")
    return record


def _record_to_summary(record: MissionRecord) -> MissionSummary:
    return MissionSummary(
        mission_id=record.mission_id,
        mission_slug=record.mission_slug,
        mission_number=record.display_number,
        mid8=record.mid8,
        friendly_name=record.friendly_name,
        mission_type=record.mission_type,
        target_branch=record.target_branch,
        lane_counts=record.lane_counts,
        weighted_percentage=record.weighted_percentage,
        is_legacy=record.is_legacy,
        **{"_links": _mission_links(record.mission_id)},
    )


def _wp_record_to_assignment(wp: WorkPackageRecord) -> WorkPackageAssignment:
    return WorkPackageAssignment(
        wp_id=wp.wp_id,
        lane=wp.lane,
        assignee=wp.assignee,
        agent_profile=wp.agent_profile,
        role=wp.role,
        claimed_at=wp.claimed_at,
        last_event_id=wp.last_event_id,
        blocked_reason=wp.blocked_reason,
        review_evidence=None,   # TODO: derive from event log in a follow-up
    )
```

**Note on `_get_mission_or_raise`**: First check the actual exception type raised by the registry on ambiguous selectors. Look for `AmbiguousMissionSelector` or similar in `registry.py`. Catch the specific type rather than bare `Exception` if it is importable.

---

### T008 — GET /api/missions

```python
@router.get("/api/missions", response_model=list[MissionSummary])
async def list_missions(
    registry: MissionRegistry = Depends(get_mission_registry),
) -> list[MissionSummary]:
    """List all missions with HATEOAS-LITE links."""
    records = registry.list_missions()
    return [_record_to_summary(r) for r in records]
```

---

### T009 — GET /api/missions/{mission_id}

```python
@router.get("/api/missions/{mission_id}", response_model=Mission)
async def get_mission(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> Mission:
    """Fetch a single mission by mission_id, mid8, or mission_slug."""
    record = _get_mission_or_raise(registry, mission_id)
    return Mission(
        mission_id=record.mission_id,
        mission_slug=record.mission_slug,
        mission_number=record.display_number,
        mid8=record.mid8,
        friendly_name=record.friendly_name,
        mission_type=record.mission_type,
        target_branch=record.target_branch,
        created_at=record.created_at,
        lane_counts=record.lane_counts,
        weighted_percentage=record.weighted_percentage,
        is_legacy=record.is_legacy,
        **{"_links": _mission_links(record.mission_id)},
    )
```

---

### T010 — GET /api/missions/{mission_id}/status

```python
@router.get("/api/missions/{mission_id}/status", response_model=MissionStatus)
async def get_mission_status(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> MissionStatus:
    record = _get_mission_or_raise(registry, mission_id)
    lc = record.lane_counts
    return MissionStatus(
        mission_id=record.mission_id,
        lane_counts=lc,
        weighted_percentage=record.weighted_percentage,
        done_count=lc.done,
        total_count=lc.total,
        current_phase=2,
        **{"_links": {
            "self": Link(href=f"/api/missions/{record.mission_id}/status"),
            "mission": Link(href=f"/api/missions/{record.mission_id}"),
        }},
    )
```

---

### T011 — GET /api/missions/{mission_id}/workpackages

```python
@router.get("/api/missions/{mission_id}/workpackages", response_model=list[WorkPackageSummary])
async def list_work_packages(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> list[WorkPackageSummary]:
    record = _get_mission_or_raise(registry, mission_id)
    wp_registry = registry.get_wp_registry(record)  # or however the registry exposes WP access
    wps = wp_registry.list_work_packages()
    return [
        WorkPackageSummary(
            wp_id=wp.wp_id,
            title=wp.title,
            assignment=_wp_record_to_assignment(wp),
            **{"_links": {
                "self": Link(href=f"/api/missions/{record.mission_id}/workpackages/{wp.wp_id}"),
                "mission": Link(href=f"/api/missions/{record.mission_id}"),
            }},
        )
        for wp in wps
    ]
```

**Important**: Check `MissionRegistry`'s actual API for accessing per-mission WP data. It may be `registry.list_work_packages(mission_id_or_slug)` directly rather than a separate `WorkPackageRegistry` object. Read `registry.py` carefully and adjust.

---

### T012 — GET /api/missions/{mission_id}/workpackages/{wp_id}

```python
@router.get("/api/missions/{mission_id}/workpackages/{wp_id}", response_model=WorkPackage)
async def get_work_package(
    mission_id: str,
    wp_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> WorkPackage:
    record = _get_mission_or_raise(registry, mission_id)
    wp = registry.get_work_package(mission_id, wp_id)  # adjust API as needed
    if wp is None:
        raise HTTPException(status_code=404, detail=f"Work package not found: {wp_id}")
    prompt_ref = str(wp.prompt_path) if wp.prompt_path and wp.prompt_path.exists() else None
    return WorkPackage(
        wp_id=wp.wp_id,
        title=wp.title,
        assignment=_wp_record_to_assignment(wp),
        subtasks_done=wp.subtasks_done,
        subtasks_total=wp.subtasks_total,
        dependencies=list(wp.dependencies),
        requirement_refs=list(wp.requirement_refs),
        prompt_ref=prompt_ref,
        **{"_links": _wp_links(record.mission_id, wp.wp_id)},
    )
```

---

### T013 — Register in app.py

**File**: `src/dashboard/api/app.py`

Add the missions router. Find the block where other routers are included and add:

```python
from dashboard.api.routers import missions as missions_router
# ...
app.include_router(missions_router.router)
```

Place it near the features/kanban routers for logical grouping.

---

### T014 — Test file

**File**: `tests/test_dashboard/test_missions_api.py` (new file)

Write tests using the FastAPI `TestClient` (or the existing test infrastructure pattern from `tests/test_dashboard/`). Cover:

1. `GET /api/missions` — 200, non-empty list, each item has `_links.self`, `_links.status`, `_links.workpackages`.
2. `GET /api/missions/{mission_id}` — 200 with valid `mission_id`; verify `_links` shape.
3. `GET /api/missions/{unknown}` — 404.
4. `GET /api/missions/{mission_id}/status` — 200; verify `lane_counts.total >= 0`, `_links.mission` present.
5. `GET /api/missions/{mission_id}/workpackages` — 200, list of items each with `assignment.wp_id` and `_links.self`.
6. `GET /api/missions/{mission_id}/workpackages/{wp_id}` — 200 for known WP.
7. `GET /api/missions/{mission_id}/workpackages/WP_NONEXISTENT` — 404.

Look at existing tests like `tests/test_dashboard/test_api_contract.py` for the fixture pattern (how the test client and fixture project are set up).

---

### T015 — Verify test_transport_does_not_import_scanner

```bash
.venv/bin/python -m pytest tests/architectural/test_transport_does_not_import_scanner.py -v
```

Must pass. If it fails because `missions.py` imports a scanner module, remove that import — all data must flow through `MissionRegistry`.

---

### T016 — Verify test_url_naming_convention

```bash
.venv/bin/python -m pytest tests/architectural/test_url_naming_convention.py -v
```

Must pass. The new `/api/missions/**` paths follow the resource-noun convention. If the test has an allowlist it checks against, the new paths should pass automatically.

## Definition of Done

- [ ] `src/dashboard/api/routers/missions.py` exists with all 5 routes.
- [ ] Router registered in `app.py`.
- [ ] `GET /api/missions` returns `list[MissionSummary]` each with `_links.self/status/workpackages`.
- [ ] `GET /api/missions/{id}` returns 200/404/409 correctly.
- [ ] `GET /api/missions/{id}/status` returns `MissionStatus` with `_links`.
- [ ] `GET /api/missions/{id}/workpackages` returns `list[WorkPackageSummary]` with `_links`.
- [ ] `GET /api/missions/{id}/workpackages/{wp_id}` returns `WorkPackage` or 404.
- [ ] `tests/test_dashboard/test_missions_api.py` passes.
- [ ] `test_transport_does_not_import_scanner.py` passes.
- [ ] `test_url_naming_convention.py` passes.
- [ ] Zero new `# type: ignore` added.

## Risks

- **Registry WP access API**: The exact method signatures for accessing per-mission WPs may differ from what's shown above. Read `registry.py` before coding and adjust accordingly.
- **Ambiguity exception type**: The `_get_mission_or_raise` helper catches generic `Exception` as a fallback. Identify the specific exception class in the registry and catch it precisely.
- **`_links` field aliasing**: When constructing `ResourceModel` subclasses, the field is accessed via its alias `_links`. Using `**{"_links": ...}` is the safe pattern; do not use `_links=...` as a keyword argument (Python interprets leading-underscore attributes specially).
