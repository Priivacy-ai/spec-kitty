---
work_package_id: WP03
title: Advisory recommendation on the dispatch payload
dependencies:
- WP01
- WP02
- WP05
requirement_refs:
- FR-004
- NFR-001
- NFR-002
- C-001
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '661274'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- tests/invocation/test_dispatch_recommendation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/dispatch.py
- tests/architectural/test_no_dead_modules.py
- tests/invocation/test_dispatch_recommendation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Advisory recommendation on the dispatch payload

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Surface the WP02 evaluator's recommendation on `InvocationPayload` through `ProfileInvocationExecutor.invoke()`, advisory and non-fatal, in both `--json` and rich render.
- SC-001: with a populated catalog, the recommendation **varies with catalog scoring inputs** (task_fit/weights changes flip the winner) — this is the anti-fake proof that it is computed, not a stub.
- Without a catalog (or on a match miss), the recommendation is absent and `dispatch` still succeeds (NFR-002).
- `--json` and rich render carry an identical recommendation payload.

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-004, NFR-001, NFR-002, C-001; `plan.md` IC-03; `tasks.md` WP03 section; `adversarial-review.md` load-bearing traps.
- **Load-bearing trap — red-first surface**: T012 MUST prove behavior through `spec-kitty dispatch` / `ProfileInvocationExecutor.invoke()` payload contents, **never** the Pydantic model in isolation and **never** a stubbed recommendation. Testing the model directly does not satisfy NFR-001.
- **Load-bearing trap — anti-fake**: SC-001 requires the recommendation to genuinely VARY when catalog content (task_fit/weights) changes. A hardcoded or always-identical recommendation fails this even if the test is green.
- **Load-bearing trap — advisory/non-fatal ceiling**: `invoke()` never spawns an LLM call (`executor.py:150,181`) — the recommendation is advisory data on the payload only, honored (or not) by the calling agent. A missing or stale catalog must degrade to "absent," and dispatch must still succeed — never raise, never block.
- Wire the loader+evaluator call into `invoke()` after profile+action resolve (~`executor.py:196/205`), before payload construction (~`:273`).
- Add the recommendation as a new `__slots__` field on `InvocationPayload` (+ `to_dict()`); update `_render_rich_payload` in `cli/commands/dispatch.py` with a recommendation line.
- Depends on **WP01** (loader), **WP02** (evaluator), and **WP05** (the shipped catalog) — consume them directly, do not reimplement scoring here.
- **Dead-modules tip**: this WP is where the `test_no_dead_modules.py` invariant flips green — `loader.py`, `task_class_map.py`, and `evaluator.py` all gain their `invoke()` caller here, and `doctrine.model_task_routing.models` is de-allowlisted here (not in WP01/WP02).
- **Integration proof (WP05 dependency)**: with no fixture override, `spec-kitty dispatch`/`invoke()` must produce a recommendation from the REAL shipped WP05 catalog through the loader's default path — the only test proving WP01's default path and WP05's file location agree.
- **MANDATORY complexity extraction**: extract a pure helper `_compute_recommendation(profile, action) -> Recommendation | None` that holds the loader+evaluator call AND the non-fatal envelope (missing/stale catalog → return `None`); `invoke()` calls it in one line so `invoke()` stays ≤15 cognitive complexity.
- Keep `ruff`/`mypy` clean; complexity ≤ 15.

## Subtasks

- [ ] T012 [red-first] `tests/invocation/test_dispatch_recommendation.py`: through `invoke()`/`dispatch --json`, recommendation present with a catalog + VARIES when catalog scoring changes (anti-fake, SC-001); absent when catalog removed, dispatch still succeeds (NFR-002). RECORD pre-fix RED (no slot exists).
- [ ] T013 [FR-004] `InvocationPayload` new `__slots__` recommendation field (+ `to_dict()`), runtime imports as needed.
- [ ] T014 [FR-004] wire the loader+evaluator call into `ProfileInvocationExecutor.invoke()` after profile+action resolve (~executor.py:196/205), before payload construction (~:273); non-fatal (missing/stale → absent). MANDATORY: extract a pure helper `_compute_recommendation(profile, action) -> Recommendation | None` holding the loader+evaluator call and the non-fatal envelope; `invoke()` calls it in one line so `invoke()` stays ≤15 cognitive complexity.
- [ ] T015 [FR-004] `_render_rich_payload` (`cli/commands/dispatch.py`) recommendation line.
- [ ] T016 [NFR-002] non-fatal paths asserted (missing/stale/unmatched catalog).
- [ ] T017 `ruff`/`mypy` clean; complexity ≤ 15.
- [ ] T018 [dead-modules tip] Remove `doctrine.model_task_routing.models` from `_ALLOWLIST` in `tests/architectural/test_no_dead_modules.py` (loader's import now satisfies its caller check); confirm loader.py/task_class_map.py/evaluator.py all gain their `invoke()` caller here so the no-dead-modules gate is green at the integration tip.
- [ ] T019 [integration] With NO fixture override, run `spec-kitty dispatch`/`invoke()` and assert a recommendation IS produced from the REAL shipped WP05 catalog through the loader's default path — the only test proving WP01's default path and WP05's file location agree.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] T012 recorded RED pre-fix (proven through `dispatch`/`invoke()` payload, not the model in isolation), GREEN post-implementation.
- [ ] `InvocationPayload` carries a recommendation slot with `to_dict()` support; `_render_rich_payload` renders it.
- [ ] Recommendation demonstrably VARIES when catalog task_fit/weights change (SC-001 anti-fake proof), and is absent (with dispatch still succeeding) when the catalog is missing/stale/unmatched.
- [ ] `--json` and rich render carry an identical recommendation payload.
- [ ] `invoke()` calls a pure `_compute_recommendation(profile, action) -> Recommendation | None` helper that holds the loader+evaluator call and the non-fatal envelope; `invoke()` itself stays ≤15 cognitive complexity.
- [ ] `doctrine.model_task_routing.models` removed from `test_no_dead_modules.py`'s `_ALLOWLIST`; `test_no_dead_modules.py` is green with loader.py/task_class_map.py/evaluator.py all gaining their `invoke()` caller at this tip.
- [ ] With no fixture override, a recommendation is produced end-to-end from the real shipped WP05 catalog through the loader's default path.
- [ ] `ruff check` and `mypy` clean on owned files; complexity ≤ 15.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T18:56:40Z – claude – shell_pid=661274 – Moved to for_review
- 2026-07-04T18:56:51Z – user – shell_pid=661274 – APPROVE (opus, uv-run): red-first genuine; see adversarial-review.
