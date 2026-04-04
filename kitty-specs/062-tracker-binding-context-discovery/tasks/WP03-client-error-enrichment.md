---
work_package_id: WP03
title: Client Error Enrichment
dependencies: []
requirement_refs:
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 68d56feb837dccbcf5f9765cfe765206367d1fb1
created_at: '2026-04-04T09:34:50.561102+00:00'
subtasks: [T011, T012, T013, T014]
shell_pid: "61558"
agent: "coordinator"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files: [src/specify_cli/tracker/saas_client.py, tests/sync/tracker/test_saas_client.py]
---

# WP03: Client Error Enrichment

## Objective

Enrich `SaaSTrackerClientError` with structured attributes (`error_code`, `status_code`, `details`, `user_action_required`) extracted from the PRI-12 error envelope. This is a prerequisite for reactive stale-binding detection in the service layer (FR-018).

## Context

- **Spec**: FR-018 (stale binding detection requires error code inspection)
- **Plan**: Client Error Enrichment section in plan.md
- **Research**: Decision 8 in research.md
- **Current code**: `src/specify_cli/tracker/saas_client.py` — `SaaSTrackerClientError` class (line ~52), `_request_with_retry` (lines 157-218)
- **Current tests**: `tests/sync/tracker/test_saas_client.py`

The current exception collapses all error info into a string message. The service layer will need to inspect `error.error_code` for codes like `binding_not_found`, `mapping_disabled`, `project_mismatch`.

## Implementation Command

```bash
spec-kitty implement WP03
```

No dependencies — this WP can start immediately.

## Subtasks

### T011: Enrich SaaSTrackerClientError

**Purpose**: Add structured attributes while preserving backward compatibility.

**Steps**:
1. Find `SaaSTrackerClientError` in `saas_client.py` (around line 52)
2. Replace with enriched version:
   ```python
   class SaaSTrackerClientError(Exception):
       """Raised when SaaS tracker API calls fail.

       Attributes carry structured PRI-12 error envelope data for
       programmatic inspection (e.g., stale-binding detection).
       Backward compatible: str(e) returns the message.
       """

       def __init__(
           self,
           message: str,
           *,
           error_code: str | None = None,
           status_code: int | None = None,
           details: dict[str, Any] | None = None,
           user_action_required: bool = False,
       ) -> None:
           super().__init__(message)
           self.error_code = error_code
           self.status_code = status_code
           self.details = details or {}
           self.user_action_required = user_action_required
   ```
3. Ensure `from typing import Any` is imported at module level

**Files**: `src/specify_cli/tracker/saas_client.py`

### T012: Update _request_with_retry to Populate Enriched Attrs

**Purpose**: Extract error_code and details from PRI-12 envelope when raising.

**Steps**:
1. Find the non-2xx error handler (around line 208-216):
   ```python
   # Current:
   if response.status_code >= 400:
       envelope = _parse_error_envelope(response)
       msg = envelope.get("message") or f"HTTP {response.status_code}"
       if envelope.get("user_action_required"):
           msg += " (action required — check the Spec Kitty dashboard)"
       raise SaaSTrackerClientError(msg)
   ```
2. Replace with enriched raising:
   ```python
   if response.status_code >= 400:
       envelope = _parse_error_envelope(response)
       msg = envelope.get("message") or f"HTTP {response.status_code}"
       if envelope.get("user_action_required"):
           msg += " (action required — check the Spec Kitty dashboard)"
       raise SaaSTrackerClientError(
           msg,
           error_code=envelope.get("error_code"),
           status_code=response.status_code,
           details=envelope,
           user_action_required=bool(envelope.get("user_action_required")),
       )
   ```
3. Also update the 429 rate-limit handler (around line 204) to include status_code:
   ```python
   raise SaaSTrackerClientError(
       envelope.get("message") or "Rate limited by SaaS API.",
       error_code="rate_limited",
       status_code=429,
   )
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T013: Write Enriched Error Tests

**Purpose**: Verify error_code and details are preserved.

**Steps**:
1. Add to `tests/sync/tracker/test_saas_client.py`:
   - `test_error_enrichment_preserves_error_code`: mock 400 with `{"error_code": "binding_not_found", "message": "..."}` → verify `e.error_code == "binding_not_found"`
   - `test_error_enrichment_preserves_status_code`: verify `e.status_code == 400`
   - `test_error_enrichment_preserves_details`: verify `e.details` is the full envelope dict
   - `test_error_enrichment_user_action_required`: verify `e.user_action_required == True`
   - `test_error_enrichment_backward_compat`: verify `str(e)` returns the message string
   - `test_error_enrichment_missing_envelope`: empty body → `error_code=None`, `status_code=400`

**Files**: `tests/sync/tracker/test_saas_client.py`

### T014: Write Regression Tests

**Purpose**: Ensure existing callers that do `except SaaSTrackerClientError as e: str(e)` still work.

**Steps**:
1. Verify existing test patterns in `test_saas_client.py` still pass unmodified
2. Add explicit test:
   ```python
   def test_existing_str_pattern():
       err = SaaSTrackerClientError("Something failed")
       assert str(err) == "Something failed"
       assert err.error_code is None
       assert err.status_code is None
       assert err.details == {}
       assert err.user_action_required is False
   ```

**Files**: `tests/sync/tracker/test_saas_client.py`

## Definition of Done

- [ ] `SaaSTrackerClientError` has `error_code`, `status_code`, `details`, `user_action_required` attrs
- [ ] `_request_with_retry` populates these from PRI-12 envelope
- [ ] `str(e)` still returns the message (backward compat)
- [ ] All existing tests pass: `python -m pytest tests/sync/tracker/test_saas_client.py -x -q`
- [ ] New enrichment tests pass
- [ ] `ruff check src/specify_cli/tracker/saas_client.py`
- [ ] `mypy src/specify_cli/tracker/saas_client.py`

## Risks

- **Existing callers constructing SaaSTrackerClientError(msg)**: All new params are keyword-only with defaults. Existing `SaaSTrackerClientError("msg")` calls work unchanged. No risk.

## Reviewer Guidance

- Check that EVERY `raise SaaSTrackerClientError(...)` call in `_request_with_retry` now passes `error_code` and `status_code`
- Verify the 401 refresh path (line ~172-189) also uses enriched raising if it re-raises
- Run the full `test_saas_client.py` suite, not just new tests

## Activity Log

- 2026-04-04T09:34:50Z – coordinator – shell_pid=32846 – Started implementation via workflow command
- 2026-04-04T09:38:50Z – coordinator – shell_pid=32846 – Ready for review: enriched SaaSTrackerClientError with error_code, status_code, details, user_action_required attrs; all 55 tests pass; ruff clean
- 2026-04-04T09:39:40Z – codex – shell_pid=51022 – Started review via workflow command
- 2026-04-04T09:44:39Z – codex – shell_pid=51022 – Moved to planned
- 2026-04-04T09:46:20Z – coordinator – shell_pid=61558 – Started implementation via workflow command
