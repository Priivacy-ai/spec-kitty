---
work_package_id: WP03
title: Converge bypass writers + 2nd routing authority + FR-008
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-008
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Write-site convergence
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2926014"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/safe_commit_cmd.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/git/commit_helpers.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Converge bypass writers + 2nd routing authority + FR-008

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/orchestrator_api/`.

---

## Objective

Converge the write sites that **bypass** `commit_for_mission` — the `safe-commit`
command (`_resolve_mission_aware_target`) and `append-history` — and the **second
routing authority** `_planning_commit_worktree`, onto the kind-aware partition. Then
enforce **FR-008**: a primary-kind commit whose `target_branch` is a protected branch
is refused with feature-branch guidance.

The "fixed N of M" trap is live (research D-1): WP02 closed the `commit_for_mission`
callers; this WP closes the bypass writers and the parallel router so the split is fully
closed.

## Context & Constraints

Ground truth: [spec.md](../spec.md) FR-003, FR-008, C-002; [plan.md](../plan.md) IC-02;
[research.md](../research.md) D-3 (protected-primary = require a feature branch, no coord
transit); [contracts/placement-bifurcation.md](../contracts/placement-bifurcation.md) G-4.
**Depends on WP02** (the kind-aware `commit_for_mission` + partition must be in place).

Verified surfaces:
- `safe_commit_cmd.py:192-209` — `_resolve_mission_aware_target` calls
  `resolve_placement_only(repo_root, mission_slug)` (no kind today) → the planning commit
  lands wherever topology routes it. The discriminator is `_mission_slug_from_paths`
  (170-189) which fires when a file lives under `kitty-specs/<slug>/`.
- `orchestrator_api/commands.py:1260-1303` — `_resolve_history_commit_args`: WP prompt
  files are committed; at `:1283` it resolves `resolve_placement_only`, at `:1289-1294`
  it routes to the coord worktree when `routes_through_coordination` holds. WP prompt
  files are `WORK_PACKAGE_TASK` — a **primary** kind now.
- `mission.py:752-806` — `_planning_commit_worktree`: the second routing authority; at
  `:775` it independently calls `routes_through_coordination(resolve_topology(...))` and
  stages into the coord worktree. For primary kinds it must return `(repo_root, paths)`.
- FR-008 guard: `safe_commit` step 6 raises `ProtectedBranchRefused`/
  `ProtectedBranchCommitError` (`specify_cli.git`) on a protected destination.
- FR-008 message sites (both rewritten in T015, DECISION 5):
  - `commit_router.py:126-137` — the router refusal (`no_op_wrong_surface` result),
    currently advises "Run 'spec-kitty spec-commit … to route through the coordination
    worktree" (a RETURNED result, not a raise).
  - `commit_helpers.py:285` — `ProtectedBranchRefused`, currently advises "Use the
    coordination worktree at .worktrees/<slug>-<mid8>-coord/, …" (a RAISED exception).

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> Overlaps `mission.py` with WP02/WP05 and `commit_router.py` with WP02/WP05;
> serialized by WP02→WP03→WP05. This WP rewrites the FR-008 refusal strings in
> `commit_router.py` (the arm WP02 wired) and `commit_helpers.py` (DECISION 5).

## Subtasks & Detailed Guidance

### Subtask T012 – `_resolve_mission_aware_target` consults the kind authority

- **Files**: `safe_commit_cmd.py:192-209`.
- **Steps**:
  1. A file under `kitty-specs/<slug>/` is a planning artifact (`SPEC`/
     `FINALIZED_EXECUTION_PLAN`/`TASKS_INDEX`/`WORK_PACKAGE_TASK`). Pass the kind into
     `resolve_placement_only(repo_root, mission_slug, kind=...)`. Determine the kind from
     the file name via a small mapping (reuse `_COORD_RESIDUE_FILENAMES`/`_COORD_RESIDUE_DIRS`
     inverse logic in `artifacts.py`, or add a public `kind_for_mission_file(rel_path)`
     helper in `mission_runtime` and consume it — prefer the public helper so there is
     ONE classification authority, NFR-004).
  2. For planning artifacts the resolved target is now the primary `target_branch`
     (#2063 fix is preserved and corrected — planning lands primary, not coord).
- **Notes**: A status/bookkeeping file under `kitty-specs/<slug>/` (e.g.
  `status.events.jsonl`) must still resolve coord — the kind mapping handles that.

### Subtask T013 – `append-history` consults the kind authority

- **Files**: `orchestrator_api/commands.py:1260-1303` (`_resolve_history_commit_args`).
- **Steps**:
  1. The WP prompt file is `WORK_PACKAGE_TASK` (a primary kind). Pass
     `kind=WORK_PACKAGE_TASK` into `resolve_placement_only` at `:1283`.
  2. Retire the `routes_coord` arm (`:1289-1294`) **for primary kinds**: a primary
     placement returns `(main_repo_root, CommitTarget(ref=target_branch))` — the WP prompt
     edit commits directly to the primary checkout, not the coord worktree. Keep the
     fallback-to-current-branch behavior (`:1296-1303`) for unresolvable missions.
- **Notes**: This removes the coord-worktree transit for history appends, matching the
  unification (C-005). Confirm `safe_commit` at `:1343` then targets the primary ref and
  worktree.

### Subtask T014 – Converge `_planning_commit_worktree` onto the partition

- **Files**: `mission.py:752-806`.
- **Steps**:
  1. `_planning_commit_worktree` decides coord-vs-primary independently at `:775`. Make
     it partition-aware: it must accept (or be called with) the artifact kind, and return
     `(repo_root, paths)` for a primary kind — no coord staging.
  2. Add a `kind: MissionArtifactKind` parameter (default a primary kind); when the kind
     is primary, short-circuit to `return repo_root, paths` BEFORE the
     `routes_through_coordination` check at `:775`. The coord-staging body (`:778-806`)
     then only runs for COORD kinds.
  3. Update its callers (`tasks.py:3870` map-requirements, and any history caller) to pass
     the kind — coordinate with WP02 T009 (map-requirements). If a caller commits a
     primary planning artifact, it now goes direct to primary.
- **Notes**: Do NOT delete the coord-staging body — it is still used by COORD-kind writes
  (governed in WP05). This WP makes the DECISION partition-aware; WP05 governs the helper
  internals.

### Subtask T015 – FR-008: refuse primary-kind commit to a protected target_branch + REWRITE both messages

- **Files**: `commit_router.py:126-137` (router refusal), `commit_helpers.py:285`
  (`ProtectedBranchRefused`). Both are owned by this WP.
- **Steps**:
  1. A primary kind resolves to `target_branch`. When that ref is protected (`main`/
     `master`), the commit must be **refused** with guidance to start a feature branch.
     This is the existing `ProtectedBranchRefused`/`ProtectedBranchCommitError` path —
     verify it FIRES for a primary-kind commit on a protected `target_branch`.
  2. **REPLACE (mandatory, not conditional — DECISION 5)** the coord-transit guidance in
     BOTH messages with `mission create --start-branch <feature-branch>` guidance:
     - `commit_router.py:126-137`: replace the "Run 'spec-kitty spec-commit … to route
       through the coordination worktree" diagnostic with text that tells the operator to
       create/start a feature branch (`mission create --start-branch <feature-branch>`)
       and commit planning artifacts there. The coordination worktree is no longer the
       remedy (planning never transits coord post-mission — C-005).
     - `commit_helpers.py:285` (`ProtectedBranchRefused`): replace "Use the coordination
       worktree at .worktrees/<slug>-<mid8>-coord/, …" with the same feature-branch
       guidance.
  3. Do NOT add a coord-transit fallback (C-002 — the deadlock is avoided by the
     feature-branch invariant, not by transiting coord).
- **DoD (DECISION 5)**: a test asserts each rewritten message **contains** the substring
  "feature branch" and does **NOT contain** "coordination worktree". Both the router
  refusal (returned result diagnostic) and `ProtectedBranchRefused` (raised exception
  message) are asserted.
- **Notes**: This is an **invariant**, not a special case — no new branch of behavior for
  protected primaries beyond refusal. The protected-ref refusal in `commit_router.py`
  was wired by WP02 T010 (message left intact); this WP rewrites its string and the
  `commit_helpers.py` string so the bypass paths refuse identically with the new remedy.
  Coordinate merge-order with WP02 (WP02 lands the refusal arm; WP03 rewrites the text).

### Subtask T016 – Red-first bypass-writer + protected-primary tests (DIRECTIVE_034)

- **Files**: `tests/specify_cli/` (safe-commit + orchestrator append-history modules).
- **Steps (red-first)**:
  1. Write the failing test FIRST through the pre-existing entry points:
     - `safe-commit` of a `spec.md` under `kitty-specs/<slug>/` on a coord-topology
       fixture lands on `target_branch` (pre-fix it lands coord — red).
     - `append-history` on a WP prompt file lands on `target_branch` on a coord fixture.
     - FR-008: a primary-kind commit on a protected `target_branch` raises the refusal,
       and the refusal message contains "feature branch" and NOT "coordination worktree"
       (DECISION 5 — assert on both the router-refusal diagnostic and the
       `ProtectedBranchRefused` message).
  2. Prove red against pre-WP03 code, then green. The message-content assertion is red
     pre-rewrite (the pre-fix strings say "coordination worktree").
  3. Realistic fixtures: real ULID/mid8, real `<slug>-<mid8>` dir, a real protected ref
     name (`main`).

## Test Strategy

- `pytest tests/specify_cli/ -k "safe_commit or append_history or planning_commit_worktree or protected" -q`.
- `ruff check` + `mypy` on owned files — zero issues, no suppressions.

## Risks & Mitigations

- **Three authorities to converge**: a missed one re-opens the split. Mitigation: the
  WP07 behavioral guard exercises a bypass writer AND `_planning_commit_worktree`
  explicitly (not just `commit_for_mission`).
- **Protected-primary deadlock**: refusing without guidance strands the operator.
  Mitigation: FR-008 message names the feature-branch remedy (D-3).
- **map-requirements coupling**: it consumes `_planning_commit_worktree`; coordinate the
  kind threading with WP02 T009.

## Review Guidance

- Verify ALL THREE bypass/parallel authorities are partition-aware (safe-commit,
  append-history, `_planning_commit_worktree`).
- Verify FR-008 refusal fires with feature-branch guidance and NO coord-transit fallback.
- Verify BOTH messages were rewritten (DECISION 5): the router refusal diagnostic AND
  `ProtectedBranchRefused` contain "feature branch" and do NOT contain "coordination
  worktree" — asserted by a test.
- Verify the red-first tests failed pre-fix.

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T22:06:03Z – claude:opus:python-pedro:implementer – shell_pid=2724995 – Started implementation via action command
- 2026-06-23T23:04:09Z – claude:opus:python-pedro:implementer – shell_pid=2724995 – WP03: converged 3 write authorities onto kind-aware partition + FR-008 rewrite. (1) safe-commit _resolve_mission_aware_target consults kind via new public kind_for_mission_file; (2) append-history WP-prompt->primary target_branch (retired coord arm + reads/commits primary feature dir); (3) _planning_commit_worktree partition-aware (primary kinds short-circuit BEFORE routes_through_coordination - the load-bearing convergence). FR-008 REWRITTEN in BOTH commit_router refusal diagnostic AND ProtectedBranchRefused: each contains 'feature branch', NOT 'coordination worktree' (asserted by test). Red-first proven via PRE-EXISTING append-history + sc6 entry points. Re-pinned sc6/finalize-clobber/validate-only/append-history to the new contract (G-4: protected target_branch refused; non-protected feature target lands directly per D-3). Diff-scoped ruff exit 0; zero new mypy/ruff. Net +7 tests fixed, 0 introduced. --force for inherited shared-lane kitty-specs guard.
- 2026-06-23T23:05:35Z – claude:opus:python-pedro:implementer – shell_pid=2724995 – WP03 impl complete (ca27c5327): bypass writers + 2nd authority converged + FR-008 message rewrite; +7 sc6 fixed. Canonical-surface sync (flat-mission divergence).
- 2026-06-23T23:05:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=2926014 – Started review via action command
- 2026-06-23T23:15:53Z – user – shell_pid=2926014 – Review passed (reviewer-renata). --force used ONLY for the inherited-state guard (lane branch carries committed kitty-specs/ planning artifacts from flattened topology; not a WP03 defect). 3 authorities converged: safe_commit _resolve_mission_aware_target kind-aware; append-history routes WORK_PACKAGE_TASK to primary (coord arm retired, mission_dir param removed); _planning_commit_worktree early-returns primary for is_primary_artifact_kind (independent planning->coord decision retired; surviving routes_through_coordination only reachable by COORD kinds + analysis-report residue). New classifiers kind_for_mission_file/is_primary_artifact_kind delegate to single _PRIMARY_ARTIFACT_KINDS partition (no parallel authority, NFR-004). FR-008: BOTH router refusal AND ProtectedBranchRefused say 'feature branch' + 'mission create --start-branch', NEITHER contains 'coordination worktree' (verified strings+assertions). Catch-22 re-pin LEGITIMATE: fixtures previously parked operator on protected main with placement escaping to coord; now operator on non-protected feature target_branch (D-3) - protected-main asserts REAL G-4 refusal+nothing-lands, feature asserts direct commit; setup/edge-cases/parametrization preserved (delete-assertion-not-test). Red-first via pre-existing entry points, not new kind= API. commands.py:796 STATUS_STATE untouched. Tests RE-RUN: WP03 new 26 passed/2xfail; sc6+finalize+orchestrator+wp05+protected-primary+coordination all green (388 passed). +0 introduced VERIFIED: 11 broad-sweep failures (ANSI/JSON env artifacts) byte-identical at WP02 base 0c0487f9. ruff clean; mypy net-improvement (WP03 fixed kind call-arg; remaining no-any-return pre-existing in untouched fn).
