---
type: explanation
updated: 2026-08-21
---

# Research: M7 — ExecutionMode / enum consolidation

> Phase-0 research for mission `rc3-execution-mode-consolidation-01M0GGX1`.
> Re-verified against `upstream/main` @ `c44b4bcf87` on 2026-08-21 (the spec's
> original audit by analyst-annie was against an earlier `main`; every citation
> below was re-grounded on the current HEAD before planning).

## Decision 1 — Do NOT unify the three enums

**Decision.** Keep three distinct types. Retire the dead one (#2), rename the live
in-repo one (#1), leave the external one (#3) as the sole surviving `ExecutionMode`.

**Rationale.** The three classes model three *orthogonal* axes. Merging enum #1
(“what a WP produces”) into the worktree-vs-direct axis would recreate the exact
`code_change` token collision this mission exists to remove. Only #2 and #3 share
an axis, and #3 (external, live) already owns it — so #2 is deleted, not merged.

**Evidence.**

| # | Type | Location (HEAD `c44b4bcf87`) | Members | Axis | Status |
|---|------|------------------------------|---------|------|--------|
| 1 | `specify_cli.ownership.models.ExecutionMode` (`StrEnum`) | `src/specify_cli/ownership/models.py:21` | `code_change` / `planning_artifact` | What a WP **produces** | LIVE, widely consumed |
| 2 | `mission_runtime.context.ExecutionMode` (`enum.Enum`) | `src/mission_runtime/context.py:42` | `worktree` / `code_change` | How context **resolves** | Members DEAD; surface-pinned |
| 3 | `spec_kitty_events.status.ExecutionMode` (`str, Enum`) | external PyPI (`spec_kitty_events`) | `worktree` / `direct_repo` | Status-payload execution mode | LIVE, external |

The collision: in #1, `code_change` is the opposite of `planning_artifact`
(“this WP changes code”). In #2, `code_change` is the opposite of `worktree`
(“resolves against an in-place checkout”). Same token, orthogonal meanings — a
reader of `ExecutionMode.code_change` cannot tell which axis they are on.

## Decision 2 — Delete enum #2, don't rename it

**Decision.** Remove `mission_runtime.context.ExecutionMode` entirely, plus its
re-export and its architectural-surface pin, and record the retirement in the ADR.

**Rationale.** Zero member consumers → renaming a dead symbol is pure churn.
Because it is surface-declared, deletion is a **governance-gate change**, not a
bare delete: the arch surface test and the ADR are in-scope, not collateral.

**Evidence (re-verified on HEAD).**
- No importers of the symbol outside `src/mission_runtime/`; no `.WORKTREE` /
  `.CODE_CHANGE` member references anywhere in `src/`.
- Exported: `src/mission_runtime/__init__.py:32` (import) and `:82` (`__all__`).
- Pinned: `tests/architectural/test_mission_runtime_surface.py:53`.
- Governed by: `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md`.

## Decision 3 — Rename enum #1, keep its member string values

**Decision.** Rename the class from `ExecutionMode` to a distinct name (candidate:
`WorkProductKind`). Keep member string values `code_change` / `planning_artifact`
so WP frontmatter stays wire-compatible. Update every consumer.

**Rationale.** Once #2 is gone, the class *name* is the residual footgun (it
clashes with the external #3). Renaming the class — not the values — removes the
clash while protecting on-disk WP frontmatter. A missed reference is a compile/mypy
break (loud), never a silent behavior change.

**Evidence — consumers to update (re-verified on HEAD).**
- `src/specify_cli/core/worktree.py`
- `src/specify_cli/workspace/context.py`
- `src/specify_cli/ownership/inference.py`
- `src/specify_cli/ownership/validation.py`
- `src/specify_cli/ownership/__init__.py`
- `src/specify_cli/lanes/implement_support.py`
- `src/specify_cli/lanes/compute.py`
- `src/specify_cli/cli/commands/agent/mission_parsing.py`

(Exact line numbers are re-derived in the plan phase from a fresh `git grep`, not
copied from the spec, because line numbers drift.)

## Decision 4 — Reserve headroom for M6, guard against re-drift

**Decision.** Write the rename and a new re-drift guard test so that M6 can later
ADD a non-diff completion-mode member to the renamed enum **without modification**,
while the guard still goes red if a second local `worktree`/`code_change` enum or
the retired symbol reappears.

**Rationale.** M6 (#3590) and M4's #3590 detector both depend on M7 landing first.
A guard written too strictly blocks M6 (AC-5). The guard asserts *absence of the
footgun* (no live `worktree`+`code_change` pairing; no `class ExecutionMode` in
`src/`; retired symbol absent from the mission_runtime surface), not the exact
member set of the renamed enum.

## Open questions / risks feeding plan & tasks

- **Final class name.** `WorkProductKind` vs `WorkPackageOutputKind` — resolve in
  plan; must not collide with any existing symbol. (`git grep` check required.)
- **External boundary.** Enum #3's `direct_repo` vs #2's `code_change` naming
  history persists across the `spec_kitty_events` package boundary; not reconcilable
  within M7 (out of scope).
- **Baseline-red attribution.** Behavior-preservation mission — must capture a green
  merge-base baseline for the targeted test surfaces before applying, so pre-existing
  reds are not misattributed.
- **Guard test placement.** Under `tests/architectural/` alongside the existing
  surface test, so it runs in the same CI gate.
