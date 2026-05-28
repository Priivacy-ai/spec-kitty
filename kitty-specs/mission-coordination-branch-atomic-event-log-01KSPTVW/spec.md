# Mission Specification: Mission Coordination Branch with Atomic Event Log

**Mission**: `mission-coordination-branch-atomic-event-log-01KSPTVW`
**Mission ID**: `01KSPTVWZ9GGWK5NC9RYNMWPVV`
**Mission Type**: `software-dev`
**Target Branch**: `main`
**Source Issue**: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348)
**Status**: Draft

---

## Purpose

**TL;DR**: Route mission bookkeeping to a per-mission coordination branch and make event-log emission atomically reversible so `implement`/`review` never leaves dangling commits on `main`.

**Context**: Today, `spec-kitty agent action implement` and `spec-kitty agent action review` silently commit planning artifacts to protected branches while loudly rejecting WP transition tracking commits, and they append events to `status.events.jsonl` *before* attempting the tracking commit — leaving dirty working trees on `main` when the commit fails. This produces a working tree where on-disk lane state diverges from committed history, and `spec-kitty agent tasks status` (which reads the event log) disagrees with `git log` (which reads the commits). Operators have to manually `git checkout -- status.events.jsonl status.json` or stand up throwaway `prep/...` branches to recover — and those prep branches then leak into `finalize-tasks` output as the "canonical" `target_branch` for WPs, causing later lane allocation to crash when the prep branch is deleted.

This mission introduces a per-mission **coordination branch** that owns mission-wide bookkeeping, parents each lane, and is merged back to the canonical target at mission close — combined with a **pre-flight workflow-mutation policy gate** (cheap refusal before any write) and a **surgical rollback** of event-log appends when a tracking commit fails *after* passing the pre-flight gate. As a side effect, `finalize-tasks` is hardened to record the canonical merge target branch (from `mission create --json` → `merge_target_branch`) rather than the current checkout branch at the moment it runs.

### Core invariant

> **No workflow mutation may occur unless the corresponding git mutation is permitted.**

Every write that the runtime makes during `implement`/`review` — appending to `status.events.jsonl`, re-materializing `status.json`, mutating WP frontmatter, emitting planning artifacts (`decisions/index.json`, `issue-matrix.md`), and dispatching outbound SaaS/dossier sync — is paired with a tracking commit. The invariant says: ask the git-policy layer *before* the write; if the commit cannot succeed, the write must not happen. Failures that only manifest at commit time (pre-commit hook reject, disk full, branch-protection rule that didn't exist at pre-flight) trigger the surgical rollback path so the workflow state on disk is restored to its pre-mutation form. Outbound side effects (SaaS, dossier) are deferred until *after* the commit succeeds.

---

## User Scenarios & Testing

### Primary Scenario — Multi-lane mission progresses cleanly

1. Operator runs `spec-kitty agent mission create my-feature --json`. The command mints `mission_id`, `mid8`, `mission_slug`, and a coordination branch `kitty/mission-my-feature-<mid8>` parented off `main` (the canonical target).
2. Operator runs `/spec-kitty.tasks` and then `spec-kitty agent mission finalize-tasks`. WP frontmatter for every WP records `planning_base_branch: main` and `target_branch: main` (the canonical target from `mission create --json`), regardless of which branch the operator was on when finalize ran.
3. Operator A runs `spec-kitty implement WP01 --agent claude`. The runtime creates `.worktrees/my-feature-<mid8>-lane-a/` parented off the **coordination branch** (not `main`). The `planned → claimed` event appends to `status.events.jsonl` on the coordination branch and is recorded by a tracking commit on the coordination branch. Code edits land on the lane branch.
4. Operator B concurrently runs `spec-kitty implement WP02 --agent opencode`. Lane B's worktree is parented off the coordination branch (which already contains lane A's claim event). Lane B's claim event appends after lane A's. Both transitions are visible in `spec-kitty agent tasks status` from either lane worktree or the coordination branch.
5. As each lane reaches `for_review`, the runtime auto-rebases that lane from the coordination branch (sync point #1: claim/start was the first; sync point #2 is `for_review → in_review`). New peer events are pulled in.
6. After all WPs reach `done`, `spec-kitty merge` fast-forwards the coordination branch to `main` and deletes the lane branches and the coordination branch.

### Exception Scenario A — Operator runs `implement` from a protected branch

1. Operator (out of habit) runs `spec-kitty agent action implement --mission my-feature --agent claude` from `main`.
2. The pre-flight workflow-mutation policy gate runs *before* any write. It asks the git-policy layer: "would a commit on `main` be allowed for this operation?" The answer is no.
3. The runtime refuses **all** bookkeeping operations (event append, status materialize, planning-artifact write, transition tracking commit) — no silent bypass for any class.
4. The error message names the correct destination: `"Refusing to record WP01 transitions on protected branch 'main'. Run from the lane worktree at .worktrees/my-feature-<mid8>-lane-a/ or pass --mission my-feature to auto-resolve."`
5. **No write happens at all** — `status.events.jsonl` is untouched, no rollback needed, working tree on `main` is byte-identical to its pre-command state.

### Exception Scenario B — Tracking commit fails *after* the pre-flight gate passed (residual failure class)

This scenario covers failures that the pre-flight gate cannot predict: pre-commit hooks that reject the tracking commit message, disk full mid-write, a branch-protection rule that was added between the pre-flight check and the commit attempt, or git plumbing failures. The pre-flight gate has already said "yes, a commit here would be permitted" — but the commit still fails when actually attempted.

1. Pre-flight gate passes (the lane worktree is on a non-protected branch; git-policy says yes). Lane worktree appends the `planned → claimed` event to `status.events.jsonl`. The runtime records `pre_emit_size = N` (the file's byte length before the append) and writes the new event line, making the file length `N + L`.
2. The runtime re-materializes `status.json` from the new event log.
3. The runtime attempts the tracking commit on the coordination branch. A pre-commit hook (or branch-protection rule, disk full, etc.) rejects it.
4. The runtime executes surgical rollback: `os.truncate(status.events.jsonl, N)` (drops *only* the appended line — preserves any other concurrent writers' state if they appended before this truncate), then re-materializes `status.json` from the truncated event log.
5. The operator sees a loud diagnostic that names: the rejected commit message, the branch it was attempted on, the lane transition that was rolled back, and a concrete next step (fix the hook and re-run).
6. After fixing the hook, the operator re-runs `spec-kitty implement WP01` — the lane transition re-emits and commits cleanly.

### Exception Scenario C — Concurrent emit during rollback

1. Lane A starts emitting `planned → claimed` for WP01, records `pre_emit_size = 4096`, appends → file is `4096 + L_A` bytes.
2. While lane A's tracking commit is being attempted (and failing), lane B (running in parallel) appends `planned → claimed` for WP02 → file is now `4096 + L_A + L_B` bytes.
3. Lane A's commit fails. Surgical truncate to 4096 would **clobber** lane B's appended event.
4. The rollback path detects this case: if the file is longer than `pre_emit_size + L_A`, it must remove **only the bytes lane A wrote** by line-id (event_id), not by raw truncate. Implementation may use a marker line, a recorded byte range `[pre_emit_size, pre_emit_size + L_A)`, or a re-read-and-rewrite-without-event-id approach. Acceptance criterion: lane B's event survives.
5. If acquiring the exclusive write lock for the rollback is not possible (another emitter has it), the runtime falls back to "surface the divergence explicitly" mode: print a precise diagnostic naming the orphaned event_id and the path the operator should run `spec-kitty agent status rollback <event_id>` to clear it manually.

### Edge Cases

- **Mission discarded mid-flight**: `spec-kitty mission close --discard` deletes the coordination branch and all lane branches. `main` is untouched.
- **Mission close after partial progress**: Closing a mission with some WPs `done` and others `canceled` still merges the coordination branch to `main` (it represents the final state of mission-wide bookkeeping).
- **Existing in-flight missions at rollout**: Missions whose lanes were created before this change continue to function; the runtime detects "no coordination branch exists for this mission" and falls back to the legacy parent (`main`) for those lanes, emitting a one-time warning. New missions get the new topology.
- **Hook reject on the rollback's re-materialize commit**: The rollback path only writes to disk (truncate + re-materialize); it does not produce a new commit. Hooks do not run on file-system rollback.
- **Coordination branch already exists** (e.g. operator partially completed `mission create` previously): `mission create` is idempotent — it reuses the existing branch if it points at a commit that is an ancestor of the canonical target; otherwise it refuses with a clear error.

---

## Functional Requirements

| ID     | Description                                                                                                                                                                                                                                                                                                                                                          | Status |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| FR-001 | The runtime MUST refuse, with a clear error, every bookkeeping commit (both planning-artifact commits and WP transition tracking commits) that targets a protected branch during `agent action implement` and `agent action review`. There is no silent-bypass path for spec-kitty-internal commits on protected branches.                                          | Draft  |
| FR-002 | The protected-branch refusal error MUST name (a) the rejected commit message, (b) the destination branch the operator should switch to (lane worktree path AND/OR coordination branch name), and (c) a one-line next-step instruction.                                                                                                                              | Draft  |
| FR-003 | `spec-kitty agent mission create` MUST mint a coordination branch named `kitty/mission-<mission_slug>-<mid8>` off the canonical target branch (resolved via the existing branch-context helper) at mission creation time.                                                                                                                                            | Draft  |
| FR-004 | Lane allocation MUST parent each lane branch (e.g. `kitty/mission-<mission_slug>-<mid8>-lane-a`) off the coordination branch, not off the canonical target branch.                                                                                                                                                                                                   | Draft  |
| FR-005 | Mission-wide bookkeeping — `status.events.jsonl`, `decisions/index.json`, `issue-matrix.md`, all WP transition tracking commits, and all planning-artifact commits — MUST be committed on the coordination branch.                                                                                                                                                   | Draft  |
| FR-006 | Lane code work (the operator's source edits inside `.worktrees/...`) MUST continue to commit on the lane branch and MUST NOT be retargeted to the coordination branch.                                                                                                                                                                                               | Draft  |
| FR-007 | Lane branches MUST auto-rebase from the coordination branch at exactly two sync points per lane lifecycle: (a) lane claim/start (the first `planned → claimed` for a WP in that lane), and (b) the first `for_review → in_review` transition for that lane.                                                                                                          | Draft  |
| FR-008 | Final mission merge MUST merge the coordination branch into the canonical target branch (typically `main`), and MUST delete the coordination branch and all of its child lane branches on success. `spec-kitty merge` and equivalents MUST NOT merge a lane branch directly into the canonical target branch.                                                       | Draft  |
| FR-009 | Before appending an event line to `status.events.jsonl`, the emission pipeline MUST capture `pre_emit_size = os.path.getsize(events_path)` (or equivalent `f.tell()` after open-for-append) and retain it for the duration of the emit attempt.                                                                                                                      | Draft  |
| FR-010 | If the tracking commit for an emitted event fails (any non-zero git exit, hook reject, disk full, branch-protection refusal), the emission pipeline MUST surgically remove the appended line from `status.events.jsonl` — by truncating to `pre_emit_size` if no concurrent writers have appended in the meantime, or by event_id-targeted removal otherwise — and MUST re-materialize `status.json` from the corrected event log. | Draft  |
| FR-011 | After a successful rollback, the runtime MUST emit a single diagnostic that names: (a) the failing tracking commit message, (b) the branch the commit was attempted on, (c) the lane transition that was rolled back (`<from_lane> → <to_lane>` for `<wp_id>`), and (d) the concrete next step.                                                                      | Draft  |
| FR-012 | `spec-kitty agent mission finalize-tasks` MUST record the canonical merge target branch (from the `mission create --json` payload's `merge_target_branch` field, persisted in `meta.json` → `target_branch`) in every WP's frontmatter (`planning_base_branch`, `target_branch`) and in `lanes.json`. The current checkout branch at finalize-tasks runtime MUST NOT be used. | Draft  |
| FR-013 | The `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` tuple in `src/specify_cli/git/commit_helpers.py` MUST NOT contain any spec-kitty-internal exception that allows bookkeeping commits to land on a protected branch silently. Documented exceptions for `upgrade`/`release` workflows MAY remain but MUST be documented in the module docstring.                              | Draft  |
| FR-014 | `agent action implement` and `agent action review` output MUST include a summary section before declaring success/failure, listing each commit produced: commit message, target branch, and outcome (committed / refused). Format MUST be both human-readable and machine-parseable (JSON output mode included).                                                     | Draft  |
| FR-015 | All coordination and lane branch names MUST be derived from `mission_id` / `mid8` / `mission_slug`. `mission_number` MUST NOT appear in any branch name. (Reinforces the mission 083 identity model.)                                                                                                                                                                | Draft  |
| FR-016 | `spec-kitty mission close --discard` MUST delete the coordination branch and all its child lane branches. Successful close (mission complete) MUST fast-forward-merge the coordination branch to the canonical target branch and then delete the coordination and lane branches.                                                                                    | Draft  |
| FR-017 | Existing in-flight missions whose lanes were created before this change (no coordination branch exists) MUST continue to function. The runtime MUST detect the missing coordination branch, emit a one-time warning, and fall back to the legacy topology (lanes parented on the canonical target) for the remainder of that mission's life.                         | Draft  |
| FR-018 | `mission create` MUST be idempotent w.r.t. coordination branch creation: re-running against a partially-created mission MUST reuse the existing coordination branch if it is an ancestor of the canonical target, or refuse with a clear error otherwise.                                                                                                            | Draft  |
| FR-019 | A workflow-mutation policy gate MUST be invoked **before the first workflow write** of every transactional command path (`agent action implement`, `agent action review`, `agent mission finalize-tasks`, planning-artifact emission). The gate asks the git-policy layer "would the corresponding tracking commit be permitted on the current branch?" and refuses the entire operation if the answer is no — *before* any file is written and *before* any event is appended. | Draft  |
| FR-020 | The policy gate (FR-019) MUST be the single chokepoint for protected-branch refusal. The raw `git add` / `git commit` call site for planning artifacts (currently `src/specify_cli/cli/commands/implement.py`) MUST route through the same gate; the lifecycle status-write call sites (currently `src/specify_cli/cli/commands/agent/workflow.py`) MUST consult the gate before writing.                                                                              | Draft  |
| FR-021 | The pre-flight gate (FR-019) and the surgical rollback (FR-010) MUST compose: when the pre-flight gate refuses, no rollback machinery runs (nothing was written); when the pre-flight gate passes but the commit fails afterward, the rollback path runs. Both paths MUST produce the same diagnostic shape (FR-002/FR-011) so operators see one consistent error format regardless of which failure class fired. | Draft  |
| FR-022 | Outbound side effects emitted during transactional command paths — SaaS event sync, decision-thread fanout to a tracker, dossier ingress, and any analogous "push to external system" — MUST be deferred until *after* the corresponding local tracking commit succeeds. If the commit fails (and rollback runs), the outbound emission MUST NOT have occurred. This applies to the implement and review command paths; non-transactional read-side syncs are unaffected. | Draft  |

---

## Non-Functional Requirements

| ID      | Description                                                                                                                                                                                                                                                                                | Threshold                                          | Status |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------ |
| NFR-001 | After a forced tracking-commit failure (with no concurrent writers), `status.events.jsonl` on disk MUST be byte-identical to its pre-emit state (SHA-256 equal).                                                                                                                          | 100% of 100 forced-failure test cases              | Draft  |
| NFR-002 | Surgical-rollback execution time (truncate + re-materialize `status.json`) MUST complete within a small bounded budget on a realistic event log.                                                                                                                                          | < 100ms on a 10 MB / 100k-line event log           | Draft  |
| NFR-003 | `spec-kitty agent tasks status` results MUST be identical when queried from any lane worktree or the coordination branch, within one rebase sync point of the most recent peer emit.                                                                                                      | ≤ 1 sync point of divergence (defined in FR-007)   | Draft  |
| NFR-004 | `spec-kitty agent mission create` total runtime MUST NOT regress beyond the existing budget despite adding coordination branch creation.                                                                                                                                                  | < 2 seconds end-to-end on a 10k-file repo          | Draft  |
| NFR-005 | The implement/review commit-summary block (FR-014) MUST add no more than a small bounded number of bytes to a typical command's stdout in success cases.                                                                                                                                  | ≤ 1 KB per command invocation in the happy path    | Draft  |
| NFR-006 | Test coverage for new code (event-log rollback path, coordination branch lifecycle, finalize-tasks branch resolution) MUST meet the project's charter policy.                                                                                                                             | ≥ 90% line coverage on new modules                 | Draft  |
| NFR-007 | The protected-branch refusal error (FR-001/FR-002) MUST cite a stable error code suitable for scripted detection.                                                                                                                                                                          | One stable identifier per refusal class            | Draft  |
| NFR-008 | The pre-flight policy gate (FR-019) MUST add bounded latency to transactional command paths.                                                                                                                                                                                                | < 10ms per invocation on a local git repo          | Draft  |
| NFR-009 | After a forced commit failure (post-pre-flight class — e.g. hook reject), any SaaS event sink configured for the project MUST NOT have received the rolled-back event.                                                                                                                       | 100% of 100 forced-failure test cases              | Draft  |

---

## Constraints

| ID     | Description                                                                                                                                                                                                                                              | Status |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| C-001  | Coordination branch naming MUST follow `kitty/mission-<mission_slug>-<mid8>` exactly, to remain consistent with the mid8 identity model from mission 083.                                                                                                | Active |
| C-002  | Lane branch naming MUST continue to follow `kitty/mission-<mission_slug>-<mid8>-lane-<id>`. (No change.)                                                                                                                                                 | Active |
| C-003  | The implementation MUST NOT regress the protected-branch guard for any commit class that is currently rejected. (The change tightens the guard for planning-artifact commits; it does not loosen it for anything else.)                                  | Active |
| C-004  | Event log entries MUST remain append-only and chronologically ordered after every rollback. (No `event_id` reuse across truncate; no out-of-order timestamps.)                                                                                           | Active |
| C-005  | All identity lookups MUST continue to disambiguate by `mission_id` (or its `mid8` prefix). `mission_number` remains display-only and MUST NOT appear in branch names or worktree paths.                                                                  | Active |
| C-006  | ASCII-only sanitization (per DIR-010 / DIR-011) applies to every input that feeds the coordination branch name derivation.                                                                                                                                | Active |
| C-007  | The change MUST NOT break existing missions whose worktrees already exist parented on the canonical target branch. Backward-compatible fallback is mandated by FR-017.                                                                                   | Active |
| C-008  | `mypy --strict` MUST continue to pass with no errors in any new or modified module. (Charter policy.)                                                                                                                                                    | Active |
| C-009  | The surgical-truncate rollback MUST NOT use `git checkout -- <path>` to restore state, because that is destructive to any other legitimate uncommitted changes in the file and races with concurrent emitters.                                           | Active |
| C-010  | No new external dependencies. The rollback path MUST use Python stdlib (`os.truncate`, `os.path.getsize`) and the existing git subprocess wrappers in `specify_cli.git`.                                                                                  | Active |

---

## Success Criteria

| ID    | Outcome                                                                                                                                                                                                              | How verified                                                    |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| SC-01 | Zero spec-kitty bookkeeping commits land on a protected branch in a sample of 100 simulated implement/review runs after rollout.                                                                                       | Integration test sweep with branch-protection-on fixtures       |
| SC-02 | A user running `spec-kitty agent tasks status` from any lane worktree or coordination branch sees the same WP lane state within one rebase sync point of the latest peer emit.                                         | Multi-lane integration test querying status from N viewpoints   |
| SC-03 | A user reading the `implement` / `review` terminal output can identify every commit the command produced (message, target branch, outcome) without inspecting `git log`.                                               | Golden-output integration test                                  |
| SC-04 | A mission created after rollout, with `finalize-tasks` run from a non-canonical branch (e.g. `prep/...`), produces WP frontmatter and `lanes.json` whose `target_branch` field equals the canonical merge target.      | Unit + integration test for `finalize-tasks` branch resolution  |
| SC-05 | After 100 forced tracking-commit failures (via hook reject), `status.events.jsonl` on disk is byte-identical (SHA-256) to its pre-emit state in every case where no concurrent writers were active.                    | Forced-failure stress test                                      |
| SC-06 | The dangling-event reproduction from issue #1348 (event appended on `main`, commit rejected, on-disk state advanced) no longer reproduces on any branch.                                                               | Regression test against the exact issue #1348 sequence          |
| SC-07 | Existing in-flight missions (created before this change) continue to function without manual intervention; the runtime warns once and falls back to legacy topology.                                                   | Migration smoke test on a pre-existing mission fixture          |
| SC-08 | A pre-flight refusal on a protected branch (Exception Scenario A) leaves `status.events.jsonl`, `status.json`, WP frontmatter, planning-artifact files, and the SaaS event sink byte-identical / event-identical to their pre-command state in 100% of test cases. | Pre-flight stress test (protected-branch fixture)               |
| SC-09 | After a forced post-pre-flight commit failure (hook reject), the SaaS event sink has received zero events for the rolled-back transition.                                                                              | Forced-failure test with mocked SaaS sink                       |

---

## Key Entities

- **Coordination branch** (`kitty/mission-<slug>-<mid8>`) — per-mission branch that owns mission-wide bookkeeping. Created at `mission create`. Parent of every lane branch for that mission. Merged to canonical target at mission close. Deleted on `--discard`.
- **Lane branch** (`kitty/mission-<slug>-<mid8>-lane-<id>`) — per-lane branch parented on the coordination branch. Owns lane code work. Auto-rebases from coordination at claim/start and `for_review → in_review`.
- **Event log** (`status.events.jsonl`) — append-only JSONL file. Lives on the coordination branch (not on individual lanes). Sole authority for WP lane state (per 3.0 status model).
- **Tracking commit** — bookkeeping commit produced by spec-kitty itself to record a lane transition (e.g. `chore: Start WP01 implementation [claude]`). Target: coordination branch.
- **Planning-artifact commit** — bookkeeping commit produced during implement/review to record planning artifacts (`decisions/index.json`, `issue-matrix.md`). Target: coordination branch.
- **Pre-emit size** — byte length of `status.events.jsonl` immediately before an event line is appended. Captured in memory for the duration of the emit attempt; used by the surgical rollback path on commit failure.
- **Rebase sync point** — a moment at which a lane branch is automatically rebased from the coordination branch. Exactly two per lane lifecycle (lane claim/start; first `for_review → in_review`).
- **Workflow-mutation policy gate** — pre-flight check invoked before the first workflow write of every transactional command path. Asks the git-policy layer: "would the corresponding tracking commit be permitted?" Refusal short-circuits the operation before any write happens. Single chokepoint for protected-branch refusal across `implement`, `review`, and `finalize-tasks`.
- **Transactional command path** — a command (`agent action implement`, `agent action review`, `agent mission finalize-tasks`) whose semantics require all writes to be atomically committed. Out-of-scope: read-only command paths (`status`, `dashboard`, `decision verify`).
- **Outbound side effect** — work performed against an external system during a transactional command path (SaaS event sync, decision-thread fanout to a tracker, dossier ingress). Deferred until the corresponding local commit succeeds.

---

## Domain Language

| Canonical term            | Avoid                                | Why                                                                                                |
| ------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------- |
| coordination branch       | "mission branch", "main mission"     | "mission branch" is ambiguous (could mean any branch related to the mission); "coordination" names its role. |
| lane branch               | "WP branch", "worktree branch"       | WPs and lanes are not 1:1 (a lane can hold multiple WPs).                                          |
| canonical target branch   | "main"                               | The target branch is project-configurable; `main` is just the most common value.                   |
| tracking commit           | "status commit", "transition commit" | "status commit" historically referred to `status.json` writes; "tracking" matches the existing CLI verb. |
| pre-emit size             | "rollback offset", "save point"      | "Pre-emit size" names exactly what the value is (file byte length before the append).             |
| surgical rollback         | "rollback", "undo", "checkout"       | Distinguishes the targeted truncate-by-offset approach from `git checkout --` (explicitly banned per C-009). |
| sync point                | "rebase", "pull", "merge"            | A sync point is the *moment* a lane rebases — not the rebase itself.                              |
| workflow-mutation policy gate | "guard", "lock", "check"        | "Guard" already refers to the protected-branch check in `commit_helpers.py`. The gate *wraps* the guard at every workflow call site; it is not the guard itself. |
| transactional command path | "command", "operation"             | Many CLI commands are read-only and not bound by the gate. Naming the class avoids over-applying the invariant. |

---

## Assumptions

1. **No remote push for coordination/lane branches** is required by this mission. The branches remain local until the mission merges. (Operators who want to push are not blocked, but tooling does not push automatically.)
2. **In-flight missions at rollout use the legacy topology**. The new topology applies to missions created after rollout. Migration is opt-in (run `mission close --discard` and recreate, or wait for the mission to finish under the legacy topology).
3. **Coordination branch is created locally by `mission create`**. No PR is opened against the coordination branch automatically; that is the operator's choice.
4. **Rebase implementation may use stock `git rebase` or a custom merge driver** for `status.events.jsonl`. The choice is deferred to `/spec-kitty.plan`; this spec only requires that the rebase succeeds without manual conflict resolution in the happy path.
5. **The protected-branch list and detection logic in `commit_helpers.py` are unchanged**. This mission tightens the guard's exception list, not the guard's detection.
6. **`os.truncate` is portable** on all platforms spec-kitty targets (per DIR-001: Linux, macOS, Windows 10+).
7. **Issue #1348's stated acceptance criteria are fully addressed by this spec** and require no additional sub-features. (See SC-06 for the explicit regression check.)
8. **The bulk-edit gate does not apply**: this mission introduces new behavior + bug fix; it does not rename existing identifiers across files.
9. **The policy-gate abstraction is new code, not a rename.** Existing call sites (planning-artifact emit in `implement.py`, lifecycle writes in `agent/workflow.py`) gain a single new precondition call; their internal logic is otherwise unchanged. The git-policy layer they delegate to is the existing `commit_helpers.py` protected-branch check.

---

## Out of Scope

- True architectural atomicity (build event in memory, stage with `git hash-object` + `git update-index --add --cacheinfo`, commit, then persist to working tree). Explicitly deferred as too large for this mission; surgical truncate-on-failure is the chosen pragmatic approach.
- A custom git merge driver registered globally for `status.events.jsonl` line-append conflicts. May be added as a `/plan` implementation choice if stock `git rebase` is insufficient, but is not an FR of this mission.
- Auto-pushing coordination/lane branches to a remote.
- Automatic migration of in-flight missions onto the new topology.
- Changes to the protected-branch detection list itself (which branches count as "protected"). Only the exception list within that guard changes.
- Changes to mission identity (`mission_id` / `mid8` / `mission_slug` / `mission_number`) — that model is settled by mission 083 and is preserved unchanged here.

---

## References

- **Source issue**: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348) — protected-branch guard bypass inconsistency and dangling event-log writes.
- **Identity model (prior mission)**: `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md` — establishes `mission_id` / `mid8` as canonical identity; this mission preserves that contract.
- **Status model**: `src/specify_cli/status/` and `kitty-specs/034-feature-status-state-model-remediation/` — the event log as sole authority for WP lane state. This mission keeps that invariant; the coordination branch becomes the canonical place where the event log lives.
- **Commit helpers**: `src/specify_cli/git/commit_helpers.py:439` — the protected-branch guard (`safe_commit()` precondition). Confirmed by cross-review: the guard itself is correct; the bugs are at the *call sites* that bypass it.
- **Cross-review file/line evidence** (independent investigation):
  - `src/specify_cli/cli/commands/implement.py:236` — raw `git add` / `git commit` for planning artifacts, bypasses `safe_commit()`. Target of FR-001 / FR-013 / FR-020.
  - `src/specify_cli/cli/commands/agent/workflow.py:689` and `:1463` — lifecycle status writes occur *before* `safe_commit()` is called. Target of FR-009 / FR-010 / FR-019 / FR-021.
  - `src/specify_cli/status/emit.py:468` — event append and `status.json` re-materialization happen before commit policy runs. Target of FR-009 / FR-010 / FR-019.
  - `src/specify_cli/cli/commands/agent/mission.py:321` — returns the current checkout branch, causing `_resolve_planning_branch()` to leak prep branches into WP frontmatter. Target of FR-012.
- **Charter directives in scope**: DIRECTIVE_003 (Decision Documentation), DIRECTIVE_010 (Specification Fidelity), DIR-010 / DIR-011 (ASCII-only identifier sanitization).
