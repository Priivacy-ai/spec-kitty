# Tasks: Consolidate the Compiled Charter Bundle

**Mission**: `consolidate-charter-bundle-01KXSYB9` | **Branch**: `feat/consolidate-charter-bundle` | **Date**: 2026-07-18
**Authoritative design**: [plan.md](./plan.md) (9-concern ICM), [data-model.md](./data-model.md) (3 landmines + INV-1..9), [contracts/](./contracts/). One WP per concern; owned_files are non-overlapping (squad-validated). One branch / one PR, tidy-first, no half-inverted ship (NFR-005/C-006).

## DAG / lanes
```
WP01 ─┬─ WP02 ─┐
      ├─ WP03 ─┼─ WP04 ── WP05 ── WP07
      └─ WP06 ─┘
      WP03 ── WP08 (P2)
      WP09 (docs, parallel — lands same PR)
```
Hard ordering (NFR-005): within WP04, re-point loaders BEFORE deleting the scrape. WP07 (migration/retirement) lands last so no consumer is orphaned.

## Subtask Index
| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `CharterYaml` pydantic model (flat activation, nested governance/directives) | WP01 | |
| T002 | `CharterBundleManifest` v2 + distinct `content_hash_files` field | WP01 | |
| T003 | Shared `load→mutate-owned-section→round-trip-save` write helper (INV-9) | WP01 | |
| T004 | Unify the duplicated charter-filename constants (campsite) | WP01 | |
| T005 | Tests: manifest v2 validates; helper preserves non-owned sections | WP01 | |
| T006 | `PackContext.from_config` resolves charter.yaml via config `charter:` pointer + reads flat activation | WP02 | |
| T007 | `activation_engine.commit_plan` writes charter.yaml (diagnostics re-word) | WP02 | |
| T008 | `pack_manager.merge_defaults`/`_save_config` via shared helper | WP02 | |
| T009 | config.yaml pointer + two-file read + fail-loud dangling pointer | WP02 | |
| T010 | Tests: activation in charter.yaml; parity/DRG-filter suites green | WP02 | |
| T011 | Compiler emits charter.yaml PARTIAL/MERGE (preserve authored sections) | WP03 | |
| T012 | Remove the `compiler.py:421` clobber; retire references.yaml writer | WP03 | |
| T013 | `generate.py` autotrack + `charter_bundle.py` reconcile | WP03 | |
| T014 | Regenerate + commit spec-kitty's own charter.yaml | WP03 | |
| T015 | INVERT clobber tests → assert authored governance/prose survive `generate --force` | WP03 | |
| T016 | Re-point `sync.py` loaders → charter.yaml (BEFORE scrape delete) | WP04 | |
| T017 | Delete `sync()` scrape + `post_save_hook`; retire `extractor.py` scraper + dead AI stub | WP04 | |
| T018 | `consistency_check.py` re-point BOTH activation-list (:199) + catalog (:420); re-home #2530 | WP04 | |
| T019 | Bypass readers: `mission_type_profiles`, `spdd_reasons/activation` (+cache), `_doctrine_collect` | WP04 | |
| T020 | Tests: decision reads charter.yaml; #2530 fail-closed; parity green | WP04 | |
| T021 | `context.py` display prose call-sites re-point (display only) | WP05 | |
| T022 | `compact.py` + `context_renderers/section_bodies.py` display re-point | WP05 | |
| T023 | Tests: no governance decision reads charter.md prose | WP05 | |
| T024 | Freshness content-hash over charter.yaml (`content_hash_files`) | WP06 | |
| T025 | Rework/retire `_compute_charter_source`; decide+test spurious-authoring-staleness | WP06 | |
| T026 | Retire #2758 `first_missing_bundle_file` + #2759 parity read | WP06 | |
| T027 | Tests: freshness reflects mutation, no permanent-stale, #2732 preserved | WP06 | |
| T028 | New fold migration (verbatim, fail-loud, sequence after seed migrations, reconcile m_unify) | WP07 | |
| T029 | `state/contract.py` charter.yaml git-tracked + retire four; `.gitignore` | WP07 | |
| T030 | `versioning.py:166 read_bundle_schema_version` → charter.yaml | WP07 | |
| T031 | Tests: migration idempotent + fail-loud + verbatim + ordering | WP07 | |
| T032 | `language_scope.py` tier-3 charter.md fallback → `catalog.languages` | WP08 | [P] |
| T033 | Preserve tier-1 references/catalog precedence | WP08 | [P] |
| T034 | Tests: language scoping never reads charter.md prose | WP08 | [P] |
| T035 | Flip `docs/context/charter-overview.md` + `governance-files.md` | WP09 | [P] |
| T036 | Update `docs/api/charter-commands.md` + `docs/architecture/06_unified_charter_bundle.md` | WP09 | [P] |
| T037 | Update charter-doctrine SKILL assets + charter mission-step prompt | WP09 | [P] |
| T038 | Update baseline snapshots + freshen page inventory | WP09 | [P] |
| T039 | Terminology guard (`test_no_legacy_terminology.py`) | WP09 | [P] |

## Work Packages

### WP01 — Schema + manifest keystone (IC-02)
**Goal**: `CharterYaml` model + manifest v2 + the shared write helper. Unblocks all. **Priority**: P1. **Deps**: none. **Independent test**: manifest v2 validates with `charter.yaml` tracked (not derived); the write helper round-trips preserving non-owned sections. **Prompt**: [tasks/WP01-schema-manifest-keystone.md](./tasks/WP01-schema-manifest-keystone.md) (~5 subtasks).
- [x] T001 CharterYaml model (WP01)
- [x] T002 Manifest v2 + content_hash_files (WP01)
- [x] T003 Shared write helper INV-9 (WP01)
- [x] T004 Unify filename constants (WP01)
- [x] T005 Tests (WP01)

### WP02 — Activation relocation (IC-01)
**Goal**: relocate flat `activated_*` config→charter.yaml; re-point the activation engine + reader; config keeps the `charter:` pointer. **Priority**: P1. **Deps**: WP01. **Independent test**: activation lives in charter.yaml; `config.yaml` has no `activated_*`; parity + DRG-filter suites green. **Prompt**: [tasks/WP02-activation-relocation.md](./tasks/WP02-activation-relocation.md).
- [x] T006 from_config pointer + flat activation read (WP02)
- [x] T007 activation_engine commit_plan → charter.yaml (WP02)
- [x] T008 pack_manager via shared helper (WP02)
- [x] T009 config pointer + two-file read + fail-loud (WP02)
- [x] T010 Tests (WP02)

### WP03 — Writer + #2772 clobber guard (IC-03)
**Goal**: emit charter.yaml as a partial/merge write; kill the clobber; retire the references writer. **Priority**: P1. **Deps**: WP01. **Independent test**: authored governance/prose survive `charter generate --force`; charter.yaml emitted with authored+derived sections. **Prompt**: [tasks/WP03-writer-clobber-guard.md](./tasks/WP03-writer-clobber-guard.md).
- [x] T011 Compiler partial/merge emit (WP03)
- [x] T012 Remove clobber + retire references writer (WP03)
- [x] T013 generate.py autotrack + charter_bundle.py (WP03)
- [x] T014 Regenerate spec-kitty's own charter.yaml (WP03)
- [x] T015 Invert clobber tests (WP03)

### WP04 — Decision re-point + extractor retirement (IC-04)
**Goal**: re-point every governance/directive/parity DECISION reader to charter.yaml; delete the scrape + dead AI stub. **Priority**: P1. **Deps**: WP03, WP02. **Independent test**: governance/directive loaders + parity read charter.yaml; extractor deleted; #2530 fail-closed re-homed. **Prompt**: [tasks/WP04-decision-repoint-extractor-retire.md](./tasks/WP04-decision-repoint-extractor-retire.md).
- [x] T016 sync.py loaders → charter.yaml (WP04)
- [x] T017 Delete scrape + retire extractor (WP04)
- [x] T018 consistency_check both reads + #2530 (WP04)
- [x] T019 Bypass readers (WP04)
- [x] T020 Tests (WP04)

### WP05 — Display prose re-point (IC-05)
**Goal**: re-point display-only charter.md-prose consumers; no governance decision reads prose. **Priority**: P2. **Deps**: WP04. **Independent test**: policy summary + critical-section render intact; no decision reads charter.md. **Prompt**: [tasks/WP05-display-repoint.md](./tasks/WP05-display-repoint.md).
- [x] T021 context.py display sites (WP05)
- [x] T022 compact.py + section_bodies.py (WP05)
- [x] T023 Tests (WP05)

### WP06 — Freshness on charter.yaml (IC-06)
**Goal**: freshness content-hash over charter.yaml; rework charter_hash staleness; retire #2758/#2759. **Priority**: P1. **Deps**: WP01. **Independent test**: a mutation flips freshness; no permanent-stale; #2732 preserved. **Prompt**: [tasks/WP06-freshness.md](./tasks/WP06-freshness.md).
- [x] T024 charter.yaml content-hash (WP06)
- [x] T025 Rework _compute_charter_source + spurious-staleness (WP06)
- [x] T026 Retire #2758/#2759 (WP06)
- [x] T027 Tests (WP06)

### WP07 — Migration + fail-loud + git-class (IC-07)
**Goal**: idempotent fail-loud fold (four files + config activation → charter.yaml); retire the four; git-class. **Priority**: P1. **Deps**: WP01, WP02, WP03, WP04, WP06. **Independent test**: legacy fixture fails loud pre-migration, migrates deterministically, re-run reports 0 changes. **Prompt**: [tasks/WP07-migration-failloud-state.md](./tasks/WP07-migration-failloud-state.md).
- [ ] T028 Fold migration (WP07)
- [ ] T029 state/contract + .gitignore (WP07)
- [ ] T030 versioning.py repoint (WP07)
- [ ] T031 Tests (WP07)

### WP08 — Language tier-3 fallback (IC-08)
**Goal**: migrate the one behavioral charter.md-prose read off prose. **Priority**: P2. **Deps**: WP03. **Independent test**: language scoping resolves from catalog; never reads charter.md prose. **Prompt**: [tasks/WP08-language-tier3.md](./tasks/WP08-language-tier3.md).
- [x] T032 tier-3 → catalog.languages (WP08)
- [x] T033 Preserve tier-1 precedence (WP08)
- [x] T034 Tests (WP08)

### WP09 — Docs / skills / snapshots (IC-09)
**Goal**: flip every doc/doctrine surface asserting "charter.md is THE source"; update SKILL assets + baselines. **Priority**: P2. **Deps**: none (validate against landed behavior). Lands same PR (C-006). **Independent test**: no doc asserts charter.md-as-source; terminology guard green; inventory fresh. **Prompt**: [tasks/WP09-docs-skills-snapshots.md](./tasks/WP09-docs-skills-snapshots.md).
- [x] T035 Flip context docs (WP09)
- [x] T036 API + architecture docs (WP09)
- [x] T037 SKILL assets + charter prompt (WP09)
- [x] T038 Baseline snapshots + inventory (WP09)
- [x] T039 Terminology guard (WP09)

## MVP / sequencing note
WP01 is the keystone (MVP-enabling). The tidy-first chain WP01→WP02/03/06→WP04→WP05→WP07 must not ship a half-inverted intermediate (NFR-005) — the whole thing is one PR. WP08/WP09 parallelize.
