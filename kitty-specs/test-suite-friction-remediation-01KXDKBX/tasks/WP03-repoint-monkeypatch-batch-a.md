---
work_package_id: WP03
title: Repoint runtime_bridge monkeypatch sites — batch A (tests/next)
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-016
- NFR-003
tracker_refs:
- '2561'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/next/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/next/**
role: implementer
tags: []
shell_pid: "3544050"
shell_pid_created_at: "1783965044.28"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-003 + Scenario 2,
[plan.md](../plan.md) §IC-02, and WP02's classification note (which `<name>`s were deleted as forwarding
delegates). This WP repoints the **batch A** monkeypatch sites; WP04 owns batch B. The two batches are
file-disjoint.

## Objective

Repoint the forwarding `monkeypatch.setattr(runtime_bridge, <name>, …)` /
`monkeypatch.setattr("runtime.next.runtime_bridge.<name>", …)` sites in **`tests/next/**`** at their
**owning seam module** (`runtime_bridge_{cores,io,identity,engine,composition,retrospective}`), so the
re-export delegates become deletable by **WP18** (the re-sequenced deletion pole, post-WP04). Repoint-only:
do NOT delete any src delegate here. This is the heaviest batch — it contains the two densest files.

## Context — batch A file map (owned: `tests/next/**`)

`grep -cE 'setattr\([^,]*runtime_bridge|runtime\.next\.runtime_bridge'` counts (forwarding subset only —
real-seam patches stay):

| occ | file |
|-----|------|
| 73 | `tests/next/test_query_mode_unit.py` |
| 67 | `tests/next/test_runtime_bridge_unit.py` |
| 20 | `tests/next/test_prompt_file_invariant.py` |
| 17 | `tests/next/test_runtime_bridge_blocked_paths.py` |
| 17 | `tests/next/test_retrospective_terminus_wiring.py` |
| 15 | `tests/next/test_occurrence_gate_next_loop.py` |
| 12 | `tests/next/test_finalized_task_routing.py` |
| 7 | `tests/next/test_next_command_integration.py` |
| 6 | `tests/next/test_mission_run_back_reference.py` |
| 3 | `tests/next/test_next_claimable_payload.py` |
| 2 | `tests/next/test_decision_unit.py` |
| 2 | `tests/next/test_composition_gate_widening.py` |

~241 occurrences across 12 files. Only the **forwarding** subset (per WP02's classification) repoints;
sites that already patch a real seam are left as-is.

## Subtask guidance

- **T011 — repoint the batch.** For each forwarding `<name>`, change the patch target from
  `runtime_bridge`/`"runtime.next.runtime_bridge.<name>"` to the seam module that now owns `<name>` (from
  WP02's classification). Prefer patching the seam module object the SUT actually resolves; do not
  re-introduce a compat forwarder.
- **T012 — the two heavy files.** `test_query_mode_unit.py` (73) and `test_runtime_bridge_unit.py` (67) are
  the density hot-spots — work them methodically; group patches by target seam module to keep the diff
  reviewable.
- **T013 — suite green.** `.venv/bin/python -m pytest tests/next -q` green. Verify no forwarded patch
  remains: `grep -rnE 'setattr\([^,]*runtime_bridge\b|"runtime\.next\.runtime_bridge\.' tests/next/` returns
  only genuine real-seam sites (documented) — zero forwarding survivors.
- **T014 — gates + tracer.** `ruff`/`mypy` clean on the diff; tracer rows.

## Branch Strategy

Branches from WP02's tip in the Lane-0 serial chain; merges into `feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every forwarding patch site in `tests/next/**` repointed at its owning seam module.
- [ ] `pytest tests/next` green with every site repointed at its owning seam (delegates still present —
      deletion is WP18); the repoint must patch the seam the SUT actually resolves, not the façade.
- [ ] Zero forwarding-delegate patch survivors in `tests/next/**` (grep evidence in review).
- [ ] `ruff` + `mypy` clean on the diff; no production edits (test-only WP).
- [ ] **Tracer (FR-016):** append a row noting the next-loop pinning suites repointed off the retired
      delegate + log any repoint friction to `../tracer-tooling-friction.md`.

## Risks

- **Wrong seam target** — patching the wrong module leaves the SUT reading the real attribute, silently
  passing a stale test. Cross-check each `<name>` against WP02's classification.
- **A real-seam patch mistaken for forwarding** — only repoint the forwarding subset; leave genuine seam
  patches untouched.

## Reviewer guidance

- Confirm the grep for forwarding survivors is 0 and the suite is green.
- Confirm no compat forwarder was re-introduced to make a test pass.

## Activity Log

- 2026-07-13T18:29:30Z – claude – shell_pid=3544050 – 23 forwarding sites repointed across 5 tests/next files; tests/next 516 passed (baseline parity); ruff clean; commit e9ea977d9. Force: lane 120 commits behind on planning/status ONLY — verified zero feat/ code changes to tests/next or runtime_bridge since lane base; merge reconciles.
- 2026-07-13T18:30:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=3544050 – Review claim
- 2026-07-13T18:36:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=3544050 – APPROVE (reviewer-renata/opus): all 9 repointed names resolve to defining seam (no false-greens); stub-widening genuine positional-convention; _check_cli_guards correctly left composite/façade; canonical __all__ untouched; tests/next 516 passed; scope tests/next+tracer only. Commit e9ea977d9.
