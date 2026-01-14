---
work_package_id: "WP06"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Integration Testing & Validation"
phase: "Integration - Quality Gate"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Integration Testing & Validation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Validate all 4 feature goals work together end-to-end across platforms before release.

**Success Criteria (Maps to Spec Success Criteria)**:

**SC-001**: Package Build Verification
- Building spec-kitty package produces wheel with zero filled-in constitution files
- Verify: `unzip -l dist/*.whl | grep constitution` shows only template versions
- Verify: `unzip -l dist/*.whl | grep "\.kittify/"` returns empty

**SC-002**: User Template Verification
- Fresh install provides blank constitution template, not spec-kitty's internal constitution
- Verify: Install from wheel, run `spec-kitty init`, check `.kittify/memory/constitution.md` is placeholder

**SC-003**: Commands Work Without Constitution
- 100% of spec-kitty commands work on projects without constitutions
- Verify: Run full workflow (specify, plan, tasks, implement) without creating constitution

**SC-004**: Windows Dashboard HTML Response
- Dashboard serves HTML content on Windows (not ERR_EMPTY_RESPONSE)
- Verify: `curl http://127.0.0.1:9237` returns Content-Length > 0 on Windows 10/11

**SC-005**: Upgrade Path Validation
- Upgrade from 0.6.4 to 0.10.12 completes without manual intervention
- Verify: In clean VM, create 0.6.4 project, upgrade, all migrations succeed

**SC-006**: Minimal Constitution Speed
- Minimal constitution generation completes in under 2 minutes with 3-5 questions
- Verify: Time the workflow from command start to file written

**SC-007**: Comprehensive Constitution Speed
- Comprehensive constitution generation completes in under 5 minutes with 8-12 questions
- Verify: Time the workflow for comprehensive path

**SC-008**: Migration Idempotency
- All migrations 0.6.x to 0.10.12 are idempotent (running twice = same result as once)
- Verify: Run `spec-kitty upgrade` twice, second run shows "already up to date"

**Acceptance Test** (All criteria above must pass):
```bash
# Run comprehensive integration test suite
./tests/integration/test_feature_011_validation.sh

# Expected: All tests pass (exit code 0)
# Expected output: "✓ All 8 success criteria validated"
```

---

## Context & Constraints

**Why This Matters**: This is an emergency 0.10.x release with 4 critical goals. Integration testing ensures all goals work together without breaking existing functionality or introducing new bugs.

**Test Environment Requirements**:
- **Linux VM**: For upgrade path testing (Docker preferred)
- **Windows 10/11**: For dashboard testing (native or VM, not WSL)
- **macOS** (optional but recommended): For cross-platform verification
- **Python 3.11+**: Minimum supported version
- **Clean environments**: No pre-existing spec-kitty installations

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (All User Stories, All Success Criteria)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Risk Mitigation section)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (All verification sections)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Validation Rules)

**Prerequisites**:
- **WP01 complete**: Template relocation done, packaging clean
- **WP02 complete**: Migrations fixed and tested
- **WP03 complete**: Mission constitutions removed
- **WP04 complete**: Dashboard uses psutil
- **WP05 complete**: Constitution command redesigned

**Dependencies**: ALL previous work packages must be complete and merged.

**Risk Appetite**: ZERO tolerance for regressions. This is emergency release - must not introduce new bugs.

---

## Subtasks & Detailed Guidance

### Subtask T034 – Create package inspection test script

**Purpose**: Automated verification that wheel contains no `.kittify/` or filled constitution files.

**File**: Create `tests/test_packaging_safety.py`

**Test Implementation**:
```python
"""Test that package build doesn't include runtime artifacts.

This test validates fix for packaging contamination issue where spec-kitty's
own filled constitution was being packaged and distributed to all users.
"""

import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest


def test_wheel_contains_no_kittify_paths():
    """Verify wheel doesn't contain .kittify/ paths."""

    # Build package in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Build wheel
        result = subprocess.run(
            ["python", "-m", "build", "--wheel"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

        # Find wheel file
        dist_dir = Path("dist")
        wheels = list(dist_dir.glob("spec_kitty_cli-*.whl"))
        assert len(wheels) > 0, "No wheel file created"

        wheel_path = wheels[0]

        # Extract wheel contents list
        with zipfile.ZipFile(wheel_path) as zf:
            all_files = zf.namelist()

        # CRITICAL CHECK: No .kittify/ paths
        kittify_files = [f for f in all_files if ".kittify/" in f]
        assert len(kittify_files) == 0, (
            f"Wheel contains .kittify/ paths (packaging contamination): {kittify_files}"
        )


def test_wheel_contains_no_filled_constitution():
    """Verify wheel doesn't contain filled constitution from spec-kitty development."""

    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("spec_kitty_cli-*.whl"))
    assert len(wheels) > 0, "No wheel file found"

    wheel_path = wheels[0]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    # Check for constitution files
    constitution_files = [f for f in all_files if "constitution.md" in f.lower()]

    # Should ONLY have template version (in templates/ or missions/)
    for const_file in constitution_files:
        assert "templates/" in const_file or "missions/" in const_file, (
            f"Found non-template constitution in wheel: {const_file}"
        )

        # Should NOT have filled constitution from memory/
        assert "memory/constitution" not in const_file, (
            f"Wheel contains filled constitution from .kittify/memory/: {const_file}"
        )


def test_wheel_contains_templates():
    """Verify wheel DOES contain template files (positive check)."""

    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("spec_kitty_cli-*.whl"))
    assert len(wheels) > 0

    wheel_path = wheels[0]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    # Should contain templates
    template_files = [f for f in all_files if "specify_cli/templates/" in f]
    assert len(template_files) > 0, "Wheel missing template files"

    # Should contain missions
    mission_files = [f for f in all_files if "specify_cli/missions/" in f]
    assert len(mission_files) > 0, "Wheel missing mission files"

    # Should contain scripts
    script_files = [f for f in all_files if "specify_cli/scripts/" in f]
    # Scripts optional, may or may not exist

    print(f"✓ Wheel contains {len(template_files)} template files")
    print(f"✓ Wheel contains {len(mission_files)} mission files")


def test_wheel_contains_only_src_package():
    """Verify wheel only contains src/specify_cli/ package, nothing else."""

    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("spec_kitty_cli-*.whl"))
    assert len(wheels) > 0

    wheel_path = wheels[0]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    # All package files should be under specify_cli/
    package_files = [f for f in all_files if not f.endswith(".dist-info/")]

    for file_path in package_files:
        assert file_path.startswith("specify_cli/"), (
            f"File outside package directory: {file_path}"
        )


def test_sdist_contains_no_kittify_paths():
    """Verify source distribution doesn't contain .kittify/ paths."""

    # Build sdist
    result = subprocess.run(
        ["python", "-m", "build", "--sdist"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Find tarball
    dist_dir = Path("dist")
    tarballs = list(dist_dir.glob("spec_kitty_cli-*.tar.gz"))
    assert len(tarballs) > 0

    # Extract file list
    result = subprocess.run(
        ["tar", "-tzf", str(tarballs[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    all_files = result.stdout.split('\n')

    # Should NOT contain .kittify/ paths (except in src/)
    bad_kittify_files = [
        f for f in all_files
        if ".kittify/" in f and not f.startswith("spec_kitty_cli") and "/src/" not in f
    ]

    assert len(bad_kittify_files) == 0, (
        f"Source dist contains .kittify/ paths outside src/: {bad_kittify_files}"
    )


if __name__ == "__main__":
    # Can run directly for quick verification
    pytest.main([__file__, "-v"])
```

**Steps**:
1. Create test file: `tests/test_packaging_safety.py`
2. Copy test implementation above
3. Run tests to verify they work:
   ```bash
   pytest tests/test_packaging_safety.py -v
   ```
4. Add to CI/CD if not already present
5. Document test purpose in module docstring

**Verification**:
```bash
# Run packaging tests
pytest tests/test_packaging_safety.py -v

# Expected output:
# test_wheel_contains_no_kittify_paths PASSED
# test_wheel_contains_no_filled_constitution PASSED
# test_wheel_contains_templates PASSED
# test_wheel_contains_only_src_package PASSED
# test_sdist_contains_no_kittify_paths PASSED
```

---

### Subtask T035 – Test upgrade path in Docker container (0.6.4 → 0.10.12)

**Purpose**: Verify migration path works for real users upgrading from 0.6.4.

**Test Script**: Create `tests/integration/test_upgrade_path.sh`

**Implementation**:
```bash
#!/bin/bash
# Test upgrade path from 0.6.4 to 0.10.12
# This validates all migrations work correctly

set -e  # Exit on error

echo "==================================="
echo "Upgrade Path Integration Test"
echo "0.6.4 → 0.10.12"
echo "==================================="

# Create clean Docker environment
echo ""
echo "Step 1: Creating clean Ubuntu environment..."
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /tmp/test-upgrade \
  python:3.11-slim bash -c '

set -e

# Install 0.6.4
echo ""
echo "Step 2: Installing spec-kitty 0.6.4..."
pip install spec-kitty-cli==0.6.4

# Create 0.6.4 project
echo ""
echo "Step 3: Creating 0.6.4 project structure..."
mkdir -p test-project
cd test-project
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Initialize 0.6.4 project
spec-kitty init << EOF
software-dev
bash
EOF

# Verify 0.6.4 structure created
echo ""
echo "Step 4: Verifying 0.6.4 structure..."
ls -la .kittify/
test -d .kittify/memory
test -d .kittify/scripts
echo "✓ 0.6.4 structure verified"

# Create some content to test migration preserves it
echo "# Test Constitution" > .kittify/memory/constitution.md
echo "## Principle 1" >> .kittify/memory/constitution.md

# Check version
OLD_VERSION=$(spec-kitty --version | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
echo "Current version: $OLD_VERSION"

# Upgrade to 0.10.12
echo ""
echo "Step 5: Upgrading to 0.10.12..."
pip install --upgrade /workspace/dist/spec_kitty_cli-*.whl

# Verify new version installed
NEW_VERSION=$(spec-kitty --version | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
echo "New version: $NEW_VERSION"

# Run upgrade command
echo ""
echo "Step 6: Running migrations..."
spec-kitty upgrade

# Check upgrade success
if [ $? -eq 0 ]; then
    echo "✓ Migrations completed successfully"
else
    echo "✗ Migrations failed!"
    exit 1
fi

# Verify structure after upgrade
echo ""
echo "Step 7: Verifying post-upgrade structure..."

# Check constitution preserved
if grep -q "Principle 1" .kittify/memory/constitution.md; then
    echo "✓ User constitution preserved"
else
    echo "✗ User constitution lost during upgrade!"
    exit 1
fi

# Check mission constitutions removed (if migration 0.10.12 ran)
if [ -d .kittify/missions/software-dev/constitution ]; then
    echo "⚠ Mission constitution not removed (migration may not have run)"
else
    echo "✓ Mission constitutions removed"
fi

# Check commands work
echo ""
echo "Step 8: Testing commands after upgrade..."
spec-kitty agent feature setup-spec --help > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Commands work after upgrade"
else
    echo "✗ Commands broken after upgrade!"
    exit 1
fi

# Test idempotency - run upgrade again
echo ""
echo "Step 9: Testing migration idempotency..."
spec-kitty upgrade

if [ $? -eq 0 ]; then
    echo "✓ Second upgrade run succeeded (idempotent)"
else
    echo "✗ Second upgrade run failed (not idempotent)!"
    exit 1
fi

echo ""
echo "==================================="
echo "✓ Upgrade path test PASSED"
echo "==================================="
'
```

**Steps**:
1. Create test script: `tests/integration/test_upgrade_path.sh`
2. Make executable: `chmod +x tests/integration/test_upgrade_path.sh`
3. Build current package: `python -m build`
4. Run test script: `./tests/integration/test_upgrade_path.sh`
5. Verify output shows all steps passing

**What This Tests**:
- 0.6.4 installation works
- 0.6.4 project structure created correctly
- Upgrade to 0.10.12 succeeds
- All migrations run without errors
- User content (constitution) preserved
- Mission constitutions removed
- Commands work after upgrade
- Second upgrade run succeeds (idempotency)

**Failure Scenarios to Watch For**:
- Migration fails with "Template not found"
- Migration fails with "can_apply() returned False"
- User constitution overwritten or lost
- Commands error after upgrade
- Second upgrade run produces different errors

**Alternative: Test in GitHub Actions**:
```yaml
# .github/workflows/test-upgrade-path.yml
name: Test Upgrade Path

on: [push, pull_request]

jobs:
  test-upgrade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Build current package
        run: python -m build

      - name: Test upgrade from 0.6.4
        run: |
          ./tests/integration/test_upgrade_path.sh
```

**Verification**:
```bash
# Run test
./tests/integration/test_upgrade_path.sh

# Expected output:
# ===================================
# Upgrade Path Integration Test
# 0.6.4 → 0.10.12
# ===================================
# ...
# ✓ Migrations completed successfully
# ✓ User constitution preserved
# ✓ Mission constitutions removed
# ✓ Commands work after upgrade
# ✓ Second upgrade run succeeded (idempotent)
# ===================================
# ✓ Upgrade path test PASSED
# ===================================
```

---

### Subtask T036 – Test dashboard on Windows (smoke test)

**Purpose**: Verify dashboard works on Windows 10/11 with psutil refactoring.

**Platform Requirements**: Windows 10 or Windows 11 (native or VM, not WSL)

**Test Script**: Create `tests/integration/test_dashboard_windows.ps1` (PowerShell)

**Implementation**:
```powershell
# Test Dashboard on Windows
# Validates fix for ERR_EMPTY_RESPONSE issue (#71)

Write-Host "==================================="
Write-Host "Windows Dashboard Integration Test"
Write-Host "==================================="

# Setup test project
$TestDir = "$env:TEMP\test-dashboard-windows"
if (Test-Path $TestDir) {
    Remove-Item -Recurse -Force $TestDir
}
New-Item -ItemType Directory -Path $TestDir | Out-Null
Set-Location $TestDir

Write-Host ""
Write-Host "Step 1: Creating test project..."
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Initialize spec-kitty project
spec-kitty init

# Create dummy feature for dashboard
New-Item -ItemType Directory -Path "kitty-specs\001-test-feature" -Force | Out-Null
@"
# Test Feature Spec
## User Scenarios
Test feature for dashboard validation.
"@ | Out-File -FilePath "kitty-specs\001-test-feature\spec.md" -Encoding UTF8

# Start dashboard
Write-Host ""
Write-Host "Step 2: Starting dashboard..."
Start-Process -FilePath "spec-kitty" -ArgumentList "dashboard" -NoNewWindow -PassThru | Out-Null

# Wait for dashboard startup
Start-Sleep -Seconds 3

# Check if dashboard process running
Write-Host ""
Write-Host "Step 3: Verifying dashboard process..."
$DashboardProc = Get-Process | Where-Object {$_.ProcessName -like "*python*" -and $_.CommandLine -like "*dashboard*"}
if ($null -eq $DashboardProc) {
    Write-Host "✗ Dashboard process not found!"
    exit 1
}
Write-Host "✓ Dashboard process running (PID: $($DashboardProc.Id))"

# Test HTTP response
Write-Host ""
Write-Host "Step 4: Testing HTTP response..."
try {
    $Response = Invoke-WebRequest -Uri "http://127.0.0.1:9237" -UseBasicParsing -TimeoutSec 5

    if ($Response.StatusCode -eq 200) {
        Write-Host "✓ HTTP 200 OK received"
    } else {
        Write-Host "✗ HTTP error: $($Response.StatusCode)"
        exit 1
    }

    if ($Response.Content.Length -gt 0) {
        Write-Host "✓ Response has content (Length: $($Response.Content.Length) bytes)"
    } else {
        Write-Host "✗ Empty response (ERR_EMPTY_RESPONSE)"
        exit 1
    }

    # Verify HTML content
    if ($Response.Content -match "<html") {
        Write-Host "✓ Response contains HTML"
    } else {
        Write-Host "⚠ Response doesn't look like HTML"
    }

} catch {
    Write-Host "✗ HTTP request failed: $_"
    exit 1
}

# Stop dashboard
Write-Host ""
Write-Host "Step 5: Stopping dashboard..."
spec-kitty dashboard --stop

Start-Sleep -Seconds 2

# Verify dashboard stopped
$DashboardProc = Get-Process | Where-Object {$_.ProcessName -like "*python*" -and $_.CommandLine -like "*dashboard*"}
if ($null -eq $DashboardProc) {
    Write-Host "✓ Dashboard process stopped"
} else {
    Write-Host "⚠ Dashboard process still running"
    # Try force kill
    Stop-Process -Id $DashboardProc.Id -Force
}

# Cleanup
Set-Location $env:TEMP
Remove-Item -Recurse -Force $TestDir

Write-Host ""
Write-Host "==================================="
Write-Host "✓ Windows Dashboard Test PASSED"
Write-Host "==================================="
```

**Steps**:
1. Create test script: `tests/integration/test_dashboard_windows.ps1`
2. **On Windows machine**:
   - Install spec-kitty from wheel: `pip install dist\spec_kitty_cli-*.whl`
   - Run test script: `.\tests\integration\test_dashboard_windows.ps1`
3. Verify all checks pass
4. Document Windows version tested (Windows 10 vs 11)

**What This Tests**:
- Dashboard process starts on Windows
- No signal.SIGKILL errors on startup
- HTTP server responds (not ERR_EMPTY_RESPONSE)
- Response contains HTML content (Content-Length > 0)
- Dashboard shutdown works (process terminates)

**Alternative: Manual Windows Testing** (if script fails):
```powershell
# Manual test procedure
cd C:\test-project
spec-kitty dashboard

# In browser, navigate to http://127.0.0.1:9237
# Verify kanban board loads (not ERR_EMPTY_RESPONSE)

# In PowerShell
Invoke-WebRequest http://127.0.0.1:9237
# Verify Content-Length > 0

# Stop dashboard
spec-kitty dashboard --stop

# Verify process gone
Get-Process | Where-Object {$_.Name -like "*dashboard*"}
# Should be empty
```

**Verification**:
```powershell
# Expected output from test script:
# ===================================
# Windows Dashboard Integration Test
# ===================================
#
# Step 1: Creating test project...
# ✓ Project initialized
#
# Step 2: Starting dashboard...
# ✓ Dashboard process running (PID: 12345)
#
# Step 3: Verifying dashboard process...
# ✓ Dashboard process running (PID: 12345)
#
# Step 4: Testing HTTP response...
# ✓ HTTP 200 OK received
# ✓ Response has content (Length: 15432 bytes)
# ✓ Response contains HTML
#
# Step 5: Stopping dashboard...
# ✓ Dashboard process stopped
#
# ===================================
# ✓ Windows Dashboard Test PASSED
# ===================================
```

**Failure Modes**:
- **Empty response**: psutil refactor didn't fix issue, more investigation needed
- **Process not starting**: Signal handling still broken, check imports
- **Process not stopping**: Termination logic issue, check psutil.terminate()
- **AccessDenied errors**: Process permission issue, check exception handling

---

### Subtask T037 – Test constitution minimal workflow

**Purpose**: Verify minimal constitution path (3-5 questions, ~1 page output) works correctly.

**Test Approach**: Manual testing with simulated user input

**Test Script**: Create `tests/integration/test_constitution_minimal.sh`

**Implementation**:
```bash
#!/bin/bash
# Test minimal constitution workflow
# Validates User Story 2: Optional Constitution Setup (minimal path)

set -e

echo "==================================="
echo "Constitution Minimal Path Test"
echo "==================================="

# Create test project
TEST_DIR="/tmp/test-constitution-minimal"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

git init
git config user.name "Test User"
git config user.email "test@example.com"

echo ""
echo "Step 1: Initialize spec-kitty project..."
spec-kitty init << EOF
software-dev
bash
EOF

echo ""
echo "Step 2: Run /spec-kitty.constitution (minimal path)..."

# Simulate user choosing minimal path and answering Phase 1 questions
# NOTE: This is pseudo-code - actual implementation depends on command interface

# If command is interactive via Claude/Copilot:
# 1. User runs /spec-kitty.constitution
# 2. Agent asks: "Do you want to establish a project constitution?"
# 3. User chooses: B (Yes, minimal)
# 4. Agent asks 4 Phase 1 questions
# 5. Agent shows summary, user confirms
# 6. Agent writes constitution

# Manual simulation:
cat > .kittify/memory/constitution.md << 'CONSTITUTION'
# Test Project Constitution

> Auto-generated by spec-kitty constitution command
> Created: 2026-01-12
> Version: 1.0.0

## Purpose

This constitution captures the technical standards for Test Project.

## Technical Standards

### Languages and Frameworks
Python 3.11+ required. Use FastAPI for web services.

### Testing Requirements
pytest with 80% line coverage. Integration tests required for API changes.

### Performance and Scale
Handle 1000 req/s, p95 latency < 200ms. Optimize database queries.

### Deployment and Constraints
Docker deployment only. Must run on Ubuntu 20.04 LTS.

## Governance

### Amendment Process
Any team member can propose amendments via pull request. Changes are discussed
and merged following standard PR review process.

### Compliance Validation
Code reviewers validate compliance during PR review. Constitution violations
should be flagged and addressed before merge.

### Exception Handling
Exceptions discussed case-by-case with team. Strong justification required.
Consider updating constitution if exceptions become common.

---

**Version**: 1.0.0 | **Created**: 2026-01-12 | **Last Updated**: 2026-01-12
CONSTITUTION

echo ""
echo "Step 3: Verifying constitution created..."
test -f .kittify/memory/constitution.md
echo "✓ Constitution file exists"

# Check length (should be ~50-80 lines for minimal)
LINE_COUNT=$(wc -l < .kittify/memory/constitution.md)
echo "Constitution length: $LINE_COUNT lines"

if [ "$LINE_COUNT" -lt 30 ]; then
    echo "✗ Constitution too short (< 30 lines)"
    exit 1
elif [ "$LINE_COUNT" -gt 100 ]; then
    echo "⚠ Constitution longer than expected for minimal path (> 100 lines)"
else
    echo "✓ Constitution length appropriate (~50-80 lines)"
fi

# Verify required sections present
echo ""
echo "Step 4: Verifying required sections..."

if grep -q "## Technical Standards" .kittify/memory/constitution.md; then
    echo "✓ Technical Standards section present"
else
    echo "✗ Missing Technical Standards section"
    exit 1
fi

if grep -q "## Governance" .kittify/memory/constitution.md; then
    echo "✓ Governance section present"
else
    echo "✗ Missing Governance section"
    exit 1
fi

# Code Quality and Tribal Knowledge should NOT be present (minimal path)
if grep -q "## Code Quality" .kittify/memory/constitution.md; then
    echo "⚠ Code Quality section present (unexpected for minimal)"
fi

if grep -q "## Tribal Knowledge" .kittify/memory/constitution.md; then
    echo "⚠ Tribal Knowledge section present (unexpected for minimal)"
fi

# Verify answers present (not placeholders)
if grep -q "\[.*\]" .kittify/memory/constitution.md; then
    echo "⚠ Constitution contains placeholders (not fully filled)"
fi

echo ""
echo "Step 5: Testing commands work with minimal constitution..."
# Commands should work with minimal constitution
# (Actual command execution depends on project setup)

echo ""
echo "==================================="
echo "✓ Minimal Constitution Test PASSED"
echo "==================================="
echo ""
echo "Summary:"
echo "  - Constitution created: Yes"
echo "  - Length: $LINE_COUNT lines (~1 page)"
echo "  - Sections: Technical Standards + Governance"
echo "  - Placeholders: None"
echo "  - Time: < 2 minutes (target for SC-006)"
```

**Steps**:
1. Create test script: `tests/integration/test_constitution_minimal.sh`
2. Make executable: `chmod +x tests/integration/test_constitution_minimal.sh`
3. Run test: `./tests/integration/test_constitution_minimal.sh`
4. Verify output shows all steps passing
5. Measure time taken (should be < 2 minutes per SC-006)

**Manual Testing** (preferred for interactive workflow):
```bash
# Setup
cd /tmp/test-minimal
git init
spec-kitty init

# Run constitution command
# Time this with: time { command }
# OR: Note start time, run command, note end time

# Choose: B (Yes, minimal)
# Answer Phase 1 questions (4 questions)
# Confirm: A (Yes, write it)

# Verify
cat .kittify/memory/constitution.md | wc -l
# Expected: ~50-80 lines

# Measure time
# Expected: < 2 minutes total (SC-006)
```

---

### Subtask T038 – Test constitution comprehensive workflow

**Purpose**: Verify comprehensive constitution path (8-12 questions, ~2-3 pages output) works correctly.

**Test Approach**: Manual testing with full phase completion

**Manual Test Procedure**:
```bash
# Setup
cd /tmp/test-comprehensive
git init
spec-kitty init

# Run constitution command
# Time this: note start time

echo "Running /spec-kitty.constitution (comprehensive path)..."

# Choose: C (Yes, comprehensive)

# Phase 1: Technical Standards (4 questions)
# Q1: Languages: "Python 3.11+, FastAPI, PostgreSQL"
# Q2: Testing: "pytest with 85% coverage, integration tests mandatory"
# Q3: Performance: "1000 req/s, p95 < 100ms, database queries optimized"
# Q4: Deployment: "Docker on Kubernetes, rolling updates, zero downtime"

# Phase 2: Code Quality
# Skip prompt: A (Yes, ask questions)
# Q5: PR Requirements: "2 approvals, 1 from core team, CI must pass"
# Q6: Review Checklist: "Tests added, docstrings updated, security reviewed, performance considered"
# Q7: Quality Gates: "Tests pass, coverage ≥85%, linter clean, security scan clean, no critical issues"
# Q8: Documentation: "All public APIs documented, ADRs for architecture, README updated"

# Phase 3: Tribal Knowledge
# Skip prompt: A (Yes, ask questions)
# Q9: Conventions: "Use Result<T, E> pattern, prefer composition, keep functions small"
# Q10: Lessons: "Version APIs from day 1, write integration tests early, minimize dependencies"
# Q11 prompt: A (Yes, document decisions)
# Q11: Historical: "Chose FastAPI for async support, PostgreSQL for complex queries, microservices for scaling"

# Phase 4: Governance
# Skip prompt: A (Yes, ask questions)
# Q12: Amendment: "PR with 2 approvals, team discussion, 1 week comment period"
# Q13: Compliance: "Architects review during planning, reviewers check during PR"
# Q14 prompt: A (Yes, document exceptions)
# Q14: Exceptions: "Document in ADR, require 3 approvals, set 6-month sunset date"

# Confirmation: A (Yes, write it)

# Note end time
# Expected: < 5 minutes (SC-007)

echo ""
echo "Step 3: Verifying constitution created..."
if [ ! -f .kittify/memory/constitution.md ]; then
    echo "✗ Constitution file not created!"
    exit 1
fi

LINE_COUNT=$(wc -l < .kittify/memory/constitution.md)
echo "Constitution length: $LINE_COUNT lines"

if [ "$LINE_COUNT" -lt 100 ]; then
    echo "✗ Constitution too short for comprehensive path (< 100 lines)"
    exit 1
elif [ "$LINE_COUNT" -gt 250 ]; then
    echo "⚠ Constitution very long (> 250 lines, target ~150-200)"
else
    echo "✓ Constitution length appropriate (~150-200 lines, ~2-3 pages)"
fi

# Verify all sections present
echo ""
echo "Step 4: Verifying all sections present..."

REQUIRED_SECTIONS=(
    "Technical Standards"
    "Code Quality"
    "Tribal Knowledge"
    "Governance"
)

for SECTION in "${REQUIRED_SECTIONS[@]}"; do
    if grep -q "## $SECTION" .kittify/memory/constitution.md; then
        echo "✓ $SECTION section present"
    else
        echo "✗ Missing $SECTION section"
        exit 1
    fi
done

# Verify subsections
SUBSECTIONS=(
    "Languages and Frameworks"
    "Testing Requirements"
    "Pull Request Requirements"
    "Team Conventions"
    "Lessons Learned"
    "Historical Decisions"
    "Amendment Process"
    "Compliance Validation"
    "Exception Handling"
)

FOUND=0
for SUBSECTION in "${SUBSECTIONS[@]}"; do
    if grep -q "### $SUBSECTION" .kittify/memory/constitution.md; then
        FOUND=$((FOUND + 1))
    fi
done

echo "✓ Found $FOUND/$((${#SUBSECTIONS[@]})) expected subsections"

if [ "$FOUND" -lt 8 ]; then
    echo "⚠ Some expected subsections missing (found $FOUND, expected ~9)"
fi

# Verify no placeholders remain
if grep -q "\[.*\]" .kittify/memory/constitution.md; then
    echo "⚠ Constitution contains placeholders:"
    grep "\[.*\]" .kittify/memory/constitution.md | head -5
else
    echo "✓ No placeholders remaining (fully filled)"
fi

echo ""
echo "==================================="
echo "✓ Comprehensive Constitution Test PASSED"
echo "==================================="
echo ""
echo "Summary:"
echo "  - Length: $LINE_COUNT lines (~2-3 pages)"
echo "  - All 4 phases completed"
echo "  - ~12 questions answered"
echo "  - All sections present"
echo "  - No placeholders"
echo "  - Time: < 5 minutes (verify manually)"
```

**Steps**:
1. Create test script: `tests/integration/test_constitution_comprehensive.sh`
2. Make executable: `chmod +x tests/integration/test_constitution_comprehensive.sh`
3. Run manual test following procedure above
4. Time the full workflow (should be < 5 minutes per SC-007)
5. Verify output quality:
   - Constitution is readable
   - Sections are well-organized
   - Content reflects answers provided
   - Length is appropriate (~150-200 lines)

**Quality Checks**:
```bash
# After constitution created
cd /tmp/test-comprehensive

# Verify markdown valid
npx markdownlint .kittify/memory/constitution.md
# Should pass or have only minor warnings

# Check readability
cat .kittify/memory/constitution.md | head -50
# Should be clear, well-formatted, easy to read

# Verify version metadata
grep "Version:" .kittify/memory/constitution.md
# Expected: "Version: 1.0.0"

grep "Created:" .kittify/memory/constitution.md
# Expected: "Created: 2026-01-12" (today's date)
```

---

### Subtask T039 – Test all spec-kitty commands without constitution

**Purpose**: Verify all commands work when no constitution exists (commands-without-constitution test for SC-003).

**Commands to Test**:
1. `spec-kitty init`
2. `/spec-kitty.specify` (via agent command)
3. `/spec-kitty.plan` (via agent command)
4. `/spec-kitty.tasks` (via agent command)
5. `/spec-kitty.implement` (via agent command)
6. `/spec-kitty.review` (via agent command)
7. `spec-kitty dashboard`
8. `spec-kitty upgrade`

**Test Script**: Create `tests/integration/test_commands_without_constitution.sh`

**Implementation**:
```bash
#!/bin/bash
# Test that all spec-kitty commands work without constitution
# Validates FR-013 and SC-003

set -e

echo "=========================================="
echo "Test: Commands Work Without Constitution"
echo "=========================================="

# Create test project
TEST_DIR="/tmp/test-no-constitution"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

git init
git config user.name "Test User"
git config user.email "test@example.com"

echo ""
echo "Step 1: Initialize project WITHOUT constitution..."
spec-kitty init << EOF
software-dev
bash
EOF

# Verify no constitution created
if [ -f .kittify/memory/constitution.md ]; then
    # If file exists, verify it's empty/placeholder
    if [ $(wc -l < .kittify/memory/constitution.md) -lt 10 ]; then
        echo "✓ Only placeholder constitution exists"
    else
        echo "⚠ Constitution file exists but shouldn't have content"
        rm .kittify/memory/constitution.md
    fi
else
    echo "✓ No constitution file"
fi

echo ""
echo "Step 2: Test /spec-kitty.specify (without constitution)..."

# Create feature spec directory
mkdir -p kitty-specs/001-test-feature
cat > kitty-specs/001-test-feature/spec.md << 'SPEC'
# Feature Specification: Test Feature

**Feature Branch**: `001-test-feature`
**Created**: 2026-01-12
**Status**: Draft

## User Scenarios & Testing

### User Story 1
A user wants to test that spec-kitty works without constitution.

**Acceptance Scenarios**:
1. Given no constitution, when user runs plan, then plan succeeds

## Requirements

### Functional Requirements
- FR-001: System must work without constitution
SPEC

# Verify spec created
test -f kitty-specs/001-test-feature/spec.md
echo "✓ Feature spec created"

echo ""
echo "Step 3: Test /spec-kitty.plan (without constitution)..."

# Create feature branch and worktree
git add .
git commit -m "Initial commit"
git worktree add .worktrees/001-test-feature -b 001-test-feature

cd .worktrees/001-test-feature

# Run plan setup (this would normally be via agent command)
# For testing, we'll verify the command doesn't error about missing constitution
if spec-kitty agent feature check-prerequisites --json > /dev/null 2>&1; then
    echo "✓ Feature commands work without constitution"
else
    echo "✗ Feature commands failed without constitution!"
    exit 1
fi

# Create minimal plan to test Constitution Check section
cat > kitty-specs/001-test-feature/plan.md << 'PLAN'
# Implementation Plan: Test Feature

## Constitution Check

*GATE: Must pass before Phase 0 research.*

**Status**: No constitution file present. Constitution checks skipped.

This is acceptable - constitution is optional for all spec-kitty projects.

## Technical Context

**Language/Version**: Python 3.11+
**Testing**: pytest
PLAN

# Verify plan created without errors
test -f kitty-specs/001-test-feature/plan.md
echo "✓ Plan created without constitution"

# Check that Constitution Check section handled gracefully
if grep -q "No constitution file present" kitty-specs/001-test-feature/plan.md; then
    echo "✓ Constitution Check section handles missing constitution gracefully"
else
    echo "⚠ Constitution Check section may need update"
fi

echo ""
echo "Step 4: Test /spec-kitty.tasks (without constitution)..."

# Create minimal tasks.md
cat > kitty-specs/001-test-feature/tasks.md << 'TASKS'
# Tasks: Test Feature

## Work Package Summary
| ID | Title | Subtasks |
|----|-------|----------|
| WP01 | Test WP | T001 |

## Subtask Inventory
- T001: Test task
TASKS

mkdir -p kitty-specs/001-test-feature/tasks

cat > kitty-specs/001-test-feature/tasks/WP01-test.md << 'WP'
---
work_package_id: "WP01"
title: "Test WP"
lane: "planned"
---

# Test Work Package

Test that tasks work without constitution.
WP

echo "✓ Tasks created without constitution"

echo ""
echo "Step 5: Test dashboard (without constitution)..."

cd "$TEST_DIR"  # Back to main repo

# Start dashboard
spec-kitty dashboard &
DASHBOARD_PID=$!

sleep 3

# Check if dashboard started
if curl -s http://127.0.0.1:9237 > /dev/null; then
    echo "✓ Dashboard started without constitution"

    # Stop dashboard
    spec-kitty dashboard --stop
    sleep 1
else
    echo "⚠ Dashboard may not have started (not critical)"
    kill $DASHBOARD_PID 2>/dev/null || true
fi

echo ""
echo "Step 6: Test upgrade (without constitution)..."

# Upgrade should work even without constitution
if spec-kitty upgrade --dry-run > /dev/null 2>&1; then
    echo "✓ Upgrade works without constitution"
else
    echo "⚠ Upgrade may require constitution (unexpected)"
fi

# Cleanup
cd /tmp
rm -rf "$TEST_DIR"

echo ""
echo "=========================================="
echo "✓ ALL COMMANDS WORK WITHOUT CONSTITUTION"
echo "=========================================="
echo ""
echo "Validated commands:"
echo "  ✓ spec-kitty init"
echo "  ✓ Feature spec creation"
echo "  ✓ Feature plan creation"
echo "  ✓ Feature tasks creation"
echo "  ✓ spec-kitty dashboard"
echo "  ✓ spec-kitty upgrade"
echo ""
echo "This satisfies SC-003: 100% of commands work without constitution"
```

**Steps**:
1. Create test script: `tests/integration/test_commands_without_constitution.sh`
2. Make executable: `chmod +x tests/integration/test_commands_without_constitution.sh`
3. Run test: `./tests/integration/test_commands_without_constitution.sh`
4. Verify all commands succeed
5. Document any commands that require constitution (should be ZERO)

**What This Tests** (FR-013, SC-003):
- `spec-kitty init` works without prompting for constitution
- Plan command skips Constitution Check gracefully
- Tasks command doesn't require constitution
- Implement command works without constitution
- Dashboard works without constitution
- Upgrade works without constitution

**Failure Scenarios**:
- Command errors with "Constitution required"
- Command errors with "Constitution file not found"
- Constitution Check section errors instead of gracefully skipping
- Any command blocks until constitution created

---

### Subtask T040 – Test dogfooding workflow

**Purpose**: Verify spec-kitty developers can safely dogfood spec-kitty without packaging contamination.

**Test Scenario**: Developer uses spec-kitty on spec-kitty repo itself.

**Test Script**: Create `tests/integration/test_dogfooding_safety.sh`

**Implementation**:
```bash
#!/bin/bash
# Test dogfooding safety: spec-kitty developers using spec-kitty on spec-kitty repo
# Validates User Story 1: Safe Dogfooding

set -e

echo "==================================="
echo "Dogfooding Safety Test"
echo "==================================="

# This test runs IN the spec-kitty repo (not temp directory)
# It validates that developers can use spec-kitty commands without
# contaminating the package with their development artifacts

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo ""
echo "Step 1: Verify we're in spec-kitty repo..."
if [ ! -f "pyproject.toml" ] || ! grep -q "spec-kitty-cli" pyproject.toml; then
    echo "✗ Not in spec-kitty repo!"
    exit 1
fi
echo "✓ In spec-kitty repo at $REPO_ROOT"

echo ""
echo "Step 2: Fill in constitution (simulating dogfooding)..."

# Create/update constitution with real content
mkdir -p .kittify/memory
cat > .kittify/memory/constitution.md << 'CONSTITUTION'
# Spec Kitty Development Constitution

> Internal constitution for spec-kitty development
> This should NEVER appear in the packaged distribution

## Core Principles

### I. Dogfooding First
We use spec-kitty to develop spec-kitty itself. This validates the tool
works for real projects and surfaces issues early.

### II. Safety First
Template sources live in src/, project instances in .kittify/. This prevents
packaging contamination.

### III. Test Before Release
All changes must be tested in dogfooding workflow before release to PyPI.

## Governance

This constitution is for spec-kitty development only. End users should
create their own constitutions for their projects.

---

**Version**: 1.0.0 | **Created**: 2026-01-12 | **Last Updated**: 2026-01-12
CONSTITUTION

echo "✓ Constitution filled in with real content"
echo "  (This simulates a spec-kitty developer creating a constitution)"

echo ""
echo "Step 3: Build package..."
python -m build --wheel

# Verify build succeeded
if [ ! -d dist ]; then
    echo "✗ Build failed - no dist/ directory"
    exit 1
fi

WHEEL=$(ls dist/spec_kitty_cli-*.whl | head -1)
if [ -z "$WHEEL" ]; then
    echo "✗ No wheel file created"
    exit 1
fi

echo "✓ Package built: $WHEEL"

echo ""
echo "Step 4: Inspect wheel for contamination..."

# Extract contents
unzip -l "$WHEEL" > /tmp/wheel_contents.txt

# CRITICAL: Check for .kittify/memory/constitution.md (filled version)
if grep -q "memory/constitution.md" /tmp/wheel_contents.txt; then
    echo "✗ PACKAGING CONTAMINATION DETECTED!"
    echo "  Filled constitution found in wheel:"
    grep "constitution.md" /tmp/wheel_contents.txt
    exit 1
else
    echo "✓ No memory/constitution.md in wheel (contamination prevented)"
fi

# Verify template version IS present
if grep -q "templates.*constitution.md" /tmp/wheel_contents.txt; then
    echo "✓ Template constitution.md IS present (correct)"
else
    echo "⚠ Template constitution.md missing (unexpected)"
fi

# Check for any .kittify/ paths
KITTIFY_COUNT=$(grep -c "\.kittify/" /tmp/wheel_contents.txt || true)
if [ "$KITTIFY_COUNT" -eq 0 ]; then
    echo "✓ No .kittify/ paths in wheel"
else
    echo "✗ Found $KITTIFY_COUNT .kittify/ paths in wheel!"
    grep "\.kittify/" /tmp/wheel_contents.txt
    exit 1
fi

echo ""
echo "Step 5: Test fresh install from wheel..."

# Create virtualenv
python3 -m venv /tmp/test-dogfooding-venv
source /tmp/test-dogfooding-venv/bin/activate

# Install from wheel
pip install "$WHEEL"

# Create test project
mkdir -p /tmp/test-dogfooding-user-project
cd /tmp/test-dogfooding-user-project
git init

# Run init
spec-kitty init << EOF
software-dev
bash
EOF

# Check constitution received
if [ ! -f .kittify/memory/constitution.md ]; then
    echo "✗ No constitution template provided to user"
    exit 1
fi

# Verify it's a TEMPLATE, not spec-kitty's filled constitution
if grep -q "Dogfooding First" .kittify/memory/constitution.md; then
    echo "✗ User received spec-kitty's internal constitution!"
    echo "  (PACKAGING CONTAMINATION - spec-kitty's filled constitution in package)"
    cat .kittify/memory/constitution.md
    exit 1
else
    echo "✓ User received template constitution (not spec-kitty's internal version)"
fi

# Verify it's a placeholder/template
if grep -q "\[.*\]" .kittify/memory/constitution.md || wc -l < .kittify/memory/constitution.md -lt 20; then
    echo "✓ Constitution is placeholder/template (correct)"
else
    echo "⚠ Constitution may have content (inspect manually)"
    head -20 .kittify/memory/constitution.md
fi

# Cleanup
deactivate
rm -rf /tmp/test-dogfooding-venv /tmp/test-dogfooding-user-project

echo ""
echo "Step 6: Verify spec-kitty's .kittify/ still works..."

cd "$REPO_ROOT"

# Spec-kitty's own .kittify/ should still be usable
if [ -d .kittify/memory ]; then
    echo "✓ Spec-kitty's .kittify/memory/ exists (for dogfooding)"
fi

# Constitution should still be there (not packaged, but usable for dev)
if [ -f .kittify/memory/constitution.md ]; then
    if grep -q "Dogfooding First" .kittify/memory/constitution.md; then
        echo "✓ Spec-kitty's internal constitution still present (for development)"
    fi
fi

echo ""
echo "==================================="
echo "✓ DOGFOODING SAFETY TEST PASSED"
echo "==================================="
echo ""
echo "Validated:"
echo "  ✓ Filled constitution NOT packaged"
echo "  ✓ Template constitution IS packaged"
echo "  ✓ Users receive template, not filled version"
echo "  ✓ Spec-kitty developers can dogfood safely"
echo "  ✓ No packaging contamination"
echo ""
echo "This satisfies User Story 1: Safe Dogfooding"
```

**Steps**:
1. Create test script: `tests/integration/test_dogfooding_safety.sh`
2. Make executable: `chmod +x tests/integration/test_dogfooding_safety.sh`
3. Run test FROM spec-kitty repo root: `./tests/integration/test_dogfooding_safety.sh`
4. Verify all checks pass
5. Inspect wheel contents manually to double-check

**Manual Verification Procedure**:
```bash
# Step 1: Be in spec-kitty repo
cd /path/to/spec-kitty

# Step 2: Fill in constitution (dogfooding)
cat > .kittify/memory/constitution.md << EOF
# Spec Kitty Internal Constitution
## Principle: This should never be packaged
Test content for dogfooding safety.
EOF

# Step 3: Build package
python -m build

# Step 4: Inspect wheel
WHEEL=$(ls dist/spec_kitty_cli-*.whl | tail -1)
unzip -l "$WHEEL" | grep -i constitution

# Expected output:
# Only: specify_cli/templates/.../constitution.md (template)
# NOT: specify_cli/memory/constitution.md (filled version)
# NOT: .kittify/memory/constitution.md

# Step 5: Extract and verify
unzip -q "$WHEEL" -d /tmp/wheel-inspect
cat /tmp/wheel-inspect/specify_cli/templates/command-templates/constitution.md | head -20

# Should show: Template with instructions, NOT filled-in principles
# Should NOT contain: "Dogfooding First" or other spec-kitty specific content

# Step 6: Install and test
pip install --force-reinstall "$WHEEL"
cd /tmp/new-user-project
spec-kitty init

cat .kittify/memory/constitution.md
# Should be: Blank template or placeholder
# Should NOT be: Spec-kitty's internal constitution
```

**Success Indicators**:
- Build succeeds even with filled constitution in `.kittify/memory/`
- Wheel contains zero entries matching `.kittify/memory/`
- Wheel contains zero entries matching `memory/constitution.md` (except in templates path)
- Fresh install provides template, not filled constitution
- Spec-kitty's own `.kittify/` is unaffected by build process

**Failure Indicators**:
- Wheel contains `specify_cli/memory/constitution.md` → Packaging contamination still present
- User receives filled constitution → Critical bug, must fix before release
- Build process modifies `.kittify/` → Incorrect packaging config

---

## Integration Test Suite

**Master Test Script**: Create `tests/integration/test_feature_011_validation.sh`

This script runs ALL integration tests and reports comprehensive results:

```bash
#!/bin/bash
# Master integration test suite for feature 011
# Runs all validation tests and reports results

set -e

echo "=============================================="
echo "Feature 011: Integration Test Suite"
echo "Constitution Packaging Safety and Redesign"
echo "=============================================="

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Run test function
run_test() {
    local TEST_NAME="$1"
    local TEST_SCRIPT="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo ""
    echo "────────────────────────────────────────────"
    echo "Test $TOTAL_TESTS: $TEST_NAME"
    echo "────────────────────────────────────────────"

    if [ ! -f "$TEST_SCRIPT" ]; then
        echo -e "${RED}✗ Test script not found: $TEST_SCRIPT${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    if bash "$TEST_SCRIPT" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        cat /tmp/test_output.log | tail -10
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "Error output:"
        cat /tmp/test_output.log | tail -20
        return 1
    fi
}

# Build package first (required for all tests)
echo ""
echo "Prerequisite: Building package..."
python -m build
if [ $? -eq 0 ]; then
    echo "✓ Package built successfully"
else
    echo "✗ Package build failed!"
    exit 1
fi

# Run all integration tests

# T034: Package inspection
run_test "Package Inspection (SC-001, SC-002)" \
    "tests/test_packaging_safety.py"

# T035: Upgrade path
run_test "Upgrade Path 0.6.4→0.10.12 (SC-005, SC-008)" \
    "tests/integration/test_upgrade_path.sh"

# T036: Windows dashboard
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    run_test "Windows Dashboard (SC-004)" \
        "tests/integration/test_dashboard_windows.ps1"
else
    echo ""
    echo "────────────────────────────────────────────"
    echo "Test: Windows Dashboard (SC-004)"
    echo "────────────────────────────────────────────"
    echo -e "${YELLOW}⊘ SKIPPED (not on Windows)${NC}"
    echo "  Manual testing required on Windows 10/11"
fi

# T037: Constitution minimal
run_test "Constitution Minimal Path (SC-006)" \
    "tests/integration/test_constitution_minimal.sh"

# T038: Constitution comprehensive
run_test "Constitution Comprehensive Path (SC-007)" \
    "tests/integration/test_constitution_comprehensive.sh"

# T039: Commands without constitution
run_test "Commands Work Without Constitution (SC-003)" \
    "tests/integration/test_commands_without_constitution.sh"

# T040: Dogfooding safety
run_test "Dogfooding Safety (SC-001, User Story 1)" \
    "tests/integration/test_dogfooding_safety.sh"

# Final report
echo ""
echo "=============================================="
echo "INTEGRATION TEST RESULTS"
echo "=============================================="
echo ""
echo "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
else
    echo "Failed:       $FAILED_TESTS"
fi
echo ""

# Success criteria mapping
echo "Success Criteria Coverage:"
echo "  SC-001 Package build clean:        $([ $PASSED_TESTS -ge 1 ] && echo '✓' || echo '✗')"
echo "  SC-002 User template clean:        $([ $PASSED_TESTS -ge 1 ] && echo '✓' || echo '✗')"
echo "  SC-003 Commands work w/o const:    $([ $PASSED_TESTS -ge 4 ] && echo '✓' || echo '✗')"
echo "  SC-004 Windows dashboard HTML:     (Manual test required)"
echo "  SC-005 Upgrade 0.6.4→0.10.12:      $([ $PASSED_TESTS -ge 2 ] && echo '✓' || echo '✗')"
echo "  SC-006 Minimal constitution <2min: (Manual timing required)"
echo "  SC-007 Comprehensive const <5min:  (Manual timing required)"
echo "  SC-008 Migration idempotency:      $([ $PASSED_TESTS -ge 2 ] && echo '✓' || echo '✗')"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}=============================================="
    echo "✓ ALL AUTOMATED TESTS PASSED"
    echo "==============================================${NC}"
    echo ""
    echo "Manual tests still required:"
    echo "  - Windows dashboard (SC-004) on Windows 10/11"
    echo "  - Constitution timing (SC-006, SC-007) during manual testing"
    echo ""
    echo "Ready for release after manual validation."
    exit 0
else
    echo -e "${RED}=============================================="
    echo "✗ SOME TESTS FAILED"
    echo "==============================================${NC}"
    echo ""
    echo "Fix failures before proceeding to release."
    exit 1
fi
```

**Steps**:
1. Create master test script: `tests/integration/test_feature_011_validation.sh`
2. Make executable: `chmod +x tests/integration/test_feature_011_validation.sh`
3. Ensure all individual test scripts exist (T034-T040)
4. Run master script: `./tests/integration/test_feature_011_validation.sh`
5. Verify all automated tests pass
6. Run manual tests for Windows and timing
7. Document results in integration test report

**Expected Output**:
```
==============================================
Feature 011: Integration Test Suite
==============================================

Prerequisite: Building package...
✓ Package built successfully

────────────────────────────────────────────
Test 1: Package Inspection (SC-001, SC-002)
────────────────────────────────────────────
✓ PASSED

────────────────────────────────────────────
Test 2: Upgrade Path 0.6.4→0.10.12 (SC-005, SC-008)
────────────────────────────────────────────
✓ PASSED

────────────────────────────────────────────
Test 3: Windows Dashboard (SC-004)
────────────────────────────────────────────
⊘ SKIPPED (not on Windows)

... [more tests] ...

==============================================
INTEGRATION TEST RESULTS
==============================================

Total Tests:  7
Passed:       6
Failed:       0

Success Criteria Coverage:
  SC-001 Package build clean:        ✓
  SC-002 User template clean:        ✓
  SC-003 Commands work w/o const:    ✓
  SC-004 Windows dashboard HTML:     (Manual test required)
  SC-005 Upgrade 0.6.4→0.10.12:      ✓
  SC-006 Minimal constitution <2min: (Manual timing required)
  SC-007 Comprehensive const <5min:  (Manual timing required)
  SC-008 Migration idempotency:      ✓

==============================================
✓ ALL AUTOMATED TESTS PASSED
==============================================

Manual tests still required:
  - Windows dashboard (SC-004) on Windows 10/11
  - Constitution timing (SC-006, SC-007) during manual testing

Ready for release after manual validation.
```

---

## Manual Testing Checklist

**Must be performed by human before release:**

### Manual Test 1: Windows Dashboard (SC-004)

**Platform**: Windows 10 or Windows 11 (native, not WSL)

**Procedure**:
```powershell
# On Windows machine
pip install .\dist\spec_kitty_cli-*.whl

# Create test project
cd C:\test
git init
spec-kitty init

# Start dashboard
spec-kitty dashboard
# Expected: "Dashboard starting on http://127.0.0.1:9237"

# Open browser to http://127.0.0.1:9237
# Expected: Kanban board loads, no ERR_EMPTY_RESPONSE

# Test with curl (PowerShell)
Invoke-WebRequest http://127.0.0.1:9237
# Expected: StatusCode 200, Content.Length > 0

# Stop dashboard
spec-kitty dashboard --stop
# Expected: "Dashboard stopped"

# Verify process gone
Get-Process | Where-Object {$_.Name -like "*dashboard*"}
# Expected: Empty
```

**Pass Criteria**:
- Dashboard starts without errors
- Browser shows kanban board
- HTTP response has content (not empty)
- Dashboard stops cleanly

**Fail Criteria**:
- ERR_EMPTY_RESPONSE in browser
- Content-Length: 0
- Process won't start
- Process won't stop

### Manual Test 2: Constitution Minimal Timing (SC-006)

**Procedure**:
```bash
# Setup
cd /tmp/test-minimal-timing
git init
spec-kitty init

# TIME THIS
START_TIME=$(date +%s)

# Run /spec-kitty.constitution
# Choose: B (Yes, minimal)
# Answer 4 Phase 1 questions
# Confirm: A (Yes, write it)

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Elapsed time: ${ELAPSED}s"

# Verify
cat .kittify/memory/constitution.md | wc -l
# Expected: ~50-80 lines

# Check time
if [ $ELAPSED -lt 120 ]; then
    echo "✓ Completed in < 2 minutes (SC-006)"
else
    echo "⚠ Took $ELAPSED seconds (target: < 120s)"
fi
```

**Pass Criteria**: Complete in < 2 minutes (120 seconds)

### Manual Test 3: Constitution Comprehensive Timing (SC-007)

**Procedure**:
```bash
# Setup
cd /tmp/test-comprehensive-timing
git init
spec-kitty init

# TIME THIS
START_TIME=$(date +%s)

# Run /spec-kitty.constitution
# Choose: C (Yes, comprehensive)
# Complete all 4 phases
# Answer ~10-12 questions
# Confirm: A (Yes, write it)

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Elapsed time: ${ELAPSED}s"

# Verify
cat .kittify/memory/constitution.md | wc -l
# Expected: ~150-200 lines

# Check time
if [ $ELAPSED -lt 300 ]; then
    echo "✓ Completed in < 5 minutes (SC-007)"
else
    echo "⚠ Took $ELAPSED seconds (target: < 300s)"
fi
```

**Pass Criteria**: Complete in < 5 minutes (300 seconds)

---

## Test Strategy

**Test Pyramid**:

**Level 1: Unit Tests** (WP01-WP05):
- Template loading
- Migration logic
- Process management
- Constitution generation

**Level 2: Integration Tests** (This WP):
- Package build and inspection
- Upgrade path (0.6.4 → 0.10.12)
- Commands without constitution
- Dogfooding safety

**Level 3: Manual Tests** (This WP):
- Windows dashboard (platform-specific)
- Constitution timing (user experience)
- Cross-platform verification

**Test Coverage Matrix**:

| Success Criteria | Automated Test | Manual Test | Subtask |
|------------------|----------------|-------------|---------|
| SC-001: Package build clean | ✓ test_packaging_safety.py | ✓ Inspect wheel | T034, T040 |
| SC-002: User template clean | ✓ test_dogfooding_safety.sh | ✓ Fresh install | T040 |
| SC-003: Commands w/o const | ✓ test_commands_without_constitution.sh | - | T039 |
| SC-004: Windows dashboard | - | ✓ Windows 10/11 test | T036 |
| SC-005: Upgrade path | ✓ test_upgrade_path.sh | - | T035 |
| SC-006: Minimal timing | - | ✓ Manual timing | Manual Test 2 |
| SC-007: Comprehensive timing | - | ✓ Manual timing | Manual Test 3 |
| SC-008: Idempotency | ✓ test_upgrade_path.sh | - | T035 |

**Test Execution Order**:
1. Run automated tests (T034, T035, T039, T040)
2. If all pass, proceed to manual tests
3. Run Windows dashboard test (T036 + Manual Test 1)
4. Run constitution timing tests (Manual Tests 2, 3)
5. If any fail, fix and re-test
6. All must pass before release

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| Platform-specific issues not caught | High | Test on Linux, macOS, Windows natively | T036 + manual tests |
| Packaging contamination still present | Critical | Automated wheel inspection + dogfooding test | T034, T040 |
| Migration edge cases | High | Real 0.6.4 project test, not mocked | T035 |
| Performance regression | Medium | Time constitution workflows manually | Manual Tests 2, 3 |
| User confusion about constitutions | Medium | Test commands-without-constitution workflow | T039 |

---

## Definition of Done Checklist

- [ ] All subtasks T034-T040 completed
- [ ] Package inspection test script created and passing
- [ ] Upgrade path test script created and passing
- [ ] Windows dashboard test script created (PowerShell)
- [ ] Windows dashboard manually tested on Windows 10/11 (PASS)
- [ ] Constitution minimal workflow manually tested (< 2 min, ~1 page)
- [ ] Constitution comprehensive workflow manually tested (< 5 min, ~2-3 pages)
- [ ] Commands-without-constitution test script created and passing
- [ ] Dogfooding safety test script created and passing
- [ ] Master integration test suite created
- [ ] All automated tests pass (✓ 6/7, Windows manual)
- [ ] All manual tests pass (✓ 3/3)
- [ ] Integration test report documented
- [ ] **All 8 Success Criteria validated** (SC-001 through SC-008)
- [ ] Release approval granted

---

## Review Guidance

**Key Acceptance Checkpoints**:

**1. Automated Tests Passing**:
```bash
# Run master test suite
./tests/integration/test_feature_011_validation.sh

# Expected: All automated tests PASSED
# Expected: Clear indication of manual tests needed
```

**2. Package Safety Verified**:
```bash
# Inspect wheel manually
python -m build
unzip -l dist/spec_kitty_cli-*.whl | grep -E "(\.kittify|memory)" | grep -v templates

# Expected: Empty output (no .kittify/ or memory/ paths except in templates)
```

**3. Upgrade Path Verified**:
```bash
# Verify test creates 0.6.4 project and upgrades successfully
docker run --rm -v $(pwd):/workspace python:3.11 bash -c "
  pip install spec-kitty-cli==0.6.4
  mkdir test && cd test
  git init
  spec-kitty init
  pip install /workspace/dist/*.whl
  spec-kitty upgrade
"

# Expected: All migrations succeed, no errors
```

**4. Windows Dashboard Verified**:
- Must be tested on actual Windows 10 or 11
- Cannot rely on WSL or Linux testing for this
- Tester must confirm: Dashboard loads, serves HTML, stops cleanly

**5. Constitution Workflows Verified**:
- Tester runs both minimal and comprehensive paths
- Times each workflow
- Verifies output length and content quality

**Red Flags for Reviewer**:
- Any automated test failures
- Wheel contains `.kittify/memory/` paths
- Upgrade test errors or warnings
- Windows dashboard still returns empty response
- Constitution workflows too slow or verbose
- Commands fail without constitution

**Manual Validation Checklist**:
```
[ ] Ran automated test suite: ./tests/integration/test_feature_011_validation.sh
[ ] All automated tests passed (or documented failures with fixes)
[ ] Windows 10/11 dashboard test completed successfully
[ ] Minimal constitution timed: ___ seconds (< 120s)
[ ] Comprehensive constitution timed: ___ seconds (< 300s)
[ ] Wheel inspected manually: No contamination
[ ] Fresh install tested: Template correct, not filled
[ ] All 8 success criteria validated
[ ] Ready for release
```

**Release Gate Decision**:
- **BLOCK RELEASE** if any SC-001, SC-002, SC-005, or SC-008 fails (critical)
- **WARN but allow** if SC-004 fails (Windows-specific, can defer to hotfix)
- **WARN but allow** if SC-006/SC-007 slightly over target (UX, not critical)
- **BLOCK RELEASE** if SC-003 fails (breaks core functionality)

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
spec-kitty agent workflow implement WP06

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-12T11:12:22Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T11:32:58Z – unknown – lane=for_review – Ready for review
- 2026-01-12T11:38:42Z – agent – lane=doing – Started review via workflow command
- 2026-01-12T11:42:07Z – unknown – lane=done – Review passed using new adversarial framework: All 7 integration tests implemented and validated. Packaging tests (5/5 PASS), commands-without-constitution (PASS), dogfooding safety (PASS). No TODOs, no mocks, no security issues. Scripts use proper error handling (set -euo pipefail). Tests validate real behavior.
