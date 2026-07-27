---
work_package_id: WP01
title: Hermetic mission-review gate invocation
dependencies:
- WP07
requirement_refs:
- FR-001
- FR-002
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer:reviewer"
shell_pid: "510816"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/_test_env_check.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- docs/quickstart.md
- docs/development/**
- src/specify_cli/missions/software-dev/command-templates/review.md
- src/specify_cli/cli/commands/_test_env_check.py
- tests/specify_cli/cli/commands/test_test_env_check.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Mission-review gate commands cannot fall through to a globally installed `pytest`. Replace documented release-gate invocations of `uv run pytest …` with `uv run python -m pytest …`; add a preflight assertion that fails fast with `MISSION_REVIEW_TEST_EXTRA_MISSING` when the project `.venv` lacks the `test` extra.

This WP fixes [#987](https://github.com/Priivacy-ai/spec-kitty/issues/987) and satisfies FR-001 and FR-002 in [`../spec.md`](../spec.md).

## Context

The release-gate apparatus depends on `pytest` being invoked from inside the project's virtual environment so that imported packages match `uv.lock`. The bug: `uv run pytest …` walks PATH and can pick up `/opt/homebrew/bin/pytest` (or similar) when `.venv` lacks the `test` extra, executing against globally-installed packages. The result is **false hard-gate failures** when the global env has different versions, or worse — false passes when the global env happens to match.

Two complementary fixes:

1. **Document hermetic invocation**. `uv run python -m pytest …` cannot fall through PATH because `python -m` always uses the venv's interpreter and imports `pytest` as a Python module from inside the venv.
2. **Preflight assertion**. Before invoking any gate, check `python -c "import pytest"` exits 0 in the project venv. If not, fail with a JSON-stable diagnostic that names `uv sync --extra test` as the remediation.

Developer-convenience invocations of `uv run pytest` in contributor docs are **out of scope** — those are not release gates; a misconfigured contributor environment fails fast and is fixed locally.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: created by `spec-kitty implement` when WP01 is claimed; lane allocation is per `lanes.json` computed during `finalize-tasks`.

You begin work in the worktree assigned by `spec-kitty implement WP01`. Do not switch branches manually.

## Subtasks

### T001 [P] — Audit and classify `uv run pytest` references

**Purpose**: produce an exhaustive inventory of every `uv run pytest` reference in the repo, tagged as `release-gate` or `developer-convenience`. This list becomes the input to T002 (release-gate replacement) and is committed in this WP's PR for review traceability.

**Steps**:

1. Grep the repo for `uv run pytest`:
   ```bash
   rg -n 'uv run pytest' --type md --type py --type yaml --type toml > /tmp/wp01-pytest-refs.txt
   ```
2. Classify each line:
   - **release-gate**: any reference inside `src/specify_cli/missions/*/command-templates/review*.md`, `docs/explanation/mission-review*.md`, `docs/migration/*.md` for release contexts, agent skill renderer outputs for `spec-kitty.review`, CI workflow files (`.github/workflows/`) where the job is a mission-review gate.
   - **developer-convenience**: `CONTRIBUTING.md`, top-level `README.md`, quickstart-for-contributors docs, casual mentions.
3. Produce a Markdown table in the PR description (or a comment) of:

   | File:line | Verbatim | Classification |
   |-----------|----------|----------------|
   | `docs/...` | `uv run pytest tests/contract/ -q` | release-gate |
   | `CONTRIBUTING.md:42` | `uv run pytest` | dev-convenience |

4. Commit the table inline in the relevant doc files OR as an audit artifact under `kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/audit/wp01-pytest-refs.md` so reviewers can confirm coverage.

**Files**: read-only across the repo; final write to the audit artifact OR the docs themselves (T002).

**Validation**:
- [ ] Every `uv run pytest` reference appears in the table.
- [ ] No reference is misclassified (reviewer spot-checks).

### T002 — Replace release-gate references with hermetic invocation

**Purpose**: for each release-gate row from T001's table, replace `uv run pytest …` with `uv run python -m pytest …` in-place. Developer-convenience rows stay as-is.

**Steps**:

1. For each release-gate file, change `uv run pytest <args>` → `uv run python -m pytest <args>`. Preserve all other tokens exactly.
2. If a doc uses fenced code blocks, the replacement is **inside** the code block; the surrounding prose stays as-is.
3. If a mission-template under `src/specify_cli/missions/*/command-templates/review*.md` is changed, regenerate the agent-skill packages by running `spec-kitty agent context update --all` (or whatever skill regeneration command exists; see the doc `docs/development/`).
4. Update `docs/quickstart.md` "Stable Release Gate" section per epic #822 to show the hermetic form.

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/review.md` (likely)
- `docs/explanation/mission-review.md` (if present)
- `docs/migration/*.md` (where release gates are quoted)
- `.github/workflows/release-readiness.yml` and `.github/workflows/ci-quality.yml` (if they quote the gate commands)
- `docs/quickstart.md`
- Any agent skill template that emits gate commands

**Validation**:
- [ ] `rg 'uv run pytest' <release-gate-files>` returns nothing (all replaced).
- [ ] `rg 'uv run python -m pytest' <release-gate-files>` returns the expected count.
- [ ] Developer-convenience files unchanged.

### T003 [P] — Preflight helper module

**Purpose**: a small Python helper that asserts `pytest` is importable from the active Python interpreter. Used by gate command invocation paths to fail fast before the gate runs.

**Steps**:

1. Create `src/specify_cli/cli/commands/_test_env_check.py` with:

   ```python
   """Preflight helper that asserts the test extra is installed in the active venv.

   See: src/specify_cli/cli/commands/review/ERROR_CODES.md for the
   MISSION_REVIEW_TEST_EXTRA_MISSING diagnostic body.
   """

   from __future__ import annotations
   import subprocess
   import sys
   from pathlib import Path


   class TestExtraMissing(Exception):
       """Raised when `pytest` cannot be imported from the active venv."""


   def assert_pytest_available(project_root: Path) -> None:
       """Assert that `python -c 'import pytest'` succeeds in the project venv.

       Raises TestExtraMissing on failure, carrying the
       MISSION_REVIEW_TEST_EXTRA_MISSING diagnostic code in args[0].
       """
       result = subprocess.run(
           [sys.executable, "-c", "import pytest"],
           cwd=project_root,
           capture_output=True,
       )
       if result.returncode != 0:
           raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")
   ```

2. Author the corresponding entry in WP03's `src/specify_cli/cli/commands/review/ERROR_CODES.md` (cross-reference but actual file authoring is in WP03). For WP01, just reference the code in the docstring as shown above.

**Files**: `src/specify_cli/cli/commands/_test_env_check.py` (new)

**Validation**:
- [ ] Module imports cleanly: `python -c "from specify_cli.cli.commands._test_env_check import assert_pytest_available"`.
- [ ] `mypy` strict pass on the file.

### T004 — Wire preflight into gate invocation paths

**Purpose**: call `assert_pytest_available()` at the start of any code path that invokes a release-gate pytest subprocess.

**Steps**:

1. Locate every place the CLI shells out to `python -m pytest` for a release gate. After WP07, this is in `src/specify_cli/cli/commands/review/_lane_gate.py`, `_dead_code.py`, `_ble001_audit.py`, and `_report.py` (the four gate modules). Pre-WP07 it's in `src/specify_cli/cli/commands/review.py`.

   Since WP07 is a hard dependency of WP01 (declared in this file's frontmatter), the package layout already exists when you start. Wire the preflight into the four gate modules.
2. At the top of each gate function that invokes pytest, call:
   ```python
   from specify_cli.cli.commands._test_env_check import assert_pytest_available, TestExtraMissing
   # at function entry:
   try:
       assert_pytest_available(project_root)
   except TestExtraMissing:
       # emit diagnostic to stdout JSON; exit non-zero
       ...
   ```
3. The diagnostic emission format follows the JSON-stable convention from `data-model.md`. WP03 owns the formal `MissionReviewDiagnostic` StrEnum; this WP raises the code string directly until WP03's enum lands. Use a comment: `# TODO(WP03): replace string with MissionReviewDiagnostic.TEST_EXTRA_MISSING once enum lands`.

**Files**: gate modules in `src/specify_cli/cli/commands/review/` (post-WP07)

**Validation**:
- [ ] Every gate function calls `assert_pytest_available()` before subprocessing.
- [ ] Failure emits the JSON-stable diagnostic code on stdout, body on stderr.

### T005 — Regression test

**Purpose**: prove that a fresh venv without the `test` extra fails the preflight before any pytest invocation happens.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_test_env_check.py`.
2. Test cases:
   - `test_assert_pytest_available_succeeds_when_pytest_importable` — sanity check in our own venv.
   - `test_assert_pytest_available_raises_when_pytest_missing` — uses `tempfile.TemporaryDirectory` + `venv.create()` to make a no-extras venv, calls `assert_pytest_available` against that interpreter, asserts `TestExtraMissing`.
3. Mark the test with `@pytest.mark.slow` since it builds a venv; it can be excluded from fast-tests but must run in the contract gate.

**Files**: `tests/specify_cli/cli/commands/test_test_env_check.py` (new)

**Validation**:
- [ ] Both tests pass on a clean clone.
- [ ] The synthetic-venv test runs end-to-end in under 30 seconds.

## Definition of Done

- [ ] T001 audit table committed (PR description or audit artifact).
- [ ] T002 release-gate replacements verified by grep.
- [ ] T003 preflight module passes mypy strict.
- [ ] T004 wiring lands in all four gate modules.
- [ ] T005 regression test green.
- [ ] FR-001 and FR-002 from spec.md cited in commit messages.
- [ ] Glossary updated if any new canonical term is introduced (none expected for this WP).

## Risks and Reviewer Guidance

**Risk**: T001 misses a release-gate reference because it lives in a non-obvious place (e.g., an agent skill template the renderer emits). Reviewer should grep the entire workspace post-PR to confirm zero `uv run pytest` references remain in any release-gate context.

**Reviewer focus**:

- T001's audit table — is the classification correct?
- T002's replacements — exact-token substitution, no whitespace/quote drift.
- T004 wiring — does every gate path call the preflight?
- T005 — does the negative test actually exercise a venv-without-pytest, or is it mocked away?

## Suggested implement command

```bash
spec-kitty agent action implement WP01 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:28:56Z – claude:sonnet:implementer-ivan:implementer – shell_pid=499373 – Started implementation via action command
- 2026-05-12T13:36:30Z – claude:sonnet:implementer-ivan:implementer – shell_pid=499373 – WP01 ready: hermetic invocation in release-gate docs + preflight helper + gate-module wiring + regression test. Audit table at kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/audit/wp01-pytest-refs.md.
- 2026-05-12T13:37:39Z – claude:opus:reviewer:reviewer – shell_pid=510816 – Started review via action command
- 2026-05-12T13:39:59Z – claude:opus:reviewer:reviewer – shell_pid=510816 – Review passed: FR-001 hermetic invocation verified (3 release-gate refs in docs/migration/ replaced with uv run python -m pytest; zero release-gate uv run pytest refs in .github/, mission templates, or commands/review/). FR-002 preflight assert_pytest_available wired into review_mission() before any gate runs; T005 negative test uses real bare venv via venv.create(with_pip=False), not mocked. T001 audit complete and accurate. test_review.py modification is minimal (3 lines: recognize import-pytest probe in _fake_run and return success); no scope expansion.
