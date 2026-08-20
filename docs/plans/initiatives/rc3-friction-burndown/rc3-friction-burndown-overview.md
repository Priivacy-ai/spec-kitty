---
title: 'rc3 fail-loud friction burndown: program overview'
description: 'Program BLUF for the eight-mission rc3 crux — the fail-silent/fail-open root cause under epic #3410, the mission table (scope, issues, size, cluster), and what changes for users and operators.'
doc_status: draft
updated: '2026-08-20'
related:
- docs/plans/investigations/friction-bugs-processing-charter-root-cause.md
- docs/plans/initiatives/rc3-friction-burndown/rc3-friction-burndown-approach.md
- docs/plans/3-2-x-milestone-roadmap.md
- docs/plans/domains/doctrine-charter-domain-plan.md
- docs/architecture/mission-type-resolution.md
- docs/architecture/execution-lanes.md
---

# rc3 fail-loud friction burndown: program overview

**rc3's crux is a single discipline applied eight times: a decision point must
fail loud or surface the delta — never default, drop, or short-circuit in
silence.** The [pre-mission investigation](../../investigations/friction-bugs-processing-charter-root-cause.md)
ran seven friction issues through five profile-loaded research lenses, all
read-only, all re-verified against `main`. The lenses converged on one finding:
**six-and-a-half of the seven issues are the same disease** — a code path
*decides correctly* and the interface *says nothing* (or worse, prints a
fabricated success line while discarding operator intent). rc3 turns that
finding into eight scoped missions that close the known instances and, where the
class can recur, install a structural invariant so it cannot.

The umbrella is epic **#3410** — *"charter/doctrine silent-drop: must fail loud,
never fake-green"* — with **#3549** owning the event-pipeline half of the
vocabulary. These missions **adopt** that vocabulary; they do not mint a new
term. The organising contract is the **operator-signal contract**: *a state
change or a dropped input must emit an operator-visible signal (diff, console
line, warning, or error), or be a documented deliberate silence.*

## The root cause in one paragraph

Every mission below fixes the same shape at a different seam. A **coarse boolean
proxy** answers a question that should be asked of the **actually-declared
entity** (M3), a **field is written to one place and read from another** (M1,
M8), an **input validates then is silently dropped** before it reaches its
consumer (M2), a **mutation happens with no signal** (M4), **N hand-rolled
readers disagree** about the same fact (M5), a **completion has no honest
terminal state** so work fake-greens through `--force` (M6), or **one class name
means three contradictory things** (M7). The remedy is always the same: gate on
the declared entity, thread the input through one seam, fail loud when a route
cannot honor it.

## The two clusters

The investigation split the class into two bounded contexts that share the
*vocabulary* but must **not** share a *fix*. rc3 keeps that split:

- **Cluster A — charter/doctrine DRG-reach** (silent input-drop in doctrine
  projection and delivery): **M2, M3, M5**. Authored governance validates, loads,
  and is then silently lost — or a coarse set starves shipped configuration.
- **Cluster B — processing / workflow** (silent mutation/allocation in the
  operator CLI and lane model): **M1, M4, M6, M8**. Operator intent is discarded,
  a rollback is invisible, a WP cannot honestly terminate.
- **M7 is cross-cutting** — a canonical-source hygiene fix (three `ExecutionMode`
  classes, one axis collision) that both clusters brush against and that M6
  structurally depends on.

## The eight missions

| Mission | Scope (one line) | Issues | Size | Cluster |
|---------|------------------|--------|------|---------|
| **M1 — Lane base honoring** | `--base` fully replaces the coord parent; fail loud on any route that cannot honor it (kills the fabricated success line). Standalone P0, ships first. | #3571 (P0); refs #3460/#3462/#3536 | **S** | B (processing) |
| **M2 — DRG projection completeness** | Close both emit gaps (procedure rationale; type-wide governance projected as `scope` from `mission_type`) and the delivery residual, bound by an anti-divergence invariant; single post-merge re-ledger. #3488 is largely already fixed on `main` — the durable value is the invariant, not re-fixing. | #3605 + #3604 + #3488; fold `_DRG_NODE_KINDS` | **M/L** | A (DRG-reach) |
| **M3 — Charter gate predicate-inversion** | Five surfaces, one shape: gate on the declared entity, not a coarse hardcoded set. One policy-reversal ADR (tasks/retrospect start delivering; a typo'd `mission_type` hard-fails). | #3596 + #3598 + `_KNOWN_ACTIONS` + #3599/#3597 + #3407 | **L** | A (DRG-reach) |
| **M4 — Operator-signal / fail-loud sweep** | Six ground-level silent sites emit an operator-visible signal; roster splits work-state from review-state; warn-only post-integration-AC detector; authors an operator-signal-contract directive in the **internal** pack. | #3578 + #3590-interim + #3548 + #3517 + #3412 + #2991 | **M** | B (processing) |
| **M5 — Canonical mission-type reader** | One shared `read_mission_type()`; every reader converges downward to the canonical field; **legacy `{"mission":…}` resolution dropped entirely**; silent `software-dev` defaults removed. | #3598 (2nd half) + #2901 + #2477–#2480 | **M/L** | A (DRG-reach) |
| **M6 — WP terminal-state** | The largest correctness surface: a non-diff completion contract (D1) + an honest accept-tolerated terminal state (D2) + event-log↔`tasks/` reconciliation. **Depends on M7.** | #3590 (deep, both) + #2945 + #3432 + #3433 | **XL** | B (processing) |
| **M7 — ExecutionMode consolidation** | Retire the dead enum (a governance-gate change), rename the live ownership enum so no two classes share `ExecutionMode`; reserve room for M6's additive member. **Lands before M6.** | #3416 (widened) | **M** | cross-cutting |
| **M8 — Lane-allocation single-seam** | Recurrence prevention for the M1 class: one shared allocation seam + anti-bypass guard + authoritative topology predicate + read-side degrade companion + the no-coord refusal fix. **Soft-depends on M1.** | #3460 + #3462 + #3536 | **L** | B (processing) |

## What changes for users and operators

- **Operator intent stops being silently discarded (M1, M8).** `implement --base
  <ref>` either produces a lane that descends from `<ref>` alone, or it
  hard-errors naming the route and the unhonored base. The `→ Using explicit base
  ref` line is never printed on a path that then ignores the base.
- **Two deliberate behavior changes ship with an ADR (M3).** Non-canonical but
  *declared* actions (`tasks`, `retrospect`) begin delivering their doctrine
  grain; a **typo'd or typeless `mission_type` now hard-fails** instead of
  resolving silently with fabricated provenance. Both are sign-offs, not
  regressions — see the approach doc.
- **Legacy `{"mission":…}` missions must be migrated (M3 + M5).** M5 drops legacy
  resolution and M3 makes a typeless type hard-fail; together, an **unmigrated**
  legacy mission goes silently-resolving → typeless → hard-fail. A dedicated
  `mission_type` backfill (not covered by `migrate backfill-identity`, which mints
  only `mission_id`) **must land and run before either reaches real projects**.
  This is the program's load-bearing gate.
- **Silent state changes become legible (M4).** A rollback-to-`planned` reports
  how many subtasks it reset; an orchestrator-api refusal keeps both its message
  and its structured payload; a malformed manifest fails loud instead of reading
  as "absent."
- **A completed-but-diffless WP has an honest home (M6).** Action/observation/
  verdict WPs reach a terminal lane without `--force` and without checking
  post-integration subtasks they cannot honestly claim; `accept` tolerates a
  provenance-backed cancel instead of forcing a false approval.
- **Authored governance reaches the agent (M2).** Procedure rationale and a
  mission type's type-wide governance selections now project into the DRG; the
  `plan` mission type stops cascading to empty.

## See also

- [Processing & charter friction bugs: shared root causes and mission scope](../../investigations/friction-bugs-processing-charter-root-cause.md) — the five-lens investigation this program executes.
- [rc3 friction burndown: delivery approach & sequencing](rc3-friction-burndown-approach.md) — the dependency DAG, wave sequencing, behavior-change sign-offs, and cut/land plan.
- [Doctrine & Charter — Domain Plan](../../domains/doctrine-charter-domain-plan.md) — the durable throughline Cluster A feeds.
- [Mission-type resolution](../../../architecture/mission-type-resolution.md) · [Execution lanes](../../../architecture/execution-lanes.md) — the architecture surfaces M3/M5 and M1/M8 touch.
