# Mission Specification: Coord-Shadows Follow-ups Closeout

**Mission Branch**: `coord-shadows-followups-01KXBCZ1`
**Created**: 2026-07-12
**Status**: Draft
**Input**: Close the post-merge follow-ups of the coord-shadows-arm-closeout work (merged PR #2572, epic #2160): five re-verified tech-debt residuals under the theme "canonical-source consolidation + gate/liveness robustness".

## Context

The `coord-shadows-arm-closeout` mission (PR #2572) shipped the canonical `core/subtask_rows` row walker and the canonical `core/process_liveness.is_process_alive` seam, and closed the coord-shadows fail-open class at the emit layer. Its pre-merge squad and a fresh brownfield re-verification squad (reviewer-renata, randy-reducer, paula-patterns, planner-priti — four independent opus lenses) confirmed **five residual defects still reproduce on aligned `main`**. Each was re-verified against the current tree with exact line evidence; none is already fixed.

All five share one doctrine: *one canonical authority per operation, made correct.* Two sub-themes:

- **Consolidate onto the canonical seam** — the triplicated subtask-gate-dir resolver (#2574), the stray fifth checkbox parser (#2567), and the duplicate liveness probe in the review lock (#2568).
- **Harden the just-shipped canonical helpers** — PID-reuse blindness in `is_process_alive` (#2575), and the unguarded out-of-lock rollback-uncheck write (#2576).

## Tracked Issues (Issue Matrix)

| Item | Issue | Surface | Linkage | Parent |
|------|-------|---------|---------|--------|
| Consolidate triplicated subtask-gate-dir resolver → one `resolve_subtasks_gate_dir` seam | #2574 | `status/emit.py`, `status/aggregate.py`, `coordination/status_transition.py` | Closes | epic #2160 (sub-issue) |
| Harden `is_process_alive` against PID reuse + truth-in-labeling | #2575 | `core/process_liveness.py`, `core/stale_detection.py`, claim path | Closes | epic #2160 (sub-issue) |
| Harden rollback-uncheck read/write path (no lock fold) | #2576 | `cli/commands/agent/tasks_move_task.py` | Closes; Relates #2513 (origin, shipped) | epic #2160 (sub-issue) |
| Reconcile stray fifth checkbox parser onto `core/subtask_rows` | #2567 | `acceptance/gates_core.py`, `core/subtask_rows.py` | Closes | epic #2071 (existing parent) |
| Migrate review-lock liveness onto `core/process_liveness` | #2568 | `review/lock.py` | Closes; Relates #2575 | epic #2071 (existing parent) |
| Scaffold→block friction | #2566 | setup-plan / specify | **EXCLUDED** — separate slice, different defect class | epic #2017 |

Epic **#2160 stays open** (this mission is a functional child). #2513 is closed/shipped (F3's origin) and is relate-only. **#2566 is explicitly out of scope** — the squad verdict (unanimous) is that it is a workflow-guard ergonomics defect under epic #2017, not an artifact-authority defect under #2160.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The subtask gate reads the true primary tasks.md (Priority: P1)

A maintainer runs a status transition (`agent status --to for_review`, or a `move-task`) on a coord-topology mission whose planning surface is the primary partition. The completeness gate must read `tasks.md` from the primary planning surface, not from a stale coordination-branch husk — regardless of which of the three internal call sites performs the resolution.

**Why this priority**: The three resolvers diverge in their `repo_root is None` fallback. The weakest (`coordination/status_transition.py`) falls straight to the coord husk with no git-ancestry recovery, so a coord-topology mission can gate on a stale husk `tasks.md` — the exact fail-open class the epic is closing. This is a live correctness defect.

**Independent Test**: Drive the `in_progress → for_review` completeness check through each of the three call sites with `repo_root=None` on a git-rooted coord-topology fixture; assert all three resolve the primary `tasks.md` and produce the same verdict. A bare (non-git) `tmp_path` fixture still falls back to `feature_dir` unchanged.

**Acceptance Scenarios**:

1. **Given** a coord-topology mission with real git ancestry and `repo_root=None`, **When** the completeness check runs via `coordination/status_transition.py`, **Then** it reads the primary `tasks.md` (not the coord husk) and gates on the true row state.
2. **Given** the two already-strong call sites (`status/emit.py`, `status/aggregate.py`), **When** the resolver is consolidated onto one helper, **Then** their resolution is byte-identical to today for every pre-existing input.
3. **Given** a bare `tmp_path` fixture with no git ancestry, **When** resolution runs, **Then** it falls back to `feature_dir` unchanged (preserving non-repo unit-test behavior).
4. **Given** the consolidation lands, **When** the dead-code gate runs, **Then** no orphaned duplicate resolver remains.

### User Story 2 - Liveness cannot be fooled by a recycled PID (Priority: P1)

A maintainer abandons a claimed WP; the claiming shell dies and the OS later recycles its PID for an unrelated process. The staleness detector must still flag the WP as stale rather than trusting the recycled PID as "the claim is alive". The review lock must use the same canonical, PID-reuse-aware check.

**Why this priority**: `is_process_alive` trusts any live PID with no identity baseline, so a recycled PID reads "alive" and an abandoned WP is never flagged stale. The review lock carries a second, independent `os.kill(pid,0)` probe that inherits the same blindness. Both defeat stale-recovery silently.

**Independent Test**: The primary test seam is a **simulated baseline mismatch** — persist an identity baseline that does not match the process currently holding the PID and assert the claim is treated as NOT alive (rather than chasing a non-deterministic OS PID-recycle); complement with a real spawn→kill test for the exited-PID path; assert the review lock's staleness verdict matches `not is_process_alive(pid)` across all branches.

**Acceptance Scenarios**:

1. **Given** a `shell_pid` whose original process has exited and whose PID is now held by an unrelated process, **When** the staleness detector checks liveness, **Then** the claim is treated as NOT alive (stale-eligible).
2. **Given** a `shell_pid` whose identity baseline cannot be verified, **When** liveness is checked, **Then** it is treated as NOT alive (conservative).
3. **Given** the review lock's staleness check, **When** it is migrated onto the canonical helper, **Then** its verdict is branch-equivalent to the prior `os.kill(pid,0)` implementation for live / dead / permission-denied inputs.
4. **Given** the liveness test suite, **When** it runs, **Then** a real spawn→kill test exercises the reuse path and the mislabeled test + docstring overclaim are corrected.

### User Story 3 - A rolled-back WP cannot pass the gate on stale checked rows (Priority: P2)

A maintainer rolls a WP back to `planned`. Its `- [x] T###` subtask rows must be reliably unchecked, so the completeness gate cannot pass on the next `for_review` with no work redone — even if the out-of-lock write encounters an error.

**Why this priority**: The rollback-uncheck read/write is unguarded (only the commit is wrapped) and bypasses the house path-guarded writer; a write failure in the out-of-lock window can re-manifest the original #2513 bug. Correctness matters but the trigger (a failing write during rollback) is narrower than US1/US2.

**Independent Test**: Simulate a write failure in the rollback-uncheck window and assert the failure mode is defined (surfaced, never silently leaving checked rows on a `planned` WP); assert the write routes through the path-guarded writer; assert the out-of-lock ordering is preserved.

**Acceptance Scenarios**:

1. **Given** a WP rolled back to `planned`, **When** the uncheck write runs, **Then** it routes through the house `write_text_within_directory` guard.
2. **Given** the uncheck write fails, **When** the failure occurs, **Then** it is surfaced per the defined failure mode and does not silently leave `- [x]` rows on the `planned` WP.
3. **Given** the fix lands, **When** reviewed, **Then** the uncheck still runs out-of-lock (the documented design in #2576 is preserved — the lock is not widened).

### User Story 4 - One checkbox-parsing authority (Priority: P3)

The acceptance gate's unchecked-task detection uses the same canonical checkbox semantics as the rest of the system (T###-scoped, fence-aware), removing the last stray whole-file `[ ]` regex.

**Why this priority**: A canonicalization cleanup with a genuine semantics shift (the acceptance gate currently flags any `- [ ]` line, including prose and fenced examples). Correct direction, lowest urgency, and must be ratified consciously rather than folded silently.

**Independent Test**: A characterization test captures the acceptance gate's unchecked-row output before and after migration onto the shared constants, making the T###/fence/indent tightening explicit and intentional.

**Acceptance Scenarios**:

1. **Given** a `tasks.md` with T### rows, prose `- [ ]` lines, and fenced example checkboxes, **When** the acceptance gate detects unchecked tasks via the new canonical whole-file iterator, **Then** it flags only genuine T###-scoped unchecked rows (fence-aware), and the change is pinned by a characterization test.
2. **Given** the migration, **When** the dead-code gate runs, **Then** the stray parser is removed with no orphan.

### Edge Cases

- **Coord-topology with no git ancestry** (bare `tmp_path`): resolution must fall back to `feature_dir` unchanged — the consolidation must not regress library-internal unit tests.
- **PID reuse across platforms**: the exposure is platform-general (any PID wraparound inside the staleness window), not macOS-specific; the fix must not assume a particular `pid_max`.
- **Identity baseline absent on legacy claims**: a `shell_pid` written before the baseline field existed preserves today's behavior (the live PID is trusted) so no legacy claim regresses; the reuse compare applies only once a baseline is present, and never crashes.
- **Claim written by any path**: the baseline is co-written at every `shell_pid` write site (`spec-kitty implement`, the `agent action implement` per-WP claim, and the review claim that overwrites `shell_pid`), so no live claim path emits a baseline-less `shell_pid`.
- **Rollback-uncheck when `tasks.md` is absent**: remains a silent skip (no write, no failure).
- **Acceptance gate on a terminal mission**: the existing normalization that zeroes unchecked tasks when all WPs are terminal must be preserved after the parser migration.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Single canonical subtask-gate-dir resolver | As a maintainer, I want the subtask-gate directory resolved by one canonical helper (`resolve_subtasks_gate_dir`) consumed by all three call sites, so the gate cannot diverge per site. | High | Open |
| FR-002 | Strong git-ancestry fallback at every site | As a maintainer, I want the weak `coordination/status_transition.py` site to gain the git-ancestry fallback (resolve canonical root when `repo_root` is None) so a coord-topology mission stops gating on the coordination husk. | High | Open |
| FR-003 | Dead-code-safe consolidation | As a maintainer, I want the named duplicate resolver deleted and its callers repointed so no orphaned duplicate survives the dead-code gate. | High | Open |
| FR-004 | PID-reuse-aware liveness | As a maintainer, I want `is_process_alive` to compare a persisted creation-time/identity baseline before trusting a live PID, so a recycled PID is treated as not alive. | High | Open |
| FR-005 | Claim-time identity baseline capture | As a maintainer, I want the claim path to persist an identity baseline alongside `shell_pid`, and the staleness consumer to compare it, so liveness has something to verify against. | High | Open |
| FR-006 | Liveness truth-in-labeling | As a maintainer, I want the mislabeled recycled-PID test and the docstring overclaim corrected and a real spawn→kill liveness test added, so the suite tells the truth about what is covered. | Medium | Open |
| FR-007 | Guarded rollback-uncheck write | As a maintainer, I want the rollback-uncheck write routed through the house path-guarded writer with a defined failure mode, so a write failure cannot silently leave checked rows on a `planned` WP. | High | Open |
| FR-008 | Canonical whole-file unchecked-row iterator | As a maintainer, I want a canonical whole-file string-yielding iterator on `core/subtask_rows` shared constants, so the acceptance gate can consume one checkbox authority instead of a stray regex. | Medium | Open |
| FR-009 | Ratified acceptance-gate migration | As a maintainer, I want the acceptance gate migrated onto the canonical iterator with the T###/fence/indent tightening pinned by a characterization test, so the semantics shift is explicit and intentional. | Medium | Open |
| FR-010 | Review-lock liveness consolidation | As a maintainer, I want `review/lock` staleness migrated onto `core/process_liveness.is_process_alive` (branch-equivalent), so there is one liveness authority. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation on strong sites | The two already-strong resolver sites and the review-lock fold produce identical resolution/verdict to today for every pre-existing input, pinned by characterization tests (0 behavioral diffs on the preserved paths). | Reliability | High | Open |
| NFR-002 | Zero new lint/type findings | The mission adds 0 new `ruff` and 0 new `mypy` findings; existing load-bearing casts/wraps are retained (no advisory-noise "cleanup" that trades for a per-file break). | Maintainability | High | Open |
| NFR-003 | Test-per-branch | Every new helper/branch has a focused test in the same work package; the terminology and architectural guards stay green. | Maintainability | High | Open |
| NFR-004 | Liveness conservatism preserved | `is_process_alive` never raises; identity-unverifiable and absent/unparseable inputs return not-alive; the conservative "cannot prove dead → alive" (AccessDenied) branch is preserved. | Reliability | High | Open |
| NFR-005 | Scope containment | No process-liveness consumer outside {`core/process_liveness`, the `core/stale_detection` claim path, `review/lock`} is modified; measured as a diff/owned-files boundary. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No lock fold for rollback-uncheck | The rollback-uncheck must NOT be folded under `feature_status_lock`; the documented out-of-lock design (#2576) is preserved — the lock is not widened. | Technical | High | Open |
| C-002 | Carry load-bearing casts verbatim | The `cast(Path, ...)` at the resolver and the `bool(...)` liveness wraps are carried verbatim into the consolidated seams; advisory whole-repo mypy noise is NOT "cleaned" (it is load-bearing under per-file `follow_imports=skip`). | Technical | High | Open |
| C-003 | Canonical sources only | Use the canonical `resolve_planning_read_dir(kind=TASKS_INDEX)` resolver and the canonical `core/subtask_rows` + `core/process_liveness` seams; no improvised parsers, resolvers, or liveness probes. | Technical | High | Open |
| C-004 | Tight owned-files scoping for the rollback seam | The rollback-uncheck change is scoped tightly to its seam in `tasks_move_task.py`; it must not touch `_mt_run_pre_review_gate` (merge-collision risk with in-flight #2573 in the same module). | Technical | High | Open |
| C-005 | No psutil-consumer sweep | Do not sweep the other psutil consumers (`sync/*`, `dashboard/lifecycle.py`) onto the hardened liveness; file a separate sync-wide audit if wanted. | Technical | Medium | Open |
| C-006 | Fork PR; operator merges | Lands as a fork PR to Priivacy-ai/main; the operator merges. No direct push to origin/main. | Business | High | Open |
| C-007 | Liveness baseline is one additive marker | The identity baseline persisted alongside `shell_pid` is a single additive field (e.g., process creation-time), not a new process-identity schema/subsystem. The reuse compare is gated on the baseline being present: a present-but-mismatched baseline → not-alive (staleness falls to the commit-timestamp heuristic, never a hard-stale flag); an absent baseline (legacy claim) preserves today's live-PID behavior so no existing claim regresses. Every claim-write path co-writes the baseline going forward. Never crashes. | Technical | High | Open |

### Key Entities

- **Subtask-gate directory**: the primary-partition `tasks.md` location resolved for the completeness gate; today resolved three ways with divergent nullable-`repo_root` fallbacks.
- **Liveness baseline**: a persisted creation-time/identity marker captured alongside `shell_pid` at claim, compared before trusting a live PID.
- **Unchecked-row predicate**: the canonical T###-scoped, fence-aware checkbox semantics in `core/subtask_rows`, to be shared by a new whole-file string-yielding iterator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three subtask-gate call sites resolve through one helper; the previously-weak site now recovers the primary `tasks.md` on a git-rooted coord-topology mission with `repo_root=None` (verified by a red-first test); the named duplicate resolver is deleted with zero dead-code-gate orphans.
- **SC-002**: A recycled-PID scenario is treated as not-alive by both the staleness detector and the review lock; a real spawn→kill test covers the reuse path; the mislabeled test and docstring overclaim are corrected.
- **SC-003**: A simulated write failure during rollback-uncheck cannot leave `- [x]` rows on a `planned` WP; the write routes through the path-guarded writer; the out-of-lock design is preserved.
- **SC-004**: The acceptance gate uses one checkbox authority; the T###/fence/indent tightening is pinned by a characterization test; the stray parser is removed with no orphan.
- **SC-005**: Full gate pass — `ruff`, `mypy`, terminology, and architectural suites green; 0 new findings; the two closed sub-issues under #2071 (#2567/#2568) and the three under #2160 (#2574/#2575/#2576) are addressed; epic #2160 remains open.

## Assumptions

- The canonical seams shipped by #2572 (`core/subtask_rows` walker, `core/process_liveness.is_process_alive`) are the correct authorities to consolidate onto; this mission extends and hardens them, it does not redesign them.
- `resolve_planning_read_dir(..., kind=TASKS_INDEX)` remains the canonical planning-surface resolver; the new `resolve_subtasks_gate_dir` wraps it plus the strong fallback (the exact home — beside the resolver vs. beside `is_process_alive`'s promotion precedent — is a plan-phase placement decision to avoid the layering smell of importing a private `status/emit` helper into `status/aggregate` and `coordination/status_transition`).
- The acceptance-gate tightening (T###-only, fence-aware, anchored) is the intended direction; it is ratified via a characterization test rather than assumed.
- The identity-baseline field is additive; missions/claims written before it existed degrade conservatively and never crash.
- This is a flat (`single_branch`) mission; planning runs from the repository root checkout.
