# Quickstart — Verifying the Naming/Identity Routing Rider

Verification is **behavioral (function over form)** plus **verification-by-deletion**, with the
architectural ratchet as the lone form-coupled guard. These are the acceptance checks the WPs must satisfy.

## 1. Behavioral parity (NFR-001 — the routing changes nothing observable)

For existing missions, identity-derived strings are byte-identical before/after the routing:

```bash
PWHEADLESS=1 pytest tests/ -k "branch_naming or mid8 or worktree or lanes or identity" -q
```

- Characterization tests pin the current output of each routed site *before* substitution, then must
  still pass after. Zero diffs in derived branch / worktree / lanes-dir / mid8 strings.
- Preserve exact empty/None contracts (e.g. `status/aggregate.py` returns `""` for a missing id).

## 2. Verification-by-deletion (C-004 — the seam is the ONLY path)

The proof that adoption is real (not a parallel path) is that the shadow implementations can be **deleted**
and the behavioral suite stays green:

```bash
# After IC-02/IC-03 routing: the inline derivations (FR-009) are removed, not just bypassed.
git grep -nE '\b\w*_id\[0?:8\]' src/ | grep -v branch_naming.py | grep -v mission_runtime/context.py
#   → expect ONLY the invocation_id[:8] non-target (Op id), nothing in the mission-identity class.
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
#   → full suite green with the shadow impls gone ⇒ the seam is the sole implementation.
```

## 3. Ratchet tripwire (FR-004 / SC-001 / SC-005 — the regression guard)

```bash
PWHEADLESS=1 pytest tests/architectural/test_no_worktree_name_guess.py -q
```

- Passes with the allow-list **shrunk** (ideally empty for the mission-identity short-id class).
- **Coverage proof (SC-005):** plant `mid8 = mission_id[:8]` in `dashboard/scanner.py` → the ratchet
  FAILS and names the site; revert → passes.
- **Non-target proof:** `invocation_id[:8]` does not trip it (pattern specificity / justified entry).

## 4. Failover entrypoint + #2000 compose-routing (FR-010, FR-005)

```bash
# Correctness/read paths use the failover-aware resolver, not bare mid8():
PWHEADLESS=1 pytest tests/architectural/test_no_worktree_name_guess.py -q
#   → the bypass rule flags bare mid8()/mission_id[:8] on correctness paths.
# #2000 composes route through the seam:
git grep -nE "kitty/mission-\{|\.worktrees/.*\{" src/specify_cli/core/mission_creation.py src/specify_cli/core/worktree.py
#   → expect ZERO hand-rolled composes; both go through mission_dir_name/worktree_dir_name.
```

## 5. #1888 real fix (FR-007) + #1971-tail verify-close (FR-006)

```bash
# #1888 — TDD: the failing repro (validation passes a phantom owned path) precedes the fix:
PWHEADLESS=1 pytest tests/ -k "ownership and (validation or existence or phantom)" -q
# #1971-tail — the regression test DISPROVES the SPECIFY_REPO_ROOT/worktree split-brain the ticket asserts
#   (not just "the three entries exist"); the deferred-import shims are unchanged.
PWHEADLESS=1 pytest tests/ -k "locate_project_root or project_root or repo_root" -q
```

- `#1888` closes **fixed** (existence check added, repro test as evidence) — it was a real bug, not verify-close.
- `#1971-tail` closes **verified** with the split-brain-disproving test.
- `#1993` / `#1900` / `#1899-tail`: recorded **deferred-with-followup → 3.2.2** / **duplicate-of-#2000** — no code here.

## 6. Quality gates (C-006)

```bash
ruff check $(git diff --name-only $(git merge-base HEAD feat/naming-rider-3-2-1) | rg '\.py$')
mypy src/   # zero issues on touched paths; no new # noqa / # type: ignore
```

## Definition of Done (mission)

- [ ] ~15 short-id route-sites consume the **failover-aware entrypoint** (`resolve_mid8`/`resolve_transaction_mid8`); inline derivations deleted (FR-001/003/009/010).
- [ ] Per-site contract table honored — byte-parity at the 5 None/empty/raise-sensitive sites (FR-008, NFR-001).
- [ ] Ratchet has the new AST short-id detector + failover-bypass rule, covers `dashboard/scanner.py`, allow-list shrank, `invocation_id[:8]` not tripped (FR-004/010).
- [ ] IC-05 entrypoint decision settled ((a) formalize+enforce or (b) refactor-to-SSOT) and realized.
- [ ] #2000 composes routed through `mission_dir_name`/`worktree_dir_name` (FR-005).
- [ ] #1888 real existence-check fix landed TDD-first; #1971-tail verified with the split-brain-disproving test (FR-006/007).
- [ ] Full suite green with shadow impls deleted; behavioral parity holds (C-004).
- [ ] ruff + mypy clean, no suppressions (C-006). Issue-matrix verdicts: #2000 fixed · #1971-tail verified · #1888 fixed · #1899-tail dup-of-#2000 · #1900/#1993 deferred→3.2.2 (SC-004).
