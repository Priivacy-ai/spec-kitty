# Research — Software-Dev Mission Composition Rewrite

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Phase**: 0 (research)
**Date**: 2026-04-25

Three research items resolved. No outstanding `[NEEDS CLARIFICATION]`.

---

## R-1 — How `StepContractExecutor.execute` resolves and routes

**Decision**: Use `StepContractExecutor.execute(StepContractExecutionContext)` as the single composition entry point, and let it select the contract via `MissionStepContractRepository.get_by_action(mission, action)`.

**Rationale**: The executor (`src/specify_cli/mission_step_contracts/executor.py`) already:
- Loads the action context via `resolve_context(graph, f"action:{mission}/{action}", depth=context.resolution_depth)` — line 148–149.
- Resolves each step's `delegates_to` candidates against the action-scoped artifact URN set — `_resolve_step_delegations` (line 208).
- Routes each step through `ProfileInvocationExecutor.invoke(...)` with the resolved `profile_hint`, actor, and mode-of-work — line 158.
- Defaults profile per `(mission, action)` from `_ACTION_PROFILE_DEFAULTS` (line 36) — already covers `specify`/`plan`/`implement`/`review`. Only `tasks` is missing.
- Raises `StepContractExecutionError` when the contract is missing for `(mission, action)` (line 142) or when a profile cannot be resolved (line 203).

This is exactly the surface FR-001..006 expect. The runtime bridge does not need to re-implement context resolution, profile defaulting, or delegation walking — it only needs to construct the context and call `execute`.

**Alternatives considered**:
- Have the runtime bridge build invocation payloads directly. Rejected: duplicates resolution logic, violates C-001 (executor stays the composer).
- Generate a synthetic `MissionStepContract` at runtime per call. Rejected: defeats the point of the shipped contracts being declarative source-of-truth.

---

## R-2 — Where the runtime bridge currently dispatches

**Decision**: Insert a composition dispatch branch inside the bridge function that today invokes the legacy DAG step IDs (after `_check_step_guards`). Branch on `mission_type == "software-dev"` and `step_id ∈ {"specify","plan","tasks","implement","review"}` (collapsing `tasks_outline`/`tasks_packages`/`tasks_finalize` into one composed `tasks`).

**Rationale**: Reading `src/specify_cli/next/runtime_bridge.py`:
- `_check_step_guards` (lines 180–225) validates artifact preconditions per step ID. The five legacy IDs we're collapsing/rewiring (`specify`, `plan`, `tasks_outline`, `tasks_packages`, `tasks_finalize`, `implement`, `review`) all have explicit branches here.
- `_build_discovery_context` (line 254) and `_candidate_templates_for_root` (line 284) discover `mission-runtime.yaml`. These remain intact — we deprecate-but-keep the file (D-3).
- The bridge has no production callsite for `StepContractExecutor` today (verified by grep: only the executor's own tests reference it). So the integration is a true new wire-up, not a refactor.

**Migration semantics**:
- For `software-dev`'s five public actions, the new branch builds a `StepContractExecutionContext` from runtime metadata (`repo_root`, `mission`, `action`, `actor`, optional `profile_hint`, `request_text`) and calls `executor.execute(context)`.
- The collapsed `tasks` guard runs the union of the three legacy `tasks_*` checks: `tasks.md` exists, ≥1 `tasks/WP*.md` exists, every WP has a raw `dependencies` frontmatter field.
- All other missions and step IDs fall through to the existing legacy DAG path unchanged.

**Alternatives considered**:
- Remove the legacy DAG branch entirely. Rejected: blast-radius too large for one slice, and D-3 explicitly chose the conservative path.
- Have `StepContractExecutor` be discovered via runtime template metadata (e.g., a flag in `mission-runtime.yaml`). Rejected: adds an extra indirection layer when a direct call site is clearer and easier to test.

---

## R-3 — Why `tasks.step-contract.yaml` does not exist

**Decision**: Create a new `tasks.step-contract.yaml` under `src/doctrine/mission_step_contracts/shipped/` mirroring the structure of the four existing shipped contracts. Three internal sub-steps: `outline`, `packages`, `finalize`.

**Rationale**: Listing `src/doctrine/mission_step_contracts/shipped/` shows only `specify.step-contract.yaml`, `plan.step-contract.yaml`, `implement.step-contract.yaml`, `review.step-contract.yaml`. The legacy DAG (`mission-runtime.yaml` v2.1.0) split `tasks` into three runtime steps; the new composition layer needs to express the same substructure but as one publicly-addressable step contract. This keeps the public action surface aligned with the operator-facing slash commands (`/spec-kitty.tasks`) per D-1.

**Action governance** (`actions/tasks/index.yaml`) already declares the right scope: `directives` 003/010/024, `tactics` adr-drafting / problem-decomposition / requirements-validation. The new contract's `delegates_to` candidates must select from this set so action-scoped resolution selects them (per `StepContractExecutor._resolve_step_delegations` semantics).

**Sub-step responsibilities**:
- `outline` — produce `tasks.md` (delegate: `problem-decomposition` tactic).
- `packages` — produce `tasks/WP##.md` files (delegate: `010-specification-fidelity-requirement` directive — each WP must trace to a spec/plan element).
- `finalize` — validate dependencies + finalize WP metadata (declared command: `spec-kitty agent mission finalize-tasks`; delegate: `024-locality-of-change` directive to enforce small WP scopes).

**Alternatives considered**:
- Three separate top-level contracts (`tasks_outline.step-contract.yaml`, …). Rejected per D-1: bloats the public action surface without operator-visible benefit; would also force three new entries in `_ACTION_PROFILE_DEFAULTS` and three new runtime-bridge dispatch branches.
- Inline the substructure inside the executor's logic. Rejected: violates declarative-source-of-truth principle and C-001 (executor stays a composer).

---

## Closed: missing items

- `[NEEDS CLARIFICATION]` count: 0
- Open assumptions: 0 (all three locked at D-1, D-2, D-3 in plan.md)
