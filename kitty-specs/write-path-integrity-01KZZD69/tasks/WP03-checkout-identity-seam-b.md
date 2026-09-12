---
work_package_id: WP03
title: Seam-B checkout-identity refusal for implement/review (#3128)
dependencies:
- WP01
requirement_refs:
- FR-005
- NFR-004
- C-001
- C-007
planning_base_branch: mission/write-path-integrity
merge_target_branch: mission/write-path-integrity
branch_strategy: Planning artifacts for this mission were generated on mission/write-path-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/write-path-integrity unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - Checkout identity
history:
- at: '2026-08-14T08:00:00+00:00'
  actor: system
  action: Prompt generated during tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/mission_runtime/
create_intent:
- tests/integration/test_wp_integrity_checkout_identity.py
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- tests/integration/test_wp_integrity_checkout_identity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Seam-B checkout-identity refusal (#3128)

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria

Refuse a **WP-execution** write (`implement`/`review`) when the invoking checkout is not the mission's
declared execution workspace (`workspace_path`), gated on **write-intent at the WP mutation chokepoint**
— without false-refusing reads or planning.

**Done when** (SC-004):
- From a foreign mission's lane (same registry), `implement`/`review` **refuse** (exit ≠ 0, actionable).
- From the mission's own lane, they **proceed**.
- Planning from any checkout resolving to the mission's `primary_root` **proceeds**.
- Pure context reads from any checkout **proceed** (never refused).
- The refusal raises a **distinct exception NOT subclassing `ActionContextError`** and cannot be
  swallowed by the audited fallbacks.

## Context & Constraints

- Spec US2, FR-005, SC-004; Plan IC-04; investigation `docs/plans/investigations/write-path-topology-root-cause.md`
  (Option A / #3128). Operator decision OD-1: **structural chokepoint**.
- **Chokepoint (OD-1)**: place the refusal at `resolve_workspace_for_wp` / the WP-claim path that
  `implement`/`review` funnel through (`workspace_path` populated at `resolution.py:662`). **NOT** on
  `resolve_action_context` — it is a **read vehicle** reused by ~20 callers (`_read_path_resolver.py:1622`).
- **`workspace_path`, not `execution_workspace`** (the latter is dead `=None` at `resolution.py:1339`).
- `resolve_ownership_claim` is a **non-authoritative fast-path** only (it classifies same-repo foreign
  lanes as OWNED, MF-8) — compare the mission's own `workspace_path`.
- Depends on WP01 (both compared paths must use the SAME symlink-canonicalization contract, else a
  `/var`→`/private/var` mismatch false-refuses an owned worktree).

## Subtasks & Detailed Guidance

### Subtask T014 – Distinct refusal exception
- **Steps**: Define a refusal exception that is **NOT** a subclass of `ActionContextError`, so the
  existing `except ActionContextError: return None` (`implement_cores.py:635`) cannot degrade it to the
  legacy meta-derived placement path.

### Subtask T015 – Refusal at the WP mutation chokepoint
- **Steps**: In `resolve_workspace_for_wp` (the `implement`/`review` mutation chokepoint), compare
  symlink-canonicalized `current_cwd` against the mission's own resolved `workspace_path`; refuse on
  mismatch. For **planning** actions compare `primary_root` (not `current_cwd`); reads carry no
  write-intent and are exempt.
- **Files**: `src/mission_runtime/resolution.py`.

### Subtask T016 – Write-intent marker table + threading (spec-mandated)
- **Steps**: Produce the enumerated table (plan IC-04) of which `implement`/`review` write sites carry
  `_MUTATING_WP_WRITE` and which read vehicles must NOT. Thread the write-intent signal from the true
  WP-write sites only. Verify no ~20 read-vehicle caller of `resolve_action_context` carries it.

### Subtask T017 – Narrow the swallow sites
- **Steps**: Physically narrow `implement_cores.py:635` (`except ActionContextError: return None`) and
  `mission_record_analysis.py:347` (`suppress(Exception)`) so a refusal cannot be swallowed. The broad
  `suppress(Exception)` is immune to the distinct-exception defense — scope it to the specific expected
  exceptions.
- **Files**: `src/specify_cli/cli/commands/implement_cores.py`,
  `src/specify_cli/cli/commands/agent/mission_record_analysis.py`.

### Subtask T018 – SC-004 two-mission local fixture
- **Steps**: Build a local fixture with **two** missions sharing one registry with distinct lanes.
  Assert: refuse-from-foreign-lane; proceed-from-own-lane; proceed-for-planning-from-root;
  proceed-for-pure-reads. No `spec-kitty-saas` dependency.
- **Files**: `tests/integration/test_wp_integrity_checkout_identity.py`.

## Definition of Done

- SC-004 fixture green across all four cases; refusal exception distinct + unswallowable; the marker
  table exists and no read vehicle is marked; `ruff`/`mypy` clean; NFR-004 (no extra git subprocess in
  the refusal path — pure path comparison).

## Risks & Reviewer Guidance

- **Reviewer**: the two biggest hazards are **over-mark** (a read vehicle carrying write-intent →
  false-refuses reads, SC-004 breach) and **under-mark** (a WP-write site missing the marker → #3128
  stays live). Check the marker table against `grep` of the real write sites. Confirm both compared
  paths are canonicalized identically (WP01 contract). Confirm `resolve_ownership_claim` is not used as
  the authority.
