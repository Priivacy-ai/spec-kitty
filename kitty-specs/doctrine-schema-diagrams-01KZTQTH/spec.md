# Mission Specification: Doctrine Schema Diagrams and PlantUML Rendering

**Mission Branch**: `feat/doctrine-schema-diagrams`
**Created**: 2026-08-12 (Scope B of the docs-plans/doctrine split)
**Status**: Draft
**Input**: Make the doctrine layer legible — add local PlantUML rendering to the DocFX docsite, author code-grounded `@startyaml` schema diagrams of the doctrine artefacts with an automated drift guard, fill the genuinely-thin artefact kinds, and add small pointer-only READMEs to the doctrine source modules so agents and maintainers reach the canonical docs in one hop.

> **Split note.** Scope B of a two-mission split (Scope A = docs/plans closeout, mission `…-01KZTK2J`). This mission carries the security-sensitive CI work (external `plantuml.jar`) and the diagram/README enrichment. The findings from Scope A's post-plan adversarial squad are baked into this spec.

## Overview

The doctrine artefact model is documented in prose but has **no schema diagrams** today. This mission adds them — generated from the frozen code models so they cannot drift — after first adding the rendering capability the docsite lacks (it renders Mermaid, not PlantUML). It also lowers the barrier for future missions and agentic harnesses: small pointer READMEs bridge each source module to its canonical documentation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PlantUML renders on the docsite, locally (Priority: P1)

A contributor adds a `@startyaml` block to a doctrine page and, on the built docsite, sees it rendered as an SVG — produced by a local build-time step that sends no doctrine content off-machine, and that leaves the existing Mermaid/C4 diagrams untouched.

**Why this priority**: Prerequisite capability for the schema diagrams (US2).

**Independent Test**: Add a sample `@startyaml` block, build the docsite, confirm the page shows a rendered SVG with descriptive alt text; run the render in a network-denied namespace and confirm success; confirm a Mermaid diagram still renders.

**Acceptance Scenarios**:

1. **Given** a page with a ` ```plantuml `-fenced `@startyaml` block, **When** the docs build runs, **Then** the published HTML contains a rendered SVG (with alt/aria text) in place of the fence.
2. **Given** the render step, **When** it runs inside a network-denied namespace (`unshare -rn`), **Then** it still succeeds — proving zero egress.
3. **Given** an existing Mermaid diagram, **When** PlantUML rendering is enabled, **Then** the Mermaid diagram renders unchanged.

### User Story 2 - Code-grounded doctrine schema diagrams (Priority: P1)

A reader sees schema diagrams for the doctrine artefacts, and they always match the code because they are generated from the canonical frozen models and enforced by a drift guard that introspects the models (never a hand-copied count).

**Why this priority**: The primary enrichment goal; depends on US1.

**Independent Test**: Open the doctrine docs; confirm each priority artefact kind has a schema diagram; run the drift guard and confirm each diagram's field set matches its model (with alias normalization and nested-model recursion).

**Acceptance Scenarios**:

1. **Given** the agent-profile schema diagram, **When** compared to `AgentProfileSchema` (kebab aliases normalized via `FieldInfo.alias or name`, recursing into its nested models), **Then** the field sets match.
2. **Given** the DRG diagram bound to `DRGNode`+`DRGEdge`+`NodeKind`+`Relation`, **When** the guard runs, **Then** it derives `NodeKind` (16 members) and `Relation` (15) from `list(...)` — never a literal — and matches.
3. **Given** a field added to any bound model, **When** the guard runs, **Then** it FAILS until the diagram is updated.

### User Story 3 - Code→docs navigation READMEs (Priority: P2)

An agent or maintainer landing in a doctrine source module finds a small README that points (not copies) to the canonical docs — the doctrine-kinds entry, the schema diagram, and the owning domain plan — reaching them in one hop.

**Why this priority**: Serves the mission's "make the codebase legible for future review/spec work" goal; low-risk, high-leverage.

**Independent Test**: Confirm each covered module has a `README.md`; confirm its links resolve; confirm it contains no duplicated schema/field content (pointer-only).

**Acceptance Scenarios**:

1. **Given** `src/doctrine/agent_profiles/`, **When** an agent opens its `README.md`, **Then** it finds a one-line description + resolving links to the doctrine-kinds entry, the schema diagram, and the owning domain plan — and no copied field content.
2. **Given** a module that already has a README, **When** this mission runs, **Then** the existing README is extended, not clobbered.

### User Story 4 - No genuinely-thin artefact kinds (Priority: P3)

A reader looking up `glossary-pack` or `anti-pattern` finds a kind description; the genuinely-thin kinds are filled (step-contract is already documented — augment only).

**Why this priority**: Completes coverage; not blocking.

**Independent Test**: Confirm the doctrine-kinds catalog documents `glossary-pack` and `anti-pattern`; confirm `action-index` is documented in `mission-type-resolution.md` (not the kinds catalog — it is not an artefact kind); confirm the DRG `anti_pattern` node is not conflated with the `styleguides` inline `AntiPattern` example type.

**Acceptance Scenarios**:

1. **Given** the kinds catalog, **When** a reader looks up `glossary-pack`, **Then** a kind description is present; `action-index` is NOT added as a kind (it is a mission concept, documented under mission-type resolution).

### Edge Cases

- A `@startyaml` block is malformed → the build fails with the offending page/line (fail-closed).
- The pinned `plantuml.jar` sha256 mismatches → build fails before rendering from an unverified binary.
- A bound model gains a field → the drift guard fails until the diagram is regenerated.
- A diagram's model has kebab aliases → the guard normalizes to `FieldInfo.alias or name`; a naive `model_fields` compare is rejected as fake-green.
- A README duplicates schema content → rejected in review (pointer-only; C-005).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Add local build-time PlantUML rendering (`scripts/docs/plantuml_render.py`, a post-DocFX HTML post-processor mirroring `glossary_linker.py`) that replaces ` ```plantuml `-fenced `@start*` blocks in `docs/_site` with SVGs; pin the insertion point in the ordered post-processor chain; pin `plantuml.jar` by version+sha256; run with `-DPLANTUML_SECURITY_PROFILE=SANDBOX`; each injected SVG carries descriptive alt/aria text | US1 | High | Open |
| FR-002 | Record the rendering decision as an ADR that cites the existing `plantuml-diagramming.toolguide.yaml`, amends R-04/#1839 with a precise carve-out (R-04 unchanged for hand-authored C4; new lane = generated, docsite-only schema diagrams), and positions schema diagrams relative to the charter's C4-zoom doctrine | US1 | High | Open |
| FR-003 | Author `@startyaml` typed-placeholder schema diagrams for the priority artefacts — agent-profile, mission-type/step, DRG, artefact-kind vocabulary — generated from the frozen code models; place the mission-type/step (and action-index) diagram in `mission-type-resolution.md`, the DRG in `doctrine-relationships.md`, the cross-kind overview in `doctrine-kinds.md` | US2 | High | Open |
| FR-004 | Provide an automated drift guard: introspect each bound model's field set (Pydantic `model_fields` with `FieldInfo.alias or name` normalization + recursion into nested models; frozen-dataclass `fields()`; StrEnum members via `list(EnumType)` — never a hand-copied count), support 1:N multi-model bindings, dispatch across the three model families, and FAIL on any field-set mismatch; bind by `file:class` to disambiguate the `AntiPattern` name-clash | US2 | High | Open |
| FR-005 | Add a small **pointer-only** `README.md` to each doctrine source module (and domain-relevant modules) linking the doctrine-kinds entry, the schema diagram, and the owning domain plan; extend existing READMEs rather than clobber; a light check confirms each covered module has a README and its links resolve | US3 | Medium | Open |
| FR-006 | Fill kind documentation for the genuinely-thin kinds (`glossary-pack`, `anti-pattern`); `step-contract` is augment-only (already documented); `action-index` is documented under mission-type resolution, not the kinds catalog | US4 | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Diagram/code fidelity | Every schema diagram matches its source model with **zero** field drift, enforced by the FR-004 guard, with all counts/members derived by introspection (`list(NodeKind)` = 16, etc.), never hand-copied. | Correctness | High | Open |
| NFR-002 | No doctrine-content egress | Proven by two mechanisms: (a) the render invocation asserts `-DPLANTUML_SECURITY_PROFILE=SANDBOX`; (b) the render step runs successfully inside a network-denied namespace (`unshare -rn`). A URL-grep is a secondary lint only. | Security/Privacy | High | Open |
| NFR-003 | Reproducible build | `plantuml.jar` pinned by version **and** sha256; SVGs CI-generated (not committed). Added build time (target ≤ 60s) is a **monitored budget/warning**, not a hard per-PR gate (flakiness policy). | Reliability | Medium | Open |
| NFR-004 | Non-regression | Existing Mermaid/C4 diagrams render unchanged; the full `tests/docs/` suite + terminology guard stay green. | Compatibility | High | Open |
| NFR-005 | Accessibility | Every injected SVG carries descriptive alt/aria text (charter Diagramming/Documentation accessibility rule + the `docs-accessibility` styleguide). | Accessibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Local rendering only | Rendering uses a local `plantuml.jar`; the client-side PlantUML-server approach is rejected on egress grounds. | Technical | High | Open |
| C-002 | Docsite-only rendering | Pre-rendered SVGs render only on the built docsite, not on github.com source view; documented and accepted. | Business | Medium | Open |
| C-003 | Introspection, never hand-counts | The drift guard derives every field set/enum member from the live model (`list(NodeKind)` → 16, `Relation` → 15, `ArtifactKind` → 12); no literal counts in diagram or guard. | Technical | High | Open |
| C-004 | Correct doctrine filing | `action-index` is NOT an artefact kind (document under mission-type resolution, not the kinds catalog); `step-contract` is already documented (augment-only); do not conflate `styleguides` `AntiPattern` with the DRG `anti_pattern` node. | Technical | High | Open |
| C-005 | READMEs are pointers, not copies | Module READMEs link the canonical docs; they never duplicate schema/field content (no new drift surface) and sit outside the FR-004 guard. | Technical | High | Open |
| C-006 | Governed reconciliation | The FR-002 ADR must cite the active `plantuml-diagramming` toolguide and reconcile the README-R-04 "generation out of scope" line against the charter diagramming doctrine — not only R-04/#1839. | Technical | Medium | Open |

### Key Entities

- **PlantUML render step**: the local build-time post-DocFX HTML post-processor.
- **Doctrine artefact model**: the frozen code model (`AgentProfileSchema`, `MissionStep`/`MissionStepContract`, `ActionIndex`, `DRGNode`/`DRGEdge`/`NodeKind`/`Relation`, `ArtifactKind`, per-kind models) — read-only source of truth.
- **Schema diagram**: a `@startyaml` typed-placeholder bound (by `file:class`, possibly 1:N) to its model(s) for the drift guard.
- **Module README**: a pointer-only `README.md` bridging a source module to its canonical docs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The published docsite renders the schema diagrams; a network-denied-namespace build check confirms **zero** doctrine content egresses.
- **SC-002**: **100%** of authored schema diagrams match their source model (alias-normalized, nested-recursed) with zero field drift, proven by the FR-004 guard in CI.
- **SC-003**: Each priority artefact kind has a schema diagram; the drift guard derives all enum members by introspection (`NodeKind`=16 verified live).
- **SC-004**: Every covered doctrine source module has a pointer-only `README.md` whose links resolve; none duplicate schema content.
- **SC-005**: `glossary-pack` and `anti-pattern` have kind descriptions; `action-index` is documented under mission-type resolution (not the kinds catalog); the full `tests/docs/` suite + terminology guard pass.

## Assumptions

- Builds on merged PR #3324 (doctrine-charter/SaaS domain plans + the docs structure) present on `main`.
- The DocFX pipeline runs an ordered `scripts/docs/` HTML post-processing chain over `docs/_site` (verified — `glossary_linker.py` is the pattern); the PlantUML step slots into it.
- Doctrine code models are `frozen=True, extra="forbid"` (closed field sets), so diagrams can depict complete schemas.
- Scope A (docs/plans closeout) is a separate mission; the domain plans it produces are the READMEs' link targets.

## Domain Language

- **Mission** (canonical; never "feature").
- **Doctrine artefact kind** — a governed artefact type; the 12 `ArtifactKind` members. `action-index` and `mission-type` are mission concepts, NOT artefact kinds.
- **Schema diagram** — a code-generated `@startyaml` depiction of an artefact model, drift-guarded.
- **`durable` / domain plan** — defined in Scope A; the READMEs link to those plans.
