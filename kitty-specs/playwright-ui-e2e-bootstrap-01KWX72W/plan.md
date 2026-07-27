# Implementation Plan: Bootstrap Playwright for dashboard UI regression coverage

**Branch**: `feat/playwright-ui-e2e-bootstrap` | **Spec**: [spec.md](./spec.md)
**Issues**: Closes #1008 (M6 of epic 1931)

## Summary

Make the aspirational "Playwright proof" rule real with a **one-time framework bootstrap + ONE representative regression-guard test**:
1. Add `pytest-playwright` as a dev/test dependency; browser (Chromium) installed/cached at test/CI time, never committed. Minimal Playwright config.
2. A hermetic fixture that materializes a **temp project root with synthetic mission(s)/WP(s)** carrying a known agent identity (`tool`/`model`/`profile`/`role`) + prompt, then boots the stdlib dashboard (`src/specify_cli/dashboard/server.py`) via `cli/commands/dashboard.py` on an ephemeral port, headless.
3. ONE e2e test: load the page → click a WP card → **assert the modal renders the agent identity + prompt** (the exact render the #970 bug dropped; the identity originates in `dashboard/scanner.py::_process_wp_file:786`). Non-vacuous: simulating the #970 regression makes it fail.
4. Wire a scoped **headless Playwright CI job** (browser cached) into the merge gate; point `CLAUDE.md`'s "Playwright proof" rule at the real test path + add `docs/development/ui-e2e.md`.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: `pytest-playwright` (new dev dep; Chromium via `playwright install`), `pytest`; drives the existing stdlib dashboard (`src/specify_cli/dashboard/` — `server.py`, `scanner.py`, `handlers/`, `static/`) via its **in-thread `start_dashboard(project_dir, port, background_process=False)`** seam (`server.py:110`) — NOT the CLI singleton `ensure_dashboard_running`. No new runtime deps.
**Storage**: files — the synthetic fixture writes a temp project root (missions/WPs) the scanner reads; no DB, no network.
**Testing**: `pytest tests/ui/` — one Playwright e2e (headless) + the synthetic-mission fixture; a non-vacuity check simulating the #970 regression.
**Target Platform**: Linux/macOS + CI (ubuntu-latest, Chromium headless).
**Project Type**: single (CLI/library with a bundled stdlib dashboard).
**Performance Goals**: bounded — ONE test + one cached browser install; a scoped CI job, not a full-suite dependency (NFR-001).
**Constraints**: deterministic/no-flake (headless, hermetic fixture, ephemeral port, explicit waits — no arbitrary sleeps, no retry-to-green; NFR-002); browser binaries not committed; `ruff` + `mypy --strict` clean, no new suppressions; version bump + CHANGELOG if `__init__.py` changes; one representative test only (C-001); no visual/screenshot/mobile (C-002).
**Scale/Scope**: `pyproject.toml` dev-dep + config, `tests/ui/` (test + fixture + conftest), a CI job, `CLAUDE.md` + `docs/development/ui-e2e.md` (inventory-registered). Small, cohesive.

## Charter Check
*GATE: passes.* Uses the canonical dashboard entrypoint (not a hand-rolled server); the test is ATDD/red-first (non-vacuous — the #970-regression simulation reds it, SC-003/FR-006); no new suppressions; bounded CI cost; a new docs page follows the page-inventory + `description`-frontmatter rules (registered at implement). "Never claim frontend works without Playwright proof" (CLAUDE.md) is finally enforceable.

## Project Structure

### Documentation (this mission)
```
kitty-specs/playwright-ui-e2e-bootstrap-01KWX72W/
├── plan.md · spec.md · tasks.md · tasks/ · contracts/
```

### Source Code (repository root)
```
pyproject.toml                                   # + pytest-playwright dev dep (respect test_pyproject_shape.py)
tests/ui/
├── conftest.py                                  # synthetic-mission temp-root fixture + dashboard boot (ephemeral port, headless)
└── test_dashboard_wp_modal.py                   # the ONE e2e: click WP card → assert modal agent identity + prompt
.github/workflows/                               # scoped headless Playwright job (browser cached) in the merge gate
CLAUDE.md                                        # "Playwright proof" rule → the real test path
docs/development/ui-e2e.md                       # how to boot the fixture + write another e2e (inventory-registered, description frontmatter)
```
**Structure Decision**: a self-contained `tests/ui/` (fixture + one test) driving the in-thread `start_dashboard` seam; the only production-surface touch is `pyproject.toml` (dev dep) + `CLAUDE.md`/docs. No dashboard source change (this mission adds the guard, not the app fix).

**Test-home decision** (post-plan finding): three dashboard-test homes already exist — `tests/dashboard/` (server-unit), `tests/test_dashboard/` (scanner/API unit), `tests/cross_cutting/dashboard/`. `tests/dashboard/test_duplicate_prefix_rendering.py` records "extend this file rather than creating a new one" — but that decision is scoped to the **HTTP-server rendering contract** (a Python-level concern), whereas this mission introduces a **browser-driven Playwright e2e** — a distinct KIND needing its own browser fixtures, page-object waits, and a scoped headless CI job. A dedicated **`tests/ui/`** home is therefore justified (not split-brain): it isolates the browser-runtime dependency + CI selector from the fast Python suites. Cross-reference it from the existing homes' module docstrings so the split is discoverable.

## Implementation Concern Map

### IC-01 — Playwright framework bootstrap + the kanban→modal e2e test + synthetic fixture
- **Purpose**: install/config `pytest-playwright`, build the hermetic synthetic-mission fixture (dict `agent: {tool, model}` + `agent_profile` + `role` frontmatter) + in-thread `start_dashboard` boot, and the ONE e2e asserting the modal renders the canonical DOM fields (`agent`/`model`/`agent_profile`/`role`) + prompt (non-vacuous vs the #970 regression).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-006, NFR-002, C-001, C-002.
- **Affected surfaces**: `pyproject.toml`, `tests/ui/conftest.py` (new), `tests/ui/test_dashboard_wp_modal.py` (new). Drives `dashboard/server.py::start_dashboard(background_process=False)` + reads `dashboard/scanner.py`'s emitted keys.
- **Sequencing/depends-on**: none.
- **Risks**: flake from timing (mitigate: explicit Playwright waits, ephemeral `find_free_port()`, headless); wrong frontmatter form → blank badges/vacuous pass (mitigate: dict `agent:{tool,model}` form the scanner decomposes, FR-003); wrong boot seam → detached-child leak / sibling-port kill under xdist (mitigate: in-thread `start_dashboard`, not the singleton); browser-binary size (mitigate: install/cache, not committed); the #970 bug may still be live (note it — this mission adds the guard; the app fix is separate/out-of-scope).

### IC-02 — CI wiring + CLAUDE.md/docs
- **Purpose**: run the e2e headless in CI (browser cached) as a scoped merge-gate job; point CLAUDE.md's "Playwright proof" rule at the real path + add the how-to-extend doc.
- **Relevant requirements**: FR-004, FR-005, NFR-001.
- **Affected surfaces**: `.github/workflows/` (job), `CLAUDE.md`, `docs/development/ui-e2e.md` (new; page-inventory + `description` frontmatter).
- **Sequencing/depends-on**: IC-01 (needs the runnable test).
- **Risks**: CI cost/slowness (mitigate: scoped job, cached browser, one test); docs-inventory gate (mitigate: regenerate inventory, add `description`).
