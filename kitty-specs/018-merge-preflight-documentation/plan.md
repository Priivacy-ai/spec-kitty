# Implementation Plan: Merge Preflight Documentation

**Branch**: `018-merge-preflight-documentation` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/018-merge-preflight-documentation/spec.md`
**Mission**: documentation

## Summary

Create comprehensive user and developer documentation for Feature 017 (Smarter Feature Merge with Preflight). Outputs include a merge guide, troubleshooting guide, and CLAUDE.md reference updates. All documentation follows existing Divio-style structure in `docs/`.

## Technical Context

**Language/Version**: Markdown (CommonMark + GitHub Flavored Markdown)
**Primary Dependencies**: None (documentation only)
**Storage**: N/A
**Testing**: Manual verification - all command examples must be copy-pasteable and functional
**Target Platform**: docs/ directory (docfx static site)
**Project Type**: Documentation
**Performance Goals**: N/A
**Constraints**: Follow existing docs/how-to/ style and cross-reference patterns
**Scale/Scope**: 3 documentation deliverables

## Constitution Check

*GATE: No violations - documentation feature with no code changes*

- No new dependencies introduced
- No architectural changes
- No security implications
- Follows existing documentation patterns

## Project Structure

### Documentation Deliverables

```
docs/
├── how-to/
│   ├── merge-feature.md           # NEW: Complete merge workflow guide
│   └── troubleshoot-merge.md      # NEW: Recovery and conflict resolution
└── toc.yml                        # UPDATE: Add new pages

CLAUDE.md                          # UPDATE: Add Merge & Preflight Patterns section
```

### Content Sources (Feature 017 Implementation)

```
src/specify_cli/merge/
├── state.py          # MergeState dataclass, persistence functions
├── preflight.py      # run_preflight(), WPStatus, PreflightResult
├── executor.py       # execute_merge(), state integration
├── forecast.py       # predict_conflicts(), ConflictPrediction
├── status_resolver.py # resolve_status_conflicts()
└── ordering.py       # get_merge_order(), dependency handling

src/specify_cli/cli/commands/merge.py  # --resume, --abort flags, CLI interface
```

## Documentation Architecture

### 1. Merge Guide (`docs/how-to/merge-feature.md`)

**Divio Type**: How-To Guide
**Audience**: Users completing workspace-per-WP features
**Style Reference**: `docs/how-to/accept-and-merge.md`

**Structure**:
```
# How to Merge a Feature
├── Prerequisites
├── Basic Merge
│   └── Command + what happens
├── Merge Strategies
│   └── merge / squash / rebase
├── Pre-flight Validation
│   └── What it checks, interpreting results
├── Dry-Run Mode
│   └── Conflict forecasting, example output
├── Cleanup Options
│   └── --keep-branch, --keep-worktree
├── Troubleshooting (link to troubleshoot-merge.md)
├── Command Reference (links)
└── See Also (related guides)
```

### 2. Troubleshooting Guide (`docs/how-to/troubleshoot-merge.md`)

**Divio Type**: How-To Guide (problem-solution format)
**Audience**: Users recovering from merge issues
**Style Reference**: Troubleshooting sections in existing docs

**Structure**:
```
# How to Troubleshoot Merge Issues
├── Quick Reference (decision tree)
├── Interrupted Merge Recovery
│   ├── Using --resume
│   └── Using --abort
├── Merge State Explained
│   └── .kittify/merge-state.json structure
├── Conflict Resolution
│   ├── Status file conflicts (auto-resolved)
│   └── Code conflicts (manual resolution)
├── Pre-flight Failures
│   ├── Uncommitted changes
│   ├── Missing worktrees
│   └── Multiple issues
├── Error Message Reference
│   └── Each error + solution
└── See Also
```

### 3. CLAUDE.md Update

**Divio Type**: Reference
**Audience**: Developers and AI agents contributing to spec-kitty
**Location**: After "Workspace-per-Work-Package Development" section

**Content**:
```
### Merge & Preflight Patterns (0.11.0+)

**Merge State Persistence**:
- Location: `.kittify/merge-state.json`
- Structure: feature_slug, wp_order, completed_wps, current_wp, strategy
- Functions: save_state(), load_state(), clear_state(), has_active_merge()

**Pre-flight Validation**:
- Entry point: run_preflight() in merge/preflight.py
- Returns: PreflightResult with passed/failed, WP statuses, errors
- Checks: dirty worktrees, missing worktrees, branch existence

**Programmatic Access**:
[Code examples for working with merge state and preflight]

**Common Patterns**:
[Patterns for implementing merge-related features]
```

## Content Extraction Plan

### From Feature 017 Code

| Source | Extract For |
|--------|-------------|
| `merge.py` | All CLI flags, help text, user-facing messages |
| `state.py` | MergeState fields, JSON structure, function signatures |
| `preflight.py` | Validation checks, error messages, WPStatus enum |
| `executor.py` | Merge workflow steps, conflict handling |
| `forecast.py` | Dry-run output format, prediction types |
| `status_resolver.py` | Auto-resolution behavior |

### From Feature 017 Tests

| Source | Extract For |
|--------|-------------|
| `test_merge_state.py` | Expected state file formats |
| `test_merge_workspace_per_wp.py` | Integration scenarios |

## Writing Guidelines

1. **Follow existing style**: Match `accept-and-merge.md` structure
2. **Code blocks**: Always include both agent command and terminal command
3. **Cross-references**: Use relative links to related docs
4. **Examples**: Real command output from spec-kitty merge --dry-run
5. **Error messages**: Quote actual error text from code

## Complexity Tracking

*No violations - documentation only*

| Aspect | Status |
|--------|--------|
| New dependencies | None |
| Code changes | None |
| Architecture impact | None |
| Breaking changes | None |
