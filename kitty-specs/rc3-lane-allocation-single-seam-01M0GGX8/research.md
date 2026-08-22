# Phase 0 Research — M8 Lane-allocation single-seam

All decisions re-verified against `main` (== `upstream/main`, 0/0) on 2026-08-22. M1 (`4dab528545`,
#3571) + #3618 are landed. No new dependency is introduced → supply-chain adversarial pass N/A.

> **Honest scope (post-plan squad, stated plainly).** M8 is a **consolidation / anti-divergence
> refactor plus one user-facing fix**, NOT a reproduction of #3571 (M1 already closed the live P0). The
> #3571 behavioral guard is M1's green `test_explicit_base_replaces_coord_parent_on_no_dep_lane` — M8
> keeps it. Net-new *behavior* concentrates in **WP5 (#3536)**, the only site carrying a live user-facing
> defect. WP1 (#3460), FR-002, and much of WP4 are already satisfied on `main`; M8's value there is
> **enforceability** (the seam + the anti-bypass/anti-divergence guards), not new behavior. Issue-closure
> text must credit M8 only for the guard/consolidation, NOT for M1/#3618/prior-WP05 work.

## D1 — Seam shape: mirror the write-side precedent

- **Decision:** `resolve_lane_base_or_refuse(...) -> LaneBaseDecision`, one resolver every allocation
  route calls. Mirror `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)`
  (`src/mission_runtime/write_target_degrade.py:67`): resolution attempted first, caller-chosen
  fail-open vs fail-closed, structured return.
- **Rationale:** the write side already proves the contract in production with 4 consumers; reusing its
  shape makes "input reaches its consumer via one seam, not a mutated proxy" a structural invariant, not
  a convention. The three sibling seams form one **fail-loud family** that differ in failure mode, NOT a
  uniform "degrade family" (post-plan squad, architect HIGH): **write/read** offer fail-open **degrade**
  and fail-closed **refuse**; **allocate is refuse-only** (honor `base`, or raise `UnhonorableBaseError`
  — it never degrades to the topology parent, because that silent fallback is exactly #3571). The seam is
  therefore named `resolve_lane_base_or_refuse` (NOT `_or_degrade`, which would re-teach the retired bypass).
- **Alternatives rejected:** (a) leave M1's two helpers (`_guard_base_honorable` + `_resolve_lane_parent`)
  separate — rejected: two decision points is exactly the split-route hazard the mission exists to close;
  (b) a brand-new bespoke contract — rejected: violates canonical-sources doctrine and diverges vocabulary.

## D2 — `LaneBaseDecision` carries the honored flag + refusal reason (fail-loud in the type)

- **Decision:** the value object returns `parent_ref: str` and `base_honored: bool` only. **Refusal is
  represented ONLY by raising `UnhonorableBaseError`** (M1's landed typed error) — there is NO `refusal`
  field (post-plan squad, architect MED: a returned refusal field would be structurally unreachable since
  unhonorable routes raise before returning). The *exception* is the fail-loud mechanism.
- **Rationale:** #3571's signature is a *fabricated success line*. Raising (not returning a soft failure)
  on an unhonorable route makes a silent drop unrepresentable — the caller cannot print success. Note:
  `base_honored` is near-redundant with `base is None` (since unhonorable routes raise); it is retained
  for logging / the anti-bypass guard's assertions, NOT as the anti-drop guarantee (that is the raise).
- **Alternatives rejected:** returning a bare ref string (M1's `_resolve_lane_parent` shape) — rejected:
  loses the honored signal at the type boundary. A returned `refusal` field — rejected: unreachable/dead.

## D3 — #3460 is residual-only; the emit site is deliberately excluded

- **Decision:** WP1 does **not** touch `emit_inner_state_changed_transactional`
  (`status_transition.py:1481`). It censuses the residual `coordination_branch is (not) None` sites in
  `mission_runtime/resolution.py` (`:1284`, `:1362`, `:1460`) and `context.py:70`, classifies each as a
  surrogate **gate** (fix → route through `_transaction_topology_available`) or a legitimate **value read**
  (leave), fixes only genuine gates, and adds an anti-divergence test.
- **Rationale:** the emit site's docstring (`~:1428-1438`) records that reusing the authority
  "was tried and reverted" because its legacy-meta fallback arm is trivially true for coord-less 083+
  missions, regressing #2939 (`test_flat_topology_annotation_still_lands`). The spec's headline framing
  is stale; the authority already gates the transactional emit/batch paths (`:1008/:1114/:1319/:1538`).
- **Alternatives rejected:** blanket-swap every `coordination_branch is None` — rejected: regresses #2939
  and conflates the off-axis annotation predicate with topology availability.
- **Contested-finding disposition (adversarial):** "WP1 is now empty" → **changed** — WP1 re-scopes from
  "swap the gate" to "prove the authority is single + close residual gates + anti-divergence test". The
  squad's census (all 4 residual sites — `resolution.py:1284/1362/1460`, `context.py:70`) found them all
  legitimate value-reads / already-SSOT-gated, so **zero surrogate GATEs remain**. WP1 therefore ships the
  anti-divergence test as its deliverable, proven **red-first against a deliberately-introduced temporary
  surrogate gate** (same synthetic-red technique as the anti-bypass guard, D6) so C-011 is honored even
  when the invariant already holds on `main`. FR-004 wording and #3460's closure text are corrected to
  "single-authority **pinned by** the anti-divergence guard" — NOT "removed surrogate gates" (nothing is
  removed; the counterfactual "removed" phrasing would dishonestly credit M8 for main's existing state).

## D4 — #3462 read companion preserves per-caller fallback contracts

- **Decision:** `resolve_read_dir_or_degrade` is parameterized on (a) fallback **strategy**
  (degrade-to-`feature_dir` / degrade-to-`primary_feature_dir` / zero-evidence sentinel / fail-closed)
  and (b) the caught-**exception set**. It never collapses distinct contracts into one hardcoded
  try/except. The #1848 data-loss re-raise (`status/aggregate.py:351`, `CoordinationBranchDeleted`
  propagates verbatim) is preserved by declaring that site's exception set to exclude the subclass.
- **Rationale:** the read side already converged on typed errors (`CoordinationBranchDeleted` /
  `StatusReadPathNotFound` / `CoordAuthorityUnavailable`) via a prior WP05/T023–T025 mission; the gap is
  the *hand-rolled* try/except shape, not the error vocabulary. A design pass, not a mechanical dedup.
- **Alternatives rejected:** one fixed try/except body — rejected: would swallow the #1848 data-loss
  verdict, the exact contract US-4.2 forbids collapsing.

## D5 — #3536 threads topology into the refusal remedy

- **Decision:** keep `commit_guard.evaluate` ref-only/env-free (C-GUARD-3a). Thread coord-availability
  (from the authoritative predicate) into the `Refused` construction at `policy.py:225-236` so the remedy
  branches: coord-available → "re-run through the coordination transaction"; no-coord (lanes/single-branch)
  → an accurate remedy (declare the target unprotected for this repo, or the real destination), never the
  impossible "target the coordination branch".
- **Rationale:** the message must be followable. The topology fact lives outside the ref-only guard, so it
  is supplied at the refusal-construction site, not inside `evaluate`.
- **Cross-reference:** epic #2739 (same protected-primary seam). Ensure the unified predicate's no-coord
  answer is the one #2739's sub-issues consume, so the two fixes converge.
- **Alternatives rejected:** making `evaluate` topology-aware — rejected: breaks C-GUARD-3a's ref-only
  contract and the single protection authority.

## D6 — Anti-bypass guard is an architectural test (FR-007)

- **Decision:** a `tests/architectural/` test asserts every allocation/degrade route computes its parent
  ref via the seam, not inline. Implementation: AST/source scan of `worktree_allocator.py` (and the
  read/degrade family) for inline parent-ref computation outside the seam, naming the offending site.
- **Rationale:** the recurrence guard must fail in CI when a *future* route bypasses the seam — a
  convention comment cannot enforce that. Mirrors existing architectural guards (e.g.
  `test_shared_package_boundary.py`).
- **Alternatives rejected:** runtime assertion only — rejected: a new bypassing route that is never
  exercised at runtime would pass; the guard must be static/structural.

## Guardrails to keep green (targeted regression, not full suite)

#2993 reuse self-heal · #2512/#2514 crash-recovery + sparse-checkout · #1684 dependency-tip propagation ·
#1915 atomic dep-merge rollback · #2939 flat-topology annotation · #1848 data-loss re-raise.
Full ~1h suite is CI's authority; locally run targeted cells (full suite breaks the session; CI is release authority).
