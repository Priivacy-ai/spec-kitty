# Contract — Runtime-bridge ↔ StepContractExecutor handoff

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Call site**: `src/specify_cli/next/runtime_bridge.py`
**Callee**: `specify_cli.mission_step_contracts.executor.StepContractExecutor.execute`

## Inputs

The bridge MUST construct a `StepContractExecutionContext` with the following fields:

| Field | Type | Source | Required |
|---|---|---|---|
| `repo_root` | `pathlib.Path` | bridge's resolved repo root | yes |
| `mission` | `str` | runtime DAG mission key (`"software-dev"`) | yes |
| `action` | `str` | normalized step ID (see normalization rule) | yes |
| `actor` | `str` | bridge's resolved actor; default `"unknown"` | yes (default) |
| `profile_hint` | `str \| None` | operator `--profile` if present | no |
| `request_text` | `str \| None` | invocation prompt text if present | no |
| `mode_of_work` | `ModeOfWork \| None` | from CLI if present | no |
| `resolution_depth` | `int` | default `2` (executor's default) | no |

### Normalization rule

Legacy DAG step IDs map to the new composition action IDs:

| Legacy step ID | Normalized action |
|---|---|
| `specify` | `specify` |
| `plan` | `plan` |
| `tasks_outline` | `tasks` |
| `tasks_packages` | `tasks` |
| `tasks_finalize` | `tasks` |
| `implement` | `implement` |
| `review` | `review` |
| anything else | passes through; bridge does NOT enter composition branch |

## Dispatch decision

```
IF mission == "software-dev"
AND normalized_action ∈ {"specify","plan","tasks","implement","review"}:
    result = StepContractExecutor.execute(context)
    run_post_action_guard(action, feature_dir)
ELSE:
    fall through to existing legacy DAG dispatch unchanged
```

## Post-action guard contract

After a successful composed run, the bridge MUST invoke a guard equivalent to today's `_check_step_guards` for the same artifacts. Per-action guard inputs and pass conditions:

| Action | Pass condition |
|---|---|
| `specify` | `feature_dir / "spec.md"` exists |
| `plan` | `feature_dir / "plan.md"` exists |
| `tasks` | `tasks.md` exists AND ≥1 `tasks/WP*.md` AND every `WP*.md` has raw `dependencies:` frontmatter (reuse `_has_raw_dependencies_field`) |
| `implement` | existing `_should_advance_wp_step("implement", feature_dir)` returns true |
| `review` | existing `_should_advance_wp_step("review", feature_dir)` returns true |

Guard failure MUST surface as a non-zero CLI exit with a clear message (same UX as today).

## Outputs

| Outcome | Bridge return |
|---|---|
| Composition succeeded AND guard passed | success exit; emit invocation_id chain to trail |
| Composition raised `StepContractExecutionError` | non-zero exit; structured error with executor message |
| Composition succeeded but guard failed | non-zero exit; guard failure message |

## Invariants

1. **C-001**: Bridge MUST NOT call `ProfileInvocationExecutor` directly for composed actions; only via `StepContractExecutor.execute`.
2. **C-002**: Bridge MUST NOT generate text or call models. Composition produces invocation payloads; the host harness interprets them.
3. **C-003 / FR-007**: Lane-state writes inside any composed step or post-action guard MUST go through `emit_status_transition`. No raw lane string writes.
4. **C-008**: Composition dispatch MUST NOT fire for any mission key other than `"software-dev"` in this slice. Other missions stay on the legacy DAG path.

## Test coverage requirements

- Positive: each of the five composed actions routes through the executor and produces an invocation_id chain.
- Negative: action outside the composed set falls through to the legacy DAG path (asserted by mocking the executor and verifying no call).
- Negative: missing contract for a composed action surfaces `StepContractExecutionError` as a non-zero CLI exit.
- Guard parity: each post-action guard's failure cases match the legacy `_check_step_guards` failure cases for the same artifacts.
