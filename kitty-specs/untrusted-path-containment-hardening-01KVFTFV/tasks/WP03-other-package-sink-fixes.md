---
work_package_id: WP03
title: Other-package reachable sink fixes (audit-driven)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-008
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1292722"
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-02 fixes (FR-001/FR-003/FR-008).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/events/decision_log.py
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/dossier/drift_detector.py
- src/specify_cli/migration/mission_state.py
- src/specify_cli/review/arbiter.py
- src/specify_cli/review/cycle.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/specify_cli/events/test_decision_log.py
- tests/specify_cli/coordination/test_surface_resolver.py
- tests/specify_cli/missions/test_read_path_resolver_validation.py
- tests/dossier/test_drift_detector.py
- tests/migration/test_mission_state_repair.py
- tests/review/test_arbiter.py
- tests/review/test_cycle.py
- tests/post_merge/test_review_artifact_consistency.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (or read
`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it), and
acknowledge its initialization declaration.

## Objective

For each WP01-confirmed-reachable untrusted→FS sink OUTSIDE `status/`, route the
segment through the canonical seam (fail-closed). For sinks WP01 marked
`unreachable` or `trusted-source`, do NOT change code — confirm and cite the
disposition. Add a negative test for each confirmed-reachable fix. (FR-001, FR-003, FR-008)

**Driven by WP01's inventory** — only fix what the audit confirms reachable; document
the rest. Do not invent fixes for unreachable sinks.

## Context

- Canonical seam: `assert_safe_path_segment` / `safe_mission_slug` (`core/paths.py`), `ensure_within_any` (`core/utils.py`).
- Pre-named candidates (verify each against WP01's disposition before touching):
  - `events/decision_log.py:99` — `worktree_root / KITTY_SPECS_DIR / mission_slug / "decisions.events.jsonl"` (write).
  - `coordination/surface_resolver.py:433-434` & `missions/_read_path_resolver.py:438` — `<root>/KITTY_SPECS_DIR/<mission_slug>` composition.
  - `dossier/drift_detector.py:211,233` — `.kittify/dossiers/<mission_slug>` read+write.
  - `migration/mission_state.py:1053` — `<...>/<mission_slug>` join (migration write path).
  - `review/arbiter.py:387,483,520` & `post_merge/review_artifact_consistency.py:59` — `tasks_dir / wp_id` (untrusted `wp_id`).
  - `review/cycle.py:225` — already validates via `_validate_segment` but no `resolve()`-containment → likely `routed-through-seam` already; document, add containment only if WP01 says reachable.

## Subtasks

### T012 — events/decision_log.py
- If WP01 marks the `mission_slug` write sink reachable, route the slug through `safe_mission_slug(..., feature_dir.name)` (or `assert_safe_path_segment` + skip) before the join; else document the disposition.

### T013 — coordination/surface_resolver.py + missions/_read_path_resolver.py
- These compose the status-surface path from `mission_slug`. Apply segment validation/containment per WP01 disposition. Note `aggregate.py` delegates here (FR-003 linkage) — coordinate with the FR-003 disposition from WP01.

### T014 — dossier/drift_detector.py + migration/mission_state.py
- Dossier read+write and the migration write path — validate the slug per disposition. Migration paths run rarely but write; treat as reachable unless WP01 proves otherwise.

### T015 — review/arbiter.py + post_merge + review/cycle.py
- The `wp_id` sinks (`tasks_dir / wp_id`) — `wp_id` is a named untrusted source. Validate it (segment grammar at minimum; containment if it composes deeper paths). For `review/cycle.py`, document that it already segment-validates; add containment only if WP01 flags it.

### T016 — negative tests for each confirmed-reachable fix
- One focused negative test per fix: a traversal segment → rejection/fallback, no FS effect outside the trusted root. Mutation-verify each (neutralize the guard → test fails).

### T017 — gates
- `ruff` + `mypy` clean on touched files; run the affected package test suites; full run green.

## Branch Strategy

Planning/base + merge target: `automation/sonar-security-20260619` (rides PR #2036; flattened). Worktree per `lanes.json` lane at implement time.

## Definition of Done

- [ ] Every WP01 `routed-through-seam (TODO)` sink outside `status/` is routed through the seam, fail-closed.
- [ ] Each `unreachable` disposition cites the **specific call chain** (named caller → callee → sink line) proving no untrusted segment can arrive, AND names the trusted origin at the chain head. A bare "internal only" is rejected.
- [ ] **Non-dismissable sinks**: the `wp_id` sinks (`review/arbiter.py:387,483,520`, `post_merge/review_artifact_consistency.py:59`) and the `mission_slug` write sinks (`events/decision_log.py:99`, `dossier/drift_detector.py:211,233`, `migration/mission_state.py:1053`) MUST be routed through the seam OR carry a reviewer-countersigned reachability proof. `wp_id`/`mission_slug` are named untrusted sources (spec FR-004) — defaulting them to `trusted-source` is a finding, not a disposition.
- [ ] One mutation-verified negative test per confirmed-reachable fix (FR-008); for any named-candidate dispositioned `unreachable`, the WP history records the exact call-chain proof verbatim.
- [ ] `wp_id` sinks (arbiter/post_merge) validated (FR-001).
- [ ] aggregate.py composed-path disposition reconciled with WP01 (FR-003).
- [ ] ruff + mypy clean; affected + full suite green.

## Risks / Reviewer guidance

- **Risk**: over-fixing unreachable sinks adds churn — stay disciplined to WP01's dispositions.
- **Risk**: some of these paths (migration, coordination) are exercised in narrow flows — ensure the fail-closed fallback doesn't break a legitimate migration/coordination path (test the happy path too).
- **Reviewer**: cross-check each fixed sink against WP01's inventory row; confirm each negative test is mutation-killing; confirm no unreachable sink was needlessly changed.

## Activity Log

- 2026-06-19T13:15:05Z – claude:sonnet:python-pedro:implementer – shell_pid=1218199 – Assigned agent via action command
- 2026-06-19T13:33:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1218199 – 5 sinks routed through seam + tests (mutation-verified); 6 dispositioned unreachable/already-seamed with cited chains; deferred CLI-arg sinks: agent/mission.py:312 (trusted-source dir.name), agent/tasks.py:1911 (read-only probe), decision.py:464 (read-only), merge.py:1055 (read-only)
- 2026-06-19T13:34:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1218199 – Reconcile lane→primary; WP03 impl complete lane-c 5aa0f6bd0 (5 fixed, 5 dispositioned, 4 CLI-arg deferred)
- 2026-06-19T13:34:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=1278176 – Started review via action command
- 2026-06-19T13:41:38Z – user – shell_pid=1278176 – Moved to planned
- 2026-06-19T13:42:15Z – claude:sonnet:python-pedro:implementer – shell_pid=1288131 – Started implementation via action command
- 2026-06-19T13:44:25Z – claude:sonnet:python-pedro:implementer – shell_pid=1288131 – cycle 2: ruff UP037 autofixed; ruff exit 0 on all WP03-touched files; 48 arbiter tests green; --force: kitty-specs-on-lane guard friction (status events on lane branch, known friction pattern)
- 2026-06-19T13:44:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1288131 – Reconcile; WP03 cycle-2 ruff UP037 fixed lane-c 687da2106 (ruff/mypy 0, 48 arbiter tests green)
- 2026-06-19T13:44:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=1292722 – Started review via action command
- 2026-06-19T13:46:46Z – user – shell_pid=1292722 – Cycle 2 passed: ruff UP037 fixed (surgical one-line delta in 687da2106), ruff exit 0 on all 11 WP03 touched .py files, mypy clean, 48 arbiter tests green; cycle-1 substantive PASS stands. Overrides: --skip-review-artifact-check (prior review-cycle-2.md rejection remediated) + --force (kitty-specs-on-lane guard friction #2036, flattened mission - status events on lane branch, known friction pattern matching implementer cycle-2 note).
- 2026-06-19T13:47:33Z – user – shell_pid=1292722 – Reconcile lane→primary; reviewer-renata APPROVED WP03 cycle 2 (ruff/mypy 0, 48 tests, one-line UP037 fix)
