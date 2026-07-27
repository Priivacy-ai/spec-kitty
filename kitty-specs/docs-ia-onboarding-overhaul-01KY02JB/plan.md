# Implementation Plan: Docs Site IA & Onboarding Overhaul

**Branch**: `feat/docs-ia-onboarding-overhaul` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/spec.md`

## Summary

Restructure docs.spec-kitty.ai's information architecture: pull contributor-only content
stranded in `docs/guides/` into the existing `docs/development/` contributor root, group both
zones into hierarchical (nested) `toc.yml` navigation with 6 or fewer unexpanded top-level
entries per zone, rebuild the homepage and Get Started path so a first-time visitor reaches a
working first mission, author net-new core-concept and doctrine documentation, lightly audit
reference-heavy sections, and activate the published glossary via a build-time HTML
post-processing linker plus a canonical-term-usage check. Every moved/deleted path gets an
entry in the existing `scripts/docs/redirect_map.yaml` (no new redirect mechanism).

## Technical Context

**Language/Version**: Python 3.11+ (matches repository standard; used for all new tooling: glossary linker, anchor generation, canonical-term check).
**Primary Dependencies**: DocFX (existing site generator, `docs/docfx.json` — unmodified pipeline internals per C-001), `ruamel.yaml`/PyYAML (already a project dependency; reads `.kittify/glossaries/spec_kitty_core.yaml`), pytest (new architectural check), existing `scripts/docs/` pipeline (`seo_postprocess.py` pattern reused for the new linker stage, `redirect_stub_generator.py` reused for moved paths).
**Storage**: N/A — content is markdown files and one YAML glossary seed; no database.
**Testing**: pytest, following the `tests/architectural/test_no_legacy_terminology.py` pattern for the new canonical-term check; existing anti-sprawl ratchet and relative-link validator (inherited doctrine from `common-docs-consolidation`) continue to gate all touched pages.
**Target Platform**: Static site served via GitHub Pages, built by the existing DocFX pipeline (`.github/workflows/docs-pages.yml`, unmodified per C-001).
**Project Type**: Single project — documentation content plus small Python tooling additions under `scripts/docs/` and `tests/architectural/`.
**Performance Goals**: Not applicable in the traditional sense — this is a static informational site; the constraint is UX-latency (clicks-to-content, time-to-first-mission), not runtime throughput. See NFR-001/NFR-002 in spec.md.
**Constraints**: Must not modify DocFX pipeline internals, the GitHub Pages workflow, or the custom domain/CNAME (C-001). Must satisfy existing CI-enforced doc-quality gates: frontmatter description 50-180 chars, anti-sprawl ratchet, relative-link validator (C-004). New build step (glossary linker) must plug into `scripts/docs/` without breaking `seo_postprocess.py` or other existing generators. Every file move must use the existing redirect-map mechanism, not an ad hoc alternative.
**Scale/Scope**: ~600 markdown files under `docs/`; 104 glossary terms in `.kittify/glossaries/spec_kitty_core.yaml`; 72 files currently in `docs/guides/` (mixed end-user/contributor) to reclassify; 8 doctrine artifact kinds to document; today's top nav has 16 top-level `docs/toc.yml` entries (verified by direct read; DocFX already supports nested `items:` — see "Historical Archive" — proving FR-015's mechanism needs no pipeline changes), target is 6 or fewer per zone.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter principle | Applies to this mission | Compliance |
|---|---|---|
| Single canonical authority | Yes — glossary terms, doctrine kind names, mission-type names must each have one owning source. | Pass. Glossary source stays `.kittify/glossaries/spec_kitty_core.yaml` (FR-011/012); doctrine kind vocabulary sourced from `charter.kind_vocabulary` (FR-007); no new parallel glossary or doctrine registry is introduced. |
| Architectural alignment | Yes — the shared-package boundary and DocFX-as-canonical-site-generator decisions are pre-existing architecture. | Pass. C-001 explicitly keeps DocFX/GitHub Pages internals untouched; the redirect mechanism reuses the existing `common-docs-consolidation` decision (D4) rather than introducing an alternative. |
| Domain-driven splits + tiered rigour | Loosely applies — "zones" and "navigation groups" are the domain model for this mission (see Key Entities in spec.md). | Pass. `NavigationZone`/`NavigationGroup`/`DocsPage` model is the bounded structure; rigour is proportional (docs content, not a runtime system). |
| ATDD-first | Yes — every FR in spec.md carries an explicit acceptance criterion. | Pass. Tasks phase will derive WPs directly from FR acceptance criteria. |
| Glossary & terminology adherence | Directly central to this mission (FR-011–FR-015 exist because of this). | Pass, with this mission actively *building* the enforcement mechanism (FR-013) rather than just complying with an existing one. |
| Model discipline | N/A for content-authoring work; applies to WP dispatch during implement-review. | Deferred to tasks/implement phase — no plan-time violation. |
| Delegate to preserve context | Applies to implement-review orchestration (large page-authoring volume). | Will be honored during implement-review via WP-scoped subagent dispatch, not a plan-time concern. |
| Dispatch a governed profile to run the mission | Applies to implement-review orchestration. | Will be honored during implement-review — no plan-time violation. |

No charter conflicts identified.

**Post-Phase-1 re-check**: `data-model.md`, `contracts/`, and `quickstart.md` introduce no new
surfaces beyond what Technical Context and the Implementation Concern Map already declared
(existing glossary schema extended with one field, one new script, one new test, `toc.yml`
changes). No new charter conflicts found.

## Project Structure

### Documentation (this mission)

```
kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/
├── spec.md               # Feature specification (committed)
├── plan.md                # This file
├── research.md             # Phase 0 output
├── data-model.md           # Phase 1 output
├── contracts/               # Phase 1 output
│   ├── glossary-anchor-contract.md
│   ├── glossary-linker-contract.md
│   ├── canonical-term-check-contract.md
│   └── redirect-map-entry-contract.md
├── quickstart.md            # Phase 1 output
├── gap-analysis.md          # Auto-generated coarse coverage matrix (mechanical tool output)
└── tasks.md                 # Phase 2 output (/spec-kitty.tasks — NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
docs/
├── index.md                       # IC-02: homepage rewrite
├── toc.yml                        # IC-01: hierarchical two-zone nav
├── guides/                        # IC-01: reclassify — end-user subset stays/reorganizes here
│   ├── getting-started.md         # IC-02: linked from homepage
│   ├── your-first-feature.md      # IC-02/FR-014: rename to your-first-mission.md
│   └── ... (72 files audited, disposition recorded in gap-analysis)
├── development/                   # IC-01: contributor runbooks land here (pr-landing.md,
│                                   #         testing-flakiness.md, etc. move here from guides/)
├── context/                       # IC-03/IC-04: Ops-vs-Missions, mission-types, charter pages
│   ├── ops-vs-missions.md         # NEW — FR-004
│   └── mission-types.md           # NEW — FR-005
├── doctrine/                      # IC-05: doctrine-kinds explanation + create-a-doctrine how-to
│   ├── doctrine-kinds.md          # NEW — FR-007
│   └── create-a-doctrine-artifact.md  # NEW — FR-008
├── api/, adr/, architecture/,
│   configuration/, operations/,
│   migrations/, archive/          # IC-06: accuracy/nav audit only, no wholesale rewrite
└── (glossary.html is generated, not hand-authored — see scripts/docs/)

scripts/docs/
├── generate_kitty_specs_docs.py   # IC-07: add stable per-term anchor ids to glossary_page()
├── glossary_linker.py             # IC-07: NEW — HTML post-processing pass (mirrors seo_postprocess.py)
├── seo_postprocess.py             # existing — pipeline-stage pattern reused, not modified
├── redirect_stub_generator.py     # existing — reused for every moved/deleted path
└── redirect_map.yaml              # IC-01/IC-07 — gets new entries for every move

tests/architectural/
├── test_no_legacy_terminology.py  # existing pattern — not modified
└── test_glossary_canonical_terms.py  # IC-07: NEW — canonical-term-usage check
```

**Structure Decision**: Single-project structure. No new top-level source directories — all
changes land inside the existing `docs/`, `scripts/docs/`, and `tests/architectural/` trees.
Zone segregation is achieved primarily through `toc.yml` grouping plus targeted file moves
(only for content genuinely misplaced today, e.g. contributor runbooks inside `guides/`), not a
wholesale directory-tree rebuild — this keeps redirect-map churn proportional to actual
misplacement rather than to the full ~600-file corpus.

## Complexity Tracking

*No Charter Check violations requiring justification — table intentionally empty.*

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP.

### IC-01 — Zone Segregation & Hierarchical Navigation

- **Purpose**: Pull contributor-only content out of `docs/guides/` into `docs/development/`, reorganize the end-user remainder, and rebuild `toc.yml` (and child TOCs) as nested, two-zone, ≤6-top-level-entries-per-zone navigation.
- **Relevant requirements**: FR-003, FR-009, FR-015, NFR-003, NFR-006, C-005.
- **Affected surfaces**: `docs/guides/**`, `docs/development/**`, `docs/toc.yml`, `scripts/docs/redirect_map.yaml`.
- **Sequencing/depends-on**: None — this is foundational; IC-02 through IC-06 depend on the resulting nav structure existing before they can be linked in.
- **Risks**: Highest blast radius in the mission (most files touched). Every move must get a redirect-map entry or NFR-006 fails. Must not silently drop pages during "consolidation" — every disposition needs a recorded rationale (gap-analysis.md).

### IC-02 — Homepage & Get Started Path

- **Purpose**: Rewrite `docs/index.md`'s above-the-fold content and wire one unambiguous Get Started entry point through install → first mission.
- **Relevant requirements**: FR-001, FR-002, FR-014.
- **Affected surfaces**: `docs/index.md`, `docs/guides/getting-started.md`, `docs/guides/your-first-feature.md` (renamed), `docs/toc.yml`.
- **Sequencing/depends-on**: IC-01 (needs the final nav structure to link into).
- **Risks**: Terminology Canon violation risk on the renamed tutorial file (FR-014) — must update all inbound references, not just the filename.

### IC-03 — Core Concepts: Ops vs. Missions & Mission Types

- **Purpose**: Author the two missing explanation pages that let a user choose between ad-hoc dispatch and a full mission, and between mission types.
- **Relevant requirements**: FR-004, FR-005.
- **Affected surfaces**: new `docs/context/ops-vs-missions.md`, new `docs/context/mission-types.md`, `docs/toc.yml`.
- **Sequencing/depends-on**: None for authoring; needs IC-01's nav structure to be placed correctly.
- **Risks**: Content accuracy — must be grounded in the actual `spec-kitty dispatch` / mission-lifecycle code, not assumption. Mission types list must match `src/specify_cli/missions/*/mission.yaml` exactly (4 types today: software-dev, research, documentation, plan).

### IC-04 — Charter How-To Consolidation

- **Purpose**: Merge four scattered charter pages into one authoritative interview-to-generation how-to.
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `docs/context/charter-overview.md`, `docs/guides/charter-governed-workflow.md`, `docs/guides/setup-governance.md`, `docs/guides/troubleshoot-charter.md`.
- **Sequencing/depends-on**: None for authoring; needs IC-01's nav placement.
- **Risks**: Must not lose troubleshooting content from `troubleshoot-charter.md` during consolidation — verify against gap-analysis disposition.

### IC-05 — Doctrine Documentation

- **Purpose**: Author the explanation page covering all 8 doctrine artifact kinds and the "create your own doctrine artifact" how-to.
- **Relevant requirements**: FR-007, FR-008.
- **Affected surfaces**: new `docs/doctrine/doctrine-kinds.md`, new `docs/doctrine/create-a-doctrine-artifact.md`, existing `docs/doctrine/index.md`/`README.md`/`spdd-reasons.md` (cross-link, don't duplicate).
- **Sequencing/depends-on**: None for authoring; needs IC-01's nav placement.
- **Risks**: The abandoned `charter-end-user-docs-828` mission's gap-analysis may have partial doctrine content — check before authoring from scratch (C-006: this mission's audit is authoritative if content conflicts).

### IC-06 — Reference Section Accuracy & Nav Audit

- **Purpose**: Audit API, ADR, Configuration, Operations, Migrations, and Historical Archive sections for factual accuracy and nav placement; fix confirmed issues.
- **Relevant requirements**: FR-010.
- **Affected surfaces**: `docs/api/**`, `docs/adr/**`, `docs/configuration/**` (if present), `docs/operations/**`, `docs/migrations/**`, `docs/archive/**`, `docs/toc.yml`.
- **Sequencing/depends-on**: IC-01 (final nav zones must exist before placement changes are meaningful).
- **Risks**: Scope creep — C-001/spec's Out-of-Scope explicitly forbid wholesale rewrites here; audit findings must be narrow, evidence-based corrections only.

### IC-07 — Glossary Activation

- **Purpose**: Add stable per-term anchors to the glossary page generator, build the HTML post-processing term-linker, and add the canonical-term-usage architectural check.
- **Relevant requirements**: FR-011, FR-012, FR-013, NFR-004.
- **Affected surfaces**: `scripts/docs/generate_kitty_specs_docs.py` (`glossary_page()`), new `scripts/docs/glossary_linker.py`, new `tests/architectural/test_glossary_canonical_terms.py`.
- **Sequencing/depends-on**: None — independent of the content/nav work; can run in parallel with IC-01–IC-06.
- **Risks**: Longest-match-first linking correctness (see spec.md Edge Cases); must not link inside code blocks or unrelated proper nouns. First-mention-only per page (NFR-004) requires per-page state tracking in the linker.

### IC-08 — Terminology Canon Sweep & Follow-Up Issue

- **Purpose**: Final terminology pass across all mission-touched pages; file the GitHub issue tracking full glossary alias/banned-synonym governance (C-003).
- **Relevant requirements**: FR-014, C-003.
- **Affected surfaces**: All files touched by IC-01–IC-07 (final pass, not new authoring).
- **Sequencing/depends-on**: IC-01 through IC-07 (runs last, over their combined output).
- **Risks**: Must run genuinely last — running it early would miss terminology introduced by later ICs.
