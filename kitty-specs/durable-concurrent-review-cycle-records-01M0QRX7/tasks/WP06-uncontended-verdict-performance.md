---
work_package_id: WP06
title: Uncontended Verdict Performance
dependencies:
- WP04
requirement_refs:
- FR-001
- FR-004
- NFR-003
- NFR-006
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: ffc5418aa88ed89c3a7423f8a177ab127c093f7f
created_at: '2026-08-24T07:36:07.765198+00:00'
subtasks:
- T026
- T027
- T028
phase: Phase 4 - Performance verification
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/review/
create_intent:
- tests/review/test_verdict_save_performance.py
execution_mode: code_change
model: ''
owned_files:
- tests/review/test_verdict_save_performance.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP06 – Uncontended Verdict Performance

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` with `/ad-hoc-profile-load`; apply its pytest, performance, type-safety, and implementation boundaries before proceeding.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Inspect `review_ref` through `spec-kitty agent tasks status --mission 01M0QRX7`. Resolve all feedback and record chronological evidence with `spec-kitty agent tasks add-history`; do not directly edit this prompt from the lane.

## Objectives & Success Criteria

Add a focused statistical performance test proving a single uncontended real verdict save—including queue acquisition, evidence write/commit/read-back, and event persistence—meets the under-two-second requirement. Fixture construction, repository seeding, and per-sample reset must not contaminate the timed callable.

Completion requires:

- one new performance test module and no production edits;
- a real reviewer command, not direct cycle writer or event-only helper;
- repository-standard performance markers and `pytest-benchmark` usage;
- deterministic setup/reset outside measurement;
- median below two seconds in the existing performance harness;
- marker selection verified by collect-only and actual benchmark invocation;
- environment/baseline evidence recorded through the event-mediated history command.

## Context & Constraints

Dependency: WP04. Read NFR-003/SC-006, plan Verification Strategy, current `.github/workflows/performance.yml`, existing benchmark conventions, and the current one-shot direct writer timing test in `tests/review/test_cycle.py`.

Do not edit the existing performance workflow in this WP. Do not replace statistical evidence with a single `perf_counter` assertion. Do not time subprocess/environment setup that a normal warmed CLI path would not repeat, but do include every durability operation promised by the command.

## Branch Strategy

- **Planning base**: `mission/durable-concurrent-review-cycle-records`
- **Merge target**: `mission/durable-concurrent-review-cycle-records`
- **Dependency**: WP04.
- **Execution**: `spec-kitty agent action implement WP06 --agent codex --mission 01M0QRX7`; Spec Kitty selects the lane worktree from `lanes.json`.

## Subtasks & Detailed Guidance

### T026 – Build the real-command benchmark fixture

**Purpose**: Make measurement representative without including unrelated setup noise.

**Steps**:

1. Create `tests/review/test_verdict_save_performance.py`.
2. Build a real temporary Git repository and mission using existing production-delegating factories.
3. Seed a WP in the correct review state outside the timed callable.
4. Prepare real reviewer input and automatic commit mode.
5. Define reset/setup needed for repeated samples outside benchmark timing.
6. Ensure every sample has a valid fresh transition/evidence target without measuring fixture recreation.
7. Keep helper functions module-local and portable.

**Validation**: a fixture-only smoke assertion confirms the command can run once and returns the expected durable fields before benchmark sampling.

### T027 – Measure the complete uncontended operation

**Purpose**: Measure the user-visible durability promise, not a subsystem proxy.

**Steps**:

1. Use current `@pytest.mark.performance` and `@pytest.mark.benchmark(group="review")` conventions.
2. Use `benchmark.pedantic` or repository-equivalent statistical API.
3. Timed callable invokes the real root reviewer command.
4. Include queue acquisition/release, evidence materialization, placement routing, Git commit, governed-ref read-back, and authoritative event persistence.
5. Assert command success and durability outside/around the benchmark in a way that cannot optimize away correctness.
6. Report median and distribution; nominal median must be below 2 seconds.
7. If repository policy retains a sanity ceiling, keep it loose and secondary to the statistical baseline.

Do not benchmark `create_rejected_review_cycle` directly or the event append alone.

### T028 – Verify selection and record baseline

**Purpose**: Ensure CI actually discovers the benchmark and future comparisons are meaningful.

**Steps**:

1. Run collect-only with the exact marker/path used by the performance workflow.
2. Confirm the new node appears exactly once and is not deselected.
3. Run the benchmark under `SPEC_KITTY_RUN_PERFORMANCE=1`.
4. Record Python version, OS, Git version, sample count, median, and relevant variance through `spec-kitty agent tasks add-history WP06 --mission 01M0QRX7 --agent <agent> --note "..."`; do not directly edit the WP prompt from the implementation lane.
5. Record any pre-existing performance harness failure separately; do not retry-to-green.
6. If the current workflow selection cannot discover the new path, report the required workflow change for WP07 rather than editing outside ownership.

## Test Strategy

```bash
SPEC_KITTY_RUN_PERFORMANCE=1 uv run python -m pytest tests/review/test_verdict_save_performance.py -n0 --benchmark-only
uv run python -m pytest tests/review/test_verdict_save_performance.py --collect-only -q
uv run ruff check tests/review/test_verdict_save_performance.py
```

## Measurement Protocol

Use a protocol that lets a reviewer distinguish product performance from fixture noise:

1. Warm the Python/test environment before collecting benchmark samples.
2. Construct the repository, mission metadata, and static fixtures once outside the timed callable.
3. Prepare a valid fresh WP transition for each measured round outside timing.
4. Start timing immediately before the real reviewer command enters production orchestration.
5. Stop only after the command has returned and its event/evidence durability work is complete.
6. Validate the returned evidence pointer against the committed destination outside the timer for every sample or a representative validated sample set consistent with benchmark policy.
7. Use enough rounds/iterations for the harness to report a stable median and variance.
8. Do not discard slow samples merely because Git housekeeping occurred; report distribution honestly.
9. Keep automatic Git maintenance disabled only if the repository's benchmark policy already does so consistently.
10. Record whether filesystem caches are warm and whether antivirus/indexing could affect Windows evidence.

The event-mediated history note should include a compact record:

```text
OS / architecture:
Python / Git:
pytest-benchmark version:
samples / rounds:
median / min / max / standard deviation:
requirement (<2s median): PASS|FAIL
collect-only selector result:
```

### Correctness guard around timing

Every measured command must operate on a valid state transition. A fast failure, early refusal, local-only result, missing event, or absent committed artifact is not a performance sample. Assert `durable`, the exact event correlation, and governed-ref evidence before accepting the benchmark result. If reset cannot guarantee independent valid samples, use single-round pedantic invocations with external fixture reset rather than weakening correctness.

### Baseline interpretation

- Treat median as the SC-006 signal.
- Record variance and outliers instead of deleting them silently.
- A local pass is provisional until the repository performance environment runs.
- A regression versus stored baseline remains actionable even when absolute median is below two seconds.
- A pre-existing harness defect is reported separately and never converted to a skip.

## Risks & Mitigations

- **Fixture-dominated timing**: keep repo creation/seeding/reset outside timed call.
- **Vacuous speed**: assert durable event and committed evidence, not exit code alone.
- **Noisy local machine**: use statistical results and record environment.
- **Undiscovered marker**: prove collect-only selection.
- **Cold subprocess overhead ambiguity**: follow existing harness policy and document invocation model.

## Review Guidance

Reject if the benchmark times a helper rather than the command, omits evidence read-back/event persistence, includes repository creation, or relies only on one-shot timing. Verify the exact node is discoverable by the intended workflow.

## Definition of Done

- T026–T028 event-marked done.
- New benchmark passes and median is below two seconds in the harness.
- Collect-only proves selection.
- Ruff passes.
- Event-mediated WP history records reproducible environment and results.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP06 --to for_review --mission 01M0QRX7` when ready.
- 2026-08-24T07:56:02Z – codex – shell_pid=98465 – Performance baseline (SC-006/NFR-003): macOS 26.5.2 (Darwin 25.5.0), arm64 Apple M3 Ultra; CPython 3.11.15; Git 2.50.1 (Apple Git-155); pytest-benchmark 5.2.3. Warm filesystem/Python caches; Spotlight/indexing not disabled. 5 measured rounds x 1 iteration plus 1 untimed warmup. Median 0.575518s; min 0.570233s; max 0.578115s; mean 0.575258s; standard deviation 0.003050s; IQR 0.003435s. Requirement (<2s median): PASS. Workflow-equivalent selector: exactly 1 benchmark selected, 1 smoke test deselected. Full module: 2 passed; 95% statement coverage. Downstream queue/cycle/command suite: 85 passed. Causal guards included exact committed-byte/event correlation, queue/lock-order tests, and typed failure controls. Pre-existing baseline record is harness issue <gate-coverage-junit>: no JUnit XML artifact at base 4772a899d5f0, not a product-test failure; tracked by https://github.com/Priivacy-ai/spec-kitty/issues/2929.
- 2026-08-24T07:59:31Z – codex – shell_pid=98465 – Review handoff correction: final implementation commit is a620efa10fc77dfda0dbc9a5737e236099459ada (amended from 404f9fedc before reviewer dispatch). The amendment makes the seeded prior rejection event reuse the real committed cycle's canonical ReviewResult instead of a synthetic pointer; measured approval behavior is unchanged. Post-amend benchmark: 5 rounds, median 0.683200s, min 0.672851s, max 0.717756s, mean 0.689233s, standard deviation 0.017902s; <2s PASS. Ruff and strict mypy remain clean.
