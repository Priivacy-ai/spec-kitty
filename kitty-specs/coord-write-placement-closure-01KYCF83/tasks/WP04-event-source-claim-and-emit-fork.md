---
work_package_id: WP04
title: Event-source the claim + subtask completion; close the emit HEAD fallback
dependencies: []
requirement_refs:
- FR-003
- FR-008
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-write-placement-closure-01KYCF83
base_commit: 7f48ef94b4559f08a07973970d2949a6b1c86355
created_at: '2026-07-25T14:20:32.783663+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 2 - Event-source authoring
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/status_transition.py
create_intent:
- tests/regression/test_claim_event_source.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/core/subtask_rows.py
- tests/regression/test_claim_event_source.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Event-source the claim + subtask completion; close the emit HEAD fallback

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objective

This WP owns `status_transition.py` and merges the two edits that share its claim region into one pass. It **adds** the event-sourcing for the two authoring paths (#2684) and **closes** the #1716 HEAD fallback. It deliberately **retains** the frontmatter `shell_pid`/`agent` write for now — the retirement happens in **WP05 after the readers migrate** (retiring it here would break claim-liveness in the window; the folded squad finding is explicit).

- **FR-008 (emit side)**: event-source the **claim fields** (`shell_pid`/`agent`) and **subtask-completion** (`tasks.md` checkboxes). Emit the events; keep the frontmatter/`tasks.md` write as a *dual-write* until WP05 retires it.
- **FR-003 (emit fork)**: close the `_current_branch` HEAD-derived current-branch fallback at `status_transition.py:685` (#1716) so a status write resolves its target through the placement port, not the ambient checkout HEAD.

**Done** = claim + subtask-completion are recorded as events (in addition to the still-present frontmatter/`tasks.md` write); the HEAD fallback is removed and routed through the port; a red-first regression proves the claim event carries `shell_pid`/`agent`.

## Context & Constraints

- Spec: [spec.md](../spec.md) US2, US3 AS3, FR-003, FR-008. Plan: [plan.md](../plan.md) IC-04-fallback + IC-07-core. Contract: [contracts/birth-cutover-and-repair.md](../contracts/birth-cutover-and-repair.md) "Event-sourced authoring". Research D-03.
- **C-002 scope**: event-source **exactly** the two enumerated paths — claim (`shell_pid`/`agent`) + subtask-completion checkboxes. No other frontmatter/`tasks.md` authoring is in scope. Do NOT broaden into the #1619 dual-write program.
- **Retirement ordering (folded squad finding)**: retiring the frontmatter `shell_pid` write breaks `stale_detection.py` / `task_metadata_validation.py` unless those readers first consume the reduced snapshot. Therefore this WP keeps the frontmatter write; **WP05** migrates the readers and then retires the write. Sequence is WP04 (emit, dual-write) → WP05 (readers + retire).
- **Write-location seam (post-tasks squad — clarifies the WP04↔WP05 hand-off)**: the claim `shell_pid`/`agent` frontmatter write flows through **`frontmatter.py`** (its authoring constants live at `frontmatter.py:71`/`:288`), NOT through `status_transition.py`. Consequence: WP05's retirement edits **`frontmatter.py` only** and thereby disables the dual-write **without re-touching this WP's `status_transition.py`**. So the dual-write you retain here is *authored downstream in `frontmatter.py`* — do not relocate it into `status_transition.py`, or you would force WP05 back into your owned file (owned_files would overlap).
- **Emit fallback deadlock risk**: the `_current_branch` fallback is reached in the pre-`meta.json` create window. The port-routed replacement must not deadlock in that window — verify against a create-time fixture.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T014 – RED-first: claim event carries `shell_pid`/`agent`

- **Purpose**: DIRECTIVE_041 — drive the emit change through the real claim entry point.
- **Steps**: Write `tests/regression/test_claim_event_source.py` that claims a WP through the existing entry point and asserts the emitted status event carries `shell_pid` + `agent` (reducible from the event log), failing before the change.
- **Files**: `tests/regression/test_claim_event_source.py` (new).
- **Validation**: red before T015, green after.

### Subtask T015 – Event-source the claim fields

- **Purpose**: FR-008 — record `shell_pid`/`agent` as events.
- **Steps**: In `status_transition.py`, at the claim path, emit the claim event carrying `shell_pid`/`agent` (via the existing status-emit surface). **Keep** the current frontmatter write (dual-write) — WP05 retires it. Do not add a parallel writer; reuse the canonical emit path.
- **Files**: `src/specify_cli/coordination/status_transition.py`.
- **Validation**: the reduced snapshot exposes `shell_pid`/`agent` after a claim.

### Subtask T016 – Event-source subtask completion

- **Purpose**: FR-008 — subtask-completion (`tasks.md` checkboxes) recorded as events.
- **Steps**: In `core/subtask_rows.py`, when a subtask row flips to complete, emit the completion event (keep the `tasks.md` checkbox write as dual-write for now). Ensure the event is idempotent for a re-completed row.
- **Files**: `src/specify_cli/core/subtask_rows.py`.
- **Validation**: completing a subtask appends exactly one completion event; re-completing appends none.

### Subtask T017 – Close the `_current_branch` HEAD fallback (#1716)

- **Purpose**: FR-003 — status writes route through the port, not the ambient HEAD.
- **Steps**: At `status_transition.py:685`, remove the HEAD-derived `_current_branch` fallback and resolve the write target through the placement seam instead. Confirm the create-window path (pre-`meta.json`) still resolves without deadlock.
- **Files**: `src/specify_cli/coordination/status_transition.py`.
- **Validation**: a status write in the create window resolves via the port; no HEAD read remains.
- **Edge cases**: detached-HEAD / mid-rebase fixtures must not regress.

### Subtask T018 – Idempotency + dual-write parity

- **Purpose**: NFR-003 — no un-seeded runtime accrues; the dual-write stays consistent until WP05.
- **Steps**: Assert the event stream and the (still-present) frontmatter/`tasks.md` write agree for claim + subtask completion. This parity is what lets WP05 safely retire the frontmatter write.
- **Files**: extend `tests/regression/test_claim_event_source.py`.
- **Validation**: event-vs-frontmatter parity green.

### Subtask T019 – Regression sweep for claim-liveness

- **Purpose**: prove the emit changes did not break claim-liveness before WP05 touches the readers.
- **Steps**: Run the existing claim/stale-related suites; they must stay green (readers still read frontmatter here — that is intentional).
- **Files**: none (verification).
- **Validation**: claim/stale suites green on this WP.

## Test Strategy

- New: `tests/regression/test_claim_event_source.py` (RED→green through the real claim path).
- Run the claim, subtask, and stale suites to confirm the dual-write keeps liveness intact.

## Definition of Done

- Claim + subtask-completion emitted as events (dual-write retained).
- `_current_branch` HEAD fallback removed and port-routed; create-window verified.
- Parity + idempotency tests green; `ruff` + `mypy` clean.
- Frontmatter `shell_pid` write **still present** (WP05 retires it).

## Risks & Mitigations

- **Retiring the write here** → explicitly out of scope; WP05 owns retirement after reader migration.
- **Create-window deadlock** → T017 verifies against a create-time fixture.
- **Scope creep into #1619** → strictly the two enumerated paths (C-002).

## Review Guidance

- Verify the frontmatter `shell_pid` write is retained (not retired) in this WP.
- Verify only the two enumerated authoring paths are event-sourced.
- Verify the HEAD fallback is gone and the create window still resolves.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
