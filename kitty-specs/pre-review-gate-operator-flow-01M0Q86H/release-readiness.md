# Release Readiness: Responsive Pre-Review Gate Operator Flow

## Verdict

`waiting_upstream`

WP05 evidence is complete, but issue #2573 is **not release-ready**. As checked on 2026-08-23, #3127 remains open. The mission must not advance to a release-ready claim until #3127 is merged, the delivery branch is rebased on the resulting `main`, and trustworthy required checks—including the mission's native Windows node—run again.

## Evidence snapshot

- Planning branch: `fix/pre-review-gate-operator-flow` at `469a04328` before these artifacts.
- WP03/public lane: `dabb8edd7` (includes the canonical mission-metadata fixture repair).
- WP04/process lane: `6f3c190b4a09ba1b4955f55ccdc4b350f2fee10b`.
- Local platform: macOS/POSIX; native Windows was not available locally.
- Tracker state: #2573 open and assigned to HiC `stijn-dejongh`; #2762 and #3127 open and assigned to `MOES-Media`; #3694 and #3695 open and unassigned.

## Trustworthy checks

| Surface | Command / evidence | Result | Limitation |
|---|---|---|---|
| Policy, engine, aggregation, registry, public command | In lane-c: `uv run pytest -q tests/review/test_gate_budget.py tests/review/test_pre_review_gate_engine.py tests/review/test_verdict_aggregation.py tests/review/test_gate_registry.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py` | Fresh reconciliation run: 145 passed in 12.91s plus 8 registry passes in 1.27s (153 total). | Lane-c does not contain WP04's verification-only tests. |
| POSIX process tree, races, parent death | In lane-d: `uv run pytest -q -rs tests/review/test_pre_review_gate_process_tree.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py` | Fresh reconciliation run: 5 passed, 1 skipped in 5.54s. | The skipped node is Windows-only. |
| Windows node discovery | In lane-d: `uv run pytest --collect-only -q -m windows_ci tests/review/test_pre_review_gate_process_tree.py` | Exact node collected: `tests/review/test_pre_review_gate_process_tree.py::test_windows_taskkill_contract_uses_tree_then_force_escalation` | Collection on macOS is not native Windows execution. |
| Windows workflow existence | `.github/workflows/ci-windows.yml`, job `Windows critical (pipx, pytest -m windows_ci)`, dynamically discovers files containing `@pytest.mark.windows_ci` | Workflow exists. Latest checked `main` run 32620455641 at SHA `d060cff9a5c9f8cf369c8786e5bf9b4f89931d0a` passed. | That run predates this mission node and is not evidence that the new node passed. The PR/rebased branch must obtain a native job result. |
| Ruff | `uv run ruff check` over all WP01–WP03 source/test ownership in lane-c and WP04 test ownership in lane-d | Passed | `tasks_move_task.py` format-only drift was independently reproduced on the base; lint passed. |
| Strict typing | In lane-c: `uv run mypy --strict src/specify_cli/review/gate_budget.py src/specify_cli/review/pre_review_gate.py src/specify_cli/review/verdict_aggregation.py src/specify_cli/review/gate_registry.py` | Passed: no issues in 4 files | CLI command module is outside this focused strict-mypy invocation. |
| Public docstrings | AST audit of public functions/classes in the four changed review modules | Required public surfaces carry docstrings; reviewer must repeat after integration. | Manual/AST review is not a substitute for final integrated lint/type checks. |
| Repaired public auto-derived integration | In lane-c at `dabb8edd7`: `uv run pytest -q -rs tests/review/test_pre_review_gate_integration.py` | 22 passed, 1 platform skip in 18.32s. The real ACTIVE `software-dev/review` binding now exercises auto-derived warn, configured block, force admission, baseline-relative exclusion, bounded scope, and handler-owned no-coverage degradation. | macOS run; the skipped subreaper SIGKILL harness is Linux-only. Native Windows remains a separate post-PR release requirement below. |
| Fixture binding guard | `tests/review/test_pre_review_gate_integration.py::_build_wp_file` writes canonical mission metadata and asserts resolver coverage/handler before each public scenario | `GateCoverage.ACTIVE`; handler list is exactly `spec-kitty-pre-review`. | Test-fixture/evidence correction only—no production behavior, CI topology, budget classification, or runtime policy changed. |

Synthetic controlled-clock timeout fixtures were used only as test evidence. No operational unknown-budget timeout occurred, so no policy candidate was appended and no deterministic budget metadata was promoted.

## Current final-accept diagnosis

WP05 can be evidence-complete while final mission acceptance remains distinct from the later #3127 release prerequisite. Current final-accept work is:

- The canonical `acceptance-matrix.json` remains `overall_verdict: pending`; FR-001 through FR-010 are all pending and still contain scaffold acceptance descriptions rather than final verifier evidence.
- The committed `tasks.md` projection still shows T001–T025 unchecked even though the authoritative event log records completed WP subtasks. The projection must be synchronized and validated before accept.
- The #3694/#3695 acceptance-evidence defect is locally fixed by `dabb8edd7`: the auto-derived public warn/block/force paths now pass through the ACTIVE binding. Both tracker issues remain open and unassigned pending tracker closure; that administrative state does not turn the repaired evidence back into an acceptance failure.
- WP01–WP04 evidence currently lives on separate reviewed lanes. The integrated delivery branch must rerun the focused and dependency suites, and the mission's new Windows node still needs an actual native `ci-windows` result where the job is available.

These are accept-diagnose findings, not reasons to rewrite the release DAG. They may be remedied before #3127 closes. No final-accept or release-ready verdict is claimed here.

## Separate release prerequisite

#3127 remains the upstream 3.2.6 release prerequisite. Even after the accept blockers above are remedied, #2573 remains `waiting_upstream` until #3127 merges, the delivery branch is rebased on the resulting `main`, and trustworthy required checks are rerun on that rebased branch.

## Issue boundary

- **#2573 — in mission, not release-ready:** implementation and focused evidence exist; final integrated and CI proof is still pending.
- **#2762 — deferred with follow-up:** abrupt-parent-death evidence proves lane/event integrity only. Reaping descendants that escape the process group remains owned by #2762.
- **#3127 — deferred with follow-up / release upstream:** it is the release-root prerequisite. Its open state is the reason for `waiting_upstream`.
- **#3694 / #3695 — open tracker records, local acceptance defect fixed:** commit `dabb8edd7` repairs the canonical test mission identity and restores the real binding evidence. The issues are not claimed closed; tracker closure remains pending.
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

Then push the rebased PR branch, require the actual `ci-windows / Windows critical (pipx, pytest -m windows_ci)` job to collect and pass `test_windows_taskkill_contract_uses_tree_then_force_escalation`, record the eventual tracker closure state for #3694/#3695 without reopening the already-passing acceptance evidence, run the remaining protected required checks, and only then reassess #2573 and the release verdict.
