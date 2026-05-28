# Quickstart: Multi-lane mission on the new coordination-branch topology

This walkthrough demonstrates the end-to-end operator experience after both PR 1 and PR 2 have landed. It covers a 2-lane mission, the happy path, a forced commit failure to show the rollback path, and the final merge.

Prerequisites: `git >= 2.25`, `spec-kitty-cli` installed, a project that has run `spec-kitty agent setup`.

---

## Setup

```bash
cd ~/my-project
git checkout main
spec-kitty agent mission create "checkout-upsell-flow" \
  --friendly-name "Checkout Upsell Flow" \
  --purpose-tldr "Add an upsell at the checkout step" \
  --purpose-context "Increase ARPU by surfacing relevant add-ons during the final checkout step." \
  --json
```

Output (truncated):
```json
{
  "result": "success",
  "mission_slug": "checkout-upsell-flow-01J6XW9K",
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "feature_dir": "/.../kitty-specs/checkout-upsell-flow-01J6XW9K",
  "coordination_branch": "kitty/mission-checkout-upsell-flow-01J6XW9K",
  ...
}
```

`spec-kitty agent mission create` has minted:
- The mission directory `kitty-specs/checkout-upsell-flow-01J6XW9K/`
- The coordination branch `kitty/mission-checkout-upsell-flow-01J6XW9K` (parented off `main`)

No worktrees exist yet.

---

## Planning

```bash
/spec-kitty.specify
/spec-kitty.plan
/spec-kitty.tasks
```

These commands run in the primary checkout on `main`. They create `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and eventually `tasks.md` + `tasks/WP01-*.md ... WPNN-*.md`.

`finalize-tasks` writes WP frontmatter with `planning_base_branch: main` and `merge_target_branch: main` — the **canonical** target, never the current checkout branch (FR-012).

---

## Implement (first WP, first lane)

Operator A starts WP01.

```bash
spec-kitty implement WP01 --agent claude
```

What happens:

1. **Coordination worktree resolution**: `.worktrees/checkout-upsell-flow-01J6XW9K-coord/` is created at `kitty/mission-checkout-upsell-flow-01J6XW9K` (FR-024).
2. **Lane worktree creation**: `.worktrees/checkout-upsell-flow-01J6XW9K-lane-a/` is created parented off the coordination branch (FR-004). The lane allocator registers the sparse-checkout pattern (FR-029) so `status.events.jsonl` and `status.json` are excluded from the lane's working tree.
3. **`BookkeepingTransaction.acquire()`** runs:
   - Resolves coordination worktree.
   - Acquires feature status lock.
   - Captures `pre_emit_size` for `status.events.jsonl`.
   - Calls `WorkflowMutationPolicy.assert_allowed()` with `destination_ref="kitty/mission-checkout-upsell-flow-01J6XW9K"` → `Allowed`.
4. **Inside the transaction**:
   - `append_event(planned → claimed for WP01)` — appends to `status.events.jsonl` in the coordination worktree, re-materializes `status.json`.
   - `commit("chore: WP01 claimed for implementation [claude]")` — runs `safe_commit(destination_ref="kitty/...", worktree_root=<coord>, ...)`. HEAD assertion passes (coord worktree is on the coordination branch). Commit succeeds.
5. **Lock released**.
6. **Agent process** continues inside the lane worktree, editing source files. Code commits land on the lane branch via standard `git commit` from inside the lane worktree.

Terminal output (FR-014):
```
[implement] WP01 claimed for lane-a
[implement] Commits recorded:
  - kitty/mission-checkout-upsell-flow-01J6XW9K  chore: WP01 claimed for implementation [claude]  ✓
[implement] Agent ready in .worktrees/checkout-upsell-flow-01J6XW9K-lane-a/
```

---

## Implement (second WP, second lane, concurrent)

Operator B starts WP02 a moment later.

```bash
spec-kitty implement WP02 --agent opencode
```

Same flow as above, except:
- The coordination worktree already exists (idempotent reuse).
- A new lane worktree `.worktrees/checkout-upsell-flow-01J6XW9K-lane-b/` is created.
- The `planned → claimed for WP02` event appends to `status.events.jsonl` *after* lane A's event (lock serialization).

Both operators can run:
```bash
spec-kitty agent tasks status --mission checkout-upsell-flow-01J6XW9K
```

…from anywhere (lane-a CWD, lane-b CWD, or primary checkout). The CLI mediates through the coordination worktree (FR-030) and returns the same lane state to both queriers.

---

## Forced failure scenario (rollback)

Suppose the project has a pre-commit hook that rejects commits with a specific message format. Operator C runs:

```bash
spec-kitty implement WP03 --agent claude
```

1. `BookkeepingTransaction.acquire()` succeeds (pre-flight policy passes because `destination_ref` is the non-protected coordination branch).
2. `append_event(planned → claimed for WP03)` runs; `status.events.jsonl` grows from N bytes to N+L bytes.
3. `status.json` is re-materialized.
4. `safe_commit()` is called. HEAD assertion passes. The pre-commit hook rejects the commit.
5. `BookkeepingTransaction.__exit__` runs the rollback path:
   - `os.truncate(status.events.jsonl, pre_emit_size=N)` → file restored to N bytes (FR-010).
   - Re-materialize `status.json` from the truncated log.
   - Deferred outbound side effects are NOT run (FR-022).
   - Lock released.

Terminal output (FR-011):
```
Tracking commit 'chore: WP03 claimed for implementation [claude]' was rejected by pre-commit hook on branch kitty/mission-checkout-upsell-flow-01J6XW9K.
Lane transition planned → claimed for WP03 has been rolled back.
status.events.jsonl restored to pre-emit state.
Next step: Fix the pre-commit hook configuration and re-run.
```

Verify on disk:
```bash
sha256sum .worktrees/checkout-upsell-flow-01J6XW9K-coord/kitty-specs/checkout-upsell-flow-01J6XW9K/status.events.jsonl
# Same SHA as before the failed implement attempt
```

The operator fixes the hook, re-runs `spec-kitty implement WP03`, and the transition succeeds.

---

## Issue #1348 reproduction is impossible

The bug reported in #1348 was: implement appears to fail loudly *after* silently committing planning artifacts to `main`, and the event-log append on disk was ahead of HEAD.

Under the new architecture:
- Planning-artifact commits go through `BookkeepingTransaction` (FR-005, FR-020). Their `destination_ref` is the coordination branch. They never land on `main`.
- Event-log appends are atomic with the tracking commit (FR-010, FR-026). If the commit fails, the append is rolled back. The on-disk state never advances ahead of HEAD.

Even if an operator runs `spec-kitty agent action implement` from a `main` checkout, the policy gate sees `destination_ref="kitty/mission-..."` (not `main`), pre-flight passes, the `BookkeepingTransaction` opens the coordination worktree, and the commit lands there. The `main` checkout is never touched.

If the operator runs against a project where the coordination branch itself is somehow protected (e.g. a CI rule on `kitty/mission-*`), pre-flight refuses with a clear error naming the coordination ref and the operator can fix the protection.

---

## Mission close (two-stage merge)

After all WPs reach `done`:

```bash
spec-kitty merge --mission checkout-upsell-flow-01J6XW9K
```

Stage 1 (lane → coordination, per WP): for each lane in topological order, the lane branch is merged into the coordination branch. Conflicts (if any, on lane code) are surfaced to the operator via `spec-kitty merge --interactive`. A `lane_integrated` status event is recorded for each integrated WP (FR-008).

Stage 2 (coordination → target): the coordination branch is merged into `main`. The lane branches and the coordination worktree are deleted on success (FR-008, FR-016).

Final state:
- `main` has all lane code + all mission-wide bookkeeping (status events, decisions, issue-matrix).
- `.worktrees/checkout-upsell-flow-01J6XW9K-*` directories are gone.
- The coordination branch and lane branches are deleted.

---

## Discard a mid-flight mission

```bash
spec-kitty mission close --discard --mission checkout-upsell-flow-01J6XW9K
```

Deletes the coordination branch and all lane branches; removes the worktrees. `main` is untouched (FR-016).

---

## Legacy mission behavior

If you started a mission *before* PR 2 landed, that mission has no coordination branch. Running `spec-kitty implement WP01` on a legacy mission:

1. Detects no coordination branch present.
2. Emits a one-time warning: "Legacy topology; bookkeeping will land on the lane branch."
3. Resolves `destination_ref` to the lane branch.
4. Runs the same `BookkeepingTransaction`, same lock, same rollback, same outbound deferral (FR-017, FR-027).

Issue #1348's symptom cannot recur on a legacy mission either.

---

## Doctor checks

```bash
spec-kitty doctor
```

New checks added by this mission:
- **Coordination worktree health**: for each active mission, verify the coordination worktree exists, is checked out to the right branch, has a clean working tree.
- **Sparse-checkout drift**: for each lane worktree, verify the sparse-checkout pattern excludes the status files.
- **Git version**: warn if `git < 2.25` (RR-01).

Any drift is reported with a `spec-kitty agent worktree repair --mission <handle>` next step.

---

## What you can't (and shouldn't) do

- **Don't `git checkout` the coordination branch into a lane worktree.** That breaks the invariant that the lane worktree's HEAD is always the lane branch.
- **Don't manually edit `status.events.jsonl` or `status.json`.** Use `BookkeepingTransaction` via the CLI.
- **Don't bypass `safe_commit()` to land bookkeeping commits.** The HEAD assertion catches this loudly; the architectural test in PR 3 prevents the import path in the first place.
- **Don't push the coordination branch** unless your project explicitly wants per-mission CI. The coordination branch is local-only by default (Assumption #1 in spec.md).
