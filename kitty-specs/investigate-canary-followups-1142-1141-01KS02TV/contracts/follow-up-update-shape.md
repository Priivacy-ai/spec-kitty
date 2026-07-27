# Contract: Mission-Exception Follow-up Update Shape

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`
**Satisfies**: FR-007
**File**: `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md`
**Branch (default)**: `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main`
**Branch (fallback if PR #1143 merged)**: `main` via a fresh PR (see research.md R4)

## What changes

Only the `## Follow-up` section. No other section is touched. Surrounding sections (`## Decision`, `## Rationale`, `## Conditions`, etc.) remain byte-identical.

## Diff shape — deferred → resolved row

**Before**:

```markdown
## Follow-up

- Issue #1142 — investigate within 7 days. Owner: HiC. Status: deferred (Gate 3).
- Issue #1141 — investigate within 14 days. Owner: HiC. Status: deferred (Gate 3).
```

**After (both resolved, illustrative)**:

```markdown
## Follow-up

- Issue #1142 — investigated 2026-05-19. Result: H1 confirmed (stale canary venv). Closed with fix-pattern.
  Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1142#issuecomment-XXXXXXXXXX
  Outcome record: kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/outcome-1142.md
- Issue #1141 — investigated 2026-05-22. Result: H4 ruled out, H3 confirmed (sequencing race).
  Recommendation: B (patch canary).
  Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1141#issuecomment-XXXXXXXXXX
  Outcome record: kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/outcome-1141.md
```

## Row schema (required sub-elements)

Each resolved row MUST carry:

1. Issue link (`#NNNN`)
2. Date investigated (ISO date)
3. Result phrase referencing the hypothesis label(s) (e.g., `H1 confirmed`, `H4 ruled out, H3 confirmed`)
4. Comment URL on the issue
5. Local outcome-record path (the markdown the operator produced under `research/`)
6. (#1141 only) Recommendation letter A/B/C

A row MAY also carry:

- `Follow-up mission`: `<slug>` (when an H2 finding spawns a separate mission)
- `Linked PR`: `<url>` (when a patch is delivered via PR before the comment is finalized)

## Inconclusive-in-window resolution

If the window expires without a confirmed/ruled-out outcome, the row becomes:

```markdown
- Issue #1142 — partial investigation 2026-05-26. Result: H1 ruled out. H2 ongoing. Status: inconclusive in window.
  Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1142#issuecomment-XXXXXXXXXX
  Next operator: continue H2 walk per spec.md.
```

This shape MUST be used when `conclusion == INCONCLUSIVE_IN_WINDOW` so the operator commitment is still discharged (FR-002 / FR-006) even when the investigation continues.

## Commit message convention

```
Record outcome of #<issue> follow-up commitment

Investigation: investigate-canary-followups-1142-1141-01KS02TV
Result: <one-line summary>
```
