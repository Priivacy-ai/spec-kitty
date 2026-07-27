---
work_package_id: WP05
title: Sonar coverage on hot release/auth/sync paths
dependencies:
- WP01
- WP04
requirement_refs:
- FR-002
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1139471"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: tests/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- tests/cli/commands/test_charter_orchestration.py
- tests/cli/commands/test_charter_io.py
- tests/cli/commands/test_charter_rendering.py
- tests/cli/commands/test_charter_bundle_coverage.py
- tests/cli/commands/test_agent_config_coverage.py
- tests/integration/test_internal_runtime_engine.py
- tests/core/test_file_lock_behavior.py
- tests/_factories/charters/**
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP05.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Author behavior-driven coverage tests for the highest-uncovered files identified by Sonar. Tests follow `function-over-form-testing`: observable outcomes only, no constructor/getter/call-count assertions, mocks only at true system boundaries. Per research §4, charter.py is partitioned into three buckets — orchestration (typer-runner), I/O (`tmp_path` real I/O), and rendering (substring-stable assertions).

**Important boundary**: This WP authors **tests only**. If a test surfaces a real bug, Pedro reports it as a new issue and does NOT fix the source — fix is out-of-scope. WP05 does not own source files in the covered modules.

## Context

### Top uncovered files (Sonar, 2026-05-14)

| Uncov / total | Cov % | File | This WP's bucket |
|---|---|---|---|
| 645 / 891 | 27.6 | `src/specify_cli/cli/commands/charter.py` | T023+T024+T025 (3 sibling files) |
| 177 / 208 | 14.9 | `src/specify_cli/cli/commands/charter_bundle.py` | T026 |
| 171 / 187 | 8.6 | `src/specify_cli/cli/commands/agent/config.py` | T026 |
| 303 / 502 | 39.6 | `src/specify_cli/next/_internal_runtime/engine.py` | T027 (hot paths only) |
| 125 / 177 | 29.4 | `src/specify_cli/core/file_lock.py` | T027 (uncovered branches) |

`doctor.py` (418 / 464) is owned by WP06 — characterization tests for the multiplexer land there, NOT here.

### Research input

`research.md` §4 — `charter.py` testability triage:

- **Bucket A (40 %)**: Pure orchestration of small helpers. Test via typer `CliRunner`; assert on stdout/exit-code outcomes.
- **Bucket B (35 %)**: Filesystem-heavy IO with branching. Test with `tmp_path` + real file I/O; no `unittest.mock` patches of `Path.read_text` etc.
- **Bucket C (25 %)**: Diagnostic / report-rendering. Substring assertions on stable message content — NOT full Rich-rendered output.

## Doctrine Citations

This WP applies:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.
- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — only if a test surfaces a real bug AND the bug fix lands in a different WP scope.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T023 — Charter orchestration tests (typer-runner integration)

**Purpose**: Bucket A coverage on `cli/commands/charter.py` — exercise the command surface, assert on stdout/exit-code outcomes.

**Steps**:

1. Create `tests/cli/commands/test_charter_orchestration.py`.
2. Use `typer.testing.CliRunner` to invoke the charter command's subcommands. Set up fixtures with realistic mini-charters in `tests/_factories/charters/` (e.g. `minimal_charter.yaml`, `full_charter.yaml`).
3. For each subcommand path (interview, generate, sync, status), author tests that:
   - Set up a `tmp_path` project with `.kittify/charter/charter.md` and `meta.json` minimal artifacts.
   - Run the command via `CliRunner.invoke`.
   - Assert on exit code, on stdout substring (e.g. "✓ Charter generated"), and on file artifacts created (e.g. `kitty-specs/charter/...`).
4. Use AAA structure visible at a glance; descriptive names per NFR-002.

**Files**:

- `tests/cli/commands/test_charter_orchestration.py` (new, ~200 lines).
- `tests/_factories/charters/*.yaml` (new, 2–4 fixtures, shared with T024).

**Validation**:

- Tests pass.
- Coverage on `charter.py` orchestration-bucket functions rises measurably.

### T024 — [P] Charter I/O tests (`tmp_path` real I/O)

**Purpose**: Bucket B coverage — exercise the file-system-heavy branches in `charter.py`.

**Steps**:

1. Create `tests/cli/commands/test_charter_io.py`.
2. For each I/O branch:
   - Set up `tmp_path` with the relevant files (or omit them to test missing-file branches).
   - Invoke the function directly (not via CLI) when the I/O branch is internal.
   - Assert on resulting file content, side effects (file creation/deletion), and any returned values.
3. **Avoid `unittest.mock` patches of `Path.read_text`, `Path.write_text`, `os.path.exists`, etc.** Use real `tmp_path` I/O.
4. Cover edge cases: file missing, file empty, file malformed (yaml syntax error), file permission denied (use `chmod 000` in fixture — skip on Windows).

**Files**: `tests/cli/commands/test_charter_io.py` (new, ~200 lines).

**Validation**:

- Tests pass.
- No `unittest.mock` patches of file-I/O primitives.

### T025 — [P] Charter rendering tests (substring-stable assertions)

**Purpose**: Bucket C coverage — diagnostic and report-rendering paths.

**Steps**:

1. Create `tests/cli/commands/test_charter_rendering.py`.
2. For each rendering path (Rich console output, diagnostic messages, summary reports):
   - Invoke the function with a captured `Console`.
   - Assert on stable substring content of the rendered output (e.g. `"Charter:"`, `"✓"`, `"error:"`).
   - **Do not** assert on the full multi-line Rich-rendered output — that is brittle and breaks on Rich version updates.
3. Cover the error and success rendering paths separately.

**Files**: `tests/cli/commands/test_charter_rendering.py` (new, ~150 lines).

**Validation**:

- Tests pass.
- Substring-stable assertions only; no full-output snapshots.

### T026 — [P] Coverage tests for `charter_bundle.py` and `agent/config.py`

**Purpose**: Bucket A/B/C coverage applied to the next two highest-uncov files.

**Steps**:

1. Create `tests/cli/commands/test_charter_bundle_coverage.py`:
   - Apply the same orchestration / I/O / rendering split as T023–T025, scaled to `charter_bundle.py`'s smaller surface.
2. Create `tests/cli/commands/test_agent_config_coverage.py`:
   - Apply the same split scaled to `agent/config.py`'s configuration-management surface.
   - Cover add / remove / list / status command variants.

**Files**:

- `tests/cli/commands/test_charter_bundle_coverage.py` (new, ~180 lines).
- `tests/cli/commands/test_agent_config_coverage.py` (new, ~150 lines).

**Validation**:

- Tests pass.
- Coverage rises on both files.

### T027 — [P] Coverage tests for `internal_runtime/engine.py` (hot paths) and `core/file_lock.py` (branches)

**Purpose**: Cover the most-touched branches in the runtime engine and the locking primitive.

**Steps**:

1. Create `tests/integration/test_internal_runtime_engine.py`:
   - Focus on the engine's mission-discovery and next-action selection hot paths.
   - Set up `tmp_path` with realistic mission fixtures; invoke the engine; assert on the selected next action.
2. Create `tests/core/test_file_lock_behavior.py`:
   - Cover the acquire / release happy path.
   - Cover contention (two processes attempt to acquire) — use `multiprocessing` or `pytest-xdist` fixtures.
   - Cover the timeout branch (set a short timeout; wait past it; assert the expected exception).
   - Cover the corrupt-lock-file recovery branch if present.

**Files**:

- `tests/integration/test_internal_runtime_engine.py` (new, ~150 lines).
- `tests/core/test_file_lock_behavior.py` (new, ~120 lines).

**Validation**:

- Tests pass.
- Coverage rises on both files; the contention test does not flake under `pytest-xdist`.

### T028 — Glossary fragment for WP05

**Purpose**: FR-013 audit. WP05 does not introduce a new canonical term but reinforces "characterization test" (introduced by WP02). Record an empty fragment for traceability.

**Steps**:

1. Create `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP05.md`:
   - Note: `# WP05 reinforces but does not introduce canonical terms. See WP02 fragment for "characterization test".`

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP05.md` (new, ~5 lines).

## Test Strategy

This WP is test authoring. Each test follows `function-over-form-testing` strictly. The reviewer applies the test-code hygiene checklist (NFR-002) and rejects any test that:

- Asserts on call counts (`mock.call_count`, `mock.assert_called_once_with`).
- Asserts on internal field values that callers do not observe.
- Patches IO primitives instead of using real `tmp_path` I/O.
- Tests a constructor, getter, or setter in isolation.
- Asserts on full Rich-rendered output (brittle).

## Definition of Done

- [ ] Every test file specified in subtasks exists and passes.
- [ ] Sonar `new_coverage` on the covered files rises measurably (target: contribution toward overall 80 %).
- [ ] Every test passes the NFR-002 hygiene checklist on first review.
- [ ] No source file modifications in this WP (test-only authorship).
- [ ] `glossary-fragments/WP05.md` exists.

## Risks

- **A coverage test surfaces a real bug** (e.g. encoding edge case in `charter.py`). Pedro reports the bug as a new issue and does NOT fix in this WP. Bug fix is a separate concern coordinated with the operator.
- **`pytest-xdist` flake on the `file_lock` contention test.** Tune the timeout or skip the parallel-process case if it cannot be made deterministic on CI.
- **Coverage rises but does not reach 80 % on `charter.py`.** Pedro documents the remaining gap with reasons; the release owner decides whether to negotiate the threshold (constraint C-005).

## Reviewer Guidance

When reviewing this WP, check:

1. Every test is **behavior-driven** per `function-over-form-testing`. Reject if `mock.call_count` / `assert_called_once_with` / structural assertions appear.
2. I/O tests use `tmp_path` real I/O, not `unittest.mock` patches of `Path.read_text` / `os.path.exists`.
3. Rendering tests use substring-stable assertions, NOT full multi-line snapshots.
4. AAA structure is visible at a glance per NFR-002.
5. Names follow `test_<unit>_<behavior>_<context>` pattern.
6. No source file modifications — if any surface bug fixes appear, redirect them to a separate issue/WP.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent claude
```

## Activity Log

- 2026-05-14T09:45:48Z – claude:sonnet:python-pedro:implementer – shell_pid=1135185 – Started implementation via action command
- 2026-05-14T09:58:10Z – claude:sonnet:python-pedro:implementer – shell_pid=1135185 – Ready: 7 new test files covering charter / charter_bundle / agent_config / internal_runtime / file_lock hot paths per function-over-form-testing tactic; 96/96 tests green; no source modifications (test-only WP); glossary fragment committed to planning branch (fix/quality-check-updates).
- 2026-05-14T09:58:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=1139471 – Started review via action command
- 2026-05-14T10:01:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1139471 – Approved: 96 behavior-driven tests across 7 files (charter A/B/C, charter_bundle, agent/config, internal_runtime engine+discovery, file_lock) per function-over-form-testing tactic. Zero source modifications (test-only WP boundary respected — diff is 1969 insertions strictly under tests/ and tests/_factories/). Function-over-form audit clean: zero mock.call_count/assert_called_once_with/call_args, zero Path/os.path/read_text/write_text/exists patches, zero full Rich snapshots; MagicMock usage limited to domain stand-ins (interview/result/ctx objects), not call-interaction assertions. NFR-002 hygiene verified: AAA structure with descriptive docstrings, names follow test_<unit>_<behavior>_<context>, shared factories live under tests/_factories/charters/ (full_charter.md, minimal_charter.md, malformed_charter.yaml). Tightness audit: only two 'is not None' guards, each followed by stronger downstream equality (e.g. record.pid == os.getpid()) — no tautological assertions. Local coverage delta on touched modules (this 96-test slice alone): file_lock 85%, discovery 74%, charter_bundle 64%, agent/config 51%, engine 29%, charter 25%. Doctrine citations confirmed on all four commits (749516e9d, 5bb18b602, 03aa79db2 cite function-over-form-testing; bf555e0a3 glossary fragment cites FR-013 with no new terms).
