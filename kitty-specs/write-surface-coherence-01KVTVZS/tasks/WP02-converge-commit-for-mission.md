---
work_package_id: WP02
title: Converge commit_for_mission write path
dependencies:
- WP01
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T031
- T032
phase: Phase 2 - Write-site convergence
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2717427"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/acceptance/__init__.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Converge commit_for_mission write path

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/coordination/`.

---

## Objective

Thread the `MissionArtifactKind` through `commit_for_mission` and **all** of its
planning callers, and **remove the planning→coordination route** in the router arm so
planning artifacts commit to the primary `target_branch` (C-005 unification, not
parity). Status callers continue to resolve coord (C-001).

## Context & Constraints

Ground truth: [spec.md](../spec.md) FR-003, C-005; [plan.md](../plan.md) IC-02;
[contracts/placement-bifurcation.md](../contracts/placement-bifurcation.md) "Caller
obligations" table. **Depends on WP01** — the partition + the kind-aware
`resolve_placement_only` must exist first.

Key surfaces (verified file:line):
- `commit_router.py:82-206` — `commit_for_mission`; the `use_coord` decision at
  `commit_router.py:124` (`routes_through_coordination(resolve_topology(...))`) is the
  arm that currently routes planning artifacts to coordination.
- `commit_router.py:116` — `resolve_placement_only(repo_root, mission_slug)` (no kind).
- `spec_commit_cmd.py:155` — `commit_for_mission(...)` caller.
- `mission.py:1087-1126` — `_commit_artifact_to_branch` helper wrapping
  `commit_for_mission` (used by spec/plan setup callers).
- `mission.py:2345`, `mission.py:2392`, `mission.py:3825` — inline `commit_for_mission`
  tails (finalize / setup-plan / tasks).
- `mission.py:1919-1931` — record-analysis `commit_for_mission` (this commits the
  `ANALYSIS_REPORT`, a COORD kind — must stay coord).
- `tasks.py:3868-3870` — `map-requirements` uses `_planning_commit_worktree` (the WP03
  surface) AND must pass the kind where it commits a planning artifact.
- `acceptance/__init__.py:1398` — `_commit_acceptance_meta_via_router` commits
  `meta.json` (`PRIMARY_METADATA`).
- `status_transition.py:332` — `_resolve_write_target` calls `resolve_placement_only`
  (no kind today) for the STATUS write target; passes `STATUS_STATE`, stays coord (T031).
- `tasks.py:359` — review-currency **base read** via `resolve_placement_only` (coord
  kind, base-ref read; T031).
- `orchestrator_api/commands.py:796` — lane-base gate **base read** via
  `resolve_placement_only` (coord kind, base-ref read; T031).
- `tasks.py:2438` / `tasks.py:3076` — direct `safe_commit(target=CommitTarget(ref=target_branch))`
  planning writes that BYPASS the placement authority (move-task WP-file/status; `tasks.md`);
  `tasks.py:2425` `_skip_target_commit` coord-suppression flag (T032).

**Constraints**: NFR-003 (no new CLI flag — kind is internal). C-001 (status stays coord).
`resolve_placement_only`'s `kind` is REQUIRED (WP01) — all 7 sites must thread it.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> Overlaps `mission.py` / `commit_router.py` with WP03 and WP05; serialized by the
> WP01→WP02→WP03→WP05 dependency order.

## Subtasks & Detailed Guidance

### Subtask T006 – Thread `kind` through `commit_for_mission`

- **Files**: `src/specify_cli/coordination/commit_router.py`.
- **Steps**:
  1. Add `kind: MissionArtifactKind` as a **REQUIRED** keyword parameter on
     `commit_for_mission` (82-91) — **no default** (DECISION 1: mirrors the required
     `resolve_placement_only` kind; a default would silently route an un-threaded caller
     primary). Import `MissionArtifactKind` from `mission_runtime`.
  2. Pass it to the placement resolve at line 116:
     `placement = resolve_placement_only(repo_root, mission_slug, kind=kind)`.
- **Notes**: With no default, every `commit_for_mission` caller MUST pass a kind — the
  callers are converged in T007–T009 (and the direct-`safe_commit` writers in T032). A
  missing caller fails to typecheck rather than mis-routing (compile-time enumeration).

### Subtask T010 – Remove the planning→coord route in the router arm

- **Files**: `commit_router.py` (the `use_coord` arm, 124-150).
- **Steps**:
  1. The `use_coord` decision (124) must become **kind-aware**: a primary kind NEVER
     routes through coordination. Replace the topology-only test with one that also
     consults the partition — e.g. resolve the placement (already kind-aware after T006)
     and derive `use_coord` from whether the placement landed on the coordination ref
     vs the primary `target_branch`, OR gate `routes_through_coordination(...)` behind
     `kind not in _PRIMARY_ARTIFACT_KINDS`. Prefer deriving from the kind-aware
     `placement` so there is ONE authority (NFR-004): if `placement.ref == target_branch`
     for the mission, it is a direct primary commit; otherwise coord.
  2. With a primary kind, the function falls into the direct-commit branch
     (`worktree_root, commit_paths = repo_root, files`, 149) — no coord materialization.
  3. The protected-ref refusal at 126-137 still applies for the primary direct path —
     this is where WP03's FR-008 invariant surfaces; keep the refusal wired (do not
     delete it). **Its diagnostic message changes** (DECISION 5): the current text
     ("Run 'spec-kitty spec-commit … to route through the coordination worktree") is
     REPLACED by WP03 T015 with `mission create --start-branch <feature-branch>`
     guidance. WP03 owns the message rewrite at this arm; WP02 must leave the refusal
     return wired and not re-introduce coord-transit wording (merge-order awareness:
     WP02 lands first, WP03 rewrites the string).
- **Notes**: The ff-advance at 199 (`if use_coord and target_branch`) must NOT fire on a
  primary commit — WP05 governs that helper; here just ensure `use_coord` is False for
  primary kinds.

### Subtask T007 – spec-commit + artifact-commit callers pass kind

- **Files**: `spec_commit_cmd.py:155`, `mission.py:1092` (`_commit_artifact_to_branch`).
- **Steps**:
  1. `spec_commit_cmd.py`: `spec.md` is a `SPEC` artifact — pass `kind=MissionArtifactKind.SPEC`.
  2. `_commit_artifact_to_branch` (mission.py ~1058-1126): it takes an `artifact_type`
     string already — map it to a `MissionArtifactKind` (spec→SPEC, plan→
     FINALIZED_EXECUTION_PLAN, gap-analysis/generator-config→the existing kind) and pass
     `kind=` into the `commit_for_mission` call at ~1092. Add a small `_kind_for_artifact`
     mapping helper (keep it ≤15 complexity; tests in WP02).
- **Notes**: If an `artifact_type` has no obvious kind, do NOT silently default to
  `SPEC` — raise/assert on the unmapped type so the gap is loud (DECISION 1 spirit:
  no silent fallback). Add the missing mapping entry explicitly. Planning artifacts are
  primary by design, but the kind must be *named*, not guessed.

### Subtask T008 – mission.py inline tails + record-analysis pass kind

- **Files**: `mission.py:2345`, `:2392`, `:3825`, `:1919`.
- **Steps**:
  1. `:2345` / `:2392` (finalize tail / setup-plan): pass the planning kind
     (`FINALIZED_EXECUTION_PLAN` / `SPEC` as appropriate to the artifact committed).
  2. `:3825` (tasks tail): `tasks.md` is `TASKS_INDEX` (primary) → pass `TASKS_INDEX`.
  3. `:1919` record-analysis: the `analysis-report.md` is `ANALYSIS_REPORT` (COORD) —
     pass `kind=MissionArtifactKind.ANALYSIS_REPORT` so it **stays on coordination**
     (C-001). This is the explicit COORD caller proving the bifurcation.
- **Notes**: Confirm each inline tail's committed file matches the kind you pass — read
  the `files=(...)` argument at each site.

### Subtask T009 – map-requirements + acceptance-meta callers

- **Files**: `tasks.py:3868-3870`, `acceptance/__init__.py:1398`.
- **Steps**:
  1. `tasks.py` map-requirements writes a WP prompt edit / `tasks.md` — pass the
     primary kind (`TASKS_INDEX` or `WORK_PACKAGE_TASK` per the file committed). Note:
     map-requirements currently uses `_planning_commit_worktree` directly (the WP03
     surface) — coordinate: after WP03 that helper is partition-aware, so here just
     ensure the kind is threaded where it commits.
  2. `acceptance/__init__.py` `_commit_acceptance_meta_via_router`: `meta.json` is
     `PRIMARY_METADATA` → pass `kind=MissionArtifactKind.PRIMARY_METADATA`. This realizes
     the INV-5 symmetry (meta moves to primary on the write side).
- **Notes**: `record_acceptance` writes meta to the primary feature dir already
  (`acceptance/__init__.py:760`); this change makes the COMMIT land on primary too.

### Subtask T011 – Red-first caller-convergence test (DIRECTIVE_034)

- **Files**: `tests/specify_cli/` (locate the existing commit_router / spec_commit test
  module; extend it).
- **Steps (red-first)**:
  1. **CRITICAL red-first entry point (DECISION 6)**: drive red through the
     **PRE-EXISTING** no-kind entry point — the `spec-commit` CLI command, or
     `commit_for_mission(...)` **WITHOUT** a `kind` argument as it exists pre-fix. Do
     **NOT** write the red test against `commit_for_mission(..., kind=SPEC)`: pre-fix
     there is no `kind` parameter, so that call `TypeError`s and captures NOTHING. The
     red test must drive the operator-facing planning commit (`spec-commit` of a
     `spec.md` under `kitty-specs/<slug>/`) on a **coord-topology fixture** and assert
     the resulting commit lands on `target_branch` (inspect `result.placement_ref` / the
     committed ref). Pre-fix this lands on coord → red.
  2. Add the COORD assertion: an `ANALYSIS_REPORT` commit (record-analysis path) lands on
     the coordination branch — driven through its pre-existing entry point.
  3. Prove red against pre-T010 code (the planning commit lands on coord pre-fix) by
     running the test on the unfixed tree (revert + restore), then green after.
  4. Realistic fixture: real ULID/mid8, real `<slug>-<mid8>` dir.

### Subtask T031 – Thread an explicit `kind` at EVERY `resolve_placement_only` call site (DECISION 2)

- **Purpose**: `resolve_placement_only`'s `kind` is now REQUIRED (WP01) — every one of
  the **7** call sites must declare its kind so behavior is preserved/intended. Missing
  a site is a compile error, but the *correct kind per site* is the real work.
- **Files**: `status_transition.py` (newly owned), `tasks.py`, `mission.py`,
  `spec_commit_cmd.py`, `commit_router.py`, plus the `orchestrator_api/commands.py` base
  reads (the `commands.py` history-append site at `:1283` is WP03-owned T013; the
  lane-base gate at `:796` is threaded here as a base-ref read).
- **The 7 sites and their kinds** (verified file:line):
  1. `commit_router.py:116` — threaded via the `kind` param in T006 (commit path).
  2. `status_transition.py:332` → pass `kind=STATUS_STATE` — this is the status write
     target; it MUST keep resolving `coordination_branch` under coord topology
     (C-001 / G-2). **Stays coord.**
  3. `tasks.py:359` (review-currency base read) → pass the **coord-preserving kind**
     (`STATUS_STATE`): this is a base-ref read for review currency under coord topology
     and must keep the coord ref. **Stays coord.**
  4. `orchestrator_api/commands.py:796` (lane-base gate, base-ref read) → pass the
     **coord-preserving kind** (`STATUS_STATE`): a base-ref read under coord topology
     must keep the coord ref. **Stays coord.**
  5. `safe_commit_cmd.py:206` — WP03 T012 (kind from file name; planning → primary).
  6. `orchestrator_api/commands.py:1283` — WP03 T013 (`WORK_PACKAGE_TASK` → primary).
  7. `mission.py:749` (`_planning_commit_worktree` placement helper) — WP03 T014
     (partition-aware; planning → primary).
- **Steps**:
  1. Thread the explicit kind at sites (2)/(3)/(4) here in WP02 (sites 5/6/7 are WP03).
     For (3) and (4), pin the coord-preserving kind because they are **base-ref reads**
     (review-currency base / lane-base gate) — switching them to a primary kind would
     wrongly read the primary ref as the base under coord topology and corrupt the
     currency/gate comparison. Add a one-line code comment at each citing "base-ref read
     under coord topology — coord kind preserves G-2".
- **DoD (DECISION 2)**: a test asserts `status_transition._resolve_write_target(...)`
  (the function at `:308-332`) on a **coord-topology fixture** returns the
  `coordination_branch` ref (RED if it returns `target_branch`). This pins that the
  status write target stayed coord after the required-kind threading.

### Subtask T032 – Converge the direct-`safe_commit` planning writers + re-evaluate `_skip_target_commit` (DECISION 3)

- **Purpose**: Two planning writes in `tasks.py` bypass `commit_for_mission` and the
  placement authority entirely, hardcoding `safe_commit(target=CommitTarget(ref=target_branch))`.
  These must route through the **kind authority** so they obey the partition (G-1: ONE
  routing authority, not a parallel hardcode).
- **Files**: `tasks.py` (`:2438`, `:3076`, `:2425`).
- **Steps**:
  1. `tasks.py:2438` (move-task: commits the WP-file + status artifacts) — its committed
     files are `WORK_PACKAGE_TASK` (primary) plus status artifacts (coord). Route the
     planning (WP-file) write through the kind authority (resolve placement with
     `WORK_PACKAGE_TASK`), and the status artifacts with `STATUS_STATE`. Replace the
     hardcoded `CommitTarget(ref=target_branch)` with the placement the authority returns
     per kind — do not hardcode a ref.
  2. `tasks.py:3076` (commits `tasks.md`) — `tasks.md` is `TASKS_INDEX` (primary). Route
     through the kind authority with `TASKS_INDEX`; replace the hardcoded
     `CommitTarget(ref=target_branch)`.
  3. **Re-evaluate `_skip_target_commit`** (`tasks.py:2411/2425`): this coord-suppression
     flag previously skipped the `target_branch` commit when the artifact was destined
     for coord. Now that these writes are PRIMARY kinds resolved through the one authority,
     `_skip_target_commit` must NOT remain a parallel routing authority (G-1). Determine
     whether it is still needed at all: if it only existed to suppress the primary commit
     for coord-routed planning artifacts (which no longer route to coord), retire it or
     narrow it to the genuine coord-artifact case so there is a single routing authority.
- **Notes**: This is the "missed direct-`safe_commit` planning writers" the squad found.
  The hazard is a hardcoded ref that ignores the partition entirely — exactly the
  split-brain this mission closes. The behavioral guard in WP07 T027 exercises a bypass
  writer and would catch a regression here.
- **DoD**: the two `tasks.py` planning writes resolve their target through the kind
  authority (no hardcoded `CommitTarget(ref=target_branch)` for the planning files);
  `_skip_target_commit` is no longer a second routing authority. Covered by the
  caller-convergence test (T011) extended to a `move-task` / `tasks.md` write path.

## Test Strategy

- `pytest tests/specify_cli/ -k "commit_router or spec_commit or write_surface" -q`.
- `ruff check` + `mypy` on every owned file — zero issues, no suppressions.
- Any new helper (`_kind_for_artifact`) needs direct tests (Sonar new-code coverage).

## Risks & Mitigations

- **"Fixed N of M" trap** (live per research D-1): missing a caller leaves a planning
  artifact on coord. Mitigation: enumerate ALL sites in T007–T009 against the verified
  file:line list; WP07's behavioral guard catches a regression.
- **record-analysis mis-kinded**: passing a primary kind there would wrongly move the
  analysis report to primary. Mitigation: T008 explicitly pins `ANALYSIS_REPORT` (COORD).
- **`use_coord` derivation drift**: deriving `use_coord` from two authorities re-opens
  the split-brain. Mitigation: derive it from the ONE kind-aware `placement` (NFR-004).
- **Hardcoded planning writers (DECISION 3)**: `tasks.py:2438/3076` hardcode
  `CommitTarget(ref=target_branch)` and `_skip_target_commit` is a parallel routing
  authority. Mitigation: T032 routes them through the kind authority and retires/narrows
  the flag — verify no hardcoded ref survives for a planning file (G-1).
- **Base-ref reads mis-kinded (DECISION 2)**: passing a primary kind at `tasks.py:359`
  or `commands.py:796` would read the primary ref as the base under coord topology and
  corrupt the currency/gate comparison. Mitigation: T031 pins the coord-preserving kind
  at both base-ref reads with a code comment + the `_resolve_write_target` coord test.

## Review Guidance

- Verify every `commit_for_mission` / placement caller in the owned files passes a kind,
  and that the kind matches the committed file. `commit_for_mission`'s `kind` is REQUIRED
  (no default) — reject a defaulted param.
- Verify **all 7** `resolve_placement_only` sites the WP owns are threaded (T031): the
  three base/status reads (`status_transition:332`, `tasks.py:359`, `commands.py:796`)
  pass the coord-preserving kind and stay coord; the `_resolve_write_target` coord test
  is present and asserts `coordination_branch`.
- Verify the direct-`safe_commit` planning writers (`tasks.py:2438/3076`) route through
  the kind authority and `_skip_target_commit` is no longer a parallel router (T032/G-1).
- Verify the COORD callers (`ANALYSIS_REPORT`, status) still resolve coordination.
- Verify the red-first test drove red through `spec-commit` / the no-kind entry point
  (NOT `kind=SPEC`), and failed pre-fix (request red-run evidence).
- Note: the protected-ref refusal message in `commit_router.py` is rewritten by WP03
  T015 — WP02 leaves it wired without coord-transit wording.

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T20:35:00Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – Assigned agent via action command
- 2026-06-23T21:32:54Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – WP02 complete + committed (ee080bae1): threaded kind through commit_for_mission + all 7 owned resolve_placement_only sites; removed planning->coord route; converged 2 direct safe_commit writers (T032). Red-first proven; diff-scoped ruff exit 0; net suite 29 baseline failures fixed, 0 introduced. --force used for known shared-lane kitty-specs guard friction (spec.md on lane base); remaining red is FR-008/WP03 + pre-existing baseline.
- 2026-06-23T21:33:22Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – WP02 complete (ee080bae1)
- 2026-06-23T21:35:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=2686301 – Started review via action command
- 2026-06-23T21:48:30Z – user – shell_pid=2686301 – Moved to planned
- 2026-06-23T21:49:19Z – claude:opus:python-pedro:implementer – shell_pid=2704117 – Started implementation via action command
- 2026-06-23T21:59:17Z – claude:opus:python-pedro:implementer – shell_pid=2704117 – Cycle 1 fix: re-pinned TestCoordTopologyPlanningCommitRoundTrip to planning-on-primary (write+read-back primary; status still coord); anti-fakeable round-trip preserved. ruff exit 0
- 2026-06-23T22:00:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=2717427 – Started review via action command
- 2026-06-23T22:05:28Z – user – shell_pid=2717427 – Cycle-1 re-review passed (renata). Cycle-0 blocker (TestCoordTopologyPlanningCommitRoundTrip asserting removed planning->coord contract) fixed by 0c0487f92. Re-pin legitimate: bifurcation leg present and non-vacuous (STATUS_STATE stays COORD while SPEC routes PRIMARY). Red-first verified myself: removing SPEC from _PRIMARY_ARTIFACT_KINDS turned both round-trip tests RED; restored -> green. No regression: changed file 7/7, regression suites 49/49, ruff clean. Scope = one test file (133 ins / 47 del). --force/--skip-review-artifact-check for inherited-state guards only.
