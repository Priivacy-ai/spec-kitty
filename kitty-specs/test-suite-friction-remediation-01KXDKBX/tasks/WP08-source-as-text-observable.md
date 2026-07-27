---
work_package_id: WP08
title: Source-as-text wiring → observable contract (+ sibling audit)
dependencies: []
requirement_refs:
- FR-007
- FR-016
- NFR-002
tracker_refs:
- '2075'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/status/test_agent_status_emit_aggregate_wiring.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/status/test_agent_status_emit_aggregate_wiring.py
- tests/test_dashboard/test_api_handler.py
- tests/agent/glossary/test_event_emission.py
- tests/sync/tracker/test_service.py
role: implementer
tags: []
shell_pid: "2975016"
shell_pid_created_at: "1783952825.42"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-007 + the Domain
Language rows "Source-as-text test" / "Observable contract", [data-model.md](../data-model.md) E-05, and
[plan.md](../plan.md) §IC-06. **Critical framing (paula's read):** the 3 siblings are *largely already
observable-outcome* — audit before you touch, and do NOT manufacture a false shared helper across four
distinct seams.

## Objective

Re-point the **confirmed** source-as-text twin to an **observable contract** (a persisted artifact asserted
with **no `@patch` on the SUT**), then audit the 3 siblings and re-point **only** those the audit confirms
are genuine source-as-text/wiring twins.

## Context — the four seams

| file | status | action |
|------|--------|--------|
| `tests/status/test_agent_status_emit_aggregate_wiring.py:211` (`test_command_module_has_no_direct_transactional_reference`, `read_text()`) | **confirmed twin** | re-point to observable |
| `tests/test_dashboard/test_api_handler.py` | audit | re-point ONLY if a genuine twin |
| `tests/agent/glossary/test_event_emission.py` | audit | re-point ONLY if a genuine twin |
| `tests/sync/tracker/test_service.py` | audit | re-point ONLY if a genuine twin |

Observable artifacts per seam: a persisted event in `status.events.jsonl`, an HTTP response body, a rendered
output, or config on disk (data-model E-05).

## Subtask guidance

- **T033 — re-point the confirmed twin.** Replace the `read_text()`-asserts-a-substring guard at `:211` with
  an assertion on a persisted/observable artifact produced by exercising the emit path — no `@patch` on the
  module under test. Keep at most one real-outcome test for this seam.
- **T034 — audit `test_api_handler.py`.** Determine whether it asserts source-as-text/wiring or already
  asserts an observable outcome (HTTP response body). Re-point ONLY if a genuine twin; otherwise leave it and
  record "already observable" in the review evidence.
- **T035 — audit the other two siblings.** Same audit for `glossary/test_event_emission.py` (persisted
  event) and `sync/tracker/test_service.py` (observable response/config). Re-point only genuine twins; do
  NOT hand-roll a shared helper spanning the four seams.
- **T036 — non-fakeable DoD.** Every re-pointed test asserts a persisted artifact and carries **no `@patch`
  on the SUT**. Run: `.venv/bin/python -m pytest tests/status/test_agent_status_emit_aggregate_wiring.py tests/test_dashboard/test_api_handler.py tests/agent/glossary/test_event_emission.py tests/sync/tracker/test_service.py -q`.
- **T037 — gates + tracer.** `ruff`/`mypy` clean; append the parity/observable tracer rows.

## Branch Strategy

Lane A root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] The confirmed `:211` twin re-pointed to an observable contract with **no `@patch` on the SUT**.
- [ ] Each of the 3 siblings is either re-pointed (if a genuine twin) OR explicitly recorded as
      already-observable — audit outcome documented per file.
- [ ] No false shared helper spanning the four seams.
- [ ] The four files' suites green.
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append catalog rows for each behavioural-parity/observable seam touched
      (invariant-vs-shape discriminator) to `../tracer-design-decisions.md` + friction log.

## Risks

- **Over-deleting a legitimate boundary-verification test** — keep the real-outcome test; assert a persisted
  artifact with no SUT patch, rather than deleting coverage.
- **Manufacturing a false shared helper** — the four seams differ; a shared helper masks their real
  contracts. Re-point each to its own observable artifact.

## Reviewer guidance

- Confirm `@patch` on the SUT is gone from each re-pointed test and the assertion is on a persisted artifact.
- Confirm siblings left untouched are genuinely already-observable (not skipped audits).

## Activity Log

- 2026-07-13T14:12:53Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:25:55Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Ready for review: re-pointed :211 source-as-text twin to observable status.events.jsonl assertion (no @patch on SUT); audited 3 siblings, all already observable-outcome, left unmodified.
- 2026-07-13T14:27:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=2975016 – Started review via action command
- 2026-07-13T14:37:18Z – user – shell_pid=2975016 – Review passed on merits: twin re-pointed to observable event, 3 siblings verified clean
