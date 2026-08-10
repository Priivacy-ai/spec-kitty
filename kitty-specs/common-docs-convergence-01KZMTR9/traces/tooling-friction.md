# Tooling Friction

> Log tooling/process friction as it happens (1–3 sentences per dated entry).

**Prompting questions**
- What tooling does this mission touch, and where did it slow you down?
- What was missing, broken, or surprising?
- What would remove the friction next time?

**Tooling this mission touches**: `scripts/docs/*` (redirect/link/inventory tooling), the
`docs_structural_lint.py` asset + `structural_lint_config`, DocFX (`docfx.json`), the audience
resolver (new), GitHub Actions (`docs-freshness.yml` + new pre-merge build), `spec-kitty` CLI under
clone-local isolation.

---

## Entries

<!-- YYYY-MM-DD — 1–3 sentences: what tooling caused friction and how. -->
- 2026-08-10 — Seeded at plan. Known friction surfaced pre-implementation: `redirect_stub_generator.py`
  hardcodes a *closed* mission's slug/occurrence-map (must be parameterized, IC-02); the authoritative
  DocFX/SEO/redirect gates run only on push, not PR (adding a pre-merge job, IC-03); the structural
  lint passes 0/699 and measures none of this mission's goals (must be extended, IC-03).
