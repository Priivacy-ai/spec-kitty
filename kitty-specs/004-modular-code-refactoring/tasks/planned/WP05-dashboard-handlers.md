---
work_package_id: WP05
work_package_title: Dashboard Handlers
subtitle: HTTP request handling and server management
subtasks:
  - T040
  - T041
  - T042
  - T043
  - T044
  - T045
  - T046
  - T047
  - T048
  - T049
phases: story-based
priority: P3
lane: planned
tags:
  - dashboard
  - handlers
  - parallel
  - agent-d
history:
  - date: 2025-11-11
    status: created
    by: spec-kitty.tasks
---

# WP05: Dashboard Handlers

## Objective

Refactor the monolithic DashboardHandler class into specialized endpoint handlers and extract server management functions.

## Context

The `DashboardHandler` class in dashboard.py is 474 lines with a large conditional chain in `do_GET()`. This work package splits it into focused handler modules.

**Agent Assignment**: Agent D (Days 4-5)

## Requirements from Specification

- Split handlers by endpoint type
- Maintain exact API compatibility
- Support subprocess spawning
- Each module under 200 lines

## Implementation Guidance

### T040: Create dashboard/handlers/base.py

Extract base handler functionality:
- Base class extending BaseHTTPRequestHandler
- `_send_json()` helper (line 2294)
- `log_message()` override (line 2290)
- Common error handling patterns
- ~100 lines total

### T041: Extract API endpoints to dashboard/handlers/api.py

Extract core API endpoints:
- `/api/health` endpoint
- `/api/shutdown` endpoint
- `_handle_shutdown()` helper (line 2302)
- Token validation logic
- ~80 lines

### T042: Extract feature endpoints to dashboard/handlers/features.py

Extract feature-related endpoints:
- `/api/features` - List all features
- `/api/kanban/{feature_id}` - Kanban board
- `/api/artifact/{feature_id}/{artifact}` - Get artifacts
- `/api/contracts/{feature_id}` - Contract files
- `/api/research/{feature_id}` - Research artifacts
- ~150 lines

### T043: Extract static file serving to dashboard/handlers/static.py

Extract static file handling:
- `/static/{path}` endpoint
- Path security checks
- MIME type handling
- ~50 lines

### T044-T045: Extract server functions to dashboard/server.py

**T044**: Extract `start_dashboard()` to `dashboard/server.py`
- Lines 2760-2829 from dashboard.py
- Server initialization logic
- Background vs threaded modes

**T045**: Extract `find_free_port()` to `dashboard/server.py`
- Lines 57-91 from dashboard.py
- Port discovery with dual verification

### T046: Extract lifecycle to dashboard/lifecycle.py

Extract dashboard lifecycle management:
- `_parse_dashboard_file()` (lines 2832-2856)
- `_write_dashboard_file()` (lines 2859-2865)
- `_check_dashboard_health()` (lines 2868-2907)
- `ensure_dashboard_running()` (lines 2910-2948)
- `stop_dashboard()` (lines 2951-3030)

### T047: Update dashboard/__init__.py

Create public API:
```python
"""Dashboard package for spec-kitty."""

from .lifecycle import (
    ensure_dashboard_running,
    stop_dashboard,
    get_dashboard_status,
)
from .server import start_dashboard

__all__ = [
    'ensure_dashboard_running',
    'stop_dashboard',
    'get_dashboard_status',
    'start_dashboard',
]
```

### T048-T049: Write tests

**T048**: HTTP endpoint tests
- Mock HTTP requests
- Verify response formats
- Test error handling

**T049**: Subprocess import tests
- Test imports work in subprocess context
- Use try/except pattern

## Testing Strategy

1. **Unit tests**: Test each handler independently
2. **Integration tests**: Test full HTTP flow
3. **Subprocess tests**: Verify subprocess imports work
4. **API tests**: Ensure all endpoints respond correctly

## Definition of Done

- [ ] Handlers split into focused modules
- [ ] Each module under 200 lines
- [ ] All endpoints work identically
- [ ] Subprocess spawning still works
- [ ] Tests written and passing
- [ ] No API breaking changes

## Risks and Mitigations

**Risk**: HTTP routing must remain compatible
**Mitigation**: Test all endpoints thoroughly

**Risk**: Subprocess context imports
**Mitigation**: Use try/except import pattern

## Review Guidance

1. Verify all endpoints respond correctly
2. Check subprocess spawning works
3. Ensure no API changes
4. Confirm error handling preserved

## Dependencies

- WP02: Needs dashboard infrastructure modules

## Dependents

- WP08: Integration will wire everything together