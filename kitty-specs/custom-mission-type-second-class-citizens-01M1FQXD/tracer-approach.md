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

## Plan phase

- Opened with spec.md's own "Deferred to Plan Phase" list as the literal agenda (five
  questions), rather than re-deriving what plan.md should cover from scratch — this
  mission's spec phase went through two HALTs specifically to hand this design work to
  plan, so treating that list as binding scope (not merely inspiration) closes the loop
  ruling #2 opened.
- Independently re-verified the majority of load-bearing source citations (line spans,
  regex bodies, function signatures) against live source before writing them into
  plan.md/research.md, rather than trusting the task brief's citations on faith — this
  surfaced one correction (see tracer-tooling-friction.md: the "mission-loader coverage"
  CI gate name is a false match for FR-005's actual file).
- Treated the #3831 SPLIT verdict as settled per the prior investigation's evidence
  (re-verified `MissionConfig`/`PhaseConfig`/`ArtifactsConfig` and `MissionTypeProfile`
  directly), and wrote the plan-phase consequence (FR-004 descoped + tracked follow-up
  description, FR-005 proceeds unconditionally) rather than re-opening the go/split
  question itself, per the task's explicit instruction not to re-litigate it.
- Applied planner-priti's decomposition/sequencing specialization beyond the required
  deliverables by adding a "Suggested Work Package Sequencing" section identifying the
  three FR clusters as independent, parallelizable WPs (disjoint file sets per C-003, no
  cross-dependency) gated behind one shared campsite-clean commit and one shared
  integration-verification checkpoint at the end.
