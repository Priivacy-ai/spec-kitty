# Tracer: Design Decisions — custom-mission-type-second-class-citizens-01M1FQXD

Mission: Custom mission types are second-class citizens (#3830, #3831, #3832)
Phase: spec

Seeded at spec authoring per charter standing order #3 (mission tracer files).
Append plan/implement-phase design decisions and rationale here as the
mission proceeds.

## Spec phase

- **Decision 1 (#3832 fix shape, operator-mandated)**: derive required
  Technical-Context-equivalent fields from the mission type's own plan
  template, not from mission-type name. A name-based guard mirroring
  `mission_check_prerequisites.py:364` was explicitly rejected. Recorded
  verbatim in spec.md Clarifications.
- **Decision 2 (#3831 scope, operator-mandated)**: this is a research-phase
  checkpoint, not resolved at spec time. The plan/research phase must settle
  against a real org-pack fixture whether the legacy `Mission`/`mission.yaml`
  schema and the modern org-tier `MissionType` schema are bridgeable without
  new schema work; go/split decision follows from that finding. Recorded
  verbatim in spec.md Clarifications, with the Issue Closure Linkage
  consequence (Closes vs. Refs #3831) made explicit.
- **Correction to the operator's #3832 call-site characterization**: the
  brief described `mission_setup_plan.py` as calling
  `is_substantive(plan_file, "plan")` at three call sites (~553, 794, 1230).
  Direct verification shows only two of those three (794, 1230) use
  `kind="plan"`; line 553 (`spec_is_substantive = is_substantive(spec_file,
  "spec")`) is the `kind="spec"` check, unguarded by any mission-type
  condition (unlike its sibling at `mission_check_prerequisites.py:364`,
  which does guard the spec check by name). spec.md's FR-007/FR-008 reflect
  this corrected picture: FR-007 targets the two genuine `kind="plan"` call
  sites (794, 1230); FR-008 separately flags the `kind="spec"` inconsistency
  between the two files without prescribing its fix shape as this mission's
  strict scope, since the FR-013 spec-row check is not template-shaped the
  way Technical Context is.
- **Decision 3 (#3832 research/plan resolution, fix-round addition)**: the
  spec-round adversarial squad (SPEC-ARCH-003) confirmed a genuine
  self-contradiction — the Edge Cases section offered "documented neutral
  pass" (always-substantive) as a live option for `research`/`plan`, while
  NFR-005 requires the gate to be able to fail for every mission type it
  applies to. Resolved by REJECTING the neutral-pass option (b) and adopting
  option (a): FR-006's template-derived mechanism now checks `research`'s
  own scaffolded fields (Research Context / Methodology / Data Sources) and
  `plan`'s own scaffolded fields (Problem Decomposition / Scope — MoSCoW /
  Sequencing & Prioritisation / Decisions), verified present in
  `packs/built-in/missions/research/templates/research-plan-template.md`
  and `packs/built-in/missions/plan/templates/plan-plan-skeleton.md`
  respectively. Rationale: a neutral pass would structurally exempt these
  two types from NFR-005 and would also contradict Decision 1's own binding
  fix shape ("derive from the mission type's own template"), which implies
  deriving from what the template DOES scaffold rather than treating the
  absence of a Technical-Context-shaped section as "nothing to check."
  Recorded verbatim in spec.md Clarifications / Decision 3, with a new
  Acceptance Scenario (User Story 3, AC5) and updated NFR-004/Edge Cases
  text.
- **SPEC-FRESH-001 fix (fresh-sweep R5b)**: the prior fix round's Decision 3
  claimed FR-006's mechanism checks `research`/`plan`'s "own scaffolded
  fields" using language that implied a literal reuse of
  `_has_substantive_technical_context`'s bold-field-scan-and-placeholder-strip
  algorithm (the mechanism that works for `documentation`). Verified against
  the live templates this is false as stated: `plan-plan-skeleton.md`'s
  `Problem Decomposition` (line 17) and `Sequencing & Prioritisation` (line
  41) are markdown TABLES with bracket placeholders the existing
  `_PLACEHOLDER_PATTERNS` list does not recognize and no `**Label**: value`
  lines for a bold-field scan to find; `research-plan-template.md`'s `Data
  Sources` (line 56) is a third-level heading nested inside `Methodology`
  (line 22), not a sibling section. Chose **option (a)** from the finding's
  remediation (not option (b), softening to "deferred to plan phase"):
  updated Decision 3, FR-006, FR-007, NFR-004, NFR-005, and User Story 3 AC5
  to make the additional, real implementation work explicit — a distinct
  table-row detector mirroring the existing `_has_substantive_fr_row`
  (`_substantive.py:71-97`) for `plan`'s table sections, plus extended
  placeholder-pattern coverage and a nested-heading scan for `research`.
  Rationale: option (a) keeps the mechanism decision-complete (consistent
  with Decision 1's binding "derive from the template" principle and with
  NFR-005's non-vacuity requirement) rather than reopening the "how" as an
  unresolved plan-phase question — the finding's own evidence shows the
  needed detectors are a bounded, well-understood extension (mirroring an
  existing in-module pattern), not open-ended design work that would justify
  deferral. Also fixed SPEC-FRESH-002: added SC-001a mirroring NFR-001/AC4's
  `plan` composition-dispatch non-regression clause, which SC-001 had omitted.
- **Operator ruling resume (fresh sweep 2, `reviews/spec.ruling.md`)**: SPEC-FRESH2-001
  (severity 4) upheld — the prior round's Decision-3 detection-mechanism note covered
  only 2 of `plan`'s 4 NFR-004-required fields (`Problem Decomposition`/`Sequencing &
  Prioritisation`, table-row detector) and falsely claimed "`plan`'s sections are
  tables." The ruling rejected narrowing (option b) and directed remediation (a),
  finding it cheaper than assumed: `Scope — MoSCoW` (a bulleted `- **Field**: value`
  list) needs no new mechanism — `_has_substantive_technical_context`'s existing
  peer-field regex (`_substantive.py:180-186`) already tolerates the leading bullet
  marker (FR-013/#1896); it only needs the bold-field-scan's heading-name lookup
  parameterized instead of hardcoded to `Technical Context`. `Decisions` nests its
  bulleted bold fields under `### Decision D-1`, the same nested-not-sibling shape
  already specified for `research`'s `### Data Sources` under `## Methodology` —
  covered by extending that same nested-heading-scan's scope, not a second mechanism.
  Updated Decision 3's detection-mechanism note, FR-006, FR-007, NFR-004, NFR-005,
  User Story 3 AC5, and the Edge Cases bullet to state all four fields' actual shapes
  (table / bulleted peer-field list / nested-heading) and that the mechanism dispatches
  on shape, not mission type.
  **AND/OR combination rule resolved**: mirrors `_has_substantive_technical_context`'s
  existing `Language/Version`-plus-a-peer-field semantics, generalized — for each
  mission type, the template's FIRST scaffolded field is the primary and must be
  substantive, PLUS at least one peer field must also be substantive (not ALL fields,
  not ANY ONE). For `plan`, verified directly against `plan-plan-skeleton.md`'s own
  heading order (`Problem Decomposition` line 17 → `Scope — MoSCoW` line 32 →
  `Sequencing & Prioritisation` line 41 → `Decisions` line 53), the primary field is
  `Problem Decomposition`.
  **SPEC-FRESH2-002** (severity 2) fixed: the `_has_substantive_technical_context`
  citation was `_substantive.py:158-186` (stops mid-regex, before the accept/reject
  loop); verified the function's real span by reading `def` to final `return` and
  corrected every citation to `_substantive.py:158-195`.
  **SPEC-FRESH2-003** (severity 2) fixed: NFR-005's rationale conflated two distinct
  failure modes into one causal claim. Split into (1) a literal bold-field-scan run
  against `plan`'s table sections matches nothing and FAILS CLOSED (returns `False`) —
  not a working check, but not vacuous-pass either; (2) a naive length/non-empty-only
  check lacking placeholder-pattern coverage for `research`/`plan`'s own bracket
  vocabulary would VACUOUSLY PASS an unfilled scaffold — named against its own,
  distinct naive implementation.
- **Org-tier resolver citation for #3831's cross-subsystem-disagreement
  claim**: verified as `src/charter/activation/org_expected_artifacts.py`,
  function `resolve_org_expected_artifacts` (module-level, ~line 54), called
  from `src/charter/activation/mission_type_profiles.py`,
  function `_resolve_expected_artifacts_slot` (~lines 1093-1128), plus
  `src/specify_cli/dossier/manifest.py::ManifestRegistry.load_manifest` and
  `src/specify_cli/runtime/resolver.py` as additional callers of the same
  org-first/built-in-fallback pattern. This substantiates the claim that a
  different, modern subsystem already consults the org tier for
  mission-type-scoped resolution while the legacy `mission.py` loader does
  not.
- **Structural reduction of #3832's mechanism content (operator ruling #2,
  `reviews/spec.ruling-2.md`, FINAL for the spec phase)**: two consecutive fix
  rounds converged the #3832 substantive-check content into detector design —
  FR-006, NFR-004, and User Story 3 Acceptance Scenario 5 each restated the
  same regex/detector/call-site mechanism (table-row detector, nested-heading-
  scan, generalized bold-field-peer-scan, `_substantive.py:NNN-NNN`
  citations), and each restatement was independently audited and
  independently found gapped. Ruling #2 diagnosed this as structural — the
  spec was designing the detector rather than stating the requirement — and
  directed a reduction rather than a third mechanism fix: FR-006, NFR-004,
  NFR-005, and User Story 3's acceptance scenarios were rewritten to
  intent/outcome-only (what the gate must accept/reject per mission type, not
  how it detects fields), FR-007 was folded into a new "Deferred to Plan
  Phase" list entry (call-site routing) since its content was entirely
  mechanism/call-site enumeration, and Decision 3's "Detection-mechanism note"
  was replaced with a short pointer to that same deferred list. The
  primary-plus-peer AND/OR combination rule was kept as behavioral content
  (per ruling #2, it states an outcome constraint, not a detection mechanism).
  Decision 1, Decision 2, the four-mission-type Technical Context template
  table, and the corrected-scope statement were left untouched, per the
  ruling's explicit scope limit.
- **Ruling #2's admission of a factual error in ruling #1**: ruling #1 had
  asserted that `Scope — MoSCoW` "needs no new mechanism… what it needs is
  for the heading name to be a parameter," reasoning from a finding summary
  rather than reading the source. Ruling #2 verified `_has_substantive_technical_context`
  first-hand and found this wrong: parameterizing the heading leaves
  `**Language/Version**` hardcoded, so the primary-field check still fails for
  every type whose template doesn't use that exact label — `documentation` is
  the proof, since it already uses the literal heading `## Technical Context`
  and still cannot pass. Both the section heading AND the primary field label
  are hardcoded in `_has_substantive_technical_context`
  (`src/specify_cli/missions/_substantive.py:158-195`, verified directly
  against source this round). This is now recorded as deferred-question #2 in
  spec.md's "Deferred to Plan Phase" list rather than re-litigated as spec
  content — the fix for ruling #1's error is a corrected framing of an open
  question, not a new mechanism decision to make at spec time.
