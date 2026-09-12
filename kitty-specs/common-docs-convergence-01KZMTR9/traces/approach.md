# Approach Evolution

> Track how the approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

**Starting approach (from plan)**: two foundations first (audience formalization IC-01; move-spine +
redirect tooling IC-02), then gates (IC-03), then movers (IC-04..07) feeding a single-threaded
nav/redirect reconcile owner (IC-11), with rewrites (IC-08) split from moves and ADR polish (IC-10) as
the only parallel-safe leaf.

---

## Entries

<!-- YYYY-MM-DD — 1–3 sentences: what approach was tried and what shifted. -->
- 2026-08-10 — Seeded at plan. Notable pre-implementation shift vs the original spec: the audience
  field + catalog were found to ALREADY exist (disconnected/free-text), so WP-0 became "formalize +
  migrate + test" rather than "create"; how-to home shifted to an audience-based split
  (contributor→development/, user→guides/) after the lint config was found to route how_to→development/.
