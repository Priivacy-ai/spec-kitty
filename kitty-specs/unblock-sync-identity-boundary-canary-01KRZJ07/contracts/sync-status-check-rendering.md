# Contract: `sync status --check` path rendering (for #1123)

**Module**: `src/specify_cli/cli/commands/sync.py` (≈line 1856, `boundary_table`)
**WP**: WP02

## Rendering contract

The `sync status --check` text renderer composes two surfaces:

1. **Identity Table** — a Rich `Table` (unchanged: `title="Identity Boundary"`, `show_header=False`, `box=None`, `expand=False`). Holds tabular identity scalars (version, server URL parity flag, foreground/daemon match indicator).
2. **Path rows** — rendered via `Console.print(f"{label}: {path}")` *outside* the Table. One line per path, label and value separated by `": "`.

Rendering order: Path rows printed immediately above OR below the Identity Table; order is deterministic.

## Behavioral guarantees

| Property | Guarantee |
|----------|-----------|
| `active_queue.path` text == `active_queue.path` JSON | byte-identical for every path field. |
| Single-line path | a path is never wrapped, never ellipsised (`…`), never folded across lines. |
| Non-TTY capture | identical guarantees under `subprocess.run([...sync status --check...], capture_output=True)` and pipes. |
| Wide TTY operator UX | path rows render alongside the Table; no visual regression. |

## Renderer skeleton (illustrative, not normative)

```python
def _render_boundary_check(...):
    console = Console()

    # Path rows first (outside the table)
    for label, path in [
        ("Active queue DB", state.active_queue_db_path),
        ("Foreground executable", state.foreground_executable_path),
        ("Foreground source", state.foreground_source_path),
        # ...etc — all canonical file path fields
    ]:
        if path is not None:
            console.print(f"{label}: {path}")

    # Identity scalars next (inside a table)
    boundary_table = Table(title="Identity Boundary", show_header=False, box=None, expand=False)
    boundary_table.add_column("Key", style="dim")
    boundary_table.add_column("Value")
    for key, value in identity_scalars(state):
        boundary_table.add_row(key, value)
    console.print(boundary_table)
```

## JSON contract (unchanged, asserted)

`sync status --check --json` continues to expose `active_queue.path` and every other canonical path as a discrete string value. The text contract converges on the JSON contract for every path field.

## Test surface (WP02)

`tests/specify_cli/cli/commands/test_sync_status_check_paths.py`:
- **Non-TTY capture test**: spawn `spec-kitty sync status --check` under `CliRunner` (forces non-TTY), parse stdout, locate every label/path line, assert each path equals the corresponding `--json` value byte-for-byte.
- **Long-path test**: seed a fixture where the queue DB path is > 80 chars; assert no `…` appears in the rendered output.
- **Narrow-column TTY test**: force `Console(width=40)` for the path renderer; confirm paths still render on one line (i.e., they bypass the Table width).
- **JSON parity test**: compare every path field between text and JSON forms.
