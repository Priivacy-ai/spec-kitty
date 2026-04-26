---
work_package_id: WP07
title: CHANGELOG, Regression Sweep, Lint, Smoke Evidence
dependencies:
- WP06
requirement_refs:
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane-per-WP-from-finalize-tasks
subtasks:
- T027
- T028
- T029
- T030
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/
execution_mode: code_change
owned_files:
- CHANGELOG.md
- kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/regression.md
- kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/lint.md
- kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke.md
tags: []
---

# WP07 — CHANGELOG, Regression Sweep, Lint, Smoke Evidence

## Objective

Pre-merge hygiene: CHANGELOG entry, regression sweep against the 6 protected suites (NFR-002), `mypy --strict` and `ruff check` on changed files (NFR-003 + NFR-004), and the dogfood smoke from a separate temp repo (NFR-005, SC-006, C-008, C-010). Each subtask produces an evidence artifact under `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/<name>.md` that the mission-review skill consumes.

## Context

The mission-review verdict requires every NFR threshold and every SC measure to have evidence. Without evidence the verdict downgrades to UNVERIFIED (NFR-005, C-008). This WP collects that evidence as committed files so the mission-review skill can read them directly.

Reference: [quickstart.md](../quickstart.md) for the smoke command sequence.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: `spec-kitty agent action implement WP07 --agent <name>`. Depends on WP06 (the integration walk must be green before regression sweep is meaningful).

## Subtasks

### T027 — `CHANGELOG.md` entry

**Steps**:
1. Open `CHANGELOG.md` (project root). Insert a new entry under the unreleased / next-release section:

   ```markdown
   ### Added — Documentation mission composition rewrite (#502, Phase 6 WP6.4)

   - Documentation mission now runs on the StepContractExecutor composition substrate, mirroring research (#504) and software-dev (#503).
   - New runtime sidecar templates: `src/specify_cli/missions/documentation/mission-runtime.yaml` and `src/doctrine/missions/documentation/mission-runtime.yaml`.
   - Six shipped step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml` (discover, audit, design, generate, validate, publish).
   - Six action doctrine bundles under `src/doctrine/missions/documentation/actions/<action>/` (governance guidelines + directive/tactic index).
   - DRG action nodes and edges for `action:documentation/{discover,audit,design,generate,validate,publish}` in `src/doctrine/graph.yaml`.
   - Composition wiring: `_COMPOSED_ACTIONS_BY_MISSION["documentation"]`, six `_ACTION_PROFILE_DEFAULTS` entries, fail-closed guard branch in `_check_composed_action_guard()` with structured error for unknown actions.
   - Real-runtime integration walk at `tests/integration/test_documentation_runtime_walk.py` proving SC-001 / SC-003 / SC-004.

   ### Backward compatibility

   - The legacy `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml` files remain on disk for backward reference. The runtime resolves the new `mission-runtime.yaml` ahead of the legacy file via the existing precedence in `_resolve_runtime_template_in_root` (no loader changes in this PR).
   ```

2. Commit message references issue #502 and the umbrella #461.

**Files**: `CHANGELOG.md` (edit only).

**Validation**:
- [ ] Entry mentions #502, #461, and the 6 documentation actions.
- [ ] Backward-compatibility note is present.

### T028 — Regression sweep evidence

**Steps**:
1. Create `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/regression.md`.
2. Run the full regression sweep and capture stdout:
   ```bash
   uv run --python 3.13 --extra test python -m pytest \
       tests/specify_cli/mission_step_contracts/ \
       tests/specify_cli/next/test_runtime_bridge_composition.py \
       tests/specify_cli/next/test_runtime_bridge_research_composition.py \
       tests/integration/test_research_runtime_walk.py \
       tests/integration/test_custom_mission_runtime_walk.py \
       tests/integration/test_mission_run_command.py \
       tests/integration/test_documentation_runtime_walk.py \
       tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
       tests/specify_cli/test_documentation_drg_nodes.py \
       tests/specify_cli/test_documentation_template_resolution.py \
       tests/specify_cli/mission_step_contracts/test_documentation_composition.py \
       -q --timeout=120
   ```
3. In `evidence/regression.md`, record:
   - The exact command above (verbatim).
   - The `passed`/`failed`/`skipped` counts from pytest summary.
   - Any failure backtrace (paste verbatim if any).
   - The git SHA of HEAD at the time of the run.
4. If any test fails, the WP fails closed; the implementer must fix or document the regression in the spec's "Open Questions" before mission-review.

**Files**: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/regression.md` (new, ~30 lines + pytest output).

**Validation**:
- [ ] All listed suites pass.
- [ ] Evidence file records the command, output, and HEAD SHA.

### T029 — Lint + type evidence

**Steps**:
1. Create `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/lint.md`.
2. Run on changed files (the precise list is given by `git diff --name-only origin/main..HEAD`; for this mission it is the files listed in [data-model.md](../data-model.md#file-inventory)):
   ```bash
   uv run --python 3.13 --extra lint ruff check \
       src/specify_cli/next/runtime_bridge.py \
       src/specify_cli/mission_step_contracts/executor.py \
       tests/integration/test_documentation_runtime_walk.py \
       tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
       tests/specify_cli/test_documentation_drg_nodes.py \
       tests/specify_cli/test_documentation_template_resolution.py \
       tests/specify_cli/mission_step_contracts/test_documentation_composition.py

   uv run --python 3.13 --extra lint mypy --strict \
       src/specify_cli/next/runtime_bridge.py \
       src/specify_cli/mission_step_contracts/executor.py \
       tests/integration/test_documentation_runtime_walk.py \
       tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
       tests/specify_cli/test_documentation_drg_nodes.py \
       tests/specify_cli/test_documentation_template_resolution.py \
       tests/specify_cli/mission_step_contracts/test_documentation_composition.py
   ```
3. In `evidence/lint.md`, record:
   - Both commands (verbatim).
   - Both stdouts (paste verbatim).
   - A "zero new findings" assertion line if the output is empty / clean.
   - The git SHA of HEAD.

**Files**: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/lint.md` (new, ~40 lines + tool output).

**Validation**:
- [ ] ruff exits 0 on all listed files.
- [ ] mypy exits 0 on all listed files.

### T030 — Dogfood smoke evidence

**Steps**:
1. Create `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke.md`.
2. Execute the [quickstart.md](../quickstart.md) command sequence verbatim. Use `uv --project <spec-kitty-repo>` (NEVER `--directory` per #735 / NFR-005 / C-010).
3. Capture into `evidence/smoke.md`:
   - The full command sequence (verbatim).
   - The full stdout of `spec-kitty agent mission create demo-docs --mission-type documentation --json` (`create.json`).
   - The full stdout of `spec-kitty next --agent claude --mission <handle> --json` (`next.json`).
   - The output of `ls -la ~/.kittify/events/profile-invocations/` (or wherever the trail records land in the smoke environment).
   - A grep-line proving no `--directory` was used: `grep -c '\-\-directory' <transcript>` returning 0.
4. Verify that `next.json` contains `"mission": "documentation"` and `issued_step_id` ∈ `{discover, audit, design, generate, validate, publish}` OR a `kind: blocked` decision with `guard_failures` naming `spec.md`.

**Files**: `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke.md` (new, ~50 lines + command output).

**Validation**:
- [ ] No `--directory` invocation anywhere in the smoke transcript.
- [ ] `next.json` has `mission == "documentation"`.
- [ ] At least one invocation event for a documentation-native action is recorded.

## Definition of Done

- [ ] T027 — CHANGELOG.md entry committed.
- [ ] T028 — `evidence/regression.md` shows full pytest pass.
- [ ] T029 — `evidence/lint.md` shows zero ruff + zero mypy findings.
- [ ] T030 — `evidence/smoke.md` shows the dogfood smoke succeeded with `--project` and recorded the documentation-native action name.
- [ ] All 4 evidence files committed to the mission's lane branch.

## Risks

1. The smoke could fail if SaaS sync trailing noise (#735) corrupts JSON parsing. Mitigation: parse only the leading JSON object; quickstart.md already documents this. If the smoke parser fails, record the trailing noise verbatim in `evidence/smoke.md` and reference #735.
2. ruff/mypy may flag pre-existing baseline errors on the touched files. NFR-003 says "zero new findings", not "zero findings". Mitigation: implementer runs ruff/mypy at baseline (`origin/main`) first to capture the existing findings count; T029's evidence records "delta = 0" rather than absolute zero.
3. A regression sweep failure in any of the 6 protected suites blocks merge. Mitigation: investigate the failure root cause; if the failure is unrelated to documentation (e.g. flake), record it explicitly in `evidence/regression.md` and re-run.

## Reviewer Guidance

- Read `evidence/regression.md` first; if any suite fails, block.
- Read `evidence/lint.md`; if non-empty findings appear, demand they are addressed or documented as pre-existing.
- Read `evidence/smoke.md`; grep for `--directory` (must be 0); verify `mission == "documentation"` in `next.json`.
- Verify the CHANGELOG entry references #502 and the 6 documentation actions.
- Verify the smoke ran from a temp repo OUTSIDE the spec-kitty source tree (per C-010).
