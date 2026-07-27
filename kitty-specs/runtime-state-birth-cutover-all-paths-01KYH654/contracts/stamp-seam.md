# Contract: Terminal-Lifecycle Auto-Stamp

**Concern**: IC-01 / IC-02 · **Requirements**: FR-001, FR-004, FR-005, FR-006, NFR-003, NFR-004

## Trigger

The `accept` step of a mission's lifecycle (all WPs approved/done → runtime state
is final), running on the mission branch, before any PR/merge.

## Behavior

1. Resolve the mission's PRIMARY `feature_dir` and COORD `status_feature_dir`
   (topology-aware, exactly as `merge/executor.py::_run_birth_cutover` does).
2. Assert `mission_id` is present. **If absent → fail closed** (no slug-namespaced
   seed fallback).
3. Call the single authority `runtime_state_cutover.cutover_mission(feature_dir,
   status_feature_dir=..., dry_run=False)`. Do **not** fork a second writer.
4. Resolve the claim anchor from the **one canonical leg** (see NFR-004) so the
   seed payload is byte-identical to what any other caller would produce.
5. `status_phase` is written **last**, only after `verify.ok` (resume-heal;
   post-target-safe; never writes a stale `meta.json` under a worktree `.git`
   redirect).
6. Commit BOTH partitions into the branch that will land: `meta.json` on PRIMARY,
   seed events on COORD. **No reliance on the background status daemon** for the
   commit.

## Postconditions (MUST)

- The committed corpus on the mission branch is **cut over** (per data-model
  definition) before the branch can be merged by any path.
- Idempotent: re-running is a no-op — no duplicate or divergent seed events;
  identical `status.events.jsonl` bytes.
- Already-cut-over or eligibility-excluded missions are untouched.

## MUST NOT

- Assume any spec-kitty code runs at GitHub-merge time (C-004).
- Reintroduce the frontmatter `lane` mirror (C-002).
- Alter already-migrated missions (C-003).

## Acceptance tests

- **US1 GitHub-squash simulation**: finalize a mission, stamp at accept, simulate
  a squash merge (no `spec-kitty merge`), assert the target-branch corpus is cut
  over with no post-merge step.
- **R5 payload determinism**: stamp twice from different leg contexts → identical
  `status.events.jsonl` bytes.
- **R6 fail-closed**: absent `mission_id` → non-zero, no seed written.
