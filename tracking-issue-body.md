# Release 0.15.0: Fix 7 Critical Bugs

This release addresses 7 critical bugs reported by the community with test-first fixes, comprehensive test coverage, and deployment to both main (v0.15.0) and 2.x (v2.0.0a2) branches.

## Bugs Being Fixed

- #95: Kebab-case validation for feature slugs (@MRiabov)
- #120: Worktree gitignore isolation (@umuteonder)
- #117: Dashboard startup false-failure detection (@digitalanalyticsdeveloper)
- #124: Branch routing unification (@fabiodouek)
- #119: Assignee validation relaxation (@fabiodouek)
- #122: Safe commit helper (prevent staged file leaks) (@umuteonder)
- #123: Atomic state transitions in orchestrator (@brkastner)

## Acceptance Checklist

### Bug Fixes
- [ ] #95 fixed + 8 tests passing
- [ ] #120 fixed + 6 tests passing
- [ ] #117 fixed + 10 tests passing
- [ ] #124 fixed + 5 tests passing
- [ ] #119 fixed + 5 tests passing
- [ ] #122 fixed + 8 tests passing
- [ ] #123 fixed + 12 tests passing

### Quality Gates
- [ ] All tests passing (1787+ total)
- [ ] No linting errors
- [ ] Test coverage 95%+ on modified files
- [ ] No regressions in existing functionality

### Release Process
- [ ] Version bumped to 0.15.0 (pyproject.toml)
- [ ] CHANGELOG.md updated with all 7 fixes
- [ ] Release branch created (release/0.15.0)
- [ ] PR created and reviewed
- [ ] PR merged to main
- [ ] Tag v0.15.0 created and pushed
- [ ] PyPI publication verified

### Cherry-Pick to 2.x
- [ ] 6 bugs cherry-picked to 2.x with -x flag
- [ ] Bug #119 manually ported (acceptance_core.py → acceptance.py)
- [ ] Tests adapted for 2.x structure
- [ ] Full test suite passing on 2.x
- [ ] Version bumped to 2.0.0a2
- [ ] Tag v2.0.0a2 created and pushed
- [ ] PyPI publication verified

### Communication
- [ ] All 7 issues closed with thank-you messages
- [ ] General announcement posted
- [ ] Contributors acknowledged in release notes

## Timeline

**Estimated Effort**: 16-20 hours total
**Target Date**: 2026-02-18 (1 week)

## Test-First Discipline

All fixes follow strict TDD:
1. Write failing test (❌ RED)
2. Implement fix
3. Run test (✅ GREEN)
4. Run full suite
5. Commit atomically (fix + tests together)
