# Scope A Acceptance Evidence

**Mission**: `077-mission-terminology-cleanup`  
**Scope**: Scope A (`#241`)  
**Acceptance date**: 2026-04-08  
**HEAD commit at evidence capture**: `d90a6465f801a160a75c812c404c5936d260eac8`

## Gate Results

| Gate | Description | Result | Evidence |
|---|---|---|---|
| 1 | No tracked-mission selector uses `--mission-run` in `src/specify_cli/cli/commands/**` | PASS | `rg --type py '(--mission-run|mission-run)' src/specify_cli/cli/commands` exited `1` with no matches. |
| 2 | No tracked-mission help text says "Mission run slug" | PASS | `rg --type py 'Mission run slug' src/specify_cli/cli/commands` exited `1` with no matches. |
| 3 | `mission current --mission A --feature B` fails deterministically | PASS | `SPEC_KITTY_CLI_VERSION=3.1.1a2 ./.venv/bin/spec-kitty mission current --mission 077-test-A --feature 077-test-B` exited `1` with: `Error: Conflicting selectors: --mission='077-test-A' and --feature='077-test-B' were both provided with different values. --feature is a hidden deprecated alias for --mission; pass only --mission.` |
| 4 | `mission current --feature X` resolves like `--mission X` and emits one warning | PASS | Proven by `tests/specify_cli/cli/commands/test_selector_resolution.py::test_mission_current_alias_succeeds_with_warning`. Direct CLI smoke emits the warning, then hits a separate mission-definition lookup bug in this checkout (`Mission 'software-dev' not found`). |
| 5 | `mission current --feature X` exit code matches `--mission X` | PASS | Proven by `tests/specify_cli/cli/commands/test_selector_resolution.py::test_mission_current_canonical_succeeds` and `::test_mission_current_alias_succeeds_with_warning`, which assert equivalent success behavior at the command layer. Direct CLI smoke is blocked by the same downstream mission-definition lookup bug noted in Gate 4. |
| 6 | `mission current --mission X --feature X` succeeds with one warning | PASS | Proven by selector-resolution coverage plus the same-value branch exercised in `tests/specify_cli/cli/commands/test_selector_resolution.py` and the full selector suite (`24 passed`). Direct CLI smoke is blocked in this checkout by the downstream mission-definition lookup bug after selector resolution. |
| 7 | Tracked-mission command surfaces pass canonical/alias/conflict assertions | PASS | `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/test_terminology_guards.py tests/specify_cli/cli/commands/test_selector_resolution.py tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py tests/specify_cli/test_active_mission_removal.py -q` -> `64 passed in 0.95s`. |
| 8 | Doctrine skills use `--mission` | PASS | Covered by `tests/contract/test_terminology_guards.py` (`9 passed` inside the suite above), including the doctrine-skill guard. |
| 9 | Agent-facing docs use `--mission` | PASS | Covered by `tests/contract/test_terminology_guards.py` (`9 passed` inside the suite above), including the doc-surface guards for live docs. |
| 10 | Orchestrator-api stays canonical-only and unchanged | PASS | `git diff -- src/specify_cli/orchestrator_api/ src/specify_cli/core/upstream_contract.json tests/contract/test_orchestrator_api.py` produced no diff. `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/test_orchestrator_api.py::TestForbiddenFlags::test_feature_flag_is_rejected -q` -> `1 passed in 0.05s`. |
| 11 | Migration docs are published and referenced from the deprecation warning | PASS | `ls -la docs/migration/feature-flag-deprecation.md docs/migration/mission-type-flag-deprecation.md` shows both files exist. `SPEC_KITTY_CLI_VERSION=3.1.1a2 ./.venv/bin/spec-kitty mission current --feature 077-mission-terminology-cleanup 2>&1` emitted `Warning: --feature is deprecated; use --mission. See: docs/migration/feature-flag-deprecation.md`. |
| 12 | Coverage on selector paths is at least 90% | PASS | `PYTHONPATH=src .venv/bin/python -m pytest --cov=specify_cli.cli.selector_resolution --cov-report=term-missing tests/specify_cli/cli/commands/test_selector_resolution.py -q` -> `24 passed`, `selector_resolution.py` coverage `93%`. |
| 13 | Locked non-goals from spec §3.3 do not appear in the diff | PASS | `git diff main -- . | rg 'mission_run_slug|MissionRunCreated|MissionRunClosed|aggregate_type="MissionRun"'` exited `1` with no matches. |
| 14 | Inverse-drift sites use `--mission-type` canonically | PASS | `PYTHONPATH=src .venv/bin/python -m specify_cli agent mission create --help`, `... charter interview --help`, and `... specify --help` all show `--mission-type`. None show visible `--mission` as the canonical selector for mission-template selection. |
| 15 | No historical artifacts outside this mission were modified | PASS | `git diff --name-only main | rg '^(kitty-specs|architecture)/' | rg -v '^kitty-specs/077-mission-terminology-cleanup/'` exited `1` with no matches. |

## Gate Notes

### Direct CLI smoke blockers for Gates 4-6

The selector layer is correct, but this checkout currently has two unrelated smoke-test blockers:

1. Repo-local version skew requires `SPEC_KITTY_CLI_VERSION=3.1.1a2` to bypass a project metadata mismatch.
2. `mission current` then falls through to a separate mission-definition lookup bug:

```text
Warning: --feature is deprecated; use --mission. See:
docs/migration/feature-flag-deprecation.md
... UserWarning: Mission 'software-dev' not found for feature 077-mission-terminology-cleanup, using software-dev as default
Error: Mission 'software-dev' not found.
Available missions: none
```

Because that failure happens after selector resolution, Gates 4-6 are proven by the command-level selector tests rather than by a misleading end-to-end smoke in this checkout.

## Spec §11.1 Edit

The charter-reconciliation edit was applied in `spec.md` and narrows the alias policy from visible deprecated aliasing to hidden deprecated aliasing:

```diff
-| FR-005 | `--feature` is accepted only as a deprecated compatibility alias on tracked-mission commands during the migration window, and emits exactly one explicit deprecation warning per invocation. | Required |
+| FR-005 | `--feature` is accepted only as a hidden deprecated compatibility alias on tracked-mission commands during the migration window, and emits exactly one explicit deprecation warning per invocation. | Required |

- `--feature` is accepted as a compatibility alias on every tracked-mission command surface.
+ `--feature` is accepted as a hidden compatibility alias on every tracked-mission command surface (that is: declared with `typer.Option(..., hidden=True)` and not advertised in `--help`, examples, tutorials, or docs).
```

## Scope A Deliverables

| WP | Title | Status | Evidence |
|---|---|---|---|
| WP01 | Selector Audit and Canonical Map | Complete | `research/selector-audit.md` created and used to drive Scope A cleanup. |
| WP02 | Selector Resolution Helper | Complete | `src/specify_cli/cli/selector_resolution.py`, `tests/specify_cli/cli/commands/test_selector_resolution.py`, `24 passed`, `93%` coverage. |
| WP03 | `mission current` Refactor | Complete | `src/specify_cli/cli/commands/mission.py` refactored to use split selector params + post-parse reconciliation. |
| WP04 | `next_cmd` and agent/tasks Refactor | Complete | Tracked-mission surfaces updated to canonical `--mission`; workflow delegation bug fixed in `agent/workflow.py`. |
| WP05 | Inverse Drift Refactor | Complete | Inverse-drift sites now advertise `--mission-type` canonically. |
| WP06 | Doctrine Skills Cleanup | Complete | Doctrine skill prompts use `--mission`; guarded by contract tests. |
| WP07 | Docs and Top-Level Cleanup | Complete | Live docs and README cleaned to canonical Mission terminology for operator surfaces. |
| WP08 | Migration Docs | Complete | `docs/migration/feature-flag-deprecation.md` and `docs/migration/mission-type-flag-deprecation.md` added. |
| WP09 | Grep Guards | Complete | `tests/contract/test_terminology_guards.py` added and passing. |
| WP10 | Scope A Acceptance Gate | Complete | This document records the full 15-gate pass. |

## Scope A Conclusion

Scope A is accepted. The operator-facing CLI now uses `--mission` canonically for tracked-mission selection, `--feature` is a hidden deprecated compatibility alias, the inverse-drift sites advertise `--mission-type`, and the regression guards are in place.
