# Tasks: Research Mission Composition Rewrite v2

**Mission**: research-mission-composition-rewrite-v2-01KQ4QVV
**Branch**: `main` (planning base = merge target)
**Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

This is the reroll of issue #504 after the v1 attempt (preserved at git tag `attempt/research-composition-mission-100-broken`) failed external review. WP06 is the **P0 mission-level gate** — it drives `get_or_start_run` end-to-end with no mocks of composition surfaces and captures dogfood evidence. Without WP06's dogfood evidence in the commit log, the mission cannot merge.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Audit software-dev mission-runtime.yaml structure (read full file; record schema, RACI, defaults) | WP01 | – | [D] |
| T002 | Author `src/specify_cli/missions/research/mission-runtime.yaml` (6 PromptSteps + meta) | WP01 | – | [D] |
| T003 | Author `src/doctrine/missions/research/mission-runtime.yaml` (mirror of T002) | WP01 | – | [D] |
| T004 | Author 6 prompt templates: `scoping.md`, `methodology.md`, `gathering.md`, `synthesis.md`, `output.md`, `accept.md` | WP01 | [D] |
| T005 | Runnability proof: from a clean tmp repo, `get_or_start_run('demo-research', tmp_repo, 'research')` succeeds without raising `MissionRuntimeError` | WP01 | – | [D] |
| T006 | Reference v1 step contracts and doctrine bundles from git tag `attempt/research-composition-mission-100-broken` (read-only; do not merge) | WP02 | – | [D] |
| T007 | Author 5 shipped step contracts: `research-{scoping,methodology,gathering,synthesis,output}.step-contract.yaml` | WP02 | [D] |
| T008 | Author 5 action doctrine bundles (10 files: `index.yaml` + `guidelines.md` per action) under `src/doctrine/missions/research/actions/<action>/` | WP02 | [D] |
| T009 | Smoke: `MissionStepContractRepository().list_all()` returns 10 contracts; `MissionTemplateRepository.get_action_guidelines("research", <action>)` returns non-empty per action | WP02 | – | [D] |
| T010 | Audit `src/doctrine/graph.yaml` — read software-dev action nodes (lines 5-18) and the surrounding edges to learn the exact node/edge shape | WP03 | – | [D] |
| T011 | Add 5 `action:research/<action>` nodes to `src/doctrine/graph.yaml` | WP03 | – | [D] |
| T012 | Add per-action `scope` edges (per plan D2 edge map) from each research action to its directives + tactics | WP03 | – | [D] |
| T013 | **PROOF (mandatory)**: `load_validated_graph(repo)` succeeds (`assert_valid()` passes) | WP03 | – | [D] |
| T014 | **PROOF (mandatory)**: for each of 5 research actions, `resolve_context(graph, f"action:research/{action}", depth=...).artifact_urns` is non-empty | WP03 | – | [D] |
| T015 | Add `tests/specify_cli/test_research_drg_nodes.py` asserting T013 + T014 hold (no mocks of `load_validated_graph` or `resolve_context`) | WP03 | – | [D] |
| T016 | Verify `researcher-robbie` and `reviewer-renata` profiles exist under `src/doctrine/agent_profiles/shipped/` | WP04 | – | [D] |
| T017 | Add 5 `("research", action)` entries to `_ACTION_PROFILE_DEFAULTS` in `executor.py` | WP04 | – | [D] |
| T018 | Author `tests/specify_cli/mission_step_contracts/test_research_composition.py` covering contract loading, profile defaults, doctrine bundle resolution, software-dev sentinel | WP04 | – | [D] |
| T019 | Run `pytest tests/specify_cli/mission_step_contracts/`; mypy + ruff on changed files; zero new findings | WP04 | – | [D] |
| T020 | Add `"research": frozenset({...})` to `_COMPOSED_ACTIONS_BY_MISSION` in `runtime_bridge.py` | WP05 | – | [D] |
| T021 | Add 5 research-action branches to `_check_composed_action_guard()` per plan D3 (artifact + event-count checks against feature_dir) | WP05 | – | [D] |
| T022 | Add fail-closed default for unknown research actions: returns `["No guard registered for research action: <action>"]` (NOT empty list) | WP05 | – | [D] |
| T023 | Author `tests/specify_cli/next/test_runtime_bridge_research_composition.py`. Cover: dispatch fires for known research actions, refuses unknown, fast-path invariant, action_hint==step.id, no fall-through after success/failure, all 5 guard-failure cases on empty feature_dir, fail-closed for unknown research action. **C-007 forbidden mock list pasted as a header comment in the test file; reviewer greps for any forbidden patch target.** | WP05 | – | [D] |
| T024 | Run `pytest tests/specify_cli/next/`; mypy + ruff on changed files; zero new findings | WP05 | – | [D] |
| T025 | Author `tests/integration/test_research_runtime_walk.py` — drives `get_or_start_run('demo-research-walk', tmp_repo, 'research')` end-to-end through at least one composed step. Asserts: no `MissionRuntimeError`, `context.action == step.id`, paired invocation lifecycle records (started + done/failed), structured guard failure on missing artifact, no fall-through to legacy DAG. **C-007 forbidden mock list pasted as header comment; reviewer greps.** | WP06 | – | [D] |
| T026 | Author `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/quickstart.md` with the operator-runnable dogfood smoke sequence (clean checkout, create demo mission, advance one step, observe trail records) | WP06 | – | [D] |
| T027 | Run full regression sweep: `pytest tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/integration/test_mission_run_command.py`. All must pass. mypy --strict + ruff zero new findings on full diff. | WP06 | – | [D] |
| T028 | Capture dogfood evidence: from a clean shell run quickstart sequence; paste full command output into `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md` and into the WP06 commit message. **Without this evidence file, mission-review verdict is UNVERIFIED.** | WP06 | – | [D] |

## Work Packages

### WP01 — Research mission-runtime.yaml + 6 Prompt Templates (P0 FOUNDATION)

**Goal**: Author the missing `mission-runtime.yaml` sidecar at `src/specify_cli/missions/research/` and `src/doctrine/missions/research/`. Add 6 prompt templates that the steps reference. Prove `get_or_start_run('demo-research', tmp_repo, 'research')` no longer raises `MissionRuntimeError`.

**Priority**: P0 (foundation; FR-001/FR-002/FR-003/FR-010; runnability)

**Independent test**: From a clean tmp repo, `get_or_start_run` for `mission_type='research'` returns a run handle without `MissionRuntimeError`. The runtime engine reaches at least the planning step.

**Subtasks**:
- [x] T001 Audit software-dev mission-runtime.yaml structure (WP01)
- [x] T002 Author `src/specify_cli/missions/research/mission-runtime.yaml` (WP01)
- [x] T003 Author `src/doctrine/missions/research/mission-runtime.yaml` (WP01)
- [x] T004 Author 6 prompt templates (WP01)
- [x] T005 Runnability proof — `get_or_start_run` succeeds (WP01)

**Dependencies**: None.

**Estimated prompt size**: ~350 lines.

**Prompt**: [`tasks/WP01-mission-runtime-and-templates.md`](./tasks/WP01-mission-runtime-and-templates.md)

---

### WP02 — Re-author 5 Step Contracts + 10 Action Doctrine Bundles (P0 FOUNDATION)

**Goal**: Re-author the contracts and doctrine bundles the v1 attempt got right. Reference v1 tag artifacts; do not merge from the tag. Prove the loader and resolver see the new files.

**Priority**: P0 (foundation; FR-006 doctrine reachable, FR-015)

**Independent test**: 10 contracts visible to `MissionStepContractRepository`; non-empty content from `MissionTemplateRepository.get_action_guidelines` for each research action.

**Subtasks**:
- [x] T006 Reference v1 tag artifacts (WP02)
- [x] T007 Author 5 step contracts (WP02)
- [x] T008 Author 10 doctrine bundle files (WP02)
- [x] T009 Smoke-load both repositories (WP02)

**Dependencies**: None.

**Estimated prompt size**: ~330 lines.

**Prompt**: [`tasks/WP02-contracts-and-doctrine.md`](./tasks/WP02-contracts-and-doctrine.md)

---

### WP03 — DRG Action Nodes + Edges, with Validity AND Resolution Proof (P0 FOUNDATION)

**Goal**: Hand-add 5 `action:research/*` nodes plus per-action scope edges to `src/doctrine/graph.yaml`. Prove the validated graph accepts the new shape AND that `resolve_context` returns non-empty `artifact_urns` for every research action.

**Priority**: P0 (foundation; FR-004/FR-005/FR-006 — closes the v1 P1 DRG-empty finding)

**Independent test**: `load_validated_graph(repo)` succeeds; `resolve_context(graph, f"action:research/{action}", depth=...)` returns non-empty `artifact_urns` for each of 5 actions.

**Subtasks**:
- [x] T010 Audit graph.yaml node + edge format (WP03)
- [x] T011 Add 5 action:research/* nodes (WP03)
- [x] T012 Add per-action scope edges (WP03)
- [x] T013 Proof — assert_valid passes (WP03)
- [x] T014 Proof — resolve_context.artifact_urns non-empty per action (WP03)
- [x] T015 Test asserting both proofs (WP03)

**Dependencies**: None.

**Estimated prompt size**: ~320 lines.

**Prompt**: [`tasks/WP03-drg-nodes-and-edges.md`](./tasks/WP03-drg-nodes-and-edges.md)

---

### WP04 — Profile Defaults + Composition Resolution Test (P0 INTEGRATION)

**Goal**: Wire 5 `("research", action)` entries into `_ACTION_PROFILE_DEFAULTS`. Author the unit test that proves contracts (WP02), doctrine bundles (WP02 + WP03), and profile defaults all resolve via the composition resolver path.

**Priority**: P0 (integration; FR-009 inherited / FR-011 / FR-014)

**Independent test**: `pytest tests/specify_cli/mission_step_contracts/test_research_composition.py` passes; software-dev sentinel passes.

**Subtasks**:
- [x] T016 Verify profile names exist (WP04)
- [x] T017 Add 5 entries to `_ACTION_PROFILE_DEFAULTS` (WP04)
- [x] T018 Author `test_research_composition.py` (WP04)
- [x] T019 Run focused + regression (WP04)

**Dependencies**: WP01, WP02, WP03.

**Estimated prompt size**: ~290 lines.

**Prompt**: [`tasks/WP04-profile-defaults-and-composition-test.md`](./tasks/WP04-profile-defaults-and-composition-test.md)

---

### WP05 — Runtime Bridge: Dispatch + 5 Guard Branches + Fail-Closed + Bridge Test (P0 INTEGRATION)

**Goal**: Add the `"research"` entry to `_COMPOSED_ACTIONS_BY_MISSION`. Extend `_check_composed_action_guard()` with 5 research branches that check `feature_dir` directly. Add a fail-closed default for unknown research actions. Author the bridge unit test that proves all of this — and explicitly forbids mocks of the C-007 surfaces.

**Priority**: P0 (integration; FR-007/FR-008/FR-009/FR-012/FR-014 — closes the v1 P1 silent-pass finding)

**Independent test**: `pytest tests/specify_cli/next/test_runtime_bridge_research_composition.py` passes (covers 5 guard cases + fail-closed + dispatch + action_hint + no-fallthrough). Software-dev bridge test stays green.

**C-007 enforcement**: The new test file's header MUST list these forbidden patch targets and the file MUST NOT match any of them via `unittest.mock.patch`:
- `_dispatch_via_composition`
- `StepContractExecutor.execute`
- `ProfileInvocationExecutor.invoke`
- `_load_frozen_template` (and any frozen-template loader)
- `load_validated_graph`
- `resolve_context`

Reviewer greps the test file. Any hit blocks approval.

**Subtasks**:
- [x] T020 Add `"research"` to `_COMPOSED_ACTIONS_BY_MISSION` (WP05)
- [x] T021 Add 5 research-action branches to `_check_composed_action_guard` (WP05)
- [x] T022 Add fail-closed default for unknown research actions (WP05)
- [x] T023 Author bridge test with C-007 enforcement (WP05)
- [x] T024 Run focused + regression + mypy/ruff (WP05)

**Dependencies**: WP04.

**Estimated prompt size**: ~430 lines.

**Prompt**: [`tasks/WP05-runtime-bridge-and-guards.md`](./tasks/WP05-runtime-bridge-and-guards.md)

---

### WP06 — Real-Runtime Walk + Dogfood Smoke (P0 FINAL GATE; BLOCKS MERGE)

**Goal**: Author the integration walk that drives `get_or_start_run('demo-research-walk', tmp_repo, 'research')` end-to-end, advancing at least one composed step, with NO mocks of the C-007 forbidden surfaces. Add quickstart.md with the operator dogfood sequence. Capture dogfood evidence from a clean shell run; without that evidence file, mission-review verdict is UNVERIFIED.

**Priority**: P0 (mission-level gate; FR-001/FR-002/FR-003/FR-013/FR-014/NFR-005/NFR-006/SC-001/SC-002/SC-003/SC-004/SC-006 — **WP06 IS THE GATE THAT BLOCKS MERGE.**)

**Independent test**: `pytest tests/integration/test_research_runtime_walk.py -v` passes; reviewer greps the file for forbidden patches; `smoke-evidence.md` contains real command output from a clean run.

**C-007 enforcement (same forbidden list as WP05; this is the most important place)**:
- `_dispatch_via_composition`
- `StepContractExecutor.execute`
- `ProfileInvocationExecutor.invoke`
- frozen-template loaders
- `load_validated_graph`
- `resolve_context`

Reviewer greps the test file. Any hit blocks approval.

**Dogfood smoke evidence (mandatory)**: WP06 produces `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md` with verbatim command output from running the quickstart sequence on a clean shell. Mission-review consumes this file as the C-008 hard gate.

**Subtasks**:
- [x] T025 Author `test_research_runtime_walk.py` with C-007 enforcement (WP06)
- [x] T026 Author `quickstart.md` with operator dogfood sequence (WP06)
- [x] T027 Run full regression sweep + mypy/ruff (WP06)
- [x] T028 Capture dogfood evidence in `smoke-evidence.md` (WP06)

**Dependencies**: WP05.

**Estimated prompt size**: ~410 lines.

**Prompt**: [`tasks/WP06-real-runtime-walk-and-smoke.md`](./tasks/WP06-real-runtime-walk-and-smoke.md)

---

## MVP Scope

There is no MVP for this reroll. **All 6 WPs are P0** because the v1 attempt shipped 4 of them (WP02 contracts, WP02 doctrine bundles, WP04 defaults, WP05 dispatch entry) without WP01 (runnability), WP03 (DRG), the WP05 guards, or WP06 (real walk + dogfood) — and that produced a non-runnable, silently-failing mission. The whole gate must close.

## Parallelization Plan

```
WP01 ┐
WP02 ├──> WP04 ──> WP05 ──> WP06 ┐
WP03 ┘                            └──> merge → mission-review (must include dogfood evidence)
```

WP01, WP02, WP03 are independent (different filesystem subtrees) and may parallelize. The integration WPs (WP04, WP05) and the gate WP (WP06) are strictly sequential.

## Mission-Level Acceptance Gates (encoded in WP06 + mission-review)

The mission MUST NOT merge unless ALL of these are true:

1. **Runnability** (WP01 + WP06): `get_or_start_run('demo-research', tmp_repo, 'research')` succeeds from a clean repo. Captured in `smoke-evidence.md`.
2. **DRG resolution** (WP03 + WP06): for each of 5 research actions, validated graph node exists AND `resolve_context.artifact_urns` is non-empty. Captured in WP03 unit test + WP06 walk.
3. **Guard parity** (WP05 + WP06): each of 5 missing-artifact scenarios produces a structured guard failure on the composed path; unknown research actions fail closed. Captured in WP05 bridge test + WP06 walk.
4. **No mocks of C-007 surfaces** (WP05 + WP06): test files greppable; reviewer asserts zero hits on the forbidden list.
5. **Dogfood smoke evidence** (WP06): `smoke-evidence.md` contains real command output. Mission-review verdict is UNVERIFIED without it.
6. **No regression** (all WPs): software-dev composition tests, custom mission walk, runtime bridge composition test, mission-run-command test all stay green.

## Branch Strategy (repeated)

- Current branch: `main`
- Planning base / merge target: `main`
- Branch matches target: `true`
- Execution worktrees assigned by `finalize-tasks` and resolved per WP at `spec-kitty implement` time.
