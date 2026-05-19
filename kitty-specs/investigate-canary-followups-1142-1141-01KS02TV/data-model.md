# Phase 1 — Data Model

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`

This mission produces no persistent runtime data. The only "records" are markdown artifacts (an issue comment and a follow-up-row update). They are documented here as record shapes so each WP's Definition of Done has a precise reference.

## Entity: Investigation Outcome (one per issue)

| Field | Type | Source / Notes |
|---|---|---|
| `issue_number` | int | `1142` or `1141` |
| `mission_window_days` | int | `7` for #1142; `14` for #1141 (anchored to mission `created_at` = 2026-05-19) |
| `window_deadline` | ISO date | `2026-05-26` for #1142; `2026-06-02` for #1141 |
| `hypothesis_order` | string | `H1→H2→H3` for #1142; `H4→H3→H2→H1` for #1141 |
| `hypothesis_tested` | string | The label of the hypothesis whose evidence the comment carries (e.g., `H1`, `H4`, or `H1+H2+H3` if multiple ruled out) |
| `commands` | string (multi-line) | Exact commands run during the repro, captured verbatim from the operator shell |
| `evidence` | string (multi-line) or URL | Log excerpts (≥ the relevant ~20 lines around the assertion); attaching a gist URL is acceptable when logs are large |
| `conclusion` | enum | `CONFIRMED` / `RULED_OUT` / `INCONCLUSIVE_IN_WINDOW` |
| `recommendation` | enum | (#1141 only) `A_new_mission` / `B_patch_canary` / `C_small_fix` |
| `closing_action` | enum | `CLOSE_WITH_FIX_PATTERN` / `LEAVE_OPEN_WITH_NEXT_STEP` / `LEAVE_OPEN_PENDING_PR` |
| `linked_pr` | URL or null | Set when `closing_action == LEAVE_OPEN_PENDING_PR` |
| `follow_up_mission_slug` | string or null | Set when an H2-discovered defect spawns a separate 1-WP mission |

## Entity: Mission-Exception Follow-up Row (the cross-branch artifact)

The `## Follow-up` section of `mission-exception.md` has one row per deferred operator commitment from the parent mission. This mission updates **at most** two such rows (one for #1142, one for #1141). Each row before-state and after-state:

**Before** (deferred / open):

```
- Issue #1142 — investigate within 7 days. Owner: HiC. Status: deferred (Gate 3).
```

**After** (resolved):

```
- Issue #1142 — investigated 2026-05-XX. Result: H1 confirmed (stale canary venv). Closed with fix-pattern.
  Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1142#issuecomment-XXXXXXXXXX
```

The before/after diff is small and orthogonal to the rest of the file. The exact diff shape is captured in `contracts/follow-up-update-shape.md`.

## Invariants

- **I-001**: An `Investigation Outcome` record exists for #1142 by `2026-05-26` and for #1141 by `2026-06-02`, regardless of whether `conclusion == INCONCLUSIVE_IN_WINDOW`.
- **I-002**: When `conclusion == CONFIRMED` and the confirmed hypothesis is operator-process (e.g., #1142 H1), `closing_action == CLOSE_WITH_FIX_PATTERN` is mandatory — the trap must be named in the closing comment.
- **I-003**: When `follow_up_mission_slug` is set, the operator opens that mission via the standard `/spec-kitty.specify` flow — this mission MUST NOT in-line a code patch (constraint C-003).
- **I-004**: Every `Investigation Outcome` is mirrored to `mission-exception.md` `## Follow-up` (FR-007).

## State transitions

There is no runtime state machine; the only transitions are markdown edits:

```
[deferred row in mission-exception.md] → [resolved row in mission-exception.md]
                                       └─ links to →
                                          [substantive comment on GitHub issue]
                                       └─ optionally links to →
                                          [follow-up mission slug] or [linked PR]
```
