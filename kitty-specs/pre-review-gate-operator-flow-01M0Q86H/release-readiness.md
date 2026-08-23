# Release Readiness: Responsive Pre-Review Gate Operator Flow

## Verdict

`waiting_upstream`

WP05 evidence is complete, but issue #2573 is **not release-ready**. As checked on 2026-08-23, #3127 remains open. The mission must not advance to a release-ready claim until #3127 is merged, the delivery branch is rebased on the resulting `main`, and trustworthy required checks—including the mission's native Windows node—run again.

## Evidence snapshot

- Planning branch: `fix/pre-review-gate-operator-flow` at `469a04328` before these artifacts.
- WP03/public lane: `79a6e960869b06991bbbfc1b9f903fd97a677bb0`.
- WP04/process lane: `6f3c190b4a09ba1b4955f55ccdc4b350f2fee10b`.
- Local platform: macOS/POSIX; native Windows was not available locally.
- Tracker state: #2573 open and assigned to HiC `stijn-dejongh`; #3127 open and assigned to `MOES-Media`; #2762 open in Product backlog.

## Trustworthy checks

| Surface | Command / evidence | Result | Limitation |
|---|---|---|---|
| Policy, engine, aggregation, registry, public command | In lane-c: `uv run pytest -q tests/review/test_gate_budget.py tests/review/test_pre_review_gate_engine.py tests/review/test_verdict_aggregation.py tests/review/test_gate_registry.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py` | 153 passed in 16.09s | Lane-c does not contain WP04's verification-only tests. |
| POSIX process tree, races, parent death | In lane-d: `uv run pytest -q tests/review/test_pre_review_gate_process_tree.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py` | 5 passed, 1 skipped in 6.01s | The skipped node is Windows-only. |
| Windows node discovery | In lane-d: `uv run pytest --collect-only -q -m windows_ci tests/review/test_pre_review_gate_process_tree.py` | Exact node collected: `tests/review/test_pre_review_gate_process_tree.py::test_windows_taskkill_contract_uses_tree_then_force_escalation` | Collection on macOS is not native Windows execution. |
| Windows workflow existence | `.github/workflows/ci-windows.yml`, job `Windows critical (pipx, pytest -m windows_ci)`, dynamically discovers files containing `@pytest.mark.windows_ci` | Workflow exists. Latest checked `main` run 32620455641 at SHA `d060cff9a5c9f8cf369c8786e5bf9b4f89931d0a` passed. | That run predates this mission node and is not evidence that the new node passed. The PR/rebased branch must obtain a native job result. |
| Ruff | `uv run ruff check` over all WP01–WP03 source/test ownership in lane-c and WP04 test ownership in lane-d | Passed | `tasks_move_task.py` format-only drift was independently reproduced on the base; lint passed. |
| Strict typing | In lane-c: `uv run mypy --strict src/specify_cli/review/gate_budget.py src/specify_cli/review/pre_review_gate.py src/specify_cli/review/verdict_aggregation.py src/specify_cli/review/gate_registry.py` | Passed: no issues in 4 files | CLI command module is outside this focused strict-mypy invocation. |
| Public docstrings | AST audit of public functions/classes in the four changed review modules | Required public surfaces carry docstrings; reviewer must repeat after integration. | Manual/AST review is not a substitute for final integrated lint/type checks. |
| Auto-derived regression fixture | `uv run pytest -q` on `test_block_mode_blocks_without_force`, `test_force_bypasses_block_and_is_recorded`, `test_override_scope_new_failure_blocks_when_opted_in`, `test_override_scope_force_bypasses_block_and_is_recorded`, and `test_pre_existing_failure_does_not_block` | 2 passed, 3 failed; failures return `NO_COVERAGE` because the fixture has no `(<mission type>, review)` gate binding. | Reproduced before mission changes and tracked as #3694/#3695. It must be triaged before final accept, not waived or counted as delivered behavior. |

Synthetic controlled-clock timeout fixtures were used only as test evidence. No operational unknown-budget timeout occurred, so no policy candidate was appended and no deterministic budget metadata was promoted.

## Current final-accept diagnosis

WP05 can be evidence-complete while final mission acceptance remains blocked. These blockers are current and independent of the later #3127 release prerequisite:

- The canonical `acceptance-matrix.json` remains `overall_verdict: pending`; FR-001 through FR-010 are all pending and still contain scaffold acceptance descriptions rather than final verifier evidence.
- The committed `tasks.md` projection still shows T001–T025 unchecked even though the authoritative event log records completed WP subtasks. The projection must be synchronized and validated before accept.
- #3694 and #3695 require an explicit disposition. The auto-derived public `NEW_FAILURES` warn/block acceptance surface currently resolves `NO_COVERAGE`; unit aggregation and the passing override-route block node do not discharge that missing public-route proof.
- WP01–WP04 evidence currently lives on separate approved lanes. The integrated delivery branch must rerun the focused and dependency suites, and the mission's new Windows node still needs an actual native `ci-windows` result where the job is available.

These are accept-diagnose findings, not reasons to rewrite the release DAG. They may be remedied before #3127 closes. No final-accept or release-ready verdict is claimed here.

## Separate release prerequisite

#3127 remains the upstream 3.2.6 release prerequisite. Even after the accept blockers above are remedied, #2573 remains `waiting_upstream` until #3127 merges, the delivery branch is rebased on the resulting `main`, and trustworthy required checks are rerun on that rebased branch.

## Issue boundary

- **#2573 — in mission, not release-ready:** implementation and focused evidence exist; final integrated and CI proof is still pending.
- **#2762 — deferred with follow-up:** abrupt-parent-death evidence proves lane/event integrity only. Reaping descendants that escape the process group remains owned by #2762.
- **#3127 — deferred with follow-up / release upstream:** it is the release-root prerequisite. Its open state is the reason for `waiting_upstream`.
- **#3694 / #3695 — pre-existing verification defects:** these explain the dependency-suite `NO_COVERAGE` failures. They must receive a disposition before final accept; this mission does not silently waive them.
- **Async redesign — deferred:** no background gate job, pending-review lane, CI log backfill, CI topology redesign, or runtime policy learning is included.

## Executable resume sequence

Run only after #3127 has merged:

```bash
gh issue view 3127 --repo Priivacy-ai/spec-kitty --json state,closedAt,url
git fetch origin main
git rev-parse origin/main
git rebase origin/main
uv sync --all-extras
uv run pytest -q tests/review/test_gate_budget.py tests/review/test_pre_review_gate_engine.py tests/review/test_verdict_aggregation.py tests/review/test_gate_registry.py tests/review/test_pre_review_gate_process_tree.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py
uv run pytest -q tests/review/test_pre_review_gate_integration.py
uv run ruff check src/specify_cli/review tests/review tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py
uv run mypy --strict src/specify_cli/review/gate_budget.py src/specify_cli/review/pre_review_gate.py src/specify_cli/review/verdict_aggregation.py src/specify_cli/review/gate_registry.py
uv run spec-kitty agent status validate --mission pre-review-gate-operator-flow-01M0Q86H --json
```

Then push the rebased PR branch, require the actual `ci-windows / Windows critical (pipx, pytest -m windows_ci)` job to collect and pass `test_windows_taskkill_contract_uses_tree_then_force_escalation`, resolve or explicitly disposition #3694/#3695 under the charter's pre-existing-failure rule, run the remaining protected required checks, and only then reassess #2573 and the release verdict.
