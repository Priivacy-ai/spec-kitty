---
affected_files: []
cycle_number: 1
mission_slug: slice-f-multi-context-extensibility-01KRX5C8
reproduction_command:
reviewed_at: '2026-05-18T15:22:11Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
review_artifact_override_at: "2026-05-18T16:11:51Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Cycle-2 approved: assertion tightened to require RichHandler's WARNING<2-spaces> format; real ATDD red→green verified (raw Python defaults at pre-bootstrap commit produce no WARNING prefix → assertion correctly fails). Cycle-1 substantive findings (bootstrap mechanics, unit tests, lane purity) carry forward unchanged. WP05's reframed value: deterministic Rich-formatted catalog-miss output (cosmetic UX), not RISK-3 fix (misdiagnosis confirmed)."
---

---

wp_id: WP05
reviewer: reviewer-renata
cycle: 1
verdict: REJECT
mission: slice-f-multi-context-extensibility-01KRX5C8
---

# WP05 Review Rejection — Cycle 1

## Verdict: REJECT

**Reason:** ATDD RED-on-first-run discipline violated. The RED commit test passes before the bootstrap is installed, which means AC-9's subprocess test does not prove what it claims to prove.

---

## RED-on-first-run investigation result: Case C/D (false-positive RED)

Running the integration test at the RED commit (`47389d40`) produces **1 passed**, confirming the test does NOT fail before the bootstrap.

The captured stderr at the RED commit shows:

```
src/charter/context.py:1627: CharterCatalogMissWarning: Charter catalog miss for styleguide:does-not-exist-typo; cause=missing_artifact
Charter catalog miss for styleguide:does-not-exist-typo; cause=missing_artifact
```

Both lines appear via Python's built-in defaults — no bootstrap required:

1. `warnings.warn(...)` in `emit_catalog_miss_warning` is handled by Python's default warning filter, which writes `source_file:line: WarningClass: message` to stderr once per (message, module, lineno) tuple.
2. `_LOGGER.warning(...)` in `emit_catalog_miss_warning` fires `logging.lastResort` — Python 3.2+'s built-in fallback handler that writes WARNING records to stderr when no handlers are configured.

**The test asserts `_CATALOG_MISS_MARKER ("Charter catalog miss") in combined_output`. This assertion passes before the bootstrap exists because Python's defaults already make both text strings visible in stderr.**

This is a hybrid Case C/D: Python's defaults coincidentally produce visible output that matches the assertion. The bootstrap's Rich-formatting is cosmetically useful but not load-bearing for this specific assertion.

---

## What the test must prove instead

Per C-011 (ATDD discipline), the test must fail before the bootstrap, and the fix must be the ONLY thing that makes it pass. Three acceptable paths:

### Option A — Assert on Rich-formatted output only

Add an assertion that the output contains Rich-specific markup or formatting that only `RichHandler` produces. Example: assert that the warning line contains the `WARNING` level label in the specific Rich format (e.g., `WARNING  Charter catalog miss…` with the double-space separator that RichHandler uses), which raw `lastResort` output does NOT produce.

Before bootstrap, `lastResort` writes: `Charter catalog miss for styleguide:does-not-exist-typo; cause=missing_artifact` (no level prefix).

After bootstrap with RichHandler, the format is: `WARNING  Charter catalog miss for styleguide:does-not-exist-typo; cause=missing_artifact` (level label + double-space).

**Assertion:**
```python
# Rich handler format: "WARNING  <message>" (double-space after level)
import re
assert re.search(r'WARNING\s{2,}Charter catalog miss', combined_output), (
    "Expected Rich-formatted WARNING record but got raw output. "
    "The bootstrap's RichHandler is required to produce this format."
)
```

This assertion fails before the bootstrap and passes after it — making the bootstrap load-bearing.

### Option B — Suppress warnings.warn and prove _LOGGER path

Disable the `warnings.warn` path in the subprocess by setting `PYTHONWARNINGS=ignore` in the test's `env`, then assert the marker still appears. Without the bootstrap, only `_LOGGER.warning` fires, and `lastResort` writes the marker. BUT — the assertion should also check Rich format to distinguish `lastResort` from `RichHandler`.

OR: Add `-W ignore::Warning` to the subprocess command, which silences `warnings.warn`. Then at RED commit the output would be EMPTY (lastResort still fires for `_LOGGER`). But wait — `lastResort` still fires. So the test would still pass.

The CORRECT version of Option B: suppress both `warnings.warn` AND disable `lastResort` in the subprocess before bootstrap. This can be done by setting `PYTHONWARNINGS=ignore` AND setting root logger level to CRITICAL in the subprocess env. But modifying subprocess env to simulate "no bootstrap" is circular — the bootstrap IS the fix.

**Recommended: Option A is cleaner and more focused.**

### Option C — Prove idempotency and no-double-print

The test could alternatively validate that with the bootstrap installed, `logging.captureWarnings(True)` suppresses the raw `warnings.warn` output (which would otherwise appear TWICE — once via warnings machinery and once via logging) and produces ONLY the Rich-formatted record. This directly proves the bootstrap changes behavior:

Before bootstrap: TWO lines in stderr (warnings machinery + lastResort).
After bootstrap: ONE line (Rich handler only, warnings.warn routed through logging).

Assertion:
```python
# After bootstrap: warning appears exactly ONCE (Rich format), not twice
import re
matches = re.findall(r'Charter catalog miss', combined_output)
assert len(matches) == 1, f"Expected exactly 1 occurrence (Rich-deduplicated), got {len(matches)}"
# AND it carries the Rich level prefix
assert re.search(r'WARNING\s+Charter catalog miss', combined_output), \
    "Expected Rich-formatted WARNING, not raw warning machinery output"
```

Before bootstrap: 2 occurrences of "Charter catalog miss" (warnings.warn + lastResort). This assertion fails.
After bootstrap: 1 occurrence (captureWarnings routes both through logging, deduplicated by Rich). This assertion passes.

---

## Required fix

1. Update `test_typoed_styleguide_produces_visible_stderr_warning` to assert on Rich-formatted output (Option A or C above) so the test FAILS at RED commit and PASSES only after the bootstrap.
2. Confirm the updated test FAILS at the RED commit (`47389d40`) — paste 3+ lines of actual stderr at RED to demonstrate.
3. Confirm the updated test PASSES at HEAD after the bootstrap.
4. No other changes required — bootstrap mechanics, unit tests, and ruff are clean.

---

## What is NOT blocking (informational)

- Bootstrap mechanics: correct. `logging.captureWarnings(True)` + idempotency guard + RichHandler at WARNING level.
- `src/specify_cli/__init__.py`: bootstrap called before Typer app. Correct placement.
- Unit tests (`test_logging_bootstrap.py`): 8/8 pass. Coverage is solid.
- Diff scope: exactly 4 files as expected. No lane purity violations.
- Ruff: clean.
- WP01–WP04 gates: all pass.
- Pre-existing failures (200): unrelated to WP05 (test files not modified by WP05).

---

## Summary

The bootstrap is genuinely useful and correctly implemented. The test is correctly structured as a subprocess test. The single defect is that the test's assertion is satisfied by Python's built-in defaults, making the RED commit a false-positive GREEN. Fix the assertion to require Rich-specific formatting, confirm it fails at RED, and resubmit.
