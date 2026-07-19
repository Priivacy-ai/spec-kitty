# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

- 2026-07-19 — **Started:** three coherent charter-layer items — delete `charter.generator`,
  delete `charter.extractor`, and fix #2373 no-op-stability — framed as a low-risk dead-code +
  campsite slice continuing #2773, with bundle-vs-split flagged as the one genuine open question.

- 2026-07-19 — **Shift — ran a read-only research squad *before* writing the spec.** Three parallel
  Explore agents grounded each item against the live tree instead of trusting the going-in
  assumptions. This is the pre-flight-squad cadence, and it paid off immediately (next entry).

- 2026-07-19 — **Scope reshaped by evidence:** the squad found #2373's *render-path* bug is already
  fixed by #2773 (`build_charter_context` no longer writes tracked doctrine). Item 3 was NOT what the
  brief assumed; the residual churn lives in the preflight → `synthesize` freshness path. Surfaced to
  the operator, who chose **Bundle deep fix** — so item 3 became a real behavioral fix, not a guard.

- 2026-07-19 — **Approach for item 3 (deliberate):** honor "live evidence over static-fixed" — do
  not close #2373 because the render code looks fixed; reproduce the residual churn red-first in a
  doctrine-tracked checkout, fix the freshness-misfire, then close with a regression guard.

- 2026-07-19 — **Would try differently:** open the mission earlier (a lightweight pre-mission handle)
  so genuine discovery questions can mint `decision_id`s in-protocol rather than being backfilled.

- 2026-07-19 — **Shift — post-tasks adversarial squad reversed a scope decision.** The bundle-deep-fix
  choice (item 3) rested on a residual churn that the squad proved is already fixed. Rather than
  implement a no-op "fix," WP04 became a regression guard. Lesson reinforced: adversarial verification
  of a WP decomposition against live code catches ghost-work before an implementer wastes a cycle.
