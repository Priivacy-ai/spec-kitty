# Research: Observable Pre-Review Gate

**Date**: 2026-07-14

## Code-truth findings

### R-01 — The live residual is orchestration liveness

`_mt_run_pre_review_gate` in `src/specify_cli/cli/commands/agent/tasks_move_task.py` prints one human notice and then calls `_mt_pre_review_gate_verdict` synchronously. The underlying `run_scoped_tests_at_head` in `src/specify_cli/review/pre_review_gate.py` uses blocking `subprocess.run(..., timeout=300, capture_output=True)`. A long quiet test run therefore provides no continuing liveness.

### R-02 — One mutation currently occurs before the gate seam

The gate hook runs before `_mt_finalize_plan` and `_mt_execute`, but `_mt_gather_review_facts` can auto-commit dirty lane deliverables first. Review/arbiter persistence also exists in the general decision phase, although it is not expected for an ordinary `for_review` move. Meeting the zero-residue contract therefore requires an explicit ordered mutation map and moving applicable recovery writes after the gate, not merely wrapping the current call position.

### R-03 — Existing controls are already delivered

Commit `35f3a2206` delivered `--skip-pre-review-gate`, synchronization-disable environment handling, and the initial human notice. Focused current-base tests cover those paths. This Mission preserves them and adds only continuing default-path liveness and interruption evidence.

### R-04 — Gate verdict policy has one authority

`pre_review_gate.py` owns scope derivation, the scoped head run, JUnit parsing, baseline diff, and `GateVerdict`. Moving or duplicating that policy into the CLI would create drift. The CLI should only manage observation and output-mode policy around the existing call.

## Decision research

### D-01 — Canonical polling runner versus subprocess streaming

**Decision**: replace the canonical runner's blocking `subprocess.run` with one gate-owned polling process lifecycle and accept a presentation-only progress callback.

**Why**: heartbeats must not depend on pytest producing output, JSON stdout must remain singular, and only the gate runner has enough authority to terminate and reap its child on timeout or cancellation.

### D-02 — Timing testability

**Decision**: inject timing/waiting and progress collaborators into the private observation helper.

**Why**: acceptance requires a 30-second maximum interval and a 65-second scenario, but CI should not sleep for 65 real seconds. A fake clock/synchronization seam proves cadence deterministically and avoids retry-based flake masking.

### D-03 — Typed timeout and cancellation semantics

**Decision**: preserve timeout and catchable cancellation as typed canonical gate outcomes, terminate/reap the child in the runner, and map them to a nonzero pre-mutation command result. Do not claim rollback after uncatchable termination.

**Why**: no transition is authorized before the gate returns, so authoritative state should remain unchanged. SIGKILL cannot run cleanup; the append-only event log remains the recovery truth and can establish whether a transition event exists.

### D-05 — Dirty deliverables and phase ordering

**Decision**: compute prospective gate scope from committed differences plus relevant staged, unstaged, and untracked deliverables, then perform the existing deliverable auto-commit only after the gate permits progress.

**Why**: the current auto-commit precedes the gate and violates the zero-placement-commit timeout/cancellation contract. Simply moving it would otherwise hide dirty implementation files from target-branch diff scope.

### D-04 — JSON progress

**Decision**: emit no progress prose to stdout in JSON mode. Prefer a no-op progress sink; any additive final metadata must remain inside the single result document.

**Why**: stderr progress is technically separable but may still surprise automation. The minimum contract is safest: human mode gets live progress, machine mode gets a clean final document and structured outcome.

## Rejected scope expansions

- Universal CLI output/progress framework.
- Streaming or parsing pytest console output.
- Changing the 300-second gate timeout.
- Root/worktree resolution redesign.
- Synchronization authority changes.
- New persistence for cancellation or recovery.
