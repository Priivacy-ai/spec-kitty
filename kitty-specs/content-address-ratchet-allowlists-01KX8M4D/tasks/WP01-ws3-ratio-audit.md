---
work_package_id: WP01
title: WS3 ratio=1.00 audit residue
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1417908"
history:
- created at planning (tasks) — WS3 residue
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_layer_rules.py
- tests/architectural/test_template_governance_payload_contract.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Before reading anything else, load your assigned profile:
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read this mission's
[spec.md](../spec.md) §WS3 and the post-spec-squad classification in
[research.md](../research.md) (D-7 context) so you know these are the *residue* of
an audit whose bulk verdict was KEEP.

## Objective
Close the small, dependency-free residue of the ratio=1.00 audit (#2548): convert
two positive-literal `__module__` sub-tests to behavioural assertions, harden one
literal-pinned contract test, and record the 10-KEEP verdict. This is free/parallel
work — no dependency on the descriptor keystone.

## Context
The post-spec squad classified all 13 ratio=1.00 architectural tests: **ten are
legitimate KEEP** (behavioural/negative/import-layer invariants — no change), and
only these residual items are real work. Do NOT touch the ten KEEP files.

## Subtasks

### T001 — Convert the two `__module__` sub-tests in `test_layer_rules.py`
Targets: `test_unified_model_resolves_at_new_location` and
`test_legacy_contract_types_resolve_at_new_location`. They assert
`X.__module__ == "doctrine.missions.models"` — positive literal path shape that
re-pins symbol location. Re-express as **behavioural**: the unified model is
importable AND is the one the resolver/facade actually uses (import it via the
public surface + assert identity/usage, not the literal module string). The rest
of `test_layer_rules.py` is KEEP — leave the import-layer invariants untouched.

### T002 — Harden `test_template_governance_payload_contract.py`
It cross-checks template-promise ↔ resolver-reality but pins the promised surface
via inlined literal section names (`"Terminology Canon"`, `"DIRECTIVE_032"`, …)
and exact CLI-command-form strings that drift on any wording change. **Derive the
promised-surface set from the contract/schema** (the same source the resolver
reads) instead of inlining it, so the invariant survives wording edits. Keep the
behavioural promise↔reality assertion intact.

### T003 — Record the FR-012 audit verdict
Record (as a module docstring / comment block referencing
[research.md](../research.md) D-context) that the ten KEEP tests
(`test_no_raw_mission_spec_paths`, `test_safe_commit_import_boundary`,
`test_pytest_marker_convention`, `test_auth_transport_singleton`,
`test_status_module_boundary`, `test_tid251_enforcement`,
`test_guard_capability_call_sites`, `test_pytest_marker_correctness`,
`test_charter_facades_reexport_doctrine`, plus `conftest` infra) were audited and
validated as legitimate behavioural/negative/import-layer invariants — no change.
This closes the #2548 audit obligation.

### T004 — Plant-and-catch non-vacuity (FR-013)
For both hardened tests, add a plant-and-catch self-test proving they still bite:
- test_layer_rules converted sub-tests: plant a *wrong* resolver wiring → red.
- test_template_governance: plant a promised-surface item MISSING from the
  resolver output → red. And confirm a pure wording change to a section title does
  NOT red (the whole point of T002).

## Branch Strategy
Planning branch `analysis/test-change-coupling`; final merge target
`analysis/test-change-coupling` (→ PR to main). Your execution worktree is
allocated per the computed lane in `lanes.json` — run `spec-kitty agent action
implement WP01 --agent <you>` to enter it.

## Definition of Done
- The 2 `__module__` sub-tests survive a `__module__` relocation (behavioural).
- test_template_governance derives its promised-surface set (no inlined literal
  drift); survives a wording change; still reds on a real promise↔reality gap.
- FR-012 verdict recorded.
- `pytest tests/architectural/test_layer_rules.py tests/architectural/test_template_governance_payload_contract.py` green; full `tests/architectural/` stays 869/0.

## Reviewer guidance
Verify T001/T002 pin *behaviour*, not a new literal (no re-pinning). Confirm the
ten KEEP files are untouched. Confirm the plant-and-catch actually reds.

## Activity Log

- 2026-07-11T14:29:14Z – claude:sonnet:python-pedro:implementer – shell_pid=1262421 – Assigned agent via action command
- 2026-07-11T15:07:14Z – claude:sonnet:python-pedro:implementer – shell_pid=1262421 – Ready: WS3 residue — 2 __module__ sub-tests → behavioural, template-governance derives promised-surface from schema, 10-KEEP verdict recorded, plant-and-catch added; ruff diff-scoped exit 0; arch 850 passed / 0 failed.
- 2026-07-11T15:08:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=1417908 – Started review via action command
- 2026-07-11T15:12:39Z – user – shell_pid=1417908 – Ready for review: WS3 ratio-audit residue. T001 converted the two __module__ sub-tests in test_layer_rules.py to behavioural (resolver actually instantiates canonical MissionStep / MissionStepContract(Step)/DelegatesTo via public surface — no literal __module__ pin); T002 hardened test_template_governance_payload_contract.py to DERIVE the promised-surface set from the resolver's own sources (ACTION_CRITICAL_SECTIONS, DEFAULT_AUTHORITY_PATHS, fetch_stanza formatter, reviewer-renata profile directive-references) instead of inlined literals; T003 recorded the 10-KEEP FR-012 verdict as a module docstring; T004 plant-and-catch self-tests added (wrong-wiring reds, consistent wording-rename does NOT red). Ten KEEP files untouched. Validation: focused 2-file run 27 passed; diff-scoped ruff exit 0; full tests/architectural/ = 850 passed / 4 skipped / 0 failed (baseline preserved; +3 net tests are my additions).
- 2026-07-11T15:26:52Z – user – shell_pid=1417908 – Review passed (reviewer-renata/opus): WS3 residue; 27 focused + arch 850/0.
