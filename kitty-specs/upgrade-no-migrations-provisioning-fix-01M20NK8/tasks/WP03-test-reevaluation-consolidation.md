---
work_package_id: WP03
title: Test re-evaluation & consolidation (frozen Group A, oracle re-pin, monkeypatch redesign)
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-008
- FR-009
- FR-010
- FR-012
- NFR-001
- NFR-003
planning_base_branch: issue-1931-ci-rework-test-remainders
merge_target_branch: issue-1931-ci-rework-test-remainders
branch_strategy: Planning artifacts for this mission were generated on issue-1931-ci-rework-test-remainders. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-1931-ci-rework-test-remainders unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-upgrade-no-migrations-provisioning-fix-01M20NK8
base_commit: 804a6d7eceb5f4c35a476cfb751b69f5914af30f
created_at: '2026-09-08T17:36:08.779242+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - Test re-evaluation
history:
- at: '2026-09-08T14:42:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/upgrade/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/upgrade/test_upgrade_char_net.py
- tests/upgrade/test_upgrade_integration.py
- tests/upgrade/test_upgrade_idempotency.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objective

Prove WP02's fix with a frozen Group A baseline, KEEP the legitimate config-absent witnesses (green-by-avoidance is forbidden), re-pin the behavior oracle to the APPLY path, redesign the two-subsystem monkeypatch test, consolidate the triplicated fixture onto WP02's `_fixtures.py`, and record every disposition. (FR-006, FR-008, FR-009, FR-010, FR-012, NFR-001, NFR-003.)

## Context

- Depends on WP02 (the fix + `tests/upgrade/_fixtures.py` builders + the `deferred_provisioning` channel shape). Do not start assertions against the diagnostic until WP02 publishes its final shape.
- `_init_project` in the failing tests does NOT run real `init` — the `metadata.yaml`-only shape IS the config-absent legacy shape. KEEP it; do not re-pin it to an init-ed project (that would stop exercising `before_bytes is None` = green-by-avoidance).

## Subtasks & Guidance

### T011 — Enumerate the frozen Group A list (SC-002 baseline, reviewer-rerunnable)
Group A is the **verbatim captured output of a stated command**, not a curated subset. Run, on the merge base, an exact recorded command (e.g. `PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/ -q 2>&1 | grep "requires an existing authority"` plus the failing-nodeid collection) and paste both the command and its raw nodeid output into the Activity Log and tasks.md. SC-002 = "every nodeid in this captured set is green after the fix" — and a **reviewer re-runs the same command on the merge base and the frozen list MUST equal its output** (under-enumeration is a rejection).

### T012 — KEEP config-absent fixtures; migrate onto the shared builder [P]
In `test_upgrade_integration.py` and `test_upgrade_idempotency.py`, confirm the config-absent tests now pass via WP02, then migrate their local `_init_project`/`_METADATA_YAML` scaffolds to import the **config-absent builder** from `tests/upgrade/_fixtures.py` (FR-010 de-duplication). Do NOT change what they exercise (still the `before_bytes is None` path). (FR-008.)

### T013 — Re-pin the oracle to the APPLY path [P]
`test_upgrade_char_net.py` currently uses a config-absent fixture → after WP02 it would pin the SKIP path. Re-pin its fixture to a **real init-ed** project (via the `_fixtures.py` init-ed builder) so it keeps exercising the provisioning **apply** path (NFR-003 behavior preservation). Re-derive `EXPECTED_CHURN_PATHS` and the `warnings` expectation for the init-ed project; confirm green. (FR-006.) **Affirmative apply-path witness (not green-by-accident):** the oracle MUST positively assert a provisioning **apply/write effect fired** (the expected in-place `apply` effect / non-empty write to the authority) — green + init-ed fixture alone is insufficient, because a skip-path run could also be green with different churn. Record the judgment: the oracle tests the apply path, not the skip path.

### T014 — Redesign the two-subsystem monkeypatch test [P]
`test_failed_run_exit_code_equals_outcome_exit_code` (`test_upgrade_integration.py`) straddles two subsystems: the managed-skill guard (`installer.py:427`) and the mission-type-activation backfill (`upgrade.py:517`, the monkeypatched `_provision_missing_mission_type_activations`). Redesign its assertions to separately assert (a) the forced activation error in `errors` and (b) the guard/skip signal in `deferred_provisioning` — a contract redesign, explicitly NOT a fixture swap. (FR-009.)

### T015 — Record dispositions; full green
For every addressed failing test record a disposition — `kept` / `redesigned` / `re-pinned-with-evidence` / `deleted` (a re-pin must cite the code proving the old fixture unreachable and preserve assertion strength; else delete). Traceable to #4032. Then confirm the whole `tests/upgrade/` suite and the `tests/specify_cli/skills/` blast-radius directory are green. (FR-012, NFR-001.)

## Branch Strategy
- **Planning base**: `issue-1931-ci-rework-test-remainders` · **Merge target**: `issue-1931-ci-rework-test-remainders` · lane per `lanes.json`.

## Definition of Done
- Frozen Group A list enumerated and every nodeid green.
- Config-absent witnesses KEPT (still drive `before_bytes is None`) and migrated onto the shared builder.
- Oracle re-pinned to the apply path and green; churn/warnings re-derived.
- Monkeypatch test redesigned (two-channel assertions).
- Every disposition recorded; `tests/upgrade/` + `tests/specify_cli/skills/` green.

## Reviewer guidance
- **No reachable config-absent test may be re-pinned.** Re-run the T011 command on the merge base and confirm the frozen list equals its output (no under-enumeration). For every Group A nodeid, confirm it is either KEPT driving `before_bytes is None`, or its re-pin/delete cites code-level proof the config-absent shape is unreachable. A re-pin of a still-reachable config-absent test is a **rejection** (green-by-avoidance).
- Verify SC-003: at least one KEPT test drives the config-absent path — and, per the above, that keeping is the rule not the exception.
- Verify the oracle positively witnesses the **apply** effect (not just green on an init-ed fixture).
- Verify each re-pin cites unreachability evidence and preserves assertion strength (else deleted, not re-pinned).
