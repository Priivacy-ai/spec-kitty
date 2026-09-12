# Contract: Explicit Checkout-Ownership Affordance

**Mission**: `worktree-owned-root-3328-01KZRG01` | **Issue**: [#3328](https://github.com/Priivacy-ai/spec-kitty/issues/3328)

This contract defines the CLI/API surface the implementation phase (WPs) must deliver. It is a specification of observable behavior — exact flag names/wording are implementation-phase decisions the tasks phase may refine, but the request/response shape and refusal taxonomy below are binding.

## CLI Surface: `spec-kitty agent mission create`

### New option

```
--owned-checkout PATH   Explicitly declare PATH as a linked worktree this invocation
                         owns. Validated via git topology (common-dir + worktree
                         registry) before acceptance. Mutually exclusive with running
                         from an unowned worktree without this flag (existing refusal
                         is unchanged when this flag is absent).
```

### Behavior contract

| Precondition | `--owned-checkout` supplied? | Outcome |
|---|---|---|
| CWD is the primary checkout | No | Unchanged — succeeds as today. |
| CWD is the primary checkout | Yes, path == CWD | Succeeds (trivial self-ownership case, mirrors `safe_commit`'s `repo_root == worktree_root` contract). |
| CWD is a linked worktree (any path) | No | Unchanged — refuses with today's `MissionCreationError` ("Cannot create missions from inside a worktree…"). |
| CWD is a linked worktree, path is a validly-linked, non-nested worktree of the resolved primary | Yes, path == CWD | Succeeds. Mission files, coordination/lane refs land under `path`. Primary checkout and every other worktree remain untouched. |
| Path is nested inside another worktree's checkout | Yes | Refuses. Error is structurally distinguishable as `NESTED` (see Error Taxonomy). |
| Path's git common-dir does not match the resolved primary's | Yes | Refuses. Error is structurally distinguishable as `FOREIGN_OR_MISMATCHED`, naming both common-dirs. |
| Path's `.git` file exists but its `gitdir:` target is unreadable/missing | Yes | Refuses. Error is structurally distinguishable as `BROKEN_POINTER`. |
| Any underlying `git rev-parse`/`git worktree list` subprocess fails | Yes | Refuses (fail-closed, NFR-004) — never falls back to unvalidated acceptance. |

### Create-time target-resolution boundary

An accepted `OWNED` claim binds the exact current checkout root; mission
creation's existing logic separately derives the explicit planning branch.
Before any mission metadata exists, and during only this
pre-readable-identity interval, mission creation MUST obtain its commit target
through the canonical `mission_runtime` create-time target seam. The seam:

- accepts an explicit non-empty, short planning-branch name and returns a
  `CommitTarget` for that same branch;
- rejects fully-qualified `refs/heads/...` inputs;
- performs no CWD, environment, topology, mission-directory, or ambient-root
  discovery; and
- is never used by the no-opt-in path or as a replacement for the ordinary
  `placement_seam(...).write_target(...)` behavior after identity is readable.

This prevents the pre-identity create path from silently falling back to the
primary branch while preserving the existing placement authority for every
ordinary mission write.

### `--json` payload shape (success)

```json
{
  "success": true,
  "mission_slug": "...",
  "owned_checkout": "/abs/path/to/worktree",
  "canonical_repo_root": "/abs/path/to/primary",
  ...
}
```

### `--json` payload shape (refusal)

```json
{
  "success": false,
  "error_code": "OWNERSHIP_NESTED" | "OWNERSHIP_FOREIGN" | "OWNERSHIP_BROKEN_POINTER" | "WORKTREE_INVOCATION_REFUSED",
  "error": "<human-readable message naming the specific checkouts/paths involved>"
}
```

`WORKTREE_INVOCATION_REFUSED` is the existing (unchanged) refusal code for the no-opt-in case — this contract does not rename or restructure it (regression risk called out in plan.md IC-04).

## CLI Surface: `spec-kitty next`

### New option

```
--owned-checkout PATH   Same semantics as `mission create`'s flag. When supplied and
                         validated OWNED, `next` roots per-checkout runtime state
                         (feature-runs.json, merge-lock directory) at PATH instead of
                         the ambiently-resolved primary checkout.
```

### Behavior contract

| Precondition | `--owned-checkout` supplied? | Outcome |
|---|---|---|
| CWD is a `.worktrees/<name>` path (today's `require_main_repo` detects this) | No | Unchanged — refuses exactly as today. |
| CWD is a generic linked worktree (today's `require_main_repo` does NOT detect this) | No | Unchanged — behaves exactly as today (ambient resolution to primary; NOT retrofitted into a new refusal — spec.md Acceptance Scenario, User Story 2 #4). |
| CWD is a validly-linked, non-nested worktree | Yes, path == CWD | Succeeds. Mission decision resolves against the mission stored at the owned checkout; runtime-state files (`feature-runs.json` equivalent) are read/written under the owned checkout's own `.kittify/runtime/`. |
| Nested / foreign / broken-pointer (same taxonomy as `mission create`) | Yes | Refuses with the same structured error codes. |

### Owned-root propagation boundary

After `next_cmd.py` validates an `OWNED` claim, its effective checkout root
remains an explicit parameter through the decision and runtime-bridge layers
and into canonical mission-context resolution. The opted-in path must not
recompute this root from CWD and must not fold it through
`get_main_repo_root`; mission content, primary-partition metadata for this
worktree-owned mission, and per-checkout runtime state all resolve from that
same explicit checkout. A mission present only under the linked checkout's
`kitty-specs/` must therefore be queryable and advanceable with
`next --owned-checkout <linked>` from both primary and linked CWD. Omitting the
flag preserves the existing primary-anchor behavior unchanged.

## Error Taxonomy (shared by both surfaces)

| `error_code` | `OwnershipValidationResult` (data-model.md) | Meaning |
|---|---|---|
| `WORKTREE_INVOCATION_REFUSED` | `UNOWNED_NO_OPT_IN` | Existing, unchanged refusal — caller did not opt in. |
| `OWNERSHIP_NESTED` | `NESTED` | The claimed checkout is nested inside another worktree's own directory tree. |
| `OWNERSHIP_FOREIGN` | `FOREIGN_OR_MISMATCHED` | The claimed checkout's git common-dir does not match the resolved primary's. |
| `OWNERSHIP_BROKEN_POINTER` | `BROKEN_POINTER` | The claimed checkout's `.git` gitdir pointer is unreadable, missing its target, or a git subprocess failed while validating it. |

## Non-Goals of This Contract

- Does not define `#3128`'s post-ownership caller-vs-declared-workspace comparison (that guard consumes this contract's validated `OwnershipClaim` as an input, in a separate mission).
- Does not add any new production `allow_worktree_context=True` call site (NFR-003) — `--owned-checkout` is a wholly independent, validated parameter.
- Does not change behavior for any caller that omits `--owned-checkout` (C-001/C-002).
