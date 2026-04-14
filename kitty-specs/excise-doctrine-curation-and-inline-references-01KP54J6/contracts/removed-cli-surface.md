# Contract: Removed CLI Surface

**Introduced in**: WP1.1
**Plan reference**: plan.md WP1.1
**Spec reference**: FR-003, Success Criterion 3

---

## Commands removed

The following Typer subcommands and their Typer app are removed in WP1.1. Any invocation after Phase 1 ships must return the standard Typer "unknown command" error with no shim text.

| Command | Previous purpose | Post-Phase-1 behavior |
| --- | --- | --- |
| `spec-kitty doctrine curate` | Launch interactive curation interview for `_proposed/` artifacts | Unknown command |
| `spec-kitty doctrine status` | Print proposed vs shipped counts per kind | Unknown command |
| `spec-kitty doctrine promote` | Promote one artifact by ID from `_proposed/` to shipped | Unknown command |
| `spec-kitty doctrine reset` | Clear in-flight curation session state | Unknown command |
| `spec-kitty doctrine` (parent) | Typer app entry point | Unknown command — parent group is unregistered |

## Python API removed

| Symbol | Module | Action |
| --- | --- | --- |
| `doctrine_module.app` (Typer app) | `src/specify_cli/cli/commands/doctrine.py` | Delete file |
| `app.add_typer(doctrine_module.app, name="doctrine")` | `src/specify_cli/cli/commands/__init__.py` | Delete registration line |
| `ProposedArtifact` | `src/doctrine/curation/engine.py` | Delete module |
| `discover_proposed()` | `src/doctrine/curation/engine.py` | Delete module |
| `promote_artifact_to_shipped()` | `src/doctrine/curation/engine.py` | Delete module |
| `CurationSession`, `load_session()`, `clear_session()` | `src/doctrine/curation/state.py` | Delete module |
| `run_curate_session()`, `promote_single()`, `get_status_counts()` | `src/doctrine/curation/workflow.py` | Delete module |
| All exports of `src/specify_cli/validators/doctrine_curation.py` | — | Delete module |
| `load_doctrine_catalog(include_proposed=...)` parameter | `src/charter/catalog.py` | Remove parameter (WP1.3) |

## Tests removed

| Path | Action |
| --- | --- |
| `tests/doctrine/curation/` (entire directory) | Delete in WP1.1 |
| `tests/cross_cutting/test_doctrine_curation_unit.py` | Delete in WP1.1 |

## Documentation / template references removed

All occurrences of the removed command names in SOURCE documentation must be removed or rewritten. Agent copy directories are out of scope (they re-flow on the next `spec-kitty upgrade`).

In-scope directories:
- `src/specify_cli/missions/*/command-templates/`
- `src/specify_cli/skills/` (if any skill references doctrine curate/promote)
- `src/doctrine/*/README.md`
- `src/charter/README.md` (the compiler/resolver table entries need updates once WP1.3 removes the resolver)
- `docs/` (if any explanation/how-to references these commands)

## Integration test (WP1.1)

```python
# tests/specify_cli/cli/test_doctrine_cli_removed.py (NEW, WP1.1)
from typer.testing import CliRunner
from specify_cli.cli.app import app

def test_doctrine_curate_is_unknown_command():
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "curate"])
    assert result.exit_code != 0
    # Typer's unknown-command error references the command name
    assert "doctrine" in (result.output + str(result.exception)).lower()

def test_doctrine_parent_group_is_unregistered():
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "--help"])
    assert result.exit_code != 0
```

This test lives on `main` after WP1.1 merges and remains there — it's the durable regression gate against reintroduction.

## Out of scope

- Deprecation warnings, shims, aliases, redirects — none. Per spec C-001.
- Migration of user-local curation session state (`.kittify/charter/context-state.json` has NO relation to curation state; there is no user data to migrate).
