# Research — Coord-Read Residuals (#2185 + #2186)

## Phase 0 — Code-state research (3 parallel agents, verified against `main`)

- **Kind corrections (debugger-verified against `is_primary_artifact_kind`):** 6 of 10 Lane-A issue labels are wrong — `merge/resolve.py:98`, `cli/commands/merge.py:269`, `lanes/worktree_allocator.py:360` read `meta.json` (PRIMARY_METADATA) not LANE_STATE; `lanes/recovery.py:611` reads `lanes.json` (LANE_STATE) not `tasks/`. `merge/executor.py`/`done_bookkeeping.py:237`/`recovery.py:356` are mixed PRIMARY+STATUS. Route by real kind.
- **Husk failure mode real:** `meta.json`/`lanes.json`/`tasks/` are PRIMARY-only post-#2106; coord-aware resolve lands on the empty `-coord` husk. `next_cmd.py:187/253` swallow `FileNotFoundError`; `:631` `get_mission_type` returns default `software-dev` (wrong-routing, not just telemetry).
- **Gate blindness:** the dir-read scanner matches only `resolver / "tasks"|"lanes.json"|"*.md"` joins; identity reads (function-call shape) escape both arms → a net-new arm is required.
- **#2115 sequencing:** `implement.py:1389` is correct only via the `:1018` fallback; guards must precede fallback removal.

## Phase 0.5 — Post-plan brownfield check (2 lenses, 2026-06-26)

### Foldable-issue search (planner-priti) — CLEAN CAMPSITE

No new issues to fold; #2185/#2186 *are* the mission. Adjacent open issues are correctly partitioned and must stay separate:

| # | Relation | Verdict |
|---|----------|---------|
| #2115 | implement-loop twin (owned by sibling, C-009) | NO-FOLD (hard boundary) |
| #2167 | repo-root `scripts/tasks/` legacy reader | NO-FOLD / reference |
| #2140, #2139, #2138 | strangler-residual cluster (parent #1878) | NO-FOLD / reference |
| #2100 | route ~62 inline `meta.json` reads through `load_meta` (authority, not surface) | NO-FOLD (orthogonal) |
| #2123, #2091 | worktree teardown / coord-branch construction (write-side) | NO-FOLD |
| #2160 | epic parent | reference |

**Watch-items (don't fold, don't regress):**
- **#2139** (dual `target_branch` reader with silent `main` fallback in `core/paths.py`/`core/git_ops.py`) sits next to Lane A merge-reads — do not reintroduce or entrench the silent fallback while editing that neighborhood.
- **#2115 boundary** — `cli/commands/merge.py` appears in BOTH missions at different lines (this mission `:269`; sibling `_mark_wp_merged_done`). The arch-gate pin set shrinks by the right issue's lines on each side.

### Split-brain / LOC / deprecation (paula-patterns)

**Split-brain pair — MUST converge (in scope, refines FR-002):** `merge/executor.py:887` already computes `target_feature_dir` PRIMARY, but `_run_lane_based_merge` recomputes `feature_dir` coord-aware at `:976` for the *same* mission, then feeds identity (`:981`) and the review-artifact gate. **Thread the existing `:887` PRIMARY dir through to `:976`** rather than swap-and-recompute.

**Missing shared seam — DEFERRED (NOT this mission):** the two-call PRIMARY idiom `primary_feature_dir_for_mission(x, _canonicalize_primary_read_handle(x, slug))` is hand-inlined at ~12 sites, with 3 duplicate `_planning_read_dir` wrappers (`orchestrator_api/commands.py:324`, `agent/mission_feature_resolution.py:69`, `acceptance/__init__.py:787`). A canonical `primary_read_dir(repo, handle)` would dedup them — but (a) it tension-conflicts with C-002 (consume-not-author the resolver), (b) it straddles the implement-loop sibling's owned `workflow.py`/`implement.py` legs (cross-mission collision), and (c) it is broader than #2185/#2186. **Record as a separate follow-on dedup ticket (cousin of #2100); this mission consumes the existing `resolve_planning_read_dir` seam only.**

**Sizing (affects IC-03):** `lanes/recovery.py::scan_recovery_state` already carries `# noqa: C901` (already over the complexity ceiling). A per-leg PRIMARY/STATUS split inside it would worsen it — **extract the PRIMARY-planning read and the status-events read into named helpers, drop the `# noqa`, add focused tests** (do not add another branch). Other mixed functions (`executor._run_lane_based_merge`, `done_bookkeeping._mark_wp_merged_done`) have headroom — safe in place.

**Deprecation / guardrail:**
- `candidate_feature_dir_for_mission` is **NOT deprecated** — it is the C-005 STATUS-partition primitive. The mission re-points PRIMARY reads *off* it; it must **never remove or "converge away"** the coord-aware primitive (a "one resolver" framing would be a regression and break C-001 status reads).
- Distinguish in `merge/resolve.py`: `:98` is the `meta.json` PRIMARY read (route) vs `:63` is handle→dir-name canonicalization at the no-silent-fallback boundary (`.name`, exists-gated — leave on `candidate_`). Same caution for `next_cmd.py:360` (canonicalization, leave) vs `:187/:253/:631` (route).
- `merge.py:269` is coordination-teardown (`--abort`) — confirm PRIMARY_METADATA semantics but it is the coord-side; verify before routing.

**Owned-file LOC (sizing reference):** executor 1066, recovery 784, next_cmd 785, merge.py 582, done_bookkeeping 569, lanes/merge 508, worktree_allocator 470, worktree_topology 309, resolve 268, forecast 210. (`workflow.py` 2799 + `implement.py` 1459 are sibling-shared — touch only the owned identity legs.)
