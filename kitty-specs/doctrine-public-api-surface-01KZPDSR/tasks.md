# Tasks: Doctrine Public API Surface

**Mission**: doctrine-public-api-surface-01KZPDSR
**Planning base / merge target**: `feat/doctrine-public-api-surface`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/public-api-contract.md](./contracts/public-api-contract.md)

10 work packages, 49 subtasks. Foundation-first: WP01 (census + golden + management enumeration)
gates everything. WP04 (ratchet) lands red-first before migration. WP05–07 migrate runtime
after the facades (WP03) exist. WP08–10 (Sonar debt) are behavior-locked by WP01's golden and
run in parallel, WP09/WP10 last per IC-09 isolation.

## Subtask Index (reference table — completion is event-sourced via `mark-status`)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Re-run reach-through census (AST direct+lazy, Sonar) and finalize the disposition table in data-model.md | WP01 | |
| T002 | Add census gate test asserting every non-exempt-reached path has a disposition | WP01 | |
| T003 | Wire `regenerate-graph --check` as the golden behavior-lock round-trip test | WP01 | [P] |
| T004 | Record the management-surface enumeration + the charter C-007 extension note | WP01 | |
| T005 | Create `src/doctrine/api.py` with curated `__all__` (PUBLIC surface) | WP02 | |
| T006 | Update `test_doctrine_wheel_closure.py` to pin the real surface | WP02 | |
| T007 | New `test_doctrine_public_surface.py`: pins `__all__` + INTERNAL negative assertion | WP02 | |
| T008 | Route caller-less wheel-only exports through `test_no_dead_symbols` `_SYMBOL_ALLOWLIST` w/ ticket | WP02 | |
| T009 | CHANGELOG entry (DIR-009) + charter C-007-extension note | WP02 | [P] |
| T010 | Widen `charter.drg` (DRGLoadError, DRGValidationError, resolve_org_roots, OrgDRGConflict) | WP03 | |
| T011 | Widen `charter.mission_steps` (GateBinding) | WP03 | |
| T012 | New `charter.missions` (MissionTemplateRepository, MissionsRootNotFound, MissionTypeRepository, builtin_mission_type_ids, project_template_set) | WP03 | |
| T013 | New `charter.model_routing` — symbol-level (`load`, `evaluate`, `RoutingRecommendation`) | WP03 | |
| T014 | New `charter.assets` (AssetRepository, AssetManifest, AssetNotFoundError, AssetPathEscapeError) | WP03 | |
| T015 | Narrow doors: `glossary_packs`, `spdd_reasons`, `pack_paths` built_in_dir/built_in_root | WP03 | |
| T016 | Grow `_FACADE_TABLE`; PUBLIC symbols re-export from `doctrine.api` | WP03 | |
| T017 | Sibling lazy-import ratchet: parent-tracking recursive descent (not `ast.walk`) | WP04 | |
| T018 | Only-shrink frozenset baseline seeded at the census | WP04 | |
| T019 | Source-side laundering guard (no doctrine symbol in `specify_cli.doctrine.*.__all__`) | WP04 | |
| T020 | Fixtures: TYPE_CHECKING not-flagged, nested-fn flagged; dynamic-import limit note | WP04 | [P] |
| T021 | De-export doctrine symbols from `specify_cli/doctrine/config.__all__` | WP05 | |
| T022 | Repoint config's non-exempt consumers to the `charter.drg` `resolve_org_roots` door (atomic) | WP05 | |
| T023 | Migrate `_doctrine_collect.py` onto facades | WP05 | |
| T024 | Migrate `_doctrine_asset.py` onto facades | WP05 | |
| T025 | Migrate `cli/commands/doctrine.py` onto facades | WP05 | |
| T026 | Fix the 5 raw `DoctrineService` sites — preserve `pack_context=None` semantics (raw_repository) | WP05 | |
| T027 | Migrate `invocation/org_profiles.py`, `mission_step_contracts/executor.py`, `_profile_health_render.py` | WP05 | |
| T028 | Migrate `invocation/executor.py` (profiles + capabilities + model_routing) | WP06 | |
| T029 | Migrate `profiles_cmd.py`, `agent/tasks_status_cmd.py` | WP06 | [P] |
| T030 | Migrate `review/gate_bindings.py`, `cli/commands/charter/_synthesis.py` | WP06 | [P] |
| T031 | Migrate `charter_runtime/lint/_drg.py` (keep the try/except graceful-degradation shape) | WP06 | [P] |
| T032 | Migrate `cli/commands/dispatch.py`, `cli/commands/agent/workflow.py` (model_routing) | WP06 | [P] |
| T033 | Migrate `template/manager.py`, `dossier/manifest.py`, `migration/rewrite_shims.py` (missions.repository) | WP07 | [P] |
| T034 | Migrate `skills/command_installer.py`, `skills/command_renderer.py`, `template/asset_generator.py` | WP07 | [P] |
| T035 | Migrate `cli/commands/mission_type.py`, `charter/{activate,mission_type,list_cmd}.py` | WP07 | [P] |
| T036 | Migrate `runtime/resolver.py`, `runtime/show_origin.py`, `mission_loader/command.py` | WP07 | [P] |
| T037 | Migrate `tool_surface/bundles/{claude,codex}.py` | WP07 | [P] |
| T038 | Migrate `upgrade/migrations/{m_2_1_3,m_2_1_4,m_3_2_0rc35}*.py` | WP07 | [P] |
| T039 | Hoist duplicate DRG-URN literals in `hand_authored_overlay.py` to named constants | WP08 | |
| T040 | Fix malformed suppression at `artifact_kinds.py:118` (S7632) | WP08 | [P] |
| T041 | Verify `regenerate-graph --check` byte-identical after WP08 edits | WP08 | |
| T042 | Refactor `extractor.py:545` (cc 183 → ≤15) with tested helpers | WP09 | |
| T043 | Refactor `extractor.py:933` + remaining extractor S3776 functions | WP09 | |
| T044 | Verify `regenerate-graph --check` byte-identical after WP09 | WP09 | |
| T045 | Refactor `versioning.py:316` (cc 65) + `base.py:227` (cc 28) | WP10 | [P] |
| T046 | Refactor `agent_profiles/repository.py:365` (cc 36) | WP10 | [P] |
| T047 | Refactor `drg/validator.py:35`, `drg/merge.py:941`, `drg/org_pack_loader.py:746` | WP10 | [P] |
| T048 | Per-helper tests for extracted helpers; verify byte-identical + cc ≤ 15 | WP10 | |
| T049 | Confirm regression-delta gate (NFR-001) + no Sonar-UI triage (NFR-005) in PR body | WP10 | |

---

## WP01 — Census, classification & behavior baseline (foundation)

- **Goal**: Produce the authoritative per-path disposition table, the reusable census gate, and the golden behavior-lock. Sole owner of the management-surface enumeration.
- **Priority**: P1 (foundation — all WPs depend on it)
- **Independent test**: `test_doctrine_census.py` fails if any non-exempt-reached doctrine path lacks a disposition; `regenerate-graph --check` is green on the untouched tree.
- **Subtasks**: T001, T002, T003, T004
- **Dependencies**: none
- **Requirements**: FR-002
- **Prompt**: [tasks/WP01-census-classification-baseline.md](./tasks/WP01-census-classification-baseline.md) (~260 lines)

## WP02 — Doctrine public surface + negative guard

- **Goal**: `doctrine/api.py` (curated `__all__`), wheel-closure pins it, INTERNAL negative test, dead-symbol wiring, CHANGELOG + charter C-007 extension.
- **Priority**: P1
- **Independent test**: importing `doctrine.api` exposes exactly `__all__`; wheel-closure + negative test green.
- **Subtasks**: T005, T006, T007, T008, T009
- **Dependencies**: WP01
- **Requirements**: FR-001, FR-007, FR-008, NFR-004
- **Prompt**: [tasks/WP02-doctrine-public-surface.md](./tasks/WP02-doctrine-public-surface.md) (~300 lines)

## WP03 — Charter facade layer (symbol-level doors)

- **Goal**: Widen `charter.drg`/`charter.mission_steps`; add `charter.missions`/`charter.model_routing`/`charter.assets`; narrow doors for glossary/spdd/pack_paths; grow `_FACADE_TABLE`; PUBLIC symbols re-export from `doctrine.api`.
- **Priority**: P1
- **Independent test**: `test_charter_facades_reexport_doctrine.py` green with new rows; every re-export is symbol-level identity + in `__all__`.
- **Subtasks**: T010, T011, T012, T013, T014, T015, T016
- **Dependencies**: WP01, WP02
- **Requirements**: FR-003, NFR-002
- **Prompt**: [tasks/WP03-charter-facade-layer.md](./tasks/WP03-charter-facade-layer.md) (~420 lines)

## WP04 — Lazy-import ratchet + source-side laundering guard

- **Goal**: Sibling ratchet (parent-tracking descent) closing the lazy reach-through + laundering, only-shrink baseline. Lands red-first before migration.
- **Priority**: P1
- **Independent test**: a throwaway lazy `from doctrine.x import y` in a runtime function turns the suite red; a `TYPE_CHECKING` one does not.
- **Subtasks**: T017, T018, T019, T020
- **Dependencies**: WP01
- **Requirements**: FR-006, NFR-006
- **Prompt**: [tasks/WP04-lazy-import-ratchet.md](./tasks/WP04-lazy-import-ratchet.md) (~280 lines)

## WP05 — Conduit closure (atomic) + sole-door fix + service/org-pack CLI migration

- **Goal**: Close the `specify_cli/doctrine/config` re-export conduit atomically (de-export + repoint consumers); migrate the drg/org-pack/service CLI cluster; fix the 5 raw `DoctrineService` sites preserving filtering semantics.
- **Priority**: P1
- **Independent test**: ratchet baseline shrinks for these files; sole-door test green; `resolve_org_roots` reaches runtime only via `charter.drg`.
- **Subtasks**: T021, T022, T023, T024, T025, T026, T027
- **Dependencies**: WP03, WP04
- **Requirements**: FR-004, FR-005, C-005
- **Prompt**: [tasks/WP05-conduit-closure-sole-door.md](./tasks/WP05-conduit-closure-sole-door.md) (~360 lines)

## WP06 — Runtime migration: profiles + routing cluster

- **Goal**: Migrate the agent-profile / model-routing / drg-model consumers onto `charter.profiles`/`charter.model_routing`/`charter.drg`, converting whole-module routing access to symbol imports.
- **Priority**: P2
- **Independent test**: ratchet baseline shrinks for these files; behavior unchanged.
- **Subtasks**: T028, T029, T030, T031, T032
- **Dependencies**: WP03, WP04
- **Requirements**: FR-004
- **Prompt**: [tasks/WP06-runtime-migration-profiles-routing.md](./tasks/WP06-runtime-migration-profiles-routing.md) (~300 lines)

## WP07 — Runtime migration: missions + skills + bundles cluster

- **Goal**: Migrate mission-repository / mission-type / template-catalog / spdd / pack_paths consumers onto `charter.missions` and the narrow doors.
- **Priority**: P2
- **Independent test**: ratchet baseline shrinks for these files; behavior unchanged.
- **Subtasks**: T033, T034, T035, T036, T037, T038
- **Dependencies**: WP03, WP04
- **Requirements**: FR-004
- **Prompt**: [tasks/WP07-runtime-migration-missions-bundles.md](./tasks/WP07-runtime-migration-missions-bundles.md) (~340 lines)

## WP08 — Campsite Sonar (duplicate literals + suppression)

- **Goal**: Hoist duplicate DRG-URN literals in `hand_authored_overlay.py`; fix the malformed suppression at `artifact_kinds.py:118`. Behavior-preserving.
- **Priority**: P3
- **Independent test**: `S1192` on the overlay = 0; `S7632` resolved; `regenerate-graph --check` byte-identical.
- **Subtasks**: T039, T040, T041
- **Dependencies**: WP01
- **Requirements**: FR-009, FR-011
- **Prompt**: [tasks/WP08-campsite-sonar.md](./tasks/WP08-campsite-sonar.md) (~200 lines)

## WP09 — Complexity refactor: extractor.py (isolated)

- **Goal**: Reduce `extractor.py` S3776 functions (cc 183 at :545, cc 16 at :933) to ≤ 15 with tested helpers. Behavior-locked by the golden.
- **Priority**: P3 (last, independently revertable)
- **Independent test**: every touched function ≤ 15; `regenerate-graph --check` byte-identical; helpers have focused tests.
- **Subtasks**: T042, T043, T044
- **Dependencies**: WP01
- **Requirements**: FR-010, NFR-003
- **Prompt**: [tasks/WP09-complexity-extractor.md](./tasks/WP09-complexity-extractor.md) (~240 lines)

## WP10 — Complexity refactor: remaining S3776 + regression closeout

- **Goal**: Reduce the remaining 6 S3776 doctrine functions to ≤ 15; per-helper tests; confirm regression-delta + no-triage in the PR body.
- **Priority**: P3 (last, independently revertable)
- **Independent test**: every touched function ≤ 15; `regenerate-graph --check` byte-identical; regression-delta gate documented.
- **Subtasks**: T045, T046, T047, T048, T049
- **Dependencies**: WP01
- **Requirements**: FR-010, NFR-001, NFR-003, NFR-005
- **Prompt**: [tasks/WP10-complexity-remaining-closeout.md](./tasks/WP10-complexity-remaining-closeout.md) (~260 lines)

---

## Dependency graph & lanes

```
WP01 ─┬─ WP02 ── WP03 ─┬─ WP05
      │                ├─ WP06
      │                └─ WP07
      ├─ WP04 ─────────┘ (ratchet lands red-first; WP05–07 shrink its baseline)
      ├─ WP08
      ├─ WP09
      └─ WP10
```

**MVP**: WP01 → WP02 → WP03 → WP04 delivers the *declared and frozen* boundary (surface + facades +
only-shrink ratchet) — the actual precondition value for #3101. Honest caveat: the ratchet prevents
**new** reach-through, but existing reach-through **and** the `config.py` laundering conduit remain
open until WP05–07, and the facades have no runtime consumers until then. The MVP is "boundary
declared + anti-regrowth frozen," not "boundary clean" (SC-001 completes across WP05–07).

**FR-010 sequencing note**: the spec's FR table lists FR-010 as depending on FR-001..FR-009. Plan
IC-09 deliberately relaxed this to WP01-only (golden baseline) so the highest-risk refactor stays
independently revertable and can run in parallel; the "last-sequenced" intent is honored by priority
(P3) + risk-isolation, not a hard graph edge. This override is intentional, not an unmet dependency.

**Parallelization**: after WP01, {WP04, WP08, WP09, WP10} run parallel with the WP02→WP03 chain;
WP05/06/07 parallelize after WP03+WP04.
