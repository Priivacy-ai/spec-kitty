# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

- 2026-07-29 — Decision: land as a NEW fast-follow branch (`feat/doctrine-delivery-activation`)
  cut from fresh upstream/main (tip `10e970ed2`), NOT on the dormant #3076 branch.
  Alternatives: reuse current checkout's branch. Rationale: the parent slice (#3070) is already
  merged at the base; a clean branch avoids entangling two missions' history (operator confirmed
  new-branch-in-this-checkout).
- 2026-07-29 — Decision: consume the 9-symbol delivery-rail forward API + treat the 10
  progressive_disclosure composition helpers as MODULE-PRIVATE (internal to
  build_disclosure_payload). Alternatives: re-derive the walk / consume helpers as public API.
  Rationale: C-001/C-002 — the parent slice already demoted the helpers out of `__all__`; the
  forward API is the sanctioned seam. Re-deriving would create a second authority.
- 2026-07-29 — Decision: FR-007 (C4 templates) delivered via a `template:instantiates` edge from
  `action:documentation/design`, NOT re-homed as assets; FR-008 anti-patterns are a
  non-activatable edge-reached kind grounded in each tactic's attested problem/when text.
  Rationale: C-004/C-005 — edges are the delivery mechanism; re-homing/inventing would drift from
  the wiring table's Family C asset assessment and fabricate doctrine.
- 2026-07-29 — Decision (post-plan squad D10): assert delivery/reachability on the PROFILE channel
  `profile_channel_reachable(agent_profile:…)`, NEVER `resolve_context`. Alternatives: the plan
  originally named `resolve_context`. Rationale: `resolve_context` is the ACTION channel — DDD is
  already action-reachable there (vacuously green) AND it reaches nothing from a profile seed
  (permanently red). The real profile surface is the only one where FR-001 is genuinely red→green.
- 2026-07-29 — Decision (D12): SPLIT the #3075 work into IC-06a (registry unify + discovery gate,
  file-disjoint → parallel) and IC-06b (repository Protocol typing, edits context.py/
  progressive_disclosure.py → sequenced after IC-01+IC-09). Alternatives: keep IC-06 monolithic
  "parallel". Rationale: the Protocol typing removes `# type: ignore` in the exact context.py hunks
  the core walk (IC-01) rewrites and the extraction (IC-05/IC-08) moves — concurrent edit collision.
- 2026-07-29 — Decision (D13/D14): FR-007 template delivery RIDES IC-01's suggests-walk reaching the
  C4 tactic's references (schema-tier, no core query.py edit — `resolve_context` doesn't walk
  `instantiates`); FR-008 anti-patterns use the EXISTING `REJECTS` relation (tactic→anti_pattern),
  validation-tier, never delivered (models.py:73). Alternatives: extend the action channel to walk
  `instantiates` (core-tier, wide blast); invent a new anti-pattern relation. Rationale: reuse the
  canonical vocabulary; anti_patterns are deliberately non-delivered so there's no inert-edge problem;
  avoids a second traversal authority.
- 2026-07-29 — Decision (D15/D17/D18/D19): graph-count/histogram goldens owned by the AUTHORING WP
  (not the terminal reconciliation WP); forward-API retirement is ~2–3 wired symbols (not 9 — the
  charter-activation/action symbols stay allowlisted-with-note, no manufactured importers); NFR-002
  reachability pins are REVIEW-gated not CI-gated; baseline deferred set = 60 (the 50/39 figures are
  stale). Rationale: keeps golden ownership no-overlap, honest scope, and correct baselines.
