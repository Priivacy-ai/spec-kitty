---
work_package_id: WP10
title: Cherry-Pick to 2.x + Release v2.0.0a2
lane: "done"
dependencies: []
base_branch: main
subtasks: [T072, T073, T074, T075, T076, T077, T078, T079, T080, T081, T082, T083]
phase: Phase 3 - 2.x Release
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# Work Package Prompt: WP10 – Cherry-Pick to 2.x + Release v2.0.0a2

## Objectives

- All 7 bug fixes cherry-picked to 2.x branch
- Bug #119 manually ported (acceptance_core.py → acceptance.py)
- Tests adapted for 2.x structure
- Full test suite passing on 2.x
- v2.0.0a2 released and published to PyPI

**Command**: `spec-kitty implement WP10 --base WP09`

## Context

- **Dependency**: WP09 (v0.15.0 must be released on main first)
- **Branch**: 2.x (currently at v2.0.0a1)
- **Known Divergence**: acceptance_core.py exists on main, NOT on 2.x
- **Strategy**: Cherry-pick with -x flag, manual port for #119

## Subtasks

### T072-T078: Cherry-Pick with -x Flag

For bugs #95, #120, #117, #124, #122, #123:
```bash
git checkout 2.x
git pull origin 2.x

# Get commit SHAs from main
git log origin/main --oneline | grep "fixes #95"
# Capture SHA

# Cherry-pick with -x (adds audit trail)
git cherry-pick -x <bug-95-sha>
git cherry-pick -x <bug-120-sha>
git cherry-pick -x <bug-117-sha>  # May conflict (resolve if needed)
git cherry-pick -x <bug-124-sha>
git cherry-pick -x <bug-122-sha>
git cherry-pick -x <bug-123-sha>
```

### T076: Manually Port Bug #119 to 2.x

**Why manual**: `acceptance_core.py` doesn't exist on 2.x

**Files on 2.x**:
- `src/specify_cli/core/acceptance.py`
- `src/specify_cli/core/acceptance_support.py`

**Process**:
1. Find equivalent assignee validation logic in 2.x acceptance modules
2. Apply same fix (make assignee optional for 'done' lane)
3. Update tests with 2.x import paths
4. Commit: `fix: relax assignee gate (cherry-picked from <main-sha>)`

### T079-T080: Adapt Tests for 2.x

- Update import paths where needed
- Run full test suite on 2.x
- Resolve any test failures

### T081-T083: Release v2.0.0a2

```bash
# Version bump
# Edit pyproject.toml: version = "2.0.0a2"

# Update CHANGELOG.md (same fixes, different version header)

# Tag and publish
git tag -a v2.0.0a2 -m "Release v2.0.0a2 - Cherry-pick 7 bug fixes from v0.15.0"
git push origin v2.0.0a2
```

## Definition of Done

- [ ] 7 commits cherry-picked to 2.x
- [ ] Tests passing on 2.x
- [ ] v2.0.0a2 tagged and published

## Activity Log

- 2026-02-11T17:40:17Z – unknown – lane=done – Bug fixes cherry-picked to 2.x (commits only, no release)
