# Tasks: Upgrade No-Migrations Provisioning Fix + `upgrade()` Tidy-First

**Mission**: upgrade-no-migrations-provisioning-fix-01M20NK8 (#4032, epic #1931)
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)
**Planning base**: `issue-1931-ci-rework-test-remainders` | **Merge target**: `issue-1931-ci-rework-test-remainders`

Three sequential work packages. **Tidy-first**: WP01 (behavior-preserving decomposition) precedes WP02 (the functional fix), which precedes WP03 (test re-evaluation & consolidation). Tests are explicitly in scope (bug-fix mission; red-first required).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Map `upgrade()` internal blocks; identify extraction seams that do NOT split the `repair_preflight` `with` span | WP01 | |
| T002 | Extract cohesive sub-functions; keep preflight `with` span atomic + exit-code/`if not dry_run and success` guard intact | WP01 | |
| T003 | Remove `# noqa: C901`; each extracted function ≤15 complexity; ruff + mypy clean | WP01 | |
| T004 | Prove behavior-preserving: `test_no_stray_noqa_c901_marker` green + pre-existing passing upgrade tests green | WP01 | |
| T005 | RED-first: adopt a pre-existing failing test as witness; confirm exact `"requires an existing authority"` signal via config-absent path | WP02 | |
| T006 | Make `PreparedUpgradeRepairs.provisioning` Optional; null at assessment layer when authority absent; no create/parent-create effects when None | WP02 | |
| T007 | Emit non-error `deferred_provisioning` diagnostic; `complete` not poisoned; outcome not `failed`; human-mode `Note:` line | WP02 | |
| T008 | Reduce `_prepare_skill_provisioning` to pure integrity validator; keep a live negative test for the raise arm (non-vacuity) | WP02 | |
| T009 | Ensure finalizer performs NO create when descriptor None (C-001); new `tests/upgrade/test_upgrade_guard_absent.py` asserts skip + no-create + diagnostic | WP02 | |
| T010 | Create shared `tests/upgrade/_fixtures.py` (config-absent + real-init-ed builders) used by the guard-aligned test | WP02 | |
| T011 | Enumerate the frozen Group A nodeid list (every test failing with the guard signal) → SC-002 baseline, recorded here | WP03 | |
| T012 | KEEP config-absent fixtures in `test_upgrade_integration.py` + `test_upgrade_idempotency.py`; migrate them onto `_fixtures.py` | WP03 | [P] |
| T013 | Re-pin `test_upgrade_char_net.py` oracle to a real init-ed fixture (apply path); re-derive churn/warnings; green | WP03 | [P] |
| T014 | Redesign `test_failed_run_exit_code_equals_outcome_exit_code`: separate `errors` (forced activation) vs `deferred_provisioning` (guard) | WP03 | [P] |
| T015 | Record each test disposition (kept/redesigned/re-pinned-with-evidence/deleted) → #4032; whole `tests/upgrade/` + `tests/specify_cli/skills/` green | WP03 | |

## WP01 — Tidy-first: decompose `upgrade()` (behavior-preserving)

- **Goal**: Split the ~345-line `upgrade()` (`cli/commands/upgrade.py:1421`) into testable sub-functions and drop `# noqa: C901`, with zero behavior change.
- **Priority**: P1 (enabler — must precede WP02).
- **Independent test**: `test_no_stray_noqa_c901_marker` passes; `ruff check` shows no C901 suppression; all previously-passing upgrade behavior tests stay green.
- **Subtasks**: T001, T002, T003, T004
- **Dependencies**: none
- **Risks**: splitting the `repair_preflight` `with` span (ContextVars + RLock) silently breaks the paired-preflight recheck; exit-code matrix / dry-run guard must move intact.
- **Prompt**: [tasks/WP01-decompose-upgrade-entry.md](./tasks/WP01-decompose-upgrade-entry.md) (~220 lines)

## WP02 — Functional fix: Optional provisioning descriptor + non-error diagnostic

- **Goal**: Decide the absent-authority deferral once at the assessment/compiler layer (Optional descriptor nulled), emit a non-error `deferred_provisioning` diagnostic, reduce the installer guard to a pure integrity validator, and guarantee the finalizer does NOT create the authority (C-001).
- **Priority**: P1.
- **Independent test**: the adopted pre-existing witness flips RED→green; `test_upgrade_guard_absent.py` asserts skip + no-create + diagnostic; the guard still raises on a malformed descriptor.
- **Subtasks**: T005, T006, T007, T008, T009, T010
- **Dependencies**: WP01
- **Risks**: poisoning `complete` with an error-severity diagnostic (re-fails the outcome); letting the raw `prepared.provisioning.apply()` create the authority (re-opens #4047); a vacuous guard.
- **Prompt**: [tasks/WP02-optional-provisioning-nonfatal.md](./tasks/WP02-optional-provisioning-nonfatal.md) (~380 lines)

## WP03 — Test re-evaluation & consolidation

- **Goal**: Prove the fix with a frozen Group A baseline, KEEP legitimate config-absent witnesses, re-pin the oracle to the apply path, redesign the two-subsystem monkeypatch test, consolidate the triplicated fixture, and record every disposition.
- **Priority**: P2.
- **Independent test**: every frozen Group A nodeid green; oracle green and still exercising the apply path; whole `tests/upgrade/` + `tests/specify_cli/skills/` green; dispositions recorded.
- **Subtasks**: T011, T012, T013, T014, T015
- **Dependencies**: WP02
- **Risks**: green-by-avoidance (re-pinning away the config-absent path); oracle silently becoming a skip-path test; a re-pin weakening assertion strength.
- **Prompt**: [tasks/WP03-test-reevaluation-consolidation.md](./tasks/WP03-test-reevaluation-consolidation.md) (~320 lines)

## MVP / sequencing

WP01 → WP02 → WP03 (sequential). WP02 is the user-facing fix; WP01 is its prerequisite; WP03 is the quality gate. Within WP03, T012–T014 are parallel-safe (different files).
