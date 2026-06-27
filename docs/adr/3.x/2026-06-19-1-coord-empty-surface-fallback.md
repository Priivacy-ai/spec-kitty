---
title: 'ADR: Coordination-Worktree-Empty Surface Policy — Loud Primary Fallback (amended)'
status: Superseded
date: '2026-06-19 (original) · **Amended**: 2026-06-21'
---

**loud primary fallback** decision in the Amendment section below.
**Mission**: `single-mission-surface-resolver-01KVGCE8` (WP06, original) ·
`mission-surface-resolver-safety-net-01KVN754` (amendment)
**Requirement**: FR-006 (`#1716`), bound to FR-001/FR-007 (single resolver)
**Module**: `src/specify_cli/coordination/surface_resolver.py`
**Tracker**: [#1716](https://github.com/Priivacy-ai/spec-kitty/issues/1716)

---

## Amendment (2026-06-21 — mission `mission-surface-resolver-safety-net-01KVN754`)

### Amended decision: coord-empty → **loud primary fallback** (not hard-fail)

A **materialized-but-empty coordination worktree NO LONGER hard-fails.** The
canonical resolver (`resolve_status_surface_with_anchor`) **falls back to the
primary checkout surface and proceeds**, but emits a **clear, structured,
operator-visible warning** at the fallback point. The read keeps working
(liveness); the staleness risk is made **loud and observable** so a human
operator or an orchestrating agent can intervene (flatten or repair) if desired.

### Why the reversal

The original decision (hard-fail, below) rejected primary fallback because it was
**silent** — a silent stale read is the `#1589`/`#1821` split-brain bug. That
rejection rationale is sound *for a silent fallback*. This amendment keeps the
fallback but **removes the silence**: the operator-visible warning names the
stale-surface risk and **both** recovery commands (collapse/flatten **or**
`spec-kitty agent worktree repair --mission <slug>`). The split-brain hazard the
original feared is a *silent* divergence; a *logged* divergence the operator can
see and act on is a different, acceptable trade.

Decisive field evidence: under the strict hard-fail, mission `01KVFTFV` was
forced to **flatten** (drop `coordination_branch`) just to make progress — i.e.
the ADR's own recovery path (a) became the routine workaround. A policy whose
escape hatch is the normal path is too strict for the operational reality;
liveness-with-observability is the better default.

### Scope of the amendment (binding)

- **Applies to the coord-empty state only**, at the canonical resolver seam.
- **Unchanged — still resolve primary (benign):** the create→first-write window
  and the no-coord topology (these were never hard-fails).
- **Unchanged — still HARD-FAIL (do not soften):** the **coord-deleted** state
  (`CoordinationBranchDeleted`, `#1848`). A declared-but-deleted coord branch
  carrying unmerged status is **data loss**, categorically worse than staleness;
  it must keep failing closed. Loud fallback is for *empty*, never for *deleted*.
- The warning is **non-silent and load-bearing**: a test asserts it fires on the
  coord-empty path (the fallback must be observable, not best-effort).

### Consequence for the typed-error surface

Coord-empty stops raising `CoordinationWorktreeEmpty`/`STATUS_READ_PATH_NOT_FOUND`
and instead returns the primary dir + warning. Callers that previously caught the
coord-empty hard-fail now receive a successful (warned) read. The genuinely
unresolvable / ambiguous cases still raise their typed errors (this mission's
typed-error-pass-through requirement is unaffected — coord-empty simply leaves
the error class).

> The original 2026-06-19 decision and its alternatives are retained below as
> historical record. Where they say "hard-fail on coord-empty", read "superseded
> by the loud primary fallback above".

### Stale reference correction (2026-06-21)

The original "Read-CLI residual (#2046)" consequence below is **stale**: #2046 is
**closed and fixed**. The operator read CLIs (`agent tasks status`,
`agent context`, `agent mission`, `decision`) now route through the unified
`missions/_read_path_resolver.resolve_handle_to_read_path`, which consumes the
`resolve_declared_mid8` cascade — so a bare-slug handle against a coord-topology
mission resolves its mid8 instead of silently reading primary. (`acceptance`
deliberately retains the lower `resolve_mission_read_path` with an explicit mid8
— the lenient acceptance-lane carve-out, blessed by the FR-010 selection guard.)
Mission `mission-surface-resolver-safety-net-01KVN754` does not re-do that work;
its differential characterization test **verifies and regression-guards** the
fix (the four `coord-*/bare` cells).

---

## Context

A Spec Kitty mission's status surface (`status.events.jsonl` /
`status.json`) lives in exactly one of two places, decided by topology:

* **primary checkout** — `kitty-specs/<slug>[-mid8]/` — for missions with no
  coordination branch (and during the create→first-write window).
* **coordination worktree** — `.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/`
  — for coord-topology missions, where lane processes write through
  `BookkeepingTransaction` and lanes sparse-exclude the status files.

There is a hazardous intermediate topology state — **coord-empty**: the mission
declares `coordination_branch` in its primary `meta.json`, the coordination
worktree ROOT has been materialized on disk, but it carries **no mission dir**
(no status surface yet). This is distinct from two adjacent, benign states:

* **create→first-write window** — `coordination_branch` declared, coord worktree
  root **not** materialized. The primary checkout legitimately holds the
  bootstrap status events; reading primary is correct.
* **no-coord** — no `coordination_branch` at all. Primary is the sole,
  authoritative, non-divergent surface.

Historically the resolver's coord-empty path either fell back to the primary
checkout (exposing a stale, split-brain status surface — the `#1589`/`#1821`
class) or raised a *bare* `StatusReadPathNotFound` with no operator guidance.

Before this mission the same coord-vs-primary selection was duplicated across
several resolvers (the read-path resolver, the surface resolver, the aggregate,
the mission-runtime boundary, and a 5th path-shape predicate site in
`status_transition.py`, `#1900`). A policy that lived in only one of those
copies would silently diverge.

## Decision

A **materialized-but-empty coordination worktree HARD-FAILS**. The single
canonical resolver (`coordination.surface_resolver.resolve_status_surface_with_anchor`
— FR-001/FR-007's sole selection authority) raises `CoordinationWorktreeEmpty`,
a carve-out of `StatusReadPathNotFound` that:

1. **Carries the same `error_code`** (`STATUS_READ_PATH_NOT_FOUND`) so every
   existing `except StatusReadPathNotFound` fail-closed handler keeps catching
   it and every caller that routes on the stable code keeps working. (This
   mirrors the sibling `CoordinationBranchDeleted` carve-out for the
   coord-deleted state, `#1848`/`#1889` R3.)
2. **Names BOTH operator recovery paths** in its message (NFR-004 — errors are
   actionable):
   * **(a) collapse/flatten** the mission — remove the `coordination_branch`
     key from `meta.json` so the primary checkout becomes authoritative; **OR**
   * **(b) recreate/populate** the coordination worktree — run
     `spec-kitty agent worktree repair --mission <slug>` so it carries the
     mission status surface.
3. **Never silently falls back to the primary checkout.** Reading primary here
   would expose a stale, split-brain status surface — the exact failure class
   the single-resolver mission exists to eliminate (FR-005/FR-006).

The hard-fail fires for **both** mission-handle forms — a bare `--mission <slug>`
and the canonical `--mission <slug>-<mid8>` — so the policy is handle-invariant.

This policy is **bound to the single resolver**: because FR-001/FR-007 collapsed
selection to `resolve_status_surface_with_anchor` (and the `#1900`
`status_transition.py` predicates were migrated to it, draining the C-002
topology-ratchet allowlist entry), there is exactly one place the coord-empty
decision is made, and no parallel resolver can contradict it.

## Distinctions preserved (what does NOT hard-fail)

* **create→first-write window** (coord declared, worktree NOT materialized) →
  the resolver composes the coord path and the aggregate's create-window gate
  keeps the **primary checkout authoritative** until the worktree exists. A
  regression that hard-failed here would break first-write on a freshly created
  coord mission. (Mutation-guarded by the equivalence test's
  `test_create_first_write_window_resolves_primary` and the surface-collapse
  test's `test_create_window_unmaterialized_coord_resolves_primary`.)
* **no-coord** → primary is authoritative; no hard-fail.
* **coord-deleted** (branch declared but deleted from git) → the distinct
  `CoordinationBranchDeleted` carve-out (`#1848`), not coord-empty.

## Consequences

* **Positive.** A genuinely broken coordination topology is surfaced **loudly
  and actionably** rather than silently degrading to a stale primary read. The
  operator is handed two concrete recovery commands. The policy is single-sourced
  on the canonical resolver, so it cannot drift across the (former) duplicate
  selection sites.
* **Bounded backward-compatibility.** `CoordinationWorktreeEmpty` subclasses
  `StatusReadPathNotFound` and reuses its `error_code`, so existing fail-closed
  handlers and code-based routing are unaffected; only the diagnostic is richer.
* **Known scope boundary.** The `MissionStatus` aggregate continues to translate
  the resolver's fail-closed signal to its own single boundary exception
  (`CoordAuthorityUnavailable`, WP04/FR-015–FR-023) for every handle form — a
  separately-tested public contract used by the `agent status` CLI. Converging
  the aggregate's *exception type* with the resolver's is therefore deferred (it
  would regress that boundary), and the corresponding equivalence-matrix cells
  remain documented, allowlisted strict-xfails (see
  `tests/missions/test_surface_resolution_equivalence.py`). The user-facing
  FR-006 two-path message is delivered regardless, at the resolver seam.
* **Read-CLI residual (#2046).** The operator read CLIs (`agent tasks status`,
  `agent context`, `agent mission`) call the lower `resolve_mission_read_path`
  primitive directly and are mid8-blind for a **bare slug**, so a bare-slug
  handle against a coord-topology mission still resolves the primary checkout
  rather than hard-failing here. Closing this needs the `resolve_declared_mid8`
  cascade inside the read path; it is tracked in **#2046** (the earlier deferral
  to the now-closed #1918 was incorrect, found by the post-merge architecture
  review). The four `coord-*/bare` equivalence-matrix cells are its acceptance gate.

## Alternatives considered

1. **Silent primary fallback.** Rejected: it is the split-brain bug
   (`#1589`/`#1821`) this mission exists to kill — a coord-declared mission that
   reads a stale primary surface mis-reports WP lane state.
2. **Bare `StatusReadPathNotFound` with no guidance.** Rejected: dead-ends the
   operator (violates NFR-004). The recovery is non-obvious (collapse vs
   repair), so the message must spell out both.
3. **Auto-repair (silently recreate/populate the worktree).** Rejected: the
   resolver is a read-side authority; mutating topology as a side effect of a
   read would be surprising and could mask a genuine teardown the operator
   intended. The repair path is offered as an explicit command instead.
