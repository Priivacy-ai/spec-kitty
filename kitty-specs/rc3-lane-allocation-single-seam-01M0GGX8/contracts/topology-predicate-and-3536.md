# Contract — Authoritative topology predicate (WP1, #3460) + #3536 refusal (WP5)

## Part A — Authoritative topology predicate (WP1, FR-004, #3460)

**Authority:** `_transaction_topology_available(identity, mission_slug)`
(`src/specify_cli/coordination/status_transition.py:142`). Already gates the transactional emit/batch
paths (`:1008`, `:1114`, `:1319`, `:1538`).

**Explicitly EXCLUDED (do NOT touch):** `emit_inner_state_changed_transactional` (`:1481`) keeps its bare
`coordination_branch is None` check. Its docstring (`~:1428-1438`) records that reusing the authority
regresses #2939 (`test_flat_topology_annotation_still_lands`) because the predicate's legacy-meta fallback
arm is trivially true for coord-less 083+ missions. This is the CORRECT narrower predicate for the
off-axis annotation path. A WP1 test pins this exclusion so a future "cleanup" cannot re-break #2939.

**Residual census (the actual WP1 work):** classify each site below as a surrogate GATE (route through the
authority) or a legitimate VALUE READ (leave, it reads the branch name, not topology availability):

| Site | Current use | Verdict (to confirm at implement) |
|------|-------------|-----------------------------------|
| `mission_runtime/resolution.py:1284` | `not routes_through_coordination(topology) or coordination_branch is None` | likely legitimate (guards a coord-only branch by value) — confirm |
| `mission_runtime/resolution.py:1362` | `if coordination_branch is not None:` | likely value read — confirm |
| `mission_runtime/resolution.py:1460` | `... and coordination_branch is not None` | likely value read — confirm |
| `mission_runtime/context.py:70` | `has_coord = coordination_branch is not None` | value read (derives a flag) — confirm leave |
| `coordination/surface_resolver.py:104/620/709` | documented as retired/not-re-inferred | already correct — confirm |

**Census result (post-plan squad, reviewer + debugger VERIFIED):** all four residual sites are legitimate
value-reads / already-SSOT-gated (`resolution.py:1284` gated on stored-topology SSOT; `:1362` derives a
worktree path from the branch name; `:1460` gated on `routes_through_coordination` + comment "single
predicate, never re-derived per-ref"; `context.py:70` is inside `classify_topology`, i.e. the classifier
itself). **Zero surrogate GATEs remain to remove.** WP1 is therefore an enforcement/anti-divergence
deliverable, not a code change.

**Deliverable:** a WP1 test (`test_topology_predicate_is_single_authority`, in
`tests/specify_cli/coordination/`) asserting the transactional routing paths consult
`_transaction_topology_available` and NOT a bare surrogate. **Red-first is proven against a deliberately-
introduced temporary surrogate gate** (post-plan squad, reviewer MED — C-011: an invariant that already
holds needs a synthetic-red anchor, mirroring the anti-bypass guard's fixture technique): a synthetic
function/AST fixture that gates on `coordination_branch is None` in a routing position is asserted to be
flagged, then the live code is asserted clean. A companion test pins the emit-annotation **exclusion**
(`status_transition.py` off-axis path keeps the bare check) so a future "cleanup" cannot re-break #2939.

**Honesty of #3460 closure (post-plan squad, reviewer MED):** close #3460 as *"topology-availability is a
single authority (`_transaction_topology_available`), already consulted by the transactional routing gates
on `main`; pinned by an anti-divergence guard"* — NOT *"removed surrogate gates"* (nothing is removed;
that phrasing would dishonestly credit M8 for main's existing state). FR-004 wording is corrected to match.

## Part B — #3536 no-coord refusal (WP5, FR-005)

**Site:** `src/specify_cli/coordination/policy.py:225-236` — the `PROTECTED_BRANCH_REFUSED` `Refused(...)`.

**Current (broken) remedy:** message "Bookkeeping commits must target the coordination branch" +
next_step "Re-run the command through the coordination transaction; the coord worktree is auto-resolved."
On a `lanes`/`single-branch` topology NO coord branch is minted → the remedy is un-followable.

**Fix contract:**
- `commit_guard.evaluate` stays ref-only / environment-free (C-GUARD-3a) — unchanged.
- Coord-availability (a topology fact, from the authoritative predicate / `coordination_branch` presence)
  is threaded into the `Refused` construction so the remedy branches:
  - **coord-available topology** → keep the current "re-run through the coordination transaction" remedy.
  - **no-coord topology** (`lanes` / `single_branch`) → an accurate, followable remedy: either the real
    destination the bookkeeping should use, or "declare the target branch unprotected for this repo"
    (the existing operator escape hatch on `ProtectionState`), never the impossible coord-branch instruction.
- **Cross-reference epic #2739** (same protected-primary seam): the no-coord answer WP5 emits MUST be the
  one #2739's sub-issues consume, so the two protected-primary fixes converge rather than diverge. Note
  the coupling in the PR body.

**Invariants pinned by tests (red-first):**
- INV-3536-1: a `lanes`/`single_branch` mission with a protected `target_branch` hitting the refusal gets
  a remedy that does NOT mention "the coordination branch" and IS followable (names a real action).
- INV-3536-2: a coord-topology mission's refusal remedy is UNCHANGED (regression guard).
- INV-3536-3 (#2739 convergence): the no-coord answer is exposed via the shared predicate, not minted
  locally in `policy.py`.
