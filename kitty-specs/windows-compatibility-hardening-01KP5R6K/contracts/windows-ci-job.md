# Contract: Windows CI Job

**Spec IDs**: FR-015, FR-016, FR-017, NFR-002, NFR-006, C-004, C-007
**Files**: `.github/workflows/ci-windows.yml` (new), `pyproject.toml` (marker registration)

## Workflow shape

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
      SPEC_KITTY_ENABLE_SAAS_SYNC: "0"   # CI does not hit SaaS unless explicitly testing sync
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install pipx
        run: |
          python -m pip install --upgrade pip pipx
          python -m pipx ensurepath
      - name: Install spec-kitty-cli (editable)
        run: pipx install --editable . --force
      - name: Install test dependencies
        run: python -m pip install pytest pytest-cov
      - name: Confirm keyring is NOT installed on Windows
        run: |
          python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('keyring') is None else 1)"
      - name: Run Windows-critical suite
        run: pytest -m windows_ci --maxfail=1 -v
```

## Required checks

- Branch protection on `main`: `ci-windows / windows-critical` is a required status check (C-004 enforcement; happens as part of merge of this mission).

## Marker registration

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "windows_ci: tests that must pass on the native windows-latest CI job",
]
# Default Linux job ignores windows_ci:
# pytest -m "not windows_ci" (set in the existing workflow)
```

Existing `ci-quality.yml` (Linux) is updated to run `pytest -m "not windows_ci"` so Windows-only tests do not fail on Linux.

## Guarantees

- G-01: Job runs on every PR and every push to `main`.
- G-02: Job completes within 20 min (NFR-002 buffer).
- G-03: Job fails fast on first failing test (`--maxfail=1`).
- G-04: `keyring` is asserted ABSENT from the Windows venv (packaging enforcement of C-001).
- G-05: UTF-8 I/O is forced via `PYTHONUTF8=1` (R-08).
- G-06: SaaS sync is disabled by default in CI; sync-specific tests that need it opt in explicitly.
- G-07: Job is blocking on PRs once branch protection is updated.
- G-08 (SC-003 evidence): A commit that reverts any of the mission's fixes (e.g. re-adds the `_DEFAULT_DIR = ~/.config/spec-kitty`, or re-adds `python -m ...` without pinning) MUST turn this job red. Demonstrated in the mission's PR description by running the job against a pre-fix SHA.

## Test contract

| Test ID | File | windows_ci? | Asserts |
|---|---|---|---|
| T-CI-01 | `.github/workflows/ci-windows.yml` exists and runs on `windows-latest` | — | File presence + workflow parse check. |
| T-CI-02 | Branch-protection required-checks update | — | Documented in PR description; manually enforced by a maintainer (GH API step). |
| T-CI-03 | `tests/packaging/test_windows_no_keyring.py` | Yes | Asserts `importlib.util.find_spec('keyring') is None` when run inside the Windows CI venv. |
| T-CI-04 | Duration guard | — | Workflow `timeout-minutes: 20` enforces an upper bound; NFR-002 target is 15 min. |
