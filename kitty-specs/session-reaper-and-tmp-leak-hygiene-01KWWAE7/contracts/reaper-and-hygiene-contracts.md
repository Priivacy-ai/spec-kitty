# Contracts — session-reaper-and-tmp-leak-hygiene-01KWWAE7 (#1842)

## Contract 1 — Session reaper (WP01, `tests/conftest.py`)

**`pytest_sessionstart(session)`** — captures a narrow name-pattern baseline (controller only, `session.config.workerinput is None`):
- Input: REPO_ROOT.
- Output (stashed): existing `kitty-specs/{test-feature-*, *-123-test-feature, *golden-path-demo*}` dir names, `kitty/mission-test-feature-*`/`kitty/*golden-path*` branch names, `.worktrees/*` dir names.
- Invariant: shallow scan only (glob/iterdir/git) — NO deep `rglob` mtime inventory (C-001).

**`pytest_sessionfinish(session, exitstatus)`** — reaps the delta (controller only):
- `reap_session_delta(repo_root, baseline)`: removes only `current − baseline` — `rmtree` dirs, `git branch -D` branches, `git worktree prune` then `rmtree` `.worktrees/*` husks absent from `git worktree list --porcelain`.
- `sweep_tmp_residue(repo_root, baseline, run_test_home_dirs)`: delta-sweeps `prompt_tmp_dir(repo_root)` residue; removes the current run's `spec-kitty-test-homes/<run_uid>/` **by name** (from `run_test_home_dirs`).
- `assert_no_leaked_test_residue(result)`: raises if the reaped REPO_ROOT delta was non-empty (reap-then-assert).
- **Invariants**: NFR-001 (workers never reap); NFR-002 (pre-session artifacts never deleted); concurrent OTHER runs' test-homes preserved (only config-derived uids removed).

**`_current_run_test_home_dirs(config)`** — serial → `serial-<pid>`; xdist controller → `serial-<pid>` + workers' shared `<testrunuid>` (via `_xdist_testrunuid`).

## Contract 2 — /tmp prompt namespace (WP02, `src/runtime/next/_tmp_namespace.py`)

**`prompt_tmp_dir(repo_root: Path) -> Path`** — single source of truth. Returns (creating if absent) `<gettempdir()>/spec-kitty-prompts/<sha256(repo_root)[:16]>/`. Consumed by `prompt_builder.py` (`spec-kitty-next-*`), `decision.py` (both `spec-kitty-composed-*` mkstemp sites), `workflow.py` (`spec-kitty-implement|review-*`), AND WP01's reaper (the swept root). Invariant: no writer hand-copies the prefix (drift-proof test asserts `is_relative_to(prompt_tmp_dir(repo_root))`).

## Contract 3 — Workspace-context tombstone (WP03)

**Cancel** (`coordination/status_transition.py` `emit_status_transition_transactional`, both coord-topology + fallback branches): on `to_lane == CANCELED`, when all lane WPs terminal (`all(wp.lane in {done, canceled})`), call `delete_context(repo_root, worktree_dir_name(slug, mission_id=None, lane_id))`.
**Merge** (`merge/executor.py` `_phase_cleanup_worktrees_and_branches`): per lane, targeted `delete_context` (order-independent — pure unlink).
**Invariant** (C-004): only the CANCELED transition fires the cancel hook; no other transition behavior changes.
