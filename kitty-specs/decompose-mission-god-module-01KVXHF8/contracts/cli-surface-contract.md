# Frozen CLI Surface Contract — `agent mission` (#2056)

This is the **immutable** contract the golden characterization test (WP01) pins. Any diff to command
names, flag names, flag defaults, positional args, exit codes, or JSON-envelope keys is a **regression**,
not a refactor. Source of truth: `mission.py` on base `c3814ec5a` (research.md §1).

`app = typer.Typer(name="mission", no_args_is_help=True)` — exposes exactly **8 subcommands**.

## Subcommands, args, flags

| Subcommand (CLI name) | def | Positional | Options (exact flags) |
|---|---|---|---|
| `branch-context` | `branch_context` | — | `--json`, `--target-branch` |
| `create` | `create_mission` | `mission_slug` (arg) | `--mission-type`, `--mission` (hidden/deprecated), `--json`, `--target-branch`, `--friendly-name`, `--purpose-tldr`, `--purpose-context`, `--pr-bound/--no-pr-bound`, `--branch-strategy`, `--start-branch`, `--force-recreate-coordination-branch` |
| `check-prerequisites` | `check_prerequisites` | — | `--mission`, `--json`, `--paths-only`, `--include-tasks`, `--require-tasks` |
| `record-analysis` | `record_analysis` | — | `--mission`, `--input-file` (default `-`), `--agent`, `--json` |
| `setup-plan` | `setup_plan` | — | `--mission`, `--json` |
| `accept` | `accept_feature` | — | `--mission`, `--mode`, `--json`, `--lenient`, `--no-commit`, `--diagnose` |
| `merge` | `merge_feature` | — | `--mission`, `--target`, `--strategy`, `--push`, `--dry-run`, `--keep-branch`, `--keep-worktree`, `--auto-retry/--no-auto-retry` |
| `finalize-tasks` | `finalize_tasks` | — | `--mission`, `--json`, `--validate-only`, `--target-branch` |

## Envelope & exit-code invariants (must also be pinned)

- **`--mission` alias**: the option flag is `--mission`; the underlying parameter is named `feature` in
  most defs. This alias surface is frozen — do NOT rename the parameter or the flag.
- **JSON envelope**: under `--json`, success AND error payloads funnel through `_emit_json({...})`,
  decorated by `_with_cli_version` (injects `cli_version` / `spec_kitty_version`) and
  `_with_mission_aliases` (injects mission aliases). The set of envelope keys is frozen.
- **Exit codes**: every error path `raise typer.Exit(1)` (except `setup_plan`'s SaaS-auth/boundary
  refusal which is `typer.Exit(2)`); success is implicit `0`.
- **`accept` / `merge`** are thin delegators to `top_level_accept` (`cli/commands/accept.py`) and
  `top_level_merge` (`cli/commands/merge.py`); their delegation behavior is frozen.

## Golden test assertions (WP01)

1. `CliRunner` invoking `app` with `--help` lists exactly the 8 command names above.
2. For each subcommand, `--help` lists exactly the flags in the table above (names + defaults).
3. Representative success JSON envelope keys are asserted for at least `branch-context --json` and
   `check-prerequisites --json`.
4. Representative error JSON envelope keys (e.g. `PLAN_CONTEXT_UNRESOLVED` from `setup-plan`) are asserted,
   including `error_code`, `error`, `spec_kitty_version`, and (when applicable) `available_missions` /
   `remediation` / `example_command`.
5. The contract is asserted against BOTH the base and the decomposed code (identical).
