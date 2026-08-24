---
affected_files: []
cycle_number: 1
mission_slug: pre-review-gate-operator-flow-01M0Q86H
reproduction_command:
reviewed_at: '2026-08-23T17:41:14Z'
reviewer_agent: user
wp_id: WP03
---

## WP03 review findings

### 1. The exact-entry timing test does not observe the engine or lowest launch seam

`test_exact_entry_wires_typed_observer_with_ordered_human_progress` replaces
`evaluate_with_scope` with a fake that directly calls the observer with
preselected `0`, `30`, and `60` values. That proves the Rich renderer prints
events it is handed, but it cannot prove the T010/NFR-001/NFR-002 contract it
claims: scope assessment before the lowest launch seam, start within one
second, heartbeat deltas no greater than 30 seconds during an actual
greater-than-60-second controlled run, and no heartbeat after finalization.
If the production engine stopped adapting its runner callback, emitted the
assessment after launch, or emitted once more after terminal completion, this
exact public-entry test would still pass because its fake owns the entire event
sequence.

Remedy: keep the exact Typer invocation and both route parameters, but drive the
real `evaluate_with_scope`/observer adaptation under an injected monotonic
clock and lowest process-launch/wait seam. Record assessment, launch, heartbeat,
terminal-render, and any subsequent callback in one timeline. Assert assessment
precedes launch, start latency is <=1 second, every active heartbeat delta is
<=30 seconds for a run exceeding 60 seconds, and no callback/render occurs after
the final outcome. Preserve the separate RED-first commit and show that both
routes fail for missing observer wiring on the post-WP02 base.

### 2. The disable/daemon acceptance matrix is incomplete

T015, FR-004, SC-003, and SC-006 require separate proof for both canonical
disable variables, including no implicit daemon start and continued explicit
daemon management. The new exact-entry collision test only spies on workspace
resolution; it does not observe an implicit-daemon start seam. The existing
`tests/sync/test_daemon_sync_disable_env.py` tests both implicit suppression and
`force_explicit=True` only with `SPEC_KITTY_SYNC_DISABLE`; despite its docstring,
it never sets `SPEC_KITTY_SYNC_MINIMAL_IMPORT`.

Remedy: add parameterized evidence for each variable independently. For each,
prove the public review-submission disable path performs neither validation nor
implicit daemon startup, and separately prove explicit daemon management still
invokes the daemon-management path. Also retain the existing both-set test to
prove canonical `SPEC_KITTY_SYNC_DISABLE` precedence. If the daemon regression
file must be touched despite WP03's ownership list, coordinate that shared-file
change explicitly rather than silently expanding scope.

## Non-blocking evidence recorded during review

- RED commit `aacd9c793` independently fails all four dual-route observer/JSON
  cases; green commit `a3ee8efec` passes them without weakened assertions.
- Owned suites: 40 passed. Related skip/baseline/binding/orchestration/daemon
  suites: 48 passed. Engine/interpreter/source/parity suites: 120 passed.
- Ruff lint and strict mypy pass. `ruff format --check` reports the large
  `tasks_move_task.py` file as unformatted at both WP03 HEAD and dependency base,
  so that formatter result is inherited rather than a WP03 regression.
- `tests/review/test_pre_review_gate_integration.py` reports 7 failed, 15 passed,
  1 skipped at WP03 HEAD; the identical seven failures reproduce at dependency
  base `bc1846d2d` and are documented in open issue #3695.
- No tracer append was introduced for synthetic timeout fixtures.
