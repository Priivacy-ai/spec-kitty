# Tasks: Glossary DRG Surfaces and Charter Lint

**Mission**: `glossary-drg-surfaces-and-charter-lint-01KPTY5Y`  
**Mission ID**: 01KPTY5YAVPZKFDFTG197XZAHG  
**Target branch**: `main`  
**Generated**: 2026-04-23

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | `InlineNotice` dataclass in `observation.py` | WP01 | [P] |
| T002 | `ObservationSurface.collect_notices()` — read `_cli.events.jsonl`, filter high/critical | WP01 | |
| T003 | `ObservationSurface.render_notices()` — Rich compact block, ≤5 lines, no-op if empty | WP01 | |
| T004 | Wire `ObservationSurface` into `do_cmd.py` after `invoke()` | WP01 | [P] |
| T005 | Wire `ObservationSurface` into `advise.py` after `invoke()` | WP01 | [P] |
| T006 | Tests for `ObservationSurface` — fixture event log, severity filtering, silent failure | WP01 | |
| T007 | Add `GlossaryHealthResponse` + `GlossaryTermRecord` TypedDicts to `api_types.py` | WP02 | [P] |
| T008 | Implement `GlossaryHandler.handle_glossary_health()` — store + event log reads | WP02 | |
| T009 | Implement `GlossaryHandler.handle_glossary_terms()` — return term array from store | WP02 | [P] |
| T010 | Implement `GlossaryHandler.handle_glossary_page()` — serve `glossary.html` at `/glossary` | WP02 | [P] |
| T011 | Register all three glossary routes in `router.py`, add `GlossaryHandler` to MRO | WP02 | |
| T012 | Adapt `glossary.html` — replace hardcoded `TERMS` array with `fetch('/api/glossary-terms')` | WP02 | |
| T013 | Add glossary tile HTML/JS to `index.html` (stat pills, link to `/glossary`) | WP02 | [P] |
| T014 | Tests for `GlossaryHandler` — mock store + event log, assert shapes, assert `/glossary` 200 | WP02 | |
| T015 | `BacklinkEntry` dataclass + `GlossaryEntityPageRenderer` skeleton in `entity_pages.py` | WP03 | [P] |
| T016 | DRG reverse-walk: load merged DRG, build `backlink_index` from `vocabulary` edges | WP03 | |
| T017 | Entity page Markdown template rendering per term (all sections from FR-008) | WP03 | |
| T018 | Atomic page write (temp → rename) + `generate_all()` / `generate_one()` public API + tests | WP03 | |
| T019 | `LintFinding` + `DecayReport` dataclasses in `findings.py`; `charter_lint` package skeleton | WP04 | [P] |
| T020 | DRG loading helper in `charter_lint/` — reads merged DRG from `.kittify/doctrine/` | WP04 | |
| T021 | `OrphanChecker` in `checks/orphan.py` — symmetric incoming-edge property | WP04 | [P] |
| T022 | `ContradictionChecker` in `checks/contradiction.py` — ADR/directive/glossary conflicts | WP04 | [P] |
| T023 | `StalenessChecker` in `checks/staleness.py` — corpus age, artifact edit timestamps | WP04 | [P] |
| T024 | `ReferenceIntegrityChecker` in `checks/reference_integrity.py` — superseded ADRs, dangling edges | WP04 | [P] |
| T025 | `DecayWatchTileResponse` TypedDict in `api_types.py` | WP05 | [P] |
| T026 | `LintTileHandler.handle_charter_lint()` — reads `.kittify/lint-report.json`, returns tile data | WP05 | |
| T027 | Register `/api/charter-lint` in `router.py`, add `LintTileHandler` to MRO | WP05 | |
| T028 | Decay watch tile HTML/JS in `index.html` + tests | WP05 | |
| T029 | `spec-kitty glossary show <term>` subcommand in `glossary.py` — calls renderer, Rich.Markdown | WP06 | |
| T030 | `<!-- glossary:<term-id> -->` anchor injection in `src/specify_cli/template/renderer.py` | WP06 | [P] |
| T031 | Verify / add `.kittify/charter/compiled/glossary/` to `.gitignore` | WP06 | [P] |
| T032 | Tests for `glossary show` CLI — mock renderer, exit codes, terminal output | WP06 | |
| T033 | `LintEngine` in `engine.py` — orchestrates all 4 checkers, times run, writes `lint-report.json` | WP07 | |
| T034 | Entity page generation hook in `charter.py` — call `generate_glossary_entity_pages()` after each `ensure_charter_bundle_fresh()` call site; silent on failure | WP07 | [P] |
| T035 | `spec-kitty charter lint` subcommand in `charter.py` — all flags (`--feature`, `--orphans`, `--contradictions`, `--stale`, `--json`, `--severity`) | WP07 | |
| T036 | Tests for `LintEngine` — fixture DRG with 4 manufactured decay conditions, ≥4 findings, `duration_seconds < 5.0` | WP07 | |
| T037 | CLI integration tests for `charter lint` — `--json` valid JSON, `--severity` filtering, `--feature` scoping | WP07 | |

---

## Work Packages

### WP01 — Inline Drift Observation Surface
**Priority**: High | **FRs**: FR-001, FR-002, FR-003, FR-004  
**Estimated prompt**: ~350 lines | **External dep**: WP5.2 chokepoint must emit `SemanticCheckEvaluated` events  
**Dependencies**: none

**Goal**: After `spec-kitty do/ask/advise`, append a ≤5-line inline notice to agent output when the chokepoint has recorded high-severity glossary drift in the current invocation window. Silent if none.

**Subtasks**:
- [ ] T001 `InlineNotice` dataclass (WP01)
- [ ] T002 `ObservationSurface.collect_notices()` (WP01)
- [ ] T003 `ObservationSurface.render_notices()` (WP01)
- [ ] T004 Wire into `do_cmd.py` (WP01)
- [ ] T005 Wire into `advise.py` (WP01)
- [ ] T006 Tests (WP01)

**Implementation sketch**: Create `observation.py` with `InlineNotice` dataclass and `ObservationSurface` class. `collect_notices()` reads `.kittify/events/glossary/_cli.events.jsonl`, iterates reversed, collects `SemanticCheckEvaluated` events from the current invocation window with `severity in {"high", "critical"}`. Wrap entire method in `try/except` — return `[]` on any read failure. Render via Rich `Panel` or plain `Text`, max 5 lines. Wire into the two CLI command modules at the point after `invoke()` returns.

**Parallel opportunities**: T001, T004, T005 can be written independently once T002–T003 are complete.  
**Key risk**: Without WP5.2 being available, tests must use fixture event logs that mimic `SemanticCheckEvaluated` shape.

**Prompt file**: `tasks/WP01-inline-drift-observation-surface.md`

---

### WP02 — Dashboard Glossary Tile + Full-Page Browser
**Priority**: High | **FRs**: FR-005, FR-006, FR-025, FR-026, FR-027  
**Estimated prompt**: ~480 lines | **Design reference**: `src/specify_cli/dashboard/templates/glossary.html` + `designs/README.md`  
**Dependencies**: none

**Goal**: New `/api/glossary-health` and `/api/glossary-terms` endpoints, a summary tile on the dashboard home page, and a live-data full-page glossary browser at `/glossary`. The visual design is specified and approved — do not deviate.

**Subtasks**:
- [ ] T007 TypedDicts in `api_types.py` (WP02)
- [ ] T008 `handle_glossary_health()` (WP02)
- [ ] T009 `handle_glossary_terms()` (WP02)
- [ ] T010 `handle_glossary_page()` (WP02)
- [ ] T011 Route registration in `router.py` (WP02)
- [ ] T012 Make `glossary.html` dynamic (WP02)
- [ ] T013 Glossary tile in `index.html` (WP02)
- [ ] T014 Tests (WP02)

**Implementation sketch**: Add TypedDicts first, then implement the three handler methods in `glossary.py`. Register routes by adding `GlossaryHandler` to the `DashboardRouter` MRO. For `glossary.html`, replace the `const TERMS = [...]` block with a `fetch('/api/glossary-terms')` call in `DOMContentLoaded`; populate the alpha-nav and stat pills from the API response. The tile in `index.html` is a summary card that shows the 4 stat pills and links to `/glossary`.

**Parallel opportunities**: T007, T009, T010, T013 can be worked in parallel once handler structure is clear.  
**Key risk**: Dashboard visual check required before WP approval — load `/glossary` in browser and verify all four filter tabs, alpha nav, card rendering, and dark mode work.

**Prompt file**: `tasks/WP02-dashboard-glossary-tile-and-browser.md`

---

### WP03 — Entity Page Renderer Core
**Priority**: High | **FRs**: FR-007, FR-008, FR-010  
**Estimated prompt**: ~290 lines | **External dep**: WP5.1 DRG must have `glossary:<id>` URN nodes and `vocabulary` edges  
**Dependencies**: none

**Goal**: A `GlossaryEntityPageRenderer` class that reverse-walks `vocabulary` edges in the merged DRG to generate per-term Markdown entity pages at `.kittify/charter/compiled/glossary/<term-id>.md`. Pages are idempotent build artifacts — never committed.

**Subtasks**:
- [ ] T015 `BacklinkEntry` dataclass + renderer skeleton (WP03)
- [ ] T016 DRG reverse-walk logic (WP03)
- [ ] T017 Markdown template rendering (WP03)
- [ ] T018 Atomic write + public API + tests (WP03)

**Implementation sketch**: Load merged DRG from `.kittify/doctrine/` via `DRGGraph.model_validate()`. Build `backlink_index: dict[term_id, list[BacklinkEntry]]` by iterating edges where `edge.type == "vocabulary"`. For each term node, render the page sections from FR-008 (definition, inbound refs grouped by type, provenance, conflict history, cross-term relationships). Write atomically: write to `<term-id>.md.tmp`, rename to `<term-id>.md`. `generate_all()` returns list of written paths.

**Parallel opportunities**: T015 and T016 can be written together; T017 is fully independent.  
**Key risk**: If WP5.1 DRG is not yet available, stub `load_merged_drg()` with a returns-None guard so all tests pass with a fixture DRG.

**Prompt file**: `tasks/WP03-entity-page-renderer-core.md`

---

### WP04 — Charter Lint Checkers
**Priority**: High | **FRs**: FR-012, FR-019, FR-020, FR-021, FR-022  
**Estimated prompt**: ~420 lines | **External dep**: WP5.1 merged DRG  
**Dependencies**: none

**Goal**: The `charter_lint` package with `LintFinding`/`DecayReport` data models, a DRG loading helper, and four independent checker classes covering orphan detection, contradiction detection, staleness detection, and reference integrity.

**Subtasks**:
- [ ] T019 Package skeleton + `LintFinding` + `DecayReport` dataclasses (WP04)
- [ ] T020 DRG loading helper (WP04)
- [ ] T021 `OrphanChecker` (WP04)
- [ ] T022 `ContradictionChecker` (WP04)
- [ ] T023 `StalenessChecker` (WP04)
- [ ] T024 `ReferenceIntegrityChecker` (WP04)

**Implementation sketch**: Each checker is an independent class with a `run(drg, feature_scope) -> list[LintFinding]` method. No inter-checker dependency. `OrphanChecker` counts incoming edges of expected types per node; zero = orphan. `ContradictionChecker` groups ADR nodes by `topic` URN, then checks `decision` content divergence. `StalenessChecker` reads `corpus_snapshot_id` metadata and compares to `datetime.now() - threshold`. `ReferenceIntegrityChecker` traverses all `references_adr` edges and checks for a `replaces:` edge on the target.

**Parallel opportunities**: T021, T022, T023, T024 can be implemented in parallel after T019–T020 are done.  
**Key risk**: DRG schema must be stable — use `DRGGraph.model_validate()` to surface schema drift immediately.

**Prompt file**: `tasks/WP04-charter-lint-checkers.md`

---

### WP05 — Dashboard Decay Watch Tile
**Priority**: Medium | **FRs**: FR-023, FR-024  
**Estimated prompt**: ~240 lines  
**Dependencies**: WP02 (owns `api_types.py`, `router.py`, `index.html`), WP07 (writes `lint-report.json`)

**Goal**: A `/api/charter-lint` GET endpoint that reads `.kittify/lint-report.json` and returns a `DecayWatchTileResponse`; a decay watch tile on the dashboard home page showing last-run finding counts and a "no data" prompt if no report exists yet.

**Subtasks**:
- [ ] T025 `DecayWatchTileResponse` TypedDict in `api_types.py` (WP05)
- [ ] T026 `LintTileHandler.handle_charter_lint()` (WP05)
- [ ] T027 Register `/api/charter-lint` in `router.py` (WP05)
- [ ] T028 Decay watch tile in `index.html` + tests (WP05)

**Implementation sketch**: `handle_charter_lint()` reads `.kittify/lint-report.json` if it exists; if missing, return `{"has_data": false, ...all counts 0}`. Parse JSON, aggregate finding counts by category and severity. Add `LintTileHandler` to the `DashboardRouter` MRO alongside `GlossaryHandler`. The dashboard tile renders "N orphans · N contradictions · N stale · N broken refs" from the counts.

**Note on file overlap**: `api_types.py`, `router.py`, and `index.html` are also modified by WP02. This overlap is safe because WP05 depends on WP02 (they are never in the same parallel execution window). WP05 adds to these files after WP02's changes are merged.

**Prompt file**: `tasks/WP05-dashboard-decay-watch-tile.md`

---

### WP06 — `glossary show` CLI + Backlink Annotations + Gitignore
**Priority**: Medium | **FRs**: FR-009, FR-011  
**Estimated prompt**: ~250 lines  
**Dependencies**: WP03 (entity page renderer must exist)

**Goal**: Add `spec-kitty glossary show <term>` subcommand that calls `GlossaryEntityPageRenderer.generate_one()` and renders to terminal. Add `<!-- glossary:<term-id> -->` HTML comment anchors in artifact rendering so entity pages can backlink to their sources.

**Subtasks**:
- [ ] T029 `glossary show` subcommand in `glossary.py` (WP06)
- [ ] T030 Backlink anchor injection in `template/renderer.py` (WP06)
- [ ] T031 Add `.kittify/charter/compiled/glossary/` to `.gitignore` (WP06)
- [ ] T032 Tests for `glossary show` (WP06)

**Implementation sketch**: In `glossary.py`, add a `show` Typer command that takes a `term` argument. Call `GlossaryEntityPageRenderer(repo_root).generate_one(term)` and render the resulting Markdown file contents via `Console.print(Markdown(content))`. Exit 1 with a clear message on `TermNotFoundError`. In `renderer.py`, inject `<!-- glossary:<term-id> -->` as an invisible HTML comment after any term name that appears in the glossary index — use a simple regex match against the loaded glossary term surfaces.

**Prompt file**: `tasks/WP06-glossary-show-cli-and-backlinks.md`

---

### WP07 — LintEngine, Charter Wiring, and Tests
**Priority**: High | **FRs**: FR-012–FR-018, FR-024; NFR-002, NFR-003, NFR-005  
**Estimated prompt**: ~380 lines  
**Dependencies**: WP03 (entity_pages.py needed for charter hook), WP04 (checker classes needed by engine)

**Goal**: `LintEngine` orchestrator that runs all four checkers, writes `lint-report.json`, and times the run. Wire into `charter.py`: add `spec-kitty charter lint` CLI subcommand and the entity page generation hook after `ensure_charter_bundle_fresh()`.

**Subtasks**:
- [ ] T033 `LintEngine` in `engine.py` (WP07)
- [ ] T034 Entity page generation hook in `charter.py` (WP07)
- [ ] T035 `charter lint` CLI subcommand in `charter.py` (WP07)
- [ ] T036 `LintEngine` tests with 4-decay fixture DRG (WP07)
- [ ] T037 `charter lint` CLI integration tests (WP07)

**Implementation sketch**: `LintEngine.run()` loads the merged DRG, instantiates all four checkers, calls each, merges findings, times the total, writes `DecayReport` to `.kittify/lint-report.json`, and returns the report. In `charter.py`, add a `lint` command on the `app` Typer group with all documented flags. Entity page hook: after each `ensure_charter_bundle_fresh()` call site, call `generate_glossary_entity_pages(repo_root)` wrapped in `try/except`; log a warning on failure, never raise.

**Parallel opportunities**: T034 and T035 can be written simultaneously once T033 is drafted.  
**Key risk**: `charter.py` is large — take care to place the lint subcommand in the correct location and not duplicate existing command registrations.

**Prompt file**: `tasks/WP07-lint-engine-charter-wiring-tests.md`

---

## Dependency Graph

```
WP01 ─────────────────────────────────────── (independent)
WP02 ─────────────────────────────────────── (independent)
WP03 ─────────────────────────────────────── (independent)
WP04 ─────────────────────────────────────── (independent)
         WP03 ──► WP06
         WP03 ──►
         WP04 ──► WP07 ──► WP05 ◄── WP02
```

**Parallel batch 1**: WP01, WP02, WP03, WP04 (all independent)  
**Parallel batch 2**: WP06 (after WP03), WP07 (after WP03 + WP04)  
**Final**: WP05 (after WP02 + WP07)

---

## MVP Scope

WP04 → WP07 (charter lint core) is the highest-leverage path: it delivers the `spec-kitty charter lint --json` contract needed by the FR4 retrospective profile and the decay watch dashboard tile. WP01 (inline surface) is the highest-visibility user-facing change.
