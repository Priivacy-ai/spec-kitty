---
work_package_id: WP07
title: Native Windows CI workflow
dependencies:
- WP03
requirement_refs:
- FR-015
- FR-016
- NFR-002
- NFR-006
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: .github/workflows/
execution_mode: code_change
owned_files:
- .github/workflows/ci-windows.yml
- .github/workflows/ci-quality.yml
tags: []
---

# WP07 — Native Windows CI workflow

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
- Implement command: `spec-kitty agent action implement WP07 --agent <name>`. Begin after WP03 is merged to main (so the `windows_ci` pytest marker is registered).

## Objective

Add a blocking GitHub Actions workflow at `.github/workflows/ci-windows.yml` that runs on `windows-latest`, installs `spec-kitty-cli` via `pipx`, forces UTF-8 I/O with `PYTHONUTF8=1`, and runs `pytest -m windows_ci --maxfail=1`. Assert that `keyring` is NOT installed in the Windows CI venv (packaging enforcement of C-001). Update the existing Linux CI workflow to exclude `windows_ci`-marked tests so they do not accidentally run on Linux runners. Document branch-protection update so a maintainer can mark the job as a required check post-merge.

## Context

- **Spec IDs covered**: FR-015 (blocking Windows PR job), FR-016 (curated suite coverage), NFR-002 (p95 ≤ 15 min), NFR-006 (10 consecutive green runs), C-004 (blocking, not nightly).
- **Discovery decision**: Q2=B (curated Windows-critical suite, not full matrix).
- **Research**: [`research.md` R-06, R-07](../research.md)
- **Contract**: [`contracts/windows-ci-job.md`](../contracts/windows-ci-job.md)

## Detailed subtasks

### T040 — Create `.github/workflows/ci-windows.yml`

**Purpose**: The native Windows CI job.

**Steps**:
1. Create `.github/workflows/ci-windows.yml`:
   ```yaml
   name: ci-windows
   on:
     pull_request:
       branches: [main]
     push:
       branches: [main]

   jobs:
     windows-critical:
       name: Windows critical (pipx, pytest -m windows_ci)
       runs-on: windows-latest
       timeout-minutes: 20
       env:
         PYTHONUTF8: "1"
         SPEC_KITTY_ENABLE_SAAS_SYNC: "0"
       steps:
         - uses: actions/checkout@v4

         - name: Setup Python
           uses: actions/setup-python@v5
           with:
             python-version: "3.11"

         - name: Install pipx
           shell: bash
           run: |
             python -m pip install --upgrade pip pipx
             python -m pipx ensurepath

         - name: Install spec-kitty-cli (editable)
           shell: bash
           run: |
             pipx install --editable . --force

         - name: Install test dependencies into the pipx venv
           shell: bash
           run: |
             pipx inject spec-kitty-cli pytest pytest-cov

         - name: Assert keyring is NOT installed on Windows
           shell: bash
           run: |
             pipx runpip spec-kitty-cli list | grep -iE '^keyring[[:space:]]' && exit 1 || echo "keyring absent (expected)"

         - name: Run Windows-critical suite
           shell: bash
           run: |
             pipx runpip spec-kitty-cli install pytest pytest-cov
             cd "$(pwd)"
             python -m pytest -m windows_ci --maxfail=1 -v
   ```
2. Notes on the shell choice: `shell: bash` is explicit and available on `windows-latest` via the GitHub-provided Git-Bash. Multi-line commands are easier to reason about in bash than PowerShell.
3. The `pipx inject` step installs test deps into the pipx venv so the editable install's Python environment is self-consistent. Alternative: `python -m pip install pytest pytest-cov` in the outer Python — either is acceptable; pick the one that causes the test runner to find the pipx-installed `specify_cli` without PYTHONPATH fiddling.

**Validation**:
- T045 smoke test: workflow runs end-to-end on a scratch push.

### T041 — "keyring NOT installed" assertion step [P]

**Purpose**: Packaging-level enforcement of C-001 from the CI side.

**Steps**:
1. The assertion step in T040's YAML already covers this: `grep -iE '^keyring[[:space:]]'` on the output of `pipx runpip spec-kitty-cli list` — if `keyring` is installed, `grep` returns zero and the step exits non-zero.
2. Alternative implementation (more robust):
   ```yaml
   - name: Assert keyring is NOT installed on Windows
     shell: bash
     run: |
       if pipx runpip spec-kitty-cli show keyring >/dev/null 2>&1; then
         echo "::error::keyring IS installed on Windows; WP03 conditional marker is not effective."
         exit 1
       fi
       echo "keyring absent (expected)"
   ```
3. Use the alternative if `pipx runpip ... list` proves flaky on `windows-latest`.

**Validation**:
- Step turns red if a future PR accidentally reintroduces a keyring dep.

### T042 — Update Linux `ci-quality.yml` to exclude `windows_ci` [P]

**Purpose**: Windows-only tests must not run on Linux runners (where they'd fail or be meaningless).

**Steps**:
1. Open `.github/workflows/ci-quality.yml`.
2. Find the step that invokes `pytest`. It likely looks like:
   ```yaml
   - name: Run tests
     run: pytest
   ```
3. Change to:
   ```yaml
   - name: Run tests (non-Windows-CI)
     run: pytest -m "not windows_ci"
   ```
4. If there are multiple pytest invocations (unit / integration / coverage), apply the same marker filter to each.
5. Do NOT remove or rename any existing required check. Only add the marker filter.

**Validation**:
- Linux CI continues to run all existing tests MINUS the `windows_ci`-marked ones.

### T043 — `timeout-minutes` and `--maxfail=1` [P]

**Purpose**: Guard against runaway jobs (NFR-002) and surface failures immediately.

**Steps**:
1. Confirm `timeout-minutes: 20` is set on the `windows-critical` job (already in T040's YAML).
2. Confirm `--maxfail=1` is set on the `pytest` invocation (already in T040's YAML).
3. Document that the p95 target is 15 min; 20 min is the hard cap.

**Validation**:
- Look at the first five runs on `main`; record wall-clock time in the PR description for SC-003 evidence.

### T044 — Document branch-protection required-check update [P]

**Purpose**: For the CI job to be blocking, a maintainer must mark it "required" in GitHub branch protection. That is an out-of-band action.

**Steps**:
1. In the PR description for WP07 (the work package's PR body), include a "Post-merge action" section:
   ```markdown
   ## Post-merge action required

   After this PR merges, a maintainer with admin rights on Priivacy-ai/spec-kitty must:

   1. Go to Settings → Branches → Branch protection rules for `main`.
   2. Add **"ci-windows / windows-critical"** to the "Require status checks to pass before merging" list.
   3. Save.

   Without this update, C-004 ("blocking Windows CI on PRs") is not enforced.
   ```
2. Add the same note to the mission's final audit report (WP09's deliverable).

**Validation**:
- Reviewer confirms the note is present in the PR description.

### T045 — Smoke-test workflow

**Purpose**: Prove the workflow actually runs and completes on `windows-latest`.

**Steps**:
1. After T040–T043 land on the lane branch, push the branch to GitHub to trigger the workflow.
2. Observe the workflow run on the Actions tab.
3. Expected outcome on a partial landing (WP03 merged, WP07 running, other code lanes not yet merged):
   - The workflow runs.
   - The curated suite executes (even if only T018 — the no-keyring test — is present, the job will pass with a small number of collected tests).
   - Wall-clock time ≤ 20 min.
4. Capture the run URL and commit SHA in the PR description.
5. If the workflow fails because of a pipx/path issue, troubleshoot by adjusting the YAML in T040 until green. Do not mark T045 done until a successful native run exists.

**Validation**:
- A real workflow run URL is captured.

## Definition of done

- [ ] All 6 subtasks complete.
- [ ] `.github/workflows/ci-windows.yml` present and valid YAML.
- [ ] `.github/workflows/ci-quality.yml` excludes `windows_ci` without regressing any existing check.
- [ ] Smoke-run URL captured in the WP PR description.
- [ ] Branch-protection note included in the WP PR description.
- [ ] Commit message references FR-015, FR-016, NFR-002, C-004.

## Risks

- **`pipx install --editable`** may require `venv` and `virtualenv`. `actions/setup-python@v5` provides both.
- **PowerShell vs bash on `windows-latest`**: default shell is PowerShell. Multi-line commands must be `shell: bash` or PowerShell-syntax-correct. The YAML in T040 uses `shell: bash` explicitly.
- **Test collection finding zero tests**: If `windows_ci` marker registration (WP03) didn't land yet, `pytest -m windows_ci` will warn about an unknown marker AND collect zero tests. WP07 depends on WP03 — do not merge WP07 before WP03.
- **Branch-protection update requires admin**: The maintainer must actually perform step 1–3 of T044. If they don't, CI "runs" but isn't blocking.

## Reviewer guidance

Focus on:
1. Is the workflow triggered on both `pull_request` and `push` to `main`?
2. Is `timeout-minutes: 20` set? (NFR-002 hard cap.)
3. Does the keyring-absent assertion use `exit 1` on presence, not just print?
4. Did the `ci-quality.yml` edit preserve every existing step and add ONLY the `-m "not windows_ci"` marker filter?
5. Is there a real workflow run URL in the PR description?

Do NOT ask about:
- Test internals — covered by the WPs that add them.
- Marker registration — that's WP03.
