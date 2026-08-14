# Mission Specification: Mission-Artifact Write-Path Integrity

**Mission Branch**: `mission/write-path-integrity`
**Created**: 2026-08-14
**Status**: Draft (post-research → post-design-squad → post-adversarial-squad → scope-narrowed; plan-ready)
**Input**: Treat the #3371 P0 as a *symptom of a structural problem*. Fix the coord/topology write-path
cluster (#3371, #2549, #3128, #3373; conditional #2570) at mandatory chokepoints, not another round of
whack-a-field. Complete the #1878 strangler and contribute to epic #2160.

> **Scope note (2026-08-14):** #3372 (upgrade-wedge) and #2702 (record-analysis) were **fixed and
> closed during this mission's authoring** — #3372 by the separate "upgrade-wedge cluster" mission
> **#3383** (landed in `upstream/main`; WP03/WP04/WP09 shipped the read-boundary duplicate-key guard +
> dup-key detect/repair + wedged-project self-recovery), and #2702's write-side confirmed closed +
> guarded (ticket closed with evidence). **Both are OUT of this mission's scope** — building the
> upgrade-wedge / doctor-repair requirements would duplicate/collide with #3383. This mission is now purely the **coord/topology partition
> + checkout-identity** cluster.

## Summary & Framing

The tracker's "ambient-location / write-path topology" cluster (#3129) keeps re-spawning because
**no mandatory seam enforces two invariants every mission-mutating write depends on**: (1) the write
originates from the checkout the mission *declares*, and (2) each artifact lands on the partition its
*kind* dictates. Both facts are *computed* today but nothing *refuses* on them, so each new command that
forgets to route correctly becomes a new field-level bug.

**This mission installs fail-closed refusals at the two mandatory write chokepoints** so the failure
class becomes hard to reintroduce rather than patched command-by-command.

### The disease, one table

| Issue | Latent-malformed write | Detonates in | Class |
|-------|------------------------|--------------|-------|
| #3371 (P0) | PRIMARY `lanes.json` committed to the **coord** ref | lane allocator `git merge` → add/add | #2160 partition |
| #2549 | COORD `status.*` committed to the **lane** ref (`move-task --force`) | tool's own later `--to approved` rejects it | #2160 partition (mirror of #3371) |
| #3128 | *(enabling gap)* nothing compares invoking checkout vs declared workspace | ambient-location write (2026-07-31 incident) | #1878 checkout-identity |
| #3373 (P2) | *(no artifact yet)* triplicated topology/checkout primitives that will drift | a future one-copy correctness fix | #2624 (substrate for #3128) |

### Structural approach — TWO mandatory refusing seams (not "one door")

The initial framing of a single fail-closed factory door was **corrected by the adversarial review**:
`build_execution_context()` (`mission_runtime/resolution.py:217`, the sole `MissionExecutionContext(`
construction site) receives only a **ref-only `placement_ref`** — it has *no file list*, so it
*cannot* enforce per-file partition purity. The honest, verified design is **two chokepoints**:

- **Seam A — Partition purity (at the write seam).** The shared planning-commit / commit-router write
  path (`implement.py::_run_planning_artifact_commit`, `commit_router._group_files_by_partition`,
  `placement_seam.write_target`) refuses (`PrimaryKindReachedCoordStagingError`) any batch that would
  route a PRIMARY kind to a coord ref or a COORD kind to a lane ref. **Every mission-mutating commit
  funnels through this seam** — this is where #3371/#2549 are actually fixed.
- **Seam B — Checkout-identity (at the WP-execution write, keyed on write-intent).** A mutating
  **WP-execution** write (`implement`/`review`) is refused when the invoking checkout is not the
  mission's declared *execution* workspace. This is keyed on **explicit write-intent at the true write
  call sites**, NOT on action-name — because `resolve_action_context(action="tasks"/"implement")` is
  reused as a **pure read vehicle** by ~20 modules (`_read_path_resolver.py:1622`), so an action-name
  gate would false-refuse reads.

Together: every mutating write passes one of two mandatory refusing seams. This still ends the
whack-a-field cycle — a *new* command cannot commit without passing Seam A, and cannot execute a WP
write from a foreign checkout without passing Seam B — while being truthful about where each invariant
can physically live. `PrimaryKindReachedCoordStagingError` (`commit_router.py:615`) is the codebase's
own proof that a defect class can be made a typed refusal at a seam; this mission gives it teeth on the
write path and adds the identity refusal at the WP-write. Both legs are on #1878's **sanctioned
deferred list**; **no topology / shadow-workspace redesign** (#1878 non-goal).

### Confirmed P0 root cause (git-true)

`implement.py::_commit_planning_artifacts_transaction` (`implement.py:890-902`, the
`placement_ref is not None` arm) commits the whole planning batch **verbatim to `placement_ref.ref`**,
which under coord topology is the coordination branch — a dirty PRIMARY `lanes.json` lands on coord
(commit `c3d92a364`). `_partition_files_for_commit` (`implement.py:714`) is **dead on this path**
(wired only into the legacy `else` branch). The lane then merges the recorded `planning_commit_sha`
(on `target_branch`, also carrying `lanes.json`); with `lanes.json` absent at the merge-base the merge
is a guaranteed add/add → `PlanningCommitMergeConflictError` (`worktree_allocator.py:339-356`),
violating ADR `2026-07-29-1` §3 (which the ADR itself deferred to #2160). This arm is a pinned C-004
deferral (`test_effective_destination_ref_is_placement_ref_verbatim`) — **this mission sanctions
reversing it.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Partition-correct commits: no artifact lands on the wrong branch (Priority: P1) — #3371 + #2549 — contributes to #2160

`implement`'s planning auto-commit (PRIMARY→coord, the P0) and `move-task --force` (COORD→lane, #2549)
today commit to the wrong partition. After this mission, every mission-mutating commit routes each file
to the partition its *kind* dictates via Seam A, and a mis-route **fails loud**.

**Why this priority**: The P0 blocks all implementation on coord + PR-bound missions; #2549 is its
exact mirror; fixing one direction alone leaves the other live (whack-a-field).

**Independent Test**: Reproduce `mission-a-p0-consistency`'s shape (coord topology, PR-bound
`--start-branch`); drive finalize + `implement WP01`; assert `allocate_lane(...)` returns **without**
`PlanningCommitMergeConflictError` and `git status --porcelain` is clean. Separately assert
`move-task --force` from a lane commits `status.*` to the coord ref (not the lane ref).

**Acceptance Scenarios**:

1. **Given** a coord-topology mission with a dirty uncommitted `lanes.json` at implement time, **When**
   `_ensure_planning_artifacts_committed_git` auto-commits, **Then** `lanes.json` (PRIMARY) commits to
   `target_branch`; any COORD-residue commits to the coord ref; **neither** partition commits an empty
   file group (empty group is skipped, never a hard-fail).
2. **Given** the coord + PR-bound `--start-branch` reproduction, **When** `implement WP01` allocates the
   lane, **Then** `_merge_recorded_planning_commit` completes without `PlanningCommitMergeConflictError`
   and no manual reconcile is required.
3. **Given** `move-task --force` from a lane (#2549), **When** it commits status, **Then** `status.*`
   (COORD) lands on the coord ref; a PRIMARY-kind or COORD-to-lane mis-route raises
   `PrimaryKindReachedCoordStagingError` at `_run_planning_artifact_commit`.
4. **Given** a legitimate coord status commit that co-travels `meta.json` (self-bookkeeping), **When**
   it commits, **Then** it succeeds — `meta.json` is exempt from the Seam-A refusal (self-bookkeeping
   exclusion runs *before* kind classification).
5. **Given** a crash between the PRIMARY and COORD partition commits, **When** `implement` is
   re-invoked, **Then** both commits re-drive idempotently (no-op resume) and no coord residue is
   stranded on primary.

---

### User Story 2 — `implement`/`review` refuse to run from a checkout the mission does not own (Priority: P1) — #3128 (Seam B)

An agent (e.g. a compacted/resumed session) runs `implement`/`review` from the wrong checkout. Today
nothing compares the invoking checkout against the mission's *declared execution* workspace, so the
write silently lands in the ambient location (the 2026-07-31 incident). After this mission the
WP-execution write refuses on that mismatch.

**Why this priority**: The structural gap under the #3129 class; wiring the refusal at the true
WP-write (keyed on write-intent, not action-name) is what makes it fire without breaking reads.

**Scope (operator decision)**: This mission's Seam-B refusal covers **`implement`/`review` only** — the
WP-bearing commands that write from a lane and caused the incident. Extending checkout-identity to the
non-factory commands (`move-task`, `record-analysis`, `migrate`, `doctor --fix`, `merge`) is **explicit
follow-on scope** (they are covered for the *partition* mis-route class by Seam A).

**Independent Test** (local fixture; no dependency on the `spec-kitty-saas` repo): from mission B's lane
in the same repo/registry, run a mission-A `implement`; assert it refuses (exit ≠ 0, actionable error).
From mission A's own lane, assert it proceeds. From the repo root, assert a planning command (`tasks`)
that resolves to A's `primary_root` proceeds. A pure context read from any checkout proceeds.

**Acceptance Scenarios**:

1. **Given** mission A whose declared execution workspace is lane A, **When** a mission-A WP-write
   (`implement`/`review`) is invoked from mission B's lane (same registry), **Then** it refuses — the
   comparison is `current_cwd` (symlink-canonicalized) vs A's own resolved `workspace_path`, not
   repo-membership (`resolve_ownership_claim` classifies same-repo foreign lanes as OWNED and is NOT
   authoritative here).
2. **Given** mission A's own owned lane worktree, **When** `implement`/`review` runs there, **Then** it
   proceeds (no false refusal).
3. **Given** a **planning** command (`specify`/`plan`/`tasks*`) run from any checkout that resolves to
   A's `primary_root`, **When** it runs, **Then** it proceeds (planning's declared workspace is the
   primary partition; the refusal keys on WP-execution write-intent, not action-name).
4. **Given** a pure context **read** (`resolve_feature_dir_for_mission`, or `resolve_action_context`
   used as a read vehicle) from any checkout, **When** it resolves, **Then** it is never refused.
5. **Given** the refusal fires, **When** it propagates, **Then** it raises a **distinct exception that
   is NOT a subclass of `ActionContextError`**, so the existing `except ActionContextError: return None`
   fallbacks (`implement_cores.py:635`, `mission_record_analysis.py:125`) and `suppress(Exception)`
   (`mission_record_analysis.py:347`) cannot silently degrade it to the legacy path.

---

### User Story 3 — Topology / checkout-identity primitives live in one place (Priority: P2, lands FIRST) — #3373

The git-common-dir/toplevel probe is re-implemented in four modules answering *semantically distinct*
questions: root-resolution with `@lru_cache` + `.resolve()` **already present** (`charter/resolution.py`,
a dashboard/sync/migration hot path, ~20 callers); is-worktree assertion (`workspace/context.py`);
linkage comparison (`commit_helpers.py`); ownership classification (`checkout_ownership.py`). The
`effective_root`-read fork recurs ~12× inside the coord/topology resolvers.

**Why this priority**: P2 tech-debt, but it is the **substrate Seam B stands on** — the identity
comparison is only sound if both sides are canonicalized *identically*, and an un-canonicalized symlink
(`/var`→`/private/var`) would false-refuse the mission's own worktree. **It lands first.**

**Independent Test**: the four probes unify behind one primitive with a single canonicalization
contract; the existing suite (charter caching, not-a-repo classification, NESTED refusal) stays green.

**Acceptance Scenarios**:

1. **Given** the four probes, **When** consolidated, **Then** one primitive answers the common
   git-topology question (caching + not-a-repo classification + `.git`-interior detection + a **single**
   symlink-canonicalization contract); each of the four call sites consumes it without behavior change.
   (Note: the `charter/resolution.py` copy already `.resolve()`s — the deliverable *unifies* the
   canonicalization contract, it does not add it where it already exists.)
2. **Given** the `effective_root is None ? legacy : compose_meta_json_path(...)` fork, **When**
   consolidated, **Then** one `read_dir_for(...)` helper is consumed by every coord/topology resolver
   (a static gate asserts zero other copies).
3. **Given** the nested/toplevel-mismatch classifier, **When** consolidated, **Then** one authority
   feeds both the fast `is_worktree_of` gate and the comparator classification, preserving the NESTED
   refusal (existing-behavior test).

---

### Edge Cases

- **Read vehicle reuse (R1)**: `resolve_action_context(action="tasks")` is used purely to read a dir
  (`_read_path_resolver.py:1622`, ~20 callers) — Seam B must NOT refuse these; it keys on WP-write
  intent, not action-name.
- **Planning from a lane checkout (R3)**: `/spec-kitty.tasks` run from inside a lane that resolves to
  the mission's `primary_root` must proceed (planning writes are PRIMARY-partition; compare against
  `primary_root`, not `current_cwd`).
- **Moving-tip**: a coord mission whose `target_branch` advances between finalize and implement — lane
  allocation still succeeds (`planning_commit_sha` frozen; no live re-derivation).
- **Legacy mission** (no `coordination_branch`): the partition-aware commit no-ops to `target_branch`
  exactly as today (no change for SINGLE_BRANCH / LANES).
- **Empty partition group (R4)**: `commit_idempotent` does **not** no-op on an empty staged set (it
  raises `BookkeepingCommitFailed`); the empty group MUST be **skipped**, never committed.
- **`meta.json` co-travel (R6)**: `meta.json` is PRIMARY by kind yet legitimately accompanies coord
  writes; it is exempt from the Seam-A refusal, from the PRIMARY→primary split, and from the SC-002
  scan count — via one named self-bookkeeping predicate applied before kind classification.
- **Crash between the two partition commits (R5)**: recovered by idempotent re-drive on re-invocation;
  a regression pin covers it.
- **Symlinked components** (`/var`→`/private/var`): must not false-refuse an owned worktree — #3373
  lands first.

## Requirements *(mandatory)*

### Mutating vs read-only classification (MF-3)

Seam B's refusal applies **only** to WP-execution *write* intent. The plan MUST introduce an explicit
signal (e.g. a `_MUTATING_WP_WRITE` marker threaded from the true `implement`/`review` write call sites,
or an equivalent write-intent flag) rather than keying on `ActionName`, because action names are reused
by read vehicles (R1). `doctor`/`status` never reach the factory and are out of the classification
entirely (exempt *by bypass*, not by classification). The plan MUST enumerate, in a table, which
`implement`/`review` write paths carry the marker.

### Functional Requirements

> **Withdrawn:** the two upgrade-wedge requirements (`upgrade` eligibility-probe degrade; `doctor
> frontmatter-integrity`) are **removed** — #3372 shipped by mission #3383. The numeric IDs 006/007 are
> left as a gap (not reused) to keep the 008..011 identifiers stable against the earlier drafts and the
> WP references.

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Partition-aware planning-artifact auto-commit (retire the verbatim arm; skip empty groups; idempotent re-drive) | US1 | High | Open |
| FR-002 | Seam-A partition guard at `_run_planning_artifact_commit`, using one named self-bookkeeping exclusion | US1 | High | Open |
| FR-003 | Route `move-task --force` (#2549) through Seam A | US1 | High | Open |
| FR-004 | Coord + PR-bound lane allocation succeeds end-to-end (regression pin) | US1 | High | Open |
| FR-005 | Seam-B write-intent checkout-identity refusal for `implement`/`review` | US2 | High | Open |
| FR-008 | One git-topology primitive (unify four distinct probes, single canonicalization contract) | US3 | High | Open |
| FR-009 | Centralized `read_dir_for(...)` effective-root helper | US3 | Medium | Open |
| FR-010 | Single nested/toplevel-mismatch classifier authority | US3 | Medium | Open |
| FR-011 | Arch gate (static call-shape) + runtime cross-partition scan reassigned to SC-002 | US1 | Medium | Open |

**FR detail (key corrections):**

- **FR-001** — Replace `implement.py`'s verbatim `placement_ref` arm with `_partition_files_for_commit`
  + **per-partition** `BookkeepingTransaction` commits. Order of operations: classify → apply the named
  self-bookkeeping exclusion → **test each group for emptiness → commit-or-skip** (never construct an
  empty transaction; `commit_idempotent` raises on an empty staged set). Each partition commit is
  idempotent so a crash between them is recovered by re-invoking `implement` (no-op resume). Reverses
  the pinned C-004/D11 verbatim contract (test rewritten to assert the split) — sanctioned by this
  mission.
- **FR-002** — The Seam-A guard bites at `_run_planning_artifact_commit`, classifying staged paths by
  kind, and excludes self-bookkeeping churn via **one named predicate** (`is_self_bookkeeping_churn`,
  `coherence.py:50`), applied **before** kind classification, so a legitimate coord commit co-traveling
  `meta.json` does not false-refuse.
- **FR-003** — Route `move-task --force` (#2549) through Seam A so `status.*` lands on the coord ref.
  Respect the withdrawn Trigger A: status→coord *under coord topology* is correct by design and MUST NOT
  be "fixed." Cite a current-code reproduction of the residual lane-status leak in the plan.
- **FR-005** — At the true `implement`/`review` WP-write call sites (write-intent, not action-name),
  refuse when symlink-canonicalized `current_cwd` is not the mission's declared **execution** workspace
  (`MissionExecutionContext.workspace_path` — **not** `execution_workspace`, which is dead `=None` at
  `resolution.py:1339`). MUST NOT refuse: pure reads (R1), planning writes resolving to the mission's
  `primary_root` from any checkout (R3), or the mission's own owned worktrees. Refusal raises a
  **distinct exception NOT subclassing `ActionContextError`**; WP04 audits/narrows the swallow sites
  (`implement_cores.py:635`, `mission_record_analysis.py:125`, `suppress(Exception)` at `:347`).
  `resolve_ownership_claim` is a non-authoritative fast-path only (it classifies same-repo foreign lanes
  as OWNED, MF-8).
- **FR-011** — A `tests/architectural/` gate asserts ONLY the **static call-shape** (no coord-topology
  `_run_planning_artifact_commit` receives a `files_to_commit` not first passed through
  `_partition_files_for_commit`), with an explicit route-through/carve-out for the legitimate **flat/legacy
  arm** (`implement.py:909`, which commits verbatim by design — no coord partition exists on a flat
  mission). The **runtime** "no `lanes.json` on any coord ref" property is NOT statically detectable and
  is assigned to the SC-002 real-git repo scan, not this gate.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Cross-partition purity | Zero PRIMARY files on any coord branch **and** zero COORD files on any lane branch across a full lifecycle (repo scan; `meta.json` excluded from the count) | Reliability | High | Open |
| NFR-003 | No new arch regressions | **No new** `tests/architectural/` gate regressions vs merge-base (some gates are honestly-red on main per repo policy — not "all green"); ADR `2026-07-29-1`/`2026-06-24-1/2`/`2026-06-22-1` invariants preserved; #1878 non-goal upheld | Compatibility | High | Open |
| NFR-004 | Refusal overhead | Seam-B refusal is a pure path comparison against already-computed metadata; patching the git primitive shows the refusal path invokes it **zero** additional times | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Two mandatory seams | Partition purity is enforced at the write seam (`_run_planning_artifact_commit`/`commit_router`); checkout-identity at the WP-execution write. NOT a single factory door, and NOT scattered per-command re-checks beyond these two seams | Technical | High | Open |
| C-002 | Preserve coord parentage | Keep the coordination-worktree mechanism (C-004) and lane coord-descent (Assert A'); do NOT re-parent lanes off `target_branch` or change the create-time coord base | Technical | High | Open |
| C-003 | No topology redesign | No shadow-workspace / topology-model change (#1878 non-goal); complete the strangler #1878 defines | Technical | High | Open |
| C-004 | Sanctioned C-004/D11 reversal | Reversing the pinned `placement_ref`-verbatim deferral (FR-001) is sanctioned because it advances #2160; the pinned test is rewritten, not silently deleted | Technical | High | Open |
| C-005 | Read-from-stored, no live re-derivation | Topology read from stored `meta.json`; `planning_commit_sha` never re-derived live; `meta.json`/`target_branch` read from the repository-root checkout | Technical | High | Open |
| C-006 | Empty-group + per-partition atomicity | Split commits skip empty groups (never an empty transaction); atomicity is per-partition; a crash between commits recovers by idempotent re-drive | Technical | High | Open |
| C-007 | Write-intent, not action-name | Seam B keys on explicit WP-write intent, never on `ActionName` (read vehicles reuse names, R1); planning proceeds from any checkout resolving to the same `primary_root` (R3) | Technical | High | Open |
| C-008 | Self-bookkeeping exemption predicate | One named predicate (`is_self_bookkeeping_churn`, `coherence.py:82`) governs the Seam-A guard's `meta.json` exemption **and** the SC-002 scan count. The FR-001 split routes by residue-kind (`is_coord_residue_churn`), under which `meta.json` already resolves PRIMARY through kind classification — the split needs no separate self-bookkeeping call | Technical | Medium | Open |
| C-009 | Project quality bars | Terminology canon (Mission not feature*); new code passes ruff + mypy zero-issue; every new branch/helper covered by focused tests same PR | Technical | Medium | Open |

### Non-Goals (explicit)

- **Frontmatter / upgrade axis (#3372) — OUT of scope.** Fixed and closed by mission **#3383** (WP03/
  WP04/WP09: read-boundary duplicate-key guard, dup-key detect/repair, wedged-project self-recovery)
  during this mission's authoring. No frontmatter reader, doctor-repair, or merge-driver work here.
- **No checkout-identity retrofit** for `move-task`/`record-analysis`/`migrate`/`doctor --fix`/`merge`
  (they bypass the factory) — Seam B is `implement`/`review` only; the partition mis-route class for
  those commands is covered by Seam A. Full retrofit is a named follow-on.
- **No read-side lookup rewrite** — the read/lookup halves of #3124/#3051/#3049/#2613 are *de-risked
  not closed* (their write halves are covered; reads serve from anywhere by design). Full closure needs
  #2624; out of scope.
- **Candidates #3131/#3133** stay candidates.

### #2549/#2570 scope confirmations (pre-plan)

- **#2549** — in scope (Seam A). Cite a current-code reproduction of the residual lane-status leak in
  the plan.
- **#2570** (allocator serialized behind its own uncommitted frontmatter write) — **WP02 performs an
  impact analysis** of FR-001's commit-split on the allocator self-write timing; **fold only if the fix
  is mechanism-compatible and low-complexity**, else spin a documented follow-on (operator preference:
  fold if cheap, not at significant complexity cost).
- **#2702 / #3372** — CONFIRMED CLOSED during authoring (see Scope note at top). #2702 ticket closed
  with evidence; #3372 shipped by #3383. **No in-mission work on either.**

### Key Entities

- **`MissionExecutionContext` + `build_execution_context()`** (`resolution.py:217`) — the sole
  construction door; carries `workspace` (`primary_root`/`current_cwd`/`allowed_command_cwd`/
  `workspace_path`) and a ref-only `placement_ref`.
- **Declared workspace** — *planning/mission-level* actions: the primary checkout
  (`WorkspaceFragment.allowed_command_cwd == primary_root`); *WP-bearing* actions: the resolved lane
  path `MissionExecutionContext.workspace_path` (**not** `execution_workspace`, dead `=None`).
- **Seam A (partition)** — `_run_planning_artifact_commit` / `commit_router._group_files_by_partition`
  / `placement_seam.write_target` + `PrimaryKindReachedCoordStagingError`.
- **Self-bookkeeping predicate** — `is_self_bookkeeping_churn` (`coherence.py:50`), the single authority
  for `meta.json` exemption.
- **Git-topology primitive** — the #3373 unified probe.

## Success Criteria *(mandatory)*

- **SC-001**: A coord-topology + PR-bound `--start-branch` mission completes specify → `implement WP01`
  with **zero** manual coord←primary reconciles — asserted by `allocate_lane(...)` returning without
  `PlanningCommitMergeConflictError` and a clean `git status --porcelain` (automated regression).
- **SC-002**: Automated scan finds **zero** cross-partition artifacts (no PRIMARY file on any coord
  branch, no COORD file on any lane branch; `meta.json` excluded) across a lifecycle covering
  `implement` and `move-task --force`.
- **SC-004**: `implement`/`review` invoked from a foreign checkout (incl. another mission's lane in the
  same registry) refuse (exit ≠ 0, actionable) in **100%** of attempts; the mission's own worktrees,
  planning-from-any-primary-resolving-checkout, and all pure reads are **never** falsely refused
  (local-fixture test; no `spec-kitty-saas` dependency).
- **SC-005**: The git-topology probe is unified behind one primitive (four call sites consume it); the
  full existing suite stays green.
- **SC-006**: A static arch gate forbids an un-partitioned coord-topology `_run_planning_artifact_commit`
  batch (flat/legacy arm carved out); the "no `lanes.json` on a coord ref" runtime property is proven by
  the SC-002 real-git scan (the P0's Axis-B cannot silently regress via either).
- **SC-007**: The `effective_root ? legacy : compose_meta_json_path` fork exists in exactly one
  `read_dir_for` helper (gate asserts zero others).
- **SC-008**: One nested/toplevel classifier feeds both `is_worktree_of` and the comparator; the NESTED
  refusal holds.

## Traceability

- **Issues**: #3371 (P0), #2549, #3128, #3373 (P2). #2702 & #3372 **confirmed closed during authoring**
  (out of scope — #3372 shipped by #3383; #2702 ticket closed). Contributes to epic **#2160**; completes
  strangler **#1878**. Class umbrella #3129. Conditional: #2570.
- **De-risked, not closed** (left under #2624/#1878): #3124, #3051, #3049, #2613 (read-side halves).
- **ADRs**: `2026-07-29-1`, `2026-06-24-1`, `2026-06-24-2`, `2026-06-22-1`, `2026-06-03-2`.
- **Investigation**: `docs/plans/investigations/write-path-topology-root-cause.md` (Option A / #3128).
- **Reproduction**: coord branch `kitty/mission-mission-a-p0-consistency-01KZWHY1`, commit `c3d92a364`.
- **Canonical seams**: `mission_runtime/resolution.py` (`build_execution_context`),
  `implement.py::_commit_planning_artifacts_transaction`/`_partition_files_for_commit`/
  `_run_planning_artifact_commit`, `coordination/commit_router.py` (`_group_files_by_partition`,
  `PrimaryKindReachedCoordStagingError`), `coordination/coherence.py` (`is_self_bookkeeping_churn`),
  `coordination/transaction.py` (`commit_idempotent`), `lanes/worktree_allocator.py`,
  `git/commit_helpers.py` / `workspace/context.py` / `charter/resolution.py` / `checkout_ownership.py`.

## Proposed WP decomposition (for planning)

- **WP01 — Unify the git-topology primitive (#3373).** Four distinct probes → one primitive + one
  `read_dir_for` helper + one nested classifier. *Depends on: none. Substrate for WP04.*
- **WP02 — Partition-correct the P0 auto-commit (#3371) + #2570 impact analysis.** `_partition_files_for_commit`
  + per-partition idempotent commits, skip-empty, reverse the verbatim arm. Impact-analyze #2570; fold
  if cheap. *Depends on: WP01.*
- **WP03 — Seam-A guard + #2549.** Guard at `_run_planning_artifact_commit` with the self-bookkeeping
  exclusion; route `move-task --force`. *Depends on: WP01, WP02.*
- **WP04 — Seam-B checkout-identity for `implement`/`review` (#3128).** Write-intent refusal vs
  `workspace_path`; distinct exception; narrow the swallow sites. *Depends on: WP01.*
- **WP05 — Arch gates (FR-011).** Static call-shape + negative `lanes.json`-on-coord. *Depends on:
  WP02, WP03.*
