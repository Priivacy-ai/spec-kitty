---
work_package_id: WP05
title: Dashboard Decay Watch Tile
dependencies:
- WP02
- WP07
requirement_refs:
- FR-023
- FR-024
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/dashboard/handlers/lint.py
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/dashboard/handlers/lint.py
- tests/specify_cli/dashboard/test_lint_tile_handler.py
tags: []
---

# WP05 — Dashboard Decay Watch Tile

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP05 --agent <name>`

**⚠ Dependencies**: This WP starts after both WP02 (dashboard infrastructure in place) and WP07 (LintEngine writes `lint-report.json`) are approved and merged into `main`. The execution worktree will have both WPs' changes available.

## Objective

Add a `/api/charter-lint` GET endpoint and a "Decay Watch" tile on the dashboard home page. The tile shows the finding counts (by category) from the last `spec-kitty charter lint` run. If no run has happened yet, the tile displays a prompt to run the command.

## Context

### `lint-report.json` format (written by WP07's `LintEngine`)

```json
{
  "findings": [
    {
      "category": "orphan",
      "type": "adr",
      "id": "ADR-7",
      "severity": "medium",
      "message": "...",
      "feature_id": null,
      "remediation_hint": "..."
    }
  ],
  "scanned_at": "2026-04-23T05:00:00Z",
  "feature_scope": null,
  "duration_seconds": 1.24,
  "drg_node_count": 312,
  "drg_edge_count": 1048
}
```

Path: `.kittify/lint-report.json`

### File overlap note

`api_types.py`, `router.py`, and `index.html` are also modified by WP02. This overlap is safe because WP05 depends on WP02 — by the time WP05's worktree is created, WP02's changes are already on `main`. WP05 adds new items to these files; it does not conflict with WP02's additions.

---

## Subtask T025 — `DecayWatchTileResponse` TypedDict

**File**: `src/specify_cli/dashboard/api_types.py`

**Add**:
```python
class DecayWatchTileResponse(TypedDict, total=False):
    has_data: bool
    scanned_at: str | None
    orphan_count: int
    contradiction_count: int
    staleness_count: int
    reference_integrity_count: int
    high_severity_count: int
    total_count: int
    feature_scope: str | None
    duration_seconds: float | None
```

Add to `__all__`.

---

## Subtask T026 — `LintTileHandler.handle_charter_lint()`

**File**: `src/specify_cli/dashboard/handlers/lint.py` (new)

```python
"""Decay watch tile handler — reads .kittify/lint-report.json."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..api_types import DecayWatchTileResponse
from .base import DashboardHandler

logger = logging.getLogger(__name__)


class LintTileHandler(DashboardHandler):

    def handle_charter_lint(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            report_path = Path(self.project_dir) / ".kittify" / "lint-report.json"

            if not report_path.exists():
                response: DecayWatchTileResponse = {
                    "has_data": False,
                    "scanned_at": None,
                    "orphan_count": 0,
                    "contradiction_count": 0,
                    "staleness_count": 0,
                    "reference_integrity_count": 0,
                    "high_severity_count": 0,
                    "total_count": 0,
                    "feature_scope": None,
                    "duration_seconds": None,
                }
            else:
                data = json.loads(report_path.read_text())
                findings = data.get("findings", [])
                response = {
                    "has_data": True,
                    "scanned_at": data.get("scanned_at"),
                    "orphan_count": sum(1 for f in findings if f.get("category") == "orphan"),
                    "contradiction_count": sum(1 for f in findings if f.get("category") == "contradiction"),
                    "staleness_count": sum(1 for f in findings if f.get("category") == "staleness"),
                    "reference_integrity_count": sum(1 for f in findings if f.get("category") == "reference_integrity"),
                    "high_severity_count": sum(1 for f in findings if f.get("severity") in {"high", "critical"}),
                    "total_count": len(findings),
                    "feature_scope": data.get("feature_scope"),
                    "duration_seconds": data.get("duration_seconds"),
                }
        except Exception as exc:
            logger.exception("lint tile error: %s", exc)
            response = {
                "has_data": False, "scanned_at": None,
                "orphan_count": 0, "contradiction_count": 0,
                "staleness_count": 0, "reference_integrity_count": 0,
                "high_severity_count": 0, "total_count": 0,
                "feature_scope": None, "duration_seconds": None,
            }

        self.wfile.write(json.dumps(response).encode())
```

---

## Subtask T027 — Route Registration in `router.py`

**File**: `src/specify_cli/dashboard/handlers/router.py`

**Steps**:
1. Import: `from .lint import LintTileHandler`
2. Add `LintTileHandler` to the `DashboardRouter` MRO:
   ```python
   class DashboardRouter(APIHandler, FeatureHandler, GlossaryHandler, LintTileHandler, StaticHandler):
   ```
3. In `do_GET`, add:
   ```python
   if path == '/api/charter-lint':
       self.handle_charter_lint()
       return
   ```

---

## Subtask T028 — Decay Watch Tile in `index.html` + Tests

**File**: `src/specify_cli/dashboard/templates/index.html` and `tests/specify_cli/dashboard/test_lint_tile_handler.py`

**Tile HTML** (add adjacent to the glossary tile from WP02):
```html
<div class="tile" id="lint-tile">
  <div class="tile-header">Decay Watch</div>
  <div class="tile-body" id="lint-tile-body">Loading…</div>
</div>
```

**JS**:
```javascript
fetch('/api/charter-lint')
  .then(r => r.json())
  .then(d => {
    if (!d.has_data) {
      document.getElementById('lint-tile-body').textContent =
        'No lint data — run `spec-kitty charter lint`';
      return;
    }
    document.getElementById('lint-tile-body').innerHTML =
      `<div>${d.orphan_count} orphans · ${d.contradiction_count} contradictions · ` +
      `${d.staleness_count} stale · ${d.reference_integrity_count} broken refs</div>` +
      `<div style="color:var(--text-dim);font-size:0.8em">${d.total_count} total findings</div>`;
  })
  .catch(() => {
    document.getElementById('lint-tile-body').textContent = 'unavailable';
  });
```

**Tests** (`tests/specify_cli/dashboard/test_lint_tile_handler.py`):

1. **Report exists** — write a fixture `lint-report.json` with 2 orphan + 1 contradiction findings; call handler; assert `has_data: true`, `orphan_count: 2`, `contradiction_count: 1`, `total_count: 3`.
2. **Report missing** — no `lint-report.json`; assert `has_data: false`, all counts 0.
3. **Malformed report** — write corrupt JSON; assert `has_data: false`, no exception raised.
4. **High-severity count** — fixture with 1 high + 1 medium finding; assert `high_severity_count: 1`.

---

## Branch Strategy

- **Planning base branch**: `main` (post WP02 + WP07 merge)
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP05 --agent <name>`. Starts from merged state after WP02 and WP07 are approved.

---

## Definition of Done

- [ ] `GET /api/charter-lint` returns `DecayWatchTileResponse` JSON
- [ ] `has_data: false` when `lint-report.json` does not exist
- [ ] Correct category counts parsed from report when it exists
- [ ] Dashboard home shows "Decay Watch" tile with count summary or "no data" prompt
- [ ] All 4 test scenarios pass: `pytest tests/specify_cli/dashboard/test_lint_tile_handler.py`
- [ ] `ruff check src/specify_cli/dashboard/handlers/lint.py` passes

---

## Reviewer Guidance

1. Confirm the `has_data: false` path works cleanly — this is the state all users will see before their first lint run.
2. Confirm `handle_charter_lint()` is wrapped in `try/except` — a corrupt `lint-report.json` must not crash the dashboard.
3. Confirm the tile in `index.html` matches the styling of the glossary tile added by WP02 (use the same tile CSS classes).
4. The tile text "N orphans · N contradictions · N stale · N broken refs" must be readable at a glance.
