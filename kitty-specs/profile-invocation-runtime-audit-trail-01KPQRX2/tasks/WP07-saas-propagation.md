---
work_package_id: WP07
title: SaaS propagation (additive, non-blocking)
dependencies:
- WP06
requirement_refs:
- FR-015
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning base: main. Merge target: main. Execution worktrees are allocated per computed lane from lanes.json.'
subtasks:
- T027
- T028
- T029
- T030
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/invocation/propagator.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/propagator.py
- tests/specify_cli/invocation/test_propagator.py
tags: []
---

# WP07 — SaaS Propagation (Additive, Non-Blocking)

## Objective

Implement `InvocationSaaSPropagator` — a background-thread propagator that sends
`InvocationRecord` events to SaaS using the existing CLI-SaaS contract, after a
successful local write. Propagation failure must never block or fail the CLI.

**Implementation command**:
```bash
spec-kitty agent action implement WP07 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Entry Gate: CLI-SaaS Contract Verification

**MANDATORY before starting T028.**

The CLI-SaaS contract in `spec-kitty-saas/contracts/cli-saas-current-api.yaml` must be
verified to contain `ProfileInvocationStarted` and `ProfileInvocationCompleted` event
types with fields that cover all v1 `InvocationRecord` fields.

**Check**:
```bash
# If you have access to spec-kitty-saas:
cat spec-kitty-saas/contracts/cli-saas-current-api.yaml | grep -A 20 "ProfileInvocation"
```

If the contract is missing fields (e.g., `request_text`, `governance_context_hash`, `outcome`):
1. **Do NOT adapt silently** — raise a blocking issue with the spec-kitty-saas team.
2. Document the gap in T027's review notes.
3. WP07 is BLOCKED until the contract is updated.

---

## Subtask T027 — Entry Gate: Contract Field Coverage Verification

**Purpose**: Verify that the CLI-SaaS contract covers the v1 `InvocationRecord` fields.

**Steps**:

1. Check the existing SaaS sync client in the spec-kitty codebase (search `src/` for `ProfileInvocationStarted` or similar):
   ```bash
   grep -r "ProfileInvocation" src/ --include="*.py" -l
   ```

2. Identify how the current charter sync sends events (likely via `src/specify_cli/sync/` or similar).

3. Verify these fields are present in the contract envelope:
   - `invocation_id`
   - `profile_id`
   - `action`
   - `started_at`
   - Ideally also: `request_text`, `governance_context_hash`, `outcome`, `evidence_ref`

4. Document findings in a `# CONTRACT VERIFICATION` comment at the top of `propagator.py`.

5. If fields are missing: STOP and file a blocking issue. Do NOT ship WP07 with silent field drops.

**Output**: Written comment in propagator.py confirming contract coverage or describing the gap.

---

## Subtask T028 — `propagator.py`: InvocationSaaSPropagator

**Purpose**: Non-blocking background propagator using `concurrent.futures.ThreadPoolExecutor`.

**Steps**:

1. Create `src/specify_cli/invocation/propagator.py`:

```python
from __future__ import annotations
import atexit
import json
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from typing import Any

from specify_cli.invocation.record import InvocationRecord

logger = logging.getLogger(__name__)

PROPAGATION_ERRORS_PATH = ".kittify/events/propagation-errors.jsonl"
_ATEXIT_TIMEOUT_SECONDS = 5.0

# CONTRACT VERIFICATION:
# Verified that spec-kitty-saas contract (cli-saas-current-api.yaml) includes:
# ProfileInvocationStarted: invocation_id, profile_id, action, started_at
# ProfileInvocationCompleted: invocation_id, outcome
# Gaps (if any): document here
# -- verified 2026-04-21 --


def _get_saas_client(repo_root: Path) -> Any | None:
    """
    Load the existing SaaS sync client if a token is configured.
    Returns None if no token is configured or if the client is unavailable.
    Replace this with the actual SaaS client factory used elsewhere in the codebase.
    """
    try:
        # Follow the pattern in src/specify_cli/sync/ (or similar)
        # Example: from specify_cli.sync.client import SaaSClient, get_client
        # return get_client(repo_root)
        return None  # Replace with actual implementation
    except Exception:
        return None  # No token configured → no-op


def _propagate_one(record: InvocationRecord, repo_root: Path) -> None:
    """
    Propagate a single InvocationRecord to SaaS.
    Runs in a background thread. Logs errors to propagation-errors.jsonl on failure.
    Never raises — swallows all exceptions.
    """
    client = _get_saas_client(repo_root)
    if client is None:
        return  # No SaaS token → no-op, no log

    try:
        # Build the SaaS envelope from the record
        if record.event == "started":
            event_type = "ProfileInvocationStarted"
            payload = {
                "invocation_id": record.invocation_id,
                "profile_id": record.profile_id,
                "action": record.action,
                "request_text": record.request_text,
                "governance_context_hash": record.governance_context_hash,
                "actor": record.actor,
                "started_at": record.started_at,
            }
        else:  # completed
            event_type = "ProfileInvocationCompleted"
            payload = {
                "invocation_id": record.invocation_id,
                "outcome": record.outcome,
                "evidence_ref": record.evidence_ref,
                "completed_at": record.completed_at,
            }

        # The idempotency key is the invocation_id — the SaaS client should handle deduplication
        client.send_event(event_type, payload, idempotency_key=record.invocation_id)

    except Exception as e:
        _log_propagation_error(repo_root, record, str(e))


def _log_propagation_error(repo_root: Path, record: InvocationRecord, error: str) -> None:
    """Append propagation failure to the local error log. Never raises."""
    try:
        import datetime
        error_log = repo_root / PROPAGATION_ERRORS_PATH
        error_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "invocation_id": record.invocation_id,
            "event": record.event,
            "error": error,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with error_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Error logging must never raise


class InvocationSaaSPropagator:
    """
    Background-thread SaaS propagator for InvocationRecord events.

    Properties:
    - Non-blocking: submit() returns immediately; propagation happens in background
    - additive: if no SaaS token, no-op (no error, no warning)
    - idempotency: invocation_id is the deduplication key sent to SaaS
    - failure-safe: propagation errors logged to propagation-errors.jsonl, never raised
    - process-exit: atexit handler waits up to 5 seconds for pending propagations
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="invocation-saas")
        self._pending: list[Future[None]] = []
        atexit.register(self._shutdown)

    def submit(self, record: InvocationRecord) -> None:
        """Submit a record for background propagation. Returns immediately."""
        future = self._executor.submit(_propagate_one, record, self._repo_root)
        self._pending.append(future)

    def _shutdown(self) -> None:
        """Wait up to 5 seconds for pending propagations at process exit."""
        self._executor.shutdown(wait=True, cancel_futures=False)
        # Timeout is handled by the ThreadPoolExecutor's graceful shutdown
        # If not completed within process exit, the thread is abandoned
```

**Files**: `src/specify_cli/invocation/propagator.py`

---

## Subtask T029 — Wire Propagator into `executor.py`

**Purpose**: After a successful `write_completed()`, the executor should submit the completed record to the propagator.

**Steps**:

1. Update `src/specify_cli/invocation/executor.py` to accept an optional propagator:

```python
class ProfileInvocationExecutor:
    def __init__(
        self,
        repo_root: Path,
        router: "ActionRouter | None" = None,
        propagator: "InvocationSaaSPropagator | None" = None,
    ) -> None:
        ...
        self._propagator = propagator
```

2. In the `invoke()` method, after `self._writer.write_started(record)`:
   ```python
   # Propagate started event (non-blocking)
   if self._propagator is not None:
       self._propagator.submit(record)
   ```

3. Add a `complete_invocation()` method to the executor (or keep it in the writer — consistent with WP03 approach):
   ```python
   def complete_invocation(
       self,
       invocation_id: str,
       profile_id: str,
       outcome: str | None = None,
       evidence_ref: str | None = None,
   ) -> InvocationRecord:
       completed = self._writer.write_completed(invocation_id, profile_id, self._repo_root, outcome=outcome, evidence_ref=evidence_ref)
       if self._propagator is not None:
           self._propagator.submit(completed)
       return completed
   ```

4. In CLI commands that create the executor (WP03's `advise.py`, WP04's `do_cmd.py`), inject the propagator:
   ```python
   from specify_cli.invocation.propagator import InvocationSaaSPropagator

   def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
       registry = ProfileRegistry(repo_root)
       router = ActionRouter(registry)
       propagator = InvocationSaaSPropagator(repo_root)
       return ProfileInvocationExecutor(repo_root, router=router, propagator=propagator)
   ```

**Note**: WP07 touches `executor.py` (from WP01). Since WP07 depends on WP01 through the chain (WP01 → WP06 → WP07), this is a sequential modification. The lane serializes it.

**Files**: `src/specify_cli/invocation/executor.py` (modify)

---

## Subtask T030 — `test_propagator.py`

**Purpose**: Verify non-blocking behavior, error handling, idempotency key, and no-op on missing token.

**Test cases**:

```python
from unittest.mock import MagicMock, patch
from specify_cli.invocation.propagator import InvocationSaaSPropagator, _propagate_one
from specify_cli.invocation.record import InvocationRecord
import time

def make_started_record() -> InvocationRecord:
    return InvocationRecord(
        event="started", invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="implementer-fixture", action="implement",
        request_text="implement the feature", started_at="2026-04-21T10:00:00Z",
    )

def test_propagator_non_blocking(tmp_path):
    """submit() returns in < 50ms even if the SaaS call takes 500ms."""
    record = make_started_record()
    propagator = InvocationSaaSPropagator(tmp_path)
    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_client_factory:
        mock_client = MagicMock()
        def slow_send(*args, **kwargs):
            time.sleep(0.5)
        mock_client.send_event.side_effect = slow_send
        mock_client_factory.return_value = mock_client
        start = time.monotonic()
        propagator.submit(record)
        elapsed = time.monotonic() - start
        assert elapsed < 0.05, f"submit() blocked for {elapsed:.3f}s"

def test_propagator_no_op_when_no_token(tmp_path):
    """When _get_saas_client returns None, no errors and no log entry."""
    record = make_started_record()
    with patch("specify_cli.invocation.propagator._get_saas_client", return_value=None):
        _propagate_one(record, tmp_path)
    error_log = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    assert not error_log.exists()

def test_propagator_logs_error_on_saas_failure(tmp_path):
    """SaaS 5xx → error logged to propagation-errors.jsonl, no exception raised."""
    record = make_started_record()
    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.send_event.side_effect = RuntimeError("SaaS returned 503")
        mock_factory.return_value = mock_client
        _propagate_one(record, tmp_path)
    error_log = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    assert error_log.exists()
    import json
    entries = [json.loads(l) for l in error_log.read_text().splitlines() if l]
    assert len(entries) == 1
    assert "503" in entries[0]["error"]
    assert entries[0]["invocation_id"] == record.invocation_id

def test_propagator_uses_invocation_id_as_idempotency_key(tmp_path):
    """invocation_id is passed as idempotency_key to client.send_event."""
    record = make_started_record()
    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        _propagate_one(record, tmp_path)
    call_kwargs = mock_client.send_event.call_args.kwargs
    assert call_kwargs.get("idempotency_key") == record.invocation_id

def test_propagator_error_log_never_raises_on_disk_full(tmp_path):
    """If propagation error log itself fails (disk full), no exception raised."""
    record = make_started_record()
    with patch("builtins.open", side_effect=OSError("disk full")):
        # Should not raise
        _log_propagation_error = __import__(
            "specify_cli.invocation.propagator", fromlist=["_log_propagation_error"]
        )._log_propagation_error
        _log_propagation_error(tmp_path, record, "test error")
```

**Files**: `tests/specify_cli/invocation/test_propagator.py`

**Acceptance**:
- [ ] All 5 propagator tests pass
- [ ] `mypy --strict` clean on `propagator.py`
- [ ] Contract verification comment in `propagator.py` is accurate
- [ ] CLI `advise`/`do` commands pass propagator to executor

## Definition of Done

- [ ] `propagator.py` implements background thread, atexit shutdown, error log
- [ ] `executor.py` accepts `propagator=` parameter and submits after writes
- [ ] Contract verification documented in propagator.py
- [ ] All 5 tests pass
- [ ] `mypy --strict` clean
- [ ] `spec-kitty advise "implement" --profile implementer-fixture` completes in < 500ms (propagation non-blocking)

## Risks

- **SaaS client import pattern**: Find the existing SaaS sync client by searching for `send_event` or `sync_client` patterns in `src/specify_cli/`. Replace the placeholder `_get_saas_client()` with the actual factory call.
- **atexit + ThreadPoolExecutor**: `ThreadPoolExecutor.shutdown(wait=True)` blocks until all pending futures complete. At 5-second process exit, threads that haven't finished are abandoned (not cancelled). This is acceptable behavior.
- **Contract gap found**: If T027 reveals that the SaaS contract is missing fields, WP07 MUST be blocked until the contract is updated. Do not silently drop fields from the propagation payload.

## Reviewer Guidance

1. Verify `submit()` returns in < 50ms (check the non-blocking test).
2. Verify error log path is `.kittify/events/propagation-errors.jsonl` (not inside profile-invocations/).
3. Verify `idempotency_key=record.invocation_id` is passed to `client.send_event`.
4. Verify `_get_saas_client()` returns None when no token is configured (check actual implementation).
5. Verify CONTRACT VERIFICATION comment in propagator.py is accurate and references the actual fields verified.
