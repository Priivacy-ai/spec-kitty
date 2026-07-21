# Tasks: Docs Site IA & Onboarding Overhaul

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md
**Branch**: `feat/docs-ia-onboarding-overhaul` (planning base = merge target)

## Subtask Index

| ID | Description | WP | Parallel |
|----|---|----|----|
| T001 | Audit `docs/guides/` (72 files) + `docs/development/` (7 files); produce `docs-audit.md` disposition table | WP01 | | [D] |
| T002 | Verify each candidate contributor-only file against live content before moving | WP01 | | [D] |
| T003 | Move confirmed contributor files from `docs/guides/` to `docs/development/` (`git mv`) | WP01 | | [D] |
| T004 | Build merged `occurrence_map.yaml`, regenerate `redirect_map.yaml` | WP01 | | [D] |
| T005 | Verify redirect coverage (`check-map`) | WP01 | | [D] |
| T006 | Design the two-zone `NavigationGroup` structure (≤6 top-level per zone) | WP02 | | [D] |
| T007 | Rebuild `docs/toc.yml` with nested `items:` under two zones | WP02 | | [D] |
| T008 | Update child `toc.yml` files referencing relocated paths | WP02 | | [D] |
| T009 | Validate `toc.yml` YAML structure; verify the C-005 cross-zone-leakage invariant (no end-user-zone page links into contributor-only content) by walking the nested tree from each end-user top-level group | WP02 | | [D] |
| T010 | Rewrite `docs/index.md` above-the-fold content | WP03 | | [D] |
| T011 | Rename `your-first-feature.md` → `your-first-mission.md`, reword prose | WP03 | | [D] |
| T012 | Update all inbound references to the old filename/title | WP03 | | [D] |
| T013 | Wire the Get Started entry chain (index → getting-started → your-first-mission) | WP03 | | [D] |
| T014 | Verify NFR-001 (≤2 clicks) by tracing the link chain; verify NFR-002 (≤30 min) via quickstart.md section 1's timed walkthrough | WP03 | | [D] |
| T015 | Research the real `spec-kitty dispatch` / Op mechanism in code | WP04 | [D] |
| T016 | Author `docs/context/ops-vs-missions.md` | WP04 | [D] |
| T017 | Read each of the 4 `mission.yaml` files for accurate purpose/phases | WP04 | [D] |
| T018 | Author `docs/context/mission-types.md` | WP04 | [D] |
| T019 | Read all four existing charter pages in full | WP05 | [D] |
| T020 | Decide consolidated home; write the single charter how-to | WP05 | [D] |
| T021 | Rework the other three pages to link in, not duplicate | WP05 | [D] |
| T022 | Verify no troubleshooting content was lost | WP05 | [D] |
| T023 | Source the 8-kind doctrine vocabulary from the charter module | WP06 | [D] |
| T024 | Check the abandoned `charter-end-user-docs-828` mission for reusable material (non-authoritative) | WP06 | [D] |
| T025 | Author `docs/doctrine/doctrine-kinds.md` (all 8 kinds) | WP06 | [D] |
| T026 | Author `docs/doctrine/create-a-doctrine-artifact.md` | WP06 | [D] |
| T027 | Cross-link from existing `doctrine/index.md`/`README.md`/`spdd-reasons.md` | WP06 | [D] |
| T028 | Audit `docs/api/` for accuracy against live CLI behavior | WP07 | [D] |
| T029 | Audit `docs/adr/`, `docs/migrations/`, `docs/operations/` for accuracy | WP07 | [D] |
| T030 | Audit `docs/archive/` nav placement | WP07 | [D] |
| T031 | Fix confirmed inaccuracies found in T028-T030 | WP07 | [D] |
| T032 | Record all findings (fixed and not-applicable) in `docs-audit.md` | WP07 | [D] |
| T033 | Add `anchor_id` generation to `glossary_page()` | WP08 | [D] |
| T034 | Implement the anchor collision-suffix rule | WP08 | [D] |
| T035 | Build `glossary_linker.py` skeleton (load glossary seed, walk HTML) | WP08 | [D] |
| T036 | Implement longest-match-first, skip-code-blocks, first-mention-only linking | WP08 | [D] |
| T037 | Document the pipeline integration point (mirrors `seo_postprocess.py`) | WP08 | [D] |
| T038 | Write `test_glossary_canonical_terms.py` sourcing the 104-term glossary | WP09 | [D] |
| T039 | Run the new check against the current `docs/` tree; record findings | WP09 | [D] |
| T040 | Run `test_no_legacy_terminology.py` + the new WP09 check across all mission-touched pages | WP10 | |
| T041 | Fix any flagged occurrences from T040 | WP10 | |
| T042 | File the C-003 follow-up GitHub issue (full alias/banned-synonym governance) | WP10 | |
| T043 | Final terminology/consistency summary report | WP10 | |
| T044 | Verify NFR-005 (100% Divio `type:` frontmatter coverage) across all mission-touched pages; add/fix missing or invalid frontmatter | WP10 | |

## Work Packages

### WP01 — Guides Audit & Contributor Content Relocation

**Goal**: Establish ground truth on every file in `docs/guides/` and `docs/development/`,
relocate confirmed contributor-only content, and regenerate redirects non-destructively.
**Priority**: P1 (foundational — everything else depends on final file locations).
**Independent test**: `docs-audit.md` exists with a disposition for every guides/development
file; every moved file resolves at its new path; `redirect_stub_generator.py check-map` passes
with zero uncovered baseline URLs.
**Subtasks**: T001-T005 (5)
**Dependencies**: none
**Estimated prompt size**: ~450 lines

### WP02 — Two-Zone Hierarchical Navigation Rebuild

**Goal**: Rebuild `docs/toc.yml` into two clearly segregated, nested-navigation zones with
≤6 unexpanded top-level entries each.
**Priority**: P1 (blocks WP03-WP07's nav placement).
**Independent test**: `docs/toc.yml` parses as valid YAML; exactly two top-level zone groups
exist; each has ≤6 immediate children; every page WP01 relocated is referenced at its new path.
**Subtasks**: T006-T009 (4)
**Dependencies**: WP01
**Estimated prompt size**: ~350 lines

### WP03 — Homepage & Get Started Path

**Goal**: A first-time visitor reaches a working first mission from the homepage.
**Priority**: P1 (User Story 1, the funnel's only entry point).
**Independent test**: `docs/index.md`'s first screen states who Spec Kitty is for before any
governance term; homepage → tutorial start is ≤2 clicks; `your-first-mission.md` replaces
`your-first-feature.md` with zero dangling references.
**Subtasks**: T010-T014 (5)
**Dependencies**: WP02
**Estimated prompt size**: ~400 lines

### WP04 — Core Concepts: Ops vs. Missions & Mission Types

**Goal**: Author the two missing explanation pages for User Story 2.
**Priority**: P2.
**Independent test**: `ops-vs-missions.md` states a concrete decision rule; `mission-types.md`
lists exactly the 4 real mission types with accurate purpose/phases.
**Subtasks**: T015-T018 (4)
**Dependencies**: WP02
**Estimated prompt size**: ~350 lines

### WP05 — Charter How-To Consolidation

**Goal**: One authoritative charter interview-to-generation how-to, replacing four scattered
pages.
**Priority**: P2.
**Independent test**: A user can create a charter following one page only; the other three
pages link in rather than duplicate; no troubleshooting content is lost.
**Subtasks**: T019-T022 (4)
**Dependencies**: WP02
**Estimated prompt size**: ~350 lines

### WP06 — Doctrine Documentation

**Goal**: Full explanation of all 8 doctrine artifact kinds plus a working "create your own"
how-to, for User Story 3.
**Priority**: P2.
**Independent test**: `doctrine-kinds.md` covers all 8 kinds with purpose + example;
`create-a-doctrine-artifact.md`'s steps work end to end.
**Subtasks**: T023-T027 (5)
**Dependencies**: WP02
**Estimated prompt size**: ~400 lines

### WP07 — Reference Section Accuracy & Nav Audit

**Goal**: Narrow, evidence-based corrections to reference-heavy sections; no wholesale
rewrites.
**Priority**: P3.
**Independent test**: Every confirmed inaccuracy from the audit is fixed; findings (including
non-fixes) are recorded.
**Subtasks**: T028-T032 (5)
**Dependencies**: WP02
**Estimated prompt size**: ~400 lines

### WP08 — Glossary Activation: Anchors + Linker

**Goal**: Every glossary term individually addressable; first-mention auto-linking with
tooltips, independent of the content/nav work.
**Priority**: P2 (independent — can start immediately).
**Independent test**: Every one of the 104 glossary terms has a unique, stable anchor; the
linker links first mention only, skips code blocks, and applies longest-match-first.
**Subtasks**: T033-T037 (5)
**Dependencies**: none
**Estimated prompt size**: ~450 lines

### WP09 — Canonical Glossary Term Check

**Goal**: A standing architectural test that flags non-canonical glossary-term usage.
**Priority**: P2 (independent — can start immediately).
**Independent test**: `pytest tests/architectural/test_glossary_canonical_terms.py` runs and
reports flagged occurrences (if any) with file:line references.
**Subtasks**: T038-T039 (2)
**Dependencies**: none
**Estimated prompt size**: ~250 lines

### WP10 — Terminology Canon Sweep & Follow-Up Issue

**Goal**: Final terminology correctness pass over the whole mission's output, full Divio
frontmatter coverage verification, plus the C-003 follow-up issue.
**Priority**: P1 (must run last — gates mission completion).
**Independent test**: Both terminology tests pass clean; every mission-touched page carries
valid Divio `type:` frontmatter (NFR-005); the GitHub issue for full alias/banned-synonym
governance exists and is linked from spec.md's C-003.
**Subtasks**: T040-T044 (5)
**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09
**Estimated prompt size**: ~340 lines

## Parallel Opportunities

- WP08 and WP09 (glossary tooling) have no dependencies and can start immediately alongside
  WP01.
- Once WP02 lands, WP03, WP04, WP05, WP06, and WP07 can all run in parallel — they touch
  disjoint file sets (see each WP's `owned_files`).
- WP10 is the only hard serialization point: it must wait for every other WP.

## MVP Scope

WP01 + WP02 + WP03 alone deliver User Story 1 (the P1 discovery→install→first-mission path) —
the smallest slice that is independently shippable and testable via quickstart.md section 1.
