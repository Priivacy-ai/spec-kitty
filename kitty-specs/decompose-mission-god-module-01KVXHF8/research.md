# Research — Decompose `agent/mission.py` god-module (#2056)

**Mission:** `decompose-mission-god-module-01KVXHF8`
**Target:** `src/specify_cli/cli/commands/agent/mission.py` — 4125 LOC, 62 top-level defs (61 `def` + 1 `class`), 8 `@app.command`s.
**Base:** worktree `sk-2056` on origin/main `c3814ec5a` (commit `4d8d3af0c`).
**Goal:** decompose the *remainder* into cohesive, independently-testable seams + a thin command-registration shim, preserving the public `agent mission` CLI surface byte-for-byte. **Research artifacts only — no source changes.**

## 0. Prior slice + sibling-mission context (read first)

- **Already extracted (mission 01KVMBD6):** the planning-commit *pipeline* now lives in `src/specify_cli/coordination/commit_router.py` (`commit_for_mission` + `_resolve_primary_target_branch`, `_materialise_coord_worktree`, `_resolve_mid8`, `_stage_artifacts_in_coord_worktree`, `_any_path_absent`, `_is_empty_changeset_error`, `_try_advance_ref`). **Do NOT re-extract that.**
- **Sibling #2058** (branch `kitty/mission-decompose-agent-tasks-god-module-01KVWVAR`) routed `agent/tasks.py` away from `mission.py._planning_commit_worktree`. **That branch is NOT on this worktree's base.** On THIS base, `tasks.py` still imports 3 symbols from `mission.py` (see §4). Treat that import edge as live; coordinate disposition with #2058 at merge time.

## 1. Public CLI surface — frozen contract (golden characterization test)

`app = typer.Typer(name="mission", ..., no_args_is_help=True)` (`mission.py:91`). 8 subcommands. **Every name + flag below is the byte-for-byte contract a golden CLI characterization test must pin BEFORE any extraction.**

| Subcommand (CLI name) | def | line | Positional | Options (exact flags) |
|---|---|---|---|---|
| `branch-context` | `branch_context` | 1443 | — | `--json`, `--target-branch` |
| `create` | `create_mission` | 1519 | `mission_slug` (arg) | `--mission-type`, `--mission` (hidden/deprecated), `--json`, `--target-branch`, `--friendly-name`, `--purpose-tldr`, `--purpose-context`, `--pr-bound/--no-pr-bound`, `--branch-strategy`, `--start-branch`, `--force-recreate-coordination-branch` |
| `check-prerequisites` | `check_prerequisites` | 1800 | — | `--mission`, `--json`, `--paths-only`, `--include-tasks`, `--require-tasks` |
| `record-analysis` | `record_analysis` | 1897 | — | `--mission`, `--input-file` (default `-`), `--agent`, `--json` |
| `setup-plan` | `setup_plan` | 2043 | — | `--mission`, `--json` |
| `accept` | `accept_feature` | 2606 | — | `--mission`, `--mode`, `--json`, `--lenient`, `--no-commit`, `--diagnose` |
| `merge` | `merge_feature` | 2661 | — | `--mission`, `--target`, `--strategy`, `--push`, `--dry-run`, `--keep-branch`, `--keep-worktree`, `--auto-retry/--no-auto-retry` |
| `finalize-tasks` | `finalize_tasks` | 2805 | — | `--mission`, `--json`, `--validate-only`, `--target-branch` |

Contract notes the golden test must also pin (NOT just flag names):
- **JSON envelope shape** under `--json` for success AND error paths. Every command funnels errors through `_emit_json({...})` + `typer.Exit(1)`; `_with_cli_version` / `_with_mission_aliases` decorate payloads (`mission.py:408-421`). `tests/integration/test_json_envelope_strict.py` already guards this — extend, don't replace.
- **Exit codes:** all error paths `raise typer.Exit(1)`; success is implicit 0.
- **`--mission` alias:** the option flag is `--mission` but the parameter is named `feature` in most defs — alias surface, do not rename.
- **`accept` / `merge` are thin delegators** to `top_level_accept` (`cli/commands/accept.py`) and `top_level_merge` (`cli/commands/merge.py`) imported at `mission.py:41-42`.

## 2. Function inventory (62 defs, LOC, purpose, complexity flag)

Mega = >150 LOC (needs internal decomposition); big = 60-150 LOC.

| line | LOC | name | purpose | flag |
|---|---|---|---|---|
| 103 | 10 | `_extract_wp_ids_from_task_files` | WP-id list from filenames | |
| 113 | 12 | `_branch_tree_relative_path` | repo-relative path | |
| 125 | 80 | `_stage_finalize_artifacts_in_coord_worktree` | copy planning artifacts into coord worktree, skip coord-owned status files | big |
| 205 | 8 | `_emit_console_or_json_error` | dual-channel error emit | |
| 213 | 37 | `_emit_check_prerequisites_detection_error` | check-prereq detection error payload | |
| 250 | 18 | `_paths_only_payload` | `--paths-only` projection | |
| 268 | 36 | `_emit_check_prerequisites_result` | check-prereq success payload | |
| 304 | 28 | `_collect_finalize_artifacts` | gather artifacts for finalize commit | |
| 332 | 8 | `_normalize_owned_file_path` | normalize owned-file path | |
| 340 | 12 | `_is_mission_specs_owned_file` | owned-file is under kitty-specs? | |
| 352 | 24 | `_owned_files_yaml_is_explicit_empty_list` | YAML `owned_files: []` detect | |
| 376 | 17 | `_raw_frontmatter_has_field` | raw frontmatter field present? | |
| 393 | 15 | `_invalid_mission_specs_owned_files` | owned-files validation rule | |
| 408 | 9 | `_with_cli_version` | inject `cli_version` into payload | |
| 417 | 5 | `_with_mission_aliases` | inject mission aliases into payload | |
| 422 | 5 | `_emit_json` | stdout JSON emit shim | |
| 427 | 5 | `_ensure_branch_checked_out` | no-op stub (`*args`) | |
| 432 | 5 | `_utc_now_iso` | timestamp | |
| 437 | 15 | `_read_feature_meta` | read meta.json | |
| 452 | 14 | `_read_meta_for_pr_bound` | meta read for pr-bound | |
| 466 | 16 | `_read_meta_for_emission` | meta read for event emission | |
| 482 | 9 | `_resolve_feature_target_branch` | target-branch resolution | |
| 491 | 103 | `_inject_branch_contract` | build branch-contract payload (current/base/target/strategy) | big |
| 594 | 18 | `_git_local_or_remote_branch_exists` | branch existence check | |
| 612 | 39 | `_resolve_primary_branch_for_recommendation` | primary-branch recommendation | |
| 651 | 43 | `_switch_to_start_branch` | checkout/create start branch | |
| 694 | 24 | `_enforce_git_preflight` | git preflight gate | |
| 718 | 26 | `_git_dirty_paths` | dirty-path list | |
| 744 | 26 | `_resolve_record_analysis_placement_ref` | placement ref for record-analysis (via `resolve_action_context`) | |
| 770 | 22 | `_resolve_planning_placement` | **planning-commit residue — only `tasks.py` calls it** (dead in mission.py) | |
| 792 | 71 | `_planning_commit_worktree` | **planning-commit residue — only `tasks.py` calls it** (dead in mission.py) | big |
| 863 | 29 | `_safe_load_meta` | load meta.json safely | |
| 892 | 60 | `_enforce_analysis_report_write_preflight` | record-analysis dirty-tree preflight | big |
| 952 | 29 | `_show_branch_context` | branch-context render (heavily test-patched) | |
| 981 | 47 | `_resolve_planning_branch` | (wraps imported `_resolve_planning_branch`) planning base resolution | |
| 1028 | 18 | `_artifact_has_no_git_changes` | no-diff check | |
| 1046 | 19 | `_artifact_absent_at_placement` | artifact presence at placement | |
| 1065 | 5 | `_print_artifact_unchanged` | unchanged notice | |
| 1070 | 7 | `_warn_commit_failed` | commit-failure warning | |
| 1077 | 36 | `CommitToBranchResult` (class) | typed result for `_commit_to_branch` (FR-006/D-5) — **exported, imported by tests** | |
| 1113 | 15 | `_kind_for_artifact` | artifact_type → `MissionArtifactKind` | |
| 1128 | 83 | `_commit_to_branch` | wraps `commit_router.commit_for_mission` for one artifact (used by setup-plan plan commit) | big |
| 1211 | 58 | `_find_feature_directory` | coord-aware mission-dir resolution (**most test-patched helper**) | |
| 1269 | 58 | `_resolve_mission_dir_name_primary_anchored` | primary-anchored dir-name resolution | |
| 1327 | 32 | `_primary_anchored_feature_dir` | primary-anchored feature dir | |
| 1359 | 26 | `_list_feature_spec_candidates` | enumerate spec candidates | |
| 1385 | 16 | `_sole_mission_slug_or_none` | single-mission detection | |
| 1401 | 43 | `_build_setup_plan_detection_error` | detection-error payload (also used by `lifecycle.py`) | |
| 1444 | 76 | `branch_context` | **CMD** branch-context | big |
| 1520 | 281 | `create_mission` | **CMD** create mission | **MEGA** |
| 1801 | 97 | `check_prerequisites` | **CMD** check-prerequisites | big |
| 1898 | 146 | `record_analysis` | **CMD** record-analysis | big |
| 2044 | 507 | `setup_plan` | **CMD** setup-plan | **MEGA** |
| 2551 | 33 | `_find_latest_feature_worktree` | latest worktree | |
| 2584 | 5 | `_find_feature_worktree` | worktree by slug | |
| 2589 | 18 | `_get_current_branch` | current branch | |
| 2607 | 55 | `accept_feature` | **CMD** accept (delegates to `top_level_accept`) | |
| 2662 | 144 | `merge_feature` | **CMD** merge (delegates to `top_level_merge`) | big |
| 2806 | 1227 | `finalize_tasks` | **CMD** finalize-tasks | **MEGA (x8 over ceiling)** |
| 4033 | 19 | `_parse_wp_sections_from_tasks_md` | parse WP sections (pure) | |
| 4052 | 30 | `_parse_dependencies_from_tasks_md` | parse deps (pure) | |
| 4082 | 18 | `_parse_requirement_refs_from_tasks_md` | parse req-refs from tasks.md (pure) — **imported by `tasks.py`** | |
| 4100 | 21 | `_parse_requirement_refs_from_wp_files` | parse req-refs from WP frontmatter (pure-ish) | |
| 4121 | 5 | `_parse_requirement_ids_from_spec_md` | parse req-ids from spec.md (wraps `requirement_mapping`) | |

### Mega-functions needing INTERNAL decomposition (complexity ceiling = 15)

1. **`finalize_tasks` (1227 LOC, 2806-4032)** — by far the worst. Internal phases (only 4 in-body markers exist; phases inferred from reading):
   - boundary/SaaS preflight (`run_preflight`, `mission.py:2885`)
   - feature-dir resolution (`_find_feature_directory`, ~2905)
   - target-branch resolution (`_resolve_planning_branch`, ~2995)
   - **pre-loop frontmatter read for conflict detection** (T004, `mission.py:3257`)
   - **dependency-conflict detection** "disagree-loud" (T004, `mission.py:3270`)
   - **charter-activation gate** (T044/FR-017, `mission.py:3322`)
   - **dependency resolution preserve-existing** (T004, `mission.py:3343`)
   - 8-field bootstrap-mutation loop (documented in docstring `mission.py:2839-2850`: dependencies, planning_base_branch, merge_target_branch, branch_strategy, requirement_refs, execution_mode, owned_files, authoritative_surface) — writes guarded by `frontmatter_changed and not validate_only`
   - manifest build + ownership/overlap validation
   - commit via `commit_for_mission` (`mission.py:3922-3927`)
   - SaaS `WPCreated`/`TasksCompleted` emit + dossier sync
   This single function carries the `--validate-only` read-only invariant (zero on-disk mutation) — that invariant MUST survive decomposition and be pinned by a regression test (`tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py` already exists).
2. **`setup_plan` (507 LOC, 2044-2550)** — mostly monolithic; phases: preflight → feature-dir resolution → branch-contract injection (3 `_inject_branch_contract` calls at 2291/2532) → plan commit via `_commit_to_branch` (`mission.py:2350`) → coord commits via `commit_for_mission` (2431/2480).
3. **`create_mission` (281 LOC, 1520-1800)** — mission scaffold, meta.json write, coordination-branch creation (`--force-recreate-coordination-branch`), `_inject_branch_contract` (1776), event emit.

## 3. Proposed seams

Validating/refining the issue's 3 clusters. The shim re-exports everything (see §4 invariant) so existing `mission.<symbol>` patch points keep working.

### Seam A — `mission_analysis` (record-analysis surface) [~260 LOC]
- `record_analysis` (CMD, 146 LOC), `_enforce_analysis_report_write_preflight` (60), `_resolve_record_analysis_placement_ref` (26).
- Cohesive: single command + its 2 dedicated helpers. Lowest-risk first slice. Depends on `commit_router.commit_for_mission`, `analysis_report.write_analysis_report`, `_find_feature_directory`, `_build_setup_plan_detection_error` (shared — see Seam D).

### Seam B — `mission_subcommands` (lifecycle commands) [~1900 LOC, will need sub-files]
- Commands: `branch_context`, `create_mission`, `check_prerequisites`, `setup_plan`, `accept_feature`, `merge_feature`, `finalize_tasks`.
- Helpers: `_inject_branch_contract`, `_resolve_primary_branch_for_recommendation`, `_git_local_or_remote_branch_exists`, `_switch_to_start_branch`, `_resolve_primary_branch...`, `_show_branch_context`, `_resolve_planning_branch`, `_find_latest_feature_worktree`, `_find_feature_worktree`, `_get_current_branch`, `_resolve_feature_target_branch`, `_read_meta_for_pr_bound`, `_read_meta_for_emission`, check-prereq emit helpers (`_emit_check_prerequisites_*`, `_paths_only_payload`), finalize helpers (`_collect_finalize_artifacts`, `_stage_finalize_artifacts_in_coord_worktree`, `_commit_to_branch`, `CommitToBranchResult`, `_kind_for_artifact`, `_artifact_*`, `_print_artifact_unchanged`, `_warn_commit_failed`).
- **This is too big as one module** — split per command-family: `mission_create.py`, `mission_setup_plan.py`, `mission_finalize.py`, `mission_branch_context.py`, `mission_accept_merge.py`, `mission_check_prereq.py`. The 3 mega-functions must each be internally decomposed (phase helpers) as part of their move to satisfy the 15-complexity ceiling. **Recommend: extract phase helpers FIRST (behavior-preserving, in place), then move.**

### Seam C — `mission_parsing` (parsing/validation helpers) [~280 LOC]
- **tasks.md/spec.md parsing (pure):** `_parse_wp_sections_from_tasks_md`, `_parse_dependencies_from_tasks_md`, `_parse_requirement_refs_from_tasks_md`, `_parse_requirement_refs_from_wp_files`, `_parse_requirement_ids_from_spec_md`, `_extract_wp_ids_from_task_files`.
- **owned-files validation:** `_normalize_owned_file_path`, `_is_mission_specs_owned_file`, `_owned_files_yaml_is_explicit_empty_list`, `_raw_frontmatter_has_field`, `_invalid_mission_specs_owned_files`.
- **JSON emit shims:** `_emit_json`, `_with_cli_version`, `_with_mission_aliases`, `_emit_console_or_json_error`, `_utc_now_iso`.
- Cohesive, mostly pure → ideal for direct unit tests. Highest test-leverage, low coupling. **Recommend as the second slice after Seam A.**

### Seam D — shared feature-dir resolution (`mission_feature_resolution`) [~250 LOC]
The issue folds this into "parsing-validation" but it is a distinct cohesion: `_find_feature_directory` (the single most test-patched helper — 39 references), `_resolve_mission_dir_name_primary_anchored`, `_primary_anchored_feature_dir`, `_list_feature_spec_candidates`, `_sole_mission_slug_or_none`, `_build_setup_plan_detection_error` (also imported by `lifecycle.py`), `_safe_load_meta`, `_read_feature_meta`. Consumed by Seams A, B, C. Extract this seam FIRST of all so the others import a stable resolution surface rather than each other.

### Planning-commit residue disposition (CRITICAL)
- `_planning_commit_worktree` (71 LOC, 792) and `_resolve_planning_placement` (22 LOC, 770) are **DEAD inside mission.py** — only referenced in comments (`mission.py:874,1054,2423,3916`). Their **only live caller is `tasks.py`** (`tasks.py:3704` imports `_resolve_planning_placement`; `tasks.py:3928/3936` imports + calls `_planning_commit_worktree`).
- `_planning_commit_worktree` is conceptually a sibling of `commit_router._materialise_coord_worktree` / `_stage_artifacts_in_coord_worktree`. **Safest disposition: relocate both into `coordination/commit_router.py`** (where the rest of the planning-commit pipeline already lives), updating `tasks.py`'s import to the new home. `_planning_commit_worktree` depends on `_stage_finalize_artifacts_in_coord_worktree` (`mission.py:854`) and `_safe_load_meta` (`mission.py:834`) — those move/duplicate decisions belong with the commit_router (note commit_router already has `_stage_artifacts_in_coord_worktree`, likely a near-duplicate — reconcile, don't fork).
- **Coordination risk with #2058:** sibling #2058 already moved `tasks.py` off `_planning_commit_worktree`. If #2058 merges first, the `tasks.py` import edge disappears and `_planning_commit_worktree`/`_resolve_planning_placement` become fully dead → **delete them** rather than relocate. **Open question O-1: sequence vs #2058.** Plan must branch on merge order.

## 4. Coupling & import map

- **Inbound (external consumers of mission.py symbols):**
  - `cli/commands/lifecycle.py:19` — `import ... mission as agent_feature`; calls `create_mission`, `setup_plan`, `finalize_tasks`, `_build_setup_plan_detection_error` (`lifecycle.py:72,148,185,232,286`). **Public-ish API edge.**
  - `cli/commands/agent/tasks.py` — imports `_resolve_planning_placement` (3704), `_parse_requirement_refs_from_tasks_md` (3836), `_planning_commit_worktree` (3928). **Live edge on this base (see §0/#2058).**
  - **Tests:** ~50 test files reference `commands.agent.mission`; heavy `@patch("...mission.<name>")` of module-level imports (`locate_project_root` 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×, `get_emitter`, `run_command`, `is_saas_sync_enabled`, etc.). `test_agent_feature.py` imports `CommitToBranchResult, app`. `test_create_feature_branch.py` imports `app`. `test_kind_for_artifact.py` exercises `_kind_for_artifact`. `test_agent_mission_commit_to_branch.py` exercises `_commit_to_branch`.
- **Outbound:** ~40 imports (mission.py:10-87) — `mission_runtime` (CommitTarget, MissionArtifactKind, resolve_topology, routes_through_coordination, is_coordination_artifact_residue_path), `coordination.commit_router.commit_for_mission` (lazy, inside functions), `coordination.workspace.CoordinationWorkspace` (lazy), `status` package (COORD_OWNED_STATUS_FILES, WPMetadata, read_wp_frontmatter, bootstrap_canonical_state), `ownership`, `core.*`, `sync.*`, `merge.config`, `missions._resolve_planning_branch`, `runtime.resolver`.
- **One-way-import feasibility:** YES, achievable. The shim (`mission.py`) imports FROM the new seam modules and re-exports; seam modules import from `core`/`status`/`coordination`/`mission_runtime` (lower layers) — never back into `mission.py`. Keep `commit_for_mission` / `CoordinationWorkspace` imports LAZY (already are) to avoid import-time cycles.
- **Circular-import risk:**
  - `coordination/commit_router.py` ↔ mission.py: TODAY one-way (mission → commit_router, lazy). If `_planning_commit_worktree` moves INTO commit_router, ensure commit_router does NOT import back from mission/seams. `_stage_finalize_artifacts_in_coord_worktree` + `_safe_load_meta` must travel with it (or be duplicated into commit_router's existing helpers). **Low risk if lazy imports retained.**
  - `tasks.py` ↔ mission.py: tasks.py imports parsing helper + planning-commit residue lazily (function-local imports at 3704/3836/3928). Moving those symbols only requires updating tasks.py's import target. **No cycle.**
  - `lifecycle.py` → mission.py: top-level `import`. If `create_mission`/`setup_plan`/`finalize_tasks` move to sub-modules, the shim MUST re-export them at `mission.<name>` so `agent_feature.<name>` keeps resolving. **Shim re-export is the invariant that holds lifecycle + all test patches stable.**
  - `status` packages: no direct cycle observed; mission.py is a downstream consumer.

## 5. Test-coverage baseline

- **Breadth:** ~50 test files touch the module (see file list in commit). Strong coverage of `finalize_tasks` (≥6 dedicated files: `test_mission_finalize_tasks.py`, `test_finalize_tasks_owned_files_validation.py`, `test_finalize_tasks_validate_only_readonly.py`, `test_finalize_tasks_explicit_empty_owned_files.py`, `test_feature_finalize_bootstrap.py`, `test_finalize_coord_staging.py`, `test_finalize_clobber_e2e.py`, `tests/tasks/test_finalize_*`), `create_mission` (`test_mission_create.py`, `test_create_feature_branch*.py`), `_commit_to_branch` (`test_agent_mission_commit_to_branch.py`), `_kind_for_artifact` (`test_kind_for_artifact.py`), record-analysis (`test_record_analysis_coord_worktree.py`, `test_analysis_report.py`), branch-context / `_show_branch_context` (`test_agent_feature.py`), JSON envelope (`test_json_envelope_strict.py`).
- **Per-seam coverage verdict:**
  - Seam A (record-analysis): GOOD (2 dedicated files).
  - Seam B (subcommands): GOOD for finalize/create/setup-plan; THIN for the standalone happy-path of `branch_context`/`check_prerequisites` JSON shapes at the CLI boundary.
  - Seam C (parsing): GAP — pure parsers (`_parse_dependencies_from_tasks_md`, `_parse_wp_sections_from_tasks_md`, `_parse_requirement_refs_*`) are exercised indirectly via finalize, NOT directly. Add direct unit tests when extracting (Sonar: every new helper needs a focused test).
  - Seam D (feature resolution): GOOD via the 39 `_find_feature_directory` patches, but those are mocks — add direct resolution tests on extraction.
- **Mocking fragility:** tests patch `mission.<imported-name>` extensively. **Any extraction that moves an imported name (e.g. `run_command`, `get_emitter`) off the `mission` namespace breaks ~100 patch targets.** The shim MUST re-export every currently-patched name at the `mission` module path, OR the patch targets get bulk-updated to the new module (a bulk-edit; see §6). Recommend: shim re-exports preserve patch targets → zero test churn.
- **GOLDEN CLI CHARACTERIZATION TEST: REQUIRED.** No single test currently pins the full 8-command × all-flags surface + JSON envelope as one frozen artifact. Before extraction, add a `typer.testing.CliRunner`-based golden test that asserts: `--help` for `app` lists all 8 commands; each subcommand's `--help` lists exact flags; representative success+error JSON envelopes. This is the safety net for "byte-for-byte preserved."

## 6. Risks / open questions

- **O-1 (planning-commit residue + #2058 sequencing):** disposition of `_planning_commit_worktree` / `_resolve_planning_placement` depends on whether #2058 merges first (→ delete as dead) or this mission merges first (→ relocate into commit_router and repoint `tasks.py`). The plan must encode both branches. **Decision required.**
- **O-2 (`_planning_commit_worktree` ownership):** if relocated, it belongs in `coordination/commit_router.py` (sibling of the existing pipeline). Reconcile its `_stage_finalize_artifacts_in_coord_worktree` dependency with commit_router's existing `_stage_artifacts_in_coord_worktree` (likely near-duplicate — verify before forking).
- **R-1 (test patch-target churn):** the dominant risk. Mitigate with shim re-exports (zero churn) rather than mass patch-target rewrites.
- **R-2 (mega-function complexity ceiling):** `finalize_tasks` (1227), `setup_plan` (507), `create_mission` (281) MUST be internally decomposed (<=15 complexity) as part of their move, each new phase-helper with its own focused test. This is the bulk of the engineering effort, not the file split itself.
- **R-3 (`--validate-only` read-only invariant):** finalize_tasks' zero-mutation guarantee under `--validate-only` (in-memory bootstrap, `_inmemory_frontmatter`/`_inmemory_bodies`) must survive phase extraction. Pin with existing readonly test + a new assertion that the write phase is unreachable when `validate_only`.
- **R-4 (lazy-import discipline):** keep `commit_for_mission` / `CoordinationWorkspace` imports function-local in seam modules to avoid import-time cycles with `coordination`.
- **O-3 (`accept`/`merge` thinness):** both already delegate to top-level commands — confirm they can move to a `mission_accept_merge` seam without re-importing the whole `merge`/`accept` graph at module top level.
