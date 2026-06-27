# Tasks: Common Docs Structural Move (Mission B)

**Mission**: `common-docs-structural-move-01KW3SBK` · **Branch**: `docs/2165-mission-b-structural-move` · **Closes**: #2165, #2054, #2192 · **Folds**: #1815 · **change_mode**: `bulk_edit`

15 work packages execute the plan's **serial spine** (the 8-IC structure, IC-split per the plan's `/tasks` sizing guidance). **This is a `bulk_edit` mission** — `occurrence_map.yaml` (2920 occ / 751 files / 23 path-pairs) is the classification authority; the no-overlap guard is **relaxed** for the bulk move/rewrite WPs, and the occurrence-map category partition disjoints the actual edits.

**Lane shape (the spine, NOT a parallel fan-out):**
`WP01` (land-first runtime reads) → `WP02` (pre-move baseline capture) → `WP03` (the gating tree move) → then the move window fans out: `WP04` (re-section) ∥ `WP05`→`WP06` (ADR conversion) ∥ `WP07` (redirects) ∥ `WP08` (refs) ∥ `WP09` (docfx/TOC) ∥ `WP10` (shadow trees), with the FR-010 backfill chain `WP11`→`WP12`→`WP13` → `WP14` (flip rulers blocking + C-005 dry-run) → `WP15` (ADR amendment + LEAK retirement). The IC-04 (ADR) ∥ IC-05 (refs) parallelism is enabled by the `era_less_pinned` filenames in the occurrence map.

**Mission-critical invariants (merge-blockers):** C-002 (no ADR content mutation — content-invariance proof, WP05/WP06); C-006 (glossary read-path preserved, WP01/WP03); C-004 (`docs/3x` distil-not-blind-delete, WP10); C-005 (the WP14 full-gate dry-run must go **RED on a re-introduced violation** — gate-unmask cannot self-validate). Every MOVE WP's DoD includes "redirect/back-compat in place so no reference or runtime read breaks."

> **Note:** the orchestrator runs `map-requirements` + `finalize-tasks`. `requirement_refs` in each WP frontmatter + the "Requirement refs" body block are **hints** for that pass.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Read the occurrence map's runtime-read contract | WP01 | | [D] |
| T002 | Author the resolution-test harness (RED-first) | WP01 | | [D] |
| T003 | `authority_paths.py`: dual-read ADR + glossary literals | WP01 | | [D] |
| T004 | Shim-registry readers: dual-read to `docs/migrations/` | WP01 | | [D] |
| T005 | Remediation string lock-step (`cli/commands/doctor.py:509`) | WP01 | | [D] |
| T006 | Non-`src/` read 5: `generate_contextive_glossaries.py` | WP01 | | [D] |
| T007 | Non-`src/` read 6: `governance.yaml` authority_paths | WP01 | | [D] |
| T008 | Prove all 6 reads resolve + suite green | WP01 | | [D] |
| T009 | Install DocFX (pinned) | WP02 | | [D] |
| T010 | Build the PRE-move tree | WP02 | | [D] |
| T011 | Snapshot the `_site` URL set into the manifest | WP02 | | [D] |
| T012 | Unit test the capture | WP02 | | [D] |
| T013 | Commit the baseline manifest BEFORE WP03 | WP02 | | [D] |
| T014 | Move the living-design surfaces → `docs/architecture/` | WP03 | | [D] |
| T015 | Move migration + shim artifacts → `docs/migrations/` | WP03 | | [D] |
| T016 | Move research/initiatives/journeys/loose-plans → `docs/plans/` | WP03 | | [D] |
| T017 | Move glossary + audiences → `docs/context/` (C-006) | WP03 | | [D] |
| T018 | CHANGELOG relocate-with-alias | WP03 | | [D] |
| T019 | Append move pairs to redirect map repr + verify section index.md | WP03 | | [D] |
| T020 | Verify the move + suite green | WP03 | | [D] |
| T021 | Enumerate + classify every `docs/development/` page | WP04 | [D] |
| T022 | Classify `docs/engineering_notes/` | WP04 | [D] |
| T023 | Move durable pages → operations/guides/configuration | WP04 | [D] |
| T024 | Move ephemeral pages → `docs/plans/` | WP04 | [D] |
| T025 | Assert the inventory file STAYED PUT | WP04 | [D] |
| T026 | Verify the re-section + suite green | WP04 | [D] |
| T027 | Parser 1: markdown-table header | WP05 | [D] |
| T028 | Parser 2: bold-inline header | WP05 | [D] |
| T029 | Parser 3: dash-bullet header (the missed dialect) | WP05 | [D] |
| T030 | Frontmatter emitter (bare `status`, MADR vocabulary) | WP05 | [D] |
| T031 | Content-invariance check (reuse `_inventory.parse_frontmatter`) | WP05 | [D] |
| T032 | Test the converter on all 3 dialects + invariance | WP05 | [D] |
| T033 | Prove the 47 mirrors byte-identical, THEN drop | WP06 | [D] |
| T034 | Convert + move the 97 era ADRs → `docs/adr/<era>/` | WP06 | [D] |
| T035 | Migrate the 20 era-less ADRs → `docs/adr/3.x/` at pinned filenames | WP06 | [D] |
| T036 | Run content-invariance over all 117 | WP06 | [D] |
| T037 | Census check: count == 117 | WP06 | [D] |
| T038 | Close the flat shim | WP06 | [D] |
| T039 | Verify + suite green | WP06 | [D] |
| T040 | Derive the redirect map from `occurrence_map.yaml` `moves:` | WP07 | [D] |
| T041 | `generate(redirect_map, site_dir) -> emitted_stubs` | WP07 | [D] |
| T042 | `check_coverage(baseline, redirect_map, site_dir) -> uncovered[]` | WP07 | [D] |
| T043 | Test the generator + coverage | WP07 | [D] |
| T044 | Wire into `docs-pages.yml` (between build + upload) | WP07 | [D] |
| T045 | Verify coverage == 100% against the committed baseline | WP07 | [D] |
| T046 | Drop the WP01 dual-read OLD branches | WP08 | [D] |
| T047 | Rewrite the remaining `src/` references (the ~39 non-runtime) | WP08 | [D] |
| T048 | Rewrite `tests/` fixtures + assertions | WP08 | [D] |
| T049 | Rewrite `kitty-specs/` + `docs/` prose references | WP08 | [D] |
| T050 | Targeted-ref-update: `ci-quality.yml` glob (CRITICAL) | WP08 | [D] |
| T051 | Targeted-ref-update: glossary functional refs + governance verify | WP08 | [D] |
| T052 | CHANGELOG reference rewrite (alias-aware) | WP08 | [D] |
| T053 | Verify the sweep + suite green | WP08 | [D] |
| T054 | Rewrite `docs/docfx.json` content + exclude globs | WP09 | [D] |
| T055 | Rewrite every `toc.yml` href to the 13 sections | WP09 | [D] |
| T056 | Update `docs/llms.txt` + `docs/index.md` nav | WP09 | [D] |
| T057 | DocFX build green on the post-move tree | WP09 | [D] |
| T058 | Verify + coordinate #648 | WP09 | [D] |
| T059 | Delete `docs/1x` + `docs/2x` with redirect entries | WP10 | [D] |
| T060 | Distil `docs/3x` live charter content | WP10 | [D] |
| T061 | Fix the 3 `docs/3x` nav refs | WP10 | [D] |
| T062 | Record the #2053 landing zone | WP10 | [D] |
| T063 | Verify-before-delete the 4 `docs/architecture/` orphans | WP10 | [D] |
| T064 | Verify + redirect coverage for the shadow deletes | WP10 | [D] |
| T065 | Define the `tag → doc_status` mapping table | WP11 | | [D] |
| T066 | Build the backfill tool (`frontmatter_backfill.py`) | WP11 | | [D] |
| T067 | Build the 50–180 `description` length gate | WP11 | | [D] |
| T068 | Derive `related` edges from in-body links | WP11 | | [D] |
| T069 | Test the tooling | WP11 | | [D] |
| T070 | Verify + suite green | WP11 | | [D] |
| T071 | Run WP11's backfill tool over the tree | WP12 | | [D] |
| T072 | Author `description` for every page (50–180) | WP12 | | [D] |
| T073 | Author/complete `related` edges (0 dangling) | WP12 | | [D] |
| T074 | Validate the full frontmatter set | WP12 | | [D] |
| T075 | Verify + hand off to WP13 | WP12 | | [D] |
| T076 | Regenerate the lockfile from frontmatter | WP13 | |
| T077 | Drive drift to 0 | WP13 | |
| T078 | Prove generate == committed (deterministic) | WP13 | |
| T079 | Verify + hand off to WP14 | WP13 | |
| T080 | R3 code change 1: thread `strict=True` | WP14 | |
| T081 | R3 code change 2: escalate severity to `error` | WP14 | |
| T082 | R3 code change 3: remove the opt-in guard (default-on) | WP14 | |
| T083 | CI wiring in `docs-freshness.yml` | WP14 | |
| T084 | Ruler-blocking regression tests | WP14 | |
| T085 | C-005 full-gate dry-run (RED on re-introduced violation) | WP14 | |
| T086 | Verify + suite green on the clean tree | WP14 | |
| T087 | Confirm the lockfile gate is proven blocking (FR-014 precondition) | WP15 | |
| T088 | Amend the reconciliation ADR Neutral note (FR-013) | WP15 | |
| T089 | Retire `LEAK-FRONTMATTER-MISMATCH` (FR-014) | WP15 | |
| T090 | Confirm no enforcement gap | WP15 | |
| T091 | Verify + suite green | WP15 | |
| T092 | Move how-to + tutorials → docs/guides | WP16 | | [D] |
| T093 | Move reference → docs/api | WP16 | | [D] |
| T094 | Move explanation → docs/architecture | WP16 | | [D] |
| T095 | Move recovery → docs/operations | WP16 | | [D] |
| T096 | Regenerate redirect_map + re-verify coverage | WP16 | | [D] |
| T097 | Verify re-section + suite green | WP16 | | [D] |
| T098 | Build the relative-link resolver | WP18 | |
| T099 | Dry-run + report unresolvable | WP18 | |
| T100 | Apply the relative-link rewrites | WP18 | |
| T101 | Body-link-resolution gate | WP18 | |
| T102 | Test the fixer | WP18 | |
| T103 | Verify + suite green | WP18 | |

## Work Packages

### WP01 — Land-first runtime-critical reads — `tasks/WP01-runtime-critical-land-first-reads.md`
- **Goal**: Re-point the 6 land-first runtime reads (4 `src/` + 2 non-`src/`) as dual-read (old ∪ new) with resolution tests, BEFORE any move (C-003). **Requirements**: FR-005, NFR-005, C-003. **Independent test**: `test_runtime_read_resolution.py` proves all 6 new paths resolve via the reader (RED-first).
- **Subtasks**: T001–T008. **Deps**: none (spine head). **Risk**: dropping the dual-read before WP03 = runtime break; C-006 extraction source.

### WP02 — Redirect baseline-URL capture (PRE-move) — `tasks/WP02-baseline-url-capture.md`
- **Goal**: Install DocFX, build the **pre-move** tree, snapshot + commit the baseline-URL manifest (the NFR-002 denominator). **Requirements**: FR-006, NFR-002. **Independent test**: `test_capture_baseline_urls.py` (normalisation over a fixture `_site`).
- **Subtasks**: T009–T013. **Deps**: WP01. **Risk**: capturing post-move = unfalsifiable 100%.

### WP03 — Tree move (architecture/ non-ADR fold) — `tasks/WP03-tree-move-architecture-fold.md`
- **Goal**: Fold `architecture/` (non-ADR) into `docs/` per the `moves:` spine; glossary→`context/` (C-006); CHANGELOG relocate-with-alias; inventory STAYS PUT. **Requirements**: FR-001, FR-004, FR-009, C-006. **Independent test**: WP01 resolution tests stay green; glossary read-path resolves.
- **Subtasks**: T014–T020. **Deps**: WP02. **Risk**: glossary seed read-path (merge-blocker); accidentally moving the inventory file. **Gates WP04–WP10.**

### WP04 — Re-section development + engineering_notes — `tasks/WP04-resection-development-engineering-notes.md`
- **Goal**: Per-file durable-vs-ephemeral re-section (FR-012/#2054); inventory yaml stays put. **Requirements**: FR-001, FR-012. **Independent test**: per-file classification table is auditable; inventory-path-stable guard.
- **Subtasks**: T021–T026. **Deps**: WP03. **Parallel** with WP05.

### WP05 — ADR converter + 3 parsers — `tasks/WP05-adr-converter-three-parsers.md`
- **Goal**: 3 parsers (table/bold-inline/dash-bullet) + content-invariance check (reuse `_inventory.parse_frontmatter`). **Requirements**: FR-002, FR-003, C-002, NFR-001. **Independent test**: a fixture per dialect green; a **mutation fixture RED** (false-green-proof).
- **Subtasks**: T027–T032. **Deps**: WP03. **Parallel** with WP04/WP07/WP08/WP09. WP06 consumes it.

### WP06 — Run the 117-unique ADR conversion — `tasks/WP06-adr-conversion-117-unique.md`
- **Goal**: Convert 117 → `docs/adr/<era>/`; 20 era-less → `adr/3.x/` (pinned); drop 47 mirrors; census == 117; content-invariance for all 117. **Requirements**: FR-002, FR-003, C-002, NFR-001. **Independent test**: count-117 census + invariance over all 117.
- **Subtasks**: T033–T039. **Deps**: WP05. **Parallel-safe with WP08** via `era_less_pinned`.

### WP07 — Redirect-stub generator + coverage — `tasks/WP07-redirect-stub-generator.md`
- **Goal**: `redirect_stub_generator.py` + redirect map (derived from `moves:`, single-writer) + coverage-vs-baseline; wire into `docs-pages.yml` between build+upload. **Requirements**: FR-006, NFR-002. **Independent test**: emit correctness + no-404 + coverage-RED-on-gap.
- **Subtasks**: T040–T045. **Deps**: WP02, WP03. **Parallel** in the move window.

### WP08 — Bulk reference rewrite — `tasks/WP08-bulk-reference-rewrite.md`
- **Goal**: ~2920 refs via the occurrence map + targeted-ref-updates (`ci-quality.yml` glob CRITICAL, glossary, CHANGELOG alias) + drop WP01 dual-read old branches. **Requirements**: FR-005, FR-009. **Independent test**: stale-`architecture/`-reference grep clean; resolution tests still green after old-branch drop.
- **Subtasks**: T046–T053. **Deps**: WP03, WP06. **Bulk overlap** with WP09/WP12 under `docs/**` (category-disjoint, sequenced).

### WP09 — docfx.json + TOC rewrite — `tasks/WP09-docfx-toc-rewrite.md`
- **Goal**: `docfx.json` globs + every `toc.yml` → 13-section; DocFX build green (FR-007). **Requirements**: FR-007. **Independent test**: `docfx docs/docfx.json` green; no dangling href.
- **Subtasks**: T054–T058. **Deps**: WP03. **Bulk overlap** with WP08/WP12 (serialized config only). Coordinates #648.

### WP10 — Shadow-tree resolution — `tasks/WP10-shadow-tree-resolution.md`
- **Goal**: `docs/1x`+`2x` delete+redirect; `docs/3x` distil+move+redirect (C-004); 4 architecture orphans verify-before-delete. **Requirements**: FR-008. **Independent test**: no shadow tree survives; shadow URLs covered by stubs; `docs/3x` charter content present in `context/`.
- **Subtasks**: T059–T064. **Deps**: WP03, WP07. **Risk**: C-004 blind-delete (merge-blocker).

### WP11 — Frontmatter backfill TOOLING + description gate — `tasks/WP11-frontmatter-backfill-tooling.md`
- **Goal**: `tag→doc_status` mapping + `frontmatter_backfill.py` + the **net-new 50–180 `description` length gate** + `related`-edge derivation. **Requirements**: FR-010, NFR-003, NFR-004. **Independent test**: `tag→doc_status` correctness + idempotence; length-gate boundaries (49/181 RED).
- **Subtasks**: T065–T070. **Deps**: WP04.

### WP12 — Frontmatter backfill AUTHORING (~580 pages) — `tasks/WP12-frontmatter-backfill-authoring.md`
- **Goal**: Author per-page `description` (50–180) + `related`; run the backfill. **Requirements**: FR-010, NFR-003, NFR-004. **Independent test**: `description_length_check.py` all green (no placeholders); `related_validator.py` 0 dangling.
- **Subtasks**: T071–T075. **Deps**: WP11. **High-touch content WP.** **Bulk overlap** with WP08/WP09 (frontmatter fields only).

### WP13 — Lockfile regen → drift 0 — `tasks/WP13-lockfile-regen-drift-zero.md`
- **Goal**: Regenerate the lockfile FROM the backfilled frontmatter; drift (252 removed / 296 changed) → 0; generated == committed. **Requirements**: FR-010, NFR-006. **Independent test**: two regens identical; committed == fresh regen.
- **Subtasks**: T076–T079. **Deps**: WP12, WP08. Precondition for WP14.

### WP14 — Flip the 3 rulers to blocking — `tasks/WP14-flip-rulers-blocking.md`
- **Goal**: R1/R2 `--strict` + R3 lockfile gate (3 code changes: thread `strict=True` [no-op] + severity→`error` + **remove the opt-in guard**) + CI wiring in `docs-freshness.yml` + **C-005 full-gate dry-run**. **Requirements**: FR-011, C-005, NFR-006, SC-005. **Independent test (DoD-critical)**: the full-gate dry-run goes **RED on a re-introduced violation** over the whole tree.
- **Subtasks**: T080–T086. **Deps**: WP13, WP06, WP10. **Risk**: gate-unmask cannot self-validate; flipping before drift=0 self-blocks merge.

### WP15 — ADR-note amendment + LEAK retirement — `tasks/WP15-adr-amendment-leak-retirement.md`
- **Goal**: Amend the reconciliation ADR Neutral note → 3 doctrine tactics (FR-013, sanctioned self-amendment); retire `LEAK-FRONTMATTER-MISMATCH` now the lockfile gate is blocking (FR-014). **Requirements**: FR-013, FR-014. **Independent test**: no enforcement gap; the amendment is scoped out of the invariance check.
- **Subtasks**: T087–T091. **Deps**: WP14. **Spine tail.**

### WP16 — Divio re-section (FR-009 IC-01 correction) — `tasks/WP16-divio-resection.md`
- **Goal**: Fold the 120 existing Divio pages (how-to+tutorials→guides, reference→api, explanation→architecture, recovery→operations) into the 13-section structure per FR-009 — the IC-01 correction the original spine missed (surfaced by WP09 review; without it the pages orphan and guides/api stay empty). Regenerate WP07's redirect_map to cover the now-moved published URLs. **Requirements**: FR-001, FR-009. **Independent test**: source→dest byte reconciliation (no data loss); the 120 Divio URLs redirect-covered against the 168 baseline; docs/api populated. **Bulk overlap**: writes guides/operations/architecture (WP04/WP03) + redirect_map (WP07) as sequenced leeway.
- **Subtasks**: T092–T097. **Deps**: WP03, WP04, WP07. Lands before WP08/WP12/WP14 (they depend on it for the complete assembled tree).

### WP18 — Relative-link integrity (FR-005 complement) — `tasks/WP18-relative-link-integrity.md`
- **Goal**: Fix the bare-relative intra-doc body links broken by the restructure (WP08-review IC — hundreds of `../../3.x/adr/…`-style links; not occurrence-map refs so WP08 didn't own them, and no existing gate catches them). A `moves:`-driven resolver rewrites each to its new location + a body-link-resolution gate so the class can't recur. Added in-mission (operator decision, mirrors WP16). **Requirements**: FR-005, NFR-004. **Independent test**: every bare-relative intra-doc body link in `docs/` resolves on disk; unresolvable links reported not guessed.
- **Subtasks**: T098–T103. **Deps**: WP04, WP06, WP08, WP10, WP16 (the full final tree). Lands before WP14 (its body-link gate joins the full-gate dry-run).
