# Phase 1 Data Model: Specify on Protected Primary + Branch-Protection Config

The mission introduces one new value object and reuses one existing one. No persistence schema
changes (the coordination worktree is materialized on disk via the existing seam).

## ProtectionPolicy (NEW — value object)

A standalone, frozen, boundary-resolved value carrying the resolved protection decision inputs.

| Field | Type | Meaning |
|-------|------|---------|
| `protected_branches` | `frozenset[str]` | Resolved set: `.kittify` config if present, else default `{main, master}` (+ remote-default augmentation on the default path only). Empty config ⇒ empty set (nothing protected). |
| `operator_hatch_active` | `bool` | Resolved `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` state, resolved once at the boundary (FR-006). |

**Behavior**

| Method | Signature | Rule |
|--------|-----------|------|
| `resolve` | `classmethod resolve(repo_root: Path) -> ProtectionPolicy` | THE single sanctioned producer. Reads `.kittify/config.yaml` (via the existing loader pattern) + name default + remote default + hatch env. The only place that touches git/fs for the protection set (NFR-003). |
| `is_protected` | `is_protected(ref: str) -> bool` | `ref in protected_branches and not operator_hatch_active`. Folds the duplicated `not hatch and ref in protected` idiom (≈3 sites). |

**Invariants**
- Frozen / immutable; constructed once per command entrypoint; no post-build mutation (C-003).
- `resolve()` performs all I/O; consumers performing protection decisions do **no** further git/fs
  reads for the set (NFR-003).
- Absent config ⇒ `{main, master}` (+ remote default) byte-identical to today (NFR-004).
- Explicit empty config ⇒ empty set (US2 edge case — NOT a silent fallback to default).

## ProtectionState (EXISTING — reused, unchanged)

`core/commit_guard.py` — the pure decision input already consumed by `evaluate(target, ProtectionState, capability)`.

| Field | Type | Meaning |
|-------|------|---------|
| `is_protected` | `bool` | Whether the target ref is protected. Now sourced from `ProtectionPolicy.is_protected(ref)` at the boundary instead of an inline `protected_branches(repo_root)` read. |

The decision function `commit_guard.evaluate(...)` is **not modified** — only its input provenance moves
to the boundary.

## CoordinationWorkspace (EXISTING — reused, unchanged)

`coordination/workspace.py` — `resolve(repo_root, mission_dir_name, mid8) -> Path` materializes the
`.worktrees/<slug>-<mid8>-coord/` worktree on demand and returns its path. Reused at the spec-commit
boundary (pillar A); not modified.

## .kittify protected-branch configuration (NEW — additive config)

A top-level `protection:` block in `.kittify/config.yaml`. See `contracts/protection-config.md` for the
full schema. Read only through `ProtectionPolicy.resolve`.

## Decision flow (resolved)

```
command entrypoint (e.g. safe_commit_cmd)
  └─ repo_root known
       └─ ProtectionPolicy.resolve(repo_root)        # boundary: 1 read, frozen result
            └─ policy.is_protected(destination_ref)  # 0 further reads
                 ├─ protected   → materialize coord worktree (CoordinationWorkspace.resolve) → commit there
                 └─ unprotected → commit directly on target (runbook behavior)
       └─ ProtectionState(is_protected=...) → commit_guard.evaluate(...)   # existing decision, unchanged
```
