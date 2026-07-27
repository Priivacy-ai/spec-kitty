---
work_package_id: WP05
title: loopback_http.py rationale + Sonar hotspot record (IC-04)
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1212239"
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-04 (FR-006/C-001).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/core/loopback_http.py
- tests/core/test_loopback_http.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (or read
`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it), and
acknowledge its initialization declaration.

## Objective

Document the loopback-only (127.0.0.1) rationale for `core/loopback_http.py` in-code,
retain/strengthen its binding regression tests, and record the two open Sonar hotspots
for UI review. **No behavioural change. Do NOT force HTTPS** on loopback control-plane
URLs (C-001 — repo policy). Independent of all other WPs (parallel). (FR-006)

## Context

- `core/loopback_http.py` provides loopback-only HTTP helpers bound strictly to
  `127.0.0.1`. Sonar raises 2 hotspots flagging plain HTTP; per repo policy
  (charter "Loopback/local-only HTTP special case") these are intentional and must
  NOT be "fixed" by forcing HTTPS.
- Hotspot review is a Sonar-UI action separate from code; this WP records the
  rationale so a future agent does not waste time "fixing" it.

## Subtasks

### T021 — loopback rationale in-code
- Add a concise module/function docstring (and an inline comment at each
  127.0.0.1-binding site) stating: transport is loopback-only by design; binding is
  strictly `127.0.0.1`; HTTPS is intentionally NOT used for this local control-plane
  transport; cite the policy. Keep it factual and short.

### T022 — retain/strengthen binding regression tests
- In `tests/core/test_loopback_http.py`, assert BOTH: (a) the helper binds `127.0.0.1`,
  AND (b) a non-loopback host (e.g. `0.0.0.0` or an external IP) is rejected/not bound.
  **Mutation-verify**: widen the bind to `0.0.0.0` in the source → the test MUST fail
  (record the result). A one-sided "binds 127.0.0.1" assertion is insufficient — it
  wouldn't catch a host-widening regression.

### T023 — record the Sonar hotspots
- Record the 2 hotspots by **Sonar rule key + location + PR #2036** (per C-005, cite
  by id not fragile description) with the loopback-only rationale and the explicit
  "review-as-safe, do not force HTTPS" recommendation. Put this record in the PR #2036
  description (a "Sonar hotspot review" section) and mirror a one-paragraph summary in
  the `loopback_http.py` module docstring (T021), so it is tracked in-code without a
  kitty-specs file. (Do not create a mission-dir record file — `owned_files` cannot
  include `kitty-specs/` paths.)

### T024 — gates
- `ruff` + `mypy` clean; `PWHEADLESS=1 python -m pytest tests/core/test_loopback_http.py -p no:cacheprovider -q` green. Confirm NO behavioural change (helpers still bind 127.0.0.1, still plain HTTP).

## Branch Strategy

Planning/base + merge target: `automation/sonar-security-20260619` (rides PR #2036; flattened). Independent WP — no dependencies; can run in parallel with WP01–WP04. Worktree per `lanes.json` lane at implement time.

## Definition of Done

- [ ] Loopback-only rationale documented in `core/loopback_http.py`; **no behavioural change verified by diff-shape**: the `git diff` to `loopback_http.py` contains only comment/docstring additions (no executable line changed) — reviewer confirms.
- [ ] Binding regression test asserts BOTH 127.0.0.1-binds AND non-loopback-rejected; mutation-verified (widen to 0.0.0.0 → test fails).
- [ ] Both hotspots recorded by rule key + PR #2036 (in the PR body + module docstring) with the do-not-force-HTTPS rationale (C-001, C-005).
- [ ] ruff + mypy clean; loopback tests green.

## Risks / Reviewer guidance

- **Risk**: a well-meaning edit forces HTTPS — explicitly prohibited (C-001). The
  regression test + rationale exist to prevent exactly that.
- **Reviewer**: confirm zero behavioural change (diff is comments/docstring + test +
  a record file); confirm the hotspot record cites rule keys, not prose descriptions.

## Activity Log

- 2026-06-19T12:54:29Z – claude:sonnet:python-pedro:implementer – shell_pid=1162679 – Assigned agent via action command
- 2026-06-19T13:01:49Z – claude:sonnet:python-pedro:implementer – shell_pid=1162679 – loopback rationale + hotspot record in docstring; two-sided binding test mutation-verified
- 2026-06-19T13:02:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=1183766 – Started review via action command
- 2026-06-19T13:06:29Z – user – shell_pid=1183766 – Moved to planned
- 2026-06-19T13:07:06Z – claude:sonnet:python-pedro:implementer – shell_pid=1199416 – Started implementation via action command
- 2026-06-19T13:10:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1199416 – cycle 2: added isinstance narrowing; mypy --strict clean; mutation still bites; 7 tests green
- 2026-06-19T13:12:09Z – claude:sonnet:python-pedro:implementer – shell_pid=1199416 – Reconcile lane→primary desync; WP05 cycle-2 fix complete on lane-e af737225c (mypy --strict clean)
- 2026-06-19T13:12:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1212239 – Started review via action command
- 2026-06-19T13:16:46Z – user – shell_pid=1212239 – reviewer-renata APPROVED (cycle 2): mypy --strict exit 0, two-sided binding test mutation-reconfirmed (4 fail under 0.0.0.0 mutation, revert→7 green), diff-shape comments-only, hotspot record present. Recorded by orchestrator on reviewer's behalf; --force/--skip past flattened-mission lane-status + stale-rejected-artifact guards (#1716).
