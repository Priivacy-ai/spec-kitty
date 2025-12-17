---
work_package_id: "WP07"
subtasks: ["T115", "T116", "T117", "T118", "T119", "T120", "T121", "T122", "T123", "T124", "T125", "T126", "T127", "T128", "T129", "T130", "T131", "T132", "T133", "T134", "T135", "T136"]
title: "Testing & Validation"
phase: "Phase 7 - Validation (Sequential)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Testing & Validation

## Objectives & Success Criteria

**Goal**: Validate all workflows work end-to-end, cross-platform compatibility verified, performance targets met.

**Success Criteria**:
- All spec-kitty workflows complete without errors
- Upgrade migration works on test projects
- CI passes on Windows, macOS, Linux
- Performance targets met (<100ms simple, <5s complex)
- 90%+ test coverage achieved for agent namespace
- Zero path-related errors in agent execution logs

**Why This Matters**: This is the final validation gate before merge. Any issues discovered here must be fixed before production release.

---

## Context & Constraints

**Prerequisites**: **WP06 complete** ✅ (all implementation finished, bash deleted, migration created)

**This is SEQUENTIAL work** - final phase before merge.

**Testing Scope**:
- Full workflow testing (specify → merge)
- Cross-platform validation (3 OS)
- Performance benchmarking
- Coverage analysis
- Edge case discovery

---

## Subtasks & Detailed Guidance

### T115-T121 – Test full feature workflows

Test each spec-kitty workflow end-to-end:

**T115**: `/spec-kitty.specify` workflow
```bash
# Create new feature
spec-kitty agent create-feature "validation-test" --json

# Verify feature directory created
ls kitty-specs/009-validation-test/

# Verify spec.md exists
cat kitty-specs/009-validation-test/spec.md
```

**T116**: `/spec-kitty.plan` workflow
- Setup plan template
- Update agent context
- Verify plan.md created with tech stack

**T117**: `/spec-kitty.tasks` workflow
- Generate work packages
- Verify tasks.md created
- Verify task prompts generated in tasks/ directory

**T118**: `/spec-kitty.implement` workflow
- Move task through lanes: planned → doing → for_review → done
- Verify history tracking
- Verify frontmatter updates

**T119**: `/spec-kitty.review` workflow
- Validate task completion
- Mark as done
- Verify workflow constraints

**T120**: `/spec-kitty.accept` workflow
- Acceptance validation
- Feature readiness check

**T121**: `/spec-kitty.merge` workflow
- Merge feature branch
- Clean up worktree
- Verify cleanup

**Manual Test Script**:
```bash
#!/bin/bash
# Full workflow validation script

set -e  # Exit on error

echo "Testing full spec-kitty workflow..."

# Phase 1: Specify
echo "1. Creating feature..."
spec-kitty agent create-feature "validation-test" --json

# Phase 2: Plan
echo "2. Setting up plan..."
cd .worktrees/009-validation-test
spec-kitty agent setup-plan --json

# Phase 3: Tasks
echo "3. Generating tasks..."
# (simulate /spec-kitty.tasks)

# Phase 4: Implement
echo "4. Moving task..."
spec-kitty agent move-task WP01 --to doing --json

# Phase 5: Review
echo "5. Validating workflow..."
spec-kitty agent validate-workflow WP01 --json

# Phase 6: Accept
echo "6. Acceptance check..."
# (simulate acceptance)

# Phase 7: Merge
echo "7. Merging feature..."
# (simulate merge)

echo "✓ Full workflow validation passed!"
```

---

### T122-T123 – Test release workflow

**T122**: Test release in dry-run mode:
```bash
spec-kitty agent build-release --dry-run --json
```

Verify:
- Version detection works
- Version alignment validated
- Release notes generated
- No actual publish (dry-run respected)

**T123**: Test release in GitHub Actions CI:
- Create test workflow that runs `spec-kitty agent build-release --dry-run`
- Verify CI environment variables work
- Verify `gh` CLI integration works

---

### T124-T126 – Test upgrade migration

**T124**: Create test project with old bash structure:
```bash
# Setup test project
mkdir test-project
cd test-project
git init
mkdir -p .kittify/scripts/bash
cp old-bash-scripts/* .kittify/scripts/bash/
cp old-templates/* .claude/commands/
```

**T125**: Run `spec-kitty upgrade` on test project:
```bash
cd test-project
spec-kitty upgrade

# Verify migration succeeded
ls .kittify/scripts/bash  # Should not exist
cat .claude/commands/spec-kitty.implement.md  # Should reference agent commands
```

**T126**: Test all workflows in upgraded project:
- Run full workflow test script (from T115-T121)
- Verify no regressions
- Verify agents can use upgraded project

---

### T127-T129 – Cross-platform validation

**T127**: Run CI tests on macOS (primary development platform)
```bash
pytest tests/ -v --cov=src/specify_cli/cli/commands/agent --cov-report=term
```

**T128**: Run CI tests on Linux (production platform)
```bash
# In GitHub Actions or Docker
pytest tests/ -v --cov --cov-report=term
```

**T129**: Run CI tests on Windows (verify file copy fallback)
```bash
# In GitHub Actions Windows runner
pytest tests/ -v --cov --cov-report=term

# Verify symlink fallback works
python -c "from specify_cli.core.worktree import setup_feature_directory; import platform; assert platform.system() == 'Windows'"
```

**GitHub Actions Matrix**:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.11", "3.12"]
```

---

### T130-T132 – Performance validation

**T130**: Measure simple command performance (target <100ms):
```python
import time

def test_simple_command_performance():
    start = time.time()
    subprocess.run(["spec-kitty", "agent", "check-prerequisites", "--json"], check=True)
    duration = time.time() - start
    
    assert duration < 0.1, f"Simple command took {duration}s, target <100ms"
```

**T131**: Measure complex command performance (target <5s):
```python
def test_complex_command_performance():
    start = time.time()
    subprocess.run(["spec-kitty", "agent", "create-feature", "perf-test", "--json"], check=True)
    duration = time.time() - start
    
    assert duration < 5.0, f"Complex command took {duration}s, target <5s"
```

**T132**: Verify no measurable overhead vs bash baseline:
- Benchmark old bash script execution time
- Benchmark new Python command execution time
- Compare: Python should be ≤ 2x bash time (acceptable overhead)

---

### T133-T136 – Coverage and edge cases

**T133**: Calculate test coverage for agent namespace:
```bash
pytest tests/ \
  --cov=src/specify_cli/cli/commands/agent \
  --cov=src/specify_cli/core/worktree \
  --cov=src/specify_cli/core/agent_context \
  --cov=src/specify_cli/core/release \
  --cov-report=term-missing \
  --cov-report=html
```

**T134**: Verify 90%+ coverage achieved (FR-026, FR-027):
- Review coverage report
- Identify gaps
- If below 90%, add targeted tests

**T135**: Verify zero path-related errors:
- Review agent execution logs (if available)
- Test from various starting directories
- Test with broken symlinks
- Test with missing .kittify marker

**T136**: Document edge cases discovered:
- Create `EDGE_CASES.md` with findings
- Document workarounds if needed
- File issues for future improvements

**Example Edge Cases**:
- Deeply nested worktree directories (>10 levels)
- .kittify directory is symlink
- Repository root is symlink
- Windows long path names (>260 chars)
- Non-ASCII characters in feature names

---

## Test Strategy

**Workflow Tests** (T115-T121):
- Manual execution of full workflows
- Automated script for CI validation
- Verify from both main repo and worktree

**Release Tests** (T122-T123):
- Dry-run mode validation
- CI environment testing
- GitHub API integration

**Migration Tests** (T124-T126):
- Test project with bash scripts
- Upgrade migration execution
- Post-upgrade workflow validation

**Cross-Platform Tests** (T127-T129):
- CI matrix: 3 OS × 2 Python versions
- Platform-specific fallbacks (Windows)

**Performance Tests** (T130-T132):
- Simple command benchmarks
- Complex command benchmarks
- Baseline comparison

**Coverage Tests** (T133-T136):
- Coverage report generation
- 90%+ validation
- Edge case discovery

---

## Acceptance Criteria Checklist

- [ ] All workflows tested end-to-end (T115-T121) ✅
- [ ] Release workflow validated (T122-T123) ✅
- [ ] Upgrade migration tested (T124-T126) ✅
- [ ] Cross-platform tests passing (T127-T129) ✅
- [ ] Performance targets met (T130-T132) ✅
- [ ] Coverage ≥90% achieved (T133-T134) ✅
- [ ] Path errors eliminated (T135) ✅
- [ ] Edge cases documented (T136) ✅

---

## Risks & Mitigations

**Risk**: Edge cases discovered late require significant rework
**Mitigation**: Comprehensive testing in WP02-WP05 reduces risk; prioritize critical path scenarios

**Risk**: Cross-platform issues on Windows
**Mitigation**: Early testing in Phase 1, existing fallback patterns validated in research

**Risk**: Performance regressions vs bash
**Mitigation**: Accept 2x overhead as reasonable for maintainability gains

---

## Definition of Done Checklist

- [ ] All workflows passing (T115-T121)
- [ ] Release workflow validated (T122-T123)
- [ ] Upgrade tested (T124-T126)
- [ ] CI passing on all platforms (T127-T129)
- [ ] Performance validated (T130-T132)
- [ ] Coverage ≥90% (T133-T134)
- [ ] Zero path errors (T135)
- [ ] Edge cases documented (T136)
- [ ] Ready for merge to main

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
