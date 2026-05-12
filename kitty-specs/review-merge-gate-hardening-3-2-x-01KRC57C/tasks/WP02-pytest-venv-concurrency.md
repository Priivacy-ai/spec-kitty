---
work_package_id: WP02
title: Concurrency-safe pytest-venv fixture
dependencies: []
requirement_refs:
- FR-003
- FR-004
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-review-merge-gate-hardening-3-2-x-01KRC57C
base_commit: fb6a45d54c20041636a147d70c43b3f6d94544b9
created_at: '2026-05-12T13:13:19.582582+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer:reviewer"
shell_pid: "469050"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: tests/conftest.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- tests/conftest.py
- tests/README.md
- tests/integration/test_pytest_venv_concurrency.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Wrap the shared `.pytest_cache/spec-kitty-test-venv` fixture creation in a file lock so parallel pytest invocations (contract + architectural gates) cannot race and observe half-created venvs. Emit operator-actionable diagnostics on lock-acquire timeout.

This WP fixes [#986](https://github.com/Priivacy-ai/spec-kitty/issues/986) and satisfies FR-003 and FR-004 in [`../spec.md`](../spec.md).

## Context

The mission-review hard gates parallelize contract and architectural test runs. Both suites depend on a shared pytest-venv at `.pytest_cache/spec-kitty-test-venv`. The fixture currently creates that venv on first observation without coordinating across processes — when both suites observe it missing simultaneously, both try to `python -m venv …` against the same path, and one of them fails partway through (`ensurepip` failure during `--upgrade --default-pip`).

The clean fix is a **file lock** around the entire create-or-validate phase of the fixture. Locking via `filelock` (pure-Python, MIT) is widely-used and cross-platform.

Per `research.md` R-2: file lock chosen over per-worker cache because per-worker doubles CI cache traffic; locked p99 latency is ~ 800 ms vs creating-the-world-per-worker on every fork.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP02`. WP02 has no dependencies; can run in parallel with WP04/WP05/WP06/WP07.

## Subtasks

### T006 [P] — Confirm `filelock` availability

**Purpose**: verify that `filelock` is importable from the project's `.venv` so `tests/conftest.py` can use it directly.

**Background**: `filelock 3.29.0` is already a direct dependency at top level in `uv.lock` (verified during planning). This subtask is a sanity check, not an edit.

**Steps**:

1. Verify availability:
   ```bash
   uv tree | grep -i '^├── filelock\|^│   filelock\|^└── filelock'
   uv run python -c "from filelock import FileLock, Timeout; print('ok')"
   ```
2. If for any reason the verification fails (e.g., a future minor version bump removed it), surface the regression — **do not** silently add it. `pyproject.toml` is owned by WP06; coordinate a single dep PR via WP06's implementer.

**Files**: read-only.

**Validation**:
- [ ] `from filelock import FileLock, Timeout` succeeds.

### T007 — Wrap venv creation in a file lock

**Purpose**: Serialize `.pytest_cache/spec-kitty-test-venv` creation across concurrent pytest processes.

**Steps**:

1. Locate the existing fixture in `tests/conftest.py` (or wherever the shared test-venv fixture lives — grep for `spec-kitty-test-venv`):
   ```bash
   rg -n 'spec-kitty-test-venv' tests/
   ```
2. Wrap the creation block in a `FileLock` context manager:
   ```python
   from filelock import FileLock, Timeout

   _VENV_PATH = Path(".pytest_cache/spec-kitty-test-venv")
   _VENV_LOCK = Path(".pytest_cache/spec-kitty-test-venv.lock")
   _LOCK_TIMEOUT_S = 60.0

   def _ensure_test_venv(project_root: Path) -> Path:
       venv_path = project_root / _VENV_PATH
       lock_path = project_root / _VENV_LOCK
       lock_path.parent.mkdir(parents=True, exist_ok=True)
       try:
           with FileLock(str(lock_path), timeout=_LOCK_TIMEOUT_S):
               if not _venv_is_valid(venv_path):
                   _build_test_venv(venv_path)
           return venv_path
       except Timeout:
           raise RuntimeError(
               f"Timed out acquiring {lock_path} after {_LOCK_TIMEOUT_S}s. "
               f"If no test process is currently running, remove the lock file: "
               f"rm {lock_path}"
           )
   ```
3. `_venv_is_valid()` is a helper that checks the venv exists, contains a working Python, and has `pytest` importable. This makes the lock zone idempotent: the second process to acquire sees a valid venv and skips re-creation.

**Files**: `tests/conftest.py`

**Validation**:
- [ ] Single-process pytest run: no behavior change vs pre-WP02.
- [ ] Manual test: two parallel `uv run python -m pytest tests/contract/` and `uv run python -m pytest tests/architectural/` complete without ensurepip errors.

### T008 [P] — Lock-acquire-timeout diagnostic

**Purpose**: when the lock cannot be acquired in 60 s, emit a diagnostic that names the lock file path so the operator can clean a stale lock if no test process is running.

**Steps**: addressed in T007's `except Timeout` block above. This subtask is the explicit acknowledgement that the diagnostic body has the required structure (path + cleanup instruction).

**Validation**:
- [ ] Inject an artificial lock (`touch .pytest_cache/spec-kitty-test-venv.lock; …`) and run pytest; verify the diagnostic body matches FR-018 style (file path + remediation).

### T009 — Regression test: concurrent gate runs

**Purpose**: prove the fixture is safe under concurrent invocation.

**Steps**:

1. Create `tests/integration/test_pytest_venv_concurrency.py`.
2. Test case:
   ```python
   import subprocess
   from concurrent.futures import ThreadPoolExecutor

   def test_concurrent_contract_and_architectural_complete():
       # Wipe any cached venv first
       shutil.rmtree(".pytest_cache/spec-kitty-test-venv", ignore_errors=True)

       def run(suite: str) -> int:
           return subprocess.run(
               ["uv", "run", "python", "-m", "pytest", suite, "-x", "--co", "-q"],
               capture_output=True,
           ).returncode

       with ThreadPoolExecutor(max_workers=2) as ex:
           f1 = ex.submit(run, "tests/contract/")
           f2 = ex.submit(run, "tests/architectural/")
           assert f1.result() == 0
           assert f2.result() == 0
   ```
3. Mark as `@pytest.mark.slow` and exclude from fast-tests; runs in CI integration job.

**Files**: `tests/integration/test_pytest_venv_concurrency.py` (new)

**Validation**:
- [ ] Test passes locally on a clean clone.
- [ ] Test fails (reproduces #986) when the lock is intentionally removed from T007's helper.

### T010 [P] — Document the concurrency contract

**Purpose**: leave breadcrumbs for future contributors who notice the lock file and wonder why it's there.

**Steps**:

1. Add a section to `tests/README.md` (create if missing):
   ```markdown
   ## Pytest venv fixture

   The shared `.pytest_cache/spec-kitty-test-venv` is created once and reused
   across all pytest invocations. To prevent races between parallel test
   processes (e.g., the mission-review gates run contract + architectural
   suites concurrently), creation is wrapped in a file lock at
   `.pytest_cache/spec-kitty-test-venv.lock`.

   If you see a "Timed out acquiring lock" error and no test process is
   running, the lock file is stale (likely from a killed pytest process).
   Remove it: `rm .pytest_cache/spec-kitty-test-venv.lock`.

   See WP02 of the `review-merge-gate-hardening-3-2-x-01KRC57C` mission for
   the original fix.
   ```

**Files**: `tests/README.md`

**Validation**:
- [ ] Section renders correctly in any Markdown viewer.

## Definition of Done

- [ ] T006: `filelock>=3.13,<4` is a direct dep; `uv.lock` updated.
- [ ] T007: fixture wraps creation in `FileLock` with 60s timeout.
- [ ] T008: timeout diagnostic names lock-file path and remediation.
- [ ] T009: regression test passes.
- [ ] T010: `tests/README.md` documents the lock.
- [ ] FR-003 and FR-004 cited in commit messages.

## Risks and Reviewer Guidance

**Risk**: a CI runner may be slow enough that 60 s is insufficient for venv creation under heavy load. If this surfaces, tune the timeout up (do **not** remove the lock).

**Risk**: the lock acquisition order across forks may serialize what was previously parallel, regressing wall-clock CI time. The fix is intentional — correctness > speed for release-gate fixtures. CI time impact should be < 5 s per run.

**Reviewer focus**:
- T007's `_venv_is_valid()` — idempotency on the second acquire is critical; a buggy check would re-build the venv every time.
- T009's negative test — make sure the test actually reproduces #986 without the lock.

## Suggested implement command

```bash
spec-kitty agent action implement WP02 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:13:21Z – claude:sonnet:implementer-ivan:implementer – shell_pid=462665 – Assigned agent via action command
- 2026-05-12T13:16:41Z – claude:sonnet:implementer-ivan:implementer – shell_pid=462665 – WP02 ready: filelock fixture + regression test + README documentation
- 2026-05-12T13:17:13Z – claude:opus:reviewer:reviewer – shell_pid=469050 – Started review via action command
- 2026-05-12T13:19:23Z – claude:opus:reviewer:reviewer – shell_pid=469050 – Review passed: FR-003/FR-004 satisfied. _ensure_test_venv() (tests/conftest.py:181) wraps creation in FileLock(60s) with idempotent _venv_is_valid() check inside lock zone; Timeout diagnostic names lock path + rm remediation; fixture (line 290) delegates correctly; regression test tests/integration/test_pytest_venv_concurrency.py exercises concurrent contract+architectural collection and passed locally (13.18s); scope clean (3 owned files only); tests/README.md documents the contract.
