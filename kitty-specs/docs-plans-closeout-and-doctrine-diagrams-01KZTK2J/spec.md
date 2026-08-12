# Mission Specification: docs/plans Tier 3 Closeout

**Mission Branch**: `feat/docs-plans-tier3-closeout`
**Created**: 2026-08-12 · **Re-scoped**: 2026-08-12 (split — this is Scope A)
**Status**: Draft
**Input**: Complete the `docs/plans` curation begun in PR #3324 — retire shipped/superseded plan clusters, author the last two domain plans, migrate the domain plans into a `docs/plans/domains/` cluster, and add a machine-distinguishable `durable` `doc_status` marker so throughlines are never swept.

> **Split note.** The post-plan squad recommended splitting the original mission on the docs-closeout / doctrine-diagrams seam (no shared surfaces, zero cross-dependency, and the diagram half is security-sensitive CI work). This mission is **Scope A — docs/plans closeout**. **Scope B** (doctrine artefact schema diagrams + local PlantUML docsite rendering + per-module code→docs READMEs) is a separate follow-on software-dev mission. Its scope is captured in the session design notes. *(The mission slug retains the legacy `…-and-doctrine-diagrams` suffix; identity is `mid8 01KZTK2J`.)*

## Overview

PR #3324 established the two-tier `docs/plans` model, the SaaS and doctrine-charter domain plans, and the curated index. This mission finishes that curation: it retires the shipped/superseded working-note clusters (evidence-gated, roadmap deferred), authors the two remaining domain plans, migrates all four domain plans into one `domains/` home, and adds a reserved `durable` `doc_status` value so a standing throughline is never mistaken for stale draft.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy planning surface (Priority: P1)

A maintainer browsing `docs/plans/` never mistakes a shipped-and-distilled working note for live planning. Shipped/superseded clusters are retired (marked `deprecated`, or moved to an archive directory) with a per-document shipped-evidence record; durable domain plans are protected from that sweep by the reserved `durable` marker.

**Why this priority**: The curation's core value is a planning surface a reader can trust at a glance.

**Independent Test**: Walk `docs/plans/`; confirm every retired cluster carries an evidence line and a valid retirement marker, no durable domain plan was retired, and the docs suite stays green.

**Acceptance Scenarios**:

1. **Given** a plan cluster whose design has shipped (evidenced), **When** it is retired, **Then** it carries a citation to the shipping evidence and the index no longer presents it as live — and its content is preserved, not deleted.
2. **Given** a durable domain plan (`doc_status: durable`), **When** the doc gates run, **Then** the plan is accepted and never flagged as stale/point-in-time.
3. **Given** `3-2-x-milestone-roadmap.md` (blocked on open-core item R), **When** the sweep runs, **Then** it is explicitly left in place and recorded as deferred.

### User Story 2 - Complete, cleanly-homed domain throughlines (Priority: P1)

A reader finds all four domain plans (SaaS, doctrine-charter, packs-extraction, api-dashboard) in one self-cataloging `docs/plans/domains/` home, each stating its scope boundary so the throughlines do not overlap.

**Why this priority**: The throughline model is only coherent once the two `*(planned)*` slots are real and the plans have one predictable home.

**Independent Test**: From the plans index, reach any of the four domain plans in one hop; confirm each new plan declares an explicit boundary against the doctrine-charter plan; confirm zero dead links after the migration.

**Acceptance Scenarios**:

1. **Given** the two new plans, **When** a reader opens the packs-extraction plan, **Then** it scopes itself to the physical extraction/modularization lineage and explicitly non-goals the doctrine-charter plan's pack-ecosystem section (and api-dashboard non-goals the doctrine public-API section).
2. **Given** the `domains/` migration, **When** the docs build runs, **Then** every reference to a moved plan resolves (zero dead links) and the reciprocal `*(planned)*` cross-references become live links.

### Edge Cases

- A retire candidate's backing design is only *partially* shipped → it stays live, recorded as "not yet retireable" with the gap noted.
- The `domains/` migration touches the same path strings across many files → the occurrence map must cover every reference or the relative-link-fixer test fails.
- `durable` is added to the enum but a validation site still rejects it → a test asserting `durable` passes every enumerated gate fails until the site is updated.
- An implementer tries to add `closeout` as a `doc_status` value → rejected: `closeout` is an archive-directory / point-in-time-marker convention that maps to `deprecated`, **not** an enum member.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retire/archive shipped or superseded plan clusters, each with a per-document shipped-evidence record; mechanism is `doc_status: deprecated` in place or move-to-archive; content is never deleted; `3-2-x-milestone-roadmap.md` is deferred (C-001) | US1 | High | Open |
| FR-002 | Add `durable` to the `doc_status` vocabulary as a **reserved, never-retire marker** — amend the authoritative directive `042-common-docs` **first**, then mirror in `scripts/docs/frontmatter_backfill.py:DocStatus` and every validation site; assert `durable ∉ point_in_time` markers | US1 | High | Open |
| FR-003 | Author the `packs-extraction` domain plan with an explicit scope boundary against doctrine-charter §3.2 (pack ecosystem) | US2 | High | Open |
| FR-004 | Author the `api-dashboard` domain plan with an explicit scope boundary against doctrine-charter §3.6 (doctrine public API) | US2 | High | Open |
| FR-005 | Migrate the four domain plans into `docs/plans/domains/` with a `domains/` index; update every reference (plans index, `3-2-x-*` release docs, reciprocal §6 cross-refs) via the occurrence map; regenerate the docs lockfiles | US2 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Vocabulary consistency | `durable` is accepted at **every** enumerated `doc_status` site — directive 042 (authority), the `DocStatus` enum, the styleguide `structural_lint_config` / freshness-SLA gate, and both `tests/docs/` and `tests/doctrine/test_schema_generation_integrity.py` — with the full `tests/docs/` suite + terminology guard green. | Correctness | High | Open |
| NFR-002 | Retirement safety | No retired document is deleted; every retirement preserves content and carries a shipped-evidence citation; the roadmap is deferred. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Roadmap retire deferred | `3-2-x-milestone-roadmap.md` must NOT be retired here (blocked on open-core item R); recorded as deferred. | Technical | High | Open |
| C-002 | Occurrence-mapped bulk edit | The `domains/` migration is a cross-file path change; `meta.json` sets `change_mode: bulk_edit` and a schema-conformant `occurrence_map.yaml` (per `src/doctrine/schemas/occurrence-map.schema.yaml`) drives it so the gate actually fires. | Technical | High | Open |
| C-003 | Terminology canon | Canonical **Mission** (never "feature"); the api-dashboard plan documents eliminating `Feature:` UI drift (#650) without reintroducing it. | Technical | High | Open |
| C-004 | `doc_status` vocabulary authority | The authoritative vocabulary is directive `042-common-docs` (draft/active/deprecated/superseded); the `DocStatus` enum **mirrors** it. `closeout` is a point-in-time-marker / archive-directory convention mapping to `deprecated`, **not** a `doc_status` enum value — it must not be added to the enum. | Technical | High | Open |

### Key Entities

- **Domain plan (throughline)**: a durable, version-spanning plan (`doc_status: durable`) homed under `docs/plans/domains/`; declares its scope boundary vs sibling plans.
- **Retire candidate**: a `docs/plans` document/cluster with a shipped-evidence record + a retire mechanism (`deprecated` in place | move-to-archive) + status (`retired` | `deferred` | `not-retireable`).
- **`doc_status` vocabulary**: the closed set governed by directive 042 (authority) and mirrored by the `DocStatus` enum; `durable` is the new reserved member.
- **`doc_status` validation site**: any surface that enumerates/validates `doc_status` (directive 042, enum, styleguide structural-lint/freshness gates, schema-integrity tests).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Walking `docs/plans/`, a reader finds **zero** shipped/superseded clusters presented as active — each is retired with an evidence citation (roadmap excepted, recorded deferred), and no content is deleted.
- **SC-002**: All **four** domain plans exist and are reachable in **one hop** from the plans index via a single `domains/` cluster; **zero** dead links after migration.
- **SC-003**: `durable` is accepted at **every** enumerated `doc_status` validation site; the full `tests/docs/` suite and the terminology guard pass on the mission branch.
- **SC-004**: Directive 042 (authority) and the `DocStatus` enum agree (4→5 vocabulary), verified by the schema-integrity test; `closeout` remains a non-enum convention.

## Assumptions

- Builds on merged PR #3324 (domain-throughline structure + SaaS/doctrine-charter plans), present on `feat/docs-plans-tier3-closeout`.
- The evidence-gated retire candidates receive per-document tracker/shipping evidence during implementation; the 3 auto-retireable clusters are evidenced by the open-core delivery plan.
- Scope B (doctrine schema diagrams + PlantUML rendering + per-module READMEs) is a separate mission and out of scope here.

## Domain Language

- **Mission** (canonical; never "feature").
- **Domain plan / throughline** — a durable, version-spanning plan; distinct from release-scoped `distil-then-retire` working notes.
- **`durable`** — the reserved `doc_status` value marking a throughline exempt from the retire sweep.
- **`doc_status`** — the documentation lifecycle vocabulary governed by directive 042; `closeout` is a point-in-time-marker convention, not a value.
