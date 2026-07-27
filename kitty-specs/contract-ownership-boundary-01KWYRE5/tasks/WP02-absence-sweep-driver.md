---
work_package_id: WP02
title: Static-arm absence-sweep driver (advisory) + anti-vacuity control
dependencies:
- WP01
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/contract-ownership-boundary
merge_target_branch: feat/contract-ownership-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/contract-ownership-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/contract-ownership-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T004
agent: "reviewer-renata"
shell_pid: "3996321"
history:
- Created for mission contract-ownership-boundary-01KWYRE5
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_retired_contracts_absent.py
execution_mode: code_change
owned_files:
- tests/architectural/test_retired_contracts_absent.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
The static-arm retirement-verification driver — a content-anchored absence sweep over `status=retired` contract records, **advisory/report-only**, that proves a retired anchor appears in zero live consumers. **FR-005, NFR-002.** Depends on WP01 (the registry loader + seeded records).

## Guidance (T004)
`tests/architectural/test_retired_contracts_absent.py`:
- Load the registry (WP01's `src/specify_cli/contracts/registry.py`). For each `status=retired` record, sweep its `anchor` across `consumers.scan_roots` minus `consumers.exemptions`, using `composite_key`/literal anchoring (via the promoted anchoring lib). Report any live occurrence.
- **Advisory/report-only**: the test must NEVER fail CI on a found occurrence — emit a warning/report (e.g. `warnings.warn` or a report artifact), not `pytest.fail`/`assert`. (This is v1; enforcement is a deferred follow-up.)
- **Mandatory anti-vacuity negative control**: a sub-test that plants a reappearance of a retired anchor (in a fixture/temp tree) and asserts the sweep **flags it** — so the sweep can't be vacuously green. This sub-test DOES assert (it guards the driver's own correctness, not a live-tree retirement).

## Definition of Done
- The sweep runs over the seeded `status=retired` records; the anti-vacuity control proves it bites; it never blocks CI on a live-tree find (advisory).
- `ruff`+`mypy --strict` clean; no suppression.

## Reviewer guidance
Confirm the sweep is genuinely advisory (grep for `pytest.fail`/blocking `assert` on live-tree finds → must be none), the anti-vacuity control actually plants + detects a reappearance, and it uses the content-anchoring lib (no `file:line`).

## Activity Log

- 2026-07-07T19:32:39Z – python-pedro – shell_pid=3924295 – Assigned agent via action command
- 2026-07-07T19:54:56Z – python-pedro – shell_pid=3924295 – Two edits outside enumerated owned_files, both minimal + mandated: (1) src/specify_cli/contracts/registry.py — the fragment-join file:line rejection the WP prompt explicitly authorizes (WP01-owned; +15/-1; benign joins still pass, positive control green); (2) tests/_arch_shard_map.py — registered the new arch test into arch_shard_3 so it passes the marker-convention + orphan/shard-completeness gates the WP requires. Driver is advisory/report-only (proven green under -W error); anti-vacuity control bites on real seeded anchors in tmp_path; fragment-join hardening red-first. ruff+mypy --strict clean. Lane commit 3f977c242.
- 2026-07-07T19:55:08Z – python-pedro – shell_pid=3924295 – Ready for review: static-arm absence-sweep driver (advisory, proven non-blocking under -W error); mandatory anti-vacuity control bites on real seeded anchors; WP01 fragment-join file:line hardening red-first; routed to arch_shard_3; ruff+mypy --strict clean. Lane commit 3f977c242.
- 2026-07-07T19:56:16Z – reviewer-renata – shell_pid=3996321 – Started review via action command
- 2026-07-07T20:04:46Z – user – shell_pid=3996321 – Review passed: advisory proven structural (-W error green), fragment-join red-first, anti-vacuity+exemption bite, orphan gate pre-empted
