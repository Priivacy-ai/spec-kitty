# Release Readiness: Responsive Pre-Review Gate Operator Flow

## Verdict

`waiting_upstream`

WP05 evidence is complete, but issue #2573 is **not release-ready**. As checked on 2026-08-23, #3127 remains open. The mission must not advance to a release-ready claim until #3127 is merged, the delivery branch is rebased on the resulting `main`, and trustworthy required checks—including the mission's native Windows node—run again.

## Evidence snapshot

- Delivery branch: `fix/pre-review-gate-operator-flow`.
- Integrated mission commit: `b67b7596f` (includes the reviewed public-binding fixture repair and process-tree evidence).
- Lifecycle closeout: `1ab824ca7` records all five work packages as `done`; `0bf90230d` restores the canonical acceptance and issue matrices.
- Local platform: macOS/POSIX; native Windows was not available locally.
- Tracker state: #2573 open and assigned to HiC `stijn-dejongh`; #2762 and #3127 open and assigned to `MOES-Media`; #3694 and #3695 open and unassigned.

## Trustworthy checks

| Surface | Command / evidence | Result | Limitation |
|---|---|---|---|
| Policy, engine, aggregation, registry, public command | Integrated focused suite across the mission-owned review and CLI surfaces | 185 passed, 2 expected platform skips after final adversarial remediation. | Local platform is macOS; platform-specific skips are reported separately. |
| POSIX process tree, races, parent death | Integrated `test_pre_review_gate_process_tree.py` and `test_tasks_move_task_pre_review_gate_parent_death.py` suites | Real timeout/cancellation cleanup and abrupt-parent authority preservation pass. | The Windows-only node is skipped locally. |
| Windows node discovery | `uv run pytest --collect-only -q -m windows_ci tests/review/test_pre_review_gate_process_tree.py` | Exact node collected: `tests/review/test_pre_review_gate_process_tree.py::test_windows_taskkill_contract_uses_tree_then_force_escalation` | Collection on macOS is not native Windows execution. |
| Windows workflow existence | `.github/workflows/ci-windows.yml`, job `Windows critical (pipx, pytest -m windows_ci)`, dynamically discovers files containing `@pytest.mark.windows_ci` | Workflow exists. Latest checked `main` run 32620455641 at SHA `d060cff9a5c9f8cf369c8786e5bf9b4f89931d0a` passed. | That run predates this mission node and is not evidence that the new node passed. The PR/rebased branch must obtain a native job result. |
| Ruff | `uv run ruff check` over all mission-owned production/test surfaces | Passed after final adversarial remediation. | `tasks_move_task.py` format-only drift was independently reproduced on the base; lint passed. |
| Strict typing | `uv run mypy --strict src/specify_cli/review/gate_budget.py src/specify_cli/review/pre_review_gate.py src/specify_cli/review/verdict_aggregation.py src/specify_cli/review/gate_registry.py` | Passed: no issues in 4 files after final adversarial remediation. | CLI command module is outside this focused strict-mypy invocation. |
| Public docstrings | AST audit of public functions/classes in the four changed review modules | Required public surfaces carry docstrings; reviewer must repeat after integration. | Manual/AST review is not a substitute for final integrated lint/type checks. |
| Repaired public auto-derived integration | Integrated `tests/review/test_pre_review_gate_integration.py` at `b67b7596f` | 22 passed, 1 platform skip. The real ACTIVE `software-dev/review` binding exercises auto-derived warn, configured block, force admission, baseline-relative exclusion, bounded scope, and handler-owned no-coverage degradation. | macOS run; the skipped subreaper SIGKILL harness is Linux-only. Native Windows remains a separate post-PR release requirement below. |
| Fixture binding guard | `tests/review/test_pre_review_gate_integration.py::_build_wp_file` writes canonical mission metadata and asserts resolver coverage/handler before each public scenario | `GateCoverage.ACTIVE`; handler list is exactly `spec-kitty-pre-review`. | Test-fixture/evidence correction only—no production behavior, CI topology, budget classification, or runtime policy changed. |

Synthetic controlled-clock timeout fixtures were used only as test evidence. No operational unknown-budget timeout occurred, so no policy candidate was appended and no deterministic budget metadata was promoted.

## Current mission-accept state

Mission acceptance and 3.2.6 release readiness are separate gates. All five work packages are integrated and canonically `done`; FR-001 through FR-010 have passing verifier evidence in `acceptance-matrix.json`; and `issue-matrix.json` records the six relevant tracker boundaries. Status was rematerialized and validated, canonical post-merge review and retrospective completed after the adversarial remediations, and final acceptance commit `a25db9709` covers finished production parent `aeab9b063`.

The #3694/#3695 acceptance-evidence defect is locally fixed in integrated commit `b67b7596f`: the auto-derived public warn/block/force paths pass through the ACTIVE binding. Both tracker issues remain open and unassigned pending tracker disposition; that administrative state does not turn the repaired evidence back into an acceptance failure.

No release-ready verdict is claimed here. The mission can be accepted while #3127 and native Windows CI remain explicit external release prerequisites.

## Separate release prerequisite

#3127 remains the upstream 3.2.6 release prerequisite. Even after final Mission acceptance is rerun, #2573 remains `waiting_upstream` until #3127 merges, the delivery branch is rebased on the resulting `main`, and trustworthy required checks are rerun on that rebased branch.

## Issue boundary

- **#2573 — accepted mission scope, not release-ready:** implementation and integrated local evidence exist; final PR CI and upstream release proof remain pending.
- **#2762 — deferred with follow-up:** abrupt-parent-death evidence proves lane/event integrity only. Reaping descendants that escape the process group remains owned by #2762.
- **#3127 — deferred with follow-up / release upstream:** it is the release-root prerequisite. Its open state is the reason for `waiting_upstream`.
- **#3694 / #3695 — open tracker records, local acceptance defect fixed:** integrated commit `b67b7596f` contains the canonical test mission identity and real binding evidence. The issues are not claimed closed; tracker disposition remains pending.
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
