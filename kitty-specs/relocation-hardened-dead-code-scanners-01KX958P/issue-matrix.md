# Issue Matrix: Relocation-Hardened Dead-Code Scanners (#2546)

Canonical schema. Verdicts: `fixed` | `verified-already-fixed` | `deferred-with-followup`
(needs `#NNN`/`Follow-up:` handle) | `in-mission` (closed by a later WP in this mission;
must resolve to a terminal verdict before merge).

| Issue | Verdict | Evidence ref | Scope |
|-------|---------|--------------|-------|
| #2546 | fixed | WP01–WP05 merged f9322a5 | Relocation-hardened the dead-code scanners (relocation-tolerant SymbolKey + live collision classifier + tier-specific dangling ratchet, T004 preserved) + remediated the arch-suite warnings (40→2, residual src-tracked). All 5 WPs opus-reviewed + approved; (a–k) bite battery green through the production path; full arch 901/0. |
| #2071 | deferred-with-followup | Follow-up: #2071 | Parent epic (test-suite friction). Remains open as a rollup; this mission is one child slice under it — not closed here. |
| #2293 | deferred-with-followup | Follow-up: #2293 | Adjacent (category_b burn-down). WP02 dropped 2 stale + FR-010 auto-exempted more (215→194 honest live count) rather than fighting its ratchet; #2293 stays open. |
| #2553 | deferred-with-followup | Follow-up: #2553 | The ~13 `tests/contract/test_example_round_trip.py` legacy-contract `# pydantic_model:` backfill warnings — OUT of `tests/architectural` scope (NFR-006 is arch-scoped). WP05 narrowly scope-suppresses the import-time leak (context-managed, not blanket) and filed #2553. Folded in as a post-merge op. |
| #2554 | deferred-with-followup | Follow-up: #2554 | Doctrine-data drift found during WP05's warning census: agent profiles cite the `bdd-scenario-lifecycle` PROCEDURE under tactic-references, emitting `CharterCatalogMissWarning` (the 2 residual arch warnings). Src/doctrine-data fix → #2554. Folded in as a post-merge op. |
