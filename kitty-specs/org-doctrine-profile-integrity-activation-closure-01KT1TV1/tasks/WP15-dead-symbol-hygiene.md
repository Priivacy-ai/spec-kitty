---
work_package_id: WP15
title: Dead-symbol gate hygiene
dependencies:
- WP12
- WP14
requirement_refs:
- FR-019
- FR-020
- FR-036
tracker_refs:
- "1588"
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T066
- T067
- T068
- T069
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
---

# WP15 — Dead-symbol gate hygiene

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Bring the dead-symbol gate to green for the in-scope symbols (FR-036/019/020): remove the 7 stale allowlist entries, remove the OperationalContext allowlist entries now that WP14 wired them, delete the orphaned empty category, and explicitly allowlist-with-tracker the two out-of-scope git/lanes offenders. This WP owns only the gate test; the *causes* of the charter sub-app offenders and the OC wiring are fixed in WP12/WP14.

## Context

- Spec FR-019/020/036, NFR-006; research R-011-E (gate already RED at branch point; offenders inherited from main; OC entries at `:407-410`; orphaned empty `_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY` at `:420-425`, unioned at `:538`; stale detector at `:771-802`).
- Out of scope: `git.sparse_checkout::SparseCheckoutKind`, `lanes.lifecycle_sync::LANE_AUTO_REBASE_FAILED` (documented pre-existing `main` regression).

### Code map

- `tests/architectural/test_no_dead_symbols.py` — `_SYMBOL_ALLOWLIST`, category C `:405-418` (OC entries `:407-410`), orphan category `:420-425` + union `:538`, stale detector `:771-802`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP12 (sub-app exports removed) + WP14 (OC wired) so removing these entries doesn't re-break the gate.

## Subtasks

### T066 — Remove 7 stale allowlist entries (FR-036)

**Steps**: Remove the 7 entries that now have callers: `specify_cli.next._internal_runtime.events::{DecisionInputAnsweredPayload, DecisionInputRequestedPayload, MissionRunCompletedPayload, MissionRunStartedPayload, NextStepAutoCompletedPayload, NextStepIssuedPayload}` and `specify_cli.lanes.auto_rebase::AutoRebaseReport`.

**Validation**: - [ ] entries gone; the stale-detector no longer flags them.

### T067 — Remove OperationalContext allowlist entries (FR-019)

**Steps**: Remove the 4 OC entries (`charter.invocation_context::{OperationalContext, build_operational_context, OperationalContext.require_active_profile, OperationalContext.require_active_role}`) now that WP14 gave them live callers. Leave `ContextPreconditionError`/`ConsistencyReport` per their own rationale unless they now have callers.

**Validation**: - [ ] OC entries removed; gate passes for them (callers exist post-WP14).

### T068 — Delete orphan category; track out-of-scope offenders (burn-down-compliant)

**Steps**: Delete the empty `_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY` declaration and its union term. Confirm the charter sub-app offenders are gone (fixed in WP12).

For the 2 git/lanes offenders (`SparseCheckoutKind`, `LANE_AUTO_REBASE_FAILED`, out of scope, tracked by [#1588](https://github.com/Priivacy-ai/spec-kitty/issues/1588)): the Burn-down Policy (charter §"Burn-down Policy" (a)) **fails CI on allowlist growth above baseline** (enforced by `tests/architectural/test_ratchet_baselines.py` against `tests/architectural/_baselines.yaml`), so **do not add a net-new allowlist entry without a baseline change**. Compliant path:
- This WP removes **7 stale + 4 OC = 11** entries (shrinkage) — the allowlist net-shrinks well below baseline.
- If the 2 external offenders must be allowlisted to keep CI green, add them **and** update `tests/architectural/_baselines.yaml` in the **same commit** with rationale + the #1588 reference, keeping net allowlist count ≤ the prior baseline (the 11 removals more than offset the 2 additions).
- Prefer leaving them un-allowlisted if the gate is otherwise satisfiable; #1588 owns the actual offender fix.
- **Never** silently fix the git/lanes source here (out of scope).

**Validation**: - [ ] orphan category removed; charter sub-apps no longer flagged; if the 2 offenders are allowlisted, `_baselines.yaml` updated in the same commit (net count ≤ baseline) and `test_ratchet_baselines.py` passes; #1588 referenced.

### T069 — Tests / gate

**Steps**: Run `pytest tests/architectural/test_no_dead_symbols.py` — it must pass. Add no new code symbols; this is allowlist + category hygiene.

**Validation**: - [ ] `test_no_dead_symbols.py` green.

## Definition of Done

- [ ] Gate green for in-scope symbols; 7 stale + 4 OC entries removed; orphan category deleted; 2 git/lanes offenders allowlisted-with-tracker. CC-2 pass. NFR-006 satisfied (in-scope scope).

## Risks

- **Ordering**: must run after WP12 (sub-apps) and WP14 (OC wiring) or the gate re-breaks. Verify `lanes.json` ordering.
- Do not "fix" the git/lanes offenders by editing their source (out of scope) — allowlist-with-tracker only.

## Reviewer Guidance (reviewer-renata)

- Confirm the gate passes and that removals correspond to symbols that genuinely gained callers.
- Confirm the 2 out-of-scope offenders are tracked, not silently fixed.
