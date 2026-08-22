---
description: "Work packages for M0 — mission_type backfill migration"
---

# Work Packages: M0 — mission_type backfill migration

**Inputs**: `spec.md`, `plan.md` (squad #1 + #2 folded; operator decision B).
**Prerequisites**: plan.md (required), spec.md.

**Tests**: ATDD-first. Every AC is a named red-first test authored before the code that greens it.

**Organization**: Subtasks (`Txxx`) roll up into work packages (`WPxx`), each independently deliverable.

## Path Conventions

- **Single project**: `src/specify_cli/`, `tests/specify_cli/`.

---

## Work Package WP01: Backfill domain module (Priority: P0)

**Goal**: The `backfill_mission_type.py` domain module — detection, profile-resolution-gated
write-vs-needs_manual decision, robust repo walk, dossier rehash — with red-first unit tests.
**Independent Test**: `pytest tests/specify_cli/migration/test_backfill_mission_type.py` green;
each AC test demonstrably red before its implementing subtask.
**Prompt**: `/tasks/WP01-backfill-domain-module.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005
**Terminal state**: `done` when all WP01 unit tests pass and the module is ruff+mypy clean.

### Included Subtasks

- [ ] T001 Create `src/specify_cli/migration/backfill_mission_type.py` skeleton: `MISSION_TYPE_KEY`/`LEGACY_MISSION_KEY`/reason constants, `MissionTypeBackfillAction` Literal, `MissionTypeBackfillResult` dataclass (incl. `dossier_warning`).
- [ ] T002 Implement `_profile_resolves(repo, key)` + per-mission `backfill_mission_mission_type` (isinstance-guarded detection, skip-already-typed, profile-resolve→write / else→needs_manual_resolution, canonical sorted-key write, broad per-mission `except → error`).
- [ ] T003 Implement `backfill_mission_type_repo` (build `MissionTypeProfileRepository.for_project` once, sorted walk, unknown-slug **structured error**, dossier rehash on `wrote ∧ ¬dry_run` via `trigger_feature_dossier_sync_if_enabled` → `dossier_warning`).
- [ ] T004 Red-first unit tests `tests/specify_cli/migration/test_backfill_mission_type.py` (`pytestmark = [pytest.mark.unit, pytest.mark.fast]`): AC-1, AC-2a, AC-2b, AC-3, AC-4, AC-6, AC-10, R-4.

### Dependencies

- None (starting package).

### Risks & Mitigations

- Non-string legacy value crash → mandatory `isinstance(raw, str)` guard (mirror the audit); covered by AC-6.
- Per-mission decision complexity → flat branch order + broad `except`; extract `_profile_resolves`.

---

## Work Package WP02: `migrate backfill-mission-type` command (Priority: P0)

**Goal**: The dedicated CLI command wrapping the WP01 module — flags, stable `--json` schema,
exit-code contract, actionable needs-manual diagnostic, structured unknown-slug error.
**Independent Test**: `pytest tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py` green.
**Prompt**: `/tasks/WP02-migrate-command.md`
**Requirement Refs**: FR-006, FR-007, FR-008
**Terminal state**: `done` when all WP02 CLI tests pass and the command is ruff+mypy clean.

### Included Subtasks

- [ ] T005 Add `@app.command("backfill-mission-type")` to `src/specify_cli/cli/commands/migrate_cmd.py`: `--json`/`--dry-run`/`--mission`, resolve repo root, call `backfill_mission_type_repo`, build the stable `--json` payload (identical dry-run/live), print the needs_manual diagnostic, exit non-zero iff `error>0`, translate the structured unknown-slug error to a non-zero exit.
- [ ] T006 Red-first CLI tests `tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py` (`pytestmark = [pytest.mark.unit, pytest.mark.fast]`): AC-7 (json shape identity), AC-8 (exit codes), AC-9 (unknown-slug structured error).

### Dependencies

- WP01 (consumes `backfill_mission_type_repo` + `MissionTypeBackfillResult`).

### Risks & Mitigations

- Copying the sibling silent unknown-slug path → AC-9 pins the structured-error/exit≠0 contract.

---

## Work Package WP03: Gate regression + cross-authority agreement (Priority: P0)

**Goal**: Prove the reused census gate reds-then-greens around the backfill, prove the writer's
candidate set equals the audit's `legacy-key-only` set (non-vacuous), and pin the
predicate-correctness regression (unactivated built-in is written + release-safety gate greens).
**Independent Test**: `pytest tests/specify_cli/test_backfill_mission_type_gate_agreement.py` green.
**Prompt**: `/tasks/WP03-gate-regression-and-agreement.md`
**Requirement Refs**: FR-009
**Terminal state**: `done` when the gate regression + agreement + AC-5 tests pass, each red-first.

### Included Subtasks

- [ ] T007 Cross-authority agreement test (R-3) + AC-11 completeness gate red→green, over a corpus incl. blank-type AND non-string legacy values (`pytestmark = [pytest.mark.integration]`).
- [ ] T008 AC-5 predicate-correctness regression: `{"mission":"research"}` (research NOT activated) is written and `doctor mission-type --fail-on legacy-key-only,typeless,error` greens; AC-6 release-safety gate reds on residual typeless/needs-manual (`pytestmark = [pytest.mark.regression]`).
- [ ] T009 Document the release-safety predicate + the residual `unknown`-typo gap in the command docstring/help (changelog entry is closeout-owned).

### Dependencies

- WP01, WP02.

### Risks & Mitigations

- Fixture masking the over-block (a provisioned activation set hides AC-5) → AC-5 asserts research is NOT in `mission_type_activations`.
