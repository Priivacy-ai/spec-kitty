---
work_package_id: WP04
title: Baseline Test Capture
dependencies: []
requirement_refs:
- FR-012
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-066-review-loop-stabilization
base_commit: 4dbb05e1ae46b17dad6ae64402cfb2861107f268
created_at: '2026-04-06T16:42:33.087254+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
shell_pid: "51798"
agent: "claude:opus-4-6:reviewer:reviewer"
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/baseline.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/baseline.py
- tests/review/test_baseline.py
---

# WP04: Baseline Test Capture

## Objective

Capture baseline test results at implement time (before the agent starts coding) and surface the baseline-vs-current test delta in review prompts so reviewers can distinguish pre-existing failures from newly introduced regressions.

**Issues**: [#444](https://github.com/Priivacy-ai/spec-kitty/issues/444)
**Dependencies**: None

## Context

### Current Problem

Reviewers reject WPs for test failures that predated the WP implementation. Without baseline context, reviewers over-attribute any failing test to the WP under review, creating false-positive rejections and arbiter overhead. This was observed repeatedly during Features 064 and 065.

### Target Behavior

At implement time, the system captures baseline test results by running the test suite on the base branch. Results are cached as a committed artifact (`baseline-tests.json`). At review time, the review prompt includes a "Baseline Context" section showing which failures are pre-existing vs. newly introduced.

### Design Decisions

- **Capture timing**: Implement time (inside `agent action implement`), not claim time. The claim transition runs in the planning context which may lack test dependencies and the worktree.
- **Output format**: JUnit XML via `pytest --junitxml=<tmpfile>`, parsed via `xml.etree.ElementTree` (stdlib). No extra plugins needed.
- **Non-pytest projects**: Configure `review.test_command` in `.kittify/config.yaml`. No auto-detection.
- **Artifact format**: Structured JSON with test name, status, one-line error for failures only. No raw stdout/stderr.

### Integration Points

This WP modifies `workflow.py` in two places:
- Implement path (lines 526-662): hook `capture_baseline()` before agent starts coding
- Review prompt (lines 1190-1310): add Baseline Context section with `diff_baseline()`

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: allocated per lane (independent lane)

## Subtask Details

### T017: Create baseline.py with dataclasses

**Purpose**: Define the data model for baseline test results.

**Steps**:
1. Create `src/specify_cli/review/baseline.py`
2. Define dataclasses:
   ```python
   @dataclass(frozen=True)
   class TestFailure:
       test: str       # fully qualified test name
       error: str      # one-line error summary
       file: str       # file:line

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> TestFailure: ...

   @dataclass(frozen=True)
   class BaselineTestResult:
       wp_id: str
       captured_at: str        # ISO 8601 UTC
       base_branch: str
       base_commit: str        # 7-40 hex chars
       test_runner: str        # "pytest", "custom"
       total: int
       passed: int
       failed: int
       skipped: int
       failures: list[TestFailure]

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> BaselineTestResult: ...
       @classmethod
       def load(cls, path: Path) -> BaselineTestResult | None: ...
       def save(self, path: Path) -> None: ...
   ```
3. `save()` writes JSON via `json.dumps(self.to_dict(), indent=2)`
4. `load()` returns None if file doesn't exist, raises on malformed JSON

### T018: Implement capture_baseline()

**Purpose**: Run the test suite on the base branch and parse results.

**Steps**:
1. Implement the capture function:
   ```python
   def capture_baseline(
       worktree_path: Path,
       base_branch: str,
       wp_id: str,
       mission_slug: str,
       feature_dir: Path,
       wp_slug: str,
       test_command: str | None = None,
   ) -> BaselineTestResult | None:
   ```

2. **Execution flow**:
   - Check if `baseline-tests.json` already exists in the WP sub-artifact dir → if yes, skip capture (return cached)
   - Get current commit hash of base_branch: `git rev-parse {base_branch}`
   - Create a temporary worktree on base_branch: `git worktree add <tmpdir> {base_branch} --detach`
   - Run `pytest --junitxml=<tmpfile>` in the temporary worktree (or custom test_command from config)
   - Parse the JUnit XML output
   - Remove the temporary worktree: `git worktree remove <tmpdir>`
   - Save result to `feature_dir/tasks/{wp_slug}/baseline-tests.json`
   - Return the BaselineTestResult

3. **JUnit XML parsing** (using `xml.etree.ElementTree`):
   ```python
   import xml.etree.ElementTree as ET

   tree = ET.parse(junit_xml_path)
   root = tree.getroot()
   failures = []
   total = passed = failed = skipped = 0

   for testcase in root.iter("testcase"):
       total += 1
       failure = testcase.find("failure")
       error = testcase.find("error")
       skip = testcase.find("skipped")

       if failure is not None or error is not None:
           failed += 1
           msg = (failure or error).get("message", "Unknown error")
           # Truncate to one line
           msg = msg.split("\n")[0][:200]
           failures.append(TestFailure(
               test=f"{testcase.get('classname')}.{testcase.get('name')}",
               error=msg,
               file=testcase.get("file", "unknown") + ":" + testcase.get("line", "?"),
           ))
       elif skip is not None:
           skipped += 1
       else:
           passed += 1
   ```

4. **Error handling**: If test suite fails to run (missing deps, broken env), create a sentinel result with `failed=-1` and `failures=[]`, log a warning, and proceed. Do NOT block implementation.

### T019: Implement load_baseline() and diff_baseline()

**Purpose**: Read cached baseline and compute pre-existing vs. new failure diff.

**Steps**:
1. `load_baseline()` is already defined as a classmethod on BaselineTestResult (T017)

2. Implement `diff_baseline()`:
   ```python
   def diff_baseline(
       baseline: BaselineTestResult,
       current_failures: list[TestFailure],
   ) -> tuple[list[TestFailure], list[TestFailure], list[str]]:
       """Compare baseline failures against current failures.

       Returns:
           pre_existing: failures that existed in baseline
           new_failures: failures NOT in baseline (regressions)
           fixed: test names that failed in baseline but pass now
       """
   ```

3. Match by test name (fully qualified):
   - If a test fails in both baseline and current → pre_existing
   - If a test fails in current but not baseline → new_failure (regression)
   - If a test failed in baseline but not current → fixed

4. Handle sentinel baseline (`failed=-1`): treat everything as new (no baseline data)

### T020: Hook capture_baseline() into implement path

**Purpose**: Capture baseline before the agent starts coding.

**Steps**:
1. In `workflow.py`, in the implement action (around lines 526-662), after the workspace is resolved and before the WP prompt is output:
   ```python
   # Capture baseline test results (one-time, cached)
   from specify_cli.review.baseline import capture_baseline
   baseline = capture_baseline(
       worktree_path=workspace_path,
       base_branch=base_branch,
       wp_id=normalized_wp_id,
       mission_slug=mission_slug,
       feature_dir=feature_dir,
       wp_slug=wp_slug,
   )
   if baseline and baseline.failed > 0:
       console.print(f"[dim]Baseline: {baseline.failed} pre-existing test failure(s) captured[/dim]")
   elif baseline and baseline.failed == -1:
       console.print("[yellow]Warning: baseline test capture failed — no baseline context available[/yellow]")
   ```

2. The capture only runs if `baseline-tests.json` doesn't already exist (cached from prior implement)

3. Git-commit the baseline artifact after writing (using existing safe-commit pattern)

### T021: Hook diff_baseline() into review prompt

**Purpose**: Add a Baseline Context section to review prompts.

**Steps**:
1. In `workflow.py` review() function (around lines 1190-1310), after the git review context section:
   ```python
   from specify_cli.review.baseline import BaselineTestResult

   baseline_path = feature_dir / "tasks" / wp_slug / "baseline-tests.json"
   baseline = BaselineTestResult.load(baseline_path)
   if baseline and baseline.failed > 0:
       # Add baseline context section
       output += "\n## Baseline Test Context\n\n"
       output += f"**{baseline.failed} test failure(s) existed BEFORE this WP** (base: {baseline.base_branch} @ {baseline.base_commit[:7]}):\n\n"
       output += "| Test | Error | File |\n|------|-------|------|\n"
       for f in baseline.failures:
           output += f"| {f.test} | {f.error[:80]} | {f.file} |\n"
       output += "\n**These failures are NOT regressions introduced by this WP.** Only flag test failures that are NOT in this list.\n"
   elif baseline and baseline.failed == -1:
       output += "\n## Baseline Test Context\n\n"
       output += "**Warning**: Baseline test capture failed at implement time. Cannot distinguish pre-existing failures from regressions. Exercise caution when attributing test failures to this WP.\n"
   ```

2. If no baseline artifact exists, skip the section (don't add it at all)

### T022: Add review.test_command config support

**Purpose**: Allow non-pytest projects to configure their test command.

**Steps**:
1. In `baseline.py`, read config from `.kittify/config.yaml`:
   ```python
   def _get_test_command(repo_root: Path) -> tuple[str, str]:
       """Get test command and output format from config.

       Returns (command_template, output_format).
       Default: ("pytest --junitxml={output_file}", "junit_xml")
       """
       config_path = repo_root / ".kittify" / "config.yaml"
       if config_path.exists():
           yaml = YAML()
           config = yaml.load(config_path)
           review_config = config.get("review", {})
           if "test_command" in review_config:
               return (
                   review_config["test_command"],
                   review_config.get("test_output_format", "junit_xml"),
               )
       return (f"pytest --junitxml={{output_file}}", "junit_xml")
   ```

2. Use `{output_file}` as a placeholder in the command template, substituted at runtime

3. For now, only `junit_xml` output format is supported. Other formats can be added later.

### T023: Write tests

**Test file**: `tests/review/test_baseline.py`

**Required test cases**:
1. `test_baseline_test_result_round_trip` — save and load JSON, compare fields
2. `test_capture_baseline_creates_artifact` — mock subprocess, verify JSON artifact created
3. `test_capture_baseline_skips_if_cached` — artifact already exists, no subprocess call
4. `test_capture_baseline_handles_failure` — subprocess fails, sentinel result created
5. `test_junit_xml_parsing` — parse a sample JUnit XML file, verify TestFailure extraction
6. `test_diff_baseline_pre_existing` — failure in both baseline and current → pre_existing
7. `test_diff_baseline_new_regression` — failure only in current → new_failure
8. `test_diff_baseline_fixed` — failure in baseline, passes now → fixed
9. `test_diff_baseline_sentinel` — sentinel baseline (failed=-1), all current failures are "new"
10. `test_review_prompt_includes_baseline_section` — baseline context appears in review prompt
11. `test_config_custom_test_command` — config overrides default pytest command

**Coverage target**: 90%+ for `src/specify_cli/review/baseline.py`

## Definition of Done

- [ ] capture_baseline() runs pytest --junitxml and parses JUnit XML correctly
- [ ] Baseline artifact cached — second implement doesn't re-run tests
- [ ] diff_baseline() correctly classifies pre-existing vs. new failures
- [ ] Review prompt includes Baseline Context section with pre-existing failures
- [ ] Graceful handling when test suite fails to run (sentinel + warning)
- [ ] Non-pytest config option works
- [ ] 90%+ test coverage on baseline.py
- [ ] All existing tests pass

## Reviewer Guidance

- Verify JUnit XML parsing handles edge cases (missing attributes, nested testsuites)
- Check that temporary worktree is always cleaned up, even on failure (use try/finally)
- Verify baseline artifact stays small (structured JSON, no raw output)
- Confirm capture happens at implement time, NOT claim time

## Activity Log

- 2026-04-06T16:42:33Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48037 – Started implementation via action command
- 2026-04-06T16:49:35Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48037 – Ready for review: baseline test capture implemented with JUnit XML parsing, diff_baseline, workflow.py hooks, and 91% test coverage (30 tests)
- 2026-04-06T16:50:13Z – claude:opus-4-6:reviewer:reviewer – shell_pid=51798 – Started review via action command
