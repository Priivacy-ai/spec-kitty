---
work_package_id: WP09
title: Release v0.15.0 on Main
lane: "done"
dependencies: []
base_branch: main
subtasks: [T064, T065, T066, T067, T068, T069, T070, T071]
phase: Phase 2 - Release
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# Work Package Prompt: WP09 – Release v0.15.0 on Main

## Objectives

- Version bumped from 0.14.2 to 0.15.0
- CHANGELOG.md updated with all 7 bug descriptions
- Full test suite passing (1787+ tests)
- Release branch created, PR merged, tag published
- PyPI publication verified

**Command**: `spec-kitty implement WP09 --base WP08`

## Context

- **Dependencies**: ALL bug fixes WP02-WP08 must be complete
- **Branch**: main (0.14.2 → 0.15.0)
- **Release Type**: Minor version (7 bugfixes)
- **Files**: pyproject.toml, CHANGELOG.md

## Subtasks

### T064: Bump Version in pyproject.toml

Edit `pyproject.toml`:
```toml
[project]
name = "spec-kitty-cli"
version = "0.15.0"  # Was 0.14.2
```

### T065: Update CHANGELOG.md

Add section:
```markdown
## [0.15.0] - 2026-02-11

### 🐛 Fixed

- **#95 - Kebab-case validation**: Feature slugs now validated before creation (fixes #95)
- **#120 - Gitignore isolation**: Worktree ignores use .git/info/exclude (fixes #120)
- **#117 - Dashboard false-failure**: Accurate process detection (fixes #117)
- **#124 - Branch routing**: Unified resolver, no implicit master fallback (fixes #124)
- **#119 - Assignee relaxation**: Optional for done WPs (fixes #119)
- **#122 - Safe commits**: Preserve staging area (fixes #122)
- **#123 - Atomic transitions**: Lane transitions before status updates (fixes #123)

### ✅ Added

- 54+ comprehensive tests for all bug fixes
- Safe commit helper (git/commit_helpers.py)
- Unified branch resolution (git/branch_utils.py)
```

### T066-T067: Run Full Test Suite and Linting

```bash
pytest tests/ -v  # Expect 1787+ pass
ruff check . && ruff format --check .
```

### T068-T071: Create Release

```bash
git checkout -b release/0.15.0
git push origin release/0.15.0
gh pr create --title "Release 0.15.0: Fix 7 critical bugs" --base main
# After CI green and approval:
gh pr merge
git checkout main
git pull
git tag -a v0.15.0 -m "Release v0.15.0"
git push origin v0.15.0
```

## Definition of Done

- [ ] Version is 0.15.0
- [ ] CHANGELOG complete
- [ ] Tests all passing
- [ ] Tagged and published to PyPI

## Activity Log

- 2026-02-11T16:42:21Z – unknown – lane=doing – Moved to doing
- 2026-02-11T17:00:16Z – unknown – lane=for_review – Moved to for_review
- 2026-02-11T17:24:17Z – unknown – lane=done – v0.15.0 released successfully to PyPI and GitHub
