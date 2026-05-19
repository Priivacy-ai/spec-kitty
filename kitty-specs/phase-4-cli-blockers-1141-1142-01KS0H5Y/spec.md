# Phase 4 CLI Blockers — #1141 and #1142

**Mission ID**: 01KS0H5YSZ2VB6TFKN7Q73MYWP
**Slug**: phase-4-cli-blockers-1141-1142-01KS0H5Y
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-05-19

## Purpose

Land the two open Phase 4 launch-gate CLI blockers in a single PR so the
identity-boundary canary's scenarios 1, 2, and 4 can pass against
`spec-kitty-dev`. Both fixes are CLI-internal; the events package, the
SaaS materializer, and the canary harness are intentionally out of scope.

This mission consumes the investigation deliverables from
`kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/` (Recommendation A
for each issue) and lands the targeted patches.

## Context

### Issue #1142 — audit predicate too narrow

`is_mission_lifecycle_row()` in
`src/specify_cli/audit/shape_registry.py` currently requires
`aggregate_type == "Mission"`. The audit engine therefore mis-classifies
rows whose aggregate is `Project`, `WorkPackage`, or `MissionDossier` as
status-transition rows and raises `FORBIDDEN_KEY` findings against
legitimate lifecycle discriminators (`event_type`, `aggregate_type`).
That blocks the canary's scenarios 1 + 2 with
`TeamSpace migration required. Finding codes: FORBIDDEN_KEY`.

The fix is structural: broaden the predicate to accept the full set
`{"Mission", "Project", "WorkPackage", "MissionDossier"}` while keeping
both predicates (allowed aggregate_type AND non-empty `event_type`)
required. The negative case (`aggregate_type == "Foo"`) still must not
classify as a lifecycle row — the regression guard against malformed
status-transition rows depends on it.

Reference: investigation note
`kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/h2-emitter-walk-1142.md`,
contract doc `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/contracts/audit-row-family.md`.

### Issue #1141 — backward review-rejection emit not in the offline queue

Scenario 4 of the identity-boundary canary tests a deliberate
`in_review → planned` rollback (the review-rejection family, force-required
per the events package's contract). Today the canary peek finds the
previous forward `for_review → in_review` row at the head of the queue
instead of the rollback. The investigation
(`kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/h1-evidence-1141.md`)
ruled out H4/H3, partially ruled out H2, and concluded H1 (silent CLI
fan-out failure) is the most likely root cause.

The fix has three parts:

1. **Defensive logging breadcrumb** at `fire_saas_fanout` entry in
   `src/specify_cli/status/adapters.py` so any future silent fan-out
   failure surfaces in operator logs.
2. **Unit regression test** that emits a forward `for_review → in_review`
   (unforced) followed by a forced backward `in_review → planned`
   through `emit_status_transition`, peeks the offline queue, and
   asserts both rows are present in order with the backward row at the
   head.
3. **Bisect the queue delta**: if the test exposes that the backward
   row is being silently replaced or dropped, fix the offending
   `queue_event` / `_try_coalesce` / handler path. The `validate_transition`
   contract in `spec_kitty_events` remains authoritative — no relaxation
   of the force-required rule.

## User scenarios & testing

### Primary scenario — audit clears lifecycle rows

**Actor**: An operator running the identity-boundary canary against
`spec-kitty-dev`.
**Trigger**: Scenario 1 (fresh authenticated mission) creates a mission;
the materializer writes lifecycle rows with `aggregate_type ∈ {Project,
WorkPackage, MissionDossier}`. The doctor invokes the audit engine.
**Happy-path outcome**: Zero `FORBIDDEN_KEY` findings against
legitimate lifecycle rows. TeamSpace gate stays green. The canary
proceeds past the audit stage.

### Secondary scenario — forced rollback enqueues correctly

**Actor**: A reviewer running
`spec-kitty agent tasks move-task WP01 --to planned --note "<feedback>"`
on a WP currently at `in_review`.
**Trigger**: The CLI auto-promotes the move to `force=True` with a
canonical `"backward rewind: in_review -> planned: …"` reason and calls
`emit_status_transition`.
**Happy-path outcome**: The offline queue contains exactly one new
`WPStatusChanged` row whose payload has `from_lane="in_review"`,
`to_lane="planned"`, `force=True`. The row is the most recent one for
`WP01`.

### Regression guard — malformed transition row still flagged

**Actor**: A future hand-edit injects a synthetic status-transition row
that carries `event_type` but no `aggregate_type`.
**Trigger**: The audit engine runs.
**Outcome**: The row is NOT classified as a lifecycle row; the
`FORBIDDEN_KEYS` rule fires and a finding is emitted. The broadening
must preserve this exact behavior.

## Functional requirements

- **FR-1142-A**: `is_mission_lifecycle_row` returns `True` iff
  `aggregate_type ∈ {"Mission", "Project", "WorkPackage",
  "MissionDossier"}` AND `event_type` is a non-empty string.
- **FR-1142-B**: For any other `aggregate_type` (including `None`,
  empty string, or unknown values) the predicate returns `False`.
- **FR-1142-C**: The module docstring and function docstring reference
  the contract doc at
  `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/contracts/audit-row-family.md`
  and enumerate the four accepted aggregate types.
- **FR-1141-A**: `fire_saas_fanout` logs an info-level breadcrumb on
  entry containing `wp_id`, `from_lane`, `to_lane`, `force` so silent
  handler exceptions can be correlated with the originating canonical
  event in operator logs.
- **FR-1141-B**: A new unit test exercises the full forward-then-forced-
  backward sequence through `emit_status_transition`, captures both
  `fire_saas_fanout` invocations via a registered fake handler, and
  asserts the backward row is the most recent.
- **FR-1141-C**: The `validate_transition` contract for the
  review-rejection family is NOT relaxed — `force=True` and a non-empty
  `reason` remain required.

## Constraints

- **C-001**: No changes to `spec_kitty_events`, `spec_kitty_tracker`,
  the SaaS code, or the canary harness.
- **C-002**: No changes to existing finalised missions under
  `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/` or
  `kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/`.
- **C-003**: No release tag, no `pyproject.toml` version bump. Release
  tracking lives in #1038.
- **C-004**: Single PR, both fixes in one mission. Closes #1141 and
  #1142.

## Acceptance criteria

| ID | Criterion | Verified by |
|---|---|---|
| A-001 | `tests/audit/` passes including a new parametrized test that exercises each of the four accepted aggregate types and the negative case | `uv run pytest tests/audit -q` |
| A-002 | `tests/sync/` and `tests/status/` pass including the new `test_emit_backward_transition.py` (or peer location) | `uv run pytest tests/sync tests/status -q` |
| A-003 | `ruff check` clean on touched modules | `uv run ruff check src/specify_cli/audit src/specify_cli/status src/specify_cli/sync` |
| A-004 | No `mypy --strict` regressions on touched packages | `uv run mypy --strict src/specify_cli/audit src/specify_cli/status src/specify_cli/sync` |
| A-005 | The audit regression guard still flags a synthetic status-transition row that carries `event_type` without a matching `aggregate_type` | New negative-case test in `tests/audit/` |
