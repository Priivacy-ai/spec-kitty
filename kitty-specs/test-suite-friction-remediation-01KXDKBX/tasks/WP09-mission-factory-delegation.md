---
work_package_id: WP09
title: Production-delegating mission factory
dependencies: []
requirement_refs:
- FR-008
- FR-016
- NFR-002
- NFR-003
tracker_refs:
- '2074'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/_factories/__init__.py
create_intent:
- tests/_factories/test_make_mission_parity.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/_factories/__init__.py
- tests/_factories/test_make_mission_parity.py
- src/specify_cli/core/mission_creation.py
role: implementer
tags: []
shell_pid: "3019175"
shell_pid_created_at: "1783953675.37"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-008 + A-002 +
[data-model.md](../data-model.md) E-06, and [plan.md](../plan.md) §IC-07. **NFR-003:** the sole production
edit permitted here is a behaviour-preserving entrypoint on `create_mission_core()` — do NOT fork the schema
and do NOT migrate the 329-writer tail (Directive 024).

## Objective

Introduce `tests/_factories.make_mission(**overrides)` as a thin wrapper over `create_mission_core()`
(`src/specify_cli/core/mission_creation.py:206`), applying test-specific overrides on production-shaped
meta so a single schema authority flows every new required field to consumers. If the core lacks a
side-effect-free / no-coordination-branch entrypoint, add one (behaviour-preserving).

## Context

- `tests/_factories/__init__.py` is currently **empty** (0 bytes).
- `create_mission_core()` is the documented programmatic mission-creation API (spec A-002). The factory must
  **delegate** to it, not re-implement meta assembly.
- The parity invariant (E-06): `make_mission()` output `meta.json` is byte-identical to a direct
  `create_mission_core()` call **after normalizing the auto-minted `{mission_id, mid8, created_at}`** and
  minus explicit overrides.

## Subtask guidance

- **T038 — core entrypoint (only if missing).** Inspect `create_mission_core()`. If it always writes side
  effects (coordination branch, worktree, git) that a factory can't use, add a **side-effect-free /
  no-coordination** entrypoint (e.g. a `write_side_effects: bool` seam or a pure `build_mission_meta()`
  extraction) — behaviour-preserving, covered by its own focused test. If a suitable entrypoint already
  exists, use it and skip the production edit.
- **T039 — the factory.** Implement `make_mission(**overrides)` in `tests/_factories/__init__.py` delegating
  to the core, applying overrides on production-shaped meta.
- **T040 — parity test.** New `tests/_factories/test_make_mission_parity.py`: assert `make_mission()`'s
  `meta.json` is byte-identical to a direct `create_mission_core()` call **AFTER normalizing the auto-minted
  `{mission_id, mid8, created_at}` fields** (freeze time + inject a fixed `mission_id`, or strip those keys
  before comparison) and minus explicit overrides. A raw byte-compare is unachievable — those three fields
  are minted per call and differ every time.
- **T041 — non-empty importer DoD.** `tests/_factories/__init__.py` is non-empty with **≥1 real importer**
  (the parity test imports and uses `make_mission`; note in the review where a production test consumes it).
- **T042 — gates + tracer.** `ruff`/`mypy` clean; append the parity tracer row.

## Branch Strategy

Lane A root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] `make_mission()` delegates to `create_mission_core()` (no forked schema).
- [ ] Output `meta.json` **byte-identical AFTER normalizing the auto-minted `{mission_id, mid8, created_at}`**
      (freeze time + inject a fixed `mission_id`, or strip those keys before comparison) and minus explicit
      overrides — asserted by `test_make_mission_parity.py`.
- [ ] `tests/_factories/__init__.py` non-empty with ≥1 real importer.
- [ ] Any production edit to `mission_creation.py` is behaviour-preserving (NFR-003) and covered by a test.
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] **Tracer (FR-016):** append a catalog row for the factory-parity assertion (invariant-vs-shape) +
      friction log.

## Risks

- **Forking the schema** instead of delegating — the byte-identical parity assertion is the guardrail.
- **Adding a side-effecting entrypoint** — if you add a core entrypoint, keep it side-effect-free and prove
  behaviour preservation with a focused test.

## Reviewer guidance

- Confirm the parity test asserts byte-identity minus overrides, and the factory delegates (no re-implemented
  meta assembly).
- Confirm any `mission_creation.py` change is behaviour-preserving with its own test.

## Activity Log

- 2026-07-13T14:13:05Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:36:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Ready for review: make_mission() factory delegates to create_mission_core(); added allow_worktree_context seam (behaviour-preserving, default False); parity test byte-identical after freezing mission_id+clock; ruff/mypy clean.
- 2026-07-13T14:39:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – factory + allow_worktree_context entrypoint; 45 passed, ruff/mypy clean
- 2026-07-13T14:41:46Z – claude:opus:reviewer-renata:reviewer – shell_pid=3019175 – Started review via action command
- 2026-07-13T15:03:32Z – user – shell_pid=3019175 – Review passed (reviewer-renata/opus): thin factory delegate, behaviour-preserving allow_worktree_context kwarg, byte-identical-after-normalization parity. Force: lane-i status-artifact hygiene reconciled at merge.
