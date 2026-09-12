# Implementation Plan: Common Docs query — CLI retrieval index

**Branch**: `feat/agent-knowledge-canonical-homes` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/common-docs-query-01KY541A/spec.md`

## Summary

Close the one canonical-knowledge retrieval gap: Common Docs (`docs/`) has a metadata spine
(the CI-drift-gated page-inventory) but no title / heading-anchor / abstract index and no query
surface, so agents glob `docs/**`. Deliver (1) a generated, freshness-gated **sibling** retrieval
index and (2) a `spec-kitty docs query --json` CLI modeled on the existing glossary query, reusing
the `scripts/docs/` inventory machinery and the glossary CLI shape rather than new infrastructure.

Pre-plan squad (architect-alphonso + python-pedro, convergent, code-cited) locked the topology and
seams below; this plan encodes them as decisions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `typer` + `rich` (CLI, existing), `ruamel.yaml` (frontmatter/index I/O, existing); reuse `scripts/docs/` inventory machinery. No new third-party dependency.
**Storage**: One new git-tracked generated file — the sibling retrieval index `docs/development/3-2-docs-retrieval-index.yaml`. The existing `docs/development/3-2-page-inventory.yaml` is untouched (C-001).
**Testing**: `pytest`. Unit tests for the pure helpers (slug, heading-scan, title-precedence, abstract-fallback), a deterministic-render/byte-stability test, a drift-gate test, and CLI JSON-shape tests against a fixture docs tree; one smoke test over the live tree.
**Target Platform**: Linux / dev CLI (`spec-kitty`).
**Project Type**: single (CLI tool).
**Performance Goals**: Full-tree `docs query` < 1s over ~500+ pages (NFR-002) via a pre-generated index loaded once + in-memory filter (no per-query body walk).
**Constraints**: Deterministic byte-stable index (NFR-001); C-001 page-inventory untouched; C-002 no HTTP server; C-003 title/anchor/abstract only, not full-text; C-004 reuse existing machinery; C-005 anchors are source-heading slugs, not DocFX-exact fragments.
**Scale/Scope**: ~500+ `docs/**/*.md` pages; ~3 new modules + tests; no migration.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority / no improvisation**: PASS — reuses the canonical `scripts/docs/` generator+gate pattern and the canonical `slugify` (`generate_kitty_specs_docs.py`), rather than forking a second slugger or a parallel index framework (DIRECTIVE_044). The sibling index is a new canonical surface for a genuinely new concern (Common Docs retrieval), not a duplicate of the page-inventory.
- **Architectural alignment / close defect classes by construction**: PASS — sibling topology holds C-001 *by construction* (the pinned frozen `PageInventoryEntry`, its byte-stable render, and its blocking drift gate are physically untouched), and the freshness gate closes the stale-index defect class (DIRECTIVE_043).
- **DDD + tiered rigour**: PASS — new code is `scripts/docs/` glue + a thin CLI surface; pure helpers (slug/heading-scan/abstract) are unit-tested directly.
- **ATDD-first**: PASS — acceptance scenarios in spec map to fixture-tree tests; NFR-001 determinism has a red-first byte-stability test before the generator lands.
- **Terminology adherence**: PASS — "Common Docs", "Mission", "DRG", "charter", "doctrine" canonical casing; no `feature*` aliases in the new `docs` command surface.
- **Complexity ceiling (≤15)**: enforced per-helper; the generator is decomposed into pure phases (walk → parse → build entry → render) to stay under the ceiling.

No charter violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/common-docs-query-01KY541A/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (DocsQueryEntry + index schema)
├── quickstart.md        # Phase 1 output (how to generate + query)
├── contracts/           # Phase 1 output (CLI contract + index-file contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/docs/             # NEW packaged package (shipped in the wheel)
├── __init__.py                   # NEW — exports the public schema/store surface.
└── index_model.py                # NEW — Anchor, DocsQueryEntry, render_index, parse_index,
│                                 #   compare_index/IndexDrift, DocsIndexStore, DEFAULT_INDEX_PATH.
│                                 #   NO scripts dependency. Imported by BOTH the CLI (src→src)
│                                 #   and the generator (scripts→src). This is the packaging fix.

scripts/docs/
├── docs_index.py                 # NEW — generator (build-tooling): generate_index (uses
│                                 #   parse_frontmatter, DivioType, sorted rglob, slugify+ordinal),
│                                 #   scan_headings/resolve_title/resolve_abstract helpers,
│                                 #   run_generate_and_compare(--write/--strict), __main__. Imports
│                                 #   schema+render+compare DOWN from specify_cli.docs.index_model.
├── check_docs_freshness.py       # EDIT — add _check_docs_index_drift + fold into the aggregate at
│                                 #   the ruler-registration site (~:433); leave
│                                 #   _check_inventory_lockfile_drift untouched (C-001/D3). Imports
│                                 #   only scripts.docs.docs_index (scripts→scripts).
└── generate_kitty_specs_docs.py  # READ-ONLY import source for slugify + ordinal logic (D5).

docs/development/
└── 3-2-docs-retrieval-index.yaml # NEW — committed, generated sibling index (byte-stable).

src/specify_cli/cli/commands/
├── docs.py                       # NEW — Typer sub-app: `query` command; imports DocsQueryEntry +
│                                 #   DocsIndexStore from specify_cli.docs.index_model (src→src, NEVER
│                                 #   scripts); mirrors glossary.py --json shape (print(json.dumps),
│                                 #   empty -> "[]", exit 0).
└── __init__.py                   # EDIT — register `docs` sub-app next to `glossary` (~:208).

tests/docs/
├── test_docs_index.py            # NEW — generator determinism, slug/ordinal, title
│                                 #   precedence, abstract fallback, ADR/changelog exemption.
├── test_docs_index_freshness.py  # NEW — drift gate red on stale index, green on fresh.
└── test_docs_query_cli.py        # NEW — JSON shape, empty->[], filters, no-tree error.

.github/workflows/docs-freshness.yml # EDIT (if the new gate needs an explicit step; the
                                      #   aggregate call may already cover it — verify).
```

**Structure Decision**: Single-project CLI with a **packaging-driven three-way split** (locked by the
post-tasks squad): the schema + query store live in a new *packaged* `src/specify_cli/docs/index_model.py`
so the installed CLI can import them; the *build-tooling* generator lives in `scripts/docs/docs_index.py`
and imports the schema *down* from `src` (`scripts→src` is legal; `src→scripts` is not — the wheel
excludes `scripts`); the CLI (`src/specify_cli/cli/commands/docs.py`) imports **only** the packaged
module. The freshness gate imports only `scripts.docs.docs_index` (`scripts→scripts`). This keeps the
pure index logic testable without the CLI, the CLI testable against a fixture index, and — critically —
makes the CLI's dependency actually loadable at runtime.

## Complexity Tracking

*No charter violations — none required.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Docs retrieval index: packaged model + generator

- **Purpose**: Build the deterministic, byte-stable sibling index — per `docs/**/*.md` page emit `path`, `title`, `divio_type`, `anchors[]` (heading slug + text), `abstract` — split across a **packaged** schema/store module and a build-tooling generator, and generate the committed index file. Foundation the gate and the CLI both consume.
- **Relevant requirements**: FR-001, NFR-001; constraints C-001, C-003, C-004, C-005; edge cases (no-description abstract fallback, duplicate-heading ordinal dedup, ADR/changelog empty-abstract exemption).
- **Affected surfaces**: `src/specify_cli/docs/index_model.py` + `src/specify_cli/docs/__init__.py` (new, packaged — schema, render/parse, compare, `DocsIndexStore`), `scripts/docs/docs_index.py` (new — generator + `__main__`), `docs/development/3-2-docs-retrieval-index.yaml` (new generated), `tests/docs/test_docs_index.py` (new). Import-only: `scripts/docs/_inventory.py` (`parse_frontmatter`, `DivioType`), `scripts/docs/generate_kitty_specs_docs.py` (`slugify` + ordinal-dedup pattern).
- **Sequencing/depends-on**: none (foundation).
- **Public API to pin (WP02/WP03 depend on it)**: the generator exposes `generate_index`, `run_generate_and_compare` (`scripts→scripts` for the gate); the packaged module exposes `DocsQueryEntry`, `Anchor`, `DocsIndexStore` (`src→src` for the CLI). WP01's DoD must pin these import paths and prove the CLI-facing symbols import from the packaged module (a one-line import test), so the fan-out is safe.
- **Risks**: Wrong layer for the schema → the installed CLI can't import it (the packaging trap). Slug must reuse canonical `slugify`, not a fork (C-005/DIRECTIVE_044) — enforce with a positive import assertion. Title/abstract precedence must be total. Byte-stability is red-first with an explicit path-sort assertion (NFR-001).

### IC-02 — Index freshness gate (`_check_docs_index_drift`)

- **Purpose**: A CI-runnable drift check that regenerates the index in-memory and compares to the committed file, mirroring the page-inventory lockfile gate, so a stale index is caught.
- **Relevant requirements**: FR-005; constraints C-001 (leave `_check_inventory_lockfile_drift` untouched), C-004.
- **Affected surfaces**: `scripts/docs/check_docs_freshness.py` (edit — new checker + aggregate registration), `.github/workflows/docs-freshness.yml` (edit if a discrete step is required), `tests/docs/test_docs_index_freshness.py` (new).
- **Sequencing/depends-on**: IC-01 (needs the generator's compare API).
- **Risks**: Must fold into the aggregate as a new `error`-severity ruler without altering the existing inventory ruler's bytes/behavior. Verify whether the CI workflow calls the aggregate (covering the new gate automatically) or needs an explicit step.

### IC-03 — `spec-kitty docs query` CLI (`src/specify_cli/cli/commands/docs.py`)

- **Purpose**: Expose the index as a first-class query surface — `spec-kitty docs query "<term>" [--json] [--divio-type <t>] [--section <anchor>]` — returning matching pages (path, title, matching anchors, abstract, divio_type) as stable JSON, loaded once and filtered in-memory.
- **Relevant requirements**: FR-002, FR-003, FR-004, NFR-002; constraints C-002 (no HTTP), C-004 (mirror glossary CLI shape).
- **Affected surfaces**: `src/specify_cli/cli/commands/docs.py` (new — Typer sub-app + `DocsIndexStore`), `src/specify_cli/cli/commands/__init__.py` (edit — register next to `glossary`), `tests/docs/test_docs_query_cli.py` (new).
- **Sequencing/depends-on**: IC-01 (consumes the index schema/shape).
- **Risks**: JSON must be `print(json.dumps(...))` (not Rich `console`, to avoid markup); empty result → `[]` and exit 0 (Acceptance Scenario 2); no-docs-tree → clear error, not a stack trace. `--divio-type` validates against `DivioType`.
