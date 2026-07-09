---
work_package_id: WP02
title: 'MissionResolver port: Protocol + adapters + free-fn delegate'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-005
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "132450"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/context/mission_resolver.py
create_intent:
- src/mission_runtime/mission_resolver_port.py
- tests/specify_cli/context/test_mission_resolver_port.py
execution_mode: code_change
owned_files:
- src/mission_runtime/mission_resolver_port.py
- src/specify_cli/context/mission_resolver.py
- tests/specify_cli/context/test_mission_resolver_port.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your agent profile via `/ad-hoc-profile-load` for `python-pedro` (implementer). Then read
`kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-001/FR-005), `plan.md` (IC-01),
`data-model.md`, `contracts/mission-resolver.md`, and `research.md` (D-Q2, D-05, D-08).

## Objective

Introduce the `MissionResolver` seam over the single `kitty-specs/` walk: a Protocol (in `mission_runtime`
to avoid a new layer-ledger edge), an `FsMissionResolver` real adapter (wrapping the existing
`_build_index`), a `FakeMissionResolver` in-memory stub, and an optional `resolver` param on the free
`resolve_mission` so the walk is injectable at its single site. This WP delivers the seam + resolver-level
tests; WP03 threads it end-to-end.

## Key constraints (from the squad)
- **Protocol home = `mission_runtime`** (D-Q2 revised): the shell must reference a local type. Adapters
  import it downward via `specify_cli → mission_runtime` (package root). **No new
  `mission_runtime → specify_cli.context` edge** — verify `test_layer_rules.py` stays green.
- **Fail-closed-loud, no legacy branch** (FR-005): ambiguity → `AmbiguousHandleError`; cold-miss →
  `MissionNotFoundError` whose message names `spec-kitty migrate backfill-identity`. NO `if x is None:
  <fallback>` / `mission_id or slug`.
- **No cache** (C-005): request-scoped; instance-lifetime memoization only; no `@lru_cache`/module state.

## Subtasks

### T006 — Define the Protocol
- New `src/mission_runtime/mission_resolver_port.py`:
  ```python
  class MissionResolver(Protocol):
      def resolve(self, handle: str) -> ResolvedMission: ...
      def all_missions(self) -> list[ResolvedMission]: ...
  ```
- `ResolvedMission` is imported from `specify_cli.context.mission_resolver` (downward import, allowed) OR
  the Protocol is typed structurally — decide so the layer gate stays green; document the choice.

### T007 — `FsMissionResolver` (real)
- In `src/specify_cli/context/mission_resolver.py`, add `FsMissionResolver` bound to a `repo_root` at
  construction, wrapping the existing `_build_index` + the `resolve_mission` priority ladder.
- `resolve(handle)` = the current `resolve_mission` logic; `all_missions()` = the current `_build_index`
  output. Preserve the silent-skip of `mission_id`-less / non-dict-meta dirs (so `identity_audit.py`'s
  separate walk keeps its purpose — C-001).
- Request-scoped; optional instance-lifetime memoization only.

### T008 — `FakeMissionResolver` (stub)
- In the same module: constructed from `list[ResolvedMission]` (canonical-shaped fixtures). Zero FS access.
- Same fail-closed contract as the real adapter (CT-2/CT-3).

### T009 — Free `resolve_mission` gains optional `resolver`
- `def resolve_mission(handle, repo_root, *, resolver: MissionResolver | None = None) -> ResolvedMission:`
  → `return (resolver or FsMissionResolver(repo_root)).resolve(handle)`.
- This is the single injection site the trunk threads to (WP03). Existing callers (no resolver) behave
  exactly as before.

### T010 — Fail-closed cold-miss/ambiguity (FR-005)
- Confirm cold-miss raises `MissionNotFoundError` naming `spec-kitty migrate backfill-identity`; ambiguity
  raises `AmbiguousHandleError`. No silent fallback branch anywhere in the new code.

### T011 — Resolver unit tests (CT-1…CT-7)
- New `tests/specify_cli/context/test_mission_resolver_port.py`:
  - CT-1 priority ladder (ULID / mid8 / numbered slug / human slug / numeric prefix).
  - CT-2 ambiguous → raises; CT-3 cold-miss → raises + `backfill-identity` in message.
  - CT-4 `all_missions()` skips `mission_id`-less dirs.
  - CT-5 `FakeMissionResolver` satisfies CT-1…CT-4 with **no** `kitty-specs/` tree present.
  - CT-7 no module/process cache (two resolver instances see independent state).
  - Use realistic ULID-shaped fixtures (26-char), not toy handles.

## Branch Strategy
Planning branch and merge target: `feat/mission-resolver-port-2173`. Lane worktree per `lanes.json`.

## Definition of Done
- Protocol in `mission_runtime`; `Fs`/`Fake` adapters in `context/mission_resolver.py`; free
  `resolve_mission` accepts `resolver`.
- `test_layer_rules.py` green (no new ledger edge); resolver tests CT-1…CT-7 green incl. FS-free Fake.
- `ruff`/`mypy` clean; no `@lru_cache`/module cache; no legacy fallback branch.

## Risks / reviewer guidance
- Reviewer confirms **no new `mission_runtime → specify_cli.context` import** (run `test_layer_rules.py`).
- Confirm the Fake test truly runs with the specs dir absent (delete/point elsewhere in the fixture).
- Sonar census on the touched module; fold SAFE trivia.

## Activity Log

- 2026-07-08T19:10:06Z – claude:sonnet:python-pedro:implementer – shell_pid=4187596 – Assigned agent via action command
- 2026-07-08T19:41:53Z – claude:sonnet:python-pedro:implementer – shell_pid=4187596 – Ready for review: MissionResolver Protocol in mission_runtime/mission_resolver_port.py (structural ResolvedMissionLike via read-only @property, no new mission_runtime->specify_cli.context ledger edge); FsMissionResolver/FakeMissionResolver in context/mission_resolver.py; free resolve_mission(resolver=None) delegates. MissionNotFoundError message now names 'spec-kitty migrate backfill-identity' (FR-005/CT-3 gap fix). No cache (C-005), no is-None/or-slug fallback (D-05). ruff/mypy exit 0 on diff-scoped files. Full tests/architectural/ suite: 827 passed, 4 skipped, 0 failed (incl. test_layer_rules.py, test_mission_runtime_surface.py, test_no_dead_symbols.py). New tests/specify_cli/context/test_mission_resolver_port.py: 26 passed (CT-1..CT-7 incl. FS-free Fake).
- 2026-07-08T19:42:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=132450 – Started review via action command
- 2026-07-08T19:46:38Z – user – shell_pid=132450 – Review passed: layer-rules green (no new mission_runtime->specify_cli.context edge; structural ResolvedMissionLike mirror sound, mypy clean); FR-005 fail-closed verified (MissionNotFoundError names 'spec-kitty migrate backfill-identity', no is-None/or-slug fallback, structural guard test); no cache (C-005 struct+live-mutation test); CT-5 Fake FS-free proven; 153 context tests pass (no regression from message change); Fs/Fake adapters + free resolve_mission(resolver=None) delegate; surface-pin re-export sanctioned; ruff+mypy exit 0; 49 arch/port tests green.
