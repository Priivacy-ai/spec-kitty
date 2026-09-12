# Specification Quality Checklist: Doctrine Behavioral Suite

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  — Note: this mission is itself an infrastructure/tooling mission (a
  conformance suite over a real adapter's source), so FRs necessarily cite
  real file paths, function names, and line numbers as normative citations
  and verification anchors. This is consistent with house style for this
  programme's prior missions (M7) and is treated as evidence, not
  implementation prescription — the spec does not dictate *how* the
  generator script or manifests must be written beyond what's needed to
  make each verification command meaningful.
- [x] Focused on user value and business needs — the mission's value (a
  maintainer learns whether a profile's declared boundaries hold under a
  real model) is stated in the Overview and User Scenarios.
- [x] Written for non-technical stakeholders — Overview and User Scenarios
  sections carry the stakeholder-facing framing; verification detail is
  scoped to the Requirements table where testability is the point.
- [x] All mandatory sections completed (User Scenarios & Testing,
  Requirements, Success Criteria).

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — all prior open questions
  (OQ-3, OQ-7, OQ-8, FR-004's tool-calling question) are resolved as
  decisions in the "Open Questions Resolved as Decisions" section, with
  rationale recorded either there or in the relevant FR's own text.
- [x] Requirements are testable and unambiguous — every FR/C row states a
  verification command, expected exit code/output, and falsification
  condition.
- [x] Requirement types are separated (Functional / Constraints) — no
  Non-Functional Requirements table is present; this mission has no
  requirement that is not either a functional behavior (FR) or a hard
  boundary (C) — measurable-threshold requirements that might otherwise be
  NFRs (runs ≥ 5, passThreshold formula) are folded into FR-006 since they
  gate that FR's own acceptance, not a standalone quality attribute.
- [x] IDs are unique across FR-### and C-### entries (FR-001..009, C-001..005,
  no collisions). The Charter Compliance table's citations to the charter's
  own numbered items are displayed with a `CHTR-` prefix (CHTR-003/004/
  007/011) specifically so they never collide, in raw text, with this
  mission's own C-003/C-004 (which name unrelated things), and never read as
  phantom, unmapped mission constraints either (the other two charter items
  have no defining row anywhere in this mission's own Constraints table) —
  `finalize-tasks` scans the whole document for `FR`/`NFR`/`C`-numbered
  tokens and cannot otherwise tell a foreign ID from one of this mission's
  own. Verified by a whole-document regex scan: zero bare foreign FR/NFR/C
  tokens remain outside FR-001..009/C-001..004.
- [x] All requirement rows include a non-empty Status value (`Proposed`
  throughout — pre-implementation).
- [x] Success criteria are measurable (SC-001..006 each name a concrete,
  checkable condition — SC-006 added during remediation, see Notes).
- [x] Success criteria are technology-agnostic in intent, though this
  mission's own subject matter is a conformance harness over named source
  files — the same accepted trade-off as the Content Quality note above.
- [x] All acceptance scenarios are defined (User Scenarios section, Given/
  When/Then form).
- [x] Edge cases are identified (all-refusal transcripts, weak models, dead
  endpoints, judge leniency).
- [x] Scope is clearly bounded (Scope Guard section).
- [x] Dependencies and assumptions identified (Dependencies & Assumptions
  section, including the real state of muster's open issues #75/#76/#77/#78/#82).

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (verification
  command + expected result + falsification condition per row).
- [x] User scenarios cover primary flows (cadence run, discrimination proof,
  directive-attached probes).
- [x] Feature meets measurable outcomes defined in Success Criteria.
- [x] No implementation details leak into specification beyond the citation
  style accepted above (real paths/line numbers as evidence, not prescribed
  code structure).

## Notes

- This spec corrects six citation/design errors found in the source GitHub
  issue (`MOES-Media/spec-kitty#24`) by direct inspection of both the
  spec-kitty and muster trees before drafting — see Overview, "Corrections
  against the source issue." None were left standing uncritically.
- FR-004's original "verification spike" framing is resolved directly rather
  than deferred to a WP, since the underlying fact (no tool-calling in the
  `openclaw-sop` adapter) was independently confirmed during spec drafting.
- **Post-draft remediation pass** (this pass): an adversarial squad found
  eight defects in this spec's own verification commands and acceptance
  coverage after the initial draft passed this checklist unchanged. All
  eight were fixed, each corrected command run for real against a
  constructed passing fixture and its rejection case (a live local
  OpenAI-compatible endpoint for FR-007's healthy/dead pair; synthetic
  JSON/YAML fixtures matching the real schema for the `jq`/`yq`/`grep`
  checks): FR-007's healthy-endpoint command was missing
  `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY` (and so was
  indistinguishable from a dead endpoint — swept into FR-002/003/004 and
  User Scenario 2 as well, which had the same omission); FR-001..004 had no
  gate requiring a real credentialed run before acceptance (added SC-006 and
  the "Acceptance Gate: One Live Credentialed Run" section); C-002/FR-007
  never required the dispatch workflow to actually invoke any manifest
  (extended C-002, and extended FR-007's `runsErrored` gate from the
  control-suite job only to the main-suite job as well); FR-006's `yq`
  paths targeted fields that don't exist in the real `SOP_RULE_MANIFEST_
  SCHEMA` (corrected to the real flat `rules[].k`/`rules[].aggregation`,
  with a `ruleId`-prefix convention replacing the nonexistent `category`
  field) and its `sort -u` asserted nothing (replaced with a real `yq -e`
  assertion); FR-005's falsification predicate was an unconditional no-op
  (replaced with a walk of `runs[].grades[].assertionKind`); FR-008's grep
  used a GNU-only BRE alternation extension (switched to portable `grep
  -E`, with the literal `+` in `model+context` escaped so the switch to ERE
  doesn't turn it into a quantifier); FR-009's two-run diff could not catch
  a no-op generator that ignores its input (added an input-sensitivity
  check requiring output to change when input does). A ninth issue —
  bare foreign `C-0xx` charter-citation tokens colliding with this
  mission's own numbering in a way that would confuse `finalize-tasks`'s
  whole-document ID scan — was found and fixed during the same pass (see
  the "IDs are unique" item above).
- **Post-plan remediation pass** (this pass): the plan phase (`plan.md`)
  found seven further defects by reading the rubric doc and hand-tracing
  muster's runtime, re-verified here directly against muster `main@8ce12906`
  and this checkout, not merely restated: (1) FR-004 tested tool
  authorization, which `docs/rubric/spec-kitty-behavioral-axes.md` §2.1
  states plainly is "not decidable by any judge" — reframed to grade §2's
  real domain-scope-containment axis, and the Dependencies section's
  previously-silent exclusion of FR-004 made explicit and resolved; (2)
  FR-006's blanket `passThreshold: ceil(k/2)` guidance could never legally
  apply to a `pass-k` row (`manifest.ts:299-306`'s validator) and, if
  `passThreshold` were omitted instead, silently degrades to majority-vote
  grading at runtime (`runner.ts:305,566`) — corrected to a matched-pair
  rule per aggregation tier, and the pass-k/safety-critical tier extended to
  `CAPABILITY-CONTAINMENT-*` per the rubric doc's own Aggregation Summary
  table. **Fixing (2) surfaced a tenth broken verification command**: the
  plan's own proposed `yq` check for this, `(.passThreshold // .k) == .k`,
  is a vacuous tautology that reads `true`/exit `0` even when
  `passThreshold` is omitted entirely — verified empirically against a
  constructed fixture before being replaced with a `has(...)`-gated form.
  (3) added C-005 (Integration Contract excerpt), a rubric-binding
  requirement no FR-001..004 verification cell previously checked; its
  exemplar command as originally proposed also had two bugs (jq bracket
  syntax for the hyphenated `avoidance-boundary` key, and a missing `-r` for
  raw output), both caught and fixed the same way, an **eleventh** broken
  command. (4) FR-007's script path collided with lane-a's write_scope —
  relocated to a new lane-b-owned `conformance/behavioral/scripts/`
  directory, and the Lanes section (which had gone stale relative to
  `plan.md`) updated to match. (5) FR-009's generator has a demonstrated
  (reproduced live against this checkout, not hypothetical) import-shadowing
  risk — added the `sys.path`-prepend and direct-`AgentProfile`-construction
  requirements to FR-009's own text. (6) C-002's `ls` file-set cross-check
  cannot run inside either lane's own worktree — made explicit, alongside
  the existing SC-006 live-run gate's same post-merge timing. (7) a
  precision note on `buildSopClient`'s actual no-op-fallback gating variable
  (`MUSTER_ENDPOINT` alone). None of the seven change an FR's stated
  user-observable behavior. `plan.md`'s own Verification Strategy table
  carried copies of the same two broken commands from items (2) and (3);
  both fixed there as well during this pass.
