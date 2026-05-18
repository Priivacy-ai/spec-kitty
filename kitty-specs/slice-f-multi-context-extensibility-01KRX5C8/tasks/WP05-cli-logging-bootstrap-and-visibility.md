---
work_package_id: WP05
title: CLI logging bootstrap + Rich-aware handler + subprocess visibility test
dependencies:
- WP04
requirement_refs:
- FR-130
- FR-131
- FR-132
- NFR-005
- NFR-006
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/__main__.py
execution_mode: code_change
owned_files:
- src/specify_cli/__main__.py
- src/specify_cli/cli/logging_bootstrap.py
- src/charter/_catalog_miss.py
- tests/integration/test_catalog_miss_cli_visibility.py
role: implementer
tags: []
shell_pid: "2408484"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Close the architect's HIGH-1 finding: the structured `_LOGGER.warning(...)` path in `src/charter/_catalog_miss.py` is silently dropped under normal CLI invocation because the spec-kitty CLI installs **no log handler**. Install `logging.captureWarnings(True)` at CLI bootstrap so `warnings.warn(...)` reaches the logging subsystem (FR-130) and install a Rich-aware `logging.Handler` that routes `WARNING+` records through the existing Rich `Console` instance to operator stderr (FR-131). Land a subprocess-based integration test that runs the CLI with a typo'd charter and asserts the catalog-miss warning text appears in captured stderr (FR-132, NFR-006).

This closes Scenario 5 (operator with a typo'd charter sees a visible warning) and AC-9.

---

## Context

Per the architect's HEAD-verified HIGH-1 finding:

> `rg "logging.captureWarnings|logging.basicConfig|configure_logging|setup_logging" src/specify_cli/` returns **0 matches**. Python's default Warning filter is `default` (one warning per location), so a charter with 5 typo'd IDs surfaces each warning exactly once per process — and only if the operator's stderr isn't being suppressed or interleaved with Rich-managed output.

The structured catalog-miss warning in `src/charter/_catalog_miss.py` carries useful metadata (`kind`, `id`, `cause`, `suggestion`) in `_LOGGER.warning(extra={...})`. With no handler, the operator never sees it. Per **RR-6** the Rich-aware handler MUST defer to the existing Rich `Console` instance rather than instantiate a new one — no Rich double-init.

References:
- [spec.md §"Scenario 5 — Catalog-miss visibility"](../spec.md)
- [spec.md §"Absorbed remediation — HIGH-1 catalog-miss CLI visibility"](../spec.md)
- [plan.md §1.7](../plan.md)
- [contracts/catalog-miss-cli-visibility.md](../contracts/catalog-miss-cli-visibility.md)
- [data-model.md §8 CatalogMissEvent](../data-model.md#8-catalogmissevent--logging-payload-extension-fr-131)
- [atdd-coverage.md Scenario 5, AC-9](../atdd-coverage.md)

**Lane B dependency:** WP05 depends on WP04 sequentially within Lane B (one lane workspace, sequential commits avoid parallel-staging collision per RR-8). WP05's logging bootstrap does NOT depend on Lane A's deliverables.

---

## ATDD Discipline

Per **C-011** WP05 lands its failing-first test as its FIRST commit:

1. **Commit A (RED, T022):** `tests/integration/test_catalog_miss_cli_visibility.py` runs `subprocess.run([sys.executable, "-m", "specify_cli", ...])` against a fixture project with `selected_styleguides: [does-not-exist]` and asserts the catalog-miss warning text appears in captured `stderr`. On the planning base this fails because no log handler exists. Commit message: `covers: Scenario 5, AC-9 — expected GREEN at: WP05 final commit`.
2. **Commits B..D (GREEN progression, T023-T026):** install `captureWarnings`, install Rich-aware handler, extend `_catalog_miss.py` payload, verify regression suite.

ATDD anchor per [atdd-coverage.md](../atdd-coverage.md):
- Scenario 5 / AC-9: `tests/integration/test_catalog_miss_cli_visibility.py::test_typoed_styleguide_produces_visible_stderr_warning`

---

## Subtasks

### T022 — Land failing-first `tests/integration/test_catalog_miss_cli_visibility.py`

**File:** `tests/integration/test_catalog_miss_cli_visibility.py` (new)

The test MUST use `subprocess.run` (NFR-006 binding — pytest's in-process warning capture does NOT prove visibility under real operator conditions).

```python
"""Catalog-miss CLI visibility (FR-132, NFR-006, Scenario 5, AC-9).

Subprocess-based test: spawn the spec-kitty CLI in a fresh process with a
typo'd charter selection, then assert the catalog-miss warning text
appears in captured stderr. This proves the warning is visible under real
operator conditions, not just under pytest's in-process warning capture.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def project_with_typoed_styleguide(tmp_path: Path) -> Path:
    """Scaffold a minimal spec-kitty project with a typo'd styleguide selection."""
    project = tmp_path / "demo-project"
    project.mkdir()
    (project / ".kittify" / "charter").mkdir(parents=True)
    (project / ".kittify" / "charter" / "charter.md").write_text(textwrap.dedent("""
        ---
        selected_styleguides:
          - does-not-exist
        ---
        # Test Charter
    """).strip())
    # ... any other minimal scaffolding required to make `spec-kitty agent context resolve`
    # or equivalent reach the catalog-miss code path
    return project


@pytest.mark.integration
def test_typoed_styleguide_produces_visible_stderr_warning(
    project_with_typoed_styleguide: Path,
) -> None:
    """Operator with a typo'd charter sees the warning on stderr."""
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "agent", "context", "resolve",
         "--action", "implement"],
        cwd=str(project_with_typoed_styleguide),
        capture_output=True,
        text=True,
        timeout=30,
    )
    # The catalog-miss warning text MUST appear in stderr
    assert "does-not-exist" in result.stderr, (
        f"Catalog-miss warning not found in stderr:\nSTDERR:\n{result.stderr}\n"
        f"STDOUT:\n{result.stdout}"
    )
    assert "styleguide" in result.stderr.lower() or "catalog miss" in result.stderr.lower(), (
        f"Stderr does not identify the missing kind:\n{result.stderr}"
    )
```

**Validation:** `pytest tests/integration/test_catalog_miss_cli_visibility.py -v` MUST FAIL on planning base (the warning is dropped silently). Commit RED.

### T023 — Install `logging.captureWarnings(True)` at CLI bootstrap

**Files:** `src/specify_cli/__main__.py` OR a new `src/specify_cli/cli/logging_bootstrap.py`

The preferred location is a dedicated bootstrap module:

```python
# src/specify_cli/cli/logging_bootstrap.py
"""CLI logging bootstrap (FR-130, FR-131).

Configures the standard logging subsystem so:
1. warnings.warn(...) reaches log handlers via logging.captureWarnings(True).
2. WARNING+ log records route through the existing Rich Console instance
   to operator stderr.

Per RR-6, the Rich handler DEFERS to the existing Console rather than
instantiating a new one -- no Rich double-init.
"""
from __future__ import annotations

import logging

__all__ = ["bootstrap_logging"]


def bootstrap_logging(console) -> None:
    """Install captureWarnings + Rich-aware handler. Idempotent."""
    if getattr(bootstrap_logging, "_installed", False):
        return
    logging.captureWarnings(True)
    handler = _RichConsoleHandler(console=console, level=logging.WARNING)
    root = logging.getLogger()
    if not any(isinstance(h, _RichConsoleHandler) for h in root.handlers):
        root.addHandler(handler)
    bootstrap_logging._installed = True
```

Wire into `src/specify_cli/__main__.py` at typer app startup (or at module import — choose the location that runs before any charter resolution).

### T024 — Add Rich-aware `logging.Handler`

**File:** `src/specify_cli/cli/logging_bootstrap.py`

```python
class _RichConsoleHandler(logging.Handler):
    """Route WARNING+ records through an existing Rich Console to stderr."""

    def __init__(self, console, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self._console = console

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Defer to the existing Console; do not instantiate a new one (RR-6).
            self._console.print(f"[yellow][WARNING][/yellow] {msg}", file=self._console.file)
        except Exception:  # pragma: no cover
            self.handleError(record)
```

The handler MUST format catalog-miss records per the data-model §8 contract:

```
[WARNING] Catalog miss: <kind>=<id> (cause=<cause>). <suggestion?> [mission=<mission_id>, scope=<scope>]
```

Implement as a custom `Formatter` or extract fields from `record.__dict__` (where `extra={...}` lands):

```python
class CatalogMissFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, "kind") and hasattr(record, "id"):
            suggestion = getattr(record, "suggestion", None)
            mission_id = getattr(record, "mission_id", None)
            scope = getattr(record, "scope", None)
            tail = []
            if suggestion:
                tail.append(f"Did you mean: {suggestion}?")
            meta = ", ".join(f"{k}={v}" for k, v in [("mission", mission_id), ("scope", scope)] if v)
            return (
                f"Catalog miss: {record.kind}={record.id} (cause={record.cause})."
                + (f" {' '.join(tail)}" if tail else "")
                + (f" [{meta}]" if meta else "")
            )
        return super().format(record)
```

### T025 — Extend `_catalog_miss.py` `_LOGGER.warning(extra=...)` payload

**File:** `src/charter/_catalog_miss.py`

Per data-model §8 (`CatalogMissEvent`), the `extra=` dict MUST carry:

| Field | Type | Required |
|---|---|---|
| `kind` | `str` | yes |
| `id` | `str` | yes |
| `cause` | `Literal["typo", "missing", "schema_validation_suspected"]` | yes |
| `suggestion` | `str \| None` | no |
| `mission_id` | `str \| None` | no |
| `scope` | `str \| None` | no |

Extend the existing `_LOGGER.warning(...)` call site:

```python
_LOGGER.warning(
    f"Catalog miss: {kind}={artifact_id}",
    extra={
        "kind": kind,
        "id": artifact_id,
        "cause": _infer_cause(kind, artifact_id, catalog),
        "suggestion": _closest_match(artifact_id, catalog),
        "mission_id": _current_mission_id(),
        "scope": _current_scope_name(),
    },
)
```

Implement `_infer_cause` (heuristic: edit-distance to known IDs ⇒ `typo`; absent entirely ⇒ `missing`; schema-validation error during load ⇒ `schema_validation_suspected`) and `_closest_match` (use `difflib.get_close_matches` against the catalog). If `mission_id` / `scope` are not reachable from this module, pass `None` — both are optional per the data-model spec.

### T026 — Confirm subprocess visibility test GREEN; regression sweep clean

```bash
pytest tests/integration/test_catalog_miss_cli_visibility.py -v
# EXPECTED: GREEN

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)

pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: 23/23 pass unchanged (NFR-001)

pytest tests/architectural/test_layer_rules.py -v
# EXPECTED: pass unchanged (NFR-003)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/integration/test_catalog_miss_cli_visibility.py::test_typoed_styleguide_produces_visible_stderr_warning` (was RED on planning base)
- ✅ 23 governance-contract fixtures pass unchanged (NFR-001)
- ✅ Layer-rule sweep unchanged (NFR-003)
- ✅ Full architectural sweep exit 0 (NFR-005)

FR coverage:

- ✅ FR-130 — `logging.captureWarnings(True)` at CLI bootstrap
- ✅ FR-131 — Rich-aware handler routes `WARNING+` to stderr via existing Console
- ✅ FR-132 — subprocess test asserts visibility under real operator conditions
- ✅ NFR-006 — test uses `subprocess.run`, not pytest in-process capture

AC coverage:

- ✅ AC-9 — typo'd styleguide produces operator-visible stderr warning

---

## Risks

1. **Rich-aware handler collides with existing Rich console** (RR-6 in plan). Mitigation: T024 explicitly DEFERS to the existing Console (passed in) rather than instantiating a new one. The bootstrap is idempotent (`getattr(bootstrap_logging, "_installed", False)`) so importing twice doesn't double-install.
2. **`logging.captureWarnings(True)` interferes with pytest's warning capture in unit tests** — would surface as warning leak. Mitigation: pytest's `caplog` and `recwarn` work alongside the logging subsystem; if a unit test breaks, opt out by calling `logging.captureWarnings(False)` in a fixture-scoped teardown. The subprocess test (FR-132) is the canonical proof; in-process tests can remain as-is.
3. **The subprocess test is slow (spawns a Python interpreter)** — adds CI time. Mitigation: mark `@pytest.mark.integration` so fast-test runs skip it; the canonical sweep includes it.
4. **The `extra={...}` field names collide with reserved `LogRecord` attributes** (e.g. `msg`, `levelno`, `name`). Mitigation: data-model §8 chose `kind`, `id`, `cause`, `suggestion`, `mission_id`, `scope` — none collide with `LogRecord` attrs. Verify with `logging.LogRecord.__init__.__doc__`.
5. **Subprocess `cwd=` resolves charter from the wrong location** in some environments. Mitigation: T022's fixture scaffolds a complete project structure under `tmp_path` (charter at `.kittify/charter/charter.md`) and passes `cwd=str(tmp_path / "demo-project")`. The CLI must resolve the charter from cwd, which it does via existing `charter.resolver` logic.
6. **CLI bootstrap order: handler installed AFTER first charter resolution** would miss the first miss. Mitigation: install at module-import time in `src/specify_cli/__main__.py` (top of file) OR in the typer app's `@app.callback()` which runs before any subcommand. Verify the bootstrap runs before any charter code by reading the import chain.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/integration/test_catalog_miss_cli_visibility.py -v
# EXPECTED: failure (warning not in stderr; no handler installed)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/integration/test_catalog_miss_cli_visibility.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `rg "logging.captureWarnings|RichConsoleHandler" src/specify_cli/` finds the bootstrap site.
- Confirm the handler DEFERS to the existing Rich Console (passed as argument) — REJECT if it instantiates a new `rich.Console()` (RR-6 violation).
- Confirm the handler is installed idempotently (re-importing doesn't double-add).
- Confirm `src/charter/_catalog_miss.py::_LOGGER.warning(...)` carries the full data-model §8 payload in `extra=`.
- Confirm the subprocess test uses `subprocess.run([sys.executable, "-m", "specify_cli", ...])` and asserts against `result.stderr` text — REJECT if it falls back to pytest's `caplog` or `recwarn` (NFR-006 binding).
- Confirm 23 governance-contract fixtures pass unchanged (NFR-001).
- Confirm layer-rule unchanged (NFR-003).
- Confirm full architectural sweep exit 0 (NFR-005).
- Confirm `tests/architectural/test_auth_transport_singleton.py` is UNCHANGED (C-005 — auth-transport descoped).

**FR-304 commit-message check:** T022 RED commit cites `covers: Scenario 5, AC-9` and `expected GREEN at: WP05 final commit`.

## Activity Log

- 2026-05-18T14:42:20Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2367982 – Started implementation via action command
- 2026-05-18T15:04:09Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2367982 – CLI logging bootstrap (FR-130 + FR-131) + subprocess visibility test (FR-132 + NFR-006); AC-9 GREEN. RISK-3 from Mission B post-merge review now fully closed at operator surface.
- 2026-05-18T15:06:02Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2408484 – Started review via action command
- 2026-05-18T15:22:11Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2408484 – Moved to planned
