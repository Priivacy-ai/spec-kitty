# Research — Decompose `doctor.py` God-Module (#2059)

**Mission:** `decompose-doctor-god-module-01KVXHFB`
**Target:** `src/specify_cli/cli/commands/doctor.py` — **3434 LOC** (the issue says 3328; the live file is 3434).
**Goal:** Decompose the RESIDUAL into cohesive, independently-testable sibling modules + a thin orchestration surface, preserving the public `spec-kitty doctor` CLI surface byte-for-byte. Research only — no source edits.

> Top-of-file pointer (`doctor.py:1-7`) already references **this** ticket: `https://github.com/Priivacy-ai/spec-kitty/issues/2059`, and notes the prior partial FR-012 extraction landed in closed #1623. Pointer is correct; no change needed.

---

## 1. Public CLI surface — the frozen contract

`app = typer.Typer(name="doctor", ...)` (`doctor.py:79`), wired into the root CLI in
`src/specify_cli/cli/commands/__init__.py:146-148` and `:206` via
`app.add_typer(doctor_module.app, name="doctor", ...)`.

**16 subcommands** (`@app.command(name=...)` decorators). Each subcommand name + every flag below is the frozen contract for a golden characterization test:

| # | Subcommand | `doctor.py:LINE` | Flags / args | Exit-code contract |
|---|-----------|------|--------------|--------------------|
| 1 | `command-files` | 637 | `--json` | 0 healthy / 1 issues |
| 2 | `skills` | 704 | `--fix`, `--json` | 0 ok / 1 gaps / 2 not-in-project/config-error |
| 3 | `tool-surfaces` | 848 | `--kind` (multi), `--tool`, `--fix`, `--json` | 0 ok / 1 issues / 2 not-in-project/unknown-kind |
| 4 | `state-roots` | 927 | `--json` | 0 healthy / 1 unhealthy |
| 5 | `workspaces` | 1031 | `--fix`, `--json` | 0 clean / 1 husks-or-error |
| 6 | `identity` | 1172 | `--json`, `--mission`, `--fail-on` | 0 / 1 fail-on-triggered or not-found |
| 7 | `topology` | 1330 | `--json`, `--mission` | 0 / 1 not-found |
| 8 | `sparse-checkout` | 1451 | `--fix` | 0 clean / 1 state-present-or-CI-refusal |
| 9 | `shim-registry` | 1591 | `--json` | 0 / 1 overdue / 2 config-error |
| 10 | `invocation-pairing` | 1712 | `--json` | 0 / 1 orphans |
| 11 | `ops` | 1842 | `--json`, `--close-stale`, `--threshold` | 0 / 1 orphans; `--threshold` requires `--close-stale` (BadParameter) |
| 12 | `orphan-daemons` | 2223 | `--json` | 0 / 1 orphans |
| 13 | `restart-daemon` | 2308 | `--json` | 0/1/2/3 (four-state restart contract) |
| 14 | `mission-state` | 2360 | `--audit`, `--fix`, `--teamspace-dry-run`, `--json`, `--mission`, `--fail-on`, `--fixture-dir`, `--include-fixtures`, `--manifest-path`, `--allow-dirty` | mode-exclusive: 0 no-mode / 2 multi-mode-or-bad-fail-on; gate exit 1 |
| 15 | `doctrine` | 2632 | `--json` | 0 healthy / 1 unhealthy (loud-over-hidden, RC=1 drives every path) |
| 16 | `coordination` | 3365 | `--json` | 0 / 1 if any `error` finding |

**Cross-module CLI coupling (must survive extraction):**
- `src/specify_cli/compat/safety_modes.py:186-194` registers safety predicates keyed on the **command path tuples** `("doctor",)`, `("doctor","skills")`, `("doctor","sparse-checkout")`. These key on subcommand *name*, not on the module, so internal extraction is transparent **iff** subcommand names are preserved byte-for-byte. `_doctor_predicate` inspects raw args for `--fix`/`--synthetic-apply` → UNSAFE; `--json`/`--mission`/`--fail-on` → SAFE.
- `src/specify_cli/__init__.py:99,164-172,282-295` has fast-path argv sniffers: `_is_doctor_skills_invocation` (`doctor skills`) and `_is_doctor_restart_daemon_invocation` (`doctor restart-daemon`). These also key on subcommand name strings, not module structure.

**Test-facing import contract** (symbols tests import directly from `specify_cli.cli.commands.doctor` — must remain importable from `doctor` after extraction, e.g. via re-export, mirroring the WP08 `_profile_health_render` precedent):
`app`, `SlashCommandGap`, `_load_slash_command_state`, `_repair_slash_command_state`,
`_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`,
`_resolve_pack_version`, `_render_org_layer_section`, `_print_overdue_details`.
(58 test files reference the doctor surface; full list in §5.)

---

## 2. Function / class inventory (top-level, with LOC + complexity)

Complexity from `radon cc` (matches Ruff C901 / Sonar S3776 ceiling = 15). Average block complexity B(7.2), 79 blocks.

**Mega-functions / high-branching (CC ≥ 13 — internal decomposition candidates):**

| Symbol | `doctor.py:LINE` | CC | Cluster |
|--------|------|----|---------|
| `skills` (cmd) | 705 | **20** | tool-surface / command-skill |
| `identity` (cmd) | 1173 | **19** | identity-audit |
| `sparse_checkout` (cmd) | 1452 | **19** | coordination/git-health |
| `_check_lane_sparse_checkout_drift` | 3255 | **19** | coordination/git-health |
| `state_roots` (cmd) | 928 | **17** | state-roots |
| `_repair_command_skill_state` | 463 | **16** | tool-surface / command-skill |
| `_print_rich_audit_report` | 1905 | 15 | mission-state-audit |
| `coordination_health` (cmd) | 3366 | 15 | coordination/git-health |
| `_print_command_skill_report` | 580 | 14 | tool-surface / command-skill |
| `shim_registry` (cmd) | 1592 | 14 | shim-registry |
| `_check_coordination_worktree_health` | 3146 | 14 | coordination/git-health |
| `tool_surfaces` (cmd) | 849 | 13 | tool-surface |
| `invocation_pairing` (cmd) | 1713 | 13 | ops/invocation |
| `ops` (cmd) | 1843 | 11 | ops/invocation |

`mission_state` (cmd, 2361) carries an explicit `# noqa: C901` — already dispatch-thin (delegates to `_validate_modes`/`_run_*` helpers) so it is structurally fine despite the suppression; the suppression can likely be dropped post-extraction once helpers move with it.

**Full top-level inventory by region:**

*Module shared infra (keep in orchestrator surface):*
- `_is_interactive_environment` 62 (CC 2), `_json_output_guard` 109, `_json_error` 125, `_CI_ENV_VARS`/`_STARTED_AT_COLUMN`/`_NOT_IN_PROJECT_MESSAGE` constants 47-59.
- `console` singleton + render re-exports imported from `_profile_health_render` (85-103).

*Cluster A — tool-surface / command-skill / slash-command (lines 135-924):*
`_vibe_skill_path_configured` 135, `_get_slash_command_agents` 240, `SlashCommandGap` (dataclass) 256, `_load_slash_command_state` 263, `_print_slash_command_report` 303, `_repair_slash_command_state` 337, `_slash_command_payload` 352, `_load_and_optionally_repair_slash_commands` 376, `_print_slash_command_payload` 405, `_load_command_skill_state` 434, `_repair_command_skill_state` 463, `_command_skill_payload` 527, `_print_command_skill_paths` 572, `_print_command_skill_report` 580, `command_files` (cmd) 637, `skills` (cmd) 704, `_configured_tool_keys` 819, `_print_tool_surface_human` 826, `tool_surfaces` (cmd) 848.

*Cluster B — state-roots (lines 927-1029):* `state_roots` (cmd) 928 — thin-ish, delegates to `state.doctor.check_state_roots`; bulk is human-render branching.

*Cluster C — workspace-husk (lines 159-237, 1031-1065):* `_workspace_husk_status_label` 159, `_emit_workspace_husk_fix` 167, `_emit_workspace_husk_report` 214, `workspaces` (cmd) 1031.

*Cluster D — identity-audit + topology (lines 1068-1375):* `_scope_to_mission` 1068, `_scope_prefixes` 1085, `_print_dup_and_ambig` 1099, `_print_identity_human` 1125, `identity` (cmd) 1172, `_read_stored_topology` 1276, `_collect_topology_rows` 1300, `_print_topology_human` 1315, `topology` (cmd) 1330.

*Cluster E — sparse-checkout remediation (lines 1377-1563):* `_render_sparse_finding` 1377, `_render_remediation_plan` 1429, `sparse_checkout` (cmd) 1451.

*Cluster F — shim-registry (lines 1566-1709):* `_print_overdue_details` 1566, `shim_registry` (cmd) 1591.

*Cluster G — ops / invocation-pairing (lines 1712-1902):* `invocation_pairing` (cmd) 1712, `_run_ops_sweep` 1792, `ops` (cmd) 1842.

*Cluster H — mission-state audit/repair/teamspace (lines 1905-2426):* `_print_rich_audit_report` 1905, `_audit_fixture_root` 1948, `_MissionStateMode` (enum) 1958, `_validate_modes` 1966, `_resolve_fail_on` 1986, `_resolve_audit_root` 2009, `_emit_mission_state` 2047, `_run_mission_repair` 2060, `_run_teamspace_dry_run_mode` 2103, `_emit_json_error` 2152, `_audit_fail_gate` 2159, `_run_audit_mode` 2181, `mission_state` (cmd) 2360.

*Cluster I — daemon (lines 2223-2358):* `orphan_daemons` (cmd) 2223, `restart_daemon_cmd` (cmd) 2308.

*Cluster J — doctrine-health collectors + command (lines 2434-3015):* `_ORG_ARTIFACT_DIRS` const 2434, `_resolve_pack_version` 2446, `_count_pack_artifacts` 2484, `_summarize_org_charter` 2494, `_collect_profile_health` 2526, `_attach_pack_health` 2589, `_build_pack_entries` 2608, `doctrine_check` (cmd) 2632, `_collect_doctrine_collisions` 2712, `_collect_org_layer_data` 2787, `_resolve_artifact_source` 2862, `_read_project_selections` 2906, `_read_org_required` 2934, `_build_selection_block` 2960.
  (The matching **render** helpers `_emit_doctrine_*` / `_render_*` are ALREADY extracted — see §3.)

*Cluster K — coordination / git-health (lines 3017-3434):* `DoctorFinding` (dataclass) 3017, `_MIN_GIT_VERSION` const 3030, `_detect_git_version` 3033, `_check_git_version` 3053, `_check_tracked_worktrees_content` 3090, `_check_coordination_worktree_health` 3146, `_check_lane_sparse_checkout_drift` 3255, `coordination_health` (cmd) 3365.

---

## 3. What is ALREADY extracted (do NOT re-extract)

The prior #1623 work extracted **two** sibling modules already present beside `doctor.py`:

- **`_doctrine_health.py`** (188 LOC) — the single-source **health MODEL**: `PackHealth`, `DoctrineHealthReport`, `build_pack_health_by_layer`. Pure data + derived-health invariants (I-H1, FR-010). `doctor.py` imports `DoctrineHealthReport` (TYPE_CHECKING, `doctor.py:40`).
- **`_profile_health_render.py`** (339 LOC) — the doctrine/profile **RENDER** helpers + the shared `console` singleton: `console`, `_SELECTION_KIND_PLURALS`, `_render_pack_invalid_profiles`, `_render_doctrine_pack`, `_render_org_charter_line`, `_emit_doctrine_human`, `_emit_doctrine_json`, `_emit_doctrine_no_packs`, `_render_org_layer_section`, `_render_selection_block_lines`. `doctor.py:85-103` re-imports these (incl. `console`) so the whole surface emits through one Console and the test-facing names stay importable from `doctor`.

> **The doctrine-health DATA COLLECTORS stay in `doctor.py`** (Cluster J) — the #1623 docstring explicitly scoped the move to render-only and left `_collect_profile_health`, `_attach_pack_health`, `_build_pack_entries`, `_collect_org_layer_data`, `_collect_doctrine_collisions`, `_build_selection_block` behind. **#2059's doctrine-health work is to extract these collectors** into a sibling (e.g. `_doctrine_collect.py`), completing the seam.

The `_auth_doctor.py` (889 LOC) sibling is **unrelated** — it backs `auth doctor` (`auth.py:127`), NOT the `doctor` CLI group. Out of scope.

---

## 4. Coupling & import map

**Module-level imports** (`doctor.py:9-41,76-105`): stdlib (`enum`, `json`, `logging`, `os`, `sys`, `warnings`, `contextlib`, `dataclasses`, `pathlib`, `collections.abc`, `typing`); third-party `typer`, `rich.console.Console`, `rich.table.Table`; first-party `core.constants.KITTY_SPECS_DIR`, `missions._read_path_resolver.resolve_feature_dir_for_mission`, `core.paths.locate_project_root`, `paths.{get_runtime_root,render_runtime_path}`, `runtime.home.get_kittify_home`. TYPE_CHECKING-only: `audit.Severity`, `compat.doctor.ShimRegistryReport`, `skills.command_installer.VerifyReport`, `skills.manifest_store.SkillsManifest`, `._doctrine_health.DoctrineHealthReport`, `status.IdentityState`. Plus the eager `._profile_health_render` re-import block.

**Deferred (function-local) imports** are the dominant pattern — nearly every command does its heavy first-party import *inside* the function body (`from specify_cli.status import ...`, `from specify_cli.doctor.ops import ...`, `from specify_cli.tool_surface.service import ...`, `from specify_cli.git.sparse_checkout import ...`, etc.). This is deliberate (keeps `doctor` import cheap; cited at `doctor.py:1476`, `:1385`) and **makes extraction low-risk**: each cluster's domain deps are already self-contained inside its functions.

**One-way-import feasibility — GOOD.** Each proposed cluster module would import only:
1. stdlib + typer/rich,
2. the shared infra (`console`, `_json_output_guard`, `_json_error`, `locate_project_root`, constants),
3. its own domain package (already function-local).

No cluster calls into another cluster's helpers. The dependency direction is uniformly *cluster → shared infra → external packages*. Clusters do **not** reference each other.

**Circular-import risks — LOW, with two named hazards:**
- **H1 (shared `console`):** `_profile_health_render.console` is the single Console instance and `doctor.py` re-imports it. Every new sibling MUST import `console` (and `_json_output_guard`/`_json_error`) from the SAME canonical location, not re-instantiate `Console()`, or `--json` stdout cleanliness and snapshot tests break. Recommendation: promote shared infra (`console`, guards, constants) into a small `_doctor_shared.py` (or keep `console` in `_profile_health_render` and import from there) and have the orchestrator + all siblings import from one place — avoids a sibling↔orchestrator cycle.
- **H2 (`merge` cross-import):** `_check_tracked_worktrees_content` (3103) imports `specify_cli.cli.commands.merge.path_is_under_worktrees` *inside the function*. Keeping it function-local in the extracted coordination sibling prevents a `doctor↔merge` module-load cycle. Do NOT hoist it to module scope.
- The orchestrator (`doctor.py`) will keep `app = typer.Typer(...)` and the `@app.command` decorators must live where `app` is defined. Two viable topologies (see data-model.md): (a) command callbacks stay in `doctor.py` and delegate to extracted pure helpers; or (b) each sibling owns its `@app.command` and registers onto the shared `app` — risk of import order / double-registration. **Recommend (a)**: thin command shells in `doctor.py`, logic in siblings — lowest CLI-surface risk, mirrors the existing `mission_state` dispatch-thin pattern.

---

## 5. Test-coverage baseline

**58 test files** touch the doctor surface. Per-cluster coverage:

| Cluster | Tests | Verdict |
|---------|-------|---------|
| tool-surface / command-skill / slash | `test_doctor_skills.py`, `test_doctor_slash_commands.py`, `tool_surface/test_*.py` (drift/findings/repair-wiring/migration-compat) | Strong |
| state-roots | `tests/specify_cli/state/` (via `state.doctor`) — command-level thin | Moderate (command render branches under-covered) |
| workspace-husk | covered via `status` husk tests + `workspaces` smoke | Moderate |
| identity-audit | `tests/doctor/test_identity_audit.py` | Strong |
| topology | `tests/cli/commands/test_doctor_topology.py` | Strong |
| sparse-checkout | `tests/integration/sparse_checkout/*` (detection, finding, non-interactive, remediation), `tests/unit/git/test_sparse_checkout_detection.py` | Strong |
| shim-registry | `tests/doctor/test_shim_registry.py` | Strong |
| ops / invocation | `tests/specify_cli/invocation/test_doctor_ops.py` | Strong |
| daemon | `test_doctor_restart_daemon.py`, `test_doctor_restart_daemon_timing.py` | Strong |
| mission-state | `tests/cli/commands/test_doctor_mission_state.py`, `tests/migration/test_mission_state_repair.py`, `tests/audit/test_audit_cli.py` | Strong |
| doctrine-health | `test_doctor_doctrine.py`, `test_doctor_doctrine_collisions.py`, `test_doctor_doctrine_org_layer.py`, `test_doctor_doctrine_selections.py`, `test_doctor_doctrine_selections_snapshot.py` (byte-pinned) | Strong |
| coordination/git-health | `tests/specify_cli/cli/commands/test_doctor_coordination.py` | Moderate |
| safety predicates | `tests/cli_gate/test_doctor_modes.py`, `test_safe_commands.py` | Strong (keyed on subcommand names) |

**GAP — no golden CLI characterization test.** Nothing today asserts the *full set of 16 subcommand names* nor each subcommand's *flag set / help / exit-code contract* as a single byte-stable snapshot. The closest is `test_doctor_doctrine_selections_snapshot.py` (one subcommand's body) and `test_doctor_modes.py` (safety, three subcommands). **A golden characterization test that enumerates `app.registered_commands` (names + param specs) and snapshots `--help` per subcommand is REQUIRED before extraction** to prove the CLI surface is byte-identical pre/post. This is the single highest-value pre-extraction artifact.

---

## 6. Risks / open questions (feed the plan)

1. **R1 — shared `console`/guards must have a single home.** Decide canonical location (`_profile_health_render.console` vs new `_doctor_shared.py`) BEFORE extracting siblings; all siblings + orchestrator import from it. Mis-instantiating `Console()` per module breaks `--json` cleanliness + the selections snapshot.
2. **R2 — test-facing re-export contract.** 11 private symbols are imported directly from `doctor` by tests (§1). After moving them, `doctor.py` must re-export (mirror the WP08 `from ._profile_health_render import _x as _x` pattern) or the plan must include updating those test imports. Re-export is lower-risk and matches precedent.
3. **R3 — `@app.command` ownership.** Pick topology (a) thin command shells in `doctor.py` delegating to siblings, vs (b) siblings own commands + register on shared `app`. Recommend (a). (See data-model.md.)
4. **R4 — golden test must land FIRST.** Sequence: write golden CLI characterization test → extract sibling → re-run golden (byte-identical) per cluster. Without it there is no objective byte-identical proof.
5. **R5 — mega-function internal decomposition.** `skills` (CC20), `identity` (CC19), `sparse_checkout` (CC19), `_check_lane_sparse_checkout_drift` (CC19), `state_roots` (CC17), `_repair_command_skill_state` (CC16) must be brought to CC≤15 *as part of* their cluster extraction (extract render/scan/repair sub-helpers + add focused tests for each — Sonar new-code-coverage). Do not merely relocate them oversized.
6. **R6 — `merge` cross-import (H2).** Keep `path_is_under_worktrees` import function-local in the coordination sibling.
7. **R7 — `__init__.py` argv fast-paths + safety_modes registrations** key on subcommand name strings. Confirm the golden test covers `doctor skills` and `doctor restart-daemon` and `doctor sparse-checkout --fix` so name preservation is enforced.
8. **OQ1 — cluster granularity.** tool-surface + command-skill + slash-command are intertwined (the `skills` command audits BOTH command-skills AND slash-commands in one payload, `doctor.py:797-799`). Open question for plan: one `_command_surface_doctor.py` sibling, or split slash vs command-skill? Leaning one sibling because the `skills` command fuses them.
9. **OQ2 — workspace-husk (Cluster C, ~120 LOC) and state-roots (Cluster B) and daemon (Cluster I)** are small. Decide whether they become standalone siblings or fold into a `_misc`/`_runtime_health` sibling. Recommend standalone for husk + daemon (cohesive), since `_misc` re-creates a mini-god-module.
