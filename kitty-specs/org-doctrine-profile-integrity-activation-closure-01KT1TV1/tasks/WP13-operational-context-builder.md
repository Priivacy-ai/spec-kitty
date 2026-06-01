---
work_package_id: WP13
title: OperationalContext assembler + guards
dependencies: []
requirement_refs:
- FR-017
- FR-018
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-org-doctrine-profile-integrity-activation-closure-01KT1TV1
base_commit: 374f90139e8c35db9845c91071a298f60e082aa3
created_at: '2026-06-01T20:54:32.869098+00:00'
subtasks:
- T059
- T060
- T061
agent: "claude:opus:python-pedro:implementer"
shell_pid: "1655372"
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/invocation_context.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/charter/invocation_context.py
- tests/charter/test_operational_context.py
role: implementer
tags: []
---

# WP13 — OperationalContext assembler + guards

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Turn `build_operational_context()` from an all-None stub into a **pure explicit-parameter assembler** in `charter`, and make `require_active_profile()`/`require_active_role()` raise `ContextPreconditionError` with actionable messages (FR-017 builder, FR-018). Keeping the builder pure + in `charter` preserves C-006 by construction. Wiring at call sites is WP14.

## Context

- Spec FR-017/018, C-006; research R-011-E (definition at `charter/invocation_context.py`: `OperationalContext` :147, guards :164/:172, stub `build_operational_context` :186 returns all-None).
- Data model §7. Contract C4.1, C4.2.

### Code map

- `src/charter/invocation_context.py:147` `OperationalContext`; `:164` `require_active_profile`; `:172` `require_active_role`; `:186` `build_operational_context` (stub).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. No dependencies — can start immediately (parallel with WP01/WP02).

## Subtasks

### T059 — Pure explicit-parameter assembler

**Steps**: Reimplement `build_operational_context(*, active_model=None, active_profile=None, active_role=None, current_activity=None, tech_stack=None) -> OperationalContext` as a pure assembler that just packages the provided values. It must NOT reach into runtime/global state and must NOT import `specify_cli`/`doctrine` runtime. Update the docstring to state callers pass values as data (C-006).

**Validation**: - [ ] returns a populated context from explicit args; no hidden state access; `charter` imports unchanged (no specify_cli).

### T060 — Guards raise `ContextPreconditionError`

**Steps**: `require_active_profile()` / `require_active_role()` raise `ContextPreconditionError` with actionable messages (what's missing, how to provide it) when the field is absent; return the value when present.

**Validation**: - [ ] guards raise on absent fields with actionable text; return value when present.

### T061 — Tests

**Steps**: `tests/charter/test_operational_context.py` — assembler packages values; guards raise on absent and return on present; the all-None stub behavior is gone.

**Validation**: - [ ] green; ruff/mypy clean.

## Definition of Done

- [ ] Pure assembler + guards with actionable errors; tests green; C-006 preserved (no upward imports). CC-2 pass.

## Risks

- Keep it pure — any reach into runtime state would tempt a layering violation. Wiring/inputs come from WP14 call sites.

## Reviewer Guidance (reviewer-renata)

- Confirm the builder is pure and takes explicit params (C-006 by construction).
- Confirm guards raise `ContextPreconditionError` with actionable messages.

## Activity Log

- 2026-06-01T17:29:16Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – Assigned agent via action command
- 2026-06-01T20:54:33Z – claude:opus:python-pedro:implementer – shell_pid=1655372 – Assigned agent via action command
- 2026-06-01T20:56:45Z – claude:opus:python-pedro:implementer – shell_pid=1655372 – WP13 recovered: OperationalContext assembler + guards; 15 tests green
