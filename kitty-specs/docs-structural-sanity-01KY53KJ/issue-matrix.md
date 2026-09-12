# Issue matrix — docs-structural-sanity-01KY53KJ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2851 | Disambiguate/redistribute docs/development by concern + retire anti-sprawl ratchet | verified-already-fixed | CLOSED via PR #2855, commit 758c2bd45 — landed on main; mission builds on it, does not reintroduce ratchet |
| #2855 | PR: retire ratchet, fold #2851 | verified-already-fixed | MERGED, commit 758c2bd45 — precondition landed independently |
| #2314 | Epic: Spec Kitty documentation and docsite | deferred-with-followup | This mission delivers bucket C (sanitization) + E (docs governance as doctrine) slice via WP01–WP05. Follow-up: #2314 remains the open tracking epic for buckets A/B/D |
| #2302 | Codify documentation standard as doctrine | in-mission | WP01 extends DIRECTIVE_042 + common-docs styleguide config block (lane-a 6f9d05bc4); WP02 lands scripts/docs/docs_structural_lint.py as the successor gate — terminal at mission done |
| #2227 | Common Docs Mission B residuals (~25 historical architecture/<era> prose mentions + 3 frontmatter-less ADR READMEs) | deferred-with-followup | Explicitly deferred per spec FR-007/NFR-006 — the 3 `docs/adr/{1.x,2.x,3.x}/README.md` are allowlisted; architecture-residual prose coordinated to #2227 |
| #2215 | Distil era-suffixed architecture/vision/research READMEs into single canonical living page | deferred-with-followup | Out of scope per spec C-003 (line 163) — era-suffixed READMEs owned by #2215 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
