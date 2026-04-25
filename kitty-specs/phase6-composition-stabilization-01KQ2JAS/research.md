# Research: Phase 6 Composition Stabilization

**Mission**: phase6-composition-stabilization-01KQ2JAS
**Created**: 2026-04-25
**Method**: Read the relevant source and tests under `/Users/robert/spec-kitty-dev/786-793-794-phase6-stabilization/spec-kitty/`. Treat existing behavior as ground truth. No new external dependencies.

## R1 — Where does the legacy fall-through happen? (#786)

### Decision
The fall-through is in `src/specify_cli/next/runtime_bridge.py::decide_next_via_runtime(...)`. After `_dispatch_via_composition(...)` returns `None` on the success path, control falls through to `runtime_next_step(...)`, which both advances run state AND executes the legacy DAG action handler.

### Evidence
- `_dispatch_via_composition(...)` at `runtime_bridge.py:393–486`:
  - calls `StepContractExecutor(repo_root).execute(context)` at line 441;
  - calls `_check_composed_action_guard(...)` at lines 480–482;
  - **returns `None` on success at line 485**.
- `decide_next_via_runtime(...)` at `runtime_bridge.py:981`:
  - the call to `_dispatch_via_composition` happens above;
  - on `None`, control falls through to `runtime_next_step(...)` at lines 986–991.

### Rationale for the fix
Make `_dispatch_via_composition(...)` return a `Decision` (not `None`) on success, constructed from a new helper that advances run-state without running the legacy DAG action handler. Treat success as a terminating dispatch in `decide_next_via_runtime(...)`. This is the option the brief recommends ("add a composition-specific advancement path"), and it minimizes changes to the legacy non-composed code path.

### Alternatives considered
- **Always-return-tuple**: change `_dispatch_via_composition(...)` to `tuple[bool, Decision | None]`. Rejected because it changes a function-private contract that other callers may depend on (more blast radius for the same outcome).
- **Edit `mission-runtime.yaml`** to remove the legacy step. Rejected by FR-004 unless tests prove there is no other correct implementation; tests will pass with the helper approach, so this option is not exercised.

## R2 — Where is the `tasks` guard? (#786 sub-question)

### Decision
The fixed `tasks` guard is keyed by `legacy_step_id` and is invoked from `_check_composed_action_guard(...)` AFTER composition runs (already on `main`). Keep it exactly where it is.

### Evidence
- `runtime_bridge.py` `_check_composed_action_guard(...)` is invoked at lines 480–482, AFTER the composer runs. The branching by `legacy_step_id` for `tasks_outline` / `tasks_packages` / `tasks_finalize` / `tasks` is the P0 fix already on `main` (per `start-here.md`).
- The guard tests already cover the three terminal states:
  - `tasks_outline` → `tasks.md`;
  - `tasks_packages` → `tasks.md` + ≥1 `tasks/WP*.md`;
  - `tasks_finalize` / `tasks` → terminal `dependencies:` block.

### Rationale
The advancement helper introduced for FR-001 must run AFTER `_check_composed_action_guard(...)`. We do not move or modify the guard.

## R3 — `complete_invocation(...)` outcome values (#793)

### Decision
Use `outcome="done"` on success, `outcome="failed"` on exception. Do not introduce a new outcome value.

### Evidence
- `src/specify_cli/invocation/record.py:34`: `outcome: Literal["done", "failed", "abandoned"] | None`.
- `src/specify_cli/invocation/executor.py:218–225`: `complete_invocation(...)` accepts that same set.
- `"abandoned"` is reserved for user-initiated cancellation; this mission does not generate that case.

### Rationale
- `start-here.md` explicitly says: *"Use an outcome value that matches current trail semantics, and document the reasoning in tests or comments if needed."*
- Adding a new outcome value would be unprincipled scope creep and would break the JSONL contract for downstream consumers.
- A one-line code comment at the close site captures the "completion does not imply the host LLM did the requested generation" semantic.

### Alternatives considered
- **Invent a new outcome `"composed"`**: rejected (scope creep, breaks `Literal` contract).
- **Skip closing on success**: rejected (re-introduces the bug).
- **Always `"abandoned"` for composed steps**: rejected (semantic mismatch — abandonment is not what happened).

## R4 — `invoke(...)` extension shape (#794)

### Decision
Add `*, action_hint: str | None = None` (keyword-only). Use it inside the `if profile_hint is not None:` branch; if truthy, set `action = action_hint`; otherwise call `_derive_action_from_request(...)` as today. The `else` (router-backed) branch is untouched.

### Evidence
- Current signature at `src/specify_cli/invocation/executor.py:113–119`:
  ```python
  def invoke(
      self,
      request_text: str,
      profile_hint: str | None = None,
      actor: str = "unknown",
      mode_of_work: ModeOfWork | None = None,
  ) -> InvocationPayload:
  ```
- The action derivation at line 132 only happens inside `if profile_hint is not None:`. The router branch at lines 134–139 already sets `action = result.action` from the router decision and does not call the deriver — so the new kwarg has no semantic interaction with the router branch.
- The action is stored in `InvocationRecord.action` (line 185) and written to the started JSONL via `write_started(record)` (line 194). Governance context assembly reads from the same record.

### Rationale
- Keyword-only avoids any positional drift in existing callers.
- Truthiness check (`if action_hint:`) treats empty string as legacy-fallback (EDGE-005 in spec).
- Limiting the new behavior to the `profile_hint`-branch ensures the router-backed callers (advise/ask/do) cannot regress (FR-012).

### Alternatives considered
- **Make `action_hint` positional after `profile_hint`**: rejected (positional drift risk).
- **Apply `action_hint` in the router branch too**: rejected (out of spec; router decisions own their action key by design).
- **Replace `_derive_action_from_request(...)` entirely**: rejected (legacy behavior is required for non-composition callers).

## R5 — Where to close the invocation lifecycle (#793 sub-question)

### Decision
Close at the call site in `StepContractExecutor.execute(...)`. Wrap the per-step `invoke(...)` + composed-step body in a try/except/else; call `complete_invocation(payload.invocation_id, outcome=...)` in both branches.

### Evidence
- `src/specify_cli/mission_step_contracts/executor.py:135–192` (`StepContractExecutor.execute(...)`):
  - `invoke(...)` is called at line 159; payloads are collected into `step_results`.
  - **No call to `complete_invocation(...)` follows**. No try/except around the call.
- `complete_invocation(...)` is the public method on `ProfileInvocationExecutor` and writes the second JSONL line via the existing writer; no new writer is needed.

### Rationale
- The composer is the closest scope that knows when a composed step has finished or raised. Closing here keeps lifecycle ownership at the same level as the start (FR-008).
- Using `complete_invocation(...)` keeps all writes inside the executor/writer boundary (C-006/C-007).
- Multi-step composed actions naturally pair each invocation independently (EDGE-004).

### Alternatives considered
- **Close in `runtime_bridge.py`**: rejected — the bridge does not know about per-step invocations and it would couple unrelated layers.
- **Close in `ProfileInvocationExecutor.invoke(...)` itself via context manager**: rejected — `invoke(...)` cannot know when the host-facing step is done; the composer is the right scope.

## R6 — Test surface (FR-015 / FR-016 / FR-017)

### Decision
Use the existing four test files; add new test functions; do not rename or split them.

### Evidence and Rationale
- `tests/specify_cli/next/test_runtime_bridge_composition.py` already covers `_dispatch_via_composition`, `_should_dispatch_via_composition`, `_check_composed_action_guard`. Adding negative-condition tests is a natural extension of existing scaffolding.
- `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` already loads the shipped `tasks` step contract and resolves the default profile; it is the right home for `action_hint` pass-through tests and lifecycle close tests on real composition flows.
- `tests/specify_cli/invocation/test_invocation_e2e.py` already verifies `started` + `complete_invocation` JSONL pairing for non-composed invocations; it is the right home for the new `action_hint` parametrized tests and for the success/failure pairing assertions seen by the executor.
- `tests/specify_cli/invocation/test_writer.py` is unit-level for the writer; it should remain untouched in this tranche unless the writer surface is changed (it is not).

## R7 — `spec-kitty-runtime` environment (per `start-here.md`)

### Decision
Confirm `spec-kitty-runtime` is installable from the sibling checkout if missing in the env. Do NOT patch around environment-only import failures in source.

### Rationale
`start-here.md` explicitly: *"If `spec-kitty-runtime` is missing in the environment, install it from the sibling checkout or the expected package source before running runtime bridge tests. Do not patch around an environment-only import failure."* The plan respects this; if a test session cannot import `spec_kitty_runtime`, fix the environment, not the code.

## Open Questions

None. All clarification points are resolved by the source inspection above plus the explicit guidance in `start-here.md`.
