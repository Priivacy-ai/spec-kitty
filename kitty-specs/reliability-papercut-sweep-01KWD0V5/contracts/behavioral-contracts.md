# Phase 1 Behavioral Contracts: Reliability Papercut Sweep

These are CLI/runtime behavioral contracts (not HTTP APIs). Each maps to an FR and is the
red-first regression target (NFR-001). "Before" = current main behavior (the bug); "After" =
post-fix contract.

## C-FR-001 — record-analysis dirty-tree gate (IC-01)
- **Given** a working tree whose only dirty path is `kitty-ops/<ulid>.jsonl`
- **When** `record-analysis` runs its dirty-tree preflight
- **Before**: exits `DIRTY_WORKTREE`, listing the orphan in `dirty_paths`.
- **After**: records the analysis; the orphan is excluded as self-bookkeeping.
- **Counter-contract**: a genuine mission-relevant dirty path STILL blocks.

## C-FR-002 — coord classification for a never-created branch (IC-02)
- **Given** a `meta.json` declaring a `coordination_branch` absent from git
- **When** `context resolve` / `doctor topology` / backfill runs
- **Before**: classifies as healthy `coord`; hard-fails `COORDINATION_BRANCH_DELETED`; remediation leads with husk-remove.
- **After**: does not classify as healthy `coord`; remediation leads with "flatten the mission".
- **Invariant**: `classify_topology` itself is unchanged (pure); the boundary caller does the git probe.

## C-FR-003 — doctor coordination recovery hint (IC-03)
- **Given** a missing/stale coordination worktree
- **When** `doctor coordination` emits its recommendation
- **Before**: may recommend a path that doesn't recreate the worktree (recurred #1890 class).
- **After**: every recommended command exists AND performs the stated recovery; a standing test guards the dead-command class; stale-behind-tip worktree is handled.

## C-FR-004 — decision-event canonical ULID (IC-04)
- **Given** a decision logged for a flat/coord-less mission with no explicit `mission_id`
- **When** the decision-event payload is built
- **Before**: persists the slug in the `mission_id` field.
- **After**: persists a real ULID (sourced from meta or minted); fails closed with a structured error if none is available.
- **Test**: `test_slug_fallback_when_no_mission_id` is INVERTED to assert ULID/fail-closed.

## C-FR-005 — target_branch read primitive (IC-05)
- **Given** a `meta.json` that is present but unreadable (corrupt JSON)
- **When** any of the three `target_branch` readers resolves
- **Before**: silently returns the repository default branch (exit 0, no signal).
- **After**: surfaces a structured error (fail closed). A *field-absent* read still returns the documented default.
- **Invariant**: all ~18 existing call sites compile and behave unchanged (thin adapters).

## C-FR-006 — mint-once coordination identity (IC-06)
- **Given** a coordination-branch composition with no resolvable mid8
- **When** the canonical mint boundary runs
- **Before**: composes an empty-mid8 / malformed coordination branch.
- **After**: mints a valid identity once, or fails closed — never persists an empty-mid8 branch.
