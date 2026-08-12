# Design Decisions

> Capture design choices and their rationale as they are made (1–3 sentences per dated entry).

**Prompting questions**
- What decision was made, and what were the alternatives?
- Why was this option chosen?
- What constraint or invariant does it protect?

---

## Entries

<!-- YYYY-MM-DD — 1–3 sentences: the decision and why. -->
- 2026-08-10 — D1: `docs/context/audience/` is the docs persona SSOT; do not copy built-in personas
  over it (DIRECTIVE_044). D2: audience-based how-to routing (config made audience-aware). D3: redirect
  map is DERIVED / baseline IMMUTABLE / own cumulative occurrence-map spine (NFR-010). D5: rewrites
  bounded + fact-guarded (NFR-009), split from mechanical moves. D6: shared manifests single-threaded
  through IC-11. See research.md for full rationale + alternatives.
- 2026-08-10 (post-plan squad) — OB-1: redirect tooling has NO additive-merge and `_relocate` is
  single-move, so the cumulative spine must be a COLLAPSED baseline->FINAL data spine carrying the prior
  mission's 29 moves (default) rather than appended entries; add a regen-reproduces-all-151 test. OB-2:
  a standing single-root blocking lint would reverse #2851 — default is terminal verification + curation,
  not a per-PR gate, unless #2851 is re-sanctioned. IC-11 made a single TERMINAL reconcile WP; IC-03 split
  into 03a (advisory scaffolding) / 03b (terminal blocking + required pre-merge docfx build).
