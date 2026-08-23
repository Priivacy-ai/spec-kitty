# Phase 1 Quickstart: Verification

Run commands from the repository root checkout on `fix/reject-cyclic-lane-graphs`.

## Focused behavior

```bash
uv run pytest \
  tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py \
  tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py \
  tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py
```

The suite must demonstrate:

- deterministic rejection of two-lane, three-lane, multiple, and planning-lane cycles;
- the same structured details from mutating and `--validate-only` finalization;
- no traceback or recursion failure;
- absent `lanes.json` remains absent;
- existing `lanes.json` remains byte-identical;
- clean DAGs preserve existing results.

## Determinism

Run the structured CLI fixture with at least three process hash seeds and compare the `error_code`, `cycle_path`, and `cycle_lanes` portions byte-for-byte:

```bash
PYTHONHASHSEED=1 uv run pytest tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py -k hash_seed
PYTHONHASHSEED=7 uv run pytest tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py -k hash_seed
PYTHONHASHSEED=97 uv run pytest tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py -k hash_seed
```

## Performance

```bash
SPEC_KITTY_RUN_PERFORMANCE=1 uv run pytest \
  tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py \
  -m benchmark --benchmark-warmup-iterations=5 --benchmark-min-rounds=20
```

For the fixed 100-lane/500-edge fixture, the detector's p95 must be no more than 100 ms on the CI runner.

## Quality gates

```bash
uv run ruff check \
  src/specify_cli/lanes/compute.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py \
  tests/specify_cli/lanes \
  tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py

uv run mypy --strict \
  src/specify_cli/lanes/compute.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py

uv run pytest tests/lanes tests/specify_cli/lanes tests/specify_cli/cli/commands/agent -q
```

If a failure is demonstrably pre-existing, follow charter directive DIR-013 and file a GitHub issue containing the command, failure summary, and evidence that this mission did not introduce it before treating it as baseline.
