# Operator ruling — plan phase HALT

**Mission**: `org-pack-drg-root-graph-guard-01KZY0QT` (GitHub issue #3384)
**Phase**: `plan`
**Ruled**: 2026-08-13, by the operator, relayed by the mission orchestrator
**Trigger**: R6 early-stop. The severity-≥3 blocking count went 3 → 2 → **3** — round 2 did not
reduce it — so the loop stopped rather than spending its remaining permitted rounds.

---

## The question that halted the phase

Round 2's fix round **broadened the design beyond the operator's original binding decision**.
That decision (spec phase, Q1) was:

> guard `_drg_helpers.py:87` with a `has_graph_files`-style check **and** make the org branch
> look for graph content at `<org_root>/drg/`.

The round-2 fixer additionally made `OrgDRGFragmentError` cover **malformed root-level graphs**
— a case neither the operator's decision nor `spec.md`'s User Story 3 mentions. Three of the
four surviving findings (FRESH2-001, -003, -004) exist only because of that broadening.

## RULING: the broadening is KEPT, and every finding is fixed in one targeted round

**Rationale** — the broadening closes the defect **class** rather than the instance, which
charter standing order #5 requires. A malformed root-level graph reaches the *same* swallow at
`src/charter/action_doctrine_bundle.py:200-207` (`DRGLoadError` → empty bundle + WARNING) and
therefore silently zeroes all doctrine, exactly like the missing-graph case in the issue.
Issue #3384's own acceptance language is unconditional:

> In no case should declaring a pack *reduce* the doctrine available to a project below the
> bare-project baseline, and in no case silently.

Guarding only the missing-graph case would leave half of that class open, and open *silently* —
the failure mode this repo treats as most serious.

**Explicitly NOT authorised by this ruling:**

- **No further design broadening.** The fix round addresses the four findings and nothing else.
  A fix round that changes design again is the defect this ruling exists to correct — it is
  what turned a converging loop (3 → 2) into a non-converging one (2 → 3).
- **The spec is NOT reopened.** Widening `spec.md` to add a malformed-root requirement and User
  Story was considered and rejected as disproportionately expensive. The consequence is
  recorded under FRESH2-004 below.

## The four findings and their acceptance bars

All four are fixed — severity gates halting, not fixing.

- **PLAN-FRESH2-003 (sev 4)** — the load-bearing one. The broadened claim is only real if it is
  pinned by a test for the **standalone "malformed root graph, no `drg/` directory"** case.
  Resolved when `plan.md`'s test strategy names that case as its own test, distinct from the
  combined malformed-root-plus-`drg/` case. Without it a conforming implementation could fire
  the wrap only when `drg/` also exists — silently reopening this mission's own defect class
  with no coverage to catch it. Note the vacuity-by-empty-set hazard: the test must assert on a
  discovered count, not merely iterate.
- **PLAN-FRESH2-001 (sev 3)** — resolve the IC-01/IC-03 ownership circularity. Exactly one
  implementation concern owns the root-level wrap; IC-01's "lands first, no dependencies"
  sequencing must stop contradicting its dependency on a symbol IC-03 declares.
- **PLAN-FRESH2-002 (sev 3)** — correct the round-2 prose that says the malformed-root +
  valid-`drg/` case zeroes "the entire org layer". The actual effect is that **all five doctrine
  kinds** zero, not merely the org layer's contribution. This is the same imprecision
  PLAN-FRESH-001 already corrected elsewhere in the document; sweep the whole file for the
  class, not just the cited line.
- **PLAN-FRESH2-004 (sev 2)** — since the spec is not being widened, the fix is to **correct the
  citation, not the spec**. IC-03 must stop citing "User Story 3" (which `spec.md` scopes
  exclusively to `drg/` fragments) as backing for root-level-malformed behaviour, and cite the
  defect-class rationale in this ruling instead.

## Re-entry

Per the review protocol, a HALT is terminal for the loop and no resume carries a ruling — hence
this file. The phase re-enters as **one final R4 fix round** (a fresh fixer: not an author,
fixer, verifier or sweeper from rounds 1–2) targeting exactly these four findings, then **a
single R5a anchored verification**, with **no fresh sweep and no further rounds**. All
`resolved` → the phase passes and the full `reviews/` trail is committed with
`spec-kitty safe-commit`. Anything `unresolved` → HALT again, back to the operator.
