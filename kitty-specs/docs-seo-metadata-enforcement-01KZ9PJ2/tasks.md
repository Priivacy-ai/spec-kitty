# Tasks: Docs SEO Metadata Audit and Enforcement

**Mission**: `docs-seo-metadata-enforcement-01KZ9PJ2`
**Branch**: planning base and merge target are both `feat/docs-seo-metadata-enforcement`
**Generated**: 2026-08-05
**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

---

## Overview

8 work packages, 41 subtasks. Six of the eight have no dependencies and can start immediately — the mission is unusually parallelizable because the bulk content work (3 packages, 147 descriptions) is fully decoupled from the pipeline code.

| WP | Title | Subtasks | Deps | Est. lines | Concern |
|---|---|---|---|---|---|
| WP01 | Published-page-set resolver | 6 | — | ~430 | IC-01 |
| WP02 | ADR descriptions — 1.x and 2.x (51 pages) | 5 | — | ~330 | IC-04 |
| WP03 | ADR descriptions — 3.x early (48 pages) | 5 | — | ~320 | IC-04 |
| WP04 | ADR descriptions — 3.x late (48 pages) | 5 | — | ~340 | IC-04 |
| WP05 | Render emission and built-output verifier | 7 | — | ~480 | IC-03 |
| WP06 | Source metadata gate hardening | 6 | WP01–WP04 | ~420 | IC-02 |
| WP07 | Internal link equity for high-intent pages | 4 | — | ~260 | IC-05 |
| WP08 | CI trigger scoping | 3 | — | ~210 | IC-06 |

**Critical path**: WP01 + (WP02 ∥ WP03 ∥ WP04) → WP06. Everything else is off the critical path.

**The one hard ordering constraint**: WP06 removes `docs/adr/` from the description gate's exclusion list. If it lands before WP02–WP04 complete, CI goes red for 147 files. This is encoded as a real dependency, not a comment.

---

## Subtask Index

*Reference table only — not a tracking surface. Progress is tracked by the checkbox rows under each work package below.*

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Establish and record the green baseline | WP01 | |
| T002 | Define `PublishedPageSet` and `Exclusion` value objects | WP01 | |
| T003 | Implement `resolve_published_pages` reading `docfx.json` | WP01 | |
| T004 | Translate DocFX glob semantics with membership validation | WP01 | |
| T005 | Add fail-closed error paths, non-vacuity floor, enumerated exclusions | WP01 | |
| T006 | Write the resolver test suite including the regression proof | WP01 | |
| T007 | Survey the 1.x/2.x batch and build an authoring worklist | WP02 | [P] |
| T008 | Author descriptions for `docs/adr/1.x` (13 pages) | WP02 | [P] |
| T009 | Author descriptions for `docs/adr/2.x` (38 pages) | WP02 | [P] |
| T010 | Self-check length band and intra-batch uniqueness | WP02 | [P] |
| T011 | Run terminology guard and confirm no lockfile drift | WP02 | [P] |
| T012 | Survey the 3.x early batch (2026-03 … 2026-05) | WP03 | [P] |
| T013 | Author descriptions for 2026-04 (33 pages) | WP03 | [P] |
| T014 | Author descriptions for 2026-03 and 2026-05 (15 pages) | WP03 | [P] |
| T015 | Self-check length band and intra-batch uniqueness | WP03 | [P] |
| T016 | Run terminology guard and confirm no lockfile drift | WP03 | [P] |
| T017 | Survey the 3.x late batch (2026-06 … 2026-08 + README) | WP04 | [P] |
| T018 | Author descriptions for 2026-06 (22 pages) | WP04 | [P] |
| T019 | Author descriptions for 2026-07 and 2026-08 (25 pages) | WP04 | [P] |
| T020 | Add title and description frontmatter to `3.x/README.md` | WP04 | [P] |
| T021 | Self-check, terminology guard, and lockfile drift check | WP04 | [P] |
| T022 | Emit `<meta name="description">` from `seo_postprocess.py` | WP05 | [P] |
| T023 | Create `seo_verify.py` with classification reusing `should_index` | WP05 | [P] |
| T024 | Implement rendered-page rules V-06 … V-10 | WP05 | [P] |
| T025 | Enforce stub, sitemap, and read-only invariants | WP05 | [P] |
| T026 | Emit the audit record including the stale-URL finding | WP05 | [P] |
| T027 | Wire the verifier into `docs-pages.yml` as the last step | WP05 | [P] |
| T028 | Write the verifier and post-processor test suite | WP05 | [P] |
| T029 | Consume the resolver in `description_length_check.py` | WP06 | |
| T030 | Retire the ADR exclusion and correct its stale rationale | WP06 | |
| T031 | Add boilerplate detection pinned to the render-side constant | WP06 | |
| T032 | Add duplicate detection that names the colliding peer | WP06 | |
| T033 | Add the non-vacuity coverage assertion | WP06 | |
| T034 | Repoint `test_docs_seo.py` and extend the boundary proofs | WP06 | |
| T035 | Add one-click links from the documentation home | WP07 | [P] |
| T036 | Add cross-links from topically relevant guides | WP07 | [P] |
| T037 | Satisfy the relative-link and related-edge validators | WP07 | [P] |
| T038 | Verify click depth against the built site | WP07 | [P] |
| T039 | Add a `paths:` filter covering every gate input | WP08 | [P] |
| T040 | Verify the required-check safety precondition still holds | WP08 | [P] |
| T041 | Record the filter's input-set invariant | WP08 | [P] |

---

## WP01 — Published-page-set resolver

**Prompt**: [tasks/WP01-published-page-set-resolver.md](tasks/WP01-published-page-set-resolver.md)

**Goal**: Make "which pages are published" answerable from exactly one authority — `docs/docfx.json` — so a directory move can never again leave a gate guarding an empty tree.

**Priority**: P0. This is the mission's root-cause fix and the foundation WP06 consumes.

**Independent test**: A page set built from the retired pre-move glob list fails the floor assertion; a page set built from `docfx.json` resolves ~674 pages including three named canary pages.

### Included subtasks

- [x] T001 Establish and record the green baseline (WP01)
- [x] T002 Define `PublishedPageSet` and `Exclusion` value objects (WP01)
- [x] T003 Implement `resolve_published_pages` reading `docfx.json` (WP01)
- [x] T004 Translate DocFX glob semantics with membership validation (WP01)
- [x] T005 Add fail-closed error paths, non-vacuity floor, enumerated exclusions (WP01)
- [x] T006 Write the resolver test suite including the regression proof (WP01)

**Implementation sketch**: Baseline first (T001 — non-negotiable, planning never confirmed it). Then value objects, then the reader, then the glob translation, then the guards, then tests. Tests last only because the guards define what they assert; the regression proof in T006 is the acceptance gate.

**Parallel opportunities**: None internally — the subtasks are a straight dependency chain. WP02–WP05, WP07, WP08 all run alongside it.

**Dependencies**: None.

**Risks**: DocFX glob semantics differ from `pathlib` semantics. Getting this wrong silently under-collects — the exact bug being repaired, in a new location. Mitigation is empirical membership assertions, never reasoning about glob translation.

---

## WP02 — ADR descriptions: 1.x and 2.x (51 pages)

**Prompt**: [tasks/WP02-adr-descriptions-1x-2x.md](tasks/WP02-adr-descriptions-1x-2x.md)

**Goal**: Give each of the 51 pages under `docs/adr/1.x/` and `docs/adr/2.x/` a unique, hand-authored description in the 50–180 character band.

**Priority**: P1. Off the critical path only in the sense that it does not block WP01 — it does block WP06.

**Independent test**: Every file in the two era directories has a `description` in band, no two descriptions are identical, and the terminology guard passes.

### Included subtasks

- [x] T007 Survey the 1.x/2.x batch and build an authoring worklist (WP02)
- [x] T008 Author descriptions for `docs/adr/1.x` (13 pages) (WP02)
- [x] T009 Author descriptions for `docs/adr/2.x` (38 pages) (WP02)
- [x] T010 Self-check length band and intra-batch uniqueness (WP02)
- [x] T011 Run terminology guard and confirm no lockfile drift (WP02)

**Implementation sketch**: Read each ADR's Context and Decision sections, write a description that says what the decision *was* rather than what the document *is*. Verify band and uniqueness mechanically before finishing.

**Parallel opportunities**: Fully parallel with WP03 and WP04 — the three own disjoint file sets by construction.

**Dependencies**: None.

**Risks**: The 50–180 band is narrow and uniqueness is enforced; near-identical ADRs need genuinely distinguishing text. `docs/` is in the terminology guard's scan roots, unlike `kitty-specs/`.

---

## WP03 — ADR descriptions: 3.x early (48 pages)

**Prompt**: [tasks/WP03-adr-descriptions-3x-early.md](tasks/WP03-adr-descriptions-3x-early.md)

**Goal**: Author descriptions for the 48 `docs/adr/3.x/` pages dated 2026-03 through 2026-05.

**Priority**: P1.

**Independent test**: All 48 dated files in range carry an in-band description; no duplicates within the batch.

### Included subtasks

- [x] T012 Survey the 3.x early batch (2026-03 … 2026-05) (WP03)
- [x] T013 Author descriptions for 2026-04 (33 pages) (WP03)
- [x] T014 Author descriptions for 2026-03 and 2026-05 (15 pages) (WP03)
- [x] T015 Self-check length band and intra-batch uniqueness (WP03)
- [x] T016 Run terminology guard and confirm no lockfile drift (WP03)

**Implementation sketch**: 2026-04 is the dense month (33 of 48) and is its own subtask for that reason. Same authoring standard as WP02.

**Parallel opportunities**: Fully parallel with WP02 and WP04.

**Dependencies**: None.

**Risks**: 2026-04 contains several closely-related ADRs (skill installation, shim generation, charter handoff) whose descriptions will collide unless deliberately differentiated.

---

## WP04 — ADR descriptions: 3.x late (48 pages)

**Prompt**: [tasks/WP04-adr-descriptions-3x-late.md](tasks/WP04-adr-descriptions-3x-late.md)

**Goal**: Author descriptions for the 47 `docs/adr/3.x/` pages dated 2026-06 through 2026-08, plus frontmatter for `docs/adr/3.x/README.md`.

**Priority**: P1.

**Independent test**: All dated files in range carry an in-band description; the README carries `title` and `description` and **no other** frontmatter keys.

### Included subtasks

- [x] T017 Survey the 3.x late batch (2026-06 … 2026-08 + README) (WP04)
- [x] T018 Author descriptions for 2026-06 (22 pages) (WP04)
- [x] T019 Author descriptions for 2026-07 and 2026-08 (25 pages) (WP04)
- [x] T020 Add title and description frontmatter to `3.x/README.md` (WP04)
- [x] T021 Self-check, terminology guard, and lockfile drift check (WP04)

**Implementation sketch**: As WP02/WP03, plus the README special case in T020.

**Parallel opportunities**: Fully parallel with WP02 and WP03.

**Dependencies**: None.

**Risks**: T020 is a live trap. `3.x/README.md` currently has **no** frontmatter. Adding `tag`, `divio_type`, or `owning_workstream` will drift the page-inventory lockfile and trip `INVENTORY-LOCKFILE-DRIFT`. Add `title` and `description` only.

---

## WP05 — Render emission and built-output verifier

**Prompt**: [tasks/WP05-render-emission-and-verifier.md](tasks/WP05-render-emission-and-verifier.md)

**Goal**: Make the render actually emit a description tag, and add a verifier that proves what ships carries correct metadata — the only layer that can catch a render-path defect.

**Priority**: P0. This closes the defect class that source-level checks structurally cannot see.

**Independent test**: A synthetic `_site` fixture with a missing description tag fails `seo_verify.py --strict`; a compliant fixture passes; the post-processor is idempotent across two runs.

### Included subtasks

- [ ] T022 Emit `<meta name="description">` from `seo_postprocess.py` (WP05)
- [ ] T023 Create `seo_verify.py` with classification reusing `should_index` (WP05)
- [ ] T024 Implement rendered-page rules V-06 … V-10 (WP05)
- [ ] T025 Enforce stub, sitemap, and read-only invariants (WP05)
- [ ] T026 Emit the audit record including the stale-URL finding (WP05)
- [ ] T027 Wire the verifier into `docs-pages.yml` as the last step (WP05)
- [ ] T028 Write the verifier and post-processor test suite (WP05)

**Implementation sketch**: Fix the emission first so the verifier has something to pass against, then build the verifier bottom-up, then wire it in. All tests use synthetic `_site` fixtures under `tmp_path`, so none of this needs a real DocFX build.

**Parallel opportunities**: The whole WP is parallel with everything else.

**Dependencies**: None.

> **Correction to plan.md**: `plan.md` lists IC-03 as depending on IC-01 "for the indexable-page definition". On closer reading of the contract that is wrong — `contracts/built-output-verifier.md` C-B4 requires reuse of `seo_postprocess.should_index()`, which is render-side and already exists. The resolver is source-side and is not needed here. WP05 is therefore dependency-free, which improves parallelism.

**Risks**: Step ordering in `docs-pages.yml` is load-bearing and already subtle. The verifier must run **after** stub generation so it can confirm stubs are correctly excluded, but must never treat a stub as indexable.

---

## WP06 — Source metadata gate hardening

**Prompt**: [tasks/WP06-source-metadata-gate.md](tasks/WP06-source-metadata-gate.md)

**Goal**: Make a missing, boilerplate, or duplicated description fail at PR time across the whole published tree instead of 2.4% of it.

**Priority**: P0. This is the gate that stops the defect recurring.

**Independent test**: The gate goes red on a missing description, a 49-character description, a 181-character description, the boilerplate string, a duplicate pair, and an empty page set — six distinct proofs that it can fail.

### Included subtasks

- [ ] T029 Consume the resolver in `description_length_check.py` (WP06)
- [ ] T030 Retire the ADR exclusion and correct its stale rationale (WP06)
- [ ] T031 Add boilerplate detection pinned to the render-side constant (WP06)
- [ ] T032 Add duplicate detection that names the colliding peer (WP06)
- [ ] T033 Add the non-vacuity coverage assertion (WP06)
- [ ] T034 Repoint `test_docs_seo.py` and extend the boundary proofs (WP06)

**Implementation sketch**: Swap the page source first, then the new rules, then flip the exclusion last — the flip is the change that turns CI red if WP02–WP04 have not landed, so it wants to be the final, obvious step.

**Parallel opportunities**: None internally.

**Dependencies**: **WP01** (needs the resolver), **WP02, WP03, WP04** (T030 turns CI red for 147 files without them).

**Risks**: T030 is the sequencing hazard of the whole mission. Also: switching from `rglob("*.md")` to the resolver may *reduce* the checked count, because unpublished trees leave scope. That reduction is legitimate and must not be mistaken for the under-collection the floor assertion guards.

---

## WP07 — Internal link equity for high-intent pages

**Prompt**: [tasks/WP07-internal-link-equity.md](tasks/WP07-internal-link-equity.md)

**Goal**: Put the install guide and the slash-command reference one click from where readers actually land, without disturbing the navigation shape a prior mission deliberately chose.

**Priority**: P2.

**Independent test**: Both pages are reachable by a single link from `docs/index.md`; `docs/toc.yml` is unchanged; the relative-link and related-edge validators pass.

### Included subtasks

- [x] T035 Add one-click links from the documentation home (WP07)
- [x] T036 Add cross-links from topically relevant guides (WP07)
- [x] T037 Satisfy the relative-link and related-edge validators (WP07)
- [x] T038 Verify click depth against the built site (WP07)

**Implementation sketch**: Edit `docs/index.md` to link both pages directly, add reciprocal cross-links from related guides, then run the two link validators.

**Parallel opportunities**: Fully parallel with everything.

**Dependencies**: None.

**Risks**: `docs/toc.yml` documents a "2 zones, ≤6 top-level entries" shape and zone 1 is already at exactly 6. Per decision `01KZ9Q2E397AB1WJYZMAP0A0VB` that file is **not** to be modified. Note the constraint is prose, not an automated gate — nothing will stop a careless edit.

---

## WP08 — CI trigger scoping

**Prompt**: [tasks/WP08-ci-trigger-scoping.md](tasks/WP08-ci-trigger-scoping.md)

**Goal**: Stop `docs-freshness` running on pull requests that touch no documentation surface.

**Priority**: P2.

**Independent test**: The workflow declares a `paths:` filter that includes every path the four gates read; a PR touching only unrelated source does not trigger it.

### Included subtasks

- [x] T039 Add a `paths:` filter covering every gate input (WP08)
- [x] T040 Verify the required-check safety precondition still holds (WP08)
- [x] T041 Record the filter's input-set invariant (WP08)

**Implementation sketch**: Add the filter, re-verify branch protection, and leave a comment explaining why the input set is what it is.

**Parallel opportunities**: Fully parallel with everything.

**Dependencies**: None.

**Risks**: A filter narrower than the gates' true input set silently stops guarding real changes — the same failure shape this mission exists to fix. Must include `scripts/docs/**` and the two `packs/built-in/` paths, not just `docs/**`.

---

## MVP scope

**WP01 alone is the meaningful minimum.** It converts the silent-coverage-collapse failure from possible to structurally unrepresentable. Even without any description backfill, landing WP01 plus WP06's coverage assertion means the next directory move fails loudly instead of quietly.

Recommended first slice if the mission must be cut: **WP01 + WP05**. Together they fix both root causes (two authorities for the page set; a render that drops metadata) without requiring the 147-page authoring effort.

---

## Parallelization

Six of eight packages have no dependencies. A realistic lane allocation:

- **Lane A**: WP01 → WP06 (the critical path)
- **Lane B**: WP02 → WP07
- **Lane C**: WP03 → WP08
- **Lane D**: WP04
- **Lane E**: WP05

Wall-clock is bounded by Lane A, which cannot finish until all of WP02–WP04 land. If the ADR authoring is the long pole, adding lanes to split WP02–WP04 further is the correct lever.
