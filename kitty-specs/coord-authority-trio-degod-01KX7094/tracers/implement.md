# Tracer: implement module decomposition

Seeded at planning (2026-07-11). Append during implement; assess at close.

## Extraction decisions (WP03, 2026-07-11)

- **New file `implement_cores.py`** houses the pure-ish decision cores + a
  `GitPort` Protocol (T015 "git injected as a port"). Every function that
  used to shell out directly (`_feature_dir_status_entries`, `_files_changed_vs_ref`,
  `_committed_meta_mapping`, `_drop_vcs_lock_only_meta`) now takes a
  keyword-only `git: GitPort = DEFAULT_GIT_PORT` parameter and calls
  `git.status_porcelain(...)` / `git.show_blob(...)` instead of `subprocess.run`
  directly. `_SubprocessGitPort` (the concrete adapter) is the ONE
  git-subprocess I/O boundary in the cores module — small, adjacent to the
  Protocol, not decision logic. Defaulting the port kept every existing
  call-site signature backward compatible (several external test files
  import these names directly with the historical git-param-free signature,
  e.g. `_drop_vcs_lock_only_meta(tmp_path, paths, None, auto_commit=True)`
  in `test_implement_vcs_lock_claim.py` — a real repo, no mocking).
  Also moved: `_exclude_coord_owned`, `_status_paths_for_commit`,
  `_is_vcs_lock_only_meta_diff`, `_parse_meta_mapping`, `_PorcelainEntry`
  (pure, no git dependency) and the placement family
  `_resolve_placement_ref` / `_resolve_claim_commit_target` /
  `_placement_coord_filter` (call the `mission_runtime` seam, not raw git).
- **New pure core `resolve_planning_artifact_staging`** (T016) extracts the
  staging DECISION out of `_ensure_planning_artifacts_committed_git`
  (structural fail-closed check, #2222 vcs-lock exclusion, dedup, idempotency
  filtering) into a `PlanningArtifactStagingPlan` NamedTuple with zero
  console/typer side effects. `_ensure_planning_artifacts_committed_git`
  became the **git executor**: it stayed in `implement.py`, calls the core,
  and turns `plan.structural` into the fail-closed print+exit and an empty
  `plan.files_to_commit` into a silent return.
- **New helper `_commit_planning_artifacts_transaction`** (also in
  `implement.py`, an executor not a core — real `BookkeepingTransaction` I/O)
  carries the back half of the old function (identifier resolution,
  destination-ref selection, transaction write+commit, legacy/coord status
  prints), further shrinking `_ensure_planning_artifacts_committed_git`.
- **`implement()` (T017) decomposed into ~11 module-level helpers** in
  `implement.py`, each owning one leaf decision/side-effect: `_detect_wp_context`,
  `_raise_if_status_commit_protected`, `_ensure_wp_claim_preconditions`,
  `_run_bulk_edit_gate_and_inference`, `_resolve_execution_lane`,
  `_resolve_active_lanes_manifest`, `_execution_mode_for_workspace`,
  `_start_wp_implementation_status`, `_report_workspace_created`,
  `_emit_blocked_on_alloc_failure`, `_commit_wp_claim_status`,
  `_build_implement_json_payload`, `_print_workspace_ready_banner`. All are
  shell-layer helpers (Typer/console/git orchestration), not cores — they
  live in `implement.py`, not `implement_cores.py`, because none of them are
  pure decision logic in the T015/T016 sense.
- **Shims**: `implement.py` re-exports the moved cores names via one bare
  `from specify_cli.cli.commands.implement_cores import (...)` block (T019),
  not added to `__all__` (which stays its pre-existing 4 names:
  `_ensure_vcs_in_meta`, `detect_feature_context`, `find_wp_file`,
  `implement`). This keeps ~15 external test files that import these
  private names directly (`_PorcelainEntry`, `_status_paths_for_commit`,
  `_placement_coord_filter`, `_resolve_claim_commit_target`,
  `_drop_vcs_lock_only_meta`, `_is_vcs_lock_only_meta_diff`, etc.) working
  unchanged.

## S3776 before → after (radon `cc -s -n B` proxy)

| Function | Before | After |
|---|---|---|
| `implement` | F (60) | C (14) |
| `_ensure_planning_artifacts_committed_git` | D (22) | B (8) |
| `_commit_planning_artifacts_transaction` (new) | — | C (12) |
| `_commit_wp_claim_status` (new) | — | C (12) |
| `_run_bulk_edit_gate_and_inference` (new) | — | B (9) |

Both `# noqa: C901` waivers removed. `implement` landed at 14 (under the
Sonar S3776<=15 gate; slightly above the "~10" local-proxy aspiration —
further extraction would have required either breaking the `top_level_implement`
6-kwarg contract or fragmenting the three source-inspected literal blocks
below, so 14 was accepted as the safe stopping point).

## Surprises / friction

- **Source-inspection tests pin literal text inside `implement()`.**
  `test_implement_placement_routing.py::test_structured_error_is_not_swallowed_as_soft_warning`
  does `inspect.getsource(implement)` and asserts `except PlacementResolutionRequired:`
  appears BEFORE the literal string `console.print(f"[yellow]Warning:[/yellow] Could not update WP status`,
  with a bare `raise` between them — so that whole outer try/except (3 clauses:
  `SafeCommitPathPolicyError` / `PlacementResolutionRequired` / generic) had
  to stay INLINE in `implement()`; only the auto-commit body inside it moved
  to `_commit_wp_claim_status`. Similarly `test_operational_context_wiring.py`
  greps `inspect.getsource(implement)` for the literal calls
  `build_operational_context_for_claim` / `require_active_role` — kept inline
  in the validate block. Two `except X:` clauses that both do a bare `raise`
  (`SafeCommitPathPolicyError` and `PlacementResolutionRequired`) look
  mergeable into one tuple-except but CANNOT be — the test greps for the
  exact substring `"except PlacementResolutionRequired:"`.
- **Line-pinned architectural ratchet.** `tests/architectural/test_no_write_side_rederivation.py`
  seeds `("src/specify_cli/cli/commands/implement.py", 88)` — an exact line
  number for the untouched `_status_commit_destination_branch` selector. The
  T019 shim-import block (11 lines) pushed it to line 99; re-pinned the seed
  (with a dated comment) rather than leaving a false-stale-allowlist failure.
  Precedent: `test(arch,#2450): re-pin write-side-rederivation allowlist
  after WP04 line drift` (same file, same pattern, prior mission).
- **A monkeypatch target moved with the code.**
  `test_wp06_sc2_paused_mission_blockers.py::_patch_implement_topology`
  patched `specify_cli.cli.commands.implement.resolve_topology` so a
  directly-invoked `_placement_coord_filter` would see a stubbed topology.
  Once `_placement_coord_filter` moved to `implement_cores.py` (its own
  `resolve_topology` import, its own module globals), the old patch target
  went inert — the stub was silently ignored and the real `resolve_topology`
  ran. Fixed by patching BOTH `implement.resolve_topology` (still used
  inline by `_commit_wp_claim_status`) and `implement_cores.resolve_topology`
  (used by the moved `_placement_coord_filter`). A textbook "patch target
  must follow the code" ripple from an extraction — worth flagging for any
  later WP that further relocates seam-calling functions.
- **`_drop_vcs_lock_only_meta` is directly git-integration-tested with the
  historical signature** (`tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py`,
  real git repos via `tmp_path`, `ref=None`) — this is why the `git: GitPort`
  parameter had to default rather than become required; a required port
  would have broken 3 external call sites this WP is not allowed to edit
  (owned_files scope).
- **A move-task blocked on a lane-branch kitty-specs/ commit.** This tracer
  append itself was first committed on the lane branch (`kitty/mission-...-lane-c`)
  alongside the WP03 code diff — `spec-kitty agent tasks move-task` correctly
  refused ("kitty-specs/ changes are not allowed on lane branches"). Reverted
  the tracer from the lane branch (a follow-up commit there) and re-applied
  it here, directly on the mission/coordination branch
  (`feat/coord-authority-trio-degod`), which is what the repo root checkout
  tracks. Mission tracer files are coord/primary-partition artifacts, not
  lane-branch content, same as spec/plan/tasks.
