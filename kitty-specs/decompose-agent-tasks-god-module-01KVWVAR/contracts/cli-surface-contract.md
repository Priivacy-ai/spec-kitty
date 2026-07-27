# Contract: frozen `agent tasks` CLI surface

This is the contract the decomposition MUST preserve byte-identically (FR-001, C-001). It is the
explicit target of the IC-01 golden characterization tests, captured against the current code
(`tasks.py:716`, typer app `name="tasks"`, `no_args_is_help=True`) BEFORE refactoring.

## Commands (9) — names, handlers, key flags

| Command | Handler (pre-refactor) | Key arguments / flags |
|---------|------------------------|------------------------|
| `move-task` | `move_task()` | `task_id`, `--to`, `--mission`, `--agent`, `--assignee`, `--shell-pid`, `--note`, `--review-feedback-file`, `--approval-ref`, `--reviewer`, `--self-review-fallback`, `--force`, `--auto-commit`, `--json` |
| `mark-status` | `mark_status()` | `task_ids`, `--status`, `--mission`, `--auto-commit`, `--json` |
| `list-tasks` | `list_tasks()` | `--lane`, `--mission`, `--json` |
| `add-history` | `add_history()` | `task_id`, `--note`, `--mission`, `--agent`, `--shell-pid`, `--json` |
| `finalize-tasks` | `finalize_tasks()` | `--mission`, `--json`, `--validate-only` |
| `map-requirements` | `map_requirements()` | `--wp`, `--refs`, `--batch`, `--replace`, `--tracker-ref`, `--mission`, `--json`, `--auto-commit` |
| `validate-workflow` | `validate_workflow()` | `task_id`, `--mission`, `--json` |
| `status` | `status()` | `--mission`, `--json`, `--stale-threshold` |
| `list-dependents` | `list_dependents()` | `wp_id`, `--mission`, `--json` |

## Invariants the golden tests assert

- **CONTRACT-1**: `spec-kitty agent tasks --help` lists exactly these 9 commands (no additions/removals/renames).
- **CONTRACT-2**: For each command, `--help` exposes exactly the flags above with unchanged names and arity.
- **CONTRACT-3**: Exit codes are unchanged: `0` success, `1` validation/refusal error, `2` usage error.
- **CONTRACT-4**: `--json` envelopes keep their existing top-level keys for success, error, and `--validate-only` paths.
- **CONTRACT-5** (commit-routing, IC-08): on a protected primary branch, the protected-primary refusal **message text and exit code are byte-identical** to pre-refactor for `move-task`, `mark-status`, and `map-requirements` — even though the decision is now made by `commit_for_mission`.

## Capture mechanism

`typer.testing.CliRunner`; normalize volatile substrings (absolute paths, timestamps, ULIDs) before
comparison; store expected help/JSON as committed fixtures. No new snapshot dependency — plain string
fixtures compared in-test, deterministic under per-worker HOME isolation.
