---
affected_files: []
cycle_number: 2
mission_slug: single-authority-topology-cleanup-01KVRJ6P
reproduction_command:
reviewed_at: '2026-06-23T08:35:26Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP09
review_artifact_override_at: "2026-06-23T08:48:24Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP09"
review_artifact_override_reason: "Cycle 2 passed: support.load_meta preserves missing→TaskCliError + malformed→raises; both arms tested; no caller relies on the removed {}"
---

# Review Cycle 1 — WP09 C2 sweep cluster 1: status/migration/coordination

**Reviewer:** reviewer-renata  
**Verdict:** CHANGES REQUESTED  
**Date:** 2026-06-23

---

## Summary

The implementation is structurally correct for 5 of the 6 owned sites, with sound contract-mapping, observable-return tests, warning-preservation, and scope discipline. One DoD violation blocks approval: the malformed-JSON arm of `task_utils/support.load_meta` was changed without a test asserting the new behavior.

---

## Blocking Issue

### [BLOCKER] `task_utils/support.py:376` — silent contract change on malformed JSON, unverified by test

**What changed:**  
Old `support.load_meta` called `json.loads(...)` with no surrounding try/except, so malformed JSON raised `json.JSONDecodeError` (propagated uncaught to the caller). New code delegates to `load_meta_strict(meta_path.parent)`, which uses `on_malformed="empty"` and returns `{}` on malformed JSON. Live-verified:

```
Old:  load_meta(malformed_path) → raises json.JSONDecodeError
New:  load_meta(malformed_path) → returns {}
```

**Why it blocks:**  
WP09 test-DoD requires: *"Contract test per distinct (missing, malformed) behavior present in the owned file."* `TestSupportLoadMetaContract` covers missing (→ TaskCliError), valid (→ dict), and BOM (→ dict). The malformed arm is entirely absent. This is a measurable DoD gap — not a style note.

**What is not required:**  
Reverting the behavior to raise. The new behavior (`{}` on malformed) is reasonable and `load_meta_strict` is documented to match the legacy contract. No production caller is known to rely on the malformed-raise. However, the test must assert the observable contract for the malformed arm — whichever behavior the implementation chooses.

**Required change:**  
Add a test asserting the observable return for malformed JSON in `TestSupportLoadMetaContract`. For example:

```python
def test_malformed_meta_returns_empty_dict(self, tmp_path: Path) -> None:
    """Malformed meta.json: load_meta returns {} (delegates to load_meta_strict/on_malformed=empty)."""
    meta_path = tmp_path / "meta.json"
    meta_path.write_bytes(b"\xef\xbb\xbf" + b"{bad json")  # BOM + malformed
    
    result = load_meta(meta_path)
    
    assert result == {}
```

This test would have failed against the old implementation (JSONDecodeError raised) and passes against the new one — making it a genuine red-first pin.

---

## Non-Blocking Observations (informational only — do NOT block approval)

### [INFO] `status/emit.py` — `_load_mission_id` debug log silently dropped

Old code logged `logger.debug(...)` on malformed. New `on_malformed="none"` silently absorbs to None with no log. The docstring update is consistent with the intent ("silent degradation"). Given debug-only severity and explicit docstring update, this is acceptable — recorded here for traceability.

### [INFO] `task_utils/support.py` — malformed→`{}` vs malformed→raise

The behavior change (JSONDecodeError→`{}`) is documented in `mission_metadata.load_meta_strict`'s docstring as reproducing the "legacy isinstance guard" for non-dict top levels, but `json.JSONDecodeError` is not a non-dict issue — it's a parse failure. The `load_meta_strict` docstring slightly misrepresents this: it says "A non-object top level is coerced to {} (matching the legacy isinstance guard), never raised" but the actual legacy contract raised on parse errors too. This is a documentation gap in `mission_metadata.py` (outside WP09's scope); record as follow-on debt. WP09's fix is: add the malformed test to pin the chosen behavior.

---

## Anti-pattern checklist verdict

| # | Item | Result |
|---|------|--------|
| 1 | Dead code | PASS — `load_meta_or_empty` has a live caller in `_mission_handle_matches` |
| 2 | Synthetic-fixture test | PASS — tests write real JSON/BOM bytes and call production code paths |
| 3 | Silent empty return | PASS with note — `_load_mission_id` malformed→None is documented in docstring |
| 4 | FR coverage | FAIL — malformed arm missing for `support.load_meta` |
| 5 | Frozen surface | PASS — no frozen files touched |
| 6 | Locked decision | PASS — no MUST NOT clause violated |
| 7 | Shared-file ownership | PASS — lane-e write scope exactly matches the 6 owned files |
| 8 | Production fragility | PASS — new raises under `on_malformed="raise"` are documented; lifecycle.py raises are pre-existing contract |

## Pre-existing failures (not grounds to reject)

The 5 `test_find_repo_root_*` failures in `tests/tasks/test_tasks_support.py` are confirmed pre-existing on the base branch (verified by stash+run). No new test regressions introduced by WP09.

## Static analysis

- `ruff check` — CLEAN on all 6 owned files and 4 test files.
- `mypy` — 8 errors in 3 files, all pre-existing on base branch (verified by stash). Zero new mypy issues introduced.
