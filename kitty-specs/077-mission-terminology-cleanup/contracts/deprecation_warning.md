# Contract: Deprecation Warning Format and Suppression

**Mission**: `077-mission-terminology-cleanup`
**Surface**: stderr output of `src/specify_cli/cli/selector_resolution.py::_emit_deprecation_warning`
**Owner**: Scope A (`#241`), specifically WPA4

## Warning Text Format

The deprecation warning is emitted to stderr via `rich.console.Console(stderr=True)` and uses the existing precedent at `src/specify_cli/cli/commands/agent/mission.py:604` exactly:

```
Warning: <alias_flag> is deprecated; use <canonical_flag>. See: docs/migration/feature-flag-deprecation.md
```

When rendered through Rich with `[yellow]Warning:[/yellow]`, the visible output is:

```
Warning: --feature is deprecated; use --mission. See: docs/migration/feature-flag-deprecation.md
```

(The "Warning:" prefix is yellow; the rest is default.)

For the inverse direction (FR-021), the same format applies:

```
Warning: --mission is deprecated; use --mission-type. See: docs/migration/mission-type-flag-deprecation.md
```

## Implementation

```python
import os
from rich.console import Console

_warned: set[tuple[str, str]] = set()
_err_console = Console(stderr=True)

def _emit_deprecation_warning(
    canonical_flag: str,
    alias_flag: str,
    suppress_env_var: str,
) -> bool:
    """Emit a single yellow stderr deprecation warning unless suppressed.

    Returns True if a warning was actually emitted, False if suppressed
    or if a warning has already been emitted for this (canonical, alias)
    pair in the current process.
    """
    pair = (canonical_flag, alias_flag)
    if pair in _warned:
        return False
    if os.environ.get(suppress_env_var) == "1":
        return False
    _warned.add(pair)
    doc_path = _doc_path_for(alias_flag)
    _err_console.print(
        f"[yellow]Warning:[/yellow] {alias_flag} is deprecated; "
        f"use {canonical_flag}. See: {doc_path}"
    )
    return True

def _doc_path_for(alias_flag: str) -> str:
    """Map an alias flag to its migration doc path."""
    return {
        "--feature": "docs/migration/feature-flag-deprecation.md",
        "--mission": "docs/migration/mission-type-flag-deprecation.md",
    }[alias_flag]
```

## Suppression Env Vars

| Env var | Direction | Set to | Effect |
|---|---|---|---|
| `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` | `--feature` → `--mission` | `"1"` | Skips the warning emit. The helper still resolves the value and still raises BadParameter on conflict. |
| `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION` | `--mission` → `--mission-type` | `"1"` | Same. |

**Default behavior**: when the env var is not set or is set to anything other than `"1"`, the warning is emitted normally. There is no `0` or `false` value handling — the env var is strictly opt-in to suppression.

**Visibility**: both env vars are documented in the same migration doc that the warning links to. They are intentionally verbose and direction-specific so a CI maintainer who needs to suppress one cannot accidentally suppress the other.

## Single-Warning-Per-Invocation Guarantee (NFR-002)

The `_warned` set is module-level. It accumulates `(canonical_flag, alias_flag)` pairs across all calls within a single Python process. A long-running CLI session that invokes the same deprecated alias multiple times sees the warning **only once per direction**.

Verified by `tests/specify_cli/cli/commands/test_selector_resolution.py::test_warning_emitted_only_once_per_pair`.

The set is reset between test cases by the `autouse` fixture defined in `data-model.md`.

## Migration Documentation

This mission must publish two short migration doc pages:

1. `docs/migration/feature-flag-deprecation.md` — explains why `--feature` is being removed, when it will be removed (named conditions only, per spec §15 Q1), how to migrate scripts, and how to suppress the warning during cutover.
2. `docs/migration/mission-type-flag-deprecation.md` — same shape for the inverse-drift case.

Both docs link back to:
- The spec at `kitty-specs/077-mission-terminology-cleanup/spec.md`
- The ADR at `architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md`
- The initiative at `architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md`

The exact content of these docs is finalized in WPA9.

## What This Contract Does NOT Specify

- The Rich color (yellow) is fixed by the `agent/mission.py:604` precedent. Implementers should not change it.
- The exact migration doc paths above are committed contracts. If they need to change, both this contract and the warning text must be updated together in the same PR.
- The warning does not include a date for removal. Per spec §15 Q1, the removal is gated on named conditions, not a date. Adding a date would violate that decision.

## Test Coverage

| Test case | What it asserts |
|---|---|
| `test_warning_text_format` | The exact stderr line matches the format above for both directions. |
| `test_warning_emitted_only_once_per_pair` | Two calls with the same pair produce one stderr line. |
| `test_warning_emitted_again_for_different_pair` | Two calls with different pairs produce two stderr lines. |
| `test_suppression_env_var_skips_warning` | With env var set to `"1"`, no stderr line is produced. |
| `test_suppression_env_var_only_responds_to_one` | With env var set to `"0"` or `"false"` or `"true"` or unset, the warning IS emitted. Only `"1"` suppresses. |
| `test_inverse_suppression_env_var_independent` | Setting `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` does not suppress the inverse direction's warning. |
