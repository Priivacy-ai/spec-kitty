---
work_package_id: WP02
title: PID-reuse-aware liveness + truth-in-labeling
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- NFR-003
- NFR-004
- NFR-005
- C-005
- C-007
tracker_refs: []
planning_base_branch: rework/coord-shadows-followups
merge_target_branch: rework/coord-shadows-followups
branch_strategy: Planning artifacts for this mission were generated on rework/coord-shadows-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/coord-shadows-followups unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Liveness hardening
assignee: ''
agent: "claude"
shell_pid: "698445"
history:
- at: '2026-07-12T15:14:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/process_liveness.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/process_liveness.py
- src/specify_cli/core/stale_detection.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/frontmatter.py
- src/specify_cli/status/wp_metadata.py
- tests/specify_cli/core/test_process_liveness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – PID-reuse-aware liveness + truth-in-labeling

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role: implementer) before parsing the rest of this prompt.

## Objectives & Success Criteria

Closes **#2575**. Make `is_process_alive` unfoolable by a recycled PID via a persisted creation-time baseline co-written at **every** claim site; correct the mislabeled test + docstring overclaim. **Degradation is additive** — an absent baseline preserves today's live-PID behavior (zero legacy regression).

Done when:
- Every `shell_pid` writer co-writes a creation-time baseline (via one extracted helper).
- `stale_detection` compares the baseline when present; a present-but-mismatched baseline → not-alive → timestamp-heuristic fallback (never hard-stale); an absent baseline preserves today's live-PID trust.
- `is_process_alive(pid) -> bool` signature is unchanged (protects `review/lock`, `sync/*`, `dashboard/lifecycle`).
- Docstring overclaim fixed; the mislabeled test renamed; new spawn→kill + baseline-mismatch + workflow_executor-carries-baseline + legacy-no-regression tests added.

## Context & Constraints

- **D3b (was a plan gap):** `implement.py:1400` is NOT the only `shell_pid` writer. `stale_detection` reads the `shell_pid` key written by THREE paths — `implement.py:~1400`, `workflow_executor.py:~668` (the `agent action implement` per-WP claim the loop uses), `workflow_executor.py:~1338` (review claim, overwrites `shell_pid`). Extract ONE helper co-writing `shell_pid` + baseline and route all three through it (close-by-construction). `reviewer_shell_pid` is consumed by no liveness path — leave it alone.
- **D3a (additive degradation):** compare gated on baseline present. Absent → preserve `is_process_alive(pid)` live-PID trust. Present + mismatch → not-alive → `check_wp_staleness` (stale_detection.py:282) already falls to the commit-timestamp heuristic when liveness is not True — do NOT hard-flag stale.
- **C-005**: fence the PID-reuse compare to `process_liveness` + the `stale_detection` consumer. Do NOT sweep `sync/owner`, `sync/daemon`, `sync/orphan_sweep`, `dashboard/lifecycle` onto baseline-aware liveness.
- **C-007**: ONE additive field (process creation-time). Not a process-identity subsystem.
- **NFR-004**: `is_process_alive` never raises; keep the AccessDenied→alive branch.

## Subtasks

- [ ] T008 [P] Truth-in-labeling (independent, D4): fix `process_liveness.py` docstring overclaim re "recycled PIDs"; rename `test_recycled_pid_generic_exception_returns_false` to describe the exception branch it actually tests.
- [ ] T009 Register the additive creation-time baseline field in `frontmatter.py`; model in `status/wp_metadata.py`.
- [ ] T010 Extract ONE claim-write helper co-writing `shell_pid` + baseline.
- [ ] T011 Route `implement.py` (~L1400) through the helper.
- [ ] T012 Route `workflow_executor.py` implement-claim (~L668) + review-claim (~L1338) through the helper.
- [ ] T013 Baseline-aware compare in `process_liveness.py` (companion / optional param; keep `is_process_alive(pid)->bool` frozen); wire `stale_detection._is_claiming_process_alive` to compare; absent → preserve live-PID trust.
- [ ] T014 [P] Test: simulated baseline mismatch → not-alive → timestamp fallback.
- [ ] T015 [P] Test: real spawn→kill liveness.
- [ ] T016 [P] Test: `workflow_executor`-claimed WP carries the baseline.
- [ ] T017 [P] Test: legacy (absent-baseline) claim preserves live-PID trust.
- [ ] T018 Verify C-005 + C-007; `ruff` + `mypy` clean.

## Campsite & Coverage Notes (post-tasks squad — fold into the listed subtasks)

- **Design — PRIMARY RISK (T010):** the two claim paths use DIFFERENT write APIs — `implement.py:1400` `update_fields(path, dict)` (file-based) vs `workflow_executor.py:668/1338` `set_scalar(front_string, key, val)` (in-memory frontmatter). The ONE helper must NOT grow a per-caller `if/else` on API shape (that defeats close-by-construction). Normalize: have the helper mutate the frontmatter string (co-write `shell_pid` + baseline via `set_scalar`) and re-route BOTH sites onto it (the file-based caller reads → helper → writes). Keep one write mechanism.
- **Literal hoist (fold into T009):** declare the NEW baseline field name ONCE as a shared module constant (mirroring the `"shell_pid"` field-name pattern at `frontmatter.py:57`); it is read in ≥3 places (helper, `wp_metadata`, `stale_detection`) — a bare repeated string would re-introduce the exact S1192 duplication this WP eliminates for `shell_pid`.
- **Coverage (fold into T014):** T014 must ALSO cover the baseline-present-AND-matches → alive branch (positive match), not only mismatch — else the "match" branch is uncovered new code.
- **Coverage (fold into T016):** add a DIRECT unit test of the claim-write helper — it co-writes BOTH `shell_pid` AND baseline, AND the `implement.py` route (T011) still round-trips (its write path differs from the two `set_scalar` sites).
- **Don't-clean (T008/T013):** `process_liveness.py:33-34` `except Exception: return False` is the load-bearing NFR-004 never-raises catch — do NOT "tidy" it; keep the `AccessDenied → True` branch. The baseline compare goes in the companion `_is_claiming_process_alive`/`is_claiming_process_alive`, NOT in `is_process_alive(pid)->bool` (frozen signature — adding a branch there breaks WP05/`sync/*`/`dashboard/lifecycle` and raises its complexity).
- Complexity: `_is_claiming_process_alive` +2 → ~5, well under 15.

## Definition of Done

All 11 subtasks checked; `pytest tests/specify_cli/core/ -q` green (incl. the new tests: T014 mismatch+match, T015 spawn→kill, T016 workflow_executor-claim + direct helper, T017 legacy no-regression); the baseline field name is a shared constant; the claim-write helper uses ONE write mechanism (no per-caller API branch); no psutil consumer outside `process_liveness`/`stale_detection` changed; `is_process_alive` signature unchanged; `ruff` + `mypy` clean.

## Dependencies

None. (WP05 depends on this WP's `is_process_alive` signature staying stable.)

## Activity Log

- 2026-07-12T15:29:07Z – claude – shell_pid=698445 – Assigned agent via action command
- 2026-07-12T16:21:50Z – claude – shell_pid=698445 – Ready: PID-reuse baseline at all 3 claim sites + end-to-end CLI staleness wiring; is_process_alive frozen; 28 WP02 tests green; opus-reviewed APPROVE
- 2026-07-12T16:22:01Z – user – shell_pid=698445 – APPROVED by reviewer-renata (opus): 12/12 checks; is_process_alive frozen byte-identical; end-to-end wiring both paths (ref-shared); flake pre-existing; 4th-writer edge filed #2580
