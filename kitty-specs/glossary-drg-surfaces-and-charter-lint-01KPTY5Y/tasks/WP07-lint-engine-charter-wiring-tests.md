---
work_package_id: WP07
title: LintEngine, Charter Wiring, and Tests
dependencies:
- WP03
- WP04
requirement_refs:
- C-003
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- FR-018
- FR-024
- NFR-002
- NFR-003
- NFR-005
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/charter_lint/engine.py
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/charter_lint/engine.py
- src/specify_cli/cli/commands/charter.py
- tests/specify_cli/charter_lint/test_engine.py
- tests/specify_cli/cli/commands/test_charter_lint.py
tags: []
---

# WP07 — LintEngine, Charter Wiring, and Tests

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP07 --agent <name>`

**⚠ Dependencies**:
- WP03 must be approved: `GlossaryEntityPageRenderer` and `generate_glossary_entity_pages()` must be importable from `specify_cli.glossary.entity_pages`
- WP04 must be approved: all four checker classes must be importable from `specify_cli.charter_lint`

## Objective

Three deliverables:
1. **`LintEngine`** in `src/specify_cli/charter_lint/engine.py` — orchestrates the four checkers, times the run, writes `lint-report.json`
2. **Charter.py wiring** — two additions to `src/specify_cli/cli/commands/charter.py`:
   - Entity page generation hook after `ensure_charter_bundle_fresh()` call sites
   - `spec-kitty charter lint` CLI subcommand with all flags
3. **Tests** — `LintEngine` unit tests + CLI integration tests

## Context

### `charter.py` layout

`src/specify_cli/cli/commands/charter.py` is large (~1300 lines). Before editing, read it fully and understand:
- Where the `app` Typer group is defined
- Where `ensure_charter_bundle_fresh()` is called (line ~83 and possibly others)
- How other subcommands (`compile`, `interview`, etc.) are registered — follow the same pattern for `lint`

**Do not** reorganize or clean up unrelated parts of `charter.py`. Surgical additions only.

### `LintEngine` contract

```python
class LintEngine:
    def __init__(self, repo_root: Path, staleness_threshold_days: int = 90) -> None: ...

    def run(
        self,
        feature_scope: str | None = None,
        checks: set[str] | None = None,  # None = all four
        min_severity: str = "low",
    ) -> DecayReport:
        """Run requested checkers, time the run, write lint-report.json, return DecayReport."""
```

### `lint-report.json` path

```python
report_path = repo_root / ".kittify" / "lint-report.json"
```

---

## Subtask T033 — `LintEngine` in `engine.py`

**File**: `src/specify_cli/charter_lint/engine.py` (new)

```python
from __future__ import annotations
import datetime
import json
import logging
import time
from pathlib import Path

from .findings import DecayReport, LintFinding
from .checks.orphan import OrphanChecker
from .checks.contradiction import ContradictionChecker
from .checks.staleness import StalenessChecker
from .checks.reference_integrity import ReferenceIntegrityChecker
from ._drg import load_merged_drg

logger = logging.getLogger(__name__)

_ALL_CHECKS = {"orphans", "contradictions", "staleness", "reference_integrity"}

_CHECK_MAP = {
    "orphans":             OrphanChecker,
    "contradictions":      ContradictionChecker,
    "staleness":           StalenessChecker,
    "reference_integrity": ReferenceIntegrityChecker,
}


class LintEngine:
    def __init__(self, repo_root: Path, staleness_threshold_days: int = 90) -> None:
        self._repo_root = repo_root
        self._staleness_days = staleness_threshold_days

    def run(
        self,
        feature_scope: str | None = None,
        checks: set[str] | None = None,
        min_severity: str = "low",
    ) -> DecayReport:
        active_checks = checks if checks is not None else _ALL_CHECKS
        unknown = active_checks - _ALL_CHECKS
        if unknown:
            raise ValueError(f"Unknown check categories: {unknown}")

        drg = load_merged_drg(self._repo_root)
        if drg is None:
            logger.warning("LintEngine: merged DRG not found — returning empty report")
            return DecayReport(
                findings=[],
                scanned_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                feature_scope=feature_scope,
                duration_seconds=0.0,
                drg_node_count=0,
                drg_edge_count=0,
            )

        t0 = time.monotonic()
        all_findings: list[LintFinding] = []

        for check_name in sorted(active_checks):
            checker_cls = _CHECK_MAP[check_name]
            kwargs = {}
            if check_name == "staleness":
                kwargs["staleness_threshold_days"] = self._staleness_days
            checker = checker_cls(**kwargs)
            try:
                findings = checker.run(drg, feature_scope=feature_scope)
                all_findings.extend(findings)
            except Exception as exc:
                logger.exception("Checker %s failed: %s", check_name, exc)

        duration = time.monotonic() - t0

        report = DecayReport(
            findings=all_findings,
            scanned_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            feature_scope=feature_scope,
            duration_seconds=round(duration, 3),
            drg_node_count=len(list(drg.nodes)),
            drg_edge_count=len(list(drg.edges)),
        )

        if min_severity != "low":
            report = report.filter_by_severity(min_severity)

        # Persist report
        try:
            report_path = self._repo_root / ".kittify" / "lint-report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report.to_json(), encoding="utf-8")
        except OSError as exc:
            logger.warning("LintEngine: could not write lint-report.json: %s", exc)

        return report
```

---

## Subtask T034 — Entity Page Generation Hook in `charter.py`

**File**: `src/specify_cli/cli/commands/charter.py`

**Purpose**: After each `ensure_charter_bundle_fresh()` call site, add a non-blocking call to generate entity pages.

**Step 1**: Find all call sites. Search `charter.py` for `ensure_charter_bundle_fresh`. There is at least one at line ~83.

**Step 2**: After each call site, add:
```python
# Generate glossary entity pages (non-blocking; silent on failure)
try:
    from specify_cli.glossary.entity_pages import GlossaryEntityPageRenderer
    GlossaryEntityPageRenderer(repo_root).generate_all()
except Exception as _ep_exc:  # noqa: BLE001
    logger.debug("entity page generation failed (non-fatal): %s", _ep_exc)
```

Use a lazy import inside the `try` block to avoid import-time failures if WP03's module is not yet available in the deployment environment.

**Important**: `repo_root` is the variable holding the repository root `Path` at each call site. Inspect the surrounding code to identify the correct variable name. Do not guess — read the code.

---

## Subtask T035 — `charter lint` CLI Subcommand in `charter.py`

**File**: `src/specify_cli/cli/commands/charter.py`

**Purpose**: Add a `lint` subcommand to the `app` Typer group.

```python
@app.command("lint")
def charter_lint(
    feature: str | None = typer.Option(None, "--feature", help="Scope lint to a specific feature slug"),
    orphans: bool = typer.Option(False, "--orphans", help="Run only orphan checks"),
    contradictions: bool = typer.Option(False, "--contradictions", help="Run only contradiction checks"),
    stale: bool = typer.Option(False, "--stale", help="Run only staleness checks"),
    output_json: bool = typer.Option(False, "--json", help="Output findings as JSON"),
    severity: str = typer.Option("low", "--severity", help="Minimum severity (low/medium/high/critical)"),
    repo_root_opt: Path | None = typer.Option(None, "--repo-root", envvar="SPEC_KITTY_REPO_ROOT"),
) -> None:
    """Detect decay in charter artifacts via graph-native checks."""
    from specify_cli.charter_lint import LintEngine
    from specify_cli.repo import find_repo_root  # or equivalent helper

    repo_root = repo_root_opt or find_repo_root(Path.cwd())

    # Resolve which checks to run
    explicit = {k for k, v in [("orphans", orphans), ("contradictions", contradictions), ("staleness", stale)] if v}
    active_checks = explicit if explicit else None  # None = all

    engine = LintEngine(repo_root)
    report = engine.run(
        feature_scope=feature,
        checks=active_checks,
        min_severity=severity,
    )

    if output_json:
        import sys
        sys.stdout.write(report.to_json())
        sys.stdout.write("\n")
        return

    # Human-readable output
    if not report.findings:
        console.print("[green]✓ No decay detected[/green]")
        console.print(f"[dim]Scanned {report.drg_node_count} nodes in {report.duration_seconds:.2f}s[/dim]")
        return

    console.print(f"\n[bold]Charter Lint[/bold] — {len(report.findings)} finding(s) in {report.duration_seconds:.2f}s\n")
    for finding in report.findings:
        severity_color = {"low": "dim", "medium": "yellow", "high": "red", "critical": "red bold"}.get(finding.severity, "white")
        console.print(f"  [{severity_color}][{finding.severity.upper()}][/{severity_color}] "
                      f"[{finding.category}] {finding.type}: {finding.id}")
        console.print(f"    {finding.message}")
        if finding.remediation_hint:
            console.print(f"    [dim]→ {finding.remediation_hint}[/dim]")
```

Place this command at the end of `charter.py`'s command section, after existing commands. Follow whatever import/console pattern the existing commands use.

---

## Subtask T036 — `LintEngine` Tests

**File**: `tests/specify_cli/charter_lint/test_engine.py` (new)

**4-decay fixture DRG**: Build a fixture DRG with exactly one manufactured decay per category:
- One orphan ADR (zero incoming edges)
- Two ADRs with same topic URN, different decision text
- One synthesized artifact with `corpus_snapshot_timestamp` 91 days ago
- One WP with `references_adr` edge to an ADR that has a `replaces` edge

**Scenarios**:

1. **All 4 categories detected**: Run `LintEngine(repo_root).run()` against the fixture. Assert `len(report.findings) >= 4` (one per category at minimum). Assert `report.duration_seconds < 5.0`. Assert `report.drg_node_count > 0`.

2. **`lint-report.json` written**: Assert `.kittify/lint-report.json` exists after `run()`. Assert `json.loads(path.read_text())` succeeds (NFR-005).

3. **Single check filter**: `run(checks={"orphans"})`. Assert all findings have `category == "orphan"`. Assert `contradiction`, `staleness`, `reference_integrity` not in finding categories.

4. **Severity filter**: `run(min_severity="high")`. Assert no findings with `severity in {"low", "medium"}`.

5. **Feature scope**: `run(feature_scope="042-my-feature")`. Assert all returned findings have `feature_id == "042-my-feature"` or are not scoped.

6. **Missing DRG**: Pass `repo_root` with no `.kittify/doctrine/`. Assert returns `DecayReport(findings=[], ...)` with `drg_node_count=0`. No exception raised.

7. **No LLM calls**: Mock the Anthropic client (if present in scope); assert it is never called. (This enforces NFR-003 / C-003.)

8. **500-node fixture**: Assert `run()` completes in <5 seconds on a 500-node DRG with synthetic decay.

---

## Subtask T037 — CLI Integration Tests for `charter lint`

**File**: `tests/specify_cli/cli/commands/test_charter_lint.py` (new)

**Scenarios** (use Typer `CliRunner`):

1. **`--json` output is valid JSON**: Run `charter lint --json` against fixture repo. Assert exit code 0. Assert `json.loads(result.output)` succeeds. Assert output has no leading/trailing text outside the JSON object (NFR-005).

2. **`--severity high` filters**: Run with `--severity high`. Assert no finding in output with severity `low` or `medium`.

3. **`--feature <id>` scopes**: Run with `--feature 042`. Assert findings in output are scoped to that feature (or assert the command completes without error on an empty scope).

4. **`--orphans` only**: Run with `--orphans`. Assert the human-readable output only mentions orphan-category findings.

5. **No DRG → no error**: Run in a repo with no compiled DRG. Assert exit code 0. Assert output contains "No decay detected" or equivalent.

---

## Branch Strategy

- **Planning base branch**: `main` (post WP03 + WP04 merge)
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP07 --agent <name>`.

---

## Definition of Done

- [ ] `LintEngine.run()` orchestrates all four checkers from WP04 and returns a `DecayReport`
- [ ] `lint-report.json` is written after every run (readable by WP05)
- [ ] `spec-kitty charter lint` CLI command available with all flags (`--feature`, `--orphans`, `--contradictions`, `--stale`, `--json`, `--severity`)
- [ ] `--json` output is valid JSON, parseable by `json.loads()` with no extra text
- [ ] Entity page generation hook added after `ensure_charter_bundle_fresh()` in `charter.py`
- [ ] Hook is wrapped in `try/except` — never raises, logs debug on failure
- [ ] All 8 engine test scenarios pass: `pytest tests/specify_cli/charter_lint/test_engine.py`
- [ ] All 5 CLI integration test scenarios pass: `pytest tests/specify_cli/cli/commands/test_charter_lint.py`
- [ ] `ruff check src/specify_cli/charter_lint/engine.py src/specify_cli/cli/commands/charter.py` passes
- [ ] No LLM client imported or called anywhere in `charter_lint/`

---

## Reviewer Guidance

1. **`charter.py` is large** — confirm the `lint` command is placed cleanly, follows existing command style, and does not accidentally shadow or conflict with another command name.
2. **Entity page hook**: confirm it is *after* `ensure_charter_bundle_fresh()` returns (not before) and is in `try/except`. Confirm `repo_root` variable is the correct in-scope variable at each call site.
3. **`--json` flag naming**: Typer uses `--json` but the Python parameter must be `output_json` (since `json` is a stdlib import). Confirm the flag name in the CLI is `--json` as specified.
4. **`lint-report.json` is always written** even when there are zero findings — WP05's `has_data: true` path depends on this.
5. Confirm `StalenessChecker` is instantiated with `staleness_threshold_days` from `LintEngine.__init__` — not hardcoded in the engine.
