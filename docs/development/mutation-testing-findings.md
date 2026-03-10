# Mutation Testing Findings (WP05)

This document captures findings from the WP05 mutation testing baseline run against all four priority modules:
`status/`, `glossary/`, `merge/`, `core/`.

## Mutation Score Baseline

Run date: 2026-03-01 (full run)
Configuration: all four priority modules (`status/`, `glossary/`, `merge/`, `core/`)
Test scope: `tests/unit/` + `tests/specify_cli/` (with problematic test files excluded)

| Status | Count |
|--------|-------|
| Killed | 11,354 |
| Survived | 4,755 |
| Not checked | 0 |
| **Kill rate** | **70.5%** |

## WP05 Targeted Kill Session (2026-03-02)

After establishing the baseline, a targeted session squashed surviving mutants in
`status/reducer.py` and `status/transitions.py` by adding 60+ new test assertions to:

- `tests/specify_cli/status/test_reducer.py` — rollback precedence, timezone-aware timestamps,
  JSON format specifics (sort_keys, indent, ensure_ascii)
- `tests/specify_cli/status/test_transitions.py` — exact error message assertions for all guard
  functions and force-validation paths

**Results from targeted rerun:**

| Module | Previous survivors | After kill session |
|--------|--------------------|--------------------|
| `status/reducer.py` | 55 | 1 (equivalent mutant) |
| `status/transitions.py` | 55 | 6 (equivalent/dead-code mutants) |

**Kill examples:**
- `_is_rollback_event` mutants 1–5: killed by `TestRollbackPrecedence` concurrent-event tests
- `_should_apply_event` mutants 3–32 (17 killed): killed by rollback-beats-forward scenarios
- `materialize_to_json` mutants (sort_keys, indent, ensure_ascii): killed by format assertions
- `_guard_*` error message mutations: killed by exact-match message assertions

## Equivalent and Dead-Code Mutants

The following surviving mutants cannot be killed with meaningful tests because they either
represent unreachable code paths or semantically equivalent behaviour:

### `status/transitions.py` — trampoline makes default-arg mutations invisible

```python
# x_validate_transition__mutmut_1: force: bool = False → force: bool = True
```

**Why equivalent**: mutmut 3.x embeds mutations via a trampoline pattern. The trampoline
wrapper always passes `force` explicitly as a kwarg, so the function's own default value
is never used. Any default-arg mutation on `validate_transition` is invisible at runtime.

### `status/transitions.py` — `_guard_subtasks_complete_or_force` force branch

```python
def _guard_subtasks_complete_or_force(
    subtasks_complete: bool | None,
    force: bool,
    ...
) -> tuple[bool, str | None]:
    if force:
        return True, None  # <-- DEAD CODE
    ...
```

**Reason**: The caller `validate_transition` already handles `force=True` at lines 259–264
(before calling `_run_guard`). When `force=True`, execution returns before reaching
`_guard_subtasks_complete_or_force`. So the `if force: return True, None` branch inside
the guard is never reached.

**Mutation evidence**: `mutmut` generates the mutation `return True, None` → `return False, None`
for this branch. Tests pass with this mutation active, confirming the branch is dead.

**Suggested action**: Remove the `if force:` guard from `_guard_subtasks_complete_or_force`
(and other guard functions that have identical dead-code force branches). The guards are only
called when `force=False`, so the force parameter can be removed from the guard signature.

### `status/transitions.py` — `_run_guard` unknown-guard return

```python
# x__run_guard__mutmut_34: return True, None → return False, None
```

**Why equivalent**: The final `return True, None` in `_run_guard` is dead code because all
known guard names are handled by the if/elif chain above it. No test can trigger this path.

### `status/transitions.py` — `_guard_reviewer_approval` getattr defaults

```python
# mutmut_13: getattr(evidence, "review", None) → getattr(evidence, "review", )
# mutmut_21: getattr(review, "reviewer", None) → getattr(review, "reviewer", )
# mutmut_30: getattr(review, "reference", None) → getattr(review, "reference", )
```

**Why equivalent**: `DoneEvidence` and `ReviewApproval` are dataclasses whose attributes
always exist. The `getattr` default (None) is never reached, so dropping it has no effect.

### `status/reducer.py` — `_should_apply_event` first-block initialiser

```python
# mutmut_13: current_setter = None → current_setter = ""
# mutmut_15: current_setter = ev → current_setter = None  (inside loop)
```

**Why equivalent**: The initialiser value of `current_setter` is always overwritten by the loop
(the loop always finds the matching event_id because every recorded state traces back to an event
in `sorted_events`). The initial value is never observable.

### `status/reducer.py` — `ensure_ascii=None` vs `ensure_ascii=False`

```python
# mutmut_5: ensure_ascii=False → ensure_ascii=None
```

**Why equivalent**: `json.dumps(ensure_ascii=None)` treats `None` as falsy, producing the same
output as `ensure_ascii=False` (non-ASCII chars not escaped). Platform-dependent on some
edge cases but observably identical in all current test data.

## Broader Surviving Mutants (Untested Modules)

The 4,755 total surviving mutants include many more in `glossary/`, `merge/`, `core/`, and
the larger `status/` sub-modules. These have not been targeted yet:

| Module | Survivors |
|--------|-----------|
| `core/vcs.py` | 1,113 |
| `glossary/events.py` | 512 |
| `status/reconcile.py` | 426 |
| `glossary/middleware.py` | 150 |
| `core/worktree.py` | 150 |
| `status/migrate.py` | 138 |
| ... | ... |

## Mutmut Configuration Notes

### Test venv pre-seeding

`mutmut` copies tests into `mutants/tests/` and runs pytest from `mutants/`. The conftest's
`test_venv` autouse session fixture builds a test venv based on `REPO_ROOT`, which resolves
to `mutants/` when running from that directory. This caused the venv to be rebuilt on every
fresh `mutants/` generation (taking 60–90s per run and requiring a GitHub clone of
`spec-kitty-runtime`).

**Fix**: Added `.pytest_cache/spec-kitty-test-venv/` to `also_copy` in `pyproject.toml`.
mutmut now copies the pre-built venv into each fresh `mutants/` directory, skipping the rebuild.

### Excluded test files

Several test files are excluded from mutmut's test scope because they fail in the
`mutants/` environment but not the main repo. These are integration tests that invoke
the CLI binary or use filesystem paths that break under the `mutants/` `REPO_ROOT` aliasing:

- `tests/unit/agent/` — fixture setup errors
- `tests/unit/mission_v1/` — creates a full test venv (takes >30s, timeout)
- `tests/unit/next/` — transitive import of `mission_v1` which requires `spec-kitty-runtime`
- `tests/unit/orchestrator_api/` — fails in mutants env
- `tests/unit/runtime/` — fails in mutants env
- `tests/unit/test_atomic_status_commits.py` — git commit operations break in mutants
- `tests/unit/test_move_task_git_validation.py` — git operations break in mutants
- `tests/specify_cli/test_cli/` — CLI JSON output tests fail in mutants env
- `tests/specify_cli/test_implement_command.py` — CLI tests fail in mutants env
- `tests/specify_cli/test_review_warnings.py` — fails in mutants env
- `tests/specify_cli/test_workflow_auto_moves.py` — fails in mutants env
- `tests/specify_cli/upgrade/test_migration_robustness.py` — filesystem ops fail in mutants
- `tests/specify_cli/status/test_parity.py` — uses `inspect.getsource()` which reads mutmut's 26k-line multi-mutation files, confusing the parser

### mutmut 3.x trampoline architecture

mutmut 3.x embeds ALL mutations into the source file simultaneously using a trampoline/dispatch
pattern. `MUTANT_UNDER_TEST` env var selects which variant runs. Each function becomes:

```python
def func(*args, **kwargs):
    return _mutmut_trampoline(func__orig, func__mutants, args, kwargs)
```

The trampoline always passes kwargs explicitly from the wrapper signature, which makes
default-argument mutations invisible (the wrapper's own default is used, not the mutant's).

This also means `mutmut results` only shows currently-cached results; running `mutmut run`
on specific mutants resets the meta file for that source file, clearing other mutants' status.

### mutmut results interpretation

`mutmut results` shows ONLY survived mutants. Killed mutants are filtered out.
To see all results: `mutmut results --all True` (but this is not a useful option).
Kill/survive counts must be computed from `.meta` JSON files in `mutants/`:

```python
import json
from pathlib import Path
killed = survived = 0
for meta_file in Path('mutants').rglob('*.meta'):
    with open(meta_file) as f:
        d = json.load(f)
    for v in d['exit_code_by_key'].values():
        if v is None: continue
        if v == 0: survived += 1
        else: killed += 1
print(f'Kill rate: {100*killed/(killed+survived):.1f}%')
```
