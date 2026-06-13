---
work_package_id: WP01
title: Lifecycle events + re-open-aware classification
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2862504"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/specify_cli/status/test_post_mission_lifecycle_events.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/lifecycle_events.py
- src/specify_cli/status/lifecycle.py
- tests/specify_cli/status/test_post_mission_lifecycle_events.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Lifecycle events + re-open-aware classification

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned implementer profile via the
`ad-hoc-profile-load` (or `spk-doctrine-profile-load`) skill — do NOT proceed on a bare
persona name. The recommended implementer is `python-pedro`. Load the doctrine YAML / governed
context and adopt its boundaries, then continue.

## Objectives & Success Criteria

Add two lifecycle event types and make a re-opened mission actually read as actionable.

- `MissionReopened` and `FollowUpRecorded` are registered, emittable, and **reducer-skipped**.
- `derive_mission_lifecycle` honors a `MissionReopened` event (postdating the last
  merge/completion marker) by yielding a new `reopened` surface_state — **the FR-002 crux**.
- New types are kept **off** the SaaS strict-validation path (local-only this mission).
- All new behavior is pinned by tests; ruff + mypy `--strict` clean on touched files (NFR-002).

## Context & Constraints

- Read: `plan.md` (IC-01), `research.md` (D-A1, D-A2, C-SAAS, R-A2), `data-model.md` (event
  payloads + registration + derived-view section), `.kittify/charter/charter.md`.
- **Review-verified BLOCKING fact:** `status/lifecycle.py::_classify_state` classifies purely
  from WP-lane counts + age and never reads `merged_*` or events. Clearing `merged_*` alone is a
  no-op — actionability MUST be driven by the `MissionReopened` event. This WP owns that change.
- `append_lifecycle_event` (lifecycle_events.py) hard-drops any `event_type` not in the LOCAL
  `LIFECYCLE_EVENT_TYPES` frozenset → both new constants MUST be added there AND to `__all__`.
- Lifecycle events coexist with WP-status events in `status.events.jsonl`; the reducer
  discriminates on `event_type` presence and skips them — keep it that way.
- Identity: attribute via `mission_id` (ULID); never a slug-derived guess (NFR-004).
- **Ownership note:** this WP owns the `lifecycle.py` *classifier* + `lifecycle_events.py`.
  WP02 only *renders* `post_mission_events` (in `views.py`) — do not edit `views.py` here.

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T001 – ATDD: failing tests first
- **Purpose:** lock the contract before code (NFR-005).
- **Steps:** in `tests/specify_cli/status/test_post_mission_lifecycle_events.py`, write failing tests:
  (1) emitting `MissionReopened`/`FollowUpRecorded` appends a well-formed envelope and is
  reducer-skipped (WP `status.json` unchanged); (2) `FollowUpRecorded` dedup on
  `(mission_id, commit_sha|pr_number)` (second identical ref = no new event); (3) on a fixture
  merged mission (all WPs terminal), after a `MissionReopened` event, `derive_mission_lifecycle`
  returns the `reopened`/actionable surface_state.
- **Notes:** drive the seams directly (pure functions / fixture event logs); no slow git scaffolding.

### T002 – Register event types + emit helpers
- **Purpose:** make the events first-class and persistable.
- **Steps:** add `MissionReopened` and `FollowUpRecorded` constants to `LIFECYCLE_EVENT_TYPES`
  and `__all__` in `lifecycle_events.py`; add emit helpers using `_build_envelope`
  (aggregate_id=mission_id, aggregate_type="Mission"); implement `FollowUpRecorded` dedup via the
  existing `has_lifecycle_event()` pattern keyed on `(mission_id, commit_sha|pr_number)`;
  `MissionReopened` is append-each (not deduped).
- **Files:** `src/specify_cli/status/lifecycle_events.py`.

### T003 – Re-open-aware classification (the crux)
- **Purpose:** make a re-opened mission actionable via the event (FR-002).
- **Steps:** in `status/lifecycle.py`, teach `derive_mission_lifecycle`/`_classify_state` to read
  the lifecycle event stream for the latest `MissionReopened`; when it postdates the last
  merge/completion marker and is not itself followed by a re-merge, return a new `reopened`
  state/surface_state (treated as actionable) regardless of WP terminality. Sort
  `post_mission_events` by `(timestamp, event_id)` so `lifecycle.json` stays byte-stable. Add the
  `post_mission_events` + `last_follow_up_at` fields to the result dataclass (rendered by WP02).
- **Files:** `src/specify_cli/status/lifecycle.py`.
- **Notes:** update any `lifecycle.json` golden-file in this same change (dataclass shape changed).

### T004 – SaaS boundary + reducer-skip confirmation
- **Purpose:** avoid the latent shared-package hard-fail; confirm invariants.
- **Steps:** ensure the two new types are NOT routed through `_validate_lifecycle_payload(strict=True)`
  / the SaaS fan-out (they are local-only — do not add them to the external model map). Add/extend a
  test confirming they round-trip through `read_events` as reducer-skipped. Document inline that SaaS
  propagation of post-mission events is a follow-up needing an external `spec_kitty_events` bump.

## Test Strategy

- Tests in `tests/specify_cli/status/test_post_mission_lifecycle_events.py`. Run
  `pytest tests/specify_cli/status/test_post_mission_lifecycle_events.py` (green) and a focused
  reducer/lifecycle regression. Diff-scoped `ruff check` + `mypy --strict` on the two source files
  (exit 0). Paste commands + exit codes into the handoff note.

## Definition of Done

- T001–T004 complete; new tests green; reducer/lifecycle existing tests unbroken; ruff+mypy clean
  on touched files; the `reopened` classification demonstrably works on a fixture merged mission.

## Risks

- Forgetting `LIFECYCLE_EVENT_TYPES`/`__all__` registration → silent event drop (fail-closed
  re-open degrades). Touching the reducer (don't — only the derivation layer reads these).
  Non-deterministic `post_mission_events` ordering → `lifecycle.json` churn.

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Verify the classification change is genuinely driven by the event
  (not merged_*), the events are reducer-skipped, registration is present, and the SaaS strict path
  is untouched. Confirm new code is actually invoked (no dead code).

## Activity Log

- 2026-06-13T16:56:15Z – claude:opus:python-pedro:implementer – shell_pid=2763962 – Assigned agent via action command
- 2026-06-13T17:08:28Z – user – shell_pid=2763962 – claim (status desync recovery)
- 2026-06-13T17:08:29Z – user – shell_pid=2763962 – in_progress (status desync recovery)
- 2026-06-13T17:10:56Z – claude:opus:python-pedro:implementer – shell_pid=2763962 – Ready: MissionReopened+FollowUpRecorded registered+emittable+reducer-skipped; reopen-aware classification (event postdating merged_at -> reopened surface_state) verified on fixture merged mission. Tests: test_post_mission_lifecycle_events.py 11 passed; status suite 329 passed; lifecycle_events 54 passed. ruff exit=0 (4 touched files); mypy --strict lifecycle.py exit=0; lifecycle_events.py 3 PRE-EXISTING errors (lines 124/486/699 vs HEAD: redundant ulid type:ignore + spec_kitty_events 6.0.0 datetime|None payload drift in untouched emit_project_initialized/emit_wp_created_local). test_no_dead_symbols: WP-in-flight allowlist for the 2 emit helpers (callers land WP02/IC-02); residual PathValidationError flag pre-existing on base (stash-verified). Code committed on lane 9dae40f35.
- 2026-06-13T17:12:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=2826535 – Started review via action command
- 2026-06-13T17:16:03Z – user – shell_pid=2826535 – Moved to planned
- 2026-06-13T17:17:31Z – claude:sonnet:python-pedro:implementer – shell_pid=2845925 – Started implementation via action command
- 2026-06-13T17:20:34Z – claude:sonnet:python-pedro:implementer – shell_pid=2845925 – cycle1: lifecycle_events.py mypy --strict clean; tests green
- 2026-06-13T17:22:23Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2862504 – Started review via action command
- 2026-06-13T17:24:13Z – user – shell_pid=2862504 – cycle2 re-review: mypy --strict exit 0 confirmed, _iso_str_to_datetime helper is type-only (no behavior change), lifecycle.py core untouched, all 11 WP01 tests + 329 status-suite tests green, ruff exit 0
