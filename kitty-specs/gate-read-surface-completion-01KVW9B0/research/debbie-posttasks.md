# Debugger Debbie — Post-Tasks Implement-Loop Risk Assessment

**Date:** 2026-06-24  
**Profile applied:** debugger-debbie (DIRECTIVE_001, DIRECTIVE_003, DIRECTIVE_030, DIRECTIVE_032)  
**Mission:** gate-read-surface-completion-01KVW9B0 | `feat/gate-read-surface-completion`  
**Question:** Will the implement loop hit the same commit-surface-misresolution class as finalize-tasks?

---

## Live Evidence (not static reading)

### Root cause of the finalize-tasks commit bug — precise location

**File:** `src/specify_cli/core/paths.py`  
**Function:** `get_feature_target_branch(repo_root, mission_slug)` — **line 617**  
**Specific defect:** Uses `candidate_feature_dir_for_mission(main_root, mission_slug)` to locate `meta.json`.  
For a `coord`-topology mission whose coordination worktree is materialized, `candidate_feature_dir_for_mission` resolves to the **coordination worktree**:

```
candidate_feature_dir → .worktrees/gate-read-surface-completion-01KVW9B0-coord/kitty-specs/gate-read-surface-completion-01KVW9B0/
```

That worktree contains ONLY `status.events.jsonl` and `status.json` — **no `meta.json`**. So `meta_file.exists()` is `False`, and the function falls back to `resolve_primary_branch()` which returns `main`.

**Live proof (run against the live CLI):**
```
$ python3 -c "from specify_cli.core.paths import get_feature_target_branch; ..."
get_feature_target_branch returns: main

$ python3 -c "from mission_runtime import resolve_placement_only, MissionArtifactKind; ..."
TASKS_INDEX placement ref: main
```

The fix is a one-line change: `candidate_feature_dir_for_mission` → `primary_feature_dir_for_mission` in `get_feature_target_branch`. The same bug exists in `resolve_target_branch` (`git_ops.py:371`) which also uses `candidate_feature_dir_for_mission` for meta.json lookup.

### Is this the same seam the read sites use?

No. This is a **write-side** resolver (`get_feature_target_branch` / `commit_router._resolve_primary_target_branch`), distinct from the READ-side seam this mission addresses (`resolve_planning_read_dir` / `_primary_anchored_feature_dir` / `_resolve_mission_dir_name_primary_anchored`). The READ-side sites (FR-004/FR-009) are addressed by WP01–WP06. The WRITE-side `get_feature_target_branch` is the finalize-tasks commit-site bug — a separate seam addressed by WP07 (the site currently labeled "site #14" or the finalize-tasks commit route in FR-004/FR-009 fix set).

---

## Implement-Loop Risk Map

### Path 1: `spec-kitty implement WP01` → status-commit gate (line 1030–1038)

```python
planning_branch = resolve_feature_target_branch(mission_slug, repo_root)  # → "main"
if auto_commit:
    status_destination = _status_commit_destination_branch(repo_root, fallback_branch=planning_branch)
    # _status_commit_destination_branch returns get_current_branch(repo_root) OR fallback
    # → get_current_branch returns "feat/gate-read-surface-completion" (the real current branch)
    protected_error = _protected_branch_status_commit_error(status_destination, repo_root)
    # "feat/gate-read-surface-completion" is NOT protected → no error
```

**Verdict: SAFE.** The status-commit gate uses `get_current_branch(repo_root)` first, so the fact that `planning_branch` misresolves to `main` does NOT trigger the protected-branch gate — `feat/gate-read-surface-completion` is not in the protection list.

### Path 2: `_ensure_planning_artifacts_committed_git` (line 1098–1106 → line 353)

```python
# implement.py line 1098-1106
_ensure_planning_artifacts_committed_git(
    ...
    planning_branch=planning_branch,  # → "main" (misresolved)
    ...
)
# Inside, line 353:
if current_branch != planning_branch:
    console.print(f"\n[red]Error:[/red] Planning artifacts must be committed on {planning_branch}.")
    raise typer.Exit(1)
```

`current_branch` = `feat/gate-read-surface-completion`, `planning_branch` = `main`.  
**BLOCKED.** `implement WP01` will refuse to start because current branch does not match the misresolved `planning_branch`.

This is **the same class** as the finalize-tasks commit refusal — `planning_branch` resolves to `main` via `get_feature_target_branch` → `candidate_feature_dir_for_mission` → coord worktree → no `meta.json` → fallback `main`.

### Path 3: Status-claim commit (line 1309–1317)

```python
_cur_branch = _get_cur_branch(repo_root) or planning_branch
safe_commit(..., target=CommitTarget(ref=_cur_branch), ...)
```

**SAFE** even if reached: uses `get_current_branch` first, not `planning_branch`. Would land on `feat/gate-read-surface-completion`.

### Path 4: `emit_status_transition` / status event routing

Status emit uses `resolve_status_surface_with_anchor` (not `get_feature_target_branch`) — **independent path, unaffected.**

---

## Finalize-Tasks Commit Bug — Precise Fix Target

| Element | Value |
|---------|-------|
| **File** | `src/specify_cli/core/paths.py` |
| **Function** | `get_feature_target_branch` |
| **Line** | 617 (`candidate_feature_dir_for_mission(main_root, mission_slug) / "meta.json"`) |
| **Bug** | `candidate_feature_dir_for_mission` → coord worktree (no `meta.json`) → fallback `main` |
| **Fix** | Change to `primary_feature_dir_for_mission(main_root, mission_slug) / "meta.json"` |
| **Same-class twin** | `src/specify_cli/core/git_ops.py:resolve_target_branch` line 371 — same pattern |
| **Same-class twin** | `commit_router._resolve_primary_target_branch` calls `get_feature_target_branch` — transitively fixed by the root fix |

This is a **separate write-surface resolver** from the read sites FR-004/FR-009 are fixing. The mission spec bundles #2085/#2107; finalize-tasks' commit site is NOT in the current WP map but was identified via live dogfooding repro (`research/dogfood-finalize-tasks-repro.md`).

---

## Chicken-and-Egg Bootstrap Analysis

**The question:** does implementing WP01 require the WP01 fix to be live in the CLI?

WP01's fix is in `mission.py` (read-side chokepoint helper + retire bespoke helper pair). It does NOT fix `get_feature_target_branch` in `paths.py` — that is the finalize-tasks commit bug and is a separate seam.

So:
- **WP01 code changes** do not unblock the implement loop — the blocker is `get_feature_target_branch`, not the read-side seam.
- The finalize-tasks commit bug fix (paths.py:617 / git_ops.py:371) IS a separate scope addition, but it would need to be applied to the LIVE CLI for `implement WP01` to proceed without a workaround.

**Chicken-and-egg status: YES, partial.** The implement loop (`_ensure_planning_artifacts_committed_git`) is blocked by the same `get_feature_target_branch` bug that blocked finalize-tasks — and no WP in the current task map explicitly fixes `paths.py:617`.

---

## Workaround / Unblock Sequence

### Option A: Run flattened (per `project_flat_mission_implement_loop_friction`)

The flat-mission implement loop is the proven mode for write-surface missions. For this coord-topology mission:

1. **Do NOT flatten** — `coordination_branch` in `meta.json` is architecture; removing it changes topology.
2. Instead, use `--no-auto-commit` to bypass the `_ensure_planning_artifacts_committed_git` block:
   ```bash
   spec-kitty implement WP01 --mission gate-read-surface-completion-01KVW9B0 --no-auto-commit
   ```
   This skips line 1031 (`if auto_commit:`) entirely, meaning the `planning_branch=main` misresolution never hits the guarded path. The worktree is allocated, status events are emitted to the coord branch (unaffected), and `implement` completes.
3. After implement completes: commit status artifacts manually from `feat` to satisfy the session.

**Per-WP friction (minimal):**
- `spec-kitty implement WPxx --no-auto-commit` (skip the planning-branch check)
- Status artifact commit: `spec-kitty agent tasks update <mission> WPxx in_progress` from the main checkout (runs `append_event` + `materialize`, then `git add` + needs a manual commit since `stage_update` stages but does not commit)
- OR: run `git commit` manually after the status update stages files

This matches the documented flat-mission pattern: status moves from the main checkout, code on the lane worktree.

### Option B: Apply the root fix to the live CLI first (recommended if WP01 fix can be hot-patched)

Fix `src/specify_cli/core/paths.py:617` and `src/specify_cli/core/git_ops.py:371`:

```python
# paths.py:617 — change:
meta_file = candidate_feature_dir_for_mission(main_root, mission_slug) / "meta.json"
# to:
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission
meta_file = primary_feature_dir_for_mission(main_root, mission_slug) / "meta.json"
```

Apply and `pip install -e .` (or the editable install is already live). Then `implement WP01` proceeds without workaround.

**This fix is NOT owned by any current WP** — it should be added to the scope (as the finalize-tasks commit site, the write-side twin of FR-004/FR-009). Candidate: add to WP07 (bookkeeping sweep) or as a new WP on the scope, or apply as a hot-fix commit before starting WP01.

### Recommended unblock sequence

1. **Add `paths.py:617` + `git_ops.py:371` to mission scope** — either fold into WP07 or add WP11 (this is the write-side residual already noted in `dogfood-finalize-tasks-repro.md`).
2. **Implement the fix NOW in the live working tree** (the `feat` branch already has the editable install) without waiting for a full WP cycle — it is a 2-line one-seam fix.
3. Commit to `feat/gate-read-surface-completion` manually (same pattern used for finalize-tasks workaround).
4. Proceed with `spec-kitty implement WP01` normally.

If the operator prefers NOT to expand scope now:
- Use `--no-auto-commit` mode for each WP (Option A workaround).
- Run status moves manually from `feat`.

---

## Summary Verdict

| Question | Answer |
|----------|--------|
| Implement loop blocked? | **YES** — `_ensure_planning_artifacts_committed_git` exits 1 when `planning_branch=main ≠ current feat/…` |
| Same class as finalize-tasks bug? | **YES** — `get_feature_target_branch` → `candidate_feature_dir` → no `meta.json` → fallback `main` |
| Fix location | `src/specify_cli/core/paths.py:617` (`get_feature_target_branch`) + `src/specify_cli/core/git_ops.py:371` (`resolve_target_branch`) |
| Covered by existing WPs? | **NO** — not in current WP01–WP10 scope; write-side twin, separate seam |
| Chicken-and-egg? | **YES** — WP01 fix (read-side) does not unblock the implement loop; the blocking bug is a write-side resolver (paths.py) |
| Workable without fix? | **YES** — `--no-auto-commit` mode + manual status commits; flattened-style per-WP friction |
| Recommended action | Hot-fix `paths.py:617` + `git_ops.py:371` on `feat` BEFORE implement WP01, then proceed normally |

---

## Falsified Hypotheses

| Hypothesis | Verdict | Evidence |
|-----------|---------|----------|
| "Status-commit gate will fire on protected `main`" | FALSIFIED | `_status_commit_destination_branch` returns `get_current_branch(repo_root)` = `feat/…`, not `planning_branch` |
| "implement loop is safe because it uses a different resolver than finalize-tasks" | FALSIFIED | Both trace to `get_feature_target_branch` via `resolve_feature_target_branch` (implement.py:206-213) → `resolve_target_branch` (git_ops.py:331) → `candidate_feature_dir_for_mission` |
| "WP01 fix (read-side) also fixes the implement-loop block" | FALSIFIED | WP01 modifies `mission.py` read helpers; the block is in `paths.py:617` (write-side) |
| "Flattening (removing `coordination_branch`) would unblock like it was tried for finalize-tasks" | PARTIALLY FALSIFIED — dogfood repro proved flatten did NOT help finalize-tasks either | The commit surface bug is in `get_feature_target_branch`, which falls back to `main` regardless of topology |
