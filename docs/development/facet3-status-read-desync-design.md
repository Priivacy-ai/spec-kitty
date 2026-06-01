# Design: fix #1589 facet 3 — coordination/mission status read desync

**Status:** proposed (design-first; no code yet)
**Scope:** `spec-kitty` status read path for lane-based missions
**Related:** [#1589](https://github.com/Priivacy-ai/spec-kitty/issues/1589) facet 3; builds on #1590 (facets 1 & 2)

## 1. Root cause (precise, evidence-backed)

Lane-based missions keep canonical status on a **coordination branch**, materialized in a
per-mission **coordination worktree** (`.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/`).

- **Writes are already correct.** `finalize`, `implement`, `move-task`, `merge`, and
  `bootstrap_canonical_state` all emit through
  `coordination.status_transition.emit_status_transition_transactional`, which commits the
  event to the **coordination branch** (via `BookkeepingTransaction`). Verified: the coord
  worktree holds the full log (82 lane events → 18 WPs materialize).

- **Reads are inconsistent.** Two commands were updated to read coordination-aware:
  - `cli/commands/agent/workflow.py` → `_canonical_status_feature_dir()` →
    `missions._read_path_resolver.resolve_mission_read_path()`
  - `acceptance/__init__.py` → `_status_read_feature_dir()`

  But three read paths were **not**, and still read the raw `main_repo_root/kitty-specs/<slug>`
  (the mission branch, which never receives the lane events):
  1. `cli/commands/agent/tasks.py::move_task` — `read_events(feature_dir)` at ~:1833 and the
     `current_event_lane` lookup.
  2. `cli/commands/next_cmd.py` — `feature_dir = repo_root_path / "kitty-specs" / mission_slug`
     (several sites) feeding the decision/status read.
  3. `status/lane_reader.py` (`get_wp_lane`/`_require_event_log`) and `status/reducer.materialize`
     when called with the primary feature_dir.

**Net effect:** `move-task`/`next` read the stale mission-branch log → "WP has no canonical
status" even though the coordination worktree has a fully materialized status. This is the
exact wall that blocks the implement-review loop.

**Conclusion:** this is **incomplete adoption** of the existing coordination-aware read
resolver, *not* an architectural redesign. The canonical helper already exists and is proven:
`resolve_mission_read_path(main_repo_root, mission_slug, mid8)` returns the coord worktree
feature_dir when it exists, else the primary checkout (legacy/no-coord missions).

## 2. Fix

Route the three missing read paths through the **existing** resolver, mirroring `workflow.py`.

- **Centralize:** promote `_canonical_status_feature_dir` (currently private in `workflow.py`)
  to a shared location — e.g. `missions._read_path_resolver` already hosts
  `resolve_mission_read_path`; add a thin `canonical_status_feature_dir(main_repo_root, slug)`
  wrapper there (computes mid8 from meta) and have `workflow.py`/`acceptance` re-use it (removing
  their private duplicates over time).
- **Apply at the read sites:**
  1. `move_task` (tasks.py): resolve the read-side `feature_dir` via the wrapper before
     `read_events` / the lane lookup. The transactional *write* already targets coord; this aligns
     the *read* with it. (The `safe_commit` to the mission branch for WP-frontmatter/status.json is
     a separate concern — see §5.)
  2. `next_cmd.py`: resolve the status-read `feature_dir` via the wrapper for the decision read
     (keep the planning/worktree-creation paths on the primary checkout).
  3. `lane_reader` / `materialize`: lowest-leverage but highest-consistency — make the canonical
     lane read resolve through the wrapper so *any* caller that goes through `get_wp_lane` is
     coordination-aware by construction. (Preferred: fix here + the command-level sites, so the
     contract "all lane reads go through lane_reader" actually holds.)

## 3. Backward compatibility

`resolve_mission_read_path` returns the **primary checkout** when no coord worktree exists
(legacy/pre-coordination missions). So non-lane/legacy missions are **unaffected** — the change
is a no-op for them. New behavior only engages when a `-coord` worktree is present.

## 4. Blast radius & risk

- **Read-only resolution change**, guarded by "coord worktree exists" → low risk of data
  corruption (no new writes introduced).
- Touches status reads across `move-task`, `next`, `lane_reader`/`materialize`. Medium surface,
  but each change is "compute feature_dir via the resolver that two other commands already use."
- Main risk: a caller that *intends* the primary checkout (e.g. planning artifact reads, worktree
  creation) accidentally redirected to coord. Mitigation: only redirect the **status/event-log
  reads**, never the planning-artifact or worktree-management paths.

## 5. Known adjacent issue (call out, do not silently fold in)

`move-task` does a `safe_commit` to the **mission branch** (tasks.py ~:1959) for WP-frontmatter /
`status.json`, while the *event* is committed to the **coordination branch**. After the read fix,
the authoritative event log is unambiguously the coord branch; the mission-branch `status.json`
becomes a derived/secondary view. We should decide whether `move-task` should stop writing
`status.json` to the mission branch (to avoid a misleading stale snapshot) — proposed as a
follow-up, not part of the minimal read fix.

## 6. ATDD test plan (reproduce the split, fail on current code)

Integration test driving the real CLI (mirrors `tests/regression/test_issue_1589.py`):

1. Init a git repo; create a lane-based mission with a `-coord` worktree (or stub the coord
   worktree + `meta.coordination_branch`/`mid8`).
2. `finalize-tasks` (or seed) so the **coord** worktree's event log has N WPs `planned`, while the
   mission-branch log is empty.
3. **Assert (RED on current code):** `move-task WP01 --to in_progress` fails with "no canonical
   status" (reads the empty mission branch).
4. **Assert (GREEN after fix):** the same `move-task` succeeds (reads the coord worktree), and a
   subsequent `materialize` via the resolver shows the transition.
5. Unit test: `canonical_status_feature_dir` returns the coord dir when the `-coord` worktree
   exists and the primary checkout when it does not (legacy no-op).

## 7. Alternatives considered

- **Make writes target the main checkout instead of coord** (drop the coordination branch for
  status): rejected — the coordination branch exists to serialize parallel lane writes; removing
  it reintroduces the multi-lane write-conflict problem the coordination model solved.
- **Sync coord→main status after each op**: rejected — fragile, re-desyncs on the next write
  (empirically unreliable in this session).

## 8. Recommendation

Implement §2 (resolver wrapper + the three read sites, fixing `lane_reader` as the central
chokepoint), with the §6 ATDD test proven RED→GREEN. Defer §5 (`move-task` mission-branch
`status.json` write) to a follow-up. Land as a focused PR to upstream `main`, like #1590.
