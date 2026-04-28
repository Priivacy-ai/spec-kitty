---
work_package_id: WP03
title: Real Fixture Synthesis (#839)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "51393"
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/charter/synthesizer/**
- src/charter/_doctrine_paths.py
- tests/doctrine_synthesizer/**
- tests/charter/test_synthesize*.py
- tests/charter/test_charter_synthesize*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

Make `charter synthesize --adapter fixture --json` produce `.kittify/doctrine/` and the synthesis manifest/provenance artifacts on the public path. Make `--dry-run --json` emit a strict envelope per `contracts/charter-synthesize-dry-run.json`. Eliminate the E2E's reliance on the `--dry-run-evidence` fallback and hand-seeding of `.kittify/doctrine/`.

Closes (with strict E2E gate): `#839`. Satisfies: `FR-003`, `FR-004`, `NFR-006`.

## Context

- **Spec FRs**: FR-003 (strict dry-run envelope), FR-004 (real synthesize writes artifacts).
- **Contracts**: `contracts/charter-synthesize-dry-run.json`, `contracts/charter-synthesize.json`.
- **Research R2** (`research.md`): identifies the gap in `fixture_adapter.py` / `synthesize_pipeline.py` / `write_pipeline.py` and the canonical artifact set.
- **Brief**: `start-here.md` "Real Charter synthesis must work from a fresh project" section.
- **Existing files** (already in repo):
  - `src/charter/synthesizer/fixture_adapter.py`
  - `src/charter/synthesizer/orchestrator.py`
  - `src/charter/synthesizer/synthesize_pipeline.py`
  - `src/charter/synthesizer/write_pipeline.py`
  - `src/charter/synthesizer/manifest.py`, `provenance.py`, `evidence.py`
  - `src/charter/_doctrine_paths.py`

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`. Enter via `spec-kitty agent action implement WP03 --agent <name>`.

## Subtasks

### T011 — Make `--dry-run --json` emit strict envelope per contract

**Purpose**: Lock the `synthesize --adapter fixture --dry-run --json` output to the strict shape in `contracts/charter-synthesize-dry-run.json`.

**Steps**:
1. Read the current dry-run output via `uv run spec-kitty charter synthesize --adapter fixture --dry-run --json` against a temp project.
2. Compare to the contract; identify drift (missing fields, unexpected fields, wrong types).
3. Update the synthesizer dry-run path to emit the strict envelope:
   - `result`: `success` | `blocked` | `error`
   - `adapter`: echoed adapter id
   - `planned_artifacts`: array of `{path, kind}`
   - `warnings`: optional structured array
4. Ensure exactly one JSON document on stdout (no trailing whitespace beyond a single newline; no SaaS sync warnings — those go to stderr or into `warnings`).

**Files**: `src/charter/synthesizer/orchestrator.py`, `src/charter/synthesizer/fixture_adapter.py`, charter CLI shim.

### T012 — Make `--json` write doctrine artifacts via real write pipeline

**Purpose**: Make `synthesize --adapter fixture --json` actually produce `.kittify/doctrine/` and the canonical artifact tree on disk.

**Steps**:
1. Read research R2 for the gap in the write pipeline.
2. Wire the fixture adapter through the same write pipeline used by the generated-artifact adapter (or fix the fixture-specific write pipeline) so the artifact set in `contracts/charter-synthesize.json` is produced.
3. Drop reliance on `--dry-run-evidence` — that flag becomes a debug affordance, not a public path. Do not remove it; just ensure `--json` does the right thing without it.
4. Confirm the artifact paths match `_doctrine_paths.py` canonical locations.

**Files**: `src/charter/synthesizer/write_pipeline.py`, `src/charter/synthesizer/synthesize_pipeline.py`, `src/charter/synthesizer/fixture_adapter.py`.

### T013 — Add unit/integration tests for dry-run envelope shape

**Purpose**: Lock the strict dry-run envelope shape with regression tests.

**Steps**:
1. Add a test in `tests/doctrine_synthesizer/` (or `tests/charter/`) that:
   - Creates a temp project with the existing fixtures.
   - Invokes the dry-run CLI via subprocess with `--json`.
   - Parses stdout with strict full-stream `json.loads`.
   - Asserts shape per `contracts/charter-synthesize-dry-run.json`.
2. Test should fail if T011 is reverted.

### T014 — Add integration test for on-disk artifacts after `--json` run

**Purpose**: Lock that the real `--json` invocation writes the canonical artifact tree.

**Steps**:
1. Add a test that:
   - Creates a temp project (with `git init`, `spec-kitty init`).
   - Runs `charter generate --json` to set up minimum charter state.
   - Invokes `charter synthesize --adapter fixture --json` via subprocess.
   - Parses stdout strictly.
   - Asserts `.kittify/doctrine/` exists and contains the expected artifacts.
   - Asserts the test did not pre-seed any of the asserted paths.

### T015 — Verify `tests/doctrine_synthesizer/` and `tests/charter/` still pass

**Steps**:
1. Run `uv run pytest tests/doctrine_synthesizer tests/charter -q`. Must exit 0.
2. Run `uv run mypy --strict src/charter` and `uv run ruff check src tests`. Must exit 0.

## Test Strategy

- **Per-fix regression coverage**: T013 + T014 (NFR-006).
- **Targeted gates**: `tests/doctrine_synthesizer/`, `tests/charter/`.

## Definition of Done

- [ ] `synthesize --dry-run --json` emits strict envelope.
- [ ] `synthesize --json` writes `.kittify/doctrine/` with canonical artifacts.
- [ ] No `--dry-run-evidence` fallback needed for the public operator path.
- [ ] T013 and T014 tests pass; both fail if fixes reverted.
- [ ] `tests/doctrine_synthesizer/`, `tests/charter/` regression-free.
- [ ] `mypy --strict src/charter` passes.
- [ ] `ruff check src tests` passes.
- [ ] Owned files only.

## Risks

- **Refactor scope**: if the write pipeline is fundamentally fixture-incompatible, scope balloons. **Mitigation**: timebox WP03; if scope > "small change in fixture_adapter + write_pipeline", escalate as follow-up tranche per plan risk register, keep the bypass flagged in WP08, and document in research.md.
- **Doctrine path schema drift**: if `_doctrine_paths.py` evolves alongside, ensure tests use canonical paths from the module, not hard-coded.

## Reviewer Guidance

- Confirm `--json` writes artifacts; review the actual write pipeline diff.
- Confirm contracts match observed CLI output (run the CLI, paste output, diff against schema).
- Confirm tests fail without fixes (revert temporarily and re-run).

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <your-agent-key>
```

## Activity Log

- 2026-04-28T10:21:21Z – claude:sonnet:implementer-ivan:implementer – shell_pid=47137 – Started implementation via action command
- 2026-04-28T10:31:30Z – claude:sonnet:implementer-ivan:implementer – shell_pid=47137 – Direction A: env-var stub mode for fixture adapter; tests for dry-run envelope and on-disk artifacts; doctrine_synthesizer + charter test trees green
- 2026-04-28T10:32:08Z – claude:opus:reviewer-renata:reviewer – shell_pid=51393 – Started review via action command
- 2026-04-28T10:34:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=51393 – Review passed: env-var-gated stub mode (SPEC_KITTY_FIXTURE_AUTO_STUB) added to FixtureAdapter without modifying write_pipeline.py; strict dry-run JSON envelope (result/adapter/planned_artifacts/warnings) emitted from charter.py; T013 envelope shape test + T014 on-disk artifact test added; tests/doctrine_synthesizer + tests/charter green (798 passed, 1 skipped).
