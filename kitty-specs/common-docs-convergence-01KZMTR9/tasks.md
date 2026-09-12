# Tasks: Common Docs Convergence

**Mission**: `common-docs-convergence-01KZMTR9` | **Branch**: `docs/common-docs-cleanup`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Reviews**: [post-spec](./reviews/post-spec-squad.md), [post-plan](./reviews/post-plan-squad.md)

Subtask completion is event-sourced — record with `spec-kitty agent tasks mark-status Txxx --status done`.
The `Txxx` rows below are reference rows, not checkboxes.

## Ownership model (post-plan squad, C-011)
Partitioned by **destination-section ownership**: each `docs/` section is owned by exactly one mover
WP; all shared manifests (`redirect_map.yaml`, `toc.yml`, `docfx.json`, `llms.txt`, per-section toc,
inventory lockfiles, `docs/plans/**` link-targets, `CLAUDE.md`/`AGENTS.md`) are written ONLY by the
terminal reconcile WP13. Movers emit per-WP occurrence-map ledger fragments that WP13 merges. Content
**rewrites (IC-08)** are done as a distinct, separately-reviewed PHASE inside each mover WP (with the
NFR-009 fidelity ledger) rather than as separate WPs — this honors "rewrite reviewed apart from move"
while keeping `owned_files` collision-free.

**Rewrite bounding (FR-014, post-tasks C1):** each mover's rewrite phase is BOUNDED — it operates only
on pages that WP has actually moved/restructured (a subset of its own completed moves), carries a
per-WP ceiling of **≤10 rewritten pages** (split into a follow-on if more are warranted), and every
rewritten page gets a fidelity-ledger row (claim → code/test backing, NFR-009). The enumerated page
list is produced by the mover from its real touched-set at implement time (the pages don't exist at
their final paths until the move lands); the ceiling + per-page ledger are the checkable bound.

**Per-section toc ownership (post-tasks ownership #3):** each mover owns its section's `toc.yml`
(regenerated as part of its own move); WP13 is the single writer of the GLOBAL manifests only
(`docs/toc.yml`, `docfx.json`, `llms.txt`, `redirect_map.yaml`) + `CLAUDE.md`/`AGENTS.md` + `docs/plans/**`
link-targets. This relaxes C-011 for section-local toc while keeping the load-bearing global single-writer.

## Dependency graph
```
WP01 doctrine ┐
WP02 audience ┤─→ WP04 gates ─→ WP05,WP06,WP07,WP08,WP09,WP10,WP11,WP12 (movers) ─→ WP13 reconcile+block
WP03 spine    ┘                         (WP09,WP10 need WP01; WP06/WP09 rehome from root)
WP08 (adr/migrations) may start after WP03 (renames need the spine)
```

## Subtask Index (reference)
| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Canonize `audience:` in 042 + 047 (semantics, resolvable-path rule) | WP01 | |
| T002 | Add `audience:` rule + tooling row to common-docs styleguide | WP01 | |
| T003 | Update concern_bucket_to_section + guides_boundary (audience routing, OB-2 stance) | WP01 | |
| T004 | Add structural_lint_config fields for new invariants (config only) | WP04 | |
| T005 | Kebab-rename snake_case personas; add catalog index; complete catalog | WP02 | [P] |
| T006 | Implement audience_resolver.py (scalar-or-list, non-vacuous floor) | WP02 | [P] |
| T007 | test_audience_resolves.py (dangling + zero-examined fail) | WP02 | [P] |
| T008 | Collapse prior mission's 29 moves into occurrence_map (baseline→FINAL); resolve destinations | WP03 | [P] |
| T009 | Repoint MISSION_SLUG default; always-pass `--occurrence-map` | WP03 | [P] |
| T010 | test_redirect_spine.py: regen reproduces all 151 prior + new (no coverage regression) | WP03 | [P] |
| T011 | Extend docs_structural_lint.py check-fns (one-index-per-dir, sanctioned-section) — advisory | WP04 | |
| T012 | Touched-set gates: audience-presence + description-band + audience-placement (git-diff) | WP04 | |
| T013 | Reverse rename-reconcile (git --find-renames ⊆ occurrence-map) + occurrence⊆map cross-check | WP04 | |
| T014 | Wire audience `--strict` + relative_link_fixer `--check` + changed-path scoping (#3147) into docs-freshness.yml | WP04 | |
| T015 | Repoint documentation mission.yaml deliverables off docs/output/ | WP05 | |
| T016 | Retire research/, core-concepts/, updates/, output/ (record fragment) | WP05 | |
| T017 | Fold reference/(skills,agent_profiles)→api/; retire reference umbrella | WP06 | |
| T018 | Rehome batch-api-contract→api/; reconcile api index/toc; drop dead apidoc glob | WP06 | |
| T019 | api kebab + one index; migrate audience: on touched api pages | WP06 | |
| T020 | Collapse README-1.x/2.x/3.x → adr era distill; repoint src/doctrine diagram anchors FIRST | WP07 | |
| T021 | Rehome loose root explanation files + doctrine explanation → architecture/ | WP07 | |
| T022 | Rehome spec-kitty-mission-workflow.md → architecture; update 4 canonical-producer refs | WP07 | |
| T023 | architecture index completeness (curated-complete) + kebab; audience:; scanability rewrite phase | WP07 | |
| T024 | ADR era README→index (reconcile #2227); #2887 dated-prefix + redundant doc_status fixes | WP08 | [P] |
| T025 | migrations delete-stale (reclassify completed one-offs); kebab numbered file | WP08 | [P] |
| T026 | Rehome examples/→guides; place user-facing how-tos | WP09 | |
| T027 | Tutorials split; Divio type on all guides pages; collapse 3 indexes | WP09 | |
| T028 | Subdivide guides by concern; index per subdir; kebab; audience:; rewrite phase | WP09 | |
| T029 | Route contributor how-tos + reference_policy into development/ | WP10 | |
| T030 | Subdivide development by concern; index; kebab; audience:; rewrite phase | WP10 | |
| T031 | Fold glossary/→context; rehome contextive-glossaries + spec-driven→context; update charter-paths test | WP11 | |
| T032 | Repair 3 dead authority paths in charter.yaml + governance.yaml | WP11 | |
| T033 | context index/kebab; audience: | WP11 | |
| T034 | media→assets; manual README `<img>` logo rewrite | WP12 | |
| T035 | Rehome HOW_TO_MAINTAIN + p0-baseline→operations; fold release-goals + archive→changelog | WP12 | |
| T036 | operations/changelog index/kebab; audience:; rewrite phase | WP12 | |
| T037 | Merge occurrence-map fragments; regenerate redirect_map (derived); verify coverage prior+new | WP13 | |
| T038 | Regenerate nav manifests (toc/docfx/llms/per-section) + inventory lockfiles in place | WP13 | |
| T039 | Fix docs/plans/** inbound link-targets; update CLAUDE.md/AGENTS.md doc refs | WP13 | |
| T040 | Add required pre-merge docfx build workflow; flip structural invariants blocking (OB-2); FR-022 stub-prefix; final green | WP13 | |
| T041 | Root-allowlist check (docs outside docs/ vs closed allowlist) — NFR-006/SC-002 | WP04 | |
| T042 | Reconcile stale plans/notes terminology-guard exemption (NFR-004) before plans link-fix | WP11 | |

## Work Packages

### WP01 — Doctrine canonization *(foundation)*
Goal: canonize the `audience:` field and the audience-based routing/lint config in the doctrine SSOT so
everything downstream consumes one authority. Priority: P1. Independent test: 042/047/styleguide declare
`audience:` with a tooling row; `concern_bucket_to_section` reflects audience routing; lint config carries
the new invariant fields. Subtasks: T001–T003. Deps: none. Requirement refs: FR-002, FR-009, FR-023.
owned_files: `packs/built-in/directives/042-common-docs.directive.yaml`, `packs/built-in/directives/047-audience-oriented-writing.directive.yaml`, `packs/built-in/styleguides/common-docs.styleguide.yaml`.

### WP02 — Audience catalog + resolver *(foundation)*
Goal: make the existing catalog kebab-clean and add the non-vacuous resolver + test. Priority: P1.
Independent test: resolver fails on dangling + zero-examined. Subtasks: T005–T007. Deps: none.
Requirement refs: FR-001, FR-003. owned_files: `docs/context/audience/**`, `scripts/docs/audience_resolver.py`, `tests/docs/test_audience_resolves.py`. create_intent: `["scripts/docs/audience_resolver.py","tests/docs/test_audience_resolves.py"]`.

### WP03 — Move spine & redirect tooling *(foundation)*
Goal: author the collapsed cumulative occurrence-map spine + repoint the tool default. Priority: P1.
Independent test: `regenerate-map` reproduces all 151 prior entries + new (T010). Subtasks: T008–T010.
Deps: none. Requirement refs: FR-021, NFR-010. owned_files: `kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml`, `scripts/docs/redirect_stub_generator.py`, `tests/docs/test_redirect_spine.py`. create_intent: `["tests/docs/test_redirect_spine.py"]`.

### WP04 — Gate scaffolding *(foundation)*
Goal: build the touched-set + reconciliation + extended-lint gates (advisory). Priority: P1. Independent
test: gates run green on the current tree, red on injected violations. Subtasks: T004, T011–T014, T041. Deps: WP01, WP02, WP03.
(T004 reconciled from WP01 per three-way parity guard.)
Requirement refs: FR-017, FR-018, FR-023, NFR-002, NFR-005. owned_files: `packs/built-in/assets/docs_structural_lint.py`, `scripts/docs/touched_set_gates.py`, `scripts/docs/rename_reconcile.py`, `tests/docs/test_touched_set_gates.py`, `.github/workflows/docs-freshness.yml`, `packs/built-in/styleguides/common-docs.styleguide.yaml`, `scripts/generate_schemas.py`, `src/doctrine/schemas/styleguide.schema.yaml`, `tests/doctrine/test_schema_generation_integrity.py`. create_intent: `["scripts/docs/touched_set_gates.py","scripts/docs/rename_reconcile.py","tests/docs/test_touched_set_gates.py"]`.

### WP05 — Retire & documentation-mission repoint *(mover)*
Goal: retire zero-value dirs and repoint the documentation mission deliverables. Priority: P2. Subtasks:
T015–T016. Deps: WP03, WP04. Requirement refs: FR-006. owned_files: `research/**`, `docs/core-concepts/**`, `docs/updates/**`, `docs/output/**`, `src/specify_cli/missions/documentation/mission.yaml`.

### WP06 — docs/api consolidation *(mover)*
Goal: fold `reference/` into `api/`, rehome the API contract, reconcile the api index/toc. Priority: P2.
Subtasks: T017–T019. Deps: WP03, WP04. Requirement refs: FR-004, FR-005, FR-007, FR-012, FR-013, FR-014. owned_files: `docs/api/**`, `docs/reference/**`, `contracts/batch-api-contract.md`.

### WP07 — docs/architecture convergence *(mover)*
Goal: collapse the version shadow to one living design, rehome loose explanation files, move the canonical
workflow doc. Priority: P2. Subtasks: T020–T023. Deps: WP03, WP04. Requirement refs: FR-004, FR-007, FR-008, FR-012, FR-013, FR-014. owned_files: `docs/architecture/**`, `docs/status-model.md`, `docs/trail-model.md`, `docs/host-surface-parity.md`, `docs/doctrine/**`, `spec-kitty-mission-workflow.md`, `scripts/lint_canonical_producers.py`, `tests/status/test_producer_conformance.py`, `tests/docs/test_no_retrospect_preview.py`, `.github/workflows/canonical-producer-lint.yml`.

### WP08 — docs/adr + migrations curation *(mover)*
Goal: era-index normalization, #2887 dated-prefix fixes, migrations delete-stale. Priority: P3. Subtasks:
T024–T025. Deps: WP03, WP04. Requirement refs: FR-013, FR-015, FR-024. owned_files: `docs/adr/**`, `docs/migrations/**`.

### WP09 — docs/guides (user surface) *(mover)*
Goal: rehome examples, place user how-tos, split tutorials, type + subdivide guides. Priority: P2.
Subtasks: T026–T028. Deps: WP01, WP03, WP04. Requirement refs: FR-004, FR-005, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014. owned_files: `docs/guides/**`, `examples/**`.

### WP10 — docs/development (contributor surface) *(mover)*
Goal: route contributor how-tos + reference_policy into development/, subdivide, type. Priority: P2.
Subtasks: T029–T030. Deps: WP01, WP03, WP04. Requirement refs: FR-009, FR-010, FR-011, FR-012, FR-013, FR-014. owned_files: `docs/development/getting-started/**`, `docs/development/how-to/**`, `docs/development/reference/**`, `docs/development/testing/**`, `docs/development/index.md`. (Excludes the `3-2-*.yaml` rollups — WP13.) create_intent: WP-defined subdir indexes.

### WP11 — docs/context + governance paths *(mover)*
Goal: fold glossary, rehome context explanation files, repair the 3 dead authority paths. Priority: P2.
Subtasks: T031–T033, T042. Deps: WP03, WP04. Requirement refs: FR-004, FR-005, FR-016, FR-019. owned_files: `docs/context/index.md`, `docs/context/execution.md`, `docs/context/orchestration.md`, `docs/context/identity.md`, `docs/context/governance.md`, `docs/context/doctrine.md`, `docs/contextive-glossaries.md`, `glossary/**`, `spec-driven.md`, `.kittify/charter/charter.yaml`, `.kittify/charter/governance.yaml`, `tests/docs/test_current_charter_paths.py`. (Excludes `docs/context/audience/**` — WP02.)

### WP12 — media/assets + operations/changelog *(mover)*
Goal: move media to assets (+ README logo), rehome ops docs, fold release-goals + archive into changelog.
Priority: P2. Subtasks: T034–T036. Deps: WP03, WP04. Requirement refs: FR-004, FR-005, FR-006, FR-012, FR-013, FR-014. owned_files: `media/**`, `docs/assets/**`, `README.md`, `docs/operations/**`, `docs/changelog/**`, `docs/release-goals/**`, `docs/archive/**`, `HOW_TO_MAINTAIN.md`, `docs/p0-baseline-refresh.md`.

### WP13 — Terminal reconcile + gates blocking *(terminal)*
Goal: merge fragments, regenerate all shared manifests + lockfiles, fix plans/CLAUDE refs, register the
required pre-merge build, flip structural gates blocking, final green. Priority: P1. Subtasks: T037–T040.
Deps: WP05, WP06, WP07, WP08, WP09, WP10, WP11, WP12. Requirement refs: FR-016, FR-020, FR-022, NFR-001, NFR-003, NFR-010. owned_files: `scripts/docs/redirect_map.yaml`, `docs/toc.yml`, `docs/docfx.json`, `docs/llms.txt`, `docs/development/3-2-page-inventory.yaml`, `docs/development/3-2-docs-retrieval-index.yaml`, `CLAUDE.md`, `AGENTS.md`, `.github/workflows/docs-build-pr.yml`. create_intent: `[".github/workflows/docs-build-pr.yml"]`. (Also applies link-target-only edits under `docs/plans/**` as the single writer — recorded as bounded out-of-map edits. Per-section `toc.yml` is owned by each section's mover, not WP13.)

## MVP / sequencing
Foundations WP01–WP04 are the MVP enabling everything. Movers WP05–WP12 run after WP04 (WP09/WP10 also
after WP01). WP13 is terminal after all movers. WP08 is the most independent mover.
