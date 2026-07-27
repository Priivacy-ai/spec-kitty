# WP06 Review — Cycle 1 (reviewer-renata)

**Verdict: HOLD (returned to planned).** The code, tests, and gates are
approval-quality and I found no correctness defect. The single blocking issue is
a **missing + falsely-cross-referenced authorization record for the C-004
charter-frozen-block edit** — the highest-risk change in this mission. The fix is
documentation-only; **do not touch the source or test logic.**

---

## What is CORRECT and must be preserved verbatim

I verified all three highest-priority concerns with RED-before proofs:

1. **Genuinely-legacy missions are UNAFFECTED.** The split
   `genuinely_legacy = _warrants_legacy_warning(...)` reuses the existing
   stored-topology classifier (C-005) — not a reinvented parallel one. The
   genuinely-legacy arm preserves the prior behaviour exactly (resolve cwd lane
   via `_resolve_legacy_lane_destination`, override `destination_ref`, emit the
   once-only warning). Proof: reverting only `transaction.py` to the pre-fix
   source and running `test_transaction_legacy_topology_routing.py` fails **only**
   the 3 modern-coordination-less parametrizations (single_branch / lanes /
   flattened); the genuinely-legacy + coordination cases stay green (8 passed).

2. **The ratchet update is HONEST, not cosmetic.** With the fix in place the
   modern arm sets `worktree_root = repo_root` and keeps the caller-supplied
   `destination_ref` — it never calls `_resolve_legacy_lane_destination` and never
   reads `Path.cwd()`. The `CommitTarget(ref=self.destination_ref)` allow-list
   entry genuinely cannot be AST-split (one construction serves both arms), and
   the cwd HEAD read now reaches it only for genuinely-legacy missions. The
   remaining re-derivation is honestly labelled permanent intentional debt.

3. **FR-001 genuinely satisfied.** `test_write_side_..._no_longer_reproduces_2647`
   reproduces the exact user-visible `Illegal transition: planned -> for_review`
   on pre-fix source through the real Typer entry point from a lane-worktree cwd,
   and passes post-fix, with an independent repo-root no-regression arm.

4. **Full suite green:** 1311 passed / 4 skipped / 0 failed across the four
   specified test trees. ruff clean on all changed files. mypy `--strict` on
   `transaction.py` shows 2 `no-any-return` at lines 164/175 — **identical on the
   base**, far from the edit; zero new. (Implementer's "3 pre-existing" is a minor
   miscount; the point holds — none are introduced by this diff.)

5. **Coord path untouched.** `_is_legacy_mission` has exactly one runtime caller
   (`_acquire_locked:745`); the `else:` coordination-topology branch is unchanged
   in the diff, and `test_coordination_topology_acquire_routes_to_coord_worktree`
   pins it.

6. **The C-004 frozen-block re-pin does NOT mask a behaviour change.** The
   protected genuinely-legacy HEAD-override code
   (`_resolve_legacy_lane_destination` + `effective_destination_ref` override) is
   byte-identical in substance — only re-indented one level and re-commented. The
   guard still fires on any real edit to that sub-block. As a narrowing of the
   frozen span (whole legacy branch → genuinely-legacy sub-block) it is
   defensible *provided the authorization exists* — see the blocker below.

7. **Scope leeway on the two out-of-`owned_files` test edits**
   (`test_legacy_mission_fallback.py`, `test_transaction.py`) is rationale-backed:
   both pin the shared coordination primitive this WP fixes; no sibling lane owns
   them; the re-characterisation of `test_legacy_routing_..._by_topology` (uniform
   → two-family write-contract split) is correct test-remediation, not a
   scaffold-revert. Approved.

---

## BLOCKER — record the C-004 authorization and fix the false cross-references

C-004 is a charter-frozen block: the guard's own message demands *"any change
must go through an explicit, reviewed decision, not an incidental refactor."* The
re-pin narrows that frozen span as part of an **operator-approved scope expansion
of WP06 to fix #2453/#2647** (beyond the WP's stated C-002 / FR-001 / #2647
boundary). That decision is the load-bearing authorization for this change — and
it is **not recorded anywhere in the mission trace on any partition**:

- `traces/design-decisions.md` contains **zero** `#2453` entries on the lane, on
  `kitty/mission-…-01KXJ1ZX`, and there is no coord branch. Its last entry is the
  POST-TASKS review-squad note; the scope expansion is absent.
- The WP spec `tasks/WP06-movetask-cwd-fix.md` has **no EXPANDED SCOPE #2453
  section** (the review prompt expected one).
- Yet the shipped deliverable references this non-existent record:
  - `test_tasks_move_task_cwd.py` docstring: *"REVISED after a live reproduction …
    see `../traces/design-decisions.md` for the full account"* and *"The operator
    expanded WP06's scope to fix #2453 …"* — the account it points to does not
    exist.
  - The `fix(WP06)` commit body cites an *"operator-reviewed #2453 decision"* with
    no traceable record.

This is not mere missing documentation — it is a **broken audit trail plus
misleading in-artifact cross-references on the single highest-risk change in the
mission.** The mission-tracer standing order requires such decisions to be
appended during implement, and the C-004 guard exists precisely to force this
authorization into daylight.

### Required to clear (documentation only — no code/test-logic changes)

1. Append an entry to
   `kitty-specs/implement-loop-commit-hardening-01KXJ1ZX/traces/design-decisions.md`
   recording the operator's decision to expand WP06 to fix #2453/#2647, and that
   it explicitly authorizes: (a) the scope expansion beyond the WP's stated
   boundary, and (b) the C-004 frozen-block re-pin to the genuinely-legacy
   sub-block. State the alternative (defer #2453 to its own sweep) and the
   rationale (P1-adjacent write-side taint blocking this mission's own
   single_branch handoff; the primitive is fixed once, correctly).
2. Add the EXPANDED SCOPE #2453 section to `tasks/WP06-movetask-cwd-fix.md` so the
   WP's authoritative scope matches what shipped.
3. Confirm the `test_tasks_move_task_cwd.py` docstring's "see
   ../traces/design-decisions.md for the full account" reference now resolves to a
   real record (it will, once step 1 lands).

Once the authorization is recorded and the cross-references are truthful, this WP
is otherwise ready to approve as-is.
