---
work_package_id: WP10
title: Re-key the acceptance lock (event-log-keyed) + migration coexistence
dependencies:
- WP05
- WP09
requirement_refs:
- C-003
- FR-010
- NFR-006
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
created_at: '2026-07-25T12:00:00+00:00'
subtasks:
- T049
- T050
- T051
- T052
- T053
phase: Phase 5 - Durable lock
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/migration/test_dogfood_corpus_backfilled.py
create_intent:
- tests/specify_cli/migration/test_backfill_migration_coexistence.py
execution_mode: code_change
owned_files:
- tests/specify_cli/migration/test_dogfood_corpus_backfilled.py
- tests/specify_cli/migration/test_backfill_migration_coexistence.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP10 – Re-key the acceptance lock (event-log-keyed) + migration coexistence

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

Re-key `test_dogfood_corpus_backfilled` to an **event-log birth invariant** so it survives FR-008's authoring retirement without going vacuous — the **highest silent-failure stakes** in the mission. Add a regression that the one-time migration still cuts over a legacy corpus.

- **FR-010**: every mission whose **event log** carries runtime (excluding the self-referential cutover mission) must be `status_phase>=1` + non-empty snapshot; event-log-keyed, not corpus-membership-keyed.
- **NFR-006**: the one-time `migrate backfill-runtime-state` path still cuts over a legacy corpus green — retains a regression test.
- **C-003**: preserve (or strengthen) the `verify_backfill` parity assertion — no green-wash.

**Done** = eligibility keys on **independent event-log evidence**; keying on `has_evictable_state()` OR `status_phase` is hard-forbidden; born-reconciled missions (WP09) pass; the migration-coexistence regression is green.

## Context & Constraints

- Spec: [spec.md](../spec.md) US2 AS2, FR-010, NFR-006, C-003, SC-001. Plan: [plan.md](../plan.md) IC-09 (read the risk block — it is the crux). Contract: [contracts/birth-cutover-and-repair.md](../contracts/birth-cutover-and-repair.md) "Acceptance lock".
- **Depends on WP05** (authoring retirement empties `has_evictable_state()`) and **WP09** (born-reconciled missions must pass the re-keyed lock).
- **HARD-FORBID (folded squad finding)**: do NOT key eligibility on `has_evictable_state()` (frontmatter — retired by WP05, would make the lock pass **vacuously**) NOR on `status_phase` (circular — only checks already-flipped). Key on **independent event-log evidence**: the mission's `status.events.jsonl` carries seed/runtime events.
- **C-003 no green-wash**: keep the `verify_backfill` parity assertion. The re-key must genuinely close the drift, not relax the predicate to pass.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T049 – RED-first: a born-un-reconciled mission must red

- **Purpose**: FR-010 — prove the re-keyed lock would catch a future un-reconciled merge (no vacuous pass).
- **Steps**: Add a fixture whose event log carries runtime but whose `status_phase` is unset; assert the re-keyed lock reds on it. This is the anti-vacuity guard — it must fail if eligibility keys on `has_evictable_state()`/`status_phase`.
- **Files**: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`.
- **Validation**: red on the un-reconciled fixture with the correct predicate; a wrong (vacuous) predicate would pass — call that out.

### Subtask T050 – Re-key `_eligible_runtime_missions` on event-log evidence

- **Purpose**: FR-010 — event-log-keyed eligibility.
- **Steps**: Rewrite `_eligible_runtime_missions:120-133` so eligibility = "the mission's event log carries runtime events" (independent evidence), excluding the self-referential cutover mission. Do NOT read `has_evictable_state()` or gate on `status_phase`.
- **Files**: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`.
- **Validation**: eligibility derives solely from the event log.

### Subtask T051 – Assert the birth invariant + preserve parity

- **Purpose**: FR-010 / C-003 — eligible missions must be `status_phase>=1` + non-empty snapshot; keep `verify_backfill` parity.
- **Steps**: For each eligible mission, assert `status_phase>=1`, a non-empty reduced snapshot, and `verify_backfill().ok`. Keep (or strengthen) the existing parity assertion at `_backfilled_missions:110-115`. No relaxation.
- **Files**: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`.
- **Validation**: born-reconciled missions (WP09) pass; the parity assertion is intact.

### Subtask T052 – Migration-coexistence regression

- **Purpose**: NFR-006 — the one-time migration still cuts over a legacy corpus after FR-008.
- **Steps**: Write `tests/specify_cli/migration/test_backfill_migration_coexistence.py` that constructs a legacy-shaped corpus (frontmatter-authored, no seed events), runs `migrate backfill-runtime-state` / `m_zz_runtime_state_backfill`, and asserts it cuts over green and is idempotent — proving forward-flow (birth) and backward-flow (migration) coexist on the same `cutover_mission` spine.
- **Files**: `tests/specify_cli/migration/test_backfill_migration_coexistence.py` (new).
- **Validation**: legacy corpus cuts over green; re-run seeds 0.

### Subtask T053 – Durable-green confirmation

- **Purpose**: SC-001 — the lock stays green after subsequent merges.
- **Steps**: Confirm the re-keyed lock passes on the current corpus (WP01's front-load + WP09's birth) and that a simulated additional born-reconciled merge keeps it green. Run the full migration suite.
- **Files**: verification.
- **Validation**: lock green; anti-vacuity fixture (T049) still reds when un-reconciled.

## Test Strategy

- Modified: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`.
- New: `tests/specify_cli/migration/test_backfill_migration_coexistence.py`.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/migration/ -q`.

## Definition of Done

- Eligibility keys on independent event-log evidence; `has_evictable_state()`/`status_phase` keying hard-forbidden.
- Birth invariant asserted; `verify_backfill` parity preserved (no green-wash).
- Migration-coexistence regression green + idempotent.
- Anti-vacuity fixture reds when un-reconciled; `ruff` + `mypy` clean.

## Risks & Mitigations

- **Vacuous pass** → T049 anti-vacuity fixture + forbidden-predicate call-out.
- **Circular keying on `status_phase`** → forbidden; key on event log.
- **Green-wash** → C-003 parity preserved.

## Review Guidance

- Verify eligibility does NOT read `has_evictable_state()` or gate on `status_phase`.
- Verify the anti-vacuity fixture reds when a runtime-carrying mission is un-reconciled.
- Verify the `verify_backfill` parity assertion is intact or stronger.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
