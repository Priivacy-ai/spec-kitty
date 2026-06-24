# Tasks — Decompose `doctor.py` God-Module (Residual)

**Mission**: `decompose-doctor-god-module-01KVXHFB` · **Branch**: `prog/2059-doctor` → PR to `main`
**Source**: [plan.md](./plan.md) (IC-00..IC-10) · [spec.md](./spec.md) · [contracts/cli-surface-contract.md](./contracts/cli-surface-contract.md)

**11 work packages, STRICTLY LINEAR.** WP01 (golden harness) first, no deps. WP02 (`_doctor_shared`) deps WP01. Every subsequent WP deps the one before it (WP03→WP02, …, WP11→WP10). Linearization is forced by two facts: every extraction edits the single shared owner `doctor.py` (in-place delegation + re-export touch), and every sibling imports the `_doctor_shared` surface WP02 stabilizes. Behavior-preserving / golden-test-first per the spec.

**Zero `owned_files` overlap.** Each extraction WP owns ONLY its new sibling module + its new test file. `src/specify_cli/cli/commands/doctor.py` is owned **solely by the final WP11** (the re-export sweep). The in-place delegation edit each extraction WP must make to `doctor.py` is an out-of-map import/delegation edit documented in that WP's "Out-of-map edits" note (the sequential chain guarantees no concurrent `doctor.py` writer).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Enumerate `app.registered_commands`: assert the 16 frozen names + per-cmd param specs | WP01 | |
| T002 | Snapshot each subcommand's `--help` (byte-pinned) | WP01 | |
| T003 | Pin exit-code contracts incl. `ops --threshold`→BadParameter, `skills` 0/1/2, `restart-daemon` 0/1/2/3; cover `doctor skills`/`restart-daemon`/`sparse-checkout --fix` names | WP01 | |
| T004 | Create `_doctor_shared.py`: move `console`/guards/`_is_interactive_environment`/constants to single home | WP02 | |
| T005 | Point `doctor.py` + `_profile_health_render` console to the single `_doctor_shared` home (no new `Console()`) | WP02 | |
| T006 | Focused tests for `_doctor_shared` (guards/constants/interactive); golden green | WP02 | |
| T007 | Create `_doctrine_collect.py`: move Cluster J collectors; import shared infra | WP03 | |
| T008 | Delegate doctrine collectors in `doctor.py` to the sibling; re-export the test-facing collector symbols | WP03 | |
| T009 | Focused collector tests ≥90%; doctrine snapshot + golden green | WP03 | |
| T010 | Create `_identity_audit.py`: move identity+topology helpers; decompose `identity` CC19 → ≤15 helpers | WP04 | |
| T011 | Delegate `identity`/`topology` bodies in `doctor.py`; re-export touched symbols | WP04 | |
| T012 | Focused tests for identity/topology helpers ≥90%; golden green | WP04 | |
| T013 | Create `_command_surface_doctor.py`: move tool-surface+command-skill+slash; decompose `skills` CC20 + `_repair_command_skill_state` CC16 | WP05 | |
| T014 | Delegate `command-files`/`skills`/`tool-surfaces` bodies; re-export `SlashCommandGap`,`_load_slash_command_state`,`_repair_slash_command_state` | WP05 | |
| T015 | Focused tests for the surface helpers ≥90%; golden + safety-mode tests green | WP05 | |
| T016 | Create `_mission_state_doctor.py`: move Cluster H; keep `mission_state` dispatch-thin, drop its `# noqa: C901` if helpers move | WP06 | |
| T017 | Delegate `mission-state` body to sibling helpers | WP06 | |
| T018 | Focused mission-state tests ≥90%; golden green | WP06 | |
| T019 | Create `_coordination_doctor.py`: move Cluster K; decompose `_check_lane_sparse_checkout_drift` CC19; KEEP `merge.path_is_under_worktrees` FUNCTION-LOCAL (H2) | WP07 | |
| T020 | Delegate `coordination` body to sibling | WP07 | |
| T021 | Focused coordination tests ≥90%; import-graph no `doctor↔merge` cycle; golden green | WP07 | |
| T022 | Create `_sparse_checkout_doctor.py`: move Cluster E render/flow; decompose `sparse_checkout` cmd CC19 | WP08 | |
| T023 | Delegate `sparse-checkout` body to sibling | WP08 | |
| T024 | Focused sparse-checkout tests ≥90%; golden green | WP08 | |
| T025 | Create `_workspace_husk_doctor.py`: move Cluster C | WP09 | |
| T026 | Delegate `workspaces` body to sibling | WP09 | |
| T027 | Focused workspace-husk tests ≥90%; golden green | WP09 | |
| T028 | Create `_daemon_doctor.py`: move `orphan-daemons` + `restart-daemon` bodies | WP10 | |
| T029 | Delegate the two daemon bodies; preserve `restart-daemon` 0/1/2/3 contract | WP10 | |
| T030 | Focused daemon tests ≥90%; golden + argv-fast-path (`restart-daemon`) green | WP10 | |
| T031 | Re-export sweep: verify all 11 private symbols + `app`/`SlashCommandGap` resolve from `doctor`; decompose `state_roots` cmd CC17 | WP11 | |
| T032 | Verify pointer comment still references #2059; confirm `doctor.py` ≤ ~400 LOC, no new responsibilities | WP11 | |
| T033 | Full gate sweep: golden + 58 doctor tests + cli_gate; `ruff`+`ruff --select C901`+`mypy --strict` clean, zero new suppressions | WP11 | |

---

## WP01 — Golden CLI characterization harness (IC-00)

- **Goal**: Capture a byte-identical proof of the `spec-kitty doctor` CLI surface BEFORE any extraction.
- **Priority**: P1 (gate). **Dependencies**: none. **Independent test**: the new golden test passes at HEAD against the un-refactored `doctor.py`.
- **Requirement refs**: FR-001, FR-002.
- [x] T001 Enumerate `app.registered_commands`: 16 frozen names + per-cmd param specs (WP01)
- [x] T002 Snapshot each subcommand `--help` (byte-pinned) (WP01)
- [x] T003 Pin exit-code contracts; cover `skills`/`restart-daemon`/`sparse-checkout --fix` names (WP01)
- **Risks**: a too-loose snapshot won't catch flag drift — pin names + params + help bytes.

## WP02 — `_doctor_shared` single console/guard home (IC-01, H1)

- **Goal**: Extract shared infra FIRST so every sibling imports a stable single-Console surface.
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: `test_doctor_shared.py` + golden green; one `Console()` instance.
- **Requirement refs**: FR-007.
- [x] T004 Create `_doctor_shared.py` (console/guards/`_is_interactive_environment`/constants) (WP02)
- [x] T005 Point `doctor.py` + `_profile_health_render` to the single home; no new `Console()` (WP02)
- [x] T006 Focused `_doctor_shared` tests; golden green (WP02)
- **Out-of-map edits**: `doctor.py` (swap shared-infra defs → import from `_doctor_shared`); `_profile_health_render.py` (console home reconciliation). Sequential chain → no concurrent writer.
- **Risks**: a per-module `Console()` breaks `--json` cleanliness + the doctrine snapshot (H1).

## WP03 — `_doctrine_collect` collector-seam completion (IC-02)

- **Goal**: Move the doctrine-health DATA COLLECTORS #1623 left in `doctor.py` into a sibling, completing the MODEL/RENDER/COLLECT triad.
- **Priority**: P1. **Dependencies**: WP02. **Independent test**: collector tests ≥90% + byte-pinned doctrine snapshot + golden green.
- **Requirement refs**: FR-003, FR-004, FR-006.
- [x] T007 Create `_doctrine_collect.py` (Cluster J collectors) (WP03)
- [x] T008 Delegate collectors in `doctor.py`; re-export `_collect_profile_health`,`_collect_org_layer_data`,`_build_pack_entries`,`_count_pack_artifacts`,`_resolve_pack_version`,`_render_org_layer_section` (WP03)
- [x] T009 Collector tests ≥90%; doctrine snapshot + golden green (WP03)
- **Out-of-map edits**: `doctor.py` (delegation + re-export). Do NOT touch `_doctrine_health.py`/`_profile_health_render.py` (already done by #1623).
- **Risks**: moving a collector without re-exporting breaks the 58 test files' imports.

## WP04 — `_identity_audit` (IC-03)

- **Goal**: Move identity+topology helpers; decompose `identity` CC19 to ≤15-CC tested helpers.
- **Priority**: P1. **Dependencies**: WP03. **Independent test**: identity/topology helper tests ≥90% + golden green.
- **Requirement refs**: FR-003, FR-004, FR-005, FR-006.
- [x] T010 Create `_identity_audit.py`; decompose `identity` CC19 (WP04)
- [x] T011 Delegate `identity`/`topology` bodies; re-export touched symbols (WP04)
- [x] T012 Focused tests ≥90%; golden green (WP04)
- **Out-of-map edits**: `doctor.py` (delegation + re-export).
- **Risks**: `identity` `--fail-on` exit semantics must be byte-preserved across the decomposition.

## WP05 — `_command_surface_doctor` (IC-04)

- **Goal**: Move tool-surface + command-skill + slash cluster (the `skills` cmd fuses command-skills + slash); decompose `skills` CC20 + `_repair_command_skill_state` CC16.
- **Priority**: P1. **Dependencies**: WP04. **Independent test**: surface helper tests ≥90% + golden + `tests/cli_gate/test_doctor_modes.py` green.
- **Requirement refs**: FR-003, FR-004, FR-005, FR-006.
- [x] T013 Create `_command_surface_doctor.py`; decompose `skills` CC20 + `_repair_command_skill_state` CC16 (WP05)
- [x] T014 Delegate `command-files`/`skills`/`tool-surfaces`; re-export `SlashCommandGap`,`_load_slash_command_state`,`_repair_slash_command_state` (WP05)
- [x] T015 Focused tests ≥90%; golden + safety-mode tests green (WP05)
- **Out-of-map edits**: `doctor.py` (delegation + re-export).
- **Risks**: `doctor skills`/`doctor sparse-checkout` safety predicates + argv fast-path key on names — keep names byte-identical (I-7).

## WP06 — `_mission_state_doctor` (IC-05)

- **Goal**: Move Cluster H (audit/repair/teamspace-dry-run); keep `mission_state` dispatch-thin and drop its `# noqa: C901` once helpers move.
- **Priority**: P1. **Dependencies**: WP05. **Independent test**: mission-state tests ≥90% + golden green.
- **Requirement refs**: FR-003, FR-004.
- [x] T016 Create `_mission_state_doctor.py`; drop the `# noqa: C901` if helpers move (WP06)
- [x] T017 Delegate `mission-state` body to sibling helpers (WP06)
- [x] T018 Focused mission-state tests ≥90%; golden green (WP06)
- **Out-of-map edits**: `doctor.py` (delegation; drop the now-unneeded suppression).
- **Risks**: mode-exclusivity (0 no-mode / 2 multi-mode) + gate exit 1 must be preserved exactly.

## WP07 — `_coordination_doctor` (IC-06, H2)

- **Goal**: Move Cluster K (git-version + worktree/sparse-drift health); decompose `_check_lane_sparse_checkout_drift` CC19; keep `merge.path_is_under_worktrees` FUNCTION-LOCAL.
- **Priority**: P1. **Dependencies**: WP06. **Independent test**: coordination tests ≥90% + import-graph shows no `doctor↔merge` cycle + golden green.
- **Requirement refs**: FR-003, FR-004, FR-005, FR-007.
- [x] T019 Create `_coordination_doctor.py`; decompose `_check_lane_sparse_checkout_drift` CC19; KEEP `merge` import function-local (WP07)
- [x] T020 Delegate `coordination` body to sibling (WP07)
- [x] T021 Coordination tests ≥90%; no `doctor↔merge` cycle; golden green (WP07)
- **Out-of-map edits**: `doctor.py` (delegation).
- **Risks**: hoisting `path_is_under_worktrees` to module scope reintroduces the `doctor↔merge` cycle (H2) — rejection criterion.

## WP08 — `_sparse_checkout_doctor` (IC-07)

- **Goal**: Move Cluster E (remediation render/flow); decompose `sparse_checkout` cmd CC19.
- **Priority**: P1. **Dependencies**: WP07. **Independent test**: sparse-checkout tests ≥90% + golden green.
- **Requirement refs**: FR-003, FR-004, FR-005.
- [x] T022 Create `_sparse_checkout_doctor.py`; decompose `sparse_checkout` cmd CC19 (WP08)
- [x] T023 Delegate `sparse-checkout` body to sibling (WP08)
- [x] T024 Focused tests ≥90%; golden green (WP08)
- **Out-of-map edits**: `doctor.py` (delegation).
- **Risks**: the `--fix` CI-refusal exit path (0 clean / 1 state-present-or-refusal) must be preserved.

## WP09 — `_workspace_husk_doctor` (IC-08)

- **Goal**: Move Cluster C (workspace-husk status/fix/report).
- **Priority**: P1. **Dependencies**: WP08. **Independent test**: workspace-husk tests ≥90% + golden green.
- **Requirement refs**: FR-003, FR-004.
- [x] T025 Create `_workspace_husk_doctor.py` (WP09)
- [x] T026 Delegate `workspaces` body to sibling (WP09)
- [x] T027 Focused tests ≥90%; golden green (WP09)
- **Out-of-map edits**: `doctor.py` (delegation).
- **Risks**: husk `--fix` vs report exit (0 clean / 1 husks-or-error) preserved.

## WP10 — `_daemon_doctor` (IC-09)

- **Goal**: Move `orphan-daemons` + `restart-daemon` bodies into a cohesive daemon sibling.
- **Priority**: P1. **Dependencies**: WP09. **Independent test**: daemon tests ≥90% + golden + argv-fast-path (`restart-daemon`) green.
- **Requirement refs**: FR-003, FR-004.
- [x] T028 Create `_daemon_doctor.py` (WP10)
- [x] T029 Delegate the two daemon bodies; preserve `restart-daemon` 0/1/2/3 contract (WP10)
- [x] T030 Focused tests ≥90%; golden + argv-fast-path green (WP10)
- **Out-of-map edits**: `doctor.py` (delegation).
- **Risks**: the four-state `restart-daemon` exit contract + `_is_doctor_restart_daemon_invocation` argv fast-path must be preserved.

## WP11 — Shim re-export sweep + pointer verify + full gate (IC-10)

- **Goal**: Sole owner of `doctor.py` — finalize the re-export block, decompose `state_roots` CC17, verify the pointer comment, and run the full gate sweep proving byte-identity.
- **Priority**: P1 (closeout). **Dependencies**: WP10. **Independent test**: golden + full doctor + cli_gate suites + ruff/C901/mypy all green.
- **Requirement refs**: FR-001, FR-002, FR-005, FR-006, FR-007.
- [x] T031 Re-export sweep: all 11 private symbols + `app`/`SlashCommandGap` resolve from `doctor`; decompose `state_roots` cmd CC17 (WP11)
- [x] T032 Verify pointer comment references #2059; `doctor.py` ≤ ~400 LOC, no new responsibilities (WP11)
- [x] T033 Full gate sweep: golden + 58 doctor tests + cli_gate; ruff + C901 + mypy --strict clean, zero new suppressions (WP11)
- **Owned files**: `src/specify_cli/cli/commands/doctor.py` (this WP is its SOLE owner) + `tests/specify_cli/cli/commands/test_doctor_shim_reexports.py`.
- **Risks**: a missing re-export or a `state_roots` left at CC17 fails the closeout gate.
