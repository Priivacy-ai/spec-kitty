---
work_package_id: WP02
title: Verify factor-(a) + contract-conformance boundary adjudication
dependencies: []
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: feat/ci-delivery-topology
merge_target_branch: feat/ci-delivery-topology
branch_strategy: Planning artifacts for this mission were generated on feat/ci-delivery-topology. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-delivery-topology unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
agent: "claude"
shell_pid: "2754847"
history:
- 'Created by planner for #2283 Phase-3 tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_unit_contract_residual_gate.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_unit_contract_residual_gate.py
role: implementer
tags: []
task_type: implement
---

# WP02 – Verify factor-(a) + contract-conformance boundary adjudication

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (Sonnet-5). Read `spec.md` (FR-004/005, C-002/003) + `plan.md` (IC-02). Study `ci-quality.yml:2407-2421` (the `unit-contract-residual` job) + `:3437` (`quality-gate.needs`) + `test_marker_job_completeness.py:288` (the EXISTING exactly-one assertion — do NOT duplicate it).

## Objective
Pin factor-(a)'s already-landed gate against regression (the 2 genuinely-uncovered facts only) + adjudicate the (c) boundary. NO workflow edit, NO new (c) sweep/allowlist mechanism (C-002).

## Changes
- **T004 — verify factor-(a) (FR-004)** in `tests/architectural/test_unit_contract_residual_gate.py`: assert ONLY the two facts NOT already covered by `test_marker_job_completeness.py` — (1) the `unit-contract-residual` job is **always-on** (parse `ci-quality.yml`: the job has NO `if:` gate), and (2) it is a **named member of `quality-gate.needs`**. Add a module docstring/comment **referencing** `test_marker_job_completeness.py:288` for the exactly-one-selects invariant (do NOT re-assert it — two tests pinning one fact drift + trip Sonar duplicate-logic). Read-only over the workflow; **NO workflow edit**. ⚠️ **Fault-injection / red-first (MANDATORY — match the directory discipline, cf. `test_workflow_coherence.py::test_faultinjection_*_reds` `:291`+):** prove each assertion BITES by feeding a **synthetic** workflow model where the residual job carries an `if:` gate (→ the always-on assertion reds) OR is dropped from `quality-gate.needs` (→ the membership assertion reds). The parse uses `.get(key, empty)`, so a mis-keyed lookup would silently yield empty and pass vacuously — the fault-injection is what stops the DIR-041 "passes-for-the-wrong-reason" vacuous green.
- **T005 — boundary adjudication + filed issue (FR-005)** in `contracts/boundary-decision.md`: record the DIR-003 decision resolving the three-mechanism overlap —
  - **#2438 discharges factor (c-dynamic) ONCE IT MERGES** to upstream (its `pre_review_gate.py` is not yet on-branch) → state this **conditionally** ("delivered-pending-#2438-merge, NOT closed").
  - **(c-static / c′)** (repo-wide assert-absence of a retired-contract literal / `falls_back` name / removed-signature call-site that no test exercises) → owned by **CT7 (#2077)** with the sharpened payload ("mechanise the `test_no_legacy_*` grep-absence family into a content-anchored, allowlist-free retired-contract sweep, triggered on shared-contract retirement").
  - The durable missing boundary: a shared contract + its retirement isn't a modeled, owned artifact with a declared consumer set → file a **contract-ownership boundary** issue (`gh issue create` — unset GITHUB_TOKEN; parent under the #2283/#2077 thread) and **EMBED its URL in this decision record** (SC-005 — grep-verifiable). **Ship NO (c) mechanism code / NO new allowlist artifact** (C-002).

## DoD
- The verify test asserts always-on + `quality-gate.needs` membership, references (doesn't duplicate) the exactly-one assertion; no workflow edit.
- **Red-first proven**: the test REDS on a fault-injected synthetic model (residual job with an `if:`, or dropped from `needs`) — it cannot vacuous-green on a mis-parse (DIR-041).
- `boundary-decision.md` records the conditional (c-dynamic) discharge + the (c-static)→CT7 handoff + the durable-boundary statement, with the **filed contract-ownership issue URL embedded**.
- No new (c) sweep/allowlist mechanism; `PWHEADLESS=1 uv run pytest tests/architectural/test_unit_contract_residual_gate.py -q` green; `ruff` clean; terminology guard green (the decision doc is prose).

## Commit
`git add tests/architectural/test_unit_contract_residual_gate.py kitty-specs/ci-local-preflight-parity-01KWXWY0/contracts/boundary-decision.md && git commit -m "docs(#2283): verify factor-(a) residual gate + adjudicate the (c) contract-conformance boundary (c-dynamic→#2438 conditional; c-static→CT7 #2077) — refs #2283"`

## Report back
The verify test (the 2 asserted facts + the reference to the existing exactly-one assertion); the boundary decision (the conditional (c-dynamic) wording + the CT7 handoff + the filed issue **URL embedded**); confirmation NO (c) mechanism/allowlist shipped; pytest + ruff + terminology; lane commit SHA + the filed issue number.

## Activity Log

- 2026-07-07T09:42:02Z – claude – shell_pid=2754847 – Assigned agent via action command
