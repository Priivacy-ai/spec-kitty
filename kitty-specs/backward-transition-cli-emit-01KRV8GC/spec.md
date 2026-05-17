# CLI Backward-Transition Emit Path

**Mission ID**: 01KRV8GCG83GH1K12CWQ52SNW5
**Slug**: backward-transition-cli-emit-01KRV8GC
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-05-17

## Purpose

Stop the CLI from emitting contradictory `WPStatusChanged` events when a user runs `spec-kitty agent tasks move-task <WP> --to <earlier_lane>`. Today's emit path sets `force=False` even when the user is moving a WP **backward** in the canonical lane order (the review-rejection family: `in_review → planned`, `approved → planned`, `for_review → planned`, `in_progress → planned`). The contract — documented in Mission 1 of this program (`spec-kitty-events` mission_number=15) — requires `force=True` and a normative `reason` shape for any such backward emit. The fix is to auto-detect the backward direction in the emit path and promote `emit_force=True` with the canonical `"backward rewind: <from> -> <to>[: <feedback-ref>]"` reason shape.

## Context

Cross-repo planning issue `Priivacy-ai/spec-kitty-planning#16` reports that the CLI emit path, the SaaS materializer, and the durable drain disagree about the wire shape of a review rejection. The evidence pack at `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` shows 22 stuck events on `spec-kitty-dev` with `from_lane=approved → to_lane=planned`, `force=False`, `reason="move-task: approved -> planned"`. The CLI emit knew it was a rewind (the reason text proves it) but did not set `force=True`. SaaS materializer correctly rejected the unforced backward events as graph-invalid; the durable drain parked them as `terminal_failed`; readiness treated them as infra debris.

Mission 1 of this program landed the contract source of truth in `spec-kitty-events`:
- Module docstring of `src/spec_kitty_events/status.py` ("Review-Rejection Transition Family") enumerates the four family members and the wire requirements.
- `docs/consumer-contract-dossier-v2.4.0.md` §7 is the cross-link target for non-Python consumers.
- Conformance fixtures registered in the events package manifest:
  - `wp-review-rejection-cycle-replay`
  - `wp-status-changed-approved-rewind-valid`
  - `wp-status-changed-unforced-in-review-to-planned-invalid`

This mission consumes the contract anchors and the positive `wp-status-changed-approved-rewind-valid` fixture as the wire-shape oracle for its regression tests. Mission 3 (`spec-kitty-saas` — materializer + drain/readiness) and Mission 4 (`spec-kitty-planning` — issue closure) follow.

## Hotspot

`src/specify_cli/cli/commands/agent/tasks.py`:

| Item | Location |
|---|---|
| `move_task()` function | line 1336 |
| Current bug | line 1710 (`emit_force = force` directly assigns the user's flag without detecting backward direction) |
| Existing helper | line 1714 (`_lane_targets_for_emit`) already knows the canonical forward order `[planned, claimed, in_progress, for_review, in_review, approved, done]` |
| Existing reason synthesis | line 1711 (`emit_reason = "Force move to ..." if force else "move-task: <from> -> <to>"`) — needs to become `"backward rewind: <from> -> <to>[: <feedback-ref>]"` on auto-promoted backward emits |

## User Scenarios & Testing

### Primary Scenario — Reviewer Rejects, Implementer Re-Implements

**Actor**: A reviewer running `spec-kitty agent tasks move-task WP05 --to planned --review-feedback-file /tmp/feedback.md --mission <slug>` after finding issues in a WP that's currently `in_review`.
**Trigger**: The reviewer determines the implementation needs another iteration and rejects the WP back to `planned`.
**Happy-path outcome**: A single `WPStatusChanged` event is emitted with `wp_id=WP05`, `from_lane=in_review`, `to_lane=planned`, `force=True`, `reason="backward rewind: in_review -> planned: feedback:///tmp/feedback.md"` (or the equivalent URI shape). The SaaS materializer (Mission 3) accepts the event cleanly. No `terminal_failed` debris on `/health/ready/`.

### Secondary Scenario — Manual Approved-Rewind

**Actor**: An operator who realizes a WP was approved prematurely and wants to send it back to `planned` for additional work.
**Trigger**: `spec-kitty agent tasks move-task WP07 --to planned --mission <slug>` from the `approved` lane.
**Happy-path outcome**: Auto-promoted `force=True` emit with `reason="backward rewind: approved -> planned"` (no feedback-ref because none was provided). Wire shape matches `wp-status-changed-approved-rewind-valid` fixture.

### Tertiary Scenario — Forward Transition Unaffected

**Actor**: An implementer running `spec-kitty agent tasks move-task WP02 --to claimed` on a `planned` WP.
**Trigger**: Normal forward progress.
**Outcome**: Existing behavior preserved — `force=False`, `reason="move-task: planned -> claimed"` (or the existing default), and `_lane_targets_for_emit` expands skip-ahead forward moves into intermediate events. Auto-promotion does NOT fire.

### Acceptance Rule (must always hold)

For every `move-task` invocation:
- If the target lane is **backward** of the current canonical lane in `[planned, claimed, in_progress, for_review, in_review, approved, done]`, the emitted `WPStatusChanged` event MUST have `force=True` and `reason` MUST start with `"backward rewind: <from_lane> -> <to_lane>"`.
- If the target lane is **forward** or equal, behavior MUST be unchanged from today (existing forward-transition guards and intermediate-event expansion intact).
- The user's explicit `--force` flag continues to be honored (no behavior change for the explicit-force path).

## Domain Language

| Term | Meaning |
|---|---|
| Review-rejection family | The set of legitimate forced backward lane transitions: `{in_progress → planned, for_review → planned, in_review → planned, approved → planned}`. Defined normatively in Mission 1's `status.py` docstring. |
| Auto-promoted backward emit | A `WPStatusChanged` emission where the CLI detected a backward direction and set `emit_force=True` automatically (without the user passing `--force`). |
| Canonical reason shape | `"backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]"` — defined normatively in Mission 1 (`docs/consumer-contract-dossier-v2.4.0.md` §7). |
| Forward order | `[planned, claimed, in_progress, for_review, in_review, approved, done]` — the canonical lane progression. |
| Feedback-ref | URI-shaped pointer to the review feedback artifact: `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md` or a `file://` / direct path when `--review-feedback-file` is provided. |

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | When `move-task` is invoked and the target lane precedes the current canonical lane in the forward order, the emitted `WPStatusChanged` event MUST have `force=True`. | Required |
| FR-002 | The auto-promoted `emit_reason` MUST start with the literal string `"backward rewind: <from_lane> -> <to_lane>"` (using the literal `Lane` enum values), and SHOULD append `": <feedback-ref>"` when a feedback reference is available (from `--review-feedback-file`, the rejected-review-result review_ref, or a synthesized URI). | Required |
| FR-003 | The auto-promotion ONLY fires when the user did NOT pass `--force`. If the user passed `--force` explicitly, behavior is identical to today (existing path preserved). | Required |
| FR-004 | Forward `move-task` requests MUST NOT be auto-promoted to `emit_force=True`. The existing `_lane_targets_for_emit` intermediate-event expansion for forward skip-ahead moves MUST be preserved exactly. | Required |
| FR-005 | Auto-promoted backward emits MUST NOT bypass guard conditions that the contract validator (`spec_kitty_events.status.validate_transition`) classifies as "checked regardless of force" — for example, `in_progress -> planned requires reason`. The canonical reason shape satisfies this. | Required |
| FR-006 | For an auto-promoted backward emit, `transition_targets` is the single literal `target_lane` (one event). The CLI MUST NOT expand backward jumps into a sequence of intermediate events. | Required |
| FR-007 | Existing terminal-lane exit semantics (e.g. `done → *`, `canceled → *`) where the user is already required to pass `--force` MUST be preserved. Auto-promotion fires for the review-rejection family only; terminal-lane exits remain explicit-`--force` territory. | Required |
| FR-008 | New focused tests under `tests/cli/commands/` (and/or `tests/status/`) MUST cover, at minimum: (a) `in_review → planned` without `--force` produces `force=True` and reason starting with `"backward rewind: in_review -> planned"`; (b) `approved → planned` without `--force` produces the same with `approved` in place; (c) `for_review → planned` and `in_progress → planned` produce the same with their respective from-lanes; (d) `planned → claimed` (forward) produces `force=False` and reason NOT starting with `"backward rewind: "`; (e) `in_progress → for_review` (forward skip-ahead) preserves intermediate-event expansion; (f) backward emit with `--review-feedback-file <path>` includes the feedback-ref in the reason. | Required |
| FR-009 | A regression test loads the `wp-status-changed-approved-rewind-valid` fixture from `spec_kitty_events.conformance.load_fixtures("edge_cases")` and asserts the auto-promoted `approved → planned` emitted payload's `force`, `reason`-prefix, `from_lane`, and `to_lane` fields match the fixture. | Required |
| FR-010 | The 22 dev evidence events on `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` MUST NOT be replayed, mutated, deleted, or skipped by this mission. Tests use synthetic data and / or Mission 1's fixtures. | Required |
| FR-011 | If the user explicitly passes `--force` AND the move is backward, the CLI continues to use the existing `--force` reason path (today's `"Force move to <to>"` text). The auto-promotion branch is bypassed. This keeps the explicit-force semantics fully preserved. | Required |
| FR-012 | The hotspot block at `src/specify_cli/cli/commands/agent/tasks.py` lines ~1700-1730 is the only `src/` file expected to change. No new helpers in unrelated modules; the backward detector can be local to `move_task()` or a private module-level helper next to `_lane_targets_for_emit`. | Required |

## Non-Functional Requirements

| ID | Description | Measurable Threshold | Status |
|---|---|---|---|
| NFR-001 | Targeted test runtime | `uv run pytest tests/cli/commands tests/status -k "move_task or status or transition" -q` completes in under 30 seconds wall-clock. | Required |
| NFR-002 | No regression in the full test suite | `uv run pytest tests/ -q` exits 0. | Required |
| NFR-003 | Lint + type-check gates pass | `uv run ruff check src/specify_cli/` exits 0; `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` (or the project's documented typing command for this file) exits 0. | Required |
| NFR-004 | Coverage gate for new code | The new backward-detection block and the new tests collectively reach ≥90% line coverage of the changed region per the charter's coverage policy. | Required |
| NFR-005 | Wire shape additivity | No new fields added to `WPStatusChanged` payload; no fields removed. Only `force` and `reason` values change on auto-promoted backward emits. | Required |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | Target branch is `main`; all work merges back to `main`. | Required |
| C-002 | `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must be set for any CLI invocation in this working tree. | Required |
| C-003 | This mission depends on Mission 1's contract anchors and fixtures (already merged in `spec-kitty-events` mission_number=15). The `spec-kitty` package already imports `from spec_kitty_events.status import Lane` etc.; no new cross-repo imports required. | Required |
| C-004 | No mutation of the 22 dev evidence events. | Required |
| C-005 | Per the worktree guide: after creating any worktree, run `python3.11 -m pip install -e ".[dev]"` (or the project-equivalent editable install). Editable installs do not propagate to fresh worktrees. After merge, reinstall from main. | Required |
| C-006 | All existing tests under `tests/` MUST continue to pass. Backward-compatibility on the explicit-`--force` path is mandatory: any prior caller that passed `--force` observes identical behavior. | Required |

## Success Criteria

| ID | Statement | Measurement |
|---|---|---|
| SC-001 | A reviewer running the focused test command sees green output for the new FR-008 tests. | `uv run pytest tests/cli/commands tests/status -k "move_task or status or transition" -q` exit 0. |
| SC-002 | A reader of the diff at `tasks.py:1700-1740` can identify the backward-detection block and canonical reason construction in under 90 seconds. | Mission review walkthrough. |
| SC-003 | The auto-promoted emitted payload for `approved → planned` matches the Mission 1 fixture `wp-status-changed-approved-rewind-valid` on the `force`, `reason`-prefix, `from_lane`, `to_lane` fields. | FR-009 test passes. |
| SC-004 | Full test suite passes without regression. | `uv run pytest tests/ -q` exit 0. |
| SC-005 | Lint + type-check + coverage gates pass. | NFR-003, NFR-004 verified. |

## Key Entities

| Entity | Notes |
|---|---|
| `move_task()` | Existing function in `src/specify_cli/cli/commands/agent/tasks.py:1336`. Mutated only in the lines 1700-1730 region. |
| `_lane_targets_for_emit()` | Existing private helper at `tasks.py:1714`. Knows the canonical forward order. Re-used as the source of truth for backward detection. |
| `emit_force` / `emit_reason` | Local variables in `move_task()`. The mission changes the value of both for auto-promoted backward emits. |
| `StatusTransitionPayload` | Wire payload class in `spec-kitty-events`. Not modified; consumed as-is. |
| `validate_transition()` | Contract validator in `spec-kitty-events`. Not invoked at emit time; emit is upstream of validation. |
| `wp-status-changed-approved-rewind-valid` | Mission 1 fixture loaded by the FR-009 regression test as the wire-shape oracle. |

## Assumptions

- `--review-feedback-file <path>` is the standard mechanism by which a reviewer attaches a feedback artifact to a rejection. When present, the CLI builds a `feedback://<path>` (or `file://<path>`) URI. When absent, the auto-promoted reason omits the colon-separated feedback-ref segment.
- The CLI emit path already has access to the resolved `mission_slug`, `task_id`, `old_lane`, `target_lane`, and `canonical_lane` variables at the hotspot. No new lookups are required.
- The contract validator in `spec-kitty-events` is downstream of emit (it runs in the SaaS materializer, not in the CLI). The CLI does not call `validate_transition()` directly; correctness is enforced by the wire-shape regression test against Mission 1's fixture.

## Dependencies

- **Upstream**: Mission 1 (`spec-kitty-events` mission_number=15, merged). Provides contract docs + manifest fixtures consumed by FR-009 test.
- **Downstream**: Mission 3 (`spec-kitty-saas` materializer + drain/readiness). Will assume CLI emits the corrected wire shape; its own tests will verify the materializer accepts it cleanly and classifies any residual `force=False` backward events as business-rule rejections (not infra terminal_failed).
- **Final**: Mission 4 (`spec-kitty-planning`). Closes planning#16 after all three code-repo PRs merge.

## Out of Scope

- SaaS materializer / drain / readiness changes (Mission 3 in `spec-kitty-saas`).
- Contract / fixture / doc changes in `spec-kitty-events` (Mission 1, already merged).
- Planning issue closure (Mission 4 in `spec-kitty-planning`).
- Mutation of the 22 dev evidence events.
- New `WPStatusChanged` payload fields or event types.
- Forward-transition guard logic changes.
- Replay or reclassification of the existing `terminal_failed` queue items in production — that is a SaaS-side decision (Mission 3 design stance).

## References

- Cross-repo planning issue: https://github.com/Priivacy-ai/spec-kitty-planning/issues/16
- Evidence pack (read-only): `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json`
- Mission 1 contract anchors (`spec-kitty-events`): `src/spec_kitty_events/status.py` module docstring; `docs/consumer-contract-dossier-v2.4.0.md` §7.
- Mission 1 fixtures: manifest ids `wp-review-rejection-cycle-replay`, `wp-status-changed-approved-rewind-valid`, `wp-status-changed-unforced-in-review-to-planned-invalid`.
- Implementation prompt: `/Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/IMPLEMENTATION_PROMPT_planning16.md`.
- Hotspot file: `src/specify_cli/cli/commands/agent/tasks.py` (move_task at line 1336; bug at line 1710).
