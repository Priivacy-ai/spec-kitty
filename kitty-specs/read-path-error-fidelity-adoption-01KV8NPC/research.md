# Phase 0 Research — Read-Path / Error-Fidelity Adoption

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC` · HEAD `87697e5e4`
**Basis documents** (the normative Phase-0 evidence):
- `research/call-site-inventory.md` — architect-alphonso: the exact call-site/bypass inventory, the
  7-IC no-overlap partition, the #1993/#1716 sizing, and line-number drift corrections.
- `research/live-repro.md` — debugger-debbie: live reproduction of every pinned bug on HEAD, the
  #1827 verdict, and the regression-test topology each fix requires.
- `research/priti-related-issues-sweep.md` — planner-priti: net-new related issues (6 FOLD-IN).

This file synthesizes the resolved decisions; the basis docs hold the cited detail.

## What the research changed about the spec

1. **#1827 does NOT reproduce on HEAD** (debbie). The record→commit→assert sequence plus the
   resume/re-run circular trigger PASSED; a falsification guard reproduced the exact error string only
   under the *broken* ordering. **FR-012 → verified-already-fixed: write a full-sequence regression
   test (incl. resume), NO code fix.**
2. **#8 mechanism corrected** (debbie). The live symptom is NOT the "escape kitty-specs" rejection — it
   is an **uncaught `ActionContextError` printed as a raw traceback**, because `decision.py:103` calls
   the resolver *before* the escape-check is reached. The fix still deletes the escape-walk for
   resolved paths (alphonso), and additionally must not let the typed error surface as a traceback.
3. **FR-006 is PARTIAL** (debbie). The hard-failure swallow in `_commit_to_branch` is already fixed;
   the residual is that the function returns `None` and never reports a commit hash / no-op paths emit
   no typed `commit_created`. Narrow FR-006 to "report the real hash + distinguish genuine-unchanged
   from no-op-against-wrong-surface", not "stop swallowing hard failures".
4. **FR-009 wording corrected** (alphonso §7). The spec's `branch_name ≠ branch_ref.target_branch`
   conflates two fields — `branch_name` is the **WP lane branch** (expected to differ). The real
   residual is `ExecutionContext` **mutability** + a post-freeze substrate write; the invariant to
   enforce is `context.target_branch == branch_ref.target_branch` (already equal at build). Harden by
   **freezing the composite + reject-on-mismatch**, NOT normalize.
5. **Typed-error fidelity loss is exactly THREE catch-sites**, all `next`-family
   (`runtime_bridge.py:3128-3130`, `:3265-3274`, `next_cmd.py:355-361`); `agent context resolve`
   (`context.py:158`) already preserves `.code` — copy it. Closes #12/#14/#15 with **zero resolver change**.
6. **Submodule root (#6/FR-007):** the live `assert_initialized` guard calls the BROKEN
   `resolve_canonical_root` (not the patched `locate_project_root`), so #1944/#1965 never covered #6.
   Fix harmonizes the two resolvers — no new authority.

## Resolved decisions

- **D-1 (decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`, C-005 scope):** **DEFER #1716 entirely** — ~2094 LOC
  write-side topology surface; no slice is required for read-path behavioral-equivalence (every FR is
  achievable read-side per inventory §8); carrying violates C-001 and explodes the NFR-005 conflict
  surface. Stays on the #1878 strangler. **CARRY #1993 minimal** — extract the ~20 LOC
  `resolve_lanes_dir` pure seam and route the 2-3 ad-hoc `feature_dir/lanes.json` derivations, owned by
  IC-E alongside #1832 (satisfies the "must not land alone" co-dependency). LOW risk.
- **D-2 (FR-009 rule):** **reject-on-mismatch + freeze the composite** (assert
  `context.target_branch == branch_ref.target_branch` at build, raise `CONTEXT_INVARIANT_VIOLATION`
  otherwise). Do NOT normalize (would hide a builder bug); do NOT retire the flat substrate (a larger
  #1619 grain, stays deferred).

## Testing approach (binding)

- **Function-over-form + verification-by-deletion**: behavioral tests detached from structure; the
  proof of adoption is deleting the bypass/shadow paths and the behavioral suite staying green. No new
  form-coupled test (the naming ratchet is the prior mission's and is out of scope).
- **TDD-first** for every behavioral fix that reproduces on HEAD (#15, #8, #7, #4, #6) — the live-repro
  topology in `live-repro.md` is the fixture each test must build.
- **Topology-true fixtures (NFR-002)**: full 26-char ULID `mission_id`; REAL coord-worktree and REAL
  git-submodule topology — no fabricated short ids, no single-repo stand-in for the submodule/coord cases.
- **#1827** is the one test-only item: a full record→commit→assert + resume regression test, no fix.
