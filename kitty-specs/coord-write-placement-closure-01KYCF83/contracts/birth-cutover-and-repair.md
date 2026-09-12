# Contract — Birth-Cutover, Acceptance Lock, and Repair

## Event-sourced authoring (FR-008)
- **Scope**: exactly two paths — claim (`shell_pid`/`agent`) and subtask-completion (`tasks.md` checkboxes), per #2684.
- **Given** a WP is claimed or a subtask completed, **when** the write occurs, **then** it is recorded as an event (not authored to frontmatter/`tasks.md`), so no un-seeded runtime accrues.
- **Bound**: no other authoring path changes (C-002).

## Birth-cutover (FR-009, NFR-003, C-004)
- **Given** a mission is merged, **when** the cutover runs at the bake stage, **then** `cutover_mission` reconciles residual runtime and stamps `status_phase`, with `meta.json`/`status_phase` routed to PRIMARY and seed events to COORD via the placement port (FR-002).
- **Timing (corrected)**: the `_bake_mission_number` hook is **pre-target** (`executor.py:1319` runs before `_phase_mission_to_target`). The PRIMARY meta flip therefore **rides the mission→target merge atomically** — if the merge aborts, the flip never reaches target, which stays consistent (the un-merged mission branch is discarded). The plan must choose ONE of: (a) keep the bake hook and rely on merge-atomicity for the PRIMARY leg, or (b) relocate the stamp to a post-`_phase_commit_and_assert` phase. Either way the earlier "fires only after the target commit is durable" wording was inaccurate for this hook.
- **Two-partition atomicity (OPEN — IC-08 must resolve)**: `cutover_mission(feature_dir)` is **single-`feature_dir` by signature** and cannot natively split meta→PRIMARY (mission branch) from seed events→COORD (coord branch). IC-08 must either add a two-target form to the cutover spine OR delegate the COORD seed-event write to the existing coord projection (`_phase_record_done_and_project`), with a transactional envelope / resume-heal so a crash between the COORD write and the PRIMARY flip cannot leave a half-born mission.
- **Idempotent**: a re-run (merge `--resume`, or the one-time migration) seeds 0 events and leaves `status_phase` + the event log byte-identical.
- **Sole writer**: reuses `cutover_mission` / `_flip_phase` (no parallel `status_phase` writer) — a two-target form extends the spine, it does not fork it (C-004).
- **Gate**: the birth-write itself must satisfy IC-02's whole-tree write-placement gate.

## Acceptance lock (FR-010, NFR-006, C-003)
- **Given** a mission whose **event log** carries runtime (excluding the self-referential cutover mission), **when** `test_dogfood_corpus_backfilled` runs, **then** it requires `status_phase>=1` + a non-empty snapshot, and preserves the `verify_backfill` parity assertion (no green-wash).
- **Durable**: the lock stays green after ≥3 subsequent mission merges with no manual backfill (SC-001).
- **Migration coexistence**: a regression proves the one-time `migrate backfill-runtime-state` path still cuts over a legacy corpus after FR-008.

## `agent mission repair` (FR-005, NFR-005)
- **Given** a mission with pre-existing content divergence across partitions:
  - **strict-ancestor + clean worktree** → forward-only (fast-forward), zero data loss;
  - **non-ancestor divergence** → **refuse**, emit a unified diff, zero mutation.
- **Bound**: distinct command; `doctor coordination --fix` stays minimized (C-002/C-003).
