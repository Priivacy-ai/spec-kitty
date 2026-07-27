# Investigation Outcome — Issue #1141

**Schema**: data-model.md "Investigation Outcome"
**Investigator**: claude:opus-4-7:researcher-robbie:implementer (orchestrated by HiC)
**Investigation date**: 2026-05-19

| Field | Value |
|---|---|
| `issue_number` | 1141 |
| `mission_window_days` | 14 |
| `window_deadline` | 2026-06-02 |
| `hypothesis_order` | H4 → H3 → H2 → H1 (cheapest-first per spec.md C-004) |
| `hypothesis_tested` | H4 ruled out + H3 ruled out + H2 partially ruled out (force-contract dimension); H1 LIKELY (most plausible) |
| `commands` | See sections below |
| `evidence` | `research/h4-evidence-1141.md`, `research/h3-evidence-1141.md`, `research/h2-evidence-1141.md`, `research/h1-evidence-1141.md`, `research/issue-1141-snapshot.json` |
| `conclusion` | LIKELY — H1 (CLI regression — rollback row does not reach offline queue) |
| `recommendation` | A — open a 1-WP follow-up mission to bisect, instrument, and fix |
| `closing_action` | LEAVE_OPEN_WITH_NEXT_STEP |
| `comment_url` | https://github.com/Priivacy-ai/spec-kitty/issues/1141#issuecomment-4488224564 |
| `posted_at` | 2026-05-19T13:13Z (within 14-day window; window deadline 2026-06-02) |
| `linked_pr` | n/a |
| `follow_up_mission_slug` | TBD — to be filed after this mission merges |

## Summary of findings (in order tested)

1. **H4 (fixture state error)** — RULED OUT. The captured failure quotes `from='for_review' to='in_review'` in the peeked row, which is itself a transition INTO `in_review`. Its presence in the queue proves the fixture reached `in_review` as designed. See `h4-evidence-1141.md`.
2. **H3 (sequencing race)** — RULED OUT. The peek runs in a subprocess after the `move-task` subprocess has exited; the SQLite WAL has settled. A race would manifest as intermittent results, not the deterministic mismatch the issue body describes. See `h3-evidence-1141.md`.
3. **H2 (canary drift)** — PARTIALLY RULED OUT. The canary's `force=True + reason` contract is the current spec-kitty contract (`tasks.py:1751-1759` matches `spec-kitty-events#32`). The captured failure is at scenario 4 **line 543** (the from/to_lane shape assertion), which is BEFORE the force-contract check. The contract-drift FR-018 path is irrelevant; the row is simply not present. See `h2-evidence-1141.md`.
4. **H1 (CLI regression)** — LIKELY. The end-to-end emission pipeline (`tasks.py:1751` → `emit_status_transition` → `_saas_fan_out` → `fire_saas_fanout` → `_saas_fanout_handler` → `emit_wp_status_changed` → `OfflineQueue`) is fully present in `origin/main`, but `fire_saas_fanout` swallows all handler exceptions silently (`adapters.py:121-126`). The most plausible root cause is a silent fan-out failure (DB lock, schema mismatch, daemon-ensure error) on the rollback emission specifically. Three sub-hypotheses outlined in `h1-evidence-1141.md`. Full bisect requires a trusted-runner workstation with live SaaS auth; out of scope for this investigation mission per C-003.

## Why this WP cannot fix the bug (C-003)

Per `spec.md` Constraint C-003: "This mission MUST NOT pre-commit to landing a code patch. If hypotheses converge on a clean-install fix-pattern (no code change), that is an acceptable terminal state for #1142."

For #1141, H1 has not converged on "no code change" — it has converged on "we need code instrumentation + a bisect in a trusted-runner environment." That is itself a follow-up mission scope (A), not a closing fix-pattern.

## Recommendation: A — new mission

Proposed follow-up mission scope:

| Step | Action |
|---|---|
| 1 | Add an info-level logging breadcrumb at `fire_saas_fanout` entry (`adapters.py:112`) and between `_saas_fanout_handler` invocation and `emit_wp_status_changed` so silent fan-out failures surface in operator logs. |
| 2 | Add a unit test in `tests/specify_cli/status/test_emit_backward_transition.py` that asserts a backward `in_review → planned` transition writes exactly one new row to a temp OfflineQueue. Use the existing test harness from `test_emit_status_transition.py`. |
| 3 | Run scenario 4 from a trusted-runner workstation with the new logging enabled; capture which handler step the rollback fails at. |
| 4 | Land the targeted fix (likely a guard or retry around the silent-failure source) and re-verify scenario 4 turns green. |

Estimated: 1 WP, 4 subtasks, ~1–2 operator-days. Same shape as the original three CLI bugs (#1122/#1123/#1124).

## Hypothesis-by-hypothesis evidence references

- `research/h4-evidence-1141.md` (fixture state)
- `research/h3-evidence-1141.md` (sequencing race)
- `research/h2-evidence-1141.md` (canary drift)
- `research/h1-evidence-1141.md` (CLI regression — most likely)
