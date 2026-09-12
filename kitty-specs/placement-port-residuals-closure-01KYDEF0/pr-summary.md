# Placement-Port Residuals Closure

> Reviewer summary for PR `placement-port-residuals-closure`. Written for a reader
> who has **not** followed the mission — the background below is enough to review
> the diff without extra context.

## Background (for a non-maintainer reader)

Spec Kitty writes each mission's files to one of two homes ("partitions"):

- **PRIMARY** — stable planning & metadata (spec, plan, and the `status_phase`
  key that gates the whole status model). Lives on the mission's planning branch.
- **COORD** — lifecycle surfaces (the append-only status event log, notes, traces)
  routed onto a separate *coordination* branch.

A single component — the **placement port** — is supposed to be the one authority
that answers "where does this artifact go?". A previous, already-merged change
(PR #2920) established that port. Its post-merge review found that a few writers
still wrote directly to a directory the caller handed them, **bypassing the port**.
They happened to be correct only because every current caller passed the right
directory — the guarantee was true by *caller discipline*, not *enforced by the
port*. A future caller passing the wrong directory would silently write to the
wrong partition with nothing to catch it. PR #2920 also merged with six
gate/contract tests red (deliberately deferred).

This PR closes those residuals: it makes partition-correctness **enforced by the
port**, and returns the deferred gates to green.

## Summary

- Route the placement-sensitive writers through the placement port and **fail
  closed** (raise, write nothing) if the resolved home disagrees with the caller —
  converting coincidental correctness into an enforced invariant.
- Consolidate three hand-rolled "resolve write target, else degrade" copies into a
  single shared helper, and guard a best-effort read against a deleted coordination
  branch.
- The six gate/contract reds the prior PR deferred were **already fixed** by other
  changes that landed in the interim; this PR verifies them green and records that.

## Why Now

PR #2920's 4-lens post-merge review deferred five residual weaknesses (tracked as
issues **#2923** and **#2924**) because each touches a load-bearing surface — the
sole `status_phase` writer, the legacy-cutover path, or a best-effort degrade
surface — and needed corpus-wide validation too risky to fold into that PR. A
sixth item (**#2926**) was an arch-gate red at the same call site. Left open, the
placement guarantees stay "true by luck" and the gates stay red. This mission
closes all of them as one cohesive unit.

## What This PR Does

**Enforce partition-correctness (Part A):**
- `_flip_phase` — the *only* code that writes `status_phase` — now resolves its
  write target through the port and raises a typed `PlacementMismatchError`
  (writing nothing) if the resolved PRIMARY home ≠ the directory it was handed.
  It degrades gracefully only when the *resolver itself* can't run, never to mask a
  genuine wrong-partition write. (FR-001)
- The two-target legacy cutover now reads `tasks/` frontmatter from the PRIMARY leg
  while the status **event write stays on COORD** — closing a read/write-partition
  mismatch without moving the event write. (FR-002)

**Remove duplication & harden degrade paths (Part B):**
- One kind-parameterized `resolve_write_target_or_degrade` helper (in the
  `mission_runtime` package) replaces three near-identical hand-rolled copies;
  each caller keeps its own degrade policy (one fails open, one fails closed, one
  is a pre-gate). Zero verbatim clones remain. (FR-005)
- The retrospective's trace loader now degrades to an empty list if the
  coordination branch was deleted, instead of crashing — scoped to that one call
  site. (FR-006)

**Tighten the gate & return deferred reds to green (Part C):**
- The write-side placement scan no longer blanket-exempts the `migration/`
  subtree, restoring true "any module" precision (proven by a red-first synthetic
  bypass); a separate, intentional resolver-walker carve-out is untouched. (FR-003/004)
- The remaining deferred gate/contract reds (raw-path use, the CLI golden-command
  contract, the merge committed-file set, and a guard-capability allow-list) were
  **already green on the current base** — fixed by other PRs that landed between
  the prior PR and this branch's rebase. Verified in-mission. (FR-008–FR-012)

## Effect on Existing Projects

- **Runtime / compatibility:** Behavior-preserving for all current callers. The one
  intended behavior change is a bug fix: a caller-supplied coordination branch that
  was previously silently discarded in the bootstrap window is now honored. The new
  fail-closed raise only fires on a genuine wrong-partition write, which no current
  caller produces.
- **Upgrade / migration:** None. No data format, config, or CLI surface changes;
  purely internal routing + a stricter internal gate.
- **Operator / reviewer impact:** A future writer that targets the wrong partition
  now fails loudly instead of silently — a safety improvement. The write-side gate
  is stricter for the `migration/` subtree.

## Validation

- [x] Red-first per fix — each behavioral fix ships a test proven to fail on the
      pre-fix code and pass after (verified by reverting the product file).
- [x] `ruff` and `mypy --strict` clean on all changed source.
- [x] Each of the 7 work packages independently reviewed and approved
      (implement=Sonnet / review=Opus; a genuine two-party cycle, including one
      rejection→re-implementation for a real regression that was caught and fixed).
- [x] Full `tests/architectural/` suite + terminology guard run locally on the
      rebased tip; pre-merge aggregate review (architect + SSOT lenses) on the
      combined diff.
- [x] Backward compatibility considered (see Effect above).
- [x] Follow-up work called out (see Follow-ups).

## Tickets / Contracts

| Ticket | Relationship |
|--------|--------------|
| #2931 | Parent epic for this mission |
| #2923 | Closed — Part A (birth-cutover placement-port hardening: FR-001/002/003/004) |
| #2924 | Closed — Part B (degrade-path + best-effort-read hygiene: FR-005/006) |
| #2926 | Closed — arch gate MERGE_BOOKKEEPING allow-list at the coord-seed call site (FR-008/012); verified already-green |
| #2932 | Closed — Part C golden-contract/raw-path/merge-committed-set (FR-009/010/011); verified already-green |
| #2920 | Parent PR whose residuals this closes (merged) — not re-fixed here |
| #2921 | Deferred (out of scope, separate mission) — `repair_lane_mismatch` frontmatter fix |
| #2922 | Deferred (out of scope, separate mission) — read-side whack-a-read (~50 modules) |

## Mission Artifacts

- Spec: `kitty-specs/placement-port-residuals-closure-01KYDEF0/spec.md`
- Plan: `kitty-specs/placement-port-residuals-closure-01KYDEF0/plan.md`
- Tasks: `kitty-specs/placement-port-residuals-closure-01KYDEF0/tasks.md`
- Analysis: `kitty-specs/placement-port-residuals-closure-01KYDEF0/analysis-report.md`
- Issue matrix: `kitty-specs/placement-port-residuals-closure-01KYDEF0/issue-matrix.md`
- Reviews: `kitty-specs/placement-port-residuals-closure-01KYDEF0/tasks/WP*/review-cycle-*.md`
- PR summary: this file (`pr-summary.md`)

## Follow-ups

- **#2921** — `repair_lane_mismatch` frontmatter-corruption fix (separate mission).
- **#2922** — read-side whack-a-read remediation across ~50 modules (separate mission).
- **Pre-merge squad NOTEs** (non-blocking; no live defect — to be filed as one follow-up under epic #2931):
  1. `write_target_degrade.py` fail-closed branch: when `resolve_placement_only` raises a
     *caught-set* exception with `degrade_ref is None`, the helper converts it to
     `ActionContextError(FEATURE_CONTEXT_UNRESOLVED)` rather than propagating the original.
     Immaterial in practice (both callers catch broadly) — a one-line docstring clarification
     would remove the ambiguity.
  2. `_flip_phase` FR-001 fail-close compares `resolve_artifact_surface(...).path` against
     `canonicalize_feature_dir(...)`; correctness depends on both normalizers producing
     identically-formed paths. No live defect (tests exercise the match case), but a defensive
     test pinning the normalization contract would harden it.
