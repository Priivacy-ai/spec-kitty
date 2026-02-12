---
work_package_id: "WP02"
subtasks:
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Fix batch error surfacing and diagnostics"
phase: "Wave 1 - Independent Fixes"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP02 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Fix batch error surfacing and diagnostics

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP02
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- `batch.py` parses per-event `results[]` from HTTP 200 responses (success, duplicate, rejected)
- `batch.py` parses `details` field from HTTP 400 responses (not just top-level `error`)
- Failed events are grouped by reason category with actionable summaries
- Queue operations: synced/duplicate events removed, failures retained with `retry_count++`
- `--report <file.json>` flag exports per-event failure details
- Existing 85+ sync tests pass with zero regressions

## Context & Constraints

- **Delivery branch**: 2.x
- **Root cause**: `batch.py:135` only reads the top-level `error` field from batch responses, discarding the `details` field and per-event `results[]` array
- **Current behavior**: `Synced: 0 Errors: 105` — no detail about WHY events failed
- **Batch contract**: See `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md`
- **Data model**: See `kitty-specs/039-cli-2x-readiness/data-model.md` (BatchResult entity)
- **Reference**: `spec.md` (User Story 2), `plan.md` (WP02)

## Subtasks & Detailed Guidance

### Subtask T004 – Parse per-event results from HTTP 200 responses

- **Purpose**: Extract individual event statuses from successful batch responses so the CLI knows which events succeeded and which were rejected.
- **Steps**:
  1. Read `src/specify_cli/sync/batch.py` on 2.x to understand current response handling
  2. Find the response parsing code (approximately line 135)
  3. After receiving an HTTP 200 response, parse the JSON body for `results[]` array
  4. Each result has: `{"event_id": "...", "status": "success|duplicate|rejected", "error": "..."}`
  5. Create a `BatchResult` dataclass (or named tuple) to hold per-event results:
     ```python
     @dataclass
     class BatchResult:
         event_id: str
         status: str  # "success", "duplicate", "rejected"
         error: Optional[str] = None
         error_category: Optional[str] = None
     ```
  6. Return a list of `BatchResult` from the batch send function
- **Files**: `src/specify_cli/sync/batch.py` (edit)
- **Parallel?**: No — foundation for T005-T009
- **Notes**: The response may also return HTTP 200 with an empty `results[]` if the batch was empty. Handle this edge case.

### Subtask T005 – Parse details field from HTTP 400 responses

- **Purpose**: Surface the `details` field from 400 error responses, which contains per-event failure reasons.
- **Steps**:
  1. In the error handling path of `batch.py`, parse both `error` and `details` from 400 response body:
     ```python
     body = response.json()
     error_msg = body.get("error", "Unknown error")
     details_msg = body.get("details", "")
     ```
  2. Include `details` in the error message surfaced to the user
  3. If `details` contains structured information (JSON string with per-event reasons), parse it
  4. Format the combined error for display: `Error: {error_msg}\nDetails: {details_msg}`
- **Files**: `src/specify_cli/sync/batch.py` (edit)
- **Parallel?**: No — depends on understanding T004's response handling
- **Notes**: The current code at line 135 discards `details` entirely. The fix is to read and display it.

### Subtask T006 – Implement error categorization

- **Purpose**: Group rejected events by failure reason so users see patterns instead of individual errors.
- **Steps**:
  1. Define error categories as constants:
     ```python
     ERROR_CATEGORIES = {
         "schema_mismatch": ["invalid", "schema", "field", "missing", "type"],
         "auth_expired": ["token", "expired", "unauthorized", "401"],
         "server_error": ["internal", "500", "timeout", "unavailable"],
     }
     ```
  2. Create a `categorize_error(error_string: str) -> str` function that inspects the error message for keywords
  3. Default to `"unknown"` if no category matches
  4. Apply categorization to each rejected `BatchResult` from T004
  5. Store the category in `BatchResult.error_category`
- **Files**: `src/specify_cli/sync/batch.py` (add function)
- **Parallel?**: Yes — independent logic, but must integrate with T004's BatchResult
- **Notes**: Keep categorization simple — keyword matching is sufficient. The SaaS team may later provide structured error codes.

### Subtask T007 – Print actionable summary with grouped counts

- **Purpose**: Replace bare "Synced: 0 Errors: 105" with a grouped, actionable summary.
- **Steps**:
  1. After processing all `BatchResult` entries, group by status and error_category:
     ```python
     synced = sum(1 for r in results if r.status == "success")
     duplicates = sum(1 for r in results if r.status == "duplicate")
     failed = [r for r in results if r.status == "rejected"]
     ```
  2. Group failures by category:
     ```python
     from collections import Counter
     category_counts = Counter(r.error_category for r in failed)
     ```
  3. Format and print:
     ```
     Synced: 42, Duplicates: 3, Failed: 60
       schema_mismatch: 45
       auth_expired: 10
       unknown: 5
     ```
  4. Add actionable next steps per category:
     - `schema_mismatch`: "Run `spec-kitty sync diagnose` to inspect invalid events"
     - `auth_expired`: "Run `spec-kitty auth login` to refresh credentials"
     - `server_error`: "Retry later or check server status"
  5. Use Rich console for formatted output
- **Files**: `src/specify_cli/sync/batch.py` (add summary function)
- **Parallel?**: No — depends on T004 and T006

### Subtask T008 – Selective queue removal for synced/duplicate events

- **Purpose**: After a batch sync, remove events that were successfully synced or duplicated, and increment retry_count for failures.
- **Steps**:
  1. Read `src/specify_cli/sync/queue.py` to understand the current queue operations
  2. Add a method to process batch results:
     ```python
     def process_batch_results(self, results: list[BatchResult]) -> None:
         synced_or_duplicate = []
         rejected = []
         for result in results:
             if result.status in ("success", "duplicate"):
                 synced_or_duplicate.append(result.event_id)
             elif result.status == "rejected":
                 rejected.append(result.event_id)
         self.mark_synced(synced_or_duplicate)
         self.increment_retry(rejected)
     ```
  3. Use existing `mark_synced(event_ids)` for success/duplicate rows
  4. Use existing `increment_retry(event_ids)` for rejected rows (`retry_count = retry_count + 1`)
  5. Wrap in a transaction for atomicity
- **Files**: `src/specify_cli/sync/queue.py` (edit)
- **Parallel?**: No — depends on T004's BatchResult type
- **Notes**: Match by `event_id` column in the `queue` table (already indexed/unique on 2.x).

### Subtask T009 – Add --report flag for JSON failure dump

- **Purpose**: For large failure sets (50+ events), allow exporting per-event details to a JSON file for offline analysis.
- **Steps**:
  1. Add `--report` option to the `sync now` CLI command:
     ```python
     @app.command()
     def now(report: Optional[Path] = typer.Option(None, help="Export failure details to JSON file")):
     ```
  2. After batch processing, if `--report` is specified and there are failures:
     ```python
     if report and failed_results:
         report_data = [{"event_id": r.event_id, "error": r.error, "category": r.error_category} for r in failed_results]
         report.write_text(json.dumps(report_data, indent=2))
         console.print(f"Failure report written to {report}")
     ```
  3. Include timestamp and summary metadata in the report
- **Files**: CLI command file for `sync now` (find on 2.x), `src/specify_cli/sync/batch.py` (report generation)
- **Parallel?**: Yes — independent flag, can be added after T004 is stable
- **Notes**: JSON format should be simple and parseable by external tools

### Subtask T010 – Write tests for batch response parsing and queue operations

- **Purpose**: Validate all new functionality with automated tests.
- **Steps**:
  1. Create or extend `tests/sync/test_batch_sync.py`:
     - Test parsing HTTP 200 with mixed results (success + duplicate + rejected)
     - Test parsing HTTP 400 with `error` + `details` fields
     - Test parsing HTTP 400 with `error` only (no `details`)
     - Test error categorization for each category
     - Test actionable summary formatting
  2. Create or extend `tests/sync/test_offline_queue.py`:
     - Test `process_batch_results` with mixed results
     - Test `remove_event` for successful events
     - Test `increment_retry` for failed events
     - Test atomicity (all-or-nothing within a transaction)
  3. Test `--report` flag:
     - Verify JSON file is written with correct structure
     - Verify no file is written when no failures
  4. Run existing sync tests to verify no regressions:
     ```bash
     python -m pytest tests/sync/ -x -v
     ```
- **Files**: `tests/sync/test_batch_sync.py`, `tests/sync/test_offline_queue.py`
- **Parallel?**: No — depends on all prior subtasks

## Test Strategy

- **New tests**: ~10-15 tests across `test_batch_sync.py` and `test_offline_queue.py`
- **Run command**: `python -m pytest tests/sync/ -x -v`
- **Baseline**: 85+ existing sync tests must still pass
- **Fixtures**: Use mock HTTP responses (httpx mock or responses library)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| batch.py structure on 2.x differs from expectations | Read the file first; adapt the fix to actual structure |
| Queue event_id matching is complex (JSON in data column) | Check if there's a dedicated event_id column; if not, add one or use JSON extract |
| Server response format doesn't match contract | Test with mock responses; document any delta in handoff doc |

## Review Guidance

- Verify `batch.py` now parses both `results[]` (200) and `details` (400)
- Verify error categorization produces correct categories for sample error strings
- Verify queue operations are atomic (transaction-wrapped)
- Run `python -m pytest tests/sync/ -x -v` and confirm 85+ tests + new tests pass
- Check that `--report` flag writes valid JSON

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
