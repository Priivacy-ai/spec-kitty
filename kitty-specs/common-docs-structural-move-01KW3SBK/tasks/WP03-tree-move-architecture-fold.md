---
work_package_id: WP03
title: Tree move — fold architecture/ (non-ADR) into docs/ per the occurrence map
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-004
- FR-009
- C-006
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: architecture/
create_intent: []
execution_mode: code_change
owned_files:
- architecture/2.x/00_landscape/**
- architecture/2.x/01_context/**
- architecture/2.x/02_containers/**
- architecture/2.x/03_components/**
- architecture/2.x/04_implementation_mapping/**
- architecture/diagrams/**
- architecture/assessments/**
- architecture/audits/**
- architecture/calibration/**
- architecture/audience/**
- architecture/2.x/initiatives/**
- architecture/2.x/user_journey/**
- architecture/2.x/05_ownership_manifest.yaml
- architecture/2.x/05_ownership_map.md
- architecture/2.x/06_unified_charter_bundle.md
- architecture/2.x/06_migration_and_shim_rules.md
- architecture/2.x/shim-registry.yaml
- architecture/*/research/**
- architecture/*/vision/**
- architecture/1.x/notes/**
- architecture/*/README.md
- architecture/README.md
- architecture/ARCHITECTURE_DOCS_GUIDE.md
- architecture/NAVIGATION_GUIDE.md
- architecture/adr-template.md
- architecture/2026-04-14-windows-compatibility-hardening-mission-review.md
- architecture/test-suite-acceleration-plan.md
- glossary/contexts/**
- CHANGELOG.md
- docs/architecture/**
- docs/context/**
- docs/migrations/**
- docs/plans/**
- docs/changelog/**
role: implementer
tags: []
shell_pid: "1389389"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Execute the **non-ADR** half of the two-root collapse: fold the `architecture/` root (everything **except** the `<era>/adr/` trees and flat `architecture/adrs/`, which WP06 owns) into the unified 13-section `docs/` root, following the **`moves:` spine in `occurrence_map.yaml`** exactly. Move the glossary human narrative into `docs/context/` **while preserving the `.kittify/glossaries/<scope>.yaml` seed read-path and the doctrine-extraction source** (C-006, merge-blocker). Relocate `CHANGELOG.md` **with an alias** (root copy persists for release tooling).

This is IC-03a, the **gating move** — WP04, WP05, WP06, WP07, WP08, WP09, WP10 all wait on it. It runs only after WP01 (runtime reads dual-read + tested) and WP02 (baseline captured + committed).

## Context

`occurrence_map.yaml` `moves:` is the authority for every old→new path-pair (23 mappings). This WP executes the **non-ADR** subset:
- C4 design layers (`2.x/00_landscape`…`04_implementation_mapping`), `diagrams/`, vision narratives, assessments/audits/calibration, ownership/charter artifacts, per-era + root READMEs, navigation guides, `adr-template.md` → **`docs/architecture/`** (FR-004, unified unversioned living design).
- `2.x/06_migration_and_shim_rules.md` + `2.x/shim-registry.yaml` → **`docs/migrations/`** (the shim-registry's runtime readers were dual-read in WP01; this move lands the new home).
- research / initiatives / user_journey / `1.x/notes` / loose mission-review + acceleration-plan + `docs/engineering_notes` → **`docs/plans/`** (distil-then-retire). **Note:** `docs/engineering_notes` re-section is WP04's per-file split; this WP moves the `architecture/`-rooted plans content.
- `architecture/audience` + `glossary/contexts` → **`docs/context/`** (FR-009, C-006).
- `CHANGELOG.md` → `docs/changelog/` as **relocate-with-alias** (root copy persists).

**Out of scope for this WP (owned elsewhere):** the `<era>/adr/` + flat `architecture/adrs/` trees (WP06); `docs/development` + `docs/engineering_notes` per-file durable-vs-ephemeral split (WP04); `docs/1x`/`2x`/`3x` shadow trees (WP10); `docfx.json`/TOC rewrites (WP09); the reference rewrites (WP08).

**Inventory file STAYS PUT** (operator directive): do **not** move `docs/development/3-2-page-inventory.yaml`. Accidentally moving it re-opens the freshness-gate self-block.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-001 (two-root collapse), FR-004 (single unversioned `docs/architecture/`), FR-009 (source→target mapping: CHANGELOG→`changelog/`, glossary+audiences→`context/`, user-journeys+investigations→`plans/`), C-006 (glossary seed read-path + extraction source preserved — merge-blocker).

## Subtasks

### T014 — Move the living-design surfaces → `docs/architecture/`
Per `moves:`, relocate the C4 layers, `diagrams/`, vision narratives, assessments/audits/calibration, the 2.x ownership/charter artifacts, per-era + root READMEs, navigation guides, and `adr-template.md` into `docs/architecture/`. De-version (no `2.x/` prefix) — FR-004 unifies into one living root. `05_ownership_manifest.yaml` is a one-off design artifact (the runtime `OwnershipManifest` reads per-WP frontmatter, NOT this file — verified), so it moves with the rest.

### T015 — Move migration + shim artifacts → `docs/migrations/`
Relocate `2.x/06_migration_and_shim_rules.md` and `2.x/shim-registry.yaml` to `docs/migrations/`. The 3 shim-registry readers were dual-read in WP01 to `docs/migrations/shim-registry.yaml` — this move lands that home. After the move, the new path resolves; the old-branch drop happens in WP08.

### T016 — Move research/initiatives/journeys/loose-plans → `docs/plans/`
Relocate research deliverables (`*/research`), `2.x/initiatives`, `2.x/user_journey`, `1.x/notes`, and the two loose `architecture/`-root docs (`2026-04-14-windows-compatibility-hardening-mission-review.md`, `test-suite-acceleration-plan.md`) into `docs/plans/` (distil-then-retire lifecycle, `doc_status: draft|active`). This is the `architecture/`-rooted plans content only; `docs/engineering_notes` is WP04.

### T017 — Move glossary + audiences → `docs/context/` (C-006 merge-blocker)
Relocate `architecture/audience` and `glossary/contexts/*.md` into `docs/context/`. **Move only the human markdown.** Verify the dashboard `GlossaryHandler` + `load_seed_file()` still resolve the `.kittify/glossaries/<scope>.yaml` seed read-path (untouched), and that `generate_contextive_glossaries.py` (dual-read in WP01) resolves the new `docs/context/` source. This is the C-006 merge-blocker — do not move or rename any `.kittify/glossaries/` file.

### T018 — CHANGELOG relocate-with-alias
Place the canonical `CHANGELOG` copy at `docs/changelog/` and **keep `CHANGELOG.md` at the repo root as an alias/copy** (release tooling — `scripts/release/`, `pyproject.toml`, `.github/release-readiness.yml` — reads root and is out-of-relocate-scope). The two copies are kept in sync; root is the alias, `docs/changelog` is canonical. (The reference rewrite for CHANGELOG mentions lives in WP08.)

### T019 — Append move pairs to the redirect map + verify section index.md
For every relocation in T014–T018, record the old→new pair so WP07's redirect-stub generator can emit a stub (the redirect map is WP07-owned and **derived from `occurrence_map.yaml` `moves:`** — confirm each move executed here is represented in `moves:`; do not hand-edit WP07's map). Ensure each new `docs/` section (`architecture/`, `context/`, `migrations/`, `plans/`, `changelog/`) carries an `index.md` (the anti-sprawl ratchet floor; WP14 flips it blocking).

### T020 — Verify the move + suite green
Confirm `architecture/`'s non-ADR content is gone from the old root (the `<era>/adr/` + `architecture/adrs/` trees remain for WP06). Run the WP01 resolution tests (still green — old ∪ new, now the new path is real). Run `ruff`/`mypy` on any touched `src/` (none expected) and the terminology guard. Confirm `docs/development/3-2-page-inventory.yaml` was **not** moved.

## Surfaces & Loci (from `occurrence_map.yaml` `moves:`, non-ADR subset)

| From (old) | To (new) | Reason |
|------------|----------|--------|
| `architecture/2.x/{00_landscape…04_implementation_mapping}`, `diagrams/`, `*/vision`, `assessments`/`audits`/`calibration`, `2.x/05_ownership_*`, `06_unified_charter_bundle.md`, per-era + root `README.md`, `ARCHITECTURE_DOCS_GUIDE.md`, `NAVIGATION_GUIDE.md`, `adr-template.md` | `docs/architecture` | FR-004 unified unversioned living design |
| `architecture/2.x/06_migration_and_shim_rules.md`, `architecture/2.x/shim-registry.yaml` | `docs/migrations` | shim-registry runtime readers dual-read in WP01 |
| `architecture/{1.x,2.x,3.x}/research`, `2.x/initiatives`, `2.x/user_journey`, `1.x/notes`, 2 loose root docs, `docs/engineering_notes`* | `docs/plans` | FR-009 distil-then-retire (*engineering_notes per-file in WP04) |
| `architecture/audience`, `glossary/contexts` | `docs/context` | FR-009 + C-006 (glossary read-path preserved) |
| `CHANGELOG.md` | `docs/changelog` | FR-009 — **relocate-with-alias** (root copy persists) |

**Excluded (owned elsewhere):** `architecture/{1.x,2.x,3.x}/adr` + `architecture/adrs` (WP06); `docs/development`/`docs/engineering_notes` per-file split (WP04); `docs/{1x,2x,3x}` (WP10); `docs/docfx.json`/`toc.yml` (WP09). **STAYS PUT:** `docs/development/3-2-page-inventory.yaml`.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-001 (two-root collapse) | T014, T015, T016 |
| FR-004 (single unversioned `docs/architecture/`) | T014 |
| FR-009 (source→target mapping) | T016, T017, T018 |
| C-006 (glossary seed read-path + extraction source preserved — merge-blocker) | T017, T020 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. This is the **gating move** — WP04/05/06/07/08/09/10 all depend on it. Sequenced after WP01 (reads safe) + WP02 (baseline captured).

## Definition of Done

- [ ] All non-ADR `architecture/` content folded into `docs/` per the `moves:` spine; the `<era>/adr/` + flat `architecture/adrs/` trees are intentionally left for WP06.
- [ ] **Source→dest reconciliation (not just "gone from old root"):** for every `moves:` pair, assert the destination file **exists AND its bytes match the source** — a move proven only by the old path's absence passes on a plain deletion (data loss). Reconcile the moved-file count source-side vs dest-side; they must be equal.
- [ ] Glossary human markdown moved to `docs/context/`; **C-006 merge-blocker satisfied** — `.kittify/glossaries/<scope>.yaml` seed read-path untouched, `GlossaryHandler`/`load_seed_file()` + `generate_contextive_glossaries.py` resolve.
- [ ] **C-006 proven executably, not by inspection:** WP01's runtime-read resolution test (which covers `generate_contextive_glossaries.py`'s `GLOSSARY_CONTEXTS_DIR` + the governance glossary authority-path) is **re-run green after this move** — it loads the seed via `load_seed_file()` and emits contexts, guarding the dashboard glossary read-path against a silent break. If that test does not exercise `GlossaryHandler` end-to-end, extend it (coordinate with WP01's owned test) rather than relying on manual checks.
- [ ] `CHANGELOG.md` relocate-with-alias: canonical in `docs/changelog/`, alias persists at repo root.
- [ ] `docs/development/3-2-page-inventory.yaml` **NOT moved** (freshness-gate self-block avoided).
- [ ] **Redirect/back-compat in place so no reference or runtime read breaks**: every move is represented in `occurrence_map.yaml` `moves:` (so WP07 emits a stub); WP01's dual-read keeps old references resolving until WP08's sweep; every new section has `index.md`.
- [ ] WP01 resolution tests still green; terminology guard clean.

## Risks & Reviewer Guidance

- **Reviewer (merge-blocker focus):** C-006 — exercise the dashboard glossary read-path and `generate_contextive_glossaries.py` against the moved `docs/context/` tree; a broken seed read-path blocks merge.
- **Accidentally moving the inventory file** re-opens the freshness self-block (FR-010) — confirm it stayed put.
- **ADR-tree leakage** — this WP must NOT touch `<era>/adr/` or `architecture/adrs/` (WP06 owns content-invariant ADR conversion); moving them here without invariance proof risks C-002.
- This WP MOVES files but does not rewrite the in-tree *references* to them (WP08) — do not attempt the bulk reference sweep here; just ensure `moves:` represents every relocation.

## Activity Log

- (populated at implement time)
- 2026-06-27T13:02:25Z – claude:opus:python-pedro:implementer – shell_pid=1360345 – Assigned agent via action command
- 2026-06-27T13:18:02Z – claude:opus:python-pedro:implementer – shell_pid=1360345 – Ready: 113 non-ADR files moved (docs/architecture, docs/plans, docs/context, docs/migrations 2, docs/changelog canonical+root alias); source->dest 113/113 byte-match, count 113==113; C-006 test_runtime_read_resolution.py GREEN (17 passed), glossary seed .kittify/glossaries untouched; terminology guard GREEN (reworded 1 pre-existing 'ceremony' in moved persona); ADR trees + 3-2-page-inventory.yaml zero diff. IC-01: 3 collision clusters (10 divergent files, moves: collapses N->1) resolved data-preserving via era-suffix (README-1.x/2.x/3.x.md) - needs reviewer ratification. Expected WP08-owned breakage: test_architecture_docs_consistency.py 2 fails (stale OLD-layout fixture + ADR-tree link to moved adr-template.md) - occurrence_map tests_fixtures sweep; tests/ not in WP03 owned_files.
- 2026-06-27T13:19:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=1389389 – Started review via action command
- 2026-06-27T13:26:42Z – user – shell_pid=1389389 – Review passed: 111/112 renames byte-identical + 1 canon-mandated ceremony->process reword (zero data loss), CHANGELOG aliased byte-equal=113/113 moves; collision-clusters era-suffixed (data-preserving, distillation=follow-up); C-006 green (15 passed); terminology guard green; ADR trees+inventory+tests/+docfx untouched; architecture/ now ADR-only
