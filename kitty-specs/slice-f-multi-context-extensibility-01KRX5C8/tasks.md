# Tasks — Slice F: Multi-Context Extensibility + Strategic Remediations

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Mission ID: `01KRX5C8MQRGG7WJW1YK53DTF5`
> Spec: [spec.md](spec.md) | Plan: [plan.md](plan.md) | Data model: [data-model.md](data-model.md) | ATDD coverage: [atdd-coverage.md](atdd-coverage.md) | Contracts: [contracts/](contracts/)
> Planning / merge target: `feat/org-doctrine-layer`

This file is the master tracking sheet for Slice F's 12 work packages across 4 lanes, decomposed into ~72 numbered subtasks. Every WP follows **ATDD-first discipline (C-011)**: lane-opening WPs land failing-first acceptance tests as their FIRST deliverable; subsequent WPs in the lane turn each test green in dependency order. See `atdd-coverage.md` for the canonical RED→GREEN map and the reviewer's red-on-base / green-on-WP verification protocol.

---

## Lane Plan

| Lane | Theme | WPs | Sequencing | Blocks |
|---|---|---|---|---|
| **A** | Architectural rigor (baselines, dead-code, contracts) | WP01, WP02, WP03 | sequential | Lane C/D cannot START until WP01 merges (RR-1: new modules must not grandfather into Cat-7) |
| **B** | Independent remediations (alias deletion, CLI logging) | WP04, WP05 | sequential within lane; parallel to Lane A | — |
| **C** | Org-DRG (Axis 1 of Slice F) | WP06, WP07, WP08 | sequential | depends on Lane A complete |
| **D** | Monorepo CharterScope (Axis 2) + composable workflows (Axis 3) + closing | WP09, WP10, WP11, WP12 | sequential | depends on Lane A; WP12 depends on every other WP |

Lane A blocks Lane C/D so the burn-down meta-test (FR-110/111) is in place before any new modules ship — preventing Slice F modules from grandfathering themselves into Cat-7.

---

## Work Package Index

- **WP01** — Ratchet baseline + meta-test + Cat-7 per-category refactor + Cat-7 shrinkage 10→7 → [tasks/WP01-ratchet-baseline-and-cat7-shrinkage.md](tasks/WP01-ratchet-baseline-and-cat7-shrinkage.md)
- **WP02** — Symbol-level dead-code gate (`__all__` walk) + `__all__` on src/charter/ + src/kernel/ → [tasks/WP02-symbol-level-dead-code-and-all-convention.md](tasks/WP02-symbol-level-dead-code-and-all-convention.md)
- **WP03** — Contract round-trip CI gate + frontmatter convention + legacy allowlist → [tasks/WP03-contract-round-trip-gate.md](tasks/WP03-contract-round-trip-gate.md)
- **WP04** — DRIFT-1 alias clean deletion + tests migration + ImportError regression → [tasks/WP04-drift1-alias-clean-deletion.md](tasks/WP04-drift1-alias-clean-deletion.md)
- **WP05** — CLI logging bootstrap + Rich-aware handler + subprocess visibility test → [tasks/WP05-cli-logging-bootstrap-and-visibility.md](tasks/WP05-cli-logging-bootstrap-and-visibility.md)
- **WP06** — Org-layer DRG: schema, loader, merge, conflict policy, validator extension → [tasks/WP06-org-drg-loader-merge-and-validator.md](tasks/WP06-org-drg-loader-merge-and-validator.md)
- **WP07** — Org-DRG integration: `build_charter_context` wiring + doctor surface + provenance render → [tasks/WP07-org-drg-context-and-doctor-integration.md](tasks/WP07-org-drg-context-and-doctor-integration.md)
- **WP08** — Org-DRG operator UX: `doctrine org init` + `doctrine org validate` + partial glossary → [tasks/WP08-org-drg-operator-ux-and-glossary.md](tasks/WP08-org-drg-operator-ux-and-glossary.md)
- **WP09** — ADR-8 + `CharterScope` abstraction (single-project default + monorepo seam) → [tasks/WP09-charter-scope-and-adr8.md](tasks/WP09-charter-scope-and-adr8.md)
- **WP10** — Workflow sequence YAML schema + registry + Pydantic model + meta.json.workflow_id → [tasks/WP10-workflow-sequence-schema-and-registry.md](tasks/WP10-workflow-sequence-schema-and-registry.md)
- **WP11** — Workflow runtime integration: `spec-kitty next` consumes workflow + back-compat + unknown-id hard-fail → [tasks/WP11-workflow-runtime-integration.md](tasks/WP11-workflow-runtime-integration.md)
- **WP12** — Closing: cross-axis integration tests + glossary canonical promotion + README + charter amendments + auth-transport ADR + GitHub ticket → [tasks/WP12-closing-cross-axis-and-artifacts.md](tasks/WP12-closing-cross-axis-and-artifacts.md)

---

## Subtask checklist (sequential T001..T072)

### Lane A — Architectural rigor

#### WP01 — Ratchet baseline + meta-test + Cat-7 shrinkage 10→7
- [x] T001 — Land failing-first `tests/architectural/test_ratchet_baselines.py` meta-test scaffold (RED on planning base) (WP01)
- [x] T002 — Create `tests/architectural/_baselines.yaml` with per-test, per-category baselines (FR-110) (WP01)
- [x] T003 — Refactor `tests/architectural/test_no_dead_modules.py::_ALLOWLIST` into per-category frozensets (FR-112) (WP01)
- [x] T004 — DELETE `src/doctrine/templates/repository.py` + its test (Cat-7 shrinkage #1, FR-113) (WP01)
- [x] T005 — DELETE `src/specify_cli/glossary/prompts.py` + its test (Cat-7 shrinkage #2, Q5/DM-01KRX6N0YAFBY7MTJC0CN3D3E4) (WP01)
- [x] T006 — DELETE `src/specify_cli/glossary/rendering.py` + its test (Cat-7 shrinkage #3) (WP01)
- [x] T007 — Set Cat-7 baseline to 7 in `_baselines.yaml`; meta-test turns GREEN; add AC-7 assertion test (WP01)

#### WP02 — Symbol-level dead-code gate + `__all__` convention
- [x] T008 — Land failing-first `tests/architectural/test_no_dead_symbols.py` (walks `__all__`; RED on planning base) (WP02)
- [x] T009 — Land failing-first `tests/architectural/test_all_declarations_required.py` (RED on planning base) (WP02)
- [x] T010 — Add `__all__` declarations to every module under `src/charter/` (FR-121, C-007) (WP02)
- [x] T011 — Add `__all__` declarations to every module under `src/kernel/` (FR-121, C-007) (WP02)
- [x] T012 — Wire any unimported public symbols (from T008 RED) into live callers, OR remove them; both gates GREEN (WP02)

#### WP03 — Contract round-trip CI gate
- [x] T013 — Land failing-first `tests/contract/test_example_round_trip.py` parameterised over tagged codeblocks (RED on planning base) (WP03)
- [x] T014 — Document the `pydantic_model:` + `expect:` frontmatter convention in this mission's `contracts/contract-round-trip-frontmatter.md` reference link AND in the test file's docstring (FR-140) (WP03)
- [x] T015 — Add legacy allowlist to `tests/architectural/_baselines.yaml::test_example_round_trip.legacy_contract_allowlist` (FR-141) (WP03)
- [x] T016 — Sweep `kitty-specs/*/contracts/*.md` and add frontmatter to current valid examples OR allowlist them; round-trip gate GREEN (WP03)

### Lane B — Independent remediations

#### WP04 — DRIFT-1 alias clean deletion
- [x] T017 — Land failing-first `tests/charter/test_alias_deleted_regression.py::test_resolve_governance_import_raises_import_error` (RED on planning base; alias still exists) (WP04)
- [x] T018 — DELETE the `resolve_governance = resolve_project_governance` alias + the "Deprecated alias" docstring at `src/charter/resolver.py:325-326` and `:198` (FR-100, C-003) (WP04)
- [x] T019 — Remove `resolve_governance` from the import block and `__all__` in `src/charter/__init__.py` (FR-101) (WP04)
- [x] T020 — Migrate `tests/charter/test_resolver.py` (and any other site `rg "resolve_governance" tests/` finds) to import `resolve_project_governance` (FR-102) (WP04)
- [x] T021 — Confirm regression test GREEN; add `test_no_test_fixture_still_imports_legacy_alias` coverage for AC-5 (WP04)

#### WP05 — CLI logging bootstrap + Rich-aware handler
- [x] T022 — Land failing-first `tests/integration/test_catalog_miss_cli_visibility.py::test_typoed_styleguide_produces_visible_stderr_warning` (subprocess; RED on planning base) (WP05)
- [x] T023 — Install `logging.captureWarnings(True)` at CLI bootstrap in `src/specify_cli/__main__.py` (FR-130) (WP05)
- [x] T024 — Add Rich-aware `logging.Handler` deferring to existing Rich `Console` instance (no double-init per RR-6); route `WARNING+` through stderr (FR-131) (WP05)
- [x] T025 — Extend `src/charter/_catalog_miss.py` `_LOGGER.warning(extra=...)` payload to carry `kind`, `id`, `cause`, `suggestion`, `mission_id`, `scope` per data-model §8 (WP05)
- [x] T026 — Confirm subprocess visibility test GREEN; layer-rules + 23-fixture regression suite still pass (NFR-001, NFR-003) (WP05)

### Lane C — Org-DRG (depends on Lane A)

#### WP06 — Org-layer DRG: schema, loader, merge, validator extension
- [x] T027 — Land failing-first ATDD suite for Lane C: `test_three_layer_drg_end_to_end.py`, `test_org_pack_missing_path_hard_fails.py`, `test_org_drg_cannot_override_shipped_invariants.py`, `test_charter_lint_lints_all_layers.py` (all RED on planning base) (WP06)
- [x] T028 — Add `OrgDRGFragment` Pydantic v2 model to `src/charter/drg.py` per data-model §2 (FR-001, C-009 8-kind parity) (WP06)
- [x] T029 — Add `OrgDRGConflict` dataclass + `OrgDRGConflictError` exception per data-model §3 (FR-004, FR-005) (WP06)
- [x] T030 — Implement `load_org_drg(repo_root) -> list[OrgDRGFragment]` reading `.kittify/config.yaml::organisation_packs:` (local_path only this mission; NEW-1) (WP06)
- [x] T031 — Implement `merge_three_layers(shipped, org_fragments, project) -> DRGGraph` with shipped-wins-on-conflict + hard-fail on layer rule violation (FR-005) (WP06)
- [x] T032 — Extend `charter lint` to invoke three-layer loader; per-layer named-source findings (FR-003) (WP06)
- [x] T033 — Add `tests/charter/test_org_drg_loader.py` unit coverage for loader + merge + provenance; Lane C ATDD suite GREEN for FR-001/003/004/005 (WP06)

#### WP07 — Org-DRG integration into `build_charter_context` + `doctor doctrine`
- [x] T034 — Land failing-first `tests/integration/test_charter_status_reports_three_layers.py` (RED on planning base) (WP07)
- [x] T035 — Wire `load_org_drg` + `merge_three_layers` into `build_charter_context` via a NEW helper (avoid signature break — WP09 owns scope= parameter via a separate router file) (FR-001 provenance, FR-007) (WP07)
- [x] T036 — Thread per-layer `source:` provenance into the `_render_*` helpers so rendered stanzas carry `built-in | org:<pack> | project` (WP07)
- [x] T037 — Extend `spec-kitty doctor doctrine` to surface org-layer state (configured packs, fetched/missing, collisions) in its Selections section (FR-007) (WP07)
- [x] T038 — Confirm Lane C tests covering `charter status` + provenance GREEN; NFR-001 (23 fixtures) still pass without org pack configured (WP07)

#### WP08 — Org-DRG operator UX + glossary partial
- [x] T039 — Land failing-first `tests/cli/test_doctrine_org_commands.py` for `org init` and `org validate` (RED on planning base) (WP08)
- [x] T040 — Implement `spec-kitty doctrine org init <path>` scaffolding `drg/fragment.yaml`, `org-charter.yaml`, README in `src/specify_cli/cli/commands/doctrine.py` (FR-006) (WP08)
- [x] T041 — Implement `spec-kitty doctrine org validate <path>` invoking the loader + schema validation independently of the rest of the system (FR-006) (WP08)
- [x] T042 — Add Slice F org-tier domain terms (Three-layer DRG, Organisation tier, etc.) to `glossary/contexts/doctrine.md` as `candidate` (promotion to `canonical` happens in WP12 per C-010 / NFR-004) (WP08)
- [x] T043 — Confirm CLI ATDD GREEN; AC-2 satisfied (`doctor doctrine` from WP07 + `org init/validate` here) (WP08)

### Lane D — Monorepo + workflows + closing (depends on Lane A; WP12 depends on all)

#### WP09 — CharterScope abstraction + ADR-8
- [x] T044 — Land failing-first `tests/integration/test_monorepo_charter_scope.py` (both happy path + malformed config) + `tests/charter/test_charter_scope.py` unit suite (RED on planning base) (WP09)
- [x] T045 — Author `architecture/adrs/2026-05-18-1-monorepo-charter-scope.md` (ADR-8) finalising the design per FR-008 / spec §1.2 (WP09)
- [x] T046 — Create `src/charter/scope.py` with `CharterScope` dataclass, `default()` + `resolve()` constructors, `CharterScopeConflict` + `CharterScopeNotFound` exceptions per data-model §4 (FR-009) (WP09)
- [x] T047 — Create `src/charter/scope_router.py` as a thin wrapper invoking `build_charter_context` with a resolved scope — avoids breaking `context.py` signature (architectural carve-out for WP07 ownership of context.py) (FR-010) (WP09)
- [x] T048 — Wire `prompt_builder.build_prompt` to call `CharterScope.resolve` → `scope_router` so single-project repos route via `CharterScope.default(repo_root)` (byte-identical to today, NFR-001) (WP09)
- [x] T049 — Confirm Scenario 2 + AC-3 GREEN; the 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged (NFR-001) (WP09)

#### WP10 — Workflow sequence YAML schema + registry
- [x] T050 — Land failing-first `tests/specify_cli/next/test_workflow_registry.py` (covers `test_unknown_workflow_id_hard_fails_with_available_list` Scenario 3 exception) (RED on planning base) (WP10)
- [x] T051 — Create `src/specify_cli/next/_internal_runtime/workflow_schema.py` with `WorkflowSequence` + `ActionStep` Pydantic v2 models per data-model §5 + §6 (FR-012) (WP10)
- [x] T052 — Create `src/specify_cli/next/_internal_runtime/workflow_registry.py` with `get_workflow(workflow_id) -> WorkflowSequence`; precedence: `src/doctrine/workflows/<id>.workflow.yaml`, then `_fixtures/`, then operator override (WP10)
- [x] T053 — Create `src/doctrine/workflows/software-dev-default.workflow.yaml` declaring the existing six-step sequence — byte-stable to today's hardcoded sequence (FR-014, C-008) (WP10)
- [x] T054 — Create `src/doctrine/workflows/_fixtures/our-team-design-first.workflow.yaml` fixture with extra `design-review` step between `plan` and `tasks` (for WP11 / Scenario 3) (WP10)
- [x] T055 — Confirm registry tests GREEN; unknown-id hard-fails with available-list message (FR-015, no silent fallback) (WP10)

#### WP11 — Workflow runtime integration
- [x] T056 — Land failing-first `tests/integration/test_workflow_sequence_runtime.py::test_non_default_workflow_id_produces_extra_design_review_step` + `test_fixture_mission_with_workflow_id_produces_documented_step_diff` (RED on planning base) (WP11)
- [x] T057 — Land failing-first `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py` (RED on planning base; pins C-008) (WP11)
- [x] T058 — Extend `src/specify_cli/next/_internal_runtime/planner.py` to consume `meta.json::workflow_id`; absent ⇒ `software-dev-default`; unknown ⇒ hard-fail via WP10's registry (FR-013, FR-015) (WP11)
- [x] T059 — Extend `src/specify_cli/next/prompt_builder.py` to look up the workflow once per mission run (cached) and resolve next-action via workflow graph instead of the hardcoded sequence (WP11)
- [x] T060 — Confirm Scenario 3 + AC-4 GREEN; default workflow is byte-stable; pre-Slice-F missions without `workflow_id` produce identical `spec-kitty next` output (NEW-2 permanent default) (WP11)

#### WP12 — Closing: cross-axis tests + glossary + READMEs + charter amendments + auth-transport ADR + GitHub ticket
- [ ] T061 — Author `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` per FR-200 (dead-code finding, audit evidence, DELETE recommendation, deferral rationale per HiC §5a.3, "deleted in commit X" reserved field for Robert) (WP12)
- [ ] T062 — Open GitHub ticket against `Priivacy-ai/spec-kitty` with the same evidence, labelled for Robert's queue; pin ticket URL in WP12 close-out commit message (FR-201, AC-13) (WP12)
- [ ] T063 — Create `tests/architectural/README.md` documenting the 5-axis architectural model (Layer × Surface × Closed-vocabulary × Lifecycle × Dependency) and listing every gate with its axis (FR-300, AC-14) (WP12)
- [ ] T064 — Create or extend `src/specify_cli/upgrade/migrations/README.md` documenting the forward-staged migrations convention (Q7 / FR-301 / AC-15) (WP12)
- [ ] T065 — Promote all 10 Slice F domain-language terms in `glossary/contexts/doctrine.md` from `candidate` to `canonical` (FR-302, C-010, NFR-004, AC-11) (WP12)
- [ ] T066 — Land failing-first `tests/glossary/test_canonical_promotion.py::test_all_slice_f_terms_are_canonical_in_doctrine_context` (RED on planning base, GREEN after T065) (WP12)
- [ ] T067 — Amend `.kittify/charter/charter.md` to add binding burn-down policy (FR-303a / C-004), `__all__` declaration convention (FR-303b / C-007), and ATDD-first discipline note (FR-303c / C-011) per AC-16 (WP12)
- [ ] T068 — Land cross-axis integration test asserting Axis 1 + Axis 2 + Axis 3 interact correctly (org pack present, monorepo scope active, custom workflow selected) (WP12)
- [ ] T069 — Update `atdd-coverage.md` Status column rows to `green` for each landed test; capture RED commit SHA per FR-304 (WP12)
- [ ] T070 — Run full architectural sweep + governance contract regression: `PWHEADLESS=1 pytest tests/architectural/ tests/specify_cli/next/test_wp_prompt_governance_contract.py -v`; capture exit 0 (NFR-001, NFR-003, NFR-005, AC-17) (WP12)
- [ ] T071 — Run `spec-kitty analyze` and confirm verdict READY FOR IMPLEMENTATION with 0 CRITICAL / 0 HIGH (NFR-007, AC-18) (WP12)
- [ ] T072 — Close-out commit aggregates: list of every test now GREEN, every FR satisfied, charter sections amended, ADR landed, GitHub ticket URL (FR-304 commit-message obligation) (WP12)

---

## Subtask Index

| Task | WP | Description |
|---|---|---|
| T001 | WP01 | ATDD: failing-first `test_ratchet_baselines.py` meta-test |
| T002 | WP01 | Create `_baselines.yaml` per-test per-category |
| T003 | WP01 | Refactor `_ALLOWLIST` into per-category frozensets |
| T004 | WP01 | DELETE `doctrine.templates.repository` + test |
| T005 | WP01 | DELETE `specify_cli.glossary.prompts` + test |
| T006 | WP01 | DELETE `specify_cli.glossary.rendering` + test |
| T007 | WP01 | Set Cat-7 baseline to 7; AC-7 assertion |
| T008 | WP02 | ATDD: failing-first `test_no_dead_symbols.py` |
| T009 | WP02 | ATDD: failing-first `test_all_declarations_required.py` |
| T010 | WP02 | `__all__` on `src/charter/**` modules |
| T011 | WP02 | `__all__` on `src/kernel/**` modules |
| T012 | WP02 | Wire/remove unimported symbols; gates GREEN |
| T013 | WP03 | ATDD: failing-first `test_example_round_trip.py` |
| T014 | WP03 | Document frontmatter convention |
| T015 | WP03 | Legacy allowlist in `_baselines.yaml` |
| T016 | WP03 | Sweep existing contracts; gate GREEN |
| T017 | WP04 | ATDD: failing-first alias ImportError regression |
| T018 | WP04 | DELETE alias in `resolver.py` |
| T019 | WP04 | Remove `__init__.py` exports |
| T020 | WP04 | Migrate test fixtures to canonical name |
| T021 | WP04 | AC-5 fixture coverage |
| T022 | WP05 | ATDD: failing-first subprocess catalog-miss test |
| T023 | WP05 | `logging.captureWarnings(True)` bootstrap |
| T024 | WP05 | Rich-aware handler routing |
| T025 | WP05 | Extend `_catalog_miss.py` payload fields |
| T026 | WP05 | Regression sweep clean |
| T027 | WP06 | ATDD: failing-first Lane C suite (4 tests) |
| T028 | WP06 | `OrgDRGFragment` Pydantic model |
| T029 | WP06 | `OrgDRGConflict` + exception |
| T030 | WP06 | `load_org_drg` reading `organisation_packs:` |
| T031 | WP06 | `merge_three_layers` policy |
| T032 | WP06 | `charter lint` three-layer extension |
| T033 | WP06 | Unit coverage; Lane C ATDD GREEN |
| T034 | WP07 | ATDD: failing-first `charter_status_reports_three_layers` |
| T035 | WP07 | Wire org-DRG into `build_charter_context` |
| T036 | WP07 | Per-layer provenance render |
| T037 | WP07 | `doctor doctrine` org section |
| T038 | WP07 | Regression sweep + NFR-001 |
| T039 | WP08 | ATDD: failing-first `test_doctrine_org_commands.py` |
| T040 | WP08 | `doctrine org init` scaffolding |
| T041 | WP08 | `doctrine org validate` |
| T042 | WP08 | Glossary org-tier terms (candidate) |
| T043 | WP08 | AC-2 satisfied |
| T044 | WP09 | ATDD: failing-first monorepo scope tests |
| T045 | WP09 | ADR-8 monorepo-charter-scope |
| T046 | WP09 | `src/charter/scope.py` `CharterScope` |
| T047 | WP09 | `src/charter/scope_router.py` |
| T048 | WP09 | `prompt_builder` integration via router |
| T049 | WP09 | AC-3 + NFR-001 |
| T050 | WP10 | ATDD: failing-first `test_workflow_registry.py` |
| T051 | WP10 | `WorkflowSequence` + `ActionStep` models |
| T052 | WP10 | `workflow_registry.get_workflow` |
| T053 | WP10 | `software-dev-default.workflow.yaml` byte-stable |
| T054 | WP10 | Fixture `our-team-design-first.workflow.yaml` |
| T055 | WP10 | Unknown-id hard-fail GREEN |
| T056 | WP11 | ATDD: failing-first workflow runtime tests |
| T057 | WP11 | ATDD: failing-first byte-stability test |
| T058 | WP11 | `planner.py` consumes `meta.json::workflow_id` |
| T059 | WP11 | `prompt_builder` workflow lookup cache |
| T060 | WP11 | Scenario 3 + AC-4 GREEN |
| T061 | WP12 | Auth-transport ADR (FR-200) |
| T062 | WP12 | GitHub ticket open (FR-201) |
| T063 | WP12 | `tests/architectural/README.md` 5-axis model |
| T064 | WP12 | Migrations README forward-staged convention |
| T065 | WP12 | Promote glossary terms to `canonical` |
| T066 | WP12 | ATDD: `test_canonical_promotion.py` |
| T067 | WP12 | Charter amendments (FR-303 a/b/c) |
| T068 | WP12 | Cross-axis integration test |
| T069 | WP12 | Update atdd-coverage.md status column |
| T070 | WP12 | Full architectural + governance regression GREEN |
| T071 | WP12 | `spec-kitty analyze` READY + 0 CRITICAL / 0 HIGH |
| T072 | WP12 | Close-out commit aggregation |

Total: 72 subtasks across 12 WPs.

---

## Work Packages

### WP01 — Ratchet baseline + meta-test + Cat-7 per-category refactor + Cat-7 shrinkage 10→7

**Lane**: A | **Dependencies**: none
**File**: [tasks/WP01-ratchet-baseline-and-cat7-shrinkage.md](tasks/WP01-ratchet-baseline-and-cat7-shrinkage.md)
**Subtasks**: T001–T007 (7) | **FRs**: FR-110, FR-111, FR-112, FR-113, C-004, C-006

Lays the burn-down foundation Slice F depends on. Lands `tests/architectural/_baselines.yaml` + the meta-test that fails on growth and warns on shrinkage; refactors `_ALLOWLIST` into per-category frozensets; shrinks Cat-7 from 10 → 7 by deleting `doctrine.templates.repository`, `specify_cli.glossary.prompts`, `specify_cli.glossary.rendering`. Blocks Lane C/D start (RR-1).

### WP02 — Symbol-level dead-code gate (`__all__` walk) + `__all__` on src/charter/ + src/kernel/

**Lane**: A | **Dependencies**: WP01
**File**: [tasks/WP02-symbol-level-dead-code-and-all-convention.md](tasks/WP02-symbol-level-dead-code-and-all-convention.md)
**Subtasks**: T008–T012 (5) | **FRs**: FR-120, FR-121, FR-122, C-007

Extends the dead-code architectural ratchet from module-level to symbol-level. Ships `tests/architectural/test_no_dead_symbols.py` + `test_all_declarations_required.py`; adds `__all__` declarations to every module under `src/charter/` and `src/kernel/`.

### WP03 — Contract round-trip CI gate + frontmatter convention + legacy allowlist

**Lane**: A | **Dependencies**: WP01
**File**: [tasks/WP03-contract-round-trip-gate.md](tasks/WP03-contract-round-trip-gate.md)
**Subtasks**: T013–T016 (4) | **FRs**: FR-140, FR-141

Lands `tests/contract/test_example_round_trip.py` that walks every `kitty-specs/<mission>/contracts/*.md`, lifts YAML codeblocks tagged with `pydantic_model:` + `expect:` frontmatter, and asserts round-trip. Slice F is the dogfood mission.

### WP04 — DRIFT-1 alias clean deletion + tests migration + ImportError regression test

**Lane**: B | **Dependencies**: none
**File**: [tasks/WP04-drift1-alias-clean-deletion.md](tasks/WP04-drift1-alias-clean-deletion.md)
**Subtasks**: T017–T021 (5) | **FRs**: FR-100, FR-101, FR-102, FR-103, C-003

DELETES `resolve_governance = resolve_project_governance` alias per HiC §5a.1 (binding). No `DeprecationWarning`, no sunset docstring. Migrates fixtures to canonical `resolve_project_governance`. Lands ImportError regression test.

### WP05 — CLI logging bootstrap + Rich-aware handler + subprocess visibility test

**Lane**: B | **Dependencies**: WP04
**File**: [tasks/WP05-cli-logging-bootstrap-and-visibility.md](tasks/WP05-cli-logging-bootstrap-and-visibility.md)
**Subtasks**: T022–T026 (5) | **FRs**: FR-130, FR-131, FR-132, NFR-006

Installs `logging.captureWarnings(True)` + Rich-aware handler at CLI bootstrap; extends `_catalog_miss.py` payload; lands subprocess-based integration test asserting typo'd charter produces operator-visible stderr.

### WP06 — Org-layer DRG: schema, loader, merge, conflict policy, validator extension

**Lane**: C | **Dependencies**: WP01, WP02, WP03
**File**: [tasks/WP06-org-drg-loader-merge-and-validator.md](tasks/WP06-org-drg-loader-merge-and-validator.md)
**Subtasks**: T027–T033 (7) | **FRs**: FR-001, FR-003, FR-004, FR-005, C-001, C-009

Lands `OrgDRGFragment` + `OrgDRGConflict` + `load_org_drg` + `merge_three_layers`; extends `charter lint` to lint all three layers; hard-fails on missing pack (FR-004) and layer-rule violation (FR-005). Lane-opening WP for Lane C with 4 ATDD tests.

### WP07 — Org-DRG integration: `build_charter_context` wiring + `doctor doctrine` + provenance render

**Lane**: C | **Dependencies**: WP06
**File**: [tasks/WP07-org-drg-context-and-doctor-integration.md](tasks/WP07-org-drg-context-and-doctor-integration.md)
**Subtasks**: T034–T038 (5) | **FRs**: FR-001, FR-002, FR-007, C-001

Wires WP06 plumbing into `build_charter_context` (additive — no signature change; WP09 owns scope= via `scope_router.py`); threads per-layer provenance into renderers; extends `doctor doctrine` org section.

### WP08 — Org-DRG operator UX: `doctrine org init` + `doctrine org validate` + partial glossary

**Lane**: C | **Dependencies**: WP07
**File**: [tasks/WP08-org-drg-operator-ux-and-glossary.md](tasks/WP08-org-drg-operator-ux-and-glossary.md)
**Subtasks**: T039–T043 (5) | **FRs**: FR-006, C-010

Adds `spec-kitty doctrine org init <path>` and `spec-kitty doctrine org validate <path>`; lands the 10 Slice F domain terms in `glossary/contexts/doctrine.md` as `candidate` (WP12 promotes to `canonical` per C-010).

### WP09 — ADR-8 + `CharterScope` abstraction (single-project default + monorepo seam)

**Lane**: D | **Dependencies**: WP01, WP02, WP03
**File**: [tasks/WP09-charter-scope-and-adr8.md](tasks/WP09-charter-scope-and-adr8.md)
**Subtasks**: T044–T049 (6) | **FRs**: FR-008, FR-009, FR-010, FR-011

Lands ADR-8 (monorepo-charter-scope); creates `src/charter/scope.py` (`CharterScope` abstraction) + `src/charter/scope_router.py` (thin wrapper that calls `build_charter_context`, avoiding signature change to WP07-owned `context.py`); wires `prompt_builder` through scope router.

### WP10 — Workflow sequence YAML schema + registry + Pydantic model + `meta.json::workflow_id`

**Lane**: D | **Dependencies**: WP09
**File**: [tasks/WP10-workflow-sequence-schema-and-registry.md](tasks/WP10-workflow-sequence-schema-and-registry.md)
**Subtasks**: T050–T055 (6) | **FRs**: FR-012, FR-013, FR-015, C-008

Ships `WorkflowSequence` + `ActionStep` Pydantic models; `workflow_registry.get_workflow`; `software-dev-default.workflow.yaml` (byte-stable per C-008); fixture `our-team-design-first.workflow.yaml`. Unknown id hard-fails (FR-015 binding).

### WP11 — Workflow runtime integration: `spec-kitty next` consumes workflow + back-compat + unknown-id hard-fail

**Lane**: D | **Dependencies**: WP10
**File**: [tasks/WP11-workflow-runtime-integration.md](tasks/WP11-workflow-runtime-integration.md)
**Subtasks**: T056–T060 (5) | **FRs**: FR-013, FR-014, FR-015, C-008

Wires the registry into `_internal_runtime/planner.py` (consumes `meta.json::workflow_id`); extends `prompt_builder.py` with cached workflow lookup; pre-Slice-F missions default to `software-dev-default` (NEW-2 permanent default).

### WP12 — Closing: cross-axis integration + glossary promotion + READMEs + charter amendments + auth-transport ADR + GitHub ticket

**Lane**: D | **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP11
**File**: [tasks/WP12-closing-cross-axis-and-artifacts.md](tasks/WP12-closing-cross-axis-and-artifacts.md)
**Subtasks**: T061–T072 (12) | **FRs**: FR-200, FR-201, FR-202, FR-300, FR-301, FR-302, FR-303, FR-304, C-005

Authors auth-transport ADR (NO source change per C-005); opens GitHub ticket for Robert's queue; lands 5-axis architectural README + forward-staged migrations README; promotes 10 Slice F glossary terms to `canonical` (AC-11, C-010); amends charter with burn-down policy + `__all__` convention + ATDD-first discipline (FR-303, AC-16); ships cross-axis integration test; runs full architectural sweep + `spec-kitty analyze` (NFR-007, AC-18). Close-out commit aggregates everything per FR-304.
