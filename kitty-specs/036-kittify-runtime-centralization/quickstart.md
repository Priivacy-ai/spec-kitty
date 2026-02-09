# Quickstart: ~/.kittify Runtime Centralization

**Feature**: 036-kittify-runtime-centralization
**Date**: 2026-02-09

## For Users

### After Upgrading

```bash
pip install --upgrade spec-kitty-cli
# That's it! Next spec-kitty command auto-updates ~/.kittify/
spec-kitty doctor  # Verify global runtime is healthy
```

### Migrating Existing Projects (Optional)

```bash
# Preview what would change
spec-kitty migrate --dry-run

# Run migration
spec-kitty migrate

# Verify resolution
spec-kitty config --show-origin
```

### Customizing Templates Per-Project

```bash
# Copy a global template to project overrides
mkdir -p .kittify/overrides/templates/
cp ~/.kittify/missions/software-dev/templates/spec.md .kittify/overrides/templates/spec.md
# Edit .kittify/overrides/templates/spec.md to your needs
```

### Setting Custom Global Path

```bash
export SPEC_KITTY_HOME=/path/to/custom/kittify
spec-kitty doctor  # Verify it resolves correctly
```

## For Developers

### Key Module: `src/specify_cli/runtime/`

```python
from specify_cli.runtime import get_kittify_home, ensure_runtime
from specify_cli.runtime.resolver import resolve_template, resolve_mission, ResolutionTier

# Get global runtime path
home = get_kittify_home()  # ~/.kittify/ on Unix, %LOCALAPPDATA%\kittify\ on Windows

# Ensure runtime is up to date (called automatically on CLI startup)
ensure_runtime()

# Resolve a template with 4-tier precedence
result = resolve_template("spec.md", project_dir=Path("."), mission="software-dev")
print(f"Resolved from: {result.path} (tier: {result.tier.name})")
```

### Running Tests

```bash
# Unit tests for runtime module
pytest tests/unit/runtime/ -v

# Integration tests for CLI commands
pytest tests/integration/test_migrate.py -v
pytest tests/integration/test_doctor_global.py -v
pytest tests/integration/test_config_show_origin.py -v

# Concurrency tests (G5)
pytest tests/concurrency/test_ensure_runtime_concurrent.py -v

# All Phase 1A tests
pytest tests/ -k "runtime or migrate or doctor_global or show_origin or legacy or pin_version or bootstrap" -v
```

### Test Fixtures

| Fixture | Directory | Tests |
|---------|-----------|-------|
| F-Legacy-001 | `tests/fixtures/f_legacy_001/` | Customized templates, deprecation warnings |
| F-Legacy-002 | `tests/fixtures/f_legacy_002/` | No customizations, identical copies |
| F-Legacy-003 | `tests/fixtures/f_legacy_003/` | Stale differing template, legacy resolution |
| F-Pin-001 | `tests/fixtures/f_pin_001/` | Version pinning warning |
| F-Bootstrap-001 | `tests/fixtures/f_bootstrap_001/` | Interrupted update recovery |

### Quality Gates

| Gate | What it tests | Key tests |
|------|--------------|-----------|
| G2 | Resolution precedence | `test_resolver.py` — override > legacy > global > package |
| G3 | Migration correctness | `test_migrate.py` — dry-run, idempotency, classification |
| G5 | Concurrency safety | `test_ensure_runtime_concurrent.py` — N parallel processes |
| G6 | Cross-platform paths | `test_home.py` — macOS, Linux, Windows, env override |
