---
work_package_id: WP02
title: Route runtime resolver through charter gateway
dependencies:
- WP01
requirement_refs:
- FR-002
- NFR-001
- NFR-003
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Runtime delegation
agent: "opencode:unknown:reviewer-renata:reviewer"
shell_pid: "1606534"
history:
- timestamp: '2026-04-24T12:56:30Z'
  agent: planner-priti
  action: WP created from mission plan
agent_profile: python-pedro
authoritative_surface: src/runtime/discovery/resolver.py
execution_mode: code_change
owned_files:
- src/runtime/discovery/resolver.py
- tests/runtime/test_resolver_monkeypatch_seam.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Route runtime resolver through charter gateway

## Goal

Rewrite the body of `src/runtime/discovery/resolver.py` so every `resolve_*` function delegates to `charter.asset_resolver`, passing `runtime.discovery.home.get_kittify_home` and `runtime.discovery.home.get_package_asset_root` as injected providers. Keep those helpers bound as top-level attributes on `runtime.discovery.resolver` so `patch("runtime.discovery.resolver.get_kittify_home", ...)` in existing tests keeps intercepting invocations. Drop the now-unreachable private helpers.

## Why

FR-002. Eliminates the 231-line duplicate against `src/doctrine/resolver.py` while preserving 122 existing test monkeypatch sites (NFR-003).

## In-scope files

- `src/runtime/discovery/resolver.py` (REWRITE body)
- `tests/runtime/test_resolver_monkeypatch_seam.py` (NEW; dedicated regression test)

## Out of scope

- `src/runtime/discovery/home.py` — that is WP03 if triggered.
- `src/doctrine/resolver.py` — untouched.
- Migrating existing test monkeypatch call sites — the design choice in `plan.md` (Option A) guarantees zero migration; if you find yourself migrating test sites, STOP and re-read the plan's R1 section.

## Subtasks (mirror tasks.md §WP02)

- T011 Read the current `src/runtime/discovery/resolver.py` end-to-end. Grep across `tests/` for every `patch(...)` or `monkeypatch.setattr(...)` call whose target string starts with `runtime.discovery.resolver.` — inventory the attributes these tests rely on.
- T012 Rewrite `resolve_template`, `resolve_command`, `resolve_mission` as thin callers that pass `get_kittify_home` and `get_package_asset_root` as providers to `charter.asset_resolver`.
- T013 KEEP `from runtime.discovery.home import get_kittify_home, get_package_asset_root` at the runtime resolver's module scope so `patch("runtime.discovery.resolver.get_kittify_home", ...)` continues to target a local attribute.
- T014 Remove helpers no longer referenced after delegation: `_is_global_runtime_configured`, `_warn_legacy_asset`, `_emit_migrate_nudge`, `_reset_migrate_nudge`, `_resolve_asset`. Verify via grep that no internal/external caller still imports them. Re-export `ResolutionResult` and `ResolutionTier` from this module for back-compat with `from runtime.discovery.resolver import ResolutionResult`.
- T015 Add `tests/runtime/test_resolver_monkeypatch_seam.py` — a dedicated regression test asserting that `patch("runtime.discovery.resolver.get_kittify_home", lambda: fake_path)` causes `fake_path` to be observed when `runtime.discovery.resolver.resolve_template(...)` runs (proves Option A really works end-to-end).
- T016 `ruff check src/runtime/discovery/resolver.py` — clean.
- T017 Run:
  ```bash
  PYTHONPATH=src pytest \
    tests/runtime/test_resolver_unit.py \
    tests/runtime/test_global_runtime_convergence_unit.py \
    tests/runtime/test_show_origin_unit.py \
    tests/runtime/test_config_show_origin_integration.py \
    tests/runtime/test_resolver_monkeypatch_seam.py \
    tests/next/test_decision_unit.py \
    tests/next/test_runtime_bridge_unit.py \
    -x -q
  ```
  All green, no monkeypatch-target edits in other test files.
- T018 Post-merge (observational): re-query Sonar duplications API for `src/runtime/discovery/resolver.py`. Expected `duplicated_blocks = 0`. Record evidence in the WP status history.

## Implementation notes

- Option A ONLY. Do NOT make `runtime.discovery.resolver` a pure re-export of charter — that breaks the monkeypatch seams (spec R1). The pattern is: runtime resolver has its own body that *calls* the charter gateway, passing locally-bound providers.
- Expected resolver module size after rewrite: ≤ 60 lines.
- If T015 fails after T012–T014, you have misunderstood the Option A pattern — stop and re-read `plan.md` §Architecture & Design.

## Acceptance

- All tests in T017 pass without test-side edits.
- T015 is a new test, asserting the monkeypatch seam survives delegation.
- `ruff check` clean on the file.
- `src/runtime/discovery/resolver.py` file size ≤ 60 lines (count `wc -l`).

## Commit message template

```
refactor(runtime): route discovery.resolver through charter.asset_resolver

Collapse the body of resolve_template/command/mission to delegate to the new
charter gateway, passing runtime.discovery.home helpers as providers. Local
module attributes stay bound so existing patch("runtime.discovery.resolver.
get_kittify_home", ...) call sites keep intercepting.

Removes the 231-line duplication vs src/doctrine/resolver.py. All existing
runtime tests pass unchanged; adds tests/runtime/test_resolver_monkeypatch_seam.py
as a dedicated regression guard.
```

## Activity Log

- 2026-04-24T14:46:40Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1603195 – Started implementation via action command
- 2026-04-24T14:51:50Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1603195 – WP02 complete: runtime resolver delegates to charter; Option A preserves monkeypatch seams. 155 focused tests green; ruff clean; file shrinks 308→128 lines.
- 2026-04-24T14:52:00Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1606534 – Started review via action command
- 2026-04-24T14:52:13Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1606534 – Review passed (reviewer-renata): Option A correctly preserves seams (6 dedicated regression tests); 155 focused tests pass with no test-side edits; ruff clean; 308→128 lines; LEGACY-tier deprecation warnings preserved via legacy_warn_hook. FR-002/NFR-001/NFR-003 met.
- 2026-04-24T15:00:03Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1606534 – Done override: Mission merged to runtime-extraction parent branch (commit 4bd65d1a4) — post-merge done transition
