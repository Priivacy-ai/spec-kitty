# Tasks: Mission Terminology Cleanup and Machine-Facing Alignment

**Mission Slug**: `077-mission-terminology-cleanup`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Branch contract**: planning on `main`, merge target `main`, `branch_matches_target=true`
**Generated**: 2026-04-08

## Overview

This mission has **two scopes** that must be sequenced (per spec §2 + C-004):

- **Scope A** (`#241` — immediate): WP01-WP10. Operator-facing CLI selector cleanup, doctrine skills, agent-facing docs, top-level project docs, migration docs, and CI grep guards. Must be fully accepted before Scope B begins.
- **Scope B** (`#543` — gated follow-on): WP11-WP13. Machine-facing contract alignment cleanup. **Cannot be merged until WP10 (Scope A acceptance gate) is green on `main`.**

Total: **13 work packages**, **60 subtasks**.

## Sequencing and Parallelization

### Dependency Tree

```
WP01 (audit)
  ├── WP02 (helper) ───┬── WP03 (mission current)
  │                    ├── WP04 (next_cmd + agent/tasks)
  │                    ├── WP05 (inverse drift)
  │                    └── WP09 (grep guards)
  ├── WP06 (doctrine skills)
  ├── WP07 (docs + top-level files)
  └── WP08 (migration docs)
                            ↓
                          WP10 (Scope A acceptance gate)
                            ↓
                          WP11 (Scope B inventory)
                            ↓
                          WP12 (Scope B field rollout)
                            ↓
                          WP13 (Scope B alignment + acceptance)
```

### Parallel Opportunities

After **WP01** lands:
- **WP02, WP06, WP07, WP08** can start immediately (different ownership; no shared files)

After **WP02** lands:
- **WP03, WP04, WP05** can start in parallel (each owns different command files; all consume the same helper)
- **WP09** can start (grep guards verify against canonical state, which now exists)

**WP10** is a sequential gate — it consumes all of WP03..WP09 and produces the acceptance evidence.

**Scope B (WP11-WP13)** is hard-gated on WP10. Do not start any Scope B WP before WP10 is accepted on `main`.

### MVP Scope Recommendation

The minimum viable scope for `#241` is **WP01 + WP02 + WP03**. After those three:
- The verified dual-flag bug in `mission current` is fixed
- The selector-resolution helper exists and is fully tested
- One end-to-end command demonstrates the canonical pattern

This MVP would not satisfy spec §10.1 acceptance (which requires WP04..WP10 too), but it's enough to demo the architectural fix and unblock review feedback. Recommended for the first PR if time-pressured.

---

## Subtask Index

| ID | Description | WP | Parallel | Status |
|---|---|---|---|---|
| T001 | Inventory tracked-mission selector sites in `src/specify_cli/cli/commands/**` | WP01 |  | [D] |
| T002 | Inventory inverse-drift sites where `--mission` means blueprint/template | WP01 | [P] | [D] |
| T003 | Cross-reference helper consumers and `require_explicit_feature` callers | WP01 | [P] | [D] |
| T004 | Produce canonical map document (research artifact) | WP01 |  | [D] |
| T005 | Create `selector_resolution.py` module shell with `SelectorResolution` dataclass | WP02 |  | [D] |
| T006 | Implement `_emit_deprecation_warning` sub-helper with single-warning guarantee | WP02 |  | [D] |
| T007 | Implement `resolve_selector` public function with conflict detection | WP02 |  | [D] |
| T008 | Wire suppression env vars for both directions | WP02 |  | [D] |
| T009 | Create `test_selector_resolution.py` with 12 unit test cases | WP02 |  | [D] |
| T010 | Verify mypy --strict + ≥90% coverage | WP02 |  | [D] |
| T011 | Refactor `mission.py:172-194` (`mission current`) — split into two parameters | WP03 |  | [D] |
| T012 | Wire `mission current` through `resolve_selector` | WP03 |  | [D] |
| T013 | Add 6 integration tests for `mission current` (canonical/alias/conflict cases) | WP03 |  | [D] |
| T014 | Manually reproduce verified dual-flag bug → confirm fixed | WP03 |  | [D] |
| T015 | Refactor `next_cmd.py:33` (drop `--mission-run`/`--feature` aliases, add hidden) | WP04 | [P] | [D] |
| T016 | Update `next_cmd.py:48` example help text | WP04 | [P] | [D] |
| T017 | Refactor `agent/tasks.py` 9 selector sites (lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659) | WP04 |  | [D] |
| T018 | Replace "Mission run slug" help text with "Mission slug" across these files | WP04 |  | [D] |
| T019 | Add integration tests for representative `next_cmd` and `agent/tasks` commands | WP04 |  | [D] |
| T020 | Refactor `agent/mission.py:488` (`agent mission create` — `--mission` → `--mission-type`) | WP05 | [P] | [D] |
| T021 | Refactor `charter.py:67` (`charter interview`) | WP05 | [P] | [D] |
| T022 | Refactor `lifecycle.py:27` (`lifecycle.specify`) | WP05 | [P] | [D] |
| T023 | Add 9 integration tests (3 sites × canonical/alias/conflict) | WP05 |  | [D] |
| T024 | Verify `--mission` help text on these sites references the deprecation | WP05 |  | [D] |
| T025 | Update `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` | WP06 |  | [D] |
| T026 | Audit other doctrine skills under `src/doctrine/skills/**` for similar drift | WP06 |  | [D] |
| T027 | Update any drifted doctrine skills found | WP06 |  | [D] |
| T028 | Update `docs/explanation/runtime-loop.md` — drop legacy selector teaching | WP07 | [P] | [D] |
| T029 | Audit `docs/explanation/**`, `docs/reference/**`, `docs/tutorials/**` and fix drift | WP07 |  | [D] |
| T030 | Clean up `README.md:883` (legacy `--feature` example block) | WP07 | [P] | [D] |
| T031 | Clean up `README.md:910` (`--feature` row in `spec-kitty accept` Options table) | WP07 | [P] | [D] |
| T032 | Audit `CONTRIBUTING.md` and `CHANGELOG.md` Unreleased section | WP07 | [P] | [D] |
| T033 | Create `docs/migration/feature-flag-deprecation.md` | WP08 | [P] | [D] |
| T034 | Create `docs/migration/mission-type-flag-deprecation.md` | WP08 | [P] | [D] |
| T035 | Verify deprecation warning paths in `selector_resolution.py` match the new doc paths | WP08 |  | [D] |
| T036 | Create `tests/contract/test_terminology_guards.py` shell with helpers | WP09 |  | [D] |
| T037 | Implement guards 1-3 (CLI command file checks) | WP09 | [P] | [D] |
| T038 | Implement guards 4-5 (doctrine skills + agent-facing docs checks) | WP09 | [P] | [D] |
| T039 | Implement guard 5b (top-level project docs) + guard 6 (inverse drift) | WP09 | [P] | [D] |
| T040 | Implement guards 7-8 (orchestrator-api envelope + meta-guard for historical-artifact safety) | WP09 | [P] | [D] |
| T041 | Run all 9 guards against current state and verify pass/fail behavior | WP09 |  | [D] |
| T042 | Edit spec.md §11.1 — change "deprecated compatibility alias" → "hidden deprecated compatibility alias" | WP10 |  | [D] |
| T043 | Run all 15 acceptance gates from spec §10.1 | WP10 |  | [D] |
| T044 | Verify orchestrator-api files unchanged (read-only check) | WP10 |  | [D] |
| T045 | Verify no historical artifacts modified (C-011 check) | WP10 |  | [D] |
| T046 | Capture acceptance evidence and document Scope A completion | WP10 |  | [D] |
| T047 | Inventory first-party machine-facing surfaces emitting tracked-mission identity | WP11 |  | [D] |
| T048 | Identify residual `feature_*` fields in payloads | WP11 |  | [D] |
| T049 | Cross-reference findings with `upstream_contract.json` | WP11 |  | [D] |
| T050 | Produce Scope B alignment plan (research artifact) | WP11 |  | [D] |
| T051 | Ensure `mission_slug`/`mission_number`/`mission_type` present in first-party payloads | WP12 |  | [D] |
| T052 | For each residual `feature_*` field, decide remove/dual-write/deprecate and execute | WP12 |  | [D] |
| T053 | Add contract tests asserting canonical fields are present | WP12 |  | [D] |
| T054 | Add contract test that fails if `mission_run_slug` is introduced (FR-019) | WP12 |  | [D] |
| T055 | Verify `MissionCreated`/`MissionClosed` event names unchanged (FR-017) | WP12 |  | [D] |
| T056 | Verify `aggregate_type="Mission"` unchanged (locked non-goal §3.3) | WP12 |  | [D] |
| T057 | Update `docs/reference/event-envelope.md` and `docs/reference/orchestrator-api.md` | WP13 | [P] | [D] |
| T058 | Run cross-repo first-party consumer fixtures and verify NFR-006 (zero breakages) | WP13 |  | [D] |
| T059 | Run all spec §10.2 acceptance criteria and capture evidence | WP13 |  | [D] |
| T060 | Document Scope B completion and close `#543` | WP13 |  | [D] |

The `[P]` marker in this index indicates parallelizable subtasks within a WP. It is **not** a status marker — `mark-status` tracks status via the per-WP checkbox rows below, not via this index.

---

## Phase 1: Setup

### WP01 — Selector Audit and Canonical Map

**Prompt**: [`tasks/WP01-selector-audit-and-canonical-map.md`](tasks/WP01-selector-audit-and-canonical-map.md)

**Goal**: Produce a complete inventory of every tracked-mission selector site and every inverse-drift site (where `--mission` semantically means "blueprint/template selector") in `src/specify_cli/cli/commands/**`. Output is the canonical input to WP02-WP05.

**Priority**: P0 (gate for everything else in Scope A).

**Independent test**: A reviewer can read the audit document and pick any random CLI command file in `src/specify_cli/cli/commands/**` and find that file's classification (tracked-mission / inverse-drift / runtime-session / N/A) and target alias list in the audit.

**Estimated prompt size**: ~250 lines.

**Dependencies**: none.

**Included subtasks**:
- [x] T001 Inventory tracked-mission selector sites in `src/specify_cli/cli/commands/**` (WP01)
- [x] T002 Inventory inverse-drift sites where `--mission` means blueprint/template (WP01)
- [x] T003 Cross-reference helper consumers and `require_explicit_feature` callers (WP01)
- [x] T004 Produce canonical map document (research artifact) (WP01)

**Implementation sketch**:
1. Use `Grep` over `src/specify_cli/cli/commands/**/*.py` for `typer.Option` declarations that mention `--mission`, `--feature`, or `--mission-run`.
2. Classify each site by reading its `help=` string and the surrounding parameter context: tracked-mission (slug), inverse-drift (mission type), runtime-session (run id), or unrelated.
3. Cross-reference with `require_explicit_feature` callers (27 known files) to confirm which sites the helper feeds.
4. Write the audit to `kitty-specs/077-mission-terminology-cleanup/research/selector-audit.md` with one row per site.

**Risks**: A site could be misclassified by reading help text alone — verify at least one runtime path per ambiguous site by reading the function body. If a site uses `--mission-run` and the function legitimately resolves a `mission_run_id` from runtime state, classify as runtime-session and exclude from refactor scope.

---

## Phase 2: Foundation

### WP02 — Selector Resolution Helper

**Prompt**: [`tasks/WP02-selector-resolution-helper.md`](tasks/WP02-selector-resolution-helper.md)

**Goal**: Implement `src/specify_cli/cli/selector_resolution.py` per `contracts/selector_resolver.md`. This is the central enforcement point for FR-006, FR-007, FR-021, NFR-002, NFR-003.

**Priority**: P0 (consumed by WP03, WP04, WP05, WP09).

**Independent test**: All 12 unit tests in `test_selector_resolution.py` pass; mypy --strict is clean on the new module; coverage on the new module is ≥ 90% (target: 100%).

**Estimated prompt size**: ~450 lines.

**Dependencies**: WP01 (audit informs which call sites will consume the helper).

**Included subtasks**:
- [x] T005 Create `selector_resolution.py` module shell with `SelectorResolution` dataclass (WP02)
- [x] T006 Implement `_emit_deprecation_warning` sub-helper with single-warning guarantee (WP02)
- [x] T007 Implement `resolve_selector` public function with conflict detection (WP02)
- [x] T008 Wire suppression env vars for both directions (WP02)
- [x] T009 Create `test_selector_resolution.py` with 12 unit test cases (WP02)
- [x] T010 Verify mypy --strict + ≥90% coverage (WP02)

**Implementation sketch**: Follow `data-model.md` and `contracts/selector_resolver.md` exactly. The whole module is ~80 lines. Test cases come from `contracts/selector_resolver.md` §"Required Test Coverage" (cases 1-12 are the unit tests).

**Risks**: If the module-level `_warned: set` is not reset between tests via the `autouse` fixture from `data-model.md`, CI will be flaky. Install the fixture in the test file from the start.

---

## Phase 3: Tracked-Mission Selector Refactor (Story 1)

### WP03 — `mission current` Refactor and Dual-Flag Bug Fix

**Prompt**: [`tasks/WP03-mission-current-refactor.md`](tasks/WP03-mission-current-refactor.md)

**Goal**: Fix the verified dual-flag bug in `mission current` (spec §8.2). Refactor `src/specify_cli/cli/commands/mission.py:172-194` to declare `--mission` and `--feature` as separate parameters and route through `resolve_selector`. This is the canonical end-to-end demonstration of the new pattern.

**Priority**: P0 (the verified bug fix).

**Independent test**: `spec-kitty mission current --mission A --feature B` (different values) exits non-zero with the deterministic conflict error. The pre-refactor command silently resolved to B; the post-refactor command must fail loudly. Asserted by an integration test.

**Estimated prompt size**: ~300 lines.

**Dependencies**: WP02.

**Included subtasks**:
- [x] T011 Refactor `mission.py:172-194` (`mission current`) — split into two parameters (WP03)
- [x] T012 Wire `mission current` through `resolve_selector` (WP03)
- [x] T013 Add 6 integration tests for `mission current` (canonical/alias/conflict cases) (WP03)
- [x] T014 Manually reproduce verified dual-flag bug → confirm fixed (WP03)

**Implementation sketch**: Follow the "Tracked-Mission Command" pattern in `contracts/selector_resolver.md` §"Call-Site Pattern". Use `quickstart.md` Step 3 as the line-by-line guide.

**Risks**: This file has other commands besides `mission current` — touch only the `current_cmd` function. The deprecated `switch` command at line 273 already has `deprecated=True` and is unchanged.

---

### WP04 — `next_cmd.py` and `agent/tasks.py` Selector Refactor

**Prompt**: [`tasks/WP04-next-cmd-and-agent-tasks-refactor.md`](tasks/WP04-next-cmd-and-agent-tasks-refactor.md)

**Goal**: Refactor every tracked-mission selector site in `next_cmd.py` and `agent/tasks.py` to use `--mission` as canonical, drop `--mission-run` from tracked-mission alias lists entirely, and add hidden `--feature` aliases routed through `resolve_selector`.

**Priority**: P0 (the bulk of the operator-facing drift).

**Independent test**: `rg --type py "(--mission-run|--feature)" src/specify_cli/cli/commands/next_cmd.py src/specify_cli/cli/commands/agent/tasks.py | grep -v "hidden=True"` returns zero matches; all integration tests for these commands pass.

**Estimated prompt size**: ~500 lines.

**Dependencies**: WP02.

**Included subtasks**:
- [x] T015 Refactor `next_cmd.py:33` (drop `--mission-run`/`--feature` aliases, add hidden) (WP04)
- [x] T016 Update `next_cmd.py:48` example help text (WP04)
- [x] T017 Refactor `agent/tasks.py` 9 selector sites (lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659) (WP04)
- [x] T018 Replace "Mission run slug" help text with "Mission slug" across these files (WP04)
- [x] T019 Add integration tests for representative `next_cmd` and `agent/tasks` commands (WP04)

**Implementation sketch**: Apply the same pattern from WP03 to each site. The 9 sites in `agent/tasks.py` are mechanical; do them in one focused pass. Update help strings together.

**Risks**: Some `agent/tasks.py` sites may have additional aliases beyond `--mission-run`. The WP01 audit must have classified each one — refer to `research/selector-audit.md` for the per-site target shape.

---

### WP05 — Inverse Drift Refactor (`--mission` → `--mission-type`)

**Prompt**: [`tasks/WP05-inverse-drift-refactor.md`](tasks/WP05-inverse-drift-refactor.md)

**Goal**: Convert the three verified inverse-drift sites to use `--mission-type` as canonical with `--mission` retained as a hidden deprecated alias. Asymmetric direction of the same `resolve_selector` helper.

**Priority**: P0 (FR-021, the inverse drift fix).

**Independent test**: `agent mission create new-thing --mission-type software-dev --mission research` (different values) exits non-zero with conflict error; `agent mission create new-thing --mission-type software-dev` succeeds without warning; `agent mission create new-thing --mission software-dev` succeeds with one yellow stderr deprecation warning.

**Estimated prompt size**: ~400 lines.

**Dependencies**: WP02.

**Included subtasks**:
- [x] T020 Refactor `agent/mission.py:488` (`agent mission create` — `--mission` → `--mission-type`) (WP05)
- [x] T021 Refactor `charter.py:67` (`charter interview`) (WP05)
- [x] T022 Refactor `lifecycle.py:27` (`lifecycle.specify`) (WP05)
- [x] T023 Add 9 integration tests (3 sites × canonical/alias/conflict) (WP05)
- [x] T024 Verify `--mission` help text on these sites references the deprecation (WP05)

**Implementation sketch**: Follow the "Inverse-Drift Command" pattern in `contracts/selector_resolver.md` §"Call-Site Pattern". Use `quickstart.md` Step 5 as the line-by-line guide.

**Risks**: `charter interview` has a default value of `"software-dev"` for the parameter. After the rename, the default lives on `--mission-type`, not on `--mission`. Make sure the default is preserved in the canonical parameter, not the alias.

---

## Phase 4: Doctrine, Docs, and Migration

### WP06 — Doctrine Skills Cleanup

**Prompt**: [`tasks/WP06-doctrine-skills-cleanup.md`](tasks/WP06-doctrine-skills-cleanup.md)

**Goal**: Update every live doctrine skill that teaches `--mission-run` for tracked-mission selection to use `--mission`. Verified primary site: `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`. Audit other skills for similar drift.

**Priority**: P0 (FR-009).

**Independent test**: `grep -rn "mission-run" src/doctrine/skills/ | grep -v "runtime\|session"` returns zero matches.

**Estimated prompt size**: ~250 lines.

**Dependencies**: WP01.

**Included subtasks**:
- [x] T025 Update `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (WP06)
- [x] T026 Audit other doctrine skills under `src/doctrine/skills/**` for similar drift (WP06)
- [x] T027 Update any drifted doctrine skills found (WP06)

**Implementation sketch**: Read `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`, find every mention of `--mission-run` for tracked-mission selection, replace with `--mission`. Then grep `src/doctrine/skills/**` for similar patterns and fix any matches.

**Risks**: A doctrine skill may legitimately mention `--mission-run` in a runtime/session context. Distinguish by reading the surrounding sentence: if it says "to select a runtime session" or "to look up an execution instance", leave it; if it says "to pick a tracked mission" or "to operate on `kitty-specs/<slug>/`", change it.

---

### WP07 — Agent-Facing Docs and Top-Level Project Docs Cleanup

**Prompt**: [`tasks/WP07-docs-and-top-level-cleanup.md`](tasks/WP07-docs-and-top-level-cleanup.md)

**Goal**: Update every live `docs/**` file and the top-level project files (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` Unreleased section) that teach legacy selectors. Verified drift sites at `README.md:883` (legacy `--feature` example block) and `README.md:910` (`--feature` documented in the `spec-kitty accept` Options table).

**Priority**: P0 (FR-010, FR-022).

**Independent test**: `grep -n "mission-run\|--feature" README.md CONTRIBUTING.md` returns zero matches; the `awk` Unreleased-section check on `CHANGELOG.md` returns zero matches; live `docs/**` files (excluding `docs/migration/**`) return zero matches.

**Estimated prompt size**: ~400 lines.

**Dependencies**: WP01.

**Included subtasks**:
- [x] T028 Update `docs/explanation/runtime-loop.md` — drop legacy selector teaching (WP07)
- [x] T029 Audit `docs/explanation/**`, `docs/reference/**`, `docs/tutorials/**` and fix drift (WP07)
- [x] T030 Clean up `README.md:883` (legacy `--feature` example block) (WP07)
- [x] T031 Clean up `README.md:910` (`--feature` row in `spec-kitty accept` Options table) (WP07)
- [x] T032 Audit `CONTRIBUTING.md` and `CHANGELOG.md` Unreleased section (WP07)

**Implementation sketch**: Use `quickstart.md` Step 7a/7b as the line-by-line guide. **Critical**: do not scan or modify `kitty-specs/**` or `architecture/**` (C-011). For `CHANGELOG.md`, only the Unreleased section above the first `## [<version>]` heading is in scope.

**Risks**: README.md is large (~900+ lines). Use targeted edits for the verified drift sites; do not rewrite sections unrelated to selector vocabulary.

---

### WP08 — Migration Policy Documentation

**Prompt**: [`tasks/WP08-migration-docs.md`](tasks/WP08-migration-docs.md)

**Goal**: Create the two migration doc files referenced from the deprecation warnings emitted by `selector_resolution.py`. These docs are the link target in the warning message and must explain the deprecation, removal criteria, and suppression env vars.

**Priority**: P1 (FR-013, NFR-002, NFR-003 — referenced from runtime warnings).

**Independent test**: `docs/migration/feature-flag-deprecation.md` and `docs/migration/mission-type-flag-deprecation.md` both exist and contain: (a) link to the spec, (b) link to the ADR, (c) named removal criteria, (d) suppression env var name, (e) example migration commands.

**Estimated prompt size**: ~300 lines.

**Dependencies**: WP01.

**Included subtasks**:
- [x] T033 Create `docs/migration/feature-flag-deprecation.md` (WP08)
- [x] T034 Create `docs/migration/mission-type-flag-deprecation.md` (WP08)
- [x] T035 Verify deprecation warning paths in `selector_resolution.py` match the new doc paths (WP08)

**Implementation sketch**: Both docs follow the same structure (problem → why → migration commands → suppression → removal criteria). Cross-link to spec.md, ADR, and the initiative README.

**Risks**: If WP02 is already complete and the warning text references a doc path that doesn't match the file actually created here, the warning text will dangle. T035 reconciles this. If WP02 has not yet committed the warning text, coordinate the path strings.

---

## Phase 5: Verification and Acceptance

### WP09 — CI Grep Guards

**Prompt**: [`tasks/WP09-grep-guards.md`](tasks/WP09-grep-guards.md)

**Goal**: Implement `tests/contract/test_terminology_guards.py` per `contracts/grep_guards.md`. Nine guard test functions that prevent the canonical drift from returning, scoped to live first-party surfaces only (FR-022).

**Priority**: P0 (FR-022, NFR-005, prevents regression).

**Independent test**: All 9 guards pass after WP02-WP08 are complete; the meta-guard (Guard 8) confirms no historical artifacts are scanned; the envelope-width guard (Guard 7) confirms the orchestrator-api envelope is unchanged.

**Estimated prompt size**: ~450 lines.

**Dependencies**: WP02 (helper must exist for guard 3 to verify against canonical state).

**Included subtasks**:
- [x] T036 Create `tests/contract/test_terminology_guards.py` shell with helpers (WP09)
- [x] T037 Implement guards 1-3 (CLI command file checks) (WP09)
- [x] T038 Implement guards 4-5 (doctrine skills + agent-facing docs checks) (WP09)
- [x] T039 Implement guard 5b (top-level project docs) + guard 6 (inverse drift) (WP09)
- [x] T040 Implement guards 7-8 (orchestrator-api envelope + meta-guard for historical-artifact safety) (WP09)
- [x] T041 Run all 9 guards against current state and verify pass/fail behavior (WP09)

**Implementation sketch**: Follow `contracts/grep_guards.md` exactly. Use the `_extract_changelog_unreleased` helper for the CHANGELOG check. Guard 7 must use the actual envelope keys: `contract_version`, `command`, `timestamp`, `correlation_id`, `success`, `error_code`, `data` (verified at HEAD `35d43a25`).

**Risks**: A guard that's too aggressive will fail on legitimate runtime/session usages. Test each guard against the current state of the codebase before declaring it ready — guards 1, 4, 5 must allow runtime/session contexts.

---

### WP10 — Charter Reconciliation Spec Edit and Scope A Acceptance Gate

**Prompt**: [`tasks/WP10-scope-a-acceptance-gate.md`](tasks/WP10-scope-a-acceptance-gate.md)

**Goal**: Make the one-line charter-reconciliation edit to spec §11.1 (the only spec change in this mission), then run all 15 acceptance gates from spec §10.1 and capture evidence. This is the gate for Scope B.

**Priority**: P0 (Scope A acceptance).

**Independent test**: All 15 acceptance gates from spec §10.1 are green and documented with evidence in this WP's completion report. The gate is mechanically verifiable.

**Estimated prompt size**: ~350 lines.

**Dependencies**: WP03, WP04, WP05, WP06, WP07, WP08, WP09 (everything else in Scope A).

**Included subtasks**:
- [x] T042 Edit spec.md §11.1 — change "deprecated compatibility alias" → "hidden deprecated compatibility alias" (WP10)
- [x] T043 Run all 15 acceptance gates from spec §10.1 (WP10)
- [x] T044 Verify orchestrator-api files unchanged (read-only check) (WP10)
- [x] T045 Verify no historical artifacts modified (C-011 check) (WP10)
- [x] T046 Capture acceptance evidence and document Scope A completion (WP10)

**Implementation sketch**: The spec edit is one line (and one short clarification phrase). The acceptance gates are listed in spec §10.1; each one is a mechanical check (grep, file existence, test pass, etc.). Capture evidence as a markdown report in `kitty-specs/077-mission-terminology-cleanup/research/scope-a-acceptance.md`.

**Risks**: If any gate fails, do not modify the gate — fix the underlying issue and re-run. The gates are the contract.

---

## Phase 6: Scope B (Gated Follow-On)

> **Important**: WP11-WP13 are gated on WP10 acceptance per spec §2 + C-004. They may be planned in parallel with Scope A but **must not be merged** until Scope A is accepted on `main`.

### WP11 — Machine-Facing Inventory

**Prompt**: [`tasks/WP11-machine-facing-inventory.md`](tasks/WP11-machine-facing-inventory.md)

**Goal**: Inventory every first-party machine-facing surface that emits or accepts tracked-mission identity. Identify residual `feature_*` payload fields. Cross-reference with `upstream_contract.json`. Output is a research artifact that informs WP12 and WP13.

**Priority**: P1 (Scope B start).

**Independent test**: A reviewer can read the inventory and identify every first-party surface where (a) `mission_slug` is canonical, (b) a residual `feature_*` field exists, or (c) alignment with `spec-kitty-events 3.0.0` is incomplete.

**Estimated prompt size**: ~250 lines.

**Dependencies**: WP10 (Scope B is gated).

**Included subtasks**:
- [x] T047 Inventory first-party machine-facing surfaces emitting tracked-mission identity (WP11)
- [x] T048 Identify residual `feature_*` fields in payloads (WP11)
- [x] T049 Cross-reference findings with `upstream_contract.json` (WP11)
- [x] T050 Produce Scope B alignment plan (research artifact) (WP11)

---

### WP12 — Canonical Field Rollout and `feature_*` Compat Gating

**Prompt**: [`tasks/WP12-canonical-field-rollout.md`](tasks/WP12-canonical-field-rollout.md)

**Goal**: For every first-party machine-facing payload identified in WP11, ensure `mission_slug`, `mission_number`, and `mission_type` are canonical. For each residual `feature_*` field, decide remove / dual-write / deprecate and execute. Add contract tests that lock the canonical state.

**Priority**: P1 (Scope B core).

**Independent test**: All FR-014..FR-020 acceptance criteria from spec §10.2 are green; no first-party payload introduces `mission_run_slug`; `MissionCreated`/`MissionClosed` event names are unchanged.

**Estimated prompt size**: ~450 lines.

**Dependencies**: WP11.

**Included subtasks**:
- [x] T051 Ensure `mission_slug`/`mission_number`/`mission_type` present in first-party payloads (WP12)
- [x] T052 For each residual `feature_*` field, decide remove/dual-write/deprecate and execute (WP12)
- [x] T053 Add contract tests asserting canonical fields are present (WP12)
- [x] T054 Add contract test that fails if `mission_run_slug` is introduced (FR-019) (WP12)
- [x] T055 Verify `MissionCreated`/`MissionClosed` event names unchanged (FR-017) (WP12)
- [x] T056 Verify `aggregate_type="Mission"` unchanged (locked non-goal §3.3) (WP12)

---

### WP13 — Contract Docs Alignment and Scope B Acceptance Gate

**Prompt**: [`tasks/WP13-scope-b-acceptance-gate.md`](tasks/WP13-scope-b-acceptance-gate.md)

**Goal**: Update first-party machine-facing contract docs (`docs/reference/event-envelope.md`, `docs/reference/orchestrator-api.md`) to align with `spec-kitty-events 3.0.0` and the alias window. Run cross-repo first-party consumer fixtures. Run all spec §10.2 acceptance criteria. Close `#543`.

**Priority**: P1 (Scope B acceptance).

**Independent test**: All 9 acceptance gates from spec §10.2 are green; cross-repo consumer fixtures show 0 breakages; `#543` can be closed.

**Estimated prompt size**: ~300 lines.

**Dependencies**: WP12.

**Included subtasks**:
- [x] T057 Update `docs/reference/event-envelope.md` and `docs/reference/orchestrator-api.md` (WP13)
- [x] T058 Run cross-repo first-party consumer fixtures and verify NFR-006 (zero breakages) (WP13)
- [x] T059 Run all spec §10.2 acceptance criteria and capture evidence (WP13)
- [x] T060 Document Scope B completion and close `#543` (WP13)

---

## Risks Summary (Cross-WP)

| Risk | Mitigation |
|---|---|
| Multi-alias `Option` declarations are reintroduced in a future PR | Guard 3 in WP09 fails the build on visible (non-`hidden=True`) `--feature` declarations |
| Doctrine skills accidentally re-teach `--mission-run` for tracked-mission selection | Guard 4 in WP09 |
| Top-level README.md regresses with new `--feature` examples | Guard 5b in WP09 (new) |
| Orchestrator-api envelope is widened by a future mission | Guard 7 in WP09 (corrected to use actual envelope keys) |
| Historical artifacts under `kitty-specs/**` are accidentally modified | Guard 8 (meta-guard) + reviewer checklist |
| The single-warning guarantee fails under test parallelism | `_reset_selector_resolution_state` autouse fixture (WP02) |
| Scope B starts before Scope A is accepted | Hard dependency in WP11 frontmatter; dependency tree enforced by `lanes.json` after `finalize-tasks` |
| Migration doc paths in selector_resolution.py drift from actual files | T035 in WP08 reconciles |

---

## Definition of Done (Mission Level)

This mission is complete when:

1. All 60 subtasks across 13 WPs are checked off.
2. Spec §10.1 (Scope A) and §10.2 (Scope B) acceptance gates are all green.
3. The only spec change is the §11.1 charter-reconciliation edit from T042.
4. No file under `kitty-specs/**` other than `077-mission-terminology-cleanup/` is modified.
5. No file under `architecture/**` is modified.
6. The orchestrator-api envelope is unchanged.
7. CI is green on all touched modules.
8. All 9 grep guards in `tests/contract/test_terminology_guards.py` pass.
9. The PR description references `Priivacy-ai/spec-kitty#241` (and `#543` if Scope B is in the same PR sequence).
