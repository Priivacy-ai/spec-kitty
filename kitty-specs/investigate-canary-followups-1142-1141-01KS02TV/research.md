# Phase 0 — Research

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`
**Date**: 2026-05-19

Investigation missions don't need technology-trade-off research; the stack is fixed by the parent mission. The four research tasks here are scoped to the unresolved questions the spec already flags.

## R1 — Parent-mission exception state (pin authoritative reference string)

**Decision**: The authoritative `## Follow-up` location is `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md`, which lives on branch `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` (and on the parent mission branch `kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07`). It is **not** on `origin/main` at the start of this mission.

**Rationale**: PR #1143 is the focused-PR carrying the parent mission's docs (mission-review.md, mission-exception.md, acceptance-matrix.json, canary-evidence/). Until #1143 merges, those files exist only on the PR branch. This mission's FR-007 update therefore lands on that PR branch (or its successor branch if #1143 has merged before the operator gets to FR-007).

**Alternatives considered**:
- Re-create the `## Follow-up` row on `main` via a fresh markdown — rejected: would duplicate, not update, the operator commitment.
- Wait for #1143 to merge first — rejected: would silently block this mission on an unrelated PR's review cycle, violating NFR-001's 7-day window.

## R2 — Canonical hypothesis bodies (snapshot before drift)

**Decision**: Treat the current GitHub issue bodies for #1142 and #1141 as canonical for hypothesis numbering. The mission spec references them by number (H1/H2/H3 for #1142; H1/H2/H3/H4 for #1141) but does not duplicate hypothesis text inline. The first action of WP01/WP02 is to fetch the issue body via `gh issue view <n>` and pin a snapshot under `research/`.

**Rationale**: Issues are mutable; pinning a snapshot at WP start eliminates drift risk if a third party edits the body mid-investigation.

**Alternatives considered**:
- Copy hypotheses into spec.md verbatim — rejected: NEXT-AGENT-HANDOFF.md already showed this is brittle; the issues remain authoritative.

## R3 — WP01 predicate canonical source

**Decision**: The WP01 predicate that #1142 H2 walks emitters against is enforced in `src/specify_cli/status/lifecycle_events.py`, lines 229–236:

```python
event_type = envelope.get("event_type")
payload = envelope.get("payload")
if not isinstance(event_type, str) or not isinstance(payload, Mapping):
    return None

aggregate_type = envelope.get("aggregate_type")
if not isinstance(aggregate_type, str):
    return None
```

The downstream emitters at lines 410 (`Project`), 459 (`Mission`), and 521 (`Mission`) all pass an explicit `aggregate_type` literal. The WP01 acceptance contract added a stronger predicate at the canary side: `aggregate_type == "Mission"` AND `event_type` non-empty.

**Rationale**: #1142 H2 needs one reference walk. Pinning the predicate source line (and the three downstream emitter call sites) means the H2 procedure is mechanical: open the five emitter files named in spec.md and check each `aggregate_type=` call against the predicate.

**Emitter inventory for H2 walk**:
- `src/specify_cli/status/lifecycle_events.py` — primary; lines 410, 459, 521 already audited above.
- `src/specify_cli/invocation/propagator.py`
- `src/specify_cli/dossier/` (package)
- `src/specify_cli/next/_internal_runtime/engine.py`
- `src/specify_cli/retrospective/events.py`

**Alternatives considered**:
- Restate the predicate in the spec — already done implicitly; pinning the source line is cheaper than maintaining a duplicate.

## R4 — Cross-branch update mechanics

**Decision**: FR-007 (`mission-exception.md` `## Follow-up` update) uses this sequence:

```bash
# From the repo root (worktree on this mission's branch is fine; the edit branch is separate)
git fetch origin
git checkout kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main
git pull --ff-only

# Edit kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md
# Section: ## Follow-up
# Rewrite the deferred commitment row(s) per follow-up-update-shape.md

git add kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md
git commit -m "Record outcome of #1142 / #1141 follow-up commitment"
git push origin kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main
```

**Conditional branch — PR #1143 has merged**: If `git rev-parse origin/kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` fails (branch deleted post-merge) or PR #1143 shows `state=MERGED`, the file is now on `main`. In that case:

```bash
git checkout main
git pull --ff-only
git checkout -b chore/record-canary-followup-outcome
# Edit the same path on main now
# Commit + push + open PR against main
```

**Rationale**: Documents the only two real paths (PR branch still open / PR branch merged) without overspecifying intermediate states.

**Alternatives considered**:
- Always merge #1143 first — rejected: couples this mission to a separate review cycle.
- Always go through `main` — rejected: would push a partial commitment-resolution before the parent mission's docs land, creating a stranded edit.
