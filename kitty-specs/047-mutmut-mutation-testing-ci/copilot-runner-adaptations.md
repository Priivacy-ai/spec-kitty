# GitHub Copilot Runner Adaptations for Mutation Testing

**Created**: 2026-03-01
**Context**: WP03 implementation attempt on GitHub Copilot runner

## Problem Statement

The spec-kitty workflow commands and mutation testing infrastructure are optimized for local interactive development, but encounter significant environmental issues when executed on GitHub Copilot's delegated runner environment.

## Issues Encountered

### 1. Mutmut Environment Isolation Issues

**Problem**: Mutmut 3.x creates a `mutants/` subdirectory and copies only the files being mutated, not their dependencies. This breaks imports when tests try to access the full `specify_cli` module.

**Symptoms**:
- `ModuleNotFoundError: No module named 'specify_cli.frontmatter'`
- `ModuleNotFoundError: No module named 'specify_cli.missions'`
- `ModuleNotFoundError: No module named 'specify_cli.validators'`
- `ModuleNotFoundError: No module named 'specify_cli.orchestrator_api'`

**Root Cause**: Mutmut's design assumes a flat package structure or that all tests can run with only the mutated modules present. The spec-kitty codebase has deep interdependencies that mutmut doesn't handle well.

### 2. Test Suite Import Errors

**Problem**: Multiple test directories have import errors due to missing/moved modules:

- `tests/adversarial/test_csv_attacks.py` → requires `specify_cli.validators.csv_schema`
- `tests/contract/test_handoff_fixtures.py` → requires `specify_cli.spec_kitty_events.models`
- `tests/cross_branch/test_parity.py` → requires `specify_cli.frontmatter`
- `tests/integration/orchestrator_api/` → requires `specify_cli.orchestrator_api`

**Workaround Attempted**: Added `--ignore` flags to skip problematic test directories, but this creates a fragile configuration that requires constant maintenance.

### 3. Test Venv Isolation

**Problem**: Test fixtures attempt to create isolated venvs and install the package in editable mode, but fail when run from the `mutants/` subdirectory:

```
OSError: License file does not exist: LICENSE
```

**Root Cause**: The `mutants/` directory doesn't contain a complete project structure (missing LICENSE, missing full src tree, etc.), so `pip install -e` fails.

### 4. Agent Command Infrastructure Missing

**Problem**: GitHub Copilot doesn't have prompt/command files in `.github/prompts/` like other agents (Claude, Codex, OpenCode).

**Impact**: Slash commands like `/spec-kitty.implement` and `/spec-kitty.review` aren't available in the Copilot environment, making the workflow harder to follow.

## Proposed Solutions

### Short-term: Direct pytest Approach

Instead of using mutmut's built-in runner, use pytest-mutagen or cosmic-ray which have better isolation:

```bash
# Alternative: pytest-mutagen (pytest plugin)
pip install pytest-mutagen
pytest --mutate src/specify_cli/status/ --mutate src/specify_cli/glossary/

# Alternative: cosmic-ray (more mature)
pip install cosmic-ray
cosmic-ray init config.toml session.sqlite
cosmic-ray exec session.sqlite
```

### Medium-term: Fix mutmut Configuration

Create a custom runner script that:
1. Copies the full `src/` directory, not just mutated files
2. Symlinks or copies test fixtures (LICENSE, pyproject.toml, etc.)
3. Sets up PYTHONPATH correctly before running tests

Example script (`scripts/run_mutmut_isolated.sh`):
```bash
#!/bin/bash
# Prepare full environment in mutants/ directory
cp -r src/ mutants/src/
cp LICENSE pyproject.toml pytest.ini mutants/
cd mutants
export PYTHONPATH=$PWD/src:$PWD
pytest tests/specify_cli/glossary/ tests/specify_cli/cli/commands/test_status_cli.py
```

### Long-term: GitHub Copilot Integration

Add command files to `.github/prompts/` following the same pattern as Claude/Codex:

```bash
.github/prompts/
├── spec-kitty.implement.md
├── spec-kitty.review.md
├── spec-kitty.tasks.md
└── ...
```

This would make the workflow commands available in the Copilot interface.

## Recommended Immediate Action

**For WP03 completion on Copilot runner**:

1. **Skip mutmut for now** - The environmental issues are too deep to fix quickly
2. **Focus on writing targeted tests** - Identify high-value test gaps by:
   - Manual code review of status/ and glossary/
   - Coverage analysis (`pytest --cov=src/specify_cli/status/ --cov=src/specify_cli/glossary/`)
   - Examining the transition matrix in `transitions.py`
   - Looking for guard conditions without tests
3. **Run mutmut locally** - Have a developer with a proper local environment run the mutation testing and share results
4. **Document equivalent mutants** - Create the `mutmut-equivalents.md` file based on local runs

## Files Modified

- `pyproject.toml`: Updated mutmut config with test filtering and runner specification (reverted after issues)
- `.gitignore`: Already contains mutmut artifact patterns (mutants/, *.py.meta, .mutmut-cache)

## Next Steps for Future WPs

- [ ] Evaluate pytest-mutagen as alternative to mutmut
- [ ] Create custom mutation test runner script for CI
- [ ] Add .github/prompts/ commands for Copilot integration
- [ ] Document the "local-first, CI-verify" workflow for mutation testing
- [ ] Consider moving mutation testing to optional CI job (workflow_dispatch only)
