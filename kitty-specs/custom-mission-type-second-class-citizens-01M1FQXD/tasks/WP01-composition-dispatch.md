---
work_package_id: WP01
title: '#3830 composition dispatch — remove misplaced early return, log genuine resolution failures'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
planning_base_branch: fix/custom-mission-type-second-class-3830
merge_target_branch: fix/custom-mission-type-second-class-3830
# DO NOT re-run 'finalize-tasks' without --validate-only for this mission -- its branch_strategy generator is topology-blind (see tracer-tooling-friction.md / SPEC-KITTY-LEDGER.md SK-133) and will silently overwrite this hand-corrected single_branch text. If a non-validate-only run is unavoidable, immediately re-apply this exact branch_strategy text afterward.
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-type-second-class-3830; this mission ships as a single branch/one PR onto that existing branch (topology single_branch) — completed changes must merge back into fix/custom-mission-type-second-class-3830, never a dependency-specific or per-WP branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Composition dispatch
history:
- timestamp: '2026-09-02T00:00:00Z'
  agent: system
  action: Prompt generated via spec-kitty agent mission finalize-tasks
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_composition.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/next/test_composition_gate_widening.py
- tests/runtime/test_bridge_composition.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – #3830 composition dispatch

## Why this WP exists

`_composition_dispatch_inputs` already knows how to resolve `profile_hint` via
`_resolve_step_agent_profile`/`PromptStep.agent_profile` — the FR-008-mandated canonical
resolution path. The bug is that this call is **skipped** precisely when the dispatched
action is a member of the mission type's own `action_sequence`
(`runtime_bridge_composition.py:303-336`, a misplaced early `return None, None`). This WP
removes that early return so the canonical path always runs, and separates "resolution
genuinely failed" from "resolution succeeded" in the surrounding `except Exception: pass`
(currently a silent swallow with no diagnostic surface at all).

This WP owns FR-001, FR-002, FR-003, NFR-001. See `plan.md` §Architecture — Seam Mapping,
§ATDD-First (FR-001/003 and FR-002 rows), §Blast Radius, and §Campsite-Clean Scope for the
binding decisions this WP implements — do not re-derive them.

## Subtasks

### T001 — Campsite-clean: correct the stale C-008 comments (behavior-preserving, own commit)

Per `plan.md` §Campsite-Clean Scope, this is the **first** commit in this WP, before any
functional change, and stays comment-only:

- `runtime_bridge_composition.py:127` — `_should_dispatch_via_composition`'s header comment
  claims "C-008: dispatch is hard-guarded on `mission == "software-dev"`." This is stale;
  the real gate is `action_sequence` membership for the resolved mission type, any type.
  Correct the comment to state the real gate.
- `runtime_bridge.py:1777-1779` (verified this session at the docstring text ending "C-008
  hard-guards this on `mission == "software-dev"`; every other mission falls through
  (returns `None`) to composition unchanged...") — `_dn_composition_dispatch`'s docstring
  makes the identical stale claim. Correct it the same way.

Do **not** "fix" the functional code to match the stale comment — the comment is wrong, not
the dispatch behavior it describes (`plan.md` §Blast Radius drift note).

### T002 — RED-FIRST repro: FR-001/FR-003 (custom-type dispatch)

Through the **pre-existing entry point** (`spec-kitty next`, not a white-box unit call):
drive a custom mission type (e.g. `qa`) whose dispatched action is a member of its own
`action_sequence`. Reproduce, live, the current `profile_hint is required` failure — this
is the failure the early `return None, None` at `runtime_bridge_composition.py:303-336`
causes by skipping `_resolve_step_agent_profile` entirely. Capture this as a failing test
in `tests/next/test_composition_gate_widening.py` or `tests/runtime/test_bridge_composition.py`
(whichever suite's existing fixtures fit) before making the functional change. Never
retry-to-green.

### T003 — Remove the misplaced early return; restore the canonical resolution path

Remove the early `return None, None` in the composition-dispatch input-building path
(`runtime_bridge_composition.py:303-336`) so `_resolve_step_agent_profile`/
`PromptStep.agent_profile` resolution always runs, including when the action is a member of
the mission type's own `action_sequence`. Confirm T002's failing test now passes. `plan`'s
own distinct failure mode (`StepContractExecutionError("No step contract found for
mission/action plan/<action>")`, `plan.md` §Blast Radius) must remain completely unchanged
— `plan` is not a beneficiary of this fix and must not start resolving via this path.

### T004 — RED-FIRST repro: FR-002 (malformed org pack swallowed silently)

Own acceptance contract, distinct from T002/T003's: drive `_composition_dispatch_inputs`
(via `spec-kitty next`) against a mission type whose `resolve_mission_type_context` call
genuinely raises (e.g. a malformed org pack triggering
`charter.activation.mission_type_profiles.UnknownMissionTypeError`). Reproduce, live,
before the fix, that the bare `except Exception: pass` swallows this with **no log record
at all** — indistinguishable from the ordinary case where resolution simply succeeds.
Capture as a failing/asserting test.

### T005 — Fix the except-clause: log genuine failures, stay silent on ordinary success

In the `except Exception` around the `_resolve_step_agent_profile` call, replace the bare
`pass` with a call to the module's own `logger`
(`logging.getLogger("runtime.next.runtime_bridge")`, `runtime_bridge_composition.py:101`,
already used via `logger.warning`/`logger.exception` elsewhere in this file) — a genuine
resolution failure now produces a log record. The ordinary "resolution succeeded, action
is/isn't in its own sequence" case (which must legitimately keep resolving unchanged, per
NFR-001 — it is not an error) must continue to log nothing. Confirm T004's test now
observes a log record for the malformed-pack case, and add a companion assertion that the
ordinary successful-resolution case still logs nothing (the two cases must be
distinguishable by log presence, not conflated).

### T006 — Blast Radius non-regression proof

Per `plan.md` §Blast Radius, prove for each built-in type that composition dispatch is
unaffected by this fix:

- `software-dev`, `research`, `documentation`: resolve `profile_hint` via
  `_ACTION_PROFILE_DEFAULTS` exactly as before (each has table entries) — unchanged.
- `plan`: dispatching an action in `plan`'s own `action_sequence` still raises
  `StepContractExecutionError("No step contract found for mission/action plan/<action>")`
  — not `profile_hint is required`, not any newly-introduced behavior (User Story 1 AC4,
  SC-001a). Add/confirm a regression test pinning this distinct failure mode.
- Any custom type (e.g. `qa`): now resolves via `PromptStep.agent_profile`/pack
  `agent-profile:` entries (the fix target, confirmed by T002/T003).

### T007 — Gate run

Per `plan.md` §Gate Set:
- `make ruff/lint` on every file this WP touches.
- Targeted pytest: `tests/next/`, `tests/runtime/`.
- `diff-coverage` critical-path 90% gate applies to `src/runtime/next/runtime_bridge_composition.py`
  (matches the `src/runtime/next/*` critical-path entry) — this WP's new/changed lines in
  that file must clear it. `mission_step_contracts/executor.py` and `runtime_bridge.py` are
  not numerically gated but still need focused tests per the charter's
  every-new-branch-needs-tests rule.
- Validate any `patch()` targets used in new/changed tests per the repo's patch-target
  hygiene gate.
- Before attributing any red to this WP, classify it against #3284's known-red baseline (23
  failures + 2 errors) and the #3283 shared test-venv lock — run the same test against
  `main`/the merge-base first. A red not covered by #3284 gets filed as its own GitHub issue
  (with the exact command, failure summary, and why it's believed pre-existing) before being
  treated as baseline — never silently waved through.

## Definition of Done

- Campsite-clean comment fix landed as its own behavior-preserving commit, before any
  functional change.
- FR-001/FR-003: the early-return removal restores canonical `profile_hint` resolution for
  any custom mission type's own-sequence actions; `plan`'s distinct
  `StepContractExecutionError` is unchanged (AC4).
- FR-002: a genuine `resolve_mission_type_context` failure now produces a log record via the
  module's own logger; the ordinary success path still logs nothing (NFR-001).
- Blast Radius table (T006) proven for all four built-in types plus one custom type.
- Gate Set items (T007) all green, or every red explicitly classified against #3284 with a
  filed issue for anything new.
