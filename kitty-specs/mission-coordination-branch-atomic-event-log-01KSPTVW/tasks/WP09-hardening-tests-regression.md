---
work_package_id: WP09
title: Hardening — architectural test + stress + regression coverage
dependencies:
- WP08
requirement_refs:
- FR-022
- NFR-009
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW
base_commit: fc1aa41f62840ca1fa430e2d8fc372f384fc5421
created_at: '2026-05-28T12:31:38.780752+00:00'
subtasks:
- T039
- T040
- T041
- T042
agent: "claude:opus:reviewer-rita:reviewer"
shell_pid: "62587"
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 3 design
agent_profile: implementer-ivan
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_safe_commit_import_boundary.py
- tests/stress/test_concurrent_emits.py
- tests/regression/test_issue_1348.py
- tests/conftest_saas_sink.py
- src/specify_cli/coordination/outbound.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

Hardening that prevents future regressions and verifies the most subtle atomicity properties at scale:

1. **Architectural test** (T039): Forbid direct imports of `safe_commit` from transactional workflow modules. After WP06, those modules go through `BookkeepingTransaction`; this test prevents accidental future regression.
2. **Stress test** (T040): 20 concurrent `implement` calls; verify no interleaved partial writes (SC-12).
3. **SaaS-sink fanout deferral** (T041): The `defer_outbound` mechanism from WP05 is the in-memory plumbing. This subtask adds the actual outbound integration (mock-sink test fixture; instrument any real SaaS code paths to register their emissions via `defer_outbound`).
4. **Issue #1348 regression test** (T042): Verify the exact reproduction sequence from the issue fails on `main` after the fix.

This WP is **optional** in the sense that the core mission (WP01..WP08) closes #1348. WP09 prevents the re-introduction of the bug class.

## Context

**Spec source**: FR-022, NFR-009, SC-06, SC-09, SC-12.
**Predecessor WPs**: WP08 (legacy fallback). All other workflow code is in place.
**Cross-review motivation**: the "implementer satisfies text superficially but recreates partial state" failure mode — WP09's architectural test specifically guards against it.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Lane D; can run in parallel with later stages of Lane C if WP05 is already reviewed.

---

## Subtask T039: Architectural test — forbid direct `safe_commit` imports

**Purpose**: After WP06, modules under `src/specify_cli/cli/commands/agent/` and `src/specify_cli/status/` go through `BookkeepingTransaction`. Future contributors might accidentally `from specify_cli.git.commit_helpers import safe_commit` and bypass the transaction layer. The architectural test catches this in CI.

**Steps**:
1. Create `tests/architectural/test_safe_commit_import_boundary.py`:
   ```python
   import ast
   from pathlib import Path
   import pytest

   FORBIDDEN_DIRECT_IMPORT_MODULES = [
       "src/specify_cli/cli/commands/implement.py",
       "src/specify_cli/cli/commands/agent/workflow.py",
       "src/specify_cli/cli/commands/agent/mission.py",  # workflow path of finalize-tasks
       "src/specify_cli/status/emit.py",
   ]

   ALLOWED_IMPORTERS = {
       "src/specify_cli/coordination/transaction.py",
       "src/specify_cli/coordination/policy.py",
       "src/specify_cli/cli/commands/safe_commit.py",  # the user-facing CLI
       # tests can import anything
   }

   def _module_imports_safe_commit(path: Path) -> bool:
       tree = ast.parse(path.read_text())
       for node in ast.walk(tree):
           if isinstance(node, ast.ImportFrom):
               if node.module and "commit_helpers" in node.module:
                   for n in node.names:
                       if n.name == "safe_commit":
                           return True
       return False

   @pytest.mark.parametrize("forbidden", FORBIDDEN_DIRECT_IMPORT_MODULES)
   def test_forbidden_modules_do_not_import_safe_commit_directly(forbidden, repo_root):
       path = repo_root / forbidden
       if not path.exists():
           pytest.skip(f"{forbidden} does not exist (file may have been renamed)")
       assert not _module_imports_safe_commit(path), (
           f"{forbidden} directly imports safe_commit. "
           f"Workflow modules MUST go through BookkeepingTransaction. "
           f"See contracts/bookkeeping_transaction.md."
       )
   ```
2. Add the test to the CI pipeline.

**Files**:
- `tests/architectural/__init__.py`
- `tests/architectural/test_safe_commit_import_boundary.py`

**Validation**:
- [ ] Test passes on the post-WP06 codebase.
- [ ] Adding `from specify_cli.git.commit_helpers import safe_commit` to `implement.py` and re-running the test makes it fail.

## Subtask T040: Stress test — 20 concurrent `implement` calls (SC-12)

**Purpose**: Verify that the feature status lock (FR-026) actually serializes 20 concurrent emitters and produces a valid event log with no interleaved partial writes.

**Steps**:
1. Create `tests/stress/test_concurrent_emits.py`:
   ```python
   import multiprocessing as mp
   from pathlib import Path
   import pytest

   def _run_implement(args):
       wp_id, mission_dir = args
       # invoke spec-kitty implement WPxx in subprocess
       ...

   @pytest.mark.stress
   @pytest.mark.timeout(60)
   def test_20_concurrent_implements_produce_valid_event_log(tmp_repo_with_mission):
       wps = [f"WP{i:02d}" for i in range(1, 21)]
       with mp.Pool(20) as p:
           p.map(_run_implement, [(wp, tmp_repo_with_mission) for wp in wps])
       # Read the event log; verify:
       events_path = tmp_repo_with_mission / "kitty-specs" / "<slug>" / "status.events.jsonl"
       lines = events_path.read_text().splitlines()
       assert len(lines) == 20  # one event per WP
       # Every line is valid JSON
       import json
       for line in lines:
           json.loads(line)
       # No event_id duplicates
       event_ids = set()
       for line in lines:
           e = json.loads(line)
           assert e["event_id"] not in event_ids
           event_ids.add(e["event_id"])
   ```
2. Mark the test `@pytest.mark.stress` so it can be excluded from fast test runs.
3. Verify the test runs in under 60 seconds on a typical CI runner. If slower, reduce to 10 concurrent emitters.

**Files**:
- `tests/stress/__init__.py`
- `tests/stress/test_concurrent_emits.py`
- `tests/conftest.py` — register the `stress` marker if not already.

**Validation**:
- [ ] Test passes; event log is valid, ordered, no duplicates.
- [ ] Removing the lock (mutation test) → test fails.

## Subtask T041: SaaS-sink fanout deferral instrumentation + mock fixture

**Purpose**: FR-022's outbound deferral is implemented as a hook in WP05 (`defer_outbound`). This subtask provides (a) a mock SaaS sink for tests, and (b) instrumentation hooking real SaaS code paths into the deferral mechanism.

**Steps**:
1. Create `tests/conftest_saas_sink.py` (or add fixtures to existing conftest):
   ```python
   import pytest
   from unittest.mock import MagicMock

   @pytest.fixture
   def mock_saas_sink(monkeypatch):
       """Mock SaaS event sink; records every emission for assertions."""
       sink = MagicMock()
       sink.calls = []
       def record(event):
           sink.calls.append(event)
       sink.side_effect = record
       monkeypatch.setattr("specify_cli.saas.client.send_event", sink)
       yield sink
   ```
2. Create `src/specify_cli/coordination/outbound.py` — a thin module that registers outbound side effects with the active transaction:
   ```python
   def queue_saas_emission(txn, event):
       """Register an outbound SaaS emission to fire after the local commit succeeds."""
       txn.defer_outbound(lambda: _send_to_saas(event))

   def _send_to_saas(event):
       from specify_cli.saas.client import send_event
       send_event(event)
   ```
3. Wherever the existing codebase currently calls `send_event(...)` from inside a workflow path, change the call to `queue_saas_emission(txn, event)`.
4. Add tests:
   - `test_saas_emits_after_commit_success()` — use `mock_saas_sink`; run implement; assert sink received the event once.
   - `test_saas_does_not_emit_on_commit_failure()` — force commit failure; assert `sink.calls == []` (SC-09 / NFR-009).

**Files**:
- `src/specify_cli/coordination/outbound.py`
- `tests/conftest_saas_sink.py`
- Tests in `tests/specify_cli/coordination/test_outbound.py`

**Validation**:
- [ ] Mock sink records emissions on success.
- [ ] Zero emissions on rollback (NFR-009).
- [ ] Existing direct `send_event` callers are migrated.

## Subtask T042: Issue #1348 regression test

**Purpose**: The exact reproduction sequence from issue #1348 must fail on `main`. This is a guardrail test that explicitly references the issue.

**Steps**:
1. Create `tests/regression/test_issue_1348.py`:
   ```python
   import pytest
   import hashlib
   from pathlib import Path

   def _sha256(path: Path) -> str:
       return hashlib.sha256(path.read_bytes()).hexdigest()

   def test_issue_1348_planning_artifact_does_not_land_on_main(tmp_repo_with_mission, monkeypatch):
       """Regression for issue #1348:
       Running `agent action implement` from a main checkout must NOT silently commit
       planning artifacts to main. The bookkeeping commit goes to the coord branch.
       """
       repo = tmp_repo_with_mission
       # Capture main's commit SHA before
       main_sha_before = subprocess.check_output(
           ["git", "-C", str(repo), "rev-parse", "main"], text=True,
       ).strip()
       # Run implement from main checkout
       subprocess.run(
           ["spec-kitky", "agent", "action", "implement", "WP01", "--agent", "test"],
           cwd=repo, check=True,
       )
       # Assert main has NOT advanced
       main_sha_after = subprocess.check_output(
           ["git", "-C", str(repo), "rev-parse", "main"], text=True,
       ).strip()
       assert main_sha_before == main_sha_after, (
           "Issue #1348: planning artifact commit landed on main."
       )

   def test_issue_1348_dangling_event_log_does_not_occur(tmp_repo_with_mission, failing_hook):
       """Regression for issue #1348 comment:
       Forced commit failure must NOT leave status.events.jsonl ahead of HEAD.
       """
       repo = tmp_repo_with_mission
       events_path = repo / ".worktrees" / "<slug>-<mid8>-coord" / "kitty-specs" / "<slug>" / "status.events.jsonl"
       sha_before = _sha256(events_path) if events_path.exists() else None
       # Install pre-commit hook that always rejects
       failing_hook.install(repo)
       result = subprocess.run(
           ["spec-kitty", "agent", "action", "implement", "WP01", "--agent", "test"],
           cwd=repo, capture_output=True,
       )
       assert result.returncode != 0  # implement should fail loudly
       # Assert events file is byte-identical
       sha_after = _sha256(events_path) if events_path.exists() else None
       assert sha_before == sha_after, (
           "Issue #1348: status.events.jsonl is ahead of HEAD after forced commit failure."
       )
   ```
2. Use real subprocesses to test the binary's behavior end-to-end (not just internal API calls). This is what an external bug reporter would do.

**Files**:
- `tests/regression/__init__.py`
- `tests/regression/test_issue_1348.py`

**Validation**:
- [ ] Both regression tests pass.
- [ ] Removing the WP06 migration (mutation test) → first test fails.
- [ ] Removing the rollback in WP05 (mutation test) → second test fails.

---

## Definition of Done

- [ ] All 4 subtasks complete (T039..T042).
- [ ] `pytest tests/architectural/` passes.
- [ ] `pytest tests/stress/ -m stress` passes within 60s.
- [ ] `pytest tests/regression/test_issue_1348.py` passes.
- [ ] Mock SaaS sink fixture is usable from other tests.
- [ ] CHANGELOG entry (or doctor command output) notes the hardening tests are present.

## Risks

- **CI slowness**: stress tests can be slow. Mark `@pytest.mark.stress` and run separately.
- **AST parsing fragility**: the architectural test uses Python AST; refactors (e.g. re-exports through `__init__.py`) could fool it. Add a comment in `commit_helpers.py` warning future contributors not to re-export `safe_commit` from another module.
- **Regression test fixture realism**: the `failing_hook` fixture must actually install a real pre-commit hook in the tmp repo. Mocks at the Python level may miss the real failure mode.

## Reviewer guidance

1. **Architectural test**: confirm the forbidden modules list is exhaustive. Add `cli/commands/agent/mission.py` (or its split-out finalize_tasks file).
2. **Stress test reliability**: confirm 20 concurrent emitters is achievable in CI. If flaky, document the flake source and lower to 10.
3. **SaaS sink fixture**: confirm it intercepts at the right boundary (the actual HTTP/IPC call to the SaaS).
4. **Issue #1348 regression**: confirm the reproduction sequence matches the issue text closely (planning artifact on main; dangling event after commit refuse).
5. **Markers**: confirm `@pytest.mark.stress` and `@pytest.mark.regression` are registered in `conftest.py`.

## References

- Spec: FR-022, NFR-009, SC-06, SC-09, SC-12
- Plan: PR 3 (optional hardening)
- Issue: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348)
- Research: R-007 in [`research.md`](../research.md)

## Activity Log

- 2026-05-28T12:31:38Z – claude:opus:implementer-ivan:implementer – shell_pid=57645 – Assigned agent via action command
- 2026-05-28T12:44:27Z – claude:opus:implementer-ivan:implementer – shell_pid=57645 – WP09 hardening ready
- 2026-05-28T12:45:18Z – claude:opus:reviewer-rita:reviewer – shell_pid=62587 – Started review via action command
- 2026-05-28T12:47:23Z – claude:opus:reviewer-rita:reviewer – shell_pid=62587 – Review passed: T039 architectural test forbids safe_commit in status/emit.py and sanity-checks the three documented legacy fallback modules (pragmatic per prompt). T040 stress test with 20 concurrent emitters passes in <8s (well under 60s SLA): all events present, unique event_ids, valid JSON, no duplicates. T041 queue_saas_emission helper + mock_saas_sink fixture: success path emits one event with correct kwargs, rollback path emits zero (NFR-009/SC-09). T042 regression tests reproduce #1348 exactly: main HEAD unchanged on implement-from-main (SC-06), SHA-256 byte-identical on forced commit failure (SC-05), legacy fallback parity (SC-11). mypy --strict clean. All 4 caveats accepted: (1) pragmatic scope per prompt guidance, (2) test scaffolding necessary, (3) production-matching worktree warming, (4) PYTHONPATH injection required for subprocess. ALL 9 WPs APPROVED. Mission ready for acceptance.
