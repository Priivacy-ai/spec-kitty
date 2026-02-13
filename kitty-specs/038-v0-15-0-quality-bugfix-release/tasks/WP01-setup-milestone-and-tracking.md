---
work_package_id: WP01
title: Setup Milestone and Tracking
lane: "done"
dependencies: []
base_branch: main
base_commit: 2570020bdd7daa33cc2cf971cb750188db2910d6
created_at: '2026-02-11T15:22:31.095923+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Setup
assignee: ''
agent: codex
shell_pid: "1489"
review_status: has_feedback
reviewed_by: Robert Douglass
history:
- timestamp: '2026-02-11T14:45:00Z'
  lane: planned
  agent: system
  action: Tasks generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Setup Milestone and Tracking

## Objectives & Success Criteria

- GitHub milestone "0.15.0 - 1.x Quality Bugfixes" exists with due date
- Tracking issue created linking all 7 bug reports
- Acceptance checklist added to tracking issue body
- All 7 issues properly labeled for organization

**Implementation command**: `spec-kitty implement WP01`

## Context & Constraints

- **Spec**: All 7 user stories (Bug #95, #120, #117, #124, #119, #122, #123)
- **Plan**: Setup process in plan.md Step 0
- **Repository**: https://github.com/Priivacy-ai/spec-kitty
- **Tool**: Use `gh` CLI for GitHub operations
- **No code changes**: This WP only creates GitHub organizational artifacts

---

## Subtask Breakdown

### Subtask T001: Create GitHub Milestone

**Purpose**: Create milestone to track all 7 bugfixes for v0.15.0 release.

**Steps**:
1. Use gh CLI to create milestone:
   ```bash
   gh api repos/Priivacy-ai/spec-kitty/milestones \
     -f title="0.15.0 - 1.x Quality Bugfixes" \
     -f description="Fix 7 critical bugs for stable 1.x maintenance release. Issues: #95, #120, #117, #124, #119, #122, #123" \
     -f due_on="2026-02-18T00:00:00Z"
   ```

2. Capture milestone number from API response

3. Verify milestone created:
   ```bash
   gh api repos/Priivacy-ai/spec-kitty/milestones | jq '.[] | select(.title == "0.15.0 - 1.x Quality Bugfixes")'
   ```

**Validation**:
- [ ] Milestone exists on GitHub
- [ ] Title matches exactly: "0.15.0 - 1.x Quality Bugfixes"
- [ ] Due date is 2026-02-18
- [ ] Description includes all 7 issue numbers

**Files**: None (GitHub API only)

**Time Estimate**: 5 minutes

---

### Subtask T002: Create Tracking Issue

**Purpose**: Create master tracking issue that links all 7 bug reports and coordinates release.

**Steps**:
1. Create issue body with comprehensive template:
   ```markdown
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
   ```

2. Create issue with gh CLI:
   ```bash
   gh issue create \
     --title "Release 0.15.0: Fix 7 Critical Bugs" \
     --body "$(cat tracking-issue-body.md)" \
     --milestone "0.15.0 - 1.x Quality Bugfixes" \
     --label "release"
   ```

3. Link all 7 issues in the tracking issue (already in body)

**Validation**:
- [ ] Tracking issue created
- [ ] Links to all 7 bug issues present
- [ ] Acceptance checklist complete (all items listed)
- [ ] Assigned to milestone

**Files**:
- Temporary: tracking-issue-body.md (can delete after issue created)

**Time Estimate**: 10 minutes

---

### Subtask T003: Add Acceptance Checklist to Tracking Issue

**Purpose**: Ensure tracking issue has comprehensive checklist for monitoring progress.

**Steps**:
1. Already included in T002 (tracking issue body includes checklist)

2. Verify checklist sections:
   - Bug Fixes (7 items)
   - Quality Gates (4 items)
   - Release Process (8 items)
   - Cherry-Pick to 2.x (7 items)
   - Communication (3 items)

3. No additional work needed - checklist is part of issue body

**Validation**:
- [ ] All checklist items present in tracking issue
- [ ] Checkboxes render correctly on GitHub
- [ ] Items grouped by category

**Files**: None (part of issue body)

**Time Estimate**: 2 minutes (verification only)

---

### Subtask T004: Verify All 7 Issues Properly Labeled

**Purpose**: Ensure consistent labeling for all 7 bug reports.

**Steps**:
1. Check labels on each issue:
   ```bash
   for issue in 95 120 117 124 119 122 123; do
     echo "Issue #$issue:"
     gh issue view $issue --json labels --jq '.labels[].name'
   done
   ```

2. Add missing labels if needed:
   ```bash
   # If bug label missing:
   gh issue edit <number> --add-label "bug"

   # Add priority labels:
   gh issue edit <number> --add-label "P1"  # For critical bugs
   gh issue edit <number> --add-label "P2"  # For medium bugs
   ```

3. Suggested labels for each:
   - All: "bug", "0.15.0"
   - #95, #120, #124, #122, #123: "P1" (critical)
   - #117, #119: "P2" (medium priority)

**Validation**:
- [ ] All 7 issues have "bug" label
- [ ] All 7 issues have "0.15.0" label
- [ ] Priority labels assigned consistently

**Files**: None (GitHub metadata)

**Time Estimate**: 5 minutes

---

## Definition of Done

- [x] GitHub milestone created and visible
- [x] Tracking issue created with all 7 bugs linked
- [x] Acceptance checklist complete in tracking issue body
- [x] All 7 issues properly labeled (bug, 0.15.0, priority)
- [x] Milestone number and tracking issue number captured for reference

---

## Risks & Mitigations

**Risk**: None (low-risk GitHub organizational work)

**Rollback**: Can delete milestone/issue if needed

---

## Reviewer Guidance

**What to verify**:
1. Milestone exists on GitHub with correct title and due date
2. Tracking issue links all 7 bugs
3. Checklist is comprehensive (29 items total)
4. All issues properly labeled

**How to verify**:
```bash
# Check milestone
gh api repos/Priivacy-ai/spec-kitty/milestones | jq '.[] | select(.title | contains("0.15.0"))'

# Check tracking issue
gh issue list --label "release" --milestone "0.15.0 - 1.x Quality Bugfixes"

# Check issue labels
gh issue list --label "0.15.0" | wc -l  # Should show 8 (7 bugs + 1 tracking)
```

**Approval criteria**:
- All GitHub artifacts created correctly
- No API errors
- Checklist is actionable and complete

## Activity Log

- 2026-02-11T14:24:42Z – claude – lane=for_review – Moved to for_review
- 2026-02-11T14:52:52Z – codex – shell_pid=90336 – lane=doing – Started review via workflow command
- 2026-02-11T15:00:42Z – codex – shell_pid=90336 – lane=planned – Moved to planned
- 2026-02-11T15:26:27Z – codex – shell_pid=1489 – lane=for_review – Ready for review: Verified milestone #1 and tracking issue #133 exist with all required artifacts. All 7 bug issues properly labeled and assigned to milestone.
- 2026-02-11T16:21:27Z – codex – shell_pid=1489 – lane=done – Codex approved - all GitHub artifacts verified
