# Implementation Plan: Orchestrator-API JSON Contract Fidelity

**Branch**: `053-orchestrator-api-json-contract-fidelity` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)

## Summary

The orchestrator-api promises "JSON-first" but breaks that promise when invoked through the root CLI. The `_JSONErrorGroup` class only overrides `main()`, which is never called when the group is nested as a sub-app — Click dispatches via `invoke()` instead. Fix by adding `invoke()` override so errors are caught at the dispatch level. Remove stale `--json` flag from docs. Add integration tests that exercise the real `spec-kitty orchestrator-api ...` command path.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, click (typer's underlying library), rich
**Storage**: Filesystem only
**Testing**: pytest with `typer.testing.CliRunner`
**Target Platform**: CLI (macOS/Linux)
**Project Type**: Single Python package (`specify_cli`)
**Constraints**: Prefer deleting code over adding it; no backward-compat shims

## Constitution Check

No constitution violations. This feature reduces code and strengthens an existing contract — no new dependencies, patterns, or structural changes.

## Root Cause Analysis

### Why `_JSONErrorGroup.main()` doesn't work when nested

Click's command dispatching has two distinct entry points:

1. **`main()`** — Called once on the top-level command. Handles standalone_mode, argument parsing for the group itself, and then delegates to `invoke()`.

2. **`invoke()`** — Called by the parent group's dispatch. Resolves the subcommand, creates a child context, parses child arguments, and calls the child's `invoke()`.

When `spec-kitty orchestrator-api contract-version --bogus` is run:

```
spec-kitty (BannerGroup)
  └─ main()           ← top-level entry point, standalone_mode=True
       └─ invoke()    ← resolves "orchestrator-api" subcommand
            └─ orchestrator-api (_JSONErrorGroup)
                 └─ invoke()    ← resolves "contract-version", parses --bogus
                      └─ UsageError("No such option: --bogus")
```

The `UsageError` from `--bogus` propagates up through:
1. `_JSONErrorGroup.invoke()` — **NOT overridden**, so error passes through
2. `BannerGroup.invoke()` — inherited from TyperGroup, no error handling
3. `BannerGroup.main()` — inherited from TyperGroup, `standalone_mode=True` catches it and prints prose to stderr

`_JSONErrorGroup.main()` is never called in this flow. It's only called when tests invoke the sub-app directly: `runner.invoke(app, ["contract-version", "--bogus"])`.

### The fix

Override `invoke()` on `_JSONErrorGroup` to catch `click.UsageError` and `click.Abort` at the dispatch level. This intercepts errors before they reach the parent group.

Keep the existing `main()` override for the direct-invocation path (used by CliRunner tests that invoke the sub-app).

Extract a shared `_emit_error()` helper to eliminate duplication between `invoke()` and `main()`.

## Design

### Modified `_JSONErrorGroup` class

```python
class _JSONErrorGroup(TyperGroup):
    """Click Group that converts all parse/usage errors to JSON envelopes.

    Error handling at two levels ensures JSON output regardless of
    whether this group is invoked directly or as a nested sub-group:

    - invoke(): Catches errors during subcommand dispatch (nested path).
      This is the path taken when the root CLI dispatches to us via
      spec-kitty orchestrator-api <subcommand>.
    - main(): Catches errors during standalone invocation (direct path).
      This is the path taken by CliRunner tests and direct module execution.
    """

    def _emit_error(self, message: str) -> None:
        """Emit a USAGE_ERROR JSON envelope to stdout."""
        _emit(make_envelope(
            command="unknown",
            success=False,
            data={"message": message},
            error_code="USAGE_ERROR",
        ))

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except click.UsageError as exc:
            self._emit_error(exc.format_message())
            ctx.exit(2)
        except click.Abort:
            self._emit_error("Command aborted")
            ctx.exit(2)

    def main(self, *args, standalone_mode=True, **kwargs):
        try:
            rv = super().main(*args, standalone_mode=False, **kwargs)
            if isinstance(rv, int) and rv != 0:
                raise SystemExit(rv)
            return rv
        except click.UsageError as exc:
            self._emit_error(exc.format_message())
            raise SystemExit(2) from exc
        except click.Abort:
            self._emit_error("Command aborted")
            raise SystemExit(2)
        except SystemExit:
            raise
```

**Error flow with fix**:

```
Direct invocation (CliRunner tests):
  _JSONErrorGroup.main()
    → standalone_mode=False → errors propagate as exceptions
    → except click.UsageError → _emit_error() + SystemExit(2)

Nested invocation (real CLI path):
  BannerGroup.main()
    → BannerGroup.invoke()
      → _JSONErrorGroup.invoke()   ← NEW: catches errors here
        → except click.UsageError → _emit_error() + ctx.exit(2)
```

### Docs fix

Remove `--json` from `docs/reference/orchestrator-api.md` line 87:

```diff
-spec-kitty orchestrator-api contract-version --json [--provider-version <semver>]
+spec-kitty orchestrator-api contract-version [--provider-version <semver>]
```

Add a note in the docs header that all output is always JSON (no flag needed).

### Test strategy

Add a new test class that invokes through the **root CLI app** (imported from `specify_cli`), not the orchestrator-api sub-app:

```python
from specify_cli import app as root_app  # The real entry point

class TestRootCLIPath:
    """Tests that exercise the real spec-kitty orchestrator-api ... path."""

    def test_contract_version_through_root(self):
        result = runner.invoke(root_app, ["orchestrator-api", "contract-version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_unknown_flag_through_root(self):
        result = runner.invoke(root_app, ["orchestrator-api", "contract-version", "--bogus"])
        assert result.exit_code != 0
        env = _parse_envelope(result.output)
        assert env["error_code"] == "USAGE_ERROR"

    def test_unknown_subcommand_through_root(self):
        result = runner.invoke(root_app, ["orchestrator-api", "nonexistent"])
        assert result.exit_code != 0
        env = _parse_envelope(result.output)
        assert env["error_code"] == "USAGE_ERROR"
```

## Project Structure

### Documentation (this feature)

```
kitty-specs/053-orchestrator-api-json-contract-fidelity/
├── spec.md
├── plan.md              # This file
├── research.md          # Root cause analysis (inlined above — no separate file needed)
├── data-model.md        # N/A (no data model changes)
└── tasks.md             # Generated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── orchestrator_api/
│   └── commands.py          # _JSONErrorGroup: add invoke() override, extract _emit_error()
└── cli/
    └── commands/__init__.py  # No changes (registration stays as-is)

docs/reference/
└── orchestrator-api.md      # Remove --json from contract-version signature

tests/agent/
├── test_json_envelope_contract_integration.py   # Add root CLI path tests
└── test_orchestrator_commands_integration.py     # No changes needed
```

**Structure Decision**: Minimal changes — one file modified in source, one file modified in docs, one file modified in tests.

## Files Changed

| File | Change |
|------|--------|
| `src/specify_cli/orchestrator_api/commands.py` | Add `invoke()` override and `_emit_error()` helper to `_JSONErrorGroup` |
| `docs/reference/orchestrator-api.md` | Remove `--json` flag from contract-version signature |
| `tests/agent/test_json_envelope_contract_integration.py` | Add `TestRootCLIPath` class exercising the real entry path |

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `ctx.exit(2)` in `invoke()` might behave differently from `raise SystemExit(2)` in `main()` | `ctx.exit()` internally raises `SystemExit`, so behavior is identical. Verify in tests. |
| Double JSON emission if both `invoke()` and `main()` catch the same error | `invoke()` errors raise `SystemExit` which `main()` passes through via `except SystemExit: raise`. No double emission. |
| Root CLI callback (`ensure_runtime`, `check_version_pin`) might fail before reaching orchestrator-api | Out of scope — root CLI errors are not part of the orchestrator-api contract. |

## Complexity Tracking

No constitution violations to justify.
