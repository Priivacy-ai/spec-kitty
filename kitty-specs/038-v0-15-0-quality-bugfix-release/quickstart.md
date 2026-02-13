# Quickstart: v0.15.0 Bugfix Release Testing

**Feature**: 038-v0-15-0-quality-bugfix-release
**Created**: 2026-02-11
**Purpose**: Quick reference for manually testing each bug fix

## Prerequisites

```bash
# Install the release
pip install --upgrade spec-kitty-cli

# Verify version
spec-kitty --version  # Should show 0.15.0 (or 2.0.0a2 for 2.x)

# Create test repository
mkdir /tmp/spec-kitty-test-v015
cd /tmp/spec-kitty-test-v015
git init
spec-kitty init .
```

---

## Bug #95: Kebab-Case Validation

**What was fixed**: Feature slug must be kebab-case (lowercase, hyphens only)

**Test (should FAIL)**:
```bash
spec-kitty agent create-feature "Invalid Feature Name"
# Expected: Error message about kebab-case requirement

spec-kitty agent create-feature "user_authentication"
# Expected: Error (underscores not allowed)
```

**Test (should PASS)**:
```bash
spec-kitty agent create-feature "user-authentication"
# Expected: Feature 001-user-authentication created successfully
```

**Verification**: ✅ Invalid slugs rejected with clear error, valid slugs accepted

---

## Bug #120: Worktree Gitignore Isolation

**What was fixed**: Worktree ignore patterns use `.git/info/exclude` (not versioned .gitignore)

**Test**:
```bash
# Create feature and implement WP
spec-kitty agent create-feature "test-gitignore"
spec-kitty specify  # Create spec
spec-kitty plan     # Create plan
spec-kitty tasks    # Create tasks
spec-kitty implement WP01

# Check worktree's exclusion (should be in .git/info/exclude, not .gitignore)
ls .worktrees/001-test-gitignore-WP01/.git/info/exclude
# Expected: File exists with exclusion patterns

# Check planning repo's .gitignore
git status
# Expected: No .gitignore changes staged

# Merge WP back
spec-kitty review WP01  # Approve
spec-kitty merge WP01

# Check git log for .gitignore pollution
git log -1 --name-only
# Expected: NO .gitignore file in changed files list
```

**Verification**: ✅ No .gitignore changes in merge commits

---

## Bug #117: Dashboard False-Failure Detection

**What was fixed**: Dashboard accurately detects running state (no false failures)

**Test (dashboard running, health check slow)**:
```bash
# Start dashboard
spec-kitty dashboard --port 8080 &
sleep 2  # Let it start

# Run dashboard command again (should detect running)
spec-kitty dashboard --port 8080
# Expected: "Dashboard already running on port 8080" (not "Unable to start")
```

**Test (missing .kittify)**:
```bash
# Test in repo without .kittify
cd /tmp/uninitialized-repo
git init
spec-kitty dashboard
# Expected: Specific error "Dashboard metadata not found. Run 'spec-kitty init .'"
```

**Verification**: ✅ Accurate state detection, specific error messages

---

## Bug #124: Branch Routing Respects Current Branch

**What was fixed**: CLI doesn't auto-checkout master (respects current branch)

**Test**:
```bash
# Create feature on non-main branch
git checkout -b feature/my-work
spec-kitty agent create-feature "test-branch-respect"
spec-kitty specify
spec-kitty plan
spec-kitty tasks

# Implement WP01 (should stay on feature/my-work)
spec-kitty implement WP01
git rev-parse --abbrev-ref HEAD
# Expected: feature/my-work (not main)

# Check worktree base
cd .worktrees/001-test-branch-respect-WP01
git log --oneline -1
git rev-parse --abbrev-ref HEAD
# Expected: Worktree based on feature/my-work
```

**Verification**: ✅ Current branch preserved, no auto-checkout to master

---

## Bug #119: Assignee Not Required for Done WPs

**What was fixed**: Acceptance doesn't require assignee for completed WPs

**Test**:
```bash
# Create feature, complete WP without assignee
spec-kitty agent create-feature "test-assignee"
spec-kitty specify
spec-kitty plan
spec-kitty tasks

# Complete WP01 (assume implemented and reviewed)
# Manually edit WP01 frontmatter: remove `assignee:` field
# Move to done lane
spec-kitty agent tasks move-task WP01 --to done

# Run acceptance
spec-kitty accept
# Expected: ✅ Success (no "missing assignee" error for done WP)
```

**Verification**: ✅ Acceptance succeeds for done WPs without assignee

---

## Bug #122: Status Commits Don't Capture Staged Files

**What was fixed**: CLI commit helpers only commit intended files

**Test**:
```bash
# Create feature
spec-kitty agent create-feature "test-staging"
spec-kitty specify
spec-kitty plan
spec-kitty tasks

# Stage unrelated file
echo "debug notes" > debug.txt
git add debug.txt

# Move task (triggers status commit)
spec-kitty agent tasks move-task WP01 --to doing

# Check if debug.txt was committed
git log -1 --name-only
# Expected: Only WP01 status file, NOT debug.txt

# Verify debug.txt still staged
git status
# Expected: debug.txt still in "Changes to be committed"
```

**Verification**: ✅ Status commits exclude unrelated staged files

---

## Bug #123: State Transitions Are Atomic

**What was fixed**: Lane transition commits BEFORE status changes

**Test**:
```bash
# This is primarily verified by unit tests
# Manual verification: Run orchestrator and check logs

spec-kitty agent create-feature "test-state-machine"
spec-kitty specify
spec-kitty plan
spec-kitty tasks

# Run orchestrator (if available on main)
spec-kitty orchestrate --feature 001-test-state-machine

# Check logs for transition order
grep "transition_wp_lane" orchestrator.log
grep "wp.status" orchestrator.log
# Expected: transition_wp_lane calls appear BEFORE corresponding status changes
```

**Verification**: ✅ No "No transition defined" warnings in logs

---

## Full Smoke Test (All Bugs)

**Complete Workflow Test**:
```bash
# 1. Create feature with valid kebab-case (Bug #95)
spec-kitty agent create-feature "full-smoke-test"  # ✅ Valid slug

# 2. Stay on current branch (Bug #124)
git checkout -b test-branch
spec-kitty specify  # Should stay on test-branch

# 3. Create worktree (Bug #120)
spec-kitty plan
spec-kitty tasks
spec-kitty implement WP01
# Verify: No .gitignore changes staged

# 4. Make status commit with staged file (Bug #122)
echo "unrelated" > unrelated.txt
git add unrelated.txt
spec-kitty agent tasks move-task WP01 --to doing
# Verify: unrelated.txt still staged, not committed

# 5. Complete WP without assignee (Bug #119)
# (Edit WP01 frontmatter, remove assignee)
spec-kitty agent tasks move-task WP01 --to done
spec-kitty accept
# Verify: Acceptance succeeds

# 6. Start dashboard (Bug #117)
spec-kitty dashboard
# Verify: Accurate status reporting

# 7. Orchestrator state transitions (Bug #123)
# (Verified by unit tests - manual check if orchestrator available)
```

**Expected Result**: All commands succeed, all bugs are fixed, workflow completes cleanly

---

## CI Verification

**Run Full Test Suite**:
```bash
cd /Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty
pytest tests/ -v --tb=short
# Expected: 1787+ tests pass, 0 failures
```

**Run Linting**:
```bash
ruff check .
ruff format --check .
# Expected: No errors
```

**Run Migration Tests**:
```bash
pytest tests/specify_cli/upgrade/test_migration_robustness.py -v
# Expected: All pass, migration registry complete
```

---

## Rollback (If Needed)

**Revert Individual Fix**:
```bash
# If Bug #95 fix causes issues
git revert <bug-95-commit-sha>
git push origin main

# Release hotfix
# Edit pyproject.toml: version = "0.15.1"
git tag v0.15.1
git push origin v0.15.1
```

**Full Rollback** (Nuclear Option):
```bash
# Advise users to downgrade
pip install spec-kitty-cli==0.14.2

# Yank from PyPI (avoid if possible)
# Fix issues and re-release as 0.15.1
```

---

## Verification Checklist

**Pre-Release**:
- [ ] All 7 bugs have failing tests
- [ ] All 7 bugs have fixes implemented
- [ ] All 54+ tests pass (green)
- [ ] Full CI green on main
- [ ] Version bumped to 0.15.0
- [ ] CHANGELOG.md updated
- [ ] Manual smoke test passes

**Post-Release**:
- [ ] v0.15.0 published to PyPI
- [ ] GitHub release created
- [ ] Fresh install verified: `pip install spec-kitty-cli` shows 0.15.0
- [ ] Each bug manually tested (7 tests above)
- [ ] No regressions in first 48 hours

**Cherry-Pick to 2.x**:
- [ ] 6 bugs cherry-picked with -x
- [ ] Bug #119 manually ported
- [ ] Tests adapted for 2.x
- [ ] Full CI green on 2.x
- [ ] v2.0.0a2 published to PyPI

**Communication**:
- [ ] 7 GitHub issues closed with thank-you
- [ ] General announcement posted
- [ ] Contributors acknowledged by name
