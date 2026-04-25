# Mission Specification: Phase 6 Composition Stabilization

**Mission ID**: 01KQ2JASW34A4K6HYNS5V41KFK
**Mission Slug**: phase6-composition-stabilization-01KQ2JAS
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-04-25

## Purpose

Close three follow-up bugs in the just-landed `software-dev` composition path so the live consumer of the composition layer is single-dispatch, leaves no orphaned invocation records, and preserves the contract action across `profile_hint` calls. This unblocks the custom mission loader (`#505`).

### Stakeholder Context

PR `#795` (issue `#503`) shipped the built-in `software-dev` composition rewrite. It made `software-dev` the first live consumer of the composition layer introduced by `StepContractExecutor` (`#501`). Three regressions remain in the dispatch and trail-writing seams:

- **`#786`** — After successful composition, `runtime_bridge.py` still falls through to the legacy DAG dispatch route (`runtime_next_step(...)`), so action execution effectively double-dispatches. This is the explicit blocker on `#505`.
- **`#793`** — `StepContractExecutor.execute()` calls `ProfileInvocationExecutor.invoke(...)` per contract step, which writes a `started` JSONL record, but nothing ever closes the invocation. Composed runs leak `started`-only files in `.kittify/events/profile-invocations/`.
- **`#794`** — `ProfileInvocationExecutor.invoke(request_text, profile_hint=...)` derives the action from the resolved profile's role default, so composed `software-dev/specify` records `analyze`, composed `software-dev/plan` records `audit`, etc. — instead of the contract action.

All three are surface-level seams in the composition layer; none require schema, mission, or charter changes.

## User Scenarios & Testing

### Primary Actors

- **Mission runtime + agents** running `spec-kitty next --agent <name>` against the `software-dev` mission.
- **Operators / contributors** inspecting the local-first invocation trail (`.kittify/events/profile-invocations/*.jsonl`).
- **Future consumers** of the composition layer (notably `#505` custom mission loader).

### Acceptance Scenarios

**Scenario A — Composed action does not double-dispatch (covers `#786`)**
Given the `software-dev` mission is on a step whose action is `specify`, `plan`, `tasks`, `implement`, or `review`,
When the runtime bridge dispatches that action through `StepContractExecutor`,
And composition succeeds,
Then the legacy DAG dispatch handler (the path that calls `runtime_next_step(...)` on a successful composed action) **MUST NOT** be entered for the same action,
And run-state, lane status, and prompt progression **MUST** still advance to the next public step,
And the existing `tasks` guard semantics **MUST** be preserved exactly:
- `tasks_outline` requires `tasks.md`;
- `tasks_packages` requires `tasks.md` and at least one `tasks/WP*.md`;
- `tasks_finalize` and the public `tasks` step require the terminal task state including a `dependencies:` block.

**Scenario B — Composed step closes its invocation lifecycle (covers `#793`)**
Given a composed `software-dev` action runs to completion (success path),
When inspecting the invocation JSONL files produced by that run under `.kittify/events/profile-invocations/`,
Then every file produced by that action **MUST** contain at least one `started` event AND a matching `completed` event with a recognizable composed-step outcome,
And no file produced by that action **MUST** remain in a `started`-only state.

**Scenario C — Composed step records failure when it fails (covers `#793`)**
Given a composed `software-dev` action begins dispatch,
When a composed step raises an error after `ProfileInvocationExecutor.invoke(...)` started the invocation,
Then the executor **MUST** close that invocation with a `failed` completion (where the existing API surface allows it),
And the resulting JSONL **MUST** show paired `started` and `failed` records.

**Scenario D — Contract action survives `profile_hint` (covers `#794`)**
Given a composed `software-dev` step calls `ProfileInvocationExecutor.invoke(profile_hint=<profile>, action_hint="specify")` (or `plan`/`tasks`/`implement`/`review`),
When the resulting `started` record and returned `InvocationPayload` are inspected,
Then the recorded action **MUST** be the contract action (`specify`/`plan`/`tasks`/`implement`/`review`),
Not the role-default verb (`analyze`/`audit`/etc.) of the resolved profile.

**Scenario E — Legacy `profile_hint`-only call paths are unchanged (regression guard for `#794`)**
Given an existing call site that supplies `profile_hint=<profile>` but no `action_hint` (e.g. `advise`, `ask`, `do`, router-backed paths),
When `ProfileInvocationExecutor.invoke(...)` runs,
Then the action **MUST** continue to be derived from the request via the existing `_derive_action_from_request(...)` flow,
And no behavioral change **MUST** be observable in those paths.

### Edge Cases

- **EDGE-001**: A composed `software-dev` action raises mid-step. Acceptance: the invocation is closed with `failed`; no orphan `started`-only file remains.
- **EDGE-002**: An action is **not** in the composition allow-list (e.g. a future non-composed `software-dev` action, or a different mission). Acceptance: legacy dispatch path is exercised exactly as today; no behavioral change.
- **EDGE-003**: Composition succeeds but run-state advancement helper raises. Acceptance: failure is surfaced in the existing `Decision` shape; the system does not silently re-enter legacy dispatch.
- **EDGE-004**: Two composed steps execute in the same action invocation. Acceptance: each `started` record gets its own matching `completed`/`failed` record; pairing is not order-dependent.
- **EDGE-005**: `profile_hint` is supplied but `action_hint` is the empty string. Acceptance: treat as if `action_hint` was not supplied (fall back to derivation), matching legacy behavior.
- **EDGE-006**: Existing fixed `tasks` guard semantics — the live runtime collapses to the public `tasks` step but still keys the guard branch by `legacy_step_id`. Acceptance: guard branching is preserved verbatim; this mission **MUST NOT** regress the P0 fix already on `main`.

### Domain Language

| Term | Canonical meaning in this mission | Avoid |
|------|-----------------------------------|-------|
| Composition dispatch | The `StepContractExecutor`-driven path that resolves a public step contract and invokes one or more `ProfileInvocationExecutor.invoke(...)` calls. | "DAG dispatch", "executor run". |
| Legacy DAG dispatch | The `runtime_next_step(...)`-based direct dispatch route used before `#501`. | "fallback", "old dispatch" — these are imprecise. |
| Single-dispatch | The property that, for composition-backed actions, exactly one of {composition path, legacy DAG path} executes per action attempt. | "non-redundant", "deduplicated". |
| Started-only invocation | A `.kittify/events/profile-invocations/*.jsonl` file with one or more `started` records and no matching `completed`/`failed` record. | "orphan invocation" without explanation. |
| Contract action | The action key from a step contract: `specify`, `plan`, `tasks`, `implement`, `review`. | Profile role-default verbs (`analyze`, `audit`). |
| Role-default verb | The action key derived by `_derive_action_from_request(...)` from a profile's role. | "Default action" without context. |

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Composition-backed `software-dev` actions (`specify`, `plan`, `tasks`, `implement`, `review`) MUST be single-dispatch: on a successful composition, the legacy DAG dispatch handler that calls `runtime_next_step(...)` for the same action MUST NOT execute. | Approved |
| FR-002 | Composition-backed `software-dev` actions MUST still advance run-state and lane/status events through to the next public step. | Approved |
| FR-003 | The fixed `tasks` guard semantics MUST be preserved exactly: `tasks_outline` requires `tasks.md`; `tasks_packages` requires `tasks.md` plus ≥1 `tasks/WP*.md`; `tasks_finalize` and the public `tasks` step require the terminal `dependencies:` state. | Approved |
| FR-004 | The mission MUST NOT modify `mission-runtime.yaml` files unless a regression test demonstrates no other correct implementation. | Approved |
| FR-005 | The public `Decision` shape returned by the runtime bridge MUST remain stable. | Approved |
| FR-006 | After a composed `software-dev` action runs (success path), every invocation JSONL file produced by that run MUST contain at least one `started` event AND a matching `completed` event. | Approved |
| FR-007 | If a composed step fails after `ProfileInvocationExecutor.invoke(...)` started its invocation, the executor MUST close that invocation with a `failed` completion via the existing `complete_invocation(...)` API. | Approved |
| FR-008 | `StepContractExecutor` MUST close every invocation it starts using `ProfileInvocationExecutor.complete_invocation(...)` or an equivalent existing executor API; no direct writes to `.kittify/events/profile-invocations/*.jsonl` from outside the writer/executor APIs. | Approved |
| FR-009 | `ProfileInvocationExecutor.invoke(...)` MUST accept an optional keyword-only `action_hint: str | None = None` parameter. | Approved |
| FR-010 | When `profile_hint` and a non-empty `action_hint` are both supplied, `ProfileInvocationExecutor.invoke(...)` MUST resolve the profile from `profile_hint` AND record the supplied `action_hint` as the action in the `started` record and the returned `InvocationPayload`. | Approved |
| FR-011 | When `profile_hint` is supplied and `action_hint` is `None` or empty, `ProfileInvocationExecutor.invoke(...)` MUST derive the action via the existing `_derive_action_from_request(...)` flow (legacy fallback). | Approved |
| FR-012 | Existing `advise`, `ask`, `do`, and router-backed call sites of `ProfileInvocationExecutor.invoke(...)` MUST NOT regress: their action recording behavior MUST remain identical to current main. | Approved |
| FR-013 | Governance context assembly MUST use the contract action when one is supplied via `action_hint`. | Approved |
| FR-014 | `StepContractExecutor.execute(...)` MUST pass `action_hint=selected_contract.action` on every `ProfileInvocationExecutor.invoke(...)` call it makes for a composed contract step. | Approved |
| FR-015 | Regression tests MUST assert the negative condition for FR-001 (legacy dispatch handler is not entered after composition success), not merely that `StepContractExecutor.execute(...)` was called. | Approved |
| FR-016 | End-to-end regression coverage MUST verify FR-006/FR-007 by reading the post-run JSONL files and asserting paired `started`+`completed` (or `started`+`failed`) records. | Approved |
| FR-017 | New tests MUST cover both `profile_hint + explicit action_hint` and the legacy `profile_hint`-only fallback paths for FR-009 through FR-013. | Approved |

### Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | The minimum focused test command (`uv run --python 3.13 --extra test python -m pytest tests/specify_cli/next/test_runtime_bridge_composition.py tests/specify_cli/mission_step_contracts/test_software_dev_composition.py tests/specify_cli/invocation/test_invocation_e2e.py tests/specify_cli/invocation/test_writer.py`) MUST pass on the merged result. | Approved |
| NFR-002 | `uv run --python 3.13 python -m ruff check` MUST pass on every touched source and test file. | Approved |
| NFR-003 | `uv run --python 3.13 python -m mypy --strict` MUST pass on `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/mission_step_contracts/executor.py`, and `src/specify_cli/invocation/executor.py`. | Approved |
| NFR-004 | Test coverage for new code paths in this tranche MUST meet or exceed 90% of changed lines (charter policy: ≥90% for new code). | Approved |
| NFR-005 | The implementation MUST NOT add a second mission runner; advancement logic added for FR-002 MUST be a shared helper extracted from the existing path or a composition-specific advancement function reusing the same primitives. | Approved |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Edits MUST be limited to the `spec-kitty` repo at `/Users/robert/spec-kitty-dev/786-793-794-phase6-stabilization/spec-kitty`. The sibling `spec-kitty-events` and `spec-kitty-runtime` checkouts MUST NOT be edited. | Approved |
| C-002 | The mission MUST NOT touch `src/spec_kitty_events/` in `spec-kitty` and MUST NOT modify the `spec-kitty-events` repo unless a proven cross-repo contract break is identified and explicitly approved by the user. | Approved |
| C-003 | The mission MUST NOT touch `.kittify/charter/`. | Approved |
| C-004 | The mission MUST NOT reopen Phase 4, Phase 5, `spec-kitty explain`, or retrospective work. | Approved |
| C-005 | `StepContractExecutor` MUST remain a composer: it MUST NOT execute shell commands, spawn an LLM, or pretend command steps ran. | Approved |
| C-006 | `ProfileInvocationExecutor` MUST remain the single invocation primitive for governance context, trail writing, and glossary checks. | Approved |
| C-007 | The local JSONL invocation trail MUST remain local-first (no remote sync added by this tranche). | Approved |
| C-008 | The mission MUST land in the implementation order WP01 → WP02 → WP03 (i.e., `#786` first, `#794` before or alongside `#793`). | Approved |
| C-009 | The mission MUST NOT start `#505` custom mission loading; that work is explicitly out of scope. | Approved |
| C-010 | The mission MUST NOT reopen the glossary-planning findings or the stale charter branch findings called out as resolved in `start-here.md`. | Approved |
| C-011 | The merge MUST add tracker comments to GitHub issues `#468`, `#786`, `#793`, `#794`, and `#505` reflecting the merge outcome and any change in their status or ordering. | Approved |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | After this tranche merges, on `main` at the merged HEAD, no composed `software-dev` action (`specify`, `plan`, `tasks`, `implement`, `review`) results in the legacy DAG dispatch handler executing for that same action — verified by an automated regression test that asserts the negative condition. |
| SC-002 | After any composed `software-dev` action run on `main` at the merged HEAD, 100% of invocation JSONL files produced by that action are closed (each contains both a `started` record and a matching `completed` or `failed` record) — verified by an end-to-end regression test that reads the post-run files. |
| SC-003 | After this tranche merges, every composed `software-dev` action's `started` event and returned payload records the contract action (`specify`/`plan`/`tasks`/`implement`/`review`) when `action_hint` is supplied, and the role-default verb when only `profile_hint` is supplied — verified by paired pytest cases. |
| SC-004 | The minimum focused pytest command from `start-here.md` passes with zero failures and zero errors on the merge result. |
| SC-005 | `ruff check` and `mypy --strict` both pass on every touched source file (and on the recommended file list in `start-here.md`). |
| SC-006 | The `#505` custom mission loader is no longer blocked by composition-layer credibility; the next workspace can begin `#505` without rebuilding any of these three seams. |
| SC-007 | Tracker comments are posted on `#468`, `#786`, `#793`, `#794`, and `#505` reflecting the merge outcome and any status / ordering change. |

## Key Entities

- **Step contract** — a YAML manifest under `src/doctrine/mission_step_contracts/shipped/<action>.step-contract.yaml` describing the composed steps for a public action; consumed by `StepContractExecutor`.
- **`StepContractExecutor`** — the composer that resolves a step contract and invokes `ProfileInvocationExecutor.invoke(...)` per composed step. Stays a composer (C-005).
- **`ProfileInvocationExecutor`** — the single invocation primitive (C-006). Owns governance context assembly, trail writing, and glossary checks. Owns `invoke(...)` and `complete_invocation(...)`.
- **Invocation JSONL** — the local-first trail under `.kittify/events/profile-invocations/<invocation>.jsonl`. Each invocation must have a `started` record paired with a `completed` or `failed` record (FR-006/FR-007).
- **Runtime bridge** — `src/specify_cli/next/runtime_bridge.py`; the seam that decides between composition dispatch and legacy DAG dispatch. Owns the single-dispatch invariant (FR-001).
- **`Decision`** — the runtime bridge's public return shape; MUST remain stable (FR-005).
- **Action keys** — the public `software-dev` actions: `specify`, `plan`, `tasks`, `implement`, `review`. The `tasks` action is the live collapsed step that internally branches on `legacy_step_id` for the fixed guard (FR-003).

## Assumptions

- The `mission-runtime.yaml` files for `software-dev` (under `src/specify_cli/missions/` and `src/doctrine/missions/`) do not need edits; the fix is in `runtime_bridge.py` and `executor.py` (informed by `start-here.md` "Likely implementation direction" notes; FR-004).
- `ProfileInvocationExecutor.complete_invocation(...)` already exists and supports an outcome value compatible with composed-step completion semantics (informed by `start-here.md` "Important design note"). Concrete outcome value will be verified during plan and recorded in tests/comments.
- Existing `tests/specify_cli/next/test_runtime_bridge_composition.py` and `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` already provide the scaffolding to extend; new tests will be added alongside.
- `spec-kitty-runtime` is available in the local environment (or installable from the sibling checkout); environment-only import failures will be fixed at the environment layer per `start-here.md`, not patched around in source.
- "Completion does not imply the host LLM did the requested generation" — the composed invocation is a governance-context/trail unit. The implementation will use an outcome value matching current trail semantics and will document this in tests or code comments (per `start-here.md` design note for `#793`).

## Out of Scope

- `#505` custom mission loader (explicitly C-009).
- `#787` `charter context` compact mode regression.
- `#504` / `#502` research/documentation mission rewrites.
- `#506`–`#511` retrospective contract and lifecycle work.
- `#469` Phase 7 hardening.
- Any change to `spec-kitty-events` or `spec-kitty-runtime` repos (C-001/C-002).
- Any change under `src/spec_kitty_events/` or `.kittify/charter/` (C-002/C-003).
- Glossary-planning re-litigation; stale charter branch re-litigation (C-010).
- `spec-kitty explain`; Phase 4 / Phase 5 reopen (C-004).

## Dependencies

- **Upstream** — PR `#795` merged (composition rewrite live). Confirmed by ground truth: `origin/main` at `16c29cce285d231ce36085294305b331b332b1d1` on 2026-04-25.
- **Upstream** — `#501` `StepContractExecutor` composer over `ProfileInvocationExecutor`. Already on `main`.
- **Downstream** — `#505` custom mission loader is **blocked** until this tranche merges (C-009 explicitly defers it to the next workspace).
- **Tooling** — `uv` (Python 3.13), `pytest`, `ruff`, `mypy --strict`. Charter policy summary loaded at specify time confirms these are the supported tools.

## References

- `start-here.md` (workspace root) — the canonical brief for this tranche.
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/spec.md`, `plan.md`, `tasks.md`, `tasks/WP02-runtime-bridge-composition-dispatch.md` — context for the just-landed composition rewrite.
- `docs/trail-model.md` — invocation trail semantics.
- GitHub issues: [#786](https://github.com/Priivacy-ai/spec-kitty/issues/786), [#793](https://github.com/Priivacy-ai/spec-kitty/issues/793), [#794](https://github.com/Priivacy-ai/spec-kitty/issues/794), [#505](https://github.com/Priivacy-ai/spec-kitty/issues/505), [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468).
- Files to inspect first (per `start-here.md`):
  - `src/specify_cli/next/runtime_bridge.py`
  - `src/specify_cli/mission_step_contracts/executor.py`
  - `src/specify_cli/invocation/executor.py`
  - `src/specify_cli/invocation/writer.py`
  - `src/specify_cli/invocation/record.py`
  - `src/specify_cli/invocation/modes.py`
  - `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml`
  - `src/specify_cli/missions/software-dev/mission-runtime.yaml`
  - `src/doctrine/missions/software-dev/mission-runtime.yaml`
  - `tests/specify_cli/next/test_runtime_bridge_composition.py`
  - `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py`
  - `tests/specify_cli/invocation/test_invocation_e2e.py`
  - `tests/specify_cli/invocation/test_writer.py`
