# Quickstart: Implement and Verify the Pre-Review Gate Operator Flow

## Preconditions

```bash
cd /var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260823-140043-cnaxTE/spec-kitty
git branch --show-current
./.venv/bin/python --version
./.venv/bin/python -m pytest --version
```

Expected branch: `fix/pre-review-gate-operator-flow`. Do not implement on `main` or in the coordination husk.

Before any implementation commit, verify GitHub issue #2573 is assigned to the project Human-in-Charge. If assignment cannot be completed, stop WP01.

## Red-first sequence

Each implementation WP must commit its own failing-first acceptance test before its production commits, prove that test RED on the WP's `planning_base_branch`, and prove it GREEN on the final WP commit.

1. In WP01, add exact policy tests for:
   - `tests/architectural` -> `oversized`;
   - `tests/architectural` plus another target -> `oversized`;
   - `./tests/architectural/` normalizes to the same rule;
   - `tests/architectural/test_layer_rules.py` -> `unknown`;
   - target order/duplicates do not change the target-only policy identity;
   - the pinned `("tests/architectural",)` identity is `budget-v1:sha256:10c1e7475c72e48b83e4910e24437646d6ecd55052ca9a3a4f413b17153946fe` in-process and in a fresh process with a different `PYTHONHASHSEED`;
   - a broad suite expressed only in a declared command stays `unknown`;
   - no runtime mutation API exists.

2. In WP02, commit failing engine/refusal tests before changing the engine or verdict model.

3. In WP03, extend the exact public-entry observability test, parameterized over both the explicit override and active registered-handler routes, so an injected clock proves assessment-before-launch, start within 1 second, heartbeat gaps no greater than 30 seconds, and no heartbeat after terminal output. Confirm these tests are still red on the approved WP02 base before changing registry/CLI code.

4. Add public-entry tests for:
   - oversized refusal within 2 seconds, no launch, lane unchanged;
   - unknown warning followed by normal execution;
   - unknown timeout candidate in human output;
   - the same timeout as one final JSON document with required fields.

Run and record each red slice in its owning WP before that WP's production edit; do not defer all red evidence to the end:

```bash
./.venv/bin/python -m pytest \
  tests/review/test_gate_budget.py \
  tests/review/test_pre_review_gate_engine.py \
  tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py \
  -q
```

Record the expected failures and the separate red-test commit for review.

## Implementation order

1. Add immutable types and classifier in `src/specify_cli/review/gate_budget.py`.
2. Assess both derived and override scopes in `pre_review_gate.py` before launch and emit `ScopeAssessed` before either path starts a process.
3. Add `SCOPE_OVERSIZED` plus `NOT_STARTED` and update canonical terminal aggregation.
4. Add the optional typed status observer to `TransitionGateContext`, delegate it through the registered handler, and adapt runner elapsed callbacks into `Heartbeat` events.
5. Pass the same observer through the explicit-override path; construct it only for human mode in `tasks_move_task.py`.
6. Add unknown-timeout classification-candidate guidance.

Do not edit `.github/workflows`, ingest timing logs, add a metadata writer, or introduce asynchronous review state.

## Targeted green verification

```bash
./.venv/bin/python -m pytest tests/review/test_gate_budget.py -q
./.venv/bin/python -m pytest tests/review/test_pre_review_gate_engine.py -q
./.venv/bin/python -m pytest tests/review/test_pre_review_gate_integration.py -q
./.venv/bin/python -m pytest \
  tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py \
  -q
```

## Compatibility verification

Run the existing gate and command slices that own landed #2573 behavior:

```bash
./.venv/bin/python -m pytest \
  tests/review/test_scope_source.py \
  tests/review/test_baseline_head_parity.py \
  tests/review/test_pre_review_gate_source_mismatch.py \
  tests/sync/test_daemon_sync_disable_env.py \
  tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py \
  -q
```

Assertions must cover:

- explicit skip before workspace/process work;
- disable precedence: `SPEC_KITTY_SYNC_DISABLE`, then `SPEC_KITTY_SYNC_MINIMAL_IMPORT`;
- human and JSON collisions for skip+blocking, skip+both disables, and both disables without skip;
- explicit daemon-management exception;
- warn-by-default and configured block;
- timeout/cancel no-transition and byproduct restoration;
- one final JSON document.

Also add a POSIX real-CLI test that confirms candidate-head validation has started, sends `os.kill(parent_pid, signal.SIGKILL)` to the parent PID only, and independently reads lane/event state before bounded teardown to prove no transition was appended. Do not assert orphan cleanup.

## Cross-platform interruption evidence

Locate the current process-tree tests before running the narrow nodes:

```bash
rg -n "taskkill|process tree|TIMED_OUT|CANCELLED|_terminate_and_reap" tests/review
```

Then run the exact POSIX real-process and Windows contract nodes named by that census. Mark the deterministic Windows contract node `@pytest.mark.windows_ci` so the existing `ci-windows` workflow discovers it, and record the actual job result (or evidence-backed absence of the job) without changing CI. Do not claim cleanup of grandchildren orphaned by uncatchable parent `SIGKILL`; verify only lane/event integrity for that case.

## Manual contract probes

Human oversized refusal should resemble:

```text
Pre-review gate refused: scope tests/architectural is classified oversized
for the interactive transition budget. The work package remains in its prior lane.
Choose a bounded pre_review_test_scope or rerun with --skip-pre-review-gate.
```

Unknown timeout JSON must parse once and contain:

```json
{
  "result": "error",
  "transition_applied": false,
  "pre_review_gate": {
    "outcome": "timed_out",
    "budget_classification": "unknown",
    "scope_identity": "...",
    "test_targets": ["..."],
    "effective_budget_seconds": 300,
    "observed_elapsed_seconds": 300.0,
    "classification_candidate": true
  }
}
```

## Quality and closeout

```bash
./.venv/bin/ruff check \
  src/specify_cli/review/gate_budget.py \
  src/specify_cli/review/gate_registry.py \
  src/specify_cli/review/pre_review_gate.py \
  src/specify_cli/review/verdict_aggregation.py \
  src/specify_cli/cli/commands/agent/tasks_move_task.py \
  tests/review/test_gate_budget.py \
  tests/review/test_pre_review_gate_engine.py \
  tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
```

Also run strict mypy on every touched production module and review every new public enum, dataclass, protocol, and function for a docstring.

Before accepting the Mission:

- complete the FR-001–FR-010 traceability matrix;
- re-evaluate issue #2573 against live behavior;
- keep async execution deferred;
- audit that each **operational** unknown-budget timeout was appended immediately at observation with `spec-kitty agent tracer-append --category approach`, including `provenance: operational`, identity, targets, configured budget, observed elapsed time, and environment context; never enqueue synthetic timeout fixtures;
- create `retrospective-handoff.md` inventorying those entries or explicit absence and requiring canonical post-merge `retrospective.yaml` to record an owner, explicit no action, or `no candidates observed`; use `spec-kitty retrospect create --mission pre-review-gate-operator-flow-01M0Q86H --json` only as the recovery command if automatic merge/close capture did not produce it;
- if #3127 is still open, record `waiting_upstream` plus the executable resume sequence. After it merges, fetch/rebase onto the resulting `main` and rerun required checks before marking #2573 release-ready.
