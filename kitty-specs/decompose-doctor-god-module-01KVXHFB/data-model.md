# Data Model — Target Topology for `doctor.py` Decomposition (#2059)

Not a persisted data model — this records the **target module topology** (orchestration surface + cohesive sibling modules) and the **invariants** that gate the decomposition. Source-research artifact only.

---

## Current state (pre-#2059)

```
src/specify_cli/cli/commands/
├── doctor.py                 3434 LOC  ← god-module (16 subcommands + 11 clusters of helpers)
├── _doctrine_health.py        188 LOC  ← ALREADY extracted (#1623): health MODEL
└── _profile_health_render.py  339 LOC  ← ALREADY extracted (#1623): doctrine RENDER + shared `console`
```

`_auth_doctor.py` (889) is unrelated (`auth doctor`, not the `doctor` group) — out of scope.

---

## Target topology (post-#2059)

Recommended: **thin command shells stay in `doctor.py`; per-cluster logic moves to siblings; shared infra centralized.** `doctor.py` keeps `app = typer.Typer(...)`, every `@app.command`, and delegates each body to its sibling. Test-facing private symbols are re-exported from `doctor` (WP08 precedent).

```
src/specify_cli/cli/commands/
├── doctor.py                  ← ORCHESTRATION SURFACE (target ≤ ~400 LOC)
│     • app = typer.Typer(name="doctor", ...)   (must stay here)
│     • 16 @app.command thin shells → delegate to siblings
│     • re-exports test-facing private symbols (from ._x import _y as _y)
│
├── _doctor_shared.py          ← NEW: shared infra single-home (R1)
│     • console (or re-exported from _profile_health_render), _json_output_guard,
│       _json_error, _CI_ENV_VARS, _STARTED_AT_COLUMN, _NOT_IN_PROJECT_MESSAGE,
│       _is_interactive_environment
│
├── _doctrine_health.py        ← EXISTING (#1623) — health MODEL (unchanged)
├── _profile_health_render.py  ← EXISTING (#1623) — doctrine RENDER (unchanged)
├── _doctrine_collect.py       ← NEW: doctrine-health COLLECTORS (Cluster J)
│     • _resolve_pack_version, _count_pack_artifacts, _summarize_org_charter,
│       _collect_profile_health, _attach_pack_health, _build_pack_entries,
│       _collect_doctrine_collisions, _collect_org_layer_data, _resolve_artifact_source,
│       _read_project_selections, _read_org_required, _build_selection_block,
│       _ORG_ARTIFACT_DIRS
│
├── _identity_audit.py         ← NEW (mirrors _doctrine_health naming): Cluster D
│     • identity + topology: _scope_to_mission, _scope_prefixes, _print_dup_and_ambig,
│       _print_identity_human, _read_stored_topology, _collect_topology_rows,
│       _print_topology_human   (split topology out if it grows)
│
├── _command_surface_doctor.py ← NEW: Cluster A (tool-surface + command-skill + slash)
│     • SlashCommandGap + all slash/command-skill/tool-surface helpers
│       (the `skills` command fuses command-skills + slash-commands → one sibling, OQ1)
│
├── _mission_state_doctor.py   ← NEW: Cluster H (audit / repair / teamspace-dry-run)
│     • _MissionStateMode, _validate_modes, _resolve_fail_on, _resolve_audit_root,
│       _emit_mission_state, _run_mission_repair, _run_teamspace_dry_run_mode,
│       _emit_json_error, _audit_fail_gate, _run_audit_mode, _print_rich_audit_report,
│       _audit_fixture_root
│
├── _coordination_doctor.py    ← NEW: Cluster K (git-version + worktree/sparse health)
│     • DoctorFinding, _MIN_GIT_VERSION, _detect_git_version, _check_git_version,
│       _check_tracked_worktrees_content, _check_coordination_worktree_health,
│       _check_lane_sparse_checkout_drift
│       (keep `merge.path_is_under_worktrees` import FUNCTION-LOCAL — H2)
│
├── _sparse_checkout_doctor.py ← NEW: Cluster E (remediation render + flow)
│     • _render_sparse_finding, _render_remediation_plan
│
├── _workspace_husk_doctor.py  ← NEW: Cluster C
│     • _workspace_husk_status_label, _emit_workspace_husk_fix, _emit_workspace_husk_report
│
└── _daemon_doctor.py          ← NEW: Cluster I (orphan-daemons + restart-daemon bodies)
```

Small clusters (B state-roots, F shim-registry, G ops/invocation) are already thin
delegators to external packages (`state.doctor`, `compat`, `doctor.ops`); the plan
may leave their thin shells in `doctor.py` or fold only their private render
helpers (`_print_overdue_details`, `_run_ops_sweep`) into a sibling. Decide in plan
(OQ2). Avoid a `_misc` catch-all (re-creates a mini-god-module).

---

## Invariants (decomposition acceptance gates)

| ID | Invariant | Enforced by |
|----|-----------|-------------|
| I-1 | **CLI surface byte-identical.** All 16 subcommand names, every flag, help text, and exit-code contract unchanged pre/post. | NEW golden characterization test (enumerate `app.registered_commands` + per-subcommand `--help` snapshot) — must land FIRST. |
| I-2 | **One-way imports.** Direction: `doctor.py` (orchestrator) → sibling clusters → `_doctor_shared` → external packages. No sibling↔sibling imports; no sibling→orchestrator import. | `tests/architectural/` import-graph check; review. |
| I-3 | **Single `console`/guard home.** Exactly one `Console()` instance + one `_json_output_guard`/`_json_error`, imported by all siblings + orchestrator. No per-module `Console()`. | Grep gate + selections snapshot test. |
| I-4 | **maxCC ≤ 15** for every function post-extraction (Ruff C901 / Sonar S3776). Mega-functions (skills CC20, identity 19, sparse_checkout 19, _check_lane_sparse_checkout_drift 19, state_roots 17, _repair_command_skill_state 16) decomposed into tested sub-helpers, not relocated oversized. Drop `mission_state` `# noqa: C901` if helpers move with it. | `ruff check --select C901`; per-helper focused tests. |
| I-5 | **Test-facing symbols stay importable from `doctor`.** The 11 private symbols + `app` + `SlashCommandGap` resolve via `from specify_cli.cli.commands.doctor import ...` (re-export). | Existing 58 test files; CI. |
| I-6 | **`merge` import stays function-local** in `_coordination_doctor.py` (no `doctor↔merge` module-load cycle). | Import-graph check. |
| I-7 | **Safety predicates + argv fast-paths intact.** `compat/safety_modes.py` `("doctor",*)` registrations and `__init__.py` `_is_doctor_skills_invocation`/`_is_doctor_restart_daemon_invocation` continue to fire (they key on subcommand name strings). | `tests/cli_gate/test_doctor_modes.py`, `test_safe_commands.py`; golden test covers those names. |
| I-8 | **No new responsibilities added to `doctor.py`** during this mission (god-module pointer rule, `doctor.py:3-7`). | Review. |

---

## Orchestration-surface contract (what stays in `doctor.py`)

1. `app = typer.Typer(name="doctor", help="Project health diagnostics")` (anchor for `add_typer`).
2. The 16 `@app.command(...)` decorated callbacks — kept as **thin shells**: resolve `repo_root`/flags, then call one sibling entrypoint; preserve every `raise typer.Exit(code)`.
3. Re-export block for test-facing private symbols (mirror `_profile_health_render` re-export style).
4. Import of `console`/guards/constants from `_doctor_shared` (or `_profile_health_render` for `console`).

Everything else moves to a sibling.
