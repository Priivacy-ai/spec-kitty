---
work_package_id: WP02
title: Dashboard Glossary Tile and Full-Page Browser
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-025
- FR-026
- FR-027
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/dashboard/handlers/glossary.py
- src/specify_cli/dashboard/api_types.py
- src/specify_cli/dashboard/handlers/router.py
- src/specify_cli/dashboard/templates/glossary.html
- src/specify_cli/dashboard/templates/index.html
- tests/specify_cli/dashboard/test_glossary_handler.py
tags: []
---

# WP02 — Dashboard Glossary Tile and Full-Page Browser

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP02 --agent <name>`

## Objective

Deliver two dashboard surfaces:

1. **Dashboard glossary tile** on `index.html`: summary stat pills (total / active / draft / deprecated / high-severity drift) with a link to `/glossary`.
2. **Full-page glossary browser** at `/glossary`: the approved design mockup made dynamic — data fetched live from `/api/glossary-terms`.

**Critical**: The visual design is approved and locked in `src/specify_cli/dashboard/templates/glossary.html`. Do not deviate from the CSS design system, card anatomy, filter UX, alpha navigation, or confidence bar. See `designs/README.md` for the exact spec.

## Context

### Dashboard architecture

The dashboard is a Python `http.server`-based server defined in `src/specify_cli/dashboard/`. The key files:

- `handlers/router.py` — `DashboardRouter` inherits from `APIHandler`, `FeatureHandler`, `StaticHandler` via multiple inheritance. Add new handlers to the MRO here.
- `handlers/api.py` — `APIHandler` pattern to follow for new handlers
- `api_types.py` — TypedDict definitions for all JSON response shapes
- `templates/index.html` — main dashboard page
- `templates/glossary.html` — the glossary browser (currently static mockup with hardcoded data)

### Pattern to follow

Look at `APIHandler.handle_health()` and `FeatureHandler.handle_features_list()` as the models. A handler method: (1) calls `self.send_response(200)`, (2) sets headers, (3) calls `self.end_headers()`, (4) writes JSON or HTML bytes.

### Existing glossary store

`GlossaryStore` lives in `src/specify_cli/glossary/store.py`. Instantiate with `GlossaryStore(repo_root)`. The key method to discover is how to list all terms with surface, definition, status, and confidence — inspect `store.py` and use whatever list/query method exists. Terms have a `status` field (`"active"`, `"draft"`, `"deprecated"`) and a `confidence` float.

---

## Subtask T007 — TypedDicts in `api_types.py`

**File**: `src/specify_cli/dashboard/api_types.py`

**Add**:
```python
class GlossaryTermRecord(TypedDict):
    surface: str
    definition: str
    status: str          # "active" | "draft" | "deprecated"
    confidence: float    # 0.0–1.0

class GlossaryHealthResponse(TypedDict, total=False):
    total_terms: int
    active_count: int
    draft_count: int
    deprecated_count: int
    high_severity_drift_count: int
    orphaned_term_count: int
    entity_pages_generated: bool
    entity_pages_path: str | None
    last_conflict_at: str | None
```

Add both to `__all__`.

---

## Subtask T008 — `handle_glossary_health()`

**File**: `src/specify_cli/dashboard/handlers/glossary.py` (new)

**Purpose**: Serve `GET /api/glossary-health` with a `GlossaryHealthResponse`.

**Implementation**:
```python
class GlossaryHandler(DashboardHandler):
    def handle_glossary_health(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            project_dir = Path(self.project_dir)
            store = GlossaryStore(project_dir)
            terms = store.list_all_terms()  # or equivalent — check store.py API

            active = [t for t in terms if t.status == "active"]
            draft  = [t for t in terms if t.status == "draft"]
            depr   = [t for t in terms if t.status == "deprecated"]

            # High-severity drift count: scan _cli.events.jsonl
            event_log = project_dir / ".kittify" / "events" / "glossary" / "_cli.events.jsonl"
            high_count = 0
            last_at: str | None = None
            if event_log.exists():
                for line in event_log.read_text().splitlines():
                    try:
                        ev = json.loads(line)
                        if ev.get("event_type") == "semantic_check_evaluated" and ev.get("severity") in {"high", "critical"}:
                            high_count += 1
                            last_at = ev.get("checked_at")
                    except json.JSONDecodeError:
                        pass

            entity_pages_dir = project_dir / ".kittify" / "charter" / "compiled" / "glossary"
            response: GlossaryHealthResponse = {
                "total_terms": len(terms),
                "active_count": len(active),
                "draft_count": len(draft),
                "deprecated_count": len(depr),
                "high_severity_drift_count": high_count,
                "orphaned_term_count": 0,  # DRG query deferred; 0 is safe default
                "entity_pages_generated": entity_pages_dir.exists() and any(entity_pages_dir.iterdir()),
                "entity_pages_path": str(entity_pages_dir) if entity_pages_dir.exists() else None,
                "last_conflict_at": last_at,
            }
        except Exception as exc:
            logger.exception("glossary health error: %s", exc)
            response = {
                "total_terms": 0, "active_count": 0, "draft_count": 0,
                "deprecated_count": 0, "high_severity_drift_count": 0,
                "orphaned_term_count": 0, "entity_pages_generated": False,
                "entity_pages_path": None, "last_conflict_at": None,
            }

        self.wfile.write(json.dumps(response).encode())
```

---

## Subtask T009 — `handle_glossary_terms()`

**File**: `src/specify_cli/dashboard/handlers/glossary.py`

**Purpose**: Serve `GET /api/glossary-terms` with a list of `GlossaryTermRecord`.

```python
def handle_glossary_terms(self) -> None:
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.send_header("Cache-Control", "no-cache")
    self.end_headers()

    try:
        store = GlossaryStore(Path(self.project_dir))
        terms = store.list_all_terms()
        records: list[GlossaryTermRecord] = [
            {
                "surface": t.surface,
                "definition": t.definition or "",
                "status": t.status or "draft",
                "confidence": float(t.confidence or 0.0),
            }
            for t in terms
        ]
    except Exception as exc:
        logger.exception("glossary terms error: %s", exc)
        records = []

    self.wfile.write(json.dumps(records).encode())
```

Inspect `GlossaryStore` to find the actual method name and field names for `surface`, `definition`, `status`, and `confidence`. Adapt accordingly.

---

## Subtask T010 — `handle_glossary_page()`

**File**: `src/specify_cli/dashboard/handlers/glossary.py`

**Purpose**: Serve the `glossary.html` template at `GET /glossary`.

```python
_GLOSSARY_HTML_PATH = Path(__file__).resolve().parents[2] / "templates" / "glossary.html"
_GLOSSARY_HTML_BYTES: bytes = _GLOSSARY_HTML_PATH.read_bytes()

def handle_glossary_page(self) -> None:
    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()
    self.wfile.write(_GLOSSARY_HTML_BYTES)
```

Cache the bytes at module load time (same pattern as `get_dashboard_html_bytes()` in `templates/__init__.py`).

---

## Subtask T011 — Route Registration in `router.py`

**File**: `src/specify_cli/dashboard/handlers/router.py`

**Purpose**: Register the three new glossary routes and add `GlossaryHandler` to `DashboardRouter`.

**Steps**:
1. Import: `from .glossary import GlossaryHandler`
2. Add `GlossaryHandler` to the MRO of `DashboardRouter`:
   ```python
   class DashboardRouter(APIHandler, FeatureHandler, GlossaryHandler, StaticHandler):
   ```
3. In `do_GET`, add before the existing 404 fallback:
   ```python
   if path == '/glossary':
       self.handle_glossary_page()
       return

   if path == '/api/glossary-health':
       self.handle_glossary_health()
       return

   if path == '/api/glossary-terms':
       self.handle_glossary_terms()
       return
   ```

---

## Subtask T012 — Make `glossary.html` Dynamic

**File**: `src/specify_cli/dashboard/templates/glossary.html`

**Purpose**: Replace the hardcoded `const TERMS = [...]` block with a live fetch from `/api/glossary-terms`.

**Steps**:
1. Remove the `const TERMS = [...]` declaration (the entire array literal).
2. Replace with:
```javascript
let TERMS = [];

async function loadTerms() {
  try {
    const resp = await fetch('/api/glossary-terms');
    if (!resp.ok) throw new Error('fetch failed');
    TERMS = await resp.json();
  } catch (e) {
    console.warn('glossary: could not load terms', e);
    TERMS = [];
  }
  updateStats();
  buildAlphaNav();
  render();
}

function updateStats() {
  const total    = TERMS.length;
  const active   = TERMS.filter(t => t.status === 'active').length;
  const draft    = TERMS.filter(t => t.status === 'draft').length;
  const depr     = TERMS.filter(t => t.status === 'deprecated').length;
  document.getElementById('header-stats').innerHTML = [
    `<span class="stat-pill total">◉ ${total} total</span>`,
    `<span class="stat-pill active">● ${active} active</span>`,
    `<span class="stat-pill draft">● ${draft} draft</span>`,
    `<span class="stat-pill depr">● ${depr} deprecated</span>`,
  ].join('');
}
```

3. Move the `buildAlphaNav()` and initial `render()` calls into `loadTerms()` (they must run after TERMS is populated).

4. Replace the `document.addEventListener('DOMContentLoaded', ...)` block (which currently calls `render()` immediately) with:
```javascript
document.addEventListener('DOMContentLoaded', loadTerms);
```

5. Keep all existing CSS, HTML structure, filter tab wiring, search wiring, and card rendering logic unchanged.

---

## Subtask T013 — Glossary Tile in `index.html`

**File**: `src/specify_cli/dashboard/templates/index.html`

**Purpose**: Add a glossary health summary tile to the main dashboard page.

Find the existing tile/card grid in `index.html`. Add a tile that:
1. Shows the 4 status counts (total / active / draft / deprecated) + high-severity drift count
2. Links to `/glossary` when clicked

The tile fetches from `/api/glossary-health` on page load. Pattern to follow: look at how other dashboard tiles fetch from their API endpoints and render.

Minimal tile HTML (adapt to match existing tile styling exactly):
```html
<div class="tile" id="glossary-tile" onclick="window.location='/glossary'" style="cursor:pointer">
  <div class="tile-header">Glossary</div>
  <div class="tile-body" id="glossary-tile-body">Loading…</div>
</div>
```

JS to populate:
```javascript
fetch('/api/glossary-health')
  .then(r => r.json())
  .then(d => {
    document.getElementById('glossary-tile-body').innerHTML =
      `<div>${d.total_terms} terms · ${d.active_count} active · ${d.high_severity_drift_count} drift</div>`;
  })
  .catch(() => {
    document.getElementById('glossary-tile-body').textContent = 'unavailable';
  });
```

Match the tile markup style of adjacent tiles in `index.html` exactly — do not introduce new CSS classes.

---

## Subtask T014 — Tests

**File**: `tests/specify_cli/dashboard/test_glossary_handler.py` (new)

**Test scenarios**:

1. **`/api/glossary-health` shape** — mock `GlossaryStore` returning 3 terms (2 active, 1 draft); assert response has `total_terms: 3`, `active_count: 2`, `draft_count: 1`.
2. **`/api/glossary-health` on empty glossary** — mock store returns `[]`; assert `total_terms: 0`, no exception.
3. **`/api/glossary-terms` shape** — mock store returns 2 terms; assert response is a list of 2 `GlossaryTermRecord`-shaped dicts.
4. **`/api/glossary-terms` on store error** — store raises exception; assert response is `[]`.
5. **`GET /glossary` returns HTML** — assert response status 200, `Content-type: text/html`.
6. **High-severity event count** — mock event log with 2 high-severity events; assert `high_severity_drift_count: 2`.
7. **Missing event log** — assert `high_severity_drift_count: 0` when log doesn't exist.

Use the existing dashboard test patterns (look at `test_diagnostics.py` or similar for how to instantiate a handler in tests).

**Run**: `cd src && pytest tests/specify_cli/dashboard/test_glossary_handler.py -v`

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP02 --agent <name>`.

---

## Definition of Done

- [ ] `GET /api/glossary-health` returns a valid `GlossaryHealthResponse` JSON object
- [ ] `GET /api/glossary-terms` returns a list of `GlossaryTermRecord` objects from the live glossary store
- [ ] `GET /glossary` returns 200 with the glossary browser HTML
- [ ] `/glossary` loads in a browser with dynamic data — search, filter tabs, alpha nav, and card rendering all functional
- [ ] Dark mode renders correctly (`@media (prefers-color-scheme: dark)` in the mockup CSS is preserved)
- [ ] Dashboard home page shows a glossary tile with counts linking to `/glossary`
- [ ] All 7 test scenarios pass: `pytest tests/specify_cli/dashboard/test_glossary_handler.py`
- [ ] `ruff check src/specify_cli/dashboard/handlers/glossary.py` passes

---

## Reviewer Guidance

1. **Visual check is mandatory**: Load `/glossary` in a browser. Verify (a) search filters live, (b) status tabs work, (c) alpha nav jumps scroll to letter sections, (d) confidence bar renders, (e) dark mode works. Do not approve without this check.
2. Confirm `glossary.html` has no remaining hardcoded `TERMS` data — the array literal must be gone.
3. Confirm `GlossaryHandler` is in the MRO before `StaticHandler` so it doesn't get shadowed.
4. Confirm the tile in `index.html` uses existing tile CSS classes — no new styles introduced.
5. `orphaned_term_count` is allowed to return 0 (DRG query deferred) — this is intentional and documented.
