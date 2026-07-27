# Tasks: Loop-reliability + CI-red burndown remediation

**Mission**: loop-reliability-ci-red-burndown-01KXWWD6 · **Branch**: `fix/loop-reliability-ci-red-burndown`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Landmines**: [data-model.md](./data-model.md)

Six independent WPs (disjoint `owned_files`), two lanes. Land the ready product fixes (WP01/WP02) and burn
down the tracked CI reds (WP03-WP06). Every WP flips a pre-existing red-first repro red→green; resolve edit
sites by SYMBOL, not line number (LM-10); use `uv run --extra test pytest` (LM: lane-venv fallback #2803).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Rebase `0153934f9` onto main (3 clean + `tasks_move_task.py --3way`) | WP01 | [P] |
| T002 | Verify the consumer-repo repro still fires + the 2 red-first tests green | WP01 | |
| T003 | `_daemon_start_skip_reason` honors `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` | WP02 | [P] |
| T004 | Flip `test_daemon_sync_disable_env` green; confirm unset-env path unchanged | WP02 | |
| T005 | Append the `_isolate` sync-toggle fixture to existing `tests/sync/conftest.py` | WP03 | [P] |
| T006 | Red-first confirm the fixture greens `test_strict_json_stdout` on main (LM-7); serial `-n0` daemon suite (LM-8) | WP03 | |
| T007 | `isinstance` guard at `load_url_list_from_config` (schema-drift) + docstring | WP04 | [P] |
| T008 | Run the FULL `test_charter_epic_golden_path` + phase3/orchestrator to green (LM-9) | WP04 | |
| T009 | Seed `charter.yaml` in `test_bundle_contract._init_fixture` | WP05 | [P] |
| T010 | Skip-when-logged-out guard on `test_upgrade_updates_templates` | WP05 | |
| T011 | Clear `resolver.__warningregistry__` in `test_resolve_by_urn` | WP06 | [P] |
| T012 | Add `platform` to the mission-loader-coverage job `if:` in ci-quality.yml | WP06 | |

---

## WP01 — Land the consumer-repo pre-review-gate calm-degrade (#2534)
**Priority**: P1 · **Prompt**: [tasks/WP01-land-consumer-repo-gate-calm-degrade.md](./tasks/WP01-land-consumer-repo-gate-calm-degrade.md)
**Requirements**: FR-002; NFR-003; C-002, C-003 · **Tracker**: #2534
**Independent test**: the 2 red-first tests (`test_pre_review_gate_engine`/`_integration`) green; a consumer-repo
`move-task --to for_review` calm-degrades (no "gate authorities unavailable").
- [ ] T001 Rebase `0153934f9` (3 clean + `tasks_move_task.py --3way`; port-intent if it fights — LM-1, C-002) (WP01)
- [ ] T002 Verify the consumer-repo repro still fires on main; the 2 red-first tests green (WP01)

## WP02 — Sync daemon honors the disable env (#2573b)
**Priority**: P1 · **Prompt**: [tasks/WP02-daemon-honor-disable-env.md](./tasks/WP02-daemon-honor-disable-env.md)
**Requirements**: FR-003; NFR-003; C-003 · **Tracker**: #2573, #2555
**Independent test**: `test_daemon_sync_disable_env` green; unset-env path spawns as before.
- [ ] T003 `_daemon_start_skip_reason` returns a skip reason when `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` truthy (reuse `is_truthy`) (WP02)
- [ ] T004 Flip `test_daemon_sync_disable_env` green; confirm unset-env → `None` (behavior-preserving) (WP02)

## WP03 — Isolate the strict-JSON test from the leaked sync toggle (#2809)
**Priority**: P2 · **Prompt**: [tasks/WP03-isolate-strict-json-sync-toggle.md](./tasks/WP03-isolate-strict-json-sync-toggle.md)
**Requirements**: FR-001, FR-005; NFR-001 · **Tracker**: #2809, #2782
**Independent test**: `test_strict_json_stdout` green in CI regardless of leaked toggle; the serial `-n0` daemon
suite still passes.
- [ ] T005 APPEND the `_isolate_pre_review_gate_sync_toggles` autouse fixture to the EXISTING `tests/sync/conftest.py` (LM-8) (WP03)
- [ ] T006 Red-first confirm the fixture greens `test_strict_json_stdout` on current main (LM-7 — if #2782's connection-refused cause is live, escalate not blind-xfail); run daemon/orphan-sweep serial `-n0`; decide the `@regression` marker (WP03)

## WP04 — Fix the schema-drift crash in dry-run evidence (#2807, clears 3 reds)
**Priority**: P2 · **Prompt**: [tasks/WP04-evidence-schema-drift-guard.md](./tasks/WP04-evidence-schema-drift-guard.md)
**Requirements**: FR-004; NFR-001 · **Tracker**: #2807
**Independent test**: `test_phase3_dry_run_evidence_smoke`, the orchestrator dry-run test, AND the full
`test_charter_epic_golden_path` all green.
- [ ] T007 `if not isinstance(charter_cfg, dict): charter_cfg = {}` at `load_url_list_from_config` + fix stale docstring; do NOT re-wire url_list (LM-2, C-005) (WP04)
- [ ] T008 Run the FULL `test_charter_epic_golden_path` to green (dies at synthesize today — post-synthesize assertions unverified, LM-9) + phase3/orchestrator (WP04)

## WP05 — Charter CI-fixture hygiene (#2807)
**Priority**: P2 · **Prompt**: [tasks/WP05-charter-ci-fixture-hygiene.md](./tasks/WP05-charter-ci-fixture-hygiene.md)
**Requirements**: FR-004; NFR-001, NFR-002 · **Tracker**: #2807
**Independent test**: `test_bundle_contract` green; `test_upgrade_updates_templates` skips-when-logged-out (green in CI).
- [ ] T009 Seed + git-commit a minimal `charter.yaml` in `test_bundle_contract._init_fixture` (v2 manifest tracks both) (WP05)
- [ ] T010 Add skip-when-logged-out guard to `test_upgrade_updates_templates` (env-guard over blanket xfail, LM-6) (WP05)

## WP06 — CI flake + workflow filter-guard (#2812)
**Priority**: P2 · **Prompt**: [tasks/WP06-ci-flake-and-workflow-guard.md](./tasks/WP06-ci-flake-and-workflow-guard.md)
**Requirements**: FR-006; NFR-001, NFR-002 · **Tracker**: #2812
**Independent test**: `test_resolve_by_urn` stable across parallel runs; the loader-coverage job runs on a
`mission_loader/**`-only change.
- [ ] T011 Clear `resolver.__warningregistry__` inside the `catch_warnings` block in `test_resolve_by_urn` (WP06)
- [ ] T012 Add `|| needs.changes.outputs.platform == 'true'` to the mission-loader-coverage job `if:` (LM-5); confirm job self-sufficiency (WP06)

---

## Dependencies & Lanes
All six WPs are independent (disjoint owned_files, no ordering dep — verified by the post-plan squad). **WP02
does NOT depend on WP03** (LM-11 — the daemon repro sets its own env). Lane A (product): WP01, WP02. Lane B
(CI hygiene): WP03-WP06. `finalize-tasks` computes lanes (~2-6 lanes).

## Landmines (see data-model.md)
LM-1 #2534 rebase (3way/port-intent, don't re-derive) · LM-2 orchestrator guard only, no url_list re-wire ·
LM-7 #2809/#2782 red-first before assuming · LM-8 conftest exists (append) + serial `-n0` · LM-9 full e2e green ·
LM-10 resolve by symbol · LM-11 WP02⊥WP03.
