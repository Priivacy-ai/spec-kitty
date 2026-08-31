# Contract — Catalog-Miss CLI Visibility

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-130, FR-131, FR-132 + NFR-006 | Companions: [charter-scope-resolution.md](charter-scope-resolution.md)
> Data model: [../data-model.md §8](../data-model.md#8-catalogmissevent--logging-payload-extension-fr-131)

The catalog-miss CLI visibility contract closes RISK-3 (Mission B): operator-visible warning surface for catalog misses caused by typo'd or missing charter selections. Today the `_LOGGER.warning(...)` path in `charter._catalog_miss` is silently dropped because the spec-kitty CLI installs no log handler.

---

## Input Contract

### Bootstrap requirement (FR-130)

The spec-kitty CLI entry point (`src/specify_cli/__main__.py` or the typer app startup hook) MUST call:

```python
import logging

logging.captureWarnings(True)
```

This routes `warnings.warn(...)` through the Python logging subsystem so the FR-131 handler can format and emit it.

### Handler installation (FR-131)

The same entry point MUST install a Rich-aware `logging.Handler` that routes `WARNING+` records through the existing Rich `Console` instance to the operator's stderr.

Reference implementation shape:

```python
import logging
from rich.console import Console
from rich.logging import RichHandler

# IMPORTANT (RR-6): defer to the existing Console instance; do NOT instantiate a new one.
from specify_cli.console import get_stderr_console  # whatever the existing accessor is

_handler = RichHandler(
    console=get_stderr_console(),
    show_path=False,
    show_time=False,
    markup=False,
    rich_tracebacks=False,
)
_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[_handler],
)
logging.captureWarnings(True)
```

The handler MUST be installed at process startup so subprocess invocations (FR-132 test) see warnings on stderr.

### Catalog-miss emission contract — `src/charter/_catalog_miss.py`

The existing `_LOGGER.warning(message, extra=extra)` call site MUST emit the following fields in `extra=` (FR-131):

#### `CatalogMissEvent` extra fields

```python
extra = {
    "kind": "styleguide",                 # str — the artifact kind that missed
    "id": "caveman-comemnts",             # str — the artifact ID that didn't resolve
    "cause": "typo",                      # Literal["typo","missing","schema_validation_suspected"]
    "suggestion": "caveman-comments",     # str | None — closest-match (None if unavailable)
    "mission_id": "01KRX5C8MQ...",        # str | None — the mission ULID, if known
    "scope": None,                        # str | None — CharterScope.name if monorepo; else None
}
```

The cause classifier is heuristic:

- `typo` — at least one allowlisted artifact ID has a Levenshtein distance ≤ 2 from the missed ID; suggestion is the closest match.
- `missing` — no close match; suggestion is `None`.
- `schema_validation_suspected` — the missed ID parsed cleanly but the artifact body failed schema validation; suggestion may be `None` or point to the failing-validation file.

---

## Output Contract

### Operator-visible stderr line

When the handler fires, the operator sees on stderr (Rich-formatted):

```
WARNING  Catalog miss: styleguide=caveman-comemnts (cause=typo). Did you mean: caveman-comments? [mission=01KRX5C8MQ..., scope=None]
```

### Multiple-miss aggregation

Each miss produces one log line. The handler does NOT deduplicate within a process (Python's `warnings` default `default` filter handles per-location deduplication; the handler preserves that semantic).

### Programmatic API

The `extra=` payload IS the structured surface — downstream tooling (e.g. CI log scrapers, JSON-log mode in a follow-up mission) can consume it directly via a custom handler.

---

## Failure modes

| Trigger | Behaviour | Operator message |
|---|---|---|
| The handler is not installed (regression) | `warnings.warn(...)` produces a Python `WARNING` line (the default `default` filter), but no Rich formatting. The structured `extra=` dict is lost | The FR-132 subprocess test FAILS, signaling the regression |
| The handler is installed but Rich Console is unavailable (e.g. non-tty) | Rich falls back to plain text on stderr; the message is still visible | None — operator sees a plain-text WARNING line |
| The `extra=` dict is missing required keys | Handler logs the raw message without the structured suffix | None — soft degradation; the structured-log contract is best-effort |
| Subprocess test runs but the catalog-miss code path never fires | FR-132 test FAILS with "no catalog-miss warning observed" | Test investigates the test fixture's charter |

---

## FR-132 subprocess test contract

`tests/integration/test_catalog_miss_cli_visibility.py`:

```python
import subprocess
import sys
from pathlib import Path

@pytest.mark.integration
@pytest.mark.git_repo
def test_typoed_styleguide_produces_visible_stderr_warning(tmp_repo):
    """A typo'd charter selection produces an operator-visible warning on stderr.

    Pinned: FR-130, FR-131, FR-132, NFR-006, AC-9, Scenario 5.
    """
    # tmp_repo fixture scaffolds a charter with selected_styleguides: [does-not-exist]
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "agent", "action", "implement", "WP01"],
        cwd=tmp_repo,
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = result.stderr
    assert "Catalog miss" in stderr, f"Expected catalog-miss warning on stderr; got:\n{stderr}"
    assert "does-not-exist" in stderr
    assert "styleguide" in stderr
```

**Why subprocess (NFR-006 binding):** pytest's in-process warning capture would mask the real-world problem. The test MUST prove the warning is visible to a real CLI invocation under operator conditions.

---

## Backward compatibility guarantee

- The bootstrap addition (`logging.captureWarnings(True)` + handler install) is **additive**. No existing CLI invocation changes behaviour except for previously-silent warnings becoming visible.
- The `extra=` dict extension is **additive**. Existing callers passing fewer fields continue to work; missing fields produce a soft-degradation message.
- The Rich Console deferral (RR-6) ensures no double-init; existing Rich output (progress bars, tables, etc.) is unchanged.

---

## Glossary terms (canonicalised in WP12 per FR-302)

- **Catalog miss** — renderer state when a charter-selected artifact ID does not resolve to a loaded artifact in any layer. Already in `glossary/contexts/doctrine.md`; this mission promotes it to canonical.

---

## ATDD anchors

- `tests/integration/test_catalog_miss_cli_visibility.py` (FR-132; NFR-006; AC-9; Scenario 5)
- `tests/unit/test_catalog_miss_event_extra_fields.py` (unit; asserts the `extra=` dict carries the FR-131 fields)
- `tests/unit/test_rich_log_handler_install.py` (unit; asserts `logging.captureWarnings(True)` + a `RichHandler` is installed at module import)
