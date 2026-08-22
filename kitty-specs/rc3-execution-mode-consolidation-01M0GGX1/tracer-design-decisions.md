---
type: explanation
updated: 2026-08-21
---

# Tracer: design decisions (M7 ExecutionMode consolidation)

## D1 — Three enums do NOT unify

Enum #1 (ownership, "what a WP produces") and #2/#3 (worktree-vs-direct) are orthogonal
axes. Merging #1 into the others would recreate the exact `code_change` collision the
mission removes. Only #2/#3 share an axis and #3 (external, live) already owns it, so #2
is **deleted**, not merged. Confirmed against the spec's locked decisions.

## D2 — New class name: `WorkProductKind`

Chosen over `WorkPackageOutputKind` (needlessly long for the same meaning). Reads as
"the kind of product a WP yields", pairs naturally with `code_change` / `planning_artifact`.
Verified collision-free (`git grep WorkProductKind` → none on the mission base).

## D3 — No back-compat alias

Leaving `ExecutionMode = WorkProductKind` in `ownership.models` would keep the clashing
name resolvable in-repo, violating FR-003/AC-3 ("no name collision remains; any live
`ExecutionMode` resolves only to the external class"). Chose the charter's
canonical-source-unification path: rename ALL consumers, old name must not resolve.

## D4 — Guard keys on the footgun's SHAPE, not a member set (M6 headroom)

`test_execution_mode_no_redrift.py` asserts (a) no `class ExecutionMode` under `src/`,
(b) no in-repo enum pairing a `worktree` member with a `code_change` member (AST scan),
(c) the retired symbol is absent from `mission_runtime.__all__`. It deliberately does NOT
pin `WorkProductKind`'s member set, so M6 (#3590) can ADD a non-diff completion-mode member
without touching the guard (AC-5). A regression test proves the permissiveness explicitly.
The AST member-value scan catches a *renamed* re-introduction of the dead enum, which a
name-only check would miss.

## D5 — Retirement is a governance-gate change, not a bare delete

Enum #2 was named in the canonical-surface ADR (2026-06-07-1) and listed in the surface
test's `_PUBLIC_SURFACE`. Both were updated in WP01 (the ADR's public-API listing amended +
dated note; the surface-list entry removed) rather than treated as collateral — even though
the surface list turned out to be a vacuous pin (see tooling-friction F2).

## D6 — Ownership-map leeway over a strict, wrong map

Planning under-scoped WP02's `owned_files` (truncated grep, F3). Rather than re-run the full
finalize on an in-progress mission, widened `owned_files` to the true rename surface (no
overlap with WP01) and recorded it — applying the charter's "no-overlap is the real guard"
principle. The external `spec_kitty_events` enum in `tasks_transition_core.py` is explicitly
out of the rename surface and untouched.

## D7 — Word-boundary rename to protect compound identifiers

The `\bExecutionMode\b` → `WorkProductKind` transform intentionally leaves compound test
class names (`TestExecutionModeDefaults`, `TestInferExecutionMode`, …) and the unrelated
lowercase `execution_mode` / `infer_execution_mode` identifiers untouched. Those cosmetic
test-class labels were left as-is (renaming them is churn with no domain meaning).
