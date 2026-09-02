# Tracer: Approach — custom-mission-type-second-class-citizens-01M1FQXD

Mission: Custom mission types are second-class citizens (#3830, #3831, #3832)
Phase: spec

Seeded at spec authoring per charter standing order #3 (mission tracer files).
Append plan/implement-phase approach notes here as the mission proceeds.

## Spec phase

- Framed as three independently testable user stories, one per issue, rather
  than a single greenfield feature — this mission is bug-fix-shaped across
  three related defects on disjoint file sets (see spec.md Constraints
  C-003) that share one theme: built-in mission types are hardcoded as the
  implicit default across three unrelated subsystems (composition dispatch,
  the legacy mission loader, the plan-substantive gate).
- Decision 1 (#3832 fix shape) and Decision 2 (#3831 scope checkpoint) are
  recorded verbatim in spec.md's Clarifications section as operator-supplied,
  binding inputs — not left as prose only in this tracer — so a later
  `analyze` pass or reviewer can audit them independently.
- The four-mission-type Technical Context template table (Decision 1) was
  re-verified directly against the checkout rather than taken on trust; it
  confirmed the operator's expected finding exactly, including the corrected
  scope statement that #3832 also breaks the built-in `documentation`,
  `research`, and `plan` mission types, not just custom ones.
