# Contract — Frozen `spec-kitty doctor` CLI Surface

**Status:** FROZEN for #2059. This is the byte-identical contract the WP01 golden characterization harness pins and every extraction WP must preserve (FR-001, C-001, I-1).

`app = typer.Typer(name="doctor", help="Project health diagnostics")` (`doctor.py:79`), registered onto the root CLI in `cli/commands/__init__.py:146-148,206` via `app.add_typer(doctor_module.app, name="doctor", ...)`. The `app` object and the 16 `@app.command` decorators MUST remain anchored in `doctor.py` (the `add_typer` target). Command *bodies* may delegate to siblings; command *names, flags, help, and exit codes* may not change.

## The 16 subcommands (frozen)

| # | Subcommand (frozen name) | Flags / args | Exit-code contract |
|---|--------------------------|--------------|--------------------|
| 1 | `command-files` | `--json` | 0 healthy / 1 issues |
| 2 | `skills` | `--fix`, `--json` | 0 ok / 1 gaps / 2 not-in-project or config-error |
| 3 | `tool-surfaces` | `--kind` (multi), `--tool`, `--fix`, `--json` | 0 ok / 1 issues / 2 not-in-project or unknown-kind |
| 4 | `state-roots` | `--json` | 0 healthy / 1 unhealthy |
| 5 | `workspaces` | `--fix`, `--json` | 0 clean / 1 husks-or-error |
| 6 | `identity` | `--json`, `--mission`, `--fail-on` | 0 / 1 fail-on-triggered or not-found |
| 7 | `topology` | `--json`, `--mission` | 0 / 1 not-found |
| 8 | `sparse-checkout` | `--fix` | 0 clean / 1 state-present or CI-refusal |
| 9 | `shim-registry` | `--json` | 0 / 1 overdue / 2 config-error |
| 10 | `invocation-pairing` | `--json` | 0 / 1 orphans |
| 11 | `ops` | `--json`, `--close-stale`, `--threshold` | 0 / 1 orphans; `--threshold` without `--close-stale` → `BadParameter` |
| 12 | `orphan-daemons` | `--json` | 0 / 1 orphans |
| 13 | `restart-daemon` | `--json` | 0/1/2/3 (four-state restart contract) |
| 14 | `mission-state` | `--audit`, `--fix`, `--teamspace-dry-run`, `--json`, `--mission`, `--fail-on`, `--fixture-dir`, `--include-fixtures`, `--manifest-path`, `--allow-dirty` | mode-exclusive: 0 no-mode / 2 multi-mode or bad-fail-on; gate exit 1 |
| 15 | `doctrine` | `--json` | 0 healthy / 1 unhealthy (loud-over-hidden: RC=1 drives every unhealthy path) |
| 16 | `coordination` | `--json` | 0 / 1 if any `error` finding |

## Cross-module coupling that keys on these names (must survive extraction)

- **`compat/safety_modes.py:186-194`** registers safety predicates on the command-path tuples `("doctor",)`, `("doctor","skills")`, `("doctor","sparse-checkout")`. `_doctor_predicate` inspects raw args: `--fix`/`--synthetic-apply` → UNSAFE; `--json`/`--mission`/`--fail-on` → SAFE. Keyed on subcommand *name*, not module — transparent to extraction iff names are byte-preserved.
- **`__init__.py:99,164-172,282-295`** argv fast-paths: `_is_doctor_skills_invocation` (`doctor skills`) and `_is_doctor_restart_daemon_invocation` (`doctor restart-daemon`). Also keyed on name strings.

The golden harness MUST exercise these three name paths: `doctor skills`, `doctor restart-daemon`, `doctor sparse-checkout --fix`.

## Test-facing import contract (11 private symbols + 2 public)

Resolvable via `from specify_cli.cli.commands.doctor import ...` before AND after extraction (re-export from the `doctor` shim, mirroring the `_profile_health_render` `from ._x import _y as _y` precedent — FR-006, I-5):

- Public: `app`, `SlashCommandGap`
- Private (11): `_load_slash_command_state`, `_repair_slash_command_state`, `_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`, `_resolve_pack_version`, `_render_org_layer_section`, `_print_overdue_details` — plus the two slash/collector entrypoints the 58 doctor test files already import. The authoritative list is re-validated against `git grep "from specify_cli.cli.commands.doctor import"` in WP11.

## Invariants (acceptance gates)

- **I-1** CLI surface byte-identical (this contract) — golden harness.
- **I-3** single `console`/guard home — no per-module `Console()`.
- **I-4** every function ≤15 CC.
- **I-5** test-facing symbols re-export from `doctor`.
- **I-6** `merge.path_is_under_worktrees` import stays function-local.
- **I-7** safety predicates + argv fast-paths intact (keyed on the frozen names).
