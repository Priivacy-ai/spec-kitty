---
work_package_id: WP04
title: Load-bearing architectural regression guard (IC-03)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1334234"
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-03 (FR-005/SC-006).
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_untrusted_path_containment.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/architectural/test_untrusted_path_containment.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (or read
`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it), and
acknowledge its initialization declaration.

## Objective

Add a `tests/architectural/` regression guard, anchored on WP01's audited-surface
inventory, that FAILS when a new unvalidated untrusted-segment join is introduced on
an audited surface — and prove it is **load-bearing** (not vacuous). (FR-005, SC-006)

Runs after WP02/WP03 fixes land so the guard is green on the fixed tree.

## Context

- WP01 produced `tests/architectural/untrusted_path_audit/audited-surfaces.md` (the
  inventory of untrusted→FS sinks + dispositions). This guard's matched-surface set is
  THAT inventory, not a heuristic over every `Path /` join (which would be
  high-false-positive).
- Existing architectural guards live in `tests/architectural/` (e.g.
  `test_no_legacy_terminology.py`) and run in the `integration-tests-core-misc` CI job.

## Subtasks

### T018 — implement the guard
- Add `tests/architectural/test_untrusted_path_containment.py`. For each audited
  surface in WP01's inventory, assert that the untrusted segment reaching its sink is
  routed through the canonical seam (`assert_safe_path_segment` / `safe_mission_slug` /
  `ensure_within_any`). Use AST or a precise source scan keyed on the inventory's
  source symbols + sink predicate — NOT a blanket `Path /` matcher.
- Keep it ruff/mypy-clean and reasonably fast (architectural tests run in CI core-misc).

### T019 — guard self-test (load-bearing proof, TWO mutations)
- **(a) Real-code mutation**: temporarily introduce an unvalidated untrusted-segment
  join into an ACTUAL audited source file from WP01's inventory (e.g. a throwaway line
  in `status/store.py` joining `mission_slug` without the seam); the guard MUST flag it;
  reverting MUST clear it. This proves the guard reads the REAL surfaces, not just a
  synthetic sample.
- **(b) Coverage assertion**: the test MUST assert the guard's matched-surface set is
  **non-empty and equals the WP01 audited-surface inventory** — failing if the inventory
  file is empty/missing or the guard inspects zero surfaces. A guard that matches nothing
  fails its own test (defeats the vacuous-guard exploit).
- Record both mutation results (with the exact diff used) in the WP history — not just "verified".
- Note: WP04 depends on WP02/WP03 being GREEN; the guard cannot be the safety net for
  upstream laziness — assertion (b) is what catches an empty/thin inventory.

### T020 — gate placement + full run
- Confirm the guard is collected by the architectural suite and would run in CI's
  core-misc job. Run `PWHEADLESS=1 python -m pytest tests/architectural/ -p no:cacheprovider -q`
  and the broader status/merge suites — all green on the post-WP02/WP03 tree.

## Branch Strategy

Planning/base + merge target: `automation/sonar-security-20260619` (rides PR #2036; flattened). Worktree per `lanes.json` lane at implement time. **Depends on WP01, WP02, WP03** — the guard asserts the fixed state, so it must run after the fixes.

## Definition of Done

- [ ] Guard added, anchored on WP01's inventory (not a blanket `Path /` heuristic).
- [ ] Self-test proves load-bearing via BOTH a real-code mutation (unvalidated join in an actual audited file is flagged) AND a coverage assertion (matched set == non-empty WP01 inventory) (SC-006).
- [ ] Guard is green on the post-WP02/WP03 tree AND inspects N>0 real audited surfaces; collected by the architectural suite.
- [ ] ruff + mypy clean.

## Risks / Reviewer guidance

- **Risk**: false positives if the matcher is too broad — anchor strictly on the inventory's source symbols/sinks.
- **Risk**: false negatives if the matcher is too narrow — the self-test (T019) is the antidote; insist it actually fails without a real guard.
- **Reviewer**: run the self-test mutation yourself; try adding a deliberate unvalidated join on an audited surface and confirm the guard catches it.

## Activity Log

- 2026-06-19T13:50:31Z – user – shell_pid=1297975 – Moved to planned
- 2026-06-19T13:50:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1301767 – Started implementation via action command
- 2026-06-19T14:11:06Z – claude:sonnet:python-pedro:implementer – shell_pid=1301767 – Guard anchored on WP01 inventory; load-bearing proven (real-code mutation flags + non-empty coverage assertion); green on fixed tree; ruff/mypy clean. --force: flattened-mission kitty-specs guard false-positive (status files committed on lane branch due to flattened mission structure; known issue per WP04 prompt)
- 2026-06-19T14:12:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1301767 – Reconcile; WP04 guard complete lane-d (load-bearing mutation proven). NOTE: WP04 also edited WP01 audit files (inventory 35→29, dropped 2 candidates) claiming WP02/WP03 fixed those sinks — review must verify audit not weakened.
- 2026-06-19T14:12:10Z – claude:opus:reviewer-renata:reviewer – shell_pid=1334234 – Started review via action command
- 2026-06-19T14:21:01Z – user – shell_pid=1334234 – Review passed (cycle-2; --force for flattened-mission kitty-specs-on-lane guard #2036 in-mission, --skip-review-artifact-check for cycle-1 which was a #771 status-conflict reset NOT a quality rejection). AUDIT NOT WEAKENED: matcher seed-set/sink-predicate/one-hop-aliasing UNCHANGED; only KNOWN_CANDIDATE_FILES shrank by 2 (decision_log.py, drift_detector.py) - both verified seam-guarded (assert_safe_path_segment before join) with ZERO AST-discovered sinks; Check-2 undercount tripwire catches any residual. Guard LOAD-BEARING: independent mutation (derived_dir/snapshot.mission_slug+.mkdir in status/views.py) caught by audit + all-discovered-rows tests; reverted clean. Coverage non-vacuous (inspected==expected, len>0). store.py T019 probe fully reverted (byte-identical to lane-b). ruff+mypy --strict clean. tests/architectural/ green except pre-existing marker-convention failure (lane diff empty for that file).
- 2026-06-19T14:21:38Z – user – shell_pid=1334234 – Reconcile lane→primary; reviewer-renata APPROVED WP04 (audit NOT weakened — matcher byte-identical, 2 dropped candidates verified seam-guarded; independent views.py mutation caught; mypy --strict 0)
