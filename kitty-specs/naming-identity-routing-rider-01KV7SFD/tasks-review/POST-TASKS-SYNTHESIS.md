# Post-tasks adversarial synthesis — Naming/Identity Routing Rider

**Date:** 2026-06-16. **Squad:** python-pedro (feasibility/anti-laziness) · paula-patterns (coverage) ·
reviewer-renata (DoD rigor) · architect-alphonso (sequencing/ownership). All opus, profile-loaded.
Verdict: **NEEDS-REMEDIATION** (routing core sound; build-breaker + anti-gaming gaps). All code claims
verified against HEAD before remediating.

## BLOCKER F-1 — orphaned `mid8` importer breaks the build (pedro + paula + alphonso)
`src/specify_cli/lanes/worktree_allocator.py` imports `mid8` (`:28`) and calls it (`:169`) but was in **no
WP**. WP01 renames `mid8`→`_mid8` + de-exports ⇒ **ImportError on load** of the module that **builds every
lane worktree** — breaking the implement loop itself (incl. WP02's 3-lane dependency merge).

**Structural fix = REORDER (demotion lands LAST):** routing targets `resolve_mid8`, which **already exists
and is public** — so the route WPs do NOT need WP01 first. Flip the graph:
```
{WP03, WP04, WP05}  (route external callers → resolve_mid8)  ──►  WP01 (demote mid8→_mid8, de-export; now safe)  ──►  WP02 (ratchet)
WP06, WP07 independent
```
By the time WP01 de-exports `mid8`, every external importer is already migrated. Add
`worktree_allocator.py` to WP03 (contract-sensitive: `try/except ValueError → None`).

## Verified code-truth corrections (pedro, all confirmed)
1. **`worktree_allocator.py:28/169`** — F-1 above. → WP03.
2. **#1888 fix ALREADY LANDED** (`validate_glob_matches`, literal-zero-match hard error,
   `ownership/validation.py:319/375`, commit `991162c0a` — the topology-stabilization mission, *after* the
   scope review). WP06's "write a failing repro" can't fail. **Reframe (operator rule: don't assume
   fixed):** WP06 writes the #1888 repro test FIRST; if it PASSES on HEAD → verify-and-close with that test
   as evidence; if it FAILS → add the missing check. Do not assume either way.
3. **`doctor.py:3066/3158`** already `from …branch_naming import mid8 as _mid8` — WP01's de-export breaks
   these imports. WP03 T007 must repoint them to `resolve_mid8`.
4. **`retrospective_terminus.py:67`** is a **local `def _mid8` shadow** (caller `:137`), not a one-line
   route at `:69`. WP04 must **delete the shadow def** + route its caller(s) to `resolve_mid8`. Harden:
   `grep 'def _mid8' retrospective_terminus.py` returns nothing after.
5. **`retrospective/generator.py:112`** is a **selector prefix-comparison** (`mid[:8] == mission_handle`),
   NOT a name derivation — routing through the failover resolver changes semantics. WP04: evaluate;
   preserve comparison (compute canonical mid8 then compare) OR exclude + allow-list in WP02 with a
   justification (it's mission-resolution prefix-matching).
6. **`mission_type.py:643`** is contract-sensitive (`… else ""`) — handle with `resolve_mid8`'s `""`
   decline contract, not as a naive "direct" route.
7. **WP05 `mission_dir_name(slug, *, mid8: str)`** takes a mid8 **string** — `mission_creation.py` still
   needs `resolve_mid8("", mission_id=…)` to derive it. The call **moves**, it is not "removed."

## F-2 — WP02 "empty allow-list" is an over-claim (alphonso)
Two permanent sanctioned slice **homes** must be carved out at FILE level (the existing `_SEAM_REL`
home-skip pattern), not emptied: `branch_naming.py` (`_mid8`/`resolve_*` keep `mission_id[:8]`) and
`mission_runtime/context.py` (`IdentityFragment`, "here and nowhere else"). Plus `invocation_id[:8]` by
name. Correct framing: **the mission-identity CONSUMER class is empty; the homes are skipped.**

## Anti-gaming DoD hardening (renata + pedro + paula) — applies mission-wide
- **WP01/03/04/05 byte-parity:** golden values must be **literals captured from HEAD before any edit**
  (assertion RHS hard-coded string/`""`/`None`), never a re-call of the routed seam (no
  `resolve_mid8(x)==resolve_mid8(x)` tautology). C-003/C-004 made diff-checkable.
- **WP02 ratchet (T018/T021):** the inner-name predicate is **substring/glob (`*mission_id*`)**, not
  exact-match (else M1 `str(raw_mission_id)[:8]` escapes — the original blind spot returns); the
  self-test plants **all 5** shapes + asserts each flagged + asserts `invocation_id[:8]` NOT flagged; pin
  the pre-mission baseline count as a committed literal.
- **WP04 terminus:** "shadow deleted" ⇒ `grep 'def _mid8'` returns nothing (delete the def, not its body).
- **WP04 FR-002:** the test constructs a real `ExecutionContext`; the 5 sites' mission-identity provenance
  recorded.
- **WP06 #1971-tail:** assert **equal resolved Path values under each of the 3 named conditions with a
  divergent input** — reject the tautological "3 entries exist / same return type" test.

## Confirmed SOUND (no change)
Ownership disjoint (only WP01 edits `branch_naming.py`; `agent/mission.py` single-owner); flatten safe
(allocator + `implement.py` handle legacy topology explicitly); WP02 3-lane dependency-merge handled
(#1684 fix + status gate; conflict-free since deps own disjoint files) — *contingent on F-1 fixed*.
WP07 doc-path compliant (SOURCE-only).
