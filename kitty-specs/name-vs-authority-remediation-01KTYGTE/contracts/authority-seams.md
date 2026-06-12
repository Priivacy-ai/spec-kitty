# Contracts — authority seams + gates (01KTYGTE)

## C-SEAM-1 (topology)
All "is this a coord worktree / what surface am I on" decisions route through
`classify_worktree_topology`/`is_registered_coord_worktree`. Path-shape predicates (`-coord` suffix,
`".worktrees" in parts`) are legal ONLY inside the seam module. Name proposes; the git registry disposes.

## C-SEAM-2 (branch identity)
All mission-branch name COMPOSITION outside `lanes/branch_naming.py` and all shape-DECOMPOSITION anywhere
are prohibited. Consumers call the grammar fed by `mission_id` from meta. Dual-era resolution (binding):
legacy and mid8-era both resolve; unresolvable-modern → `BranchIdentityUnresolved` (structured), never a
fabricated/empty mid8.

## C-GATE-1 (verifier-writer authority parity, FR-001)
Any gate that verifies an artifact's committed-ness MUST read via the same `resolve_*` authority the
writing path uses. Pattern: `git cat-file -e <authority.ref>:<rel>`.

## C-GATE-2 (accept idempotency, FR-002)
`spec-kitty accept` re-run on an unchanged tree converges in every mode; accept-owned writes never trip
the gate's own dirty check.

## C-RATCHET (FR-009) — tests/architectural/test_topology_resolution_boundary.py
1. AST/grep: coord-predicate idioms allowlisted to {surface_resolver.py} (+ named test fixtures).
2. AST: `f"kitty/mission-{...}"`-class composes outside branch_naming = failure.
3. Zero occurrences of the `+"00000000")[:8]` fabrication idiom in src/.
Strictness: each assertion proven by a temporary rogue injection that FAILS the test, then reverted.

## C-ERR-1 (FR-003/FR-008)
New error surfaces are StructuredError subclasses with stable error_code + actionable next_step; no
silent stubs (mission=unknown/reason=None class prohibited).
