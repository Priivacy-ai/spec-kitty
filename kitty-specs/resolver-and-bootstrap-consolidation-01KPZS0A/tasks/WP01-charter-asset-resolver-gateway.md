---
work_package_id: WP01
title: Charter asset-resolver gateway
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-resolver-and-bootstrap-consolidation-01KPZS0A
base_commit: 657a57ca4d2da4278c47f9466d3040005f9c598c
created_at: '2026-04-24T13:51:17.489758+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Gateway
shell_pid: "1601171"
agent: "opencode:unknown:reviewer-renata:reviewer"
history:
- timestamp: '2026-04-24T12:56:30Z'
  agent: planner-priti
  action: WP created from mission plan
agent_profile: python-pedro
authoritative_surface: src/charter/asset_resolver.py
execution_mode: code_change
owned_files:
- src/charter/asset_resolver.py
- tests/charter/test_asset_resolver.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Charter asset-resolver gateway

## Goal

Create `src/charter/asset_resolver.py`. The module exposes asset-resolution functions (`resolve_template`, `resolve_command`, `resolve_mission`) and re-exports the `ResolutionTier` enum and `ResolutionResult` dataclass from `doctrine.resolver`. The three resolve functions accept injected `home_provider` and `asset_root_provider` callables so downstream callers (runtime) can pass their own monkeypatch-targetable helpers without the gateway caching them.

## Why

Today `src/runtime/discovery/resolver.py` duplicates 231 lines of `src/doctrine/resolver.py`. FR-001 asks for a charter-level gateway so runtime has a supported dependency target and doctrine remains the canonical implementation layer.

## In-scope files

- `src/charter/asset_resolver.py` (NEW)
- `tests/charter/test_asset_resolver.py` (NEW; create `tests/charter/` if it does not exist)

## Out of scope

- Changing `src/doctrine/resolver.py` — this WP must not touch doctrine.
- Wiring runtime to use the new gateway — that is WP02.

## Subtasks (mirror tasks.md §WP01)

- T001 Create `src/charter/asset_resolver.py` re-exporting `ResolutionTier` and `ResolutionResult` from `doctrine.resolver`.
- T002 Implement `resolve_template(name, project_dir, mission, *, home_provider, asset_root_provider)` using doctrine's 4-tier order (OVERRIDE → LEGACY → GLOBAL_MISSION → GLOBAL → PACKAGE_DEFAULT). Call `home_provider()` and `asset_root_provider()` at lookup time (NOT at module import) so caller-side monkeypatches win.
- T003 [P] Implement `resolve_command(...)` with the same provider-injection signature.
- T004 [P] Implement `resolve_mission(...)` with the same provider-injection signature.
- T005 Create `tests/charter/` if needed; add `tests/charter/test_asset_resolver.py`.
- T006 [P] Unit test — OVERRIDE tier wins when override path exists.
- T007 [P] Unit test — GLOBAL tier is consulted when override/legacy miss; uses `home_provider` callable.
- T008 [P] Unit test — PACKAGE_DEFAULT fallback uses `asset_root_provider` callable.
- T009 [P] Unit test — `home_provider` and `asset_root_provider` are invoked *per call*, not captured at import time (monkeypatch-seam contract). Use a `MagicMock` / spy.
- T010 Run quality gate on the files you touched:
  - `ruff check src/charter/asset_resolver.py tests/charter/test_asset_resolver.py`
  - `mypy src/charter/asset_resolver.py`
  - `pytest tests/charter/test_asset_resolver.py -x -q`

## Implementation notes

- Do not redefine `ResolutionTier` or `ResolutionResult`. Import and re-export from `doctrine.resolver`.
- The gateway's resolution logic can either (a) call into `doctrine.resolver` internals if they accept provider callables, or (b) re-implement the 4-tier chain ~50 lines using the injected providers. Option (b) is preferred per §Architecture & Design in `plan.md` (Gateway-A). Keep doctrine unchanged.
- Charter must not import from `runtime.*` or `specify_cli.*`. Layer rule; verify via `pytestarch` tests if already configured for charter.

## Acceptance

- Tests above all pass.
- `ruff`, `mypy` clean on the two files.
- `grep -r "runtime\|specify_cli" src/charter/asset_resolver.py` returns nothing (charter does not import runtime/specify_cli).
- File size expected ≤ 80 lines for `asset_resolver.py`; test file comparable.

## Commit message template

```
feat(charter): introduce asset_resolver gateway for doctrine-backed resolution

Adds src/charter/asset_resolver.py exposing resolve_template/command/mission
with injectable home_provider and asset_root_provider callables. Runtime will
route through this gateway in a follow-up WP to eliminate doctrine/runtime
resolver duplication while preserving monkeypatch seams.
```

## Activity Log

- 2026-04-24T13:51:18Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1570979 – Assigned agent via action command
- 2026-04-24T14:28:08Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1570979 – WP01 complete: charter.asset_resolver gateway + 15 unit tests. ruff/mypy/pytest all green.
- 2026-04-24T14:44:41Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1601171 – Started review via action command
- 2026-04-24T14:46:04Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1601171 – Review passed (reviewer-renata): charter/asset_resolver.py (175 lines) exposes resolve_template/command/mission with provider injection; grep confirms no forbidden runtime/specify_cli imports; 15 unit tests pass (tier precedence, provider-per-call contract, resolve_mission 4-tier); ruff + mypy clean. FR-001 and NFR-002 met.
- 2026-04-24T15:00:01Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1601171 – Done override: Mission merged to runtime-extraction parent branch (commit 4bd65d1a4) — post-merge done transition
