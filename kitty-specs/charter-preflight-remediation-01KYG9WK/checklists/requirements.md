# Specification Quality Checklist: Charter Preflight Remediation Authority

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Validation performed 2026-07-27, first pass. Three rewrites were required before the items above
passed.

1. **Implementation detail leaked into the user stories.** The first draft named the specific
   modules, functions and commands from the reproduction (`_compute_charter_source`,
   `charter sync`, `charter.yaml`). Those belong in plan, not spec — and naming them pre-commits the
   design, which matters here because C-002 forbids the obvious parity-patch. Rewritten to describe
   what the operator experiences: an instruction that changes nothing, and diagnostics that disagree
   with the gate.

2. **Success criteria were technology-specific.** SC-003 originally counted implementations by
   file path. Restated as "the number of independent answers goes from two to one", which is
   verifiable without knowing where they live.

3. **NFR-003 was unfalsifiable as first written** ("does not break existing behaviour"). Replaced
   with a bounded claim over the four enumerated fixture shapes: the count of blocking states must
   be the same or lower, never higher.

### Second pass — adversarial gate, 2026-07-27 (verdict: concerns, two HIGH, both upheld)

4. **The resolver count was wrong and the scope boundary was unfalsifiable.** The spec asserted
   charter presence was "resolved two different ways by two sets of consumers". Verified against
   live code: there are more than two independent definitions, keyed off *different artifacts*
   (`charter.yaml` vs `charter.md`) and including two migration-local definitions built for
   idempotency rather than health reporting. Worse, one of the three diagnostics named in User
   Story 2 — the prerequisites check — contains **zero** charter references and never asks the
   question at all, so "they return the same answer" was untestable for it. Fixed by: removing the
   hard count (the enumeration is now a plan deliverable, FR-004/SC-003), scoping Acceptance
   Scenario 1 to surfaces *that resolve charter presence*, excluding migration-local resolvers in
   Assumptions, and adding an explicit Out-of-Scope line so nobody reads this as an obligation to
   make a new surface charter-aware.

   **Root cause worth naming**: the three diagnostics came from issue #2831's own body. I inherited
   the reporter's framing without re-deriving it — the exact failure the Diagnosis Provenance
   section was written to guard against, repeated one section further down.

5. **The escalation carve-out was a loophole around the mission's central guarantee.** US1
   Acceptance Scenario 3 let a check "escalate explicitly" instead of proving its remediation works,
   with no criterion for what makes escalation explicit. A check could dodge the FR-003 automated
   test by being reclassified into the carve-out — and prose that merely *reads* like escalation was
   precisely the BC-2 failure mode (a command that looked like a valid remediation and was
   structurally a no-op). Fixed by requiring exempt checks to emit no remediation and appear in an
   enumerable exemption set, with NFR-001 now pinning that set's size so reclassification turns the
   enforcement red instead of silently shrinking its coverage.

6. **A "read-only" diagnostic mutates.** Confirmed while checking finding 4: one charter surface runs
   a bundle-freshness sync before answering the presence question. Added as an edge case because it
   constrains C-002 — the surviving canonical resolver must answer without mutating, or consolidation
   would spread a side effect into every caller.

### Residual judgement calls, recorded rather than hidden

- **The Assumptions section carries a real risk to FR-004.** It asserts the operator-reachable
  charter-presence resolvers are answering the *same* question. That is inferred from their names and
  their operator-visible effect, not from reading every resolution path end to end. If plan finds
  they deliberately answer different questions, FR-004 must become "name them distinctly" rather than
  "consolidate them" — and C-002's consolidation mandate would then not apply. **Plan must settle
  this before any consolidation work starts.**

- **SC-002 says "a bounded number of steps" rather than naming a number.** Naming one now would be
  invented precision; the honest bound falls out of whatever remediation chain plan settles on.
  Plan should replace it with the actual step count.

- **FR-005 may already be satisfied.** The distinction between "absent" and "present but unusable"
  might exist in the current state vocabulary. It is specified as a requirement because the
  *operator-facing surfaces* conflate them; plan should check whether the underlying model already
  makes the distinction and only the reporting drops it.

- **This spec deliberately does not name the fixing command.** The reproduction established which
  one works today, but writing it into the spec would make the spec's correctness depend on that
  command's continued behaviour — the exact staleness trap that cost two adversarial gate rounds on
  the preceding mission. The requirement is that the emitted remediation *works*, not that it is a
  particular string.
