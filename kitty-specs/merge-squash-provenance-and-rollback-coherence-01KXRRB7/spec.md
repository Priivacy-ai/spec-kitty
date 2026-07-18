# Mission Specification: Merge squash provenance + rollback/resume coherence (P0 #2709/#2711)

**Mission Branch**: `kitty/mission-merge-squash-provenance-and-rollback-coherence-01KXRRB7`
**Created**: 2026-07-17
**Status**: Draft (post-spec adversarial squad folded)
**Input**: Remediate the open P0 pair #2709 (squash merge overwrites target-newer artifacts + drops acceptance provenance) and #2711 (merge rollback/resume leave committed `done` events opposed to reverted working status). Both surfaced in the #2658 multi-WP coordination merge.

<!--
  Grounded by a pre-spec research squad (findings in ./research/lens-{a,b,c,d}-*.md)
  and hardened by a post-spec adversarial squad (reviewer-renata, python-pedro,
  planner-priti). Confirmed squad findings are folded below; the audit trail is in
  the "Post-Spec Squad Findings (folded)" section at the end.
-->

## Problem & Root Cause *(context)*

Both defects are symptoms of **one architectural class**: the merge core treats the
committed target/coord branch as passive and non-authoritative — it never reconciles
its writes against the durable event-log authority the charter names as the sole source
of truth. There are **two distinct fix surfaces with no shared call path**, so this is a
related pair, **not one bug** (Lens B §4). They share only the coord-topology test
harness and the class-closing invariant.

### #2709 — happy-path content loss (three sub-surfaces, ranked by RED strength)

`src/specify_cli/lanes/merge.py` (squash branch of `_merge_branch_into`) runs
`git merge --squash -X theirs <mission_branch>` (default strategy, via
`integrate_mission_into_target`). `-X theirs` steers git's **built-in text** driver to
favor the mission branch on every conflicting file. The loss depends on the file's merge
treatment:

1. **`meta.json` acceptance/VCS fields — LOAD-BEARING RED (no driver).** Keys
   `accepted_at`, `accepted_by`, `accepted_from_commit`, `acceptance_mode`,
   `accept_commit`, `acceptance_history`, `vcs`, `vcs_locked_at` (canonical shapes in
   `src/specify_cli/acceptance/__init__.py`) have **no** merge driver, so `-X theirs`
   reverts target-newer values to the older mission-branch copy. **No reconciler exists
   for `meta.json` at all** — this is net-new infrastructure, not "routing" (Priti HIGH,
   Lens C "missing seam").
2. **`traces/*.md` — LOAD-BEARING RED (no driver, no dedup key).** Append-only trace
   sections have no driver *and* no natural unique key (unlike JSONL's `event_id`), so
   "append-union" is under-specified and must be given a concrete contract (Pedro
   MEDIUM). Target-newer sections are dropped today.
3. **`status.events.jsonl` projection — GUARD assertion, separate fix surface (FR-005).**
   The event log *does* have the `spec-kitty-event-log` driver, so it may survive
   `-X theirs`; the real event-log loss for #2709 is a *different* code path —
   `merge/bookkeeping_projection.py::_project_status_bookkeeping_to_target` does a blind
   `write_bytes` of coord-worktree bytes over target (Lens C leak; Renata HIGH). This is
   **not** exercised by the squash repro and needs its **own** witnessing RED (see
   FR-005 / US2-S4).

Regression introduced in `a5f30616e` (#1732) — `-X theirs` added to keep the mission
branch authoritative for *planning* artifacts, but over-broadly captured acceptance
provenance. **Empirically confirmed (Pedro):** a custom `.gitattributes` merge driver
*does* fire under `git merge --squash -X theirs` when both sides diverge from
merge-base — so the driver approach is mechanically sound; `-X theirs` only steers git's
built-in text driver, not custom drivers.

### #2711 — failure-path status incoherence

Per-WP `approved → done` events are durably committed to the coord branch
(`merge/done_bookkeeping.py`, via `emit_status_transition_transactional`) **before**
target advancement, when `done_marked_before_target` is True (gated on the coord worktree
existing). On a target-advance failure (`merge/executor.py` `_phase_mission_to_target`),
rollback (`_restore_pre_target_if_at_baseline` → `bookkeeping_projection.py`
`_restore_final_bookkeeping_snapshots`) reverts **only working-tree bytes** — the
committed coord-branch `done` commit is never git-reverted. Then `spec-kitty merge
--resume` derives progress from `MergeState.completed_wps` (byte-restored to empty by the
same rollback) instead of the durable log → banner reads `0/N`, reconcile short-circuits,
and the dedup reads the reverted **worktree** (`coordination/status_transition.py`
worktree-first read contract) rather than the committed branch ref → it re-emits a
**duplicate** `done`.

### The fix posture

- `status.events.jsonl` reconciliation authority already exists
  (`src/specify_cli/status/event_log_merge.py::merge_event_payloads`, union/dedupe/sort).
  **FR-005 reuses it** (~5-line swap of the blind `write_bytes`) — satisfies C-001.
- `meta.json` acceptance provenance needs a **field-level JSON reconciler** (FR-004) —
  a *structurally different* reconciler from event-union. This is acceptable and
  necessary; C-001 forbids a duplicate *authority for the same data*, not a
  fit-for-purpose reconciler for a different artifact (see C-001 wording note).
- #2711 is fixed by **restoring committed==working coherence on rollback (Option A —
  revert the coord `done` commit)**, NOT by re-routing the read-contract SSOT
  (see FR-006/FR-007 decision).

## User Scenarios & Testing *(mandatory)*

> **RED-integrity note (binding, Renata):** every reproduction below must be RED **for
> the right reason** — the *first* failing assertion must be the contract assertion
> (provenance-field survival / committed-vs-working divergence / duplicate-`done` count),
> never a fixture/setup error. See SC-001.

### User Story 1 - Red-first reproductions land first (Priority: P1)

As a maintainer working a red-main P0, I want a committed failing reproduction test for
each defect **before** any fix, so the bug is witnessed against live code and can never
silently regress again.

**Why this priority**: Charter red-main/ATDD-first discipline requires a failing repro
through the pre-existing entry point before implementation, and the repros are the shared
dependency for both fix chains. The two repros are **independently authored** (WP01a for
#2709, WP01b for #2711 — Priti re-slice) so the fast fix does not wait on the slow one.

**Independent Test**: Run each new regression test on the mission base and observe it RED
on its contract assertion; no product change required to author them.

**Acceptance Scenarios**:

1. **(#2709, must genuinely conflict)** **Given** a coord mission where the coord branch
   holds an OLDER accepted `meta.json` (acceptance v1 at T1) **and** the target branch
   (`main`) holds a NEWER accepted `meta.json` (acceptance v2 at T2) — i.e. `meta.json`
   is modified on **both** sides vs merge-base so `-X theirs` genuinely fires — **When**
   the supported squash merge runs via `_run_lane_based_merge`, **Then** the test asserts
   on `git show main:kitty-specs/<slug>/meta.json` that the target-newer acceptance/VCS
   fields survive, and this is RED on the mission base.
   *(Binding precondition: without both-sides divergence git trivially keeps target and
   the test is green-on-base — proves nothing.)*
2. **(#2711, must not be vacuous)** **Given** a materialized-coord multi-WP mission,
   **When** the test arranges the run, **Then** it first asserts
   `is_under_worktrees_segment(...)` / `done_marked_before_target` is True **and** that
   the committed coord branch shows a `done` event per WP **before** the coherence check
   — so the coherence equality cannot pass vacuously via "no `done` was ever committed".
3. **(#2711 act)** **Given** the arranged mission, **When** target advancement is injected
   to fail via `patch("specify_cli.lanes.merge.integrate_mission_into_target", side_effect=RuntimeError)`
   (the canonical source-module target — **not** `specify_cli.merge.executor.*`, which is
   a lazy local import and never fires) and `spec-kitty merge --resume` runs, **Then** the
   coherence and duplicate-`done` assertions (US3) are RED on the mission base.

---

### User Story 2 - Squash merge preserves target-newer canonical state (Priority: P1)

As an operator merging an accepted mission, I want the squash merge to reconcile mission
artifacts with target-newer canonical state instead of clobbering it, so acceptance
provenance and target-side updates survive.

**Why this priority**: #2709 is silent data loss on the *happy* merge path — every
mission merge can drop acceptance provenance. Release-blocker while red.

**Independent Test**: The #2709 regression tests flip RED → GREEN; planning-artifact
authority (the #1732 behavior) is preserved by a companion assertion.

**Acceptance Scenarios**:

1. **Given** divergent `meta.json` (older on coord, newer accepted on target), **When**
   the squash merge runs, **Then** target-authoritative acceptance/VCS fields survive and
   `acceptance_history` is the union of both sides.
2. **Given** append-only `traces/*.md` with target-newer sections, **When** the squash
   merge runs, **Then** both sides' sections are present per the defined markdown-union
   contract (append-only, stable section delimiter, line-level dedup), none dropped.
3. **Given** a divergent *planning* artifact (spec/plan/WP outline), **When** the squash
   merge runs, **Then** the mission-branch copy remains authoritative (no #1732
   regression).
4. **(FR-005 projection hop — own witnessing RED)** **Given** a target-newer event on the
   projected `status.events.jsonl` that the coord-worktree copy lacks, **When** the
   coord→target status projection runs, **Then** the target-newer event survives on target
   (the projection unions via `merge_event_payloads` rather than blind-overwriting). RED
   on base because today `_project_status_bookkeeping_to_target` does `write_bytes`.

---

### User Story 3 - Rollback and resume stay coherent with the durable log (Priority: P1)

As an operator whose merge fails mid-flight, I want rollback to leave committed and
working mission state coherent, and `--resume` to derive progress from durable events
without duplicating transitions, so a retried merge is correct and idempotent.

**Why this priority**: #2711 corrupts status truth (committed `done` over reverted
`approved`) and makes resume double-emit — a reliability P0 on the failure path.

**Independent Test**: The #2711 regression test flips RED → GREEN; a resume-twice check
proves idempotency.

**Acceptance Scenarios**:

1. **Given** a target-advance failure after `done` events committed, **When** rollback
   runs, **Then** committed coord-branch status and the working snapshot agree per WP —
   asserted by reducing the committed ref via `read_event_log(EventLogReadContract.coordination_branch_ref(...))`
   + `wp_lane_actor_from_events()` and comparing to the working reduction (coherent, not
   split-brain; contract-routed, not a raw `git show <branch>:path` string).
2. **Given** a rolled-back merge, **When** `spec-kitty merge --resume` runs, **Then**
   progress derives from the reduced durable event log (not `MergeState.completed_wps`
   bytes), and the committed `done` event for each WP is **identity-stable** across resume
   (its `event_id` does NOT churn) — read via `EventLogReadContract.coordination_branch_ref(...)`.
   **NOTE (WP02 empirical finding):** the bug does NOT manifest as a `done` *count > 1* —
   the coordination safe-commit *replaces* the branch-tip log rather than appending, so a
   tip-count assertion is green-on-base (vacuous). The discriminating contract is
   idempotency / `event_id` stability, not a count.
3. **Given** `--resume` run twice, **When** the second run completes, **Then** the coord
   event log is byte-stable (idempotent) — the binding #2711 assertion.
4. **(edge — already-done)** **Given** a WP genuinely `done` before the failure, **When**
   resume runs, **Then** it is neither re-emitted nor reverted.
5. **(edge — non-coord no-op)** **Given** a `single_branch`/`lanes` mission (no coord
   worktree, `done_marked_before_target=False`), **When** merge + any failure runs,
   **Then** the fix path is a proven no-op (no coord-commit revert attempted).

---

### Edge Cases

- `meta.json` is written twice on the merge path (squash blob + post-merge
  `record_baseline_merge_commit` stamp of `baseline_merge_commit`/`mission_number`). The
  FR-004 field-merge must be idempotent under that second write and under `--resume`
  (Pedro: confirmed holds; pin a test that `write_meta(validate=False)` never drops an
  unknown key).
- Squash of a mission with **no** target-side divergence must remain byte-identical to
  today (NFR-001) — the new drivers must not manufacture spurious conflicts.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Red-first repro for #2709 (both-sides divergence) | As a maintainer, I want a committed failing test proving squash clobbers target-newer acceptance/trace state, with binding both-sides-divergence setup so it is RED-for-the-right-reason. | High | Open |
| FR-002 | Red-first repro for #2711 (non-vacuous) | As a maintainer, I want a committed failing test proving rollback+resume incoherence and duplicate `done`, with `done_marked_before_target` + committed-`done` preconditions asserted so it cannot pass vacuously. | High | Open |
| FR-003 | Per-artifact-class squash reconciliation | As an operator, I want planning artifacts to stay mission-authoritative but `meta.json` acceptance/VCS fields and `traces/*.md` target-reconciled, so provenance survives without a #1732 regression. Traces need a concrete markdown-union contract (or descope to a post-merge reconcile). | High | Open |
| FR-004 | meta.json acceptance field-merge (net-new) | As an operator, I want acceptance/VCS keys reconciled at field level with `acceptance_history` unioned. **Spike-flagged: no reconciler exists today; top mission risk.** | High | Open |
| FR-005 | Route event-log projection through the canonical reconciler (+ rematerialize the snapshot) | As a maintainer, I want `_project_status_bookkeeping_to_target` to union `status.events.jsonl` via `merge_event_payloads` instead of blind `write_bytes` **and** rematerialize `status.json` from the unioned events via `reduce()` (NOT blind-copy it — `status.json` is a derived reduced snapshot at `bookkeeping_projection.py:308`, so blind-copy would leave it contradicting the unioned log). Assert `snapshot == reduce(union)`. Own witnessing RED per US2-S4 for a target-newer `status.json` field. | High | Open |
| FR-006 | Coherent rollback — **Option A (revert coord `done` commit)** | As an operator, I want target-advance-failure rollback to revert the coord-branch `done` commit (capturing its ref SHA before the pre-target done emit — not captured today; `executor.py` snapshots working bytes only), so committed and working per-WP status stay coherent. **Source the ref-to-revert from `resolve_placement_only(repo_root, slug, kind=STATUS_STATE).ref`** (the canonical write-target the `done` commit actually used — NOT an inline `meta.get("coordination_branch")`, which reintroduces the retired D-2 CWD-divergence class). Revert via a **sanctioned ref path** (coord-worktree `git revert`/`git commit` or `git/ref_advance.py::advance_branch_ref`) — **never raw `git update-ref`** (AC-B3 lint) with subprocess env via `_make_merge_env` (AC-F1). **Option B (defer the commit) is rejected — it fights the INV-5 #1827 phase-ordering ratchet.** | High | Open |
| FR-007 | Durable-log resume derivation | As an operator, I want `--resume` progress derived from the reduced durable event log with `MergeState.completed_wps` demoted to an advisory hint. **Consume the existing committed-ref reduce authority — `read_event_log(EventLogReadContract.coordination_branch_ref(...))` + `wp_lane_actor_from_events()` (`coordination/status_service.py`); do NOT author a new `reduce_lane_by_wp`** (it would duplicate that authority — DIRECTIVE_044). With Option A restoring worktree==ref coherence, the existing worktree-first dedup becomes correct for free — **do NOT re-route the `status_transition.py` read-contract SSOT.** | High | Open |
| FR-008 | Class-closing invariant guard (non-vacuous, TWO mechanisms) | As a maintainer, I want a concrete guard covering **both** loss mechanisms: (1) a no-blind-copy AST lint over the `merge/` projection path (catches the `write_bytes` vector), **and** (2) a **driver-registry-completeness lint** asserting every both-sides-divergent `kitty-specs/**` canonical glob carries a registered merge driver (catches the `-X theirs`/no-driver vector in `lanes/merge.py`, which the projection lint is blind to). NOT a re-run of WP01. Lint home has precedent in `tests/architectural/test_merge_pipeline_ratchets.py` (AST per-call-site lints). Split per chain (WP04a/WP04b) + one cross-cutting lint. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No happy-path regression | A squash merge with no target-side divergence produces a byte-identical result to the pre-fix behavior. | Reliability | High | Open |
| NFR-002 | Resume idempotency | Running `spec-kitty merge --resume` N times after a rollback yields a byte-stable coord event log (zero duplicate transitions). | Reliability | High | Open |
| NFR-003 | Scoped test surface | Validation targets `tests/regression/test_issue_2709_*`, `tests/regression/test_issue_2711_*`, the existing merge suites (`tests/integration/test_merge_*`, `tests/merge/`, `tests/specify_cli/cli/commands/test_merge_*`), the **INV-5 #1827 ratchet homes** (`tests/merge/test_executor_phase_boundary.py`, `tests/specify_cli/merge/test_1827_baseline_regression.py`), and the AC-B3/AC-F1 lint (`tests/architectural/test_merge_pipeline_ratchets.py`), not the full suite. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Single canonical authority (scoped wording) | Reuse `merge_event_payloads` for event-log reconciliation; do NOT add a second authority *for the same data*. A fit-for-purpose field-level `meta.json` reconciler (FR-004) is a different artifact, not a duplicate authority. | Technical | High | Open |
| C-002 | Preserve #1732 intent | Planning artifacts remain mission-authoritative after the fix; do NOT naively drop `-X theirs` for all files. | Technical | High | Open |
| C-003 | Rebase-first + re-resolve anchors by symbol | The merge/rollback surfaces were recently refactored (#2057/#2173/#2632/#2675) — all landed on the mission base; **no active dedicated-session owns the merge core** (verified). Rebase onto current upstream, and re-resolve every cited file:line by SYMBOL — the anchors in this spec/lenses may have drifted. | Technical | High | Open |
| C-004 | Out of scope | Executor phase re-refactor (#2057 done), push/remote-state (017/018/049), SaaS/dossier sync. | Business | Medium | Open |
| C-005 | Terminology canon | Use `Mission` (not `feature`); user-facing flags use `--mission`. | Technical | Medium | Open |
| C-006 | .gitattributes multi-surface wiring | The FR-003/FR-004 drivers must register across the same surfaces as the event-log driver: root `.gitattributes`, `init.py`, an `m_3_1_1_event_log_merge_driver.py`-sibling migration, the `_ensure_*_merge_driver_config` self-heal, CLI registration, and the `_make_merge_env` PATH pin. 4–5 coordinated edits — do not under-scope. | Technical | Medium | Open |

### Key Entities

- **Durable event log** (`status.events.jsonl`): append-only, sole authority for WP lane
  state; reconciled by `merge_event_payloads` (union/dedupe/sort, keyed on `event_id`).
- **meta.json acceptance block**: `accepted_at/by/from_commit`, `acceptance_mode`,
  `accept_commit`, `acceptance_history`, `vcs`, `vcs_locked_at` — canonical shapes in
  `src/specify_cli/acceptance/__init__.py`; needs a net-new field-level reconciler.
- **traces/*.md**: append-only, **no** natural dedup key — needs an explicit union
  contract.
- **MergeState** (`merge/state.py`): `completed_wps`/`current_wp` — becomes an advisory
  progress *hint*, not the resume authority.
- **Coord worktree vs coord branch ref**: the split-brain surface; Option A restores
  their coherence rather than re-routing reads.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both new regression tests are RED on the mission base **with the *first*
  failing assertion being the contract assertion** (not setup/fixture error), and GREEN
  on the final mission commit.
- **SC-002**: After the fix, a squash merge with target-newer accepted `meta.json`
  preserves 100% of acceptance/VCS fields and unions `acceptance_history`; zero
  target-newer trace sections dropped; the FR-005 projection unions target-newer events.
- **SC-003**: After a target-advance-failure rollback, committed and working per-WP
  status are coherent in 100% of WPs, and `--resume` is **idempotent** — the committed
  `done` event identity (`event_id`) per WP is byte-stable across any number of resume
  invocations (NOT a tip-count assertion — see US3-S2 note).
- **SC-004**: The existing merge suites and the **real INV-5 #1827 ratchet homes**
  (`tests/merge/test_executor_phase_boundary.py`, `tests/specify_cli/merge/test_1827_baseline_regression.py`)
  plus the AC-B3/AC-F1 lints (`tests/architectural/test_merge_pipeline_ratchets.py`) remain
  green — no #1732 planning-authority regression, no phase-ordering regression.
- **SC-005**: The FR-008 guard is non-vacuous — it fails on a synthetic reintroduction of
  a blind overwrite of target-newer canonical/durable state (self-mutation check), and is
  NOT a re-run of WP01.

## Implementation Notes for Planning *(non-binding — from the research + adversarial squads)*

**WP graph (Priti re-slice — one mission, two decoupled chains):**

| WP | Scope | Depends on | Parallel |
|----|-------|-----------|----------|
| **WP01a** | #2709 red repro (per-branch `record_acceptance`/`set_vcs_lock` + deterministic `_now_iso`; both-sides `meta.json` divergence) | — | ∥ WP01b |
| **WP01b** | #2711 red repro (coord-worktree materialization + real-done-recording mock + `review_status: approved` seed; non-vacuous preconditions) | — | ∥ WP01a |
| **WP02** | #2709 reconcile seam: FR-003 per-class squash + **FR-004 meta.json field-merge (spike-flagged, top risk)** + FR-005 projection union + C-006 wiring | WP01a | ∥ WP03 |
| **WP03** | #2711 FR-006 Option A coord-`done`-revert + FR-007 durable-log resume (rebase-first, re-resolve anchors) | WP01b | ∥ WP02 |
| **WP04a** | #2709 invariant guard (no-blind-copy lint / property) | WP02 | — |
| **WP04b** | #2711 resume-non-reemission invariant | WP03 | — |

Critical path = the longer `WP01b→WP03→WP04b` (#2711 surgery). #2709 (`WP01a→WP02→WP04a`)
can land first and independently.

**Canonical entry point (both repros):** `_run_lane_based_merge` (`from specify_cli.cli.commands.merge import _run_lane_based_merge`). Reuse the real-git coord harness in
`tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py` (`_init_git_repo`,
`_bootstrap_coord_mission`, `_write_meta`, `_write_manifest`, `_file_on_branch`,
`_real_merge_external_mocks(real_baseline_recording=...)`, `_git`). Harness gaps all
confirmed fillable (Pedro): (a) accept helpers exist (`mission_metadata.record_acceptance`/`set_vcs_lock`);
(b) coord-worktree materialization pattern at `tests/merge/test_merge_target_resolution.py`
(`CoordinationWorkspace.worktree_path` + `git worktree add`); (c) the real-done mock is
already a parameterized seam (`real_baseline_recording`); (d) `review_status: approved` +
`reviewed_by` frontmatter seed.

**Architecture decision resolved by the squad:** FR-006 = **Option A** (revert the coord
`done` commit), rejecting Option B (defer commit) because B inverts the
`done_marked_before_target` machinery and fights the INV-5 #1827 ratchets; A restores
worktree==ref coherence and dissolves FR-007's "read committed ref" without touching the
read-contract SSOT. FR-003 merge-driver-under-`--squash -X theirs` is **empirically
confirmed to fire** — approach is sound; the soft spot is the traces markdown-union
contract.

**Red-proof commands:**
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2709_squash_provenance.py -n0 -q`
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2711_merge_rollback_resume_coherence.py -n0 -q`

**Tracker / issue-matrix:** #2709 and #2711 assigned to HiC, mission named in a comment on
each. Record in the issue-matrix: (a) **verified #2770 is a DRG/doctrine P0, unrelated to
the merge core — no lane collision** (corrects Lens C's phantom claim); (b) both issues
carry dual `priority:P0`+`priority:P1` — recommend reconciling to a single priority (HiC's
call); (c) confirmed no `test_issue_2709*`/`test_issue_2711*` exist on base — WP01 is not
redundant vs #2764.

## Post-Spec Squad Findings (folded) *(audit trail)*

Three independent lenses (reviewer-renata, python-pedro, planner-priti), profile-loaded,
read-only, code-verified. Convergent, no irreconcilable divergence.

- **Renata (anti-laziness):** 3 HIGH green-on-base traps closed → both-sides `meta.json`
  divergence (US1-S1/FR-001), non-vacuous `done`-committed preconditions (US1-S2/FR-002),
  FR-005 projection own-RED (US2-S4). Plus: pin duplicate-`done` to committed coord ref,
  SC-001 right-reason, promoted edge cases, corrected Lens B patch target.
- **Pedro (feasibility):** empirically proved the merge driver fires under
  `--squash -X theirs` (kills the stated critical risk); FR-006 → **Option A** (B fights
  INV-5); FR-005 is a clean ~5-line union; traces need a concrete union contract;
  FR-004/idempotency hold; C-006 multi-surface wiring; harness gaps all fillable.
- **Priti (scope):** RE-SLICE to two decoupled chains under one mission; meta.json
  field-merge is net-new infra (spike-flag); WP04 must be a concrete guard, split per
  chain; #2770 collision is a **phantom** (verified); re-resolve drifted anchors by
  symbol; tracker hygiene notes.

## Post-Plan Squad Findings (folded) *(audit trail)*

Post-plan brownfield squad (architect-alphonso, implementer-ivan, paula-patterns),
profile-loaded, read-only, all claims code-verified. **The pivotal charter-check bet is
CONFIRMED TRUE:** Option A (failure-path coord-`done`-revert) does NOT violate the INV-5
#1827 phase-ordering ratchet — rollback runs before the RECORD→commit→ASSERT sequence and
reorders nothing (architect, verified structurally).

Confirmed corrections folded above (and into plan.md IC map):

- **INV-5 #1827 anchor was WRONG** (architect HIGH, verified): the spec/plan cited
  `test_merge_pipeline_ratchets.py`, which has **zero** INV-5/1827 content (it locks
  #1826/#1736 via AC-B3/AC-F1/AC-F3). Real homes: `tests/merge/test_executor_phase_boundary.py`
  + `tests/specify_cli/merge/test_1827_baseline_regression.py`. Repointed in NFR-003/SC-004.
- **FR-005 has a second leg** (architect + Ivan, both HIGH — converged): the projection
  blind-writes `status.events.jsonl` **and** `status.json` (a reduced snapshot, `:308`).
  Snapshot must be rematerialized via `reduce(union)`, not blind-copied. Folded into FR-005.
- **FR-006 revert mechanism is ratchet-bound** (architect HIGH): the coord-`done`-revert
  moves a branch ref → must use `advance_branch_ref`/coord-worktree `git revert`, never raw
  `update-ref` (AC-B3), env via `_make_merge_env` (AC-F1). Folded into FR-006 + IC-04 surfaces.
- **FR-008 guard covers only ONE mechanism** (paula HIGH): scoped over `merge/` it catches
  the `write_bytes` vector but is blind to the `-X theirs`/no-driver vector in `lanes/merge.py`
  (the *primary* #2709 loss path). Added the driver-registry-completeness lint to FR-008.
- **Chains are NOT file-disjoint** (Ivan MEDIUM): `bookkeeping_projection.py` is edited by
  both WP02 (projection) and WP03 (rollback machinery lives there too) → tasks must publish a
  function-level ownership map or serialize the two edits.
- **WP02 spike isolation** (architect MEDIUM): split the FR-004 meta.json-driver spike into
  its own WP so a spike failure fails fast without stalling the #2709 chain's replicable wiring.
- **WP01b is a fixture *fusion*** (Ivan): fuse the coord-branch shape (`test_merge_coord_topology_1772.py`)
  with worktree materialization (`test_merge_target_resolution.py`). **Do NOT author a
  `reduce_lane_by_wp`** — superseded by the seam-fit fold below: consume the existing
  `EventLogReadContract.coordination_branch_ref` + `wp_lane_actor_from_events` authority.
- **Split-brain scan CLEAN** (paula): exactly the two named defect sites, no third instance —
  scope is complete. Campsite LOWs to fold at WP time: stale `_project_status_bookkeeping_to_target`
  shadow re-export in `cli/commands/merge.py.__all__`; committed temp `tests/architectural/tmp_ratchet_baseline.txt`.
- **Open question for WP03** (architect concession): confirm the coord `done` commit is made
  via `git commit` vs an `update-ref` path inside `BookkeepingTransaction` — determines whether
  AC-B3 is a live constraint on the revert. Resolve first in WP03.
- **Self-heal must be generalized, not cloned** (Ivan): `_ensure_event_log_merge_driver_config`
  hard-codes the event-log driver name/command — parametrize it for the new drivers
  (DIRECTIVE_044, avoid split-brain config). `_make_merge_env` PATH pin already auto-covers
  new drivers.

## Canonical Resolution Seam Fit (folded) *(audit trail)*

Seam-fit mini-squad (architect-alphonso, paula-patterns), read-only, code-verified.
**Both converge: the plan does NOT bypass or duplicate the canonical resolution seam, and
Option A is genuinely required — not subsumed by "route through the seam."** Key structural
fact: `resolve_status_surface[_with_anchor]` returns filesystem *paths* (`surface_path`,
`primary_anchor`), NOT a git ref — the seam owns coord-vs-primary *surface selection*, not
committed-ref reads. Three DIRECTIVE_044 hygiene corrections (folded into FR-005/006/007 +
plan IC-03/IC-04):

- **coord-ref source (HIGH):** the ref-to-revert must come from `resolve_placement_only(repo_root, slug, kind=STATUS_STATE).ref`
  — the canonical write-target the pre-target `done` commit actually used — NOT an inline
  `meta.get("coordination_branch")` (which reintroduces the retired D-2 CWD-divergence class
  and could revert a *different* ref than was committed).
- **no new reducer (HIGH):** FR-007 resume derivation and the repro assertions consume the
  existing committed-ref reduce authority `read_event_log(EventLogReadContract.coordination_branch_ref(...))`
  + `wp_lane_actor_from_events()` (`coordination/status_service.py`) — `reduce_lane_by_wp` is
  retired from scope (it would duplicate that authority).
- **FR-005 write-back (MEDIUM):** union (`source ∪ original`, both byte-sets already captured
  at `bookkeeping_projection.py:302-303`) + status.json rematerialization write back through
  the already-resolved `trusted_*` target paths (`_target_bookkeeping_status_paths`, seam-resolved
  via `primary_feature_dir_for_mission`) — compose no new path.
- **seam is path-only (note):** IC-04 must not try to obtain the coord ref from
  `_with_anchor`; capturing the ref SHA is legitimately net-new state (via `resolve_placement_only(...).ref`
  + `git rev-parse`, env `_make_merge_env`).
- **WP03 root confirmed:** the #2711 split lives at `status_transition.py:680-693`
  (`_read_contract_from_transaction_target` reads the worktree leg when the coord worktree
  exists, else `coordination_branch_ref`). Confirms FR-007's "force coherence via Option A,
  don't re-route the read contract" is defensible; still verify this read is worktree-anchored
  in WP03.
