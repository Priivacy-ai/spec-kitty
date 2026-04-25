# Quickstart: Phase 6 Composition Stabilization

**Mission**: phase6-composition-stabilization-01KQ2JAS
**Audience**: operators / contributors verifying the three behaviors locally before merge.

## Prerequisites

```bash
cd /Users/robert/spec-kitty-dev/786-793-794-phase6-stabilization/spec-kitty
uv sync --python 3.13 --extra test
```

If `spec-kitty-runtime` fails to import, install it from the sibling checkout:

```bash
uv pip install -e ../spec-kitty-runtime
```

(Do **not** patch around an environment-only import failure in the source.)

## 1. Verify single-dispatch (`#786`)

The fastest signal: the bridge composition tests pass with the new negative-condition tests.

```bash
uv run --python 3.13 --extra test python -m pytest \
  tests/specify_cli/next/test_runtime_bridge_composition.py -q
```

Expected: all tests green. The new test names start with `test_composition_success_skips_legacy_dispatch[...]` and `test_decision_shape_unchanged_for_composed_action`.

Manual smoke (optional): run the live `software-dev` mission against any test mission and watch `.kittify/status.events.jsonl` — each composed action should produce exactly one set of lane transitions per action call.

## 2. Verify contract-action recording (`#794`)

```bash
uv run --python 3.13 --extra test python -m pytest \
  tests/specify_cli/invocation/test_invocation_e2e.py \
  tests/specify_cli/mission_step_contracts/test_software_dev_composition.py -q
```

Expected: all tests green. The new parametrized tests `test_invoke_with_action_hint_and_profile_hint_records_hint[specify|plan|tasks|implement|review]` confirm the started JSONL records carry the contract action.

Manual smoke (optional): trigger any composed `software-dev` action against a scratch mission, then inspect the most recent JSONL:

```bash
ls -t .kittify/events/profile-invocations/*.jsonl | head -1 | xargs -I{} head -1 {} | python3 -m json.tool | grep '"action"'
```

For a composed `software-dev/specify`, the value should be `"specify"`, not `"analyze"`.

## 3. Verify lifecycle pairing (`#793`)

After running any composed `software-dev` action against a scratch mission:

```bash
# All started records:
grep -h '"event":"started"' .kittify/events/profile-invocations/*.jsonl | wc -l

# All completion records (completed + failed):
grep -hE '"event":"(completed|failed)"' .kittify/events/profile-invocations/*.jsonl | wc -l
```

Expected: the two counts are equal. No `started`-only files.

The automated equivalent:

```bash
uv run --python 3.13 --extra test python -m pytest \
  tests/specify_cli/invocation/test_invocation_e2e.py::test_composed_action_pairs_started_with_completed \
  tests/specify_cli/invocation/test_invocation_e2e.py::test_composed_step_failure_writes_failed_completion -q
```

## 4. Full focused suite

```bash
uv run --python 3.13 --extra test python -m pytest \
  tests/specify_cli/next/test_runtime_bridge_composition.py \
  tests/specify_cli/mission_step_contracts/test_software_dev_composition.py \
  tests/specify_cli/invocation/test_invocation_e2e.py \
  tests/specify_cli/invocation/test_writer.py \
  -q
```

## 5. Static checks

```bash
uv run --python 3.13 python -m ruff check \
  src/specify_cli/next/runtime_bridge.py \
  src/specify_cli/mission_step_contracts/executor.py \
  src/specify_cli/invocation/executor.py \
  tests/specify_cli/next/test_runtime_bridge_composition.py \
  tests/specify_cli/mission_step_contracts/test_software_dev_composition.py \
  tests/specify_cli/invocation/test_invocation_e2e.py

uv run --python 3.13 python -m mypy --strict \
  src/specify_cli/next/runtime_bridge.py \
  src/specify_cli/mission_step_contracts/executor.py \
  src/specify_cli/invocation/executor.py
```

Expected: zero failures, zero errors.

## What NOT to expect

- No CLI surface changes — `spec-kitty next ...` and `spec-kitty agent ...` behave identically from the operator's perspective.
- No JSONL format changes — the trail file format is byte-compatible with pre-merge format.
- No `mission-runtime.yaml` changes.
- No `.kittify/charter/` changes.

## If something is wrong

- If `runtime_bridge` tests fail with "legacy dispatch was called" or similar, the single-dispatch invariant has regressed — see `contracts/runtime_bridge_dispatch.md`.
- If invocation files have only `started` records, lifecycle close was missed — see `contracts/step_contract_executor_lifecycle.md`.
- If a composed action records action `"analyze"` or `"audit"` instead of `"specify"` / `"plan"` / `"tasks"` / `"implement"` / `"review"`, `action_hint` propagation regressed — see `contracts/invocation_executor_invoke.md`.
