---
work_package_id: WP05
work_package_title: Dashboard Handlers
subtitle: Implement HTTP endpoint handlers using WP02 infrastructure
subtasks:
  - T040
  - T041
  - T042
  - T043
  - T044
  - T045
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
  - date: 2025-11-11
    status: updated
    by: claude
    notes: Removed infrastructure tasks (moved to WP02), focused on handler implementation only
---

# WP05: Dashboard Handlers

## Objective

Implement specialized endpoint handlers that extend the base DashboardHandler class provided by WP02, splitting the monolithic conditional routing into focused handler modules.

## Context

WP02 has extracted the dashboard infrastructure including the base `DashboardHandler` class, server initialization, and lifecycle management. This work package now focuses solely on implementing the specific endpoint handlers using that infrastructure.

**Agent Assignment**: Agent D (Days 4-5)

## Requirements from Specification

- Split handlers by endpoint type
- Maintain exact API compatibility
- Support subprocess spawning
- Each module under 200 lines

## Implementation Guidance

### T040: Extract API endpoints to dashboard/handlers/api.py

Extend the base `DashboardHandler` from WP02 to implement core API endpoints:
```python
from ..handlers.base import DashboardHandler

class APIHandler(DashboardHandler):
    """Handler for core API endpoints."""

    def handle_health(self):
        """Handle /api/health endpoint."""

    def handle_shutdown(self):
        """Handle /api/shutdown endpoint."""
        # Include _handle_shutdown() helper (line 2302)
        # Token validation logic
```
Target: ~80 lines

### T041: Extract feature endpoints to dashboard/handlers/features.py

Implement feature-related endpoints extending base handler:
```python
from ..handlers.base import DashboardHandler
from ..scanner import scan_all_features, scan_feature_kanban

class FeatureHandler(DashboardHandler):
    """Handler for feature-related endpoints."""

    def handle_features_list(self):
        """Handle /api/features - List all features."""

    def handle_kanban(self, feature_id):
        """Handle /api/kanban/{feature_id}."""

    def handle_artifact(self, feature_id, artifact):
        """Handle /api/artifact/{feature_id}/{artifact}."""

    def handle_contracts(self, feature_id):
        """Handle /api/contracts/{feature_id}."""

    def handle_research(self, feature_id):
        """Handle /api/research/{feature_id}."""
```
Target: ~150 lines

### T042: Extract static file serving to dashboard/handlers/static.py

Implement static file handler:
```python
from ..handlers.base import DashboardHandler

class StaticHandler(DashboardHandler):
    """Handler for static file serving."""

    def handle_static(self, path):
        """Handle /static/{path} endpoint."""
        # Path security checks
        # MIME type handling
```
Target: ~50 lines

### T043: Create main router in dashboard/handlers/router.py

Create the main routing logic that dispatches to appropriate handlers:
```python
from .api import APIHandler
from .features import FeatureHandler
from .static import StaticHandler

class DashboardRouter(DashboardHandler):
    """Main router that dispatches to specialized handlers."""

    def do_GET(self):
        """Route GET requests to appropriate handlers."""
        # Parse path
        # Dispatch to APIHandler, FeatureHandler, or StaticHandler

    def do_POST(self):
        """Route POST requests to appropriate handlers."""
```
Target: ~100 lines

### T044-T045: Write handler tests

**T044**: HTTP endpoint tests
- `tests/test_dashboard/test_handlers/test_api.py` - Test API endpoints
- `tests/test_dashboard/test_handlers/test_features.py` - Test feature endpoints
- `tests/test_dashboard/test_handlers/test_static.py` - Test static file serving
- Mock HTTP requests and verify response formats

**T045**: Integration tests
- `tests/test_dashboard/test_handlers/test_router.py` - Test routing logic
- Test that all endpoints are reachable
- Verify no API breaking changes
- Ensure subprocess spawning still works

## Testing Strategy

1. **Unit tests**: Test each handler independently
2. **Integration tests**: Test full HTTP flow
3. **Subprocess tests**: Verify subprocess imports work
4. **API tests**: Ensure all endpoints respond correctly

## Definition of Done

- [ ] API handler implemented in dashboard/handlers/api.py (<100 lines)
- [ ] Feature handler implemented in dashboard/handlers/features.py (<150 lines)
- [ ] Static handler implemented in dashboard/handlers/static.py (<50 lines)
- [ ] Router implemented in dashboard/handlers/router.py (<100 lines)
- [ ] All handlers extend base DashboardHandler from WP02
- [ ] All endpoints work identically to original
- [ ] Subprocess spawning still works
- [ ] All handler tests written and passing
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

- WP02: Requires complete dashboard infrastructure including:
  - Base DashboardHandler class (dashboard/handlers/base.py)
  - Server functions (dashboard/server.py)
  - Lifecycle management (dashboard/lifecycle.py)
  - Scanner and diagnostics modules
  - Static assets extracted
  - Dashboard package properly initialized with exports

## Dependents

- WP08: Integration will wire everything together