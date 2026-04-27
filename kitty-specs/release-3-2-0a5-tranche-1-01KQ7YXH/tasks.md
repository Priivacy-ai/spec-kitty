# Tasks: 3.2.0a5 Tranche 1 — Release Reset & CLI Surface Cleanup

**Mission ID**: `01KQ7YXHA5AMZHJT3HQ8XPTZ6B` (mid8 `01KQ7YXH`)
**Mission Slug**: `release-3-2-0a5-tranche-1-01KQ7YXH`
**Branch contract**: planning/base/merge target = `release/3.2.0a5-tranche-1` (`branch_matches_target = true`)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Bulk-edit map**: [occurrence_map.yaml](./occurrence_map.yaml)

## Overview

Eight work packages, 39 subtasks total. Seven WPs are independent and lane-parallelizable; **WP02 lands last** as the CHANGELOG / release-metadata consolidator. Two WPs (WP04, WP06) are at the upper end of complexity for this tranche; the rest are focused 3–5 subtask packages. **WP08 was added live during `/spec-kitty.tasks`** when `finalize-tasks` rejected the mission's own DecisionPoint event — same class of "tooling that bites real workflows" bug as FR-002.

## Subtask Index

| ID   | Description                                                                 | WP   | Parallel |
|------|-----------------------------------------------------------------------------|------|----------|
| T001 | Swap call order in `runner.py:163-164` so `metadata.save()` precedes `_stamp_schema_version()` | WP01 |          | [D] |
| T002 | Extend `tests/cross_cutting/versioning/test_upgrade_version_update.py` with schema_version persistence assertion | WP01 | [D] |
| T003 | New `tests/e2e/test_upgrade_post_state.py` smoke covering upgrade → branch-context | WP01 | [D] |
| T004 | Run `mypy --strict` and `ruff check` on changed surfaces; address any drift | WP01 |          | [D] |
| T005 | Bump `pyproject.toml::[project].version` from `3.2.0a4` → `3.2.0a5`         | WP02 |          |
| T006 | Split `CHANGELOG.md` heading: convert `[Unreleased - 3.2.0]` → `[3.2.0a5] — <date>` and insert new `[Unreleased]` placeholder above | WP02 |          |
| T007 | Consolidate per-FR CHANGELOG entries under `[3.2.0a5]` (collected from each landed WP's PR description) | WP02 |          |
| T008 | Run `tests/release/test_dogfood_command_set.py` and `tests/release/test_release_prep.py`; update fixtures if drifted | WP02 |          |
| T009 | Verify `spec-kitty --version` reports `3.2.0a5` after editable reinstall   | WP02 |          |
| T010 | Replace `.python-version` contents with `3.11`                              | WP03 |          |
| T011 | Run `mypy --strict src/specify_cli/mission_step_contracts/executor.py`; triage and fix any errors | WP03 |          |
| T012 | Add new test `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` invoking mypy in-process and asserting clean exit | WP03 | [P]      |
| T013 | Re-run `tests/cross_cutting/` and `tests/missions/` to confirm no regressions from python-version change | WP03 |          |
| T014 | Run `ruff check .python-version pyproject.toml src/specify_cli/mission_step_contracts/` | WP03 | [P]      |
| T015 | Delete deprecated `/spec-kitty.checklist` source template AND its override copy | WP04 |          |
| T016 | Remove `/spec-kitty.checklist` entries from `.kittify/command-skills-manifest.json` and `_legacy_codex_hashes.py` | WP04 | [P]      |
| T017 | Delete every deprecated checklist snapshot, regression baseline, and upgrade fixture per `occurrence_map.yaml` | WP04 |          |
| T018 | Update `tests/specify_cli/skills/{test_registry,test_command_renderer,test_installer}.py` and `tests/missions/test_command_templates_canonical_path.py` to drop checklist expectations | WP04 |          |
| T019 | Add aggregate regression `tests/specify_cli/test_no_checklist_surface.py` (recursive grep for `/spec-kitty.checklist` and `checklist*` filenames across src/tests/docs/agent dirs) | WP04 | [P]      |
| T020 | Add artifact-preservation test `tests/missions/test_specify_creates_requirements_checklist.py` proving `kitty-specs/<slug>/checklists/requirements.md` still gets created | WP04 | [P]      |
| T021 | Update doc references: `README.md`, `docs/reference/{slash-commands,file-structure,supported-agents}.md` per occurrence_map (REMOVE surface mentions, KEEP artifact-name mentions) | WP04 | [P]      |
| T022 | Add non-git-target detection in `src/specify_cli/cli/commands/init.py` near the existing `git not detected` branch (~line 360); print one yellow info line containing both "not a git repository" and "git init" | WP05 |          |
| T023 | Append a "next: run `git init`" item to the post-init quick-start summary in `init.py` when target is not a git repo | WP05 |          |
| T024 | Remove the `/spec-kitty.checklist` quick-start line at `init.py:723` (FR-003 boundary owned by WP05 to keep `init.py` ownership single-WP) | WP05 |          |
| T025 | Add `tests/specify_cli/cli/commands/test_init_non_git_message.py` covering both unit assertions and CliRunner-driven smoke | WP05 |          |
| T026 | Create `src/specify_cli/diagnostics/__init__.py` and `src/specify_cli/diagnostics/dedup.py` exposing `report_once`, `mark_invocation_succeeded`, `invocation_succeeded`, `reset_for_invocation` | WP06 |          |
| T027 | Wrap `Not authenticated, skipping sync` callsites at `sync/background.py:270` and `:325` with `report_once("sync.unauthenticated")` gate | WP06 |          |
| T028 | Locate the token-refresh-failed logger in `src/specify_cli/auth/` and wrap with `report_once("auth.token_refresh_failed")` | WP06 |          |
| T029 | In the `agent mission create` JSON-payload writer ONLY, call `mark_invocation_succeeded()` immediately after the final `print(json.dumps(...))`. Auditing other JSON-emitting commands is explicitly out of scope. | WP06 |          |
| T030 | Update atexit handlers at `sync/background.py:456` and `sync/runtime.py:381` to consult `invocation_succeeded()` and downgrade warnings on success | WP06 |          |
| T031 | Add `tests/sync/test_diagnostic_dedup.py` covering ContextVar gate + reset behavior | WP06 | [P]      |
| T032 | Add `tests/e2e/test_mission_create_clean_output.py` covering JSON cleanup + dedup + no-red-after-success | WP06 | [P]      |
| T033 | Add `tests/specify_cli/cli/test_no_visible_feature_alias.py` (typer walk + `--help` grep + `hidden=True` assertion) | WP07 | [P]      |
| T034 | Add `tests/e2e/test_feature_alias_smoke.py` (passing `--feature` to one historically-accepting command behaves identically to `--mission`) | WP07 | [P]      |
| T035 | Add `tests/specify_cli/cli/test_decision_command_shape_consistency.py` (typer walk + multi-source grep + `--help` listing assertion) | WP07 | [P]      |
| T036 | Add an `event_type`-presence guard in `read_events()` (`src/specify_cli/status/store.py:209` per-line loop) that skips events carrying a top-level `event_type` field (the wire-format discriminator for mission-level events), with a `# Why:` comment naming Decision Moment Protocol as the cooperating writer. Preserves the existing fail-loud contract for malformed lane-transition events. | WP08 |          |
| T037 | Add `tests/status/test_read_events_tolerates_decision_events.py` exercising mixed lane-transition + DecisionPoint event logs | WP08 | [P]      |
| T038 | Re-run this mission's `finalize-tasks` against the fixed reader to confirm the live regression is closed (no bypass needed) | WP08 |          |
| T039 | Run `mypy --strict src/specify_cli/status/store.py` and `ruff check src/specify_cli/status/ tests/status/test_read_events_tolerates_decision_events.py` | WP08 | [P]      |

## Work Packages

---

### WP01 — FR-002 schema_version clobber fix + regression

- **Goal**: After `spec-kitty upgrade --yes` succeeds, `spec_kitty.schema_version` MUST persist in `.kittify/metadata.yaml`, and a subsequent `spec-kitty agent mission branch-context --json` MUST exit 0 (no `PROJECT_MIGRATION_NEEDED` block).
- **Priority**: P0 — foundational; the dev-experience blocker every other WP would hit.
- **Independent test**: `tests/e2e/test_upgrade_post_state.py` (new) drives a tmp project end-to-end.
- **Subtasks**:
  - [x] T001 Swap call order in `runner.py:163-164` so `metadata.save()` precedes `_stamp_schema_version()` (WP01)
  - [x] T002 Extend `tests/cross_cutting/versioning/test_upgrade_version_update.py` with schema_version persistence assertion (WP01)
  - [x] T003 New `tests/e2e/test_upgrade_post_state.py` smoke covering upgrade → branch-context (WP01)
  - [x] T004 Run `mypy --strict` and `ruff check` on changed surfaces; address any drift (WP01)
- **Implementation sketch**: One-line code change (move `_stamp_schema_version` call below `metadata.save`) plus two test files. Read-modify-atomic-write in `_stamp_schema_version` already handles the post-save file safely.
- **Parallel opportunities**: T002 and T003 can be drafted in parallel by the same agent after T001.
- **Dependencies**: none.
- **Risks**: minimal; covered by both unit and e2e tests.
- **Estimated prompt size**: ~350 lines.
- **Prompt**: [tasks/WP01-fr002-schema-version-clobber-fix.md](./tasks/WP01-fr002-schema-version-clobber-fix.md)

---

### WP02 — NFR-002 release metadata coherence (final consolidator)

- **Goal**: `pyproject.toml`, `CHANGELOG.md`, `.python-version`, and the release-prep test fixtures all agree on the next prerelease state (`3.2.0a5`).
- **Priority**: P0 — gates `tests/release/`; lands LAST so per-WP CHANGELOG entries can be consolidated.
- **Independent test**: `tests/release/test_dogfood_command_set.py` and `tests/release/test_release_prep.py` pass.
- **Subtasks**:
  - [ ] T005 Bump `pyproject.toml::[project].version` from `3.2.0a4` → `3.2.0a5` (WP02)
  - [ ] T006 Split `CHANGELOG.md` heading: convert `[Unreleased - 3.2.0]` → `[3.2.0a5] — <date>` and insert new `[Unreleased]` placeholder above (WP02)
  - [ ] T007 Consolidate per-FR CHANGELOG entries under `[3.2.0a5]` (collected from each landed WP's PR description) (WP02)
  - [ ] T008 Run `tests/release/test_dogfood_command_set.py` and `tests/release/test_release_prep.py`; update fixtures if drifted (WP02)
  - [ ] T009 Verify `spec-kitty --version` reports `3.2.0a5` after editable reinstall (WP02)
- **Implementation sketch**: Mechanical edits + run release-prep tests + add CHANGELOG entries summarizing each WP01/WP03..WP08 fix.
- **Parallel opportunities**: none — single-file consolidator.
- **Dependencies**: WP01, WP03, WP04, WP05, WP06, WP07, WP08 (lands last).
- **Risks**: release-prep fixtures may have hardcoded version strings that need updating beyond pyproject — covered by T008.
- **Estimated prompt size**: ~250 lines.
- **Prompt**: [tasks/WP02-release-metadata-coherence.md](./tasks/WP02-release-metadata-coherence.md)

---

### WP03 — FR-001 `.python-version` + restore strict mypy

- **Goal**: `.python-version` no longer pins a higher floor than `pyproject.toml::requires-python`; `mypy --strict` is clean on `mission_step_contracts/executor.py` and stays clean.
- **Priority**: P1 — local agent productivity.
- **Independent test**: `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` (new).
- **Subtasks**:
  - [ ] T010 Replace `.python-version` contents with `3.11` (WP03)
  - [ ] T011 Run `mypy --strict src/specify_cli/mission_step_contracts/executor.py`; triage and fix any errors (WP03)
  - [ ] T012 Add new test `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` invoking mypy in-process and asserting clean exit (WP03)
  - [ ] T013 Re-run `tests/cross_cutting/` and `tests/missions/` to confirm no regressions from python-version change (WP03)
  - [ ] T014 Run `ruff check .python-version pyproject.toml src/specify_cli/mission_step_contracts/` (WP03)
- **Implementation sketch**: One-byte file change for `.python-version`; minor type-annotation cleanups; one new test file.
- **Parallel opportunities**: T012 and T014 can be drafted in parallel after T011.
- **Dependencies**: none.
- **Risks**: T011 may surface latent type errors that pre-existed but were never enforced; budget extra time inside the WP.
- **Decision**: Decision Moment `01KQ7ZSQKT9DVH7B4GGXWS8DTW` chose `3.11` floor.
- **Estimated prompt size**: ~250 lines.
- **Prompt**: [tasks/WP03-python-version-and-strict-mypy.md](./tasks/WP03-python-version-and-strict-mypy.md)

---

### WP04 — FR-003 + FR-004 `/spec-kitty.checklist` bulk removal

- **Goal**: Zero references to `/spec-kitty.checklist` across every supported agent's rendered surface; `kitty-specs/<mission>/checklists/requirements.md` still gets created by `/spec-kitty.specify`.
- **Priority**: P1 — largest WP; bulk-edit gated by [`occurrence_map.yaml`](./occurrence_map.yaml).
- **Independent test**: `tests/specify_cli/test_no_checklist_surface.py` (new) + `tests/missions/test_specify_creates_requirements_checklist.py` (new).
- **Subtasks**:
  - [ ] T015 Delete deprecated `/spec-kitty.checklist` source template AND its override copy (WP04)
  - [ ] T016 Remove `/spec-kitty.checklist` entries from `.kittify/command-skills-manifest.json` and `_legacy_codex_hashes.py` (WP04)
  - [ ] T017 Delete every deprecated checklist snapshot, regression baseline, and upgrade fixture per `occurrence_map.yaml` (WP04)
  - [ ] T018 Update `tests/specify_cli/skills/{test_registry,test_command_renderer,test_installer}.py` and `tests/missions/test_command_templates_canonical_path.py` to drop checklist expectations (WP04)
  - [ ] T019 Add aggregate regression `tests/specify_cli/test_no_checklist_surface.py` (WP04)
  - [ ] T020 Add artifact-preservation test `tests/missions/test_specify_creates_requirements_checklist.py` (WP04)
  - [ ] T021 Update doc references per `occurrence_map.yaml` (WP04)
- **Implementation sketch**: Mechanical removal driven by `occurrence_map.yaml`. Implementing agent MUST load the `spec-kitty-bulk-edit-classification` skill before starting and verify the diff against the occurrence map before commit.
- **Parallel opportunities**: T016, T019, T020, T021 can be done in parallel after T015 lands.
- **Dependencies**: none.
- **Risks**: missed reference creates a DIRECTIVE_035 violation; mitigated by T019's aggregate scanner. Snapshot tests in T017/T018 must be regenerated for ALL 12 slash-command agents.
- **Boundary**: `init.py:723` (one occurrence) is owned by **WP05** (T024) to keep `init.py` ownership single-WP.
- **Estimated prompt size**: ~500 lines.
- **Prompt**: [tasks/WP04-checklist-surface-bulk-removal.md](./tasks/WP04-checklist-surface-bulk-removal.md)

---

### WP05 — FR-005 `init` non-git message (+ FR-003 init.py boundary line)

- **Goal**: Running `spec-kitty init` in a non-git directory emits a single actionable message; the deprecated `/spec-kitty.checklist` quick-start line at `init.py:723` is removed in the same WP that owns `init.py`.
- **Priority**: P2 — UX polish.
- **Independent test**: `tests/specify_cli/cli/commands/test_init_non_git_message.py` (new).
- **Subtasks**:
  - [ ] T022 Add non-git-target detection in `src/specify_cli/cli/commands/init.py` near the existing `git not detected` branch; print one yellow info line containing both "not a git repository" and "git init" (WP05)
  - [ ] T023 Append a "next: run `git init`" item to the post-init quick-start summary in `init.py` when target is not a git repo (WP05)
  - [ ] T024 Remove the `/spec-kitty.checklist` quick-start line at `init.py:723` (FR-003 boundary owned by WP05 to keep `init.py` ownership single-WP) (WP05)
  - [ ] T025 Add `tests/specify_cli/cli/commands/test_init_non_git_message.py` covering both unit assertions and CliRunner-driven smoke (WP05)
- **Implementation sketch**: Single subprocess check using `git rev-parse --is-inside-work-tree`; small UX additions; one new test file.
- **Parallel opportunities**: T025 can be drafted in parallel with T022/T023/T024 by the same agent.
- **Dependencies**: none.
- **Risks**: subprocess to `git` may fail with the binary missing; existing `is_git_available()` branch already handles that case — reuse it.
- **Estimated prompt size**: ~250 lines.
- **Prompt**: [tasks/WP05-init-non-git-message.md](./tasks/WP05-init-non-git-message.md)

---

### WP06 — FR-008 + FR-009 diagnostic dedup + atexit success-flag

- **Goal**: One-per-cause diagnostic gating per CLI invocation; no red shutdown noise after a successful JSON-output command.
- **Priority**: P2 — visible noise but not blocking.
- **Independent test**: `tests/sync/test_diagnostic_dedup.py` (new) + `tests/e2e/test_mission_create_clean_output.py` (new).
- **Subtasks**:
  - [ ] T026 Create `src/specify_cli/diagnostics/__init__.py` and `src/specify_cli/diagnostics/dedup.py` exposing `report_once`, `mark_invocation_succeeded`, `invocation_succeeded`, `reset_for_invocation` (WP06)
  - [ ] T027 Wrap `Not authenticated, skipping sync` callsites at `sync/background.py:270` and `:325` with `report_once("sync.unauthenticated")` gate (WP06)
  - [ ] T028 Locate the token-refresh-failed logger in `src/specify_cli/auth/` and wrap with `report_once("auth.token_refresh_failed")` (WP06)
  - [ ] T029 In the `agent mission create` JSON-payload writer ONLY, call `mark_invocation_succeeded()` immediately after the final `print(json.dumps(...))`. Auditing other JSON-emitting commands is explicitly out of scope. (WP06)
  - [ ] T030 Update atexit handlers at `sync/background.py:456` and `sync/runtime.py:381` to consult `invocation_succeeded()` and downgrade warnings on success (WP06)
  - [ ] T031 Add `tests/sync/test_diagnostic_dedup.py` covering ContextVar gate + reset behavior (WP06)
  - [ ] T032 Add `tests/e2e/test_mission_create_clean_output.py` covering JSON cleanup + dedup + no-red-after-success (WP06)
- **Implementation sketch**: New `diagnostics` package using `contextvars.ContextVar` for dedup + module-level boolean for success flag. Wrap two existing log sites; call `mark_invocation_succeeded()` from JSON-emitting command paths; consult `invocation_succeeded()` from atexit handlers.
- **Parallel opportunities**: T031 and T032 (test-only) can run in parallel after T026 + T030 land.
- **Dependencies**: none.
- **Risks**: `mark_invocation_succeeded()` must NOT be called on failure paths; tests in T032 cover the failure path explicitly.
- **Estimated prompt size**: ~500 lines.
- **Prompt**: [tasks/WP06-diagnostic-dedup-and-atexit.md](./tasks/WP06-diagnostic-dedup-and-atexit.md)

---

### WP07 — FR-006 + FR-007 close-with-evidence regressions

- **Goal**: Lock down "already-fixed-on-main" status of `--feature` hidden alias (#790) and `spec-kitty agent decision` command shape (#774) by adding regression tests that prevent future drift.
- **Priority**: P3 — close-with-evidence per `start-here.md` "Done Criteria".
- **Independent test**: the three new test files themselves.
- **Subtasks**:
  - [ ] T033 Add `tests/specify_cli/cli/test_no_visible_feature_alias.py` (typer walk + `--help` grep + `hidden=True` assertion) (WP07)
  - [ ] T034 Add `tests/e2e/test_feature_alias_smoke.py` (passing `--feature` to one historically-accepting command behaves identically to `--mission`) (WP07)
  - [ ] T035 Add `tests/specify_cli/cli/test_decision_command_shape_consistency.py` (typer walk + multi-source grep + `--help` listing assertion) (WP07)
- **Implementation sketch**: Three new test files; no production code changes. Each test introspects the typer app and grep-checks docs/snapshots/templates.
- **Parallel opportunities**: All three tests are independent — agent can implement in any order.
- **Dependencies**: none.
- **Risks**: minimal — purely additive tests over already-working code.
- **Estimated prompt size**: ~150 lines.
- **Prompt**: [tasks/WP07-close-with-evidence-regressions.md](./tasks/WP07-close-with-evidence-regressions.md)

---

### WP08 — FR-010 status event reader robustness fix

- **Goal**: `read_events()` in `src/specify_cli/status/store.py` MUST tolerate non-lane-transition events (e.g. `DecisionPointOpened`, `DecisionPointResolved`) in `status.events.jsonl` instead of raising `KeyError('wp_id')`.
- **Priority**: P0 — currently blocks `finalize-tasks` (and every other reader) for any mission that has used the Decision Moment Protocol. Discovered live during this very `/spec-kitty.tasks` run; the mission's own DecisionPoint event triggered the bug.
- **Independent test**: `tests/status/test_read_events_tolerates_decision_events.py` (new).
- **Subtasks**:
  - [ ] T036 Add an `event_type`-presence guard in `read_events()` (per-line loop) that skips events carrying a top-level `event_type` field, with a `# Why:` comment naming Decision Moment Protocol as the cooperating writer. Preserves the existing fail-loud contract for malformed lane-transition events. (WP08)
  - [ ] T037 Add `tests/status/test_read_events_tolerates_decision_events.py` exercising mixed lane-transition + DecisionPoint event logs (WP08)
  - [ ] T038 Re-run this mission's `finalize-tasks` against the fixed reader to confirm the live regression is closed (WP08)
  - [ ] T039 Run `mypy --strict src/specify_cli/status/store.py` and `ruff check src/specify_cli/status/ tests/status/test_read_events_tolerates_decision_events.py` (WP08)
- **Implementation sketch**: ~5 LOC inside `read_events()` per-line loop + a sibling unit test. Uses the duck-type approach instead of an event-type allowlist for future-proofing.
- **Parallel opportunities**: T037 and T039 can be drafted in parallel after T036.
- **Dependencies**: none.
- **Risks**: low — additive guard; existing lane-transition path unaffected.
- **Live evidence**: this mission's own `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/status.events.jsonl` starts with a `DecisionPointOpened` event and `finalize-tasks` failed on it. After T036 lands, T038 confirms the live regression is closed.
- **Estimated prompt size**: ~250 lines.
- **Prompt**: [tasks/WP08-status-event-reader-robustness.md](./tasks/WP08-status-event-reader-robustness.md)

## MVP Scope

**MVP** = WP01 + WP08 + WP02. Without WP01, every other WP's implementer hits the `PROJECT_MIGRATION_NEEDED` gate documented in `spec.md`. Without WP08, every other WP's implementer hits the `finalize-tasks` reader bug as soon as their mission opens any Decision Moment. Without WP02, the release-prep tests fail. Everything else is desirable but not on the critical path for "the next prerelease tag exists and works".

## Parallelization

WP01, WP03, WP04, WP05, WP06, WP07, WP08 are all dependency-free and can be lane-parallelized. WP02 lands last to consolidate CHANGELOG entries.
