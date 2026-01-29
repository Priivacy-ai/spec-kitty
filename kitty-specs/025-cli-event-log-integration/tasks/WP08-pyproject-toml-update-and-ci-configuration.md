---
work_package_id: WP08
title: pyproject.toml Update & CI Configuration
lane: planned
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
subtasks:
- T041
- T042
- T043
- T044
- T045
phase: Phase 2 - Advanced Features & Edge Cases
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – pyproject.toml Update & CI Configuration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you start.
- **Report progress**: Update Activity Log as you address feedback items.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate if work needs changes.]*

---

## Objectives & Success Criteria

**Primary Goal**: Finalize Git dependency configuration, validate CI/CD pipeline, and document the dependency update process.

**Success Criteria**:
- ✅ spec-kitty-events pinned to specific stable commit hash in pyproject.toml
- ✅ GitHub Actions workflow includes SSH setup steps (uses deploy key)
- ✅ CI build succeeds end-to-end (installs spec-kitty-events, runs tests)
- ✅ Dependency update process documented in CONTRIBUTING.md
- ✅ `spec-kitty --version` output includes spec-kitty-events version
- ✅ All WP01-WP07 implementation merged and functional

**Priority**: P1 (completes US6)

**User Story**: US6 - Git Dependency Integration (completion)

**Independent Test**:
```bash
# Trigger GitHub Actions workflow
git push origin 2.x

# Monitor build
gh run list --workflow=ci.yml --branch=2.x --limit=1
gh run watch <run_id>

# Verify:
# 1. SSH setup step succeeds
# 2. pip install succeeds (spec-kitty-events installed)
# 3. All tests pass
# 4. Build completes successfully
```

---

## Context & Constraints

### ⚠️ CRITICAL: Target Branch

**This work package MUST be implemented on the `2.x` branch (NOT main).**

**IMPORTANT**: This is the final integration WP. Verify ALL prior WPs (WP01-WP07) are merged to 2.x before starting.

```bash
# Verify you're on 2.x
git branch --show-current  # Must output: 2.x

# Verify all prior WPs merged
git log --oneline --graph -20  # Should see WP01-WP07 merge commits
```

### Prerequisites

- **WP01-WP07 complete**: All implementation merged into 2.x branch
- **Constitution**: SSH deploy key requirements (lines 86-102)
- **ADR-11**: Dual-Repository Pattern documentation
- **Spec**: US6 acceptance scenarios (lines 120-124)

### Architectural Constraints

**From constitution (Private Dependency Pattern)**:
- MUST use commit hash pinning (not `rev="main"`)
- MUST document update process for contributors
- MUST validate CI builds before merging

**From spec.md (FR-001 to FR-004)**:
- Git dependency with SSH URL
- Deploy key configured in GitHub Actions
- Graceful error if library unavailable
- Documentation for setup

### Key Technical Decisions

1. **Commit Pinning** (ADR-11): Pin to stable commit, update explicitly
2. **CI Validation** (T043): Must verify end-to-end before merging
3. **Version Display** (T045): Show library version for transparency

---

## Subtasks & Detailed Guidance

### Subtask T041 – Pin spec-kitty-events to specific commit hash in pyproject.toml

**Purpose**: Update the dependency declaration to pin to a stable, tested commit of spec-kitty-events.

**Steps**:

1. **Identify stable commit in spec-kitty-events**:
   ```bash
   # Clone spec-kitty-events to check latest stable commit
   cd /tmp
   git clone git@github.com:Priivacy-ai/spec-kitty-events.git
   cd spec-kitty-events

   # Find latest commit on main branch
   git log main -1 --format="%H"
   # Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0

   # Verify tests pass on this commit
   pytest tests/
   # Only pin if tests pass!
   ```

2. **Update pyproject.toml with commit hash**:
   ```toml
   # In pyproject.toml (modify)

   [tool.poetry.dependencies]
   python = "^3.11"
   typer = "^0.9.0"
   rich = "^13.0.0"
   # ... other existing dependencies

   # spec-kitty-events with commit pinning
   spec-kitty-events = { git = "ssh://git@github.com/Priivacy-ai/spec-kitty-events.git", rev = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0" }
   ```

   **Critical**:
   - Use full 40-character commit hash (not short hash)
   - Use `ssh://` protocol (not `https://`)
   - Replace the example hash with actual stable commit

3. **Regenerate poetry.lock**:
   ```bash
   cd /path/to/spec-kitty
   poetry lock --no-update
   poetry install

   # Verify installation
   python -c "import spec_kitty_events; print('✓ Library installed')"
   ```

4. **Test locally**:
   ```bash
   # Fresh virtual environment test
   poetry env remove python3.11  # Remove existing venv
   poetry install                # Reinstall from scratch

   # Verify event store works
   python << 'EOF'
   from specify_cli.events.store import EventStore
   from pathlib import Path
   store = EventStore(Path("/tmp/test-final"))
   event = store.emit("Test", "test-id", "Test", "test-actor", {"data": "test"})
   print(f"✓ Event emitted: {event.event_id}")
   EOF
   ```

**Files**:
- `pyproject.toml` (modify: update spec-kitty-events dependency)
- `poetry.lock` (regenerate via `poetry lock`)

**Validation**:
- [ ] pyproject.toml has SSH Git URL with full commit hash
- [ ] `poetry lock --no-update` succeeds
- [ ] `poetry install` installs spec-kitty-events successfully
- [ ] EventStore can be imported and used
- [ ] Commit hash points to tested, stable commit

**Edge Cases**:
- Commit hash doesn't exist: poetry install fails with clear error
- Network failure during install: poetry retries automatically
- SSH key not configured: Fails with permission denied (expected locally)

**Parallel?**: No - Final integration step (needs all prior WPs complete)

---

### Subtask T042 – Update GitHub Actions workflow with SSH setup steps

**Purpose**: Ensure CI/CD pipeline can access private spec-kitty-events repository.

**Steps**:

1. **Locate CI workflow file**:
   ```bash
   ls .github/workflows/
   # Common names: ci.yml, test.yml, python-package.yml
   ```

2. **Add SSH setup before install**:
   ```yaml
   # In .github/workflows/ci.yml (or equivalent)

   name: CI

   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: '3.11'

         # NEW: SSH setup for private dependency
         - name: Setup SSH for spec-kitty-events access
           run: |
             # Create SSH directory
             mkdir -p ~/.ssh
             chmod 700 ~/.ssh

             # Write deploy key from secrets
             echo "${{ secrets.SPEC_KITTY_EVENTS_DEPLOY_KEY }}" > ~/.ssh/id_ed25519
             chmod 600 ~/.ssh/id_ed25519

             # Add GitHub to known hosts
             ssh-keyscan github.com >> ~/.ssh/known_hosts

             # Verify SSH key works (optional but helpful)
             ssh -T git@github.com || true  # Returns non-zero, but that's OK
           shell: bash

         - name: Install Poetry
           run: |
             curl -sSL https://install.python-poetry.org | python3 -
             echo "$HOME/.local/bin" >> $GITHUB_PATH

         - name: Install dependencies
           run: |
             poetry install --no-interaction --no-ansi

         - name: Run tests
           run: |
             poetry run pytest tests/ -v

         - name: Type checking
           run: |
             poetry run mypy src/ --strict
   ```

3. **Add workflow comment documentation**:
   ```yaml
   - name: Setup SSH for spec-kitty-events access
     # Purpose: spec-kitty depends on private spec-kitty-events library.
     # Uses SSH deploy key stored in GitHub Actions secret: SPEC_KITTY_EVENTS_DEPLOY_KEY
     # See docs/development/ssh-deploy-keys.md for setup instructions.
     run: |
       # ... SSH setup commands
   ```

**Files**:
- `.github/workflows/ci.yml` (or equivalent - modify)

**Validation**:
- [ ] SSH setup step runs BEFORE `poetry install`
- [ ] Uses `SPEC_KITTY_EVENTS_DEPLOY_KEY` secret
- [ ] SSH key written to `~/.ssh/id_ed25519` with permissions 600
- [ ] GitHub host key added to known_hosts
- [ ] Workflow comment explains purpose

**Edge Cases**:
- Secret not configured: Workflow fails with permission denied (T043 will catch)
- Multiple workflows: Update all workflows that run `poetry install`
- Matrix strategy (multiple Python versions): SSH setup in each matrix job

**Parallel?**: No - Sequential after T041 (needs pyproject.toml finalized)

---

### Subtask T043 – Test CI build end-to-end (trigger workflow, verify library installs)

**Purpose**: Validate the full CI/CD pipeline before merging to 2.x branch.

**Steps**:

1. **Commit changes and push**:
   ```bash
   # Ensure all WP01-WP07 changes are committed
   git add .
   git commit -m "Complete Feature 025: CLI Event Log Integration

   - Integrated spec-kitty-events library (Git dependency)
   - Implemented event emission (EventStore, AOP middleware)
   - Implemented event reading (EventReader, state reconstruction)
   - Implemented SQLite query index (performance optimization)
   - Implemented conflict detection (LWW merge rule)
   - Implemented error logging (Manus pattern)

   Closes Feature 025"

   # Push to trigger CI
   git push origin 2.x
   ```

2. **Monitor GitHub Actions run**:
   ```bash
   # Get latest workflow run
   gh run list --workflow=ci.yml --branch=2.x --limit=1

   # Watch it live
   gh run watch <run_id>

   # Or view in browser
   gh run view <run_id> --web
   ```

3. **Verify each step succeeds**:
   - ✅ Checkout code
   - ✅ Setup Python
   - ✅ **Setup SSH** (new step from T042)
   - ✅ Install Poetry
   - ✅ **Install dependencies** (should install spec-kitty-events)
   - ✅ Run tests
   - ✅ Type checking

4. **If workflow fails, diagnose and fix**:
   ```bash
   # View logs
   gh run view <run_id> --log

   # Common issues:
   # - SSH key secret not configured → Add to repository secrets
   # - Commit hash doesn't exist → Update hash in pyproject.toml
   # - Tests fail → Fix tests before merging
   ```

**Files**:
- (No new files - verification step)

**Validation**:
- [ ] GitHub Actions workflow triggered by push to 2.x
- [ ] All steps succeed (green checkmarks)
- [ ] "Install dependencies" step shows spec-kitty-events installed
- [ ] Tests pass (pytest and mypy)

**Edge Cases**:
- Workflow doesn't trigger: Check workflow file syntax (YAML validation)
- SSH step fails: Verify secret name matches (SPEC_KITTY_EVENTS_DEPLOY_KEY)
- Tests fail: Fix implementation before proceeding

**Parallel?**: No - Sequential after T042 (needs workflow updated)

---

### Subtask T044 – Document dependency update process in CONTRIBUTING.md

**Purpose**: Provide clear instructions for contributors to update the spec-kitty-events dependency.

**Steps**:

1. **Add dependency update section to CONTRIBUTING.md**:
   ```markdown
   # In CONTRIBUTING.md (add new section)

   ## Updating spec-kitty-events Dependency

   Spec-kitty depends on the private [spec-kitty-events](https://github.com/Priivacy-ai/spec-kitty-events) library via Git dependency with commit pinning.

   ### When to Update

   Update the dependency when:
   - New features added to spec-kitty-events that spec-kitty needs
   - Bug fixes or performance improvements in spec-kitty-events
   - Security patches in spec-kitty-events

   ### Update Process

   1. **Make changes in spec-kitty-events repository:**
      ```bash
      cd /path/to/spec-kitty-events
      # ... make changes, run tests, commit
      git push origin main
      ```

   2. **Get commit hash:**
      ```bash
      git log -1 --format="%H"
      # Example: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
      ```

   3. **Update spec-kitty pyproject.toml:**
      ```bash
      cd /path/to/spec-kitty
      git checkout 2.x

      # Edit pyproject.toml
      # Update rev = "OLD_HASH" to rev = "NEW_HASH"
      ```

   4. **Regenerate lock file:**
      ```bash
      poetry lock --no-update
      poetry install
      ```

   5. **Test integration:**
      ```bash
      # Run spec-kitty tests
      poetry run pytest tests/

      # Verify event store works
      python -c "from specify_cli.events.store import EventStore; print('OK')"
      ```

   6. **Commit and push:**
      ```bash
      git add pyproject.toml poetry.lock
      git commit -m "Update spec-kitty-events to <short_hash>

      Changes: <brief description of what changed in library>
      "
      git push origin 2.x
      ```

   7. **Verify CI:**
      ```bash
      gh run list --workflow=ci.yml --limit=1
      gh run watch <run_id>
      ```

   ### Troubleshooting

   **Error: "Could not find a version that matches..."**
   - Verify commit hash exists in spec-kitty-events repository
   - Check for typos in commit hash (40 characters exactly)

   **Error: "Permission denied (publickey)"**
   - Verify SSH key configured locally: `ssh -T git@github.com`
   - For CI, verify SPEC_KITTY_EVENTS_DEPLOY_KEY secret configured

   **Tests fail after update:**
   - Check spec-kitty-events CHANGELOG for breaking changes
   - Update adapter layer (src/specify_cli/events/adapter.py) if API changed
   - Run `poetry install` to ensure lock file matches pyproject.toml

   ### Local Development with Unreleased Changes

   For rapid iteration (use sparingly):

   ```bash
   # Temporary: Install local editable version
   pip install -e /path/to/spec-kitty-events

   # ... test changes ...

   # IMPORTANT: Revert to Git dependency before committing!
   pip uninstall spec-kitty-events
   poetry install
   ```

   **Never commit with local path dependency!**
   ```

**Files**:
- `CONTRIBUTING.md` (modify: add dependency update section, ~80 lines)

**Validation**:
- [ ] Documentation includes step-by-step update process
- [ ] Covers: get commit hash → update pyproject.toml → regenerate lock → test → commit
- [ ] Troubleshooting section addresses common errors
- [ ] Warning about local path dependencies (never commit)

**Edge Cases**:
- Contributor forgets to run `poetry lock`: Tests fail in CI (lock file out of sync)
- Commit hash typo: poetry install fails with clear error
- Local path dependency committed: Pre-commit hook should catch (if configured)

**Parallel?**: Yes - Can implement in parallel with T041-T043 (documentation work)

---

### Subtask T045 – Add spec-kitty-events version to `spec-kitty --version` output

**Purpose**: Display library version for debugging and transparency.

**Steps**:

1. **Locate version command**:
   ```bash
   find src -name "*.py" | xargs grep -l "__version__"
   # Likely in: src/specify_cli/__init__.py or src/specify_cli/cli/app.py
   ```

2. **Add library version to version output**:
   ```python
   # In src/specify_cli/cli/app.py (or wherever --version is handled)

   import typer

   def version_callback(value: bool):
       """Display version information."""
       if value:
           from specify_cli import __version__
           print(f"spec-kitty version: {__version__}")

           # Add spec-kitty-events version (NEW)
           try:
               import spec_kitty_events
               events_version = getattr(spec_kitty_events, "__version__", "unknown")
               print(f"spec-kitty-events: {events_version}")
           except ImportError:
               print("spec-kitty-events: not installed")

           raise typer.Exit()

   # In main app
   @app.callback()
   def main(
       version: bool = typer.Option(
           None,
           "--version",
           callback=version_callback,
           is_eager=True,
           help="Show version information"
       ),
   ):
       pass
   ```

3. **Test version output**:
   ```bash
   spec-kitty --version
   # Expected output:
   # spec-kitty version: 2.0.0
   # spec-kitty-events: 1.0.0
   ```

**Files**:
- `src/specify_cli/cli/app.py` (modify: add library version to --version output)

**Validation**:
- [ ] `spec-kitty --version` shows spec-kitty-events version
- [ ] Handles library not installed (shows "not installed" instead of crashing)
- [ ] Version extracted from `spec_kitty_events.__version__`

**Edge Cases**:
- Library doesn't have __version__: Shows "unknown"
- Library not installed: Shows "not installed"
- Import fails: Exception caught, shows "not installed"

**Parallel?**: Yes - Can implement in parallel with other subtasks (independent)

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T041**: Install test - `poetry install` succeeds with pinned commit
2. **T042**: Workflow test - Verify SSH setup step in CI workflow file
3. **T043**: CI test - GitHub Actions build succeeds end-to-end
4. **T044**: Documentation review - Clear, complete instructions
5. **T045**: Version test - `spec-kitty --version` shows library version

**Full CI validation test**:
```bash
# 1. Ensure all WPs merged to 2.x
git checkout 2.x
git log --oneline -10  # Verify WP01-WP07 commits present

# 2. Push to trigger CI
git push origin 2.x

# 3. Monitor build
gh run list --workflow=ci.yml --branch=2.x --limit=1
run_id=$(gh run list --workflow=ci.yml --branch=2.x --limit=1 --json databaseId -q '.[0].databaseId')

echo "Watching CI run: $run_id"
gh run watch $run_id

# 4. Verify success
gh run view $run_id
# All steps should have ✓ green checkmarks

# 5. Check logs for SSH setup
gh run view $run_id --log | grep -A 10 "Setup SSH"
# Should show:
# - SSH key written to ~/.ssh/id_ed25519
# - Permissions set to 600
# - GitHub host key added

# 6. Check logs for dependency install
gh run view $run_id --log | grep -A 5 "Install dependencies"
# Should show:
# - Installing spec-kitty-events from git
# - Installation successful

echo "✓ CI validation complete"
```

---

## Risks & Mitigations

### Risk 1: SSH deploy key secret not configured

**Impact**: CI build fails with "Permission denied (publickey)"

**Mitigation**:
- T042 references docs/development/ssh-deploy-keys.md in workflow comments
- T043 validation test catches this before merge
- T044 documents troubleshooting steps

### Risk 2: Commit hash becomes stale (library updated but spec-kitty not)

**Impact**: Spec-kitty misses bug fixes or new features from library

**Mitigation**:
- T044 documents update process (explicit, intentional)
- Commit pinning prevents silent breakage
- Contributors can update when needed (controlled, not automatic)

### Risk 3: CI build passes but local development fails

**Impact**: Developers can't install library locally (SSH key issues)

**Mitigation**:
- T044 documents local SSH setup
- WP01 T002 documentation provides SSH key generation instructions
- `spec-kitty --version` (T045) shows if library installed correctly

---

## Definition of Done Checklist

- [ ] T041: pyproject.toml has spec-kitty-events with commit hash pinning
- [ ] T041: poetry.lock regenerated successfully
- [ ] T041: `poetry install` succeeds and imports library
- [ ] T042: GitHub Actions workflow includes SSH setup step
- [ ] T042: SSH setup runs BEFORE `poetry install`
- [ ] T042: Workflow comments document purpose and reference docs
- [ ] T043: GitHub Actions workflow triggered and monitored
- [ ] T043: All workflow steps succeed (green checkmarks)
- [ ] T043: spec-kitty-events installed successfully in CI
- [ ] T043: Tests pass in CI environment
- [ ] T044: CONTRIBUTING.md has dependency update section
- [ ] T044: Troubleshooting section covers common errors
- [ ] T045: `spec-kitty --version` shows spec-kitty-events version
- [ ] Full CI validation passes (end-to-end)

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T041 - Commit Pinning**:
   - ✓ Full 40-character commit hash (not short hash or branch name)
   - ✓ SSH URL format (ssh://git@github.com/...)
   - ✓ poetry.lock regenerated and committed

2. **T042 - CI Workflow**:
   - ✓ SSH setup before install
   - ✓ Correct secret name (SPEC_KITTY_EVENTS_DEPLOY_KEY)
   - ✓ File permissions (600 for private key)
   - ✓ Host key added (prevents interactive prompt)

3. **T043 - CI Validation**:
   - ✓ Workflow runs successfully
   - ✓ Library installed in CI
   - ✓ Tests pass

4. **T044 - Documentation**:
   - ✓ Clear step-by-step instructions
   - ✓ Troubleshooting guide
   - ✓ Warning about local path dependencies

5. **T045 - Version Display**:
   - ✓ Shows library version
   - ✓ Handles library not installed gracefully

**Reviewers should**:
- Trigger CI build manually (verify T043)
- Read T044 documentation (verify clarity)
- Run `spec-kitty --version` (verify T045)
- Check GitHub Actions logs (verify SSH setup and install steps)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

## Implementation Command

This WP depends on ALL prior WPs (WP01-WP07). This is the final integration WP.

**IMPORTANT**: Before implementing, ensure all WP01-WP07 are merged to 2.x branch.

```bash
# Merge all prior WPs first
spec-kitty merge --feature 025-cli-event-log-integration

# Then implement WP08 from merged 2.x branch
git checkout 2.x
git pull origin 2.x
spec-kitty implement WP08
```

This will create workspace: `.worktrees/025-cli-event-log-integration-WP08/` branched from 2.x (with all WP01-WP07 merged).
