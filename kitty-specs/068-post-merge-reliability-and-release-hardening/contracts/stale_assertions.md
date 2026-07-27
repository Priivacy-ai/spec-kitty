# Contract: WP01 Stale-Assertion Analyzer

**Owns**: FR-001, FR-002, FR-003, FR-004, FR-022 + NFR-001, NFR-002

## Library entry point

**Module**: `src/specify_cli/post_merge/stale_assertions.py`

```python
from pathlib import Path
from specify_cli.post_merge.stale_assertions import (
    run_check,
    StaleAssertionFinding,
    StaleAssertionReport,
)

def run_check(
    base_ref: str,
    head_ref: str,
    repo_root: Path,
) -> StaleAssertionReport:
    """Compare base_ref..head_ref and return likely-stale test assertions.

    Algorithm:
      1. git diff base_ref..head_ref -- '*.py' → list of changed source files + line ranges
      2. For each changed file, parse with ast and extract changed identifiers and string literals
      3. For each test file from `git ls-files 'tests/**/*.py'`, parse with ast
      4. Walk test ASTs for Constant/Name nodes referencing changed identifiers in
         assertion-bearing positions (Compare, Assert, Call(func=Attribute(attr='assert*')))
      5. Emit a StaleAssertionFinding for each match with appropriate confidence
      6. Compute findings_per_100_loc against the changed-line count

    Returns: a StaleAssertionReport with findings list, elapsed_seconds, files_scanned,
             and findings_per_100_loc populated.
    """
```

**Re-exported from**: `src/specify_cli/post_merge/__init__.py`:

```python
from .stale_assertions import (
    run_check,
    StaleAssertionFinding,
    StaleAssertionReport,
)

__all__ = ["run_check", "StaleAssertionFinding", "StaleAssertionReport"]
```

## CLI surface

**Command path**: `spec-kitty agent tests stale-check`

**Module**: `src/specify_cli/cli/commands/agent/tests.py`

```python
import typer
from pathlib import Path
from rich.console import Console
from specify_cli.post_merge.stale_assertions import run_check

app = typer.Typer(name="tests", help="Test-related commands for AI agents", no_args_is_help=True)
console = Console()

@app.command("stale-check")
def stale_check(
    base: str = typer.Option(..., "--base", help="Base git ref for the diff"),
    head: str = typer.Option("HEAD", "--head", help="Head git ref for the diff"),
    repo_root: Path = typer.Option(Path("."), "--repo", help="Repository root"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of human-readable text"),
) -> None:
    """Detect test assertions likely invalidated by source changes between two refs."""
    report = run_check(base_ref=base, head_ref=head, repo_root=repo_root.resolve())
    # Render rich text or JSON depending on json_output
```

**Registration**: `src/specify_cli/cli/commands/agent/__init__.py` adds:

```python
from . import tests as tests_module
app.add_typer(tests_module.app, name="tests")
```

## Merge runner integration

**File**: `src/specify_cli/cli/commands/merge.py` inside `_run_lane_based_merge`, after the FR-019 `safe_commit` step and before the merge summary print.

```python
from specify_cli.post_merge.stale_assertions import run_check

# ... after _mark_wp_merged_done loop and after safe_commit (FR-019):
stale_report = run_check(
    base_ref=merge_base_sha,
    head_ref="HEAD",
    repo_root=repo_root,
)
# Append stale_report findings to the merge summary that's printed to console
```

**Wiring contract** (FR-004): the merge runner SHALL invoke `run_check` via direct library import, NOT by spawning the CLI subcommand as a subprocess. The CLI entry and the merge runner are two thin shims around the same library function.

## Confidence assignment rules (FR-003)

| Confidence | Condition |
|---|---|
| `high` | Changed function/class name appears as an `Attribute(attr=...)` or `Name(id=...)` node directly inside an `Assert` test or `assertEqual`/`assertTrue`/etc. call |
| `medium` | Changed identifier appears in any `Compare` or `Assert` node anywhere in the test file |
| `low` | Changed string literal matches a `Constant(value="...")` node in an assertion-bearing position |

**Forbidden**: the analyzer SHALL NEVER produce a `definitely_stale` confidence (FR-003).

## Self-monitoring (FR-022)

After every `run_check` call, the report's `findings_per_100_loc` is checked against `5.0` (the NFR-002 ceiling). If exceeded:

1. The CLI command emits a warning to stderr.
2. The merge runner emits a warning in the merge summary.
3. WP01's tests SHALL include a benchmark that fails the build if the curated benchmark exceeds the ceiling, forcing WP01 to narrow scope per FR-022.

## Test surface

**File**: `tests/post_merge/test_stale_assertions.py`

| Test | FR / NFR | Asserts |
|---|---|---|
| `test_renamed_function_flagged_high_confidence` | FR-001, FR-003 | high-confidence finding for a renamed function reference in a test |
| `test_changed_string_literal_flagged_low_confidence` | FR-001, FR-002 | low-confidence finding for a changed literal that matches a `Constant` node |
| `test_string_literal_in_comment_not_flagged` | FR-002 worked example | comment-only mention of a literal does NOT produce a finding |
| `test_unchanged_use_of_string_not_flagged` | FR-002 worked example | new use of a literal (without modifying any existing literal) does NOT produce a finding |
| `test_no_test_suite_load` | FR-002 | analyzer does not import or execute any test file as code |
| `test_no_definitely_stale_confidence` | FR-003 | output never contains the literal `"definitely_stale"` |
| `test_cli_subcommand_invokes_library` | FR-004 | the CLI subcommand calls `run_check` and prints its findings |
| `test_merge_runner_imports_library_directly` | FR-004 | the merge runner does NOT use `subprocess` to invoke the CLI |
| `test_runs_within_30s_on_spec_kitty_core` | NFR-001 | benchmark fails the build if elapsed > 30s |
| `test_fp_ceiling_under_5_per_100_loc` | NFR-002, FR-022 | benchmark fails if FP rate > 5/100 LOC |
| `test_fr_022_fallback_narrows_scope` | FR-022 | when the FP ceiling is exceeded, the documented fallback path is exercised |
