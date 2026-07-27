# Quickstart: Validate Observable Pre-Review Gate

## Red-first proof

1. Add the focused liveness acceptance test through the Typer `move-task` entry point without production changes; replace only the canonical runner with a synchronized controllable double.
2. Run only that test and capture the expected failure on the planning base.
3. Commit the failing test separately.
4. Do not begin implementation until the RED commit is visible in history.

## Focused validation

```bash
PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py -q -n0
PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py -q -n0
PWHEADLESS=1 uv run pytest tests/review/test_pre_review_gate_engine.py tests/review/test_pre_review_gate_integration.py -q -n0
uv run ruff check src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/review/pre_review_gate.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
uv run mypy src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/review/pre_review_gate.py
uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

Do not use retries.

## Acceptance evidence

- Human progress: initial indication and deterministic heartbeat cadence.
- JSON: stdout parsed directly as one document for all terminal cases.
- Interruption: before/after snapshots show zero state residue.
- Compatibility: delivered skip and synchronization-disable cases remain green.
- Git: RED test commit precedes all implementation commits.

## Delivery boundary

After Spec Kitty acceptance and local Mission merge, push only the authorized PR branch and create a draft PR against `origin/main`. Do not mark it ready or merge it.
