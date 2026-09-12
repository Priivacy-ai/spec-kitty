---
divio_type: how-to
audience: software-engineer
updated: 2026-08-23
---

# Quickstart: Implement and Verify Issue #3235

Run from the repository root on `mission/durable-concurrent-review-cycle-records`.

## 1. Establish the red-first signal

Strengthen the issue-pinned test so it invokes the real reviewer command and independently reads both event history and committed evidence. Before the production fix, verify that disabling evidence commitment cannot remain green.

```bash
uv run python -m pytest tests/integration/test_review_durability_matrix.py::test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations tests/integration/test_review_durability_matrix.py::test_sc004_event_serialization_mutant_reports_missing_authoritative_event tests/integration/test_review_durability_matrix.py::test_sc004_evidence_commit_mutant_reports_missing_committed_evidence -n0 -q --tb=short
```

Do not weaken, skip, quarantine, or mark the reproduction expected-failure.

## 2. Develop the queue and recovery behavior

```bash
uv run python -m pytest tests/review/test_verdict_commit_queue.py tests/review/test_cycle.py -n0 -q --tb=short
uv run python -m pytest tests/integration/review/test_reject_from_in_review.py tests/specify_cli/cli/commands/agent/test_move_task_durability.py -n0 -q --tb=short
```

Confirm returned router failures, raised failures, timeouts, interruption, identical adoption, non-identical non-adoption, and `--no-auto-commit`.

## 3. Verify placement and topology behavior

```bash
uv run python -m pytest tests/integration/review/test_verdict_save_topologies.py tests/integration/review/test_reject_from_in_review.py -n0 -q --tb=short
```

For every claimed durable success, inspect the placement-selected ref rather than the primary working tree.

## 4. Run mutation controls

Run the production queue/event-serialization mutant and the fabricated evidence-commit mutant independently. The same acceptance oracle must fail for each mutant. Remove the mutation and verify green; never retry a flaky run to green.

## 5. Run quality and performance gates

```bash
uv run ruff check src/specify_cli/review src/specify_cli/cli/commands/agent tests/review tests/integration/review
uv run mypy --strict src/specify_cli/review/verdict_commit_queue.py src/specify_cli/review/cycle.py src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
SPEC_KITTY_RUN_PERFORMANCE=1 uv run python -m pytest tests/review/test_verdict_save_performance.py -n0 --benchmark-only
```

Require the repository's enforced `diff-coverage` job to run `diff-cover` against `origin/main` with `--fail-under=90` for every touched critical production path, and record its completed result. Require an uncontended median below 2 seconds in the existing performance harness. Run all three exact issue-pinned production/mutant nodes natively on Linux, macOS, and Windows and record successful completed job links; a pending hosted run is not acceptance evidence.

## 6. Acceptance evidence

Record:

- at least 50 synchronized rounds with two persistent `spawn` processes;
- each pair's two-success or success-plus-explicit-refusal classification;
- event references and `git show` evidence from governed refs;
- both independently red mutation controls;
- retry adoption of the retained evidence path;
- topology matrix, native OS, performance, lint, type, and coverage results.
