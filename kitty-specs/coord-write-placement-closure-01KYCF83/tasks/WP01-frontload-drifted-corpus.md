---
work_package_id: WP01
title: Front-load the drifted corpus (unblock CI)
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-write-placement-closure-01KYCF83
base_commit: cc4ad0a1a89c81e317d6fcbc3c30dfe80bf6e511
created_at: '2026-07-25T13:51:30.519102+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Unblock CI
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/regression/test_corpus_frontload_idempotent.py
create_intent:
- tests/regression/test_corpus_frontload_idempotent.py
execution_mode: code_change
owned_files:
- tests/regression/test_corpus_frontload_idempotent.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Front-load the drifted corpus (unblock CI)

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

Run the one-time runtime-state backfill over the 12 drifted missions and commit the resulting flips so `test_dogfood_corpus_backfilled` passes and the 3.2.6 CI Quality red is cleared. This WP is **independent and lands first** — it is a mechanical, deterministic corpus write plus a small idempotency regression test. It must NOT depend on any structural work in this mission.

- **FR-007**: run `migrate backfill-runtime-state` over the currently-drifted missions and commit, so the acceptance lock passes.
- **SC-001 (initial green)**: `test_dogfood_corpus_backfilled` passes with no other change. (WP10 later re-keys the lock for *durable* green; this WP delivers *initial* green.)

**Done** = the 12 drifted missions carry their seed events + `status_phase=1`; `verify_backfill().ok` is true for each; `test_dogfood_corpus_backfilled` passes; a new idempotency regression proves a second backfill run is byte-stable.

## Context & Constraints

- Spec: [spec.md](../spec.md) US1, FR-007, SC-001. Plan: [plan.md](../plan.md) IC-01. Research: [research.md](../research.md) D-07.
- Backfill entry point: `spec-kitty migrate backfill-runtime-state` (`src/specify_cli/cli/commands/migrate_cmd.py` → `src/specify_cli/runtime/migrate.py`; migration `m_zz_runtime_state_backfill`). Use the **canonical CLI command** — do NOT hand-roll a seeding loop.
- **Deterministic seeds (NFR-003)**: seed event IDs are namespaced on the immutable `mission_id`. A re-run must seed 0 events and leave `status_phase` + the event log byte-identical.
- **Exclude the self-referential mission** `coord-write-placement-closure-01KYCF83` — it is event-sourcing itself and is excluded from the lock (spec Edge Cases; FR-010).
- Run the backfill against **this branch** (`feat/coord-write-placement-closure`) — the corpus it writes IS the corpus the lock reads.
- **Corpus data is not code ownership.** The committed `kitty-specs/**` flips are mission data produced by running the canonical command; they are intentionally NOT in `owned_files` (which holds only your new regression test). Commit the corpus flips as part of this WP's landing, but do not treat `kitty-specs/**` as an owned source surface.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `feat/coord-write-placement-closure`; completed changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T001 – Enumerate the drifted missions

- **Purpose**: know exactly which missions the lock currently reds on before mutating anything.
- **Steps**: Run `PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/migration/test_dogfood_corpus_backfilled.py -q` and capture the failing mission set. Cross-check against `migrate backfill-runtime-state --dry-run` (or `--json` if available) to list the eligible-but-un-flipped missions. Confirm the count matches the spec's "12 drifted missions" (if it differs, record the actual number — the corpus may have moved since planning).
- **Files**: none (read-only enumeration).
- **Validation**: the dry-run list and the lock's failing set agree.
- **Edge cases**: if the self-mission appears in the eligible set, confirm it is excluded by the migration; if not, that is a defect to flag (do NOT flip the self-mission).

### Subtask T002 – Run the backfill and commit the flips

- **Purpose**: seed the runtime state so each drifted mission gains `status_phase=1` + seed events.
- **Steps**: Run `spec-kitty migrate backfill-runtime-state` (real command) over the corpus. Verify each drifted mission now has `status_phase="1"` in `meta.json`, deterministic seed events appended to `status.events.jsonl`, and `verify_backfill().ok` true. Stage and commit the `kitty-specs/**` flips.
- **Files**: `kitty-specs/**` (mission data — committed, not owned).
- **Validation**: `git status` shows only the expected drifted-mission `meta.json` + `status.events.jsonl` changes; no source files touched.
- **Edge cases**: if the migration touches a mission NOT in the drifted set, stop and investigate — the seed namespace may be wrong.

### Subtask T003 – Author the idempotency regression (RED→green)

- **Purpose**: lock in NFR-003 — a second backfill run is a no-op.
- **Steps**: Write `tests/regression/test_corpus_frontload_idempotent.py` that: (a) constructs a small fixture corpus (or re-uses a tmp copy of an already-backfilled mission), (b) runs the backfill once, snapshots `status.events.jsonl` + `meta.json.status_phase`, (c) runs it again, (d) asserts zero new events and byte-identical `status_phase` + event log. Use production-shaped `mission_id` ULIDs (26 chars) so the seed-namespacing is exercised realistically, not placeholder ids.
- **Files**: `tests/regression/test_corpus_frontload_idempotent.py` (new).
- **Validation**: `PWHEADLESS=1 uv run --extra test pytest tests/regression/test_corpus_frontload_idempotent.py -q` passes; deliberately mutating the seed-id namespace makes it red (sanity).
- **Edge cases**: the second run must not re-order existing events; assert on the exact byte content, not just length.

### Subtask T004 – Confirm the acceptance lock passes

- **Purpose**: prove FR-007 / SC-001 initial green.
- **Steps**: Run `PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/migration/test_dogfood_corpus_backfilled.py -q`; it must pass. Do NOT modify the lock in this WP — WP10 owns the re-key. If the lock still reds after backfill, the eligibility predicate or a mission's seed is wrong — investigate, do not green-wash.
- **Files**: none (verification only).
- **Validation**: the lock is green on this branch.

## Test Strategy

- New: `tests/regression/test_corpus_frontload_idempotent.py` (idempotency, NFR-003).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/regression/test_corpus_frontload_idempotent.py tests/specify_cli/migration/test_dogfood_corpus_backfilled.py -q`.

## Definition of Done

- 12 (or actual-count) drifted missions flipped and committed.
- Idempotency regression green; a re-run seeds 0 events.
- `test_dogfood_corpus_backfilled` passes.
- `ruff` + `mypy` clean on the new test.

## Risks & Mitigations

- **Wrong mission set flipped** → mitigate with the T001 dry-run cross-check; stop on any unexpected mission.
- **Self-mission flipped** → explicitly excluded; verify before commit.
- **Non-deterministic seeds** → assert byte-identical re-run in T003.

## Review Guidance

- Verify the backfill was run via the **canonical CLI command**, not a hand-rolled loop.
- Verify the committed corpus diff is only `meta.json` + `status.events.jsonl` for drifted missions.
- Verify the idempotency test asserts byte-identity, not just count.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
