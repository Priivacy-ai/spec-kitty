# Lens D — Red-first ATDD reproduction design (#2709, #2711)

Read-only research. This document is a **repro DESIGN**, not the tests. The
implementer authors the tests mechanically from this spec, confirms RED on
current `main` through the pre-existing entry point, then fixes to GREEN. No
retry-to-green; both tests must FAIL first on unmodified `main`.

Canonical entry point for both repros: `_run_lane_based_merge` — the real merge
executor — driven exactly as every other merge test drives it. Do NOT
reconstruct paths or hand-roll a merge; reuse the real coord-topology harness.

- Canonical driver: `specify_cli.merge.executor._run_lane_based_merge`
  (re-exported as `from specify_cli.cli.commands.merge import _run_lane_based_merge`).
- Canonical squash mechanics: `specify_cli/lanes/merge.py::_merge_branch_into`
  line 401 — `git merge --squash -X theirs <source_branch>`. `theirs` = the
  mission/coord branch. This `-X theirs` is the #2709 clobber vector.
- Canonical target-advance step: `executor._phase_mission_to_target`
  (`executor.py:465`) → `integrate_mission_into_target` (`executor.py:482`).
  Its `try/except Exception: _restore_pre_target_if_at_baseline(run); raise`
  (`executor.py:489-491`) is the #2711 rollback site.
- Canonical acceptance-field writers: `mission_metadata.record_acceptance(...)`
  (`mission_metadata.py:466`) and `mission_metadata.set_vcs_lock(...)`
  (`mission_metadata.py:512`).

Reused fixture template for BOTH repros: the real-git coord-topology harness in
`tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`:
`_init_git_repo`, `_bootstrap_coord_mission`, `_write_meta`, `_write_manifest`,
`_file_on_branch`, and the `_real_merge_external_mocks(...)` context manager
(mocks ONLY non-git side effects; runs real `integrate_mission_into_target` /
`_merge_branch_into` / real `git merge --squash`). That harness's
`test_merge_records_baseline_merge_commit_on_target` (reads
`git show main:kitty-specs/<slug>/meta.json` on the committed target meta) is a
near-exact structural template for #2709.

---

## Issue #2709 — squash `-X theirs` clobbers target-newer acceptance provenance

### Root cause (confirmed by reading source)
`_merge_branch_into` runs `git merge --squash -X theirs <mission_branch>`
(`lanes/merge.py:401`). When `meta.json` diverged on BOTH the target branch
(newer acceptance provenance) and the mission/coord branch (older copy), git
conflicts on `meta.json` and `-X theirs` resolves the whole hunk toward the
mission branch, silently overwriting the target's newer `accepted_at`,
`accepted_by`, `accepted_from_commit`, `acceptance_mode`, `accept_commit`,
`acceptance_history`, `vcs`, `vcs_locked_at`. The append-only
`acceptance_history` array is truncated back to the older copy's entries.

### 1. Test file + name + markers
- Path: `tests/regression/test_issue_2709_squash_provenance.py`
- Test: `TestIssue2709SquashPreservesTargetAcceptanceProvenance::test_squash_merge_does_not_clobber_target_newer_acceptance_fields`
- Markers: `pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]`
  (`non_sandbox` is required — `integrate_mission_into_target` does a real
  `git worktree add`; `git_repo` matches the harness convention; `regression`
  matches `tests/regression/` convention and `test_finalize_clobber_e2e.py`.)

### 2. Arrange (reuse the real harness — realistic data, no stubs)
1. `repo = tmp_path / "repo"; _init_git_repo(repo)` (copy the helpers from
   `test_merge_coord_topology_1772.py`, or import them — they are module-level
   in that file).
2. `feature_dir = _bootstrap_coord_mission(repo)` — this creates a coord mission
   (`MISSION_SLUG="coord-topology-1772"`, `COORD_BRANCH`, `target_branch="main"`,
   a real lane branch `kitty/mission-<slug>-lane-a` carrying a real code diff
   `src/feature_code.py` NOT on `main`). Use a distinct mission slug for the
   regression (e.g. `"issue-2709-provenance"`) by parameterizing copies of the
   `_write_meta`/`_write_manifest`/`_bootstrap_coord_mission` helpers, or reuse
   verbatim — the slug is not load-bearing.
3. **Older acceptance on the mission/coord branch** (this is the `-X theirs`
   winner pre-fix). Check out `COORD_BRANCH`, then on that branch's
   `kitty-specs/<slug>/meta.json` call:
   `record_acceptance(feature_dir, accepted_by="reviewer-old", mode="local", from_commit="<coord_base_sha>", accept_commit="<coord_accept_sha>")`
   Commit to `COORD_BRANCH` (`git commit -m "accept (v1, older)"`). This yields
   `acceptance_history == [v1]`, an older `accepted_at`. NOTE:
   `record_acceptance` stamps `accepted_at` from `datetime.now`; to force a
   deterministically OLDER timestamp on the coord side, either (a) run the coord
   acceptance first and the target acceptance second (wall-clock ordering is
   enough since `_now_iso` is second-granular — add a tiny explicit sleep or
   monkeypatch `mission_metadata._now_iso` to return fixed T1 then T2), or (b)
   monkeypatch `_now_iso` (preferred, deterministic) to return `"...T1..."`
   during the coord write and `"...T2..."` during the target write.
4. **Newer acceptance provenance on the target branch** `main`. Check out
   `main`, and on `main`'s `kitty-specs/<slug>/meta.json`:
   - `record_acceptance(feature_dir, accepted_by="reviewer-new", mode="pr", from_commit="<target_base_sha>", accept_commit="<target_accept_sha>")`
     TWICE (or append a second distinct entry) so `acceptance_history == [v1, v2]`
     (two entries) with newer `accepted_at == T2`.
   - `set_vcs_lock(feature_dir, vcs_type="git", locked_at="2026-07-17T00:00:00Z")`
     so `vcs` + `vcs_locked_at` exist ONLY on target.
   Commit to `main` (`git commit -m "accept (v2, newer) + vcs lock"`).
   Result: `meta.json` is modified on BOTH branches relative to the bootstrap
   base → guaranteed squash conflict → `-X theirs` picks the coord branch.
5. Enter the real-git mock context: `with _real_merge_external_mocks():`. Do NOT
   use `real_baseline_recording=True` for the primary assertion (the default
   mocks `_record_baseline_merge_commit` + `commit_merge_bookkeeping`, so the
   ONLY thing that rewrites the target `meta.json` is the squash — isolating the
   clobber). (A second variant with `real_baseline_recording=True` can confirm
   the fix is durable through the bookkeeping commit; keep it secondary.)

### 3. Act (pre-existing entry point, canonical)
```python
with _real_merge_external_mocks():
    _run_lane_based_merge(
        repo_root=repo,
        mission_slug=<slug>,
        push=False, delete_branch=False, remove_worktree=False,
        strategy=MergeStrategy.SQUASH,
        allow_sparse_checkout=True,
    )
```

### 4. Assert (field-level target-newer survivors — RED now, GREEN after fix)
Read the committed target meta after the merge, exactly like the #1827 test:
```python
committed = _git(repo, "show", f"main:kitty-specs/{slug}/meta.json").stdout
meta = json.loads(committed)
```
Assert every target-newer field SURVIVED the squash (all currently FAIL — the
coord/mission-branch older copy won via `-X theirs`):
- `meta["accepted_at"] == T2`               (not the coord T1)
- `meta["accepted_by"] == "reviewer-new"`   (not `"reviewer-old"`)
- `meta["acceptance_mode"] == "pr"`         (not `"local"`)
- `meta["accepted_from_commit"] == "<target_base_sha>"`
- `meta["accept_commit"] == "<target_accept_sha>"`
- `len(meta["acceptance_history"]) == 2` and the v2 entry is present
  (append-only section not truncated back to the older `[v1]`)
- `meta["vcs"] == "git"` and `meta["vcs_locked_at"] == "2026-07-17T00:00:00Z"`
  (target-only fields not dropped)

Append-only trace section (secondary, same test or a sibling): also stage a
target-only appended line on `main`'s tracked
`kitty-specs/<slug>/status.events.jsonl` (an extra event not on the coord
branch) before the merge, and after the merge assert that appended line still
appears in `git show main:kitty-specs/<slug>/status.events.jsonl`. Pre-fix the
`-X theirs` squash drops the target-only append. (The event log has a semantic
merge driver via `_ensure_event_log_merge_driver_config`, but `-X theirs`
overrides per-hunk conflict resolution — the implementer should confirm whether
the driver saves the log; if it does, keep the meta.json assertions as the
load-bearing RED and demote the trace-line assertion to a guard.)

### 5. Red proof plan
```
PWHEADLESS=1 uv run pytest tests/regression/test_issue_2709_squash_provenance.py -n0 -q
```
Expect FAIL on current `main`: `AssertionError` on `accepted_at` /
`acceptance_history` length (coord-branch older copy survived). Confirm the
first failing assertion is a provenance field, not a fixture error.

### 6. Gaps the implementer must fill
- No shared "accept a mission" test helper exists; call
  `mission_metadata.record_acceptance` + `set_vcs_lock` directly on each branch's
  checkout (both writers confirmed at `mission_metadata.py:466,512`).
- Deterministic timestamp ordering: monkeypatch `mission_metadata._now_iso` (or
  the module's `_now_iso` symbol) to yield T1 for the coord write and T2 for the
  target write. Without this the `accepted_at` assertion is wall-clock flaky.
- `_bootstrap_coord_mission` commits `meta.json` at the bootstrap tip on BOTH
  `main` and `COORD_BRANCH` — the repro must add the two divergent acceptance
  commits (steps 3–4) so `meta.json` genuinely conflicts; a target-only change
  would 3-way-merge cleanly and `-X theirs` would NOT fire (no RED). This
  divergence is the crux; do not skip the coord-side acceptance commit.

---

## Issue #2711 — merge rollback + `--resume`: committed-vs-working coherence

### Mechanism (confirmed by reading source)
Under coord topology with a **materialized coordination worktree**,
`_phase_baseline_and_surface` sets `run.done_marked_before_target = True`
(because `is_under_worktrees_segment(status_surface_path)` is True). Then
`_phase_bake_and_pre_target_done` records **and durably commits** the
`approved -> done` events to the coord branch BEFORE `_phase_mission_to_target`
advances the target. If target advancement then FAILS,
`_phase_mission_to_target`'s `except` calls `_restore_pre_target_if_at_baseline`
which restores the pre-done bytes into the coord worktree's working
`status.events.jsonl` — but the coord BRANCH commit still carries the done
events. Committed (coord branch) says `done`; working (restored coord worktree
file) says pre-done → split brain. On `--resume`,
`_reconcile_completed_wps_for_resume` (`done_bookkeeping.py:510`) is supposed to
derive progress from durable events (`_has_transition_to(... "done" ...)`) and
the `_mark_wp_merged_done` dedup guard (`done_bookkeeping.py:285`) is supposed
to prevent a second `done` event.

### 1. Test file + name + markers
- Path: `tests/regression/test_issue_2711_merge_rollback_resume_coherence.py`
- Tests (one class, two methods):
  - `test_committed_and_working_status_stay_coherent_after_target_advance_failure`
  - `test_resume_derives_progress_from_durable_events_without_duplicating_transitions`
- Markers: `pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]`

### 2. Arrange (real coord harness + materialized coord worktree + REAL done recording)
1. `_init_git_repo(repo)` and `_bootstrap_coord_mission(repo)` as in #2709, but
   the WP markdown in `tasks/` must carry approval evidence so the REAL
   `_mark_wp_merged_done` emits `approved -> done` (frontmatter
   `review_status: approved`, `reviewed_by: <name>` — see
   `done_bookkeeping._extract_done_evidence` / `_emit_approved_replay_if_needed`).
   Seed the pre-merge lane state as `approved` (not pre-baked `done`) so the
   merge actually performs the `approved -> done` transition under test. Prefer
   a 2-WP, single-code-lane mission (or 2 lanes) so "no duplicate transitions"
   is asserted across more than one WP.
2. **Materialize the coordination worktree** so the status surface is under
   `.worktrees/` and `done_marked_before_target` becomes True. Reuse the pattern
   from `tests/merge/test_merge_target_resolution.py:79-80`:
   ```python
   from specify_cli.coordination.workspace import CoordinationWorkspace
   coord_wt = CoordinationWorkspace.worktree_path(repo, <slug>, <mid8>)
   _git(repo, "worktree", "add", "-q", str(coord_wt), COORD_BRANCH)
   ```
   Confirm the ordering with a sanity assert:
   `is_under_worktrees_segment(resolve_status_surface(repo, <slug>))` is True.
3. Preload a `MergeState` (via `save_state`) representing the mission so the
   SECOND run is a `--resume` (state.json present):
   `MergeState(mission_id=<MID>, mission_slug=<slug>, target_branch="main", wp_order=[...], completed_wps=[], strategy="squash")`.
4. Use a REDUCED mock set derived from `_real_merge_external_mocks` but with the
   done-recording pipeline LEFT REAL — i.e. do NOT mock
   `_record_merged_wps_done_for_merge`, `_mark_wp_merged_done`,
   `_assert_merged_wps_reached_done`, or `_reconcile_completed_wps_for_resume`.
   Keep the non-git side-effect mocks (gates, policy, dossier, SaaS emit,
   stale-assertion, sparse-checkout, `_bake_mission_number_into_mission_branch`,
   `_classify_porcelain_lines -> ([],0)`, `has_remote -> False`). This is a
   NEW mock context the implementer must build (see Gaps).

### 3. Act — inject the target-advance failure at the canonical step
Patch the target-advance function at its SOURCE module (it is imported lazily
inside `_phase_mission_to_target`), matching the precedent in
`tests/merge/test_executor_phase_boundary.py`:
```python
with patch("specify_cli.lanes.merge.integrate_mission_into_target",
           side_effect=RuntimeError("simulated target advancement failure")):
    with pytest.raises((typer.Exit, RuntimeError)):
        _run_lane_based_merge(repo_root=repo, mission_slug=<slug>,
            push=False, delete_branch=False, remove_worktree=False,
            strategy=MergeStrategy.SQUASH, allow_sparse_checkout=True)
```
This fails AFTER the pre-target `approved -> done` events are durably committed
to the coord branch — the exact "target advancement fails after done committed"
condition. Then (test 2) drop the patch and re-run `_run_lane_based_merge`
(state.json present → resume path) to completion.

### 4. Assert (RED now, GREEN after fix)
Helper: `reduce_lane_by_wp(text)` = latest `to_lane` per `wp_id` from a
`status.events.jsonl` blob (mirror `done_bookkeeping._parse_target_lanes_by_wp`).

Test 1 — committed vs working coherence after the failed merge:
- committed = `git show <COORD_BRANCH>:kitty-specs/<slug>/status.events.jsonl`
- working  = read the coord worktree's `kitty-specs/<slug>/status.events.jsonl`
- Assert `reduce_lane_by_wp(committed) == reduce_lane_by_wp(working)` for every
  WP (direction-agnostic coherence). Pre-fix these DIVERGE (committed `done`,
  working restored to `approved`/pre-done) → RED. Also assert the two do not
  form a split brain where committed shows `done` while working shows the
  pre-done lane.

Test 2 — resume derives from durable events, no duplicate transitions:
- After the resumed run completes (exit 0), read
  `git show main:kitty-specs/<slug>/status.events.jsonl` (target) AND the coord
  branch log. For each WP assert `to_lane == "done"` appears **exactly once**
  (`count == 1`) in the coord branch event log — the dedup / reconcile prevented
  a second `approved -> done`. Pre-fix a broken reconcile re-emits done →
  `count == 2` → RED.
- Assert the resumed run did not re-run the mission→target integration for
  work already durably done (progress derived from durable events, not a blind
  replay): assert the final `MergeState` (`load_state`) has each WP in
  `completed_wps` and there is no duplicate `done` event (covered above).

### 5. Red proof plan
```
PWHEADLESS=1 uv run pytest tests/regression/test_issue_2711_merge_rollback_resume_coherence.py -n0 -q
```
Expect FAIL on current `main`: test 1 `AssertionError` on committed-vs-working
lane divergence; test 2 `AssertionError` on duplicate `done` event count (or a
resume exception). Run `-n0` (serial) — real `git worktree` + coord worktree are
OS-global resources, per the parallel-test rules in `CLAUDE.md`.

### 6. Gaps the implementer must fill
- **Coord-worktree materialization is not in `_bootstrap_coord_mission`.** The
  existing coord harness only creates `COORD_BRANCH`, so `resolve_status_surface`
  lands on the primary path → `done_marked_before_target == False` → done is
  recorded POST-target, which does NOT reproduce "target advancement fails AFTER
  done committed." The repro MUST materialize the coord worktree (pattern above,
  from `test_merge_target_resolution.py`). Add a small helper
  `_materialize_coord_worktree(repo, slug, mid8) -> Path` in the new test module
  and assert `done_marked_before_target` via the `is_under_worktrees_segment`
  sanity check.
- **A "real done-recording" merge-mock context does not exist.** `_real_merge_
  external_mocks` mocks `_record_merged_wps_done_for_merge` and
  `_mark_wp_merged_done` out. The implementer must author a sibling context
  manager (same non-git side-effect mocks) that leaves the done-recording +
  reconcile pipeline REAL. Place it in the new test module.
- **WP approval evidence.** The seeded WP markdown must carry `review_status:
  approved` + `reviewed_by` (and the pre-merge lane must be `approved`, not a
  pre-baked `done`) so the real `_mark_wp_merged_done` performs a genuine
  `approved -> done` transition — otherwise the dedup guard short-circuits and
  the duplicate-transition assertion is vacuous.
- **Fallback ordering (document, do not default to it).** If materializing the
  coord worktree proves impractical, the alternative injection is a POST-target
  housekeeping failure: leave the squash real (target advances), let done record
  post-target, then patch `specify_cli.merge.executor.commit_merge_bookkeeping`
  with `side_effect=RuntimeError` (precedent:
  `test_executor_phase_boundary.py::test_commit_failure_restores_then_reraises`)
  and resume. This matches the `_reconcile_completed_wps_for_resume` docstring
  ("after the target ref advanced but before the final status-event housekeeping
  commit") but is a WEAKER match to the issue's literal "target advancement to
  fail" wording — prefer the coord/pre-target injection as primary.

---

## Cross-cutting notes
- Both tests drive the SAME canonical entry point `_run_lane_based_merge` with
  `strategy=MergeStrategy.SQUASH` — the pre-existing surface, not a
  reconstructed merge. Do not call phase helpers directly for the RED repro
  (phase-level tests exist in `tests/merge/test_executor_phase_boundary.py` but
  they are unit guards, not the operator-facing repro these P0s demand).
- Reuse `_init_git_repo`, `_bootstrap_coord_mission`, `_write_meta`,
  `_write_manifest`, `_file_on_branch`, `_real_merge_external_mocks`, and `_git`
  from `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py` —
  import them or copy verbatim into the regression modules (the regression
  package convention keeps repros self-contained; `test_issue_2508.py` copies
  its `_git` helper likewise). Do NOT improvise a new mission-scaffold path.
- Terminology canon: use "Mission" everywhere; the fixtures already do.
