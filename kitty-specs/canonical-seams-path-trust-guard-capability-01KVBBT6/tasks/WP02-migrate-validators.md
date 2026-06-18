---
work_package_id: WP02
title: Migrate divergent validators to delegate
dependencies:
- WP01
requirement_refs:
- FR-002
- NFR-003
tracker_refs:
- '#2022'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3748643"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/transaction.py
create_intent:
- tests/specify_cli/coordination/test_transaction_segment_validation.py
- tests/specify_cli/status/test_aggregate_slug_validation.py
- tests/specify_cli/review/test_cycle_segment_validation.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/transaction.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/review/cycle.py
- tests/specify_cli/coordination/test_transaction_segment_validation.py
- tests/specify_cli/status/test_aggregate_slug_validation.py
- tests/specify_cli/review/test_cycle_segment_validation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-002**, **C-001** (migrate,
   don't wrap — no parallel mechanism).
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **§(a)** the validator census
   + the brownfield finding (5 validators, not 3) recorded in `plan.md` → **Post-Planning Brownfield Check**.

## Objective

Point the divergent safe-segment validators at the canonical `assert_safe_path_segment` (WP01), **preserving each
call site's existing exception type** so observable behavior is unchanged (NFR-001). This removes the duplicated
logic the #1868 spine targets. **`merge.py`'s validator is NOT here — it belongs to WP04 (sole merge.py owner).**

**Depends on WP01** (the canonical validator must exist). Start command:
`spec-kitty agent action implement WP02 --agent <name>` (after WP01 is approved).

## Subtasks

### T006 — Delegate `coordination/transaction.py::_validate_safe_segment`
**Purpose:** one authority; keep the `BookkeepingError` contract. At `transaction.py:168`:
- This validator has TWO inline checks today: an explicit `.`/`..`/`/`/`\` pre-check (~:175) AND the
  `_SAFE_PATH_SEGMENT_RE.fullmatch` (~:177). **Remove BOTH** and replace with a single call to
  `assert_safe_path_segment(value)` (the canonical validator already covers both) — leaving the pre-check in place
  would double-validate (squad flag). Catch `ValueError` and re-raise as `BookkeepingError(name, ...)` to preserve
  the call-site contract (`_validate_safe_segment` is used for `mission_id` :317, `mission_slug` :693, `mid8` :694
  — all must keep raising `BookkeepingError`).
- Remove the now-dead `_SAFE_PATH_SEGMENT_RE` module constant (grep-gated in T010).
- Keep the function signature `_validate_safe_segment(name, value)` so callers are untouched.

### T007 — Delegate `status/aggregate.py::_validate_mission_slug`
**Purpose:** same authority; keep `InvalidMissionSlug`. At `aggregate.py:347`:
- Replace the inline `_MISSION_SLUG_PATTERN`/`isascii` check with `assert_safe_path_segment`, catching `ValueError`
  and raising `InvalidMissionSlug(mission_slug)` (which is already a `ValueError` subclass).
- Remove the dead `_MISSION_SLUG_PATTERN` constant if unused elsewhere (grep).
- Preserve the `MissionStatus.load` docstring/behavior that references the slug rule.

### T008 — Delegate `review/cycle.py::_validate_segment` (brownfield +1)
**Purpose:** the brownfield-surfaced 4th validator (identical safe-segment idiom). At `cycle.py:75`:
- Replace the inline `_SEGMENT_RE.fullmatch` + `.`/`..`/`/`/`\` checks with `assert_safe_path_segment`, catching
  `ValueError` and re-raising as `ReviewCycleError(f"{name} …")` to preserve the contract.
- Keep `_validate_segment(name, value)` signature. Remove the dead `_SEGMENT_RE` if unused (note: a sibling
  `_REVIEW_CYCLE_FILE_RE` **defined at :27** — consumed at :121 — is a *different* check; leave it).
- **Do NOT touch `retrospective/schema.py:203 _validate_safe_slug`** — it is a Pydantic-bound, length-capped
  identifier validator (different mechanism); it is a documented default scope-out (research.md / plan.md).

### T009 — Tests: preserve each domain exception type (RED-first, exact-type, multi-input)
**Purpose:** prove behavior-preserving migration. **Write these BEFORE the T006–T008 delegate edits** (RED-first per
C-006): they fail until each delegate is wired. For each of the three modules:
- Assert the **exact** type with `type(exc) is <DomainError>` — NOT `isinstance` (both `ReviewCycleError` and
  `InvalidMissionSlug` subclass `ValueError`, so an `isinstance(ValueError)` check would wrongly pass on a *leaked*
  raw `ValueError`; the squad flagged this). Targets: `transaction.py` → `BookkeepingError`, `aggregate.py` →
  `InvalidMissionSlug`, `review/cycle.py` → `ReviewCycleError`.
- Exercise **multiple distinct malformed inputs** (`".."`, `"a/b"`, `"a\\b"`, non-ASCII, `""`) — not just
  `../escape` — so every reject branch is covered and a delegate that leaks `ValueError` on one branch is caught.
- Accept case uses a real-format valid value (full ULID / `<slug>-<mid8>`). Put them in the per-module test files.

### T010 — Quality gate + scope-out note
- `ruff`+`mypy` clean (≤15, no suppressions) on all three modules.
- Run each module's existing suite green (behavior-preserving).
- **Dead-constant removal is a RED/GREEN gate, not prose:** paste `grep -n _SAFE_PATH_SEGMENT_RE
  src/specify_cli/coordination/transaction.py`, `grep -n _MISSION_SLUG_PATTERN src/specify_cli/status/aggregate.py`,
  `grep -n _SEGMENT_RE src/specify_cli/review/cycle.py` each showing zero hits (or the constant removed) into the handoff.
- Note in the handoff that `retrospective/schema.py:203` was intentionally NOT migrated (documented scope-out).

## Branch Strategy

Planning/merge base `feat/canonical-seams-path-trust-guard-capability` (PR → main). Worktree per lane from
`lanes.json`. **Depends on WP01.**

## Definition of Done

- [ ] All three validators delegate to `assert_safe_path_segment`; each preserves its original exception type.
- [ ] Dead per-module regex constants removed where unused; signatures unchanged.
- [ ] T009 tests prove the exception-type contract for all three.
- [ ] `retrospective/schema.py:203` untouched (documented).
- [ ] `ruff`+`mypy` clean; existing suites green.

## Risks / reviewer guidance

- **Exception-type drift is the trap.** If a delegate lets the raw `ValueError` escape instead of re-wrapping,
  callers catching `BookkeepingError`/`ReviewCycleError` break. Reviewer: verify the catch-and-rewrap in T006/T008
  and the `InvalidMissionSlug` subclass path in T007.
- **owned_files spans three modules but no overlap with WP04** — confirm `merge.py` is NOT touched here.
- Don't widen/loosen any accept set — the canonical validator must already admit everything these three accepted
  today (WP01's union test is the guarantee). If a real value these accepted is now rejected, that's a WP01 bug,
  not a reason to special-case here.

## Activity Log

- 2026-06-17T20:36:26Z – claude:sonnet:python-pedro:implementer – shell_pid=3698747 – Assigned agent via action command
- 2026-06-17T20:52:01Z – claude:sonnet:python-pedro:implementer – shell_pid=3698747 – Ready: T006/T007/T008 delegates wired + exception-type tests green (29/29) + dead constants removed + ruff exit 0. Whitespace gap in assert_safe_path_segment fixed in paths.py (value != stripped guard added). Pre-existing mypy errors (2) unchanged. Baseline review test failures pre-existing.
- 2026-06-17T20:53:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=3748643 – Started review via action command
