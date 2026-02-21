# Implementation Plan: Adversarial Test Suite for 0.13.0

**Branch**: `024-adversarial-test-suite-0-13-0` | **Date**: 2026-01-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/024-adversarial-test-suite-0-13-0/spec.md`

## Summary

Create a comprehensive adversarial test suite for spec-kitty 0.13.0 that validates security, robustness, and edge-case handling across 9 categories: distribution testing, path validation, CSV schema attacks, git state detection, migration robustness, multi-parent merges, workspace context, context validation bypass, and agent config manipulation. Tests will be organized in a new `tests/adversarial/` directory with one file per category.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing test suite)
**Primary Dependencies**: pytest, pytest-timeout (existing), multiprocessing (stdlib)
**Storage**: N/A (test suite)
**Testing**: pytest with existing conftest.py fixtures
**Target Platform**: Linux/macOS (CI), Windows (best-effort)
**Project Type**: Single project - test module addition
**Performance Goals**: Full test suite runs in under 5 minutes on CI
**Constraints**: Must not require additional CI infrastructure; must work with existing fixtures
**Scale/Scope**: ~50-70 test cases across 9 test files

## Constitution Check

*No constitution file found - skipping constitution gates.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/024-adversarial-test-suite-0-13-0/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Test entity definitions
├── quickstart.md        # Implementation quickstart
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # WP files (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/
├── adversarial/                          # NEW: Adversarial test suite
│   ├── __init__.py
│   ├── conftest.py                       # Shared adversarial fixtures
│   ├── test_distribution.py              # P1: PyPI user experience validation
│   ├── test_path_validation.py           # P1: Directory traversal, symlinks
│   ├── test_csv_attacks.py               # P1: Injection, encoding, malformed
│   ├── test_git_state.py                 # P2: Detached HEAD, merge state
│   ├── test_migration_robustness.py      # P2: Interruption, concurrency
│   ├── test_multi_parent_merge.py        # P2: Diamond deps, conflicts
│   ├── test_workspace_context.py         # P3: Orphaned, corrupted contexts
│   ├── test_context_validation.py        # P3: Bypass prevention
│   └── test_agent_config.py              # P3: Corrupt YAML handling
├── conftest.py                           # Existing root conftest (extend)
└── [existing test directories...]
```

**Structure Decision**: New `tests/adversarial/` directory keeps adversarial tests isolated and organized by attack category, following the user's preference for Option A.

## Key Design Decisions

### 1. Distribution Tests Without SPEC_KITTY_TEMPLATE_ROOT

Distribution tests (`test_distribution.py`) will:

- Build wheel from source using `python -m build`
- Install into fresh venv without `SPEC_KITTY_TEMPLATE_ROOT`
- Validate template resolution uses packaged templates
- Test all three mission types (software-dev, research, documentation)

This directly addresses the 0.10.8 catastrophe where 100% of tests used the bypass.

### 2. Fixture Strategy

New fixtures in `tests/adversarial/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `malicious_paths` | Parametrized path traversal vectors |
| `malformed_csv` | Factory for creating attack CSVs |
| `git_merge_state` | Create repos in merge/rebase state |
| `detached_head_repo` | Create worktree in detached HEAD |
| `concurrent_migration` | Multiprocessing setup for race tests |
| `corrupt_config` | Generate malformed config.yaml |
| `symlink_factory` | Cross-platform symlink creation |

### 3. Platform Considerations

- Symlink tests: Skip on Windows if not elevated
- Case-sensitivity tests: Mark as `@pytest.mark.skipif` on case-sensitive FS
- Concurrent tests: Use `multiprocessing` not `threading` (GIL)

### 4. Test Markers

```python
pytest.mark.adversarial      # All adversarial tests
pytest.mark.distribution     # Distribution-only (isolated CI job)
pytest.mark.slow            # Tests > 10s (concurrent/build)
pytest.mark.platform_linux  # Linux-specific edge cases
pytest.mark.platform_darwin # macOS-specific (case-insensitive FS)
```

## Target Modules Under Test

| Test File | Target Module(s) | Attack Surface |
|-----------|------------------|----------------|
| test_distribution.py | Package bundling | Template resolution |
| test_path_validation.py | `mission.py:validate_deliverables_path()` | Path traversal, symlinks |
| test_csv_attacks.py | `validators/csv_schema.py` | Injection, encoding |
| test_git_state.py | `cli/commands/agent/tasks.py:_validate_ready_for_review()` | Git state detection |
| test_migration_robustness.py | `upgrade/runner.py`, `upgrade/metadata.py` | Atomicity, concurrency |
| test_multi_parent_merge.py | `core/multi_parent_merge.py` | Conflict handling |
| test_workspace_context.py | `workspace_context.py` | Orphaned/corrupt JSON |
| test_context_validation.py | `core/context_validation.py` | Decorator bypass |
| test_agent_config.py | `upgrade/migrations/*.py` | Config parsing |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Distribution tests slow CI | Separate marker, run only on release branches |
| Concurrent tests flaky | Use file locks, increase timeout, retry once |
| Symlink tests platform-dependent | Skip gracefully with clear message |
| Multiprocessing spawn issues | Use `spawn` context explicitly on all platforms |

## Dependencies

- No new dependencies required
- Uses existing: pytest, pytest-timeout
- stdlib only: multiprocessing, tempfile, pathlib
