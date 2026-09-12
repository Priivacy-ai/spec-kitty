# Specification Quality Checklist: Read-Side Seam: Placement-Authority Closure

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-28 · **Revalidated**: 2026-07-28 after two scope revisions (see Provenance note)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *see Note 1*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders — *see Note 1*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (zero markers; every open scope question was resolved by an explicit operator decision before authoring)
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries (FR-001…020, NFR-001…011, C-001…009)
- [x] All requirement rows include a non-empty Status value (all `Open`)
- [x] Non-functional requirements include measurable thresholds — *see Note 2*
- [x] Success criteria are measurable (SC-001…017 are counts, identity assertions, or binary gate outcomes; the comprehension check moved to US7's Independent Test)
- [x] Success criteria are technology-agnostic — *see Note 1*
- [x] All acceptance scenarios are defined (7 user stories × 3–4 scenarios each)
- [x] Edge cases are identified (10 across 8 bullets, including the backfilled composed-handle divergence and the foundation-site recursion hazard)
- [x] Scope is clearly bounded (explicit Out of Scope section + C-006 scope boundary + C-004/FR-005 naming what is deliberately *not* touched)
- [x] Dependencies and assumptions identified (Assumptions section, 5 entries, each either independently verified or explicitly scheduled for re-derivation)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to a user story whose Acceptance Scenarios are the criteria)
- [x] User scenarios cover primary flows (single placement authority, delegation-surfaces-the-delta, no-green-by-omission, husk protection, ledger integrity, residual + record closure, and design-doc-instead-of-rediscovery)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification — *see Note 1*

## Notes

**Note 1 — "no implementation details" / "non-technical stakeholders" / "technology-agnostic", in context.**
This is an infrastructure mission in a developer-tooling repository: the product
surface *is* code and architectural gates, and the primary actor is a
maintainer/agent, not an end user. The spec names code surfaces where they are the
*subject* of a requirement, not as an implementation choice, and it does not prescribe
diff shapes, control flow, or new APIs. Context & Motivation and Domain Language carry
a plain-language account of PRIMARY/COORD partitions, "semi-compliance", and the
husk, so a stakeholder who has not followed the programme can read it. `meta.json`'s
`purpose_tldr` / `purpose_context` are written for that reader. Matches the
established pattern for this repo's infrastructure missions. PASS with rationale
recorded rather than silently ticked.

**Note 2 — NFR thresholds are identity / zero-count / enumerated-condition assertions.**
The mission changes no performance characteristic, so the meaningful thresholds are
equality and zero-count claims: identical resolved directory for materialized
missions (NFR-001), zero new raises (NFR-002), enumerated gate-bite conditions
(NFR-004), no site passing by omission (NFR-005), recorded before/after integers for
any floor that moves (NFR-007), and no cycle in the resolver call graph (NFR-009).
Each is mechanically checkable.

**Note 3 — Provenance: two scope revisions, both evidence-driven.**

*Draft 1* inherited #3014's premise. A two-lens post-spec squad (architect + patterns)
returned **10 MAJOR findings** against the live tree, three falsifying that premise:
`primary_feature_dir_for_mission` is already censused (on the *anchoring* axis) by
`test_resolution_authority_gates.py`; its **fail-loud** surface is zero; and a
*fourth* kind-blind resolver (`resolve_feature_dir_for_mission`, 8 sites / 7 files) is
the genuinely unpoliced gap. The squad also **executed** the prescribed ledger
restructuring and showed it parses *silently vacuously*, showed the stay-lenient index
cannot represent a multi-site qualname, and showed that deleting the `#2214` pin reds a
test by construction.

*Draft 2* (honest-reframe, operator-chosen) dropped the vacuous fail-loud migration and
kept record-correction + policing the real gap.

*Draft 3* (this one) followed the operator's question — do the "already policed" sites
route through the seam, or are they semi-compliance with a hardcoded target? A
placement-authority audit established: the 34 sites pass a canonical *handle* (all the
floors check) while **hardcoding the partition at the call site**;
`read_dir(<PRIMARY kind>)` is answer-equivalent across eight real-repo fixtures and
**strictly better** on a backfilled mission (the blind composition returns a
non-existent path); the 33 compositions are hand-inlined resolver internals
(`resolve_planning_read_dir`'s PRIMARY leg *is* that composition); the six "lands on the
husk" comments argue against a *different* resolver and do not survive as an argument;
and the floor collision is bookkeeping with five recorded in-tree shrinks, one for this
exact routing move. The operator prescribed **delegate-then-remove** and chose to carry
both steps here. Two live gate holes were found and folded in as FR-001 (a canonicalizer
the fold set does not recognise, and allow-sets that would let migrated sites go
green-by-omission).

Every MAJOR is now a requirement or a constraint: FR-008/009 (grammar and index
prerequisites, before any rows), FR-014 (paired pin + pin-existence-test retirement),
FR-016 (record correction), FR-017 (honest bounds), FR-005 + NFR-009 (foundation sites
stay out; no resolution cycle), NFR-004 (per-primitive non-vacuity), NFR-005
(no green-by-omission), NFR-007 (honest floor accounting), C-004 (privatise, never
delete), C-005 (delegation is a hard sequencing gate). Note that C-004's meaning is
**reversed** from draft 2, where it excluded the primitive from scope.

**Note 4 — Two facts in the source issues were corrected, not inherited.**
(a) #2824's functional defect was already fixed (`6923d1d40`, regression-green,
independently re-verified) and its *suggested* fix would have broken `lanes.json`
placement — recorded as C-001. The issue was closed with that evidence; only its
comments remain in scope (FR-015). (b) #3014's census figure (40) is stale in both the
ledger and the gate docstring; FR-016 re-derives and corrects it rather than
trusting the issue text. The corrected findings were posted to #3014.

**Note 5 — Size and sequencing.**
24 FR / 11 NFR / 11 C / 21 SC across eight user stories is larger than a typical mission
here. The tasks phase should expect roughly 10–12 work packages, with **three** hard
sequencing gates at constraint level: the grammar/index prerequisites (FR-008/009) before
any ledger rows (C-009), the delegation before any call-site rewrite (C-005), and the
tidy-first extraction before the delegation (IC-00, which exists because delegating
without it is literal infinite recursion). The floors are retired at the **start** of
Step 2 — IC-0T — because their strict bound breaks at roughly the fifth routed site
(NFR-007).

**Note 7 — Quick post-spec squad (2026-07-28): 6 MAJOR folded, spec is draft 4.**
A two-lens quick pass on the *new* material found 6 MAJOR. **Document coherence (renata):**
`SC-005`/`FR-011` were **conditionally vacuous** — a zero-fail-loud census would have
satisfied them with zero work and silently evaporated User Story 4, which is exactly how
draft 1 died on the *other* primitive; `FR-010` now records per-disposition counts and
`SC-005` carries an explicit zero-case discharge. The FR table's "User Story" column held
narrative rather than story ids, so the Feature-Readiness claim was unverifiable and
`/plan` could not see the mapping; the table now carries a `Story` column (US1…US7, no
orphans either way). **SSOT (paula):** my asserted three-layer split **misdescribed the
code in two load-bearing ways** — the decision layer is *two* functions whose divergence
is deliberate (`declared_read_surface` is materialization-blind precisely so it can
disagree with a resolved stamp, which is what makes the `surface_cannot_hold`/#2906 guard
possible), and `translate_surface` **selects** an already-discovered location rather than
assembling a path. Publishing the original description would have taught readers to
strangle through `translate_surface` and re-add discovery at the call site — *causing* the
misappropriation the page exists to prevent. `docs/architecture/branch-target-routing.md`
already asserts per-artifact-kind placement rules in retired vocabulary, so FR-020 now
narrows it in the same slice instead of leaving two authorities. The glossary home is
pinned to the prose glossary + `CLAUDE.md` Canon (the doctrine pack and seed are
byte-frozen by a SHA + term-count pin and a parity gate). And "routing" has **≥10** senses,
not 5 — governed senses now include model/task routing (the highest-collision sense in
agent-authored prose) and scope routing, with the infrastructural senses scoped out by
name. Minors folded: docs registries corrected to the gated ones, explanatory-only +
`module:symbol` citation discipline, filename `artifact-placement-seam.md`, anchor
stability, 33-vs-34 reconciled, slug/title note, Given/When/Then completion, and SCs added
for previously uncovered FRs.

**Note 6 — New IC added at operator request (2026-07-28): document the seam.**
FR-018/FR-019 add the operator-requested implementation concern — *"update the
architecture docs to describe the routing/decisioning seam, and formalize the split
between runtime, decision module, path resolution"* — as a first-class deliverable
rather than a follow-up. Rationale: the seam has been repeatedly misappropriated as a
"stable API to strangle through", and the discovery cost of re-establishing the layering
has now been paid three times (a follow-up filed on a false premise, two spec
re-framings, and a full operator-guided audit) even though the governing decisions
already existed. Grounding checked before writing the requirement: ADR `2026-06-24-1`
(kind-and-topology-aware placement) and ADR `2026-07-23-1` (`TopologySurface`
vocabulary) already state the principle — the latter even names the forbidden
conditioning pattern that *is* this mission's semi-compliance shape — so the gap is a
findable **explanation**, not a missing decision. `docs/architecture/branch-target-routing.md`
already owns the *branch* sense of "routing", and the glossary already defines
`PRIMARY partition`, `COORD partition` and `Topology Surface`; FR-018/019 therefore
require alignment and cross-reference (NFR-011) rather than a competing vocabulary, plus
docs-hygiene compliance for a new page (NFR-010). Verified as a comprehension outcome
(SC-012) rather than a "page exists" checkbox.

**Note 8 — Suite-expectations WP + doctrine grounding (2026-07-28, operator-directed).**
Three additions, all at the operator's instruction, after two model-disciplined doctrine
scouts swept all 23 activated artefacts.

*(a) The suite as the acceptance signal.* US8 + FR-023 make an early "re-express the suite's
expectations against the target design" work package explicit, and IC-0T is its plan-side
concern. The operator's own bar is now the DoD: it is *only* a good acceptance signal **if
the tests are updated adequately** — so every remaining red must manifest in an
**assertion** traceable to a named FR, with **zero collection errors introduced**, and the
expected-red node list is recorded so later WPs can demonstrate the intended greens. This
is also where the two use-count floors are retired, which converts "the floors break around
the fifth routed site" from a timing hope into a structural fact. Grounded in
`DIRECTIVE_034` (a red must go red *in the assertion*, not at import) — two of the mission's
worst frictions are precisely collection errors.

*(b) Doctrine grounding.* FR-024 + C-011 + the plan's new **Doctrine grounding** section
cite the refactor-specific artefacts. The load-bearing finding: all of them are **activated
but wired to no action index**, so an implementer receives *none* of them from charter
context — they reach execution only via an explicit `Run: spec-kitty charter context
--include <kind>:<id>` citation in the WP body (the command is activation-exempt and exits
non-zero on a bad id, so a wrong citation is self-detecting). The chain that matters:
`tactic:refactoring-change-function-declaration` **is** delegate-then-remove (C-005/FR-006
are that tactic, not a local invention); `tactic:canonical-source-unification` step 5 —
*"do not leave a non-canonical copy as a fallback"* — is the doctrinal case for deleting the
wrapper; `DIRECTIVE_041` supplies the disposition taxonomy the ledger had been restating;
`DIRECTIVE_025` bounds IC-00's tidy-first extraction. C-011 forbids the two tempting
propagation shortcuts: a new WP frontmatter key (`WPMetadata` is `extra="forbid"` — it
raises and breaks workspace resolution) and the mission-type action index (permanent,
mission-type-wide over-broadcast, and inert on the implement route anyway).

*One genuine doctrine-vs-doctrine tension surfaced and is adjudicated in the plan:*
`DIRECTIVE_043` (`enforcement: required`) demands a concrete gate floor, while FR-007
retires two. Resolution: non-vacuity is **preserved by transfer** — the retired floors count
uses of a symbol being deliberately drained, so post-migration they assert only that the
resolver calls its own assembler; the guarantee moves to the bypass census, which carries
its own floor, per-primitive non-vacuity, alias resistance and a shrink-only allow-list.
The retiring commit must say so, citing both artefacts.

*Doctrine gaps recorded, not fixed:* the **semantic-compression** family (the best fit for
"behaviour-preserving with one named delta", and the only home of "characterization test")
is unactivated here; no artefact adjudicates tensions of this shape; `agent action
implement` does not forward the WP's `agent_profile` into charter context though `dispatch`
does; and activated directives can be silently pruned out of an action's resolved context
via non-activated intermediate paradigms.

*(c) Foreign honest-red P0s are out of scope (C-010).* Missions have landed on
`upstream/main` carrying deliberately-red P0 pins — live on our base:
`tests/sync/test_sync_consent_default_deny.py` (#3031, red by design per ADR
`2026-07-17-1`, and marked `fast` so implementers **will** see it, on
`sync/routing.py` — the *sync fan-out* sense of routing, zero surface overlap). The
classification rule is **by surface, not by timing**: a red is this mission's business only
if it touches a placement/read-path surface the mission owns, or is a demonstrable
regression from this mission's diff. Never green-wash a foreign P0; never let its presence
justify widening scope.

- Items marked incomplete require spec updates before `/spec-kitty.plan` — none are incomplete.
