# Contract: CLI Agent Status (Windows-aware path rendering)

**Spec IDs**: FR-012, FR-013, FR-019, SC-002
**Modules**: `src/specify_cli/cli/commands/agent/status.py`, `src/specify_cli/cli/commands/migrate_cmd.py`, `src/specify_cli/paths/windows_paths.py`

## `render_runtime_path(path: Path, *, for_user: bool = True) -> str`

```python
def render_runtime_path(path: Path, *, for_user: bool = True) -> str:
    """Render a runtime-state path for user-facing output.

    - On Windows, returns the real absolute path (e.g. `C:\\Users\\alice\\AppData\\Local\\spec-kitty\\auth`).
    - On POSIX, returns a tilde-compressed form when the path is under $HOME and `for_user=True`,
      otherwise returns the absolute path.
    """
```

**Guarantees**:
- G-01: On Windows, the returned string NEVER contains `~/.kittify`, `~/.spec-kitty`, or `$LOCALAPPDATA` (literal variable expansion shown to users); only resolved absolute paths.
- G-02: On POSIX, tilde compression preserves existing UX.
- G-03: Pure function; no filesystem access required.

## Call-site sweep

All user-facing messages that currently name a runtime path MUST be migrated to `render_runtime_path(...)`. Minimum set from prior scan:

- `src/specify_cli/cli/commands/migrate_cmd.py` — any message referencing `~/.kittify`.
- `src/specify_cli/cli/commands/agent/status.py` — any message referencing `~/.kittify`.
- Additional call-sites surfaced by the second-pass audit (lane H).

## CLI output contract

On Windows, the following commands MUST render runtime paths as real `C:\...` paths:

| Command | Message surface | Expectation |
|---|---|---|
| `spec-kitty agent status` | "Runtime state lives at ..." | Real `%LOCALAPPDATA%\spec-kitty` absolute path. |
| `spec-kitty migrate` | Migration summary (see migrate contract) | Real absolute paths for both canonical and quarantine locations. |
| `spec-kitty --help` (and subcommand help where paths appear) | Help text | Platform-aware; no hardcoded POSIX literals. |

## Test contract

| Test ID | File | windows_ci? | Asserts |
|---|---|---|---|
| T-RNDR-01 | `tests/paths/test_render_runtime_path.py::test_windows_returns_absolute` | Yes | Synthetic Windows path renders as `C:\...` absolute; no tilde. |
| T-RNDR-02 | `tests/paths/test_render_runtime_path.py::test_posix_tilde_compression` | No | Path under `$HOME` renders as `~/...`. |
| T-STAT-01 | `tests/cli/test_agent_status_messaging.py::test_no_legacy_path_literals_on_windows` | Yes | Running `spec-kitty agent status` on Windows emits no substring matching `~/.kittify` or `~/.spec-kitty`. |
| T-AUDIT-01 | `tests/audit/test_no_legacy_path_literals.py` | No | Static grep over `src/specify_cli/cli/` for `~/.kittify` / `~/.spec-kitty` returns zero hits in user-output-producing code paths (whitelist documented in audit report). |
