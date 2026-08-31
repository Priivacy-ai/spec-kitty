# Implementation Plan: Doctrine, Glossary & Architecture Consolidation

**Branch**: `feat/doctrine-glossary-consolidation-01KTNWFC` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-glossary-architecture-consolidation-01KTNWFC/spec.md`
**Decisions**: [research.md](./research.md) (R-01…R-10, C-005, FR-012)

## Summary

Consolidate Spec Kitty's governance, terminology, and architecture surfaces into single-source-of-truth artefacts and **eliminate parallel mechanisms** (C-005). Three streams run with a phased dependency: (1) restructure/move the architecture-docs + promote the glossary to a top-level canonical surface [bulk-edit reference rewrites], then (2) author new content (refreshed C4, planning/tracking doctrine, Ops ADR, glossary content) into the settled layout, while (3) the code lanes (charter `extends:`, DRG generator/freshness + built-in re-curation) run in parallel. Validation dogfoods the new doctrine by reorganizing the #391 dumping-ground epic.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: spec-kitty CLI; `ruamel.yaml` (doctrine/charter/glossary YAML); doctrine schemas (agent-profile, DRG `graph.yaml`, glossary seed); Mermaid (Markdown C4); `gh` CLI + GitHub GraphQL (FR-012 #391 reorg)
**Storage**: Filesystem only — Markdown/YAML doctrine artefacts, glossary seeds, architecture docs (no database)
**Testing**: `pytest` (incl. `tests/architectural/` — terminology guard, shared-package-boundary), `spec-kitty glossary validate`, `spec-kitty doctor doctrine --json`, DRG freshness gate, charter activation/cascade tests; `ruff` + `mypy`
**Target Platform**: Repo-internal tooling + documentation (developer/CLI)
**Project Type**: single (repo-internal docs + Python tooling)
**Performance Goals**: N/A (authoring/consolidation); determinism required for DRG regeneration and glossary validation
**Constraints**: feature-branch only (C-001); canonical sources/CLI (C-002); Terminology Canon + guard (C-003); charter content preserved, additive `extends:` (C-004); **no parallel mechanisms / single source of truth (C-005)**; new/changed code `ruff`+`mypy` clean
**Scale/Scope**: 5 work-streams · 12 FRs · touches `src/charter/`, `src/glossary/`, `src/doctrine/`, `architecture/`, `docs/`, top-level `glossary/`, `.kittify/`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (Charter loaded: compact, software-dev-default, DIR-001…013.)

- **Shared-package boundary** (ADR 2026-04-25-1): no change to runtime/events/tracker boundaries — this mission is doctrine/docs/charter/glossary, not runtime. ✅
- **Terminology Canon** (C-003): all authored prose + glossary must pass `tests/architectural/test_no_legacy_terminology.py`. Watch "Feature" (issue-type term) in toolguide/styleguide prose. ✅ with care.
- **Doctrine-layer merge semantics** (ADR 2026-05-16-1): charter `extends:` (IC-07) and DRG re-curation (IC-08) must use the activation-engine/cascade, not a parallel path (C-005). ✅
- **⚠️ Self-referential authority-path update:** the charter's "Project authority paths" cite `architecture/2.x/adr/`, `architecture/adrs/`, `glossary/contexts/` — these **move** under this mission. IC-01/IC-02 must update the charter's own references. (Tracked as a bulk-edit reference site.)
- **CI/branch protection:** all work lands on `feat/doctrine-glossary-consolidation-01KTNWFC`; no push to origin/main. ✅

No charter violations requiring Complexity Tracking justification.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-glossary-architecture-consolidation-01KTNWFC/
├── plan.md            # this file
├── research.md        # decisions R-01..R-10, C-005, FR-012
├── data-model.md      # artefact/schema shapes (Phase 1)
├── quickstart.md      # validation walkthrough (Phase 1)
├── contracts/         # charter-extends + DRG-regen contracts (Phase 1)
├── occurrence_map.yaml# bulk-edit reference-rewrite map (IC-01/IC-02)
└── tasks.md           # (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root) — target layout after restructure

```
architecture/                 # LIVING current+future architecture (R-02)
├── README.md                 # boundary rule + navigation (updated)
├── vision/                   # current+future vision (R-03)
├── audience/                 # stakeholder views (existing, retained)
├── diagrams/                 # living C4, Markdown+Mermaid, numbered levels (R-04)
│   ├── 01_context/  02_containers/  03_components/
├── 1.x/  2.x/  3.x/          # versioned history: {adr/, vision/, research/}  (decay target)
glossary/                     # PROMOTED top-level canonical surface (R-01)
├── contexts/                 # (moved from prior locations; charter authority path)
docs/                         # Divio consumption; explanation links UP to architecture (no dup)
src/
├── charter/                  # FR-008 org-charter extends (activation_engine/cascade)
├── glossary/                 # GlossaryScope loader + seed paths (reference rewrites)
└── doctrine/                 # DRG generator/graph.yaml + built-in profiles (FR-009); new doctrine artefacts (FR-001..004)
.kittify/glossaries/          # deployed glossary seeds (reference rewrites)
```

**Structure Decision**: Single-project repo-internal. The architecture/docs/glossary tree is the primary surface; `src/{charter,glossary,doctrine}` are the code surfaces. Layout per R-01…R-04 (living architecture + versioned history; glossary promoted; Divio docs).

## Complexity Tracking

No charter violations. One scope note: this is a **large mission** (5 streams). Decomposition is managed via the phased IC sequencing below, not by relaxing any gate.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs. Sequencing notes encode the R-06 phased dependency; `change_mode` and review/sign-off notes encode R-05 and R-07.

### IC-01 — Promote glossary to a top-level canonical surface
- **Purpose**: Make `glossary/` the single source of truth (C-005, R-01); eliminate the scattered glossary locations.
- **Relevant requirements**: FR-005 (boundary), supports FR-010
- **Affected surfaces**: top-level `glossary/` (+ `contexts/`), `src/glossary/` (`GlossaryScope` loader paths), `.kittify/glossaries/`, `architecture/glossary/` (source), charter "Project authority paths", doctrine/doc cross-links
- **Change mode**: **bulk_edit** — every old→new glossary path enumerated in `occurrence_map.yaml`; hard moves, no stubs
- **Sequencing/depends-on**: none (Phase 1 — runs first)
- **Review/sign-off**: doctrine/charter sign-off (authority-path correctness) + reviewer profile
- **Risks**: missing a reference breaks glossary loading or the charter authority path; the occurrence map must cover all 8 categories

### IC-02 — Establish the living-architecture layout + execute moves
- **Purpose**: Top-level living `architecture/` (vision/, audience/, diagrams/, README boundary rule) with versioned history beneath (R-02/R-03); carry C4 forward; demote obsolete content into version dirs.
- **Relevant requirements**: FR-005, FR-006 (move portion)
- **Affected surfaces**: `architecture/**` (new `vision/`, `diagrams/`, updated `README.md`; `1.x/2.x/3.x/{adr,vision,research}`), `docs/explanation/` (link-up, de-dup), charter authority paths
- **Change mode**: **bulk_edit** — dir moves + cross-reference rewrites in `occurrence_map.yaml`
- **Sequencing/depends-on**: none (Phase 1, parallel with IC-01)
- **Review/sign-off**: **architect-alphonso sign-off** (boundary rule + layout) + reviewer profile
- **Risks**: broken internal doc links; version-dir decay rule must be documented in README to prevent re-drift

### IC-03 — Refresh the 3.x C4 model
- **Purpose**: Update the living C4 (Markdown+Mermaid, numbered levels) to the current 3.x domain model (Governance / Mission-Management / Execution-Runtime, Op/lifecycle tier).
- **Relevant requirements**: FR-006
- **Affected surfaces**: `architecture/diagrams/{01_context,02_containers,03_components}/`
- **Change mode**: normal (additive authoring into settled paths)
- **Sequencing/depends-on**: IC-02 (layout must exist)
- **Review/sign-off**: **architect-alphonso sign-off**
- **Risks**: Mermaid drift from reality (mitigated; generated-C4 swap deferred to #1812)

### IC-04 — Author the planning/tracking doctrine artefacts
- **Purpose**: Procedure + tactic(s) (iterative-deepening, MoSCoW) + styleguide + toolguide for "spec-kitty planning and tracking" (FR-001…004), from the `work/` traces.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004
- **Affected surfaces**: `src/doctrine/` (procedures/tactics/styleguides/toolguides per schema), DRG edges
- **Change mode**: normal (additive); conform to doctrine schemas + register DRG edges (coordinate with IC-08)
- **Sequencing/depends-on**: IC-01/IC-02 (settled layout + glossary)
- **Review/sign-off**: doctrine sign-off + **architect-alphonso sign-off on the styleguide/toolguide** (they encode architecture conventions) + reviewer profile
- **Risks**: terminology guard (C-003) on "Feature"/"features" in prose; DRG must be regenerated after adding artefacts (IC-08)

### IC-05 — Author the Ops ADR (shared Op/lifecycle abstraction)
- **Purpose**: Fill the top architecture gap (FR-007) — ratify "Op as a first-class execution artifact", scoped to also cover pre/post-mission lifecycle (#1804 + #1802 shared abstraction).
- **Relevant requirements**: FR-007
- **Affected surfaces**: `architecture/3.x/adr/` (new ADR per `architecture/adr-template.md`); cross-links from #1804/#1802/#1810
- **Change mode**: normal (additive)
- **Sequencing/depends-on**: IC-02 (layout)
- **Review/sign-off**: **architect-alphonso sign-off**
- **Risks**: must define the shared abstraction (not two parallel ones, C-005) — this ADR is the seam that prevents #1804/#1802 divergence

### IC-06 — Glossary content refresh + record runtime-scope defer
- **Purpose**: Refresh/expand glossary content NOW for the new epic landscape + architectural direction (FR-010); reconcile the planning-and-tracking subset; record explicit defer of runtime-`GlossaryScope` promotion (FR-011, #1418).
- **Relevant requirements**: FR-010, FR-011
- **Affected surfaces**: `glossary/` seeds (canonical), `.kittify/glossaries/planning-and-tracking.yaml`, glossary validation
- **Change mode**: normal (content authoring into the promoted surface)
- **Sequencing/depends-on**: IC-01 (glossary promoted)
- **Review/sign-off**: doctrine/glossary sign-off + reviewer profile
- **Risks**: `spec-kitty glossary validate` must pass; terminology guard

### IC-07 — Charter `extends:` (additive multi-org config)
- **Purpose**: Implement `org-charter.yaml` `extends:` as additive merge with base-org precedence + cycle detection, integrated with the existing `charter.activation_engine`/cascade — **no parallel mechanism** (FR-008, R-10, C-005).
- **Relevant requirements**: FR-008
- **Affected surfaces**: `src/charter/` (activation_engine, cascade, org-charter loader), charter schema, tests
- **Change mode**: normal (code)
- **Sequencing/depends-on**: none (Phase 3 — parallel code lane)
- **Review/sign-off**: doctrine/charter sign-off + reviewer profile; `ruff`/`mypy` clean (NFR-002)
- **Risks**: cycle detection; must reuse activation/cascade, not fork; preserve existing charter content (C-004)

### IC-08 — DRG generator/freshness + built-in DRG & profile re-curation
- **Purpose**: Close DRG gaps (regeneration command + symmetric profile-edge detection) and **sanitize/re-curate the built-in DRG + agent profiles** to absorb the new doctrine (IC-04) and prune stale/duplicate edges (FR-009, R-09).
- **Relevant requirements**: FR-009
- **Affected surfaces**: `src/doctrine/` DRG generator + `graph.yaml`, built-in `agent_profiles/`, freshness test
- **Change mode**: normal (code + curated data)
- **Sequencing/depends-on**: re-curation pass depends on IC-04 (new artefacts must exist to be graphed); the generator/freshness code does not
- **Review/sign-off**: doctrine sign-off + reviewer profile; freshness gate + `ruff`/`mypy` clean
- **Risks**: regen must be deterministic; re-curation must not drop valid edges

### IC-09 — #391 doctrine usage-test (validation)
- **Purpose**: Dogfood the new doctrine (IC-04) by reorganizing the #391 dumping-ground epic — split, reparent children to functional homes, close #391 as superseded (FR-012, SC-6).
- **Relevant requirements**: FR-012
- **Affected surfaces**: GitHub tracker (epics/sub-issues via `gh`/GraphQL); produces a usage-test record in `work/`
- **Change mode**: normal (tracker operations, not repo files)
- **Sequencing/depends-on**: IC-04 (the procedure/styleguide must exist to be applied)
- **Review/sign-off**: reviewer profile; success = SC-1 demonstrated on a real case
- **Risks**: community-precedence on any dedup; honour the toolguide rate-limit/mechanics findings
