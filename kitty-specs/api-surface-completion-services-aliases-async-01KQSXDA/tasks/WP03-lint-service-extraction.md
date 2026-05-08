---
work_package_id: WP03
title: LintService Extraction
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-017
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T013
- T014
- T015
- T016
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "1965199"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/specify_cli/charter_lint/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/specify_cli/charter_lint/service.py
- src/dashboard/api/routers/lint.py
- src/specify_cli/dashboard/handlers/lint.py
- tests/specify_cli/charter_lint/test_lint_service.py
- tests/test_dashboard/test_lint_tile_handler.py
tags: []
---

## Objective

Extract the charter-lint router's private helper function `_build_charter_lint` into a proper domain service class `LintService` in `src/specify_cli/charter_lint/service.py`. Delegate the FastAPI router's handler body to the service. Update the legacy `BaseHTTPRequestHandler` in `handlers/lint.py` to import from the new canonical type location. Write parity and unit tests.

## Context

The current `src/dashboard/api/routers/lint.py` contains `_build_charter_lint(project_dir)` — a private helper that reads `.kittify/lint-report.json` and computes the `DecayWatchTileResponse`. The same logic is duplicated in `src/specify_cli/dashboard/handlers/lint.py`. `LintService` becomes the single implementation (NFR-002).

**What `_build_charter_lint` does** (from `research.md` section C):
1. Reads `.kittify/lint-report.json` if it exists
2. Parses `data["findings"]` — a list of dicts
3. Counts findings by `category` field: `"orphan"`, `"contradiction"`, `"staleness"`, `"reference_integrity"`
4. Counts `high_severity_count` where `severity in {"high", "critical"}`
5. Reads top-level fields: `scanned_at`, `feature_scope`, `duration_seconds`
6. Returns `DecayWatchTileResponse` (or empty response if file is absent)

**`.kittify/lint-report.json` schema:**
```json
{
  "scanned_at": "2026-01-18T10:00:00+00:00",
  "feature_scope": "083-my-mission",
  "duration_seconds": 0.42,
  "findings": [
    {"category": "orphan", "severity": "high"},
    {"category": "contradiction", "severity": "low"}
  ]
}
```

**Constraint (C-003):** `LintService` must not import `fastapi`, `starlette`, or `pydantic`.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- WP01 must be merged to the lane branch before this WP starts. Can run in parallel with WP02.

## Subtask Guide

### T013: Create `src/specify_cli/charter_lint/service.py`

**Purpose:** Provide a pure-Python domain service that encapsulates charter-lint report reading. This replaces the private helper in both the FastAPI router and the legacy HTTP handler.

**Steps:**

1. Read `src/dashboard/api/routers/lint.py` in full, focusing on `_build_charter_lint(project_dir)`.

2. Create `src/specify_cli/charter_lint/service.py`:

```python
"""LintService — read-only domain service for charter-lint data.

No FastAPI, Starlette, or Pydantic imports (C-003).
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.charter_lint.types import DecayWatchTileResponse

_LINT_REPORT_PATH = ".kittify/lint-report.json"
_HIGH_SEVERITIES = {"high", "critical"}
_CATEGORY_FIELDS = {
    "orphan": "orphan_count",
    "contradiction": "contradiction_count",
    "staleness": "staleness_count",
    "reference_integrity": "reference_integrity_count",
}


class LintService:
    """Read-only domain service for charter-lint data. No FastAPI/Pydantic imports."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir
        self._report_path = project_dir / _LINT_REPORT_PATH

    def get_decay_tile(self) -> DecayWatchTileResponse:
        """Read .kittify/lint-report.json and return the decay watch tile payload.

        Returns the zero-count empty response when the report file is absent
        or cannot be parsed. All fields set to their zero/None values so the
        caller always gets a complete DecayWatchTileResponse shape.
        """
        if not self._report_path.exists():
            return DecayWatchTileResponse(
                has_data=False,
                scanned_at=None,
                orphan_count=0,
                contradiction_count=0,
                staleness_count=0,
                reference_integrity_count=0,
                high_severity_count=0,
                total_count=0,
                feature_scope=None,
                duration_seconds=None,
            )

        try:
            data = json.loads(self._report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return DecayWatchTileResponse(
                has_data=False,
                scanned_at=None,
                orphan_count=0,
                contradiction_count=0,
                staleness_count=0,
                reference_integrity_count=0,
                high_severity_count=0,
                total_count=0,
                feature_scope=None,
                duration_seconds=None,
            )

        findings: list[dict[str, str]] = data.get("findings", [])
        counts: dict[str, int] = {field: 0 for field in _CATEGORY_FIELDS.values()}
        high_severity_count = 0

        for finding in findings:
            category = finding.get("category", "")
            if category in _CATEGORY_FIELDS:
                counts[_CATEGORY_FIELDS[category]] += 1
            if finding.get("severity", "") in _HIGH_SEVERITIES:
                high_severity_count += 1

        return DecayWatchTileResponse(
            has_data=True,
            scanned_at=data.get("scanned_at"),
            feature_scope=data.get("feature_scope"),
            duration_seconds=data.get("duration_seconds"),
            high_severity_count=high_severity_count,
            total_count=len(findings),
            **counts,  # type: ignore[misc]
        )
```

3. Verify no FastAPI/Starlette/Pydantic imports: `grep -n "fastapi\|starlette\|pydantic" src/specify_cli/charter_lint/service.py` must produce no output.

4. Verify importable: `cd src && python -c "from specify_cli.charter_lint.service import LintService; print('OK')"`.

**Files:** `src/specify_cli/charter_lint/service.py` (new)

**Validation:**
- [x] `LintService.__init__` accepts `project_dir: Path`
- [x] `get_decay_tile()` returns `DecayWatchTileResponse`
- [x] Returns `has_data=False` when `.kittify/lint-report.json` does not exist
- [x] Returns `has_data=False` when file is malformed JSON
- [x] No `fastapi`, `starlette`, or `pydantic` imports
- [x] Imports from `specify_cli.charter_lint.types` (not `dashboard.api_types`)
- [x] `mypy --strict src/specify_cli/charter_lint/service.py` passes

---

### T014: Update `src/dashboard/api/routers/lint.py`

**Purpose:** Remove `_build_charter_lint` from the router; delegate the route handler body to `LintService`. Handler body ≤ 15 LOC. Remove `# TODO(follow-up)` markers for issue #955. Update imports to `specify_cli.charter_lint.types`.

**Steps:**

1. Read `src/dashboard/api/routers/lint.py` in full.

2. Remove `_build_charter_lint(project_dir)` function entirely.

3. Add imports:
   ```python
   from specify_cli.charter_lint.service import LintService
   from specify_cli.charter_lint.types import DecayWatchTileResponse
   ```

4. Update the route handler:
   ```python
   @router.get("/api/charter-lint")
   async def get_charter_lint(request: Request) -> DecayWatchTileResponse:
       project_dir = request.app.state.project_dir
       service = LintService(project_dir)
       return service.get_decay_tile()
   ```

5. Remove all `# TODO(follow-up)` comments referencing issue #955.

6. Remove imports of `DecayWatchTileResponse` from `dashboard.api_types`.

7. Run: `cd src && python -c "from dashboard.api.routers.lint import router; print('OK')"`.

**Files:** `src/dashboard/api/routers/lint.py` (update)

**Validation:**
- [x] `_build_charter_lint` removed
- [x] Handler body is ≤ 15 LOC
- [x] No imports from `dashboard.api_types` remain
- [x] No `# TODO(follow-up)` markers for issue #955 remain
- [x] Router imports without error

---

### T015: Update `src/specify_cli/dashboard/handlers/lint.py` Imports

**Purpose:** The legacy `BaseHTTPRequestHandler` currently imports `DecayWatchTileResponse` from `..api_types`. Update to import from `specify_cli.charter_lint.types`. No other behavioral changes.

**Steps:**

1. Open `src/specify_cli/dashboard/handlers/lint.py`.

2. Find the import line(s) referencing `api_types`:
   ```python
   # Before:
   from ..api_types import DecayWatchTileResponse
   # OR
   from specify_cli.dashboard.api_types import DecayWatchTileResponse
   ```

3. Replace with:
   ```python
   from specify_cli.charter_lint.types import DecayWatchTileResponse
   ```

4. Do NOT change any other logic in this file.

5. Run existing tests: `cd src && pytest ../tests/test_dashboard/test_lint_tile_handler.py -v`.

**Files:** `src/specify_cli/dashboard/handlers/lint.py` (import update only)

**Validation:**
- [x] Import uses `specify_cli.charter_lint.types`, not `..api_types`
- [x] No other lines changed
- [x] Existing handler tests pass

---

### T016: Write `tests/specify_cli/charter_lint/test_lint_service.py`

**Purpose:** Unit tests for `LintService.get_decay_tile()` covering the happy path, the absent-file path, the malformed-JSON path, and parity with the original helper (NFR-002, NFR-006).

**Steps:**

1. Create the directory if it does not exist: `mkdir -p tests/specify_cli/charter_lint/`.

2. Create `tests/specify_cli/charter_lint/test_lint_service.py`:

```python
"""Unit tests for LintService.

Covers:
  - get_decay_tile() with a valid lint-report.json
  - get_decay_tile() when lint-report.json is absent → has_data=False
  - get_decay_tile() when lint-report.json is malformed JSON → has_data=False
  - Counting by category and severity
  - Parity: service output matches _build_charter_lint golden data (NFR-002)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.charter_lint.service import LintService


SAMPLE_REPORT = {
    "scanned_at": "2026-01-18T10:00:00+00:00",
    "feature_scope": "083-my-mission",
    "duration_seconds": 0.42,
    "findings": [
        {"category": "orphan", "severity": "high"},
        {"category": "orphan", "severity": "low"},
        {"category": "contradiction", "severity": "critical"},
        {"category": "staleness", "severity": "low"},
        {"category": "reference_integrity", "severity": "medium"},
    ],
}


def _write_report(project_dir: Path, data: dict) -> None:
    kittify = project_dir / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "lint-report.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


class TestLintServiceAbsent:
    def test_returns_has_data_false_when_file_missing(self, tmp_path: Path) -> None:
        service = LintService(tmp_path)
        result = service.get_decay_tile()
        assert result["has_data"] is False

    def test_all_counts_zero_when_file_missing(self, tmp_path: Path) -> None:
        service = LintService(tmp_path)
        result = service.get_decay_tile()
        for key in ("orphan_count", "contradiction_count", "staleness_count",
                    "reference_integrity_count", "high_severity_count", "total_count"):
            assert result.get(key) == 0, f"{key} should be 0 when file absent"

    def test_returns_dict_shape(self, tmp_path: Path) -> None:
        service = LintService(tmp_path)
        result = service.get_decay_tile()
        assert isinstance(result, dict)


class TestLintServiceMalformed:
    def test_returns_has_data_false_on_invalid_json(self, tmp_path: Path) -> None:
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "lint-report.json").write_text("not json!!!", encoding="utf-8")
        service = LintService(tmp_path)
        result = service.get_decay_tile()
        assert result["has_data"] is False


class TestLintServiceHappyPath:
    def test_has_data_true(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["has_data"] is True

    def test_scanned_at(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["scanned_at"] == "2026-01-18T10:00:00+00:00"

    def test_feature_scope(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["feature_scope"] == "083-my-mission"

    def test_duration_seconds(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["duration_seconds"] == pytest.approx(0.42)

    def test_orphan_count(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["orphan_count"] == 2  # two orphan findings

    def test_contradiction_count(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["contradiction_count"] == 1

    def test_staleness_count(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["staleness_count"] == 1

    def test_reference_integrity_count(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["reference_integrity_count"] == 1

    def test_high_severity_count(self, tmp_path: Path) -> None:
        # SAMPLE_REPORT: "high" + "critical" = 2
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["high_severity_count"] == 2

    def test_total_count(self, tmp_path: Path) -> None:
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        assert result["total_count"] == 5

    def test_empty_findings_list(self, tmp_path: Path) -> None:
        report = {**SAMPLE_REPORT, "findings": []}
        _write_report(tmp_path, report)
        result = LintService(tmp_path).get_decay_tile()
        assert result["has_data"] is True
        assert result["total_count"] == 0
        assert result["high_severity_count"] == 0


class TestLintServiceParity:
    """Parity: service output matches original _build_charter_lint (NFR-002)."""

    def test_parity_with_golden_data(self, tmp_path: Path) -> None:
        """Service produces the same output as the original helper for the same input."""
        _write_report(tmp_path, SAMPLE_REPORT)
        result = LintService(tmp_path).get_decay_tile()
        # Golden values derived from SAMPLE_REPORT by hand:
        assert result["orphan_count"] == 2
        assert result["contradiction_count"] == 1
        assert result["staleness_count"] == 1
        assert result["reference_integrity_count"] == 1
        assert result["high_severity_count"] == 2
        assert result["total_count"] == 5
        assert result["has_data"] is True
```

3. Also update `tests/test_dashboard/test_lint_tile_handler.py` to verify delegation:

```python
def test_lint_tile_route_delegates_to_service(client, mocker):
    """The /api/charter-lint route delegates to LintService."""
    mock_service = mocker.patch("dashboard.api.routers.lint.LintService")
    mock_service.return_value.get_decay_tile.return_value = {"has_data": False}
    response = client.get("/api/charter-lint")
    assert response.status_code == 200
    mock_service.return_value.get_decay_tile.assert_called_once()
```

4. Run and confirm coverage: `cd src && pytest ../tests/specify_cli/charter_lint/test_lint_service.py --cov=specify_cli.charter_lint.service --cov-report=term-missing`.

**Files:** `tests/specify_cli/charter_lint/test_lint_service.py` (new), `tests/test_dashboard/test_lint_tile_handler.py` (update)

**Validation:**
- [x] All tests in `test_lint_service.py` pass
- [x] Line coverage ≥ 90% for `specify_cli.charter_lint.service`
- [x] Parity test passes
- [x] `test_lint_tile_handler.py` delegation test passes

---

## Definition of Done

- [x] `src/specify_cli/charter_lint/service.py` exists with `LintService` class
- [x] `LintService.get_decay_tile()` contains the extracted logic
- [x] Returns `has_data=False` with zero counts when report file is absent
- [x] `src/dashboard/api/routers/lint.py` has no private helpers; handler ≤ 15 LOC
- [x] No `# TODO(follow-up)` markers for issue #955 remain in the router
- [x] `src/specify_cli/dashboard/handlers/lint.py` imports from `specify_cli.charter_lint.types`
- [x] `tests/specify_cli/charter_lint/test_lint_service.py` passes with ≥ 90% coverage
- [x] `tests/test_dashboard/test_lint_tile_handler.py` passes

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Parity break: field names differ between service and original helper | High | Parity tests compare golden counts against hand-computed values from `SAMPLE_REPORT` |
| C-003 violation: FastAPI/Pydantic imported in service | High | `grep` check in T013 validation |
| `.kittify/lint-report.json` path assumption is wrong | Medium | All tests use `tmp_path` fixture; test both present and absent cases |
| `DecayWatchTileResponse(**counts)` spread syntax fails mypy | Low | Add `# type: ignore[misc]` or use explicit field assignment |

## Reviewer Guidance

1. Confirm no `fastapi`, `starlette`, or `pydantic` imports in `service.py`.
2. Count the category fields in `SAMPLE_REPORT` manually and verify the test assertions match.
3. Confirm the router handler body is ≤ 15 LOC after the delegation update.
4. Run `pytest tests/specify_cli/charter_lint/ tests/test_dashboard/test_lint_tile_handler.py -v`.
5. Check that `handlers/lint.py` diff is import-only (no logic change).

Implement command: `spec-kitty agent action implement WP03 --agent <name>`

## Activity Log

- 2026-05-04T17:46:02Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1962577 – Started implementation via action command
- 2026-05-04T17:48:33Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1962577 – LintService extracted, router delegated, parity tests pass
- 2026-05-04T17:48:55Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1965199 – Started review via action command
- 2026-05-04T17:50:29Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1965199 – Review passed: LintService extracted cleanly, router delegates, tests pass
