# WP07 Review — Cycle 1

**Commit reviewed:** `08899022`
**Reviewer:** `claude:sonnet-4-7:python-reviewer:reviewer`
**Date:** 2026-04-23

---

## Verdict: CHANGES REQUESTED

Two blocking issues. All linting / mypy / tests pass (45/45), but the implementation
silently drops `summary_json` provenance from every `resolve_decision` call, which is
the core write-back contract for this WP.

---

## Blocking Issue 1 — `_handle_accept` drops `summary_json` (T036 / §6.1 / C-005)

**Location:** `src/specify_cli/widen/review.py` lines 268–275

**Problem:** The contract (§6.1) and WP spec (T036) both require:
```python
dm_service.resolve_decision(
    ...,
    final_answer=final,
    summary_json={"text": candidate.candidate_summary, "source": SummarySource.SLACK_EXTRACTION},
    actor=actor,
)
```
The implementation calls `resolve_decision` with only `final_answer` + `actor` — `summary_json` is absent.

**Root cause:** `decisions.service.resolve_decision` (from dependency #757) does not currently
accept a `summary_json` keyword argument. The implementer dropped it silently rather than noting
the gap.

**Impact:** The `source` provenance value (`slack_extraction`) is **never persisted** to the
decision artifact on the accept path. C-005 is violated: `summary_json.source` is the only
field that distinguishes widen-resolved decisions from locally-answered ones. Without it, SaaS
and downstream reporting cannot tell whether a resolution came from a widened discussion or was
typed directly.

**Fix required (two parts):**

1. Extend `decisions.service.resolve_decision` to accept `summary_json: dict | None = None`
   and persist it to the decision artifact (this may need to be coordinated with WP10 or done
   here as a patch to the existing decisions module).

2. Pass `summary_json` in `_handle_accept`:
   ```python
   dm_service.resolve_decision(
       repo_root=repo_root,
       mission_slug=mission_slug,
       decision_id=candidate.decision_id,
       final_answer=final,
       summary_json={"text": candidate.candidate_summary, "source": SummarySource.SLACK_EXTRACTION},
       actor=actor,
   )
   ```

---

## Blocking Issue 2 — `_handle_edit` drops `summary_json` (T037 / §6.2 / C-005)

**Location:** `src/specify_cli/widen/review.py` lines 317–325

**Problem:** Same root cause as Issue 1. The `source` value computed by `_determine_source()`
(which correctly returns `SLACK_EXTRACTION`, `MISSION_OWNER_OVERRIDE`, or `MANUAL`) is never
written. The `resolve_decision` call does not include `summary_json`.

**Fix required:** Pass `summary_json` in `_handle_edit`:
```python
dm_service.resolve_decision(
    repo_root=repo_root,
    mission_slug=mission_slug,
    decision_id=candidate.decision_id,
    final_answer=final,
    summary_json={"text": candidate.candidate_summary, "source": source},
    rationale=rationale,
    actor=actor,
)
```

---

## Blocking Issue 3 — Tests do not assert `summary_json` (rubber-stamp gap)

**Location:** `tests/specify_cli/widen/test_review.py` lines 323–327 and 402–404

`TestHandleAccept::test_calls_resolve_decision` asserts `kwargs["final_answer"]` and
`kwargs["decision_id"]` but does NOT assert `kwargs["summary_json"]`. Same gap in
`TestHandleEdit::test_major_edit_prompts_rationale` (asserts `rationale` but not `summary_json`).

These tests pass today because the implementation does not pass `summary_json` — they are
rubber-stamping the omission.

**Fix required:** After adding `summary_json` to the calls, add assertions:
```python
# In test_calls_resolve_decision:
assert kwargs["summary_json"]["source"] == SummarySource.SLACK_EXTRACTION
assert kwargs["summary_json"]["text"] == "S"  # matches candidate_summary

# In test_major_edit_prompts_rationale:
assert kwargs["summary_json"]["source"] == SummarySource.MISSION_OWNER_OVERRIDE
```

---

## Non-Blocking Observations (no action required)

### LLM protocol — reads stdin, not SaaS (C-008 satisfied)
`_read_llm_response` uses `sys.stdin` (or injectable `_stdin`). No SaaS endpoint calls.
Architecture constraint C-008 is correctly observed.

### §5.1 format — matches contract
The box header lines, `[DISCUSSION DATA]` section, message list, and JSON schema template all
match the §5.1 contract. The `markup=False, highlight=False` flags on `console.print` prevent
Rich from misinterpreting bracket characters in discussion messages. Correct.

### Timeout constant — env var respected
`SUMMARIZE_TIMEOUT = float(os.environ.get("SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT", "30"))`.
Correctly reads the env var at module load time. Tests inject a fast timeout via `_stdin` rather
than monkeypatching the env var (acceptable for unit tests where `_read_llm_response` is
patched at the integration level anyway).

### JSON parse robustness — adequate for §5.2
`_read_llm_response` collects lines until `}` appears alone on a line, then uses
`re.search(r"\{[^{}]*\}", raw, re.DOTALL)` with a fallback greedy match. Handles:
- Pure JSON (test: `test_valid_json_parsed`)
- JSON embedded in prose (test: `test_json_embedded_in_prose`)
- Multi-line JSON (test: `test_multiline_json`)
- Malformed JSON (test: `test_malformed_json_returns_none`)
- Empty stdin (test: `test_empty_stdin_returns_none`)

Code-fenced JSON (` ```json ... ``` `) is not directly tested but the regex is tolerant enough
to extract the `{...}` block inside a fence. Acceptable for V1.

### Provenance threshold math — correct
`edit_distance_fraction = 1.0 - ratio; if edit_distance_fraction > 0.30` is the correct
implementation of "ratio < 0.7 == >30% edit distance". The reviewer guidance examples
(`_determine_source("PostgreSQL.", "PostgreSQL with replicas.")` → OVERRIDE;
`_determine_source("PostgreSQL.", "")` → MANUAL) both pass.

### `[d]efer` rationale — not silently skipped
`_handle_defer` prompts with `"Rationale for deferral (required):"`. On KeyboardInterrupt/EOFError,
it substitutes the default string `"deferred during candidate review"` rather than silently
passing an empty rationale. §6.3 satisfied.

### Cancellation / KeyboardInterrupt / EOFError — correct
At the main `[a/e/d]` prompt, `KeyboardInterrupt` and `EOFError` return `None`, preserving
pending state. Tested by `test_keyboard_interrupt_at_prompt_returns_none` and
`test_eof_error_at_prompt_returns_none`.

### Full suite regression — 133/133 passing
`pytest tests/specify_cli/widen/ -v` → 133 passed, 2 skipped. No regressions.

---

## Summary of Required Fixes

1. Extend `decisions.service.resolve_decision` to accept and persist `summary_json`.
2. Pass `summary_json` in `_handle_accept` (T036).
3. Pass `summary_json` in `_handle_edit` (T037).
4. Add `summary_json` assertions to `test_calls_resolve_decision` and
   `test_major_edit_prompts_rationale` (and add a test that `minor_edit_uses_slack_extraction`
   also checks the source value).
