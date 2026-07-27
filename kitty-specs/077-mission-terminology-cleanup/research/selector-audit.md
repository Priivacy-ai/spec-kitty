# Selector Audit and Canonical Map

**Mission**: `077-mission-terminology-cleanup`  
**Audit date**: 2026-04-08  
**Baseline HEAD commit**: `d90a6465f801a160a75c812c404c5936d260eac8`  
**Method**: `rg` over `src/specify_cli/cli/commands/**` for `typer.Option(...)` declarations mentioning `--mission`, `--feature`, or `--mission-run`, plus cross-reference against direct `require_explicit_feature(...)` callers.

## Summary

| Classification | Site count | Notes |
|---|---:|---|
| tracked-mission | 34 | Mission slug selectors that resolve to `kitty-specs/<slug>/` or equivalent mission-scoped context. |
| inverse-drift | 5 | `--mission` means mission type / blueprint selector, so canonical flag must be `--mission-type`. |
| runtime-session | 0 | No remaining `--mission-run` selectors exist under `src/specify_cli/cli/commands/**` in the live command surface. |
| other / mission-adjacent | 3 | Mission-adjacent selectors that are not tracked-mission slugs (`charter status`, `config`, wrapper aliases). |

## Tracked-Mission Sites

| File | Line | Function | Current declaration | Help string | Classification | Target alias list | Calls `require_explicit_feature`? |
|---|---:|---|---|---|---|---|---|
| `src/specify_cli/cli/commands/accept.py` | 118 | `accept` | `--mission` + hidden `--feature` | `Mission slug to accept` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/context.py` | 240 | `mission_resolve_command` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/implement.py` | 388 | `implement` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `detect_feature_context()` |
| `src/specify_cli/cli/commands/lifecycle.py` | 48 | `plan` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/materialize.py` | 24 | `materialize` | `--mission` + hidden `--feature` | `Mission slug to materialise` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/merge.py` | 536 | `merge` | `--mission` + hidden `--feature` | `Mission slug when merging from main branch` | tracked-mission | `--mission` canonical + hidden `--feature` | no |
| `src/specify_cli/cli/commands/mission.py` | 175 | `current_cmd` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/mission_type.py` | 175 | `current_cmd` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | no |
| `src/specify_cli/cli/commands/next_cmd.py` | 22 | `next_step` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/research.py` | 23 | `research` | `--mission` + hidden `--feature` | `Mission slug to target` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/validate_encoding.py` | 20 | `validate_encoding` | `--mission` + hidden `--feature` | `Mission slug to validate` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/validate_tasks.py` | 26 | `validate_tasks` | `--mission` + hidden `--feature` | `Mission slug to validate` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/agent/context.py` | 70 | `resolve_context` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `resolve_selector` |
| `src/specify_cli/cli/commands/agent/mission.py` | 609 | `check_prerequisites` | `--mission` only at baseline | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | direct |
| `src/specify_cli/cli/commands/agent/mission.py` | 743 | `setup_plan` | `--mission` only at baseline | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | direct |
| `src/specify_cli/cli/commands/agent/mission.py` | 1030 | `accept_feature` | `--mission` only at baseline | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | direct |
| `src/specify_cli/cli/commands/agent/mission.py` | 1206 | `finalize_tasks` | `--mission` only at baseline | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | direct |
| `src/specify_cli/cli/commands/agent/status.py` | 109 | `emit` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/status.py` | 222 | `materialize` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/status.py` | 307 | `doctor` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_resolve_feature_dir()` |
| `src/specify_cli/cli/commands/agent/status.py` | 523 | `migrate` | `--mission/-f` + hidden `--feature` | `Single mission slug to migrate` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/status.py` | 579 | `validate` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/status.py` | 722 | `reconcile` | `--mission/-f` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 851 | `move_task` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 1399 | `mark_status` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 1584 | `list_tasks` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 1667 | `add_history` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 1741 | `finalize_tasks` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 1940 | `map_requirements` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 2218 | `validate_workflow` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 2310 | `status` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/tasks.py` | 2674 | `list_dependents` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/workflow.py` | 358 | `implement` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |
| `src/specify_cli/cli/commands/agent/workflow.py` | 1063 | `review` | `--mission` + hidden `--feature` | `Mission slug` | tracked-mission | `--mission` canonical + hidden `--feature` | indirect via `_find_mission_slug()` |

## Inverse-Drift Sites

| File | Line | Function | Current declaration | Help string | Classification | Target alias list |
|---|---:|---|---|---|---|---|
| `src/specify_cli/cli/commands/agent/mission.py` | 487 | `create_mission` | `--mission-type` + hidden `--mission` | `Mission type` | inverse-drift | `--mission-type` canonical + hidden `--mission` |
| `src/specify_cli/cli/commands/charter.py` | 67 | `interview` | `--mission-type` + hidden `--mission` | `Mission type for charter defaults` | inverse-drift | `--mission-type` canonical + hidden `--mission` |
| `src/specify_cli/cli/commands/charter.py` | 189 | `generate` | `--mission-type` + hidden `--mission` | `Mission type for template-set defaults` | inverse-drift | `--mission-type` canonical + hidden `--mission` |
| `src/specify_cli/cli/commands/lifecycle.py` | 26 | `specify` | `--mission-type` + hidden `--mission` | `Mission type` | inverse-drift | `--mission-type` canonical + hidden `--mission` |
| `src/specify_cli/cli/commands/config_cmd.py` | 25 | `config` | `--mission` only | `Mission to resolve assets for` | inverse-drift | `--mission-type` canonical + hidden `--mission` |

## Runtime-Session Sites

No live `--mission-run` selector remains in `src/specify_cli/cli/commands/**` as of the audit. The remaining `--mission-run` hits are all in doctrine skill markdown and docs, not in executable CLI command declarations.

## Helper Consumer Cross-Reference

| Surface | Location | Relationship to `require_explicit_feature(...)` |
|---|---|---|
| selector helper | `src/specify_cli/cli/selector_resolution.py` | canonical missing-value path; delegates to `require_explicit_feature(None, command_hint=...)` |
| execution context | `src/specify_cli/core/execution_context.py` | still consumes direct mission slug input |
| agent mission dir lookup | `src/specify_cli/cli/commands/agent/mission.py::_find_feature_directory` | direct consumer at baseline; tracked-mission downstream sites still depend on it |
| agent status resolution | `src/specify_cli/cli/commands/agent/status.py::_find_mission_slug` | baseline direct consumer; now a helper wrapper site |
| agent context dir lookup | `src/specify_cli/cli/commands/agent/context.py::_find_feature_directory` | baseline direct consumer; now a helper wrapper site |
| acceptance layer | `src/specify_cli/acceptance.py` | direct consumer outside CLI declaration layer |

## Notes and Ambiguities

1. The verified-known list from the spec was incomplete relative to the live command surface. In particular, `accept`, `agent/status`, `agent/context`, `merge`, `mission_type current`, and multiple `agent/mission` subcommands were still mission-slug selectors even though they were not named in the original WP list.
2. `config_cmd.config` is the main inverse-drift site outside the three verified-known examples. Its `mission` parameter defaults to `software-dev` and is passed to asset resolution as a mission type / template-set selector, not a tracked mission slug.
3. There are no surviving executable `--mission-run` selectors under `src/specify_cli/cli/commands/**`. The lingering `--mission-run` terminology is now concentrated in doctrine skill markdown and operator documentation, which makes those files Scope A doc/skill cleanup rather than command-surface cleanup.
4. `merge.py` and several `agent/mission.py` subcommands already carried some compatibility alias behavior at baseline, but the audit still classifies them as tracked-mission surfaces because they resolve a mission slug and must follow the same canonical migration policy.
5. The command-surface audit intentionally excludes `src/specify_cli/orchestrator_api/**`; those are machine-facing compatibility surfaces handled in Scope B and by the upstream contract.
