# Data Model: Worktree-Owned Root for Mission Create/Next

**Mission**: `worktree-owned-root-3328-01KZRG01` | **Issue**: [#3328](https://github.com/Priivacy-ai/spec-kitty/issues/3328)

This mission has no persisted business data model (it is a CLI/runtime-topology fix). This document instead models the **checkout-ownership domain concepts** the implementation must reason about precisely — entities, their attributes, and the relationships/validation rules between them, derived from the code inventory in `research.md`.

## Entities

### `Checkout`

A single git working directory — either the primary checkout or a linked worktree.

| Attribute | Type | Description |
|---|---|---|
| `path` | absolute path | The checkout's working directory root. |
| `git_common_dir` | absolute path | Result of `git rev-parse --git-common-dir` run from `path`, resolved to absolute. Shared by every checkout of the same repository. |
| `toplevel` | absolute path | Result of `git rev-parse --show-toplevel` run from `path`. |
| `is_primary` | bool | True iff `path == git_common_dir.parent` (the checkout that owns `.git` as a real directory, not a `gitdir:` pointer file). |
| `gitdir_pointer_target` | absolute path \| None | For a linked worktree, the target of the `.git` file's `gitdir:` line (e.g. `<primary>/.git/worktrees/<name>`). `None` for the primary checkout. |

**Existing code that computes these attributes** (research D-2, D-4): `is_worktree_context()`, `_is_worktree_of()`, `locate_project_root()`, `resolve_canonical_repo_root()` — each recomputes a subset independently; the plan should route new validation through `_is_worktree_of`'s comparison rather than adding a sixth implementation.

### `OwnershipClaim`

The explicit, per-invocation declaration that a `Checkout` should be treated as the mission's write root.

| Attribute | Type | Description |
|---|---|---|
| `claimed_checkout` | `Checkout` | The checkout the caller has explicitly named (new — does not exist today). |
| `resolved_primary` | `Checkout` | The canonical common-repository checkout, resolved independently of the claim (via the existing `locate_project_root`/`get_main_repo_root` family). |
| `validation_result` | `OwnershipValidationResult` (enum, below) | Outcome of comparing `claimed_checkout` against `resolved_primary`'s topology. |
| `opted_in` | bool | Whether the caller supplied the new explicit-ownership affordance at all. When `False`, today's existing fail-closed default behavior (research D-1) applies unchanged — no `OwnershipClaim` is constructed. |

### `OwnershipValidationResult` (enum)

The five possible validation outcomes (spec.md Key Entities, User Story 2's acceptance scenarios):

| Value | Meaning | Existing precedent |
|---|---|---|
| `OWNED` | `claimed_checkout`'s `git_common_dir` matches `resolved_primary`'s `git_common_dir`, and `claimed_checkout` is not nested inside any other worktree per the registry. Accepted. | `_is_worktree_of()` returning `True`, plus a new nested-worktree negative check (research D-4). |
| `UNOWNED_NO_OPT_IN` | Caller did not supply the ownership affordance; today's existing refusal (mission create) or ambient behavior (next) applies unchanged. | Existing `is_worktree_context()` / `require_main_repo` behavior — UNCHANGED (C-001, FR-004). |
| `NESTED` | `claimed_checkout`'s path is a descendant of another worktree's root per `git worktree list --porcelain`. Refused. | New — built on `coordination/surface_resolver.read_worktree_registry()`'s raw entries (research D-4), not its `.worktrees`-literal `_enclosing_worktree_root()`. |
| `FOREIGN_OR_MISMATCHED` | `claimed_checkout`'s `git_common_dir` does not match `resolved_primary`'s. Refused, common-dir named in the error. | `_is_worktree_of()` returning `False` on a common-dir mismatch. |
| `BROKEN_POINTER` | `claimed_checkout`'s `.git` file exists but its `gitdir:` target is missing/unreadable, or any underlying git subprocess failed. Refused (fail-closed, NFR-004). | New — must not raise an unstructured `KeyError`/`FileNotFoundError`; wrap as a named error. |

### `PerCheckoutRuntimeState`

Runtime bookkeeping that must be rooted under the `OwnershipClaim.claimed_checkout` rather than `resolved_primary` once ownership is `OWNED` (research D-6).

| Attribute | Type | Description |
|---|---|---|
| `feature_runs_path` | path | `<claimed_checkout>/.kittify/runtime/feature-runs.json` (today always `<resolved_primary>/...` — FR-007 fix target). |
| `merge_runtime_dir` | path | `<claimed_checkout>/.kittify/runtime/merge/<mission_id>/` (today always `<resolved_primary>/...`). |

**Explicitly excluded** from this entity (research D-6): the cross-worktree status lock (`status/locking.py`'s `spec-kitty-locks/<mission_slug>.status.lock`) stays rooted at the shared `git_common_dir` by design — it is a different concern (serializing convergent writes to shared planning artifacts, not per-checkout isolation) and is out of scope for relocation.

## Relationships

```
Checkout (1) ──is_common_dir_peer_of──> Checkout (0..N)   [same git_common_dir; e.g. primary + N linked worktrees]
OwnershipClaim ──references── claimed_checkout: Checkout
OwnershipClaim ──references── resolved_primary: Checkout
OwnershipClaim ──produces── validation_result: OwnershipValidationResult
OwnershipClaim (validation_result=OWNED) ──scopes── PerCheckoutRuntimeState
OwnershipClaim (validation_result=OWNED) ──scopes── safe_commit(repo_root=resolved_primary, worktree_root=claimed_checkout)
```

## Validation Rules (drive FR-003/FR-005/FR-006/NFR-004 directly)

1. An `OwnershipClaim` is only constructed when the caller opts in explicitly (`opted_in=True`); absent that, behavior is byte-identical to today (C-001/C-002/FR-004).
2. `resolved_primary` MUST be computed independently of `claimed_checkout` (via the existing ambient-collapse resolvers) — never derived FROM the claim — so a claim cannot self-certify.
3. Common-dir comparison (`OWNED` vs `FOREIGN_OR_MISMATCHED`) MUST use the fail-closed comparator (`_is_worktree_of`'s internal logic: any `None` from a git subprocess call → refuse), never the non-fail-closed `status/locking._git_common_dir` fallback pattern (NFR-004).
4. Nested-worktree detection (`NESTED`) MUST be evaluated using the raw `git worktree list --porcelain` registry entries' paths (ancestor/descendant path comparison), not the `.worktrees`-literal `_enclosing_worktree_root()` helper (C-006).
5. Every non-`OWNED` result MUST raise/return a structurally distinguishable error (FR-011) — not a single generic string match on `"worktree"` (the current UX hint in `mission_create.py:_print_worktree_navigation_hint` string-matches this way and must not be the ONLY signal for the new refusal classes).
6. `PerCheckoutRuntimeState` paths are only used when `validation_result == OWNED`; otherwise runtime state continues to resolve against `resolved_primary` exactly as today.
