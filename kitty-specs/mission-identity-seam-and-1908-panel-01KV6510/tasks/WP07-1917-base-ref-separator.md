---
work_package_id: WP07
title: '#1917 base-ref -- separator in _validate_base_ref'
dependencies: []
requirement_refs:
- FR-007
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-identity-seam-and-1908-panel-01KV6510
base_commit: 72d6dad089f77046a1418a5b7e4c024395be2a50
created_at: '2026-06-15T18:59:09.206480+00:00'
subtasks:
- T030
- T031
- T032
phase: Phase 3 - Cluster B
assignee: ''
agent: claude
shell_pid: '1019484'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- tests/specify_cli/cli/commands/test_implement_base_ref.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement_base_ref.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – #1917 base-ref `--` separator

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
`_validate_base_ref` must pass the operator `--base` value to `git rev-parse --verify` **after a
`--` end-of-options separator**, so a leading-dash value is treated as a ref, not an option
(defense-in-depth, #1917). Read [spec.md](../spec.md) FR-007, [research.md](../research.md) R4.

**Done when:** `implement --base=--something` treats the value as a ref (rev-parse gets it after
`--`); test green. Independent of the seam (no WP01 dependency).

## Context & Constraints
- TDD-first. Only `cli/commands/implement.py` (`_validate_base_ref`, def ~L215, caller ~L1158) + the
  new test. Do NOT touch `lanes/implement_support.py` (different file, WP04).

## Subtasks
### T030 — Failing regression (#1917) — probe MUST behave differently with/without `--`
Create `tests/specify_cli/cli/commands/test_implement_base_ref.py`. **Squad note:** a naive probe like
`--abbrev-ref` is consumed as an option with OR without `--` in some git builds (same rc) → a test
using it passes before AND after the fix (fake RED). Pick a `--base` value that `git rev-parse
--verify` treats as an **option** (changing behavior / leaking) when `--` is ABSENT but as a **ref**
(→ unknown-revision, non-zero, no option effect) when `--` is PRESENT — i.e. a value starting with
`--` that maps to a real rev-parse option. Assert: pre-fix it is consumed as an option (wrong
success/effect), post-fix it is validated AS A REF. The test MUST be genuinely RED before the
one-line fix. Use a controlled/monkeypatched runner that captures the exact argv passed to `git`.

### T031 — Insert the `--` separator
In `_validate_base_ref`, change `["git","rev-parse","--verify", base_ref]` to
`["git","rev-parse","--verify","--", base_ref]` (or the equivalent end-of-options placement for the
exact argv used). Keep the existing success/error semantics otherwise.

### T032 — Gates
`ruff`+`mypy`; `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_implement_base_ref.py -q`.
- [ ] leading-dash base value treated as ref; [ ] normal refs still validate; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
`--` separator added; regression test green; no behavior change for normal refs.

## Reviewer Guidance
Confirm the `--` is placed before the value (not after), normal refs unaffected, and the regression
test actually exercises a leading-dash value.
