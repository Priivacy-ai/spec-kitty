# Mission Specification: docs/plans Closeout and Doctrine Schema Diagrams

**Mission Branch**: `feat/docs-plans-tier3-closeout`
**Created**: 2026-08-12
**Status**: Draft
**Input**: Complete the `docs/plans` curation begun in PR #3324 (retire shipped/superseded plan clusters; author the last two domain plans; migrate the domain plans into a `domains/` cluster; codify the throughline lifecycle marker) and enrich the doctrine documentation with code-grounded PlantUML schema diagrams of the doctrine artefacts — which first requires adding local PlantUML rendering to the DocFX docsite.

## Overview

Following PR #3324 (which established the two-tier `docs/plans` model, the SaaS and doctrine-charter domain plans, and the curated index) and PR #3319 (meta.json seam, merged), this mission finishes the planning-surface curation and gives the doctrine documentation its first schema diagrams. The diagrams are generated from the canonical, frozen doctrine code models so they cannot drift from the artefacts they describe. Because the docsite (stock DocFX `modern`) renders Mermaid but not PlantUML, the mission also adds a local, build-time PlantUML rendering capability as the prerequisite for the diagrams.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy planning surface (Priority: P1)

A maintainer browsing `docs/plans/` should never mistake a shipped-and-distilled working note for live planning. Shipped/superseded clusters are retired (marked `superseded`/`closeout` in place, or moved to an archive) with a per-document shipped-evidence record; durable domain plans are protected from the same sweep by a machine-distinguishable marker.

**Why this priority**: The curation's core value is a planning surface a reader can trust at a glance; without it the throughline model added in #3324 is undermined by stale neighbours.

**Independent Test**: Walk the `docs/plans/` index and subdirectories; confirm every retired cluster carries an evidence line and a retirement marker, no durable domain plan was swept, and the docs test suite stays green.

**Acceptance Scenarios**:

1. **Given** a plan cluster whose design has shipped (evidenced in the open-core plan), **When** the sweep runs, **Then** the cluster is marked retired with a citation to the shipping evidence, and the index no longer presents it as live.
2. **Given** a durable domain plan, **When** the retire tooling runs, **Then** the plan is skipped because it carries the durable marker.
3. **Given** the `3-2-x-milestone-roadmap.md` (retire blocked on open-core item R), **When** the sweep runs, **Then** it is explicitly left in place and recorded as deferred.

### User Story 2 - Complete, cleanly-homed domain throughlines (Priority: P1)

A reader looking for a domain's standing strategy finds all four domain plans (SaaS, doctrine-charter, packs-extraction, api-dashboard) in one self-cataloging `docs/plans/domains/` home, each stating its scope boundary so the throughlines do not overlap.

**Why this priority**: The throughline model is only coherent once the two `*(planned)*` slots are real and the plans have one predictable home.

**Independent Test**: From the plans index, reach any of the four domain plans in one hop; confirm the packs-extraction and api-dashboard plans each declare an explicit boundary against the doctrine-charter plan; confirm no dangling links after the migration.

**Acceptance Scenarios**:

1. **Given** the two new plans are authored, **When** a reader opens the packs-extraction plan, **Then** it scopes itself to the physical extraction/modularization lineage and explicitly non-goals the doctrine-charter plan's pack-ecosystem section.
2. **Given** the `domains/` migration, **When** the docs build runs, **Then** every internal reference to a moved domain plan resolves (zero dead links) and the reciprocal `*(planned)*` cross-references are now live links.

### User Story 3 - PlantUML renders on the docsite, locally (Priority: P2)

A contributor adds a `@startjson`/`@startyaml` block to a docs page and, on the built docsite, sees it rendered as an SVG diagram — produced by a local build-time render step that sends no doctrine content off-machine.

**Why this priority**: This is the prerequisite capability for the schema diagrams (US4); it is a discrete, independently valuable docsite enhancement.

**Independent Test**: Add a sample `@startyaml` block to a test page, build the docsite, and confirm the page shows a rendered SVG; confirm the render runs entirely locally (no network calls to a PlantUML server) and that existing Mermaid/C4 diagrams still render.

**Acceptance Scenarios**:

1. **Given** a page with a `@startyaml` block, **When** the docs build runs, **Then** the published HTML contains a rendered SVG in place of the fenced block.
2. **Given** the render step, **When** the build runs offline, **Then** it still succeeds using a pinned local `plantuml.jar` (no external server dependency).
3. **Given** an existing Mermaid diagram, **When** the build runs with PlantUML rendering enabled, **Then** the Mermaid diagram still renders unchanged.

### User Story 4 - Code-grounded doctrine schema diagrams (Priority: P2)

A reader of the doctrine documentation sees schema diagrams for the doctrine artefacts (agent-profile, mission-type/step, the DRG, the artefact-kind vocabulary, and others), and those diagrams always match the code because they are generated from the canonical frozen models.

**Why this priority**: The primary enrichment goal; depends on US3's rendering capability.

**Independent Test**: Open the doctrine docs pages; confirm each priority artefact kind has a schema diagram; run the drift guard and confirm each diagram's fields match its code model exactly.

**Acceptance Scenarios**:

1. **Given** the agent-profile schema diagram, **When** compared to `AgentProfileSchema`, **Then** its fields/structure match the model field-for-field.
2. **Given** a change to a doctrine code model that a diagram describes, **When** the drift guard runs, **Then** it fails until the diagram is regenerated/updated.

### User Story 5 - No under-documented artefact kinds (Priority: P3)

A reader looking up any doctrine artefact kind finds a description; the four previously thin/absent kinds (anti-pattern, glossary-pack, action-index, step-contract) now have kind documentation.

**Why this priority**: Completes coverage; valuable but not blocking the throughline or diagram goals.

**Independent Test**: Confirm the doctrine-kinds catalog has an entry for all documented kinds, including the four previously missing/weak ones.

**Acceptance Scenarios**:

1. **Given** the doctrine-kinds catalog, **When** a reader looks up `glossary-pack` or `anti-pattern`, **Then** a kind description is present (and the DRG `anti_pattern` node is not conflated with the `styleguides` inline `AntiPattern` example type).

### Edge Cases

- A retire candidate's backing design is only *partially* shipped → it stays live and is recorded as "not yet retireable" with the gap noted (no premature retirement).
- The `domains/` migration and a durable-marker rename touch the same reference strings across many files → an occurrence map must cover every reference or the build fails on a dead link.
- A doctrine code model gains a field after a diagram is authored → the drift guard fails, forcing the diagram back in sync.
- The pinned `plantuml.jar` sha256 does not match on download → the build fails closed rather than rendering from an unverified binary.
- A page mixes Mermaid and PlantUML blocks → both render, each via its own path.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retire/archive shipped or superseded plan clusters, each with a per-document shipped-evidence record and a chosen mechanism (in-place `superseded`/`closeout` marker or move-to-archive) | As a maintainer, I want stale plans retired with evidence so the planning surface stays trustworthy. | High | Open |
| FR-002 | Introduce a machine-distinguishable `durable` `doc_status` value; apply it to the domain plans; make the retire tooling and doc gates skip `durable` pages | As a maintainer, I want durable throughlines exempt from the retire sweep. | High | Open |
| FR-003 | Author the `packs-extraction` domain plan with an explicit scope boundary against the doctrine-charter plan's pack-ecosystem section | As a reader, I want the packs-extraction strategy documented without overlapping a sibling throughline. | High | Open |
| FR-004 | Author the `api-dashboard` domain plan with an explicit scope boundary against the doctrine-charter plan's public-API section | As a reader, I want the api/dashboard strategy documented distinctly from the doctrine API. | High | Open |
| FR-005 | Migrate the four domain plans into `docs/plans/domains/` with a `domains/` index; update every internal reference (plans index, `3-2-x-*` release docs, reciprocal `§6` cross-refs) via an occurrence map | As a reader, I want all domain plans in one predictable home with no broken links. | High | Open |
| FR-006 | Add PlantUML rendering to the DocFX docsite via a local build-time pre-render step (post-DocFX HTML post-processor) that replaces `@startjson`/`@startyaml` blocks with generated SVGs | As a contributor, I want PlantUML diagrams to render on the docsite. | High | Open |
| FR-007 | Record the PlantUML-rendering decision as an ADR and amend the R-04 diagram convention (and its #1839 basis) to carve a governed PlantUML lane for schema diagrams | As a maintainer, I want the rendering decision and convention change governed and traceable. | Medium | Open |
| FR-008 | Author `@startyaml` schema diagrams for the priority artefacts (agent-profile, mission-type/step/action-index, DRG, artefact-kind vocabulary), generated from the canonical frozen code models, placed in the doctrine-docs cluster | As a reader, I want visual, accurate schemas of the doctrine artefacts. | High | Open |
| FR-009 | Add kind documentation for the four under-documented kinds: anti-pattern, glossary-pack, action-index, step-contract | As a reader, I want every artefact kind documented. | Low | Open |
| FR-010 | Provide an automated drift guard that fails when a schema diagram no longer matches its source code model | As a maintainer, I want diagrams that cannot silently drift from code. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Diagram/code fidelity | Every schema diagram matches its source model with **zero** field drift, enforced by the FR-010 guard in CI. | Correctness | High | Open |
| NFR-002 | No doctrine-content egress | The PlantUML render sends **zero** bytes of doctrine content off-machine: rendering uses a local `plantuml.jar` only, with **no** call to any external PlantUML server, verified by the absence of network egress in the render path. | Security/Privacy | High | Open |
| NFR-003 | Bounded, reproducible build | `plantuml.jar` is pinned by version **and** sha256; SVGs are generated in CI (not committed); the PlantUML pre-render adds ≤ 60s to the full docs build. | Reliability | Medium | Open |
| NFR-004 | Non-regression of existing rendering | Existing Mermaid/C4 diagrams render unchanged and the full `tests/docs/` suite plus the terminology guard stay green. | Compatibility | High | Open |
| NFR-005 | Retirement safety | No retired document is deleted outright; every retirement preserves the content (marker-in-place or move) and carries a shipped-evidence citation. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Roadmap retire deferred | `3-2-x-milestone-roadmap.md` must NOT be retired in this mission (blocked on open-core item R); it is recorded as deferred. | Technical | High | Open |
| C-002 | Occurrence-mapped bulk edits | The `domains/` migration and the `doc_status: durable` propagation are cross-file same-string changes and MUST be driven by an occurrence map (bulk-edit guardrail) so no reference/validator is missed. | Technical | High | Open |
| C-003 | Terminology canon | Canonical **Mission** (never "feature"); the api-dashboard plan must document eliminating `Feature:` UI drift (#650) without reintroducing it. | Technical | High | Open |
| C-004 | Docsite-only diagram rendering | Pre-rendered SVGs render only on the built docsite, not on github.com source view; this limitation is documented and accepted. | Business | Medium | Open |
| C-005 | Enum propagation | Adding `doc_status: durable` MUST update every place `doc_status` is enumerated/validated (schema, gates, tooling) so the new value is not rejected. | Technical | High | Open |
| C-006 | Local rendering only | The client-side PlantUML-server approach is rejected on egress grounds; only the local build-time `plantuml.jar` approach is permitted. | Technical | High | Open |

### Key Entities

- **Domain plan (throughline)**: a durable, version-spanning plan (`doc_status: durable`) homed under `docs/plans/domains/`; holds a domain's invariants and cross-references release-scoped epics.
- **Retire candidate**: a `docs/plans` cluster/document with an associated shipped-evidence record and a chosen retire mechanism.
- **Doctrine artefact model**: the canonical frozen code model for an artefact kind (e.g. `AgentProfileSchema`, `MissionStep`, `DRGNode/Edge`, `ArtifactKind`) — the source of truth for a diagram.
- **Schema diagram**: a `@startyaml` typed-placeholder rendering of an artefact model, plus its drift-guard binding to the model.
- **PlantUML render step**: the local, build-time post-DocFX HTML post-processor that turns `@start*` blocks into SVGs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Walking `docs/plans/`, a reader finds **zero** shipped/superseded working-note clusters presented as active — each is retired with an evidence citation (roadmap excepted, recorded deferred).
- **SC-002**: All **four** domain plans exist and are reachable in **one hop** from the plans index via a single `domains/` cluster; **zero** dead links after migration.
- **SC-003**: **100%** of authored schema diagrams match their source code model with zero field drift, proven by the drift guard in CI.
- **SC-004**: Each priority artefact kind (agent-profile, mission-type, step-contract/action-index, DRG, artefact-kind vocabulary) has a schema diagram, and the four previously under-documented kinds now have kind descriptions.
- **SC-005**: The published docsite renders the schema diagrams, and a build-time check confirms **zero** doctrine content egresses during rendering.
- **SC-006**: The full `tests/docs/` suite and the terminology guard pass on the mission branch.

## Assumptions

- Builds on merged PR #3324 (domain-throughline structure + SaaS/doctrine-charter plans) and PR #3319 (meta.json seam) — both present on `feat/docs-plans-tier3-closeout`.
- The 8 human-judgment retire candidates receive per-document tracker/shipping evidence during implementation; the 3 auto-retireable clusters are evidenced by the open-core delivery plan.
- The PlantUML integration follows the investigated approach: a local build-time `plantuml.jar` pre-render wired as a post-DocFX HTML post-processor (mirroring the existing `glossary_linker.py` chain), pinned by version+sha256, SVGs generated in CI.
- Doctrine code models are `frozen=True, extra="forbid"` (closed field sets), so diagrams can depict a complete schema safely.

## Domain Language

- **Mission** (canonical; never "feature") — the unit of governed work.
- **Domain plan / throughline** — a durable, version-spanning plan; distinct from release-scoped `distil-then-retire` working notes.
- **Doctrine artefact kind** — a governed artefact type (agent-profile, mission-type, step-contract, directive, tactic, styleguide, toolguide, paradigm, procedure, glossary-pack, template, asset, anti-pattern) and the DRG (nodes/edges/relations).
- **`durable`** — the `doc_status` value marking a throughline exempt from the retire sweep.
