# Specification — Research Mission Composition Rewrite v2

**Mission ID**: `01KQ4QVVZ4DC6CXA1XCZZAQ8AG`
**Mission slug**: `research-mission-composition-rewrite-v2-01KQ4QVV`
**Mission type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-26
**Source**: Reroll of Phase 6 GitHub issue [#504](https://github.com/Priivacy-ai/spec-kitty/issues/504) after the v1 attempt failed external review
**Baseline commit**: `e056f39870343c31300959099d6955f1c8ed48e3` on `origin/main`
**Prior attempt evidence**: git tag `attempt/research-composition-mission-100-broken` at commit `d10af600` (local-only, never pushed)

## Purpose

### TL;DR

Deliver a runnable, composition-backed research mission. Operators must be able to create a fresh research mission and advance it via `spec-kitty next`. Each composed action must resolve real governance context from the validated DRG, and missing-artifact scenarios must produce structured guard failures, not silent passes.

### Context

PRs #795 / #797 / #799 already moved `software-dev` onto the Phase 6 composition substrate and added the local custom mission loader. Issue #504 promised the same migration for the built-in `research` mission. The v1 attempt at #504 (preserved at tag `attempt/research-composition-mission-100-broken`) authored 5 step contracts, 5 doctrine bundles, 5 profile-default entries, 1 dispatch-table entry, and 3 test files — but it left the runtime gap unbridged. External review found four blocking defects:

1. Research has no `MissionTemplate.steps` and no `mission.key`, so `get_or_start_run('demo-research', repo, 'research')` raises `MissionRuntimeError: Mission 'research' not found`. The mission cannot start.
2. The new action doctrine bundles exist on disk but the validated DRG has no `action:research/*` nodes; `resolve_context()` returns empty `artifact_urns`. Right-sized governance context is not delivered.
3. `_check_composed_action_guard()` handles only software-dev action names; research actions fall through with no failures, so missing-artifact runs silently succeed on the composed path.
4. The v1 integration walk called `_dispatch_via_composition()` directly because it could not enter the real runtime. It cannot prove end-to-end runnability or guard parity.

This mission closes those four defects. The contracts, doctrine bundles, profile defaults, and dispatch entry are re-authored on top of the corrected substrate, but the value-add is the four corrections.

## User Scenarios & Testing

### Primary actor

A spec-kitty operator (human or agent harness) who runs `spec-kitty agent mission create demo-research --mission-type research` and then drives the mission via `spec-kitty next` in a clean checkout.

### Acceptance Scenarios

**Scenario 1 — Fresh research mission starts and advances via composition**
- **Given** a clean spec-kitty checkout with no prior research missions
- **When** the operator runs `spec-kitty agent mission create demo-research --mission-type research --json`, parses the result, then runs `spec-kitty next --agent <name> --mission <handle>`
- **Then** the runtime returns a next-step decision without raising `MissionRuntimeError`
- **And** the step is dispatched via `StepContractExecutor` (not the legacy DAG)
- **And** the operator's invocation trail under `~/.kittify/invocations/` contains a paired `started`+`done` (or `failed`) lifecycle for the action

**Scenario 2 — Each research action resolves real DRG context**
- **Given** the merged code and a freshly created research mission
- **When** the runtime resolves governance context for any of the five research actions
- **Then** `load_validated_graph(repo).get_node('action:research/<action>')` is truthy for each of `scoping`, `methodology`, `gathering`, `synthesis`, `output`
- **And** `resolve_context(graph, 'action:research/<action>', depth=...)` returns non-empty `artifact_urns`
- **And** the action-scoped doctrine surfaced to the host LLM is the bundle authored under `src/doctrine/missions/research/actions/<action>/`, not the empty default

**Scenario 3 — Missing artifacts produce structured guard failures**
- **Given** an empty research feature directory (no `spec.md`, no `plan.md`, no `source-register.csv`, no `findings.md`)
- **When** the runtime attempts to advance via composition for any of the five research actions
- **Then** `_check_composed_action_guard()` returns a non-empty failure list naming the missing artifact (or the failing predicate from `mission.yaml`)
- **And** `_dispatch_via_composition()` propagates the failure as a structured error with no run-state advancement
- **And** the legacy DAG path is NOT invoked as a fallback (PR #797 invariant preserved)

**Scenario 4 — Real-runtime integration walk passes**
- **Given** the test suite at HEAD on `main`
- **When** an operator runs `uv run pytest tests/integration/test_research_runtime_walk.py -v`
- **Then** at least one test in that file calls `get_or_start_run` (or its programmatic equivalent) and drives a research mission through every advancing action via the live runtime
- **And** that test does NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, or any frozen-template loader
- **And** the test asserts paired lifecycle records, action_hint correctness, and structured guard failure on missing artifacts

**Scenario 5 — Software-dev and custom-mission paths preserved**
- **Given** the existing software-dev composition test suite, the custom-mission walk test, and the runtime bridge composition test on `origin/main`
- **When** they run after this mission lands
- **Then** they pass byte-identically — no test edits beyond import-path adjustments forced by new module placement, if any

**Scenario 6 — Operator dogfood smoke matches the integration walk**
- **Given** the merged code on a clean repo
- **When** an operator follows the quickstart's "drive a real research mission" section
- **Then** the same outcomes Scenario 1 asserts are observable interactively, and the trail records under `~/.kittify/invocations/` show the research-native action names (not profile-default verbs)

### Edge cases

- A research action whose contract resolves successfully but whose composed step raises an exception inside `StepContractExecutor.execute`: the invocation lifecycle must close as `failed`, run state must not advance, and the legacy DAG must not be invoked as fallback.
- A doctrine bundle that exists on disk but is not referenced by the DRG: `resolve_context()` must return empty for that action, and a contract referencing it must surface a structured error pointing at the missing graph node, not silently succeed.
- Two consecutive composed research actions sharing the same profile but different action_hints: each invocation must record its own action_hint and action-scoped doctrine context.
- A future runtime change that adds a sixth research action without a corresponding entry in `_check_composed_action_guard`: the guard must fail closed (return a structured "no guard registered for (research, X)" error), not silently pass.

## Domain Language (canonical terms)

| Term | Meaning | Avoid as synonym |
|---|---|---|
| MissionTemplate | The Pydantic schema at `src/specify_cli/next/_internal_runtime/schema.py:445` that the runtime engine consumes; requires `mission.key`, `steps: list[PromptStep]`, optional `audit_steps`. | "mission spec", "mission file" |
| Composition substrate | `StepContractExecutor` + `ProfileInvocationExecutor` + the `_should_dispatch_via_composition` fast path. | "v2 path", "new runtime" |
| Validated DRG | The graph returned by `charter._drg_helpers.load_validated_graph(repo)`. The shipped portion lives at `<doctrine_root>/graph.yaml`; project overlays at `.kittify/doctrine/graph.yaml`. | "DRG", "doctrine graph" |
| Action node | A DRG node with URN of the form `action:<mission>/<action>`. Carries VOCABULARY/SCOPE/etc. edges that `resolve_context()` walks to populate `artifact_urns`. | "doctrine entry", "action index entry" |
| Composed-action guard | The function `_check_composed_action_guard()` in `runtime_bridge.py` that fires after composition to verify expected artifacts/events; returns a non-empty failure list to block run-state advancement. | "post-action validator", "guard" |
| Real-runtime walk | An integration test that calls `get_or_start_run` (or `decide_next_via_runtime` end-to-end) without mocking `_dispatch_via_composition`, `StepContractExecutor.execute`, frozen-template loaders, or the DRG. | "integration test" |
| Dogfood smoke | A documented operator-facing sequence (quickstart) that creates a real research mission and advances it. The mission-review skill must execute this before issuing PASS. | "smoke test", "dry run" |

## Requirements

### Functional Requirements

| ID | Requirement | Status | Notes |
|---|---|---|---|
| FR-001 | A fresh research mission MUST start via `get_or_start_run(slug, repo, 'research')` from a clean repo without raising `MissionRuntimeError`. | Required | Closes v1 P0 finding. |
| FR-002 | The runtime MUST advance at least one composed step in a fresh research mission via `spec-kitty next` without falling through to the legacy DAG. | Required | Closes v1 P0 finding. |
| FR-003 | The research `MissionTemplate` MUST declare `mission.key: research`, an explicit non-empty `steps: list[PromptStep]`, and any `audit_steps` required by the schema. | Required | Inferred from schema.py:445. |
| FR-004 | For every research action in `_COMPOSED_ACTIONS_BY_MISSION["research"]`, `load_validated_graph(repo).get_node(f'action:research/{action}')` MUST return a truthy node. | Required | Closes v1 P1 DRG finding. |
| FR-005 | For every research action, `resolve_context(graph, f'action:research/{action}', depth=...)` MUST return non-empty `artifact_urns`. | Required | Closes v1 P1 DRG finding. |
| FR-006 | The action-scoped doctrine bundle (under `src/doctrine/missions/research/actions/<action>/`) authored for each research action MUST be reachable via the DRG resolution path used by composition (not just via `MissionTemplateRepository.get_action_guidelines`). | Required | Closes v1 P1 DRG finding. |
| FR-007 | `_check_composed_action_guard()` MUST handle each of the five research actions with parity to existing software-dev guards. | Required | Closes v1 P1 guard finding. |
| FR-008 | When a research-action precondition is unmet (missing `spec.md`, missing `plan.md`, fewer than 3 `source_documented` events, missing `findings.md`, missing `publication_approved` gate), the guard MUST return a non-empty structured failure list naming the missing artifact or predicate. | Required | Closes v1 P1 guard finding. |
| FR-009 | `_dispatch_via_composition()` MUST propagate guard failures as structured errors with no run-state advancement and no legacy-DAG fallback. | Required | Inherited PR #797 invariant; preserved for research. |
| FR-010 | The `MissionTemplate` for research MUST satisfy the same loader path that `software-dev` uses today (`load_mission_template` → discovery tier walk). | Required | No bespoke loader for research. |
| FR-011 | Every composed research action invocation MUST record `action_hint == contract.action`. | Required | Inherited from `executor.py:173`; preserved for research. |
| FR-012 | Every profile invocation opened for a research action MUST be closed with a paired terminal record (`done` or `failed`) before the step returns. | Required | Inherited; preserved for research. |
| FR-013 | The integration test that proves SC-001 / SC-002 / SC-003 MUST drive the real runtime via `get_or_start_run` (or `decide_next_via_runtime`) and MUST NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, frozen-template loaders, or the DRG. | Required | Closes v1 P1 bypass-test finding. |
| FR-014 | Existing software-dev composition behavior, custom mission loader behavior, and runtime bridge behavior MUST remain unchanged for inputs that already passed at the baseline commit. | Required | Regression contract. |
| FR-015 | The 5 step contracts under `src/doctrine/mission_step_contracts/shipped/research-{action}.step-contract.yaml`, the 5 doctrine bundles under `src/doctrine/missions/research/actions/<action>/`, the 5 entries in `_ACTION_PROFILE_DEFAULTS`, and the `"research"` entry in `_COMPOSED_ACTIONS_BY_MISSION` MUST exist (re-authored on top of the corrected substrate, not carried forward from the v1 attempt). | Required | Wholesale replacement, not patch. |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Test coverage: a real-runtime integration test MUST exist for research alongside refreshed unit tests for each new map entry, contract, and doctrine surface. | At least one real-runtime walk (no mocks of the listed surfaces) plus parametrized unit tests for: contract loading, profile defaults, DRG node existence, doctrine bundle resolution, guard parity. | Required |
| NFR-002 | Existing test suites that protect the substrate MUST stay green. | 100% pass on `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/integration/test_mission_run_command.py`. | Required |
| NFR-003 | mypy --strict MUST report zero new errors on changed files. | Zero new findings. Pre-existing baseline errors are not regressed. | Required |
| NFR-004 | ruff check MUST report zero new findings on changed files. | Zero new findings. | Required |
| NFR-005 | Mission-review verdict of PASS MUST require the dogfood smoke (Scenario 6) to succeed before the verdict is issued. The mission-review skill must record the smoke output as evidence. | Hard gate. PASS verdicts that omit smoke evidence are invalid. | Required |
| NFR-006 | Trail records for composed research actions MUST be operator-readable: each contains action name, profile name, and lifecycle status. | All trail records contain these three fields without internal-only identifiers. | Required |

### Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | Spec Kitty MUST NOT call host LLMs or generate research findings. Research content (reading, reasoning, citation drafting, synthesis prose) is owned by the host harness. | Trust boundary preserved from v1 spec. | Required |
| C-002 | The composition chokepoint for research MUST remain `StepContractExecutor`. The runtime bridge MUST NOT call `ProfileInvocationExecutor` directly for research actions. | Inherited PR #797 architectural invariant. | Required |
| C-003 | `_ACTION_PROFILE_DEFAULTS` additions MUST be limited to built-in research actions. No generalization to wildcard keys or arbitrary custom missions. | Preserves PR #799 custom-loader contract. | Required |
| C-004 | Out of scope: documentation mission composition (#502), retrospective work (#506-#511), low-priority loader hygiene (#801), `spec-kitty explain` (#534), SaaS / tracker / sync, `spec_kitty_events` and `spec_kitty_tracker` package surfaces. | Phase 6 sequencing; package-boundary discipline. | Required |
| C-005 | The mission MUST build on PR #795 / #797 / #799 invariants. It MUST NOT re-open already-closed Phase 6 review findings. | Treat past invariants as regression risks, not open bugs. | Required |
| C-006 | If the existing legacy `mission.yaml` (state machine with `states`/`transitions`/`guards`) at `src/specify_cli/missions/research/mission.yaml` and `src/doctrine/missions/research/mission.yaml` is replaced rather than coexisting with the new `MissionTemplate`, the mission MUST document why and prove backward compatibility for any consumer of the legacy file. | Plan-time decision; do not implicitly orphan downstream consumers. | Required |
| C-007 | Real-runtime tests MUST NOT use `unittest.mock.patch` against `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. | The point of FR-013 is to prove the live path; mocking those defeats it. | Required |
| C-008 | The mission-review skill invocation that issues the final PASS verdict MUST include explicit dogfood smoke evidence in its report. Reports without smoke evidence are downgraded to UNVERIFIED. | NFR-005 is the consequent. | Required |

## Success Criteria

| ID | Outcome | Measure |
|---|---|---|
| SC-001 | A fresh research mission can be created and advanced. | From a clean checkout: `spec-kitty agent mission create demo-research --mission-type research --json` succeeds; subsequent `spec-kitty next --agent <name> --mission <handle>` returns a next-step decision without `MissionRuntimeError`. |
| SC-002 | Each research action has a real DRG node with non-empty resolved context. | For each of the 5 research actions, `load_validated_graph(repo).get_node(f'action:research/{action}')` is truthy and `resolve_context(...).artifact_urns` is non-empty. |
| SC-003 | Missing artifacts produce structured guard failures. | `_check_composed_action_guard` returns a non-empty failure list naming the missing artifact for each of the 5 actions on an empty feature directory; `_dispatch_via_composition` propagates the failure with no run-state advancement. |
| SC-004 | Real-runtime test passes without bypassing composition surfaces. | `tests/integration/test_research_runtime_walk.py` passes; `grep` confirms the file does not patch `_dispatch_via_composition`, `StepContractExecutor.execute`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. |
| SC-005 | No regression. | All four regression suites (mission_step_contracts/, runtime_bridge_composition, custom_mission_walk, mission_run_command) pass on the merged commit. |
| SC-006 | Mission-review PASS verdict carries dogfood smoke evidence. | Mission-review report includes a "dogfood smoke" section with command output proving SC-001 from a clean repo. Without that section, the verdict is UNVERIFIED. |

## Key Entities

- **MissionTemplate (research)** — the Pydantic-validated runtime template that the engine consumes when `mission_type='research'`. Its `mission.key` is `research` and its `steps` list defines the concrete sequence of `PromptStep` objects the engine walks. New artifact in this mission.
- **Action node (research/X)** — a DRG node whose URN is `action:research/<action>` for X in `{scoping, methodology, gathering, synthesis, output}`. Carries the same edge shape as software-dev action nodes (VOCABULARY, SCOPE, etc.). New artifact in this mission.
- **Composed-action guard (research branch)** — the new conditional branches inside `_check_composed_action_guard()` that handle research actions and emit structured failures on unmet preconditions. New code path in this mission.
- **Real-runtime walk** — `tests/integration/test_research_runtime_walk.py` rewritten to call `get_or_start_run` and assert end-to-end without mocking any composition surface. Replacement artifact in this mission.
- **Dogfood smoke** — a hard-gated quickstart sequence that an operator (or the mission-review skill) executes to prove SC-001 against the merged code on a clean repo.

## Assumptions

These will be re-confirmed in `/spec-kitty.plan` against the actual code; any contradicted by the audit must be resolved before tasks.

1. `MissionTemplate` (Pydantic) is loaded from a YAML file via `load_mission_template_file()` (`src/specify_cli/next/_internal_runtime/schema.py:548-576`). The discovery tier walk (`load_mission_template`, `src/specify_cli/next/_internal_runtime/discovery.py:294-313`) maps `mission_type='research'` to a YAML file on disk. The new template lands at one of those discovered locations.
2. The validated DRG (`<doctrine_root>/graph.yaml` plus `.kittify/doctrine/graph.yaml` overlay) is the consumer for `action:research/*` nodes. The shipped graph is hand-authored or migrated; there is no extractor that would automatically populate research nodes from the action doctrine bundles.
3. `_check_composed_action_guard()` (`src/specify_cli/next/runtime_bridge.py:444-520`) is the right surface to extend; on unrecognized `(mission, action)` pairs it returns an empty failure list (silent pass), which is the v1 P1 finding.
4. Software-dev's `MissionTemplate` exists somewhere on the discovery path with `steps: list[PromptStep]`; mirroring it for research is the minimum sufficient change for runnability.
5. The five research action verbs (`scoping`, `methodology`, `gathering`, `synthesis`, `output`) and their profile defaults (researcher-robbie x4, reviewer-renata for output) remain the right choices; the reroll preserves these from the v1 plan.

## Dependencies

- Landed: PR #795 (software-dev composition), PR #797 (composition stabilization), PR #799 (local custom mission loader).
- Not blocked by: #502, #506-#511, #801. These remain downstream Phase 6 tranches.
- External: none. Self-contained inside `Priivacy-ai/spec-kitty`.
- Local artifacts of v1 attempt are preserved at git tag `attempt/research-composition-mission-100-broken` for reference; the reroll does not import them but may copy verbatim from them where the v1 work was correct (contracts, doctrine prose, profile defaults).

## Out of Scope

- Documentation mission composition rewrite (#502).
- Retrospective contract / lifecycle work (#506-#511).
- Local-loader hygiene (#801) unless directly co-located with reroll changes.
- SaaS / tracker / sync behavior.
- `spec-kitty explain` (#534).
- `spec_kitty_events`, `spec_kitty_tracker`, or any external package-boundary surfaces.
- Host-LLM-side research authorship.
- Any framework-level redesign of the runtime engine to natively support state-machine missions (the existing v1 `mission.yaml` may coexist with the new `MissionTemplate` as long as runnability and guard parity are met; replacing it wholesale is acceptable but optional).

## Open Questions

To be resolved during `/spec-kitty.plan`:

1. **Coexistence vs replacement**: does the new `MissionTemplate` replace the legacy `src/specify_cli/missions/research/mission.yaml` and its `src/doctrine/missions/research/mission.yaml` counterpart, or do both coexist? If they coexist, what is the read precedence in `load_mission_template`?
2. **DRG authoring**: are `action:research/*` nodes added to the shipped `<doctrine_root>/graph.yaml`, or to the project overlay, or via a calibration step that reads action bundles? Plan-time audit must answer.
3. **Guard semantics**: do the research guard branches in `_check_composed_action_guard()` enforce mission.yaml's declarative predicates (`artifact_exists`, `event_count`, `gate_passed`) directly, or do they re-implement the same checks against the feature directory? Plan-time decision.
4. **PromptStep shape per action**: each of the 5 research actions needs at least one `PromptStep`. What `agent_profile` and `contract_ref` (if any) does each step bind to, and how does the existing software-dev pattern translate? Plan-time decision.
5. **v1 preserved artifacts**: which v1 artifacts can be copied verbatim from the `attempt/research-composition-mission-100-broken` tag (e.g. step contract YAML files, doctrine bundles), and which must be re-authored against the corrected substrate? Plan-time decision.

## Definition of Done

- All FR-### items have at least one explicit test or assertion proving them.
- All NFR-### items have a measurement or threshold check.
- All C-### items are observable in the diff or in test code.
- Every Open Question is resolved in `plan.md` with code-grounded evidence.
- All 6 Acceptance Scenarios pass against the merged code.
- The mission-review skill invocation includes dogfood smoke evidence in its report; without it, the verdict is UNVERIFIED, not PASS.
- v1's regression suites pass byte-identically.
