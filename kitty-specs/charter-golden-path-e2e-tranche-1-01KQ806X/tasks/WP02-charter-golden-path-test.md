---
work_package_id: WP02
title: Charter golden-path E2E test
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-021
- NFR-001
- NFR-002
- NFR-003
- NFR-005
- NFR-006
planning_base_branch: test/charter-e2e-827-tranche-1
merge_target_branch: test/charter-e2e-827-tranche-1
branch_strategy: Planning artifacts for this feature were generated on test/charter-e2e-827-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into test/charter-e2e-827-tranche-1 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 2
assignee: ''
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "58927"
history:
- at: '2026-04-27T18:15:53Z'
  actor: spec-kitty.tasks
  action: Generated
agent_profile: python-pedro
authoritative_surface: tests/e2e/test_charter_epic_golden_path.py
execution_mode: code_change
owned_files:
- tests/e2e/test_charter_epic_golden_path.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package WP02 — Charter golden-path E2E test

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this file, load your agent profile so you adopt the correct identity, scope, and boundaries for this work package:

```
/ad-hoc-profile-load python-pedro implementer
```

If `/ad-hoc-profile-load` is unavailable, read `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml` directly and adopt the implementer role and Python conventions described there before continuing.

## Objective

Create `tests/e2e/test_charter_epic_golden_path.py`: a single end-to-end pytest test that drives the operator path through public CLI from a fresh project, asserts the JSON envelopes and lifecycle records per spec, and asserts the source checkout is byte-identical before and after.

This is the operator-path proof for issue #827 tranche 1. The test must fail loudly when the Charter epic regresses, and must not pass via private helpers, monkeypatches, or fallback chains.

## Branch Strategy

- **Planning / base branch**: `test/charter-e2e-827-tranche-1`
- **Final merge target**: `test/charter-e2e-827-tranche-1`
- WP02 depends on WP01 — implement only after WP01 is approved and merged into the lane base.
- Worktree allocation is computed by `finalize-tasks` from `lanes.json`. Use `spec-kitty agent action implement WP02 --agent <name>` to enter the correct workspace; do not branch manually.

## Context

- **Mission spec**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/spec.md`
- **Implementation plan**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/plan.md`
- **Research record**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/research.md` — read in full before writing code. Especially: R-001 (mission pin), R-002 (`--adapter fixture` deviation), R-004 (`next` issue/advance shape), R-005 (pollution guard), R-009 (premortem).
- **CLI flow contract**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/contracts/cli-flow-contract.md` — authoritative subprocess-by-subprocess contract.
- **Data model**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/data-model.md` — invariants I-001..I-004 are the structural assertions you are encoding.
- **WP01 helpers**: `tests/e2e/conftest.py` — `fresh_e2e_project`, `capture_source_pollution_baseline`, `assert_no_source_pollution`, `format_subprocess_failure`, `SourcePollutionBaseline`. WP01 must be merged before WP02 starts.
- **Existing reference test**: `tests/e2e/test_cli_smoke.py:91-358` — the smoke test's mission scaffolding pattern (seed `spec.md`, `tasks.md`, `WP01-*.md`, meta.json patch, commit, finalize) is reusable. **Do not** copy its `implement`/`move-task` flow; this WP uses `next` instead, per spec.
- **Existing reference for `profile-invocations` reads**: `tests/integration/test_documentation_runtime_walk.py:295-340` — shows how to read `.kittify/events/profile-invocations/*.jsonl` from disk. **Do not** copy its `decide_next_via_runtime` calls (forbidden surface).

## Forbidden surface (mandatory)

The test file MUST NOT import, reference, or call any of:

- `decide_next_via_runtime`
- `_dispatch_via_composition`
- `StepContractExecutor`
- `run_terminus`
- `apply_proposals`
- `ProfileInvocationExecutor` (read its output, never call it)
- Any private member of `specify_cli.next._internal_runtime` or sibling internal modules.

The test MUST NOT call `pytest.MonkeyPatch.setattr` against the dispatcher, executor, DRG resolver, or frozen-template loader. If the test seems to need a monkeypatch to pass, that is a product finding — surface it via spec FR-021, do not paper over.

## Documented deviation from `start-here.md` (cite in PR + inline comment)

`start-here.md` recommends `spec-kitty charter synthesize --json` (no `--adapter` flag). This test MUST use `spec-kitty charter synthesize --adapter fixture --dry-run --json` and `spec-kitty charter synthesize --adapter fixture --json`. Reason: the default `generated` adapter validates LLM-authored YAML under `.kittify/charter/generated/`, which doesn't exist in an unattended automated test. The `fixture` adapter is the documented offline/testing path. See research.md R-002. Restate this in the PR description (spec FR-021) AND in an inline comment in the test file.

## Subtask Details

### T004 — Scaffold the test module

**Purpose.** Create the file with markers, imports, the single test function (or one-test class), and the fixture wiring. Spec FR-001, FR-002.

**Steps.**

1. Create `tests/e2e/test_charter_epic_golden_path.py` with:

   ```python
   """End-to-end golden-path test for the Charter epic (#827 tranche 1).

   This test drives the entire operator path through public CLI commands
   from a fresh project, asserts the JSON envelopes and lifecycle records
   per spec, and asserts the source checkout is byte-identical before
   and after.

   It does not call any private helper (decide_next_via_runtime,
   _dispatch_via_composition, StepContractExecutor, run_terminus,
   apply_proposals) and does not monkeypatch the dispatcher, executor,
   DRG resolver, or frozen-template loader. If a step seems to require
   one, that's a product finding -- surface it, do not paper over.

   Composed mission pin: software-dev (per mission research R-001).

   Documented deviation from start-here.md: charter synthesize uses
   --adapter fixture because the default 'generated' adapter requires
   LLM-authored YAML that an unattended automated test cannot provide.
   See research.md R-002 and the PR description.
   """

   from __future__ import annotations

   import json
   import subprocess
   from pathlib import Path
   from typing import Any

   import pytest

   from tests.e2e.conftest import (
       REPO_ROOT,
       SourcePollutionBaseline,
       assert_no_source_pollution,
       capture_source_pollution_baseline,
       format_subprocess_failure,
   )


   pytestmark = [pytest.mark.e2e, pytest.mark.slow]


   def test_charter_epic_golden_path(
       fresh_e2e_project: Path,
       run_cli,  # type: ignore[no-untyped-def]
   ) -> None:
       """Drive the Charter epic operator path through public CLI."""
       baseline = capture_source_pollution_baseline(REPO_ROOT)
       try:
           _run_golden_path(fresh_e2e_project, run_cli)
       finally:
           # Pollution guard runs even when an earlier assertion fails.
           # An earlier failure is no excuse for leaving the source
           # checkout dirty.
           assert_no_source_pollution(baseline, REPO_ROOT)
   ```

2. Add a placeholder for `_run_golden_path`; subsequent subtasks fill it in.

**Files.** Creates `tests/e2e/test_charter_epic_golden_path.py`. Initial size ~50 lines.

**Validation.**

- [ ] `pytest --collect-only tests/e2e/test_charter_epic_golden_path.py` lists exactly one test.
- [ ] `ruff check` and `mypy --strict` pass.

### T005 — Project bootstrap + Charter governance flow

**Purpose.** Implement the test's first phase: a fresh project from `fresh_e2e_project` is already initialized; the test must drive interview, generate, bundle validate, synthesize (dry-run + real, both with `--adapter fixture`), status, and lint. Spec FR-004, FR-008..FR-013.

**Steps.**

1. Define a small JSON-parse helper in `_run_golden_path`:

   ```python
   def _expect_success(
       *,
       command: list[str],
       cwd: Path,
       completed: subprocess.CompletedProcess[str],
       parse_json: bool = True,
   ) -> dict[str, Any] | None:
       if completed.returncode != 0:
           raise AssertionError(format_subprocess_failure(
               command=command, cwd=cwd, completed=completed,
           ))
       if not parse_json:
           return None
       try:
           payload = json.loads(completed.stdout)
       except json.JSONDecodeError as err:
           raise AssertionError(
               f"--json output not parseable:\n"
               f"{format_subprocess_failure(command=command, cwd=cwd, completed=completed)}\n"
               f"  parse error: {err}"
           ) from err
       assert isinstance(payload, dict), (
           f"--json output is not a dict:\n"
           f"{format_subprocess_failure(command=command, cwd=cwd, completed=completed)}"
       )
       return payload
   ```

2. Call the charter flow in order. For each call, build the args list as a Python list so it can be passed to `format_subprocess_failure` cleanly:

   ```python
   project = fresh_e2e_project

   # FR-004 Step 1: charter interview (minimal, defaults).
   cmd = ["charter", "interview", "--profile", "minimal", "--defaults", "--json"]
   _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))

   # FR-004 Step 2: charter generate (from interview).
   cmd = ["charter", "generate", "--from-interview", "--json"]
   _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   # FR-009: charter.md exists.
   assert (project / ".kittify" / "charter" / "charter.md").is_file(), (
       "FR-009: .kittify/charter/charter.md missing after charter generate"
   )

   # FR-010: bundle validate.
   cmd = ["charter", "bundle", "validate", "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   # Widen this assertion once the live envelope is observed; for now,
   # require that the payload signal success in some explicit field.
   _assert_signals_success(payload, fr_id="FR-010")

   # FR-011: synthesize --dry-run --adapter fixture must NOT create .kittify/doctrine/.
   doctrine_path = project / ".kittify" / "doctrine"
   doctrine_existed_before_dryrun = doctrine_path.exists()
   cmd = [
       "charter", "synthesize",
       "--adapter", "fixture",
       "--dry-run",
       "--json",
   ]
   _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   if not doctrine_existed_before_dryrun:
       assert not doctrine_path.exists(), (
           "FR-011: charter synthesize --dry-run created .kittify/doctrine/"
       )

   # FR-012: real synthesize (still --adapter fixture; see R-002 deviation).
   cmd = [
       "charter", "synthesize",
       "--adapter", "fixture",
       "--json",
   ]
   _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   assert doctrine_path.is_dir(), (
       "FR-012: .kittify/doctrine/ missing after charter synthesize"
   )

   # FR-013: status reports non-error state.
   cmd = ["charter", "status", "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   _assert_no_error_state(payload, fr_id="FR-013 status")

   # FR-013: lint runs successfully or returns documented warning-only status.
   cmd = ["charter", "lint", "--json"]
   completed = run_cli(project, *cmd)
   if completed.returncode == 0:
       payload = _expect_success(command=cmd, cwd=project, completed=completed)
       _assert_no_silent_error(payload, fr_id="FR-013 lint")
   else:
       # Non-zero is acceptable ONLY if it's a documented warning-only
       # exit code AND the JSON payload makes that explicit. Surface as
       # FR-021 finding if neither is true.
       raise AssertionError(
           "FR-013: charter lint returned non-zero. If this is a documented "
           "warning-only exit, widen the assertion; otherwise surface as a "
           "product finding per spec FR-021.\n"
           f"{format_subprocess_failure(command=cmd, cwd=project, completed=completed)}"
       )
   ```

3. Define `_assert_signals_success`, `_assert_no_error_state`, and `_assert_no_silent_error` as small helpers that look for an explicit success / state field. **At first run, capture the live envelope shape** (e.g. `print(json.dumps(payload, indent=2))` behind a `--debug` switch) and lock the assertion to the actual field name.

**Files.** Modifies `tests/e2e/test_charter_epic_golden_path.py`. Estimated +120 lines.

**Validation.**

- [ ] `pytest tests/e2e/test_charter_epic_golden_path.py -q -s` reaches the end of the charter flow without failure.
- [ ] `.kittify/doctrine/` exists in the temp project after the real synthesize call.
- [ ] No write to `REPO_ROOT/.kittify/` during this phase (assert manually if needed during development).

**Edge cases.**

- `charter lint` warnings vs errors — distinguish by exit code AND payload shape.
- `synthesize --adapter fixture` exit codes if the fixture adapter is missing in a future release — surface as FR-021 finding.

### T006 — Mission scaffolding

**Purpose.** Create a minimal `software-dev` mission inside the temp project via public CLI and finalize tasks so `next` can advance against it. Spec FR-005.

**Steps.**

1. After the charter flow (T005), call `agent mission create`:

   ```python
   mission_slug_human = "golden-path-demo"

   cmd = [
       "agent", "mission", "create", mission_slug_human,
       "--mission-type", "software-dev",
       "--friendly-name", "Golden Path Demo",
       "--purpose-tldr", "Minimal demo mission for the golden-path E2E.",
       "--purpose-context", (
           "This mission exists solely to give the golden-path E2E test a "
           "concrete software-dev mission to advance through `spec-kitty next`. "
           "It is created and discarded inside the test's temp project."
       ),
       "--branch-strategy", "already-confirmed",
       "--json",
   ]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   assert payload["result"] == "success", payload
   mission_handle = payload["mission_slug"]
   feature_dir = Path(payload["feature_dir"])
   ```

2. Run `setup-plan`:

   ```python
   cmd = ["agent", "mission", "setup-plan", "--mission", mission_handle, "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   assert (feature_dir / "plan.md").is_file()
   ```

3. Seed minimal mission content (mirroring `tests/e2e/test_cli_smoke.py:132-214` recipe). Keep this content inline in the test file; do NOT factor into conftest. The seed data is:
   - Replace `spec.md` with a minimal FR/NFR/C table (one of each).
   - Write `tasks.md` with a single WP01 entry referencing FR-001.
   - Write `tasks/WP01-hello-world.md` with frontmatter that omits `dependencies` (so `finalize-tasks` has work to do).
   - Patch `meta.json` to update `mission_type`, `created_at`, `vcs` while preserving the minted `mission_id`.

4. Commit the seed:

   ```python
   subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
   subprocess.run(
       ["git", "commit", "-m", "Seed minimal golden-path demo mission"],
       cwd=project, check=True, capture_output=True,
   )
   ```

5. Run `finalize-tasks`:

   ```python
   cmd = ["agent", "mission", "finalize-tasks", "--mission", mission_handle, "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   wp01 = (feature_dir / "tasks" / "WP01-hello-world.md").read_text(encoding="utf-8")
   assert "dependencies" in wp01.lower(), (
       "finalize-tasks did not write the dependencies field into WP01"
   )
   ```

**Files.** Modifies `tests/e2e/test_charter_epic_golden_path.py`. Estimated +130 lines (most of which is the seed strings).

**Validation.**

- [ ] `feature_dir` exists; `spec.md`, `meta.json`, `plan.md`, `tasks.md`, `tasks/WP01-hello-world.md` all present.
- [ ] After `finalize-tasks`, WP01 frontmatter contains a `dependencies` field.
- [ ] No write to `REPO_ROOT/kitty-specs/`.

**Edge cases.**

- A future `agent mission create` that requires a `--branch-strategy` value other than `already-confirmed` — surface as FR-021 finding.
- `meta.json` schema additions — preserve unknown fields, only patch the documented ones.

### T007 — `next` issue + advance + lifecycle assertions

**Purpose.** Issue exactly one composed action via `next --json`, advance it via `next --result success --json`, and assert paired pre/post lifecycle records under `.kittify/events/profile-invocations/`. Spec FR-006, FR-014, FR-015, FR-016.

**Steps.**

1. Query mode:

   ```python
   cmd = ["next", "--agent", "test-agent", "--mission", mission_handle, "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   issued_step_id = _extract_step_id(payload)
   prompt_file = _extract_prompt_file(payload)
   if prompt_file is not None:
       assert prompt_file, "FR-014: prompt-file path is empty"
   ```

   Implement `_extract_step_id` and `_extract_prompt_file` to read documented public fields from the live envelope. **On first run, log the full payload** so you can lock the field names. If a documented field name is unstable across releases, surface as FR-021 finding.

2. Advance mode:

   ```python
   cmd = [
       "next", "--agent", "test-agent",
       "--mission", mission_handle,
       "--result", "success",
       "--json",
   ]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   # FR-015: payload either advances exactly one action or returns a
   # documented structured "blocked / missing guard artifact" envelope.
   _assert_advanced_or_documented_block(payload, fr_id="FR-015")
   ```

3. Lifecycle records:

   ```python
   pi_dir = project / ".kittify" / "events" / "profile-invocations"
   assert pi_dir.is_dir(), (
       "FR-016: .kittify/events/profile-invocations/ missing after next advance"
   )
   started: list[dict[str, Any]] = []
   completed_records: list[dict[str, Any]] = []
   for jsonl_file in pi_dir.glob("*.jsonl"):
       for line in jsonl_file.read_text(encoding="utf-8").splitlines():
           if not line.strip():
               continue
           record = json.loads(line)
           kind = record.get("kind") or record.get("phase") or record.get("event")
           if kind in ("started", "start", "pre"):
               started.append(record)
           elif kind in ("completed", "done", "post"):
               completed_records.append(record)
   assert len(started) >= 1 and len(started) == len(completed_records), (
       f"FR-016: lifecycle records not paired: started={len(started)}, "
       f"completed={len(completed_records)}"
   )
   for record in (*started, *completed_records):
       action = record.get("action") or record.get("step_id")
       assert action == issued_step_id, (
           f"FR-016: lifecycle record action {action!r} does not equal "
           f"issued step id {issued_step_id!r}. A role-default verb leak."
       )
   ```

   The exact field names (`kind`, `action`, ...) need to be locked against the live writer on first run; widen the test if the writer's vocabulary differs but keep the action-name comparison tight.

**Files.** Modifies `tests/e2e/test_charter_epic_golden_path.py`. Estimated +80 lines.

**Validation.**

- [ ] Test reaches the end of `next` advance without raising.
- [ ] `pi_dir` contains at least one JSONL file with paired records.
- [ ] Recorded `action` equals the `step_id` returned by query mode (the regression-sensitive assertion).

**Edge cases.**

- `next --result success` returning a documented blocked envelope (FR-015 alternative) — `_assert_advanced_or_documented_block` accepts either branch but rejects silent no-ops.
- A future writer using different field names — first-run logging helps; FR-021 governs deviations.

### T008 — `retrospect summary` + final pollution-guard assertion + verification

**Purpose.** Run the retrospect summary, then verify the source-checkout pollution guard fires correctly. Run the quickstart commands. Spec FR-007, FR-017, FR-018, plus quickstart (`research.md`/`quickstart.md`).

**Steps.**

1. Retrospect:

   ```python
   cmd = ["retrospect", "summary", "--project", str(project), "--json"]
   payload = _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
   assert isinstance(payload, dict), (
       f"FR-007: retrospect summary --json did not return a dict envelope:\n"
       f"  got: {payload!r}"
   )
   ```

2. Final pollution guard runs in the `finally` block from T004 — no extra code needed here. Confirm with a direct test by adding one stray write to `REPO_ROOT/.kittify/` during local development (then revert!) and observe that `assert_no_source_pollution` raises.

3. After the test passes locally, run the verification commands from `quickstart.md`:

   ```bash
   uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s
   uv run pytest tests/e2e/ tests/next/ tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q
   uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py
   uv run mypy --strict tests/e2e/test_charter_epic_golden_path.py
   ```

   All four commands MUST exit 0. If any other previously-green test newly fails, that's a regression to fix before opening the PR.

4. PR description checklist (per spec SC-003):
   - List the public CLI commands the golden path executes.
   - List the Charter epic surfaces covered by this tranche.
   - List which #827 items remain for follow-up.
   - State whether any product defects were discovered while writing the test.
   - Restate the `--adapter fixture` deviation under FR-021.
   - Provide exact verification commands and results.
   - Confirm zero source-checkout pollution.

**Files.** Modifies `tests/e2e/test_charter_epic_golden_path.py`. Estimated +30 lines (most of T008's effort is verification, not code).

**Validation.**

- [ ] All four quickstart commands exit 0.
- [ ] `git status --short` in `REPO_ROOT` is empty after the run.
- [ ] PR description is filled per SC-003.

## Definition of Done

- [ ] `tests/e2e/test_charter_epic_golden_path.py` exists and contains exactly one test marked `@pytest.mark.e2e` and `@pytest.mark.slow`.
- [ ] `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s` exits 0.
- [ ] `git status --short` in `REPO_ROOT` is empty after the run (FR-017).
- [ ] No new or modified files in `REPO_ROOT/{kitty-specs,.kittify,.worktrees,docs}` or any `**/profile-invocations/` (FR-018).
- [ ] `uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py` exits 0 (NFR-003).
- [ ] `uv run mypy --strict tests/e2e/test_charter_epic_golden_path.py` exits 0 (NFR-003).
- [ ] Regression slice passes: `uv run pytest tests/e2e/ tests/next/ tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q` (NFR-006).
- [ ] Test runs ≤ 180 s wall-clock on a current runner (NFR-001).
- [ ] No reference to any forbidden private symbol (C-001/C-002). Verify with `grep -nE 'decide_next_via_runtime|_dispatch_via_composition|StepContractExecutor|run_terminus|apply_proposals|ProfileInvocationExecutor' tests/e2e/test_charter_epic_golden_path.py` returning no hits.
- [ ] No `pytest.MonkeyPatch` calls in the test (C-002). Verify with `grep -n 'monkeypatch' tests/e2e/test_charter_epic_golden_path.py`.
- [ ] `--adapter fixture` deviation cited in inline comment AND PR description (FR-021).
- [ ] PR description fills the SC-003 checklist.

## Risks and Mitigations (mirrors plan.md premortem)

| Risk | Mitigation |
|---|---|
| `run_cli` 60 s per-call timeout fires for an unexpectedly slow step | Diagnostic message includes the offending command + cwd + stdout + stderr (NFR-004). If a step legitimately needs more than 60 s, surface as FR-021 finding before extending the budget. |
| Live JSON envelope shape differs from data-model.md expectation | First-run logging locks the actual shape; widen assertion fields and document the actual surface in code comments. Surface true mismatches under FR-021. |
| `next --result success` returns a documented blocked envelope instead of advancing | FR-015 accepts both; `_assert_advanced_or_documented_block` codifies that. Silent no-ops fail. |
| Writer field name (`kind` vs `phase` vs `event`) differs in production | Helpers tolerate alternates while keeping the action-name comparison tight. Document the actual writer vocabulary in a code comment after observation. |
| Forbidden helper accidentally imported "for convenience" | Reviewer grep for forbidden names; CI mypy + ruff. |
| Source-checkout pollution masked by `.gitignore` | WP01's layer-2 inventory catches it. Pollution guard runs in `finally`, not `else`. |

## Reviewer Checklist

- [ ] Test imports zero forbidden private symbols.
- [ ] Test contains zero `monkeypatch.setattr` calls against the dispatcher / executor / DRG / template loader.
- [ ] `synthesize` calls use `--adapter fixture`; deviation cited inline AND in PR.
- [ ] Mission pin is `software-dev` and is documented in a comment.
- [ ] Lifecycle action-name assertion is tight (action == issued step id, not a substring match).
- [ ] Pollution guard runs in `finally`, fires even on prior failure.
- [ ] Failure messages include command + cwd + rc + stdout + stderr (FR-019).
- [ ] All four quickstart commands exit 0.
- [ ] PR description fills the SC-003 checklist and explicitly enumerates #827 follow-up items.

## Implementation Command

```
spec-kitty agent action implement WP02 --agent <name>
```

This resolves the lane workspace and enters it. WP02 depends on WP01; do not start until WP01 is approved and merged into the lane base.

## Activity Log

- 2026-04-27T18:37:39Z – claude:opus-4-7:python-pedro:implementer – shell_pid=52140 – Started implementation via action command
- 2026-04-27T19:00:44Z – claude:opus-4-7:python-pedro:implementer – shell_pid=52140 – Ready for review: golden-path E2E driving public CLI from fresh project; --adapter fixture deviation documented inline; pollution guard in finally; ruff + mypy --strict + pytest all green
- 2026-04-27T19:02:02Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=58927 – Started review via action command
