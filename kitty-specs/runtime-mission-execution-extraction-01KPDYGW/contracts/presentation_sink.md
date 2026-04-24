# Contract: PresentationSink Protocol

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**FR**: FR-013
**Status**: Authoritative IDL — WP02 implements this at `src/runtime/seams/presentation_sink.py`

---

## Purpose

Runtime must surface output (progress messages, status lines, JSON results) to the user without importing `rich.*` or `typer.*`. `PresentationSink` is the abstract output surface that CLI adapters implement. Runtime accepts a `PresentationSink` at injection points and never calls Rich directly.

## Protocol Definition

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable


@runtime_checkable
class PresentationSink(Protocol):
    """Abstract output surface injected into runtime services.

    CLI adapters provide a Rich-backed implementation.
    Tests use NullSink or a recording sink.
    Runtime must never import rich.* directly.
    """

    def write_line(self, text: str) -> None:
        """Emit a single line of plain-text output."""
        ...

    def write_status(self, message: str) -> None:
        """Emit a transient status/progress message (e.g. spinner label)."""
        ...

    def write_json(self, data: object) -> None:
        """Emit structured output in JSON format (for --json mode)."""
        ...
```

## NullSink (test / offline implementation)

```python
class NullSink:
    """No-op PresentationSink for tests and contexts without a console."""
    def write_line(self, text: str) -> None: pass
    def write_status(self, message: str) -> None: pass
    def write_json(self, data: object) -> None: pass

assert isinstance(NullSink(), PresentationSink)  # structural check at module load
```

## RichPresentationSink (CLI layer — lives in `specify_cli.cli`, NOT in `runtime`)

```python
# src/specify_cli/cli/_rich_sink.py  ← CLI layer only; never imported by runtime
import json
from rich.console import Console
from runtime.seams.presentation_sink import PresentationSink

class RichPresentationSink:
    """Rich-backed PresentationSink injected by CLI command modules."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def write_line(self, text: str) -> None:
        self._console.print(text)

    def write_status(self, message: str) -> None:
        self._console.print(f"[dim]{message}[/dim]")

    def write_json(self, data: object) -> None:
        self._console.print_json(json.dumps(data, default=str))
```

## Injection Pattern

Functions in `src/runtime/` that surface output take a `sink` parameter with a `NullSink` default so they remain callable without a console (e.g. from tests):

```python
from runtime.seams.presentation_sink import PresentationSink
from runtime.seams._null_sink import NullSink

def run_next_step(
    mission_slug: str,
    agent: str,
    sink: PresentationSink = NullSink(),
) -> Decision:
    ...
    sink.write_status(f"Evaluating WPs for {mission_slug}...")
    ...
```

CLI adapters inject the Rich implementation:

```python
# src/specify_cli/cli/commands/next_cmd.py
from specify_cli.cli._rich_sink import RichPresentationSink
from runtime.bridge.runtime_bridge import run_next_step

sink = RichPresentationSink()
result = run_next_step(mission_slug=mission, agent=agent, sink=sink)
```

## Extension Notes

- If the WP01 audit finds additional Rich call patterns in `runtime_bridge.py` (beyond `print`, `status`, `json`), add the corresponding method to this Protocol before WP02 finalises the implementation.
- Do NOT add Rich or Typer imports to the Protocol definition itself.
- The `@runtime_checkable` decorator enables `isinstance(obj, PresentationSink)` structural checks in tests.
