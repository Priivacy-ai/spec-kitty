# Data model — name-vs-authority-remediation-01KTYGTE

## 1. WorktreeTopology (new enum, coordination/surface_resolver.py)
`PRIMARY | COORD_WORKTREE | LANE_WORKTREE | UNREGISTERED` — produced ONLY by
`classify_worktree_topology(path, *, repo_root, registry=None)`; the registry param is the injectable
cached `git worktree list --porcelain` parse (exemplar doctor.py:~3063). `is_registered_coord_worktree()`
= convenience predicate over the classifier. No consumer may derive topology from path shape directly
(ratchet-enforced).

## 2. BranchIdentityUnresolved (new structured error, lanes/branch_naming.py)
Carries `error_code="BRANCH_IDENTITY_UNRESOLVED"`, `mission_handle`, `next_step`. Subclasses
`core.errors.StructuredError` (#1893 base). Raised by `mission_branch_name_required(...)` only for
unresolvable-MODERN identities (dual-era rule: legacy `\d{3}-` and mid8-era names both resolve).

## 3. #1889 decision table (NORMATIVE — from research-authority-seams)
| Row | meta.coordination_branch | worktree | branch | Answer |
|-----|--------------------------|----------|--------|--------|
| R1 | declared | materialized (registered) | exists | COORDINATION surface |
| R2 | declared | absent | exists | compose-once coord target, no raise (create-on-write path) |
| R2′ | declared | root exists, mission dir absent | exists | fail closed (StatusReadPathNotFound — existing) |
| R3 | declared | absent | **deleted** | NEW: distinct loud structured error (composes with #1848 status-transition carve-out); never silent primary fallback |
| R4 | undeclared | — | — | PRIMARY surface |
One `git rev-parse --verify` per R3 evaluation accepted.

## 4. Accept-gate ownership model (FR-002)
`ACCEPT_OWNED_PATHS` = the artifact set the accept gate itself writes (acceptance-matrix.json, acceptance
commit bookkeeping, NI verification updates). Invariant: the `git_dirty` snapshot is taken BEFORE any
accept-owned write of the current run AND excludes accept-owned paths dirty from prior runs in
non-committing modes. Convergence property: accept ∘ accept ≡ accept on an unchanged tree.
