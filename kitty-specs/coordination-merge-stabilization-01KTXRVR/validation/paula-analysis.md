# Paula Patterns — Coordination & Merge Cluster Scout Matrix
Repo: spec-kitty @ HEAD 956ab0e3e (2026-06-12). Cluster: 13 candidate issues.
All file:line citations spot-verified at HEAD.

## 1. Architectural Seams (boundary scout)

### Seam A — Execution-context placement: coord worktree vs primary checkout (the cluster's spine)
Who decides where a mission artifact is read/written: the coordination worktree under
`.worktrees/<slug>-coord` or the primary checkout's `kitty-specs/<slug>/`?

- Canonical authority (post-#1850): `src/mission_runtime/resolution.py:559-577`
  (`_assemble_artifact_placement_fragment` — planning artifacts and status events resolve to
  "literally the same value object"), `resolution.py:599-621` (`resolve_placement_only`, "the
  literal #1784 fix"), `resolution.py:528-535` (single-branch+coord-meta → `FLATTENED`).
- Consumers now routed through it: implement-claim (`src/specify_cli/cli/commands/implement.py:478-525,985-1003`),
  record-analysis preflight (`src/specify_cli/cli/commands/agent/mission.py:613-657`, C-PLACE-1),
  retrospect status reads (`src/specify_cli/cli/commands/retrospect.py:98-112,166-168` via
  `src/specify_cli/coordination/surface_resolver.py:83-96`), retrospective writes
  (`src/specify_cli/retrospective/writer.py:36-49`), merge baseline recording
  (`src/specify_cli/cli/commands/merge.py:1984,2227-2231` via `primary_feature_dir_for_mission`,
  `src/specify_cli/missions/feature_dir_resolver.py:23-27`), merge bake
  (`merge.py:887-888,905-916,962-977`, FR-035/FR-037 guards).
- Not yet routed (residual leaks): `src/specify_cli/retrospective/gate.py:597` reads
  `feature_dir / "status.events.jsonl"` directly; `src/specify_cli/cli/commands/agent_retrospect.py:432`
  uses identity `resolved.feature_dir`; `COORD_OWNED_STATUS_FILES`
  (`src/specify_cli/status/__init__.py:187`) covers only status.events.jsonl/status.json, not
  lanes.json/tasks/matrix residue copied by `_stage_finalize_artifacts_in_coord_worktree`
  (`mission.py:99-131`, no primary-side cleanup).
- Issues on this seam: #1770, #1827, #1816, #1814, #1771, #1735, #1784 (catch-22 half).

### Seam B — Worktree checkout-state coherence: who resyncs a worktree after its branch ref moves?
`git update-ref` advances refs without updating any worktree that has the branch checked out.
- Ref advances from detached temp worktrees: `src/specify_cli/lanes/merge.py:440-441,474-475`
  (Stage 1 lane→mission), `src/specify_cli/cli/commands/merge.py:993-998` (mission-number bake).
- The coord worktree has that same branch checked out: `src/specify_cli/coordination/workspace.py:160-211`
  (resolve verifies the symbolic-ref name only; never repairs a stale index/tree);
  coord branch == mission branch at `merge.py:2513-2515`.
- The next consumer commits THROUGH that worktree: `_record_merged_wps_done_for_merge`
  (`merge.py:662-695`) → `BookkeepingTransaction` (`src/specify_cli/coordination/transaction.py:744-815`)
  → safe_commit backstop diffs stale index vs advanced HEAD
  (`src/specify_cli/git/commit_helpers.py:474-519`, error at :333).
- Only the PRIMARY checkout gets resynced: `_refresh_primary_checkout_after_merge`
  (`merge.py:698-718`). Nobody owns coord-worktree resync. Issue: #1826 (LIVE).

### Seam C — Workspace resolution trust: "a path under .worktrees/ exists" ≠ "it is a git worktree"
- `ResolvedWorkspace.exists` is bare `Path.exists()` (`src/specify_cli/workspace/context.py:148-150`).
- `ReviewLock.acquire` mkdirs the resolved path BEFORE the existence/creation block
  (`src/specify_cli/cli/commands/agent/workflow.py:2237` lock vs :2243 `if not workspace.exists`;
  lock mkdir at `src/specify_cli/review/lock.py:102-105`; failed `git worktree add` is only a
  warning at workflow.py:2265).
- move-task gates on `worktree_path.exists()` then runs git with cwd=that path
  (`src/specify_cli/cli/commands/agent/tasks.py:1346,1404,1437,1484,1498`) — a husk without
  `.git` silently falls through to the primary repo's state.
- Naming-divergence trigger fixed (#1850: `workflow.py:926-938` returns canonical slug), but the
  fall-through-as-failure invariant is unimplemented. Issue: #1833 (residuals LIVE), sibling #1832.

### Seam D — status.json materialization ownership: background writers vs git
- Resolved by #1850: background reads use write-free `materialize_snapshot`
  (`src/specify_cli/status/reducer.py:289`); dashboard short-circuits during git ops
  (`src/specify_cli/dashboard/scanner.py:576-608`); git-op detection is linked-worktree-aware
  (`src/specify_cli/status/views.py:150-222`, gate at :288-296); daemon reaping consolidated
  (`src/specify_cli/sync/owner.py:467-816`, spawn-path wiring `daemon.py:1017-1025`).
- Residual (accepted): foreground `materialize()` still writes tracked status.json
  (`reducer.py:318-345`) — operator-command scope, not the background race class.
- Issues: #1789 (FIXED), #1071 regression (FIXED).

### Seam E — Read-only command contract: "validate/preflight must not mutate git state"
- LIVE violation: finalize-tasks `--validate-only` switches the primary checkout —
  `mission.py:2462` calls `_ensure_branch_checked_out` unconditionally (helper :781-812 runs
  `git checkout`, never restores); first `validate_only` guard is at :2496, after the checkout.
- Retired sibling: safe-commit no longer bounces — fail-closed `SafeCommitHeadMismatch`
  (`commit_helpers.py:894-901`, since 8e79b3f6d 2026-05-28). Issue: #1861 (Part 1 LIVE).

### Seam F — Publish-layer vs local-merge layering
- Fixed by PR #1719: remote-sync preflight gated on `effective_push` (`merge.py:1911-1918`;
  `src/specify_cli/merge/push_preflight.py:4-9,78-81`); non-destructive remediation
  (`src/specify_cli/merge/preflight.py:34-103`). Issue: #1571 (FIXED).

## 2. Ownership Confusion — competing authorities per seam (whack-a-field signatures)

| Seam | Authority 1 | Authority 2 (competitor) | Whack-a-field symptom |
|---|---|---|---|
| A placement | `resolve_placement_only` / `_assemble_artifact_placement_fragment` (mission_runtime/resolution.py) | Per-command derivations: legacy meta-fallback in implement.py:478-505 (C-004 strangler), gate.py:597 direct read, agent_retrospect.py:432 identity path, COORD_OWNED_STATUS_FILES allowlist | Each command re-derived coord-vs-primary independently → #1816/#1814/#1827/#1771/#1735 were five symptoms of one decision made five ways |
| B ref/worktree coherence | `git update-ref` callers (lanes/merge.py, merge.py bake) believe refs are theirs | `CoordinationWorkspace.resolve` + `BookkeepingTransaction` believe the coord checkout is theirs and current | safe_commit backstop fires on phantom deletions (#1826); each new ref-advance step re-creates the bug |
| C workspace identity | `resolve_workspace_for_wp` fallback naming (workspace/context.py:707) | Real allocators' naming (core/worktree.py:252, lanes/worktree_allocator.py:77) + ReviewLock's mkdir + move-task's exists() check | Husk dirs minted and then trusted by three downstream layers, none validating .git (#1833) |
| D status writes | Foreground emit path (reducer.materialize) | Formerly daemons + dashboard scanner; now read-only | Fixed; ratchet = no new background materialize() callers |
| E read-only contract | `validate_only` flag semantics | `_ensure_branch_checked_out` "compatibility shim" (mission.py:789) from the pre-WP07 read model | A read command repositions the checkout (#1861) |
| F merge layering | Local merge executor | Remote-sync policy (push concern) | Fixed in #1719 |

The cluster's meta-pattern: **the decision "which surface (branch/worktree/path) is authoritative
for this artifact" was duplicated per command instead of owned by one resolver**. PR #1850 built
that resolver (CommitTarget / placement fragment); remaining bugs are call sites not yet behind it
plus two coherence invariants nobody owns (B: resync-after-update-ref; C: resolved-path-must-be-a-worktree).

## 3. Ship-now vs Follow-up split (3.2.0 thesis: stability; no architecture creep)

### #1826 (LIVE — coord worktree behind own HEAD mid-merge)
- SHIP NOW: after each `update-ref` that advances the coord/mission branch
  (lanes/merge.py:440,474; merge.py:993-998), if a coordination worktree has that branch checked
  out, run `git -C <coord> reset --hard <branch>` under the feature-status lock (or equivalently
  self-heal in `BookkeepingTransaction._acquire_locked` when index is behind HEAD). ~20 lines,
  localized, no new abstractions.
- FOLLOW-UP issue: "Ref-advance/worktree-coherence invariant" — single helper owning all branch
  advances (commit-tree + update-ref + worktree resync), retire direct update-ref calls.
  Non-goals: changing coord topology, changing safe_commit semantics.

### #1861 Part 1 (LIVE — validate-only switches checkout)
- SHIP NOW: gate mission.py:2462 behind `not validate_only`. One-line guard; reads already anchor
  on the primary feature dir post-WP07.
- FOLLOW-UP: delete the `_ensure_branch_checked_out` shim entirely (mission.py:781-812) once the
  commit phase reads via plumbing. Non-goal: redesigning finalize-tasks branch model (done in #1850).
- Part 2: needs-issue-update only (already fixed by 8e79b3f6d).

### #1833 residuals (LIVE — husk dirs trusted as workspaces)
- SHIP NOW (guards, not rework): (a) move-task: treat a resolved path lacking a `.git` marker as
  resolution FAILURE before any git call (tasks.py:1346); (b) reorder ReviewLock.acquire after the
  workspace existence/creation block (workflow.py:2237→ after :2243); (c) make
  `ResolvedWorkspace.exists` require the `.git` marker (context.py:148-150).
- FOLLOW-UP: unify worktree naming into one allocator authority so the context.py:707 fallback
  cannot diverge from core/worktree.py:252. Non-goals: workspace lifecycle redesign, lock redesign.

### #1814 residual gap
- SHIP NOW: either extend the coord-residue exclusion to the artifacts finalize actually stages
  coord-side (lanes.json, tasks/, matrices) OR have `_stage_finalize_artifacts_in_coord_worktree`
  clean up its primary-side copies. Pick the cleanup option (removes residue at source).
- FOLLOW-UP: fold into the Seam-A "all reads/writes behind the placement resolver" ratchet.

### #1736 residuals
- SHIP NOW (one small PR): extract `_make_merge_env()` in lanes/merge.py; narrow
  status_transition.py:400 `except Exception` to `ValueError/FileNotFoundError`; add the
  mixed-timestamp ratchet test. Hardening, hours not days.
- FOLLOW-UP: none beyond the tests.

### #1784 / #1827 follow-up crumbs
- SHIP NOW (P3, optional): suppress "Upgrade complete!" on --dry-run (upgrade.py:987); make the
  safe_commit backstop message (commit_helpers.py:321-339) name the likely cause when index is
  behind HEAD (dovetails with the #1826 fix).
- FOLLOW-UP: regression test for coord-topology baseline recording (test_merge_coord_topology_1772.py
  currently mocks the baseline helpers out); the crash-between-record-and-commit re-run edge.

### Long-term architecture issue (ONE umbrella, file under epic #1666)
"Execution-surface ownership: complete the strangler" — (1) all artifact reads/writes behind
`resolve_placement_only`/`resolve_status_surface` (kill gate.py:597, agent_retrospect.py:432,
implement.py legacy fallback C-004); (2) single ref-advance helper with worktree resync; (3) single
worktree-naming allocator + is-a-worktree validation as a type invariant; (4) AC10 lint/architectural
rule forbidding `resolved.feature_dir → read_events()`. Explicit non-goals for 3.2.0: no topology
changes, no resolver API redesign, no status-model changes, no daemon work.

## 4. Release-blocker status per issue (3.2.0)

| # | Status | Verdict | One-line justification |
|---|---|---|---|
| 1826 | VALID | **BLOCKER** | Breaks unattended merge of every coord-topology mission with >1 ref-advance; mechanism untouched by #1793/#1850. |
| 1861 | PARTIAL | **BLOCKER** (Part 1; trivial fix) | A nominally read-only command mutating the primary checkout is a trust defect squarely against the stability thesis; one-line guard. |
| 1833 | PARTIAL | **strongly-recommended** | Naming trigger fixed in #1850, but husk fall-through still mis-reports primary-repo state as lane state — false review/approval failures. |
| 1814 | PARTIAL | strongly-recommended | Named deadlock fixed; lanes.json/tasks residue can still trip DIRTY_WORKTREE under coord topology; `git clean` workaround exists. |
| 1736 | PARTIAL | strongly-recommended | Bugs A/B/C fixed; residuals are cheap hardening that prevents silent recurrence (env omission, swallowed sentinel). |
| 1784 | PARTIAL | safe-to-defer (close core as dup of #1777/#1850; split P3 polish) | Catch-22 landed in #1850; remaining items are messaging polish. |
| 1827 | FIXED | safe-to-defer (close; add reg test) | Fixed in rc42 (9c8bff06f); only the missing regression test matters. |
| 1770 | FIXED | safe-to-defer (close) | Drained by #1793 + #1850; CHANGELOG lists it; issue stale-open. |
| 1789 | FIXED | safe-to-defer (close) | WP11/WP12 of #1850; regression tests in tree. |
| 1816 | FIXED | safe-to-defer (close) | WP06 of #1850 with regression tests. |
| 1771 | FIXED | safe-to-defer (close) | FR-006 fix + test_record_committable_1771.py. |
| 1735 | FIXED-core | safe-to-defer (update+close; residuals → umbrella) | Core read-surface fix landed; AC7/AC10 residuals are lint/doc debt. |
| 1571 | FIXED | safe-to-defer (close) | Fixed by PR #1719 (2026-06-05) with push/no-push matrix tests. |

## 5. Required regression tests for 3.2.0 (so the class cannot silently return)

1. `tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py` — coord-topology
   mission, 2 lanes: after Stage 1 update-ref advances the mission branch, assert the coord
   worktree index == HEAD and `_record_merged_wps_done_for_merge` commits without
   SafeCommitBackstopError. (Pattern: test_merge_coord_topology_1772.py.)
2. `tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py` — capture
   `git symbolic-ref HEAD` before/after `finalize-tasks --validate-only`; assert unchanged; assert
   no new files staged. (Pattern: existing agent/mission CLI tests.)
3. `tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py` — mint a bare dir
   `.worktrees/<slug>-lane-a` (no .git): assert move-task approval fails with a resolution error
   (not "No implementation commits"); assert review claim does not mkdir before worktree creation;
   assert `ResolvedWorkspace.exists` is False for the husk.
4. `tests/status/test_event_log_merge.py` — add `test_merge_event_payloads_mixed_at_timestamp_neither`
   covering the at/timestamp/neither sort (issue #1736 Bug B ratchet).
5. `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py` — extend (or sibling file)
   to exercise REAL `_record_baseline_merge_commit`/assert under coord topology instead of mocking
   both helpers (closes the #1827 test gap), and assert `git show <target>:kitty-specs/<slug>/meta.json`
   contains `baseline_merge_commit`.
6. `tests/architectural/test_execution_context_parity.py` — extend with the AC10 ratchet: forbid
   `resolved.feature_dir` → `read_events()`/direct `status.events.jsonl` reads outside the surface
   resolver (catches gate.py:597 / agent_retrospect.py:432 class).
7. `tests/specify_cli/cli/commands/test_wp06_sc2_paused_mission_blockers.py` — extend: untracked
   `lanes.json`/`tasks/WP01.md` residue on the primary checkout must not block record-analysis
   under coordination placement (the #1814 residual).
8. Keep/verify existing ratchets stay green: tests/status/test_views_gitop_guard.py,
   tests/sync/test_daemon_singleton_reaper_consolidation.py,
   tests/retrospective/test_record_committable_1771.py.
