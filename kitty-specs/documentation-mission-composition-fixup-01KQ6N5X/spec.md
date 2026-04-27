# Specification — Documentation Mission Composition Fix-up

**Mission ID**: `01KQ6N5X9EHGJPPMZN00X6EVX1`
**Mission slug**: `documentation-mission-composition-fixup-01KQ6N5X`
**Mission type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-27
**Predecessor**: mission `01KQ5M1Y190VANF39KMBWZP6SD` merged at commit `1c03e2f4`
**Source**: Phase 6 #502 fix-up. User review on the predecessor's mission-review commit surfaced 5 findings the AI-driven mission-review missed.

## Purpose

### TL;DR

Close the 5 review findings on #502 so the documentation mission is genuinely operator-runnable. The substrate (sidecar template, contracts, action bundles, DRG nodes, dispatch entry, guard branch) is correct and stays. This mission ships the missing prompt templates, deepens the integration walk to advance all 6 actions, replaces direct guard-helper unit assertions with dispatch-level blocked-decision assertions, fixes the quickstart's wrong JSON field, and re-runs the dogfood smoke so it actually issues a composed action with paired trail records.

### Findings being closed

Each finding was raised by user review on commit `1c03e2f4`. Cited file:line refs are at HEAD when the user filed.

- **F-1 [P1] Prompts not shipped**: `src/specify_cli/missions/documentation/mission-runtime.yaml:24-65` declares `prompt_template: <verb>.md` for each step, but no matching files ship under `src/specify_cli/missions/documentation/templates/`. The live `spec-kitty next` path resolves `f"{action}.md"` via `resolve_command(...)`; with the files absent, `_build_prompt_safe` returns `None` and every documentation step (discover, audit, design, generate, validate, publish, accept) returns `prompt_file=None` to the operator/host harness. The original plan called templates "advisory"; the user-observable behavior is broken without them.
- **F-2 [P1] Dogfood smoke never dispatched**: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke.md:108-136` records `kind: query` only — `step_id` is null, no invocation records were written. The predecessor spec's Scenario 6 / SC-006 / NFR-005 require *the same outcomes Scenario 1 asserts*, including StepContractExecutor dispatch and paired `started`/`done` trail records under `~/.kittify/events/profile-invocations/` with documentation-native action names. The PASS verdict on predecessor mission-review over-claimed this gate.
- **F-3 [P2] Integration walk advances only one action**: `tests/integration/test_documentation_runtime_walk.py:202-259` issues `discover` once, asserts `success`, and only checks the next preview is another documentation verb. It never advances `audit`, `design`, `generate`, `validate`, `publish` through dispatch. WP06 of the predecessor mission required driving every advancing action.
- **F-4 [P2] Guard tests bypass dispatch**: `tests/integration/test_documentation_runtime_walk.py:410-430` calls `_check_composed_action_guard()` directly. Predecessor SC-003 / FR-009 require `_dispatch_via_composition()` to propagate the failure as a structured blocked decision with no run-state advancement and no legacy-DAG fallback. The helper-level test does not prove that dispatch contract.
- **F-5 [P2] Quickstart KeyError**: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md:47-56` asserts `d["issued_step_id"]`, but the runtime `Decision` JSON schema uses `step_id` for issued steps and `preview_step` for the query path. Running the quickstart literally raises `KeyError` before reaching the trail check.

### Architecture boundary preserved

- C-001 (no host-LLM calls), C-002 (StepContractExecutor chokepoint), C-003 (no new shipped profile), C-005 (no edits to research/software-dev branches), C-007 (no mocks of forbidden symbols in the integration walk) — all inherited from the predecessor mission and remain in force.
- The legacy `mission.yaml` files stay coexistent with `mission-runtime.yaml` (D1 unchanged).
- DRG nodes/edges authored by predecessor WP04 stay untouched (`src/doctrine/graph.yaml`).

## User Scenarios & Testing

### Primary actor

A spec-kitty operator who runs `spec-kitty agent mission create demo-docs --mission-type documentation --json` then drives the mission via `spec-kitty next --agent <name> --mission <handle>`. After this fix-up, every issued step returns a non-null `prompt_file` and the operator's invocation trail records paired `started` + (`done` or `failed`) lifecycle entries with documentation-native action names.

### Acceptance Scenarios

**Scenario 1 — Every documentation step yields a runnable prompt**
- **Given** a fresh documentation mission
- **When** the runtime issues any of the 7 documentation steps (discover, audit, design, generate, validate, publish, accept)
- **Then** the returned `Decision.prompt_file` is non-null and points at an existing `*.md` file under `src/specify_cli/missions/documentation/templates/`
- **And** the file is non-empty markdown that can be read by the host LLM as the action prompt.

**Scenario 2 — Real dogfood smoke dispatches a composed action**
- **Given** a clean checkout and a separate temp repo outside the spec-kitty tree
- **When** the mission-review skill runs `uv --project <spec-kitty-repo> spec-kitty agent mission create demo-docs ... && spec-kitty next ...` and **issues** the discover step (not just queries)
- **Then** the runtime returns a `Decision` whose `kind` is `success` (not `query`)
- **And** paired `started` + `done` (or `failed`) records exist under `<temp_repo>/.kittify/events/profile-invocations/`
- **And** at least one record has `action` ∈ `{discover, audit, design, generate, validate, publish}`.

**Scenario 3 — Integration walk advances every action**
- **Given** a fresh documentation mission with happy-path artifacts authored
- **When** the integration walk issues each of the 6 documentation actions in sequence via `decide_next_via_runtime` (not direct helper calls)
- **Then** each issuance returns a non-blocked decision and run state advances
- **And** trail records cover all 6 documentation-native action names (one paired lifecycle per action).

**Scenario 4 — Missing artifacts produce dispatch-level blocked decisions**
- **Given** an empty documentation feature_dir
- **When** the runtime is asked to advance via `decide_next_via_runtime` (NOT via direct `_check_composed_action_guard()` calls)
- **Then** the returned decision is a structured blocked decision naming the missing artifact (e.g. `spec.md`)
- **And** run state does NOT advance (snapshot before/after equal)
- **And** the legacy-DAG fallback is NOT invoked.

**Scenario 5 — Quickstart runs end-to-end without KeyError**
- **Given** the merged code and a fresh temp repo
- **When** an operator copy-pastes `quickstart.md` verbatim
- **Then** every JSON field referenced in the quickstart actually exists on the wire (`step_id` for issued steps, `preview_step` for query mode, etc.)
- **And** the smoke runs to completion without a Python exception.

## Requirements

### Functional Requirements

| ID | Requirement | Status | Notes |
|---|---|---|---|
| FR-001 | 7 prompt templates MUST ship at `src/specify_cli/missions/documentation/templates/{discover,audit,design,generate,validate,publish,accept}.md`. Each MUST be non-empty governance/authorship prose suitable for the host LLM. | Required | Closes F-1. |
| FR-002 | For every documentation step, `_build_prompt_safe` (or its callers in the live `spec-kitty next` path) MUST return a non-null `prompt_file` pointing at the corresponding template under `src/specify_cli/missions/documentation/templates/`. | Required | Closes F-1; verification gate. |
| FR-003 | `tests/integration/test_documentation_runtime_walk.py` MUST include a test that drives a happy-path documentation mission through every one of the 6 composed actions via `decide_next_via_runtime` and asserts success on each. | Required | Closes F-3. |
| FR-004 | The trail-record assertion in the integration walk MUST verify a paired `started`/`done` lifecycle record for every advancing documentation action (not just one). | Required | Closes F-3. |
| FR-005 | The integration walk's missing-artifact test MUST assert via `decide_next_via_runtime` that the returned decision is a structured blocked decision (not by calling `_check_composed_action_guard()` directly). | Required | Closes F-4 / SC-003. |
| FR-006 | The integration walk's unknown-action test MAY remain at the helper level (since `decide_next_via_runtime` does not allow injecting an unknown action), but it MUST be supplemented by a dispatch-level test that simulates an unknown action via the runtime path if achievable, OR documented as the only helper-level assertion needed. | Required | Closes F-4 (partial). |
| FR-007 | `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md` MUST be corrected so every JSON field reference matches the actual `Decision` schema (`step_id` / `preview_step`, never `issued_step_id`). | Required | Closes F-5. |
| FR-008 | A new dogfood smoke MUST be captured at `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md`. The smoke MUST issue at least one composed action (not just query) and record paired `started`/`done` trail records under `<temp_repo>/.kittify/events/profile-invocations/` with documentation-native action names. | Required | Closes F-2 / NFR-005 / SC-006. |
| FR-009 | The new smoke MUST use `uv --project <spec-kitty-repo>` (NEVER `--directory`, per #735). The temp repo MUST be created OUTSIDE the spec-kitty tree (per predecessor C-010). | Required | Inherited contract. |
| FR-010 | All predecessor regression suites MUST stay green after this mission's edits. | Required | Inherited NFR-002. |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Test coverage: the integration walk gains at least 4 new tests (full advancement walk; per-action trail-record assertions; dispatch-level guard failure; corrected unknown-action coverage). | New file diff shows ≥ 4 new test functions. | Required |
| NFR-002 | All predecessor protected suites pass: the 11-suite list from `evidence/regression.md`. | 100% pass on the list. | Required |
| NFR-003 | mypy --strict on changed files: zero new findings. Pre-existing baselines do not regress. | Zero new findings. | Required |
| NFR-004 | ruff check on changed files: zero new findings. | Zero new findings. | Required |
| NFR-005 | Mission-review verdict requires the new smoke evidence to actually show action issuance (not query). The reviewer greps `smoke-v2.md` for `"kind": "success"` (or equivalent confirmation that an action was issued) — absence of that evidence downgrades verdict to UNVERIFIED. | Hard gate. | Required |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | This mission MUST NOT modify the predecessor's runtime sidecar (`src/specify_cli/missions/documentation/mission-runtime.yaml`), step contracts, action bundles, DRG nodes/edges, or composition wiring (`runtime_bridge.py` / `executor.py`). The substrate is correct; only the missing pieces and tests are added/edited. | Required |
| C-002 | All inherited predecessor constraints (C-001..C-010 from `documentation-mission-composition-rewrite-01KQ5M1Y/spec.md`) remain in force. Especially C-007: zero mocks of forbidden symbols in the integration walk. | Required |
| C-003 | The new smoke evidence file is named `smoke-v2.md` to preserve `smoke.md` as the historical record of the F-2 finding. The mission-review report MUST reference both. | Required |
| C-004 | The predecessor's `quickstart.md` is edited in place. The diff MUST be ≤ 50 lines and confined to the JSON field references and command output expectations. No restructure. | Required |
| C-005 | Out of scope: any change to the predecessor `mission-review.md` content (it is historical record). A new mission-review report for THIS fix-up will land at `kitty-specs/documentation-mission-composition-fixup-01KQ6N5X/mission-review.md`. | Required |

## Success Criteria

| ID | Outcome | Measure |
|---|---|---|
| SC-001 | Every documentation step issues a non-null `prompt_file`. | A test `tests/specify_cli/test_documentation_prompt_resolution.py` parametrizes over the 7 step ids and asserts `Decision.prompt_file is not None and Path(prompt_file).is_file()`. |
| SC-002 | Real dogfood smoke shows action issuance + paired trail records. | `evidence/smoke-v2.md` contains a `next.json` with `"kind": "success"` or a `step_id` field, plus a trail-records section showing at least one paired `started`+`done` record with action ∈ documentation verbs. |
| SC-003 | Integration walk advances all 6 actions. | A new test in `tests/integration/test_documentation_runtime_walk.py` drives `decide_next_via_runtime` 6 times and asserts each issuance succeeds + each action has a paired trail record. |
| SC-004 | Dispatch-level guard failures observable. | A new test asserts that `decide_next_via_runtime` on an empty feature_dir returns a blocked decision naming `spec.md`. |
| SC-005 | Quickstart runs without KeyError. | `quickstart.md` field references match the actual `Decision` schema; the smoke evidence walks the corrected sequence end-to-end. |
| SC-006 | Mission-review verdict is PASS WITHOUT NOTES (or PASS WITH only the pre-existing acceptable mypy baseline note). | New mission-review report acknowledges all 5 findings closed; no new HIGH/CRITICAL findings. |

## Dependencies

- Predecessor mission `01KQ5M1Y190VANF39KMBWZP6SD` (commit `1c03e2f4`) — substrate must be present.
- No external dependencies; no schema changes; no new shipped profile.

## Out of Scope

- Any change to the predecessor's runtime sidecar, contracts, action bundles, DRG, runtime_bridge.py, executor.py.
- Any new functional capability beyond what FR-001..FR-010 mandate.
- Refactoring the guard dispatch ladder (Phase 7).
- Loosening the Python pin or generalizing the mypy cast in executor.py (#805).
- New shipped agent profiles.
- Changes to the predecessor's `mission-review.md`.

## Definition of Done

- All 10 FRs verified by tests or evidence.
- All 5 acceptance scenarios pass.
- All 6 SCs measurable in committed artifacts.
- Predecessor's protected suites still green (NFR-002).
- mypy --strict and ruff zero new findings (NFR-003 / NFR-004).
- New smoke evidence shows action issuance (NFR-005 / SC-002 / SC-006 hard gate).
- Mission-review report at `kitty-specs/documentation-mission-composition-fixup-01KQ6N5X/mission-review.md` lands with verdict PASS.
