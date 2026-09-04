# Operator ruling — tasks phase HALT, mission `spdd-reasons-activation-split-brain-01M1K6VN`

Date: 2026-09-03. Issued by the operator (Human-in-Charge) via the mission orchestrator.

The tasks phase HALTed under the R6 early-stop rule. The severity>=3 count across rounds ran
3 -> 1 -> 2: every confirmed finding was fixed and verified resolved, but each round's R5b fresh
sweep surfaced new material in a large artifact (5 work packages, ~120KB of work-package prose).
The loop stopped rather than sampling for a lucky pass. Two findings survive, recorded in
`reviews/tasks-fresh-2.yaml`.

**This ruling REPLACES the acceptance bar for the tasks phase.** A verifier handed the original
bar would re-derive the original verdict and HALT the mission a second time on a question already
answered.

## The pattern that drove this ruling

Three consecutive rounds each surfaced a distinct instance of **one class**: an absent or
un-normalized input silently collapsing to a wrong value instead of the correct one, with no
fixture pinning the failure.

1. `TASKS-VERIFY-001` — WP04 fixtures permitted keeping legacy `governance:` writes, so rewrites
   passed against old and new code alike (a bug-preserving fixture).
2. `TASKS-FRESH-001` — WP02 T009 collapsed an absent `pack_context` to empty sets instead of
   catalog defaults.
3. `TASKS-FRESH2-001` — WP02 T009 drops the `_normalize_directive_id` step that currently happens
   implicitly via `_load_doctrine_selection`'s pre-union.

Instance 3 is the severe one because it reproduces Decision Record 2's own **silent incorrect
exclusion** mechanism through a new path: a stem-form id such as `001-architectural-integrity-standard`
would sit in `project_directives` while the DRG and catalog use canonical `DIRECTIVE_NNN`, so the
exclusion guard in `delivery_table.py` would silently drop a legitimately org-required,
DRG-reachable directive. Nothing raises. Nothing reports. The directive simply is not there.

Fixing instance 3 alone leaves instance 4 available. **The class is the defect.**

## Ruling — fix both, and close the class inside the tasks artifact

**Decision: apply both remediations as written, AND add the invariant below as an explicit
acceptance requirement at every union and exclusion boundary in WP02 and WP03 — not only at the
two boundaries where findings happened to land.**

The invariant:

> Every directive, tactic and paradigm identifier is canonicalized at the moment it enters a
> union, and every union and exclusion boundary either canonicalizes its inputs or fails loud.
> An identifier whose form cannot be canonicalized is an error, never a silently-excluded entry.
> Absent input resolves to the documented catalog default, never to an empty set.

The two literal remediations, unchanged:

- **TASKS-FRESH2-001 (severity 4)**: normalize each `_read_org_required_selections()["directives"]`
  entry via `_normalize_directive_id` before unioning onto `project_directives`; add a stem-form
  red-first fixture to T007, which currently exercises the org-required union not at all.
- **TASKS-FRESH2-002 (severity 3)**: add an explicit type-check step to T004 and a non-list fixture
  to T002, so a scalar under an `activated_*` key raises as FR-005/NFR-001 require rather than
  iterating a string character by character.

## Alternatives considered and rejected

1. **Fix the two findings literally and stop.** Rejected: it is the third consecutive round to fix
   an instance of this class, and the two previous instance-fixes did not prevent this one. The
   remediations are correct but insufficient on their own.
2. **Amend `plan.md` with the canonicalization contract and regenerate WP02/WP03 from it.**
   Strongest class closure on paper, and rejected on operational grounds: a review-mandated
   `plan.md` correction mid-tasks staleness-locks the next work package, and the prescribed
   recovery is itself blocked by a sibling's untracked verdict (ledger **SK-149**, observed
   first-hand today). The invariant therefore lands in the tasks artifact, where it binds the
   implementers without re-opening the plan.

## NFR-002 collision in WP05 — ruled from precedent, not escalated

WP05's contract-doc edits collide with `tests/architectural/test_archive_root_byte_identical.py`.
This is settled: a sibling mission hit the identical trap today, where two reviewers ruled the edit
defensible from convention (250+ precedents in `kitty-specs/*/contracts/`) and the enforced gate
disagreed. Archived mission directories are byte-frozen; only new-path ADDs are permitted.

**Restore any pre-existing archived file byte-identical and relocate the new material into this
mission's own live dossier. Do not weaken, skip or exempt the gate.**

## How the phase closes

One final targeted R4 fix round covering both findings and the invariant, then a single R5a
anchored verification against the bar set by this ruling. **No further fresh sweep, no further
rounds.** All resolved -> the phase passes and the whole `reviews/` trail is committed with the
phase. Anything still unresolved -> HALT again, back to the operator.

**Acceptance signal**: the R5a verifier must confirm, per union and exclusion boundary in WP02 and
WP03, that the boundary either canonicalizes its inputs or fails loud — enumerated boundary by
boundary, not asserted in aggregate — and that the two new fixtures fail against the task text as
it stood before this round.
