# Tasks: Org-Tier Doctrine Reaches Its Consumers

**Mission**: `up-org-doctrine-consumers-01M05YAB` · **Branch**: `pr/up-org-doctrine-consumers-01M05YAB`
**Input**: [plan.md](./plan.md) (IC-01…IC-05 Implementation Concern Map, two mandatory lockstep pairs), [spec.md](./spec.md) (FR-001–FR-008 incl. FR-006a, NFR-001–006, C-001–006, SC-001–007).

> Reference rows below are **not** checkboxes. Subtask completion is event-sourced —
> record with `spec-kitty agent tasks mark-status T0xx --status done`. The reduced
> event-log snapshot is the sole authority.

> **Verification Bar (binding on every WP, NFR-001):** every FR fix must be proven by a
> before/after measurement — a count or boolean that changes in a committed regression test —
> never merely "no exception was raised." The DRG probe for FR-002 is **347 → 348 nodes in
> this checkout** (verified live during spec/plan authoring, D-000(4)); the issue's own
> "347 → 350" figure came from a different org pack and is **not reproducible here** — do not
> quote it.

## Lockstep pairs (hard constraints — do not split across packages)

- **Lockstep Pair A** (User Story 3 / IC-02): `src/specify_cli/review/gate_bindings.py:168`
  (`_build_repository`) **must** land in the same work package as
  `src/specify_cli/mission_step_contracts/executor.py:160` (`StepContractExecutor.__init__`).
  Splitting them leaves an org-tier contract's delegations resolving while its `gates:` block
  silently never fires — review gates pass while verifying nothing. **Both in WP02.**
- **Lockstep Pair B** (User Story 2 / IC-03): `src/specify_cli/mission_loader/command.py:237`
  (`_resolve_contract_refs`) **must** land in the same work package as
  `src/runtime/next/runtime_bridge_composition.py:252` (`_resolve_runtime_contract_for_step`).
  Splitting them converts a consistent "always invisible" org-tier `contract_ref` into an
  inconsistent "accepted at runtime, rejected at load-time" (or vice versa). **Both in WP03.**

## Requirement → Work-Package coverage

| FR | WP | FR | WP |
|----|----|----|----|
| FR-001 | WP02 | FR-006 | WP03 |
| FR-002 | WP02 | FR-006a | WP03 |
| FR-003 | WP01 | FR-007 | WP03 |
| FR-004 | WP04 | FR-008 | WP05 |
| FR-005 | WP02 | | |

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Implement `resolve_org_dirs(repo_root, subdir)` in `src/doctrine/drg/org_pack_config.py` + register in `__all__` | WP01 | |
| T002 | Unit tests: no org packs → `[]`; one pack → `[root/subdir]` (C-1 invariant) | WP01 | |
| T003 | Unit tests: two-pack declaration-order precedence (NFR-003) + nonexistent org root filtered before join (NFR-002) | WP01 | |
| T004 | Verify `src/doctrine/*` diff-cover critical-path gate and `test_no_legacy_terminology.py` pass locally (NFR-006) | WP01 | |
| T005 | FR-001: `executor.py` `__init__` threads `org_dirs` via `resolve_org_dirs(repo_root, "mission_step_contracts")` | WP02 | |
| T006 | FR-002: `executor.py` `execute()` threads an inline first-match `org_root` into `load_validated_graph` | WP02 | |
| T007 | FR-005: `gate_bindings.py` `_build_repository` threads the **same** `org_dirs` helper — lockstep mirror of T005 | WP02 | |
| T008 | Red-first regression tests for FR-001/FR-002 in `test_executor.py` (SC-001 DRG count delta 347→348, SC-002 `None`→contract) | WP02 | |
| T009 | Activation-interaction test in `test_executor_activation.py` proving C-001 (activation filtering unchanged) | WP02 | |
| T010 | Shared-fixture FR-005 test in `tests/review/test_gate_bindings.py` (SC-003, gate-bindings third) | WP02 | |
| T011 | FR-006: `runtime_bridge_composition.py` `_resolve_runtime_contract_for_step` threads `org_dirs` | WP03 | |
| T012 | FR-006a: `mission_loader/command.py` `_resolve_contract_refs` threads the **same** `org_dirs` helper — lockstep mirror of T011 | WP03 | |
| T013 | Shared-fixture SC-003 test (FR-006) in `tests/runtime/test_bridge_composition.py` | WP03 | |
| T014 | Shared-fixture SC-003 test (FR-006a) in `tests/unit/mission_loader/test_command.py` + identical-failure-when-org-pack-absent test (User Story 2 AS3) | WP03 | |
| T015 | FR-007: `_dispatch_via_composition` logs one WARNING per step with 1+ unresolved delegation candidates | WP03 | |
| T016 | FR-007 `caplog` positive/negative test (SC-004) in `tests/runtime/test_bridge_composition.py` | WP03 | |
| T017 | FR-004: `_mission_type_profile_repository` threads `org_dirs` via `resolve_org_dirs(repo_root, "mission_types")` into `MissionTypeProfileRepository.for_project` | WP04 | |
| T018 | Regression test: org-tier `governance-profile.yaml` override reflected in `resolve_mission_type_context(...).governance_text` | WP04 | |
| T019 | Regression guard: `action_grain.py:220`'s deliberately built-in-only call site stays unchanged (D-004 boundary) | WP04 | |
| T020 | Verify `src/charter/*` diff-cover ≥90% and architectural sole-door gates green locally (NFR-005) | WP04 | |
| T021 | Implement `resolve_org_expected_artifacts(org_roots, mission_type)` in new `src/charter/activation/org_expected_artifacts.py` per contract C-4 | WP05 | |
| T022 | `_resolve_expected_artifacts_slot` calls the new helper first, falls back to built-in-only when `None` | WP05 | |
| T023 | `ManifestRegistry.load_manifest` cache-key fix: add `repo_root: Path \| None = None`, cache key becomes `(mission_type, tuple(sorted org roots))` | WP05 | |
| T024 | `ManifestRegistry.load_manifest` calls `resolve_org_expected_artifacts` when `repo_root` is given, preserving byte-identical no-override behavior | WP05 | |
| T025 | Unit tests for `resolve_org_expected_artifacts` (no override→`None`, one root, later-org-root-wins precedence, no-built-in-baseline custom type) | WP05 | |
| T026 | Integration tests: `_resolve_expected_artifacts_slot` org override (SC-005 count/content delta) + whole-file-precedence test | WP05 | |
| T027 | Integration tests: `ManifestRegistry.load_manifest` org override (SC-005) + cache-key regression (two `repo_root`s don't shadow each other) + byte-identical Given #2 test | WP05 | |

---

## Work Packages

### WP01 — Shared `org_dirs` resolution helper (IC-01) · FR-003
**Prompt**: [tasks/WP01-shared-org-dirs-helper.md](./tasks/WP01-shared-org-dirs-helper.md)
**Goal**: One function resolves the existing-path-filtered, declaration-ordered `org_dirs` list for a caller-supplied subdirectory name, so FR-001/FR-004/FR-005/FR-006/FR-006a cannot independently drift the way sites 3 and 6 already had before this mission.
**Priority**: High (foundation). **Independent test**: `resolve_org_dirs(repo_root, "mission_step_contracts")` returns `[]` with no org packs configured, one path with one pack, and preserves declared order with two.
**Subtasks**: T001–T004. **Depends on**: none — must land before WP02/WP03/WP04 (they import it), but is itself inert until they do. **Risk**: low; the one design decision is existence-filtering at the org-root level, not the joined-subdirectory level. **~150–200 lines.**

### WP02 — Executor org-tier threading + gate-binding lockstep [LOCKSTEP PAIR A] (IC-02) · FR-001, FR-002, FR-005
**Prompt**: [tasks/WP02-executor-gate-binding-lockstep.md](./tasks/WP02-executor-gate-binding-lockstep.md)
**Goal**: `StepContractExecutor` gains org-tier repository construction (FR-001) and org-tier DRG resolution (FR-002); `gate_bindings._build_repository` (FR-005) moves in the **same package** because splitting it from the executor leaves review gates silently inert (User Story 3).
**Priority**: High. **Independent test**: an org-only step contract resolves via `StepContractExecutor.execute`, its delegation resolves against the org pack's own DRG node, and `load_gate_bindings` returns that contract's `gates` for the same fixture.
**Subtasks**: T005–T010. **Depends on**: WP01. **Risk**: FR-001/FR-002 are forced into the same file (`executor.py`) regardless of the lockstep rule. Neither `executor.py` nor `gate_bindings.py` sits in the enforced diff-cover critical-path list — this WP's real backstop is the red-first regression tests (NFR-001), not a coverage gate. **~350–430 lines.**

### WP03 — Runtime dispatch / mission-load lockstep + delegation surfacing [LOCKSTEP PAIR B] (IC-03) · FR-006, FR-006a, FR-007
**Prompt**: [tasks/WP03-runtime-dispatch-mission-load-lockstep.md](./tasks/WP03-runtime-dispatch-mission-load-lockstep.md)
**Goal**: `_resolve_runtime_contract_for_step` (runtime dispatch) and `_resolve_contract_refs` (mission-load validation) resolve an org-tier `contract_ref` identically — splitting them is explicitly worse than not fixing either (User Story 2). FR-007 (surface unresolved delegation candidates as a WARNING) is folded in because its edit site shares a file with FR-006.
**Priority**: High. **Independent test**: a custom mission template step with an org-tier `contract_ref` validates at load time and resolves at dispatch time against the same fixture; both fail identically when the org pack is absent.
**Subtasks**: T011–T016. **Depends on**: WP01. **Risk**: `runtime_bridge_composition.py` (FR-006) is critical-path (enforced diff-cover); `mission_loader/command.py` (FR-006a) has its own dedicated `--cov-fail-under=90` job (NFR-004). **~380–460 lines.**

### WP04 — Governance-profile org-tier threading (IC-04) · FR-004
**Prompt**: [tasks/WP04-governance-profile-org-tier.md](./tasks/WP04-governance-profile-org-tier.md)
**Goal**: `_resolve_governance_slot` → `_mission_type_profile_repository` → `MissionTypeProfileRepository.for_project` threads `org_dirs` so an org-tier `governance-profile.yaml` override is not silently invisible in every mission-type context resolution (it runs eagerly).
**Priority**: High. **Independent test**: `resolve_mission_type_context(...).governance_text` reflects an org-pack override instead of the built-in baseline.
**Subtasks**: T017–T020. **Depends on**: WP01. **Risk**: low in isolation; the only material risk is the file collision with WP05 on `mission_type_profiles.py`. `src/charter/*` is critical-path (enforced diff-cover). **~150–200 lines.**

### WP05 — Org-tier `expected-artifacts.yaml` override (IC-05) · FR-008
**Prompt**: [tasks/WP05-expected-artifacts-org-tier.md](./tasks/WP05-expected-artifacts-org-tier.md)
**Goal**: `MissionTemplateRepository`/`ManifestRegistry` have no tiering mechanism today — this is net-new surface. An org pack can ship `<org_root>/<mission_type>/expected-artifacts.yaml` that fully replaces (not merges with) the built-in manifest for that mission type. Includes the self-identified `ManifestRegistry` cache-key fix (see prompt for full rationale).
**Priority**: Medium. **Independent test**: `ManifestRegistry.load_manifest("software-dev")`'s `required_always` count/content changes when an org override is added to the fixture, in the same process, before/after.
**Subtasks**: T021–T027. **Depends on**: **WP04 — file-collision only, not functional.** Both WPs edit `src/charter/activation/mission_type_profiles.py` (and its test module); this dependency exists purely so `owned_files` stays non-overlapping for two *concurrent* packages (the finalizer exempts dependency-ordered pairs from the overlap check). Do not "optimise" WP04/WP05 into parallel execution. **Risk**: `src/charter/activation/org_expected_artifacts.py` and `mission_type_profiles.py` are critical-path; `specify_cli/dossier/manifest.py` is not — same red-first-tests-are-the-real-backstop caveat as WP02. **~500–620 lines** (largest package; see prompt's Sizing note).
