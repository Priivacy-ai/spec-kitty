---
work_package_id: WP01
title: Stale-Assertion Analyzer
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-022
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-068-post-merge-reliability-and-release-hardening
base_commit: e361b104cbecf8fb24bf8c9f504d0f0868c14492
created_at: '2026-04-07T09:17:25.969482+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
shell_pid: "62766"
agent: "claude:sonnet:reviewer:reviewer"
history:
- at: '2026-04-07T08:46:34Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/post_merge/
execution_mode: code_change
mission_number: '068'
mission_slug: 068-post-merge-reliability-and-release-hardening
owned_files:
- src/specify_cli/post_merge/**
- src/specify_cli/cli/commands/agent/tests.py
- src/specify_cli/cli/commands/agent/__init__.py
- tests/post_merge/**
- tests/cli/commands/agent/test_tests_stale_check.py
priority: P1
status: planned
---

# WP01 — Stale-Assertion Analyzer

## Objective

Build the post-merge stale-assertion analyzer for issue [Priivacy-ai/spec-kitty#454](https://github.com/Priivacy-ai/spec-kitty/issues/454). The analyzer compares two git refs (typically `merge-base` and `HEAD`) and emits a structured report listing test assertions likely invalidated by merged source changes. It uses Python's stdlib `ast` module on **both** source and test files (no regex, no `libcst`, no `tree-sitter`). It ships as both a library function and a new `agent tests stale-check` CLI subcommand. The merge runner imports the library function directly — no subprocess.

## Context

This WP closes one of the four primary-scope issues in the mission. The library and CLI are new code; the only modification to existing files is registering the new `agent tests` typer subapp in `agent/__init__.py`.

**Key spec references**:
- FR-001: structured report listing likely-stale assertions
- FR-002: AST on both sides; never regex on test text; no test-suite load
- FR-003: confidence indicators `high`/`medium`/`low`; never `definitely_stale`
- FR-004: locked CLI path `spec-kitty agent tests stale-check --base <ref> --head <ref>`; library imported directly by merge runner
- FR-022: NFR-002 fallback — narrow scope if FP ceiling exceeded
- NFR-001: ≤ 30 seconds wall-clock on spec-kitty core
- NFR-002: ≤ 5 false-positive findings per 100 LOC of merged change

**Key planning references**:
- `plan.md` source-tree section for the new package layout
- `research.md` Decision 1 for the library-choice rationale (`ast` on both sides)
- `contracts/stale_assertions.md` for the full library + CLI signatures and the test surface table
- `data-model.md` for `StaleAssertionFinding` and `StaleAssertionReport` shapes

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP01` and resolved from `lanes.json`. Do NOT reconstruct paths manually.

To start work:
```bash
spec-kitty implement WP01
```

The command prints the resolved workspace path. `cd` into it before editing.

## Subtasks

### T001 — Create the `post_merge/` package skeleton

**Purpose**: Lay down the new package with module docstring, the two dataclasses, and a stub `run_check` so subsequent subtasks have a concrete file to populate.

**Files to create**:
- `src/specify_cli/post_merge/__init__.py` — re-exports `run_check`, `StaleAssertionFinding`, `StaleAssertionReport`; sets `__all__`
- `src/specify_cli/post_merge/stale_assertions.py` — module with the two `@dataclass(frozen=True)` types from `data-model.md` and a `run_check` stub that raises `NotImplementedError`

**Steps**:
1. `mkdir -p src/specify_cli/post_merge` and create `__init__.py`
2. Define `StaleAssertionFinding` per `data-model.md` (test_file, test_line, source_file, source_line, changed_symbol, confidence, hint)
3. Define `StaleAssertionReport` per `data-model.md` (base_ref, head_ref, repo_root, findings, elapsed_seconds, files_scanned, findings_per_100_loc)
4. Stub `run_check(base_ref, head_ref, repo_root) -> StaleAssertionReport` that raises `NotImplementedError("WP01 T002+")`
5. Re-export from `__init__.py`

**Validation**: `python -c "from specify_cli.post_merge import run_check, StaleAssertionFinding, StaleAssertionReport"` succeeds.

### T002 — Source-side AST identifier and literal extraction

**Purpose**: Walk the diff between `base_ref` and `head_ref`, parse the changed Python source files with `ast`, and collect the changed identifiers (function names, class names) and changed string literal values.

**Steps**:
1. Use `subprocess.run(["git", "diff", "--name-only", base_ref, head_ref, "--", "*.py"], ...)` to enumerate changed Python source files (exclude `tests/` paths from this side)
2. For each changed file, get the content at both `base_ref` and `head_ref` via `git show`
3. Parse both versions with `ast.parse(...)`
4. Walk both trees and compute the diff:
   - Function/class names removed (defined in base, missing in head) → "renamed away" identifiers
   - String `Constant` values removed from a file's set of literals → changed literals
5. Return a `ChangedSymbols` data structure (internal helper) containing both lists with their source file + line number

**Files**: `src/specify_cli/post_merge/stale_assertions.py` (extend existing skeleton)

**Validation**: an internal helper `_extract_changed_symbols(base_ref, head_ref, repo_root)` returns the expected identifier lists for a synthetic 2-commit fixture.

### T003 — Test-side AST scan in assertion-bearing positions

**Purpose**: For every test file in the repo, parse with `ast` and find references to changed identifiers in positions that look like assertions.

**Steps**:
1. Use `subprocess.run(["git", "ls-files", "tests/**/*.py"], ...)` to enumerate test files
2. For each test file, parse with `ast.parse(...)` (handle `SyntaxError` gracefully — skip the file with a warning, do not abort)
3. Walk the AST looking for these node patterns:
   - `Assert(test=...)` — pytest-style bare `assert`
   - `Compare(left=..., ops=..., comparators=...)` inside an `Assert` test or a `Call(func=Attribute(attr='assert*'))`
   - `Call(func=Attribute(attr='assertEqual'|'assertTrue'|'assertFalse'|'assertIn'|...))` — unittest-style
4. Within each match, look for `Name(id=...)` or `Attribute(attr=...)` referencing a changed function/class identifier, OR `Constant(value=...)` matching a changed string literal
5. Emit `StaleAssertionFinding` records for each match

**Critical**: do NOT scan raw text. The whole point of the AST approach is that comments and inert string literals (e.g., docstrings) MUST NOT be matched. If you find yourself reaching for `re` to search test file content, stop — that's the FP-bleed path FR-002 explicitly bans.

**Files**: `src/specify_cli/post_merge/stale_assertions.py`

**Validation**: an internal helper `_scan_test_file(test_path, changed_symbols)` returns the expected findings for a synthetic test file with both real assertions and decoy comments.

### T004 — Implement `run_check()` orchestration and confidence assignment

**Purpose**: Wire T002 + T003 into the public `run_check(...)` function. Assign confidence indicators per the contract. Populate the report metadata fields.

**Steps**:
1. In `run_check(base_ref, head_ref, repo_root)`:
   - Capture `start_time = time.monotonic()`
   - Call `_extract_changed_symbols(base_ref, head_ref, repo_root)`
   - Call `_scan_test_file(...)` for every test file from `git ls-files 'tests/**/*.py'`
   - Compute confidence per finding using the rules from `contracts/stale_assertions.md`:
     - `high`: changed function/class name appears as `Attribute(attr=...)` or `Name(id=...)` directly inside `Assert` or `assert*` call
     - `medium`: changed identifier appears in any `Compare`/`Assert` node
     - `low`: changed string literal matches a `Constant(value=...)` in an assertion-bearing position
   - Compute `elapsed_seconds = time.monotonic() - start_time`
   - Compute `files_scanned` (count of test files parsed successfully)
   - Compute `findings_per_100_loc` against the `git diff --shortstat` line count
2. Return the populated `StaleAssertionReport`

**Forbidden**: never produce a `definitely_stale` confidence value (FR-003).

**Files**: `src/specify_cli/post_merge/stale_assertions.py`

**Validation**: a synthetic 3-commit fixture produces the expected report shape with at least one `high`, one `medium`, and one `low` finding.

### T005 — New `agent tests` CLI subapp + `stale-check` command + register

**Purpose**: Expose the analyzer via the locked CLI path `spec-kitty agent tests stale-check --base <ref> --head <ref>`. Register the new typer subapp in `agent/__init__.py`.

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/tests.py` with a typer.Typer named `tests`, help text "Test-related commands for AI agents", and `no_args_is_help=True`
2. Define `@app.command("stale-check")` per `contracts/stale_assertions.md`:
   - `--base <ref>` (required)
   - `--head <ref>` (default `"HEAD"`)
   - `--repo <path>` (default `Path(".")`)
   - `--json` flag
3. Inside the command, call `run_check(base_ref=base, head_ref=head, repo_root=repo_root.resolve())`
4. If `--json`, render via `dataclasses.asdict` and print as JSON
5. Otherwise, render as a rich-formatted table grouped by confidence
6. In `src/specify_cli/cli/commands/agent/__init__.py`, add `tests` to the import line at the top of the file and add `app.add_typer(tests.app, name="tests")` after the existing registrations

**Files**:
- New: `src/specify_cli/cli/commands/agent/tests.py`
- Modified: `src/specify_cli/cli/commands/agent/__init__.py`

**Validation**: `spec-kitty agent tests stale-check --help` returns help text. `spec-kitty agent tests stale-check --base HEAD~1 --head HEAD` runs successfully against the current repo.

### T006 — Test suite for FR-001/002/003/004 + NFR-001/002 + FR-022 fallback

**Purpose**: Lock the contracts with pytest. Use a fixture that builds synthetic git repos for deterministic testing.

**Files to create**:
- `tests/post_merge/__init__.py` (empty)
- `tests/post_merge/test_stale_assertions.py`
- `tests/cli/commands/agent/test_tests_stale_check.py`

**Tests** (per `contracts/stale_assertions.md` test surface table):
- `test_renamed_function_flagged_high_confidence`
- `test_changed_string_literal_flagged_low_confidence`
- `test_string_literal_in_comment_not_flagged` (FR-002 worked example)
- `test_unchanged_use_of_string_not_flagged` (FR-002 worked example)
- `test_no_test_suite_load` — assert `run_check` does not import or execute any test file as Python (mock `importlib`)
- `test_no_definitely_stale_confidence` — assert no finding has confidence `"definitely_stale"`
- `test_cli_subcommand_invokes_library` — assert the CLI command calls `run_check` (use a mock)
- `test_merge_runner_will_import_library_directly` — assert `run_check` is importable from `specify_cli.post_merge`; the actual merge runner integration is tested in WP02
- `test_runs_within_30s_on_synthetic_large_repo` (NFR-001 benchmark)
- `test_fp_ceiling_under_5_per_100_loc_on_curated_benchmark` (NFR-002)
- `test_fr_022_fallback_warns_when_fp_exceeds_ceiling`

**Validation**: `pytest tests/post_merge tests/cli/commands/agent/test_tests_stale_check.py -v` exits zero. No network calls.

### T007 — `--json` output mode + NFR-005 zero-network assertion

**Purpose**: Lock the JSON output mode for downstream automation and assert that the analyzer makes zero network calls.

**Steps**:
1. In `tests.py` CLI command, when `--json` is true, use `dataclasses.asdict(report)` and print via `console.print_json(json.dumps(...))`
2. In `test_stale_assertions.py`, add a `test_no_network_calls` test that monkeypatches `urllib.request.urlopen` and `requests.get` (if requests is even imported) to raise on call, then runs `run_check(...)` and asserts no exception
3. The CLI test uses typer's `CliRunner` to invoke `stale-check --base HEAD~1 --head HEAD --json` and asserts the output parses as JSON with the expected fields

**Files**: extends `tests.py`, `test_stale_assertions.py`, `test_tests_stale_check.py`

**Validation**: the JSON output round-trips through `json.loads` and contains all `StaleAssertionReport` fields.

## Test Strategy

Tests are explicitly required by the spec (FR-001..FR-004, FR-022, NFR-001, NFR-002). All tests live under `tests/post_merge/` and `tests/cli/commands/agent/`. Use synthetic git fixtures (`tmp_path` + `subprocess.run(["git", "init", ...])`) for deterministic behavior. No network access.

## Definition of Done

- [ ] `src/specify_cli/post_merge/` package exists with `__init__.py` re-exporting `run_check`, `StaleAssertionFinding`, `StaleAssertionReport`
- [ ] `run_check(base_ref, head_ref, repo_root)` is fully implemented per `contracts/stale_assertions.md`
- [ ] Source-side AST extraction works (T002 internal helper passes its tests)
- [ ] Test-side AST scan works (T003 internal helper passes its tests)
- [ ] Confidence assignment never produces `definitely_stale` (FR-003)
- [ ] `spec-kitty agent tests stale-check --help` and `--json` both work
- [ ] `agent/__init__.py` registers the new `tests` subapp
- [ ] All FR-001..FR-004, FR-022 tests pass
- [ ] NFR-001 benchmark within 30s on the synthetic large fixture
- [ ] NFR-002 benchmark within 5 FP/100 LOC on the curated benchmark
- [ ] Zero network calls in any test path (mocked `urllib`, `requests`)
- [ ] `mypy --strict` passes on all new modules
- [ ] `ruff` clean

## Risks

- **NFR-002 FP ceiling**: the AST heuristic might still be noisier than 5 FP/100 LOC on real codebases. If so, FR-022 mandates narrowing scope (literal-string changes only, or function-rename only) AND documenting the narrowed scope as a new constraint row in `spec.md` BEFORE requesting review. Do NOT just relax NFR-002.
- **`SyntaxError` on parse**: not every test file is valid Python (e.g., a test that intentionally checks parsing errors with a literal source string). Skip those with a warning, do not abort.
- **Python version skew**: `ast` constants/nodes vary slightly by Python version. Use `ast.Constant` (Python 3.8+) and avoid the deprecated `ast.Str`/`ast.Num`.

## Reviewer Guidance

- Verify the analyzer never reads test file content as raw text — only via `ast.parse`
- Verify the CLI subcommand path is exactly `spec-kitty agent tests stale-check` (not a placeholder)
- Verify `agent/__init__.py` adds `tests` to both the import line AND the `add_typer` registrations
- Verify FR-002's worked-example tests are present and pass
- Verify FR-022's fallback test exists (even if it's a unit test of the warning emission)
- Run the analyzer against current spec-kitty `main` and confirm wall clock < 30s

## Next steps after merge

Once WP01 lands, WP02 can start its T013 subtask (importing `run_check` from `specify_cli.post_merge.stale_assertions` inside `_run_lane_based_merge`).

## Activity Log

- 2026-04-07T09:18:37Z – claude:sonnet:implementer:implementer – shell_pid=42447 – Started implementation via action command
- 2026-04-07T09:34:01Z – claude:sonnet:implementer:implementer – shell_pid=42447 – Ready for review: stale-assertion analyzer implemented with full test suite (24/24 passing, ruff clean)
- 2026-04-07T09:35:05Z – claude:sonnet:reviewer:reviewer – shell_pid=62766 – Started review via action command
- 2026-04-07T09:36:39Z – claude:sonnet:reviewer:reviewer – shell_pid=62766 – Review passed: stale-assertion analyzer complete, 24 tests pass, CLI registered
