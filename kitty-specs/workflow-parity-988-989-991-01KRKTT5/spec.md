# Spec: Workflow Parity Fixes 988/989/991

## Purpose

Operators and AI agents use `spec-kitty next --json`, `spec-kitty review --mode lightweight`, and `spec-kitty merge --dry-run` as the canonical readiness signals for whether a mission can move forward, ship, or merge. Today, each of these three surfaces silently disagrees with the underlying real command it is meant to preview:

- `next --json` can omit the concrete work package (WP) identity it could legitimately claim, making missions look "blocked" when the explicit implement action would succeed.
- `lightweight` review can emit a clean pass while skipping the dead-code scan whenever a modern mission lacks `baseline_merge_commit`, hiding missing release evidence behind a green verdict.
- `merge --dry-run` can preview a normal merge for a mission where the real merge would reject with `REJECTED_REVIEW_ARTIFACT_CONFLICT`, because dry-run skips the review-artifact consistency gate that real merge runs.

This mission restores parity so each preview surface reflects the real surface it claims to represent. After the fix, an operator can trust that a green dry-run, a green lightweight review, and an actionable `next --json` mean what they say.

## Intent Summary

- **Primary actors**: human operators driving the CLI; AI agents driving `spec-kitty agent` flows.
- **Trigger**: operator or agent invokes one of the three readiness surfaces against a mission.
- **Desired outcome**: each preview surface returns the same actionable verdict — including the same structured failure codes — that the real surface would return for that mission state.
- **Always-true rule**: a dry-run / preview / lightweight surface MUST NOT report a green or actionable result that the corresponding real command would not produce.
- **Canonical domain terms**: "work package" (WP), "mission", "lane", "baseline_merge_commit", "review cycle", "review artifact", "consistency gate", `REJECTED_REVIEW_ARTIFACT_CONFLICT`, `MISSION_REVIEW_MODE_MISMATCH`.

## User Scenarios & Testing

### Scenario A — Claimable WP visible in `next --json` (issue #988)

1. Operator runs `spec-kitty next --mission <slug> --json` against a mission whose state allows the explicit `agent action implement` to claim a WP.
2. The JSON payload reports `mission_state: implement`, `planned_wps >= 1`, `preview_step: implement`.
3. The JSON payload includes the concrete `wp_id` that `agent action implement` would claim, **not** `null`.
4. If selection is intentionally impossible (e.g. dependencies unsatisfied, all WPs already claimed by other agents), the JSON payload includes a structured reason explaining why selection was suppressed.

### Scenario B — Lightweight review with missing baseline_merge_commit (issue #989)

1. Operator runs `spec-kitty review --mission <slug> --mode lightweight` against a modern numbered mission whose `meta.json` has `baseline_merge_commit: null`.
2. The command does **not** emit a clean pass while silently skipping the dead-code scan.
3. Either the command exits non-zero with a structured diagnostic and remediation guidance, or it returns a verdict whose payload makes the missing dead-code scan explicit and non-passing.
4. Genuinely historical / legacy missions whose schema never carried `baseline_merge_commit` retain their existing behavior, with explicit messaging that names the legacy path.

### Scenario C — Dry-run merge surfaces review-artifact conflict (issue #991)

1. Mission fixture: `WP01` has lane `approved`; the latest review-cycle artifact for that WP has `verdict: rejected`.
2. Operator runs `spec-kitty merge --mission <slug> --dry-run --json`.
3. The dry-run output reports `REJECTED_REVIEW_ARTIFACT_CONFLICT` in both human and JSON form, exiting non-zero (matching real merge semantics) and pointing at the offending WP and review cycle.
4. The same gate fires for the human (non-JSON) dry-run output.
5. Real merge consistency tests continue to pass unchanged.

### Edge Cases

- A mission with multiple planned WPs where the first is blocked but a later WP is claimable: `next --json` should expose whichever WP `agent action implement` would actually claim, with a deterministic selection rule documented in the implementation.
- Lightweight review against a mission with `baseline_merge_commit` populated and a clean dead-code scan: behavior unchanged (still passes).
- `merge --dry-run` against a mission with all review cycles `approved` and no artifact conflicts: still previews a normal merge (no false positives introduced).

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `next --json` MUST serialize the concrete claimable `wp_id` whenever `spec-kitty agent action implement` against the same mission would auto-claim a WP. | Active |
| FR-002 | `next --json` MUST include a structured `selection_reason` (or equivalent named field) explaining why no `wp_id` was selected, whenever `wp_id` is omitted but `preview_step == "implement"`. | Active |
| FR-003 | `next --json` claimability discovery MUST share a single implementation path with the explicit `agent action implement` claim logic, with no divergent forking. | Active |
| FR-004 | `review --mode lightweight` MUST NOT emit a passing verdict for a modern numbered mission when `baseline_merge_commit` is `null` and the dead-code scan was therefore skipped. | Active |
| FR-005 | `review --mode lightweight` MUST emit a structured failure code (e.g. `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` or named-equivalent) with remediation guidance when it cannot run the dead-code scan on a modern mission. | Active |
| FR-006 | `review --mode lightweight` MUST preserve existing behavior for explicitly-legacy missions (those marked as pre-baseline schema), with a clearly-named diagnostic path. | Active |
| FR-007 | `merge --dry-run` MUST invoke the same review-artifact consistency gate as real `merge`, including the path that emits `REJECTED_REVIEW_ARTIFACT_CONFLICT`. | Active |
| FR-008 | `merge --dry-run --json` MUST surface `REJECTED_REVIEW_ARTIFACT_CONFLICT` in JSON output (under the same key real merge emits) when the gate fires. | Active |
| FR-009 | `merge --dry-run` human output MUST surface a clearly-labeled `REJECTED_REVIEW_ARTIFACT_CONFLICT` blocker when the gate fires. | Active |
| FR-010 | The three fixes MUST add regression tests that fail before the fix and pass after it, for the exact mission states described in scenarios A, B, and C. | Active |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The fixes MUST NOT degrade existing test pass rate on the touched modules. | 100% of pre-existing tests in `tests/specify_cli/cli/commands/test_merge.py`, `tests/post_merge/test_review_artifact_consistency.py`, `tests/specify_cli/cli/commands/test_review.py`, and `tests/specify_cli/cli/commands/review/test_mode_resolution.py` continue to pass. | Active |
| NFR-002 | Added regression tests MUST execute quickly to keep the focused suite snappy. | New tests for this mission complete in under 5 seconds aggregate when run with `pytest -q`. | Active |
| NFR-003 | The fixes MUST keep the dry-run / lightweight code paths CLI-safe in the absence of network access. | All new tests run with no network connectivity and no `SPEC_KITTY_ENABLE_SAAS_SYNC` requirement. | Active |
| NFR-004 | Structured diagnostic codes MUST be discoverable. | Every new error code is referenced at least once in docstrings or test assertion strings so `rg` can locate it. | Active |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Do not change the wire shape of `next --json` for non-implement states; only the implement-path payload may gain new fields. | Active |
| C-002 | Do not change the success path of `merge --dry-run`; the gate only fires when real merge would reject. | Active |
| C-003 | Do not modify behavior for `Priivacy-ai/spec-kitty#971`, `#771`, or `#825` (out of scope per start-here.md). | Active |
| C-004 | Reuse the existing `REJECTED_REVIEW_ARTIFACT_CONFLICT` and `MISSION_REVIEW_MODE_MISMATCH` error codes; do not invent parallel codes for the same conditions. | Active |
| C-005 | Keep the lightweight-review legacy path opt-in via mission schema signal, not by silent fallback. | Active |

## Domain Language

- **Work package (WP)**: a unit of mission scope identified by `WP##`; transitions through the 9-lane state machine documented in CLAUDE.md.
- **Claimable WP**: a WP that the `agent action implement` flow would auto-claim for the calling agent (typically lane `planned` with satisfied dependencies and no competing in-flight claim).
- **Baseline merge commit**: the commit SHA recorded in `meta.json#baseline_merge_commit` that anchors the dead-code scan diff for a mission.
- **Review cycle**: a `tasks/<WP>/review-cycle-N.md` artifact with a `verdict` (approved | rejected | pending).
- **Review-artifact consistency gate**: the preflight that verifies the latest review cycle's verdict is compatible with the WP's current lane before merge.
- **Lightweight review mode**: review verdict produced without re-running the heavy post-merge scans; intended for fast iteration but MUST NOT mask missing release evidence.

## Assumptions

- The existing real-merge consistency gate (`tests/post_merge/test_review_artifact_consistency.py`) already covers the canonical failure shape, so the dry-run fix is primarily a wiring/factoring change rather than a new gate.
- Modern missions are detectable from `meta.json` schema (e.g. presence of `mission_id` or `mission_number` keys, or schema version), so the lightweight-review fix can distinguish modern vs. legacy missions deterministically without a heuristic.
- `spec-kitty agent action implement --mission <slug> --agent <name>` already encapsulates the canonical claim algorithm; `next --json` can call into that algorithm in discovery-only mode rather than re-deriving it.

## Success Criteria

- **SC-001**: For a mission whose state lets `agent action implement` claim a WP, `next --json` reports the concrete `wp_id` in 100% of invocations (covered by regression test).
- **SC-002**: For a modern numbered mission with `baseline_merge_commit: null`, `review --mode lightweight` returns a non-passing structured verdict in 100% of invocations (covered by regression test).
- **SC-003**: For a mission with a `rejected` latest review-cycle artifact on an `approved` WP, `merge --dry-run` exits non-zero and emits `REJECTED_REVIEW_ARTIFACT_CONFLICT` in 100% of invocations across human and JSON output (covered by regression test).
- **SC-004**: All four pre-existing focused test files (test_merge.py, test_review_artifact_consistency.py, test_review.py, test_mode_resolution.py) continue to pass at 100%.

## Key Entities

- `MissionMeta` (`meta.json`): identity + schema fields including `mission_id`, `mission_number`, `baseline_merge_commit`, `mission_slug`.
- `WP` (work package): lane state + dependencies; lane history in `status.events.jsonl`.
- `ReviewCycle` (`tasks/<WP>/review-cycle-N.md`): YAML frontmatter with `verdict`.
- `NextJsonPayload`: the JSON document emitted by `spec-kitty next --json`.
- `MergeDryRunPayload`: the JSON document emitted by `spec-kitty merge --dry-run --json`.
- `LightweightReviewVerdict`: the structured result emitted by `spec-kitty review --mode lightweight`.

## Dependencies

- Existing real-merge review-artifact consistency gate implementation (referenced by `tests/post_merge/test_review_artifact_consistency.py`).
- Existing `agent action implement` claim algorithm.
- Existing `MISSION_REVIEW_MODE_MISMATCH` diagnostic path used by `post-merge` review.

## Out of Scope

- TeamSpace MVP scope.
- Issues assigned to `stijn-dejongh`, in particular `#971`, `#771`, `#825`.
- Refactoring of the broader `next`, `review`, or `merge` command surfaces beyond what is necessary to fix the three parity bugs.
- Changes to SaaS sync, hosted auth, or tracker behavior.
