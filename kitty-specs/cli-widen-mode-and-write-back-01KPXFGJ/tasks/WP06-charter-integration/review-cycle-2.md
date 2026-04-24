---
affected_files: []
cycle_number: 2
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
reproduction_command:
reviewed_at: '2026-04-23T17:06:21Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

# WP06 Review Cycle 1 — Charter Integration

**Reviewer:** claude:sonnet-4-7:python-reviewer:reviewer
**Commit reviewed:** `51278bb4`
**Date:** 2026-04-23

## Overall Assessment: CONDITIONAL BLOCK

The WP06 implementation is fundamentally solid. All 19 widen-integration tests pass, all 7 existing charter tests pass, ruff is clean, and the integration logic correctly handles all three WidenAction paths (CANCEL/BLOCK/CONTINUE). However, there is one blocking issue: a new mypy error introduced by WP06 that was not present in the pre-WP06 baseline.

---

## Blocking Issue

### [BLOCK] New mypy error: `run_candidate_review` stub reference

**Location:** `src/specify_cli/cli/commands/charter.py:581`

**Error:**
```
src/specify_cli/cli/commands/charter.py:581: error: Module "specify_cli.widen.review" has no attribute "run_candidate_review"  [attr-defined]
```

**Baseline (pre-WP06):** 18 charter.py mypy errors (all in `status()` command, lines 1324+ and line 1658).

**Post-WP06:** 19 charter.py mypy errors (same 18 + this new one).

The pre-WP06 charter.py file had 18 mypy errors. WP06 introduced 1 new error by referencing `run_candidate_review` from the `specify_cli.widen.review` stub (which was created by WP02 as a forward-stub for WP07 and currently contains no functions).

The runtime behavior is correct — the import is wrapped in `try/except (ImportError, AttributeError)` so it degrades gracefully. But the mypy error is real and violates the "delta must be zero" criterion.

**Fix (one of the following):**

Option A — Add a `# type: ignore` comment at the import site:
```python
from specify_cli.widen.review import run_candidate_review  # type: ignore[attr-defined]
```

Option B — Stub out the function in `review.py`:
```python
# In src/specify_cli/widen/review.py
from __future__ import annotations
from typing import Any

def run_candidate_review(*args: Any, **kwargs: Any) -> None:
    """WP07 stub — not yet implemented."""
    raise NotImplementedError
```
(Option B is preferred as it also gives WP07 a clean function signature to implement against, and the existing `except (ImportError, AttributeError)` will catch `NotImplementedError`... actually no, NotImplementedError is not caught. Use Option A or add the explicit type stub with the correct signature.)

**Recommended fix:** Add `# type: ignore[attr-defined]` on line 581. This is honest — it's explicitly a forward reference to a WP07 stub.

---

## What Passes (informational)

### Test counts
- 19 widen-integration tests: ALL PASS
- 7 existing charter tests: ALL PASS
- 88 widen module tests (WP01-WP05): ALL PASS (2 skipped)
- 1 charter decision integration test: PASSES

### Patch paths
All 5 uses of `patch("specify_cli.widen.check_prereqs", ...)` use the correct package-level name binding. No uses of the wrong path `specify_cli.widen.prereq.check_prereqs`.

### Integration point correctness
- `[w]iden` gate: correctly gated on `prereq_state.all_satisfied` AND `current_decision_id is not None` AND `mission_id is not None` AND `not _is_already_widened(...)`.
- CANCEL path: `run_widen_mode` → CANCEL → re-prompts same question (inner loop continues). ✓
- CONTINUE path: `run_widen_mode` → CONTINUE → `widen_store.add_pending(WidenPendingEntry(...))` → advance to next question. ✓
- BLOCK path: `run_widen_mode` → BLOCK → `_run_blocked_prompt_loop(...)` → resolved in loop → advance to next question. `add_pending` NOT called on BLOCK (correct — BLOCK resolves synchronously in-session, no pending entry needed). ✓

### Prereq gate
When `SPEC_KITTY_SAAS_TOKEN` is unset (or `mission_slug` is `None`), `[w]iden` does NOT appear in any prompt. Confirmed by `test_widen_option_not_shown_without_token` and `test_widen_option_not_shown_without_mission_slug`.

### `WidenFlow.run_widen_mode` call signature
Matches WP05 contract: `run_widen_mode(decision_id=..., mission_id=..., mission_slug=..., question_text=..., actor=...)`. ✓

### Ruff
Clean. `ruff check src/specify_cli/cli/commands/charter.py` → "All checks passed!"

### Exception safety
`run_widen_mode()` is not wrapped in a try/except in `_dispatch_widen_input`, but the outer `interview()` has a broad `except Exception as e:` that will catch any unexpected raises and exit cleanly with a message (not a crash). Acceptable.

### NFR-004 inactivity timer
`_schedule_inactivity_reminder` creates a `threading.Timer` with `timer.daemon = True`. Timer is cancelled when the blocked prompt resolves. ✓

### Prompt label format
`[enter]=accept default | [text]=type answer | [w]iden | [d]efer | [!cancel]` — matches §1.2 contract exactly. ✓

---

## Required Fix Before Approval

Add `# type: ignore[attr-defined]` to line 581 of `src/specify_cli/cli/commands/charter.py`:

```python
from specify_cli.widen.review import run_candidate_review  # type: ignore[attr-defined]
```

After this fix, `mypy src/specify_cli/cli/commands/charter.py` should show 18 errors (same as pre-WP06 baseline).
