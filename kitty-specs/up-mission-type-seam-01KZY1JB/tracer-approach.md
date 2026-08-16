# Tracer: Approach — up-mission-type-seam

Seeded at planning (specify phase). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## Scope

Give the mission-type roster a layered lookup so a non-built-in mission type from an org-tier
doctrine pack resolves **end to end** — through mission create, charter activation, and
action-sequence projection — not just "loads without crashing." Three parts, corresponding to an
upstream research programme's internal work-item numbering that is deliberately **not** named in
this artifact (per operator instruction — this repo is public and the internal numbering is not
this repo's concern):

1. **Roster layering** — a new, separate, layered mission-type lookup alongside the existing
   built-in-only `MissionTypeRepository.default()`.
2. **Projection wiring** — thread the `PackContext` that `resolve_mission_type_context` already
   constructs one frame down into actual action-sequence/template-set projection, so a non-built-
   in type's projected fields are real, not silently defaulted.
3. **Activation-scan widening** — `charter activate mission-type` scans org and project layers,
   not only the built-in four.

Plus two required companions: a red-first loud-fail for the dominant silent-wrong risk (an
org-pack type with no `action_sequence` resolving cleanly to an empty one), and four CLI consumer
surfaces that must stop lying (`charter mission-type list`, `mission-type show`,
`doctrine mission-type list`, `charter activate`'s step-removal warnings) — see spec FR-004 and
FR-006–FR-009.

## Spec-authoring approach

1. Read the charter (`.kittify/charter/charter.md`), `AGENTS.md`, `CONTRIBUTING.md` in full
   before touching the spec, per the charter's own "Load the Project Charter First" rule and this
   mission's explicit instruction to read them in that order.
2. Read the canonical `software-dev` spec template resolved through the doctrine chain
   (`packs/built-in/missions/software-dev/templates/spec-template.md`, confirmed identical to the
   project-tier override at `.kittify/overrides/missions/software-dev/templates/spec-template.md`
   — a byte-for-byte `diff` was run to confirm this, not assumed) rather than copying an older
   mission's spec.md, per the charter's "Use Canonical Sources, Never Improvise" rule.
3. Independently re-verify every file:line piece of evidence supplied by the operator against
   live code at HEAD `ab0a0b9b5b5e6803775e45bebd66d1cc8d3b68dc`, via a dedicated read-only
   verification pass, before writing any of it into the spec as a citation. Several line numbers
   had drifted slightly (see below); all six binding decisions themselves held up as substantively
   true on re-verification, with one caveat: item 7's "WP06" docstring claim is confirmed **false**
   as described (a caching-authority switch, not an org/project seam) — which is exactly why the
   spec requires it be corrected, not merely cited as true.
4. The canonical template does not literally contain a "Clarifications" heading or a sizing
   section — it is User Scenarios & Testing / Requirements (FR/NFR/C, numeric IDs) / Key Entities
   / Success Criteria. The operator's brief required a Clarifications/decision-records section,
   a provenance note, an explicit out-of-scope list, and a sizing statement; these were added as
   clearly-labeled additional sections around the template's mandatory core rather than distorting
   the mandatory sections' own shape — the mandatory sections (User Scenarios, Requirements with
   numeric FR-NNN/NFR-NNN/C-NNN IDs, Key Entities, Success Criteria) are followed structurally
   as-is.
5. Every requirement in the spec is written with red-first, no-silent-success framing threaded
   through explicitly (not left implicit) — see NFR-002, NFR-005, and the User Story 2 acceptance
   scenarios.

## Line-number drift found during re-verification

- `MissionTypeRepository.default()`: cited as `:49-50`, is actually `:48-50` (the
  `@classmethod`/`@functools.cache`/`def` triplet spans one line earlier than cited).
- `_resolve_action_slot`'s empty-sequence fallback: cited as "around line ~805", the actual
  `if not is_registered: return []` fallback line is `789` (lines 805/807 are separate `or []`
  None-guards on the `extends` chain, not the primary fallback).
- All other file:line citations in the operator's brief held on re-verification, within the
  template's own citation-format tolerance (a `def`/decorator spanning +/-1 line of a stated
  range).

No spec-shape drift was found between the charter and CLAUDE.md — both agree that the charter
wins on conflict and neither actually conflicted on anything touched by this mission.
