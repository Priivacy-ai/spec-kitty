# Tasks: Common Docs query — CLI retrieval index

**Mission**: `common-docs-query-01KY541A` | **Branch**: `feat/agent-knowledge-canonical-homes` (coord topology)
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

3 work packages. WP01 is the foundation (the generator + committed index); WP02 (freshness gate) and
WP03 (query CLI) both depend on WP01 and run in parallel after it.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first byte-stability test for the index (NFR-001) | WP01 | |
| T002 | `DocsQueryEntry` + `Anchor` dataclasses + slug helper (canonical `slugify` + ordinal dedup) | WP01 | |
| T003 | Pure helpers: `##`/`###` heading scan, title precedence, abstract fallback | WP01 | [P] |
| T004 | `generate_index` / `render_index` / `compare_index` / `run_generate_and_compare(--strict)` | WP01 | |
| T005 | Generate + commit `docs/development/3-2-docs-retrieval-index.yaml` | WP01 | |
| T006 | Unit tests + C-001 no-import-of-`PageInventoryEntry` regression | WP01 | |
| T007 | `_check_docs_index_drift` checker in `check_docs_freshness.py` | WP02 | |
| T008 | Register `DOCS-INDEX-DRIFT` in the aggregate ruler list (inventory ruler untouched) | WP02 | |
| T009 | Verify `docs-freshness.yml` covers the new checker (explicit step only if needed) | WP02 | |
| T010 | Tests: gate red on stale index, green on fresh | WP02 | |
| T011 | `DocsIndexStore` load-once + `query(term, divio_type, section)` in-memory filter | WP03 | |
| T012 | `docs.py` Typer sub-app: `query` command (`--json`/`--divio-type`/`--section`) | WP03 | |
| T013 | Register `docs` sub-app at `cli/commands/__init__.py` next to `glossary` | WP03 | |
| T014 | Error handling: no-tree/missing-index clear error; invalid `--divio-type` usage error | WP03 | |
| T015 | Tests: JSON shape, empty→`[]`, filters, no-tree error, live-tree <1s smoke | WP03 | |

## WP01 — Docs retrieval index generator

**Goal**: Build the deterministic, byte-stable sibling index generator and generate the committed index
file. Foundation for WP02 + WP03.
**Priority**: P1 (MVP — nothing else works without it).
**Independent test**: `python scripts/docs/docs_index.py --write` twice produces a byte-identical file;
unit tests prove slug/ordinal, title precedence, abstract fallback, and the ADR/changelog exemption.
**Dependencies**: none.
**Requirement refs**: FR-001, NFR-001 (+ NFR-003).
**Prompt**: [tasks/WP01-docs-index-generator.md](tasks/WP01-docs-index-generator.md) (~380 lines)

- [ ] T001 Red-first byte-stability test: regenerating the index over an unchanged tree is byte-identical (WP01)
- [ ] T002 `DocsQueryEntry` + `Anchor` frozen dataclasses + slug helper importing canonical `slugify` + ordinal dedup (WP01)
- [ ] T003 Pure helpers: heading scan (`##`/`###`), title precedence (frontmatter→H1→stem), abstract fallback (description→first paragraph→"") (WP01)
- [ ] T004 `generate_index`/`render_index`/`compare_index`/`run_generate_and_compare(--strict)` mirroring `inventory_lockfile.py`, reusing `parse_frontmatter`/rglob/`DivioType` (WP01)
- [ ] T005 Generate + commit `docs/development/3-2-docs-retrieval-index.yaml` (WP01)
- [ ] T006 Unit tests for all helpers + a regression asserting the generator does not import/mutate `PageInventoryEntry` (C-001) (WP01)

## WP02 — Index freshness gate

**Goal**: A CI-runnable drift check that reds when the committed index is stale, mirroring the
page-inventory lockfile gate, leaving the inventory ruler byte-for-byte untouched.
**Priority**: P2.
**Independent test**: edit a doc heading without regenerating → `check_docs_freshness --ci` reds with
`DOCS-INDEX-DRIFT`; regenerate → green.
**Dependencies**: WP01 (needs the generator's compare API).
**Requirement refs**: FR-005 (+ NFR-003).
**Prompt**: [tasks/WP02-index-freshness-gate.md](tasks/WP02-index-freshness-gate.md) (~250 lines)

- [ ] T007 `_check_docs_index_drift` checker in `check_docs_freshness.py` (regenerate in-memory, compare to committed) (WP02)
- [ ] T008 Register the new checker in the aggregate as an `error`-severity ruler (`DOCS-INDEX-DRIFT`); leave `_check_inventory_lockfile_drift` untouched (WP02)
- [ ] T009 Verify `.github/workflows/docs-freshness.yml` runs the aggregate (covers the new checker); add an explicit step only if it does not (WP02)
- [ ] T010 Tests: drift red on stale index, green on fresh; inventory-ruler-untouched assertion (WP02)

## WP03 — `spec-kitty docs query` CLI

**Goal**: Expose the index as a first-class query surface mirroring the glossary CLI shape.
**Priority**: P2.
**Independent test**: `spec-kitty docs query "<term>" --json` returns matching pages (path/title/matching
anchors/abstract/divio_type); no match → `[]` exit 0; filters + no-tree error behave per contract.
**Dependencies**: WP01 (consumes the index schema).
**Requirement refs**: FR-002, FR-003, FR-004, NFR-002 (+ NFR-003).
**Prompt**: [tasks/WP03-docs-query-cli.md](tasks/WP03-docs-query-cli.md) (~320 lines)

- [ ] T011 `DocsIndexStore.load()` + `query(term, *, divio_type, section)` in-memory filter over title/anchors/abstract (WP03)
- [ ] T012 `docs.py` Typer sub-app with `query` command: `--json` (`print(json.dumps)`, empty→`[]`, exit 0), `--divio-type`, `--section`; human Rich table (WP03)
- [ ] T013 Register `docs` sub-app at `src/specify_cli/cli/commands/__init__.py` next to `glossary` (out-of-map one-line edit, rationale recorded) (WP03)
- [ ] T014 Error handling: missing tree/index → clear stderr error, non-zero exit, no traceback; invalid `--divio-type` → usage error exit 2 (WP03)
- [ ] T015 Tests: JSON shape, empty→`[]`, `--divio-type`/`--section` filters, no-tree error, live-tree `<1s` smoke (WP03)

## Dependencies & parallelization

```
WP01 (foundation) ──┬──> WP02 (freshness gate)
                    └──> WP03 (query CLI)
```

WP02 ∥ WP03 once WP01 is `approved`. MVP = WP01.
