# Spec-phase HALT ruling

**Mission**: `custom-mission-type-second-class-citizens-01M1FQXD`
**Phase**: spec
**Ruling by**: orchestrator
**Date**: 2026-09-02
**Trigger**: fresh sweep 2 returned 3 findings, one at severity 4; protocol early-stop
fired because the severity≥3 count did not fall round-over-round (6 → 1 → 1).

The early-stop was correct and the finding is upheld. This ruling directs a bounded
resume; it does not waive any finding.

## SPEC-FRESH2-001 (severity 4) — UPHELD. Take remediation (a): cover all four fields.

Reject option (b) (narrowing NFR-004/FR-006/AC5 to the two table-shaped fields).

**Ground**: the operator's Decision 1 chose derive-from-template *specifically over* the
name-based guard, because the name-based guard "abandons the check for every
non-software-dev type rather than fixing it". Narrowing `plan`'s check to 2 of its own 4
scaffolded fields reintroduces the same defect one level down — arbitrary partial
coverage, justified by an implementation convenience rather than by what the mission type
declares. A mechanism that silently checks half of what a template scaffolds is the
"check that cannot fail" class this repo's own standing orders exist to prevent.

**The finding also shows (a) is cheaper than the note assumed**, which removes the usual
reason to prefer narrowing:

- `Scope — MoSCoW` needs **no new mechanism**. It is a bulleted `- **Field**: value` list,
  and `_substantive.py:180-186`'s peer-field regex already tolerates a leading `- `/`* `
  marker (the FR-013/#1896 fix). What it needs is for the heading name to be a parameter
  rather than the hardcoded `Technical Context` literal.
- `Decisions` needs the **nested-heading scan already being specified** for research's
  `### Data Sources`. Plan's `### Decision D-1` under `## Decisions` is the same
  nested-not-sibling shape. Extend that scan's scope; do not invent a second one.

So the true remaining work is one generalisation (parameterise the heading) and one scope
extension (point the nested scan at both), not two new detectors.

**Also correct the note's false premise.** "Plan's sections are tables" is empirically
false for 2 of 4. State which shape each of the four fields actually has, and that the
mechanism dispatches on shape, not on mission type.

## The AND/OR rule — resolve it as: primary field AND at least one peer

The spec must state this explicitly; leaving it unstated is half the finding.

**Mirror the existing semantics rather than inventing a second rule.**
`_has_substantive_technical_context` today requires `Language/Version` **plus at least one
peer field** — one designated primary, plus evidence the section was genuinely filled in.
Generalise exactly that shape: for each mission type, the template's first scaffolded
field is the primary and must be substantive, plus at least one peer field from the same
section.

This follows the charter's **single canonical authority** principle — extend the existing
rule to a new axis rather than adding a competing one. Requiring ALL scaffolded fields
would be stricter than software-dev is held to today and would fail authors who
legitimately leave one section thin; requiring ANY ONE would make the gate near-vacuous.

## SPEC-FRESH2-002 and -003 (severity 2 each) — UPHELD, fix both

- **-002**: correct the citation range for `_has_substantive_technical_context` to its
  real close (`:195`, not `:186`). A citation that stops mid-regex is exactly what the
  correspondence lens exists to catch, and this mission's own spec must survive its own
  standard.
- **-003**: split NFR-005's conflated rationale. A bold-field scan run against a table
  **fails closed** (returns False); it does not "accept placeholder text". Those are two
  different failure modes and the sentence asserts a causal link between them that does
  not hold.

## Scope of the resume — bounded

Fix these three findings only. Do **not** re-open settled material: the four-type template
table is re-verified TRUE five times over and is closed; Decisions 1 and 2 stand as the
operator gave them; the #3831 go/split checkpoint stays a plan-phase question.

Then run **one** verify pass over the three fixes plus **one** fresh sweep. If that sweep
returns any finding at severity ≥3, HALT again and report — do not enter a fourth round.
Rounds are capped; a spec that cannot converge in bounded rounds is a signal about the
spec, not a budget to spend.

Commit the full `reviews/` trail, including this ruling and the currently-uncommitted
`spec-fresh.yaml`, `spec-fresh-2.yaml`, `spec-verify.yaml`.

## Note on the lens-catalog deviation

The phase agent reported the task brief named spec lens groups `gov|arch|complete` while
the sk overlay's actual catalog is `gov|arch|verify`, and followed the overlay per its
stated precedence. **That was correct** — the overlay wins on conflict, and the brief was
wrong. The error is mine, recorded here rather than corrected silently.
