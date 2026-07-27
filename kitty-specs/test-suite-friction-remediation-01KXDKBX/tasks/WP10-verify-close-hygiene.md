---
work_package_id: WP10
title: 'Verify-and-close hygiene: #2553 backfill + #2295 quarantine recount'
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-016
- NFR-002
tracker_refs:
- '2553'
- '2295'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
- T047
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/retrospective/test_summary_tolerance.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/retrospective/test_summary_tolerance.py
role: implementer
tags: []
shell_pid: "2964635"
shell_pid_created_at: "1783952729.87"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-009/FR-010 +
C-002, and [plan.md](../plan.md) §IC-08. **Boundaries:** this WP MUST NOT edit `tests/conftest.py` (that
quarantine-deselection hook is WP16's), MUST NOT drive the quarantine count to 0, and MUST NOT re-enable a
#2309-owned test.

## Objective

One housekeeping WP, two terminal zero-production-code tasks: (a) verify #2553's legacy-contract backfill is
a **real fix** (not a warning suppression) and close or minimal-fix; (b) recount the #2295 CI-quarantine
backlog against current `main` (the historical "17" is stale — ~1 active marker remains), triage the
residual marker, cross-reference #2309.

## Context

- #2553: verify whether the shipped legacy-contract-backfill work is a real contract fix or a warning
  suppression. `tests/contract/test_example_round_trip.py` is **read-only unless a real gap surfaces** — it
  is NOT in this WP's owned_files; do not drift into #2323's baseline accounting.
- #2295: exactly **one** active `@pytest.mark.quarantine` remains —
  `tests/retrospective/test_summary_tolerance.py:704`. The "17 quarantined" figure is stale.
- Cross-reference **#2309** (the routed-out daemon-reaper kill-gate bug) for reaper-family ownership; do NOT
  re-enable a #2309-owned test.

## Subtask guidance

- **T043 — verify #2553.** Inspect the shipped backfill. If it is a real contract fix, record the evidence
  and mark the issue closeable. If it is a warning suppression masking a real gap, land the **minimal** fix
  (do not re-open the full round-trip contract). If a real backfill gap surfaces, note that this task grows
  into its own WP (escalate rather than silently expand scope).
- **T044 — recount #2295.** Confirm the current active-quarantine count by grepping the tree
  (`git grep -n '@pytest.mark.quarantine' tests/`) — expect ~1, at
  `tests/retrospective/test_summary_tolerance.py:704`. Record the true count vs the stale "17".
- **T045 — triage the residual marker.** For the remaining marker: re-enable (if the root is fixed), fix the
  root, or record a tracked reason — cross-referencing #2309 for reaper-family ownership. Do NOT drive the
  count to 0; do NOT edit `tests/conftest.py`.
- **T046 — DoD evidence.** Record the verification/recount/triage outcomes; confirm **zero production
  behaviour change** (NFR-003) — this WP touches test code and issue state only.
- **T047 — tracer.** Append a tracer row noting the quarantine ratchet observed.

## Branch Strategy

Lane A root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] #2553 resolved to a verified state: recorded evidence it is a real fix (close) OR a landed minimal fix.
- [ ] #2295 recount recorded against current `main` (true count vs stale "17"), and the residual marker
      triaged (re-enable / fix-root / tracked-reason) with #2309 cross-reference.
- [ ] Quarantine count NOT driven to 0; no #2309-owned test re-enabled.
- [ ] `tests/conftest.py` NOT edited; `tests/contract/test_example_round_trip.py` not modified (read-only).
- [ ] Zero production behaviour change; affected test(s) green.
- [ ] **Tracer (FR-016):** append a catalog row for the quarantine ratchet (invariant-vs-shape, verdict).

## Risks

- **Scope creep into #2323** (round-trip baseline accounting) — stay bounded to verify + close/minimal-fix.
- **#2295 over-reach** — recount and triage only; the reaper-family bug is #2309's (routed out).

## Reviewer guidance

- Confirm no `conftest.py` edit and the count was not driven to 0.
- Confirm #2553's disposition is evidence-backed (real fix vs suppression), not asserted.

## Activity Log

- 2026-07-13T14:13:18Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:23:14Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Ready for review: verify-only WP, no code change. #2553 verified real fix (record_property replaced warnings.warn, signal preserved, NFR-006 zero warnings confirmed live). #2295 recounted at 1 active quarantine marker (not stale 17), triaged and tracked to #2342, cross-referenced #2309 (already resolved via pytest.mark.skip, not double-counted). Tracer row appended to tracer-design-decisions.md (committed on feat/test-suite-friction-remediation, e90906051).
- 2026-07-13T14:25:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Verify-only WP: #2553 real-fix closeable, #2295 recount=1; no code diff
- 2026-07-13T14:25:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=2964635 – Started review via action command
- 2026-07-13T14:37:25Z – user – shell_pid=2964635 – Verified: #2553 real record_property fix (14 nudges/0 warnings); #2295 recount=1
