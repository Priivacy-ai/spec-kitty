---
affected_files: []
cycle_number: 2
mission_slug: untrusted-path-containment-hardening-01KVFTFV
reproduction_command:
reviewed_at: '2026-06-19T13:41:37Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
review_artifact_override_at: "2026-06-19T13:47:33Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Reconcile lane→primary; reviewer-renata APPROVED WP03 cycle 2 (ruff/mypy 0, 48 tests, one-line UP037 fix)"
---

# WP03 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED** — one NEW ruff gate failure on a touched test file.
Everything else (the 5 fixes, all dispositions, the deferrals, the pre-existing
failure claim) verified PASS. This is a one-line fix.

## BLOCKING

**Issue 1 — NEW ruff `UP037` error on new WP03 code (DoD: "ruff + mypy clean").**

`ruff check tests/review/test_arbiter.py` fails on a line this WP added:

```
UP037 [*] Remove quotes from type annotation
  --> tests/review/test_arbiter.py:790:33
      def _make_decision(self) -> "ArbiterDecision":
```

`ArbiterDecision` is imported at module top (not a forward reference), so the
quotes are unnecessary and ruff flags it. The base mission branch passes ruff
cleanly here, so this is NEW-code breakage, not pre-existing.

**Fix:** unquote the annotation — `def _make_decision(self) -> ArbiterDecision:`
(autofixable with `ruff check --fix tests/review/test_arbiter.py`). Re-run
`ruff check` on all touched files and confirm zero issues before re-requesting
review.

## What I verified PASS (no action needed — recorded for the audit trail)

**The 5 fixes are real + mutation-killing.** All route the segment through
`assert_safe_path_segment` (fail-closed `ValueError`) before the join/mkdir:
`drift_detector.py:209/233`, `snapshot.py:140/160`, `decision_log.py:99`,
`mission_state.py:1049` (quarantine path, meta-sourced slug), `arbiter.py:483`
(wp_id before `mkdir`). 39 negative tests pass.

Mutation-verified 2 (guard neutralised → revert):
- `arbiter.py` wp_id guard neutralised → 5/6 traversal cases FAIL (guard kills mutant). Reverted.
- `mission_state.py` meta-slug guard neutralised → repair returns `updated` not
  `error`, test FAILS. Reverted.

**Laziness check — dispositions all hold against the code:**
- `surface_resolver.py:429,434` — `mission_slug` composed ONLY inside the
  `raise StatusReadPathNotFound(...)` payload; no open/write. `unreachable` ✔
- `_read_path_resolver.py:438` — `assert_safe_path_segment(mission_slug)` at
  :437 precedes the join. already-seamed ✔
- `arbiter.py:387,520` — `.exists()`+`.glob()` read-probes; traversal fails
  `.exists()`. `unreachable` ✔
- `post_merge/review_artifact_consistency.py:59` — `.is_dir()`+`iterdir()`
  prefix filter; no raw-join open. `unreachable` ✔
- `review/cycle.py:225` — all 3 segments validated via `_validate_segment`
  (→ seam) before join; result `.resolve()`'d + existence-gated. already-seamed ✔

**4 deferred CLI-arg sinks — deferral is LEGITIMATE (not dodged):**
`mission.py:312`, `tasks.py:1911`, `decision.py:464`, `merge.py:1055`. None are
in WP03's `owned_files`, none are in the WP03 prompt's named-candidate list, and
all four are read-only probes (mission.py: existence-gated candidate list;
tasks.py: `.exists()`; decision.py: `load_meta` read; merge.py: `.exists()` +
`read_text`). No mkdir/write. Correctly out of scope for WP03.

**snapshot.py out-of-owned fix** — sound; `snapshot.mission_slug` is on-disk
content-derived; guard added before `mkdir`+write. Leeway justified.

**Pre-existing failure confirmed:**
`tests/review/test_baseline.py::TestCoverageEdgeCases::test_find_repo_root_walks_up`
fails on the lane, but both `review/baseline.py` and `test_baseline.py` are
byte-identical to the base mission branch (empty WP03 diff). Environmental
(`_find_repo_root` walks up and finds a `.git` at/above `/tmp`). NOT introduced
by WP03.

**Anti-pattern checklist:** 1 Dead code N/A · 2 Synthetic-fixture PASS (tests
invoke real sinks) · 3 Silent empty return N/A · 4 FR coverage PASS · 5 Frozen
surface PASS · 6 Locked decision PASS · 7 Shared-file ownership PASS · 8
Production fragility PASS (all new `raise`s are fail-closed traversal guards).
