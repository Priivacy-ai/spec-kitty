# Implementation Plan: Glossary DRG Surfaces and Charter Lint

**Mission**: `glossary-drg-surfaces-and-charter-lint-01KPTY5Y` | **Date**: 2026-04-22  
**Mission ID**: 01KPTY5YAVPZKFDFTG197XZAHG  
**Spec**: [spec.md](spec.md)  
**Target branch**: `main`

## Branch Contract

- **Current branch at plan start**: `feat/glossary-save-seed-file-and-core-terms`
- **Planning/base branch**: `feat/glossary-save-seed-file-and-core-terms` (CLI resolves from current branch; `meta.json` records `main` as merge target)
- **Final merge target**: `main`

## Design Reference

**Approved mockup**: `src/specify_cli/dashboard/templates/glossary.html`  
**Design notes**: `designs/README.md`  

The glossary browser UI is designed and approved. WP02 adapts the static mockup into a dynamic dashboard page at `/glossary`. Implementers must not deviate from the CSS design system, card anatomy, or filter UX defined in the mockup. See `designs/README.md` for the full design spec including color tokens, card structure, and API contract.

---

## Summary

Implement four user-facing surfaces on top of the DRG-resident glossary (Phase 5 WP5.3–WP5.6 from issue #467): an inline high-severity drift notice injected into `do/ask/advise` output (WP5.3); a dashboard glossary health tile (WP5.4); per-term entity pages with two-way backlinks reverse-walked from the merged DRG (WP5.5); and a `spec-kitty charter lint` command with four decay-check categories plus a dashboard decay watch tile (WP5.6). WP5.1 (glossary-in-DRG) and WP5.2 (chokepoint middleware) are external dependencies assumed available.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: existing `doctrine.drg.models`, `charter.sync`, `specify_cli.glossary`, `specify_cli.dashboard` — no new packages  
**Storage**: filesystem (`.kittify/events/glossary/`, `.kittify/charter/compiled/`, `.kittify/lint-report.json`)  
**Testing**: pytest, fixture-based DRG mocks; no LLM calls in any test  
**Target Platform**: CLI + dashboard HTTP server (same as rest of spec-kitty)  
**Performance Goals**: chokepoint overhead ≤ 50ms p95 (WP01); lint ≤ 5s (WP04); entity page generation ≤ 10s/500 terms (WP03)  
**Constraints**: no LLM calls in hot path; nothing blocks agent output; entity pages gitignored  
**Scale/Scope**: up to 500 glossary terms; up to 200 ADRs for contradiction checks

## Charter Check

Governance: `software-dev-default`, DIR-001, tools: git, spec-kitty.  
DIR-001: all changes committed via safe-commit pattern.  
No charter conflicts. Gate: PASS.

## Project Structure

### Documentation (this feature)

```
kitty-specs/glossary-drg-surfaces-and-charter-lint-01KPTY5Y/
├── plan.md              # This file
├── research.md          # Phase 0 — codebase research findings
├── data-model.md        # Phase 1 — new types and file layout
├── designs/
│   └── README.md        # Design reference: CSS tokens, card anatomy, API contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not yet created)
```

### Source Code (repository root)

```
src/specify_cli/
  glossary/
    observation.py          # NEW — InlineNotice, ObservationSurface (WP01)
    entity_pages.py         # NEW — GlossaryEntityPageRenderer (WP03)
  charter_lint/
    __init__.py             # NEW (WP04)
    findings.py             # NEW — LintFinding, DecayReport dataclasses (WP04)
    engine.py               # NEW — LintEngine orchestrator (WP04)
    checks/
      __init__.py           # NEW
      orphan.py             # NEW — OrphanChecker (WP04)
      contradiction.py      # NEW — ContradictionChecker (WP04)
      staleness.py          # NEW — StalenessChecker (WP04)
      reference_integrity.py # NEW — ReferenceIntegrityChecker (WP04)
  dashboard/
    api_types.py            # MODIFY — add GlossaryHealthResponse, GlossaryTermRecord, DecayWatchTileResponse
    handlers/
      glossary.py           # NEW — GlossaryHandler: /api/glossary-health, /api/glossary-terms, /glossary (WP02)
      lint.py               # NEW — LintTileHandler: /api/charter-lint (WP05)
      router.py             # MODIFY — register /api/glossary-health, /api/glossary-terms, /glossary, /api/charter-lint
    templates/
      glossary.html         # MODIFY — replace hardcoded TERMS with fetch('/api/glossary-terms') (WP02)
                            #          [file already exists as approved design mockup]
  cli/commands/
    do_cmd.py               # MODIFY — call ObservationSurface after invoke() (WP01)
    advise.py               # MODIFY — same pattern (WP01)
    glossary.py             # MODIFY — add `show` subcommand (WP03)
    charter.py              # MODIFY — add `lint` subcommand; call entity page gen after bundle refresh (WP03, WP04)

tests/specify_cli/
  glossary/
    test_observation.py     # WP01
    test_entity_pages.py    # WP03
  dashboard/
    test_glossary_handler.py  # WP02
    test_lint_tile_handler.py # WP05
  charter_lint/
    test_engine.py            # WP04
    checks/
      test_orphan.py
      test_contradiction.py
      test_staleness.py
      test_reference_integrity.py
  cli/commands/
    test_glossary_show.py     # WP03
    test_charter_lint.py      # WP04
```

## Work Packages

### WP01 — Inline drift observation surface (WP5.3, FR-001–FR-004)

**What**: After a `spec-kitty do/ask/advise` invocation, if the chokepoint (WP5.2) recorded high-severity `SemanticCheckEvaluated` events during the invocation window, append a compact inline notice (≤5 lines) to CLI output. Never blocks. Silent if no high-severity events.

**New file**: `src/specify_cli/glossary/observation.py`
- `InlineNotice` dataclass (term, term_id, conflicting_senses, severity, suggested_action, conflict_type)
- `ObservationSurface` class:
  - `collect_notices(repo_root, invocation_id) -> list[InlineNotice]`: reads `_cli.events.jsonl`, filters `severity in {"high", "critical"}`
  - `render_notices(notices, console) -> None`: renders compact block via Rich; no-op if empty
- All reads wrapped in `try/except` — any failure returns empty list silently

**Modified files**:
- `src/specify_cli/cli/commands/do_cmd.py`: after `invoke()`, call `ObservationSurface().collect_notices()` and `render_notices()` before returning
- `src/specify_cli/cli/commands/advise.py`: same pattern

**Render format**:
```
⚠ Glossary drift [high]: "deployment-target" — conflicting senses detected
  Suggest: run `spec-kitty glossary resolve deployment-target`
```

**Tests**: `tests/specify_cli/glossary/test_observation.py` — fixture event log with high/medium/low events; assert only high surfaced; assert empty list when no high; assert silent failure on missing log.

**Dependency**: External WP5.2. No internal WP dependencies.

---

### WP02 — Dashboard glossary tile + full-page browser (WP5.4, FR-005–FR-006, FR-025–FR-027)

**Design reference**: `src/specify_cli/dashboard/templates/glossary.html` (static mockup) + `designs/README.md`

**What**: Two deliverables:
1. **Dashboard glossary tile** (`/api/glossary-health`): summary stat pills (total / active / draft / deprecated term counts, high-severity drift count, orphaned term count) + link to `/glossary`.
2. **Full-page glossary browser** (`/glossary`): adapts the approved static mockup into a dynamic page by replacing the hardcoded `TERMS` array with a live fetch from `/api/glossary-terms`.

**Design constraints** (from `glossary.html` mockup — do not deviate):
- CSS design system: inherit dashboard color palette exactly — `--bg`, `--surface`, `--green`, `--lavender`, `--peach`, `--yellow-dark`; dark mode via `@media (prefers-color-scheme: dark)`
- **Card anatomy**: `border-top: 3px solid` colored by status (green = active, lavender = draft, peach = deprecated); surface name in `var(--mono)` bold; status badge (pill shape, uppercase); definition text; confidence bar (3px height, colored by status) + percentage label
- **Deprecated term treatment**: strikethrough surface name with `var(--peach-dark)` color; italic definition
- **Hover lift**: `transform: translateY(-1px)` + stronger shadow on `.card:hover`
- **Filter UX**: sticky toolbar with lavender-bordered search input + status tab pills (All / Active / Draft / Deprecated); real-time filter across `surface` and `definition` fields; result count in monospace
- **Alpha nav**: A–Z buttons (28×28px); dimmed if letter has no terms; green-tinted if letter has terms; clicks scroll to the letter section
- **Grid**: `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))` — collapses to single column on ≤600px
- **Search highlight**: wrap matches in `<mark class="hl">` (yellow background, rounded)
- **Empty state**: centered `🔍` icon + "No terms match …" message

**New/modified backend files**:
- `src/specify_cli/dashboard/handlers/glossary.py` *(new)* — `GlossaryHandler`:
  - `handle_glossary_health()`: serves `/api/glossary-health` → `GlossaryHealthResponse`
  - `handle_glossary_terms()`: serves `/api/glossary-terms` → `list[GlossaryTermRecord]`
  - `handle_glossary_page()`: serves `/glossary` → renders `templates/glossary.html`
- `src/specify_cli/dashboard/api_types.py` *(modify)* — add `GlossaryHealthResponse`, `GlossaryTermRecord` TypedDicts
- `src/specify_cli/dashboard/handlers/router.py` *(modify)* — add `GlossaryHandler` to MRO; register `/api/glossary-health`, `/api/glossary-terms`, `/glossary`
- `src/specify_cli/dashboard/templates/glossary.html` *(modify)* — replace hardcoded `const TERMS = [...]` with a `fetch('/api/glossary-terms')` call on DOMContentLoaded; update the alpha nav and stat pills to populate from the API response

**`GlossaryTermRecord` TypedDict**:
```python
class GlossaryTermRecord(TypedDict):
    surface: str
    definition: str
    status: str          # "active" | "draft" | "deprecated"
    confidence: float    # 0.0–1.0
```

**`GlossaryHealthResponse` data sources**:
1. `GlossaryStore(project_dir)` → `total_terms`, `active_count`, `draft_count`, `deprecated_count`
2. `_cli.events.jsonl` → `high_severity_drift_count`, `last_conflict_at`
3. DRG (if available, else 0) → `orphaned_term_count`

**Tests**:
- `tests/specify_cli/dashboard/test_glossary_handler.py` — mock store; assert `GlossaryHealthResponse` shape; assert `GlossaryTermRecord` list shape; assert `/glossary` returns 200 HTML
- Visual: load `/glossary` in a browser before approving the WP; verify search, filter tabs, alpha nav, and card rendering all work; verify dark mode

**Dependency**: None (reads glossary store directly). Tile links to `/glossary` which is part of the same WP.

---

### WP03 — Glossary entity pages and `glossary show` CLI (WP5.5, FR-007–FR-011)

**What**: Renderer that reverse-walks merged DRG `vocabulary` edges to build per-term Markdown entity pages at `.kittify/charter/compiled/glossary/<term-id>.md`. Hooks into `ensure_charter_bundle_fresh()` call sites. New `spec-kitty glossary show <term>` CLI command.

**New file**: `src/specify_cli/glossary/entity_pages.py`
- `GlossaryEntityPageRenderer`:
  - `generate_all(repo_root) -> list[Path]`: reads merged DRG, reverse-walks vocabulary edges, writes pages
  - `generate_one(repo_root, term_id) -> Path`: single-term variant; raises `TermNotFoundError`
- Algorithm: load DRG from `.kittify/doctrine/`, build `backlink_index: dict[term_id, list[BacklinkEntry]]`, render Markdown template per term, write atomically (write to temp, rename)

**Modified files**:
- `src/specify_cli/cli/commands/charter.py`: after each `ensure_charter_bundle_fresh()` call, call `generate_glossary_entity_pages(repo_root)`; on failure: log warning, don't raise
- `src/specify_cli/cli/commands/glossary.py`: add `show` subcommand — call `generate_one()`, render with `Rich.Markdown`; exit 1 if `TermNotFoundError`
- `.gitignore`: verify/add `.kittify/charter/compiled/glossary/` is gitignored

**Backlink anchors**: In artifact rendering paths (ADR/WP templates), add `<!-- glossary:<term-id> -->` HTML comment annotation. Entity page renderer discovers these during generation. Comments are invisible to standard Markdown renderers.

**Tests**: `tests/specify_cli/glossary/test_entity_pages.py` — 3-term DRG fixture, assert 3 pages generated, backlinks correct, idempotent.

**Dependency**: External WP5.1 (DRG must have glossary URN nodes and vocabulary edges). No internal WP deps.

---

### WP04 — `spec-kitty charter lint` core engine and CLI (WP5.6, FR-012–FR-022)

**What**: New `charter_lint` package with 4 decay checkers and `LintEngine` orchestrator. CLI subcommand `spec-kitty charter lint` with all flags. Saves `DecayReport` to `.kittify/lint-report.json` as side effect.

**New package**: `src/specify_cli/charter_lint/`
- `findings.py`: `LintFinding` dataclass + `DecayReport` dataclass (see data-model.md)
- `engine.py`: `LintEngine(repo_root, staleness_threshold_days=90)` with `run(feature_scope, checks, min_severity) -> DecayReport`
- `checks/orphan.py`: `OrphanChecker` — symmetric incoming-edge property; checks WPs, ADRs, glossary terms, synthesized artifacts, procedures
- `checks/contradiction.py`: `ContradictionChecker` — ADR topic overlap + decision divergence; directive scope/severity conflict; multiple active glossary senses per scope
- `checks/staleness.py`: `StalenessChecker` — corpus snapshot age; WP-referenced artifact edit timestamps; profile context-source validity
- `checks/reference_integrity.py`: `ReferenceIntegrityChecker` — superseded ADR references; dangling DRG edges

**Modified files**:
- `src/specify_cli/cli/commands/charter.py`: add `lint` subcommand to `app` Typer; handle `--feature`, `--orphans`, `--contradictions`, `--stale`, `--json`, `--severity` flags; call `LintEngine.run()`; write `lint-report.json`; print Rich table or JSON to stdout

**CLI surface**:
```bash
spec-kitty charter lint [--feature <id>] [--orphans|--contradictions|--stale] [--json] [--severity <level>]
```

**Tests**: `tests/specify_cli/charter_lint/test_engine.py` — fixture DRG with 1 manufactured decay per category; assert 4 findings; assert `duration_seconds < 5.0`; assert `--json` output parseable.

**Dependency**: External WP5.1 (merged DRG). No internal WP deps. WP05 depends on this WP.

---

### WP05 — Dashboard decay watch tile (WP5.6 dashboard, FR-023–FR-024)

**What**: New `/api/charter-lint` GET endpoint + frontend tile showing summary of most recent lint run. If `.kittify/lint-report.json` does not exist: `has_data: false` with zero counts.

**New file**: `src/specify_cli/dashboard/handlers/lint.py`
- `LintTileHandler` with `handle_charter_lint()`: reads `.kittify/lint-report.json`, aggregates counts, returns `DecayWatchTileResponse`

**Modified files**:
- `src/specify_cli/dashboard/api_types.py`: add `DecayWatchTileResponse` TypedDict
- `src/specify_cli/dashboard/handlers/router.py`: add `LintTileHandler` to MRO, register `/api/charter-lint`
- dashboard templates/static: add decay watch tile HTML/JS

**Tests**: `tests/specify_cli/dashboard/test_lint_tile_handler.py` — assert correct counts when report exists; assert `has_data: false` when missing.

**Dependency**: WP04 (produces `.kittify/lint-report.json`). Cannot start until WP04 is approved.

---

## Dependency Graph

```
WP01 ── (external: WP5.2) ── no internal dep ── PARALLEL
WP02 ── (no deps)          ── no internal dep ── PARALLEL
WP03 ── (external: WP5.1)  ── no internal dep ── PARALLEL
WP04 ── (external: WP5.1)  ── no internal dep ── PARALLEL
WP05 ── depends on WP04    ── starts after WP04 approved
```

**Suggested lane assignments**:
- Lane A: WP01 → WP05
- Lane B: WP02
- Lane C: WP03
- Lane D: WP04 (unlocks WP05 in Lane A)

## Non-Functional Requirements Approach

- **NFR-001** (chokepoint ≤50ms): `collect_notices()` reads JSONL synchronously, <5ms typical. Benchmark assertion in test.
- **NFR-002** (lint ≤5s): O(n²) only on ADR contradiction check; realistic sizes well under budget. `assert report.duration_seconds < 5.0` in test.
- **NFR-003** (no LLM): Mock LLM client in test suite; assert never called.
- **NFR-004** (entity pages ≤10s/500 terms): Single-pass batched writes. Benchmark in test.
- **NFR-005** (valid JSON): `json.loads(output)` assertion in CLI test.

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| WP5.1/WP5.2 not yet on `main` at implementation time | High | DRG-dependent calls (WP03, WP04) guarded by `if drg_available` — compile and test cleanly without external dep |
| DRG schema changes between WP5.1 and this mission | Medium | Use `DRGGraph.model_validate()` — raises on schema mismatch immediately |
| Dashboard tiles need visual verification | Low | Manual browser check required before WP02/WP05 approval |
| Lint false positives → operator fatigue | Medium | Default: show all; dashboard shows only high; `--severity` flag for narrowing |

## Complexity Tracking

No charter violations. No unjustified complexity introduced.
