# Spec-phase HALT ruling #2

**Mission**: `custom-mission-type-second-class-citizens-01M1FQXD`
**Phase**: spec
**Ruling by**: orchestrator
**Date**: 2026-09-02
**Trigger**: second HALT. Fresh sweep 3 returned SPEC-FRESH3-001 at severity 4.

## SPEC-FRESH3-001 is UPHELD, and it caught an error in ruling #1

Verified first-hand against `src/specify_cli/missions/_substantive.py:158-195`.
`_has_substantive_technical_context` performs **two** independent hardcoded matches:

```python
section   = re.search(r"##\s+Technical Context\s*\n...", body)      # literal 1
if section is None: return False
lang_match = re.search(r"\*\*Language/Version\*\*[ \t]*:...", sec_body)  # literal 2
if lang_match is None: return False        # returns BEFORE any peer scan
```

Ruling #1 asserted that `Scope — MoSCoW` "needs **no new mechanism** … what it needs is
for the heading name to be a parameter". **That was wrong.** Parameterising the heading
leaves `**Language/Version**` hardcoded, so the primary-field check still fails for every
type whose template does not use that exact label. `documentation` is the proof: it uses
the literal heading `## Technical Context`, needs zero heading parameterisation, and still
cannot pass. Heading was never the whole mechanism.

The error was mine — asserted from a finding's summary rather than read from the source.
The squad caught it, which is the loop working as designed. Recorded here rather than
quietly corrected.

## But the remedy is NOT to specify the mechanism more precisely

Two HALTs, both on mechanism detail, is the signal — and ruling #1 said as much: "a spec
that cannot converge in bounded rounds is a signal about the spec, not a budget to spend."
That signal has now fired twice. Reading the artifact, the cause is structural:

**The spec is designing the detector.** FR-006 currently pins the regex strategy per field
shape, which existing function to generalize, which literal to parameterize, and the exact
call-site routing. NFR-004 and User Story 3 / Acceptance Scenario 5 restate the same
mechanism a second and third time. So each fresh sweep audits a *design* rather than a
*requirement*, correctly finds another gap in it, and the spec grows another paragraph of
implementation detail. That regress does not terminate, and each round makes the artifact
harder to review — Acceptance Scenario 5 is now a single 400-word sentence.

It also violates the doctrine this mission is meant to uphold: a list restated in three
places drifts in one of them, and FR-006/NFR-004/AC5 are three statements of one mechanism.

## Direction — move the mechanism to the plan phase

**Keep in the spec (behaviour and acceptance):**
- FR-006 reduced to intent: the plan-substantive check derives its required fields from the
  mission type's OWN resolved plan template, rather than the hardcoded `## Technical
  Context` + `**Language/Version**` shape specific to `software-dev`. Decision 1's
  name-based guard remains explicitly rejected.
- The combination rule — **primary field AND at least one peer** — stays. It is behaviour,
  it mirrors the existing `Language/Version`-plus-a-peer semantics, and the plan phase
  needs it as a constraint.
- NFR-005's non-vacuity requirement stays: for **every** mission type the gate must be able
  to pass AND to fail. No type structurally exempted, no neutral pass.
- Per-type acceptance criteria stay, expressed as outcomes: for each of `software-dev`,
  `documentation`, `research`, `plan`, a faithfully-populated plan passes and an unfilled
  scaffold fails. **State the expected outcome, not the detector that produces it.**
- The corrected scope statement stays (three of four built-in types affected, #3832 as
  filed understates it).

**Move to the plan phase (explicitly, as named open design questions):**
- Which section each mission type's template designates for this check, and how that is
  determined.
- How the primary field label is obtained per type — note for the plan phase that **both**
  the heading and the primary label are hardcoded today, so both must be addressed.
- Per-shape detection (tables / bulleted bold fields / nested third-level headings).
- Placeholder-pattern coverage for `research`/`plan` bracket vocabulary.
- Call-site routing in `mission_setup_plan.py`.

Record these in the spec as a short "deferred to plan phase" list naming each question in
one line. Do not answer them in the spec.

## Scope of this resume — final for the spec phase

Perform the reduction above. Fix nothing else. Do **not** re-open: Decisions 1 and 2, the
four-type table (closed, re-verified five times), the #3831 go/split checkpoint, or the
corrected-scope statement.

Then run **one** verify pass confirming (a) the reduction preserved every behavioural
requirement and acceptance outcome, and (b) no mechanism prescription survives in FR-006,
NFR-004 or AC5. **No further fresh sweep on mechanism detail** — the mechanism is no longer
in the artifact, so a sweep for gaps in it has nothing legitimate to find.

If that verify pass fails, HALT and report. Otherwise the spec phase is PASSED: commit and
proceed to the plan phase, carrying the deferred-questions list forward as the plan's
opening agenda.

## Note on rounds spent

Three fix rounds and two HALTs on one artifact is expensive, and roughly half of it traces
to ruling #1's factual error plus a spec that was over-specified before the squad ever saw
it. Both are orchestrator faults, not phase-agent faults. The phase agent followed every
bound it was given, stopped exactly where it was told to stop, and independently verified
the finding against source before accepting it — which is why the error surfaced at all.
