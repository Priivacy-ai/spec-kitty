# Tasks — Documentation Mission Composition Rewrite

**Mission ID**: `01KQ5M1Y190VANF39KMBWZP6SD`
**Mission slug**: `documentation-mission-composition-rewrite-01KQ5M1Y`
**Target branch**: `main`
**Total subtasks**: 30 across 7 work packages
**Reference plan**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

The plan suggested 8 work packages; this tasks.md consolidates them into 7 because the plan's WP05 (dispatch wiring) and WP06 (guard branch) both edit `src/specify_cli/next/runtime_bridge.py`. Merging them into a single WP05 prevents ownership overlap and lets the runtime-bridge change ship atomically.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Author `src/specify_cli/missions/documentation/mission-runtime.yaml` (mission.key=documentation, 6 composed steps + accept) | WP01 | [P] | [D] |
| T002 | Author `src/doctrine/missions/documentation/mission-runtime.yaml` (byte-for-byte mirror) | WP01 | [D] |
| T003 | Author `tests/specify_cli/test_documentation_template_resolution.py` proving sidecar wins over legacy `mission.yaml` | WP01 |  | [D] |
| T004 | Author `documentation-discover.step-contract.yaml` | WP02 | [P] |
| T005 | Author `documentation-audit.step-contract.yaml` | WP02 | [P] |
| T006 | Author `documentation-design.step-contract.yaml` | WP02 | [P] |
| T007 | Author `documentation-generate.step-contract.yaml` | WP02 | [P] |
| T008 | Author `documentation-validate.step-contract.yaml` | WP02 | [P] |
| T009 | Author `documentation-publish.step-contract.yaml` | WP02 | [P] |
| T010 | Author `tests/specify_cli/mission_step_contracts/test_documentation_composition.py` (parametrized over all 6 contracts; profile-default mapping; no `expected_artifacts` key check) | WP02 |  |
| T011 | Author `discover/{index.yaml,guidelines.md}` action bundle | WP03 | [P] |
| T012 | Author `audit/{index.yaml,guidelines.md}` | WP03 | [P] |
| T013 | Author `design/{index.yaml,guidelines.md}` | WP03 | [P] |
| T014 | Author `generate/{index.yaml,guidelines.md}` | WP03 | [P] |
| T015 | Author `validate/{index.yaml,guidelines.md}` | WP03 | [P] |
| T016 | Author `publish/{index.yaml,guidelines.md}` | WP03 | [P] |
| T017 | Add 6 documentation action nodes to `src/doctrine/graph.yaml` | WP04 |  |
| T018 | Add 22 scope edges from documentation action URNs to existing directive/tactic URNs | WP04 |  |
| T019 | Author `tests/specify_cli/test_documentation_drg_nodes.py` (DRG node + resolve_context non-empty + bundle↔edges consistency + NFR-007 latency) | WP04 |  |
| T020 | Add `"documentation"` entry to `_COMPOSED_ACTIONS_BY_MISSION` | WP05 |  |
| T021 | Add 6 entries to `_ACTION_PROFILE_DEFAULTS` in `src/specify_cli/mission_step_contracts/executor.py` | WP05 |  |
| T022 | Add `_has_generated_docs(feature_dir)` helper + documentation branch in `_check_composed_action_guard()` (with fail-closed default for unknown actions) | WP05 |  |
| T023 | Author `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` (dispatch entry + per-action guard cases + unknown-action fail-closed + missing-artifact failure messages) | WP05 |  |
| T024 | Author scaffolding `_init_min_repo` + `_scaffold_documentation_feature` + `isolated_repo` fixture in `tests/integration/test_documentation_runtime_walk.py`. Include C-007 docstring at top. | WP06 |  |
| T025 | Author happy-path tests: `test_get_or_start_run_succeeds_for_documentation`, `test_documentation_template_resolves_runtime_sidecar`, `test_composition_advances_one_documentation_step`, `test_paired_invocation_lifecycle_is_recorded` | WP06 |  |
| T026 | Author guard-failure tests: `test_missing_artifact_blocks_with_structured_failure`, `test_unknown_documentation_action_fails_closed` | WP06 |  |
| T027 | Author `CHANGELOG.md` entry for #502 documentation mission composition | WP07 |  |
| T028 | Run full regression sweep: `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, `tests/specify_cli/next/test_runtime_bridge_research_composition.py`, `tests/integration/test_research_runtime_walk.py`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/integration/test_mission_run_command.py` — record pass/fail evidence | WP07 |  |
| T029 | Run `mypy --strict` and `ruff check` on changed files; record zero-new-findings evidence | WP07 |  |
| T030 | Verify dogfood smoke (quickstart.md sequence) executes end-to-end from a temp repo using `uv --project`; record JSON outputs as mission-review evidence | WP07 |  |

`[P]` = parallel-safe within the WP (different files, no shared state).

---

## WP01 — Runtime Sidecar Templates

**Goal**: introduce `mission-runtime.yaml` for documentation in both `src/specify_cli/missions/documentation/` and `src/doctrine/missions/documentation/`, with `mission.key: documentation` so the loader at `runtime_bridge.py:1056-1073` resolves it ahead of the legacy `mission.yaml`.
**Priority**: P0 (blocks everything else; runnability gate).
**Independent test**: a unit test that `_resolve_runtime_template_in_root(...)` returns a path basename `mission-runtime.yaml` for `mission_type='documentation'`.
**Dependencies**: none.
**Estimated prompt size**: ~280 lines.

**Included subtasks**:

- [x] T001 Author `src/specify_cli/missions/documentation/mission-runtime.yaml` with `mission.key=documentation`, 6 composed steps + `accept` per data-model.md (WP01)
- [x] T002 Author `src/doctrine/missions/documentation/mission-runtime.yaml` as a byte-for-byte mirror (WP01)
- [x] T003 Author `tests/specify_cli/test_documentation_template_resolution.py` proving the sidecar wins over `mission.yaml` (WP01)

**Implementation sketch**: copy research's `mission-runtime.yaml` shape verbatim, swap action verbs and prompt_template names, change `mission.key` to `documentation`. Mirror to doctrine side. Test calls `_resolve_runtime_template_in_root(<package_root>, "documentation")` and asserts the resolved path basename.

**Risks**: schema may reject `mission.key=documentation` if a Pydantic literal validator restricts allowed keys. Mitigation — the test catches it at WP01 implementation time, before WPs that depend on it ship.

---

## WP02 — Shipped Step Contracts

**Goal**: ship 6 step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml`, plus a parametrized loading test.
**Priority**: P0.
**Independent test**: parametrized test over all 6 contracts proves they load via the existing contract loader, declare `mission: documentation` and `action: <verb>`, and have no `expected_artifacts` field.
**Dependencies**: none.
**Estimated prompt size**: ~340 lines.

**Included subtasks**:

- [ ] T004 Author `documentation-discover.step-contract.yaml` per [contracts/step-contracts.md](./contracts/step-contracts.md) (WP02)
- [ ] T005 Author `documentation-audit.step-contract.yaml` (WP02)
- [ ] T006 Author `documentation-design.step-contract.yaml` (WP02)
- [ ] T007 Author `documentation-generate.step-contract.yaml` (WP02)
- [ ] T008 Author `documentation-validate.step-contract.yaml` (WP02)
- [ ] T009 Author `documentation-publish.step-contract.yaml` (WP02)
- [ ] T010 Author `tests/specify_cli/mission_step_contracts/test_documentation_composition.py` (WP02)

**Implementation sketch**: copy `research-scoping.step-contract.yaml` as the template; substitute action verb, mission key, step IDs, delegate references per the [contracts/step-contracts.md](./contracts/step-contracts.md) one-paragraph spec for each contract. Test parametrizes over the 6 contracts and asserts schema invariants.

**Parallel opportunities**: T004-T009 are six independent files; an implementer can author them in any order. T010 depends on T004-T009 being on disk so the parametrize-over-glob discovers them.

---

## WP03 — Action Doctrine Bundles

**Goal**: ship 12 files under `src/doctrine/missions/documentation/actions/<action>/` (6 actions × `{index.yaml, guidelines.md}`), modeled on the existing research bundles.
**Priority**: P0.
**Independent test**: WP04's `test_action_bundle_matches_drg_edges` proves index.yaml ↔ DRG edges 1-to-1 mapping; the bundles must exist for that test to load. A small unit test in WP03 asserts each `index.yaml` parses as YAML and declares the expected `action` field.
**Dependencies**: none.
**Estimated prompt size**: ~400 lines.

**Included subtasks**:

- [ ] T011 Author `discover/index.yaml` + `discover/guidelines.md` (WP03)
- [ ] T012 Author `audit/index.yaml` + `audit/guidelines.md` (WP03)
- [ ] T013 Author `design/index.yaml` + `design/guidelines.md` (WP03)
- [ ] T014 Author `generate/index.yaml` + `generate/guidelines.md` (WP03)
- [ ] T015 Author `validate/index.yaml` + `validate/guidelines.md` (WP03)
- [ ] T016 Author `publish/index.yaml` + `publish/guidelines.md` (WP03)

**Implementation sketch**: copy research's `actions/scoping/{index.yaml,guidelines.md}` as the template; substitute action verb and adjust directives/tactics per the [data-model.md DRG edges table](./data-model.md#edges-add-to-srcdoctrinegraphyaml-edges-block). Each `guidelines.md` is 30-50 lines of governance prose for the host LLM. The directives/tactics in `index.yaml` MUST match the URN edges WP04 will add to `graph.yaml` (the unit test in WP04 enforces the 1-to-1 mapping by URN suffix).

**Parallel opportunities**: T011-T016 are 6 independent action directories; an implementer can author them in any order.

---

## WP04 — DRG Wiring

**Goal**: add 6 documentation action nodes + ~22 scope edges to `src/doctrine/graph.yaml`, plus a test file that proves DRG resolution and bundle/edges consistency.
**Priority**: P0.
**Independent test**: `test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` asserts node existence and `resolve_context(...).artifact_urns` non-empty for each action.
**Dependencies**: WP03 (the bundle directives/tactics list must match the URN edges 1-to-1).
**Estimated prompt size**: ~310 lines.

**Included subtasks**:

- [ ] T017 Add 6 documentation action nodes to `src/doctrine/graph.yaml` `nodes:` block (alphabetical with the existing `action:` URN family) (WP04)
- [ ] T018 Add ~22 scope edges to `src/doctrine/graph.yaml` `edges:` block per the data-model.md table (WP04)
- [ ] T019 Author `tests/specify_cli/test_documentation_drg_nodes.py` with 3 tests: per-action node+context; bundle↔edges consistency; resolve_context latency vs research 2× median (NFR-007) (WP04)

**Implementation sketch**: append nodes and edges directly to graph.yaml in the locations data-model.md specifies. The validated graph loader will reject the file if any directive/tactic URN does not exist; verify URNs DIRECTIVE_001/003/010/037 and the four tactics already exist via grep before authoring.

**Risks**: DIRECTIVE_037 (`Living Documentation Sync`) — verify it exists in graph.yaml before referencing. If it does not, fall back to DIRECTIVE_010 to keep the edges complete (no new directives/tactics introduced; spec C-005).

---

## WP05 — Composition Dispatch + Guard + Profile Defaults

**Goal**: wire documentation into the composition substrate via `_COMPOSED_ACTIONS_BY_MISSION`, `_ACTION_PROFILE_DEFAULTS`, and a fail-closed guard branch in `_check_composed_action_guard()`. Add the `_has_generated_docs` helper.
**Priority**: P0.
**Independent test**: `test_runtime_bridge_documentation_composition.py` covers dispatch entry, per-action guard pass/fail cases, unknown-action fail-closed, and missing-artifact failure-message text.
**Dependencies**: WP01 (sidecar template must exist); WP02 (contracts must exist); WP04 (DRG nodes must exist so resolution succeeds inside composition).
**Estimated prompt size**: ~480 lines.

**Included subtasks**:

- [ ] T020 Add `"documentation": frozenset({"discover", "audit", "design", "generate", "validate", "publish"})` to `_COMPOSED_ACTIONS_BY_MISSION` at `src/specify_cli/next/runtime_bridge.py:~274` (WP05)
- [ ] T021 Add 6 `(mission, action) → profile` entries to `_ACTION_PROFILE_DEFAULTS` at `src/specify_cli/mission_step_contracts/executor.py:~49` per FR-016 (WP05)
- [ ] T022 Add `_has_generated_docs` helper + documentation branch in `_check_composed_action_guard()` (per data-model.md), including fail-closed default for unknown actions (WP05)
- [ ] T023 Author `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` (WP05)

**Implementation sketch**: see [data-model.md → Guard branch shape](./data-model.md#guard-branch-shape) for the exact code skeleton. The `_has_generated_docs` helper is module-level. Tests should assert exact failure-message strings (e.g. `"Required artifact missing: spec.md"`, `"No guard registered for documentation action: ghost"`) so future copy-edits are caught.

**Risks**: ruff or mypy could flag the new branch (e.g. cyclomatic complexity from C901 `# noqa` comment; the research branch already has `# noqa: C901` at `runtime_bridge.py:515` — preserve it). Mitigation: WP05 implementer runs `ruff check src/specify_cli/next/runtime_bridge.py` and `mypy --strict src/specify_cli/next/runtime_bridge.py` before declaring done.

---

## WP06 — Real-Runtime Integration Walk

**Goal**: ship `tests/integration/test_documentation_runtime_walk.py` mirroring the research walk, with the C-007 docstring guard at the top.
**Priority**: P0 — this is the gate test for SC-001 / SC-003 / SC-004 / FR-013.
**Independent test**: the file itself runs end-to-end; reviewer greps for forbidden patch targets (FR-013).
**Dependencies**: WP01, WP02, WP03, WP04, WP05 (the runtime path must be wired before the walk can pass).
**Estimated prompt size**: ~430 lines.

**Included subtasks**:

- [ ] T024 Author scaffolding (`_init_min_repo`, `_scaffold_documentation_feature`, `isolated_repo` fixture) and the C-007 docstring at the top of `tests/integration/test_documentation_runtime_walk.py` (WP06)
- [ ] T025 Author 4 happy-path tests: `test_get_or_start_run_succeeds_for_documentation`, `test_documentation_template_resolves_runtime_sidecar`, `test_composition_advances_one_documentation_step`, `test_paired_invocation_lifecycle_is_recorded` (WP06)
- [ ] T026 Author 2 guard-failure tests: `test_missing_artifact_blocks_with_structured_failure`, `test_unknown_documentation_action_fails_closed` (WP06)

**Implementation sketch**: copy `tests/integration/test_research_runtime_walk.py` verbatim, substitute mission_type and action verbs, write the necessary "happy-path" feature artifacts (spec.md, gap-analysis.md, plan.md, docs/index.md, audit-report.md, release.md) before invoking composition for tests that should advance.

**Risks**: SaaS sync output noise (#735) could leak into stdout and break JSON parsing. Mitigation — the integration walk does not parse stdout (it calls Python APIs directly); only the dogfood smoke quickstart parses CLI JSON, and that uses `python -c "json.loads(open(file).read())"` which tolerates trailing noise.

---

## WP07 — CHANGELOG, Regression Sweep, Lint, Smoke Evidence

**Goal**: pre-merge hygiene — author CHANGELOG entry, run the full regression suite, run mypy/ruff on changed files, and verify the dogfood smoke runs cleanly from a separate temp repo.
**Priority**: P1 (final gate before mission-review).
**Independent test**: each subtask has an evidence artifact (CHANGELOG diff, pytest output, mypy output, ruff output, smoke command transcript).
**Dependencies**: WP06 (the integration walk must be green before regression sweep is meaningful).
**Estimated prompt size**: ~250 lines.

**Included subtasks**:

- [ ] T027 Add `CHANGELOG.md` entry for #502 documentation mission composition rewrite (WP07)
- [ ] T028 Run full regression sweep on the 6 protected suites; record results (WP07)
- [ ] T029 Run `mypy --strict` and `ruff check` on all changed files; record results (WP07)
- [ ] T030 Verify quickstart dogfood smoke runs cleanly from a temp repo using `uv --project`; record outputs (WP07)

**Implementation sketch**: this is a checklist WP. Each subtask produces an artifact under `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/<subtask-id>.md` (newly created directory); these are the inputs the mission-review skill consumes for the SC-006 verdict.

**Risks**: a regression in the protected suite (NFR-002) blocks merge. Mitigation — WP07 fails closed; mission-review will not issue PASS without all 4 evidence artifacts.

---

## Parallelization

- WP01, WP02, WP03 are independent; an implementer can dispatch them in parallel lanes (a, b, c).
- WP04 starts as soon as WP03 lands.
- WP05 starts after WP01 + WP02 + WP04 land (it depends on the contracts existing for composition wiring tests, the sidecar for runtime resolution, and the DRG nodes for resolve_context smoke).
- WP06 is the integration gate; it starts after WP05 lands.
- WP07 is the pre-merge gate; it starts after WP06 lands.

Critical path: WP03 → WP04 → WP05 → WP06 → WP07 (5 sequential WPs). WP01 and WP02 are off-critical-path because WP05 takes them as inputs but they can land first.

## MVP scope

The minimum viable deliverable is **all 7 WPs**. There is no smaller MVP; the spec's acceptance scenarios collectively require all of: a runtime sidecar (WP01), shipped contracts (WP02), action bundles (WP03), DRG nodes (WP04), composition wiring (WP05), an integration walk (WP06), and a dogfood smoke (WP07). Any partial subset leaves either the runtime unrunnable, a guard missing, or evidence incomplete.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Per-WP execution: `spec-kitty next --agent <name> --mission documentation-mission-composition-rewrite-01KQ5M1Y` allocates one worktree per execution lane; lane assignments are computed by `finalize-tasks`.
- Each WP commits to its lane branch; merge orchestration is part of the mission-merge step after WP07 lands.
