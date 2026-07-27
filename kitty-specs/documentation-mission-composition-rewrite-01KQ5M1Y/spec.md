# Specification — Documentation Mission Composition Rewrite

**Mission ID**: `01KQ5M1Y190VANF39KMBWZP6SD`
**Mission slug**: `documentation-mission-composition-rewrite-01KQ5M1Y`
**Mission type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-26
**Source**: Phase 6 WP6.4 — GitHub issue [#502](https://github.com/Priivacy-ai/spec-kitty/issues/502) (umbrella [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461), epic [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468))
**Baseline commit**: `62ec07b952d53e215857cd0e1c1eb7bf3f1a32dc` on `origin/main`
**Reference implementation**: research mission composition (`kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/`, landed via #504)

## Purpose

### TL;DR

Move the built-in documentation mission onto the StepContractExecutor composition substrate. After this mission lands, an operator must be able to run `spec-kitty agent mission create demo-docs --mission-type documentation` from a clean repo and drive it end-to-end via `spec-kitty next` through the live runtime path, with each composed action resolving real DRG context and missing artifacts producing structured guard failures (no silent passes, no legacy-DAG fallback).

### Context

Phase 6 has now landed two of the three built-in mission composition rewrites:

- `software-dev` (#503 + stabilization #786 / #793 / #794) — single-dispatch composition, paired invocation trails, contract-action-name correctness.
- `research` (#504) — runtime sidecar template, action-scoped doctrine bundles, DRG action nodes, fail-closed guard branches, real-runtime integration walk.
- `documentation` is the **last** remaining built-in legacy state-machine mission. It still ships only the legacy `mission.yaml` (states/transitions/guards) at `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml`. There is no `mission-runtime.yaml`, no `documentation-*.step-contract.yaml` under `src/doctrine/mission_step_contracts/shipped/`, no action bundle under `src/doctrine/missions/documentation/actions/`, no `action:documentation/*` nodes in `src/doctrine/graph.yaml`, no entry in `_COMPOSED_ACTIONS_BY_MISSION`, no documentation entries in `_ACTION_PROFILE_DEFAULTS`, and no documentation branch in `_check_composed_action_guard()`.

The result is that `spec-kitty agent mission create … --mission-type documentation` followed by `spec-kitty next` on a documentation mission cannot enter the composition path at all. Documentation is the only built-in mission still routed through the legacy DAG, which makes it the last blocker before Phase 6 can declare composition the universal substrate for built-in missions.

The runtime substrate this mission sits on is now stable:

- StepContractExecutor (#501) is landed.
- Single-dispatch composition + paired invocation trails + contract-action-name correctness (#786 / #793 / #794) is landed.
- Runtime-boundary preflight (#798) and local custom mission loader (#505) are landed.

This mission re-uses that substrate. It does not modify it. The closest reference for the work is the merged research composition (#504); the implementer should mirror its file layout and test shape, substituting documentation-native action verbs and artifact gates.

## User Scenarios & Testing

### Primary actor

A spec-kitty operator (human or agent harness) who runs `spec-kitty agent mission create demo-docs --mission-type documentation --json` in a clean checkout and then drives the mission via `spec-kitty next --agent <name> --mission <handle>`.

### Acceptance Scenarios

**Scenario 1 — Fresh documentation mission starts and advances via composition**
- **Given** a clean spec-kitty checkout with no prior documentation missions
- **When** the operator runs `spec-kitty agent mission create demo-docs --mission-type documentation --json`, parses the result, then runs `spec-kitty next --agent <name> --mission <handle>`
- **Then** the runtime returns a next-step decision without raising `MissionRuntimeError`
- **And** the step is dispatched via `StepContractExecutor` (not the legacy DAG)
- **And** the operator's invocation trail under `~/.kittify/invocations/` contains a paired `started` + (`done` or `failed`) lifecycle for the action
- **And** the recorded action name is documentation-native (one of `discover`, `audit`, `design`, `generate`, `validate`, `publish`), not a profile-default verb (e.g. `specify`, `plan`, `tasks`).

**Scenario 2 — Each documentation action resolves real DRG context**
- **Given** the merged code and a freshly created documentation mission
- **When** the runtime resolves governance context for any of the six documentation actions
- **Then** `load_validated_graph(repo).get_node(f'action:documentation/{action}')` is truthy for each of `discover`, `audit`, `design`, `generate`, `validate`, `publish`
- **And** `resolve_context(graph, f'action:documentation/{action}', depth=...)` returns non-empty `artifact_urns`
- **And** the action-scoped doctrine surfaced to the host LLM is the bundle authored under `src/doctrine/missions/documentation/actions/<action>/`, not the empty default.

**Scenario 3 — Missing artifacts produce structured guard failures**
- **Given** an empty documentation feature directory (no `spec.md`, `gap-analysis.md`, `plan.md`, `docs/`, validation report, or publication handoff artifact)
- **When** the runtime attempts to advance via composition for any of the six documentation actions
- **Then** `_check_composed_action_guard()` returns a non-empty failure list naming the missing artifact (or the failing predicate from `mission.yaml` / `expected-artifacts.yaml`) for that action
- **And** `_dispatch_via_composition()` propagates the failure as a structured error with no run-state advancement
- **And** the legacy DAG path is NOT invoked as a fallback (#797 invariant preserved)
- **And** an unknown documentation action (e.g. a hypothetical seventh verb absent from `_COMPOSED_ACTIONS_BY_MISSION`) MUST fail closed with a structured `"No guard registered for documentation action: <name>"` error rather than silently pass.

**Scenario 4 — Real-runtime integration walk passes**
- **Given** the test suite at HEAD on `main`
- **When** an operator runs `uv run --python 3.13 --extra test python -m pytest tests/integration/test_documentation_runtime_walk.py -v`
- **Then** at least one test in that file calls `get_or_start_run` (or `decide_next_via_runtime`) and drives a documentation mission through every advancing action via the live runtime
- **And** that test does NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`
- **And** the test asserts paired lifecycle records, action_hint correctness, and structured guard failure on missing artifacts.

**Scenario 5 — Software-dev, research, and custom-mission paths preserved**
- **Given** the existing software-dev composition test suite, the research composition test suite, the custom-mission walk test, and the runtime bridge composition test on `origin/main`
- **When** they run after this mission lands
- **Then** they pass byte-identically — no edits beyond import-path adjustments forced by new module placement, if any.

**Scenario 6 — Operator dogfood smoke matches the integration walk**
- **Given** the merged code on a clean repo
- **When** the mission-review skill executes a documented quickstart sequence in a separate temp repo using `uv run --project <spec-kitty-repo> spec-kitty agent mission create demo-docs --mission-type documentation --json` followed by `uv run --project <spec-kitty-repo> spec-kitty next --agent <name> --mission <handle>`
- **Then** the same outcomes Scenario 1 asserts are observable interactively, and the trail records under `~/.kittify/invocations/` show the documentation-native action names.

### Edge cases

- A documentation action whose contract resolves successfully but whose composed step raises an exception inside `StepContractExecutor.execute`: the invocation lifecycle must close as `failed`, run state must not advance, and the legacy DAG must not be invoked as fallback.
- A doctrine bundle that exists on disk but is not referenced by the DRG: `resolve_context()` must return empty for that action, and a contract referencing it must surface a structured error pointing at the missing graph node, not silently succeed.
- Two consecutive composed documentation actions sharing the same profile but different action_hints (e.g. `discover` and `audit` both bound to `researcher-robbie`): each invocation must record its own action_hint and action-scoped doctrine context.
- A future runtime change that adds a seventh documentation action without a corresponding entry in `_check_composed_action_guard`: the guard must fail closed (return a structured "no guard registered for (documentation, X)" error), not silently pass.
- A documentation mission that only produces a partial `docs/` tree (e.g. one Markdown file but no top-level `docs/index.md`): the `generate` guard must still fail closed if the configured artifact predicate is unmet, and the failure list must name the missing path or pattern.
- Smoke output that contains trailing background-sync / final-sync lines after the JSON payload (#735): the smoke evidence must be tolerant of the trailing noise — JSON parsing must use a leading-line strategy, not whole-stdout `json.loads()` — but the documentation-mission acceptance criteria are unaffected by it.

## Domain Language (canonical terms)

| Term | Meaning | Avoid as synonym |
|---|---|---|
| MissionTemplate | The Pydantic schema at `src/specify_cli/next/_internal_runtime/schema.py` (the same one consumed for software-dev and research) that the runtime engine consumes; requires `mission.key`, `steps: list[PromptStep]`, optional `audit_steps`. | "mission spec", "mission file" |
| Composition substrate | `StepContractExecutor` + `ProfileInvocationExecutor` + the `_should_dispatch_via_composition` fast path. | "v2 path", "new runtime" |
| Validated DRG | The graph returned by `charter._drg_helpers.load_validated_graph(repo)`. The shipped portion lives at `src/doctrine/graph.yaml`; project overlays at `.kittify/doctrine/graph.yaml`. | "DRG", "doctrine graph" |
| Action node | A DRG node with URN of the form `action:<mission>/<action>`. Carries VOCABULARY/SCOPE/etc. edges that `resolve_context()` walks to populate `artifact_urns`. | "doctrine entry", "action index entry" |
| Composed-action guard | The function `_check_composed_action_guard()` in `src/specify_cli/next/runtime_bridge.py` that fires after composition to verify expected artifacts/events; returns a non-empty failure list to block run-state advancement. | "post-action validator", "guard" |
| Real-runtime walk | An integration test that calls `get_or_start_run` (or `decide_next_via_runtime` end-to-end) without mocking `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. | "integration test" |
| Dogfood smoke | A documented operator-facing sequence that creates a real documentation mission and advances it from a separate temp repo using `uv run --project <spec-kitty-repo>`. The mission-review skill must execute this before issuing PASS. | "smoke test", "dry run" |
| Documentation action set | The six documentation-native action verbs: `discover`, `audit`, `design`, `generate`, `validate`, `publish`. Mirrors the existing legacy `mission.yaml` workflow phases. A terminal `accept` step may be added if the runtime template requires it; `accept` is not a composed action and does not appear in `_COMPOSED_ACTIONS_BY_MISSION`. | "phases", "states" |

## Requirements

### Functional Requirements

| ID | Requirement | Status | Notes |
|---|---|---|---|
| FR-001 | A fresh documentation mission MUST start via `get_or_start_run(slug, repo, 'documentation')` from a clean repo without raising `MissionRuntimeError`. | Required | Closes the v0 runnability gap. |
| FR-002 | The runtime MUST advance at least one composed step in a fresh documentation mission via `spec-kitty next` without falling through to the legacy DAG. | Required | Closes the v0 dispatch gap. |
| FR-003 | A `MissionTemplate` for documentation MUST be authored at `src/specify_cli/missions/documentation/mission-runtime.yaml` and (mirrored at) `src/doctrine/missions/documentation/mission-runtime.yaml`, declaring `mission.key: documentation`, an explicit non-empty `steps: list[PromptStep]` covering at least the six documentation actions plus any terminal `accept` step required by the schema, and any `audit_steps` required by the schema. | Required | Mirrors `src/specify_cli/missions/research/mission-runtime.yaml` and the doctrine-side sidecar. |
| FR-004 | For every documentation action in `_COMPOSED_ACTIONS_BY_MISSION["documentation"]`, `load_validated_graph(repo).get_node(f'action:documentation/{action}')` MUST return a truthy node. | Required | Closes the DRG node gap. |
| FR-005 | For every documentation action, `resolve_context(graph, f'action:documentation/{action}', depth=...)` MUST return non-empty `artifact_urns`. | Required | Right-sized governance context delivery. |
| FR-006 | The action-scoped doctrine bundle authored at `src/doctrine/missions/documentation/actions/<action>/index.yaml` and `src/doctrine/missions/documentation/actions/<action>/guidelines.md` for each of the six documentation actions MUST be reachable via the DRG resolution path used by composition (not just via `MissionTemplateRepository.get_action_guidelines`). | Required | Closes the bundle-not-reachable gap. |
| FR-007 | `_check_composed_action_guard()` MUST handle each of the six documentation actions with parity to existing software-dev and research guards. | Required | Closes the silent-pass guard gap. |
| FR-008 | When a documentation-action precondition is unmet, the guard MUST return a non-empty structured failure list naming the missing artifact or predicate. The minimum gates are: (a) `discover` ⇒ `spec.md` exists; (b) `audit` ⇒ `gap-analysis.md` exists; (c) `design` ⇒ `plan.md` exists; (d) `generate` ⇒ at least one Markdown file exists under the documentation-output path declared by `expected-artifacts.yaml` (default: `docs/**/*.md`); (e) `validate` ⇒ a validation/audit report exists at the path declared by the runtime template (default: `audit-report.md`); (f) `publish` ⇒ a publication-handoff artifact exists at the path declared by the runtime template (default: `release.md`). | Required | Promotes the legacy mission.yaml predicates into observable artifact gates. |
| FR-009 | `_dispatch_via_composition()` MUST propagate guard failures as structured errors with no run-state advancement and no legacy-DAG fallback. | Required | Inherited from #797 invariant; preserved for documentation. |
| FR-010 | The documentation `MissionTemplate` MUST satisfy the same loader path that `software-dev` and `research` use today (`load_mission_template` → discovery tier walk). No bespoke loader for documentation. | Required | No regression to the loader. |
| FR-011 | Every composed documentation action invocation MUST record `action_hint == contract.action`. | Required | Inherited from `executor.py`; preserved for documentation. |
| FR-012 | Every profile invocation opened for a documentation action MUST be closed with a paired terminal record (`done` or `failed`) before the step returns. | Required | Inherited; preserved for documentation. |
| FR-013 | The integration test that proves SC-001 / SC-002 / SC-003 MUST drive the real runtime via `get_or_start_run` (or `decide_next_via_runtime`) and MUST NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. | Required | Mirrors `tests/integration/test_research_runtime_walk.py`. |
| FR-014 | Existing software-dev composition behavior, research composition behavior, custom mission loader behavior, and runtime bridge behavior MUST remain unchanged for inputs that already passed at the baseline commit. | Required | Regression contract. |
| FR-015 | The 6 step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-{discover,audit,design,generate,validate,publish}.step-contract.yaml`, the 6 doctrine bundles under `src/doctrine/missions/documentation/actions/<action>/`, the 6 entries in `_ACTION_PROFILE_DEFAULTS`, and the `"documentation"` entry in `_COMPOSED_ACTIONS_BY_MISSION` MUST exist after this mission. Step contracts MUST use `StepContractExecutor` as composer over `ProfileInvocationExecutor` and MUST NOT become model runners or text generators. | Required | Wholesale composition wiring. |
| FR-016 | The default profile assignments per documentation action MUST be: `discover → researcher-robbie`, `audit → researcher-robbie`, `design → architect-alphonso`, `generate → implementer-ivan`, `validate → reviewer-renata`, `publish → reviewer-renata`. No new shipped profile is introduced. If a contract or runtime template declares an explicit `agent_profile`, that explicit binding takes precedence over `_ACTION_PROFILE_DEFAULTS`, matching the substrate contract. | Required | Reuses landed profiles per the brief. |
| FR-017 | Unknown documentation actions (any `(mission="documentation", action=<name>)` not in `_COMPOSED_ACTIONS_BY_MISSION["documentation"]`) MUST fail closed in `_check_composed_action_guard()` with a structured `"No guard registered for documentation action: <name>"` failure entry. The mission-review evidence MUST include a test asserting this fail-closed behavior. | Required | Mirrors the research fail-closed default added in #504. |
| FR-018 | The legacy state-machine `mission.yaml` files at `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml` MAY remain on disk for backward reference, but the runtime resolution path used by `spec-kitty next` for `mission_type='documentation'` MUST resolve the new `mission-runtime.yaml`. If both files exist, the discovery walk MUST prefer the runtime sidecar; if it ever resolves the legacy `mission.yaml` for a documentation mission, that is a regression. | Required | Mirrors how research handled coexistence. |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Test coverage: a real-runtime integration test MUST exist for documentation alongside refreshed unit tests for each new map entry, contract, and doctrine surface. | At least one real-runtime walk (no mocks of the listed surfaces) plus parametrized unit tests covering: contract loading for all 6 actions, profile defaults for all 6 actions, DRG node existence for all 6 actions, doctrine bundle resolution for all 6 actions, guard parity for all 6 actions including the unknown-action fail-closed path. | Required |
| NFR-002 | Existing test suites that protect the substrate MUST stay green. | 100% pass on `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, `tests/specify_cli/next/test_runtime_bridge_research_composition.py`, `tests/integration/test_research_runtime_walk.py`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/integration/test_mission_run_command.py`. | Required |
| NFR-003 | mypy --strict MUST report zero new errors on changed files. | Zero new findings. Pre-existing baseline errors are not regressed. The narrow cast in `mission_step_contracts/executor.py` tracked by #805 is allowed only as a hygiene subtask if and only if mypy-strict on changed files would otherwise fail; it does not block #502 acceptance. | Required |
| NFR-004 | ruff check MUST report zero new findings on changed files. | Zero new findings on `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/mission_step_contracts/executor.py`, all new test files, and any other touched module. | Required |
| NFR-005 | Mission-review verdict of PASS MUST require the dogfood smoke (Scenario 6) to succeed in a separate temp repo before the verdict is issued. The mission-review skill must record the smoke output as evidence. The smoke MUST be invoked via `uv run --project <spec-kitty-repo> …`, never `uv --directory <spec-kitty-repo>`, because `--directory` pollutes the source repo and corrupts JSON output (per #735). | Hard gate. PASS verdicts that omit smoke evidence — or that ran the smoke via `--directory` — are invalid and downgraded to UNVERIFIED. | Required |
| NFR-006 | Trail records for composed documentation actions MUST be operator-readable: each contains action name, profile name, and lifecycle status. | All trail records contain these three fields without internal-only identifiers. | Required |
| NFR-007 | DRG load + per-action context resolution latency MUST not exceed 2× the current research-action median when measured on the same machine. | A microbenchmark run on the test machine (median of 5 runs) shows documentation `resolve_context` latency ≤ 2× the research median for the same depth. | Required |

### Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | Spec Kitty MUST NOT call host LLMs or generate documentation content. Documentation content (reading source files, drafting prose, generating reference output, summarizing audits) is owned by the host harness. | Trust boundary preserved from #503 / #504. | Required |
| C-002 | The composition chokepoint for documentation MUST remain `StepContractExecutor`. The runtime bridge MUST NOT call `ProfileInvocationExecutor` directly for documentation actions. | Inherited #797 architectural invariant. | Required |
| C-003 | `_ACTION_PROFILE_DEFAULTS` additions MUST be limited to built-in documentation actions. No generalization to wildcard keys or arbitrary custom missions. No new shipped profile is introduced. | Preserves #505 custom-loader contract. | Required |
| C-004 | Out of scope: retrospective work (#506-#511), `spec-kitty explain` (#534), SaaS / tracker / sync architecture changes, low-priority loader hygiene (#801), Python pin & strict-mypy hygiene (#805) except as a narrow preflight subtask if and only if mypy-strict on changed files would otherwise fail, and sync/final-shutdown noise (#735) except as smoke-tolerance evidence. | Phase 6 sequencing; package-boundary discipline. | Required |
| C-005 | The mission MUST build on #501 / #503 / #504 / #505 / #786 / #793 / #794 / #798 invariants. It MUST NOT re-open already-closed Phase 6 review findings. | Treat past invariants as regression risks, not open bugs. | Required |
| C-006 | The legacy `mission.yaml` (state machine) for documentation MAY coexist with the new `mission-runtime.yaml`, but `spec-kitty next` for `mission_type='documentation'` MUST always resolve the runtime sidecar. If the legacy file is preserved, the plan MUST justify it; if it is removed, the plan MUST prove no consumer of the legacy file is orphaned. Either choice is acceptable; an unjustified silent change is not. | Plan-time decision; do not implicitly orphan downstream consumers. | Required |
| C-007 | Real-runtime tests MUST NOT use `unittest.mock.patch` against `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. | The point of FR-013 is to prove the live path; mocking those defeats it. | Required |
| C-008 | The mission-review skill invocation that issues the final PASS verdict MUST include explicit dogfood smoke evidence in its report. Reports without smoke evidence are downgraded to UNVERIFIED. | NFR-005 is the consequent. | Required |
| C-009 | Documentation step contracts MUST NOT add `expected_artifacts` or any new top-level field to the contract schema. Artifact gates live in `_check_composed_action_guard()` (and, where the legacy file remains the source of truth, in the existing `expected-artifacts.yaml`). Contracts remain delegation records, not artifact validators. | Inherited contract schema invariant. | Required |
| C-010 | The dogfood smoke MUST be executed in a temp repo OUTSIDE the spec-kitty source tree (not inside `<spec-kitty-repo>/.dogfood/` or any sub-path of the working tree). The temp repo MUST be `git init`-ed before invocation and removed after. | Prevents source-tree pollution and matches the research smoke pattern. | Required |

## Success Criteria

| ID | Outcome | Measure |
|---|---|---|
| SC-001 | A fresh documentation mission can be created and advanced. | From a clean checkout: `spec-kitty agent mission create demo-docs --mission-type documentation --json` succeeds; subsequent `spec-kitty next --agent <name> --mission <handle>` returns a next-step decision without `MissionRuntimeError`. |
| SC-002 | Each documentation action has a real DRG node with non-empty resolved context. | For each of the 6 documentation actions, `load_validated_graph(repo).get_node(f'action:documentation/{action}')` is truthy and `resolve_context(graph, ..., depth=...).artifact_urns` is non-empty. |
| SC-003 | Missing artifacts produce structured guard failures. | `_check_composed_action_guard` returns a non-empty failure list naming the missing artifact for each of the 6 actions on an empty feature directory; `_dispatch_via_composition` propagates the failure with no run-state advancement. An unknown documentation action fails closed with a structured "No guard registered for documentation action: <name>" entry. |
| SC-004 | Real-runtime test passes without bypassing composition surfaces. | `tests/integration/test_documentation_runtime_walk.py` passes; `grep` confirms the file does not patch `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`. |
| SC-005 | No regression. | All five regression suites (mission_step_contracts/, runtime_bridge_composition, runtime_bridge_research_composition, research_runtime_walk, custom_mission_walk) pass on the merged commit. |
| SC-006 | Mission-review PASS verdict carries dogfood smoke evidence. | Mission-review report includes a "dogfood smoke" section with command output proving SC-001 from a separate temp repo, executed via `uv run --project <spec-kitty-repo>`. Without that section — or if the smoke ran via `--directory` — the verdict is UNVERIFIED. |
| SC-007 | Documentation runtime template resolves before legacy mission.yaml. | An assertion in the integration test (or a unit test on the loader) shows `load_mission_template('documentation')` resolves the new `mission-runtime.yaml`, not the legacy `mission.yaml`. |

## Key Entities

- **MissionTemplate (documentation)** — the Pydantic-validated runtime template that the engine consumes when `mission_type='documentation'`. Its `mission.key` is `documentation` and its `steps` list defines the concrete sequence of `PromptStep` objects the engine walks across the six documentation actions plus any terminal `accept` step. New artifact in this mission.
- **Action node (documentation/X)** — a DRG node whose URN is `action:documentation/<action>` for X in `{discover, audit, design, generate, validate, publish}`. Carries the same edge shape as research action nodes (VOCABULARY, SCOPE, etc.). New artifact in this mission.
- **Composed-action guard (documentation branch)** — the new conditional branches inside `_check_composed_action_guard()` that handle documentation actions and emit structured failures on unmet preconditions, including a fail-closed default for unknown documentation actions. New code path in this mission.
- **Real-runtime walk** — `tests/integration/test_documentation_runtime_walk.py` authored to call `get_or_start_run` (or `decide_next_via_runtime`) and assert end-to-end behavior without mocking any composition surface. New artifact in this mission.
- **Dogfood smoke** — a hard-gated quickstart sequence that the mission-review skill executes from a separate temp repo using `uv run --project <spec-kitty-repo>` to prove SC-001 against the merged code on a clean repo.

## Assumptions

These will be re-confirmed in `/spec-kitty.plan` against the actual code; any contradicted by the audit must be resolved before tasks.

1. `MissionTemplate` (Pydantic) is loaded from a YAML file via `load_mission_template_file()`. The discovery tier walk (`load_mission_template`) maps `mission_type='documentation'` to a YAML file on disk in the same way it does for software-dev and research; placing `mission-runtime.yaml` next to the legacy `mission.yaml` is sufficient for the runtime to resolve it (mirroring research).
2. The validated DRG (`src/doctrine/graph.yaml` plus optional `.kittify/doctrine/graph.yaml` overlay) is the consumer for `action:documentation/*` nodes. The shipped graph is hand-authored or migrated; there is no extractor that would automatically populate documentation nodes from the action doctrine bundles. Documentation nodes mirror research nodes' edge shape.
3. `_check_composed_action_guard()` is the right surface to extend. On unrecognized `(mission, action)` pairs it currently returns an empty failure list (silent pass) for missions other than research; the existing research fail-closed default is the model the documentation branch follows.
4. The six action verbs (`discover`, `audit`, `design`, `generate`, `validate`, `publish`) are the right choices because they match the legacy `mission.yaml` workflow phases verbatim. The audit step in `/spec-kitty.plan` confirms whether a terminal `accept` step is required by the runtime schema; if so, it is added as a non-composed step (it does NOT appear in `_COMPOSED_ACTIONS_BY_MISSION`).
5. The four shipped profiles already used by software-dev and research (`researcher-robbie`, `architect-alphonso`, `implementer-ivan`, `reviewer-renata`) are sufficient for documentation. No new shipped profile is introduced.
6. `expected-artifacts.yaml` for documentation already declares legacy artifact predicates (`spec.md`, `gap-analysis.md`, `plan.md`, `tasks.md`, `docs/**/*.md`); the plan-time audit decides whether the runtime template references these or whether the guard branch hardcodes them. Either is acceptable as long as the gates in FR-008 are observable at runtime.
7. The `accept` step in the research runtime template (`src/specify_cli/missions/research/mission-runtime.yaml`) is the right shape to mirror for documentation if the schema requires a terminal step.

## Dependencies

- Landed: #501 (StepContractExecutor), #503 (software-dev composition), #786 / #793 / #794 (composition stabilization), #504 (research composition), #505 (local custom mission loader), #798 (runtime-boundary preflight).
- Not blocked by: #506-#511 (retrospective tranche), #534 (`spec-kitty explain`), #801 (loader hygiene), #805 (Python pin & strict-mypy hygiene), #735 (sync/final-shutdown noise).
- External: none. Self-contained inside `Priivacy-ai/spec-kitty`.
- Tooling: `.python-version` is currently pinned to `3.13.12`, which may not be installable through `uv` on the test machine. All test/lint/type commands MUST use the explicit form `uv run --python 3.13 --extra test python -m pytest …`, `uv run --python 3.13 --extra lint ruff check …`, `uv run --python 3.13 --extra lint mypy --strict …`. The dogfood smoke MUST use `uv run --project <spec-kitty-repo>` rather than `uv --directory <spec-kitty-repo>`.

## Out of Scope

- Retrospective contract / lifecycle work (#506-#511) — separate Phase 6 tranche.
- `spec-kitty explain` (#534).
- SaaS / tracker / sync behavior changes.
- `spec_kitty_events` and `spec_kitty_tracker` package-boundary surfaces.
- Host-LLM-side documentation authorship.
- Loosening the Python patch pin or generalizing the strict-mypy cast in `executor.py` (#805) beyond the narrow hygiene subtask permitted by NFR-003.
- Background sync / final-sync shutdown noise cleanup (#735) beyond making the smoke parser tolerant of trailing lines.
- New shipped agent profiles. The documentation defaults reuse `researcher-robbie`, `architect-alphonso`, `implementer-ivan`, `reviewer-renata`.
- Custom-mission loader behavior (#505) — already landed; no documentation-specific code paths are added to the custom-mission loader.
- Software-dev or research composition changes — both are landed and out of scope for this tranche.

## Open Questions

To be resolved during `/spec-kitty.plan`:

1. **Coexistence vs replacement of legacy `mission.yaml`**: does the new `mission-runtime.yaml` coexist with the legacy `mission.yaml` (matching how research handled it), or is the legacy file removed entirely? If coexisting, the plan must prove `load_mission_template('documentation')` always resolves the runtime sidecar first. If removing, the plan must prove no consumer of the legacy file is orphaned.
2. **DRG authoring**: are `action:documentation/*` nodes added to the shipped `src/doctrine/graph.yaml` (matching research), to the project overlay, or via a calibration step that reads action bundles? Plan-time audit must answer.
3. **Guard data source**: do the documentation guard branches in `_check_composed_action_guard()` enforce `mission.yaml`'s declarative predicates (`artifact_exists`) and `expected-artifacts.yaml` directly, or do they re-implement the same checks against the feature directory? Plan-time decision.
4. **PromptStep shape per action**: each of the six documentation actions needs at least one `PromptStep`. Plan-time decision: which steps bind `contract_ref` (if any) and which use the contract-synthesis path mirroring research?
5. **Terminal step**: does the runtime schema for documentation require a non-composed `accept` step (mirroring `src/specify_cli/missions/research/mission-runtime.yaml`)? If yes, what is its `agent_profile`? Plan-time decision.
6. **`generate` artifact predicate**: the legacy `expected-artifacts.yaml` declares `docs/**/*.md` as a non-blocking output. The `generate` guard MUST upgrade this to a blocking gate; plan must decide whether the gate is "any Markdown file under `docs/`" or "an explicit top-level `docs/index.md`".
7. **`validate` and `publish` artifact predicates**: the legacy `mission.yaml` does not declare a concrete `audit-report.md` or `release.md` location. Plan must commit to specific paths so that FR-008(e) and FR-008(f) are observable.

## Definition of Done

- All FR-### items have at least one explicit test or assertion proving them.
- All NFR-### items have a measurement or threshold check.
- All C-### items are observable in the diff or in test code.
- Every Open Question is resolved in `plan.md` with code-grounded evidence.
- All 6 Acceptance Scenarios pass against the merged code.
- The mission-review skill invocation includes dogfood smoke evidence in its report; without it — or if smoke was invoked via `--directory` — the verdict is UNVERIFIED, not PASS.
- All five regression suites (mission_step_contracts/, runtime_bridge_composition, runtime_bridge_research_composition, research_runtime_walk, custom_mission_walk) pass byte-identically.
- `mypy --strict` reports zero new errors on changed files.
- `ruff check` reports zero new findings on changed files.
- The dogfood smoke runs from a separate temp repo using `uv run --project <spec-kitty-repo>` and the trail records under `~/.kittify/invocations/` show documentation-native action names.
