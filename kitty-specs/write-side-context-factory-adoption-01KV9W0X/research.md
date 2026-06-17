# Phase 0 Research — Write-Side Context-Factory Adoption (Mission B)

**Basis documents** (normative Phase-0 evidence, verified on HEAD `efb28158f`):
- `research/write-site-inventory.md` — architect-alphonso: the exact write-site inventory classified by
  artifact family (C-007), the Q3 pivotal verdict, the C-003 sizing, the #2016 fold, the 7-WP partition.
- `research/reduction-census.md` — randy-reducer: the re-verified write-path census, 0→load-bearing
  confirmation, reduction LOC, verification-by-deletion list, fragment-retirement targets, and the
  idempotency-divergence finding.
- Carried from Mission A: `docs/engineering_notes/context-factory-readwrite-symmetry/00-SYNTHESIS.md` +
  `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/investigation-3-readwrite/`.

## Resolved questions

1. **Q3 — do the write-half fragment fields exist + resolve correctly? YES (pure consumer-routing).**
   `workspace.primary_root` (`context.py:144`/`resolution.py:698`), `status_surface.status_write_dir`
   (`context.py:162`/`resolution.py:724-728` → `resolve_status_surface`, the coord-aware fail-closed
   authority — routes to **status/coord, NOT primary_root**, C-007-correct), `branch_ref.destination_ref`
   (`context.py:130`/`resolution.py:705-722`). The factory needs **no completion**; the only
   `mission_runtime/` touch is FR-006 deletion. C-001 honored.

2. **C-003 scope → Option A (bounded), ~90–130 LOC.** R1–R5 root walks + P1 placement + S1 surface +
   FR-006 retirement. The S2 write-surface-SELECTION ladder (the #1716 ~2094-LOC authority root) computes
   the same value the factory already does → cleanly deferrable (reduction-not-symmetry).

3. **FR-004 (write-target) DEFERS — the one idempotency divergence (D-2).** The flattened-arm
   `destination_ref` (= `target_branch`, CWD-invariant) vs the inline `_current_branch(repo_root)` (= git
   HEAD) diverge on off-target-branch topology — a latent-bug-fix that CHANGES the on-disk write target,
   violating NFR-004 for the bounded cut. Deferred to the #1716 slice with before/after verification. All
   bounded-cut sites resolve a root/anchor (flip no destination) → NFR-004 clean.

4. **#2016 → cross-ref, not fold.** Read-path bootstrap already fixed by Mission A WP09 (`d4f0cf581`).

5. **0→load-bearing (SC-002):** all four targets (`primary_root`, `status_write_dir`, `destination_ref`,
   `prompt_source`) have **zero live consumers** today (grep-proven) — adoption flips them load-bearing;
   `prompt_source` + the dead `surface=` param are retired (FR-006).

## Decisions of record

- **D-1 (C-003 scope, decision `01KV9WY760JEXVEQ4KXF7F2VSB`):** Option A bounded; defer S2/#1716.
- **D-2 (FR-004 idempotency defer):** write-target → #1716 slice (NFR-004 binding).
- **D-3 (#2016):** cross-ref (Mission A WP09).
- **D-4 (W9/W10):** route both to `primary_root` = the consolidation.
- **D-5 (NFR-001 gate):** topology-true root+surface equivalence test in the bounded cut; target equivalence
  is the precondition for the deferred FR-004 flip.

## Testing approach (binding)

Function-over-form + verification-by-deletion (delete the inline re-derivations; green suite + the
previously-0-reader fragments now exercised = the proof). TDD-first. Topology-true fixtures (full 26-char
ULID, real coord-worktree + real submodule). Idempotency-preserving (NFR-004 — before/after on-disk
topology identical for the bounded cut). ruff/mypy clean, ≤15, no suppressions.
