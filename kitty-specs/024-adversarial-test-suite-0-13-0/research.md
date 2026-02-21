# Research: Adversarial Test Suite for 0.13.0

**Date**: 2026-01-25
**Feature**: 024-adversarial-test-suite-0-13-0

## Executive Summary

Deep analysis of spec-kitty 0.13.0 changes identified **critical vulnerabilities** requiring adversarial testing. The research examined source code, ADRs, and existing test coverage to find gaps that could cause user-facing failures.

## Research Findings

### 1. Path Validation Vulnerabilities (CRITICAL)

**Source**: `src/specify_cli/mission.py:561-637`

**Identified Attack Vectors**:

| Attack | Current Behavior | Risk |
|--------|------------------|------|
| `../../../etc/passwd` | Not blocked | Directory traversal |
| `Kitty-Specs/` (case) | Not blocked on macOS | Bypass kitty-specs check |
| Symlink to kitty-specs/ | Not resolved | Symlink bypass |
| Empty string `""` | Passes validation | Write to project root |
| `~/research/` | Not blocked | Home directory escape |
| Null bytes `\x00` | Not validated | Path injection |

**Decision**: Test all vectors; expect explicit rejection with clear error messages.

### 2. CSV Schema Vulnerabilities (HIGH)

**Source**: `src/specify_cli/validators/csv_schema.py:62-117`

**Identified Attack Vectors**:

| Attack | Current Behavior | Risk |
|--------|------------------|------|
| Formula injection (`=cmd\|...`) | No warning | Spreadsheet code execution |
| Invalid UTF-8 | Generic exception | Poor UX |
| Duplicate columns | Not detected | Silent data loss |
| Empty file | "Schema mismatch" | Confusing error |
| UTF-8 BOM + wrong encoding | Partial handling | Data corruption |

**Decision**: Test all vectors; focus on clear error messages over execution prevention (CSV injection is spreadsheet-level risk).

### 3. Git State Detection Gaps (MEDIUM)

**Source**: `src/specify_cli/cli/commands/agent/tasks.py:218-356`

**Identified Issues**:

| Scenario | Current Behavior | Risk |
|----------|------------------|------|
| Detached HEAD | May pass validation | Incomplete work reaches review |
| MERGE_HEAD exists | Not checked | Merge state undetected |
| Staged but uncommitted | Error says "uncommitted" | Confusing guidance |
| Main diverged from origin | Uses local `main` | Stale base undetected |
| Submodules | Not handled | Modified submodules block review |

**Decision**: Test each git state; verify correct detection and actionable error messages.

### 4. Migration Race Conditions (HIGH)

**Source**: `src/specify_cli/upgrade/runner.py`, `metadata.py`

**Identified Issues**:

| Scenario | Current Behavior | Risk |
|----------|------------------|------|
| Concurrent upgrade | No lock | Data corruption |
| Kill mid-write | No atomic writes | Corrupted metadata |
| Partial migration | Marked as applied | Silently incomplete |
| Permission denied | Generic OSError | Poor UX |

**Decision**: Test with multiprocessing; verify recovery scenarios.

### 5. Multi-Parent Merge Edge Cases (MEDIUM)

**Source**: `src/specify_cli/core/multi_parent_merge.py` (per ADR 4)

**Identified Issues**:

| Scenario | Current Behavior | Risk |
|----------|------------------|------|
| Merge conflict during auto-merge | Detected but cleanup unclear | Orphaned branches |
| Non-deterministic order | Sorted, but untested | Reproducibility |
| Diamond with 3+ parents | Sequential merge | Increased conflict risk |

**Decision**: Test diamond patterns; verify determinism and cleanup.

### 6. Distribution Testing Gap (CRITICAL)

**Source**: `tests/integration/conftest.py:44` - All tests use `SPEC_KITTY_TEMPLATE_ROOT`

**Finding**: Zero tests validate PyPI user experience. The 0.10.8 catastrophe (100% user failure despite 323 passing tests) was caused by this gap.

**Decision**: Create dedicated distribution tests that:

- Build wheel from source
- Install without SPEC_KITTY_TEMPLATE_ROOT
- Validate template resolution

## ADR Analysis

### ADR 7: Research Deliverables Separation

**Attack Surface**: `deliverables_path` validation in `mission.py`

**Key Assumptions to Test**:

- Path must NOT be inside kitty-specs/
- Path should not be project root
- Symlinks should be resolved

### ADR 8: CSV Schema Enforcement

**Attack Surface**: Schema validation in `csv_schema.py`

**Key Assumptions to Test**:

- Agents see schema before editing (documentation, not enforcement)
- Validation during review catches mismatches
- Migration is informational-only

### ADR 4: Auto-Merge Multi-Parent

**Attack Surface**: `create_multi_parent_base()` function

**Key Assumptions to Test**:

- Deterministic merge ordering
- Conflict detection and cleanup
- No orphaned temporary branches

### ADR 5: Context Validation Decorators

**Attack Surface**: `@require_main_repo` decorator

**Key Assumptions to Test**:

- Cannot be bypassed via environment variables
- Filesystem check is authoritative
- Works from any subdirectory

### ADR 6: Config-Driven Agent Management

**Attack Surface**: `get_agent_dirs_for_project()` function

**Key Assumptions to Test**:

- Corrupt config produces clear error (not silent fallback)
- Missing config has explicit warning
- Unknown agent keys are reported

## Existing Test Coverage Analysis

| Area | Existing Tests | Gap |
|------|----------------|-----|
| Path validation | 0 adversarial | All attack vectors |
| CSV validation | 13 unit tests | Injection, encoding, duplicates |
| Git state | 0 for detached HEAD | Merge state, divergence |
| Migrations | 15 integration | Concurrency, interruption |
| Multi-parent | 8 unit, 3 integration | Determinism, cleanup |
| Distribution | 0 | Everything |
| Context validation | 23 unit | Env var bypass |
| Agent config | 20 unit, 11 integration | Corrupt YAML |

## Recommendations

1. **P1: Distribution tests first** - Prevents another 0.10.8 catastrophe
2. **P1: Path validation** - Security-critical, easy to implement
3. **P1: CSV attacks** - User data integrity
4. **P2: Git state** - Workflow correctness
5. **P2: Migration robustness** - Data safety
6. **P2: Multi-parent merge** - Complex feature validation
7. **P3: Context/config** - Edge cases, lower user impact

## Files Analyzed

- `/Users/robert/Code/spec-kitty/src/specify_cli/mission.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/validators/csv_schema.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/upgrade/runner.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/upgrade/metadata.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/core/multi_parent_merge.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/workspace_context.py`
- `/Users/robert/Code/spec-kitty/src/specify_cli/core/context_validation.py`
- `/Users/robert/Code/spec-kitty/architecture/adrs/*.md` (ADRs 4, 5, 6, 7, 8)
- `/Users/robert/Code/spec-kitty/tests/conftest.py`
- `/Users/robert/Code/spec-kitty/tests/integration/conftest.py`
