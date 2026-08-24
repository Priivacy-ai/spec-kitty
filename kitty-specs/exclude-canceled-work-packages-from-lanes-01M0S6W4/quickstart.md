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

## 2. Verify the pure projection

```bash
uv run --extra test pytest -q tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py
```

Required cases: unchanged graph, canceled exclusion, reopened/done inclusion, all-canceled graph, canceled-to-canceled edge, and complete deterministic stale-edge ordering.

## 3. Verify command behavior

```bash
uv run --extra test pytest -q \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py \
  tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
```

Check that canceled definitions remain in history, canceled ownership cannot fail or collapse eligible work, every stale edge is reported before writes, mixed Missions contain only eligible execution work, and all-canceled Missions produce a valid zero-lane result in normal and validate-only modes.

## 4. Verify unaffected allocation semantics

```bash
uv run --extra test pytest -q \
  tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py \
  tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py \
  tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py \
  tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py \
  tests/tasks/test_finalize_tasks_json_output_unit.py
```

These protect #3431 post-collapse cycle behavior, no-cancellation parity, and the existing invalid-empty-input refusal.

## 5. Run focused quality gates

```bash
uv run --extra test ruff check \
  src/specify_cli/cli/commands/agent/finalization_eligibility.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py \
  tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py

uv run --extra test mypy --strict \
  src/specify_cli/cli/commands/agent/finalization_eligibility.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py
```

Use the repository's established architecture/terminology gates at implementation closeout. The full suite belongs at the later acceptance gate.
