# Mission Specification: Doctrine, Glossary & Architecture Consolidation

**Mission ID**: 01KTNWFC3B1ZGFR9FTT77X7H2Y
**Slug**: doctrine-glossary-architecture-consolidation
**Type**: software-dev
**Target branch**: feat/doctrine-glossary-consolidation-01KTNWFC
**Tracker**: epic #1799 (Charter & Doctrine); bundles #1811, #1805, #1397, #1755, #1418

## Purpose

Following a full issue-tracker remediation (see repo `work/` traces), turn the proven planning/tracking patterns and the surfaced architecture gaps into durable, governed artefacts. The mission authors the planning/ticketing/tracing doctrine, restructures the architecture-vs-docs boundary with refreshed C4 models and a `vision/` home, closes two charter/DRG tooling gaps, and refreshes the glossary for the new epic landscape — so governance, terminology, and architecture stay legible and aligned.

## User Scenarios & Testing

**Primary actor:** a Spec Kitty maintainer / operating agent organizing or extending the project's governance and architecture surfaces.

- **Scenario A — author doctrine:** A maintainer needs to organize the tracker or onboard a new contributor to that discipline. They consult a single planning/tracking **procedure + tactics + styleguide + toolguide** instead of re-deriving it from scattered notes. *Success:* the artefacts exist, validate, and are discoverable via the doctrine surfaces.
- **Scenario B — navigate architecture:** A contributor changing a structural boundary opens `architecture/` and finds a clear architecture-vs-docs split, current C4 drilldowns, and a `vision/` home for forward-looking material distinct from ratified decisions. *Success:* every active functional epic resolves to a stable architecture/vision doc (no orphan epics in the correlation matrix).
- **Scenario C — extend a charter:** An org maintainer declares `extends:` in `org-charter.yaml` to inherit/add charter config from a base org. *Success:* the extended charter resolves additively and validates.
- **Scenario D — regenerate doctrine graph:** A maintainer edits a profile/artifact and runs a single DRG regeneration command; freshness checks detect profile-edge changes symmetrically. *Success:* DRG regenerates deterministically and the freshness gate passes.
- **Edge/exception:** Glossary or doctrine edits that fail schema validation must block (not silently ship); the terminology guard must reject forbidden terms.

## Functional Requirements

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-001 | Author the **planning/ticketing/tracing procedure** (tracker-organisation workflow: inventory → classify roots → drain closed epics / collapse passthrough tiers / relabel meta-trackers → re-slice → sweep + flag overlaps → dedup → hygiene → verify). | #1811 | Draft |
| FR-002 | Author **tactic(s)**: iterative-deepening review (widening time windows) and the MoSCoW prioritisation *approach* (scoping lens, distinct from `priority:Px`). | #1811 | Draft |
| FR-003 | Author the **styleguide**: functional-epic-vs-meta-tracker rule, community-precedence on dedup, label/type/priority conventions (single `priority:Px`; `bug`⟺Bug; `triage:*`, `usability`, `future`), epic naming, "no ticket list in epic body". | #1811 | Draft |
| FR-004 | Author the **toolguide**: gh CLI + GitHub GraphQL mechanics & gotchas (sub-issues API, node-id vs db-id, batched parent lookups, secondary-rate-limit loop trap, auth). | #1811 | Draft |
| FR-005 | **Reconcile** the `architecture/` vs `docs/**` boundary (ratified architecture vs explanatory docs): eliminate residual parallel content, introduce a `vision/` directory for forward-looking material, and delete pointer stubs — a single source of truth per surface (C-005). | #1805 | Draft |
| FR-006 | Refresh the **C4 drilldowns** (context → container → component) for the current 3.x system. | #1805 | Draft |
| FR-007 | Fill architecture gaps by authoring the **Ops ADR**, scoping its abstraction to also cover pre/post-mission lifecycle (the shared Op shape across #1804 and #1802). | #1805 / #1804 / #1802 | Draft |
| FR-008 | Implement **`org-charter.yaml` `extends:`** for additive multi-org charter configuration. | #1397 | Draft |
| FR-009 | Close **DRG generator/freshness gaps** (regeneration command + symmetric profile-edge detection) **and sanitize/re-curate the built-in DRG and agent profiles** — fold in this mission's new doctrine additions and prune stale/duplicate edges/profiles so the graph reflects the consolidated doctrine. | #1755 | Draft |
| FR-010 | **Reconcile and refresh the glossary**: confirm the top-level `glossary/` as the single canonical surface (delete the residual `architecture/glossary/` pointer — C-005), then expand content for the new epic landscape and architectural direction; reconcile the planning-and-tracking subset terms. | glossary | Draft |
| FR-011 | **Defer** promoting the planning-and-tracking subset to a runtime `GlossaryScope`; record an explicit deferral with rationale (reassess under #1418). | #1418 | Draft |
| FR-012 | **Validate the new doctrine by applying it to #391**: use the authored procedure/tactic/styleguide to split the #391 dumping-ground epic, reparent its children to functional homes, and close #391 as superseded/deprecated (dogfood / usage test). | aside | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Doctrine artefacts validate against their schemas. | `spec-kitty doctor doctrine --json` reports healthy; DRG freshness gate passes. | Draft |
| NFR-002 | New/changed code passes quality gates. | `ruff` and `mypy` report zero issues/warnings on changed paths; `pytest tests/architectural/test_no_legacy_terminology.py` passes. | Draft |
| NFR-003 | Glossary changes are valid. | `spec-kitty glossary validate <files>` passes for all touched seeds. | Draft |
| NFR-004 | Architecture docs conform to the repo template. | New ADR follows `architecture/adr-template.md`; C4 levels (context/container/component) present and cross-linked. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | All work plans, implements, and merges on `feat/doctrine-glossary-consolidation-01KTNWFC`; no new mission branch is introduced. | Active |
| C-002 | Use canonical doctrine templates / CLI surfaces; do not improvise artefacts or copy older missions. | Active |
| C-003 | Honour the Terminology Canon (Mission not feature; canonical glossary terms); terminology guard must pass. | Active |
| C-004 | Preserve existing charter content and user customizations; charter `extends:` must be additive, not destructive. | Active |
| C-005 | **Consolidate; eliminate parallel mechanisms.** New work must replace/reconcile existing surfaces, not fork a second one (a primary cause of the split-brain failures across recent releases). Applies to glossary (one canonical surface), charter extends, DRG/profiles, and architecture docs (single source of truth). | Active |

## Success Criteria

- **SC-1:** A new contributor can organise the tracker end-to-end using only the authored procedure/tactic/styleguide/toolguide (no recourse to ad-hoc notes).
- **SC-2:** 100% of active functional epics resolve to a stable architecture or vision document (zero gaps in the epic↔architecture correlation).
- **SC-3:** A charter that declares `extends:` resolves additively and passes validation.
- **SC-4:** Doctrine graph regenerates from a single command and the freshness gate passes deterministically.
- **SC-5:** All touched glossary seeds validate; planning-and-tracking content is refreshed, and an explicit defer is recorded for runtime-scope promotion.
- **SC-6:** #391 is organized per the newly authored doctrine — residual open children classified and reparented to functional homes where the procedure prescribes; #391 itself REMAINS OPEN as the canonical debt bucket (operator decision 2026-06-11: the 2026-06-09 tracker restructure deliberately keeps #391 live; the original 'close as superseded' wording predated it) — accomplished using *only* the new doctrine (proving SC-1 on a real case).
- **SC-7:** No new parallel mechanism is introduced; each touched surface (glossary, charter config, DRG, architecture docs) has a single source of truth after the mission (C-005).

## Key Entities

- **Doctrine artefacts** — procedure, tactic(s), styleguide, toolguide (under the doctrine layer).
- **Architecture surfaces** — `architecture/` (ADRs, C4), the new `vision/` directory, the architecture-vs-docs boundary.
- **Charter config** — `org-charter.yaml` with `extends:`.
- **Doctrine Relationship Graph (DRG)** — generator + freshness checks.
- **Glossary** — `spec_kitty_core.yaml` + the planning-and-tracking subset, scope registry.

## Assumptions

- Source material is authoritative: the repo `work/` traces (`TRACKER_DOCTRINE_NOTES.md`, `GH_TOOLING_NOTES.md`, `EPIC_ARCHITECTURE_CORRELATION.md`, `EXECUTIVE_SUMMARY.md`, `TRIAGE_FINDINGS_BUGS_P0_P1.md`) and `.kittify/glossaries/planning-and-tracking.yaml`.
- The architecture/docs reconciliation (FR-005/006, #1805 folded as source FR) executes within this mission (operator chose full scope), led by the architect profile.
- The top-level `glossary/` is already the canonical surface (established #1636/01KTB6AN era); WP01 reconciles (deletes residual pointer), does NOT perform a new promotion move.
- `change_mode: standard` (O1-reverted); occurrence_map is a reference-rewrite advisory checklist, not an enforcement gate.

## Out of Scope

- Implementing the Ops/dispatch feature itself (#1810/#1688) — this mission authors the **ADR**, not the runtime.
- The broader tracker remediation (Phase 1) — already complete.
