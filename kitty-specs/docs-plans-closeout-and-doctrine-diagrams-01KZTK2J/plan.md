# Implementation Plan: docs/plans Closeout and Doctrine Schema Diagrams

**Branch**: `feat/docs-plans-tier3-closeout` | **Date**: 2026-08-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/docs-plans-closeout-and-doctrine-diagrams-01KZTK2J/spec.md`

## Summary

Finish the `docs/plans` curation begun in PR #3324 and give the doctrine documentation code-grounded schema diagrams. Three docs threads (retire sweep with a new `durable` `doc_status` marker; two new domain plans + a `domains/` migration; filling four under-documented artefact kinds) plus a docsite-tooling thread: add local PlantUML rendering to the DocFX pipeline (build-time `plantuml.jar` pre-render wired as a post-DocFX HTML post-processor), governed by an ADR, then author `@startyaml` schema diagrams generated from the frozen doctrine code models with an automated drift guard. Rendering (US3) precedes diagrams (US4).

## Technical Context

**Language/Version**: Python 3.11+ (render step, drift guard, `doc_status` validators); Markdown + YAML frontmatter (docs); PlantUML `@startyaml` (diagram source); a pinned `plantuml.jar` (Java, build-time only)
**Primary Dependencies**: DocFX (`modern` template, existing); pinned `plantuml.jar` (new, build-time); the existing `scripts/docs/` HTML post-processing chain (`glossary_linker.py` is the pattern to mirror); ruamel.yaml; pytest; ruff; mypy
**Storage**: Files — Markdown/YAML docs, generated SVGs (CI-generated into `docs/_site`, not committed), the two docs lockfiles
**Testing**: pytest — `tests/docs/` (existing suite must stay green), a new diagram/code drift guard, the terminology guard; a no-egress assertion on the render path; ATDD-first per charter C-011
**Target Platform**: Linux CI (GitHub Actions `docs-pages.yml` + `docs-build-pr.yml`) producing the published GitHub Pages docsite
**Project Type**: single (repo tooling + documentation)
**Performance Goals**: PlantUML pre-render adds ≤ 60s to the full docs build
**Constraints**: zero doctrine-content egress (local `plantuml.jar` only, no external PlantUML server); `plantuml.jar` pinned by version **and** sha256; SVGs CI-generated not committed; diagrams render on the built docsite only (not github.com source view)
**Scale/Scope**: ~12 artefact-kind schema diagrams; ~11 retire-candidate clusters (3 auto, 8 evidence-gated, 1 deferred); 2 new + 2 migrated domain plans; 1 new render script; 2 workflow edits; 1 ADR + 1 convention amendment; 1 `doc_status` enum value across all validation sites

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`, template set `software-dev-default`). Relevant gates:

- **ATDD-First (C-011)** — the drift guard (FR-010) and the render-step behaviour (FR-006) land red-first with executable tests; docs threads are verified by the docs suite + terminology guard. ✅ satisfiable.
- **Terminology Canon (Mission ≠ feature)** — enforced by the terminology guard; the api-dashboard plan documents killing `Feature:` UI drift without reintroducing it (C-003). ✅
- **Writing, Communication & Diagramming Doctrine** — the ADR (FR-007) must reconcile the PlantUML lane with the existing Mermaid/C4 convention (R-04/#1839). ✅ addressed as an explicit ADR.
- **Quality gates** — new Python (render step, drift guard, `doc_status` change) must pass ruff + mypy with zero suppressions; every new branch/helper gets focused tests (Sonar new-code coverage). ✅
- **No egress / privacy** — NFR-002 forbids sending doctrine content off-machine; the local-jar approach satisfies it, the client-server approach is rejected (C-006). ✅

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/docs-plans-closeout-and-doctrine-diagrams-01KZTK2J/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (retire evidence, doc_status sites, PlantUML approach, artefact schemas)
├── data-model.md        # Phase 1 — the entities (domain plan, retire candidate, artefact model, schema diagram, render step)
├── quickstart.md        # Phase 1 — how to add a schema diagram / run the render + drift guard locally
├── contracts/           # Phase 1 — the render-step contract, the drift-guard contract, the doc_status enum contract
├── occurrence_map.yaml  # Bulk-edit map for the domains/ migration + durable propagation (C-002)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
scripts/docs/
├── plantuml_render.py        # NEW — post-DocFX HTML post-processor: @start* fences -> SVG (local plantuml.jar)
├── glossary_linker.py        # EXISTING — the post-processing pattern to mirror
└── docs_index.py, inventory_lockfile.py, check_docs_freshness.py  # EXISTING lockfile/freshness tooling

.github/workflows/
├── docs-pages.yml            # EDIT — add setup-java + pinned plantuml.jar fetch + render step
└── docs-build-pr.yml         # EDIT — same render step on PR builds

docs/
├── plans/domains/            # NEW home — 4 domain plans migrated here + domains/index.md
│   ├── saas-hosted-sync-domain-plan.md, doctrine-charter-domain-plan.md   # MOVED from docs/plans/
│   ├── packs-extraction-domain-plan.md, api-dashboard-domain-plan.md      # NEW
│   └── index.md
├── plans/index.md            # EDIT — domains/ cluster link; retire-sweep index updates
├── plans/**                  # retire-sweep targets (engineering-notes/, reviews/, refactor/, 3-2-doc-publication/, doctrine/)
├── architecture/doctrine-kinds.md, doctrine-relationships.md   # EDIT — schema diagrams + fill kinds
├── architecture/mission-type-resolution.md                     # EDIT — mission-type/step diagram
├── architecture/diagrams/README.md                             # EDIT — R-04 amendment (PlantUML lane)
└── adr/3.x/2026-08-12-*-plantuml-schema-diagram-rendering.md    # NEW ADR (FR-007)

src/**                        # doc_status validators/enumerations — enumerated in research.md (C-005), extended with `durable`
tests/docs/ (or tests/architectural/)
└── test_doctrine_diagram_drift.py   # NEW — FR-010 drift guard; + render-step + no-egress tests
```

**Structure Decision**: Single-project repo tooling + docs. New code is confined to `scripts/docs/` (render step), the two docs workflows, the `doc_status` validation sites (enumerated in research), and a new drift-guard test. All doctrine code models under `src/doctrine/` are **read-only** sources of truth for the diagrams.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Durable doc_status marker + validator propagation

- **Purpose**: Add a machine-distinguishable `durable` `doc_status` value so the retire sweep never flags a throughline.
- **Relevant requirements**: FR-002, C-005
- **Affected surfaces**: every `doc_status` enumeration/validation site (enumerated in `research.md`); the domain-plan frontmatter
- **Sequencing/depends-on**: none (foundation for IC-02)
- **Risks**: missing a validation site → the new value is rejected somewhere; mitigated by the research enumeration + a test asserting `durable` is accepted everywhere `doc_status` is checked.

### IC-02 — Retire/archive sweep with evidence

- **Purpose**: Retire shipped/superseded plan clusters safely (marker-in-place or move), each with a shipped-evidence line.
- **Relevant requirements**: FR-001, NFR-005, C-001
- **Affected surfaces**: `docs/plans/engineering-notes/**`, `reviews/**`, `refactor/**`, `3-2-doc-publication/**`, `doctrine/**`; `docs/plans/index.md`
- **Sequencing/depends-on**: IC-01 (durable marker must exist so throughlines are exempt)
- **Risks**: premature retirement of not-yet-shipped work; the roadmap retire is out of scope (C-001). Per-doc evidence gate required.

### IC-03 — Two new domain plans with boundary seams

- **Purpose**: Author `packs-extraction` and `api-dashboard` domain plans, each with an explicit scope boundary vs the doctrine-charter plan.
- **Relevant requirements**: FR-003, FR-004, C-003
- **Affected surfaces**: the two new plan files; doctrine-charter plan §3.2/§3.6 (boundary references)
- **Sequencing/depends-on**: none (can precede or parallel IC-04)
- **Risks**: overlap with doctrine-charter §3.2 (packs) / §3.6 (API); mitigated by explicit non-goal statements.

### IC-04 — domains/ migration (bulk edit)

- **Purpose**: Move all four domain plans into `docs/plans/domains/` with an index; update every reference.
- **Relevant requirements**: FR-005, C-002
- **Affected surfaces**: the 4 plan files; `docs/plans/index.md`; the four `3-2-x-*` release docs; SaaS/doctrine-charter §6 cross-refs; the docs lockfiles
- **Sequencing/depends-on**: IC-03 (new plans exist before the move, or move-then-add); occurrence-mapped
- **Risks**: dead links if a reference is missed → covered by `occurrence_map.yaml` + the relative-link-fixer test.

### IC-05 — PlantUML docsite rendering (Phase 0 capability)

- **Purpose**: Add local build-time PlantUML rendering (`plantuml_render.py` post-processor) so `@start*` blocks render on the docsite with zero egress.
- **Relevant requirements**: FR-006, NFR-002, NFR-003, NFR-004, C-004, C-006
- **Affected surfaces**: `scripts/docs/plantuml_render.py`; `docs-pages.yml` + `docs-build-pr.yml`; a sample diagram page for verification
- **Sequencing/depends-on**: none (independent capability); **precedes IC-07**
- **Risks**: build-time cost; jar-pinning integrity; Mermaid non-regression — all covered by NFRs + tests.

### IC-06 — ADR + R-04 convention amendment

- **Purpose**: Govern the PlantUML lane decision (supersede/amend R-04/#1839).
- **Relevant requirements**: FR-007
- **Affected surfaces**: new ADR under `docs/adr/3.x/`; `docs/architecture/diagrams/README.md`
- **Sequencing/depends-on**: co-lands with IC-05
- **Risks**: convention drift if the amendment is vague; keep the Mermaid/C4 default explicit.

### IC-07 — Schema diagrams + drift guard

- **Purpose**: Author `@startyaml` schema diagrams for the priority artefacts, grounded in the frozen code models, with an automated drift guard.
- **Relevant requirements**: FR-008, FR-010, NFR-001
- **Affected surfaces**: `docs/architecture/doctrine-kinds.md`, `doctrine-relationships.md`, `mission-type-resolution.md`; a new drift-guard test; read-only `src/doctrine/**` models
- **Sequencing/depends-on**: IC-05 (rendering must exist)
- **Risks**: diagram/code drift → the drift guard (FR-010) is the mitigation and lands with the diagrams.

### IC-08 — Fill under-documented kinds

- **Purpose**: Add kind documentation for anti-pattern, glossary-pack, action-index, step-contract.
- **Relevant requirements**: FR-009
- **Affected surfaces**: `docs/architecture/doctrine-kinds.md` (+ related)
- **Sequencing/depends-on**: none (pairs naturally with IC-07)
- **Risks**: conflating the DRG `anti_pattern` node with the `styleguides` inline `AntiPattern` example type — call out the distinction.
