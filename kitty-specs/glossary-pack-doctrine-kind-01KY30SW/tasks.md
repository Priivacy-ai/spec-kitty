# Tasks: Glossary Pack Doctrine Kind (Mission A)

**Feature dir**: `kitty-specs/glossary-pack-doctrine-kind-01KY30SW/`
**Planning base / merge target**: `research/glossary-doctrine-artefact`
**Source of truth**: `plan.md` (IC-01…07, squad-hardened), `spec.md`, `data-model.md`,
`contracts/pack-schema.md`, `reviews/post-plan-squad.md`.

Naming invariant (squad M4): plural == dir == accessor == `glossary_packs`; built-in dir
`built-in/` (hyphen); enum value / URN prefix singular `glossary_pack` (underscore). Every WP is
ATDD **red-first**; every guard is co-located with the surface it protects.

## Work-package map

| WP | Goal | ICs | Depends | Subtasks | Est. lines |
|----|------|-----|---------|----------|-----------|
| WP01 | Kind registration (ArtifactKind + NodeKind + URN + token) | IC-01 | — | 5 | ~320 |
| WP02 | Pack repository + schema + service accessor + boundary guard | IC-02, C-002 | WP01 | 6 | ~420 |
| WP03 | Built-in pack + extractor emission + root graph fragment + parity + regression | IC-04, IC-05, SC-004 | WP01, WP02 | 6 | ~460 |
| WP04 | Charter activation wiring + three-way drift-guard + default-on | IC-03 | WP01, WP02, WP03 | 6 | ~470 |
| WP05 | Doctor reporting + performance | IC-06 | WP02, WP04 | 3 | ~220 |

MVP / keystone slice: **WP01 → WP02 → WP03** delivers a loaded, resolving, parity-checked built-in
pack (the core value); WP04 adds default-on activation; WP05 adds observability.

## Subtask index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | URN hyphen-rejection regression (RED-first): `glossary_pack:` accepted, `glossary-pack:` rejected | WP01 | |
| T002 | Add `ArtifactKind.GLOSSARY_PACK` + `_PLURALS`/`_PATTERNS`; assert NOT in `_NON_AUGMENTATION_ELIGIBLE_KINDS` | WP01 | |
| T003 | Add `NodeKind.GLOSSARY_PACK` + comment fence vs runtime `GLOSSARY`/`GLOSSARY_SCOPE` | WP01 | |
| T004 | Assert `from_operator_token`/`CHARTER_KIND_TOKENS`/`YAML_KEY_MAP` derive the kind (free) | WP01 | |
| T005 | Kind-classification test: charter-activatable, token present | WP01 | |
| T006 | Model round-trip test (RED): all seed fields, `confidence: float`, `None` defaults | WP02 | |
| T007 | Implement `GlossaryPack`/`GlossaryTerm` models (all fields) | WP02 | |
| T008 | Implement `GlossaryPackRepository(BaseDoctrineRepository)` glob `*.glossary-pack.yaml`; `__all__` | WP02 | |
| T009 | `DoctrineService.glossary_packs` accessor + `_built_in_dir("glossary_packs")` | WP02 | |
| T010 | Duplicate-surface validation (synthetic fixture) + enforcement-field round-trip | WP02 | |
| T011 | C-002 import-boundary test: no `src/glossary` import from `src/doctrine/glossary_packs/` | WP02 | |
| T012 | Non-vacuous resolves-as-loaded-node guard with negative-control arm (RED) | WP03 | |
| T013 | New emission block in `extract_artifact_edges` (extract helper, complexity ≤15) | WP03 | |
| T014 | Author `spec-kitty-core.glossary-pack.yaml` — migrate all 104 seed terms, all fields | WP03 | |
| T015 | Regenerate + commit `src/doctrine/glossary_pack.graph.yaml` (root) | WP03 | |
| T016 | Standing pack⟺seed full-key parity test + 3 `synonyms_to_avoid` round-trip | WP03 | |
| T017 | SC-004 regression guard: pre-existing casing + legacy-terminology gates stay green | WP03 | |
| T018 | `activations.py`: `_ALLOWED_KINDS` + `_SINGULAR_TO_PLURAL_KIND` | WP04 | |
| T019 | `pack_context.py`: `_BUILTIN_ARTIFACT_KINDS` + `activated_glossary_packs` field/reader/wiring | WP04 | |
| T020 | `org_pack_loader._ORG_DRG_KIND_ALIASES` + `consistency_check._CLI_KIND_TO_DRG_SINGULAR` + `charter/drg.py` maps | WP04 | |
| T021 | Update exact-set tests (`test_pack_manager*`, `test_packcontext_has_all_ten` 10→11) | WP04 | |
| T022 | Extend drift-guard to three-way (incl `_BUILTIN_ARTIFACT_KINDS`) + positive default-on assertion (RED) | WP04 | |
| T023 | Default-on end-to-end: built-in pack active with no manual activate; cascade activate/deactivate | WP04 | |
| T024 | Doctor health test (RED): glossary-pack counts + invalid→unhealthy (synthetic fixture) | WP05 | |
| T025 | Implement glossary-pack health in `_doctrine_health.py` | WP05 | |
| T026 | Doctor `< 2 s` performance assertion (NFR-005) | WP05 | |

---

## WP01 — Kind registration (ArtifactKind + NodeKind + URN + token)

- **Goal**: `GLOSSARY_PACK` exists as a first-order, charter-activatable kind with the correct
  underscore URN; the derived token/classification machinery picks it up for free.
- **Priority**: P1 (foundation). **Depends**: none.
- **Independent test**: URN regression + classification tests go green; `from_operator_token('glossary-pack')` → `glossary_pack`.
- **Prompt**: `tasks/WP01-kind-registration.md`

- [x] T001 URN hyphen-rejection regression, RED-first (WP01)
- [x] T002 ArtifactKind.GLOSSARY_PACK + plurals/patterns + exclusion-set assertion (WP01)
- [x] T003 NodeKind.GLOSSARY_PACK + comment fence (WP01)
- [x] T004 Derived-token/classification assertions (WP01)
- [x] T005 Charter-activatable classification test (WP01)

## WP02 — Pack repository + schema + service accessor + boundary guard

- **Goal**: Load `*.glossary-pack.yaml` into `GlossaryPack`/`GlossaryTerm` (all seed fields,
  `confidence: float`) via a `BaseDoctrineRepository`; expose `DoctrineService.glossary_packs`;
  guard against runtime coupling.
- **Priority**: P1. **Depends**: WP01.
- **Independent test**: model round-trip (all fields) + duplicate-surface rejection + import-boundary test green.
- **Prompt**: `tasks/WP02-repository-schema-service.md`

- [x] T006 Model round-trip test, RED (WP02)
- [x] T007 GlossaryPack/GlossaryTerm models (WP02)
- [x] T008 GlossaryPackRepository + `__all__` (WP02)
- [x] T009 DoctrineService.glossary_packs accessor (WP02)
- [x] T010 Duplicate-surface + enforcement-field round-trip (WP02)
- [x] T011 C-002 import-boundary architectural test (WP02)

## WP03 — Built-in pack + extractor emission + root graph fragment + parity + regression

- **Goal (load-bearing)**: The built-in `spec-kitty-core` pack (104 terms, all fields) is emitted
  by the extractor, ships a generated root graph fragment, resolves as a loaded DRG node, and stays
  in standing parity with the seed. Runtime stays green.
- **Priority**: P1. **Depends**: WP01, WP02.
- **Independent test**: resolves-as-loaded-node guard (with negative control) + standing parity + regression suites green.
- **Prompt**: `tasks/WP03-builtin-pack-emission-resolution.md`

- [x] T012 Non-vacuous resolves-as-loaded-node guard, RED (WP03)
- [x] T013 Extractor emission block + helper (WP03)
- [x] T014 Author + migrate 104-term built-in pack (WP03)
- [x] T015 Regenerate + commit root graph fragment (WP03)
- [x] T016 Standing pack⟺seed full-key parity + synonyms round-trip (WP03)
- [x] T017 SC-004 regression guard (WP03)

## WP04 — Charter activation wiring + three-way drift-guard + default-on

- **Goal**: The kind activates/cascades/deactivates generically across ALL activation surfaces; the
  built-in pack is active by default; the drift-guard actually protects default-on (three-way).
- **Priority**: P1. **Depends**: WP01, WP02, WP03 (needs the graph fragment for resolution).
- **Independent test**: extended three-way drift-guard + positive default-on assertion + cascade test green; exact-set tests updated.
- **Prompt**: `tasks/WP04-charter-activation-wiring.md`

- [x] T018 activations._ALLOWED_KINDS + _SINGULAR_TO_PLURAL_KIND (WP04)
- [x] T019 pack_context._BUILTIN_ARTIFACT_KINDS + activated_glossary_packs (WP04)
- [x] T020 org_pack_loader alias + consistency_check + charter/drg.py maps (WP04)
- [x] T021 Update exact-set tests (10→11) (WP04)
- [x] T022 Extend drift-guard three-way + default-on assertion, RED (WP04)
- [x] T023 Default-on + cascade end-to-end (WP04)

## WP05 — Doctor reporting + performance

- **Goal**: `spec-kitty doctor doctrine --json` reports glossary-pack counts + health; invalid packs
  never healthy; doctor stays under 2 s.
- **Priority**: P2. **Depends**: WP02, WP04.
- **Independent test**: doctor health test (valid + invalid fixture) + perf assertion green.
- **Prompt**: `tasks/WP05-doctor-reporting.md`

- [ ] T024 Doctor health test, RED (WP05)
- [ ] T025 Implement glossary-pack health (WP05)
- [ ] T026 Doctor `< 2 s` perf assertion (WP05)
