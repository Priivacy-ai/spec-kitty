# Tasks: Built-In Doctrine Seam Consolidation

**Mission**: `doctrine-built-in-seam-consolidation-01KYW3TX`
**Branch**: `feat/relocate-builtin-doctrine-packs` (planning base + merge target)
**Input**: [plan.md](plan.md) (IC-01..07), [spec.md](spec.md) (FR/NFR/C), [contracts/built-in-location-authority.md](contracts/built-in-location-authority.md), [occurrence_map.yaml](occurrence_map.yaml), [notes/research-synthesis.md](notes/research-synthesis.md)

Work is partitioned by **file** (not by concern) to keep `owned_files` strictly non-overlapping — the
seam work is tightly coupled across shared files, so each source/test file has exactly one owner. WP01 is
the additive foundation; WP02/WP03/WP05 route readers onto it in parallel; WP04 drops the fail-open param
and adds the CI ratchet once all production readers (incl. WP05's `pack_manager.py:658`) are migrated;
WP07 migrates the coupled test callers after the param is gone; WP06 (context-shim shrink) lands after
WP07; WP08 is fully independent.

## Subtask Index

| Task | Description | WP | Requirements |
|------|-------------|----|--------------|
| T001 | Add content-dir SSOT attribute in `artifact_kinds.py`; `built_in_root()` + `built_in_dir(kind)` + computed-complement raise | WP01 | FR-001, FR-001b, FR-004, FR-005, NFR-005 |
| T002 | Route the 9 doctrine-repository defaults through `built_in_dir(kind)` | WP01 | FR-002 |
| T003 | Route the 2 DRG root callers (`loader.py:135`, `extractor.py:113`) through `built_in_root()` | WP01 | FR-002, FR-001b |
| T004 | Verify additive + behaviour-preserving (graph identity, per-authority tests, ruff/mypy) | WP01 | FR-004, NFR-001, NFR-003 |
| T005 | Route catalog/compiler (incl. :873)/kind-vocabulary variable-indirected joins → `built_in_dir` | WP02 | FR-002 |
| T006 | Remove nested dual-read fallbacks (`catalog.py:283`, `compiler.py:1162`, `kind_vocabulary.py:179`) | WP02 | FR-006 |
| T007 | Strip dead `built_in_root=None` (compiler/doctrine_service_builder); root call → `built_in_root()` | WP02 | FR-003, FR-001b |
| T008 | Repoint `resolver.py:187,250` operator strings → `packs/built-in/<kind>/` | WP02 | FR-009 |
| T009 | Retire CWD ancestor-walk in `doctrine.py:204-210` → `built_in_root()` (NFR-001 delta) | WP03 | FR-006, NFR-001 |
| T010 | Route pack-validator + tool-surface joins → `built_in_dir(kind)` | WP03 | FR-002 |
| T011 | Strip dead `built_in_root=None` (factory / org_layer / generate) | WP03 | FR-003 |
| T012 | Update the 2 SOURCE `SKILL.md` `DoctrineService(built_in_root=None)` examples | WP03 | FR-003 |
| T013 | Drop `built_in_root` param + nested `_built_in_dir` from `service.py` | WP04 | FR-003, FR-004 |
| T014 | Joins-only AST ratchet (both join limbs, permit bare root, exempt ~20 markers) + negative bite test | WP04 | NFR-002 |
| T015 | Positive per-kind coverage via `resolve_pack_root(...)` + `#3091`-marked derived complement | WP04 | NFR-003, NFR-005, FR-005 |
| T016 | Anti-vacuity: shipped `agent_profiles` non-empty | WP04 | NFR-003 |
| T017 | Fix live migration drift (`activated_glossary_packs`) + derive migration keys from `YAML_KEY_MAP` | WP05 | FR-010 |
| T018 | Derive `charter_yaml_io._ACTIVATION_KEYS` from the authority | WP05 | FR-010 |
| T019 | Set-equality guard test (both vocab lists == derived authority) | WP05 | FR-010 |
| T020 | Route the `pack_manager.py:658` join → `built_in_dir`; leave the 5 marker sites | WP05 | FR-002 |
| T032 | End-to-end finalize-migration test: activated glossary pack survives onto charter.yaml | WP05 | FR-010 |
| T021 | Inventory private `charter.context` symbols → leaf-module map | WP06 | FR-011 |
| T022 | Repoint imports/patches in the 17 owned test files (mind multi-line blocks) | WP06 | FR-011 |
| T023 | Delete the `context.py` re-export block; keep the public surface | WP06 | FR-011 |
| T024 | Migrate nested-tmp `built_in_root=` group → `SPEC_KITTY_PACKS_ROOT` / flat | WP07 | FR-003 |
| T025 | Real-repo-stale group + own the org-pack collision RED (assert `DoctrineLayerCollisionWarning`) | WP07 | FR-003, FR-007 |
| T026 | Glossary-gate fixture (`test_gate_terms.py`) loads from `packs/built-in/<kind>/` | WP07 | FR-007 |
| T027 | Fix false-green profile-inheritance fixture + repoint `_render_profile_sections` in 2 dual files | WP07 | FR-008 |
| T028 | Verify completeness — zero `built_in_root=`, zero dead reader paths | WP07 | FR-003, FR-008 |
| T029 | Verify provenance fields are descriptive, not runtime-resolved (record in evidence) | WP08 | FR-012 |
| T030 | Sweep descriptive `src/doctrine/<kind>/built-in/` → `packs/built-in/<kind>/` in 18 YAMLs | WP08 | FR-012 |
| T031 | Verify no dead path + graph identity unchanged | WP08 | FR-012, NFR-001 |

## Dependency graph

```
WP01 (foundation, additive) ──┬── WP02 (charter readers) ──┐
                              ├── WP03 (specify_cli readers) ┼── WP04 (drop param + ratchet) ── WP07 (test-caller migration) ── WP06 (context shim, test-only)
                              └── WP05 (activation vocab) ───┘
WP08 (provenance sweep)        — independent
```

WP04 depends on WP02 + WP03 + **WP05** (its joins-only ratchet enforces against `pack_manager.py:658`,
which WP05 migrates). WP06 depends on **WP07** (WP07 repoints the two `_render_profile_sections` test
importers before the shim shrink lands). Full chain `WP06 → WP07 → WP04 → {WP02, WP03, WP05} → WP01` is
acyclic; WP08 is independent.

---

## WP01 — Built-in location authorities + repo defaults + DRG root callers

- **Summary**: Add a content-dir SSOT attribute to `artifact_kinds.py`, then create `built_in_dir(kind)`
  + `built_in_root()` in `pack_paths.py` with the **computed** `{mission_step_contract, template,
  anti_pattern}` complement raise; route the 9 repository defaults and the 2 DRG root callers through them.
  Additive, behaviour-preserving, zero deps.
- **Implementation sketch**: new `has_built_in_content_dir` / `_BUILT_IN_CONTENT_KINDS` (the 9) in
  `artifact_kinds.py` — NOT `_NON_AUGMENTATION_ELIGIBLE_KINDS` (wrong set); `built_in_dir` =
  `resolve_pack_root("built-in") / kind.plural`, complement = members minus the attribute (no literal in
  `pack_paths.py`); `built_in_root()` wraps `resolve_pack_root("built-in")`. Repos call
  `built_in_dir(<kind>)`; `drg/loader.py:135` + `drg/migration/extractor.py:113` call `built_in_root()`.
- **Reference rows**: T001 SSOT attr + authorities + computed raise (WP01) · T002 9 repo defaults (WP01) · T003 2 DRG callers (WP01) · T004 verify (WP01)
- **Dependencies**: none.
- **Risks**: `pack_paths`→`artifact_kinds` import-cycle (verified leaf, enum-only); reusing the wrong SSOT set; hand-listed complement drift; not the leaf `built_in_dir=` param.
- **Estimated size**: 13 files (incl. `artifact_kinds.py`), 4 subtasks, S–M.

## WP02 — Charter-layer readers

- **Summary**: Route the variable-indirected `catalog.py` joins + `compiler.py`/`kind_vocabulary.py`
  joins through `built_in_dir`; remove the three nested dual-reads; strip two `built_in_root=None` sites;
  route `bootstrap_text.py:271` root call; repoint `resolver.py:187,250` operator strings.
- **Implementation sketch**: `catalog.py:74` local var + :80/:89/:102/:111/:120/:129/:138 joins →
  per-kind `built_in_dir` calls; `compiler.py:842/843/934` **and :873** (the `python-implementation`
  styleguide ref) → `built_in_dir`; delete `catalog.py:283`/`compiler.py:1162`/`kind_vocabulary.py:179`
  fallbacks; `resolve_doctrine_root()` (catalog.py:160) stays live (template sets only).
- **Reference rows**: T005 route joins (WP02) · T006 remove dual-reads (WP02) · T007 strip None + root call (WP02) · T008 operator strings (WP02)
- **Dependencies**: WP01.
- **Risks**: missed variable-indirected join (SC-001 false + ratchet false-green); over-reaching into `resolve_doctrine_root`; touching a forbidden-pattern guard.
- **Estimated size**: 6 files, 4 subtasks, M.

## WP03 — specify_cli readers + skill templates

- **Summary**: Retire the `doctrine.py` CWD-walk (intentional NFR-001 delta) → `built_in_root()`; route
  `pack_validator.py:793` + `tool_surface/bundles/claude.py:434` joins; strip three `built_in_root=None`
  sites; update the two SOURCE `SKILL.md` examples.
- **Implementation sketch**: `doctrine.py:204-210` → `built_in_root()`; `pack_validator.py:786` var +
  :793 join → `built_in_dir`; factory/org_layer/generate lose the `None` kwarg; edit only
  `src/doctrine/skills/**/SKILL.md`.
- **Reference rows**: T009 CWD-walk retire (WP03) · T010 route joins (WP03) · T011 strip None + fix `_doctrine_asset.py:54` comment (WP03) · T012 SKILL.md examples (WP03)
- **Dependencies**: WP01. Parallel with WP02 (disjoint files).
- **Risks**: NFR-001 delta undocumented; missed `pack_validator.py:793` join; editing generated skill copies.
- **Estimated size**: 9 files (2 SOURCE docs, +`_doctrine_asset.py` comment), 4 subtasks, M.

## WP04 — Drop the fail-open param + anti-regression ratchet

- **Summary**: Drop `DoctrineService.built_in_root` + nested `_built_in_dir` (all production callers
  migrated by WP01/02/03); add the joins-only AST ratchet + positive per-kind coverage + `#3091`-marked
  complement + anti-vacuity in its OWN new arch file.
- **Implementation sketch**: `service.py` param/helper removed, `SPEC_KITTY_PACKS_ROOT` preserved; new
  `tests/architectural/test_built_in_location_authority.py` with both join limbs, marker exemptions,
  negative bite test, coverage via `resolve_pack_root(...)`, non-empty `agent_profiles`.
- **Reference rows**: T013 drop param (WP04) · T014 joins-only ratchet (WP04) · T015 per-kind coverage + #3091 (WP04) · T016 anti-vacuity (WP04)
- **Dependencies**: WP02, WP03, **WP05** (the ratchet enforces against `pack_manager.py:658`, which WP05 migrates — without it the gate false-reds its own keystone). WP07 depends on this WP.
- **Risks**: grammar too narrow (false-green indirected joins) / too broad (false-red markers); raw `.exists()` (#3036); folding into the dead-paths file (#3039).
- **Estimated size**: 2 files (1 new), 4 subtasks, M — the keystone gate.

## WP05 — Activation-vocabulary unification + migration drift fix

- **Summary**: Derive both activation-key vocabularies from `YAML_KEY_MAP`; fix the live drift so the
  finalize migration carries `activated_glossary_packs`; route the `pack_manager.py:658` join; add a
  set-equality guard. **Must land before Mission 2** (C-004).
- **Implementation sketch**: cheap plain-tuple constant from `YAML_KEY_MAP` (no heavy import) consumed by
  `charter_yaml_io._ACTIVATION_KEYS` + migration `ACTIVATION_KEYS`; only :658 is a join (five marker
  sites stay).
- **Reference rows**: T017 drift fix + derive migration keys (WP05) · T018 derive io keys (WP05) · T019 set-equality guard (WP05) · T020 route :658 join (WP05) · T032 e2e finalize-migration regression (WP05)
- **Dependencies**: WP01 (for T020). WP04 depends on this WP. Parallel with WP02/WP03.
- **Risks**: heavy import in the migration; editing a marker site as a join; C-004 ordering.
- **Estimated size**: 4 files (1 new), 5 subtasks, M.

## WP06 — context.py shim shrink (severable, test-only)

- **Summary**: Census `src/` + `tests/` for private `charter.context` importers; repoint the DELETE-set
  (test-only) importers to leaf modules and remove only those re-exports; **retain** every re-export a
  production function-local cycle-breaker imports; public surface unchanged.
- **Implementation sketch**: census → retain/delete split; rewrite `from charter.context import _x` →
  `from <leaf> import _x` for DELETE-set; keep RETAIN-set (e.g. `_build_doctrine_service`,
  `_render_profile_sections`, `_iter_org_charter_docs`, `_read_org_required_selections`,
  `_default_agent_profile_repository`, …) and RETAIN-set patch targets on `charter.context`; keep `__all__`.
- **Reference rows**: T021 repo-wide census (WP06) · T022 repoint DELETE-set in owned tests (WP06) · T023 remove DELETE-set re-exports only (WP06)
- **Dependencies**: **WP07** (repoints the two `_render_profile_sections` test importers first). No production importer file is edited.
- **Risks**: deleting a production-imported private (census guards it); repointing a RETAIN-set patch target off `charter.context`; multi-line imports.
- **Estimated size**: 18 files (1 src, 17 tests), 3 subtasks, M — mechanical but wide; a shrink, not a wholesale delete.

## WP07 — Relocation-completeness + param-test migration

- **Summary**: Migrate the ~16 `built_in_root=` test callers off the dropped param; fix the glossary-gate
  + false-green profile-inheritance fixtures; own the org-pack collision RED (self-resolve + assert the
  warning). Zero relocation readers remain on a dead path (SC-003).
- **Implementation sketch**: nested-tmp group → `SPEC_KITTY_PACKS_ROOT`; real-repo/None group → remove
  kwarg; `test_org_pack_artifact_lifecycle.py` asserts `DoctrineLayerCollisionWarning`;
  `test_gate_terms.py`/`test_profile_inheritance.py` → `packs/built-in/`; repoint the 2 dual files'
  `_render_profile_sections`. Honour occurrence_map (`built_in_dir=` leaf + guard docstrings stay).
- **Reference rows**: T024 nested-tmp group (WP07) · T025 real-repo group + collision RED (WP07) · T026 glossary gate (WP07) · T027 false-green + dual-import repoint (WP07) · T028 verify (WP07)
- **Dependencies**: WP04. Non-overlap with WP06 (`test_context.py` stays WP06).
- **Risks**: touching the `built_in_dir=` leaf param; collision test green-without-warning; `test_pack_relocation_guard.py` docstring.
- **Estimated size**: 18 test files, 5 subtasks, M–L (the big `test_service_org_layer.py` has 17 sites).

## WP08 — Provenance-string sweep (severable, lowest)

- **Summary**: After verifying the fields are descriptive (not runtime-resolved), sweep the stale
  `src/doctrine/<kind>/built-in/` strings in 18 shipped artefact YAMLs to `packs/built-in/<kind>/`.
  occurrence_map-governed.
- **Implementation sketch**: trace `related:`/`source_files:` read paths → confirm descriptive (record in
  evidence); same-string rename per occurrence_map `filesystem_paths: rename`; escalate any
  runtime-resolved field to FR-008 (WP07).
- **Reference rows**: T029 verify descriptive (WP08) · T030 sweep 18 YAMLs (WP08) · T031 verify no dead path + graph identity (WP08)
- **Dependencies**: none. Fully parallel.
- **Risks**: sweeping a runtime-resolved field; touching an occurrence_map exception file.
- **Estimated size**: 18 YAML files, 3 subtasks, S — mechanical, gated by the T029 verification.

---

## Recommended FR → WP coverage (for `map-requirements`)

| Requirement | WP(s) |
|-------------|-------|
| FR-001 | WP01 |
| FR-001b | WP01 |
| FR-002 | WP01, WP02, WP03, WP05 |
| FR-003 | WP02, WP03, WP04, WP07 |
| FR-004 | WP01, WP04 |
| FR-005 | WP01, WP04 |
| FR-006 | WP02, WP03 |
| FR-007 | WP07 |
| FR-008 | WP07 |
| FR-009 | WP02 |
| FR-010 | WP05 |
| FR-011 | WP06 |
| FR-012 | WP08 |
| NFR-001 | WP03, WP04 (+ WP01/WP08 graph-identity checks) |
| NFR-002 | WP04 |
| NFR-003 | WP04 (+ WP01 authority tests) |
| NFR-004 | all WPs |
| NFR-005 | WP04 |
