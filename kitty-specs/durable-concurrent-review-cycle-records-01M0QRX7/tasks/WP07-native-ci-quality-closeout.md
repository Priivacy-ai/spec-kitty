---
work_package_id: WP07
title: Native CI and Quality Closeout
dependencies:
- WP01
- WP05
- WP06
requirement_refs:
- C-003
- C-004
- FR-008
- NFR-001
- NFR-004
- NFR-005
- NFR-006
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: e7a19ba7f89afad7fe474dd4a643db6e9e141aaa
created_at: '2026-08-24T10:14:30.529976+00:00'
subtasks:
- T029
- T030
- T031
- T032
phase: Phase 5 - Platform and quality closeout
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent:
- .github/workflows/review-verdict-durability.yml
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/review-verdict-durability.yml
- .github/workflows/ci-quality.yml
- tests/architectural/_gate_coverage.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP07 – Native CI and Quality Closeout

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` and apply its Python, pytest, cross-platform, and quality-gate guidance before proceeding.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Inspect `review_ref` via `spec-kitty agent tasks status --mission 01M0QRX7`. Resolve every item and record evidence with `spec-kitty agent tasks add-history`; do not directly edit this prompt from the lane.

## Objectives & Success Criteria

Create and register a narrow native three-operating-system workflow for the exact issue-pinned production-path concurrency proof, then run and record the complete targeted quality suite. This package owns the workflow definition, the exact `ci-quality.yml` routing entries needed to make workflow-only changes exercise repository architecture checks, and its fail-closed architecture-model registration; product and feature-test corrections must return to their owning WPs through review rather than being patched across lane ownership.

Completion requires:

- a new workflow using current repository checkout, Python, uv/cache, and artifact conventions;
- native Ubuntu, macOS, and Windows jobs;
- the exact WP01 production concurrency node, two persistent `spawn` workers, at least 50 rounds, and `-n0`;
- no queue-only substitute, POSIX-only skip, quarantine, xfail, or retry-to-green;
- focused integration/unit tests, Ruff, strict mypy, and at least 90% changed-line coverage run and recorded;
- workflow syntax/selection validated locally where possible;
- external CI status and any pre-existing failure captured factually through event-mediated WP history.

## Context & Constraints

Dependencies: WP01, WP05, and WP06. Read NFR-001/NFR-004/NFR-005/NFR-006, plan cross-platform strategy, the exact WP01 node, `.github/workflows/ci-windows.yml`, `.github/workflows/ci-quality.yml`, and `.github/workflows/performance.yml`.

Current Windows discovery is marker-based and current stress is Linux-only; neither alone proves the required contract. The new workflow must invoke the exact baseline, event-mutant, and evidence-mutant node paths directly on all three OSes. Use Python 3.11 floor coverage where compatible with repository policy.

This WP cannot edit `kitty-specs/`, production modules, or feature tests. Its only existing-workflow ownership is the exact path-filter registration in `.github/workflows/ci-quality.yml`, and its only architecture-test ownership is `tests/architectural/_gate_coverage.py`, where the repository's fail-closed pytest-workflow allowlist must register the new workflow. Record evidence via `spec-kitty agent tasks add-history WP07 --mission 01M0QRX7` for mission-level tracer curation after lane integration.

## Branch Strategy

- **Planning base**: `mission/durable-concurrent-review-cycle-records`
- **Merge target**: `mission/durable-concurrent-review-cycle-records`
- **Dependencies**: WP01, WP05, WP06.
- **Execution**: `spec-kitty agent action implement WP07 --agent codex --mission 01M0QRX7`; use the finalized lane worktree selected from `lanes.json`.

## Subtasks & Detailed Guidance

### T029 – Add the native three-OS workflow

**Purpose**: Make cross-platform durability an executed gate.

**Steps**:

1. Create `.github/workflows/review-verdict-durability.yml`.
2. Add `.github/workflows/review-verdict-durability.yml` to both outer `pull_request.paths` and `push.paths`, plus the `core_misc` dorny filter, in `.github/workflows/ci-quality.yml`; this preserves the repository's two-layer architecture-check routing for workflow-only changes.
3. Register `review-verdict-durability.yml` in `tests/architectural/_gate_coverage.py::WORKFLOW_FILES`; do not weaken or bypass fail-closed workflow discovery.
4. Reuse current action versions, permissions, checkout depth, Python setup, uv install/cache, and dependency groups.
5. Define a bounded matrix for Ubuntu, macOS, and Windows.
6. Choose triggers consistent with P0 regression policy and avoid duplicate unbounded runs.
7. Set a realistic timeout based on persistent-worker stress.
8. Keep permissions read-only unless repository fixtures demonstrably require more.
9. Upload pytest diagnostics on failure using existing artifact conventions.
10. Avoid shell syntax that is invalid on Windows; prefer portable action steps and `uv run python -m pytest`.

### T030 – Invoke the exact production proof

**Purpose**: Prevent a weaker platform smoke test from being presented as NFR-004 evidence.

**Steps**:

1. Invoke all three exact nodes created/renamed by WP01: `test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations`, `test_sc004_event_serialization_mutant_reports_missing_authoritative_event`, and `test_sc004_evidence_commit_mutant_reports_missing_committed_evidence`. Do not use `-m "regression or stress"` as a substitute.
2. Pass `-n0` because the test owns shared Git concurrency internally.
3. Confirm the node itself uses `spawn`, top-level pickleable workers, `sys.executable`/real root runner, and bounded joins.
4. Preserve at least 50 synchronized rounds and two persistent OS processes.
5. Do not add per-platform skip/xfail for production behavior.
6. Emit enough diagnostics to distinguish busy refusal, worker crash, event loss, and missing committed evidence.
7. Validate the workflow references a node that collect-only can find.

### T031 – Run the complete targeted quality gates

**Purpose**: Close the mission's specified quality bar, not only the new workflow file.

Run from a fully integrated dependency lane:

```bash
uv run python -m pytest tests/integration/test_review_durability_matrix.py::test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations tests/integration/test_review_durability_matrix.py::test_sc004_event_serialization_mutant_reports_missing_authoritative_event tests/integration/test_review_durability_matrix.py::test_sc004_evidence_commit_mutant_reports_missing_committed_evidence -n0 -q --tb=short
uv run python -m pytest tests/integration/review/test_verdict_save_topologies.py tests/integration/review/test_reject_from_in_review.py -n0 -q --tb=short
uv run python -m pytest tests/review/test_verdict_commit_queue.py tests/review/test_cycle.py tests/specify_cli/cli/commands/agent/test_move_task_durability.py -n0 -q --tb=short
SPEC_KITTY_RUN_PERFORMANCE=1 uv run python -m pytest tests/review/test_verdict_save_performance.py -n0 --benchmark-only
```

Also run Ruff on every touched Python file and strict mypy on all touched production modules. The authoritative changed-line gate is the repository `diff-coverage` job: record its completed invocation of `uv run diff-cover` against `origin/${{ github.base_ref }}` with `--fail-under=90`, the report inputs, percentage, exit status, and workflow URL. Run the exact named mutation-control nodes and verify their causal classifications.

If a product/test failure appears, report it against the owning WP; do not patch outside `.github/workflows/review-verdict-durability.yml`.

### T032 – Record reproducible closeout evidence

**Purpose**: Leave an auditable proof trail for mission acceptance.

Record through `spec-kitty agent tasks add-history WP07 --mission 01M0QRX7 --agent <agent> --note "..."` rather than directly editing this prompt from the implementation lane. Include:

- exact commands and exit results;
- all three collected exact node names;
- OS/Python/Git versions for local evidence;
- benchmark median/environment from WP06;
- Ruff, strict mypy, and changed-line coverage outcomes;
- event-mutant and evidence-mutant exact expected classifications;
- workflow run links/statuses when available;
- any pre-existing failure clearly distinguished from mission regressions;
- tooling friction and the owning WP for any required correction.

Do not edit mission tracer files from this code-change WP. Mission closeout will curate the event-mediated WP history after integration.

## Test Strategy

Validate YAML with the repository's existing workflow/lint tooling if present. Use `gh workflow` inspection only as read-only evidence unless explicitly authorized to dispatch. Local commands above are mandatory. WP07 must remain blocked/in review until successful completed Linux, macOS, and Windows jobs for all three exact nodes, plus the completed enforced 90% diff-coverage result, are linked; pending hosted results are factual progress but not Definition-of-Done evidence.

## Native Job Acceptance Checklist

For every OS matrix cell, verify and record:

- checkout contains full Git history/ref data required by topology fixtures;
- Python and uv versions match repository policy;
- the exact test node is collected once;
- multiprocessing reports the `spawn` start method;
- both persistent workers start, complete 50 rounds, and terminate cleanly;
- no worker timeout is reported as command success;
- baseline production test passes;
- event-lock mutant observes `missing_authoritative_event` for its intended cause;
- evidence-commit mutant observes `missing_committed_evidence` for its intended cause;
- failure artifacts include enough logs to reproduce locally;
- job timeout is bounded and no retry step masks the first failure.

Workflow review must compare action versions and cache keys with current canonical workflows. If a platform needs a genuinely different shell command, keep the semantic node/arguments identical and explain only the syntax difference.

## Risks & Mitigations

- **Wrong node/zero collection**: use all three exact nodes and collect-only verification.
- **Windows shell incompatibility**: portable commands and action primitives.
- **CI duration**: two persistent workers amortize startup; set bounded job timeout.
- **Cross-lane failure temptation**: route fixes back to owner; maintain no-overlap.
- **External wait**: keep the WP blocked/in review until completed native and diff-coverage evidence exists; never convert pending status into acceptance.
- **False mutation proof**: require causal classification and seam-hit evidence from WP01.

## Review Guidance

Reject if any OS runs a weaker node, if the command selects zero tests, if Windows/macOS are skipped, if outer xdist adds contention, or if evidence claims hosted results that did not run. Confirm all quality commands and ownership boundaries.

## Definition of Done

- T029–T032 event-marked done.
- Workflow syntax and all three exact node selections validate.
- Local targeted quality gates are recorded; successful completed native Linux/macOS/Windows jobs for all three exact nodes are linked.
- The completed repository `diff-coverage` job proves at least 90% changed-line coverage and records its base, reports, percentage, exit status, and URL.
- No out-of-ownership code/test changes occur.
- Event-mediated WP history provides sufficient proof for acceptance and mission tracer closeout.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP07 --to for_review --mission 01M0QRX7` when ready.
- 2026-08-24T11:18:27Z – codex – shell_pid=15577 – Hosted PR #3712 run 32719727958: macOS exact three-node job passed; Ubuntu baseline returned opaque unproven_refusal at round 2; Windows baseline returned opaque unproven_refusal at round 0 and event mutant started its 5s seam wait before spawned workers were ready. Diagnosis: WP01 oracle expects an invented busy JSON shape rather than production durability_classification=busy/durability_reason=verdict_save_busy, and lacks a worker-readiness handshake. WP01 reopened cycle 4; no hosted retry or WP07 completion claimed.
- 2026-08-24T12:11:52Z – codex – shell_pid=15577 – Integrated correction revision c8f791333 local closeout: exact SC-004 baseline/event-mutant/evidence-mutant nodes 3 passed in 66.73s (-n0, spawn, 50 rounds); topology/rejection suite 20 passed in 42.85s; queue/cycle/durability suite 87 passed in 37.71s; performance benchmark median 566.54ms across 5 rounds (<2s); integrated architecture/CLI correction gate 64 passed in 110.88s (dead-symbol, golden-count, collection completeness, approval-collision regression). Ruff/strict mypy evidence is recorded in the independently approved owning WP reviews. Hosted native run 32725512250 and CI Quality run 32725512455 are in progress; no completion claimed.
- 2026-08-24T12:36:36Z – codex – shell_pid=15577 – Second hosted revision c8f791333: native run 32725512250 passed Ubuntu and macOS but Windows failed baseline with typed persistence_failed/destination_readback_mismatch after both commits and event mutant before its stale-preimage seam; Windows XML linked the baseline to text-mode CRLF vs Git LF exact-byte mismatch. WP03 correction 45de90399 now writes deterministic UTF-8 LF bytes without weakening exact readback; WP01 correction 0b010ddbe replaces the non-causal 5s pre-seam wait with bounded output-first causal sequencing. Both independently approved and integrated at f03e8df5a. CI Quality run 32725512455 completed success; enforced diff-coverage job 97430228199 used origin/main, 255 changed lines, 11 missing, 95%, exit success. Third native/quality runs are pending; no cross-platform completion claimed.
- 2026-08-24T13:13:11Z – codex – shell_pid=15577 – Final correction revision 09ab8107c: independently approved WP04 structured invalid-transition refusal integrated without retry/timeout/state-policy changes. Local exact SC-004 baseline/event-mutant/evidence-mutant nodes passed 3/3 in 68.25s; WP04 focused command suites passed 29/29; Ruff, strict mypy, and diff-check passed. Hosted native run 32730562924 completed success: Ubuntu job 97441630642, macOS job 97441630431, and Windows job 97441630612 each collected and passed all three exact nodes. Fresh CI Quality run 32730563173 is still in progress; diff-coverage completion is not yet claimed.
- 2026-08-24T13:21:02Z – codex – shell_pid=15577 – Acceptance evidence complete for revision 09ab8107c. Native run 32730562924 completed success with Ubuntu 97441630642, macOS 97441630431, and Windows 97441630612 all passing the exact SC-004 baseline/event-mutant/evidence-mutant nodes. CI Quality run 32730563173 completed success with no failed jobs. Enforced diff-coverage job 97445991966 completed success against origin/main: 262 changed lines, 11 missing, 95% coverage (>=90%). WP07 T029-T032 are ready for independent review.
- 2026-08-24T14:00:38Z – codex – Cycle-1 correction complete. Prior job 97445991966 proved 95% only in the advisory full-diff step and was rejected as non-enforcing evidence. Reviewed correction 7465f0982 adds the exact five durability production modules to the existing critical_paths gate without changing origin/base, --fail-under=90, or advisory behavior. Fresh CI Quality run 32734019233 completed success. Enforced diff-coverage job 97457875132 consumed 12 coverage reports, compared origin/main, measured tasks_move_task 100%, tasks_verdict_persistence 94.9%, artifacts 100%, cycle 93.4%, verdict_commit_queue 100%; total 262 changed lines, 11 missing, 95%, exit success under --fail-under=90. Native rerun 32734018925 also completed success on Ubuntu, macOS, and Windows.
