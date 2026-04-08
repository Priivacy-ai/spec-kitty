# Phase 1 Data Model: Mission Terminology Cleanup

**Mission**: `077-mission-terminology-cleanup`
**Date**: 2026-04-08

This document defines the in-memory data structures introduced by this mission. There is **no persisted state**: this mission modifies CLI parameter declarations, helper modules, doctrine skill markdown, doc markdown, and contract tests. Nothing is written to disk beyond source-code edits.

## Scope of the Data Model

The "data model" for this mission is essentially the type signature of one helper function and one small dataclass. There are no entities, no relationships, no state transitions. The model exists entirely to make the contract for the selector-resolution helper precise enough that an implementer cannot misread it.

## Entities

### `SelectorResolution`

A frozen dataclass returned by the selector-resolution helper. Captures the canonical resolved value and a structured record of how it was resolved (so callers and tests can assert on the path taken).

| Field | Type | Description |
|---|---|---|
| `canonical_value` | `str` | The resolved canonical slug. Guaranteed non-empty when the helper returns successfully. |
| `canonical_flag` | `str` | The literal canonical flag name as it appears on the command line, e.g. `"--mission"` or `"--mission-type"`. Used in error messages. |
| `alias_used` | `bool` | `True` if the legacy alias parameter (`--feature` or `--mission`) supplied the value. `False` if the canonical parameter supplied it. When both supplied the same value, `True` (because the alias did contribute). |
| `alias_flag` | `str \| None` | The literal alias flag name (e.g. `"--feature"`) when `alias_used` is `True`; `None` otherwise. Used in the deprecation warning message. |
| `warning_emitted` | `bool` | `True` if a deprecation warning was emitted to stderr during this resolution. `False` if `alias_used` is `False`, or if `alias_used` is `True` but the suppression env var was set. Used by tests. |

**Validation rules**:
- `canonical_value` is always non-empty when returned from the helper. If the input is missing/empty, the helper raises `typer.BadParameter` *before* constructing a `SelectorResolution` — there is no "empty" or "unresolved" state.
- `canonical_flag` and `alias_flag` are passed in by the call site (so the helper supports both `--mission`/`--feature` and `--mission-type`/`--mission` direction with the same code path).
- If `alias_used` is `True`, `alias_flag` must be a non-empty string. If `alias_used` is `False`, `alias_flag` must be `None`. Enforced by `__post_init__`.

**Frozen**: yes (`@dataclass(frozen=True, slots=True)`).

### `SelectorConflictError`

Not a new exception class — the helper raises `typer.BadParameter` directly so the typer error rendering pipeline handles output formatting consistently with the rest of the CLI. The exception's message follows the format defined in `contracts/selector_resolver.md` §"Conflict Error Format".

## Helper Function Signature

```python
def resolve_selector(
    *,
    canonical_value: str | None,
    canonical_flag: str,
    alias_value: str | None,
    alias_flag: str,
    suppress_env_var: str,
    command_hint: str | None = None,
) -> SelectorResolution:
    """Resolve a canonical/deprecated-alias selector pair into one canonical value.

    This is the central enforcement point for FR-006, FR-007, FR-021, and the
    §11.1 hidden-deprecated-alias migration policy. Every tracked-mission and
    inverse-drift command in the main CLI calls this helper after typer parses
    the parameters.

    Args:
        canonical_value: Value parsed from the canonical typer parameter
            (e.g. the value provided via ``--mission``).
        canonical_flag: Literal canonical flag name for error messages
            (e.g. ``"--mission"`` or ``"--mission-type"``).
        alias_value: Value parsed from the hidden alias typer parameter
            (e.g. the value provided via ``--feature`` or ``--mission``).
        alias_flag: Literal alias flag name for error messages
            (e.g. ``"--feature"`` or ``"--mission"``).
        suppress_env_var: Name of the environment variable that, when set
            to ``"1"``, suppresses the deprecation warning emit (still resolves,
            still detects conflict). E.g. ``"SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION"``.
        command_hint: Optional command-name hint included in the missing-value
            error message. Forwarded to ``require_explicit_feature``.

    Returns:
        A frozen ``SelectorResolution`` describing the canonical value and
        how it was resolved.

    Raises:
        typer.BadParameter: If both flags supplied non-equal non-empty values
            (FR-006 / inverse FR-021), or if neither flag supplied a value
            (delegated to ``require_explicit_feature``).
    """
```

### Resolution Algorithm

The helper follows a deterministic decision tree. The order of checks matters because conflict detection must run *before* deprecation warning emission (otherwise a conflict case would emit a warning that the caller never sees because the BadParameter raises first).

```
1. Normalize:
   canonical_norm = (canonical_value or "").strip() or None
   alias_norm     = (alias_value or "").strip() or None

2. Both empty:
   If canonical_norm is None and alias_norm is None:
       raise typer.BadParameter via require_explicit_feature(None, command_hint=...)

3. Both set, conflicting:
   If canonical_norm and alias_norm and canonical_norm != alias_norm:
       raise typer.BadParameter(
           f"Conflicting selectors: {canonical_flag}={canonical_norm!r} "
           f"and {alias_flag}={alias_norm!r} were both provided with "
           f"different values. {alias_flag} is a hidden deprecated alias "
           f"for {canonical_flag}; pass only {canonical_flag}."
       )

4. Both set, equal:
   If canonical_norm and alias_norm and canonical_norm == alias_norm:
       _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
       return SelectorResolution(
           canonical_value=canonical_norm,
           canonical_flag=canonical_flag,
           alias_used=True,
           alias_flag=alias_flag,
           warning_emitted=<see warning function>,
       )

5. Only canonical set:
   If canonical_norm and not alias_norm:
       return SelectorResolution(
           canonical_value=canonical_norm,
           canonical_flag=canonical_flag,
           alias_used=False,
           alias_flag=None,
           warning_emitted=False,
       )

6. Only alias set:
   If alias_norm and not canonical_norm:
       _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
       return SelectorResolution(
           canonical_value=alias_norm,
           canonical_flag=canonical_flag,
           alias_used=True,
           alias_flag=alias_flag,
           warning_emitted=<see warning function>,
       )
```

### Deprecation Warning Sub-helper

```python
def _emit_deprecation_warning(
    canonical_flag: str,
    alias_flag: str,
    suppress_env_var: str,
) -> bool:
    """Emit a single yellow stderr deprecation warning unless suppressed.

    The single-warning-per-invocation guarantee (NFR-002) is enforced by a
    module-level set of (canonical_flag, alias_flag) pairs. The set is reset
    at the start of each Python process, so re-entrant CLI invocations from
    tests get fresh state.

    Returns:
        True if a warning was actually emitted, False if suppressed.
    """
```

State variables for the single-warning guarantee:

- Module-level: `_warned: set[tuple[str, str]] = set()`
- Each unique `(canonical_flag, alias_flag)` pair is added on first emit.
- Subsequent calls within the same process check `(canonical_flag, alias_flag) in _warned` and skip the emit.
- Tests that need to verify multi-emit behavior must reset the module-level set explicitly via a fixture.

## What This Mission Does NOT Add to the Data Model

To preserve the spec's locked non-goals (§3.3, C-001..C-011):

- ❌ No new persisted state. Nothing under `kitty-specs/<mission>/`, nothing in `meta.json`, nothing in `status.events.jsonl`, nothing in `.kittify/`.
- ❌ No new event types in `spec-kitty-events`.
- ❌ No new fields in any payload defined by `upstream_contract.json`.
- ❌ No `mission_run_slug` field anywhere.
- ❌ No new `aggregate_type` value.
- ❌ No new typer command groups (`agent`, `mission`, `mission-type`, etc.) and no renames of existing ones.
- ❌ No new top-level keys in the orchestrator-api envelope (C-010).
- ❌ No new `_vendored/` files.

## Type Checking

All new code is `mypy --strict`-clean:
- All fields on `SelectorResolution` have explicit types.
- The helper function signature uses keyword-only arguments and explicit return type.
- The module-level `_warned` set is annotated.
- The `Console(stderr=True)` import and usage is type-correct against current `rich` stubs.

## Test Fixture for the Module-Level State

```python
@pytest.fixture(autouse=True)
def _reset_selector_resolution_state():
    """Reset the module-level _warned set between tests."""
    from specify_cli.cli import selector_resolution
    selector_resolution._warned.clear()
    yield
    selector_resolution._warned.clear()
```

This fixture is `autouse=True` in `tests/specify_cli/cli/commands/test_selector_resolution.py` and in any other test file that exercises the helper. Without it, test order would affect whether the deprecation warning is emitted, and CI would be flaky.
