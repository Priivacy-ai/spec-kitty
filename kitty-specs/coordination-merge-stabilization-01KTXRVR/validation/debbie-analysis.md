# Coordination & Merge Cluster — Structural Root-Cause Analysis
**Debugger Debbie — 2026-06-12, repo HEAD 956ab0e3e**
Scope: 13 candidate issues (#1571 #1735 #1736 #1770 #1771 #1784 #1789 #1814 #1816 #1826 #1827 #1833 #1861)

---

## 0. Headline finding

The cluster is NOT 13 independent bugs. It decomposes into **seven root-cause classes**, of which
**four are already structurally closed at HEAD** (mostly by PR #1850 / commit 8544012fa, the
execution-context-unification mission, merged 2026-06-12T06:46Z — hours before this analysis), and
**three remain live**. The live defect surface is small and well-localized:

1. **Class B (live, only fully-VALID issue #1826):** `git update-ref` advances a branch that is
   checked out in the coordination worktree, with no worktree resync — the next bookkeeping
   `safe_commit` through that worktree trips the behind-HEAD backstop.
2. **Class C (live, #1861 Part 1):** `finalize-tasks --validate-only` switches the primary checkout
   via an unguarded `_ensure_branch_checked_out` call.
3. **Class D (live residual, #1833):** workspace resolution fall-through is treated as success —
   husk dirs under `.worktrees/` pass `Path.exists()` checks and git calls silently fall through to
   the primary repo.

Plus narrow residuals of the drained Class A (#1814/#1735) and hardening debt of Class F (#1736).

---

## 1. Root-cause classes (Five-Whys, verified against src/)

### Class A — Coord-vs-primary execution-context split-brain (no single placement/read-surface authority)
**Status: STRUCTURALLY DRAINED at HEAD (PR #1850 + rc42 9c8bff06f + rc41 c5a10ce56), narrow residuals remain.**

Five-Whys chain:
- Why did merge baking / accept / finalize / implement-claim / record-analysis / retrospect fail?
  → They wrote or read mission artifacts via a path that resolved into the coordination worktree
  under gitignored `.worktrees/` while git operations (add/commit/show) ran against the primary
  checkout / target branch — or vice versa.
- Why did paths diverge? → Each command surface had its **own** derivation of "where do this
  mission's artifacts live / get committed" (coord-aware resolver vs HEAD vs cwd vs meta.json).
- Why were there multiple derivations? → The coordination-branch topology (mission branch checked
  out in `.worktrees/<slug>-coord`) was retrofitted onto code written for a single-checkout model;
  no shared CommitTarget/placement object existed.
- Why was that not caught? → `.worktrees/` is gitignored *and* the divergence is dormant on
  flat-topology missions, which is what unit tests modelled.
- **Root structural defect:** absence of a single placement/read authority.

**The structural fix landed:** `resolve_placement_only()` / `_assemble_artifact_placement_fragment`
in `src/mission_runtime/resolution.py:528-621` — planning artifacts and status events resolve to
"literally the same value object" (resolution.py:559-577); single-branch missions with coord meta
collapse to `CommitTargetKind.FLATTENED` (resolution.py:528-535). Consumers verified:
`implement.py:478-525` (#1816), `mission.py:613-657` placement-aware dirty gate (#1814),
`retrospect.py:98-112,166-168` → `coordination/surface_resolver.py:83-96` (#1735),
`retrospective/writer.py:36-49` (#1771), `merge.py:1984` `primary_feature_dir_for_mission` (#1827),
`merge.py:887-998` tempdir bake worktree + `path_is_under_worktrees` guards (#1770),
`acceptance/__init__.py:575-599,929` primary anchor. Ratchet:
`tests/architectural/test_execution_context_parity.py`.

**Residuals (verified live):**
- A-r1 (#1814): `COORD_OWNED_STATUS_FILES = frozenset({status.events.jsonl, status.json})`
  (`status/__init__.py:187`) — but `_stage_finalize_artifacts_in_coord_worktree`
  (`mission.py:99-131`) copies `lanes.json`/`tasks/*`/matrices into the coord worktree and never
  cleans the primary copies; that untracked residue still trips the DIRTY_WORKTREE gate
  (`mission.py:643-657`) under coordination placement.
- A-r2 (#1735): `retrospective/gate.py:597` reads `feature_dir / "status.events.jsonl"` directly
  (coord-unaware if handed a primary path); `agent_retrospect.py:432` still consumes
  `resolved.feature_dir`; no lint rule bans `resolved.feature_dir → read_events()` (AC10).
- A-r3 (#1827): no regression test covers coord-topology baseline recording
  (`test_merge_coord_topology_1772.py:224-225` mocks both baseline helpers out); crash between
  baseline record and safe_commit leaves a re-run tripping the working-tree invariant.

### Class B — Ref-advance without checked-out-worktree resync (LIVE — #1826, the cluster's only fully-VALID issue)
Five-Whys:
- Why does `spec-kitty merge` abort with SAFE_COMMIT_BACKSTOP "working tree is behind HEAD"?
  → The done-bookkeeping commit runs through the coordination worktree
  (`merge.py:662-695` → `coordination/transaction.py:744-815` → safe_commit), whose backstop
  (`git/commit_helpers.py:305-340,474-519`) sees phantom staged deletions.
- Why phantom deletions? → The coord worktree's index/working tree are *behind their own HEAD*.
- Why behind? → Stage-1 lane→mission merges and mission-number baking advance the mission branch via
  `git update-ref` **from detached temp worktrees**: `lanes/merge.py:440,474` and
  `cli/commands/merge.py:994` (verified — the only three update-ref sites in src/specify_cli).
  `update-ref` bypasses git's checked-out-branch protection and updates nothing in the worktree
  that has the branch checked out (coord worktree; branch == mission_branch, merge.py:2513-2515).
- Why no resync? → `_refresh_primary_checkout_after_merge` (`merge.py:698-718`, verified `git reset
  --hard HEAD`) repairs **only the primary checkout**; `CoordinationWorkspace.resolve`
  (`workspace.py:160-211`) verifies symbolic-ref name only and never repairs staleness.
- **Root structural defect:** plumbing-level ref mutation with no invariant that every worktree
  checking out that ref is resynced (or that bookkeeping commits bypass the worktree entirely).
Note: the backstop is the *detector working as designed*; no data loss — but every coord-topology
mission with >1 ref advance before bookkeeping breaks unattended merge.

### Class C — Nominally read-only commands mutating checkout state (LIVE — #1861 Part 1)
`finalize-tasks --validate-only`: `mission.py:2462` calls `_ensure_branch_checked_out` (helper at
:781-812 runs `git checkout`, never restores) **before** the first `validate_only` guard (:2496).
Verified at HEAD. Part 2 (safe-commit checkout bounce) is retired: safe_commit fails closed with
`SafeCommitHeadMismatch` (`commit_helpers.py:894-901`, since 8e79b3f6d 2026-05-28, pre-dating the
issue). Root defect: branch positioning treated as an eager precondition retained from the
pre-WP07 flow where the checkout *was* the read surface; post-WP07 reads anchor on the primary
feature dir, so the checkout move is pure side effect in validate-only mode.

### Class D — Workspace-resolution fall-through treated as success (LIVE residuals — #1833)
The naming-divergence *trigger* (raw mid8 handle → husk names `.worktrees/01KTRC04-lane-X`) was
fixed in #1850 (`workflow.py:926-938` returns canonical slug). The structural defect survives,
verified at HEAD:
- `ReviewLock.acquire(Path(workspace_path), ...)` at `workflow.py:2237` runs **before** the
  `if not workspace.exists:` creation block at :2243; `ReviewLock.save` mkdirs the path
  (`review/lock.py:102-105`) — any future resolver divergence mints a husk, and the subsequent
  `git worktree add` failure is only a **warning** (`workflow.py:2264-2266`).
- `ResolvedWorkspace.exists` is bare `Path.exists()` (`workspace/context.py:148-150`) — a husk with
  no `.git` counts as an existing workspace.
- move-task approval gates only on `worktree_path.exists()` (`agent/tasks.py:1346`) then runs git
  with `cwd=worktree_path` (:1404,1437,1484,1498) — `git -C <husk>` falls through to the primary
  repo, producing false "No implementation commits" / false-dirty verdicts.
**Root defect:** no layer enforces "a resolved workspace must be an actual git worktree; git
fall-through to an enclosing repo is a resolution FAILURE."

### Class E — Background writers vs git operations (CLOSED — #1789)
Daemons/dashboard rewrote tracked `status.json` during rebase/checkout + #1071 daemon-leak
regression. Fixed in #1850: `git_operation_in_progress()` gate (`status/views.py:198-296`,
linked-worktree-aware), write-free `materialize_snapshot` for dashboard
(`dashboard/scanner.py:576-608`), canonical scoped reaper (`sync/owner.py:467-816`, wired at
`daemon.py:1017-1025`). Regression tests exist. Residual (accepted): foreground `materialize()`
(`reducer.py:318-345`) still writes tracked status.json — dormant if a new background caller appears.

### Class F — Merge-driver environment/schema assumptions (#1736 — core fixed, hardening debt live)
Bugs A/B/C fixed (verified: `lanes/merge.py:335-337` venv-PATH env threaded to all subprocess calls;
`status/event_log_merge.py:35-63` event_id-only requirement + `(at|timestamp, event_id)` sort key;
`merge.py:393-435,526-527` PLANNED fallback + ValueError tolerance). Live debt, verified:
- `coordination/status_transition.py:399-400` broad `except Exception  # noqa: BLE001` returning
  `Lane.GENESIS` — a dormant mask that swallows the sentinel ValueError class silently.
- env construction is inline in `_merge_branch_into` (no `_make_merge_env()` helper) — new
  subprocess calls can silently omit `env=_env`.
- no mixed `at`/`timestamp`/neither ratchet test for `merge_event_payloads`
  (`tests/status/test_event_log_merge.py` only tests homogeneous `at`).

### Class G — Publish-layer policy enforced in local merge path (CLOSED — #1571)
Remote-sync preflight gated on `if effective_push:` (`merge.py:1911-1918`;
`merge/push_preflight.py:4-9,78-81`); non-destructive remediation (`merge/preflight.py:34-103`).
Fixed by PR #1719 (2026-06-05). Close.

---

## 2. Falsification record

| Class | Falsifier checked | Result |
|---|---|---|
| A drained | A still-live write/read surface diverging from `resolve_placement_only` for the *named* defects | NOT FOUND for #1770/#1816/#1827/#1771/#1735-core — all route through the unified resolver (citations above). Hypothesis "A is fully closed" IS falsified by residuals A-r1/A-r2 (gate.py:597 and finalize residue verified live). |
| B | A resync of the coord worktree after update-ref, or staleness self-heal in `CoordinationWorkspace.resolve`/`BookkeepingTransaction` | NOT FOUND — grep confirms only 3 update-ref sites, only-primary `reset --hard` (merge.py:698-718), resolve() checks symbolic-ref name only. The lane sparse-checkout `read-tree -mu HEAD` (`coordination/workspace.py:327`) is creation-time only, not a post-update-ref repair. Class B stands. |
| B alt-hypothesis "backstop itself is buggy" | Would require commit_helpers diffing wrong refs | FALSIFIED — backstop diffs index vs HEAD correctly; the index genuinely is stale. Detector, not defect. |
| C | A `validate_only` guard before mission.py:2462, or branch-restore in the helper | NOT FOUND — read :2455-2500: checkout fires unconditionally; first guard at :2496. Part-2 hypothesis "safe-commit bounces checkout" FALSIFIED (fail-closed HEAD assertion since 8e79b3f6d). |
| D | A `.git`-marker check in `ResolvedWorkspace.exists` or move-task, or lock-after-create ordering | NOT FOUND — context.py:148-150 bare Path.exists; workflow.py lock at :2237 precedes creation at :2243; worktree-add failure is a warning only. Class D stands. |
| E | Any remaining background materialize/write of tracked status.json | NOT FOUND in daemon/dashboard (grep clean per recon; gitop guard verified). Class E falsified-as-live → CLOSED. |
| F core | Subprocess call in `_merge_branch_into` missing `env=_env` | NOT FOUND (all 15 calls pass env). Core closed; debt items each re-verified live. |
| G | Sync preflight outside `if effective_push:` | NOT FOUND. CLOSED. |
| Cluster meta-hypothesis "all 13 stem from coord worktree under .worktrees/" | #1571 (publish-layer policy), #1789 (background writers), #1861 (eager checkout) | PARTIALLY FALSIFIED — the cluster is dominated by Class A but contains 3 mechanically unrelated classes that keyword triage wrongly folded in. |

---

## 3. Divergence matrix (issues × classes)

| Issue | A split-brain | B ref-resync | C fake-read-only | D fall-through | E bg-writers | F env/schema | G publish-layer | Verdict |
|---|---|---|---|---|---|---|---|---|
| #1770 | ●fixed | | | | | | | close-as-fixed (PR #1793 + #1850) |
| #1827 | ●fixed | | | | | | | close-as-fixed (rc42 9c8bff06f); file test-gap follow-up (A-r3) |
| #1816 | ●fixed | | | | | | | close-as-fixed (#1850 WP06) |
| #1814 | ●residual A-r1 | | | | | | | update + narrow to non-status residue |
| #1771 | ●fixed (write-path variant) | | | | | | | close-as-fixed (#1850 WP08) |
| #1735 | ●core fixed, residual A-r2 | | | | | | | update + close or split residual |
| #1784 | ●core fixed (dup of #1777) | | ◐ (rough edges: dry-run msg, backstop wording) | | | | | close core as dup/#1850; split P3 polish |
| #1826 | | ● LIVE | | | | | | **fix-in-3.2.0** — the one fully-valid bug |
| #1861 | | | ● Part 1 LIVE | | | | | fix-in-3.2.0 (one-line guard) + mark Part 2 resolved |
| #1833 | | | | ● residuals LIVE | | | | fix-in-3.2.0 (fall-through-as-failure invariant) |
| #1789 | | | | | ●fixed | | | close-as-fixed (#1850 WP11/WP12) |
| #1736 | ◐ (exposed by topology) | | | | | ●core fixed, debt LIVE | | re-scope to 3 hardening items |
| #1571 | | | | | | | ●fixed | close-as-fixed (dup of #1706, PR #1719) |

**Fold-ins / duplicates:** #1784-core = dup of #1777 (collaborator-confirmed) and fixed by the same
#1850 work as #1816/#1814; #1771/#1735 are a write-target/read-source sibling pair (one root
cause); #1571 superseded by #1706/#1719; #1833 shares its resolver-divergence class with #1832.
Seven of thirteen issues are pure close-as-fixed hygiene; GitHub state is stale relative to code.

---

## 4. Dormant masks (same defect class, no filed issue yet)

1. **`coordination/status_transition.py:399-400`** — broad `except Exception` returns
   `Lane.GENESIS`, silently converting any read/parse/sentinel error into "unseeded WP". Masks
   Class-F sentinel errors *and* future Class-A surface mistakes. (Named in #1736 but unfixed.)
2. **`cli/commands/agent/workflow.py:2264-2266`** — `git worktree add` failure downgraded to a
   `Warning:` print and execution continues against a nonexistent/husk workspace (Class D mask).
3. **`workspace/context.py:148-150`** — every consumer of `resolve_workspace_for_wp` inherits the
   husk-passes-as-workspace defect, not just review-claim/move-task (Class D, broader than #1833).
4. **`retrospective/gate.py:597`** — direct `feature_dir/"status.events.jsonl"` read; any caller
   passing a primary path on a coord-topology mission reproduces #1735's stale-lane verdict
   (Class A dormant).
5. **`cli/commands/agent_retrospect.py:432`** — identity-path (`resolved.feature_dir`) consumption;
   currently artifact-existence only, but one refactor away from an events read (Class A dormant).
6. **`agent/mission.py:781-812` `_ensure_branch_checked_out`** — never restores the prior branch;
   *every* caller, not only validate-only finalize, leaves the operator's checkout moved (Class C
   generalization of #1861).
7. **`agent/mission.py:99-131` `_stage_finalize_artifacts_in_coord_worktree`** — leaves untracked
   `lanes.json`/`tasks/*` copies on the primary checkout forever; feeds any *future* dirty-tree
   gate, not just record-analysis (Class A residue generator).
8. **`status/reducer.py:318-345`** foreground `materialize()` writes tracked status.json — safe
   today; becomes #1789-redux the moment a new background/timer caller is added (Class E latent).
9. **`git/commit_helpers.py:321-339`** — backstop message always says "working tree is behind HEAD"
   regardless of actual divergence cause; a diagnostic mask that sent #1784's reporter (and will
   send future operators) down the wrong recovery path.
10. **`lanes/merge.py` inline `_env` construction** — the 16th subprocess call added to
    `_merge_branch_into` without `env=_env` silently reintroduces #1736 Bug A (Class F).
11. **`cli/commands/merge.py:994` baking update-ref** — second live instance of Class B beyond the
    Stage-1 sites; any *new* `update-ref` call site (e.g. future bookkeeping) inherits #1826 unless
    fix B1 lands as a shared helper.

---

## 5. Structural fix plan (minimal set, dependency-ordered)

### Fix 1 — `advance_branch_ref()` invariant helper (Class B) — closes #1826; defuses mask 11
**What:** Extract one helper (suggested home: `src/specify_cli/git/ref_advance.py` or
`commit_helpers.py`): wrap `git update-ref refs/heads/<branch> <sha>`, then consult
`git worktree list --porcelain`; if any worktree has `<branch>` checked out, resync it
(`git -C <wt> reset --hard <sha>`, or `read-tree -mu HEAD` if local-change-preserving semantics are
wanted) under the feature-status lock. Replace the three call sites (`lanes/merge.py:440,474`,
`cli/commands/merge.py:994`). Defense-in-depth: teach `BookkeepingTransaction._acquire_locked`
(`coordination/transaction.py`) to detect index-behind-HEAD and self-heal before staging.
**Blast radius:** merge pipeline only; resync of a worktree that exists solely for bookkeeping
commits is semantically safe (it carries no unique uncommitted state by design — verify and assert
that precondition in the helper, fail loudly if dirty).
**Tests:** integration test — coord-topology mission, ≥2 lane merges + number baking, then done-event
bookkeeping must succeed unattended; ratchet test greping that no raw `update-ref` subprocess call
exists outside the helper.

### Fix 2 — validate-only is non-mutating (Class C) — closes #1861 Part 1; shrinks mask 6
**What:** Gate `mission.py:2462` behind `not validate_only` (reads at :2466+ already anchor on the
primary feature dir, not HEAD — verified). Preferred deeper cut: delete the eager call entirely and
let the planning-commit path own destination positioning; if the helper survives, make it
save/restore the previous ref for any non-commit caller. Update #1861 to record Part 2 as already
resolved by `SafeCommitHeadMismatch`.
**Blast radius:** one call site; commit-phase behavior unchanged.
**Tests:** `finalize-tasks --validate-only` asserts `git symbolic-ref HEAD` unchanged before/after,
on a repo where mission target ≠ current branch.

### Fix 3 — "fall-through is failure" workspace invariant (Class D) — closes #1833 residuals (+#1832 class); defuses masks 2, 3
**What (three coordinated edits, one invariant):**
(a) `ResolvedWorkspace.exists` (`context.py:148`) requires `(worktree_path / ".git").exists()`
(file or dir), not bare path existence; add `is_git_worktree` property.
(b) `workflow.py`: move `ReviewLock.acquire` *after* the workspace-exists/create block, and promote
the `git worktree add` failure from warning to hard error.
(c) `agent/tasks.py:1346`: before any `git -C worktree_path`, assert
`git -C <path> rev-parse --show-toplevel == <path>`; mismatch → structured resolution-failure error,
never the primary repo's answer.
**Blast radius:** review-claim and move-task flows; husks already on disk will now error explicitly
(desired) — ship with a doctor check that lists/removes `.worktrees/*` entries lacking `.git`.
**Tests:** plant a husk dir, assert review-claim refuses/recreates and move-task reports resolution
failure instead of "No implementation commits".

### Fix 4 — drain Class A residuals — closes #1814 (narrowed), #1735 residuals, #1827 test gap
**What:** (a) Make `_stage_finalize_artifacts_in_coord_worktree` remove (or never create) the
primary-checkout copies of artifacts it commits to coord — eliminate the residue at the source
rather than widening `COORD_OWNED_STATUS_FILES` (widening the exclusion list is the per-symptom
patch; cleaning the writer closes the class). (b) Route `retrospective/gate.py:597` and
`agent_retrospect.py:432` through `resolve_status_surface`; add the AC7 "identity-only" docstring to
`ResolvedMission.feature_dir`. (c) Add an architectural test banning
`resolved.feature_dir → read_events()/status.events.jsonl` outside the surface resolver (extend
`test_execution_context_parity.py`). (d) Add the missing coord-topology baseline-recording
regression test (unmock the helpers in `test_merge_coord_topology_1772.py` or add a sibling).
**Depends on:** nothing; independent of Fixes 1-3.
**Blast radius:** finalize staging + retrospect read paths; low.

### Fix 5 — Class F hardening (one small PR) — re-scopes #1736
Extract `_make_merge_env()` in `lanes/merge.py` and ratchet-test that every subprocess call uses it;
narrow `status_transition.py:399` to `except (ValueError, FileNotFoundError)` with the GENESIS
fallback documented; add the mixed `at`/`timestamp`/neither sort ratchet test to
`tests/status/test_event_log_merge.py`. Also (from #1784 leftovers): suppress "Upgrade complete!"
on `--dry-run` (`upgrade.py:987`) and make the safe_commit backstop message
(`commit_helpers.py:321-339`) report *which* divergence it found (defuses mask 9).

### Fix 6 — issue hygiene (no code)
Close as fixed citing landed commits: #1770, #1789, #1816, #1771, #1571, #1827 (file A-r3 follow-up),
#1784-core (dup #1777), #1735-core. Update #1814/#1736/#1833/#1861 to their narrowed residual scope.
Seven open issues currently describe retired behavior — the tracker itself is the biggest current
source of triage noise for this cluster.

**Order:** 6 (hygiene, unblocks triage) → 2 (one-liner) → 1 (only live hard blocker) → 3 → 4 → 5.
Fixes 1-5 are mutually independent; all are 3.2.0-sized.

---

## 6. Why the cluster kept shape-shifting (Stenographer's note)
Every class shares one observability gap: failures surface as *git's* error messages
("paths ignored by .gitignore", "working tree is behind HEAD", "No implementation commits"),
naming the detector rather than the diverging surface. Fixes 1/3/5 all include making the failing
layer name the *resolution* it used (which worktree, which ref, which placement kind) — that is the
cheapest structural change that prevents the next sibling from being filed as a brand-new bug.
