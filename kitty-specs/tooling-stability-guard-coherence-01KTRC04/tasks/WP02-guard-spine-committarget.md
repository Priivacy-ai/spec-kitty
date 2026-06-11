---
work_package_id: WP02
title: 'Guard spine: commit_guard policy module + safe_commit(CommitTarget) + mechanical callers'
dependencies:
- WP01
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T15:27:47.228595+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Spine
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "148640"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/git/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/commit_guard.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/git/__init__.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/coordination/policy.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/types.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/implement.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Guard spine (ADR Step 7)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match for `src/specify_cli/git/` if none assigned.

---

## Objectives & Success Criteria
Complete **ADR 2026-06-03-2 "Strangler Step 7"** for the mechanical surface:
- New SK policy module `core/commit_guard.py` (D1): `evaluate(target: CommitTarget, protection_state, capability: GuardCapability) → GuardVerdict` — pure, the ONLY protection decision.
- `safe_commit` (git/commit_helpers.py) consumes `CommitTarget` as its atomic destination argument + an asserted `capability` param (default `standard`). **Capability grants for the legacy flows (release / upgrade / merge-bookkeeping) wire ATOMICALLY in the SAME commit as the signature change** (debby RISK-1) — the old channels remain TOLERATED (not deleted; that's WP03) so the guard is never broken mid-strangle.
- Convert the **13 mechanical callers** (your owned files minus commit_guard) to the CommitTarget path.
- **Done when:** evaluate() unit tests + the WP01 invariants are green; mechanical callers converted; NO WIP-broken guard at any commit.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-001, FR-008), plan.md (IC-02), data-model.md (GuardCapability/GuardVerdict/CommitTarget consumption), contracts/ (C-GUARD-1, C-GUARD-3a), research.md, research/plan-review-python-pedro.md (the caller census starting point), research/plan-review-architect-alphonso.md (capability adjudication)}`.
- `CommitTarget` EXISTS (`mission_runtime.context`) — consume, don't redefine. `evaluate` ECHOES `CommitTarget.ref`, never re-derives (C-GUARD-3a).
- Capability is **asserted-at-the-surface** (parameter; auditability for the LLM-agent threat model) — NEVER derived from message/file/env/topology. `GuardCapability` defaults `standard`; no capability can grant direct-push-to-origin/main.
- NOT in this WP: `safe_commit_cmd.py` (WP04), `upgrade.py`/`decision_log.py`/`mission_creation.py` (WP03), `agent/mission.py` (WP05), channel deletion (WP03).
- **Self-hosting:** this repo's own commits use this guard. Keep every commit on a working guard; run the WP01 suite before each commit. Escape hatch exists (`SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1`-style env, see commit_helpers) — do not remove it in this WP.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T004 — Caller census (first task)
- Grep `safe_commit\(|assert_not_protected_branch` across src/ + tests/; record EVERY site (17 confirmed by review) in a census table inside the commit message or a code comment block in commit_guard.py: file, call shape, destination source, which WP converts it. Confirm whether the `"release: "` prefix has ANY live producer (pedro suspects dead code) — if dead, note it; the capability enum still covers release flow for the release scripts.

### T005 — `core/commit_guard.py` (D1)
- `GuardCapability` (enum: standard/release_flow/upgrade_bookkeeping/merge_bookkeeping/test_mode), `GuardVerdict` (allowed, resolved_destination, reason), `evaluate(...)` pure function. `__all__` declared (C-007). Unit tests: placement-match allows; mismatch refuses with reason naming the resolved destination; each capability authorizes ONLY its flow; NO capability authorizes a push; default standard.
- Document in the module docstring: `GuardVerdict` is intentionally distinct from `policy/merge_gates.GateVerdict` (different domain).

### T006 — `safe_commit(CommitTarget, …, capability=standard)` — ATOMIC
- Convert the signature (keep a thin compat shim for the two-arg form if needed mid-WP, removed by WP03); the protection decision delegates to `commit_guard.evaluate`. In the SAME commit, the merge-bookkeeping callers you own (agent/tasks.py done-transitions etc.) pass their capability explicitly — so no flow loses its privilege before its capability exists. Old channels (prefix/bools) remain tolerated (logically OR'd) until WP03.

### T007 — Convert the 13 mechanical callers
- Each call site constructs/receives a `CommitTarget` (the ADR forensic pass: all existing pairs are already consistent — mechanical) and passes its capability where applicable (merge-bookkeeping sites: `merge_bookkeeping`). No caller re-derives a destination.

### T008 — Gates
- WP01 invariants green (xfails still xfail — channels not yet deleted); new unit tests green; `ruff`+`mypy` clean; full status/coordination smoke (`pytest tests/specify_cli/coordination tests/git -q` at minimum).

## Definition of Done
- evaluate() is the only decision path for converted callers; atomic capability wiring verified by reading the diff of each commit; WP01 suite green at EVERY commit; census recorded.

## Risks & Mitigations
- *Highest blast radius in the mission* → incremental commits, each self-consistent; never land a broken guard (run WP01 suite pre-commit).
- *Two-arg/CommitTarget mixed period* → compat shim documented + tracked for WP03 removal.

## Review Guidance
- Recommended: **architect-alphonso sign-off** (capability model, mechanism/policy split, C-GUARD-3a echo-never-derive) + **reviewer-renata**. Check: no caller derives privilege from message text; no new destination derivation; census complete.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T15:40:47Z – user – shell_pid=122180 – WP02 Guard spine (ADR Step 7) complete. Census: 17 safe_commit/assert_not_protected_branch sites; 7 safe_commit callers in owned files converted to CommitTarget (orchestrator_api/commands, invocation/executor, agent/workflow x2, agent/tasks x3, implement, coordination/transaction); accept.py+acceptance/__init__ call only assert_not_protected_branch (retained env hatch); coordination/policy+types are comments only. NOT mine: safe_commit_cmd.py [WP04], upgrade/decision_log/mission_creation [WP03], agent/mission.py [WP05], merge.py [other]. release: prefix has NO in-code safe_commit producer (pedro correct) but IS live at the manual/release-script git level (recent bad5f8219); release_flow capability correctly retained. NEW core/commit_guard.py (D1): GuardCapability enum + GuardVerdict + ProtectionState + pure evaluate() echoing CommitTarget.ref (C-GUARD-3a); __all__ declared. safe_commit delegates protection decision to evaluate; legacy 5 channels OR'd/tolerated (WP03 deletes). Merge-bookkeeping wired atomically (transaction.py + agent/tasks done-transitions = MERGE_BOOKKEEPING) in same commit as signature change. Gates: 15 evaluate() unit tests green; WP01 suite 4 passed/5 xfailed (no XPASS); coordination+git+executor suites green (124 passed); ruff clean; mypy clean on all changed lines (2 pre-existing _get_current_build_id no-any-return errors unrelated). Commits: bf381d678 (T005-T006 atomic), 8f58f4517 (T007). Note: 9 pre-existing test_acceptance_support.py failures (typer SystemExit(2), present at WP01 baseline 81e3fa7a4) are NOT this WP's regression.
- 2026-06-10T15:41:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=148640 – Started review via action command
- 2026-06-10T15:45:11Z – user – shell_pid=148640 – Review passed (incl. architect-alphonso sign-off): capability asserted-at-surface (defaulted param, never content/file/env-derived in NEW code, no push capability); evaluate() pure (ProtectionState injected) and ECHOES CommitTarget.ref (C-GUARD-3a verified by parametrized test); mechanism/policy split clean (__all__, GuardVerdict!=GateVerdict + operator hatch documented, WP03 deletion flagged). ATOMIC wiring confirmed in bf381d678 (signature change + transaction.py MERGE_BOOKKEEPING grant same commit, debby RISK-1). 7 callers convert to CommitTarget, none re-derive destination, merge-bookkeeping sites pass MERGE_BOOKKEEPING, compat shim flagged for WP03. Census/release-prefix-liveness sound (RELEASE_FLOW retained for live release.yml). Gates: protection-preserved 4 passed/5 xfailed NO XPASS (crown-jewel invariants survived); guard unit 15 green; coordination+git 107 passed/5 xfailed; ruff clean; mypy zero NEW (2 commit_helpers no-any-return pre-existing at 81e3fa7a4); 9 test_acceptance_support failures pre-existing at 81e3fa7a4 (identical set). Scope: owned files only, WP01 suite untouched, worktree clean.
