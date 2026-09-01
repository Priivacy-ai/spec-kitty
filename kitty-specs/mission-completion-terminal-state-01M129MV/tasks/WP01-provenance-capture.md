---
work_package_id: WP01
title: Operator-authored provenance capture + reducer projection
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-completion-terminal-state-01M129MV
base_commit: 044e4be4eed879f9e154ecbbeeb67ff1de22658a
created_at: '2026-08-28T05:30:54.150532+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Provenance foundation
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-A after post-spec squad (F1 BLOCKER, F3)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — corrected emit anchor + owned_files (pedro BLOCKER), raw-event test (renata HIGH)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/specify_cli/cli/commands/agent/test_cancellation_provenance.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/reducer.py
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/status/test_reducer.py
- tests/specify_cli/cli/commands/agent/test_cancellation_provenance.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/2945
- https://github.com/Priivacy-ai/spec-kitty/issues/3590
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. State which you applied, then begin.

## Objective

Make cancellation provenance **operator-authored, durably captured, and readable by acceptance**.
Today `move-task` auto-synthesizes a non-empty `reason` (`tasks_transition_core.py:307-317`), so
"non-empty reason" cannot distinguish a documented replan from a bare force-cancel (post-spec squad
**F1 BLOCKER**), and the reduced snapshot drops `reason` (`reducer.py:166-177`, **F3**). This WP adds
a **first-class `reason_source` field** on the status event, sets it at the emit site, and projects it
into the snapshot. It is the foundation WP02–WP04/WP06 build on.

> **Post-tasks squad correction (pedro BLOCKER):** `build_transition_plan`
> (`tasks_transition_core.py:307-366`) is a **pure planning function — it never emits**. Persistence
> happens in `tasks_move_task.py` (`_mt_hop_policy_metadata:2105`, `_mt_emit_transitions:2148`) via
> `status/emit.py` writing a `StatusEvent` (`status/models.py:318`, `to_dict:357`, `from_dict:388`).
> The chosen mechanism (R1, pinned in data-model.md) is a **first-class `reason_source: "operator" |
> "synthetic"` field** on `StatusEvent` — NOT overloading `policy_metadata`, and NOT a reduce-time
> template match (renata: template-match is fakeable and reintroduces F1).

## Context

- Evidence: [../research/post-spec-squad-findings.md](../research/post-spec-squad-findings.md) (F1, F3);
  post-tasks feasibility + anti-laziness findings. Decisions: [../research.md](../research.md) R1, R2.
- Data model: [../data-model.md](../data-model.md) entities 1 & 2. C-002 (event-log authority, no
  frontmatter reads); C-001 (adding an optional event field is not a transition-matrix change).

## Subtasks

### T001 — Add `reason_source` to the status event, set at the emit site
Add `reason_source: str | None` to `StatusEvent` (`status/models.py:318`) with `to_dict`/`from_dict`
round-trip (`:357`, `:388`), defaulting to `None` for non-cancel events (NFR-002: existing events
deserialize unchanged). Thread it through `status/emit.py`. At the cancel emit site in
`tasks_move_task.py` (`_mt_hop_policy_metadata`/`_mt_emit_transitions`), set `reason_source="operator"`
when the operator supplied a `--note`, else `"synthetic"`. Keep `build_transition_plan`
(`tasks_transition_core.py`) computing the human `reason` string as today; the discriminator is the
new field, not the string.

### T002 — Force/whitespace note → synthetic
Ensure `move-task --to canceled --force` with no `--note`, or a whitespace-only `--note` (trim before
deciding), yields `reason_source="synthetic"` (so FR-003's blocker is reachable through the canonical
command). Do **not** change `validate.py:126-128` — that is the force-audit invariant (`force=true`
requires a reason), a different concern; leave it intact.

### T003 — Project provenance into the reduced snapshot
In `status/reducer.py:166-177` (`_wp_state_from_event`), project `cancellation_reason` and
`reason_source` into the per-WP snapshot **only when `lane == "canceled"`**. Derive purely from the
event log (C-002). Non-canceled snapshots stay byte-identical (NFR-002).

### T004 — Sweep canceled-event snapshot goldens
Update golden/snapshot assertions for the new projected slot **across `tests/status/`** — not just
`test_reducer.py`: also `test_parity.py`, `test_2960_blanked_runtime_slot.py`,
`tests/specify_cli/status/test_resolved_binding_reducer.py`, `test_finalize_canceled_work_packages.py`,
and confirm the `_RUNTIME_SLOTS` authority invariant (`test_2093_authority_invariant.py`) still holds
(the new slot is a canceled-only projection, not a runtime slot). Declare a `pytestmark` on the new
test file (T005) per the repo marker-convention gate.

### T005 — Unit tests: raw-event capture (non-fakeable)
New `tests/specify_cli/cli/commands/agent/test_cancellation_provenance.py` (declare `pytestmark`):
drive the **canonical** `move-task` command, then read the **raw event** via `read_events` and assert
`event.reason_source == "operator"` for `--note "x"` and `== "synthetic"` for `--force` w/o note and
for a whitespace note. This raw-event assertion (renata HIGH) is what forbids a reduce-time
template-match fake. Add a legacy-compat case: an event predating `reason_source` (field absent) whose
non-synthetic `reason` is treated as operator by the downstream reader (NFR-002) — and document that
this template fallback applies ONLY to legacy events, never to new emits (which carry the field).

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- `StatusEvent.reason_source` exists, round-trips, and is set operator/synthetic at the cancel emit site.
- Force/whitespace-note cancels are `synthetic`; `--note` cancels are `operator`.
- The reduced snapshot exposes `cancellation_reason` + `reason_source` for canceled WPs.
- T005 asserts `reason_source` on the **raw event**; `tests/status/` goldens updated; new test files carry
  `pytestmark`; `ruff` + `mypy` clean on owned files. `mission_finalize.py` untouched (C-005).

## Risks / Reviewer guidance

- **Do not** derive provenance by template-matching `reason` at reduce time — that is the F1 defect
  one layer up (renata). The durable field must be captured at emit and asserted on the raw event.
- Verify `StatusEvent` field addition is backward-compatible (old events deserialize with
  `reason_source=None`); confirm no non-canceled snapshot changes (NFR-002).
