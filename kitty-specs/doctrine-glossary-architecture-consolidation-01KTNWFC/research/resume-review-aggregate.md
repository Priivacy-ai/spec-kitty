# Resume-review aggregate — 2026-06-11 (post-pause, post-PR-#1850)

Three-profile fan-out after the pause (architect-alphonso/opus, researcher-robbie/sonnet,
planner-priti/sonnet — full reviews in this directory). Trigger: significant decisions landed during the
pause (guard coherence, config-determined placement, DRG declared provenance, mission_runtime canonical
surface, tiered-standards intent #1843, tickets #1805/#1839/#1812).

## Verdict: RESUMABLE — core architecture SOUND; amend before WP01 claim

| Reviewer | Verdict | Counts |
|---|---|---|
| alphonso (architecture) | no FR dead; 2 partially pre-delivered | 6 HOLD · 5 AMEND · 0 superseded · 1 latent conflict |
| robbie (research inputs) | core SOUND, NEEDS-REFRESH | 8 CURRENT · 3 STALE · 0 INVALIDATED · 9 new facts |
| priti (plan/tasks mechanics) | GO after editorial fix-first | frontmatter/lanes/deps/ownership all PASS; 6 staleness flags |

## Triangulated findings (all three independently)

1. **Glossary already promoted** (the #1636/01KTB6AN era + 2026-03-10 `glossary/contexts/`):
   top-level `glossary/` IS the charter authority path; `architecture/glossary/` is a pointer README.
   WP01/WP02's literal "move" framing would RE-FORK the surface C-005 forbids.
   → **Re-scope WP01/WP02: "move" → "reconcile + delete residual"** (operator decision 4 — approved).
2. **WP03/WP06 source lists predate Step 7**: the C4 refresh and Ops ADR must depict
   `commit_guard.evaluate`/`GuardCapability`, `mission_runtime` + `CommitTarget(ref, kind)`,
   `resolve_placement_only` + `resolve_status_surface_with_anchor` (single authorities), per the
   2026-06-10 ADR addendum and ADR 2026-06-07-1.
3. **WP09/WP10 prose predates the declared `provenance` field** (D2-revised, shipped in 01KTRC04);
   graph.yaml serialization unaffected (extractor excludes it) — WP09 simplifies, doesn't change.
4. **Stale prose refs** (fixed in the editorial commit accompanying this aggregate): 8
   `fixups/code-engine-stabilization` references in spec/plan/quickstart/tasks prose; stale
   `change_mode: bulk_edit` header (O1 revert); occurrence_map is a reference-rewrite checklist, not a gate.
5. **WP04/WP05/WP11 cite pre-2026-06-09 `work/` traces** — re-read against the cleaned tracker tree at claim.
6. **Profile surface is live** (`agent profile list/show`; phantom commands removed) — WP04/05/10 reference it.

## Ticket adjudications (alphonso, seconded by priti's tracker plan)
- **#1805** → fold: it is effectively this mission's source FR; add `tracker_refs: ['#1805']` to WP02/WP03
  + `Closes #1805` DoD line (operator decision 2).
- **#1839** → keep carved out/deferred; cross-reference in WP03 context only (contradicts R-04's
  hand-authored-C4 decision; dedup against #1812) (operator decision 1).
- **#1843** → reserve room cheaply: tier expressed as an optional declared field, never structural; one
  non-foreclosure DoD line (operator decision 3).

## Execution order (priti)
Tier 0 parallel: **WP08, WP09, WP01(keystone)** → Tier 1: WP02 → Tier 2 parallel: WP03/WP04/WP05/WP06 →
Tier 3 parallel: WP10/WP11. Critical path (5 hops): WP01→WP02→{WP04,WP05}→WP10/WP11.

## Outstanding operator decisions
The four adjudications above (1839-defer/dedup, 1805-fold, 1843-DoD-line, glossary-re-scope) — presented
2026-06-11; amendments to WP prompts apply once confirmed.
