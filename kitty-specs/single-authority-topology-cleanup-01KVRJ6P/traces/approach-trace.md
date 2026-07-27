# Approach Trace — single-authority-topology-cleanup-01KVRJ6P

**Purpose:** a running log of the METHODOLOGY used to plan + run this mission — the
front-loaded research, the multiple adversarial squads across spec→tasks, and the WP
sizing — so we can assess afterward whether the approach paid off (squad ROI, sizing
realism, front-loading vs discovery-during-implement).

---

## Seeded during spec → plan → tasks (2026-06-23)

### Heavy front-loaded research
- **#1716 design squad (4 agents)** designed the resolve_target SSOT (alphonso seam /
  paula matrix / randy consolidation / debbie live-evidence) BEFORE this mission's
  scope was finalized — stored in #1716. It (a) carved the right scope for this mission
  vs the #2090 follow-on, (b) surfaced the "kind×intent×topology" keying + the
  residue-as-derived insight that shaped FR-012, (c) gave the forward-#1716 acceptance
  criteria the post-tasks squad checked against.
- **Operator `topology=None` absorption insight** (mid-research) folded into FR-004 —
  turned a "KEEP-until-backfill" band-aid into an in-scope, behavior-improving collapse.
- **Dedup-research squad** (paula+randy+alphonso) corrected the LOC scope (the C2/C6
  clusters are the real dedup; the resolution chains are load-bearing).

### Multiple squads across spec → tasks (the cadence)
| Point-cut | Squad | Outcome |
|-----------|-------|---------|
| post-spec | priti+paula+alphonso (consistency + related-tickets) | folded #1887/#1891 (FR-012/FR-013); carved the write-side twin to #1716 (C-012); CONSISTENT-AND-GROUNDED |
| post-plan | randy+alphonso (brownfield) | 4th residue site (auto_rebase); IC-02×IC-04 collision; meta-reader count re-baseline; safe_commit shim |
| (mid) | debbie+alphonso+pedro (mid8 root-cause) | the #2091 fix design (primary-anchored identity) — folded into PR #2089 |
| post-tasks #1 | renata+paula+alphonso+randy (anti-laziness) | build-break ownership seam; FR-006 undersize; fakeable-DoD hardening; forward-#1716 ALIGNED |
| post-tasks #2 | daphne+randy+paula (test-suite-pitfall) | reusable doctrine test-standard for every WP; CT1 re-key obligation; the mutation blind-spot (differential gate proves legs-agree not mapping-correct) |

### Squad discipline applied
- Bounded (2–4), profile-LOADED, structured output, model discipline, second-opinion on
  divergence (e.g. alphonso vs pedro on the mid8 fix — adjudicated to the primary-anchor
  via the core/paths.py precedent). The squads caught a **build-break** and a **mutation
  gap** that static reading missed.

### WP sizing
- 13 WPs / 6 lanes / 26 subtasks. IC-to-WP intentionally NOT 1:1. Lane B = the entangled
  `CommitTargetKind` core (17 files) as a **sequential same-lane chain** (WP02→07) — only
  viable because the #2088 fix made the validator allow same-lane shared ownership. Lanes
  C/D/E/F disjoint. The same-lane model is itself a methodology bet to assess.

### Methodology lessons banked (→ doctrine/memory)
- **Red-first reproduction** through the stable entry point (operator caught a fix-then-
  test-new-API slip → DIRECTIVE_034 amended, memory stored).
- **Failing-test remediation framework** (classify stale/stub/valid; causation by code-path
  coupling not git-blame → DIRECTIVE_041 amended).
- **Fix-in-the-PR** (mid8 #2091 folded into #2089 to merge green rather than a separate PR).

## During / after implement — APPEND BELOW
<!-- Assess: did front-loading reduce implement churn? which squad gave the highest ROI?
     did WP sizing hold (any WP blow past 10 subtasks / need re-split)? did the same-lane
     sequential chain work in the loop, or fight it? was the heavy research over- or
     under-invested vs what the implement loop actually needed? -->

_(append during/after implement)_
