# Mission Specification: Common Docs query — CLI retrieval index

**Mission Branch**: `feat/agent-knowledge-canonical-homes` (coord topology)
**Created**: 2026-07-22
**Status**: Draft
**Input**: Move 3 of `docs/plans/engineering-notes/agent-knowledge-canonical-homes.md` — close the Common Docs retrieval gap. Charter, doctrine, and glossary already expose `--json` retrieval; Common Docs (`docs/`) is the last canonical knowledge home with no query API, so agents read it by ad-hoc file globbing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — An agent retrieves the relevant Common Docs slice by query, not by globbing (Priority: P1)

An AI agent (or maintainer) needs the documentation relevant to a task — e.g. "how do redirects
work" or "the merge runbook" — without knowing filenames. Today it must glob `docs/**` and read
whole files. It should instead run one command and get back the matching pages with enough metadata
(path, title, the specific heading anchors that matched, a short abstract, Divio type) to decide what
to open.

**Why this priority**: This is the whole mission — a first-class, harness-neutral retrieval surface
over the canonical reference-knowledge home. Every other knowledge home (charter, doctrine, glossary)
already has one.

**Independent Test**: `spec-kitty docs query "redirect" --json` returns a JSON array of matching
`docs/` pages, each with `path`, `title`, matching `anchors`, `abstract`, and `divio_type` — verified
against a fixture docs tree and the live tree.

**Acceptance Scenarios**:

1. **Given** the docs tree with a page whose title/heading/abstract contains the query term, **When**
   `spec-kitty docs query "<term>" --json` runs, **Then** that page appears in the results with its
   `path`, `title`, the `anchors` (heading slugs) that matched, `abstract`, and `divio_type`.
2. **Given** a query that matches nothing, **When** the command runs, **Then** it returns an empty
   JSON array and exits 0 (not an error).
3. **Given** `--divio-type reference` (or `--section <anchor-slug>`), **When** the command runs,
   **Then** results are filtered to that Divio type / to pages containing that heading anchor.
4. **Given** the generated retrieval index is stale relative to the docs frontmatter/headings,
   **When** the freshness gate runs in CI, **Then** it reports drift (mirroring the existing
   page-inventory lockfile drift gate).

### Edge Cases

- A page with no frontmatter `description` → the abstract falls back to its first non-heading
  paragraph (or empty if none), never crashes.
- A page with duplicate heading text → anchors are de-duplicated deterministically (slug + ordinal
  suffix), using the repo's canonical `slugify` convention, so the index is byte-stable.
- ADR / changelog pages that intentionally carry no `description` → included with an empty abstract,
  not flagged as violations (consistent with the description-length gate's exemptions).
- The command run outside a repo / with no docs tree → a clear error, not a stack trace.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Generate a docs retrieval index | As a maintainer, I want a generated per-page index that adds title, heading-anchor slugs, and a short abstract on top of the existing page-inventory metadata, so docs are queryable. | High | Open |
| FR-002 | `spec-kitty docs query` command | As an agent, I want `spec-kitty docs query "<term>" [--json]` to search the index by term across title/heading/abstract and return matching pages. | High | Open |
| FR-003 | Structured JSON result shape | As a harness, I want each result to carry `path`, `title`, matching `anchors`, `abstract`, and `divio_type` in a stable JSON schema, so I can consume it without parsing prose. | High | Open |
| FR-004 | Filter flags | As an agent, I want `--divio-type <type>` and `--section <anchor-slug>` filters so I can narrow to a Divio class or to pages containing a given heading. | Medium | Open |
| FR-005 | Freshness gate for the index | As a maintainer, I want a CI-runnable drift check that regenerates the index from `docs/` and compares it to the committed file, mirroring the page-inventory lockfile gate. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic, byte-stable index | Regenerating the index from an unchanged `docs/` tree produces a byte-identical file (alphabetical by path; deterministic anchor slugs); the freshness gate keys off this. | Reliability | High | Open |
| NFR-002 | Full-tree query latency | A single `docs query` over the whole live `docs/` tree (~500+ pages) returns in under 1 second on a dev machine (in-memory over the pre-generated index; no per-query filesystem walk of doc bodies). | Performance | Medium | Open |
| NFR-003 | Quality gates clean | `ruff` + `mypy --strict` report 0 issues on touched modules; cyclomatic complexity ≤15; every new branch/helper carries a focused test; no new suppressions. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Page-inventory untouched | The existing `docs/development/3-2-page-inventory.yaml` pinned path, its schema, and its consumers (`test_inventory_path_stable.py`, the freshness gate) are NOT changed; the retrieval index is a **sibling artifact** (or a strictly-additive enrichment), not a breaking edit. | Technical | High | Open |
| C-002 | CLI-only, no HTTP server | No REST/GraphQL/HTTP server is introduced. The dossier `DossierAPIHandler` FastAPI port (T033) remains the separate later HTTP option. | Scope | High | Open |
| C-003 | Index scope, not search engine | The index covers **title + heading anchors + a short abstract** only — NOT full document body text. This is structured retrieval, not full-text search. | Scope | High | Open |
| C-004 | Reuse existing machinery | Reuse the `scripts/docs/inventory_lockfile.py` generator + freshness-gate pattern (`parse_frontmatter`, the sorted `rglob` walk, `DivioType`, the drift-compare shape) and the glossary query surface shape (`src/specify_cli/cli/commands/glossary.py`, `spec-kitty glossary … --json`) rather than building parallel infrastructure. The page-inventory's `PageInventoryEntry` is a C-001-pinned frozen schema, so define a **sibling** `DocsQueryEntry` + sibling generator + sibling index file + a new drift-gate entry — do NOT widen the shared dataclass in place. | Technical | Medium | Open |
| C-005 | Anchors are source-heading slugs, not DocFX fragments | Index anchors use the repo's canonical `slugify` + ordinal disambiguation to point an agent at a source heading deterministically. They are NOT reverse-engineered to be byte-identical to the rendered DocFX site's URL fragments; DocFX-exact deep-link fidelity is an explicit non-goal. | Scope | Medium | Open |

### Key Entities

- **Docs retrieval index** (generated artifact): per `docs/**/*.md` page → `path`, `title`, `divio_type`, `anchors[]` (heading slug + text), `abstract`. Deterministic, freshness-gated.
- **Docs query** (CLI verb): term + optional `--divio-type`/`--section` filters → matching index entries as JSON.
- **Anchor**: a `##`/`###` heading's deterministic slug (repo-canonical `slugify` + ordinal suffix for duplicates) — the addressable source-heading a query result points an agent to. NOT guaranteed byte-identical to the rendered DocFX site's fragment (that is a non-goal, C-005).
- **Abstract**: frontmatter `description` else first non-heading paragraph else empty.
- **Title**: frontmatter `title` else the first `# H1` else the path stem (deterministic precedence, for NFR-001 byte-stability).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent can locate the relevant Common Docs page(s) + heading for a task with a single
  `spec-kitty docs query --json` call — no `docs/` globbing — proven by tests against a fixture tree
  and the live tree.
- **SC-002**: The retrieval index is generated + freshness-gated: regenerating from an unchanged tree
  is byte-identical, and a drift is caught by the CI gate (mirroring the page-inventory lockfile).
- **SC-003**: The result JSON is stable and complete (`path`, `title`, `anchors`, `abstract`,
  `divio_type`); no page-inventory path/schema/consumer changed (C-001 held).
- **SC-004**: `ruff` + `mypy --strict` clean; new branches/helpers covered by focused tests; query
  over the full live tree returns in under 1 second.
