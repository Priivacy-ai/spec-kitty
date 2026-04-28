---
work_package_id: WP08
title: E2E Test Hardening (Strip All Bypasses)
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Mission base branch is fix/charter-e2e-827-tranche-2; lane worktree path/branch resolved by finalize-tasks. WP08 must run after all of WP02..WP07 are merged.
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
- T040
agent: claude
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: tests/e2e/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- tests/e2e/test_charter_epic_golden_path.py
- tests/e2e/conftest.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

Strip every PR-#838 bypass from `tests/e2e/test_charter_epic_golden_path.py`. After this WP merges, the strict E2E will fail for any regression in WP02..WP07's product fixes. Closes the mission's core deliverable.

Satisfies: `FR-008`, `FR-009`, `FR-010`, `FR-011`, `FR-012`, `NFR-001`, `NFR-002`, `NFR-003`, `NFR-004`, `NFR-005`.

## Context

- **Spec**: FR-008 through FR-012 enumerate every required strictening; NFR-001..005 the gates that must pass.
- **Brief**: `start-here.md` "Test Hardening Requirements" and "Done Criteria" sections.
- **Plan**: `plan.md` Risk register notes runtime budget (NFR-001 ≤ 5 min) and pollution guard (NFR-004) must be preserved.
- **Quickstart**: `quickstart.md` Steps 1–10 are the operator path the strict E2E exercises.
- **Existing test**: `tests/e2e/test_charter_epic_golden_path.py` (PR #838 baseline).

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`.
- **Hard prerequisite**: WP02..WP07 must all be merged before this WP starts. Verify via `git log` showing all six fixes on `fix/charter-e2e-827-tranche-2`.

## Subtasks

### T034 — Delete `_parse_first_json_object` and use full-stream `json.loads`

**Purpose**: Implement FR-009 (strict JSON parsing).

**Steps**:
1. Locate `_parse_first_json_object` in `tests/e2e/test_charter_epic_golden_path.py`.
2. Delete the helper.
3. Replace every call site with `json.loads(stdout)` (full stream). If a call site needs to read both stdout and stderr, capture them separately via `subprocess.run(..., capture_output=True, text=True)`.
4. Add a small inline assertion that stripped trailing whitespace produces the same result (i.e., no trailing non-whitespace was ever there) — or just rely on `json.loads` raising on garbage.

### T035 — Delete `_bootstrap_schema_version` and any metadata mutation

**Purpose**: Implement FR-001's lock — fresh init must produce the schema fields without test help.

**Steps**:
1. Locate `_bootstrap_schema_version()` (or any direct `.kittify/metadata.yaml` mutation).
2. Delete the helper and all call sites.
3. After `spec-kitty init` runs in the test, immediately assert `.kittify/metadata.yaml` contains `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` (rely on WP02's product fix).

### T036 — Delete `--dry-run-evidence` fallback and hand-seeding of doctrine

**Purpose**: Implement FR-003/FR-004 lock — real `synthesize` must work.

**Steps**:
1. Find the synthesize block in the E2E. Remove any conditional that falls back to `--dry-run-evidence` when `--dry-run --json` or `--json` fails.
2. Find any `os.makedirs(".kittify/doctrine/...")` or file-write that pre-seeds doctrine artifacts; delete it.
3. After `synthesize --adapter fixture --json`, assert `.kittify/doctrine/` exists and contains the canonical artifact set per `contracts/charter-synthesize.json` (rely on WP03's product fix).

### T037 — Delete conditional prompt-file acceptance

**Purpose**: Implement FR-006/FR-011 lock.

**Steps**:
1. Find the prompt-file assertion. It currently looks like `if "prompt_file" in step and step["prompt_file"]: ...` — make it unconditional:
   ```python
   pf = step["prompt_file"]
   assert isinstance(pf, str) and pf, f"prompt_file must be non-empty, got {pf!r}"
   assert os.path.exists(pf), f"prompt_file must resolve on disk, got {pf!r}"
   ```
2. Apply this assertion to every issued step the test exercises (rely on WP06's product fix).
3. If the test handles a step that's expected to be `blocked`, assert `status == "blocked"` with a non-empty `reason`.

### T038 — Delete profile-invocation absent-directory early return

**Purpose**: Implement FR-007/FR-010 lock.

**Steps**:
1. Find the early-return that exits the profile-invocation assertion block when `.kittify/events/profile-invocations/` is absent.
2. Replace with: assert the directory exists, then list its files, then assert paired `started`/`completed` records exist for every action the test issued, with action identity match and `outcome == "done"` per `contracts/next-advance.json` (rely on WP07's product fix).

### T039 — Keep pollution guard, fresh-project fixture, subprocess assertions; add new strict assertions per FR-008..012

**Purpose**: Make the test the strict gate spec.md requires.

**Steps**:
1. **Keep** (do not delete):
   - The source-checkout pollution guard.
   - The fresh-project fixture.
   - Every "exercise via subprocess CLI" assertion (no internal Python helpers replacing public commands).
2. **Add new strict assertions per FR-008..012**:
   - FR-008: confirm every step in `quickstart.md` Steps 1–10 is exercised via subprocess. If a step is missing, add it.
   - FR-009: every `--json` stdout passes `json.loads(stdout)` strictly.
   - FR-010: paired profile-invocation records for every issued action.
   - FR-011: non-empty resolvable `prompt_file` for every issued step.
   - FR-012: pollution guard reports zero diffs at end.
3. Use the contract files in `kitty-specs/<mission>/contracts/` as the source of truth for envelope shapes.

### T040 — Run narrow gate, targeted gates, ruff, mypy strict, 5-run determinism

**Purpose**: Verify NFR-001..005.

**Steps**:
1. **Narrow gate**: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s`. Must exit 0 in ≤ 5 min.
2. **Targeted gates**:
   - `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q`
   - `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q`
   - `uv run ruff check src tests`
3. **Strict typing**: `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py`. Exit 0.
4. **Pollution guard**: After one full run, `git status --porcelain` in the source checkout returns empty.
5. **Determinism**: Run the narrow gate 5 times consecutively; all must pass.
6. If any gate fails, **diagnose and fix** within this WP. Do not skip flaky tests; do not loosen assertions.

## Test Strategy

- **This WP is itself the test hardening.** No new product code; only test changes.
- All assertions must trace to a spec FR.

## Definition of Done

- [ ] All six bypass blocks deleted (T034..T038).
- [ ] All "Keep" items preserved (T039).
- [ ] All FR-008..012 strict assertions present.
- [ ] `mypy --strict` passes on `tests/e2e/test_charter_epic_golden_path.py`.
- [ ] Narrow gate passes in ≤ 5 minutes (NFR-001).
- [ ] All targeted gates exit 0 (NFR-002).
- [ ] Pollution guard zero diffs (NFR-004).
- [ ] 5-run determinism check passes (NFR-005).
- [ ] Owned files only (single E2E test file plus optional conftest tweak).

## Risks

- **Runtime budget exceeded**: Strict E2E might exceed 5 min. **Mitigation**: profile the slowest CLI subprocess invocation; consider parallelizing fixture setup or running fewer redundant operations. Document any unavoidable runtime increase in the PR description.
- **Flake on slow workstations**: 5-run determinism may fail on slow disk I/O. **Mitigation**: ensure each subprocess call has appropriate timeout; do not rely on filesystem race conditions; add `time.sleep(0)` only as last resort with explanation.
- **Coordination drift**: a product fix might land with subtle behavioral differences from the contract. **Mitigation**: read each merged WP's commit and confirm the actual envelope shape matches the contract before adding the strict assertion.

## Reviewer Guidance

- Diff against the PR-#838 baseline; confirm all six bypass blocks are gone.
- Run the narrow gate locally; confirm it fails when any product fix is reverted (revert one fix at a time and verify the gate fails on the corresponding strict assertion).
- Confirm pollution guard still catches a synthetic source-checkout mutation (add a temp file before the test ends, confirm guard fires).
- Confirm 5-run determinism on the reviewer's workstation.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent <your-agent-key>
```
