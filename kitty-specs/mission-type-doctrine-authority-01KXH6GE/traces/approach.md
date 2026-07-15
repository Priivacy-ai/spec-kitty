# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

- 2026-07-14 — **Seed.** Foundational doctrine mission driven the full length: pre-spec research squad (4 lenses) → architect design pass → ADR `2026-07-14-2` → spec (+3-lens review squad) → plan (+3-lens post-plan squad) → tasks (+3-lens post-task squad). Each planning point-cut hardened by an adversarial squad before advancing. Execution via the implement-review loop: implement = `claude:sonnet:python-pedro`, review = `claude:opus:reviewer-renata`; 12 WPs across 12 lanes, dependency-ordered (roots WP01/WP02/WP09 → seam WP03 → WP04/05/06-08/11 → join WP12); the WP09/WP10 gates lane is detachable and excluded from the WP12 enforcement join.
- 2026-07-15 — **Roots + seam landed clean.** WP01/WP02/WP09 approved, then WP03 (the resolver seam) approved with a rigorous review of its 0-survivor subsume. Fanned out WP04/WP05/WP11 in parallel on WP03's approval.
- 2026-07-15 — **Shift (under review):** WP04 closed the action-path leak by keying the Surface-A DRG path off `meta.json` directly, rather than populating the resolver's `action_grain` and unioning the two grains as the plan sketched — deferring the full grain-union (citing a circular-dependency risk between the resolver and DRG loading). Whether this is an acceptable slice-1 boundary or a gap is under reviewer adjudication; if accepted, the grain-union becomes a follow-up.
