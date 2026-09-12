# Mission Specification: Runtime Advance Guard — Uninitialized-WP Completion

**Mission Branch**: `fix/runtime-advance-guard-3883`
**Created**: 2026-09-06
**Status**: Draft
**Input**: User description: "Fix the advance guard so a coord-topology mission's `gather_artifact_presence` reads named artifacts off the primary partition instead of the coord worktree (#3883), and close the `implement`-gate hole that lets a never-claimed work package (lane `uninitialized`) advance past `implement` unblocked (#3884)."

## Scope Narrowing (operator ruling, 2026-09-07) — read before the rest of this document

This mission originally targeted **both** issues named in the Input line above
(#3883 and #3884) as User Story 1 and User Story 2 respectively, and its spec/plan/
tasks artifacts were adversarially reviewed across four-to-six rounds each on that
two-issue premise (see `reviews/*.yaml`, `reviews/plan.ruling.md`).

**The operator has ruled this mission down to #3884 only.** Verified, not assumed:
draft PR **#3923** (`codex/upgrade-preview-mission-health`) is already fixing #3883
in `src/runtime/next/runtime_bridge_io.py`, using a kind-aware placement seam
(`_artifact_presence_read_dir` via `kind_for_mission_file` + `placement_seam`) that
anchors named-artifact reads while keeping lifecycle/status reads on `feature_dir` —
the same shape this mission's own (now-deleted) User Story 1 design proposed, via a
different, independently-invented mechanism (`resolve_primary_anchor_dir` /
`PrimaryPlacementResolutionError`). Confirmed by the paginated GitHub API (a plain
`gh pr view --json files` truncates at 100 and hides this): PR #3923 has **125**
files, touches `runtime_bridge_io.py`, and its diff mentions `gather_artifact_presence`
9 times. Equally confirmed: **PR #3923 does NOT touch
`src/runtime/next/runtime_bridge.py`**, and its diff contains **zero** mentions of
`_wp_blocks_step`, `_should_advance_wp_step`, or `UninitializedState`. A handover
comment recording this has already been posted on #3883.

**What this means for this document:**

- **Removed entirely**: former User Story 1 (the `gather_artifact_presence`
  topology-anchoring fix), FR-001, FR-002, FR-003, FR-006, FR-007, FR-008, NFR-002,
  C-001 through C-005, and every Success Criterion/Edge Case that existed only to
  serve those — all of it is `runtime_bridge_io.py` territory now owned by PR #3923.
  This is a scope *reduction* of already-reviewed artifacts, not a re-derivation:
  nothing about #3883's design was found wrong: it is redundant with independent,
  further-progressed work.
- **Survives, unchanged in substance**: FR-004 and FR-005 (the `_wp_blocks_step`
  `Lane.UNINITIALIZED` fix at the heart of #3884).
- **Survives, promoted from an implicit plan-level completion to an explicit
  requirement here**: the reachability-anchoring subtlety plan.md's fourth review
  round (PLAN-FIT-001) discovered — `_should_advance_wp_step` (the function that
  must reach `_wp_blocks_step`'s per-WP loop in the first place) does its own
  *separate*, unanchored `tasks_dir` read in `runtime_bridge.py`, independent of
  `gather_artifact_presence`'s own (now out-of-scope) read in `runtime_bridge_io.py`.
  Without anchoring this second read too, FR-004's fix is structurally unreachable
  for a real coord-topology mission — the exact production shape #3884 was filed
  against. This survives as **new FR-009/FR-010** below, because `runtime_bridge.py`
  is not a file PR #3923 touches: fixing it is still this mission's job, not a
  duplicate of #3923's work.

Record of what was checked and not carried forward for nothing: this narrowing
removes requirements because an equivalent, more-progressed fix already exists
upstream for that half of the original ask — not because the original design was
found incorrect. See `plan.md`'s own new "Narrowing" section for the full
before/after diff of the technical design.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A never-claimed work package blocks `implement` advancement (Priority: P1)

As a mission-runtime maintainer, when a work package file exists under
`tasks/` but was never claimed (its folded lane stays `Lane.UNINITIALIZED`
forever, per `committed_authority.wp_ending` / `_fold_wp_state`,
`src/runtime/next/committed_authority.py:102-133`), I want
`_wp_blocks_step("implement", state, has_provenance)`
(`src/runtime/next/runtime_bridge.py:781-810`) to report that this WP
blocks advancement, so that `_should_advance_wp_step` cannot let a mission
skip past `implement` while a scaffolded-but-untouched WP sits there — and I
want that reachable for a real COORD-topology mission, not merely provable
against a synthetic fixture where `feature_dir` happens to already contain
`tasks/` directly.

**Why this priority**: this is the actively-reproducing defect (#3884).

**The reachability subtlety (FR-009/FR-010) — why this story is not "just" the
`_wp_blocks_step` branch fix.** `_should_advance_wp_step(step_id, feature_dir)`
(`runtime_bridge.py:738-780`) does its own, separate, unanchored PRIMARY-partition
read — `tasks_dir = feature_dir / "tasks"` (`:753`) — *before* it ever reaches the
per-WP loop that calls `_wp_blocks_step`. `tasks/WP*.md` is a PRIMARY-partition
artifact (`MissionArtifactKind.WORK_PACKAGE_TASK`, a member of
`_PRIMARY_ARTIFACT_KINDS`, `src/mission_runtime/artifacts.py:69,147-155,261`) — it
is minted on the mission's PRIMARY checkout by `specify`/`plan`/`tasks`, and for a
COORD-topology mission the coordination branch is cut before any of that runs
(`src/specify_cli/missions/_create.py:195-259`), so the coordination worktree never
receives it. When `_should_advance_wp_step` is called with a coord-worktree
`feature_dir` (as it genuinely is for a real coord-topology mission's `implement`/
`review` step advance), `tasks_dir.is_dir()` is `False` there even though
`tasks/WP*.md` genuinely exist on primary — the function hits its own early return
(`:754-755`, `if not tasks_dir.is_dir(): return True`) and returns `True`
(permits advancement) *unconditionally*, before the per-WP loop — the only place
FR-004's `Lane.UNINITIALIZED` disjunct can fire — is ever reached. FR-004's fix is
therefore verified-correct only at the unit level (`_wp_blocks_step` called
directly) and for topologies where `feature_dir` already contains `tasks/` directly
(SINGLE_BRANCH, LANES, or a lane worktree carrying the FR-009/#2993
recorded-planning-commit backfill, `src/specify_cli/lanes/worktree_allocator.py:576-649`)
— it remains structurally unreachable for the actual COORD-topology production
scenario #3884 was filed against, unless `_should_advance_wp_step` anchors this
second, independent read too.

**Independent Test — three calls, not one**:

1. Direct: `_wp_blocks_step("implement", UninitializedState(), has_provenance=False)`
   returns `True` (blocks) — before the fix it returns `False`.
2. End-to-end, non-coord: `_should_advance_wp_step("implement", feature_dir)`
   against a fixture whose `feature_dir` directly contains `tasks/` (a WP with zero
   lane-transition events) returns `False` for the mission as a whole — before the
   fix it returns `True`. This alone is FR-004/FR-005's scope and needs no
   anchoring, no `placement_seam`, no coord-topology fixture.
3. End-to-end, coord-topology (FR-009): the SAME never-claimed-WP fixture, but with
   `tasks/WP*.md` on a separate primary checkout and `feature_dir` pointing at a
   coordination worktree holding only `status.events.jsonl` (mirroring the
   coord-topology fixture description this mission's own former User Story 1 used,
   now repurposed for this reproduction instead). Before FR-009's fix,
   `_should_advance_wp_step("implement", coord_feature_dir, repo_root=<repo_root>,
   mission_slug=<slug>)` (the extended, opted-in signature) returns `True` — wrong —
   because the unanchored `tasks_dir` read still resolves against the coord
   worktree regardless of whether FR-004's disjunct exists. After FR-009's fix it
   returns `False` — proving FR-004's fix genuinely fires for the production
   scenario, not just at the unit level.

**Acceptance Scenarios**:

1. **Given** a WP file exists under `tasks/` with zero lane-transition events
   (never claimed), **When** `_wp_blocks_step("implement", state,
   has_provenance=False)` is evaluated for that WP's folded
   `UninitializedState`, **Then** it returns `True` (blocks), not `False`.
2. **Given** the same WP, on a fixture whose `feature_dir` directly contains
   `tasks/`, **When** `_should_advance_wp_step("implement", feature_dir)` runs
   across all WPs in the mission, **Then** it returns `False` for the mission as a
   whole (the never-claimed WP prevents advancement), matching what
   `WpEnding.acceptable == False` for that WP already signals at the
   `committed_authority` layer today.
3. **Given** a mission type with genuinely no `tasks/` directory (e.g. the
   `plan` mission family, which produces plans without work packages — see
   `docs/architecture/mission-system.md`'s mission-selection table), **When**
   `_should_advance_wp_step` runs — with or without FR-009's anchoring opted in —
   **Then** the existing early return (`if not tasks_dir.is_dir(): return True`,
   `runtime_bridge.py:754-755`) is left untouched and still returns `True` — this
   is the legitimate no-op case, not the defect being fixed, and FR-009's
   anchoring must not change this outcome (see Edge Cases).
4. **Given** the pre-existing `except ValueError` branch in
   `_should_advance_wp_step` (`runtime_bridge.py:768-773` — corrected from an
   earlier draft's `:763-767` citation, per plan.md's own "Flagged Deviations"
   finding; the branch's behavior was always described correctly, only its line
   pointer drifted, "Unknown lane … treat as not-yet-handed-off"), **When** the
   folded lane is `"uninitialized"`, **Then** this branch is confirmed NOT to
   fire — `"uninitialized"` is a registered key in `wp_state.py`'s `_STATE_MAP`
   (`wp_state_for` returns `UninitializedState()` without raising) — so the
   fix must not rely on that branch as an accidental safety net; the defect
   lives entirely inside `_wp_blocks_step`'s implement-branch fall-through.
5. **Given** the same never-claimed-WP fixture, but with `tasks/WP*.md` on a
   primary checkout and `feature_dir` pointing at a separate coordination
   worktree holding only `status.events.jsonl` (FR-009), **When**
   `_should_advance_wp_step("implement", coord_feature_dir, repo_root=<repo_root>,
   mission_slug=<slug>)` is called with the anchoring parameters supplied,
   **Then** it resolves `tasks_dir` against the primary checkout (not the coord
   worktree) and returns `False` — matching Acceptance Scenario 2's verdict for
   the non-coord fixture, now also reachable for the coord-topology shape.
6. **Given** the anchoring resolution genuinely cannot determine a unique primary
   mission directory for the supplied `mission_slug` (an ambiguous handle —
   `MissionSelectorAmbiguous`, propagated from handle canonicalization; verified
   live as the one exception `mission_runtime.placement_seam(...).read_dir(
   MissionArtifactKind.WORK_PACKAGE_TASK)` can actually raise for this kind — see
   FR-010), **When** `_should_advance_wp_step` is called through its one real
   production call site (`_dn_dependency_gate`'s WP-iteration branch,
   `runtime_bridge.py:1680`), **Then** the raise is caught there and converted into
   a `DecisionKind.blocked` Decision, never left to propagate as an uncaught
   exception out of `decide_next_via_runtime`.

### Edge Cases

- What happens for a `flattened`/`single_branch`-topology mission (like this
  mission's own scaffold) where `feature_dir` already IS the primary checkout?
  FR-009's anchoring must be a no-op there — `mission_runtime.placement_seam(...)
  .read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)` resolves a PRIMARY-partition
  kind to the primary mission directory "for EVERY topology and coord state"
  (`PlacementSeam.read_dir`'s own documented contract) — so anchoring cannot change
  behavior when `feature_dir` and the primary dir already coincide, by
  construction, not via a special-cased branch. This mission's own checkout is a
  live regression fixture for that no-op property.
- What happens when a WP has SOME events (e.g. was claimed and then the
  event log was truncated/corrupted) versus truly zero events? This mission
  only targets the zero-events, folds-to-`UNINITIALIZED` case; a corrupted
  log is a distinct failure mode already covered by
  `CanonicalStatusNotFoundError` handling and is out of scope here.
- **Rollout impact on real in-flight missions**: before this fix,
  `_should_advance_wp_step` was never anchored with `repo_root` on a
  coord-topology mission, so its `tasks/` lookup against the coordination
  worktree always failed and the function returned `True` unconditionally on
  `implement` — skipping the per-WP loop entirely, regardless of whether any
  WP was in-progress, blocked, or rejected, not only never-claimed. Once this
  fix ships, ANY coord-topology mission currently in `implement` with a WP
  that is not in an acceptable/handed-off state will newly (and correctly)
  block on its next `next`/advance call — a WP that was never claimed
  (the originally-reported #3884 case), but equally one that is merely
  `in_progress`, `blocked`, or rejected without operator provenance. This is
  the intended, correct verdict, but it is a real operational discontinuity
  for whoever is driving such a mission, not merely an internal test-suite
  delta. Recommend a spot-check of EVERY currently-in-`implement`
  coord-topology mission (not only ones already suspected to have a
  never-claimed WP) immediately after this mission ships, so an operator is
  not surprised by a mission newly blocking on its next `next` call with no
  user-visible change of their own.
- What does FR-009's anchoring do for the genuinely-ambiguous-`mission_slug`
  failure mode? It must raise (verified live: `MissionSelectorAmbiguous` is the
  one exception `placement_seam(...).read_dir(WORK_PACKAGE_TASK)` can raise for
  this PRIMARY-partition kind — a corrupt/missing `meta.json` does **not** raise
  here, since resolving a PRIMARY-partition kind's directory is pure path
  composition off the canonicalized `mission_slug`, not a `meta.json` content
  read; verified empirically against this checkout, not assumed), and FR-010
  requires it be caught at the one real call site into a structured `blocked`
  Decision — never a silent fallback and never an uncaught crash.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-004 | `_wp_blocks_step` blocks `implement` for an uninitialized WP | As a mission-runtime maintainer, I want `_wp_blocks_step("implement", state, has_provenance)` to return `True` (blocks) when `state.lane == Lane.UNINITIALIZED` and the WP has never been claimed, so that a scaffolded-but-untouched work package can no longer be silently treated as "fine to advance past `implement`". | High | Open |
| FR-005 | Preserve existing legitimate no-`tasks/`-dir and canceled/approved/done behavior | As a mission-runtime maintainer, I want the FR-004 fix scoped so that the existing early return for mission types with no `tasks/` directory (`runtime_bridge.py:754-755`) and the existing acceptable-ending handling for `approved`/`done`/operator-`canceled` (via `is_acceptable_ending`) are unaffected, so that only the genuinely-buggy uninitialized-and-never-claimed case changes behavior. | High | Open |
| FR-009 | Anchor `_should_advance_wp_step`'s own `tasks/` read so FR-004's fix is reachable on a coord-topology mission | As a mission-runtime maintainer, I want `_should_advance_wp_step(step_id, feature_dir)` to optionally resolve the `tasks_dir` it reads against the mission's PRIMARY-partition placement directory (`mission_runtime.placement_seam(repo_root, mission_slug).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)`, mirroring the pattern already live at `runtime_bridge.py:265-275`/`:1529-1537` for `MissionArtifactKind.PRIMARY_METADATA`) instead of the raw `feature_dir` parameter, when a caller opts in by supplying `repo_root`/`mission_slug`, so that a coord-topology mission's coordination-worktree `feature_dir` — which never receives `tasks/WP*.md`, per this story's reachability subtlety — does not cause the function's own no-`tasks/`-dir early return to fire and skip the per-WP loop that is the only place FR-004's fix can run. Gated on `repo_root is not None` (not a separate flag), mirroring the #3704 precedent already established elsewhere in this call graph: a true no-op for every existing 2-arg test call site, and a true no-op for a `flattened`/`single_branch` mission where `feature_dir` already IS primary (see Edge Cases). This lives entirely in `runtime_bridge.py` — it does not touch `gather_artifact_presence`/`runtime_bridge_io.py`, which is PR #3923's surface, not this mission's. | High | Open |
| FR-010 | Fail loud on an unresolvable `mission_slug`, and catch it at the one real call site | As a mission-runtime maintainer, I want FR-009's anchoring to raise (never silently degrade) when `mission_slug` cannot be resolved to a unique primary mission directory — verified live, the sole such failure `mission_runtime.placement_seam(...).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)` can raise is `MissionSelectorAmbiguous` (`src/specify_cli/missions/_read_path_resolver.py:44`), propagated from handle canonicalization; a corrupt/missing `meta.json` does not raise here, since a PRIMARY-partition kind's directory resolves via pure path composition, not a `meta.json` content read — and I want that raise caught at `_should_advance_wp_step`'s one genuinely load-bearing production call site (`_dn_dependency_gate`'s WP-iteration branch, `runtime_bridge.py:1680`) and converted into a structured `blocked` Decision, mirroring the existing sibling `except CanonicalStatusNotFoundError as exc:` arm at that exact call site (`:1681-1697`), so that an ambiguous handle degrades to a reportable `blocked` verdict rather than an uncaught crash out of `decide_next_via_runtime`. No new exception class is introduced — `MissionSelectorAmbiguous` already exists and is already the typed signal this codebase uses for exactly this failure class elsewhere (`src/mission_runtime/resolution.py`). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression in the existing fast/unit baseline | `tests/runtime tests/next tests/specify_cli/next tests/specify_cli/status` (fast/unit) continues to report 1666 passed, 1 skipped, 325 deselected (the pre-mission baseline, already verified clean); `tests/runtime/next tests/next` full continues to report 598 passed; **the exact invocation `pytest tests/runtime --ignore=tests/runtime/next` continues to report 672 passed, 1 skipped** (verified: this invocation collects 673 tests; the naive `pytest tests/runtime -q`, WITHOUT the `--ignore`, collects 746 tests / 745 passed, 1 skipped instead — a different, larger number that reads as a false regression to an implementer who runs the bare command) — no new reds introduced in this blast radius. | Reliability | High | Open |
| NFR-003 | Shared test-venv lock contention is an environmental risk, not a defect | Test runs against the shared test-venv lock (#3283) may time out under contention; such a timeout must be classified as environmental (re-run / classify per the baseline-red gotcha) and not folded into this mission's own pass/fail accounting. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-006 | No edits to installed artifact trees | This mission edits only source under this repository checkout. It must not propose or make edits under `~/.local/`, `~/.hermes/`, or `~/.claude/` (installed/deployed copies, not source). | Technical | High | Open |
| C-007 | Terminology canon | Authored prose in this spec and its downstream plan/tasks/implementation uses "Mission", never "Feature" — `feature_dir`/`feature-dir` remain as pre-existing code identifiers and are not renamed by this mission. | Business | Medium | Open |
| C-008 | ATDD / red-first discipline deferred to plan+implement | This spec phase does not write tests; the plan phase must design, and the implement phase must execute, a red-first reproduction for: (a) `_wp_blocks_step`'s `Lane.UNINITIALIZED` disjunct (FR-004), against a never-claimed WP, using the function's plain signature — no directory I/O; (b) `_should_advance_wp_step`'s end-to-end behavior for a non-coord fixture (FR-004/005, Acceptance Scenario 2); (c) the coord-topology end-to-end reproduction proving FR-009's anchoring is what makes FR-004's fix reachable (Acceptance Scenario 3/5) — red until BOTH FR-004's disjunct AND FR-009's anchoring extension are in place, since FR-004's disjunct alone is necessary but not sufficient; and (d) FR-010's raise-and-catch contract at its one real call site (a fixture that makes `mission_slug` resolve ambiguously) — per DIRECTIVE_034/DIRECTIVE_041. | Technical | High | Open |
| C-009 | Scope boundary with PR #3923 — record, do not silently re-derive | `gather_artifact_presence`/`runtime_bridge_io.py`'s own primary-partition anchoring (the former User Story 1 of this mission, #3883) is explicitly out of scope: PR #3923 (`codex/upgrade-preview-mission-health`, draft, base `main`) already implements it via a kind-aware placement seam, verified to touch 125 files including `runtime_bridge_io.py` and to mention `gather_artifact_presence` 9 times in its diff. This mission must not re-implement that fix under a different name, and any future rediscovery of an #3883-shaped gap must be checked against PR #3923's status first, not treated as a fresh requirement here. | Technical | High | Open |

### Key Entities *(include if feature involves data)*

- **`MissionArtifactKind`** (`src/mission_runtime/artifacts.py`): the enum partitioning mission artifacts into `_PRIMARY_ARTIFACT_KINDS` (primary-partition — includes `WORK_PACKAGE_TASK`, the kind FR-009's anchoring resolves) versus coord-partition kinds (`_PLACEMENT_ARTIFACT_KINDS`, e.g. `STATUS_STATE`).
- **`WpEnding`** (`src/runtime/next/committed_authority.py`): the folded `(lane, acceptable, reason_source)` result for one WP, used by both `_should_advance_wp_step`/`_wp_blocks_step` (the buggy consumer, FR-004) and the already-correct `acceptable` computation inside `_fold_wp_state`.
- **`Lane.UNINITIALIZED` / `UninitializedState`** (`src/specify_cli/status/wp_state.py`): the read sentinel for a WP with zero lane-transition events — a real, registered lane (`_STATE_MAP["uninitialized"]`), not an error case that `wp_state_for` rejects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-003**: A direct call to `_should_advance_wp_step("implement", feature_dir)` against a WP with zero lane-transition events (never claimed), on a fixture whose `feature_dir` directly contains `tasks/`, returns `False`, where it returned `True` before the fix.
- **SC-005**: The full baseline test counts in NFR-001 hold after the fix (1666 passed / 1 skipped / 325 deselected on the fast/unit tier; 598 passed on `tests/runtime/next tests/next`; 672 passed / 1 skipped on the exact `pytest tests/runtime --ignore=tests/runtime/next` invocation) — zero new reds attributable to this mission's diff.
- **SC-007**: The SAME never-claimed-WP fixture, reshaped as a coord-topology fixture (`tasks/WP*.md` on a separate primary checkout, `feature_dir` a coordination worktree holding only `status.events.jsonl`), makes `_should_advance_wp_step("implement", coord_feature_dir, repo_root=<repo_root>, mission_slug=<slug>)` return `False` — proving FR-004's fix genuinely fires for the coord-topology production scenario, not only the unit level or the non-coord fixture SC-003 covers.
- **SC-008**: A fixture where `mission_slug` resolves ambiguously (`MissionSelectorAmbiguous`) makes `_dn_dependency_gate`'s WP-iteration branch return a `DecisionKind.blocked` Decision carrying the exception's message, never an uncaught exception out of `decide_next_via_runtime`.
