# Mission Specification: Bootstrap Playwright for dashboard UI regression coverage

**Status**: Draft
**Issues**: Closes [#1008](https://github.com/Priivacy-ai/spec-kitty/issues/1008) (M6 of epic 1931)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor/reviewer changing the dashboard UI whose click-through regression cannot be caught by any automated layer today.

**Grounding** (verified against the code):
- Playwright is **not installed** — no `pytest-playwright` dependency, no Playwright config, no end-to-end UI tests. `PWHEADLESS=1` is set at `tests/conftest.py:168` (and in `ci-quality.yml`) purely as a defensive guard to stop browser windows in subprocess tests; **no runtime code reads it to drive a browser**.
- `CLAUDE.md` carries an **aspirational** rule — "Never claim the frontend works without Playwright proof" — that the project cannot actually enforce, creating a false sense of safety.
- This drift shipped a real bug (PR #970): the dashboard's WP-card click opened a modal missing the **agent identity**. The dashboard is a **stdlib-HTTP app** (`src/specify_cli/dashboard/server.py`, booted by `cli/commands/dashboard.py`) whose `scanner.py::_process_wp_file` (`:786`) extracts `agent_raw.get("tool"/"model"/…)` and surfaces it via `/api/kanban`; the click-through modal must render that identity. **338 backend tests + all architectural tests passed** and the bug still shipped, because no layer exercised the click-through *render*.

This mission is a **one-time framework bootstrap + ONE representative regression-guard test** that makes the "Playwright proof" rule real, so the exact #970 class of bug reds a check.

### User Story 1 - The kanban→modal click-through is regression-guarded (Priority: P1)
As a reviewer, I want one end-to-end test that boots the dashboard, clicks a WP card, and asserts the modal renders the agent identity + prompt — so a future change that breaks that flow (the #970 bug) fails CI instead of shipping green.

**Independent test**: run the e2e test against the current dashboard → it passes; simulate the #970 regression (modal stops rendering agent identity) → the test fails cleanly.

### User Story 2 - A future contributor can copy the test as a template (Priority: P2)
As a contributor adding a new dashboard panel, I want a documented, runnable e2e test I can copy — so UI coverage grows instead of staying aspirational.

### Edge Cases
- Browser binaries are large + environment-specific → managed via the Playwright install step / fixture cache, **NOT committed** to the repo.
- The dashboard boots on a real port → the test uses a **temp project root with synthetic missions** (deterministic fixture), headless, on an ephemeral port — no dependency on the developer's real `~/.spec-kitty`.
- CI runners lack browsers by default → the CI job installs the browser (cached) before the test; the job is scoped so it doesn't slow every unrelated PR.
- The test must assert **content**, not just HTTP 200 — a 200 with an empty modal is the #970 bug (per CLAUDE.md: "API responses don't guarantee UI works").

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Install + configure `pytest-playwright` | As a maintainer, I want `pytest-playwright` added as a **dev/test dependency** with browser binaries managed by the install step / fixture cache (never committed), and the minimal Playwright config, so `pytest tests/ui/` can drive a real headless browser. Any `pyproject.toml`/`__init__.py` change respects the repo's version-bump + CHANGELOG rule + shared-package-boundary gates. | High | Open |
| FR-002 | One representative kanban→modal e2e test | As a reviewer, I want ONE test that: (1) boots the dashboard **in-thread via `start_dashboard(project_dir, port, background_process=False)`** (`dashboard/server.py:110` — the hermetic seam that dies with the pytest process; NOT the CLI singleton `ensure_dashboard_running`, which detaches a PID'd child + kills siblings on the shared port range) against a temp project root with synthetic missions; (2) loads the page; (3) asserts the modal (`#prompt-modal`) is **hidden BEFORE the click**; (4) clicks a WP card; (5) **asserts — SCOPED to the modal container (`#prompt-modal` / `.agent-identity-section` / `#modal-prompt-meta`), NEVER page-global and NEVER via `.card .badge`** — that the modal renders the canonical fields `agent`, `model`, `agent_profile`, `role` (per `api_types.py` / `dashboard.js`, NOT `tool`/`profile`) + the prompt (`prompt_markdown`). ⚠️ `agent`/`agent_profile`/`role` ALSO render as **card badges before any click** (`dashboard.js:514-516`) — only `model` is modal-exclusive — so a page-global assertion is fakeable (passes while the modal drops the identity, the #970 class). Headless; deterministic; ephemeral `find_free_port()`. | High | Open |
| FR-003 | Deterministic synthetic-mission fixture | As a maintainer, I want a fixture that materializes a temp project root with synthetic mission(s)/WP(s) whose frontmatter uses the **dict `agent: {tool, model}` + `agent_profile` + `role`** form the scanner reads (`scanner.py::_process_wp_file:851-869`) — NOT the dominant colon-string `agent: 'tool:model:profile:role'`, which the scanner does NOT decompose (it assigns the whole blob to `agent` + leaves `model` blank) → so the modal badges render populated and the assertion is exact + hermetic (no real state, no network). | High | Open |
| FR-004 | CI wiring (scoped, headless) | As a maintainer, I want the e2e test wired into CI (a Playwright job in `ci-quality.yml` or a new `ui-e2e.yml`) running **headless** with the browser installed/cached, gated so it participates in the merge decision but doesn't bloat every unrelated shard. | High | Open |
| FR-005 | Make the CLAUDE.md rule real + document how to extend | As a future agent, I want `CLAUDE.md`'s "Playwright proof" guidance to **link to the runnable test path** (not an aspiration), plus a short doc (`docs/development/ui-e2e.md`) explaining how to boot the fixture + write another e2e test. The doc is registered in the page inventory + carries `description` frontmatter. | Medium | Open |
| FR-006 | Non-vacuous regression proof (RENDER-path) | As a reviewer, I want proof the test bites the **modal render**: temporarily mutate the render path (delete the identity block in `showPromptModal`, `dashboard.js:628-631`) with the **fixture data left INTACT** → the modal-scoped assertion **fails cleanly**; revert → green. A throwaway demonstration (pasted as evidence, NOT committed — line C-002's "no dashboard source change" governs committed source only). ⚠️ Do NOT prove via blanking the scanner/fixture data: that reds the always-visible card badge too and proves nothing about the modal render. (The modal does NO separate detail fetch — it reuses the card's `task` object — so a "detail-not-fetched" regression mode cannot occur; not a valid mode.) | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Bounded CI cost | ONE representative test + one browser install (cached). The e2e job runs in bounded wall-clock; it is not a full-suite dependency of every PR shard. | Performance | High | Open |
| NFR-002 | Deterministic, no flake | Headless, hermetic synthetic fixture, ephemeral port, explicit waits (no arbitrary sleeps) — the test is stable enough to gate merges (no retry-to-green). | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | One representative test only | Scope is the framework bootstrap + ONE kanban→modal test. Comprehensive dashboard coverage is iterative follow-up (out of scope). | Product | High | Open |
| C-002 | No visual/screenshot regression, no mobile | Content assertions only; no pixel/screenshot diffing; no responsive variants. | Product | High | Open |
| C-003 | Browser binaries not committed; no new suppressions | Binaries via install/cache only. `ruff` + `mypy --strict` clean; no new `# noqa`/`# type: ignore`. Version bump + CHANGELOG if `__init__.py` changes. | Technical | High | Open |

### Key Entities
- **`pyproject.toml`** — `pytest-playwright` dev dependency (respecting `test_pyproject_shape.py` / shared-package-boundary gates).
- **`tests/ui/`** (new) — the e2e test + its synthetic-mission fixture + conftest.
- **`dashboard/server.py::start_dashboard(..., background_process=False)`** (`:110`) — the hermetic in-thread boot seam the test drives (NOT `cli/commands/dashboard.py`'s `ensure_dashboard_running` singleton). **`dashboard/scanner.py::_process_wp_file`** (`:786`, `:851-869`) reads `agent: {tool, model}` + `agent_profile` + `role` from WP frontmatter and emits DOM keys `agent`/`model`/`agent_profile`/`role` (typed in `api_types.py`, rendered by `dashboard.js`) via `/api/kanban` — the exact render the modal must show (the #970 surface).
- **`.github/workflows/`** — the Playwright CI job (headless, browser-cached).
- **`CLAUDE.md`** + **`docs/development/ui-e2e.md`** (new) — the "Playwright proof" rule pointed at the real test path + the how-to-extend doc (page-inventory registered, `description` frontmatter).

## Success Criteria *(mandatory)*
- **SC-001**: `pytest tests/ui/` runs the representative e2e test locally + in CI (headless) against a temp synthetic project root.
- **SC-002**: The test asserts `#prompt-modal` is hidden BEFORE the click, then — **scoped to the modal container** (not page-global, not `.card .badge`) — that the modal renders `agent`/`model`/`agent_profile`/`role` + `prompt_markdown`, populated.
- **SC-003**: Mutating the modal RENDER path (`showPromptModal` identity block) with the fixture data intact makes the modal-scoped test **fail cleanly** (FR-006 — render-path non-vacuity); a scanner/data-blank is NOT an acceptable proof (it reds the card, not the modal).
- **SC-004**: The Playwright CI job runs headless with a cached browser + participates in the merge gate; CI cost stays bounded (NFR-001).
- **SC-005**: `CLAUDE.md`'s "Playwright proof" rule links a runnable test path; `docs/development/ui-e2e.md` exists (inventory-registered, `description` frontmatter) explaining how to add more.
- **SC-006**: `ruff` + `mypy --strict` clean; browser binaries not committed; version bump + CHANGELOG if `__init__.py` changes.

## Out of Scope
- Comprehensive UI coverage for every dashboard surface (iterative follow-up).
- Visual/screenshot regression testing (separate concern).
- Mobile / responsive variants.
- Fixing the underlying #970 API bug itself if still present — this mission adds the guard; the API fix is its own tracked change (note it if the test reds on current code).

## Assumptions
- The dashboard's `start_dashboard(project_dir, port, background_process=False)` (`server.py:110`) boots the real app **in-thread** against a given project root (the hermetic test seam — dies with pytest, no PID file, no sibling-kill); the test drives that, NOT the CLI singleton (`ensure_dashboard_running`) and not a bespoke harness.
- `pytest-playwright` + a cached Chromium is acceptable in CI (headless).
- One representative test is sufficient to make the "Playwright proof" rule real + serve as the copy-template for future coverage.
