# Tasks: Local Custom Mission Loader

**Mission**: `local-custom-mission-loader-01KQ2VNJ`
**Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-25T17:54:43Z
**Branch contract**: planning_base=`main`, merge_target=`main`, branch_matches_target=true.

---

## Subtask Index

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Add `agent_profile` field with kebab alias to `PromptStep` | WP01 |  | [D] |
| T002 | Add `contract_ref` field to `PromptStep` | WP01 |  | [D] |
| T003 | Configure `populate_by_name=True` on `PromptStep.model_config` | WP01 |  | [D] |
| T004 | Schema parse / alias / round-trip unit tests | WP01 | [D] |
| T005 | Create `mission_loader/__init__.py` stub package | WP02 |  | [D] |
| T006 | Create `mission_loader/errors.py` (closed enums + Pydantic models) | WP02 |  | [D] |
| T007 | Create `mission_loader/retrospective.py` (`has_retrospective_marker`) | WP02 | [D] |
| T008 | Add `RESERVED_BUILTIN_KEYS` constant + `is_reserved_key()` to `_internal_runtime/discovery.py` | WP02 |  | [D] |
| T009 | Create `mission_loader/validator.py` with `validate_custom_mission()` | WP02 |  | [D] |
| T010 | Unit tests: retrospective marker presence / absence | WP02 | [D] |
| T011 | Unit tests: every closed error code reachable + envelope shape | WP02 | [D] |
| T012 | Unit tests: precedence / shadow rules / reserved-key rejection | WP02 | [D] |
| T013 | Create `mission_loader/contract_synthesis.py` (`synthesize_contracts`) | WP03 |  | [D] |
| T014 | Create `mission_loader/registry.py` (in-process registry shadow) | WP03 |  | [D] |
| T015 | Hook contract registration into `MissionStepContractRepository` lookup path | WP03 |  | [D] |
| T016 | Unit tests: contract synthesis output shape (FR-008) | WP03 | [D] |
| T017 | Unit tests: registry shadow precedence + lifetime | WP03 | [D] |
| T018 | Extend `_should_dispatch_via_composition` (read `agent_profile`) | WP04 |  | [D] |
| T019 | Add `_resolve_step_agent_profile()` helper in `runtime_bridge.py` | WP04 |  | [D] |
| T020 | Extend `_dispatch_via_composition` caller to thread `profile_hint` | WP04 |  | [D] |
| T021 | Unit tests: gate widening true/false matrix | WP04 | [D] |
| T022 | Extend `test_runtime_bridge_composition.py` (built-ins unchanged + custom dispatches) | WP04 |  | [D] |
| T023 | Create `mission_loader/command.py` (functional core) | WP05 |  | [D] |
| T024 | Register `@app.command("run")` in `cli/commands/mission_type.py` | WP05 |  | [D] |
| T025 | Implement validation → registry-register → run-start orchestration | WP05 |  | [D] |
| T026 | Implement `--json` envelope rendering (success + error) | WP05 |  | [D] |
| T027 | Implement human (`rich.panel.Panel`) rendering | WP05 |  | [D] |
| T028 | Unit tests: command happy / sad path against the validator stub | WP05 | [D] |
| T029 | Author `tests/fixtures/missions/erp-integration/mission.yaml` | WP06 |  |
| T030 | Integration test: `spec-kitty mission run` happy path with `--json` | WP06 |  |
| T031 | Integration test: validation error envelope shape locked | WP06 |  |
| T032 | Integration test: ERP runtime walk through composition + decision_required | WP06 |  |
| T033 | Integration test: paired invocation records record contract action | WP06 |  |
| T034 | Integration test: built-in mission walk unchanged | WP06 | [P] |
| T035 | Perf test: loader p95 < 250 ms on ERP fixture | WP07 |  |
| T036 | Perf test: ERP fixture full walk < 10 s | WP07 |  |
| T037 | Configure `pytest --cov` fail-under 90 on `mission_loader/` package | WP07 |  |
| T038 | Update CI quality workflow to run `mypy --strict` on new modules | WP07 | [P] |
| T039 | Update `docs/reference/missions.md`: author guide for custom missions | WP08 |  |
| T040 | Update `docs/reference/missions.md`: closed error code table | WP08 |  |
| T041 | Update `docs/reference/missions.md`: ERP example walkthrough | WP08 |  |

The Subtask Index is a reference table only. Per-WP progress is tracked via the checkbox lists below.

---

## Phase 1 — Schema (foundational)

### WP01 — PromptStep Schema Additions

**Goal**: Land the schema fields that downstream WPs read. Smallest possible blast radius; no behavior change to built-ins.

**Priority**: P0 (blocks WP02 + WP04).

**Independent test**: `pytest tests/next/test_prompt_step_schema_extensions.py -q` passes; `mypy --strict src/specify_cli/next/_internal_runtime/schema.py` clean; existing test suite stays green.

**Subtasks**:

- [x] T001 Add `agent_profile: str | None = None` to `PromptStep` with field alias `agent-profile` (WP01)
- [x] T002 Add `contract_ref: str | None = None` to `PromptStep` (WP01)
- [x] T003 Configure `populate_by_name=True` on `PromptStep.model_config` so kebab and snake both parse (WP01)
- [x] T004 Add unit tests: snake-case parse, kebab-case parse, both-set round-trip, default `None`, mypy strict (WP01)

**Implementation sketch**: Pydantic v2 supports per-field alias via `Field(alias="agent-profile")`. Use `model_config = ConfigDict(frozen=True, populate_by_name=True)` so `PromptStep(agent_profile="x")` and `PromptStep.model_validate({"agent-profile": "x"})` both succeed. Default `None` so existing built-in templates parse unchanged.

**Parallel opportunities**: T004 can be drafted in parallel with T001-T003 by another agent.

**Dependencies**: none.

**Risks**: forgetting `populate_by_name=True` would force YAML to use kebab-only (or snake-only). Mitigation: T004 explicitly tests both spellings.

**Prompt**: [`tasks/WP01-prompt-step-schema-additions.md`](./tasks/WP01-prompt-step-schema-additions.md)

---

## Phase 2 — Loader core (parallelizable after WP01)

### WP02 — Loader Errors, Validator, and Reserved-Key Discovery Extension

**Goal**: Stand up the `mission_loader/` package's error model, retrospective check, validator, and the discovery-side reserved-key constant. Test-first for every stable error code (NFR-002).

**Priority**: P0 (blocks WP05).

**Independent test**: `pytest tests/unit/mission_loader/ -q` passes with ≥ 90% line coverage on the new modules; `mypy --strict src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py` clean.

**Subtasks**:

- [x] T005 Create `src/specify_cli/mission_loader/__init__.py` exporting public API (WP02)
- [x] T006 Create `errors.py` with `LoaderErrorCode`, `LoaderWarningCode` (StrEnum), `LoaderError`, `LoaderWarning`, and `ValidationReport` Pydantic models (WP02)
- [x] T007 Create `retrospective.py` with `has_retrospective_marker(template) -> bool` (WP02)
- [x] T008 Add `RESERVED_BUILTIN_KEYS = frozenset({"software-dev","research","documentation","plan"})` and `is_reserved_key(key)` helper to `_internal_runtime/discovery.py` (WP02)
- [x] T009 Create `validator.py` with `validate_custom_mission(mission_key, context) -> ValidationReport` implementing the flow in `data-model.md` §Validation flow (WP02)
- [x] T010 Unit tests: marker present / absent / wrong id / steps empty (WP02)
- [x] T011 Parametrized unit tests: every closed error code in `contracts/validation-errors.md` reachable; envelope shape locked (WP02)
- [x] T012 Unit tests: precedence (env > project_override > project_legacy > user_global > project_config > builtin); shadow warnings for non-built-in keys; reserved-key rejection (WP02)

**Implementation sketch**: `validate_custom_mission()` returns `ValidationReport(template, discovered, errors=[...], warnings=[...])`. Catches every YAML-load `ValidationError` and converts to `LoaderError(MISSION_YAML_MALFORMED)` (with `MISSION_REQUIRED_FIELD_MISSING` as a sub-case when known fields are missing). Re-uses `discovery.discover_missions_with_warnings()` and `load_mission_template_file()` — does NOT add a parallel loader (FR-003).

**Parallel opportunities**: T010 / T011 / T012 are independent test files and can be drafted concurrently.

**Dependencies**: WP01.

**Risks**: `MissionTemplate` already validates required fields strictly, so `MISSION_REQUIRED_FIELD_MISSING` may need a try/except wrapping the `model_validate` call to extract missing-field details. Mitigation: T011 covers this branch explicitly.

**Prompt**: [`tasks/WP02-loader-errors-validator-and-reserved-key.md`](./tasks/WP02-loader-errors-validator-and-reserved-key.md)

---

### WP03 — Contract Synthesis + Runtime Registry Shadow

**Goal**: At load time, synthesize a `MissionStepContract` per composed step in a custom mission template, and provide a per-process registry shadow so `StepContractExecutor` can look them up alongside on-disk contracts.

**Priority**: P0 (blocks WP05).

**Independent test**: `pytest tests/unit/mission_loader/test_contract_synthesis.py tests/unit/mission_loader/test_registry.py -q` passes with ≥ 90% coverage on new modules.

**Subtasks**:

- [x] T013 Create `mission_loader/contract_synthesis.py` with `synthesize_contracts(template) -> list[MissionStepContract]` (WP03)
- [x] T014 Create `mission_loader/registry.py` with `RuntimeContractRegistry` class wrapping `MissionStepContractRepository` (WP03)
- [x] T015 Wire registry shadow into the lookup path used by `StepContractExecutor` (e.g., expose a context-managed `with registered_runtime_contracts(template):` helper) (WP03)
- [x] T016 Unit tests: one contract per composed step; `mission == template.mission.key`; `action == step.id`; profile_hint default; contract_ref short-circuit (WP03)
- [x] T017 Unit tests: registry shadow takes precedence over on-disk; lifetime ends after context exits (WP03)

**Implementation sketch**: `synthesize_contracts()` walks `template.steps`, skipping steps where `requires_inputs` is non-empty (decision-required gates do NOT need contracts) and steps with `contract_ref` set. For each remaining composed step, build `MissionStepContract(id=f"custom:{key}:{step.id}", mission=key, action=step.id, steps=[MissionStep(id=f"{step.id}.execute", title=step.title, ...)])`. `RuntimeContractRegistry` exposes `register(contracts)`, `lookup(id) -> MissionStepContract | None`, and a context manager that auto-deregisters.

**Parallel opportunities**: T016 / T017 are independent test files.

**Dependencies**: WP01 (PromptStep.contract_ref / agent_profile fields).

**Risks**: `StepContractExecutor` uses `MissionStepContractRepository` directly, not a façade. Mitigation: WP03 adds a thin façade that the executor consumes; WP04 adapts `_dispatch_via_composition` to use the façade.

**Prompt**: [`tasks/WP03-contract-synthesis-and-registry.md`](./tasks/WP03-contract-synthesis-and-registry.md)

---

### WP04 — Composition Gate Widening + Profile Hint Plumbing

**Goal**: Widen `_should_dispatch_via_composition` to include any step whose frozen-template entry has `agent_profile` set, and thread that value through `_dispatch_via_composition` as `profile_hint`.

**Priority**: P0 (blocks WP06; built-in dispatch must remain unchanged).

**Independent test**: existing 21-case parametrization in `tests/specify_cli/next/test_runtime_bridge_composition.py` stays green; new tests for the widening matrix pass; `mypy --strict src/specify_cli/next/runtime_bridge.py` clean.

**Subtasks**:

- [x] T018 Extend `_should_dispatch_via_composition(mission, step_id, *, run_dir=None)` to also return True when the frozen template's matching step has non-empty `agent_profile` (WP04)
- [x] T019 Add `_resolve_step_agent_profile(run_dir, step_id) -> str | None` reading the frozen template (WP04)
- [x] T020 In the dispatch caller (around line 1158-1180 in `runtime_bridge.py`), source `profile_hint` from `_resolve_step_agent_profile(run_dir, current_step_id)` (WP04)
- [x] T021 Unit tests for `_should_dispatch_via_composition`: built-in still True; custom with agent_profile True; custom without agent_profile False (WP04)
- [x] T022 Extend `tests/specify_cli/next/test_runtime_bridge_composition.py` with: (a) regression test that built-in software-dev dispatch is byte-identical post-widening; (b) new test for a custom mission's composed step (WP04)

**Implementation sketch**: The widened gate calls `_resolve_step_agent_profile(run_dir, step_id)` only when `mission` is not in `_COMPOSED_ACTIONS_BY_MISSION`. This preserves the existing fast-path for built-ins. `_resolve_step_agent_profile()` calls `_load_frozen_template(run_dir)` (already in scope) and looks up the step.

**Parallel opportunities**: T021 in `tests/next/test_composition_gate_widening.py` can be drafted parallel to T022 in the existing composition test file.

**Dependencies**: WP01 (agent_profile field), WP03 (T022 exercises synthesized contracts during the runtime walk; without WP03 the integration assertion is weaker).

**Risks**: existing tests use mocks that pass `profile_hint=None`. Mitigation: confirm via T022 that the new mock paths still work. Also: do NOT add `_ACTION_PROFILE_DEFAULTS` entries for custom missions (FR-008 explicit).

**Prompt**: [`tasks/WP04-composition-gate-and-profile-hint.md`](./tasks/WP04-composition-gate-and-profile-hint.md)

---

## Phase 3 — Operator surface

### WP05 — `spec-kitty mission run` CLI Subcommand

**Goal**: Wire the `mission run <mission-key> --mission <mission-slug> [--json]` subcommand: validate → register synthesized contracts → start the run → render success / error envelope.

**Priority**: P0 (blocks WP06).

**Independent test**: `pytest tests/integration/test_mission_run_command.py -q` passes (WP05 ships unit-level tests; WP06 ships E2E).

**Subtasks**:

- [x] T023 Create `src/specify_cli/mission_loader/command.py` with `run_custom_mission(...)` functional core, decoupled from Typer (WP05)
- [x] T024 Register `@app.command("run")` in `src/specify_cli/cli/commands/mission_type.py` delegating to `run_custom_mission()` (WP05)
- [x] T025 Implement orchestration: validate → register synthesized contracts via `with` block → call `runtime_bridge.get_or_start_run(mission_slug, repo_root, mission_type=<key>)` → return result envelope (WP05)
- [x] T026 Implement `--json` envelope (success and error shapes per `contracts/mission-run-cli.md`) (WP05)
- [x] T027 Implement human (`rich.panel.Panel`) rendering with the same field set (WP05)
- [x] T028 Unit tests: happy path, validation error → exit 2, infrastructure error → exit 1, JSON envelope shape locked (WP05)

**Implementation sketch**: Functional core signature: `run_custom_mission(mission_key: str, mission_slug: str, repo_root: Path, *, json_output: bool) -> int`. Returns exit code; emits to stdout. Typer wrapper just calls it and `raise typer.Exit(code)`. The `with` block holds the runtime registry shadow active for the duration of the run-start; long-lived steps continue to read it via the executor's repository façade.

**Parallel opportunities**: T028 (unit tests) parallel to T026 / T027 (rendering).

**Dependencies**: WP02, WP03, WP04.

**Risks**: `runtime_bridge.get_or_start_run` may eagerly load the mission template inside `start_mission_run()` before the registry shadow is active. Mitigation: confirm via tracing that the registry context manager wraps the *whole* run-start and remains active for `decide_next_via_runtime` calls; if not, surface the lifetime issue and fix before integration tests run.

**Prompt**: [`tasks/WP05-mission-run-subcommand.md`](./tasks/WP05-mission-run-subcommand.md)

---

## Phase 4 — End-to-end fidelity

### WP06 — ERP Reference Fixture + Integration Tests

**Goal**: Land the canonical ERP custom mission fixture (FR-009) and the integration suite that exercises CLI run + runtime walk + decision_required + paired invocation records.

**Priority**: P0 (verifies FR-001 / FR-006 / FR-007 / FR-009 / FR-013).

**Independent test**: `pytest tests/integration/test_mission_run_command.py tests/integration/test_custom_mission_runtime_walk.py -q` passes.

**Subtasks**:

- [ ] T029 Author `tests/fixtures/missions/erp-integration/mission.yaml` with the seven-step ERP flow per `quickstart.md` (WP06)
- [ ] T030 Integration test: `spec-kitty mission run erp-integration --mission <slug> --json` returns success envelope + creates run dir + does not start invocation execution (FR-001 / FR-013) (WP06)
- [ ] T031 Integration test: missing-retrospective fixture returns `MISSION_RETROSPECTIVE_MISSING` envelope; reserved-key fixture returns `MISSION_KEY_RESERVED` envelope (FR-005 / FR-011) (WP06)
- [ ] T032 Integration test: full ERP runtime walk via `decide_next_via_runtime`: composed step pairs invocation records, decision_required step pauses + resumes (FR-006 / FR-007 / FR-009) (WP06)
- [ ] T033 Integration test: paired invocation records carry `action == <step.id>` (FR-006) (WP06)
- [ ] T034 Integration test: re-run all built-in software-dev composition cases through the new gate; assert byte-identical Decisions to pre-widening (FR-010 regression trap) (WP06)

**Implementation sketch**: Fixtures live under `tests/fixtures/missions/<key>/mission.yaml`. The integration tests use `tmp_path` to assemble a project with the fixture copied to `.kittify/missions/erp-integration/mission.yaml`. The runtime walk test mocks `StepContractExecutor.execute` to return a synthetic `StepContractExecutionResult` with `invocation_ids=("inv-…",)`, then asserts the expected event log entries (mirroring patterns in `test_runtime_bridge_composition.py`).

**Parallel opportunities**: T034 is a regression test that can be drafted independently.

**Dependencies**: WP05 (CLI must exist).

**Risks**: integration tests are slow if not careful. Mitigation: NFR-004 caps the suite at < 10 s; T036 (perf) re-asserts.

**Prompt**: [`tasks/WP06-erp-fixture-and-integration-tests.md`](./tasks/WP06-erp-fixture-and-integration-tests.md)

---

### WP07 — NFR Enforcement (Perf + Coverage CI Guards)

**Goal**: Wire the NFR thresholds into the test / CI surface so regressions break the build.

**Priority**: P1 (deliverable but not blocking integration-level correctness).

**Independent test**: `pytest tests/perf/test_loader_perf.py -q` passes; CI YAML changes lint clean; coverage report shows ≥ 90% on `mission_loader/`.

**Subtasks**:

- [ ] T035 Add `tests/perf/test_loader_perf.py::test_load_p95_under_250ms` (50 iterations, asserts p95 < 250 ms) (WP07)
- [ ] T036 Add `tests/perf/test_loader_perf.py::test_erp_full_walk_under_10s` (single-shot wall-clock assertion) (WP07)
- [ ] T037 Configure `pytest --cov=src/specify_cli/mission_loader --cov-fail-under=90` for the new package; either via `pyproject.toml`, a dedicated invocation in `Makefile`/CI, or `pytest.ini` (WP07)
- [ ] T038 Add `mypy --strict src/specify_cli/mission_loader` to `.github/workflows/ci-quality.yml` so NFR-005 is enforced in CI (WP07)

**Implementation sketch**: For T037, prefer adding a per-package coverage gate to the existing CI quality job rather than to the global pyproject (which may have a lower fail-under). For T038, the existing job likely already runs `mypy --strict src/`; if so, the new modules are covered automatically and T038 reduces to verifying the CI run picks them up.

**Parallel opportunities**: T038 parallel to T035-T037.

**Dependencies**: WP06 (fixture exists).

**Risks**: perf test flakiness on slow CI runners. Mitigation: take p95 of 50 runs; allow a 1.5× slack on CI (env-gated).

**Prompt**: [`tasks/WP07-nfr-enforcement.md`](./tasks/WP07-nfr-enforcement.md)

---

## Phase 5 — Polish

### WP08 — Documentation: Custom Mission Author Guide + Error Code Table

**Goal**: Update `docs/reference/missions.md` with the operator-facing material that complements `quickstart.md`.

**Priority**: P1.

**Independent test**: `markdownlint docs/reference/missions.md` clean; manual read-through against `quickstart.md` confirms parity.

**Subtasks**:

- [ ] T039 Add author guide section (YAML shape, retrospective marker rule, profile rules, requires_inputs) to `docs/reference/missions.md` (WP08)
- [ ] T040 Add closed error code table (mirror of `contracts/validation-errors.md`) (WP08)
- [ ] T041 Add ERP example walkthrough (cross-link `quickstart.md`) (WP08)

**Implementation sketch**: The author guide subsumes parts of `quickstart.md` but lives in `docs/reference/missions.md` because it's reference material, not a how-to. The error code table is the closed-enum source of truth; tooling can grep it.

**Parallel opportunities**: All three subtasks parallel to one another.

**Dependencies**: WP05 (CLI command shape final).

**Risks**: documentation drift if the error codes change. Mitigation: WP08 adds a `MARKER` comment in the table linking back to `contracts/validation-errors.md`; mission-review verifies parity.

**Prompt**: [`tasks/WP08-documentation-author-guide.md`](./tasks/WP08-documentation-author-guide.md)

---

## MVP Scope

**MVP = WP01 + WP02 + WP05** (assuming WP03/WP04/WP06 are needed for a runnable end-to-end). For a *demonstrable validator* without runtime composition, WP01 + WP02 alone produces a working `validate_custom_mission()` that any future caller can use.

The recommended cut for the FIRST shippable slice: **WP01 → WP02 → WP04 → WP03 → WP05 → WP06**. WP07 and WP08 follow.

## Parallelization Highlights

After WP01 lands:
- WP02, WP03, WP04 are pairwise independent (touch disjoint files).

After WP05 lands:
- WP06, WP07, WP08 are pairwise independent.

## Branch Contract Reminder

planning_base=`main`, merge_target=`main`, branch_matches_target=true. Each WP's worktree is computed by `finalize-tasks` from the lane assignment; do NOT pre-create worktrees here.
