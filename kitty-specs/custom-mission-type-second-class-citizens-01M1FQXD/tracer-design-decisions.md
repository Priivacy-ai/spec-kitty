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

## Plan phase

Resolved all five deferred-question decisions from spec.md's "Deferred to Plan Phase"
list, per ruling #2's instruction (design decisions with rationale, not restated
questions, not literal regex/pseudo-code). Full text lives in `plan.md`'s "Deferred
Design Decisions" section; summarized here for the tracer record:

- **Decision 1 (field-location determination)**: a mission type's field layout — which
  heading(s) hold which field, at what depth, in what shape — is template-derived
  metadata resolved via a small, hand-maintained per-type declaration checked into the
  fix alongside the template it describes, NOT re-parsed from template prose at runtime
  (ruling #2's caution against "a second, fragile inference layer"). Justified as a thin
  index onto the template's authority (single-canonical-authority), not a second source
  of truth — mirroring `_ACTION_PROFILE_DEFAULTS`'s own role as a thin built-ins-only
  index onto the `PromptStep.agent_profile` canonical path (C-001's precedent).
- **Decision 2 (primary label + heading, one axis)**: both hardcoded literals in
  `_has_substantive_technical_context` (`_substantive.py:158-195`, re-verified this
  session) become per-type parameters resolved from the SAME Decision-1 declaration,
  not two independently-generalized mechanisms — explicitly closing the exact gap
  ruling #2 caught in ruling #1's factual error (parameterizing only the heading would
  still leave a hardcoded label, and vice versa).
- **Decision 3 (per-shape detection)**: bold-field-list and markdown-table shapes reuse
  EXISTING code (`_has_substantive_technical_context`'s peer-field scan,
  `_has_substantive_fr_row`'s table-row half at `_substantive.py:71-90`), generalized by
  parameter; only the nested-`###`-heading shape (research's Data Sources, plan's
  Decisions) needs one genuinely new detector — stated as a decision about what
  "substantive" means for that shape (at least one populated nested `###` entry), not as
  an algorithm. Reuse-before-invent stated explicitly: 2 of 3 shapes are generalization,
  not new code.
- **Decision 4 (placeholder coverage)**: extend `_PLACEHOLDER_PATTERNS`
  (`_substantive.py:31-49`) with the SAME conservative enumerated-literal style used
  today, adding the actual bracket vocabulary read directly from
  `research-plan-template.md` and `plan-plan-skeleton.md` (full list in `research.md`
  §R4.2) — rejected a generic "any bracketed span" rule because it risks stripping real
  content that legitimately contains brackets (e.g. a citation `[Smith 2024]`),
  violating NFR-005's non-vacuity in the false-negative direction, not just the
  already-known false-positive direction.
- **Decision 5 (call-site routing)**: `is_substantive` gains a mission-type/template
  parameter for `kind="plan"` callers only (`kind="spec"` unaffected). Both confirmed
  `kind="plan"` call sites (`_commit_plan_if_substantive` L794, `setup_plan` L1230)
  already receive `plan_template: ResolutionResult` in scope — decision: thread
  `setup_plan`'s single upstream-resolved value into `_commit_plan_if_substantive`
  rather than each site re-resolving independently (locality/smallest-viable-diff:
  zero new resolution logic needed, one fewer divergence path). The `kind="spec"`
  call site (`mission_check_prerequisites.py:364`) stays behaviorally unchanged this
  mission — verified `research-spec-template.md`/`plan-spec-skeleton.md` both contain
  ZERO `FR-###` rows (grep, no matches), so there is no FR-vocabulary for a
  template-derived check to point at for those two types today; recorded via an inline
  code comment (documentation task, not a logic change) rather than left as a silent gap.

**#3831 SPLIT verdict (research-phase checkpoint, Decision 2/C-005 resolved)**: the
legacy `MissionConfig` pydantic schema (strict, `workflow.phases` with required
per-phase descriptions, flat `required`/`optional` artifacts, closed 5-value `domain`
enum, semver `version`) and the modern org-tier `MissionTypeProfile`/
`expected-artifacts.yaml` system (bare `action_sequence: list[str]` with no
descriptions, per-step `required_by_step` with no "optional" concept, no `domain`/
`version` representation at all) are confirmed incompatible without new schema/
migration work — re-verified directly against both models this session (full evidence
in `research.md` §R1-R2). A third schema (`mission-runtime.yaml`'s own step shape,
consumed by yet another independent resolver, `runtime_bridge_io.py::
_runtime_template_key`) means a bridge would reconcile THREE resolvers, not two.
Consequence: FR-004 (org-tier lookup) is descoped to a tracked follow-up issue
(description recorded in `research.md` §R3, not filed by this plan); FR-005 (loud
fallback) proceeds unconditionally per spec.md's own text. PR closure:
`Closes #3830`, `Closes #3832`, `Refs #3831`.

**Correction surfaced during plan-phase verification (not a spec-phase error, a
plan-phase finding)**: the task brief's suggested gate list named "mission-loader
coverage ≥90%" as applicable because "mission.py is touched by FR-005." Direct
verification against `.github/workflows/ci-quality.yml` shows this is a false
name-match: the CI job literally named `mission-loader-coverage` covers
`src/specify_cli/mission_loader/` (a distinct package: `command.py`,
`contract_synthesis.py`, `errors.py`, `registry.py`, `retrospective.py`,
`validator.py`), which does not contain `_mission_path_by_name`/
`get_mission_for_feature` — those live in `src/specify_cli/mission.py`, outside that
package. Recorded explicitly in `plan.md` §Gate Set / `research.md` §R5 rather than
silently inheriting the brief's assumption, per the charter's version-governance
principle (cite the current canonical source, not a cached/stale characterization).

## Plan-phase fix round (post plan.confirmed.yaml, 9 confirmed findings)

A fresh reviewer (not the plan/research author, not a reviewer this round) addressed
all 9 confirmed findings from `reviews/plan.confirmed.yaml` in one coherent pass —
severity 4, 3, and 2 findings alike, not only the highest-severity subset:

- **PLAN-FIT-001 + PLAN-FIT-002 (severity 4, fixed together — same underlying gap)**:
  `research`'s checked-field set (2 fields: Research Question primary, Data Sources
  peer) silently narrowed spec.md's 3-name list (Research Context, Methodology, Data
  Sources) without saying why. Fix: added an explicit reconciliation to plan.md's
  Decision 1 stating `## Methodology` (research-plan-template.md:22) has no bold-field/
  table content of its own — only nested `###` subheadings — so it names a section, not
  a checkable field; the 2-field design is the accurate resolution, stated out loud, not
  a silent subset. Simultaneously, Decision 3(c)'s single nested-heading rule was split
  into its two real sub-shapes: (c-i) "repeatable instance" (`plan`'s Decisions — the
  container IS the field, any populated `### Decision D-N` suffices) vs. (c-ii)
  "specifically-named sibling" (`research`'s Data Sources — the container is the shared
  `## Methodology`, and the detector must locate the ONE nested heading matching the
  field's own name, not any sibling). Both fixed together per the review's instruction,
  since a coherent 2-field declaration for `research` only makes sense once Data
  Sources' own detection sub-shape (c-ii) is correctly distinguished from Decisions'
  (c-i) — fixing one without the other would have left an internal contradiction.
  Mirrors `research.md` §R4.1's own added reconciliation note.
- **PLAN-FIT-003 (severity 3)**: FR-005's "loud CLI signal" mechanism was an unnamed
  "e.g." Verified `mission.py` has zero rich/console/typer dependency and
  `get_mission_for_feature` has three call sites, only one of which
  (`mission_type.py`'s `active` command) is a CLI command with its own console. Fix:
  named the concrete existing mechanism — the single CLI-output seam
  (`specify_cli.cli.console.console`) `mission_type.py` already uses for the two
  sibling exceptions right next to this call — and scoped the loud-CLI-surface half of
  FR-005 to that one call site (the other two, `acceptance/__init__.py`,
  `core/worktree.py`, are not CLI modules and keep the unchanged `warnings.warn`
  signal). This is a declared, not silent, extension of #3831's C-003 file set to
  include `mission_type.py` — recorded in §Project Structure.
- **PLAN-FIT-004 (severity 2)**: `research.md` §R3's FR-004 follow-up issue
  description named the three-schema reconciliation problem but never carried forward
  C-002's specific reuse mandate. Fix: added one sentence to §R3 naming
  `resolve_existing_org_roots`/the org-roots precedence convention explicitly, so the
  constraint travels with the tracked issue rather than living only in this mission's
  own (closing) spec.md.
- **PLAN-SEQ-001 (severity 3)**: the campsite-clean comment fix instructed touching
  `_dn_composition_dispatch`'s docstring, which lives in `runtime_bridge.py` —
  undeclared in #3830's C-003 file set — while plan.md's own §Blast Radius claimed
  "strictly inside the touched file, no file-set growth." Fix: added
  `runtime_bridge.py` to §Project Structure (annotated comment-only, no functional
  change) and corrected the drift note / §Campsite-Clean Scope wording to state the
  campsite-clean commit touches two files, not one.
- **PLAN-VERIFY-001 (severity 4)**: the qa row of §Architectural Gate Non-Vacuity used
  "malformed/missing/unresolvable template" as its negative fixture — a different code
  path (error handling) from the four built-in rows' "unfilled/placeholder-only
  scaffold" shape, and inconsistent with §ATDD-First's own "fails when scaffold-only"
  text for the same FR cluster. Fix: changed the qa row's negative fixture to
  "unfilled/placeholder-only scaffold of `test-plan-template.md`" (matching the other
  four rows), and kept the malformed-template fail-closed behavior as an explicitly
  separate edge case, not a substitute. Re-read both sections after the fix — they
  now agree.
- **PLAN-VERIFY-002 (severity 3)**: FR-002 (distinguish a genuine
  `resolve_mission_type_context` failure from the "action in own sequence" branch) had
  no acceptance-test anchor in §ATDD-First, and the plan's prose claimed the fix
  "separates" the two cases when in fact removing FR-001's early return makes both
  converge on the same fallthrough call, adding no signal. Fix: added a dedicated
  FR-002 row naming the concrete mechanism (log the exception via the module's
  existing `logger`, `runtime_bridge_composition.py:101`, instead of a bare `pass`)
  and the observable before/after signal (log record present vs. absent), plus a
  RED-FIRST reproduction using a malformed-org-pack-triggered `UnknownMissionTypeError`.
- **PLAN-VERIFY-003 (severity 2)**: `research.md` §R5 paraphrased the CI
  `critical_paths` array inaccurately (blanket `dashboard/*` instead of the two actual
  entries; missing `src/charter/offering/*` as its own entry; `tasks_*` entries
  mis-attributed to `review/`). Fix: re-read `.github/workflows/ci-quality.yml`
  (L3370-3399) directly and replaced the paraphrase with the verbatim 15-entry array.
  Mission-scope conclusion unchanged (no fix-site file in this mission matches
  `dashboard/*` or the corrected entries).
- **PLAN-VERIFY-004 (severity 2)**: §Baseline Discipline's issue-filing bullet named
  the mechanism (classify against #3284, file a new issue) but not the charter's
  specific required content for that issue. Fix: added the charter's Pre-existing
  Failure Reporting Rule content requirement (command run, failure summary,
  pre-existing rationale) inline, so a WP implementer does not need a round-trip back
  to the charter text.

All 9 findings closed in this pass. No spec.md/tasks/checklists edits; only plan.md and
research.md changed, plus this tracer append.

## Round 2 (fresh sweep, `reviews/plan-fresh.yaml`, 4 findings)

- **PLAN-FRESH-001 (severity 3)**: Decision 1's peer field for `research` (`Data
  Sources`, a nested `### ` heading under `## Methodology`) forces the most complex new
  detector sub-shape (c-ii), when `## Research Context` — the SAME container as the
  primary field `Research Question` — already has five other bold-field peers
  (`Research Type`, `Domain`, `Time Frame`, `Resources Available`, `Key Background`)
  that would satisfy the AND/OR rule using only the already-generalized shape-(a)
  detector, at zero new detection cost. **Decision taken: kept `Data Sources` as the
  peer field (option (b) of the two offered), and added the missing reasoning to
  Decision 1** rather than switching to a cheaper in-Research-Context field. Rationale
  recorded in plan.md itself: spec.md's Decision 3 (BINDING) names `research`'s
  scaffolded fields as "Research Context, Methodology, Data Sources" and NFR-004
  independently forbids checking "a convenient subset"; swapping `Data Sources` — one
  of spec.md's three named fields — for an unnamed, cheaper-to-detect field purely for
  implementation-cost reasons would itself be the "convenient subset" NFR-004 bars, and
  is the same narrowing-for-convenience move ruling #1 (SPEC-FRESH2-001, severity 4,
  UPHELD) already rejected for `plan`'s fields. Ruling #1 also explicitly anchored
  `research`'s `Data Sources` to the same nested-heading detection `plan`'s `Decisions`
  needs, and ruling #2's carried-forward "Deferred to Plan Phase" list names nested
  third-level headings among the shapes this plan phase must detect for `research`
  specifically — so sub-shape (c-ii)'s cost was already an anticipated consequence of
  spec.md's own field list, not a plan-time choice this Decision could have dodged for
  free. Because option (b) was chosen (not option (a)), Decision 3's c-i/c-ii split, the
  Blast Radius table, the Architectural Gate Non-Vacuity table, and research.md §R4.1
  needed **no** structural changes — verified by grepping both plan.md and research.md
  for `c-ii`, `sub-shape`, `Data Sources`, and `specifically-named sibling` after the
  fix: every reference is intentional and consistent, none stale.
- **PLAN-FRESH-002 (severity 3)**: §Constitution Check still asserted a blanket "no
  violation identified" without naming that this mission's own round-1 fixes
  (PLAN-SEQ-001, PLAN-FIT-003) added two explicit extensions beyond spec.md's binding
  C-003 file-set enumeration (`runtime_bridge.py` for #3830, `mission_type.py` for
  #3831). Fix: added one sentence to §Constitution Check naming both files, the C-003
  deviation, and the Boy Scout Rule / Locality of Change justification already recorded
  elsewhere in the document (§Project Structure, §Blast Radius) — so the one section
  whose job is to surface governance deviations actually surfaces this one.
- **PLAN-FRESH-003 (severity 2)**: research.md §R3's follow-up-issue paragraph
  (extended by round-1's PLAN-FIT-004 fix) cited the ambiguous `runtime/resolver.py`
  where §R1.4 in the same document correctly cites the fully-qualified
  `src/specify_cli/runtime/resolver.py`. Fix: expanded both occurrences in §R3 to match
  §R1.4's path exactly. Verified directly: `src/specify_cli/runtime/resolver.py` exists;
  no `resolver.py` exists anywhere under `src/runtime/next/`.
- **PLAN-FRESH-004 (severity 1)**: plan.md §Decision 4 and research.md §R4.2 both
  miscounted `_PLACEHOLDER_PATTERNS` as 16 entries. Fix: re-counted the live tuple at
  `src/specify_cli/missions/_substantive.py:32-48` directly (17 `re.compile(...)`
  entries, tuple spanning lines 31-49) and corrected both citations to "17-entry"/"17
  entries"; the line-range citation (`:31-49`) was already correct and unchanged.

All 4 round-2 findings closed in this pass. No spec.md/tasks/checklists edits; only
plan.md, research.md, and this tracer append changed.
research.md changed, plus this tracer append.

## Round 3 fixes (plan-fresh-2)

- **PLAN-FRESH2-001 (severity 3)**: plan.md named FR-005's CLI fix-site as "the
  `active` command" in three places (the C-003/#3831 rationale table row, the
  `get_mission_for_feature` call-site paragraph, and the §Project Structure file-list
  comment for `mission_type.py`). No `active` command exists in
  `src/specify_cli/cli/commands/mission_type.py` — verified live: `grep -n
  "command("` shows only `current`, `info`, `create`, `run`, `close`, `reopen`,
  `follow-up`, `switch` (deprecated), `list`, `show`; the function at the previously
  cited line 132-133 is `@app.command("current")` / `def current_cmd(...)`. The cited
  supporting line numbers (`mission_type.py:190-197`) were already correct — only the
  command-name label was wrong. Fix: replaced all three "the `active` command"
  occurrences with "the `current` command (`current_cmd`)" / "`current`
  command/`current_cmd`", leaving the surrounding rationale and line citations
  unchanged.
- **PLAN-FRESH2-002 (severity 2)**: plan.md's Blast Radius "Drift note" and its
  Campsite-Clean Scope repeat both cited `runtime_bridge.py:1775-1777` for
  `_dn_composition_dispatch`'s stale C-008 docstring claim. Verified live via
  `sed -n '1775,1780p' src/runtime/next/runtime_bridge.py`: lines 1775-1776 are
  unrelated docstring prose; the actual claim ("C-008 hard-guards this on `mission ==
  "software-dev"`; every other mission falls through...") spans lines 1777-1779. Fix:
  corrected both occurrences of `runtime_bridge.py:1775-1777` to
  `runtime_bridge.py:1777-1779`.

Both round-3 findings closed in this pass. Re-swept plan.md and research.md for
`active command`, `` the `active` `` , `def active`, and `1775-1777`: zero occurrences
remain anywhere. No spec.md/tasks/checklists edits; only plan.md and this tracer
append changed.

## Round 4 (final) fixes (`reviews/plan-fresh-3.yaml`) — early-stop, one verification pass follows

- **PLAN-FRESH3-001 (severity 3)**: §Project Structure's `runtime_bridge_composition.py`
  line was labeled `# FR-001, FR-002 (comment fix too)`, bundling the :127 stale C-008
  comment fix into the same annotation as the functional FR-001/FR-002 diff — while its
  sibling `runtime_bridge.py` line in the same table was already correctly labeled
  campsite-clean-only (round 3's PLAN-FRESH2-002 fix touched that line's citation but not
  its sibling's framing). This contradicted §Campsite-Clean Scope, which requires both
  files' stale comments corrected together in ONE preceding, distinct,
  behavior-preserving commit (Standing Order #2). Re-verified §Campsite-Clean Scope and
  §Suggested Work Package Sequencing directly: both already state the single preceding
  campsite-clean commit covers both files — only §Project Structure's own line was out of
  step. Fix: reworded the line to `# FR-001, FR-002; the :127 C-008 comment fix lands in
  the campsite-clean commit (see §Campsite-Clean Scope), not bundled into the FR-001/FR-002
  diff`, matching the remediation text and the sibling line's explicit-separation style.
  No other section needed a change.
- **PLAN-FRESH3-002 (severity 3)**: Decision 3(a) claimed `documentation`'s Technical
  Context needs zero new detector work (same shape as software-dev, fully covered by the
  generalized bold-field peer scan). Verified directly against
  `packs/built-in/missions/documentation/templates/documentation-plan-template.md`: three
  of the four declared peer fields (`Languages Detected`, `Output Format`, `Hosting
  Platform`) do have inline same-line values, but `Build Commands` (L24) writes its value
  as a bulleted sub-list on L26-28, below the label — the existing/generalized shape-(a)
  regex (`_substantive.py:186`, `(?P<val>[^\n]*)`) only captures same-line text, so a
  faithfully-populated `Build Commands` field reads as empty. Also verified: `Generator
  Tools` (L16, sub-list on L18-20) has the identical shape but was never in documentation's
  declared peer-field set to begin with. **Decision taken: option (a)** — extended
  shape-(a)'s own value-capture behavior (a new declared per-field flag: inline-valued vs.
  sub-list-valued, added to Decision 1's per-type declaration) to also read a field's value
  from an immediately-following bulleted sub-list when its same-line value is empty, rather
  than inventing a fourth shape or a second detector, or excluding `Build Commands` from
  the checked set. Chosen over option (b) (exclude `Build Commands` and narrow NFR-004's
  documentation field list) for the same reason round 2's PLAN-FRESH-001 kept `Data
  Sources` as `research`'s peer field over a cheaper substitution: NFR-004 forbids checking
  "a convenient subset," and `Build Commands` is one of spec.md/NFR-004's own named
  checkable fields — narrowing it away for detector-cost reasons would be exactly the
  convenience-driven move that rule bars, even though (as in round 2) the chosen option
  costs more implementation surface than the alternative. `Generator Tools` was left
  outside the declared field set, unchanged (that omission pre-dates and is independent of
  this defect — adding it would be a scope expansion beyond what this finding raised, per
  Locality of Change), with a note that the same extension would cover it for free if a
  future revision adds it. Updated: Decision 1 (declaration now records inline-vs-sub-list
  value shape), Decision 3(a) (the value-capture extension itself, plus the Generator Tools
  note), Decision 3's reuse-principle paragraph (one sentence confirming this stays a
  generalization, not a fourth shape), the Architectural Gate Non-Vacuity table's
  `documentation` row (WP test plan must include a `Build Commands`-only positive fixture
  so the AND/OR rule's other inline-valued peers can't mask a regression in the new
  extension), and `research.md` §R4.1's `documentation` row (shape distinction + Generator
  Tools note). Verified consistency: grepped plan.md and research.md for `Build Commands`
  and `Generator Tools` after the fix — every occurrence in both files agrees `Build
  Commands` stays checkable via the new extension and `Generator Tools` stays
  intentionally undeclared; none stale or contradictory.

Both round-4 findings closed in this pass. No spec.md/tasks/checklists edits; only
plan.md, research.md, and this tracer append changed. Per the early-stop rule (severity≥3
count did not decrease round-over-round), this is the last fix round — one verification
pass follows, no further fresh sweep.
