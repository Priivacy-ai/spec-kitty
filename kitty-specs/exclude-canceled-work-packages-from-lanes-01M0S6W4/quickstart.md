# Phase 1 Quickstart: Verify Cancellation-Aware Finalization

Run from the repository root with SaaS sync disabled for local fixtures:

```bash
unset SPEC_KITTY_ENABLE_SAAS_SYNC
```

## 1. Record RED acceptance evidence

Before production edits, add the exact-command cancellation acceptance tests and commit them separately. On the planning base, the mixed-canceled, stale-dependency, and all-canceled scenarios must fail for the expected behavioral reason.

```bash
uv run --extra test pytest -q tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py
```

Do not use retries or mark the expected defect as `xfail`.

## 2. Record the tidy-first campsite checkpoint

After the RED commit and before functional production edits, inspect the exact `mission_finalize.py` methods that will change. Record their size/complexity and current focused-test baseline. Commit proportional behavior-preserving cleanup separately, or record a measured frozen baseline plus locality rationale when cleanup would expand Mission scope.

## 3. Verify the pure projection and Windows collection

```bash
uv run --extra test pytest -q tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py
uv run --extra test pytest --collect-only -q -m windows_ci \
  tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py
```

Required cases: unchanged graph, canceled exclusion, reopened/done inclusion, all-canceled graph, canceled-to-canceled edge, and complete deterministic stale-edge ordering.

## 4. Verify command behavior

```bash
uv run --extra test pytest -q \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py \
  tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
```

Check that canceled definitions remain in history, canceled ownership cannot fail or collapse eligible work, every stale edge is reported before writes, mixed Missions contain only eligible execution work, and all-canceled Missions produce a valid zero-lane result in normal and validate-only modes.

## 5. Verify unaffected allocation semantics

```bash
uv run --extra test pytest -q \
  tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py \
  tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py \
  tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py \
  tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py \
  tests/tasks/test_finalize_tasks_json_output_unit.py
```

These protect #3431 post-collapse cycle behavior, no-cancellation parity, and the existing invalid-empty-input refusal.

## 6. Run the governed performance proof

The benchmark uses the repository's off-PR performance mechanism. Its reference environment is Blacksmith 4-vCPU Ubuntu 24.04 with CPython 3.11. The test records 10 rounds after two discarded warm-ups and requires p95 at or below two seconds.

```bash
SPEC_KITTY_RUN_PERFORMANCE=1 uv run python -m pytest \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages_performance.py \
  -m performance -n0 -q
```

## 7. Enforce changed-line coverage and focused quality gates

Generate focused coverage and enforce the charter's 90% new-code floor against the planning branch:

```bash
mkdir -p out/reports/coverage
uv run --extra test pytest -q \
  tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py \
  tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py \
  --cov=specify_cli.cli.commands.agent.finalization_eligibility \
  --cov=specify_cli.cli.commands.agent.mission_finalize \
  --cov-report=xml:out/reports/coverage/coverage-canceled-finalization.xml

uv run diff-cover \
  out/reports/coverage/coverage-canceled-finalization.xml \
  --compare-branch=fix/exclude-canceled-work-packages-from-lanes \
  --fail-under=90
```

Then run lint and strict typing:

```bash
uv run --extra test ruff check \
  src/specify_cli/cli/commands/agent/finalization_eligibility.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py \
  tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages_performance.py \
  tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py

uv run --extra test mypy --strict \
  src/specify_cli/cli/commands/agent/finalization_eligibility.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py
```

Run the exact architecture and terminology gates for this surface:

```bash
uv run --extra test pytest -q \
  tests/architectural/test_lane_allocation_single_seam.py \
  tests/architectural/test_no_legacy_terminology.py \
  tests/contract/test_terminology_guards.py
```

The full suite belongs at the later acceptance gate.
