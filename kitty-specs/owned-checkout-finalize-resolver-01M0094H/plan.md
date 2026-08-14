# Implementation Plan: Finalize owned-checkout mission resolver

## Technical Context

`locate_project_root()` intentionally returns the primary checkout from a linked
worktree. That is correct as a repository/topology anchor, but
`finalize-tasks` currently uses it as the mission-artifact root as well. The
result is a split-brain: a caller-owned mission created only in a linked
worktree is invisible to finalization.

The fix introduces one immutable operation context with separate repository and
mission-anchor roots. Candidate indexing is read-only and fail-closed when
allowed surfaces disagree on the mission identity. The finalizer consumes this
context and passes the mission anchor through placement/status/read seams.

## Design

1. Add `MissionOperationContext` and conflict diagnostics in
   `specify_cli.missions.operation_context`.
2. Thread `mission_anchor_root` through the shared mission-runtime placement
   seam and workspace/status readers without removing existing compatibility
   seams.
3. Resolve the context at the `finalize-tasks` boundary. Keep legacy mocked or
   primary behavior as a narrow fallback only when no indexed mission exists.
4. Add a structural census guard for covered lifecycle consumers and targeted
   integration tests for caller-owned, managed, foreign, and conflicting roots.

## Verification gates

- Red-first operation-context regression against current upstream.
- Targeted operation-context and finalizer tests.
- `finalize-tasks --validate-only` on a mission present only in the owned
  checkout; primary tree must remain byte-identical.
- Existing primary/managed topology tests remain green.
- Architectural census and full relevant test slice pass before canary build.

## Non-goals

- No changes to mission creation ownership semantics.
- No removal of unrelated legacy path helpers.
- No direct edits, reset, or merge in primary `main`.
