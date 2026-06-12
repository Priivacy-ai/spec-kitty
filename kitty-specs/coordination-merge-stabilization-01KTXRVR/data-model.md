# Data Model: Coordination and Merge Stabilization

**Date**: 2026-06-12

This mission introduces no new persistent entities. It hardens the *state model* of existing git-surface entities. The model below names those entities, their states, and the invariants the fixes enforce.

## Entities & States

### CoordinationWorktree

Checkout of `kitty/mission-<slug>` under `.worktrees/<slug>-coord` (canonical path from `CoordinationWorkspace.worktree_path`).

| State | Definition | Legal? |
|---|---|---|
| CONSISTENT | `HEAD` == branch tip; index/working tree clean | ✅ steady state |
| BEHIND_REF | branch advanced by `update-ref` while checked out here; index behind HEAD | ❌ Class B defect state — must be eliminated by resync (FR-001) |
| DIRTY | uncommitted local modifications | ⚠️ design violation during bookkeeping — resync must refuse loudly (NFR-002) |
| MISSING | path absent | ✅ created on first resolve |
| BRANCH_MISMATCH | checked out to a different branch | ❌ existing `CoordinationWorkspaceBranchMismatch` error (unchanged) |

**Transitions enforced by this mission**: `CONSISTENT --update-ref--> BEHIND_REF` is immediately followed by `--resync--> CONSISTENT` inside the same operation (the ref-advance helper); `DIRTY` at resync time → structured refusal (no transition, merge halts resumably).

### LaneWorkspace (ResolvedWorkspace)

Per-lane execution worktree under `.worktrees/<slug>-lane-<id>`.

| State | Definition | Legal? |
|---|---|---|
| REAL_WORKTREE | directory exists AND contains `.git` entry AND `git rev-parse --show-toplevel` == path | ✅ only resolvable state (FR-003) |
| HUSK | directory exists, no `.git` entry | ❌ must resolve as structured failure, never fall through (FR-003/FR-005); doctor lists/removes (FR-007) |
| ABSENT | no directory | ✅ triggers creation; creation failure is a hard error (FR-004) |

**Invariant**: `ResolvedWorkspace.exists ⇒ REAL_WORKTREE`. `ReviewLock` may only be acquired when the workspace is REAL_WORKTREE (lock-after-create ordering, FR-004).

### PrimaryCheckout

The operator's root checkout (here: branch `main`).

**Invariants**: (1) Read-only commands (`finalize-tasks --validate-only`) leave `HEAD`, index, and working tree byte-identical (FR-002). (2) Post-finalize, no untracked planning-artifact residue (`lanes.json`, `tasks/*`, matrices) remains (FR-006) — coordination-owned artifacts live only in the CoordinationWorktree.

### StatusEventLog (`status.events.jsonl`)

Append-only event log; merge driver unions divergent histories.

**Invariants hardened**: deterministic sort under mixed `at` / `timestamp` / absent-timestamp schemas (FR-008c); reads in retrospective gating route through `resolve_status_surface` — never via `resolved.feature_dir` directly (FR-009, AC-A2 ratchet); lane-read fallback-to-GENESIS triggers only on `(ValueError, FileNotFoundError)` (FR-008d).

### CommitTarget (existing, from `resolve_placement_only`)

`(ref, kind ∈ {COORDINATION, FLATTENED, ...})` — the single placement authority (PR #1850). **Unchanged by this mission** (C-001). All new code consults it; none re-derives placement.

## New Error Types (shape only — names finalized in implementation)

| Error | Raised when | Required fields (NFR-003) |
|---|---|---|
| RefAdvanceDirtyWorktreeError (Class B refusal) | resync target worktree has uncommitted state | worktree path, advanced ref, old/new SHA, dirty entries |
| WorkspaceResolutionError (Class D) | resolved path is not a real git worktree | resolved path, expected branch/lane, which check failed (`.git` missing / toplevel mismatch) |
| (existing) SafeCommitBackstopError | unchanged semantics; message now names the divergence cause (FR-012) | worktree, ref, behind/ahead state |

## Relationships

```
PrimaryCheckout 1──1 CoordinationWorktree   (per mission; placement authority: CommitTarget)
CoordinationWorktree 1──* LaneWorkspace     (per lane; created at implement)
CoordinationWorktree 1──1 StatusEventLog    (coordination-owned under coordination topology)
MergePipeline ──advances──> branch refs     (only via the ref-advance helper; AC-B3 ratchet)
```
