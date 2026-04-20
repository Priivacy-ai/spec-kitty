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

---

## 2026-04-20 whole-`src/` partial run

First whole-repository mutation run since the local-only adoption (ADR
`2026-04-20-1`). The run was sampled partway through (`max_children=8`, ~1 h
elapsed, ~75 % of mutants tested); results below are a snapshot, not a final
score. Configuration: `paths_to_mutate = ["src/"]`, `do_not_mutate =
["src/specify_cli/upgrade/migrations/", "src/specify_cli/version_utils.py"]`,
sandbox baseline green after the marker migration described in ADR
`2026-04-20-1` To-Be.

### Snapshot (in-flight totals)

Computed from `mutants/**/*.meta` (`exit_code_by_key` → `0` = survived, else
killed). `mutmut results` agrees on the non-killed categories:

| Status | Count | Notes |
|--------|------:|-------|
| Killed | 55,096 | Silent in `mutmut results`; read from `.meta` |
| Survived | 15,389 | Actionable — tests pass with mutant in place |
| No tests | 30,244 | Mutation location not reached by any test |
| Timeout | 755 | Mutation caused hang; treat like survived unless clearly benign |
| Not checked | 13,067 | Still pending at the snapshot |

Apparent kill rate: **55,096 / (55,096 + 15,389) = 78.2 %** against the
tested-set. Including `no tests` as unkilled brings the effective score on
reached-plus-unreached code to roughly **55 %** — the "no coverage" bucket is
the single largest category and the first lever to pull.

### Hotspot modules by survivor count (top-level)

```
2053  specify_cli.cli            — sprawling CLI entry points; many handlers
1136  specify_cli.glossary       — already audited in the 2026-03-01 WP05 baseline
1103  specify_cli.sync           — tracker/daemon IO wrappers
 904  specify_cli.core           — mission selectors, worktree topology
 855  specify_cli.migration      — bulk mutation operations (semi-equivalent risk)
 683  specify_cli.verify_enhanced
 615  specify_cli.tracker
 594  specify_cli.runtime
 562  specify_cli.next
 524  specify_cli.status
 508  specify_cli.review
 439  charter.synthesizer
 434  specify_cli.agent_utils
```

### Hotspot sub-modules (top 15)

```
1716  specify_cli.cli.commands                  ← single biggest pile of survivors
 519  specify_cli.glossary.events
 432  specify_cli.agent_utils.status
 296  specify_cli.review.baseline
 295  specify_cli.migration.rebuild_state
 280  specify_cli.validators.research
 244  specify_cli.sync.events
 233  specify_cli.dashboard.scanner
 219  specify_cli.sync.daemon
 219  specify_cli.migration.backfill_identity
 217  specify_cli.next.runtime_bridge
 216  specify_cli.cli.ui
 209  specify_cli.core.worktree_topology
 204  specify_cli.runtime.agent_commands
 200  specify_cli.next.prompt_builder
```

`specify_cli.cli.commands` alone accounts for ~11 % of all survivors — many of
its handlers are thin adapters that either lack direct unit coverage (most
tests use `typer.testing.CliRunner` and assert only on exit codes) or use
assertion patterns that miss mutation operators on branch conditions and
string literals.

### Compat module (the original trigger)

```
29  no tests
20  survived
```

All survivors cluster in `_validate_canonical_import` and
`_validate_version_order`. Example survivor IDs:

```
specify_cli.compat.registry.x__validate_canonical_import__mutmut_7..12  (6)
specify_cli.compat.registry.x__validate_version_order__mutmut_10,12    (2)
specify_cli.compat.registry.x_load_registry__mutmut_14                 (1)
specify_cli.compat.registry.xǁRegistrySchemaErrorǁ__init____mutmut_4   (1)
```

Validation-function survivors are the canonical case for the Boundary Pair +
Non-Identity Inputs styleguide patterns — the tests exercise the happy path
and a broad "malformed input" case but miss the **exact** comparison boundaries
that `>=` / `>` / `<=` / `<` mutation operators flip.

### Follow-up prioritisation

Order kill-the-survivor passes by survivor density and review-blast-radius:

1. **`specify_cli.compat`** (20 survivors, narrow surface) — first PR. Small
   enough to demonstrate the kill-the-survivor workflow end-to-end; directly
   protects the compatibility-shim mission we just landed.
2. **`specify_cli.cli.commands`** (1716 survivors) — not a single PR. Split by
   sub-command file; target ≥ 80 % mutation score on the top-5 busiest files.
3. **`specify_cli.glossary.events`** (519) and **`specify_cli.agent_utils.status`** (432)
    — both have strong existing coverage; survivors indicate
   assertion-strength gaps, not coverage gaps. Good candidate for
   mutation-aware pattern demonstrations in review.
4. **`specify_cli.review.baseline` / `specify_cli.migration.rebuild_state`**
   (~295 each) — overlap with the post-merge stale-assertion detector landed
   in mission 068. Cross-reference before mutating to avoid duplicate work.

### Caveats

- The snapshot is partial; the final kill rate will drift as the remaining
  ~13 k pending mutants resolve. Re-sample after the run completes.
- The `no tests` category inflates easily in packages with large data-model
  modules where the "test" is really a schema round-trip — mutations on
  private helpers are structurally unreachable from black-box tests. Not
  every `no tests` entry is a real coverage bug.
- Migration packages (`specify_cli.migration.*`) produce many equivalent
  mutants by construction (idempotent `dict.setdefault` / `copy()` operations).
  Apply `# pragma: no mutate` liberally and don't treat the survivor count
  there as comparable to business-logic modules.
- The run still included some sandbox-hostile tests before we landed the
  `non_sandbox` / `flaky` marker migration. Post-migration re-runs should
  produce slightly tighter numbers (fewer no-tests entries caused by tests
  that silently skipped).

### Re-sampling

Once the run completes, repeat the `.meta` scan; if the ratio holds,
publish the completed numbers here. Kill-the-survivor PRs should cite the
specific mutant IDs they address (`mutmut show <id>`) in their commit
messages so the lineage is traceable across snapshots.
