# Work Packages: Team Kitty launch defaults for the CLI

**Inputs**: Design documents from `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md, occurrence_map.yaml (bulk edit)

**Tests**: Required. NFR-005 demands a witnessed failing-first check through the pre-existing entry point for every behavior change, and contracts/acceptance.md A1–A11 name the evidence.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and reviewable. Ownership is disjoint; a small out-of-map edit is acceptable with a one-line rationale in the Activity Log.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Subtasks are **reference rows**, not checkboxes: record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`.

## Path Conventions

Single Python package: `src/specify_cli/`, `src/charter/`, tests under `tests/`, docs under `docs/`. Mission artifacts under `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/`.

---

## Work Package WP01: Record the D-5 reversal (Priority: P0)

**Goal**: Land the architecture decision record that authorizes a packaged hosted target, and retire the "coming soon" launch-readiness page it supersedes.
**Independent Test**: The ADR is indexed, passes the docs gates, and names precedence, provenance, and why D-5 no longer applies.
**Prompt**: `/tasks/WP01-record-d5-reversal-adr.md`
**Requirement Refs**: C-005, FR-001

### Included Subtasks

T001 Write `docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md` (D-5 reversal: packaged default, precedence, provenance, no alias)
T002 Register the ADR in `docs/adr/3.x/README.md` and `docs/adr/3.x/index.md`
T003 [P] Supersede `docs/architecture/launch-readiness-future.md` and retarget its `docs/architecture/index.md` entry
T004 Run the docs gates for the touched pages

### Implementation Notes

- ADR template and numbering per `docs/adr/3.x/README.md`; status Accepted; cite #1621, #3980, PR #3249 (D-5 scoping) and the SaaS PRD that names the decision as open.

### Parallel Opportunities

- T003 is independent of T001/T002.

### Dependencies

- None (starting package; WP02 depends on it).

### Risks & Mitigations

- Docs description-length and SEO gates: keep descriptions within 50–180 chars; run `tests/docs/` for the touched files.

---

## Work Package WP02: Target authority with packaged default (Priority: P1)

**Goal**: One resolver knows the packaged default, reads `[team_kitty] server_url`, never reads `[sync]`, and reports its source.
**Independent Test**: contracts/target-resolution.md matrix passes as unit tests; `MISSING_HOST_CONFIG` no longer exists.
**Prompt**: `/tasks/WP02-target-authority-packaged-default.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-012, C-001

### Included Subtasks

T005 Red-first: extend `tests/auth/test_server_target.py` with the precedence matrix, `source`, `[team_kitty]` key, and `[sync]` ignored
T006 `src/specify_cli/auth/config.py`: `DEFAULT_HOSTED_SAAS_URL`; `get_saas_base_url` returns env or `None`
T007 `src/specify_cli/auth/server_target.py`: `[team_kitty] server_url`, packaged default, `source` on `ResolvedServerTarget`, no-target error removed
T008 [P] `src/specify_cli/tracker/saas_readiness.py`: drop the enable gate and `MISSING_HOST_CONFIG`; consume the resolver
T009 [P] `src/specify_cli/saas_client/auth.py` and `tests/integration/test_spec_kitty_home_cli.py`, `tests/tracker/test_server_target_fail_closed.py`: follow the new contract

### Implementation Notes

- Precedence env > configuration > packaged default; split-brain guard unchanged; `_warn_process_override` wording names `[team_kitty]`.

### Parallel Opportunities

- T008 and T009 after T007.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Hidden callers that catch `ConfigurationError` for "no target": grep before deleting the error path; A3 covers the matrix.

---

## Work Package WP03: Target visibility in auth commands (Priority: P1)

**Goal**: `auth login`, `auth status`, `auth whoami` (and `auth doctor`) print the resolved target and its source through the single printer, including JSON fields, with no credential leakage.
**Independent Test**: `auth status` prints `packaged default` on a fresh machine; `auth login` prints the same line before the flow; JSON carries `target.url`/`target.source`.
**Prompt**: `/tasks/WP03-target-visibility-auth-commands.md`
**Requirement Refs**: FR-004, NFR-004

### Included Subtasks

T010 Red-first: `tests/cli/commands/test_auth_status.py`, `test_auth_login.py`, `tests/auth/test_auth_doctor_report.py` expect the target line, the `packaged default` source, and JSON fields
T011 `src/specify_cli/cli/commands/_auth_saas_target.py`: packaged-default provenance; delete the "not configured" branch
T012 `src/specify_cli/cli/commands/_auth_login.py`: print the target line via the shared printer before the flow
T013 [P] `_auth_status.py`, `_auth_whoami.py`, `_auth_doctor.py`: JSON `target` fields; redaction test over every new string
T014 [P] `docs/api/auth-whoami-output.md`: document the line and fields

### Implementation Notes

- Never add a second resolver call site; the printer is the only place the target is rendered.

### Parallel Opportunities

- T013 and T014 after T011.

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Rich markup in URLs: keep `escape()` + `sanitize_terminal_text` on every rendered value (#182).

---

## Work Package WP04: Delete the enable gate (Priority: P1)

**Goal**: Remove `core/saas_sync_config.py`, its re-export, and every remaining consumer, so hosted features are always present and auth decides; the test suite no longer arms a flag.
**Independent Test**: `git grep is_saas_sync_enabled` is empty; tracker commands logged out fail with sign-in guidance; `tests/conftest.py` sets no flag.
**Prompt**: `/tasks/WP04-delete-enable-gate.md`
**Requirement Refs**: FR-009, FR-012, FR-013, C-001

### Included Subtasks

T015 Red-first: tracker command group and `mission create --from-ticket` logged out return sign-in guidance, never the "not enabled" message (`tests/agent/cli/commands/test_tracker*.py`)
T016 `src/specify_cli/cli/commands/tracker.py` and `mission_type.py`: remove the gate; readiness ladder and auth errors carry the guidance
T017 Delete `src/specify_cli/core/saas_sync_config.py` and `src/specify_cli/tracker/feature_flags.py`; update `tracker/__init__.py`
T018 [P] `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/integration/conftest.py`: remove the flag arming; replace `tests/architectural/test_saas_sync_gate_selection_invariance.py` with a guard that the retired name is never set by any test
T019 Verify no live reader of the retired name remains (`git grep`) and run the blast radius

### Implementation Notes

- Run only after WP02, WP05, WP06 removed their imports; otherwise the deletion breaks import.

### Parallel Opportunities

- T018 alongside T016.

### Dependencies

- Depends on WP02, WP05, WP06.

### Risks & Mitigations

- Collection-time skip gates keyed on the flag (#3213 class): the replacement arch test pins that none reappear.

---

## Work Package WP05: Named opt-outs and owned-checkout moves (Priority: P1)

**Goal**: The pre-review gate and the moment-handler import gate each get an honest switch; owned-checkout `move-task` / `mark-status` no longer refuse when hosted features are present.
**Independent Test**: `SPEC_KITTY_SKIP_PRE_REVIEW_GATE=1` skips only the gate; `SPEC_KITTY_NO_MOMENT_HANDLERS=1` registers nothing; an owned-checkout move with a fake capability fans out exactly once.
**Prompt**: `/tasks/WP05-named-opt-outs-owned-checkout.md`
**Requirement Refs**: FR-007, FR-008, FR-011, C-002

### Included Subtasks

T020 Red-first: `tests/specify_cli/core/test_env.py` for the two accessors; `tests/integration/test_owned_checkout_mark_status.py` + `test_explicit_checkout_commands.py` prove the owned move succeeds and fans out
T021 `src/specify_cli/core/env.py`: replace `SYNC_DISABLE_ENV_VARS` / `first_set_sync_disable_env` with `is_pre_review_gate_skipped()` and `moment_handlers_disabled()`
T022 [P] `src/specify_cli/status/adapters.py`: import gate reads `moment_handlers_disabled()`
T023 `src/specify_cli/cli/commands/agent/tasks_move_task.py` and `tasks_mark_status.py`: delete `_mt_preflight_owned_request`'s hosted refusal and the mark-status twin; re-key `_mt_pre_review_gate_env_disable_reason`
T024 [P] `src/specify_cli/cli/commands/agent/tasks.py` help text, `move-task.help` fixture, `tests/specify_cli/cli/commands/agent/conftest.py` and `test_tasks_move_task_pre_review_gate_observability.py`, `tests/next/test_internal_runtime_coverage.py`
T025 [P] `src/charter/offering/skills/spk-run-implement-review/SKILL.md` and `docs/api/skills/spk-run-implement-review.md`: opt-out guidance

### Implementation Notes

- Keep `--skip-pre-review-gate`; only the env-var spelling changes.

### Parallel Opportunities

- T022, T024, T025 after T021.

### Dependencies

- None.

### Risks & Mitigations

- Test isolation fixtures that set the old names silently stop isolating: T024 updates every fixture in the owned list and T019 (WP04) sweeps the rest.

---

## Work Package WP06: Readiness always on, one-time sign-in hint (Priority: P1)

**Goal**: The startup readiness coordinator no longer has a disabled path; a machine with no session gets one non-blocking hint, once, interactively; `auth logout` resets it; machine output stays clean.
**Independent Test**: tests/readiness matrix: first interactive run hints, second does not, JSON/help/version/non-TTY never do; logout resets.
**Prompt**: `/tasks/WP06-readiness-one-time-hint.md`
**Requirement Refs**: FR-005, FR-006, FR-013, NFR-003

### Included Subtasks

T026 Red-first: `tests/readiness/` cases for the hint contract and for `NOT_IN_TEAMSPACE`; `tests/cli/commands/test_auth_logout.py` for the reset
T027 `src/specify_cli/readiness/hint_state.py` (new): per-machine marker under the runtime state root, atomic write
T028 `src/specify_cli/readiness/coordinator.py`: remove the disabled path and the gate import; render the one-time hint for `NOT_IN_TEAMSPACE`; keep `LOGGED_OUT_IN_TEAMSPACE` guidance
T029 [P] `src/specify_cli/readiness/render.py`: hint text (interactive only) and the non-interactive no-op
T030 [P] `src/specify_cli/cli/commands/_auth_logout.py`: reset the marker after `clear_session()`; `src/specify_cli/cli/helpers.py` docstring cleanup

### Implementation Notes

- Suppression matrix stays authoritative: MACHINE_OUTPUT, `--help`, `--version`, non-TTY are silent.

### Parallel Opportunities

- T029 and T030 after T027.

### Dependencies

- None.

### Risks & Mitigations

- Hint printed twice by concurrent invocations: atomic marker write; acceptable worst case is one duplicate.

---

## Work Package WP07: Provisioning, redaction, completion, env docs (Priority: P2)

**Goal**: Every registry that lists environment names carries the two new opt-outs and none of the retired ones; the env-var reference documents launch behavior.
**Independent Test**: `m_3_2_8` never seeds a retired name; redaction allowlist and completion match; `docs/api/environment-variables.md` has no retired name.
**Prompt**: `/tasks/WP07-provisioning-redaction-env-docs.md`
**Requirement Refs**: FR-011, FR-014, C-002

### Included Subtasks

T031 Red-first: `tests/specify_cli/upgrade/migrations/test_provision_kitty_env.py`, `tests/specify_cli/core/test_secret_redaction.py`, `tests/specify_cli/bootstrap/test_env_file_loader.py`, `tests/docs/test_env_var_scope_warning.py`
T032 `src/specify_cli/upgrade/migrations/m_3_2_8_provision_kitty_env.py`: `GOVERNED_OPERATOR_VARS` follows contracts/environment-and-config.md
T033 [P] `src/specify_cli/core/secret_redaction.py` and `src/specify_cli/completion.py`
T034 [P] `docs/api/environment-variables.md`: rewrite the hosted section (launch behavior, precedence, `[team_kitty]`, opt-outs)
T035 [P] `.github/workflows/ci-windows.yml`: drop the retired variable

### Implementation Notes

- The migration never invents values; it seeds only names observed in the live environment.

### Parallel Opportunities

- T033–T035 after T032.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- `tests/architectural/test_no_dead_symbols.py` tracks these registries: run it.

---

## Work Package WP08: Vocabulary sweep under the occurrence map (Priority: P2)

**Goal**: No live source, skill, doc, or test fixture speaks of the retired names or of "sync" as a live thing; archives untouched.
**Independent Test**: A10 `git grep` witness is empty outside occurrence-map exceptions; terminology guard green; docs index regenerated.
**Prompt**: `/tasks/WP08-vocabulary-sweep.md`
**Requirement Refs**: C-002, C-003

### Included Subtasks

T036 Skills: `spk-team-sync`, `spk-team-auth`, `spk-team-tracker`, `spec-kitty-mission-review` SKILL.md files; `src/specify_cli/__init__.py` and `src/runtime/next/_internal_runtime/events.py` comments
T037 Docs: supersede or rewrite the non-archive pages listed in the prompt; rewrite the flag section of `docs/context/team-kitty.md`; `CHANGELOG.md` entry
T038 Test fixtures not owned by WP02–WP07/WP09 that set or assert the retired names
T039 Regenerate `docs/development/3-2-docs-retrieval-index.yaml`; run `tests/docs/`
T040 A10 witness: `git grep` over live paths; `tests/architectural/test_no_legacy_terminology.py`; record in the Activity Log

### Implementation Notes

- Follow `occurrence_map.yaml` category actions; `kitty-specs/**`, `kitty-ops/**`, `docs/adr/**`, `docs/archive/**`, `docs/changelog/**` are never edited.

### Parallel Opportunities

- T036, T037, T038 in parallel; T039/T040 last.

### Dependencies

- Depends on WP03, WP04, WP07.

### Risks & Mitigations

- Over-reach into archives: the diff-compliance check at review blocks `do_not_change` paths.

---

## Work Package WP09: Public-CLI acceptance and gates (Priority: P1) 🎯 integration

**Goal**: contracts/acceptance.md A1–A9 pass through the public `spec-kitty` subprocess against recording stubs; A11 gates green.
**Independent Test**: `tests/integration/test_launch_defaults_acceptance.py` green; `tests/architectural/` full at or below baselines; `make test-fast` green.
**Prompt**: `/tasks/WP09-public-cli-acceptance.md`
**Requirement Refs**: NFR-001, NFR-002, NFR-005, C-004

### Included Subtasks

T041 `tests/integration/_hosted_stubs.py`: threaded recording stubs for the SaaS (admission, capability mint, OAuth token) and the relay (`/managed/control`)
T042 A1/A2: fresh home first run (hint once, JSON clean), `auth login` targets the packaged default
T043 [P] A3: `auth status` precedence matrix via subprocess
T044 [P] A4: owned-checkout lane move publishes exactly one moment, attrs identical to the worktree case
T045 [P] A5/A6: unauthenticated full cycle observes zero requests; `auth logout` restores zero
T046 [P] A7/A8: tracker logged out gives guidance; retired names and `[sync]` have no effect
T047 Run `tests/architectural/` in full and `make test-fast`; record counts in the Activity Log

### Implementation Notes

- Isolated `SPEC_KITTY_HOME` per test; pty for the interactive hint case; never touch the developer's real home.

### Parallel Opportunities

- T043–T046 after T041.

### Dependencies

- Depends on WP08.

### Risks & Mitigations

- Windows: the subprocess tests carry `git_repo`/platform markers consistent with `tests/integration/`.

---

## Work Package WP10: Tracker hygiene and issue matrix (Priority: P2)

**Goal**: The mission's issue matrix and tracker comments make every claimed issue traceable.
**Independent Test**: `issue-matrix.json` has a row per claimed issue with a verdict and evidence ref; each issue carries a claim comment naming the mission.
**Prompt**: `/tasks/WP10-tracker-hygiene-issue-matrix.md`
**Requirement Refs**: C-006

### Included Subtasks

T048 Create `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json` with rows for #1621, #3980, #2875, #2695 (closing) and #3154, #3892, #3277 (referenced)
T049 Claim comments and assignments on GitHub naming the mission; verdicts filled from WP09 evidence
T050 Append the tracer files (`traces/`) with implementation friction and decisions

### Implementation Notes

- Planning-artifact WP; no source changes.

### Parallel Opportunities

- T049 can start once WP09 evidence exists.

### Dependencies

- Depends on WP09.

### Risks & Mitigations

- Never close issues from the PR body with `Fixes` until the acceptance evidence is in the matrix.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03; WP05 and WP06 in parallel from the start; WP04 after WP02+WP05+WP06; WP07 after WP05; WP08 after WP03+WP04+WP07; WP09 after WP08; WP10 after WP09.
- **Parallelization**: three lanes open immediately (WP01→WP02→WP03, WP05→WP07, WP06); WP04 joins them; WP08/WP09/WP10 are the integration tail.
- **MVP Scope**: WP01–WP03 (a launch build signs in with no configuration and shows where it points).

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01, WP02 |
| FR-002 | WP02 |
| FR-003 | WP02 |
| FR-004 | WP03 |
| FR-005 | WP06 |
| FR-006 | WP06 |
| FR-007 | WP05 |
| FR-008 | WP05 |
| FR-009 | WP04 |
| FR-010 | WP09 |
| FR-011 | WP05, WP07 |
| FR-012 | WP02, WP04 |
| FR-013 | WP04, WP06 |
| FR-014 | WP07 |
| NFR-001 | WP09 |
| NFR-002 | WP09 |
| NFR-003 | WP06 |
| NFR-004 | WP03 |
| NFR-005 | WP09 |
| C-001 | WP02, WP04 |
| C-002 | WP05, WP07, WP08 |
| C-003 | WP08 |
| C-004 | WP09 |
| C-005 | WP01 |
| C-006 | WP10 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Write the D-5 reversal ADR | WP01 | P0 | No |
| T002 | Register the ADR | WP01 | P0 | No |
| T003 | Supersede launch-readiness-future page | WP01 | P0 | Yes |
| T004 | Docs gates | WP01 | P0 | No |
| T005 | Resolver red-first tests | WP02 | P1 | No |
| T006 | auth/config.py default | WP02 | P1 | No |
| T007 | server_target.py resolution | WP02 | P1 | No |
| T008 | saas_readiness gate removal | WP02 | P1 | Yes |
| T009 | saas_client/auth + integration tests | WP02 | P1 | Yes |
| T010 | Visibility red-first tests | WP03 | P1 | No |
| T011 | Printer provenance | WP03 | P1 | No |
| T012 | auth login prints target | WP03 | P1 | No |
| T013 | JSON target fields + redaction | WP03 | P1 | Yes |
| T014 | auth-whoami-output doc | WP03 | P1 | Yes |
| T015 | Tracker/from-ticket red-first | WP04 | P1 | No |
| T016 | Remove tracker and from-ticket gates | WP04 | P1 | No |
| T017 | Delete gate module and re-export | WP04 | P1 | No |
| T018 | Conftest flag arming removed; arch guard | WP04 | P1 | Yes |
| T019 | grep witness + blast radius | WP04 | P1 | No |
| T020 | Opt-out and owned-checkout red-first | WP05 | P1 | No |
| T021 | env.py accessors | WP05 | P1 | No |
| T022 | adapters import gate | WP05 | P1 | Yes |
| T023 | Delete owned refusal; re-key gate opt-out | WP05 | P1 | No |
| T024 | Help text and agent fixtures | WP05 | P1 | Yes |
| T025 | Implement-review skill docs | WP05 | P1 | Yes |
| T026 | Readiness red-first | WP06 | P1 | No |
| T027 | hint_state module | WP06 | P1 | No |
| T028 | Coordinator always on + hint | WP06 | P1 | No |
| T029 | Render hint | WP06 | P1 | Yes |
| T030 | Logout reset; helpers cleanup | WP06 | P1 | Yes |
| T031 | Registry red-first | WP07 | P2 | No |
| T032 | Provisioning var lists | WP07 | P2 | No |
| T033 | Redaction + completion | WP07 | P2 | Yes |
| T034 | environment-variables.md | WP07 | P2 | Yes |
| T035 | ci-windows.yml | WP07 | P2 | Yes |
| T036 | Skills and source comments | WP08 | P2 | Yes |
| T037 | Docs pages + context + changelog | WP08 | P2 | Yes |
| T038 | Remaining test fixtures | WP08 | P2 | Yes |
| T039 | Docs index regen | WP08 | P2 | No |
| T040 | A10 witness | WP08 | P2 | No |
| T041 | Recording stubs | WP09 | P1 | No |
| T042 | A1/A2 first run + login | WP09 | P1 | No |
| T043 | A3 matrix | WP09 | P1 | Yes |
| T044 | A4 owned checkout moment | WP09 | P1 | Yes |
| T045 | A5/A6 zero egress | WP09 | P1 | Yes |
| T046 | A7/A8 guidance + retired names | WP09 | P1 | Yes |
| T047 | Full gates + test-fast | WP09 | P1 | No |
| T048 | issue-matrix.json | WP10 | P2 | No |
| T049 | Claims and assignments | WP10 | P2 | Yes |
| T050 | Tracer files | WP10 | P2 | Yes |
